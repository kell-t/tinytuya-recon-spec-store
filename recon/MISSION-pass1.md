# MISSION pass 1 — recon-spec jasonacox/tinytuya @ v1.20.0

You are the spec agent (sole writer of this store). Build the initial OpenSpec behavioral model of **jasonacox/tinytuya** — a Python library for local/cloud control of Tuya smart devices — at the fixed pin below.

## Pin (immutable for this pass)
- Commit `8512d8364a9d0e351bbec2597bafa17595545b13` = tag `v1.20.0` (annotated tag obj `8cd2e73`), published 2026-07-06. License MIT. Default upstream branch: `master`.
- Pinned clone already at `repo/` (blobless). Validate/drift-check only against this pin.

## Store ground rules (cluster WORKFLOW.md + your SOUL are binding)
- This store = private working model. NEVER commit spec content upstream (upstream has no `openspec/`).
- License firewall: tinytuya content stays inside this store. Do not read or import from other stores (droiddeck, hermes-agent).
- Release-branch policy: work on `main`; when pass 1 closes green, create branch `v1.20.0` at the final commit.
- Remote `origin` = https://github.com/kell-t/tinytuya-recon-spec-store.git — push access may not be granted yet; if a push 403s, keep committing locally, note "push pending" in your Telegram milestone, continue working. NEVER print tokens.

## Objectives (in order)
1. **Scope**: survey the repo; decide capability decomposition (suggest starting points: device lifecycle/connection, Tuya message protocol + crypto, local DPS control, discovery/broadcast, cloud API, scenes, utilities/mocking/versioning, CLI tools — but decide from evidence, not from this list). Record the decision + rejected alternatives in `recon/RECON_LEDGER.md`.
2. **Evidence mining**: mine git history (full log at pin), docstrings, README/ChangeLog, tests. Build `recon/evidence/` bundles per capability with file:line anchors AT THE PIN.
3. **Drafts + conversion**: draft specs per capability in `specs_draft/` following `recon/DRAFT_TEMPLATE.md` (VERIFIED/INFERRED statuses, Evidence, Anchor). Convert with `/opt/data/agent-github-spec-store/tools/draft_to_spec.py` into `openspec/specs/<capability>/spec.md`. Every requirement: RFC-2119 text < 500 chars, ≥1 scenario (mark converter-derived ones SCENARIO-DEBT, never citable as evidence).
4. **Validation gate**: `openspec validate --all --strict --store tinytuya --no-interactive` must be GREEN at every milestone commit (register the store if this machine lost registrations).
5. **Ledger**: `recon/RECON_LEDGER.md` with CURRENT STATE (pin, counts, VERIFIED %, scenario debt, validation line) + NEXT-PASS (gaps, weak spots) + provenance notes (scripts registered).

## Constraints
- Milestone commits, signed (repo-local config handles identity+signing; do not override).
- Anchor discipline: open every cited file at the pin before claiming VERIFIED.
- If you use subagents: max 3 concurrent; leaf-drafted requirements are self-verified by YOU before commit (fabrication audit: re-open anchors, check PR/issue cites).
- Telegram updates per your standing addendum: actual `curl sendMessage`, response must show `"ok":true`, prefix `spec:`, ≤1 per 5 min. First message soon: capability list decided.
- Headless approvals: never answered — retry, work around with non-flagged equivalents, never disguise intent.

## Definition of done (pass 1)
All capabilities drafted with evidence, converter output strictly green, ledger CURRENT STATE + NEXT-PASS written, branch `v1.20.0` created, final Telegram report with counts + validation line + commit list.
