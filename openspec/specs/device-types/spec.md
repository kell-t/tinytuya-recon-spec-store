# Capability: device-types

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06).

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


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The library SHALL expose `OutletDevice`, `BulbDevice` and `CoverDevice` as subclasses of the core `Device` class, exported from the top-level `tinytuya` package, so every built-in type inherits the shared constructor signature and Device commands (set_status, turn_on, set_value, status, etc.).
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Outlet dimmer control with percentage and raw value
`OutletDevice.set_dimmer()` SHALL accept either a percentage (0–100, scaled to raw 0–255) or a raw `value`, default the dimmer to DPS index 3, clamp non-zero levels to a minimum of 25 and maximum of 255, and delegate to inherited `turn_on()` + `set_value()` — while a level of 0 SHALL turn the device off via `turn_off()` instead of writing a value.
**Status**: VERIFIED
**Evidence**: doc: API.md § OutletDevice (`d.set_dimmer(0) # turns device off via turn_off()`); OutletDevice is otherwise a pure Device subclass ("adds dimmer support")
**Anchor**: `tinytuya/OutletDevice.py:55-78` (scale at :66, off at :70-71, clamp at :73-76)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `OutletDevice.set_dimmer()` SHALL accept either a percentage (0–100, scaled to raw 0–255) or a raw `value`, default the dimmer to DPS index 3, clamp non-zero levels to a minimum of 25 and maximum of 255, and delegate to inherited `turn_on()` + `set_value()` — while a level of 0 SHALL turn the device
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Bulb type auto-detection from DPS key sets
`BulbDevice.detect_bulb()` SHALL classify a device as Type A, B, C or 'None' from the DPS indexes present in a status response: DP 20+21 → Type B; DP 1+2 with DP 2 a string → Type A (mode) else Type C (brightness); both DP 1 and DP 20 present → type 'None' (probably not a bulb). Types A/B/C map to the Tuya product-function DP layout per the cited Tuya developer doc.
**Status**: VERIFIED
**Evidence**: [PR #617](https://github.com/jasonacox/tinytuya/pull/617) — BulbDevice rewrite (v1.17.0) introducing DPSET-based detection; doc: API.md § BulbDevice type table (A/B/C, switch DPS 1/20/1)
**Anchor**: `tinytuya/BulbDevice.py:840-891` (rules at :880-891, Tuya doc ref at :878)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `BulbDevice.detect_bulb()` SHALL classify a device as Type A, B, C or 'None' from the DPS indexes present in a status response: DP 20+21 → Type B;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Per-type default DP sets with value ranges and hex format
Each bulb type SHALL carry a `DEFAULT_DPSET` entry mapping features (switch, mode, brightness, colourtemp, colour, scene, scene_data, timer, music) to DPS indexes plus `value_min`/`value_max` and `value_hexformat`: A = DP 1–8, 25–255, `rgb8`; B = DP 20–28, 10–1000, `hsv16`; C = DP 1–3, 25–255, `rgb8`; 'None' = DP 1 only, 0–255, `rgb8`.
**Status**: VERIFIED
**Evidence**: doc: API.md § BulbDevice table (A brightness 25–255, B 10–1000); commit `ff3a5000` "Rewrite BulbDevice"
**Anchor**: `tinytuya/BulbDevice.py:80-136`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Each bulb type SHALL carry a `DEFAULT_DPSET` entry mapping features (switch, mode, brightness, colourtemp, colour, scene, scene_data, timer, music) to DPS indexes plus `value_min`/`value_max` and `value_hexformat`: A = DP 1–8, 25–255, `rgb8`;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Lazy bulb configuration with explicit failure
`BulbDevice` SHALL defer configuration until first contact (constructor forces `version=None` to avoid an immediate status call; `status()` triggers `detect_bulb()` on first DPS payload), and percentage getters/setters SHALL call `detect_bulb()` before reading `value_max` and raise `RuntimeError` if the bulb still is not configured.
**Status**: VERIFIED
**Evidence**: [PR #714](https://github.com/jasonacox/tinytuya/pull/714) — `set_brightness_percentage()`/`set_colourtemp_percentage()` now call `detect_bulb()` before reading `value_max`, preventing `AttributeError` (v1.19.0); regression test `test_percentage_raises_when_unconfigured`
**Anchor**: `tinytuya/BulbDevice.py:174-184`, `:596-599`, `:664-667`, `:716-719`, `:768-769`; test: `tests.py:281`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `BulbDevice` SHALL defer configuration until first contact (constructor forces `version=None` to avoid an immediate status call;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Manual bulb type and DP-capability override
`BulbDevice` SHALL let users override auto-detection via `set_bulb_type(bulb_type, mapping)` / `set_bulb_capabilities(mapping)`, which fill each dpset key from the user mapping first, then the type default, and mark the bulb configured once switch and brightness DPs are known.
**Status**: VERIFIED
**Evidence**: commit `e94b972f` "Fix BulbDevice set_bulb_type()"; doc: `examples/bulb.py:45,62` (`#d.set_bulb_type('B')`, `d.set_bulb_capabilities(mapping)`)
**Anchor**: `tinytuya/BulbDevice.py:921-942`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `BulbDevice` SHALL let users override auto-detection via `set_bulb_type(bulb_type, mapping)` / `set_bulb_capabilities(mapping)`, which fill each dpset key from the user mapping first, then the type default, and mark the bulb configured once switch and brightness DPs are known.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Tuya colour hex encodings rgb8 and hsv16
The bulb colour model SHALL provide static converters between RGB/HSV and the two Tuya hex encodings: `rgb8` = `rrggbbhhhhssvv` (h scaled 0–360, s/v 0–255) and `hsv16` = `hhhhssssvvvv` (h 0–360, s/v 0–1000), with input-range validation (`ValueError` outside 0–255 for RGB, 0–1.0 for HSV) and length-based auto-detection (6/14 hex digits → rgb8, 12 → hsv16) when `hexformat=None`.
**Status**: VERIFIED
**Evidence**: commit `27aa6986` "fix: correct 16 verified bugs across Cloud, core, Bulb…" (RELEASE.md v1.20.0: "BulbDevice rgb8 hue offset fixed"); round-trip unit test `test_rgb8_round_trip`
**Anchor**: `tinytuya/BulbDevice.py:186-228` (rgb_to_hexvalue), `:243-275` (hsv_to_hexvalue), `:277-320` (hexvalue_to_rgb), `:334-379` (hexvalue_to_hsv); test: `tests.py:481-486`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The bulb colour model SHALL provide static converters between RGB/HSV and the two Tuya hex encodings: `rgb8` = `rrggbbhhhhssvv` (h scaled 0–360, s/v 0–255) and `hsv16` = `hhhhssssvvvv` (h 0–360, s/v 0–1000), with input-range validation (`ValueError` outside 0–255 for RGB, 0–1.0 for HSV) and length-b
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Colour set semantics switch mode and power
`set_colour(r,g,b)` and `set_hsv(h,s,v)` SHALL encode the colour in the detected bulb's `value_hexformat` and send it together with `mode='colour'` and `switch=True`, skipping any DP that already holds the target value when a cached status exists (delta-send via `_set_values_check()`), and SHALL return an `ERR_FUNCTION` error JSON if the device lacks the colour capability.
**Status**: VERIFIED
**Evidence**: [PR #617](https://github.com/jasonacox/tinytuya/pull/617) — rewrite reworked `set_multiple_values()`/delta sending; unit tests `test_set_colour_A` / `test_set_colour_B`
**Anchor**: `tinytuya/BulbDevice.py:536-575` (set_colour/set_hsv), `:393-418` (`_set_values_check`); tests: `tests.py:138,159`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `set_colour(r,g,b)` and `set_hsv(h,s,v)` SHALL encode the colour in the detected bulb's `value_hexformat` and send it together with `mode='colour'` and `switch=True`, skipping any DP that already holds the target value when a cached status exists (delta-send via `_set_values_check()`), and SHALL ret
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Percentage setters as primary API, raw setters deprecated
The primary white/brightness/colour-temperature API SHALL be the percentage-based `set_white_percentage()`, `set_brightness_percentage()` and `set_colourtemp_percentage()` (0–100, scaled by the bulb's `value_max`); the raw-value `set_white()`, `set_brightness()` and `set_colourtemp()` SHALL be marked deprecated, and `set_brightness()` SHALL adapt to the current mode — white-mode bulbs via `set_white()`, colour-mode bulbs by rescaling HSV value — and turn the bulb off below `value_min`.
**Status**: VERIFIED
**Evidence**: doc: BulbDevice.py DEPRECATED docstrings at `:606-607`, `:671-672`, `:723-724`; API.md § set_white_percentage/set_brightness_percentage; unit tests `test_set_white_A/B`, `test_set_brightness_C`
**Anchor**: `tinytuya/BulbDevice.py:577-604`, `:654-704` (mode-aware at :691-704), `:706-744`; tests: `tests.py:180,201,220`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The primary white/brightness/colour-temperature API SHALL be the percentage-based `set_white_percentage()`, `set_brightness_percentage()` and `set_colourtemp_percentage()` (0–100, scaled by the bulb's `value_max`);
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: BulbDevice usable on non-bulb devices
`BulbDevice` SHALL remain functional as a generic device wrapper: `turn_onoff()` defaults the switch to DPS 1 when no bulb switch DP was detected, and detection classifies devices reporting both DP 1 and DP 20 as type 'None' rather than failing.
**Status**: VERIFIED
**Evidence**: [PR #620](https://github.com/jasonacox/tinytuya/pull/620) — "Fix BulbDevice for non-bulb devices… allow BulbDevice to be used even for non-bulb devices, e.g. turn_on() & turn_off()" (v1.17.1); [PR #625](https://github.com/jasonacox/tinytuya/pull/625) — "Update BulbDevice for non-bulb devices again" (v1.17.2); test `test_not_a_bulb`
**Anchor**: `tinytuya/BulbDevice.py:420-436`, `:880-883`; test: `tests.py:260`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `BulbDevice` SHALL remain functional as a generic device wrapper: `turn_onoff()` defaults the switch to DPS 1 when no bulb switch DP was detected, and detection classifies devices reporting both DP 1 and DP 20 as type 'None' rather than failing.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Music-mode frame composition
`set_music_colour()` SHALL compose a music-DP frame of transition nibble + colour hex in the bulb's `value_hexformat` + brightness and colourtemp scaled into `value_max` with a width matching the format (`%02x` for rgb8, `%04x` for hsv16) and write it to the music DP, returning `ERR_FUNCTION` when the device has no music capability; the bulb is put into music mode by the inherited mode setter (`set_mode('music')`).
**Status**: VERIFIED
**Evidence**: doc: API.md § set_music_colour, `MUSIC_TRANSITION_JUMP`/`MUSIC_TRANSITION_FADE` examples; example `examples/bulb-music.py:45,65,69` uses `set_mode('music')` then `set_music_colour()`
**Anchor**: `tinytuya/BulbDevice.py:77-78` (transition constants), `:504-534`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `set_music_colour()` SHALL compose a music-DP frame of transition nibble + colour hex in the bulb's `value_hexformat` + brightness and colourtemp scaled into `value_max` with a width matching the format (`%02x` for rgb8, `%04x` for hsv16) and write it to the music DP, returning `ERR_FUNCTION` when t
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: CoverDevice eight command-type lexicons
`CoverDevice` SHALL support exactly 8 open/close/stop/continue command vocabularies (COVER_TYPES 1–8: `open/close/stop/continue`; `true/false`; `'0'/'1'/'2'`; `'00'/'01'/'02'/'03'`; `fopen/fclose`; `on/off/stop`; `up/down/stop`; `ZZ/FZ/STOP`) and expose `open_cover()`, `close_cover()`, `stop_cover()` and `continue_cover()` which translate the action into the active type's command value.
**Status**: VERIFIED
**Evidence**: RELEASE.md v1.17.5 "CoverDevice: Major rewrite to support 8 different device command types with automatic detection"; issue #653 credit @make-all; commits `70810f61`, `8b7daecb`, `ef895fb4` ("#653")
**Anchor**: `tinytuya/CoverDevice.py:89-146` (table), `:236-300` (four action methods)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `CoverDevice` SHALL support exactly 8 open/close/stop/continue command vocabularies (COVER_TYPES 1–8: `open/close/stop/continue`;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: One-shot cover type detection with priority and safe default
`CoverDevice` SHALL auto-detect the command type once, on the first command, by matching the cover DPS value from a `status()` read against each type's `detect_values` using priority order 1→8→3→4→5→7→2→6, defaulting to Type 1 when no value matches or the status call fails, and `set_cover_type(type_id)` SHALL allow manual override with `ValueError` for ids outside 1–8.
**Status**: VERIFIED
**Evidence**: RELEASE.md v1.17.5 ("automatically detected on first command using priority ordering… Defaults to Type 1 if detection fails"); doc: `tinytuya/CoverDevice.py:22-36` header notes citing issue #653
**Anchor**: `tinytuya/CoverDevice.py:153-195` (priority at :184, default at :168-169), `:197-215`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `CoverDevice` SHALL auto-detect the command type once, on the first command, by matching the cover DPS value from a `status()` read against each type's `detect_values` using priority order 1→8→3→4→5→7→2→6, defaulting to Type 1 when no value matches or the status call fails, and `set_cover_type(type_
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Cover action dispatch with default switch and silent no-op
Cover action methods SHALL default the target DPS to `DPS_INDEX_MOVE` ("1") when `switch` is None, and SHALL silently do nothing (no error) when the detected type does not support the action — stop is unsupported for Types 2 and 5, continue only for Types 1 and 4.
**Status**: VERIFIED
**Evidence**: RELEASE.md v1.17.5 "Added `continue_cover()` method for device types that support it (Types 1 and 4)"; commit `732a3040` "Refactor CoverDevice methods to use DPS_INDEX_MOVE as default switch value"
**Anchor**: `tinytuya/CoverDevice.py:79` (DPS_INDEX_MOVE), `:244-249` (default + None-guard pattern), `:274-275`, `:292-293` (support notes)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Cover action methods SHALL default the target DPS to `DPS_INDEX_MOVE` ("1") when `switch` is None, and SHALL silently do nothing (no error) when the detected type does not support the action — stop is unsupported for Types 2 and 5, continue only for Types 1 and 4.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Contrib subclass contract and naming convention
A community device module SHALL be a single file `tinytuya/Contrib/<Name>Device.py` defining a class of the same name that subclasses `core.Device` (imported as `from ..core import Device, …`), passes `*args/**kwargs` through to `super().__init__()`, and may override constructor defaults (e.g. force `version=3.3` and `persist=True`) or declare class-level DPS constants for its own protocol.
**Status**: VERIFIED
**Evidence**: doc: `tinytuya/Contrib/README.md:275-278` "Follow the template example in ThermostatDevice.py to add your device"; [PR #711](https://github.com/jasonacox/tinytuya/pull/711) — new FloorFanDevice contributed this way (v1.19.0)
**Anchor**: `tinytuya/Contrib/ThermostatDevice.py:218,220,260-268`; `tinytuya/Contrib/IRRemoteControlDevice.py:119,121,154-158` (DP/NSDP constants at :122-137)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** A community device module SHALL be a single file `tinytuya/Contrib/<Name>Device.py` defining a class of the same name that subclasses `core.Device` (imported as `from ..core import Device, …`), passes `*args/**kwargs` through to `super().__init__()`, and may override constructor defaults (e.g.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Contrib import pattern with deprecated __init__ registry
New Contrib device modules SHALL be consumed via `from tinytuya.Contrib import YourNewModule` and instantiated as `YourNewModule.YourNewModule(...)` without being registered in `tinytuya/Contrib/__init__.py`, which is deprecated and retained only for backward compatibility with the old `from tinytuya import Contrib` style and its `DeviceTypes` listing.
**Status**: VERIFIED
**Evidence**: [PR #466](https://github.com/jasonacox/tinytuya/pull/466) — deprecates `tinytuya/Contrib/__init__.py`; [PR #686](https://github.com/jasonacox/tinytuya/pull/686) — "Revert deprecated Contrib/__init__.py" (v1.18.0); commit `34e6f449` "use preferred import pattern"
**Anchor**: `tinytuya/Contrib/__init__.py:1-15` (deprecation notice, `DeviceTypes` at :15); `testcontrib.py:4-9,17-27`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** New Contrib device modules SHALL be consumed via `from tinytuya.Contrib import YourNewModule` and instantiated as `YourNewModule.YourNewModule(...)` without being registered in `tinytuya/Contrib/__init__.py`, which is deprecated and retained only for backward compatibility with the old `from tinytuy
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: DPS-to-name mapping sourced from cloud devices.json
DPS indexes SHALL be presented to users with human-readable names sourced from the Tuya Cloud download in `devices.json` (since TinyTuya v1.12.8); when that mapping is wrong for a product, the documented remedy is to switch the product's Control Instruction Mode to "DP Instruction" in the Tuya IoT developer console and re-poll.
**Status**: INFERRED
**Evidence**: doc: DP_Mapping.md (whole file — steps 1–6 for enabling DP Instruction mode and rebuilding devices.json)
**Anchor**: anchor not located (cloud-side behavior; devices.json loading is owned by the cloud-api / device-control capabilities)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** DPS indexes SHALL be presented to users with human-readable names sourced from the Tuya Cloud download in `devices.json` (since TinyTuya v1.12.8);
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

## Known gaps / open questions
- DOC/CODE DRIFT — `set_musicmode()` and `unset_musicmode()` are documented in API.md § BulbDevice (lines ~556-562) and listed in the `tinytuya/BulbDevice.py` module docstring (`tinytuya/BulbDevice.py:24-25`), and `set_music_colour()`'s own docstring references `set_musicmode()` (`:514`), but no `def set_musicmode`/`def unset_musicmode` exists anywhere in the package at this pin; the shipped example uses `set_mode('music')` instead (`examples/bulb-music.py:45`).
- DOC/CODE DRIFT — API.md § CoverDevice documents signatures `open_cover(switch=1, nowait=False)` (and same for close/stop), while the code defaults `switch=None` resolved to `DPS_INDEX_MOVE` (`tinytuya/CoverDevice.py:236,251,266`); API.md also omits the newer `continue_cover()` and `set_cover_type()` methods.
- Legacy method `set_decore()` (older tinytuya API) does not exist at this pin; its role is covered by the deprecated `set_white()` / current `set_white_percentage()` — no doc at this pin references `set_decore`.
- `CoverDevice.DPS_INDEX_BL = "101"` (backlight) is declared (`tinytuya/CoverDevice.py:80`) and mapped in `DPS_2_STATE` but never used by any method in the class; intended behavior unverified.
- The Contrib "preferred" example `from tinytuya.Contrib import ThermostatDevice` then calling `ThermostatDevice(...)` directly (Contrib/README.md:17-19) only resolves to the class because the deprecated `tinytuya/Contrib/__init__.py` shadows the submodule attribute; unregistered new modules resolve to the module and require `Module.Module(...)` per `tinytuya/Contrib/__init__.py:2-4`. Not executed here (runtime import test not run); behavior inferred from import mechanics.
- DP numbers were cross-checked between docs and code and agree (bulb A/B/C DPSETs vs API.md type table; dimmer DPS 3 vs API.md; cover DPS 1/101/4 notes vs constants) except the signature drift noted above; `DP_Mapping.md` content is a cloud-console procedure with no code anchor at this pin.
- Release notes attribute the v1.20.0 "BulbDevice rgb8 hue offset fixed" to commit `27aa6986`; the current code state is consistent with a fix, but the pre-fix code (blobless clone) could not be diffed to confirm what changed.
