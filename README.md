# tinytuya-recon-spec-store

A **reconnaissance spec store** for [jasonacox/tinytuya](https://github.com/jasonacox/tinytuya) — a reverse-engineered behavioral model maintained by an autonomous spec agent, built *from* the source at a pinned release, never merged upstream.

## What this is

An [OpenSpec](https://openspec.dev/) store describing what tinytuya **does**, capability by capability:

| Capability | Models |
|---|---|
| `protocol-crypto` | 55AA/6699 framing, CRC32/HMAC/GCM integrity, AES-ECB/GCM, v3.4/v3.5 session-key negotiation, command ids |
| `device-control` | local TCP lifecycle: connect/status/set DPS, timeouts/retries, device22 quirks |
| `device-types` | Outlet/Bulb/Cover + Contrib class hierarchy, DP-mapping semantics |
| `discovery` | broadcast scan (3.1/3.4/3.5), sniffer, force-scan, offline representation, file outputs |
| `monitor` | multi-device reactor monitor, decryption modes, reliability/reconnect contract |
| `cloud-api` | Tuya cloud v1/v2 REST: HMAC signing, token cache, device/log/record endpoints, error dicts |
| `cli-wizard-tools` | CLI subcommands, scan/monitor/wizard entry points, MQTT API server, dev tools |
| `packaging-surface` | public exports, versioning, exceptions/error codes, config file formats, install metadata |

Every requirement carries a provenance status:

- `VERIFIED` — an anchor (`file:line` at the pinned commit) or a release-note/PR/issue/test citation, re-checked at the pin by a scripted audit gate.
- `INFERRED` — supported by evidence not yet anchor-checked; treat as a hypothesis.

Scenario blocks are grounded, not invented: each `#### Scenario:` carries a `Source:` line into a human-written source — release notes (`[relnote vX.Y.Z]`), in-repo docs (`PROTOCOL.md`, `API.md`, `README.md`, `DESIGN.md`, `DP_Mapping.md`, …), or tests at the pin (`tests.py::Class::method`). Requirements whose behavior is only expressible from code reading are deliberately left property-style and carry **SCENARIO-DEBT** derived placeholders instead — those are documented gaps, not evidence.

The authoritative snapshot (counts, pin, coverage, open gaps, next pass) lives in [`recon/RECON_LEDGER.md`](recon/RECON_LEDGER.md) — everything else in this README is by-design approximate.

## How it is derived

The spec agent clones upstream **blobless at the pinned tag** (kept out of git on purpose — see `.gitignore`) and works in an isolated per-repo store. tinytuya's commit log carries almost no `(#NNNN)` references (4/1152), so the evidence model is **docs + pin-code + tests**; commit history is mined without a ref filter and cited only as intent-provenance (`[commit <12-hex>]`). GitHub issue/PR numbers used as citations are verified live via API and allowlisted in `recon/evidence/verified_prs.json` — the gate rejects numbers outside it.

Pipeline, per pass:

1. `recon/scripts/mine_evidence.py` — mine the full log, normative docs, test inventory into `recon/evidence/` bundles.
2. `recon/scripts/mine_relnotes.py` — split RELEASE.md into 75 per-version `evidence/relnote_v*.txt` citation files.
3. Drafting in `specs_draft/` (source of truth; fleet children on disjoint files under parent-audited citation law).
4. Gates before every commit: `recon/scripts/audit_drafts.py` (anchor existence at pin, sha cites resolve, allowlisted numbers) and `recon/scripts/audit_scenarios.py` (scenario quotes ≥60% non-stopword overlap with the cited relnote/doc; test cites exact-grepped at the pin).
5. Convert `specs_draft/` → `openspec/specs/` via the cluster `tools/draft_to_spec.py`, then `openspec validate --all --strict`.

Nothing is asserted without a citation, and citations are mechanically re-checked against the pin.

Upstream tinytuya is MIT-licensed; this store is derivative documentation of it, attributed above and per-spec in `recon/`. The store's contents never cross into other repos' work (license firewall).

## Branches

One branch per upstream **full release** modeled here, named exactly after the tag — currently `v1.20.0` (pin `8512d836`, tag obj `8cd2e73`, 2026-07-06). `main` is the working trunk. Future releases follow the fleet workflow policy: base the new branch off whichever of {previous release branch, last main-dev pin} yields the smaller reconciliation delta, then walk to the new release. Pre-releases never get a branch.

## How to use

```bash
# validate (needs: npm i -g @fission-ai/openspec)
openspec store register .
openspec validate --all --strict --no-interactive

# get the pinned source alongside, the way the agent does:
git clone --filter=blobless --branch v1.20.0 https://github.com/jasonacox/tinytuya repo
```

Read order: `recon/RECON_LEDGER.md` (state + gaps) → `openspec/specs/<capability>/spec.md` (requirements) → `recon/evidence/` (bundles, relnotes, docs at pin) → `specs_draft/` (per-requirement Status/Evidence/Anchor and Scenario-ification notes).

**Status snapshot (rot-prone; the ledger wins):** 118 requirements, 116 VERIFIED (98.3%), 178 grounded scenarios + 12 scenario-debt placeholders, at pin v1.20.0.
