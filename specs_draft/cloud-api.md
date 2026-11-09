# Capability: cloud-api

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06).

## Summary

This capability is the Tuya IoT Platform REST client: `tinytuya/Cloud.py` implements a self-contained signed-HTTPS client (HMAC-SHA256 request signing in two generations, OAuth token fetch/refresh with server-clock sync) plus helpers for device lists, per-device status/function/DPS reads, command dispatch, DP-name mappings and paginated event logs. Credentials come from constructor arguments or the `tinytuya.json` config file. `tinytuya/core/error_helper.py` supplies the shared error-dict contract; `tinytuya/core/core.py` adds `assign_dp_mappings()` for attaching cloud-downloaded mappings to device lists. Docs authority: API.md § Cloud, DESIGN.md § Cloud, README § Tuya Cloud Access.

## Primary code locations
- `tinytuya/Cloud.py` — the entire `Cloud` class: signing, token lifecycle, endpoints, device list, mappings, logs.
- `tinytuya/core/error_helper.py` — cloud error codes (909–913) and the `error_json()` dict contract.
- `tinytuya/core/const.py` — `CONFIGFILE` default and `DEVICEFILE_SAVE_VALUES` fields persisted from the cloud record.
- `tinytuya/core/core.py` — `assign_dp_mappings()` helper operating on `getdevices()` output.
- `tinytuya/__init__.py` — top-level export of `Cloud`.
- `API.md` § Cloud — user-facing method reference; `DESIGN.md` § Cloud — architecture intent; `README.md` § Tuya Cloud Access — rate-limit caution and usage.

## Requirements

### Requirement: Credential sourcing with config-file fallback and token reuse
The `Cloud` constructor SHALL accept `apiRegion`, `apiKey`, `apiSecret`, `apiDeviceID`, an `initial_token` from a previous run, and a configurable `configFile` (default `tinytuya.json`); when key or secret is missing it SHALL load `apiRegion`/`apiKey`/`apiSecret`/optional `apiDeviceID` from that JSON file, raising `TypeError('Tuya Cloud Key and Secret required')` (with an `ERR_CLOUDKEY` error payload recorded on the instance) if neither arguments nor config supply them; when `initial_token` is supplied it SHALL skip the immediate token fetch and let the normal expiry path refresh it lazily on the first request that reports the token invalid.
- Status: VERIFIED
- Evidence: [commit 7eba3057c485] "Load cloud config file if available"; [commit 736ba6774d88] release-notes entry adding the `configFile` option; [commit 4413314b6dc9] "Allow passing an initial token from a previous run to Cloud init"; doc: API.md § Cloud Constructor (lines 729–744)
- Anchor: `tinytuya/Cloud.py:50`; `tinytuya/Cloud.py:96`; `tinytuya/Cloud.py:103-120`; `tinytuya/Cloud.py:124-126`; `tinytuya/core/const.py:22`

### Requirement: Region-to-datacenter hostname mapping
`Cloud.setregion()` SHALL map region codes case-insensitively to the Tuya datacenter hostnames — `cn` China (default), `us`/`az` Western America, `us-e`/`ue` Eastern America, `eu` Central Europe, `eu-w`/`we` Western Europe, `in` India, `sg` Singapore — and SHALL be callable after construction to switch datacenter.
- Status: VERIFIED
- Evidence: [commit 1d97627875dd] "Add new Singapore datacenter to Cloud"; doc: API.md region table (lines 746–756) and `setregion` (lines 760–765); DESIGN.md line 49
- Anchor: `tinytuya/Cloud.py:128-145`

### Requirement: HMAC-SHA256 request signing, two algorithm generations
Every request SHALL be signed with HMAC-SHA256 keyed by the API secret and sent upper-case hex in the `sign` header together with `client_id`, `t` (13-bit ms timestamp) and `sign_method: HMAC-SHA256`; with no token the signed payload SHALL be `apiKey + timestamp` and the secret additionally sent as a `secret` header, and with a token the payload SHALL be `apiKey + token + timestamp`; when `new_sign_algorithm` is true (the default) the payload SHALL additionally concatenate the HTTP method, SHA-256 hex of the body, the `Signature-Headers` entries and the request path, per the post-June-2021 Tuya signing update.
- Status: VERIFIED
- Evidence: [commit 9bb3656e6421] "Fix new Tuya IoT payload signature" (the 2021-06-30 algorithm update); [commit b538f78e2bb3] original Cloud API support; doc: `tinytuya/Cloud.py:66-77` header/signature reference; DESIGN.md line 106
- Anchor: `tinytuya/Cloud.py:195-224`; `tinytuya/Cloud.py:202-208`

