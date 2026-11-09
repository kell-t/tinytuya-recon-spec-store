# Capability: cli-wizard-tools

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06).

## Purpose

This capability is the user-facing tooling around the TinyTuya library: an argparse command-line interface entered via `python -m tinytuya` (or the `tinytuya` console script) implemented in `tinytuya/__main__.py` with helpers in `tinytuya/cli.py`; the interactive `wizard` setup flow in `tinytuya/wizard.py` that harvests Tuya Cloud credentials and device local keys; the always-on `server/` API server (HTTP + UDP discovery threads, optional MQTT gateway); and standalone developer helpers in `tools/`. Configuration file names (`tinytuya.json`, `devices.json`, `snapshot.json`, `tuya-raw.json`) are shared constants defined in `tinytuya/core/const.py`.

## Primary code locations
- `tinytuya/__main__.py` — argparse parser, subcommand registry, dispatch, built-in `help` text.
- `tinytuya/cli.py` — `list` command, device-resolution logic, device control commands, CLI monitor loop.
- `tinytuya/wizard.py` — interactive Setup Wizard (credentials, cloud device fetch, file saving, poll).
- `tinytuya/core/const.py` — `SCANTIME`, `CONFIGFILE`, `DEVICEFILE`, `RAWFILE`, `SNAPSHOTFILE` defaults.
- `setup.py` — packaging metadata; the `console_scripts` entry point for the `tinytuya` command.
- `server/server.py` — API server: UDP discovery listeners + threaded HTTP API on port 8888.
- `server/mqtt/mqtt_gateway.py` — optional MQTT bridge polling the API server.
- `tools/pcap_parse.py` — offline PCAP decrypt/analysis tool (keys from `devices.json`).
- `tools/fake-v35-device.py`, `tools/broadcast-relay.py`, `tools/ttcorefunc.py` — dev/test helpers.
- `README.md` § Command Line / Scan Tool — user-facing CLI documentation.
- `server/README.md` — API endpoint and Docker deployment documentation.
- `tools/README.md` — PCAP parser tool documentation.

## Requirements

