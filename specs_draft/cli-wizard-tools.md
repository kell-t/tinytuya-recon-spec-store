# Capability: cli-wizard-tools

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06). | Pass 3 (scenario-ification) applied 2026-11-09

## Summary

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
- Status: VERIFIED
- Evidence: [commit f46d8623dafe] — "Rewrite main to use argparse and add additional options"; doc: README.md § Command Line (`python -m tinytuya` / `tinytuya`)
- Anchor: `tinytuya/__main__.py:30-32`

#### Scenario: Bare invocation shows usage page
- **WHEN** `tinytuya` is run by itself with no arguments
- **THEN** it produces a "Usage" page instead of running a scan
- **AND** scanning requires `tinytuya scan` or `python -m tinytuya scan`
- Source: [relnote v1.14.0] "Running tinytuya by itself will now produce a "Usage" page instead of running a scan.  Use tinytuya scan or python -m tinytuya scan."

### Requirement: Fixed subcommand registry covering setup, discovery, control and info
The CLI SHALL register exactly these subcommands: `wizard`, `scan`, `devices`, `snapshot`, `json`, `list`, `version`, `help` plus the device-control set `on`, `off`, `set`, `get`, `monitor`, each as its own argparse subparser with per-command option matrices (control and `list` commands skip scan-oriented flags such as `-force`, `-no-broadcasts`, `-no-poll`; `json`/`list` skip most common flags).
- Status: VERIFIED
- Evidence: [commit 08ac8876f0f2] — "Enhance command line interface with device control and listing commands"; [commit 2a5ebf934067] — "Move CLI into new file and add monitor command"; doc: README.md § Command Line usage block
- Anchor: `tinytuya/__main__.py:41-65` (cmd_list registry), `:64-98` (per-command option matrix), `:239-266` (dispatch)

#### Scenario: Documented subcommand matrix
- **WHEN** the CLI is invoked with one of its documented commands
- **THEN** `wizard` launches the Setup Wizard to get Tuya Local Keys from Tuya Cloud, `scan` scans the local network for Tuya devices, `devices` scans all devices listed in the `devices.json` file and `snapshot` scans devices listed in the `snapshot.json` file
- **AND** the `list` command accepts only `-h`, `-debug`, `--json` and `-device-file FILE`
- Source: doc: README.md § Command Line "wizard Launch Setup Wizard to get Tuya Local Keys from Tuya Cloud. scan Scan local network for Tuya devices. devices Scan all devices listed in devices.json file. snapshot Scan devices listed in snapshot.json file."
- Source: doc: README.md § Command Line "tinytuya list [-h] [-debug] [--json] [-device-file FILE]"

#### Scenario: Info subcommands version and help
- **WHEN** the user runs `tinytuya version` or `tinytuya help`
- **THEN** `version` prints the installed TinyTuya version and `help` prints a detailed usage summary with examples for all commands
- **AND** running `tinytuya` with no arguments also shows the full help
- Source: [relnote v1.18.0] "New version subcommand — tinytuya version prints the installed TinyTuya version."
- Source: [relnote v1.18.0] "New help subcommand — tinytuya help prints a detailed usage summary with examples for all commands. Running tinytuya with no arguments also shows the full help."

### Requirement: Console-script install (pipx) via no-op entry function
The distribution SHALL declare a `tinytuya` console script bound to `tinytuya.__main__:dummy` — the CLI executes at module import time (argparse parsing and dispatch are top-level statements), so the packaged entry point only needs a callable no-op `dummy()` to satisfy setuptools; `pyproject.toml` carries only the build-system table, all install metadata lives in `setup.py`.
- Status: VERIFIED
- Evidence: [commit 71789638886b] — "Add pipx/entry_points support for CLI"; doc: README.md line 39-40 (`# Optional: Install Command Line Tool` / `pipx install tinytuya`)
- Anchor: `setup.py:50`; `tinytuya/__main__.py:198` (top-level parse), `:268-270` (`dummy` with explanatory comment); `pyproject.toml:1-2`

