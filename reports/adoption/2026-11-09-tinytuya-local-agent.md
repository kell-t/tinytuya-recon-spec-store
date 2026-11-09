# Adoption review — tinytuya as local control for a durable home agent (ZigBee via Tuya)

- **Reviewer:** critic agent, 2026-11-09
- **Reviewed at:** tag `v1.20.0` @ `8512d8364a9d0e351bbec2597bafa17595545b13` (= store pin; what `pip install tinytuya` delivers). Master has +42 unmerged commits (scanner robustness, FakeTuyaDevice tests) — not reviewed as release surface.
- **Method:** static analysis of the clone (`/opt/data/agent-github/jasonacox/tinytuya`), cross-checked against store specs (`openspec/specs/**`). Code was NOT built or executed (untrusted-repo policy); all findings are grep/file:line-anchored at the pin.
- **Baseline specs consulted:** device-control, discovery, cloud-api, protocol-crypto, device-types.

## Verdict: **integrate-with-controls** (with one hard precondition)

**Precondition — the ZigBee reality.** tinytuya speaks the Tuya LAN protocol to Wi-Fi endpoints. Zigbee end-devices are supported **only as sub-devices behind a Tuya Wi-Fi/Zigbee gateway** (`dev_type='zigbee'`, `cid`/`node_id` ctor params wrap DPS in `{"protocol":5,...,"data":{"cid":...}}` — `tinytuya/core/XenonDevice.py:213-232,241-261`; `PROTOCOL.md` § "Sub-Devices / Gateways (Zigbee via Wi-Fi Hub)"). If the home's Zigbee mesh is (or will be) managed by something other than a Tuya gateway, tinytuya is the wrong tool — Zigbee2MQTT/ZHA territory. Everything below assumes Tuya gateway or Tuya Wi-Fi devices.

## Security findings

| # | Sev | Finding | Evidence | Control |
|---|-----|---------|----------|---------|
| S1 | HIGH *if used* | The bundled API server binds **all interfaces, port 8888, no authentication** — unauthenticated LAN clients can `/turnon`, `/set/...`, read state. Docker example additionally publishes UDP 6666/6667. Marked BETA. | `server/server.py:678` (`ThreadingHTTPServer(('', port), handler)`); route list `server/README.md`; no token/password handling anywhere in `server/server.py` | **Do not run `server/` or `server/mqtt/`.** Use the library directly from the agent. |
| S2 | MED | `local_key` is written to debug logs. | `tinytuya/core/XenonDevice.py:958,968,1085` (`log.debug(... local_key ...)`); `tinytuya/scanner.py:411` (`print(... real_local_key)` when debug) | Never enable debug logging/`-d`/`set_debug()` in the deployed agent; set log level WARNING+. |
| S3 | MED | Secrets on disk in plaintext with default permissions: `devices.json` (all local keys) and cloud config (apiKey/apiSecret) written without chmod/umask. | `tinytuya/wizard.py:166,263,278,311`; `tinytuya/scanner.py:1927`; no `chmod`/`umask` anywhere in lib/server | `chmod 600` after wizard; mount `devices.json` into container read-only; **do not ship cloud credentials into the agent container at all** (only needed once, at provisioning). |
| S4 | INFO (protocol-inherited, not library) | Tuya wire weaknesses: v3.1 STATUS/DP_QUERY are plaintext JSON with CRC32 only (no integrity key); UDP discovery broadcasts decryptable with well-known key `MD5("yGAdlopoPVldABfn")`; AES-ECB used in 3.1/3.3. | `PROTOCOL.md:27,116,125`; store `discovery` spec ("Transparent decryption … well-known UDP key"); `tinytuya/core/const.py:7-10` | Prefer 3.4/3.5 devices (session-key negotiation + AES-GCM, store `protocol-crypto` spec). VLAN-isolate Tuya devices regardless. |
| S5 | INFO (supply chain) | Clean surface: 3 runtime deps (`cryptography`, `requests`, `colorama`); floating pins; `setup.py` probes installed crypto libs and picks one (benign); no install-time scripts, no network at build beyond pip. | `requirements.txt`, `setup.py:18-35`, `pyproject.toml` | Pin exact versions in the agent image; vendor tinytuya at the v1.20.0 sha. |
| S6 | INFO | No eval/exec/pickle/subprocess/os.system/raw-socket promiscuous code in `tinytuya/`, `server/`, `tools/`. No telemetry, no update-check, no hidden egress. Only egress code path is `Cloud.py` (Tuya REST endpoints, opt-in). | grep sweep at pin (zero hits); `requests` imported only `tinytuya/Cloud.py` (guarded try/except, `Cloud.py:36-42`), `server/server.py`, `server/mqtt/mqtt_gateway.py` | — |
| S7 | INFO | Maintenance: active upstream (master HEAD 2026-11-09, release v1.20.0 2026-07, ~1,150 commits since 2020, tests suite at pin). `SECURITY.md` exists but routes vulns to public issues. | `git log` at clone; `SECURITY.md` | Watch upstream for releases touching `XenonDevice.py`/crypto. |

## The four capability questions

