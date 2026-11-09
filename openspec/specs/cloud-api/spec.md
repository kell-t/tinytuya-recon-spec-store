# Capability: cloud-api

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06). | Pass 3 (scenario-ification) applied 2026-11-09

## Purpose

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
The `Cloud` constructor SHALL accept `apiRegion`, `apiKey`, `apiSecret`, `apiDeviceID`, an `initial_token` from a previous run, and a configurable `configFile` (default `tinytuya.json`); when key or secret is missing it SHALL load them from that JSON file, raising `TypeError('Tuya Cloud Key and Secret required')` if neither arguments nor config supply them; when `initial_token` is supplied it SHALL skip the immediate token fetch and refresh lazily via the normal expiry path.
**Status**: VERIFIED
**Evidence**: [commit 7eba3057c485] "Load cloud config file if available"; [commit 736ba6774d88] release-notes entry adding the `configFile` option; [commit 4413314b6dc9] "Allow passing an initial token from a previous run to Cloud init"; doc: API.md § Cloud Constructor (lines 729–744)
**Anchor**: `tinytuya/Cloud.py:50`; `tinytuya/Cloud.py:96`; `tinytuya/Cloud.py:103-120`; `tinytuya/Cloud.py:124-126`; `tinytuya/core/const.py:22`

#### Scenario: Constructor with no credentials loads tinytuya.json
- **WHEN** `tinytuya.Cloud()` is constructed without key/secret arguments
- **THEN** credentials are loaded automatically from tinytuya.json
- Source: doc: API.md § Constructor "Or load credentials automatically from tinytuya.json"

#### Scenario: configFile option relocates the credentials file
- **WHEN** a `configFile` option is given to the Cloud constructor
- **THEN** the config file location used for credentials is the one specified
- **AND** the default remains 'tinytuya.json'
- Source: [relnote v1.17.4] "Add `configFile` option to the Cloud constructor, allowing users to specify the config file location (default remains 'tinytuya.json')"

### Requirement: Region-to-datacenter hostname mapping
`Cloud.setregion()` SHALL map region codes case-insensitively to the Tuya datacenter hostnames — `cn` China (default), `us`/`az` Western America, `us-e`/`ue` Eastern America, `eu` Central Europe, `eu-w`/`we` Western Europe, `in` India, `sg` Singapore — and SHALL be callable after construction to switch datacenter.
**Status**: VERIFIED
**Evidence**: [commit 1d97627875dd] "Add new Singapore datacenter to Cloud"; doc: API.md region table (lines 746–756) and `setregion` (lines 760–765); DESIGN.md line 49
**Anchor**: `tinytuya/Cloud.py:128-145`

#### Scenario: Region code selects the data center
- **WHEN** a supported region code is passed as `apiRegion`
- **THEN** requests go to that region's data center endpoint
- **AND** the supported codes include cn, us, us-e, eu, eu-w, in and sg
- Source: doc: API.md § Constructor "Region code: cn, us, us-e, eu, eu-w, in, sg"

#### Scenario: Switching datacenter after construction
- **WHEN** `setregion(apiRegion)` is called after construction
- **THEN** the client switches region/datacenter for subsequent requests
- Source: doc: API.md § setregion "Switch region after construction."
- Source: [relnote v1.2.10] "Added new data center regions for Tuya Cloud"

### Requirement: HMAC-SHA256 request signing, two algorithm generations
Every request SHALL be signed with HMAC-SHA256 keyed by the API secret, sent upper-case hex in the `sign` header with `client_id`, `t` (ms timestamp) and `sign_method: HMAC-SHA256`; the payload SHALL be `apiKey + timestamp` when no token is held (the secret also sent in a `secret` header) and `apiKey + token + timestamp` with a token; with `new_sign_algorithm` true (default) the payload SHALL also concatenate the HTTP method, body SHA-256 hex, `Signature-Headers` entries and the path.
**Status**: VERIFIED
**Evidence**: [commit 9bb3656e6421] "Fix new Tuya IoT payload signature" (the 2021-06-30 algorithm update); [commit b538f78e2bb3] original Cloud API support; doc: `tinytuya/Cloud.py:66-77` header/signature reference; DESIGN.md line 106
**Anchor**: `tinytuya/Cloud.py:195-224`; `tinytuya/Cloud.py:202-208`

