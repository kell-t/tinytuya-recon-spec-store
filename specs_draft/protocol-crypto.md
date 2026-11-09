# Capability: protocol-crypto

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06).

## Summary
The wire layer: Tuya local message framing in two transports (legacy `55AA` and v3.5 `6699`), payload integrity (CRC32 or HMAC-SHA256, or the AES-GCM tag), payload encryption (AES-ECB for 3.1–3.4, AES-GCM for 3.5), and the 3-message session-key negotiation used by protocol 3.4/3.5 devices. Implementation lives in `tinytuya/core/message_helper.py` (`pack_message`/`unpack_message`), `core/crypto_helper.py` (backend-agnostic AES wrapper), `core/header.py` (format constants), `core/command_types.py` (command ids), with session negotiation inside `core/XenonDevice.py`. PROTOCOL.md is the in-repo authority for per-revision behavior.

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

### Requirement: 55AA trailer is CRC32 without a key, HMAC-SHA256 with one
For `55AA` messages the trailer SHALL be `>2I` CRC32 + suffix `0x0000AA55` when no hmac key is supplied, and `>32sI` HMAC-SHA256 + suffix when a key is supplied; unpack SHALL recompute over the header+payload span and treat a mismatch as a bad checksum.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § At a Glance (Integrity column: CRC32 for 3.1–3.3, HMAC-SHA256 for 3.4)
- Anchor: `tinytuya/core/message_helper.py:58` (`crc = hmac.new(hmac_key, data, sha256).digest()`), `:60` (`binascii.crc32(data)`), `tinytuya/core/header.py:20-21` (`MESSAGE_END_FMT` / `MESSAGE_END_FMT_HMAC`), `tinytuya/core/message_helper.py:160-165` (unpack-side recompute, `crc_good`)

### Requirement: 6699 frames require a key and use AES-GCM end-to-end
Packing or unpacking a `6699` message without a key SHALL raise `TypeError`; the payload SHALL be AES-GCM encrypted with a leading 12-byte IV, header bytes authenticated as AAD, and the GCM tag occupying the trailer slot — integrity passes iff GCM authentication succeeds.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Quick Comparison row 3.5 ("AES-GCM per packet (session key)", integrity "AES-GCM Tag")
- Anchor: `tinytuya/core/message_helper.py:37` (`TypeError('key must be provided to pack 6699-format messages')`), `:54` (GCM encrypt with `header=data[4:]`), `:117` (unpack-side `TypeError`), `:168-171` (`iv = payload[:12]`, decrypt with `tag=crc`, `crc_good = True`)

### Requirement: Malformed or truncated frames fail as DecodeError, never raw struct errors
`unpack_message` SHALL raise `DecodeError('Not enough data to unpack payload')` when the buffer is shorter than the declared length or when a corrupt frame declares a length smaller than retcode+CRC+suffix, instead of letting `struct.unpack` leak an exception.
- Status: VERIFIED
- Evidence: [commit 27aa6986ed52] hardening pass "correct 16 verified bugs across Cloud, core, Bulb, scanner, Monitor" (see code comment at anchor)
- Anchor: `tinytuya/core/message_helper.py:127-129` (short-buffer `DecodeError`), `:132-135` (declared-length sanity check)

### Requirement: Crypto backend is auto-selected from installed libraries
The AES wrapper SHALL pick the first available backend in order pyca/cryptography (version >3.0), PyCryptodomex, PyCrypto, pyaes, and SHALL raise `ModuleNotFoundError` when none is installed; GCM support SHALL be exposed as `CRYPTOLIB_HAS_GCM` (pyaes raises `NotImplementedError` for GCM).
- Status: VERIFIED
- Evidence: doc: README.md / PROTOCOL.md notes on crypto dependencies; code fallback ladder
- Anchor: `tinytuya/core/crypto_helper.py:9` (backend order tuple), `:38` (`raise ModuleNotFoundError('No crypto library found…')`), `:167` and `:181` (pyaes GCM `NotImplementedError`), `:204-214` (`CRYPTOLIB_HAS_GCM`)

