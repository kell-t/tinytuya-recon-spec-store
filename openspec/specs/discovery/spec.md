# Capability: discovery

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06).

## Purpose
Discovery finds Tuya devices on the LAN by listening for their UDP broadcasts on ports 6666 (3.1 plaintext), 6667 (3.2+ AES-ECB and some 3.5 GCM) and 7000 (app/solicited 3.5), and by optionally "force-scanning" TCP 6668 across IP ranges to brute-force version and local key from `devices.json`. It lives in `tinytuya/scanner.py` (single-threaded `select()` loop plus per-device state machines), with broadcast decryption in `tinytuya/core/udp_helper.py` and port/timing constants in `tinytuya/core/const.py`. Scan results are reported to stdout, returned as a dictionary, and persisted to `snapshot.json`; `tools/broadcast-relay.py` extends the broadcast mechanism across broadcast-blocking networks.

## Primary code locations
- `tinytuya/scanner.py` — network discovery: UDP listeners, force-scan state machines, snapshot I/O (2132 lines)
- `tinytuya/core/udp_helper.py` — tri-format discovery broadcast decryption under the well-known UDP key
- `tinytuya/core/const.py` — UDP/TCP ports (6666/6667/7000/6668), SCANTIME, TIMEOUT, DEFAULT_NETWORK
- `tinytuya/core/core.py` — legacy `tinytuya.scan()` / `tinytuya.deviceScan()` wrappers mapping `maxretry`→`scantime`
- `tinytuya/core/XenonDevice.py` — module-level `find_device()` delegating to the scanner
- `tinytuya/cli.py` — `tinytuya scan|list|snapshot|json` command plumbing (`scanner.devices()` call)
- `tools/broadcast-relay.py` — cross-network relay of Tuya broadcasts to app clients
- `tools/pcap_parse.py` — offline pcap analysis of 6666/6667/7000/6668 traffic

## Requirements

