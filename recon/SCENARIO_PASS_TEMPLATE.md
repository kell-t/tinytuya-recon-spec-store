# SCENARIO_PASS_TEMPLATE.md — Pass 3: scenario-ification of verified requirements

Goal: add OpenSpec-conformant `#### Scenario:` blocks (WHEN / THEN / AND) beneath existing
requirements in the files in `specs_draft/`, WITHOUT ever inventing behavior.

## THE GROUNDING RULE (stricter than pass 1 — binding)

Every scenario clause must be traceable to a HUMAN-WRITTEN SOURCE:
- **Tier A (preferred): release notes** — `evidence/relnote_<ver>.txt` (75 files, v1.0.0..v1.20.0,
  mined from RELEASE.md) text describing the trigger and outcome.
- **Tier B (accepted): repo documentation** — `evidence/docs/**` at the pin: `PROTOCOL.md`,
  `API.md`, `DESIGN.md`, `README.md`, `DP_Mapping.md`, `AGENTS.md`, `SECURITY.md`,
  `server_README.md`, `tinytuya_Contrib_README.md`, `tools_README.md` — text describing the
  trigger and outcome.
- **Tier C (accepted): tests at the pin** — test names / test asserts in `repo/tests.py`
  (read-only clone at pin; inventory in `evidence/tests_inventory.txt`). A test name may
  supply the WHEN trigger and the asserted outcome together.

A scenario is admitted ONLY when BOTH the trigger (WHEN) and the outcome (THEN)
appear, in substance, in the cited Tier A/B text. Exact quote not required —
substance match is — but you must cite the file and quote the supporting phrase(s).

## Rules

1. If the release notes / docs give trigger + outcome → write:
   ```
   #### Scenario: <short name>
   - **WHEN** <trigger as documented>
   - **THEN** <outcome as documented>
   - **AND** <further documented clause>   (only if documented)
   - Source: [relnote v1.20.0] "…quoted phrase…"   (or doc:/test: cite, see gates below)
   ```
   Place the scenario block INSIDE its requirement block — after the `- Anchor:` line,
   before the next `###` header. Add one `- Source:` line per cited clause group at the end
   of the scenario. Keep the requirement's Status/Evidence/Anchor lines untouched.
   Cite formats (enforced by recon/scripts/audit_scenarios.py):
   `[relnote v<X.Y.Z>] "quoted phrase"` — ≥60% non-stopword token overlap with relnote_<ver>.txt;
   `doc: <path> § <section> "quoted phrase"` — path under evidence/docs/ (flattened names) or repo/;
   `test: tests.py::TestClass::test_method` — EXACT class+method grep in repo at the pin.
2. If trigger or outcome is NOT in Tier A/B/C text (code-only or inferred) → DO NOT write a
   scenario. Leave the requirement as-is (property-style) and add, under the file's
   `## Scenario-ification notes` section:
   `- REQ "<title>": no doc-grounded trigger; kept as invariant. (reason)`
3. NEVER derive a WHEN clause from code reading. Code tells you the behavior exists;
   only the docs/releases tell you the documented contract.
4. AND clauses only for clauses that are themselves documented. Do not compound inferences.
5. One scenario minimum per requirement where documentable; two preferred when the docs
   describe both a happy path and a fallback/edge ("stays", "unless", "even when", "instead").
6. Keep RFC-2119 verbs consistent with the parent requirement's force.
7. Do not modify any requirement text, grade, anchor, or gap entries.
   Append-only behavior: scenarios under requirements, notes under the notes section.
8. Update each file's header line: append `| Pass 3 (scenario-ification) applied <date>`.
9. At the end of each file assigned to you, output for the return summary:
   - scenarios added per file (count)
   - requirements left property-style (count + one-line reasons)
   - any doc-grounding surprises (docs contradicting the pass-1 requirement → flag, don't fix)
