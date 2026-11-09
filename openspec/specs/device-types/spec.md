# Capability: device-types

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06). | Pass 3 (scenario-ification) applied 2026-11-09.

## Purpose

This capability covers the concrete device classes layered on top of the base `Device` class: the three built-ins (`OutletDevice`, `BulbDevice`, `CoverDevice` in `tinytuya/`) and the community-contributed subclasses in `tinytuya/Contrib/`. Built-ins add device-specific semantics on the shared connection/status mechanics owned by the device-control capability: dimmer levels for outlets, a bulb-type auto-detection plus colour-mode/colour-conversion model for lights, and an eight-command-type auto-detected control lexicon for covers. `Contrib/` defines a documented subclass contract (module naming, `Device` inheritance, import pattern) for community device modules such as `ThermostatDevice` and `IRRemoteControlDevice`.

## Primary code locations
- `tinytuya/OutletDevice.py` — smart plug/switch subclass; adds `set_dimmer()`.
- `tinytuya/BulbDevice.py` — light subclass; bulb type A/B/C/None detection, DP-set model, HSV/RGB hex conversions, scene/music modes.
- `tinytuya/CoverDevice.py` — window-cover subclass; 8 command types with automatic detection.
- `tinytuya/Contrib/README.md` — contributed device catalog and "submit your device" template pointer.
- `tinytuya/Contrib/__init__.py` — deprecated legacy registration list (`DeviceTypes`); kept for backward compatibility.
- `tinytuya/Contrib/ThermostatDevice.py` — reference template Contrib class (sensors, setpoints, schedules).
- `tinytuya/Contrib/IRRemoteControlDevice.py` — Contrib class with class-level DP/NSDP constants and control-type detection.
- `tinytuya/__init__.py` — exports the three built-in classes at package top level.
- `API.md` § Class Hierarchy / OutletDevice / BulbDevice / CoverDevice — user-facing documentation.
- `DP_Mapping.md` — how DPS-to-name mappings are obtained (cloud devices.json / DP Instruction Mode).

## Requirements

### Requirement: Built-in class hierarchy over Device
The library SHALL expose `OutletDevice`, `BulbDevice` and `CoverDevice` as subclasses of the core `Device` class, exported from the top-level `tinytuya` package, so every built-in type inherits the shared constructor signature and Device commands (set_status, turn_on, set_value, status, etc.).
**Status**: VERIFIED
**Evidence**: doc: API.md § Class Hierarchy (`XenonDevice → Device → {OutletDevice, BulbDevice, CoverDevice}`)
**Anchor**: `tinytuya/__init__.py:96-98`; `tinytuya/OutletDevice.py:48-50`; `tinytuya/BulbDevice.py:50-54`; `tinytuya/CoverDevice.py:70-72`

#### Scenario: Subclasses inherit shared constructor and Device commands
- **WHEN** an application uses any built-in class (`OutletDevice`, `BulbDevice`, `CoverDevice`)
- **THEN** the class shares the constructor signature and connection methods from `XenonDevice`
- **AND** `Device` adds commands such as `set_status`, `turn_on`, `set_value`, while subclasses add device-specific helpers on top
- Source: doc: API.md § Class Hierarchy "All device classes share the constructor signature and connection methods"
- Source: doc: API.md § Class Hierarchy "Device adds commands such as set_status, turn_on, set_value"

### Requirement: Outlet dimmer control with percentage and raw value
`OutletDevice.set_dimmer()` SHALL accept either a percentage (0–100, scaled to raw 0–255) or a raw `value`, default the dimmer to DPS index 3, clamp non-zero levels to a minimum of 25 and maximum of 255, and delegate to inherited `turn_on()` + `set_value()` — while a level of 0 SHALL turn the device off via `turn_off()` instead of writing a value.
**Status**: VERIFIED
**Evidence**: doc: API.md § OutletDevice (`d.set_dimmer(0) # turns device off via turn_off()`); OutletDevice is otherwise a pure Device subclass ("adds dimmer support")
**Anchor**: `tinytuya/OutletDevice.py:55-78` (scale at :66, off at :70-71, clamp at :73-76)

