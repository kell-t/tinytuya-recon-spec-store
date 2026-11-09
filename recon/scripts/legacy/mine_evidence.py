#!/usr/bin/env python3
"""Phase-1 evidence mining for tinytuya store (pin 8512d836). No PR-ref filter:
history carries almost no refs — commits.json is provenance, docs+tests+pin code
carry the evidence. Writes recon/evidence/."""
import json, os, re, subprocess

STORE = "/opt/data/agent-github-spec-store/github/jasonacox/tinytuya"
REPO = os.path.join(STORE, "repo")
EV = os.path.join(STORE, "recon", "evidence")
os.makedirs(EV, exist_ok=True)

# 1) full commit log at the pin (all commits, no filter)
out = subprocess.run(["git", "-C", REPO, "log", "--no-merges",
                      "--format=%H|%ad|%s", "--date=short"],
                     capture_output=True, text=True, check=True).stdout
rows = []
for line in out.splitlines():
    p = line.split("|", 2)
    if len(p) == 3:
        rows.append({"sha": p[0][:12], "date": p[1], "subject": p[2]})
json.dump(rows, open(os.path.join(EV, "commits.json"), "w"), indent=1)
print("commits mined:", len(rows), "| window:", rows[-1]["date"], "..", rows[0]["date"])

# 2) normative doc corpus
DOCS = ["PROTOCOL.md", "API.md", "DESIGN.md", "README.md", "AGENTS.md", "SECURITY.md",
        "RELEASE.md", "DP_Mapping.md", "docs/README.md", "tinytuya/Contrib/README.md",
        "server/README.md", "tools/README.md"]
dd = os.path.join(EV, "docs"); os.makedirs(dd, exist_ok=True)
for d in DOCS:
    src = os.path.join(REPO, d)
    if os.path.exists(src):
        open(os.path.join(dd, d.replace("/", "_")), "w").write(open(src).read())
        print("doc:", d, os.path.getsize(src), "bytes")
    else:
        print("doc MISSING:", d)

# 3) test inventory with anchors (tests.py; test.py/testcontrib.py are manual scripts)
t = open(os.path.join(REPO, "tests.py")).read().splitlines()
tests = [(i + 1, l) for i, l in enumerate(t) if re.match(r"\s*(class |def test|    def test)", l)]
open(os.path.join(EV, "tests_inventory.txt"), "w").write(
    "tests.py @ pin (line: def)\n" + "\n".join("%d: %s" % x for x in tests) + "\n")
print("test defs/classes:", len(tests))

# 4) per-capability bundles: file inventory + commit-subject matches
CAPS = {
 "protocol-crypto": (r'protocol|encrypt|aes|gcm|hmac|session|key|pack|unpack|frame|checksum|crc|55aa|6699|version 3|v3\.',
   ["tinytuya/core/message_helper.py", "tinytuya/core/crypto_helper.py",
    "tinytuya/core/XenonDevice.py (negotiation)", "tinytuya/core/header.py",
    "tinytuya/core/command_types.py", "PROTOCOL.md"]),
 "device-control": (r'status|set_|set\(|dps|timeout|retry|connect|receive|udpport|device22|heartbeat|state',
   ["tinytuya/core/XenonDevice.py", "tinytuya/core/Device.py",
    "tinytuya/core/udp_helper.py", "API.md § XenonDevice/Device"]),
 "device-types": (r'bulb|cover|outlet|thermostat|contrib|dimmer|fan|ir |climate|socket|color',
   ["tinytuya/OutletDevice.py", "tinytuya/BulbDevice.py", "tinytuya/CoverDevice.py",
    "tinytuya/Contrib/*", "API.md § OutletDevice/BulbDevice/CoverDevice", "DP_Mapping.md"]),
 "discovery": (r'scan|broadcast|discover|udp|sniff|ap\b|wizard',
   ["tinytuya/scanner.py", "tinytuya/core/udp_helper.py", "tools/broadcast-relay.py",
    "DESIGN.md § Discovery"]),
 "monitor": (r'monitor|realtime|sniffer|listen',
   ["tinytuya/core/Monitor.py", "PROTOCOL.md § monitoring sections"]),
 "cloud-api": (r'cloud|token|sign|record|endpoint|rest|http|api key|v2|share|device list',
   ["tinytuya/Cloud.py", "API.md § Cloud", "DESIGN.md § Cloud"]),
 "cli-wizard-tools": (r'wizard|cli|main|server|mqtt|command|subcommand|help|example',
   ["tinytuya/cli.py", "tinytuya/__main__.py", "tinytuya/wizard.py",
    "server/server.py", "tools/*", "examples/"]),
 "packaging-surface": (r'export|import|version|exception|setup|pypi|release|init|depend|python',
   ["tinytuya/__init__.py", "tinytuya/core/__init__.py", "tinytuya/core/exceptions.py",
    "tinytuya/core/error_helper.py", "tinytuya/core/const.py", "pyproject.toml", "setup.py"]),
}
for cap, (kw, files) in CAPS.items():
    rx = re.compile(kw, re.I)
    hits = [r for r in rows if rx.search(r["subject"])]
    lines = ["# Bundle: %s — %d/%d commit-subject hits (full history; refs rare — subject = intent only, verify at pin)"
             % (cap, len(hits), len(rows)), "# Primary code/doc inventory:",
             *[("  - " + f) for f in files], ""]
    for r in hits[:60]:
        lines.append("%s [%s] %s" % (r["date"], r["sha"], r["subject"]))
    open(os.path.join(EV, "bundle_%s.txt" % cap), "w").write("\n".join(lines) + "\n")
    print("bundle_%s: %d hits" % (cap, len(hits)))
print("done")