### Requirement: Query-parameter signing before URL-encoding, keys sorted
When query parameters are supplied as a dict, the signature SHALL be computed over the un-encoded `key=value` pairs joined with `&` in alphabetically sorted key order, while the actual request URL is separately URL-encoded by the HTTP library; a pre-encoded query string SHALL be signed verbatim.
- Status: VERIFIED
- Evidence: doc: `tinytuya/Cloud.py:170` ("signature must be calculated before URL-encoding!") and `tinytuya/Cloud.py:179-180` citing Tuya's signing spec; DESIGN.md line 106 ("alphabetically sorted query params")
- Anchor: `tinytuya/Cloud.py:169-192`

### Requirement: HTTP method dispatch fidelity
`_tuyaplatform()` SHALL default the action to POST when a body is supplied and GET otherwise, SHALL accept GET/POST/PUT/DELETE, SHALL send non-GET requests with the actual HTTP method (the signature is computed over it), and SHALL set `Content-type: application/json` only for POST unless explicitly overridden.
- Status: VERIFIED
- Evidence: [commit 00574f78f19e] "Cloud: send PUT/DELETE with the real HTTP method"; [commit 3060e8b7f827] revert of setting Content-type on non-POST requests; [commit b077f49dd8af] Content-Type update
- Anchor: `tinytuya/Cloud.py:163-168`; `tinytuya/Cloud.py:227-238`

### Requirement: Token fetch, single-retry renewal, and server clock sync
The client SHALL obtain an OAuth token from `token?grant_type=1`, return an `ERR_CLOUDTOKEN` error dict on failure, detect the `"token invalid"` response string, renew the token and replay the original request exactly once (aborting with `None` if the renewal or second attempt fails), and — when the token response carries the server timestamp `t` — record a `server_time_offset` rounded to 120-second granularity for use in log-window time math.
- Status: VERIFIED
- Evidence: [commit 0a45cc9c6a1f] "Add Cloud API syncing with auto-retry"; [commit 44f52876e203] "Abort requests on token-fetch failure"; [commit 47bdc6e714b3] `_gettoken()` bug fix; [commit 0d3209d50240] token renewal logic
- Anchor: `tinytuya/Cloud.py:243-254`; `tinytuya/Cloud.py:271-291`

### Requirement: Generic raw-endpoint request escape hatch
`cloudrequest(url, action=None, post=None, query=None)` SHALL sign and send any absolute API path (no version prefix inserted), defaulting the action to GET unless POST data is supplied, so callers can reach endpoints with no dedicated method.
- Status: VERIFIED
- Evidence: [commit 8393e6c71446] "Add fetching device logs to Cloud, and generic URLs"; [commit c51b4c3f4074] added the CloudRequest example; doc: API.md lines 767–772; `examples/cloudrequest.py`
- Anchor: `tinytuya/Cloud.py:319-333`

### Requirement: Full-account device listing via two endpoint strategies
`getdevices()` SHALL use the legacy user-scoped flow (`/v1.0/devices/{id}` → uid → `/v1.0/users/{uid}/devices`, supporting a comma-separated `apiDeviceID`) when an `apiDeviceID` is configured, and otherwise the keyless paginated flow — `/v1.0/iot-01/associated-users/devices` (size 50, `last_row_key` paging) followed by a per-uid second fetch via `/v1.3/iot-03/devices` (page size 75) merged with `_update_device_list()` to recover local keys and gateway IDs; malformed entries in `oldlist` SHALL be logged and skipped.
- Status: VERIFIED
- Evidence: [commit a8fff854ddcc] rework to fetch all devices without an initial Device ID; [commit 74c0b19adcc0] second fetch to ensure the local key; [commit 5afef6ebceaf]; [commit f7cf7effb24d] device-list bug fix; [commit bd8408bd9039] malformed-entry logging
- Anchor: `tinytuya/Cloud.py:427-476`; `tinytuya/Cloud.py:352-406`; `tinytuya/Cloud.py:338-350`; `tinytuya/Cloud.py:421-422`

### Requirement: Incremental device-list refresh against a previous run
`getdevices(oldlist=...)` SHALL classify each fetched device as changed (new id, changed `local_key`, newly present icon, missing mapping when `include_map` is set, or any differing `DEVICEFILE_SAVE_VALUES` field except `icon`/`last_ip`) and return freshly re-projected changed devices plus the cached unchanged entries untouched.
- Status: VERIFIED
- Evidence: doc: API.md line 774 (`oldlist` parameter); `tinytuya/Cloud.py:412-415` argument docstring; `tinytuya/core/const.py:27` (`DEVICEFILE_SAVE_VALUES`)
- Anchor: `tinytuya/Cloud.py:488-515`; `tinytuya/Cloud.py:548`

