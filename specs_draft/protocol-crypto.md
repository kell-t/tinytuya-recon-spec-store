# Capability: protocol-crypto

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06). | Pass 3 (scenario-ification) applied 2026-11-09

## Summary
The wire layer: Tuya local message framing in two transports (legacy `55AA` and v3.5 `6699`), payload integrity (CRC32 or HMAC-SHA256, or the AES-GCM tag), payload encryption (AES-ECB for 3.1–3.4, AES-GCM for 3.5), and the 3-message session-key negotiation used by protocol 3.4/3.5 devices. Implementation lives in `tinytuya/core/message_helper.py` (`pack_message`/`unpack_message`), `tinytuya/core/crypto_helper.py` (backend-agnostic AES wrapper), `tinytuya/core/header.py` (format constants), `tinytuya/core/command_types.py` (command ids), with session negotiation inside `tinytuya/core/XenonDevice.py`. PROTOCOL.md is the in-repo authority for per-revision behavior.

## Primary code locations
- `tinytuya/core/message_helper.py` — pack/parse/unpack, suffix detection
- `tinytuya/core/header.py` — prefixes, header/end formats, protocol version bytes
- `tinytuya/core/crypto_helper.py` — crypto-library backend selection + AES-ECB/GCM
- `tinytuya/core/command_types.py` — command id constants
- `tinytuya/core/XenonDevice.py` — session-key negotiation (steps 1/3/finalize)
- `PROTOCOL.md` — per-revision framing/crypto reference

## Requirements

### Requirement: Two message transports with distinct framing
`pack_message`/`unpack_message` SHALL handle exactly two prefixes — `0x000055AA` (header `>4I`: prefix, seqno, cmd, length) and `0x00006699` (header `>IHIII`: prefix, unknown, seqno, cmd, length) — and SHALL raise for any other prefix value.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Quick Comparison (55AA legacy vs 6699 GCM transports)
- Anchor: `tinytuya/core/header.py:16` (`MESSAGE_HEADER_FMT_55AA = ">4I"`), `:17` (`MESSAGE_HEADER_FMT_6699 = ">IHIII"`), `tinytuya/core/message_helper.py:28` (prefix dispatch), `:50` (`ValueError` on unknown prefix)

#### Scenario: Transport frame chosen by protocol revision
- **WHEN** messages are packed for legacy (3.1–3.4) devices versus protocol 3.5 devices
- **THEN** legacy traffic uses the `55AA` frame and 3.5 traffic uses the `6699` (GCM) frame — the 6699 frame replaces 55AA for data
- Source: doc: PROTOCOL.md § Key Changes vs 3.4 "6699 frame replaces 55AA for data"
- Source: doc: DESIGN.md § Protocol Versions "3.5 | 6699 | AES-GCM tag | AES-GCM, 12-byte IV, retcode inside ciphertext"

### Requirement: 55AA trailer is CRC32 without a key, HMAC-SHA256 with one
For `55AA` messages the trailer SHALL be `>2I` CRC32 + suffix `0x0000AA55` when no hmac key is supplied, and `>32sI` HMAC-SHA256 + suffix when a key is supplied; unpack SHALL recompute over the header+payload span and treat a mismatch as a bad checksum.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § At a Glance (Integrity column: CRC32 for 3.1–3.3, HMAC-SHA256 for 3.4)
- Anchor: `tinytuya/core/message_helper.py:58` (`crc = hmac.new(hmac_key, data, sha256).digest()`), `:60` (`binascii.crc32(data)`), `tinytuya/core/header.py:20-21` (`MESSAGE_END_FMT` / `MESSAGE_END_FMT_HMAC`), `tinytuya/core/message_helper.py:160-165` (unpack-side recompute, `crc_good`)

