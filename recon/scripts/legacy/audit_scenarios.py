#!/usr/bin/env python3
"""Pass-3 gate: audit grounded scenario blocks in specs_draft/.

For every `#### Scenario:` block, its `- Source:` lines must be one of:
  [relnote <ver>] "quoted phrase"   -> relnote_<ver>.txt exists; >=60% of the
                                        quote's non-stopword tokens appear in body
  doc: <path> ... "quoted phrase"   -> path resolves under evidence/docs/ or repo/;
                                        >=60% token overlap with that doc
  test: <path>::Class::method        -> EXACT grep of path + class + method in repo at pin
                                          (repo/tests.py::Class::method or bare tests.py ok)
Also counts per-cap grounded scenarios and requirements lacking one.
Exit non-zero on any violation."""
import json, os, re, sys

STORE = "/opt/data/agent-github-spec-store/github/jasonacox/tinytuya"
DRAFTS = os.path.join(STORE, "specs_draft")
DOCS = os.path.join(STORE, "recon/evidence/docs")
EVID = os.path.join(STORE, "recon/evidence")
REPO = os.path.join(STORE, "repo")

STOP = set("a an the and or but if then that this these those of to in on for with as at by from is are was were be been being it its into over under not no nor so than too very can could will would shall may might must do does did done have has had having you your we our they their he she i when while before after also more most other some any each per via that's".split())

def tokens(s):
    return [t for t in re.findall(r"[A-Za-z0-9_]{3,}", s.lower()) if t not in STOP]

def overlap(quote, body):
    qt = tokens(quote)
    if not qt:
        return 1.0
    bt = set(tokens(body))
    return sum(1 for t in qt if t in bt) / len(qt)

def resolve_doc(path):
    # try evidence docs mapping, then repo
    cand = os.path.join(DOCS, path)
    if os.path.exists(cand):
        return cand
    cand2 = os.path.join(REPO, path)
    if os.path.exists(cand2):
        return cand2
    # evidence docs use flattened names like server_README.md
    flat = path.replace("/", "_")
    cand3 = os.path.join(DOCS, flat)
    if os.path.exists(cand3):
        return cand3
    return None

bad = []
stats = {}
for fn in sorted(os.listdir(DRAFTS)):
    if not fn.endswith(".md"):
        continue
    cap = fn[:-3]
    text = open(os.path.join(DRAFTS, fn)).read()
    reqs = text.count("### Requirement:")
    scen = text.count("#### Scenario:")
    stats[cap] = dict(reqs=reqs, grounded=scen)
    # split into scenario blocks: header -> next ^#### or ^### or ^##
    for m in re.finditer(r'(?m)^#### Scenario: (.+)$', text):
        name = m.group(1)
        end = len(text)
        nm = re.search(r'(?m)^#{2,4} ', text[m.end():])
        # find next header AFTER m.end() (skip nothing; header regex matches the next one only if we search from m.end())
        blk_end = m.end() + (nm.start() if nm else len(text) - m.end())
        blk = text[m.end():blk_end]
        sources = re.findall(r'(?m)^- Source: (.+)$', blk)
        if not sources:
            bad.append(f"{cap} | {name}: scenario with no Source line")
        for s in sources:
            rm = re.match(r'\[relnote (v[0-9.]+)\]\s*"(.+)"', s, re.S)
            dm = re.match(r'doc: (\S+)(?:\s*§\s*[^"]*)?\s*"(.+)"', s, re.S)
            tm = re.match(r'test: (\S+)::(\w+)::(\w+)', s)
            if rm:
                rf = os.path.join(EVID, f"relnote_{rm.group(1)}.txt")
                if not os.path.exists(rf):
                    bad.append(f"{cap} | {name}: relnote {rm.group(1)} not mined")
                    continue
                ov = overlap(rm.group(2), open(rf).read())
                if ov < 0.6:
                    bad.append(f"{cap} | {name}: relnote quote overlap {ov:.0%}: {rm.group(2)[:60]}...")
            elif dm:
                p = resolve_doc(dm.group(1))
                if p is None:
                    bad.append(f"{cap} | {name}: doc path unresolved: {dm.group(1)}")
                    continue
                ov = overlap(dm.group(2), open(p).read())
                if ov < 0.6:
                    bad.append(f"{cap} | {name}: doc quote overlap {ov:.0%}: {dm.group(2)[:60]}...")
            elif tm:
                path, cls, meth = tm.groups()
                fp = os.path.join(REPO, path)
                if not os.path.exists(fp):
                    bad.append(f"{cap} | {name}: test path missing: {path}")
                    continue
                src = open(fp, errors="replace").read()
                if f"class {cls}" not in src:
                    bad.append(f"{cap} | {name}: test class missing: {path}::{cls}")
                if f"def {meth}" not in src:
                    bad.append(f"{cap} | {name}: test method missing: {path}::{cls}::{meth}")
            else:
                bad.append(f"{cap} | {name}: unparseable Source: {s[:80]}")

tot_g = sum(v["grounded"] for v in stats.values())
tot_r = sum(v["reqs"] for v in stats.values())
print(json.dumps(stats, indent=1))
print(f"TOTAL grounded scenarios {tot_g} / requirements {tot_r}")
if bad:
    print("\n".join(f"VIOLATION: {b}" for b in bad))
    print(f"FAIL: {len(bad)} violations")
    sys.exit(1)
print("GATE GREEN")