#### Scenario: Every API request carries an HMAC-SHA256 signature
- **WHEN** the client makes a request to the Tuya IoT Platform
- **THEN** the request carries HMAC-SHA256 request signing over the key + token + timestamp material
- Source: doc: DESIGN.md § Cloud "HMAC-SHA256 request signing (key + token + timestamp, alphabetically sorted query params)"

### Requirement: Query-parameter signing before URL-encoding, keys sorted
When query parameters are supplied as a dict, the signature SHALL be computed over the un-encoded `key=value` pairs joined with `&` in alphabetically sorted key order, while the actual request URL is separately URL-encoded by the HTTP library; a pre-encoded query string SHALL be signed verbatim.
**Status**: VERIFIED
**Evidence**: doc: `tinytuya/Cloud.py:170` ("signature must be calculated before URL-encoding!") and `tinytuya/Cloud.py:179-180` citing Tuya's signing spec; DESIGN.md line 106 ("alphabetically sorted query params")
**Anchor**: `tinytuya/Cloud.py:169-192`

#### Scenario: Query params are signed in sorted order
- **WHEN** query parameters are supplied with a signed request
- **THEN** the signature covers the alphabetically sorted query params
- Source: doc: DESIGN.md § Cloud "alphabetically sorted query params"

### Requirement: HTTP method dispatch fidelity
`_tuyaplatform()` SHALL default the action to POST when a body is supplied and GET otherwise, SHALL accept GET/POST/PUT/DELETE, SHALL send non-GET requests with the actual HTTP method (the signature is computed over it), and SHALL set `Content-type: application/json` only for POST unless explicitly overridden.
**Status**: VERIFIED
**Evidence**: [commit 00574f78f19e] "Cloud: send PUT/DELETE with the real HTTP method"; [commit 3060e8b7f827] revert of setting Content-type on non-POST requests; [commit b077f49dd8af] Content-Type update
**Anchor**: `tinytuya/Cloud.py:163-168`; `tinytuya/Cloud.py:227-238`

#### Scenario: PUT and DELETE sent with their real HTTP method
- **WHEN** a Cloud API call requests the `PUT` or `DELETE` method
- **THEN** the request is sent with the correct HTTP method instead of being sent as `POST`
- **AND** this fixes Cloud API calls that silently failed on certain endpoints
- Source: [relnote v1.19.0] "`PUT` and `DELETE` requests now use the correct HTTP method instead of being sent as `POST`. Fixes Cloud API calls that silently failed on certain endpoints"

### Requirement: Token fetch, single-retry renewal, and server clock sync
The client SHALL obtain an OAuth token from `token?grant_type=1`, return an `ERR_CLOUDTOKEN` error dict on failure, detect the `"token invalid"` response string, renew the token and replay the original request exactly once (aborting with `None` if the renewal or second attempt fails), and — when the token response carries the server timestamp `t` — record a `server_time_offset` rounded to 120-second granularity for use in log-window time math.
**Status**: VERIFIED
**Evidence**: [commit 0a45cc9c6a1f] "Add Cloud API syncing with auto-retry"; [commit 44f52876e203] "Abort requests on token-fetch failure"; [commit 47bdc6e714b3] `_gettoken()` bug fix; [commit 0d3209d50240] token renewal logic
**Anchor**: `tinytuya/Cloud.py:243-254`; `tinytuya/Cloud.py:271-291`

#### Scenario: Expired token is detected and renewed
- **WHEN** the held token has expired
- **THEN** expiration is detected and the renewal logic renews the token
- Source: [relnote v1.3.1] "Added TuyaCloud token expiration detection and renewal logic"

#### Scenario: Token-refresh retry keeps the query string
- **WHEN** a request is replayed after a token-refresh retry
- **THEN** the retry preserves the query string of the original request
- Source: [relnote v1.20.0] "Cloud token-refresh retry preserves the query string"

### Requirement: Generic raw-endpoint request escape hatch
`cloudrequest(url, action=None, post=None, query=None)` SHALL sign and send any absolute API path (no version prefix inserted), defaulting the action to GET unless POST data is supplied, so callers can reach endpoints with no dedicated method.
**Status**: VERIFIED
**Evidence**: [commit 8393e6c71446] "Add fetching device logs to Cloud, and generic URLs"; [commit c51b4c3f4074] added the CloudRequest example; doc: API.md lines 767–772; `examples/cloudrequest.py`
**Anchor**: `tinytuya/Cloud.py:319-333`

