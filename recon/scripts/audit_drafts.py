#!/usr/bin/env python3
"""Phase-4 audit for tinytuya store: anchors exist at pin + line in range;
commit-sha cites resolve; PR cites rejected (repo has none)."""
import json, os, re, subprocess, sys

STORE = "/opt/data/agent-github-spec-store/github/jasonacox/tinytuya"
DRAFTS = os.path.join(STORE, "specs_draft")
REPO = os.path.join(STORE, "repo")

anchor_re = re.compile(r'`([\w/\-\.]+\.py):(\d+)`')
sha_re = re.compile(r'\[commit ([0-9a-f]{12})\]|`([0-9a-f]{12})`')
bad = []
tot = dict(reqs=0, V=0, I=0)
for fn in sorted(os.listdir(DRAFTS)):
    if not fn.endswith(".md"):
        continue
    text = open(os.path.join(DRAFTS, fn)).read()
    tot["reqs"] += text.count("### Requirement:")
    tot["V"] += text.count("Status: VERIFIED")
    tot["I"] += text.count("Status: INFERRED")
    for f, ln in anchor_re.findall(text):
        p = os.path.join(REPO, f)
        if not os.path.exists(p):
            bad.append((fn, f + ":" + ln, "MISSING-FILE"))
        else:
            n = sum(1 for _ in open(p, errors="ignore"))
            if int(ln) > n:
                bad.append((fn, f + ":" + ln, "LINE-OOB(%d)" % n))
    for m in sha_re.findall(text):
        sha = m[0] or m[1]
        r = subprocess.run(["git", "-C", REPO, "cat-file", "-e", sha + "^{commit}"],
                           capture_output=True)
        if r.returncode != 0:
            bad.append((fn, sha, "SHA-NOT-AT-PIN"))
    for m in re.findall(r'pull/(\d+)', text):
        bad.append((fn, "pull/" + m, "PR-CITE-IN-REF-FREE-REPO"))

print("totals:", tot)
if bad:
    print("PROBLEMS:")
    for b in bad:
        print("  ", b)
    sys.exit(1)
print("AUDIT CLEAN")