### Requirement: UDP broadcast listeners on ports 6666, 6667 and 7000
The scanner SHALL listen for device broadcasts on UDP 6666 (3.1, plaintext), 6667 (3.2+ encrypted) and 7000 (app/solicited) with `SO_BROADCAST` and best-effort `SO_REUSEPORT`, so multiple concurrent scans/listeners can coexist where the OS supports it.
**Status**: VERIFIED
**Evidence**: commits [4df14afeeead] Add UDP 7000 broadcast, [b64fb93e6948] Allow multiple concurrent scans under some operation systems; doc: DESIGN.md:100-102 (§ Discovery), README.md:714
**Anchor**: `tinytuya/scanner.py:1195-1226` (three bound listeners), `tinytuya/core/const.py:7-9` (UDPPORT/UDPPORTS/UDPPORTAPP)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The scanner SHALL listen for device broadcasts on UDP 6666 (3.1, plaintext), 6667 (3.2+ encrypted) and 7000 (app/solicited) with `SO_BROADCAST` and best-effort `SO_REUSEPORT`, so multiple concurrent scans/listeners can coexist where the OS supports it.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Periodic v3.5 solicitation on UDP 7000
The scanner SHALL send an app-style 6699/GCM broadcast `{"from":"app","ip":"<client-ip>"}` to each interface's broadcast address on UDP 7000, re-sending every 6 seconds during the scan, because newer 3.5 devices stay silent until solicited. If every send fails, it SHALL log an error stating that v3.5 devices will not be found.
**Status**: VERIFIED
**Evidence**: commits [831f1131f17e] Make scanner send broadcasts to port 7000, [7d160a0f98ac] Allow device discovery packets on port 7000, [fcee73701ea0] better error message when sending scanner broadcasts fails; doc: PROTOCOL.md § "Discovery (v3.5)" (PROTOCOL.md:494-499, 524-531)
**Anchor**: `tinytuya/scanner.py:213-267` (send_discovery_request; payload at 242-244), `tinytuya/scanner.py:81` (BROADCASTTIME=6), `tinytuya/scanner.py:1670-1672` (periodic re-send)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The scanner SHALL send an app-style 6699/GCM broadcast `{"from":"app","ip":"<client-ip>"}` to each interface's broadcast address on UDP 7000, re-sending every 6 seconds during the scan, because newer 3.5 devices stay silent until solicited.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Scan functionality without GCM crypto
Discovery SHALL still run when the crypto library lacks AES-GCM: solicitation is skipped (not crashed), so only silent newer-3.5 devices are missed.
**Status**: VERIFIED
**Evidence**: commits [8d191d792cd7] Allow scanner to work even without GCM, [1be11b2e6406] Remove requirement for PyCryptodome in scanner (allows pyaes when no devices are v3.5+)
**Anchor**: `tinytuya/scanner.py:216-218` (`if not tinytuya.AESCipher.CRYPTOLIB_HAS_GCM: return False`)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Discovery SHALL still run when the crypto library lacks AES-GCM: solicitation is skipped (not crashed), so only silent newer-3.5 devices are missed.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Transparent decryption of all three broadcast formats
Discovery SHALL transparently decrypt broadcast payloads in all three wire formats — raw AES-ECB blob, 55AA-framed (plaintext or ECB payload), and 6699/GCM — using the well-known UDP key `MD5("yGAdlopoPVldABfn")`, and SHALL strip trailing NUL bytes that app packets append.
**Status**: VERIFIED
**Evidence**: commits [ff4b2f25eeca] refactor udp decryption to own file, [9fce7640a84d] Fix tinytuya.find_device() and decrypt_udp() for v3.1 devices, [e52cc07e39ed] Strip trailing NULs to make the scanner JSON parser happy; doc: PROTOCOL.md:499, API.md § scanning
**Anchor**: `tinytuya/core/udp_helper.py:21` (udpkey), `tinytuya/core/udp_helper.py:23-44` (decrypt_udp; NUL strip at 42)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Discovery SHALL transparently decrypt broadcast payloads in all three wire formats — raw AES-ECB blob, 55AA-framed (plaintext or ECB payload), and 6699/GCM — using the well-known UDP key `MD5("yGAdlopoPVldABfn")`, and SHALL strip trailing NUL bytes that app packets append.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: `devices()` scan API and return contract
`scanner.devices()` SHALL return a dictionary of discovered devices keyed by IP address, or by Device ID when `byID=True`, each entry carrying `ip`, `gwId`, `version`, `key`, `name`, `mac` and an `origin` field of `broadcast`, `forcescan`, or `cloud`.
**Status**: VERIFIED
**Evidence**: commits [a495c694990c] Complete rewrite of the scanner, now allows force-scanning of IP ranges, [0b199901c01f] Rewrite tinytuya.find_device() to use the scanner; doc: API.md:42-50 (deviceScan returns dictionary), README.md:714
**Anchor**: `tinytuya/scanner.py:1131-1151` (signature/params docstring), `tinytuya/scanner.py:1777-1795` (keying + `origin`), `tinytuya/scanner.py:1801-1809` (cloud-origin entries)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `scanner.devices()` SHALL return a dictionary of discovered devices keyed by IP address, or by Device ID when `byID=True`, each entry carrying `ip`, `gwId`, `version`, `key`, `name`, `mac` and an `origin` field of `broadcast`, `forcescan`, or `cloud`.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Targeted scans stop early and suppress snapshot writes
When callers specify `wantips`, `wantids` or `maxdevices`, the scan SHALL end as soon as all targets are found, report any targets never found, and SHALL NOT write the `snapshot.json` file (the scan was targeted, not a full inventory).
**Status**: VERIFIED
**Evidence**: commits [a6bdef71517a] Tell scanner to not save snapshot file when only looking for certain devices, [0b199901c01f] Rewrite tinytuya.find_device() to use the scanner
**Anchor**: `tinytuya/scanner.py:1653-1668` (early-end on wantids/wantips), `tinytuya/scanner.py:1620-1631` (maxdevices), `tinytuya/scanner.py:1767-1770` (not-found report), `tinytuya/scanner.py:1797` (`if verbose and not can_end_early:` gate on save)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** When callers specify `wantips`, `wantids` or `maxdevices`, the scan SHALL end as soon as all targets are found, report any targets never found, and SHALL NOT write the `snapshot.json` file (the scan was targeted, not a full inventory).
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Force-scan fallback for targeted devices missed by broadcast
If a targeted scan's time budget expires with `wantips` still unmatched, the scanner SHALL automatically force-scan (TCP 6668) exactly the missing IP addresses.
**Status**: VERIFIED
**Evidence**: commits [d3be0ac645fc] Fix scanner force-scanning, [0b199901c01f] Rewrite tinytuya.find_device() to use the scanner
**Anchor**: `tinytuya/scanner.py:1646-1651` ("Not all devices were found by broadcast, starting force-scan for missing devices")


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** If a targeted scan's time budget expires with `wantips` still unmatched, the scanner SHALL automatically force-scan (TCP 6668) exactly the missing IP addresses.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Force-scan target selection with keys precondition
Force scanning SHALL accept explicit networks (list, nested list, or a single string, host bits tolerated via `strict=False`) or auto-detect the host's networks from interfaces via netifaces (preferred) or psutil, prompting per-network unless `assume_yes`; loopback is excluded. Force scan SHALL require known local keys: with broadcast listening on it SHALL warn and disable itself, with `discover=False` it SHALL raise `RuntimeError`.
**Status**: VERIFIED
**Evidence**: commits [ff6abf2275da] Add get_ip_to_broadcast() function to scanner, [c6dba30c6eae] Also use psutil to get the force-scan IP list if netifaces is not available, [133fd359fdd8] Allow host bits in the force-scan network list, [d3bc3d08ba56] Allow a string as the force-scan list, [2b495bca257c] Add network configuration for force scan; doc: DESIGN.md:102
**Anchor**: `tinytuya/scanner.py:1300-1341` (target parsing + auto-detect + keys gate at 1188-1193), `tinytuya/scanner.py:1072` (`ipaddress.ip_network(..., strict=False)`), `tinytuya/scanner.py:120-181` (getmyIPs via netifaces/psutil)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Force scanning SHALL accept explicit networks (list, nested list, or a single string, host bits tolerated via `strict=False`) or auto-detect the host's networks from interfaces via netifaces (preferred) or psutil, prompting per-network unless `assume_yes`;
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Protocol-version detection via probe-and-classify state machine
For force-scanned devices of unknown version, the scanner SHALL send an unencrypted status request and classify the reaction: plaintext error reply ⇒ 3.1 (brute-force path); encrypted reply ⇒ 3.3; connection dropped three times ⇒ 3.4/3.5 session-key negotiation, assuming 3.4 unconfirmed and upgrading to 3.5 only when a 6699 prefix is seen in the response. A default-type device that connects-then-closes shall be retried once as `device22` (CONTROL_NEW).
**Status**: VERIFIED
**Evidence**: commits [d72f3085c5ea] Enhance device version detection for v3.4 and v3.5 in ForceScannedDevice class #671, [e9fd881cff54] Add force-scanning v3.5 devices to scanner, [7259b8dec70a] Rename scanner variable try_v35 to try_v35_with_v34, [5e066415e651] Scanner fix for v3.1 devices
**Anchor**: `tinytuya/scanner.py:606-624` (DP_QUERY/CONTROL_NEW probe), `tinytuya/scanner.py:662-684` (6699-vs-55AA prefix discrimination), `tinytuya/scanner.py:729-768` (3.1 vs 3.3 classification), `tinytuya/scanner.py:487-513` (device22 retry, then 3.4/3.5 negotiation)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** For force-scanned devices of unknown version, the scanner SHALL send an unencrypted status request and classify the reaction: plaintext error reply ⇒ 3.1 (brute-force path);
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Local-key brute forcing from devices.json
Force scan SHALL attempt to match each found device's local key by trying keys from `devices.json` (decrypting captured payloads for 3.1/3.3, running session negotiation for 3.4/3.5), marking matched keys used, falling back to passive listening when the list is exhausted, and reporting "No matching key found" on failure.
**Status**: VERIFIED
**Evidence**: commits [e9fd881cff54] Add force-scanning v3.5 devices to scanner, [a495c694990c] Complete rewrite of the scanner; doc: DESIGN.md:102 ("brute-forcing version/key from devices.json")
**Anchor**: `tinytuya/scanner.py:810-842` (brute_force_v3x_data), `tinytuya/scanner.py:844-892` (key cycling, passive fallback, brute_force_found_key)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Force scan SHALL attempt to match each found device's local key by trying keys from `devices.json` (decrypting captured payloads for 3.1/3.3, running session negotiation for 3.4/3.5), marking matched keys used, falling back to passive listening when the list is exhausted, and reporting "No matching 
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: snapshot.json persistence with field normalization
Verbose full scans SHALL save discovered/polling data to `snapshot.json` as `{timestamp, devices:[...]}`, normalizing `version`→string `ver` and `gwId`→`id`, and SHALL load/normalize snapshots (accepting either field name, version preferred) for snapshot polling.
**Status**: VERIFIED
**Evidence**: commits [35c1842dbbea] Save keys listed in DEVICEFILE_SAVE_VALUES to devices.json and rework wizard, [bddb9736b01b] Move creation of tuya-raw.json file info block into Wizard; doc: README.md:116 (wizard creates snapshot.json), DESIGN.md § Package Layout
**Anchor**: `tinytuya/scanner.py:1911-1928` (save_snapshotfile), `tinytuya/scanner.py:1872-1896` (_snapshot_save_item normalization), `tinytuya/scanner.py:1860-1870` (_snapshot_load_item), `tinytuya/scanner.py:1898-1909` (load_snapshotfile)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Verbose full scans SHALL save discovered/polling data to `snapshot.json` as `{timestamp, devices:[...]}`, normalizing `version`→string `ver` and `gwId`→`id`, and SHALL load/normalize snapshots (accepting either field name, version preferred) for snapshot polling.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Offline device representation
Snapshot-based reporting SHALL keep registered devices that are not currently reachable and display them distinctly: no IP recorded ⇒ flagged "No IP found - Battery-powered or offline"; IP but no poll reply ⇒ "No Response". The API server's `/offline` endpoint is a downstream consumer of this record set.
**Status**: VERIFIED
**Evidence**: commits [9c3b0d2fee91] Scan for new IP address then auto-IP is used and connection to last-known address fails, [bddb9736b01b]; doc: server/README.md:25 (`/offline - List of registered devices that are offline` — consumer boundary, not discovery code)
**Anchor**: `tinytuya/scanner.py:1841-1846` (_display_status offline / no-response branches)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** Snapshot-based reporting SHALL keep registered devices that are not currently reachable and display them distinctly: no IP recorded ⇒ flagged "No IP found - Battery-powered or offline";
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: Legacy scan() / deviceScan() wrappers with maxretry→scantime mapping
The public `tinytuya.scan()` and `tinytuya.deviceScan()` SHALL remain available and map the legacy `maxretry` argument onto the scanner's `scantime` (seconds), defaulting to `SCANTIME` (18) when unset.
**Status**: VERIFIED
**Evidence**: commits [637c9aeefd03] Map maxretry to scantime in scan functions #247; doc: API.md:42-53 — doc disagrees on default (see Known gaps)
**Anchor**: `tinytuya/core/core.py:228-231` (scan), `tinytuya/core/core.py:235-261` (deviceScan; mapping at 261), `tinytuya/core/const.py:6` (SCANTIME=18)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** The public `tinytuya.scan()` and `tinytuya.deviceScan()` SHALL remain available and map the legacy `maxretry` argument onto the scanner's `scantime` (seconds), defaulting to `SCANTIME` (18) when unset.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: find_device() single-device lookup
`tinytuya.find_device(dev_id=None, address=None)` SHALL run the scanner in targeted mode for one Device ID or IP and return `{ip, version, id, product_id, data}`, with all-`None`/empty-data on no match (never raising).
**Status**: VERIFIED
**Evidence**: commits [0b199901c01f] Rewrite tinytuya.find_device() to use the scanner, [2fbb69158cc3] Allow calling send_discovery_request() without an argument; doc: API.md:59-67
**Anchor**: `tinytuya/core/XenonDevice.py:27-63` (find_device; scanner call at 44, empty-result shapes at 38 and 61-62)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `tinytuya.find_device(dev_id=None, address=None)` SHALL run the scanner in targeted mode for one Device ID or IP and return `{ip, version, id, product_id, data}`, with all-`None`/empty-data on no match (never raising).
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: broadcast-relay for broadcast-blocking networks
A companion tool SHALL listen on UDP 6666/6667/7000, track app clients that announce themselves via port-7000 broadcasts, unicast raw device broadcasts to each active app client, and age clients out after twice the 6-second broadcast period — enabling apps on WiFi networks that block broadcasts.
**Status**: VERIFIED
**Evidence**: commits [155efba4086e] Add new tool: broadcast-relay, [36e3d11a4830] broadcast-relay: no need to bind the sending socket, [b9e41462dbdf] make it work with older versions of the scanner
**Anchor**: `tools/broadcast-relay.py:6` (purpose docstring), `tools/broadcast-relay.py:44-72` (three listeners), `tools/broadcast-relay.py:110-128` (app tracking/timer), `tools/broadcast-relay.py:154` (unicast sendto), `tools/broadcast-relay.py:14` (BROADCASTTIME=6)


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** A companion tool SHALL listen on UDP 6666/6667/7000, track app clients that announce themselves via port-7000 broadcasts, unicast raw device broadcasts to each active app client, and age clients out after twice the 6-second broadcast period — enabling apps on WiFi networks that block broadcasts.
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