#### Scenario: Raw request to any endpoint
- **WHEN** a caller needs an endpoint that has no dedicated method
- **THEN** `cloudrequest(url, ...)` makes a raw HTTP request to any Tuya Cloud endpoint
- **AND** custom URL and params are supported, e.g. `result = c.cloudrequest('/v1.0/devices/DEVICE_ID/logs', query={'size': 10})`
- Source: doc: API.md § cloudrequest "Make a raw HTTP request to any Tuya Cloud endpoint."
- Source: [relnote v1.8.0] "make generic cloud request with custom URL and params"

### Requirement: Full-account device listing via two endpoint strategies
`getdevices()` SHALL use the legacy user-scoped flow (`/v1.0/devices/{id}` → uid → `/v1.0/users/{uid}/devices`, supporting a comma-separated `apiDeviceID`) when an `apiDeviceID` is configured, and otherwise the keyless paginated flow — `/v1.0/iot-01/associated-users/devices` with `last_row_key` paging followed by a per-uid second fetch via `/v1.3/iot-03/devices`, merged via `_update_device_list()` to recover local keys and gateway IDs.
**Status**: VERIFIED
**Evidence**: [commit a8fff854ddcc] rework to fetch all devices without an initial Device ID; [commit 74c0b19adcc0] second fetch to ensure the local key; [commit 5afef6ebceaf]; [commit f7cf7effb24d] device-list bug fix; [commit bd8408bd9039] malformed-entry logging
**Anchor**: `tinytuya/Cloud.py:427-476`; `tinytuya/Cloud.py:352-406`; `tinytuya/Cloud.py:338-350`; `tinytuya/Cloud.py:421-422`

#### Scenario: List all registered devices
- **WHEN** `getdevices()` is called
- **THEN** it returns a list of all registered devices (name, id, key, etc.)
- Source: doc: API.md § getdevices "Return a list of all registered devices (name, id, key, etc.)"

#### Scenario: Second fetch recovers local keys
- **WHEN** the initial device-list fetch may not carry the local key
- **THEN** the device list is fetched a 2nd time to make sure we have the local key
- Source: [relnote v1.12.1] "Fetch the device list a 2nd time to make sure we have the local key"

### Requirement: Incremental device-list refresh against a previous run
`getdevices(oldlist=...)` SHALL classify each fetched device as changed (new id, changed `local_key`, newly present icon, missing mapping when `include_map` is set, or any differing `DEVICEFILE_SAVE_VALUES` field except `icon`/`last_ip`) and return freshly re-projected changed devices plus the cached unchanged entries untouched.
**Status**: VERIFIED
**Evidence**: doc: API.md line 774 (`oldlist` parameter); `tinytuya/Cloud.py:412-415` argument docstring; `tinytuya/core/const.py:27` (`DEVICEFILE_SAVE_VALUES`)
**Anchor**: `tinytuya/Cloud.py:488-515`; `tinytuya/Cloud.py:548`


#### Scenario: Conformance check (derived)
- **WHEN** the behavior described by this requirement is exercised
- **THEN** `getdevices(oldlist=...)` SHALL classify each fetched device as changed (new id, changed `local_key`, newly present icon, missing mapping when `include_map` is set, or any differing `DEVICEFILE_SAVE_VALUES` field except `icon`/`last_ip`) and return freshly re-projected changed devices plus the cache
- NOTE: SCENARIO-DEBT (derived, pass-4 conformance) — no scenario evidence in pass-3 corpus;
  replace with evidence-backed scenarios on next recon pass.

### Requirement: DP-name mapping download, caching and failure preservation
With `include_map=True`, `getdevices()` SHALL download per-product DP mappings, cache them per product id (`getmapping`/`getmappings`, preloadable via `setmappings`), treat Tuya code 2009 as a legitimately empty mapping, never overwrite a good cached mapping with an empty result, and restore the previous run's mapping only when the new one is missing or explicitly `None`.
**Status**: VERIFIED
**Evidence**: [commit 9fd5b924e0f0] new Cloud functions to download DP Name mappings; [commit cbe2ecff1d51] preserve device mappings on API failure; [commit 26e2929e0a5c] key-absence sentinel for mapping fallback; doc: API.md line 77 (`assign_dp_mappings` consumes these mappings)
**Anchor**: `tinytuya/Cloud.py:517-542`; `tinytuya/Cloud.py:853-882`; `tinytuya/Cloud.py:884-918`; `tinytuya/Cloud.py:920-942`; `tinytuya/core/core.py:155`

