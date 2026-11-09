# Capability: device-control

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06).

## Purpose
Local TCP control of Tuya devices: construction and address/version selection, socket connect/retry policy, synchronous and non-blocking status/set round-trips, error-dict return conventions, device22 command quirks, and status caching. Lives in `tinytuya/core/XenonDevice.py` (base class + module-level discovery helpers), `tinytuya/core/Device.py` (control wrappers), `tinytuya/core/error_helper.py` (error codes) and `tinytuya/core/udp_helper.py` (discovery-broadcast decryption feeding the auto-IP path). Wire framing and crypto are owned by the protocol-crypto capability and are referenced, not duplicated, here.

## Primary code locations
- `tinytuya/core/XenonDevice.py` — base device: construction, sockets, retry policy, status/set round-trips, device22 quirks, payload templating, caching
- `tinytuya/core/Device.py` — `Device(XenonDevice)`: set_status/turn_on/turn_off/set_value/set_multiple_values/set_timer/heartbeat
- `tinytuya/core/error_helper.py` — ERR_* codes and `error_json()` return convention
- `tinytuya/core/udp_helper.py` — `decrypt_udp()` for discovery broadcasts (feeds auto-IP)
- `tinytuya/core/const.py` — port constants (TCP 6668, UDP 6666/6667/7000)

## Requirements

