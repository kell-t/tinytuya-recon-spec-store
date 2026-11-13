# Pin health survey — 2026-11-14 (read-only, pass-4 scope)

Trigger: GitHub `releases/latest` = **v1.21.1** (published 2026-11-12T07:20:59Z)
> store pin v1.20.0 @ `8512d8364a9d0e351bbec2597bafa17595545b13`.
`compare/pin...master` → **ahead_by 135**. v1.21.1 commit
`b0482da13af473677a78ea76a94bd8ed2c37a3e7`; v1.21.0 @ `8acad457`.
Re-pin remains OWNER-GATED — this file is a readiness survey only; pin unchanged.

Method: all 216 `file:line` anchor cites extracted from `specs_draft/*.md`
(118 requirements, 31 cited files) probed against both revisions via
`git show <ref>:<path>` in the blobless `repo/` clone (fetched `--tags`
2026-11-14). Classification per probe: untouched-file / byte-identical cited
block at cited lines / SHIFTED (block found at a different line, or hint
identifier/first-line match) / FUZZ (difflib close match, needs human read) /
DEAD.

## Headline

- **0 dead anchors at v1.21.1** (0 FILE-MISSING, 0 CONTENT-GONE, 216/216
  probes located). Re-pin is mechanically cheap; no requirement dies.
- 81 probes in files untouched pin→v1.21.1; the rest located byte-identical
  at the cited lines or SHIFTED within 12 touched files.
- Shift concentration (probes needing line moves at re-pin):
  `tinytuya/core/Monitor.py` 31, `tinytuya/scanner.py` 28,
  `tinytuya/Cloud.py` 27, `tinytuya/core/XenonDevice.py` 16,
  `tinytuya/BulbDevice.py` 6, `setup.py` 5, `tinytuya/__main__.py` 8,
  `pyproject.toml` 3, `tinytuya/wizard.py` 3, `tests.py` 3,
  `tinytuya/core/Device.py` 2, `tinytuya/core/core.py` 2.
- 1 FUZZ cleared by hand: `tinytuya/core/core.py:104` (REQ
  "Single-source version declaration") — same line number at v1.21.1, only
  the value bumped `version_tuple = (1, 21, 1)`; anchor live, requirement
  unaffected.

## Behavioral re-read candidates at re-pin (merged in v1.21.0/v1.21.1)

Tier-A release-note text (RELEASE.md at `b0482da1`, headings `## v1.21.1 -
Force-Scan Fixes`, `## v1.21.0 - ...`) describes behavior changes that the
pin-version specs must be re-read against (removal-check law applies to OLD
requirements):

1. **#748 drop-eol-python** — Python ≥3.10 required; `setup.py:48` now
   carries `python_requires=">=3.10"`. This FIXES fleet-drift-register item
   "no python_requires" upstream → packaging-surface wording must follow at
   re-pin (pip on old Pythons keeps v1.20.0).
2. **#762 PEP 639 SPDX license expression** in packaging metadata (removes
   setuptools deprecation warning) — packaging-surface.
3. **#767 server path-traversal fix** (static handler refuses paths outside
   `server/web`) — cli-wizard-tools server sub-area; security behavior change.
4. **#754 `send_retry_limit` ctor option + `set_sendRetryLimit()`** incl.
   `set_multiple_values()` skipping its one-DP fallback at 0 —
   device-control new surface.
5. **#735 poll-configured discovery** (`poll_configured=True`, `-no-poll-configured`)
   — discovery new surface.
6. **#770 force-scan v3.4 identification + key-retry backoff** (nonce fix;
   pyaes backend skips 3.5 hello; failed key/IP not retried for 1 h) —
   discovery + protocol-crypto negotiation behavior.
7. **#759 gateway `receive()` returns result dict** for queued child updates
   (was `(child, result)` tuple); **#761 `generate_payload()` no longer
   mutates cached command template** — device-control/device-types.
8. **#755 `set_hsv()`/`set_colour()` float tolerance on rgb8 bulbs**;
   relevant to device-types REQ "Colour set semantics…" (already carries a
   pass-3 relnote-vs-pin FLAG).
9. **#756 `getdevicelog(size>100)` pages past 100**; **#757 token-refresh
   retry signs un-encoded query** — cloud-api (Cloud docstring drift
   register may partially self-heal; re-verify).
10. **#758 per-device debug log prefix + `device_id` log-record attribute** —
    new cross-cutting surface (monitor/device-control logging).
11. Scanner robustness/output fixes #750/#765/#766/#769 — discovery
    scenarios citing scanner behavior need line + wording re-checks.
12. PROTOCOL.md camera-signalling section added (#763) — protocol-crypto/
    docs corpus grows; re-run `mine_relnotes.py`.

## Scenario-debt closure candidates (post-re-pin pass, Tier-A first)

The 12 residual `SCENARIO-DEBT (derived, pass-4 conformance)` reqs were
"code-only" at v1.20.0. v1.21.x relnotes ADD Tier-A text for several:

- discovery (4 debt): #735 poll-configured, #750/#765/#766 robustness,
  #769 saved-IP output wording, #770 force-scan — strong Tier-A candidates.
- packaging-surface (4 debt): #748 `python_requires`, #762 SPDX/PEP 639.
- cloud-api (1 debt): #756 paging / #757 retry signing.
- protocol-crypto (1 debt): #770 negotiation-skip behavior on non-GCM backends.
- monitor (1), cli-wizard-tools MQTT-gateway (1): no new Tier-A text seen —
  likely permanent debt; say so in spec rather than churning.

Do NOT ground against v1.21.1 text while the pin is v1.20.0 — grounding and
spec re-conversion belong to the owner-approved re-pin pass.

## Evidence provenance

- Survey script: session scratch `tt_pin_survey.py` (stdlib + git show on
  blobless clone); classification counts reproduced above verbatim from its
  stdout: `anchor probes: 216 cited files: 31 / untouched 81 / SHIFTED 134 /
  FUZZ 1 / DEAD 0 / DEAD-FILE 0 / total commits 135 / breaking-candidates 2`
  (`3bff8c8 send_retry_limit …`, `720bd5e Merge PR #748 drop-eol-python`).
- API: `releases/latest` tag_name/published_at per store;
  `compare/8512d83…master` → `"ahead_by": 135`.