#### Scenario: Dimmer percentage maps to the raw range on the default dimmer DPS
- **WHEN** `set_dimmer()` is called with a percentage of 0-100 on a plug/switch with dimming support
- **THEN** the level maps to the 0-255 raw range on the dimmer DPS index, default `3`
- **AND** a raw `value` of 0-255 may be supplied instead of a percentage
- Source: doc: API.md § OutletDevice "0-100 (maps to 0-255 raw)"
- Source: doc: API.md § OutletDevice "DPS index for the dimmer (default 3)"
- Source: doc: API.md § OutletDevice "raw value 0-255 (alternative to percentage)"

#### Scenario: Setting the dimmer to zero turns the device off
- **WHEN** `set_dimmer(0)` is called
- **THEN** the device is turned off via `turn_off()` instead of writing a zero value
- Source: doc: API.md § OutletDevice "turns device off via turn_off()"

### Requirement: Bulb type auto-detection from DPS key sets
`BulbDevice.detect_bulb()` SHALL classify a device as Type A, B, C or 'None' from the DPS indexes present in a status response: DP 20+21 → Type B; DP 1+2 with DP 2 a string → Type A (mode) else Type C (brightness); both DP 1 and DP 20 present → type 'None' (probably not a bulb). Types A/B/C map to the Tuya product-function DP layout per the cited Tuya developer doc.
**Status**: VERIFIED
**Evidence**: [PR #617](https://github.com/jasonacox/tinytuya/pull/617) — BulbDevice rewrite (v1.17.0) introducing DPSET-based detection; doc: API.md § BulbDevice type table (A/B/C, switch DPS 1/20/1)
**Anchor**: `tinytuya/BulbDevice.py:840-891` (rules at :880-891, Tuya doc ref at :878)

#### Scenario: Bulb type auto-detected from a status response
- **WHEN** `detect_bulb()` is run against a device's status response
- **THEN** the bulb type is resolved to 'A', 'B', 'C', or None from the DPS indexes reported
- Source: doc: API.md § detect_bulb "Auto-detect bulb type from a status response or by calling"

#### Scenario: Type A and Type B distinguished by DPS layout
- **WHEN** a bulb reports DPS index 1-5 with the switch on index 1
- **THEN** it is treated as Type A (older RGB+CCT); a device using DPS indexes 20-27 with no index 1 is treated as Type B
- Source: [relnote v1.1.1] "Type A - Uses DPS index 1-5 and represents color with RGB+HSV"
- Source: [relnote v1.1.1] "Type B - Uses DPS index 20-27 (no index 1)"

### Requirement: Per-type default DP sets with value ranges and hex format
Each bulb type SHALL carry a `DEFAULT_DPSET` entry mapping features (switch, mode, brightness, colourtemp, colour, scene, scene_data, timer, music) to DPS indexes plus `value_min`/`value_max` and `value_hexformat`: A = DP 1–8, 25–255, `rgb8`; B = DP 20–28, 10–1000, `hsv16`; C = DP 1–3, 25–255, `rgb8`; 'None' = DP 1 only, 0–255, `rgb8`.
**Status**: VERIFIED
**Evidence**: doc: API.md § BulbDevice table (A brightness 25–255, B 10–1000); commit `ff3a5000` "Rewrite BulbDevice"
**Anchor**: `tinytuya/BulbDevice.py:80-136`

#### Scenario: Per-type brightness ranges from the documented type table
- **WHEN** a Type A bulb is configured from its default DP set
- **THEN** brightness uses the 25-255 range; a Type B bulb instead uses 10-1000
- Source: doc: API.md § BulbDevice "Older RGB+CCT (brightness 25-255)"
- Source: doc: API.md § BulbDevice "Newer RGB+CCT (brightness 10-1000)"

#### Scenario: Colour hex format follows the bulb type
- **WHEN** a colour value is encoded for a Type A bulb
- **THEN** the hex format is rrggbb0hhhssvv; a Type B bulb instead encodes hhhhssssvvvv
- Source: [relnote v1.1.1] "Index: 5 in hex format: rrggbb0hhhssvv"
- Source: [relnote v1.1.1] "Index: 24 in hex format: hhhhssssvvvv"

### Requirement: Lazy bulb configuration with explicit failure
`BulbDevice` SHALL defer configuration until first contact (constructor forces `version=None` to avoid an immediate status call; `status()` triggers `detect_bulb()` on first DPS payload), and percentage getters/setters SHALL call `detect_bulb()` before reading `value_max` and raise `RuntimeError` if the bulb still is not configured.
**Status**: VERIFIED
**Evidence**: [PR #714](https://github.com/jasonacox/tinytuya/pull/714) — `set_brightness_percentage()`/`set_colourtemp_percentage()` now call `detect_bulb()` before reading `value_max`, preventing `AttributeError` (v1.19.0); regression test `test_percentage_raises_when_unconfigured`
**Anchor**: `tinytuya/BulbDevice.py:174-184`, `:596-599`, `:664-667`, `:716-719`, `:768-769`; test: `tests.py:281`

#### Scenario: Percentage setters auto-detect before reading value_max
- **WHEN** `set_brightness_percentage()` or `set_colourtemp_percentage()` is called on a newly created `BulbDevice` instance
- **THEN** `detect_bulb()` is called before reading `value_max`, preventing `AttributeError`
- Source: [relnote v1.19.0] "now call `detect_bulb()` before reading `value_max`, preventing `AttributeError` on newly created `BulbDevice` instances"

#### Scenario: Unconfigured percentage call raises RuntimeError
- **WHEN** a `*_percentage()` setter is called before bulb detection with no cached status available
- **THEN** the call raises `RuntimeError` instead of silently computing with an unset `value_max`
- Source: test: tests.py::TestXenonDevice::test_percentage_raises_when_unconfigured

### Requirement: Manual bulb type and DP-capability override
`BulbDevice` SHALL let users override auto-detection via `set_bulb_type(bulb_type, mapping)` / `set_bulb_capabilities(mapping)`, which fill each dpset key from the user mapping first, then the type default, and mark the bulb configured once switch and brightness DPs are known.
**Status**: VERIFIED
**Evidence**: commit `e94b972f` "Fix BulbDevice set_bulb_type()"; doc: `examples/bulb.py:45,62` (`#d.set_bulb_type('B')`, `d.set_bulb_capabilities(mapping)`)
**Anchor**: `tinytuya/BulbDevice.py:921-942`

#### Scenario: Manual bulb type override
- **WHEN** auto-detection is unsuitable and the user calls `set_bulb_type()`
- **THEN** the bulb type and DPS mapping are set manually
- Source: doc: API.md § set_bulb_type "Manually set the bulb type and DPS mapping."
- Source: [relnote v1.2.7] "Added Bulb type C and manual setting function"

#### Scenario: Manually typed bulb writes its mapped switch DP
- **WHEN** `set_bulb_type('C')` is declared for a device whose status reports switch DP 1
- **THEN** a subsequent `turn_on()` writes the switch DP using the manually configured mapping
- Source: test: tests.py::TestXenonDevice::test_set_bulb_type

### Requirement: Tuya colour hex encodings rgb8 and hsv16
The bulb colour model SHALL provide static converters between RGB/HSV and the two Tuya hex encodings: `rgb8` = `rrggbbhhhhssvv` (h scaled 0–360, s/v 0–255) and `hsv16` = `hhhhssssvvvv` (h 0–360, s/v 0–1000), with input-range validation (`ValueError` outside 0–255 for RGB, 0–1.0 for HSV) and length-based auto-detection (6/14 hex digits → rgb8, 12 → hsv16) when `hexformat=None`.
**Status**: VERIFIED
**Evidence**: commit `27aa6986` "fix: correct 16 verified bugs across Cloud, core, Bulb…" (RELEASE.md v1.20.0: "BulbDevice rgb8 hue offset fixed"); round-trip unit test `test_rgb8_round_trip`
**Anchor**: `tinytuya/BulbDevice.py:186-228` (rgb_to_hexvalue), `:243-275` (hsv_to_hexvalue), `:277-320` (hexvalue_to_rgb), `:334-379` (hexvalue_to_hsv); test: `tests.py:481-486`

#### Scenario: RGB and HSV encode to the Tuya hex formats
- **WHEN** `rgb_to_hexvalue()` is called with RGB values 0-255
- **THEN** the Tuya hex string is produced in the requested format: 'rgb8' as rrggbb0hhhssvv (Type A) and 'hsv16' as hhhhssssvvvv (Type B)
- **AND** `hsv_to_hexvalue()` accepts HSV values 0.0-1.0 in the same encodings
- Source: doc: API.md § Colour Conversion Helpers "Convert RGB (0-255) to Tuya hex string"
- Source: doc: API.md § Colour Conversion Helpers "Convert HSV (0.0-1.0) to Tuya hex string"

#### Scenario: Hex values round-trip back to RGB/HSV
- **WHEN** an encoded Tuya hex string is converted back with `hexvalue_to_rgb()` / `hexvalue_to_hsv()`
- **THEN** the original (r, g, b) tuple is recovered, with the rgb8 encoding verified by a round-trip regression test
- Source: doc: API.md § Colour Conversion Helpers "Convert Tuya hex string back to (r, g, b) tuple."
- Source: test: tests.py::TestHexvalueRoundTrip::test_rgb8_round_trip

### Requirement: Colour set semantics switch mode and power
`set_colour(r,g,b)` and `set_hsv(h,s,v)` SHALL encode the colour in the detected bulb's `value_hexformat` and send it together with `mode='colour'` and `switch=True`, skipping any DP that already holds the target value when a cached status exists (delta-send via `_set_values_check()`), and SHALL return an `ERR_FUNCTION` error JSON if the device lacks the colour capability.
**Status**: VERIFIED
**Evidence**: [PR #617](https://github.com/jasonacox/tinytuya/pull/617) — rewrite reworked `set_multiple_values()`/delta sending; unit tests `test_set_colour_A` / `test_set_colour_B`
**Anchor**: `tinytuya/BulbDevice.py:536-575` (set_colour/set_hsv), `:393-418` (`_set_values_check`); tests: `tests.py:138,159`

#### Scenario: set_colour sends colour, mode and switch together (Type A)
- **WHEN** `set_colour(255, 127, 63)` is called on a Type A bulb
- **THEN** the control payload carries the encoded colour DP together with mode 'colour' and switch True
- Source: doc: API.md § set_colour "Set colour using RGB values (0-255 each)."
- Source: test: tests.py::TestXenonDevice::test_set_colour_A

#### Scenario: Same semantics on Type B with the hsv16 colour DP
- **WHEN** `set_colour(255, 127, 63)` is called on a Type B bulb
- **THEN** the payload writes the Type B switch, mode and colour DPs (20, 21, 24) with the hsv16-encoded colour value
- Source: test: tests.py::TestXenonDevice::test_set_colour_B

### Requirement: Percentage setters as primary API, raw setters deprecated
The primary white/brightness/colour-temperature API SHALL be the percentage-based `set_white_percentage()`, `set_brightness_percentage()` and `set_colourtemp_percentage()` (0–100, scaled by the bulb's `value_max`); the raw-value `set_white()`, `set_brightness()` and `set_colourtemp()` SHALL be marked deprecated, and `set_brightness()` SHALL adapt to the current mode — white-mode bulbs via `set_white()`, colour-mode bulbs by rescaling HSV value — and turn the bulb off below `value_min`.
**Status**: VERIFIED
**Evidence**: doc: BulbDevice.py DEPRECATED docstrings at `:606-607`, `:671-672`, `:723-724`; API.md § set_white_percentage/set_brightness_percentage; unit tests `test_set_white_A/B`, `test_set_brightness_C`
**Anchor**: `tinytuya/BulbDevice.py:577-604`, `:654-704` (mode-aware at :691-704), `:706-744`; tests: `tests.py:180,201,220`

#### Scenario: Percentage API sets white mode as percentages
- **WHEN** `set_white_percentage(brightness, colourtemp)` is called with values 0-100
- **THEN** white mode is set with brightness and colour temperature applied as percentages
- **AND** `set_brightness_percentage()` sets brightness in percent (0-100) without changing colour temp or mode
- Source: doc: API.md § set_white_percentage "Set white mode with brightness and colour temperature as percentages (0-100)."
- Source: doc: API.md § set_brightness_percentage "Set brightness in percent (0-100) without changing colour temp or mode."
- Source: test: tests.py::TestXenonDevice::test_set_white_A

#### Scenario: Raw set_brightness adapts to the current bulb mode
- **WHEN** `set_brightness()` is called on a bulb in either white or colour mode
- **THEN** the brightness update is handled for both *white* and *colour* modes
- Source: [relnote v1.2.3] "Updated `set_brightness()` in BulbDevice to handle *white* and *colour* modes"

### Requirement: BulbDevice usable on non-bulb devices
`BulbDevice` SHALL remain functional as a generic device wrapper: `turn_onoff()` defaults the switch to DPS 1 when no bulb switch DP was detected, and detection classifies devices reporting both DP 1 and DP 20 as type 'None' rather than failing.
**Status**: VERIFIED
**Evidence**: [PR #620](https://github.com/jasonacox/tinytuya/pull/620) — "Fix BulbDevice for non-bulb devices… allow BulbDevice to be used even for non-bulb devices, e.g. turn_on() & turn_off()" (v1.17.1); [PR #625](https://github.com/jasonacox/tinytuya/pull/625) — "Update BulbDevice for non-bulb devices again" (v1.17.2); test `test_not_a_bulb`
**Anchor**: `tinytuya/BulbDevice.py:420-436`, `:880-883`; test: `tests.py:260`

#### Scenario: BulbDevice drives a non-bulb device
- **WHEN** `BulbDevice` is pointed at a device that is not a bulb
- **THEN** it can still be used for basic switching, e.g. `turn_on()` and `turn_off()`
- Source: [relnote v1.17.1] "allow BulbDevice to be used even for non-bulb devices, e.g. `turn_on()` & `turn_off()`"

#### Scenario: Switch-only device still toggles via the default DP
- **WHEN** detection finds only a plain switch DP (no bulb DP set) and `turn_on()` is called
- **THEN** the device's switch DP is written with True instead of failing bulb classification
- Source: test: tests.py::TestXenonDevice::test_not_a_bulb

### Requirement: Music-mode frame composition
`set_music_colour()` SHALL compose a music-DP frame of transition nibble + colour hex in the bulb's `value_hexformat` + brightness and colourtemp scaled into `value_max` with a width matching the format (`%02x` for rgb8, `%04x` for hsv16) and write it to the music DP, returning `ERR_FUNCTION` when the device has no music capability; the bulb is put into music mode by the inherited mode setter (`set_mode('music')`).
**Status**: VERIFIED
**Evidence**: doc: API.md § set_music_colour, `MUSIC_TRANSITION_JUMP`/`MUSIC_TRANSITION_FADE` examples; example `examples/bulb-music.py:45,65,69` uses `set_mode('music')` then `set_music_colour()`
**Anchor**: `tinytuya/BulbDevice.py:77-78` (transition constants), `:504-534`

#### Scenario: Single colour frame while in music mode
- **WHEN** the bulb is put into music mode via `set_mode('music')`
- **THEN** the operating mode becomes 'music'
- **AND** each `set_music_colour(transition, red, green, blue)` call sets a single colour frame while in music mode
- Source: doc: API.md § set_mode "Set operating mode: 'white', 'colour', 'scene', or 'music'."
- Source: doc: API.md § set_music_colour "Set a single colour frame while in music mode."

### Requirement: CoverDevice eight command-type lexicons
`CoverDevice` SHALL support exactly 8 open/close/stop/continue command vocabularies (COVER_TYPES 1–8: `open/close/stop/continue`; `true/false`; `'0'/'1'/'2'`; `'00'/'01'/'02'/'03'`; `fopen/fclose`; `on/off/stop`; `up/down/stop`; `ZZ/FZ/STOP`) and expose `open_cover()`, `close_cover()`, `stop_cover()` and `continue_cover()` which translate the action into the active type's command value.
**Status**: VERIFIED
**Evidence**: RELEASE.md v1.17.5 "CoverDevice: Major rewrite to support 8 different device command types with automatic detection"; issue #653 credit @make-all; commits `70810f61`, `8b7daecb`, `ef895fb4` ("#653")
**Anchor**: `tinytuya/CoverDevice.py:89-146` (table), `:236-300` (four action methods)

#### Scenario: Eight command vocabularies with automatic detection
- **WHEN** a CoverDevice sends cover commands
- **THEN** it uses one of 8 different device command types with automatic detection, e.g. Type 1 open/close/stop/continue for most curtains, blinds, roller shades
- **AND** the lexicons range from Type 2 true/false for simple relays, garage doors, locks to Type 8 ZZ/FZ/STOP vendor-specific commands
- Source: [relnote v1.17.5] "support 8 different device command types with automatic detection"
- Source: [relnote v1.17.5] "Most curtains, blinds, roller shades (DEFAULT)"
- Source: [relnote v1.17.5] "Simple relays, garage doors, locks"
- Source: [relnote v1.17.5] "Vendor-specific (Abalon-style, older standard)"

#### Scenario: Directional-only lexicon has no stop
- **WHEN** a cover is detected as the fopen/fclose directional binary type
- **THEN** it supports only the directional open/close commands (no stop)
- Source: [relnote v1.17.5] "Directional binary (no stop)"

### Requirement: One-shot cover type detection with priority and safe default
`CoverDevice` SHALL auto-detect the command type once, on the first command, by matching the cover DPS value from a `status()` read against each type's `detect_values` using priority order 1→8→3→4→5→7→2→6, defaulting to Type 1 when no value matches or the status call fails, and `set_cover_type(type_id)` SHALL allow manual override with `ValueError` for ids outside 1–8.
**Status**: VERIFIED
**Evidence**: RELEASE.md v1.17.5 ("automatically detected on first command using priority ordering… Defaults to Type 1 if detection fails"); doc: `tinytuya/CoverDevice.py:22-36` header notes citing issue #653
**Anchor**: `tinytuya/CoverDevice.py:153-195` (priority at :184, default at :168-169), `:197-215`

#### Scenario: Type auto-detected on first command by frequency priority
- **WHEN** the first cover command is issued
- **THEN** the device type is automatically detected on first command using priority ordering based on real-world frequency
- **AND** the ordering starts Type 1 (most common), then Type 8 (second most common, older standard), then Type 3
- Source: [relnote v1.17.5] "automatically detected on first command using priority ordering based on real-world frequency"
- Source: [relnote v1.17.5] "Priority: Type 1 (most common) → Type 8 (second most common, older standard) → Type 3"

#### Scenario: Safe default and manual override when detection cannot match
- **WHEN** detection fails to identify a command type
- **THEN** the device defaults to Type 1 for best compatibility
- **AND** `set_cover_type(type_id)` can manually override the auto-detection
- Source: [relnote v1.17.5] "Defaults to Type 1 if detection fails for best compatibility"
- Source: [relnote v1.17.5] "method to manually override auto-detection"

### Requirement: Cover action dispatch with default switch and silent no-op
Cover action methods SHALL default the target DPS to `DPS_INDEX_MOVE` ("1") when `switch` is None, and SHALL silently do nothing (no error) when the detected type does not support the action — stop is unsupported for Types 2 and 5, continue only for Types 1 and 4.
**Status**: VERIFIED
**Evidence**: RELEASE.md v1.17.5 "Added `continue_cover()` method for device types that support it (Types 1 and 4)"; commit `732a3040` "Refactor CoverDevice methods to use DPS_INDEX_MOVE as default switch value"
**Anchor**: `tinytuya/CoverDevice.py:79` (DPS_INDEX_MOVE), `:244-249` (default + None-guard pattern), `:274-275`, `:292-293` (support notes)

#### Scenario: Cover action commands
- **WHEN** the user calls `open_cover()` or `close_cover()`
- **THEN** the device is sent the open or close command
- **AND** `stop_cover()` stops cover movement
- Source: doc: API.md § CoverDevice "Send the open command."
- Source: doc: API.md § CoverDevice "Send the close command."
- Source: doc: API.md § CoverDevice "Stop cover movement."

### Requirement: Contrib subclass contract and naming convention
A community device module SHALL be a single file `tinytuya/Contrib/<Name>Device.py` defining a class of the same name that subclasses `core.Device` (imported as `from ..core import Device, …`), passes `*args/**kwargs` through to `super().__init__()`, and may override constructor defaults (e.g. force `version=3.3` and `persist=True`) or declare class-level DPS constants for its own protocol.
**Status**: VERIFIED
**Evidence**: doc: `tinytuya/Contrib/README.md:275-278` "Follow the template example in ThermostatDevice.py to add your device"; [PR #711](https://github.com/jasonacox/tinytuya/pull/711) — new FloorFanDevice contributed this way (v1.19.0)
**Anchor**: `tinytuya/Contrib/ThermostatDevice.py:218,220,260-268`; `tinytuya/Contrib/IRRemoteControlDevice.py:119,121,154-158` (DP/NSDP constants at :122-137)

#### Scenario: Adding a community device module
- **WHEN** a contributor wants to add support for a new device
- **THEN** they follow the template example in ThermostatDevice.py to add the device as a contributed module
- Source: doc: tinytuya_Contrib_README.md § Submit Your Device "Follow the template example in ThermostatDevice.py to add your device"

#### Scenario: New Contrib class ships for contributed hardware
- **WHEN** a community member contributes a new device class, such as the Comfort Zone floor standing tower fan
- **THEN** it ships as a Contrib device class (FloorFanDevice)
- Source: [relnote v1.19.0] "New device class for Comfort Zone floor standing tower fan (CZTF423S)"

### Requirement: Contrib import pattern with deprecated __init__ registry
New Contrib device modules SHALL be consumed via `from tinytuya.Contrib import YourNewModule` and instantiated as `YourNewModule.YourNewModule(...)` without being registered in `tinytuya/Contrib/__init__.py`, which is deprecated and retained only for backward compatibility with the old `from tinytuya import Contrib` style and its `DeviceTypes` listing.
**Status**: VERIFIED
**Evidence**: [PR #466](https://github.com/jasonacox/tinytuya/pull/466) — deprecates `tinytuya/Contrib/__init__.py`; [PR #686](https://github.com/jasonacox/tinytuya/pull/686) — "Revert deprecated Contrib/__init__.py" (v1.18.0); commit `34e6f449` "use preferred import pattern"
**Anchor**: `tinytuya/Contrib/__init__.py:1-15` (deprecation notice, `DeviceTypes` at :15); `testcontrib.py:4-9,17-27`

#### Scenario: Direct module import for Contrib devices
- **WHEN** an application consumes a Contrib module
- **THEN** the documented usage imports it directly from tinytuya.Contrib and instantiates it as Module.Module(...)
- Source: doc: API.md § Contrib Modules "from tinytuya.Contrib import ThermostatDevice"
- Source: doc: API.md § Contrib Modules "thermo = ThermostatDevice.ThermostatDevice"

#### Scenario: Legacy registry deprecated in favour of the preferred import pattern
- **WHEN** registration in the legacy Contrib `tinytuya/Contrib/__init__.py` registry is considered for a new module
- **THEN** that registry is deprecated and the preferred import pattern is used instead, as reflected in the updated `testcontrib.py` and Contrib README
- Source: [relnote v1.13.2] "Deprecates Contrib/__init__.py"
- Source: [relnote v1.19.0] "Updated `testcontrib.py` and `Contrib/README.md` to use the preferred import pattern"

### Requirement: DPS-to-name mapping sourced from cloud devices.json
DPS indexes SHALL be presented to users with human-readable names sourced from the Tuya Cloud download in `devices.json` (since TinyTuya v1.12.8); when that mapping is wrong for a product, the documented remedy is to switch the product's Control Instruction Mode to "DP Instruction" in the Tuya IoT developer console and re-poll.
**Status**: INFERRED
**Evidence**: doc: DP_Mapping.md (whole file — steps 1–6 for enabling DP Instruction mode and rebuilding devices.json)
**Anchor**: anchor not located (cloud-side behavior; devices.json loading is owned by the cloud-api / device-control capabilities)

#### Scenario: DPS names come with the devices.json download
- **WHEN** TinyTuya downloads the cloud device list into devices.json (since v1.12.8)
- **THEN** DPS-to-name mappings are included with the download
- Source: doc: DP_Mapping.md § Tuya Cloud - Changing the Control Instruction Mode "DPS to Name mappings are now downloaded with devices.json starting with TinyTuya v1.12.8"
- Source: [relnote v1.12.8] "New Cloud functions to download DP Name mappings"

#### Scenario: Wrong mapping is fixed via DP Instruction mode
- **WHEN** the downloaded DPS mapping for a product is not correct
- **THEN** the documented remedy is to change the Control Instruction Mode to DP Instruction Mode for the device type
- **AND** then delete devices.json and re-run the Wizard to pull the full DPS list
- Source: doc: DP_Mapping.md § How to get the full DPS mapping from Tuya Cloud "If this DPS mapping is not correct then you will need to change the Control Instruction Mode to DP Instruction Mode"
- Source: doc: DP_Mapping.md § How to get the full DPS mapping from Tuya Cloud "Simply delete devices.json and re-run the Wizard"

## Known gaps / open questions
- DOC/CODE DRIFT — `set_musicmode()` and `unset_musicmode()` are documented in API.md § BulbDevice (lines ~556-562) and listed in the `tinytuya/BulbDevice.py` module docstring (`tinytuya/BulbDevice.py:24-25`), and `set_music_colour()`'s own docstring references `set_musicmode()` (`:514`), but no `def set_musicmode`/`def unset_musicmode` exists anywhere in the package at this pin; the shipped example uses `set_mode('music')` instead (`examples/bulb-music.py:45`).
- DOC/CODE DRIFT — API.md § CoverDevice documents signatures `open_cover(switch=1, nowait=False)` (and same for close/stop), while the code defaults `switch=None` resolved to `DPS_INDEX_MOVE` (`tinytuya/CoverDevice.py:236,251,266`); API.md also omits the newer `continue_cover()` and `set_cover_type()` methods.
- Legacy method `set_decore()` (older tinytuya API) does not exist at this pin; its role is covered by the deprecated `set_white()` / current `set_white_percentage()` — no doc at this pin references `set_decore`.
- `CoverDevice.DPS_INDEX_BL = "101"` (backlight) is declared (`tinytuya/CoverDevice.py:80`) and mapped in `DPS_2_STATE` but never used by any method in the class; intended behavior unverified.
- The Contrib "preferred" example `from tinytuya.Contrib import ThermostatDevice` then calling `ThermostatDevice(...)` directly (Contrib/README.md:17-19) only resolves to the class because the deprecated `tinytuya/Contrib/__init__.py` shadows the submodule attribute; unregistered new modules resolve to the module and require `Module.Module(...)` per `tinytuya/Contrib/__init__.py:2-4`. Not executed here (runtime import test not run); behavior inferred from import mechanics.
- DP numbers were cross-checked between docs and code and agree (bulb A/B/C DPSETs vs API.md type table; dimmer DPS 3 vs API.md; cover DPS 1/101/4 notes vs constants) except the signature drift noted above; `DP_Mapping.md` content is a cloud-console procedure with no code anchor at this pin.
- Release notes attribute the v1.20.0 "BulbDevice rgb8 hue offset fixed" to commit `27aa6986`; the current code state is consistent with a fix, but the pre-fix code (blobless clone) could not be diffed to confirm what changed.

## Scenario-ification notes
- All 17 requirements received at least one doc-grounded scenario; none kept property-style.
- Requirement clauses left out of scenarios (not in Tier A/B/C text, code-only or inferred): `set_colour`/`set_hsv` ERR_FUNCTION-on-missing-capability and cached delta-send (REQ "Colour set semantics switch mode and power"); raw-setter DEPRECATED markers and off-below-value_min (REQ "Percentage setters as primary API, raw setters deprecated"); dimmer clamp 25/255 bounds (REQ "Outlet dimmer control with percentage and raw value"); silent no-op for unsupported cover actions and DPS_INDEX_MOVE None-default (REQ "Cover action dispatch with default switch and silent no-op"); ValueError range checks and length-based hexformat auto-detection (REQ "Tuya colour hex encodings rgb8 and hsv16"); `set_cover_type` ValueError outside 1-8 (REQ "One-shot cover type detection with priority and safe default"); both-DP-1-and-20 → 'None' classification detail (REQ "Bulb type auto-detection from DPS key sets" — only the 'None' outcome value is documented, not the trigger pair).
- FLAG (no fix): [relnote v1.10.1] "Removed bulb attribute conditional blocking in BulbDevice set_colour(), set_hsv() and set_colourtemp()... Conditional provides debug warning message instead" contradicts the pass-1 requirement "Colour set semantics switch mode and power", whose ERR_FUNCTION capability check was reintroduced by the v1.17.0 rewrite the requirement itself cites.
- FLAG (no fix): REQ "Contrib import pattern with deprecated __init__ registry" says the registry is "retained only for backward compatibility" — the phrase "backward compatibility" appears in `testcontrib.py` docstring and `tinytuya/Contrib/__init__.py` comments, not in any Tier A/B document, so the scenario for this requirement cites only the deprecation and preferred-pattern bullets.