### Requirement: Constructor defaults and bounded connection-time budget
`XenonDevice` SHALL default to `connection_timeout=5`, `version=3.1`, `persist=False`, `connection_retry_limit=5`, `connection_retry_delay=5`, `port=6668` (TCPPORT), and a failed connect SHALL retry at most `socketRetryLimit` times with `socketRetryDelay` sleeps between attempts (total budget = timeout×limit + delay×(limit−1)).
**Status**: VERIFIED
**Evidence**: doc: API.md § XenonDevice Constructor (defaults + total-timeout formula); [commit f44daa364d09] — expose retry limit/delay via constructor; [commit e51c0d2669ee] — socketRetryDelay as parameter instead of fixed 5
**Anchor**: `tinytuya/core/XenonDevice.py:238-244` (signature), `:274-275` (socketRetryLimit/Delay), `:359` + `:423-424` (retry loop + delay sleep), `:391` (connect timeout); `tinytuya/core/const.py:10` (TCPPORT=6668)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `XenonDevice` SHALL default to `connection_timeout=5`, `version=3.1`, `persist=False`, `connection_retry_limit=5`, `connection_retry_delay=5`, `port=6668` (TCPPORT), and a failed connect SHALL retry at most `socketRetryLimit` times with `socketRetryDelay` sleeps between attempts (total budget = time
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Auto-IP discovery and re-scan on failure
When `address` is `None`, `"Auto"` or `"0.0.0.0"`, the constructor SHALL discover the device via UDP broadcast (`find_device`), adopt its IP and advertised protocol version, and SHALL raise `RuntimeError("Unable to find device on network (specify IP address)")` if discovery fails; if a later connect attempt fails for an auto-IP device, the cached address SHALL be dropped and re-discovered on the next retry.
**Status**: VERIFIED
**Evidence**: doc: API.md § XenonDevice Constructor (`address="Auto"` to discover); [commit 9c3b0d2fee91] — scan for new IP when auto-IP and last-known address fails
**Anchor**: `tinytuya/core/XenonDevice.py:321-330` (auto branch, RuntimeError at :327, version adopt at :329), `:360-365` (re-discover in `_get_socket`), `:425-426` (address cleared after failed retry), `:40` (lazy `from .. import scanner`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** When `address` is `None`, `"Auto"` or `"0.0.0.0"`, the constructor SHALL discover the device via UDP broadcast (`find_device`), adopt its IP and advertised protocol version, and SHALL raise `RuntimeError("Unable to find device on network (specify IP address)")` if discovery fails;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: IPv6-capable connection addresses
The connect path SHALL select `AF_INET6` when the address contains `:` and `AF_INET` otherwise, so IPv6/NAT64 device addresses work without caller changes.
**Status**: VERIFIED
**Evidence**: [commit f30100c49572] — add support for IPv6/NAT64 device connection addresses
**Anchor**: `tinytuya/core/XenonDevice.py:387-388` (`family = socket.AF_INET6 if ':' in self.address else socket.AF_INET`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The connect path SHALL select `AF_INET6` when the address contains `:` and `AF_INET` otherwise, so IPv6/NAT64 device addresses work without caller changes.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Pre-connect key/version gate and session negotiation for v3.4+
For `version > 3.1`, `_get_socket` SHALL refuse to connect (returning `ERR_KEY_OR_VER`) when the local key is missing or not 16 bytes; for `version >= 3.4` it SHALL complete session-key negotiation immediately after TCP connect and return `ERR_KEY_OR_VER` (socket closed) if negotiation fails. (Nonce/HMAC mechanics belong to protocol-crypto.)
**Status**: VERIFIED
**Evidence**: [commit 19c6495d20bd] — better error/timeout handling for 3.4 devices; [commit 0c8caad3bfc9] — make connection/key errors more descriptive; doc: API.md § Error Codes row 914
**Anchor**: `tinytuya/core/XenonDevice.py:380-385` (key length gate), `:395-403` (negotiation on connect, `ERR_KEY_OR_VER` on failure); `tinytuya/core/error_helper.py:24` (ERR_KEY_OR_VER=914)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** For `version > 3.1`, `_get_socket` SHALL refuse to connect (returning `ERR_KEY_OR_VER`) when the local key is missing or not 16 bytes;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Per-call sockets by default, persistent on request
The default lifecycle SHALL close the socket after each command (`_check_socket_close` when not persistent, also clearing the status cache); `set_socketPersistent(True)` SHALL keep it open between commands, and switching to non-persistent SHALL immediately close an open socket.
**Status**: VERIFIED
**Evidence**: doc: API.md § set_socketPersistent ("close after each one (False, default)"); [commit 5bac27006a45] — persistent connections across commands (gateway rework)
**Anchor**: `tinytuya/core/XenonDevice.py:432-436` (`_check_socket_close` + `cache_clear`), `:629` / `:769` (per-call close in `_send_receive`/`_process_message`), `:1173-1178` (`set_socketPersistent`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The default lifecycle SHALL close the socket after each command (`_check_socket_close` when not persistent, also clearing the status cache);
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Split send/receive retries with null-ACK handling in _send_receive
`_send_receive` SHALL retry sends on socket timeout/network exceptions up to `socketRetryLimit` (tossing the socket each time) but retry *reads* separately up to `socketRetryLimit` only when `retry` is enabled; a null-payload response SHALL be treated as an ACK so the request is not re-sent; `nowait` callers get send-only semantics (`getresponse=False`).
**Status**: VERIFIED
**Evidence**: [commit 8528e03565d6] — separate read and write retries, retry reads on corrupt messages/null payloads; [commit d5f483e9296b] — allow nowait for status(), split message parsing
**Anchor**: `tinytuya/core/XenonDevice.py:552` (`_send_receive`), `:583` (`max_recv_retries = 0 if not self.retry else self.socketRetryLimit`), `:611-626` (null-ACK = partial success, no re-send), `:640-643` (send retry: `do_send=True`, socket tossed)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `_send_receive` SHALL retry sends on socket timeout/network exceptions up to `socketRetryLimit` (tossing the socket each time) but retry *reads* separately up to `socketRetryLimit` only when `retry` is enabled;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Errors returned as error dicts, not exceptions
Send/receive failures SHALL return `{"Error": <text>, "Err": "<code>", "Payload": ...}` dicts — `ERR_TIMEOUT`(902) on exhausted send retries after timeout, `ERR_CONNECT`(901) on exhausted network-error retries, `ERR_PAYLOAD`(904) on decode exhaustion without any valid message — instead of raising; `ERR_OFFLINE`(905) when no socket can be obtained.
**Status**: VERIFIED
**Evidence**: doc: API.md § Error Codes ("return an error dict instead of raising exceptions"); [commit 11a3e2eb9720] — timeout error handling; [commit c01993d60996] — catch timeouts in new function
**Anchor**: `tinytuya/core/error_helper.py:10-24,46-50` (codes + `error_json`); `tinytuya/core/XenonDevice.py:595` (`ERR_OFFLINE`), `:655` (`ERR_TIMEOUT`), `:668` (`ERR_PAYLOAD`), `:687` (`ERR_CONNECT`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Send/receive failures SHALL return `{"Error": <text>, "Err": "<code>", "Payload": ...}` dicts — `ERR_TIMEOUT`(902) on exhausted send retries after timeout, `ERR_CONNECT`(901) on exhausted network-error retries, `ERR_PAYLOAD`(904) on decode exhaustion without any valid message — instead of raising;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: status() DP_QUERY with transparent device22 retry and version hint
`status(nowait=False)` SHALL send a DP_QUERY payload and return the decoded dict; when the reply carries `ERR_DEVTYPE`(908) it SHALL regenerate the payload for the switched dev_type and re-send once; on `ERR_PAYLOAD` it SHALL log a "is version/local key correct?" hint. `nowait=True` SHALL fire without waiting (`receive()` later).
**Status**: VERIFIED
**Evidence**: doc: API.md § status; [commit 563182a16988] — add device22 check back in; [commit c15837d04032] + [commit 71fb5410b74b] — "check version" suggestion on status error/no data
**Anchor**: `tinytuya/core/XenonDevice.py:1069-1087` (status; device22 resend :1079-1083; version hint :1084-1085), `:725-732` (`ERR_DEVTYPE` raised on dev_type switch in `_process_message`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `status(nowait=False)` SHALL send a DP_QUERY payload and return the decoded dict;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: device22 command overrides with explicit DPS list
Devices with 22-character IDs (and all 3.2 devices) reject plain DP_QUERY; for `dev_type="device22"` the library SHALL override DP_QUERY with the CONTROL_NEW (0x0d) command and include the explicit `dps_to_request` list in the payload. Detection is automatic unless disabled: a `"data unvalid"` payload on v3.3/3.4 SHALL flip `dev_type` to `"device22"` and seed `dps_to_request = {"1": None}`.
**Status**: VERIFIED
**Evidence**: doc: DESIGN.md § XenonDevice ("device22 detection... rewrites DP_QUERY → CONTROL_NEW with an explicit DPS list"); doc: API.md § Constructor `dev_type="device22"`; [commit 563182a16988], [commit 55af8d1d7493] — skip DPS detection if already set
**Anchor**: `tinytuya/core/XenonDevice.py:169-174` (payload_dict device22 → CONTROL_NEW), `:1357-1358` (explicit dps list injected), `:825-833` ("data unvalid" auto-switch + DPS-1 seed), `:269` (`disabledetect`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Devices with 22-character IDs (and all 3.2 devices) reject plain DP_QUERY;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: detect_available_dps brute-forces ranges with DPS 1 always seeded
`detect_available_dps()` SHALL probe the fixed ranges (2-10, 11-20, 21-30, 50-60, 61-70, 100-110, 111-120, 121-130, 131-140) in separate status calls (payload length limit), always seeding `dps_to_request` with `{"1": None}` first, accumulate found DPS into `dps_cache`, and return `{dp: None}` while installing the result as the request set.
**Status**: VERIFIED
**Evidence**: doc: API.md § detect_available_dps ("Returns a dict {dp_id: None}"); [commit 89e3ceb35ad5] — dps "1" seed for 3.2 discovery; [commit f8bd7febada7] — optimize detect_available_dps
**Anchor**: `tinytuya/core/XenonDevice.py:1123-1152` (ranges :1131, DPS-1 seed :1136, default short-circuit :1147-1149)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `detect_available_dps()` SHALL probe the fixed ranges (2-10, 11-20, 21-30, 50-60, 61-70, 100-110, 111-120, 121-130, 131-140) in separate status calls (payload length limit), always seeding `dps_to_request` with `{"1": None}` first, accumulate found DPS into `dps_cache`, and return `{dp: None}` while
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: set_version normalizes to float and maps 3.2 to device22
`set_version()` SHALL coerce its argument with `float()`, rebuild `version_str`/`version_bytes`/`version_header` and invalidate the merged payload dict; version 3.2 SHALL behave as 3.3-with-device22 (set `dev_type="device22"`, running `detect_available_dps()` if no DPS set exists).
**Status**: VERIFIED
**Evidence**: [commit e3c7358ac426] — fix set_version() for float; [commit 9420ec66f8d3] — make sure set_version() is given a float (#507); doc: API.md § set_version ("Must be called before any command")
**Anchor**: `tinytuya/core/XenonDevice.py:1161-1171` (`float(version)` :1162, device22 + detect :1168-1171)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `set_version()` SHALL coerce its argument with `float()`, rebuild `version_str`/`version_bytes`/`version_header` and invalidate the merged payload dict;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Status cache requires a persistent connection
While connected persistently, every decoded response SHALL be merged into last-status and historic caches; `cached_status()` SHALL return the cache only when a status was seen AND the connection is persistent AND open — otherwise it SHALL call `status()` (nowait=False) or return None (nowait=True); `historic=True` returns the never-invalidated merge of all DPs ever seen.
**Status**: VERIFIED
**Evidence**: doc: API.md § cached_status ("requires persist=True... Falls back to status() if cache is empty"); [commit 0b5682c6040c] — add status caching
**Anchor**: `tinytuya/core/XenonDevice.py:874-885` (`_cache_response`, persist gate :880), `:1089-1111` (`cached_status` fallback logic :1103-1108), `:1113-1115` (`cache_clear`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** While connected persistently, every decoded response SHALL be merged into last-status and historic caches;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Device control wrappers with non-blocking option
`Device` SHALL provide `set_status(on, switch=1)`, `turn_on`/`turn_off`, `set_value(index, value)` and `set_timer(num_secs, dps_id=0)` issuing CONTROL payloads — each accepting `nowait` — with `dps_id=0` auto-selecting the highest-numbered DPS from a fresh status as the timer; `heartbeat(nowait=True)` SHALL default to fire-and-forget since HEART_BEAT replies carry an empty payload.
**Status**: VERIFIED
**Evidence**: doc: API.md § Device (set_status/turn_on/turn_off/set_value/set_timer, heartbeat(nowait=True)); [commit dd3ad7f091a2] — heartbeat() default nowait=True as HEART_BEAT does not return data
**Anchor**: `tinytuya/core/Device.py:17-34` (set_status), `:155-161` (turn_on/turn_off), `:80-97` (set_value), `:163-192` (set_timer auto-detect :174-186), `:47-60` (heartbeat `nowait=True` default, rationale comment :51)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `Device` SHALL provide `set_status(on, switch=1)`, `turn_on`/`turn_off`, `set_value(index, value)` and `set_timer(num_secs, dps_id=0)` issuing CONTROL payloads — each accepting `nowait` — with `dps_id=0` auto-selecting the highest-numbered DPS from a fresh status as the timer;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: set_multiple_values adapts to multi-DP-incapable devices
`set_multiple_values(data)` SHALL send all pairs in one CONTROL when allowed, SHALL chunk into per-DP `set_value` calls when `len(data) > max_simultaneous_dps > 0`, and on a failed multi-DP send SHALL retry the first DP alone — if that succeeds it SHALL latch `max_simultaneous_dps = 1` and set the rest one by one.
**Status**: VERIFIED
**Evidence**: doc: API.md § set_multiple_values; [commit 0b5682c6040c] — modify set_multiple_values() to detect devices that cannot set multiple; [commit b5e93d3c2c40] — documentation for set_multiple_values()
**Anchor**: `tinytuya/core/Device.py:99-153` (chunking :123-131, capability probe + latch :141-152); `tinytuya/core/XenonDevice.py:243,293` (`max_simultaneous_dps`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `set_multiple_values(data)` SHALL send all pairs in one CONTROL when allowed, SHALL chunk into per-DP `set_value` calls when `len(data) > max_simultaneous_dps > 0`, and on a failed multi-DP send SHALL retry the first DP alone — if that succeeds it SHALL latch `max_simultaneous_dps = 1` and set the r
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: UDP broadcast decryption for the discovery/auto path
`decrypt_udp()` SHALL transparently decrypt discovery broadcasts in all three shapes — raw AES-ECB under the static key `MD5("yGAdlopoPVldABfn")`, `55AA`-framed, and `6699`/GCM (stripping trailing NULs) — since this is what feeds `find_device`/auto-IP; it is decryption of received broadcasts only.
**Status**: VERIFIED
**Evidence**: doc: API.md § decrypt_udp; doc: DESIGN.md § Discovery (UDP 6666/6667/7000, static key, `decrypt_udp()` handles raw-ECB/55AA/6699)
**Anchor**: `tinytuya/core/udp_helper.py:21` (static key), `:23-44` (three-shape dispatch); `tinytuya/scanner.py:1536` (sole call site)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `decrypt_udp()` SHALL transparently decrypt discovery broadcasts in all three shapes — raw AES-ECB under the static key `MD5("yGAdlopoPVldABfn")`, `55AA`-framed, and `6699`/GCM (stripping trailing NULs) — since this is what feeds `find_device`/auto-IP;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

## Known gaps
- **No UDP control fallback at this pin.** The capability brief lists a "udp fallback path", but `XenonDevice` contains no UDP transport for commands — UDP exists only for discovery broadcast decryption (`tinytuya/core/udp_helper.py`, used solely by `tinytuya/scanner.py:1536`) feeding auto-IP. Recorded as-is rather than assumed.
- `max_simultaneous_dps` is a constructor parameter (`tinytuya/core/XenonDevice.py:243`) but is absent from API.md § XenonDevice Constructor.
- Doc nit: API.md § updatedps shows `updatedps(index=[1], ...)` while the code signature is `index=None` with `[1]` applied internally (`tinytuya/core/Device.py:62,70-71`) — behaviorally equivalent, signature differs.
- Doc nit: API.md § send says "Send a raw `MessagePayload`"; the code accepts a `MessagePayload` **or** pre-encoded bytes (`tinytuya/core/XenonDevice.py:600`).
- Monitor `auto_reconnect` connector-thread commits ([commit f3629a1f5985], [commit 0d66872ffd97]) touch reconnection around this class but live outside the owned files; not specified here.
- Session-key negotiation is invoked from the connect path but its wire mechanics are owned by the protocol-crypto capability draft.
