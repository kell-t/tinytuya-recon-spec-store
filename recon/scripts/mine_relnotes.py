#!/usr/bin/env python3
"""Pass-3 groundwork: split evidence/docs/RELEASE.md into per-version
recon/evidence/relnote_<ver>.txt files so drafts can cite
`[relnote <ver>] "quote"` and audit_scenarios.py can word-overlap-verify.
Version header shape in tinytuya RELEASE.md: '## vX.Y.Z - Title'.
Idempotent: rewrites all relnote_*.txt each run."""
import os, re, glob

STORE = "/opt/data/agent-github-spec-store/github/jasonacox/tinytuya"
SRC = os.path.join(STORE, "recon/evidence/docs/RELEASE.md")
OUT = os.path.join(STORE, "recon/evidence")

text = open(SRC).read()
# strip old
for f in glob.glob(os.path.join(OUT, "relnote_*.txt")):
    os.remove(f)

parts = re.split(r'(?m)^## (v[0-9][^\n]*)$', text)
# parts[0] = preamble, then pairs (header, body)
count = 0
for i in range(1, len(parts) - 1, 2):
    header = parts[i].strip()
    body = parts[i + 1].strip()
    ver = header.split(" - ")[0].strip()
    ver = re.sub(r'[^v0-9.]', '', ver)
    if not re.match(r'^v\d+\.\d+(\.\d+)?$', ver):
        print("SKIP weird version header:", header)
        continue
    with open(os.path.join(OUT, f"relnote_{ver}.txt"), "w") as fh:
        fh.write(header + "\n" + body + "\n")
    count += 1
print(f"wrote {count} relnote files from {SRC}")