#### Scenario: 55AA trailer is CRC32 when no HMAC key is used (3.1–3.3)
- **WHEN** a 55AA message is framed for a 3.2/3.3 device (no session/HMAC key)
- **THEN** the integrity field is a 32-bit CRC32 of everything from prefix through final payload byte
- **AND** on receive, `unpack_message()` verifies integrity before the payload is used
- Source: doc: PROTOCOL.md § Packet Format (55AA, v3.2–v3.4) "32-bit CRC32 of everything from prefix through final payload byte"
- Source: doc: DESIGN.md § Message Flow "unpack_message() verifies integrity"

#### Scenario: 55AA trailer is HMAC-SHA256 when a key is supplied (3.4)
- **WHEN** a 55AA message is framed for a v3.4 device after session-key negotiation
- **THEN** the integrity field is a 32-byte HMAC-SHA256 over prefix, optional retcode and ciphertext with the session key as HMAC key
- Source: doc: PROTOCOL.md § Packet Format (55AA, v3.2–v3.4) "32-byte HMAC-SHA256 over prefix..retcode(optional)..ciphertext (session key as HMAC key)"

### Requirement: 6699 frames require a key and use AES-GCM end-to-end
Packing or unpacking a `6699` message without a key SHALL raise `TypeError`; the payload SHALL be AES-GCM encrypted with a leading 12-byte IV, header bytes authenticated as AAD, and the GCM tag occupying the trailer slot — integrity passes iff GCM authentication succeeds.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Quick Comparison row 3.5 ("AES-GCM per packet (session key)", integrity "AES-GCM Tag")
- Anchor: `tinytuya/core/message_helper.py:37` (`TypeError('key must be provided to pack 6699-format messages')`), `:54` (GCM encrypt with `header=data[4:]`), `:117` (unpack-side `TypeError`), `:168-171` (`iv = payload[:12]`, decrypt with `tag=crc`, `crc_good = True`)

#### Scenario: 6699 payload is AES-GCM end-to-end
- **WHEN** a 6699 data message is packed for a v3.5 device
- **THEN** the payload is AES-GCM encrypted with a leading 12-byte IV/nonce, the header fields are only authenticated (AAD from after the prefix up to the IV), and a 16-byte AES-GCM authentication tag precedes the footer
- Source: doc: PROTOCOL.md § Packet Format (6699, v3.5) "12-byte IV / nonce (unique per packet) ... 16-byte AES-GCM authentication Tag ... header fields are only authenticated"

#### Scenario: A 6699 frame failing its GCM tag is rejected
- **WHEN** a received 6699/GCM frame fails its authentication tag verification
- **THEN** the frame is rejected instead of being passed on as raw ciphertext
- **AND** the receive path raises `DecodeError` for a frame with a corrupted tag
- Source: [relnote v1.20.0] "6699/GCM frames that fail their authentication tag are rejected instead of being passed on as raw ciphertext"
- Source: test: tests.py::TestSessionCrypto::test_receive_rejects_gcm_auth_failure

### Requirement: Malformed or truncated frames fail as DecodeError, never raw struct errors
`unpack_message` SHALL raise `DecodeError('Not enough data to unpack payload')` when the buffer is shorter than the declared length or when a corrupt frame declares a length smaller than retcode+CRC+suffix, instead of letting `struct.unpack` leak an exception.
- Status: VERIFIED
- Evidence: [commit 27aa6986ed52] hardening pass "correct 16 verified bugs across Cloud, core, Bulb, scanner, Monitor" (see code comment at anchor)
- Anchor: `tinytuya/core/message_helper.py:127-129` (short-buffer `DecodeError`), `:132-135` (declared-length sanity check)

#### Scenario: Truncated frames raise DecodeError
- **WHEN** an inbound buffer is shorter than the frame's declared length (a truncated frame)
- **THEN** unpacking raises `DecodeError`
- Source: [relnote v1.20.0] "truncated frames raise DecodeError"

#### Scenario: Absurd declared length from a corrupt stream is rejected
- **WHEN** a parsed header declares a payload larger than `MAX_PAYLOAD_LENGTH` (absurd sizes from a corrupt or desynced stream)
- **THEN** parsing rejects the frame with `DecodeError`
- Source: doc: DESIGN.md § Message Flow "parse_header() yields total length (bounded by MAX_PAYLOAD_LENGTH)"
- Source: test: tests.py::TestParseHeader::test_oversized_payload_rejected

