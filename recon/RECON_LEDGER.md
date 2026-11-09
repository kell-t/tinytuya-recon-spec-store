# RECON_LEDGER — tinytuya

Store: `github/jasonacox/tinytuya` (id `tinytuya`). Boot order: PLAYBOOK.md → this file. License MIT; private working model; license firewall — content never leaves this store.

## CURRENT STATE (pass 3 COMPLETE, 2026-11-09; pass 1 complete 2026-11-09)

- Baseline pin: `master-line tag v1.20.0 @ 8512d8364a9d0e351bbec2597bafa17595545b13` (annotated tag obj 8cd2e73, published 2026-07-06). `recon/baseline.txt`. Blobless clone at `repo/` — READ-ONLY for drafting.
- Validation: `openspec validate --all --strict --store tinytuya` → **Totals: 8 passed, 0 failed**. Fleet: 118 requirements (116 VERIFIED / 2 INFERRED); **178 grounded scenarios** added pass-3 (Tier A relnotes / Tier B docs / Tier C pin-tests, all Source-cited) across 106 of 118 requirements; scenario debt 118 → **12** remaining `SCENARIO-DEBT (derived, pass-4 conformance)` placeholders (protocol-crypto 1, discovery 4, monitor 1, cloud-api 1, cli-wizard-tools 1, packaging-surface 4 — each documented under its draft's `## Scenario-ification notes` as code-only behavior).
- Pass-3 grounding law honored: no WHEN derived from implementation code; requirement Status/Evidence/Anchor text append-only. Gate: `recon/scripts/audit_scenarios.py` (relnote/doc quotes ≥60% non-stopword overlap vs evidence; `test:` cites exact class+method grep at pin; grounded-vs-reqs tally). Relnote corpus: `recon/scripts/mine_relnotes.py` splits RELEASE.md → 75 `evidence/relnote_v*.txt`.
- Per-cap requirements: protocol-crypto 10, device-control 15, device-types 17, discovery 15, monitor 15, cloud-api 15, cli-wizard-tools 16, packaging-surface 15. Drafts in `specs_draft/` (source of truth), converted specs in `openspec/specs/`.
- History: 1,152 commits total (946 no-merge mined), 2020-09-03 .. 2026-07-02; only 4 carry `(#NNNN)` refs — evidence is docs + pin code + tests, history is intent-provenance only. Upstream master +42 commits vs pin (FakeTuyaDevice wire-test suite, AGENTS.md policy, scanner robustness) — none merged into a release; pin stands until v1.21.x tags.
- Evidence inventory (`recon/evidence/`): `commits.json` (946), `docs/` (12 normative docs), `relnote_v*.txt` (75), `tests_inventory.txt` (47 defs/classes in tests.py), `bundle_<cap>.txt` ×8, `verified_prs.json` (12 GitHub numbers verified live via API).
- Scripts registered: kit-standard `recon/scripts/` — `gate.py` sequencer + `audit_requirements.py` / `audit_scenarios.py` auditors + miners (`mine_evidence`, `mine_relnotes`, `mine_tail`, `tally`) + `draft_to_spec.py`, configured by `recon/scripts/store_config.yaml` (kit = kell-t/recon-spec-store-kit @ PR#3). Bespoke pre-kit scripts archived under `recon/scripts/legacy/`.
- Anchor-hint graduation (2026-11-10): the 17 pre-convention descriptive hints enumerated by the strict hint check were rewritten to prepend a literal identifier present at the cited line (`cmd_list`, `add_argument`, `_monitor_device`, `__init__`, `set_multiple_values`, `udpkey`, `set_dimmer`, `COVER_TYPES`, `send_discovery_request`, `devices`, `tuyadevices`, `FSCAN`, `broadcast packets`, `monitor entry`, `INSTALL_REQUIRES`, `load_devicefile`, `Reference`); original descriptive pointers kept. `anchor_hint_check` now `strict`; gate GREEN, validate 8/8. Specs re-converted from drafts after the edits.

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
| 2026-11-09 | 3 | v1.20.0 @ 8512d836 | scenario grounding via 3+3+2 fleet waves on disjoint drafts; groundwork: RELEASE.md → 75 relnote files + `audit_scenarios.py` gate (baseline-green first). 178 grounded scenarios on 106/118 reqs (Tier A/B/C, all Source-cited; ≥60% quote-overlap + exact test-cite gate); 12 reqs kept property-style with reasons (code-only behavior, listed in each draft's Scenario-ification notes). Parent audit per wave: write-scope clean ×3, 3 prose bare-path/quote FPs fixed by parent, 8-cite spot audit clean; strict validate 8/8 green after conversion (190 scenarios = 178 grounded + 12 derived); pin unchanged (master +42 unmerged) |

## Pass-3 grounding flags (docs-vs-requirement tensions; verified at pin, specs unchanged)

- API.md § set_timer says `dps_id=0` uses "the last DPS in the status"; pin behavior is numeric-max DP selection (relnote v1.20.0 + `tests.py::TestXenonDevice::test_set_timer_picks_numeric_max_dp`) — upstream doc imprecision, spec follows code-at-pin.
- API.md § set_version example implies 3.3 required; relnote v1.18.0 clarifies "3.3 is not the required version".
- README § Command Line: `--version` "defaults to 3.3 if omitted" vs relnote v1.18.0 "triggers an auto-scan instead of silently defaulting to v3.3" — requirement's reconciliation (3.3 only when scan finds nothing) not verbatim in either source.
- relnote v1.10.1 claims capability-conditional blocking in `set_colour()/set_hsv()/set_colourtemp()` was removed (debug warning); code at pin returns `ERR_FUNCTION` (check reintroduced by v1.17.0 rewrite) — relnote history vs pin divergence, requirement correct at pin.
- Cloud region matching "case-insensitive" (pass-1 requirement detail) has no Tier A/B statement — code-only, excluded from scenario clauses.
- Monitor v1.20.0 relnote bullet "truncated frames raise DecodeError" belongs to `XenonDevice._receive`, not the Monitor buffer path — not used to ground Monitor scenarios.

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