### Requirement: DP-name mapping download, caching and failure preservation
With `include_map=True`, `getdevices()` SHALL download per-product DP mappings (merging the v1.1 `specifications` status and functions sets, normalizing unicode/temperature units and preserving raw JSON values), cache them per product id (`getmapping`/`getmappings`, preloadable via `setmappings`), treat Tuya code 2009 / "not support this device" as a legitimately empty mapping, never overwrite a good cached mapping with an empty result, and restore the previous run's mapping only when the new one is missing or explicitly `None` (key-absence sentinel).
- Status: VERIFIED
- Evidence: [commit 9fd5b924e0f0] new Cloud functions to download DP Name mappings; [commit cbe2ecff1d51] preserve device mappings on API failure; [commit 26e2929e0a5c] key-absence sentinel for mapping fallback; doc: API.md line 77 (`assign_dp_mappings` consumes these mappings)
- Anchor: `tinytuya/Cloud.py:517-542`; `tinytuya/Cloud.py:853-882`; `tinytuya/Cloud.py:884-918`; `tinytuya/Cloud.py:920-942`; `tinytuya/core/core.py:155`

### Requirement: Device record projection with hardware addresses
`filter_devices()` SHALL project cloud records down to `name`/`id`/`key` (from `local_key`)/`mac` plus any present `DEVICEFILE_SAVE_VALUES` fields (icon rewritten to the region's image host) and `gateway_id`, enriching mac/uuid/sn from `/v1.0/devices/factory-infos` batched 50 device ids per request.
- Status: VERIFIED
- Evidence: [commit 8b0fb849d787] "Add mac address lookup from Tuya Cloud"; doc: `tinytuya/Cloud.py:547` inline comment "Filter to only Name, ID and Key"; `tinytuya/core/const.py:27`
- Anchor: `tinytuya/Cloud.py:550-562`; `tinytuya/Cloud.py:564-602`

### Requirement: Per-device reads and command dispatch
The client SHALL provide `getstatus`, `getfunctions` and `getproperties` against `iot-03/devices/{id}/{status|functions|specification}`, `getdps` against the v1.1 `devices/{id}/specifications` endpoint, `sendcommand(deviceid, commands, uri='iot-03/devices/')` POSTing a commands payload with an overridable URI, and `getconnectstatus` returning the device `online` flag — each returning an `ERR_PARAMS` error dict when the device id is missing and an `ERR_CLOUD` error dict when the cloud response is unsuccessful.
- Status: VERIFIED
- Evidence: doc: API.md lines 783–833 (method-by-method reference); [commit b538f78e2bb3] original Cloud API support
- Anchor: `tinytuya/Cloud.py:604-642`; `tinytuya/Cloud.py:644-667`; `tinytuya/Cloud.py:669-692`; `tinytuya/Cloud.py:694-715`

### Requirement: Device log retrieval with paging and fetch limits
`getdevicelog()` SHALL resolve `start`/`end` as millisecond timestamps — negative values meaning "N days before now" adjusted by the synced server offset — normalize `evtype` (defaulting to all types 1–10) from str/bytes/int/list, cap each server page at 100 records, page via `next_row_key` up to `max_fetches` (default 50) accumulating logs and reporting `fetches`, and accept `start_row_key`/extra `params` pass-throughs against `/v1.0/devices/{id}/logs`.
- Status: VERIFIED
- Evidence: [commit 2bf893a9642b] reworked log start/end times and documentation; [commit 8393e6c71446] added log fetching; doc: API.md lines 835–857 (defaults, negative-day semantics, 100-per-fetch cap); README § Tuya Cloud Access (up to one week of logs)
- Anchor: `tinytuya/Cloud.py:717-839`; `tinytuya/Cloud.py:841-851`

### Requirement: Errors returned as dicts with cloud error codes
Cloud methods SHALL return the shared error dict `{"Error": <text>, "Err": <code>, "Payload": <detail>}` instead of raising for operational failures, using the cloud code range 909 `ERR_CLOUDKEY` (missing/invalid credentials or unparseable response), 911 `ERR_CLOUDTOKEN` (token fetch failure), 912 `ERR_PARAMS` (missing device id/commands) and 913 `ERR_CLOUD` (unsuccessful cloud response), and SHALL return the recorded error when a method requiring a token is called with none.
- Status: VERIFIED
- Evidence: doc: API.md § Error Codes (lines 861–887); README § TinyTuya Error Codes (lines 277–298)
- Anchor: `tinytuya/core/error_helper.py:17-25`; `tinytuya/core/error_helper.py:46-52`; `tinytuya/Cloud.py:278-282`; `tinytuya/Cloud.py:604-623`

### Requirement: Rate-limit caution for automation use
The library SHOULD steer users away from frequent cloud polling by documenting that free Tuya Developer Trial accounts impose strict API call limits, rather than enforcing client-side throttling.
- Status: INFERRED
- Evidence: [commit d887b06ed026] "Caution for Tuya Cloud API limits"; doc: API.md line 727 (rate-limit note); README.md line 506 (CAUTION block)
- Anchor: anchor not located (documentation-only constraint; no client-side limiter exists in `tinytuya/Cloud.py`)

## Known gaps / open questions
- DOC/CODE DRIFT — error code 910 `ERR_CLOUDRESP` ("Invalid JSON Response from Cloud") is defined (`tinytuya/core/error_helper.py:20`) and listed in the README and API.md error tables, but `tinytuya/Cloud.py` never emits it: the unparseable-cloud-response path returns `ERR_CLOUDKEY` (909) instead (`tinytuya/Cloud.py:263-267`).
- DOC/CODE DRIFT — the `tinytuya/Cloud.py` module docstring header lists `cloudrequest(url, action=[POST if post else GET], post={}, query={})` (`tinytuya/Cloud.py:15`, repeated in README's Cloud Functions list) while the real signature defaults are `action=None, post=None` (`tinytuya/Cloud.py:319`) — `post={}` would wrongly flip the method to POST for an empty body.
- DOC/CODE DRIFT — the module docstring documents `getdevicelog(..., evtype="1,2,3,4,5,6,7,8,9,10", size=100, params={})` (`tinytuya/Cloud.py:23`) but the actual defaults are `evtype=None, size=0` and the signature adds `max_fetches=50` and `start_row_key=None` (`tinytuya/Cloud.py:717`); README's Cloud Functions list shows `size=0` and `max_fetches` but still omits `start_row_key`.
- DOC/CODE DRIFT — public mapping methods `getmapping()`, `getmappings()` and `setmappings()` (`tinytuya/Cloud.py:884-942`, added by [commit 9fd5b924e0f0]) appear in no doc at this pin: API.md § Cloud documents only the `include_map` flag of `getdevices()` (API.md line 774), and the module docstring header function list (lines 13–23) omits them too.
- DOC/CODE DRIFT — constructor docstring lists example regions "e.g., 'us', 'eu', 'cn', 'in'" (`tinytuya/Cloud.py:55`) — missing `us-e`/`eu-w`/`sg` and the `az`/`ue`/`we` aliases that API.md's table (lines 746–756) and the code (lines 134–145) both support; any unrecognized region code silently falls back to the China host `openapi.tuyacn.com` with no validation error (`tinytuya/Cloud.py:133`).
- DOC/CODE DRIFT — `getdevices()` docstring says "Return dictionary of all devices" (`tinytuya/Cloud.py:410`) while the non-verbose path returns a list of device dicts (`tinytuya/Cloud.py:548`); API.md correctly documents a list.
- Undocumented-in-code URI reference: the class docstring lists only v1.0 token/device URIs (`tinytuya/Cloud.py:80-82`) while the default keyless device fetch uses `/v1.3/iot-03/devices` for the per-uid pass (`tinytuya/Cloud.py:363`) — version mix documented only as inline doc links (`tinytuya/Cloud.py:362`, `tinytuya/Cloud.py:372`).
- Robustness gap — `getconnectstatus()` indexes `response_dict["result"]["online"]` unguarded (`tinytuya/Cloud.py:715`), so a successful-but-malformed payload raises `KeyError` instead of returning the error-dict contract every other method follows.
- No client-side rate limiting or backoff exists anywhere in `tinytuya/Cloud.py`, despite the trial-account cautions in README (line 506) and API.md (line 727) and the historical limits issue ([commit d887b06ed026]); only `max_fetches` bounds per-call paging (`tinytuya/Cloud.py:785-786`).
- The `requests` dependency is imported optionally with a printed WARN and late `NameError`-style breakage rather than a guarded failure (`tinytuya/Cloud.py:36-41`); README line 57 marks it required-for-cloud, but no code path converts the missing dependency into an `error_json` — behavior on a machine without `requests` was not executed here.