#### Scenario: DP Name mappings are downloaded
- **WHEN** device data is fetched with mapping download enabled
- **THEN** new Cloud functions download DP Name mappings for the devices
- Source: [relnote v1.12.8] "New Cloud functions to download DP Name mappings"

#### Scenario: Transient API failure preserves existing mappings
- **WHEN** the Cloud API fails transiently during `getdevices()`
- **THEN** device mappings are preserved so a temporary outage no longer wipes the local device map
- Source: [relnote v1.18.0] "Preserve device mappings on transient Cloud API failure in `getdevices()` so a temporary outage no longer wipes the local device map"

### Requirement: Device record projection with hardware addresses
`filter_devices()` SHALL project cloud records down to `name`/`id`/`key` (from `local_key`)/`mac` plus any present `DEVICEFILE_SAVE_VALUES` fields (icon rewritten to the region's image host) and `gateway_id`, enriching mac/uuid/sn from `/v1.0/devices/factory-infos` batched 50 device ids per request.
**Status**: VERIFIED
**Evidence**: [commit 8b0fb849d787] "Add mac address lookup from Tuya Cloud"; doc: `tinytuya/Cloud.py:547` inline comment "Filter to only Name, ID and Key"; `tinytuya/core/const.py:27`
**Anchor**: `tinytuya/Cloud.py:550-562`; `tinytuya/Cloud.py:564-602`

#### Scenario: Device list carries name, id, key and mac
- **WHEN** `getdevices()` builds the device records
- **THEN** records carry the name, id and key of each registered device
- **AND** device mac addresses are imported from the cloud (same as wizard)
- Source: doc: API.md § getdevices "Return a list of all registered devices (name, id, key, etc.)"
- Source: [relnote v1.6.1] "Fix bug in `getdevices()` to import device mac addresses (same as wizard)"

### Requirement: Per-device reads and command dispatch
The client SHALL provide `getstatus`, `getfunctions` and `getproperties` against `iot-03/devices/{id}/{status|functions|specification}`, `getdps` against the v1.1 `devices/{id}/specifications` endpoint, `sendcommand(deviceid, commands, uri='iot-03/devices/')` POSTing a commands payload, and `getconnectstatus` returning the device `online` flag; each SHALL return an `ERR_PARAMS` error dict when the device id is missing and an `ERR_CLOUD` error dict on unsuccessful cloud responses.
**Status**: VERIFIED
**Evidence**: doc: API.md lines 783–833 (method-by-method reference); [commit b538f78e2bb3] original Cloud API support
**Anchor**: `tinytuya/Cloud.py:604-642`; `tinytuya/Cloud.py:644-667`; `tinytuya/Cloud.py:669-692`; `tinytuya/Cloud.py:694-715`

#### Scenario: Read device DPS status from the cloud
- **WHEN** `getstatus(deviceid)` is called for a device
- **THEN** it returns the current DPS status of a device from the cloud
- Source: doc: API.md § getstatus "Get the current DPS status of a device from the cloud."

#### Scenario: Send commands and check online state
- **WHEN** `sendcommand(deviceid, commands)` is called with a commands payload
- **THEN** it sends one or more commands to a device
- **AND** `getconnectstatus(deviceid)` returns `True` if the device is currently online in the cloud
- Source: doc: API.md § sendcommand "Send one or more commands to a device."
- Source: doc: API.md § getconnectstatus "Return `True` if the device is currently online in the cloud."

### Requirement: Device log retrieval with paging and fetch limits
`getdevicelog()` SHALL resolve `start`/`end` as millisecond timestamps — negative values meaning "N days before now" adjusted by the synced server offset — normalize `evtype` (defaulting to all types 1–10) from str/bytes/int/list, cap each server page at 100 records, page via `next_row_key` up to `max_fetches` (default 50) accumulating logs and reporting `fetches`, and accept `start_row_key`/extra `params` pass-throughs against `/v1.0/devices/{id}/logs`.
**Status**: VERIFIED
**Evidence**: [commit 2bf893a9642b] reworked log start/end times and documentation; [commit 8393e6c71446] added log fetching; doc: API.md lines 835–857 (defaults, negative-day semantics, 100-per-fetch cap); README § Tuya Cloud Access (up to one week of logs)
**Anchor**: `tinytuya/Cloud.py:717-839`; `tinytuya/Cloud.py:841-851`

#### Scenario: Negative start means N days ago
- **WHEN** `getdevicelog()` is called with a negative `start`/`end` value
- **THEN** it is interpreted as Unix timestamp, or negative for "N days ago" (e.g. `-1` = yesterday)
- Source: doc: API.md § getdevicelog "Unix timestamp, or negative for "N days ago" (e.g. `-1` = yesterday)"

#### Scenario: Paging continues while more logs are available
- **WHEN** the cloud reports more log pages are available ("has_next" is True)
- **THEN** `getdevicelog()` handles fetching more records
- **AND** paging stops after `max_fetches` — stop after this many API calls (default 50)
- Source: [relnote v1.10.0] "Updated getdevicelog() to handle fetching more when "has_next" is True"
- Source: doc: API.md § getdevicelog "Stop after this many API calls (default 50)"

### Requirement: Errors returned as dicts with cloud error codes
Cloud methods SHALL return the shared error dict `{"Error": <text>, "Err": <code>, "Payload": <detail>}` instead of raising for operational failures, using the cloud code range 909 `ERR_CLOUDKEY` (missing/invalid credentials or unparseable response), 911 `ERR_CLOUDTOKEN` (token fetch failure), 912 `ERR_PARAMS` (missing device id/commands) and 913 `ERR_CLOUD` (unsuccessful cloud response), and SHALL return the recorded error when a method requiring a token is called with none.
**Status**: VERIFIED
**Evidence**: doc: API.md § Error Codes (lines 861–887); README § TinyTuya Error Codes (lines 277–298)
**Anchor**: `tinytuya/core/error_helper.py:17-25`; `tinytuya/core/error_helper.py:46-52`; `tinytuya/Cloud.py:278-282`; `tinytuya/Cloud.py:604-623`

#### Scenario: Operational failures return error dicts, not exceptions
- **WHEN** a Cloud helper hits a failed or empty response
- **THEN** it returns an error dict instead of raising
- **AND** functions return an error dict `{"Error": "...", "Err": "NNN", "Payload": ...}` instead of raising exceptions
- Source: [relnote v1.20.0] "Cloud helpers return error dicts instead of raising on failed/empty responses"
- Source: doc: API.md § Error Codes "Functions return an error dict `{"Error": "...", "Err": "NNN", "Payload": ...}` instead of raising exceptions."

#### Scenario: Error dict shape carries code and payload
- **WHEN** an error dict is produced for a cloud error code
- **THEN** the dict has exactly the `Error`, `Err` and `Payload` keys with the code rendered as a string (e.g. `Err` "913" for `ERR_CLOUD`)
- **AND** the payload detail passed in is preserved in `Payload`
- Source: test: tests.py::TestErrorJson::test_known_code_shape
- Source: test: tests.py::TestErrorJson::test_payload_preserved

### Requirement: Rate-limit caution for automation use
The shipped documentation SHALL warn that free Tuya Developer Trial accounts impose strict API call limits, and the client SHALL NOT enforce client-side throttling or backoff beyond its paging bounds.
**Status**: INFERRED
**Evidence**: [commit d887b06ed026] "Caution for Tuya Cloud API limits"; doc: API.md line 727 (rate-limit note); README.md line 506 (CAUTION block)
**Anchor**: anchor not located (documentation-only constraint; no client-side limiter exists in `tinytuya/Cloud.py`)

#### Scenario: Shipped docs caution against frequent automation calls
- **WHEN** a user considers automation that calls the Cloud frequently
- **THEN** the shipped documentation warns that the free Tuya Developer Trial account has strict rate limits
- **AND** the README CAUTION block states the free trial account allows a very limited number of Cloud API calls
- Source: doc: API.md § Cloud "The free Tuya Developer Trial account has strict rate limits. Avoid automation that calls the Cloud frequently."
- Source: doc: README.md § Tuya Cloud Access "The free Tuya IoT Developer (Trial) account allows a very limited number of Cloud API calls."

## Scenario-ification notes
- REQ "Incremental device-list refresh against a previous run": no doc-grounded trigger; kept as invariant. (API.md lists the `oldlist=[]` parameter but no Tier A/B/C text describes the changed-classification or unchanged-cache-return behavior.)

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
