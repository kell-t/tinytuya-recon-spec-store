# RECON_LEDGER — tinytuya

Store: `github/jasonacox/tinytuya` (id `tinytuya`). Boot order: PLAYBOOK.md → this file. License MIT; private working model; license firewall — content never leaves this store.

## CURRENT STATE (pass 1 in progress, 2026-11-09)

- Baseline pin: `master-line tag v1.20.0 @ 8512d8364a9d0e351bbec2597bafa17595545b13` (annotated tag obj 8cd2e73, published 2026-07-06). `recon/baseline.txt`. Blobless clone at `repo/` — READ-ONLY for drafting.
- History: 1,152 commits total (946 no-merge mined), 2020-09-03 .. 2026-07-02; only 4 carry `(#NNNN)` refs — evidence is docs + pin code + tests, history is intent-provenance only.
- Evidence inventory (`recon/evidence/`): `commits.json` (946), `docs/` (12 normative docs incl. PROTOCOL.md 37KB, API.md 28KB, DESIGN.md, README 60KB, AGENTS.md, Release notes inside RELEASE.md), `tests_inventory.txt` (47 defs/classes in tests.py), `bundle_<cap>.txt` ×8.
- Validation: pending first conversion. Scripts registered: `recon/scripts/mine_evidence.py` (phase 1).

## Scope decision (pass 1, 2026-11-09)

Capability decomposition (8) — decided from repo shape (docs-dense ~10.5k-LOC library; PROTOCOL.md is the authority for wire contracts):

| Capability | Owns | Primary code |
|---|---|---|
| protocol-crypto | 55AA/6699 framing, pack/unpack, CRC32/HMAC/GCM, AES-ECB/GCM, 3.4/3.5 session-key negotiation, command ids | `core/message_helper.py`, `core/crypto_helper.py`, `core/XenonDevice.py` (negotiation), `core/header.py`, `core/command_types.py`, PROTOCOL.md |
| device-control | local TCP lifecycle: connect/status/set DPS, timeouts/retries, device22 quirks, udp fallback | `core/XenonDevice.py`, `core/Device.py`, `core/udp_helper.py`, API.md |
| device-types | Outlet/Bulb/Cover + Contrib class hierarchy, DP mapping semantics | `OutletDevice.py`, `BulbDevice.py`, `CoverDevice.py`, `Contrib/*`, DP_Mapping.md |
| discovery | broadcast scan (3.1/3.4/3.5), sniffer, AP-mode scan, offline list, file outputs | `scanner.py`, `core/udp_helper.py`, DESIGN.md § Discovery |
| monitor | live device monitor, decryption modes, output formats | `core/Monitor.py`, PROTOCOL.md |
| cloud-api | Tuya cloud v1/v2 REST: signing, token/cache, device/rooms/records, config sources | `Cloud.py`, API.md § Cloud |
| cli-wizard-tools | CLI subcommands, scan/monitor/wizard entry points, MQTT server, dev tools | `cli.py`, `__main__.py`, `wizard.py`, `server/`, `tools/` |
| packaging-surface | public exports, versioning, exceptions, error strings, config file formats, install metadata | `__init__.py`, `core/__init__.py`, `core/exceptions.py`, `core/error_helper.py`, `core/const.py`, `pyproject.toml`, `setup.py` |

Rejected alternatives: per-protocol-version capabilities (framing shared; versions differ only in crypto/framing details handled inside protocol-crypto requirements); per-device-type capabilities (~20 classes too granular; one device-types cap with sub-areas); single "core" capability (density would exceed reviewable size and mix wire-contract with lifecycle); server/MQTT as separate cap (thin — folded under cli-wizard-tools with a sub-area).

Deferred buckets: `examples/` (usage demos, not behavior), `tests.py` internal fixtures beyond contract value.

## Pass history
| Date | Pass | Pin | Outcome |
|---|---|---|---|
| (in progress) | 1 | v1.20.0 @ 8512d836 | scope set; evidence mined (946 commits, 12 docs, 8 bundles) |