## Known gaps
- "Sniffer mode" and "AP-mode scan" are named as discovery-owned in the recon ownership notes, but no feature by those names exists in code at the pin. The nearest grounded behaviors are the passive-listen states (`tinytuya/scanner.py:98` `FSCAN_v31_PASSIVE_LISTEN`, used at 541-545 and 772-778) and the offline capture analyzer `tools/pcap_parse.py:283` (parses 6666/6667/7000 UDP and 6668 TCP from pcap files). Not reconstructed as requirements — anchor not located.
- DOC-vs-CODE: API.md:42,52 document `deviceScan(maxretry=15)` / `scan(maxretry=15, poll=True)`; the code defaults are `maxretry=None` (→ SCANTIME=18 s, const.py:6) and `core.scan()` has no `poll` parameter (`tinytuya/core/core.py:228`).
- MAC-address lookup via optional `getmac` is fully commented out (`tinytuya/scanner.py:1580-1587`); MAC now derives only from broadcasts, devices.json, or the 20-digit-gwId trick (`tinytuya/scanner.py:1590-1595`).
- `MAXCOUNT` is imported into the scanner (`tinytuya/scanner.py:75`) but no longer used there; retry/delay knobs that actually bind are `connect_timeout=3`, per-step `retries < 2`, and `hard_time_limit = +30 s` (`tinytuya/scanner.py:83-84`, `tinytuya/scanner.py:304`).
- PROTOCOL.md:532-534 notes the 255.255.255.255 "ip" solicitation edge case as unreliable; the scanner always sends the client's own IP and does not special-case it — undocumented in code, left as protocol trivia.