### Requirement: Module-entry CLI with adaptive usage banner
The package SHALL run a command-line interface when invoked as `python -m tinytuya`, parsing arguments with `argparse` under a description carrying the library version, and SHALL adapt the usage `prog` name to `python3 -m tinytuya` only when executed as `tinytuya/__main__.py` (so pipx/console-script invocations show the bare `tinytuya` command name).
**Status**: VERIFIED
**Evidence**: [commit f46d8623dafe] — "Rewrite main to use argparse and add additional options"; doc: README.md § Command Line (`python -m tinytuya` / `tinytuya`)
**Anchor**: `tinytuya/__main__.py:30-32`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The package SHALL run a command-line interface when invoked as `python -m tinytuya`, parsing arguments with `argparse` under a description carrying the library version, and SHALL adapt the usage `prog` name to `python3 -m tinytuya` only when executed as `tinytuya/__main__.py` (so pipx/console-script
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Fixed subcommand registry covering setup, discovery, control and info
The CLI SHALL register exactly these subcommands: `wizard`, `scan`, `devices`, `snapshot`, `json`, `list`, `version`, `help` plus the device-control set `on`, `off`, `set`, `get`, `monitor`, each as its own argparse subparser with per-command option matrices (control and `list` commands skip scan-oriented flags such as `-force`, `-no-broadcasts`, `-no-poll`; `json`/`list` skip most common flags).
**Status**: VERIFIED
**Evidence**: [commit 08ac8876f0f2] — "Enhance command line interface with device control and listing commands"; [commit 2a5ebf934067] — "Move CLI into new file and add monitor command"; doc: README.md § Command Line usage block
**Anchor**: `tinytuya/__main__.py:41-65` (registry), `:64-98` (per-command option matrix), `:239-266` (dispatch)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The CLI SHALL register exactly these subcommands: `wizard`, `scan`, `devices`, `snapshot`, `json`, `list`, `version`, `help` plus the device-control set `on`, `off`, `set`, `get`, `monitor`, each as its own argparse subparser with per-command option matrices (control and `list` commands skip scan-or
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Console-script install (pipx) via no-op entry function
The distribution SHALL declare a `tinytuya` console script bound to `tinytuya.__main__:dummy` — the CLI executes at module import time (argparse parsing and dispatch are top-level statements), so the packaged entry point only needs a callable no-op `dummy()` to satisfy setuptools; `pyproject.toml` carries only the build-system table, all install metadata lives in `setup.py`.
**Status**: VERIFIED
**Evidence**: [commit 71789638886b] — "Add pipx/entry_points support for CLI"; doc: README.md line 39-40 (`# Optional: Install Command Line Tool` / `pipx install tinytuya`)
**Anchor**: `setup.py:50`; `tinytuya/__main__.py:198` (top-level parse), `:268-270` (`dummy` with explanatory comment); `pyproject.toml:1-2`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The distribution SHALL declare a `tinytuya` console script bound to `tinytuya.__main__:dummy` — the CLI executes at module import time (argparse parsing and dispatch are top-level statements), so the packaged entry point only needs a callable no-op `dummy()` to satisfy setuptools;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Wizard CLI surface for credentials, files and dry-run
The `wizard` subcommand SHALL expose a "Cloud API Credentials" option group (`-credentials-file`, `-key`, `-secret`, `-region` restricted to the seven choices `cn, eu, eu-w, in, sg, us, us-e`, repeatable `-device DEVICE_ID`), a `-dry-run` flag, and `-raw-response-file` in addition to the shared `-device-file`/`-snapshot-file` overrides, and SHALL pass them into the wizard function.
**Status**: VERIFIED
**Evidence**: doc: README.md § Command Line "Wizard" usage block (mirrors the flag set one-for-one, including `-region {cn,eu,eu-w,in,sg,us,us-e}` and `-dry-run`); [PR #625](https://github.com/jasonacox/tinytuya/pull/625) — added Singapore datacenter region
**Anchor**: `tinytuya/__main__.py:82-85` (wizard file options), `:101-108` (credential group + dry-run), `:247-253` (dispatch into `wizard.wizard()`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The `wizard` subcommand SHALL expose a "Cloud API Credentials" option group (`-credentials-file`, `-key`, `-secret`, `-region` restricted to the seven choices `cn, eu, eu-w, in, sg, us, us-e`, repeatable `-device DEVICE_ID`), a `-dry-run` flag, and `-raw-response-file` in addition to the shared `-de
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Wizard credential load-or-prompt with persistence
The Setup Wizard SHALL load Cloud API credentials (`apiKey`, `apiSecret`, `apiRegion`, `apiDeviceID`) from the config file (default `tinytuya.json`), display and offer to reuse existing settings unless `-yes`, prompt interactively for any missing values (including a printed region list) and write the resulting config back to the credentials file immediately.
**Status**: VERIFIED
**Evidence**: doc: `tinytuya/wizard.py:10-13` module docstring ("prompt the user for Tuya IoT Developer credentials … save the credentials and the device data in the tinytuya.json and devices.json configuration files"); [commit 28ada7b9fa4a] — "Fix newline in Wizard region list"
**Anchor**: `tinytuya/wizard.py:84-106` (load), `:129-141` (reuse prompt), `:143-169` (prompt + save, region list at `:154-161`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The Setup Wizard SHALL load Cloud API credentials (`apiKey`, `apiSecret`, `apiRegion`, `apiDeviceID`) from the config file (default `tinytuya.json`), display and offer to reuse existing settings unless `-yes`, prompt interactively for any missing values (including a printed region list) and write th
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Wizard device harvest via Cloud with scan shortcut, dry-run, linking and dual file output
Unless `--dry-run` (`nocloud`) reuses the existing `devices.json` list, the wizard SHALL accept `apiDeviceID` set to the literal `scan` by auto-discovering one Device ID via a one-device network scan; call `Cloud.getdevices()`, optionally downloading DP name mappings; infer sub-device parents via `gateway_id` or shared local key; print the device listing; and save the normalized list to `devices.json` plus the full raw cloud response to `tuya-raw.json`.
**Status**: VERIFIED
**Evidence**: doc: README.md line 115 (wizard creates `devices.json` and `tuya-raw.json`); [commit 14e6b7a3f307] — "Add IoT core service renewal info to the setup wizard in the README"; [commit 2a95d00f8f61] — "improve error messaging in scanner and wizard"
**Anchor**: `tinytuya/wizard.py:171-184` (dry-run/scan shortcut), `:186-215` (cloud fetch + renewal hint at `:192-194` and `:211-213`), `:217-254` (parent linking), `:256-265` (save devices.json), `:267-281` (raw file)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Unless `--dry-run` (`nocloud`) reuses the existing `devices.json` list, the wizard SHALL accept `apiDeviceID` set to the literal `scan` by auto-discovering one Device ID via a one-device network scan;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Wizard optional poll with IP/version write-back
After saving the device list, the wizard SHALL ask (or honor `-yes`/`-no-poll`) whether to poll local devices; on poll it SHALL run the scanner's `poll_and_display()` with snapshot output, then merge discovered `ip` and `version` per gwId back into the device list and rewrite `devices.json` reporting how many addresses were found.
**Status**: VERIFIED
**Evidence**: doc: `tinytuya/wizard.py:12-13` ("The Wizard will then optionally scan the local devices for status"); doc: README.md § Scan Tool (`python -m tinytuya snapshot` consumes the wizard/scan snapshot)
**Anchor**: `tinytuya/wizard.py:283-313` (poll prompt at `:284-289`, write-back at `:301-313`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** After saving the device list, the wizard SHALL ask (or honor `-yes`/`-no-poll`) whether to poll local devices;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: list command renders device table or JSON
The `list` subcommand SHALL load devices from the device file (default `devices.json`), normalize rows to `name/id/key/ip/version` preferring `last_ip` over `ip`, print an aligned ASCII table by default or a JSON array under `--json`, and exit non-zero with a distinct message when the file is missing versus when it contains no valid devices.
**Status**: VERIFIED
**Evidence**: [commit 3cea89363d21] — "enhance device file loading, and improve error handling in CLI"; doc: README.md § Command Line "List" block (`--json  Output as a JSON array instead of a table`)
**Anchor**: `tinytuya/cli.py:29-73` (last_ip preference at `:51`, error split at `:34-38`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The `list` subcommand SHALL load devices from the device file (default `devices.json`), normalize rows to `name/id/key/ip/version` preferring `last_ip` over `ip`, print an aligned ASCII table by default or a JSON array under `--json`, and exit non-zero with a distinct message when the file is missin
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Control-target resolution by ID or name with device-file lookup
Device-control commands SHALL require exactly one of `--id`/`--name` (mutually exclusive argparse group), resolve `--name` case-insensitively against the device file (erroring if not found), and fill missing `--key`, `--ip` and `--version` from the matched device record — including a warning and fallback for a non-numeric `version` value.
**Status**: VERIFIED
**Evidence**: doc: README.md § Command Line "Device Control Options" (`--key, --ip, and --version are loaded automatically from devices.json if found`); [commit 49dfafe96ba4] — "fix: correct argument description in CLI"
**Anchor**: `tinytuya/__main__.py:115-121` (mutually-exclusive group); `tinytuya/cli.py:76-131` (name match at `:89-98`, lookup at `:101-131`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Device-control commands SHALL require exactly one of `--id`/`--name` (mutually exclusive argparse group), resolve `--name` case-insensitively against the device file (erroring if not found), and fill missing `--key`, `--ip` and `--version` from the matched device record — including a warning and fal
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Hidden local-key prompt and strict 16-character validation with shell-escape guidance
When no local key is supplied or found, the CLI SHALL prompt via `getpass` (input hidden) only when stdin is a TTY — exiting with a clear error in piped/CI contexts — and SHALL strip whitespace then reject any key whose length is not exactly 16 characters, printing platform-specific shell-quoting tips (single quotes on Linux/Mac, `^` escapes on Windows CMD, or omitting `--key` to use the prompt).
**Status**: VERIFIED
**Evidence**: [commit 754cc1c007cd] — "Enhance CLI key handling: prompt for missing keys and validate key length"; [commit 3f1ed917ace9] — "CLI: harden device key prompt and validation"; doc: README.md § Device Control Options (`If --key is omitted … input is hidden … Tuya local keys are always exactly 16 characters`)
**Anchor**: `tinytuya/cli.py:139-164` (getpass + TTY guard at `:147-155`), `:166-181` (length check + tips)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** When no local key is supplied or found, the CLI SHALL prompt via `getpass` (input hidden) only when stdin is a TTY — exiting with a clear error in piped/CI contexts — and SHALL strip whitespace then reject any key whose length is not exactly 16 characters, printing platform-specific shell-quoting ti
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Auto-discovery of IP and protocol version with 3.3 fallback
If the device IP is unknown (absent or `--ip auto`) or the protocol version is unresolved, the CLI SHALL run an inline targeted network scan (honoring `-maxtime`, `-force`, `-no-broadcasts`, debug flags) restricted to the target device ID, adopt the scanned `ip`/`version`, and default the protocol version to 3.3 when the scan cannot find the device.
**Status**: VERIFIED
**Evidence**: [commit 8105e6b636b2] — "Make sure CLI defaults to v3.3 if not found"; [commit 97f2347c7928] — "Updated help text for --ip"; doc: README.md § On/Off (`--ip … auto-discovered if omitted or set to "Auto"`, `--version … defaults to 3.3`)
**Anchor**: `tinytuya/cli.py:183-195` (scanner call at `:185-188`, fallback at `:193-195`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** If the device IP is unknown (absent or `--ip auto`) or the protocol version is unresolved, the CLI SHALL run an inline targeted network scan (honoring `-maxtime`, `-force`, `-no-broadcasts`, debug flags) restricted to the target device ID, adopt the scanned `ip`/`version`, and default the protocol v
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Control command execution and output contract
`on`/`off` SHALL call `turn_on()/turn_off()` on the resolved switch DPS (default 1); `set` SHALL require `--dps` and `--value`, parsing `--value` as JSON first and falling back to a plain string; `get` SHALL print the full status JSON without `--dps`, or the bare DPS value with `--dps`; any result containing `Err` SHALL print `Error <code>: <msg>` and exit non-zero, otherwise the JSON result (or `OK`) is printed.
**Status**: VERIFIED
**Evidence**: [commit e9a23af8c916] — "Enhance device command handling by improving value parsing and error handling"; doc: README.md § Set/Get (`parsed as JSON if possible … otherwise sent as a plain string`, `--dps N → plain scalar value only`)
**Anchor**: `tinytuya/__main__.py:123-129` (per-command DPS flags); `tinytuya/cli.py:209-255` (JSON parse at `:221-224`, get branches at `:226-242`, error/OK contract at `:248-255`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `on`/`off` SHALL call `turn_on()/turn_off()` on the resolved switch DPS (default 1);
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: CLI monitor with persistent socket, 30 s status and 12 s heartbeat cadence
The `monitor` subcommand SHALL connect with a persistent socket, print the initial status, then loop: full `status()` poll every 30 s, `heartbeat()` every 12 s when idle, otherwise non-blocking `receive()` for asynchronous updates, printing every received payload, sleeping 5 s after an error response to throttle retries, and exiting cleanly on Ctrl-C.
**Status**: VERIFIED
**Evidence**: [commit cec1830af19a] — "Use persistent sockets for CLI monitor"; [commit 2a5ebf934067] — monitor command introduction; doc: README.md § Monitor (`sends a heartbeat every 12 seconds, and polls for a full status refresh every 30 seconds. Press Ctrl-C to exit`)
**Anchor**: `tinytuya/cli.py:258-300` (timers at `:265-266`, loop at `:276-298`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The `monitor` subcommand SHALL connect with a persistent socket, print the initial status, then loop: full `status()` poll every 30 s, `heartbeat()` every 12 s when idle, otherwise non-blocking `receive()` for asynchronous updates, printing every received payload, sleeping 5 s after an error respons
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: API server: UDP discovery threads plus threaded HTTP control API with env configuration
The bundled server SHALL run one thread per Tuya UDP discovery port (6666/6667/7000) decrypting broadcasts into a device database, and a `ThreadingHTTPServer` GET API on port 8888 (env `APIPORT`) with routes for device listing, status, set, turnon/turnoff, delayed off, cloud sync/config and offline listing; behavior SHALL be configurable via environment (`DEBUGMODE=yes`, `HOST`) or a leading `-d` argument, and the process SHALL exit on SIGTERM.
**Status**: VERIFIED
**Evidence**: doc: server/README.md (endpoint table, Docker `-e DEBUGMODE`/`-e HOST`, port 8888); [commit e59d6bfb95f6] — "Add option to specify host for server"; [commit 518328ba7b21] — server build version bump to p16
**Anchor**: `server/server.py:78` (APIPORT), `:92-93` (DEBUGMODE/HOST), `:97-103` (HOST broadcast math), `:112-114` (`-d` flag), `:128` (SIGTERM), `:673-678` (HTTP server), `:691-694` (threads)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The bundled server SHALL run one thread per Tuya UDP discovery port (6666/6667/7000) decrypting broadcasts into a device database, and a `ThreadingHTTPServer` GET API on port 8888 (env `APIPORT`) with routes for device listing, status, set, turnon/turnoff, delayed off, cloud sync/config and offline 
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Optional MQTT gateway bridging server device output to a broker
The MQTT gateway SHALL bridge the server's `/devices` HTTP output to an MQTT broker per `mqtt.json` (topic/broker/port/pollingtime) when that config is present, SHALL apply built-in defaults when the config is unreadable, and SHALL remain inactive otherwise.
**Status**: VERIFIED
**Evidence**: [commit 93834cdfaa04] — "MQTT Gateway for Server"
**Anchor**: `server/mqtt/mqtt_gateway.py:83-99` (readconfig with defaults)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The MQTT gateway SHALL bridge the server's `/devices` HTTP output to an MQTT broker per `mqtt.json` (topic/broker/port/pollingtime) when that config is present, SHALL apply built-in defaults when the config is unreadable, and SHALL remain inactive otherwise.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Offline PCAP decrypt tool keyed by devices.json
The `tools/pcap_parse.py` utility SHALL read tcpdump PCAP files (via the optional `dpkt` module, with an install hint and hard failure when missing), decrypt Tuya traffic using local keys loaded from a `devices.json` (explicit `-d FILE`, else auto-probing `devices.json` and `../devices.json`), and offer `-z/--hide-zero-len` (suppress 0-length heartbeats) and `-s/--sortable` (device-ID-sortable output) flags.
**Status**: VERIFIED
**Evidence**: doc: tools/README.md § Packet Capture Parser (usage block matches all flags); [commit 736b980df8d8] — related tooling work on the fake v3.5 device
**Anchor**: `tools/pcap_parse.py:16-23` (dpkt guard), `:403-409` (argparse flags), `:417-427` (devices.json auto-probe)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The `tools/pcap_parse.py` utility SHALL read tcpdump PCAP files (via the optional `dpkt` module, with an install hint and hard failure when missing), decrypt Tuya traffic using local keys loaded from a `devices.json` (explicit `-d FILE`, else auto-probing `devices.json` and `../devices.json`), and o
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

## Known gaps / open questions
- DOC/CODE DRIFT — server/README.md documents the delayed-off route as `/delayedoff/{DeviceID}|{DeviceName}/{SwitchNo}/{Seconds}`, but the code implements `/delayoff/` (`server/server.py:532-533`, docstring `server/server.py:31`, built-in `/help` route listing `server/server.py:434`). Calling `/delayedoff/...` as documented would 404.
- DOC/CODE DRIFT — server/README.md documents `/set/{DeviceID}|{DeviceName}/{Key}/{Value}`, while the server docstring advertises the extended `/set/.../{Key}|{Code}/{Value}` form (DPS code lookup); the README omits the `{Code}` variant (`server/server.py:21-22`).
- DOC/CODE DRIFT — the CLI's built-in `help` text states `--dps N  DPS index for on/off/set/get (default: 1)` (`tinytuya/__main__.py:190`), but per the parser `set` requires `--dps` with no default (`tinytuya/__main__.py:128`) and `get` defaults it to `None` meaning "full status" (`tinytuya/__main__.py:126`). The README's per-command blocks are correct; the summary line is stale.
- DOC/CODE DRIFT — README's generic usage line `tinytuya <command> [-debug] [-nocolor] [-h] [-yes] [-no-poll] [-device-file FILE] [-snapshot-file FILE]` implies a uniform option set; the parser grants options per subcommand — `json` and `list` get almost none, control commands get no `-force`/`-no-broadcasts`/`-no-poll`, and `snapshot` gets no positional `max_time` (`tinytuya/__main__.py:68-98`).
- UNDOCUMENTED TOOLS — `tools/README.md` (49 lines) documents only the PCAP parser; `tools/broadcast-relay.py` (listens for device broadcasts and re-sends them via unicast for broadcast-blocking WiFi, `-h` for options) and `tools/fake-v35-device.py` (simulates a v3.5 device, e.g. replying `json obj data unvalid` to unknown commands, `tools/fake-v35-device.py:112`) appear in no bundle doc — behavior is grounded only in code and commit subjects.
- DUPLICATION RISK — `tools/ttcorefunc.py:1` declares itself a "Copy of TinyTuya core Module" (a self-contained re-implementation importing PyCryptodome directly, used by `tools/fake-v35-device.py:2` as `import ttcorefunc as tinytuya`); no doc or mechanism keeps it in sync with `tinytuya/core/` at this pin.
- UNDOCUMENTED FEATURE — shell tab-completion support: `tinytuya/__main__.py:3` carries the `PYTHON_ARGCOMPLETE_OK` marker and `:21-25`/`:131-132` wire optional `argcomplete` when installed; no README section mentions it. Likewise `server/mqtt/mqtt_gateway.py` needs `paho-mqtt`, which is absent from `setup.py` `install_requires` (`setup.py:15-19`) — install is manual per the module's own imports.
- README § Command Line shows the `version` command output "e.g.:  TinyTuya version: 1.19.0" while this pin reports 1.20.0 (`tinytuya/core/core.py:104-105`); trivial doc staleness.
- Console-script contract quirk: `tinytuya=tinytuya.__main__:dummy` means the installed `tinytuya` command does real work purely as an import side effect and `dummy()` itself no-ops (`tinytuya/__main__.py:268-270`); any tool that imports `tinytuya.__main__` for another reason would trigger a full argparse run. Intentional per the in-code comment; flagged as a design smell, not a gap.
- The bundle's 162 commit-subject hits were mined from full history; subjects were treated as intent only. All behavior above was re-grounded in pin code; no PR/issue numbers are cited except externally verified ones (#625 in the allowlist).