### Requirement: Session key negotiation is a 3-message exchange deriving local_key = local_nonce XOR remote_nonce
For protocol 3.4/3.5, negotiation SHALL send `SESS_KEY_NEG_START`(0x03) with a fresh 16-byte random client nonce, validate the `SESS_KEY_NEG_RESP`(0x04) payload (≥48 bytes; HMAC-SHA256 over the local nonce matching bytes 16:48; for 3.4, payload first decrypted with the local key), reply `SESS_KEY_NEG_FINISH`(0x05) with HMAC over the remote nonce, and derive the session key as the 16-byte XOR of the two nonces (subsequently encrypted with the real local key).
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Version 3.4 / 3.5 (session key 3-way handshake)
- Anchor: `tinytuya/core/XenonDevice.py:893` (`_negotiate_session_key`), `:902-911` (step 1, `os.urandom(16)`), `:929-945` (len/HMAC validation), `:948` (step 3 HMAC reply), `:952-958` (XOR finalize + encrypt)

### Requirement: A fresh random client nonce per negotiation
The client nonce SHALL be generated with `os.urandom(16)` on every negotiation (not hardcoded), so the session key is not a deterministic function of the device nonce alone and 3.5 GCM IVs do not repeat across sessions; devices accept any nonce, so this stays wire-compatible.
- Status: VERIFIED
- Evidence: code comment at step 1 documenting the wire-compatibility rationale
- Anchor: `tinytuya/core/XenonDevice.py:903-908` (comment) + `:908` (`self.local_nonce = os.urandom(16)`)

### Requirement: Command ids match the Tuya LAN protocol SDK
Command ids SHALL follow the upstream Tuya embedded SDK numbering (`tuya-iotos-embeded-sdk-wifi-ble-bk7231n/lan_protocol.h`), including `CONTROL=0x07`, `DP_QUERY=0x0a`, `CONTROL_NEW=0x0d`, `DP_QUERY_NEW=0x10`, `UPDATEDPS=0x12`, session ids 0x03–0x05, `REQ_DEVINFO=0x25`, `LAN_EXT_STREAM=0x40`.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Command IDs; upstream SDK reference cited in module header
- Anchor: `tinytuya/core/command_types.py:5` (upstream reference URL), `:6-28` (id table)

### Requirement: Protocol version headers are version bytes plus 12 zero bytes
The 3.x "version header" SHALL be the version string (`b"3.3"`/`b"3.4"`/`b"3.5"`) concatenated with 12 `\x00` padding bytes; commands in `NO_PROTOCOL_HEADER_CMDS` (DP_QUERY, DP_QUERY_NEW, UPDATEDPS, HEART_BEAT, the three session-negotiation ids, LAN_EXT_STREAM) SHALL carry no protocol header.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Version Header ("3.x header")
- Anchor: `tinytuya/core/header.py:10` (`PROTOCOL_3x_HEADER = 12 * b"\x00"`), `:11-13` (33/34/35 headers), `:30` (`NO_PROTOCOL_HEADER_CMDS` list)

### Requirement: Payload suffix detection
`has_suffix(payload)` SHALL report whether a byte string contains the `55AA` message suffix (`0x0000AA55`), used to decide whether a full message has arrived.
- Status: VERIFIED
- Evidence: doc: PROTOCOL.md § Packet Framing (55AA) — suffix closes every legacy frame
- Anchor: `tinytuya/core/message_helper.py:179` (`has_suffix`), `tinytuya/core/header.py:24-25` (`SUFFIX_VALUE`/`SUFFIX_BIN`)

## Known gaps / open questions
- The 3.5 GCM AAD span is `data[4:header_len]` (header minus prefix) — whether upstream devices include the prefix in their AAD is asserted by interop, not provable from this repo at the pin (anchor `tinytuya/core/message_helper.py:171`).
- `unpack_message` logs CRC/suffix mismatches but does not hard-fail on bad CRC for 55AA (decoding proceeds; `crc_good` flag returned in the message) — where callers must treat `crc_good=False` as fatal is a device-control-layer contract, not anchored here.
- 3.2 "rare device" behaviors documented in PROTOCOL.md § Version 3.2 are handled as device22-with-3.3 in code (`tinytuya/core/XenonDevice.py:1168`); no separate 3.2 code path exists — mapping kept as doc claim.