### Requirement: Crypto backend is auto-selected from installed libraries
The AES wrapper SHALL pick the first available backend in order pyca/cryptography (version >3.0), PyCryptodomex, PyCrypto, pyaes, and SHALL raise `ModuleNotFoundError` when none is installed; GCM support SHALL be exposed as `CRYPTOLIB_HAS_GCM` (pyaes raises `NotImplementedError` for GCM).
- Status: VERIFIED
- Evidence: doc: README.md / PROTOCOL.md notes on crypto dependencies; code fallback ladder
- Anchor: `tinytuya/core/crypto_helper.py:9` (backend order tuple), `:38` (`raise ModuleNotFoundError('No crypto library found…')`), `:167` and `:181` (pyaes GCM `NotImplementedError`), `:204-214` (`CRYPTOLIB_HAS_GCM`)

#### Scenario: Crypto backend selected at import time
- **WHEN** the library initializes at import time
- **THEN** `tinytuya/core/crypto_helper.py` selects the first available backend pyca/cryptography → PyCryptodome(x) → PyCrypto → pyaes and wraps whichever it finds in a single `AESCipher` class
- Source: doc: DESIGN.md § Key Design Decisions "selects pyca/cryptography → PyCryptodome(x) → PyCrypto → pyaes at import time and wraps whichever it finds in a single AESCipher class"

#### Scenario: pyaes backend cannot serve v3.5 devices
- **WHEN** only pyaes is installed and the device requires Tuya Protocol 3.5
- **THEN** it will not work: pyaes does not support GCM which is required for v3.5 devices, and protocol 3.5 support is gated on `CRYPTOLIB_HAS_GCM`
- Source: doc: README.md § Encryption Notes "pyaes does not support GCM which is required for v3.5 devices"
- Source: doc: DESIGN.md § Key Design Decisions "pyaes has no GCM, so protocol 3.5 support is gated on CRYPTOLIB_HAS_GCM"

### Requirement: Session key negotiation is a 3-message exchange deriving local_key = local_nonce XOR remote_nonce
For protocol 3.4/3.5, negotiation SHALL send `SESS_KEY_NEG_START`(0x03) with a fresh 16-byte random client nonce, validate the `SESS_KEY_NEG_RESP`(0x04) payload (≥48 bytes; HMAC-SHA256 over the local nonce matching bytes 16:48; for 3.4, payload first decrypted with the local key), reply `SESS_KEY_NEG_FINISH`(0x05) with HMAC over the remote nonce, and derive the session key as the 16-byte XOR of the two nonces (subsequently encrypted with the real local key).
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Version 3.4 / 3.5 (session key 3-way handshake)
- Anchor: `tinytuya/core/XenonDevice.py:893` (`_negotiate_session_key`), `:902-911` (step 1, `os.urandom(16)`), `:929-945` (len/HMAC validation), `:948` (step 3 HMAC reply), `:952-958` (XOR finalize + encrypt)

#### Scenario: Session key handshake precedes data commands (3.4/3.5)
- **WHEN** the client starts communicating with a protocol 3.4/3.5 device
- **THEN** a 3-way handshake runs — `SESS_KEY_NEG_START` (0x03) carrying the 16-byte client nonce, `SESS_KEY_NEG_RESP` (0x04) carrying the device nonce plus HMAC-SHA256(client_nonce), `SESS_KEY_NEG_FINISH` (0x05) carrying HMAC-SHA256(device_nonce)
- **AND** both sides derive the session key from the XOR of client_nonce and device_nonce encrypted with the real local key (3.4: AES-ECB; 3.5: GCM derivation slice)
- Source: doc: PROTOCOL.md § Key Changes vs 3.3 "Session key negotiation (3-way handshake) precedes data commands"
- Source: doc: PROTOCOL.md § Session Key Handshake "Both sides derive session_key = AES_ECB_realKey( client_nonce XOR device_nonce )"
- Source: doc: PROTOCOL.md § Session Key Handshake "session_key = GCM_Derive( XOR(client_nonce, device_nonce) )"