**1. Succeed without outbound internet? — YES (runtime), internet needed once (provisioning).**
No egress occurs at import or on the local-control path (S6; `XenonDevice.py:394` connects only to the device's LAN address). `requests` isn't even required for local control (`Cloud.py:36-42` degrades to a warning). Internet is needed **once** to obtain device IDs + `local_key`s via the setup wizard / Tuya Cloud (`tinytuya/wizard.py`, `Cloud.py`), after which `devices.json` is self-sufficient. Spec corroboration: store `cloud-api` is a separate, opt-in capability; `PROTOCOL.md` is explicitly LAN-only.

**2. No inbound port forwarding, containerized, outbound polling only? — YES.**
The library is pure client-initiated: TCP connect to `device:6668` per call (or persistent on request) — `XenonDevice.py:394`, `const.py:10`. `status()`/`set_value()` are request/response, so an outbound-only container works (bridge SNAT returns the replies). The library opens **no listeners on the control path**; the UDP binds on 6666/6667/7000 (`scanner.py:1204,1215,1226`) exist only during scan/listen mode. Consequence: **broadcast discovery from a NAT bridge container won't cross to the LAN** — either provision with host networking (or macvlan), or skip scanning entirely and pin static IPs in `devices.json` (`address=` param; targeted/force-scan paths use unicast, store `discovery` spec "Force-scan fallback"). Zero WAN inbound.

**3. Indicator light in a different state than the relay? — YES, iff the device exposes a separate DP; tinytuya itself never couples them.**
Any DP can be set/read independently: `set_value(index, value)`, `set_multiple_values(data)`, `status()` (`tinytuya/core/Device.py:80,99`), and unknown DPs can be probed with `detect_available_dps()` (`XenonDevice.py:1123-1129`). Precedent in-tree: `CoverDevice.py:85` maps `"101": "backlight"`. Whether a given switch has an indicator/backlight DP (commonly a separate DP on Tuya switch modules) is firmware-specific — verify per device with `detect_available_dps()`/`status()`. If firmware hard-wires the LED to the relay, no tool can decouple it.

**4. Read current from a heater switch to know it's fully heated? — YES for energy-metering switches; a temperature DP is better when present.**
- `Contrib/SocketDevice.py:62-87`: `get_current()` (mA), `get_power()` (0.1 W), `get_voltage()` (0.1 V) from metering DPs. `Contrib/WiFiDualMeterDevice.py:56-60`: per-channel power/current/total-energy DPs (incl. `'102'` directional current).
- Pattern: heating load draws near-max current; sustained drop to standby current ⇒ element off. Agent polls `status()` and watches current/power.
- Even better if the heater switch reports a temperature DP — e.g. `Contrib/TowelRailHeaterDevice.py:53-56` (current-temp DP 24, set-temp DP 16). Non-metering, non-thermostat switches give no such signal — check the specific model's DPS first (wizard `devices.json`, `detect_available_dps()`, or Tuya IoT platform DP listing per `DP_Mapping.md`).

## Lowest-attack-vector deployment guide (agent container)

**Phase A — provision once (throwaway environment, internet OK):**
1. `pip install tinytuya` in a temp venv on a LAN host; run `python -m tinytuya wizard` to fetch IDs/local keys → `devices.json` (set Tuya IoT project to *DP Instruction* mode for full DP listings, `DP_Mapping.md`).
2. `chmod 600 devices.json`; also record per-device protocol version (prefer 3.4/3.5; note metering/indicator DPs while you're here via `tinytuya scan` + `status()`).
3. Give every device a DHCP reservation so pinned IPs stay valid.

**Phase B — the durable agent container (no internet, no inbound):**
4. Build an image with tinytuya **pinned at v1.20.0** plus exact-version `cryptography`/`requests`; or drop `requests` entirely if you never call Cloud from the agent.
5. Run only your own script that `import tinytuya` — **never `server/`, never `server/mqtt/`** (S1).
6. Networking: no `-p` published ports. Bridge is fine for unicast polling of pinned IPs; use `--network host` or macvlan only if you need broadcast discovery (then drop back after provisioning).
7. Firewall (at host/VLAN): default-deny **egress** from the container except the device subnet(s); deny everything inbound to the container; between IoT VLAN and the rest of the home, default-deny — the agent is the only bridge, device-unicast-only.
8. Filesystem: read-only rootfs; mount `devices.json` read-only, mode 600, owned by a non-root user; run non-root; keep `tinytuya.json`/cloud creds **outside** the container (S3).
9. Logging: level WARNING+; never `set_debug(True)` / `-d` (S2); ensure agent logs don't land in world-readable locations.
10. Optional hardening: app-level allowlist of device IDs + DP numbers the agent may touch (tinytuya happily sets anything the device exposes); alert on repeated auth failures (wrong local key ⇒ `XenonDevice.py:1085` path) as a tamper signal.

**Phase C — ongoing:**
11. Watch upstream releases (pin-upgrade cadence quarterly); re-run `openspec validate`/drift check against the store when the pin moves.
12. Re-verify S1–S3 assumptions at each pin bump (debug-log leaks and server binds are the moving parts).

## Unknowns (stated, not guessed)
- The user's actual gateway/device models are unknown; Q3/Q4 answers are capability-level. Per-device DP confirmation is required before wiring the agent.
- No dynamic verification was performed (static policy). Recommend a live smoke test on one device in a maintenance window, followed by `detect_available_dps()` inventory.
- Master's +42 unmerged commits include scanner-robustness fixes relevant to discovery reliability; if discovery is kept in the loop, consider building from a tagged v1.21.x when it lands rather than master.
