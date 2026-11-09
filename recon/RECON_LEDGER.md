# RECON_LEDGER — tinytuya

Store: `github/jasonacox/tinytuya` (id `tinytuya`). Boot order: PLAYBOOK.md → this file. License MIT; private working model; license firewall — content never leaves this store.

## CURRENT STATE (pass 1 COMPLETE, 2026-11-09)

- Baseline pin: `master-line tag v1.20.0 @ 8512d8364a9d0e351bbec2597bafa17595545b13` (annotated tag obj 8cd2e73, published 2026-07-06). `recon/baseline.txt`. Blobless clone at `repo/` — READ-ONLY for drafting.
- Validation: `openspec validate --all --strict --store tinytuya` → **Totals: 8 passed, 0 failed**. Fleet: 118 requirements (116 VERIFIED / 2 INFERRED), 118 DERIVED scenarios all tagged `SCENARIO-DEBT (derived, pass-4 conformance)` — pass 1 had no scenario corpus; grounded scenarios are the pass-3 style follow-up.
- Per-cap requirements: protocol-crypto 10, device-control 15, device-types 17, discovery 15, monitor 15, cloud-api 15, cli-wizard-tools 16, packaging-surface 15. Drafts in `specs_draft/` (source of truth), converted specs in `openspec/specs/`.
- History: 1,152 commits total (946 no-merge mined), 2020-09-03 .. 2026-07-02; only 4 carry `(#NNNN)` refs — evidence is docs + pin code + tests, history is intent-provenance only.
- Evidence inventory (`recon/evidence/`): `commits.json` (946), `docs/` (12 normative docs incl. PROTOCOL.md 37KB, API.md 28KB, DESIGN.md, README 60KB, AGENTS.md, Release notes inside RELEASE.md), `tests_inventory.txt` (47 defs/classes in tests.py), `bundle_<cap>.txt` ×8, `verified_prs.json` (12 GitHub numbers — 7 PRs + 5 issues — verified live via API 2026-11-09; state/title recorded).
- Scripts registered: `recon/scripts/mine_evidence.py` (phase 1), `recon/scripts/audit_drafts.py` (anchor existence + line-range, `[commit <12sha>]` resolves at pin, PR/issue cites must be in verified_prs.json allowlist, repo-root files like tests.py allowed unqualified).

## Fleet drift register (verified at pin; candidate upstream doc-fix list)

- `set_musicmode()`/`unset_musicmode()` documented in API.md + `tinytuya/BulbDevice.py` docstring but NOT implemented at pin (use `set_mode('music')`).
- API.md cover signatures `open_cover(switch=1,...)` vs code `switch=None`→`DPS_INDEX_MOVE`; API.md omits `continue_cover()`, `set_cover_type()`.
- `ERR_CLOUDRESP` (910) defined/documented but never emitted by `Cloud.py` (unparseable-response path returns `ERR_CLOUDKEY` 909, `tinytuya/Cloud.py:263-267`).
- `Cloud.py` module docstrings stale: `cloudrequest(post={})` vs real `action=None,post=None`; `getdevicelog` defaults/params drifted; region list missing us-e/eu-w/sg + aliases; unknown region silently falls back to China host; `getdevices()` docstring says dict, returns list (non-verbose).
- `getmapping()/getmappings()/setmappings()` public methods documented nowhere.
- server/README.md route `/delayedoff/...` vs code `/delayoff/` (`server/server.py:532`); `/set/` doc omits `{Code}` variant.
- setup.py crypto probe order (cryptography→pycryptodome→pyaes→pycrypto) != runtime order (`crypto_helper.py:9`: pyca→PyCryptodomex→PyCrypto→pyaes); no `python_requires`; pyproject `[build-system]`-only; colorama optional at runtime yet hard install-requires; console_script runs CLI via import side effect (`dummy` no-op).
- `tools/broadcast-relay.py`, `tools/fake-v35-device.py` undocumented; `tools/ttcorefunc.py` hand-copy with no sync mechanism.
- `CoverDevice.DPS_INDEX_BL="101"` declared/mapped but never used.
- No client-side cloud rate limiting despite trial-account cautions (spec'd as documentation-SHALL requirement).
- `getconnectstatus()` indexes `result['online']` unguarded (`tinytuya/Cloud.py:715`).

## Pass history
| Date | Pass | Pin | Outcome |
|---|---|---|---|
| 2026-11-09 | 1 | v1.20.0 @ 8512d836 | scope set (8 caps); evidence mined (946 commits, 12 docs, 8 bundles); drafts via 2×3 children + inline protocol-crypto; parent audit gate caught+fixed bare/relative anchors (W1: Monitor/XenonDevice/scanner/udp_helper/core/*/Contrib paths) and 1 placeholder sha; PR/issue cites verified via GitHub API (all 12 real, titles match); W2 self-reports audit-clean (write-scope clean); strict validate 8/8 green; 118 reqs 98.3% VERIFIED; scenario debt 118 derived → next: pass-3 scenario grounding, pass-2 tail check vs newer tags (none past v1.20.0 as of pin date) |

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