#### Scenario: Device handshake HMAC validated before FINISH
- **WHEN** the `SESS_KEY_NEG_RESP` (step 2) payload arrives
- **THEN** the client recomputes HMAC(client_nonce) using real key and compares to bytes 16..48 of the decrypted step 2 payload; if valid, it sends step 3 and both sides derive the session key
- Source: doc: PROTOCOL.md § Session Key (Detailed) "Client recomputes HMAC(client_nonce) using real key and compares to bytes 16..48 of the decrypted step 2 payload. If valid, it sends step 3 and both sides derive the session key"

### Requirement: A fresh random client nonce per negotiation
The client nonce SHALL be generated with `os.urandom(16)` on every negotiation (not hardcoded), so the session key is not a deterministic function of the device nonce alone and 3.5 GCM IVs do not repeat across sessions; devices accept any nonce, so this stays wire-compatible.
- Status: VERIFIED
- Evidence: code comment at step 1 documenting the wire-compatibility rationale
- Anchor: `tinytuya/core/XenonDevice.py:903-908` (comment) + `:908` (`self.local_nonce = os.urandom(16)`)

#### Scenario: Client nonce comes from os.urandom, eliminating nonce reuse
- **WHEN** session-key negotiation step 1 generates the v3.4/v3.5 client nonce
- **THEN** it uses `os.urandom` instead of a time-derived/constant value, eliminating nonce/IV reuse under a session key
- **AND** the change stays wire-compatible
- Source: [relnote v1.20.0] "the v3.4/v3.5 session-key client nonce now use os.urandom instead of a time-derived/constant value, eliminating nonce/IV reuse under a session key. Wire-compatible"

#### Scenario: Two successive negotiations produce different 16-byte nonces
- **WHEN** step 1 of session-key negotiation runs twice in a row
- **THEN** each run produces a fresh 16-byte client nonce and the two nonces differ between negotiations
- Source: test: tests.py::TestSessionCrypto::test_client_nonce_is_random_and_16_bytes

### Requirement: Command ids match the Tuya LAN protocol SDK
Command ids SHALL follow the upstream Tuya embedded SDK numbering (`tuya-iotos-embeded-sdk-wifi-ble-bk7231n/lan_protocol.h`), including `CONTROL=0x07`, `DP_QUERY=0x0a`, `CONTROL_NEW=0x0d`, `DP_QUERY_NEW=0x10`, `UPDATEDPS=0x12`, session ids 0x03–0x05, `REQ_DEVINFO=0x25`, `LAN_EXT_STREAM=0x40`.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Command IDs; upstream SDK reference cited in module header
- Anchor: `tinytuya/core/command_types.py:5` (upstream reference URL), `:6-28` (id table)

#### Scenario: device22 DP query uses CONTROL_NEW (0x0D)
- **WHEN** a device22 requires an explicit DPS list for its DP query
- **THEN** the DP_QUERY is sent using command ID 0x0D (CONTROL_NEW)
- Source: doc: PROTOCOL.md § Device22 Behavior "DP_QUERY uses command ID 0x0D"
- Source: doc: PROTOCOL.md § Command IDs (subset) "CONTROL_NEW New control frame (used for device22 + 3.4+ override)"

#### Scenario: v3.5 discovery solicitation uses REQ_DEVINFO (0x25)
- **WHEN** a client solicits newer v3.5 devices with a broadcast on UDP port 7000
- **THEN** the solicitation is a single 6699-format AES-GCM packet with command ID 0x25 REQ_DEVINFO
- Source: doc: PROTOCOL.md § Command IDs (subset) "REQ_DEVINFO Discovery solicitation request (UDP/7000, v3.5)"
- Source: doc: PROTOCOL.md § Discovery Packets Redux "Send a single 6699-format AES-GCM packet (same key rules) via UDP to the subnet broadcast"