#### Scenario: pipx install provides the CLI tool
- **WHEN** the distribution is installed with `pipx install tinytuya`
- **THEN** the tinytuya command-line tool is available for easier CLI use
- Source: [relnote v1.14.0] "Add support for pipx install tinytuya as raised by @felipecrs in https://github.com/jasonacox/tinytuya/issues/500 allowing for easier CLI use."
- Source: doc: README.md § TinyTuya Installation "Optional: Install Command Line Tool"

### Requirement: Wizard CLI surface for credentials, files and dry-run
The `wizard` subcommand SHALL expose a "Cloud API Credentials" option group (`-credentials-file`, `-key`, `-secret`, `-region` restricted to the seven choices `cn, eu, eu-w, in, sg, us, us-e`, repeatable `-device DEVICE_ID`), a `-dry-run` flag, and `-raw-response-file` in addition to the shared `-device-file`/`-snapshot-file` overrides, and SHALL pass them into the wizard function.
- Status: VERIFIED
- Evidence: doc: README.md § Command Line "Wizard" usage block (mirrors the flag set one-for-one, including `-region {cn,eu,eu-w,in,sg,us,us-e}` and `-dry-run`); [PR #625](https://github.com/jasonacox/tinytuya/pull/625) — added Singapore datacenter region
- Anchor: `tinytuya/__main__.py:82-85` (wizard file options), `:101-108` (credential group + dry-run), `:247-253` (dispatch into `wizard.wizard()`)

#### Scenario: Dry-run skips the Cloud
- **WHEN** the `wizard` subcommand is invoked with `-dry-run`
- **THEN** the wizard does not actually connect to the Cloud
- Source: doc: README.md § Command Line "-dry-run             Do not actually connect to the Cloud"

#### Scenario: Command-line Cloud API credential options
- **WHEN** the wizard is invoked with `-key`, `-secret`, `-region` or `-device` options
- **THEN** those values are used as the Cloud API Key, Cloud API Secret, Cloud API Region (one of cn, eu, eu-w, in, sg, us, us-e) and one or more Device ID(s) to use
- Source: doc: README.md § Command Line "Wizard Cloud API Options -dry-run Do not actually connect to the Cloud -credentials-file JSON file to load/save Cloud credentials from/to [Default: tinytuya.json] -key KEY Cloud API Key to use -secret SECRET Cloud API Secret to use -region Cloud API Region to use {cn,eu,eu-w,in,sg,us,us-e} -device DEVICE(S) One or more Device ID(s) to use"

### Requirement: Wizard credential load-or-prompt with persistence
The Setup Wizard SHALL load Cloud API credentials (`apiKey`, `apiSecret`, `apiRegion`, `apiDeviceID`) from the config file (default `tinytuya.json`), display and offer to reuse existing settings unless `-yes`, prompt interactively for any missing values (including a printed region list) and write the resulting config back to the credentials file immediately.
- Status: VERIFIED
- Evidence: doc: `tinytuya/wizard.py:10-13` module docstring ("prompt the user for Tuya IoT Developer credentials … save the credentials and the device data in the tinytuya.json and devices.json configuration files"); [commit 28ada7b9fa4a] — "Fix newline in Wizard region list"
- Anchor: `tinytuya/wizard.py:84-106` (load), `:129-141` (reuse prompt), `:143-169` (prompt + save, region list at `:154-161`)

#### Scenario: Wizard prompts for Cloud credentials
- **WHEN** the Setup Wizard runs and collects the Tuya IoT Cloud credentials
- **THEN** the Wizard prompts for the API ID key, API Secret and API Region (cn, us, us-e, eu, eu-w, sg, or in) from the user's Tuya IoT project
- **AND** the credentials are loaded from and saved to the JSON credentials file (default `tinytuya.json`)
- Source: doc: README.md § Setup Wizard "The Wizard will prompt you for the API ID key, API Secret, API Region (cn, us, us-e, eu, eu-w, sg, or in) from your Tuya IoT project"
- Source: doc: README.md § Command Line "credentials-file    JSON file to load/save Cloud credentials from/to [Default: tinytuya.json]"

### Requirement: Wizard device harvest via Cloud with scan shortcut, dry-run, linking and dual file output
Unless `--dry-run` (`nocloud`) reuses the existing `devices.json` list, the wizard SHALL accept `apiDeviceID` set to the literal `scan` by auto-discovering one Device ID via a one-device network scan; call `Cloud.getdevices()`, optionally downloading DP name mappings; infer sub-device parents via `gateway_id` or shared local key; print the device listing; and save the normalized list to `devices.json` plus the full raw cloud response to `tuya-raw.json`.
- Status: VERIFIED
- Evidence: doc: README.md line 115 (wizard creates `devices.json` and `tuya-raw.json`); [commit 14e6b7a3f307] — "Add IoT core service renewal info to the setup wizard in the README"; [commit 2a95d00f8f61] — "improve error messaging in scanner and wizard"
- Anchor: `tinytuya/wizard.py:171-184` (dry-run/scan shortcut), `:186-215` (cloud fetch + renewal hint at `:192-194` and `:211-213`), `:217-254` (parent linking), `:256-265` (save devices.json), `:267-281` (raw file)

#### Scenario: Wizard Device ID scan shortcut
- **WHEN** the wizard asks for a sample Device ID and the user enters `scan`
- **THEN** the wizard scans for a Device ID instead of requiring one to be typed
- Source: doc: README.md § Setup Wizard "It will also ask for a sample Device ID.  You can have the wizard scan for one (enter `scan`)"
- Source: [relnote v1.12.4] "Adds option allowing wizard to scan for a Device ID"

#### Scenario: Wizard saves devices.json and tuya-raw.json
- **WHEN** the Wizard has polled the Tuya IoT Cloud Platform and displays the list of registered devices
- **THEN** it creates a local file `devices.json` for TinyTuya to use
- **AND** the wizard also creates a local file `tuya-raw.json` that contains the entire payload from Tuya Cloud
- Source: doc: README.md § Setup Wizard "In addition to displaying the list of devices, **Wizard** will create a local file `devices.json`"
- Source: doc: README.md § Setup Wizard "The wizard also creates a local file `tuya-raw.json` that contains the entire payload from Tuya Cloud."

### Requirement: Wizard optional poll with IP/version write-back
After saving the device list, the wizard SHALL ask (or honor `-yes`/`-no-poll`) whether to poll local devices; on poll it SHALL run the scanner's `poll_and_display()` with snapshot output, then merge discovered `ip` and `version` per gwId back into the device list and rewrite `devices.json` reporting how many addresses were found.
- Status: VERIFIED
- Evidence: doc: `tinytuya/wizard.py:12-13` ("The Wizard will then optionally scan the local devices for status"); doc: README.md § Scan Tool (`python -m tinytuya snapshot` consumes the wizard/scan snapshot)
- Anchor: `tinytuya/wizard.py:283-313` (poll prompt at `:284-289`, write-back at `:301-313`)

#### Scenario: Wizard poll creates snapshot
- **WHEN** the Wizard asks if you want to poll all the devices and you agree
- **THEN** it displays the status of all devices on record and creates a `snapshot.json` file with these results
- Source: doc: README.md § Setup Wizard "The **Wizard** will ask if you want to poll all the devices. If you do, it will display the status of all devices on record and create a `snapshot.json` file with these results."

#### Scenario: no-poll answers the poll prompt with no
- **WHEN** the wizard is invoked with `-no-poll` (or `-no`)
- **THEN** it answers "no" to the "Poll?" question, overriding `-yes`
- Source: doc: README.md § Command Line "-no-poll, -no        Answer "no" to "Poll?" (overrides -yes)"

### Requirement: list command renders device table or JSON
The `list` subcommand SHALL load devices from the device file (default `devices.json`), normalize rows to `name/id/key/ip/version` preferring `last_ip` over `ip`, print an aligned ASCII table by default or a JSON array under `--json`, and exit non-zero with a distinct message when the file is missing versus when it contains no valid devices.
- Status: VERIFIED
- Evidence: [commit 3cea89363d21] — "enhance device file loading, and improve error handling in CLI"; doc: README.md § Command Line "List" block (`--json  Output as a JSON array instead of a table`)
- Anchor: `tinytuya/cli.py:29-73` (last_ip preference at `:51`, error split at `:34-38`)

#### Scenario: List renders a table or JSON array
- **WHEN** the `list` command runs
- **THEN** it lists all devices from `devices.json` as a formatted table (default) or JSON (`--json`)
- **AND** the JSON form is "a JSON array instead of a table"
- Source: [relnote v1.17.5] "list – List all devices from devices.json as a formatted table (default) or JSON (--json)."
- Source: doc: README.md § Command Line "Output as a JSON array instead of a table"

#### Scenario: Wrapped-dict device file accepted
- **WHEN** the device file uses the {"devices": [{...}]} wrapped-dict format instead of a flat list
- **THEN** the CLI (like the library, scanner, wizard and API server loading paths) supports both formats via the centralized load_devicefile() helper
- Source: [relnote v1.18.0] "All loading paths (library, CLI, scanner, wizard, API server) now support both a flat [{...}] list and the {"devices": [{...}]} wrapped-dict format via a new centralized load_devicefile() helper"
- Source: test: tests.py::TestLoadDeviceFile::test_wrapped_dict

### Requirement: Control-target resolution by ID or name with device-file lookup
Device-control commands SHALL require exactly one of `--id`/`--name` (mutually exclusive argparse group), resolve `--name` case-insensitively against the device file (erroring if not found), and fill missing `--key`, `--ip` and `--version` from the matched device record — including a warning and fallback for a non-numeric `version` value.
- Status: VERIFIED
- Evidence: doc: README.md § Command Line "Device Control Options" (`--key, --ip, and --version are loaded automatically from devices.json if found`); [commit 49dfafe96ba4] — "fix: correct argument description in CLI"
- Anchor: `tinytuya/__main__.py:115-121` (mutually-exclusive group); `tinytuya/cli.py:76-131` (name match at `:89-98`, lookup at `:101-131`)

#### Scenario: Name resolution via case-insensitive lookup
- **WHEN** a control command (`on`, `off`, `set`, `get`) is given `--name NAME` to identify the target device
- **THEN** the device ID is resolved via a case-insensitive lookup in `devices.json`
- **AND** `--id` and `--name` are mutually exclusive and one is required
- Source: [relnote v1.17.5] "All control commands (on, off, set, get) accept --id ID or --name NAME to identify the target device. When --name is used, the device ID is resolved via a case-insensitive lookup in devices.json."
- Source: [relnote v1.18.0] "--id and --name are now mutually exclusive and one is **required** (previously both were optional)"

#### Scenario: Missing credentials filled from device file
- **WHEN** `--key`, `--ip` or `--version` is missing on a control command
- **THEN** they are automatically filled in from the matching `devices.json` entry
- Source: [relnote v1.17.5] "Missing credentials (--key, --ip, --version) are automatically filled in from the matching devices.json entry."
- Source: doc: README.md § Command Line "--key, --ip, and --version are loaded automatically from devices.json if found."

### Requirement: Hidden local-key prompt and strict 16-character validation with shell-escape guidance
When no local key is supplied or found, the CLI SHALL prompt via `getpass` (input hidden) only when stdin is a TTY — exiting with a clear error in piped/CI contexts — and SHALL strip whitespace then reject any key whose length is not exactly 16 characters, printing platform-specific shell-quoting tips (single quotes on Linux/Mac, `^` escapes on Windows CMD, or omitting `--key` to use the prompt).
- Status: VERIFIED
- Evidence: [commit 754cc1c007cd] — "Enhance CLI key handling: prompt for missing keys and validate key length"; [commit 3f1ed917ace9] — "CLI: harden device key prompt and validation"; doc: README.md § Device Control Options (`If --key is omitted … input is hidden … Tuya local keys are always exactly 16 characters`)
- Anchor: `tinytuya/cli.py:139-164` (getpass + TTY guard at `:147-155`), `:166-181` (length check + tips)

#### Scenario: Interactive hidden key prompt when key unresolvable
- **WHEN** `--key` is omitted and the key is not found in `devices.json`
- **THEN** the CLI prompts interactively for the key with input hidden, bypassing shell interpretation entirely so no quoting or escaping is needed
- Source: [relnote v1.18.0] "If --key is omitted and the key is not found in devices.json, the CLI now prompts interactively for the key. Input at a terminal prompt bypasses shell interpretation entirely, so no quoting or escaping is needed."
- Source: doc: README.md § Command Line "If --key is omitted and not in devices.json, the CLI will prompt for it interactively (input is hidden, avoiding shell-escaping issues with special characters like $, #, =)."

#### Scenario: Wrong-length key rejected with quoting tips
- **WHEN** the resolved key is the wrong length (Tuya local keys are always exactly 16 characters)
- **THEN** a clear error is printed with platform-specific quoting tips for Linux/Mac and Windows CMD
- Source: [relnote v1.18.0] "Added key length validation — Tuya local keys are always exactly 16 characters. If the resolved key is the wrong length (the most common symptom of a shell-escaping problem), a clear error is printed with platform-specific quoting tips for Linux/Mac and Windows CMD."

### Requirement: Auto-discovery of IP and protocol version with 3.3 fallback
If the device IP is unknown (absent or `--ip auto`) or the protocol version is unresolved, the CLI SHALL run an inline targeted network scan (honoring `-maxtime`, `-force`, `-no-broadcasts`, debug flags) restricted to the target device ID, adopt the scanned `ip`/`version`, and default the protocol version to 3.3 when the scan cannot find the device.
- Status: VERIFIED
- Evidence: [commit 8105e6b636b2] — "Make sure CLI defaults to v3.3 if not found"; [commit 97f2347c7928] — "Updated help text for --ip"; doc: README.md § On/Off (`--ip … auto-discovered if omitted or set to "Auto"`, `--version … defaults to 3.3`)
- Anchor: `tinytuya/cli.py:183-195` (scanner call at `:185-188`, fallback at `:193-195`)

#### Scenario: IP auto-discovered when omitted or Auto
- **WHEN** `--ip` is omitted or set to "Auto" on a control command
- **THEN** the device IP address is auto-discovered via network scan
- Source: doc: README.md § Command Line "Device IP address (auto-discovered if omitted or set to "Auto")"
- Source: [relnote v1.1.3] "Feature added to do automatic IP address lookup via network scan if _None_ or '0.0.0.0' is specified"

#### Scenario: Version auto-scan with 3.3 default
- **WHEN** `--version` is omitted on a control command
- **THEN** the CLI triggers an auto-scan instead of silently defaulting to v3.3
- **AND** the Tuya protocol version documentation states it is "auto-discovered if omitted, defaults to 3.3"
- Source: [relnote v1.18.0] "--version omitted now triggers an auto-scan instead of silently defaulting to v3.3"
- Source: doc: README.md § Command Line "Tuya protocol version (auto-discovered if omitted, defaults to 3.3)"

### Requirement: Control command execution and output contract
`on`/`off` SHALL call `turn_on()/turn_off()` on the resolved switch DPS (default 1); `set` SHALL require `--dps` and `--value`, parsing `--value` as JSON first and falling back to a plain string; `get` SHALL print the full status JSON without `--dps`, or the bare DPS value with `--dps`; any result containing `Err` SHALL print `Error <code>: <msg>` and exit non-zero, otherwise the JSON result (or `OK`) is printed.
- Status: VERIFIED
- Evidence: [commit e9a23af8c916] — "Enhance device command handling by improving value parsing and error handling"; doc: README.md § Set/Get (`parsed as JSON if possible … otherwise sent as a plain string`, `--dps N → plain scalar value only`)
- Anchor: `tinytuya/__main__.py:123-129` (per-command --dps add_argument); `tinytuya/cli.py:209-255` (JSON parse at `:221-224`, get branches at `:226-242`, error/OK contract at `:248-255`)

#### Scenario: Set value parsed as JSON with string fallback
- **WHEN** a value is supplied with `--value` to the `set` command
- **THEN** it is parsed as JSON if possible (true, false, 123, "text"), otherwise sent as a plain string
- Source: doc: README.md § Command Line "Value to set – parsed as JSON if possible (true, false, 123, "text"), otherwise sent as a plain string"
- Source: [relnote v1.17.5] "set – Write a value to a DPS index (--dps N --value VALUE)."

#### Scenario: Get output shape by DPS option
- **WHEN** the `get` command is run without `--dps`, versus with `--dps N`
- **THEN** omitting `--dps` returns the full status JSON and supplying `--dps N` retrieves a single plain scalar value
- Source: [relnote v1.17.5] "get – Read device status; omit --dps for full status JSON or supply --dps N to retrieve a single plain scalar value."
- Source: doc: README.md § Command Line "No --dps → full status JSON, e.g. {"dps": {"1": true, "2": 500}} --dps N → plain scalar value only, e.g. true"

### Requirement: CLI monitor with persistent socket, 30 s status and 12 s heartbeat cadence
The `monitor` subcommand SHALL connect with a persistent socket, print the initial status, then loop: full `status()` poll every 30 s, `heartbeat()` every 12 s when idle, otherwise non-blocking `receive()` for asynchronous updates, printing every received payload, sleeping 5 s after an error response to throttle retries, and exiting cleanly on Ctrl-C.
- Status: VERIFIED
- Evidence: [commit cec1830af19a] — "Use persistent sockets for CLI monitor"; [commit 2a5ebf934067] — monitor command introduction; doc: README.md § Monitor (`sends a heartbeat every 12 seconds, and polls for a full status refresh every 30 seconds. Press Ctrl-C to exit`)
- Anchor: `tinytuya/cli.py:258-300` (def _monitor_device; timers at :265-266, loop at :276-298)

#### Scenario: Monitor loop cadence and exit
- **WHEN** the `monitor` command connects to the device
- **THEN** it prints the initial status, then enters a persistent loop that listens for asynchronous updates, sends a heartbeat every 12 seconds, and polls for a full status refresh every 30 seconds
- **AND** pressing Ctrl-C exits the monitor
- Source: doc: README.md § Command Line "Connects to the device, prints the initial status, then enters a persistent loop that listens for asynchronous updates, sends a heartbeat every 12 seconds, and polls for a full status refresh every 30 seconds. Press Ctrl-C to exit."
- Source: [relnote v1.18.0] "New monitor command — connects to a device with a persistent socket, prints the initial status, then listens for async updates with a heartbeat every 12 s and a full status refresh every 30 s"

### Requirement: API server: UDP discovery threads plus threaded HTTP control API with env configuration
The bundled server SHALL run one thread per Tuya UDP discovery port (6666/6667/7000) decrypting broadcasts into a device database, and a `ThreadingHTTPServer` GET API on port 8888 (env `APIPORT`) with routes for device listing, status, set, turnon/turnoff, delayed off, cloud sync/config and offline listing; behavior SHALL be configurable via environment (`DEBUGMODE=yes`, `HOST`) or a leading `-d` argument, and the process SHALL exit on SIGTERM.
- Status: VERIFIED
- Evidence: doc: server/README.md (endpoint table, Docker `-e DEBUGMODE`/`-e HOST`, port 8888); [commit e59d6bfb95f6] — "Add option to specify host for server"; [commit 518328ba7b21] — server build version bump to p16
- Anchor: `server/server.py:78` (APIPORT), `:92-93` (DEBUGMODE/HOST), `:97-103` (HOST broadcast math), `:112-114` (`-d` flag), `:128` (SIGTERM), `:673-678` (HTTP server), `:691-694` (threads)

#### Scenario: Server discovers devices and serves the GET API
- **WHEN** the API server is running
- **THEN** it continually listens for Tuya UDP discovery packets and updates the database of active devices
- **AND** it listens for GET requests on local port 8888 with the documented routes (including /devices, /status/, /set/, /turnon/, /turnoff/, /sync, /cloudconfig/ and /offline)
- Source: doc: server_README.md § "The TinyTuya API Server provides a central service to access all your Tuya devices on your network.  It continually listens for Tuya UDP discovery packets and updates the database of active devices."
- Source: doc: server_README.md § API Functions "The server listens for GET requests on local port 8888"

#### Scenario: Server debug mode via -d
- **WHEN** the server is started with the `-d` argument
- **THEN** the server runs in Debug Mode
- Source: doc: server_README.md § Quick Start "Start Server in Debug Mode"

### Requirement: Optional MQTT gateway bridging server device output to a broker
The MQTT gateway SHALL bridge the server's `/devices` HTTP output to an MQTT broker per `mqtt.json` (topic/broker/port/pollingtime) when that config is present, SHALL apply built-in defaults when the config is unreadable, and SHALL remain inactive otherwise.
- Status: VERIFIED
- Evidence: [commit 93834cdfaa04] — "MQTT Gateway for Server"
- Anchor: `server/mqtt/mqtt_gateway.py:83-99` (readconfig with defaults)

### Requirement: Offline PCAP decrypt tool keyed by devices.json
The `tools/pcap_parse.py` utility SHALL read tcpdump PCAP files (via the optional `dpkt` module, with an install hint and hard failure when missing), decrypt Tuya traffic using local keys loaded from a `devices.json` (explicit `-d FILE`, else auto-probing `devices.json` and `../devices.json`), and offer `-z/--hide-zero-len` (suppress 0-length heartbeats) and `-s/--sortable` (device-ID-sortable output) flags.
- Status: VERIFIED
- Evidence: doc: tools/README.md § Packet Capture Parser (usage block matches all flags); [commit 736b980df8d8] — related tooling work on the fake v3.5 device
- Anchor: `tools/pcap_parse.py:16-23` (dpkt guard), `:403-409` (argparse flags), `:417-427` (devices.json auto-probe)

#### Scenario: Decrypt Tuya traffic from PCAP files
- **WHEN** the parser is run on PCAP files created by tcpdump
- **THEN** it prints the traffic to/from Tuya devices with local keys loaded from devices.json
- **AND** the `-d` option specifies the devices.json file to read local keys from
- Source: doc: tools_README.md § Packet Capture Parser "Reads PCAP files created by tcpdump and prints the traffic to/from Tuya devices. Local keys are loaded from devices.json."
- Source: doc: tools_README.md § Usage "-d devices.json,      devices.json file to read local keys from"

#### Scenario: Output filtering flags
- **WHEN** `-z` / `--hide-zero-len` or `-s` / `--sortable` is passed to the parser
- **THEN** zero-length heartbeat packets are hidden, or the data is output in a way which is sortable by device ID
- Source: doc: tools_README.md § Usage "-z, --hide-zero-len   Hide 0-length heartbeat packets"
- Source: doc: tools_README.md § Usage "-s, --sortable        Output data in a way which is sortable by device ID"

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

## Scenario-ification notes
- REQ "Optional MQTT gateway bridging server device output to a broker": no doc-grounded trigger; kept as invariant. (Tier A relnotes only record the gateway's existence and a CPU-loop fix for it; no Tier A/B/C text describes the mqtt.json trigger, the built-in defaults when the config is unreadable, or the inactive state — behavior is code-only.)
- REQ "Auto-discovery of IP and protocol version with 3.3 fallback": scenarios added cover the documented auto-discovery and the documented 3.3 default wording; the reconciliation "default to 3.3 when the scan cannot find the device" is not verbatim in any Tier A/B text (README says "defaults to 3.3"; relnote v1.18.0 says the omitted `--version` "triggers an auto-scan instead of silently defaulting to v3.3" — flagged, not fixed).