### Requirement: Protocol version headers are version bytes plus 12 zero bytes
The 3.x "version header" SHALL be the version string (`b"3.3"`/`b"3.4"`/`b"3.5"`) concatenated with 12 `\x00` padding bytes; commands in `NO_PROTOCOL_HEADER_CMDS` (DP_QUERY, DP_QUERY_NEW, UPDATEDPS, HEART_BEAT, the three session-negotiation ids, LAN_EXT_STREAM) SHALL carry no protocol header.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Version Header ("3.x header")
- Anchor: `tinytuya/core/header.py:10` (`PROTOCOL_3x_HEADER = 12 * b"\x00"`), `:11-13` (33/34/35 headers), `:30` (`NO_PROTOCOL_HEADER_CMDS` list)

#### Scenario: Version header layout
- **WHEN** a 3.x protocol header is prepended to a payload
- **THEN** it is the ASCII version followed by 12 zero bytes — `<ascii version><12 x 0x00>`
- **AND** its presence differs by version and command
- Source: doc: PROTOCOL.md § Version Header "ascii version><12 x 0x00"

#### Scenario: Skip-list commands carry no version header
- **WHEN** the command is DP_QUERY, DP_QUERY_NEW, UPDATEDPS, HEART_BEAT, a session-negotiation command, or LAN_EXT_STREAM
- **THEN** the message is sent without the 3.x version header (but encryption still applies)
- Source: doc: PROTOCOL.md § Version Header "skipped for DP_QUERY, DP_QUERY_NEW, UPDATEDPS, HEART_BEAT, session negotiation, LAN_EXT_STREAM"
- Source: doc: DESIGN.md § Protocol Versions "skip the 3.x version header but not encryption"

### Requirement: Payload suffix detection
`has_suffix(payload)` SHALL report whether a byte string contains the `55AA` message suffix (`0x0000AA55`), used to decide whether a full message has arrived.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Packet Framing (55AA) — suffix closes every legacy frame
- Anchor: `tinytuya/core/message_helper.py:179` (`has_suffix`), `tinytuya/core/header.py:24-25` (`SUFFIX_VALUE`/`SUFFIX_BIN`)

## Known gaps / open questions
- The 3.5 GCM AAD span is `data[4:header_len]` (header minus prefix) — whether upstream devices include the prefix in their AAD is asserted by interop, not provable from this repo at the pin (anchor `tinytuya/core/message_helper.py:171`).
- `unpack_message` logs CRC/suffix mismatches but does not hard-fail on bad CRC for 55AA (decoding proceeds; `crc_good` flag returned in the message) — where callers must treat `crc_good=False` as fatal is a device-control-layer contract, not anchored here.
- 3.2 "rare device" behaviors documented in PROTOCOL.md § Version 3.2 are handled as device22-with-3.3 in code (`tinytuya/core/XenonDevice.py:1168`); no separate 3.2 code path exists — mapping kept as doc claim.

## Scenario-ification notes
- REQ "Payload suffix detection": no doc-grounded trigger; kept as invariant. (Docs record the `0000aa55` footer closing every 55AA frame — PROTOCOL.md § Packet Framing — but no Tier A/B/C text documents `has_suffix()`'s trigger, i.e. using the suffix to decide whether a full message has arrived; that purpose comes from code usage only.)
- Pass-3 summary: 17 grounded scenarios added across 9 requirements; 1 requirement left property-style (above).
- Doc-vs-requirement flag (not fixed): REQ "55AA trailer is CRC32 without a key, HMAC-SHA256 with one" frames the switch as "when a hmac key is supplied", while PROTOCOL.md keys HMAC-SHA256 to protocol v3.4 itself ("CRC32 replaced by HMAC-SHA256", session key as HMAC key) — behaviorally consistent, framing differs; scenarios follow the version-keyed doc wording.
