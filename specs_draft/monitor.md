# Capability: monitor

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d836 (2026-07-06). | Pass 3 (scenario-ification) applied 2026-11-09

## Summary
The monitor attaches to live device traffic and reports status changes in real time. Two shapes exist: the experimental `Monitor` class (`tinytuya/core/Monitor.py`, #713) — a single-thread, multi-device reactor over `selectors` with callbacks, thread-safe command dispatch, per-device heartbeats and optional auto-reconnect — and the classic single-device monitor loop (persistent socket + status/heartbeat/receive cycle) exposed as the CLI `monitor` command and examples. Frame parsing and payload decryption are delegated to the protocol-crypto layer (`parse_header`/`unpack_message` and `device._decode_payload`); Monitor keeps its own buffered prefix-scanning wrapper, a documented duplication of `XenonDevice._receive()`.

## Primary code locations
- `tinytuya/core/Monitor.py` — selectors-based multi-device monitor reactor, connector thread, command queue (916 lines)
- `tinytuya/cli.py` — `_monitor_device()`: single-device persistent-connection monitor loop for `tinytuya monitor`
- `tinytuya/__main__.py` — `monitor` subcommand registration
- `examples/monitor_example.py`, `examples/monitor_poll_example.py` — threaded and manual-poll usage
- `examples/monitor.py` — classic single-device status/heartbeat/receive loop

## Requirements

### Requirement: Single-thread multi-device monitoring via selectors
The `Monitor` class SHALL watch any number of devices on one OS thread using `selectors` (select/poll/epoll), with no asyncio and no per-device threads; all socket I/O for monitored devices happens on the reactor thread.
- Status: VERIFIED
- Evidence: commits [835514c1d96d] Add Monitor class — single-thread multi-device status monitoring; doc: README.md:432, DESIGN.md:98
- Anchor: `tinytuya/core/Monitor.py:158-168` (class docstring), `tinytuya/core/Monitor.py:190` (DefaultSelector), `tinytuya/core/Monitor.py:461-482` (reactor `_run` loop)

#### Scenario: Watch many devices on one thread
- **WHEN** a `Monitor` is created to watch any number of Tuya devices
- **THEN** all device I/O is handled on a single OS thread via `selectors` (`select`/`poll`/`epoll`) with callback-driven updates
- **AND** no asyncio, no per-device threads and no new dependencies are required
- Source: [relnote v1.19.0] "Single-thread, multi-device status monitoring using selectors"
- Source: [relnote v1.19.0] "Watch any number of Tuya devices on one OS thread with callback-driven updates"
- Source: [relnote v1.19.0] "No asyncio, no per-device threads, no new dependencies"

### Requirement: add() establishes the persistent connection up front
`Monitor.add(device)` SHALL force persistent-socket mode and perform one blocking connect — including the 3.4/3.5 session-key handshake — before registering the socket with the selector, returning a proxy handle on success or the error string on failure; re-adding an already-registered device SHALL return a proxy without reconnecting.
- Status: VERIFIED
- Evidence: commits [835514c1d96d]; doc: README.md:430-480 (usage: "add() connects and returns a proxy handle"), API.md § Persistent Connection Monitor Pattern (API.md:1043-1060)
- Anchor: `tinytuya/core/Monitor.py:223-295` (add; persist at 251-252, blocking connect comment + call at 254-256, duplicate-guard at 246-248)

#### Scenario: add() connects and returns a proxy handle
- **WHEN** a device is registered with `mon.add(device)`
- **THEN** add() connects and returns a proxy handle for the device
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "add() connects and returns a proxy handle"

### Requirement: Callback-based output with per-device overrides and error containment
Status, connect and disconnect events SHALL be delivered through `on_status(device, result)` / `on_connect(device, error)` / `on_disconnect(device, error)` callbacks, configurable globally and overridable per device; `on_disconnect` is opt-in, and exceptions raised inside any callback SHALL be logged, never propagated into the reactor.
- Status: VERIFIED
- Evidence: commits [9102a3eb446f] docs: add Monitor class section to README, showcase on_disconnect opt-in; doc: README.md:434-440 (Key features), README.md:486 ("The on_disconnect callback is opt-in")
- Anchor: `tinytuya/core/Monitor.py:874-896` (_fire_status/_fire_connect/_fire_disconnect with per-state override and try/except), `tinytuya/core/Monitor.py:95-98` (callback type contract)

#### Scenario: Status updates arrive via callback
- **WHEN** a monitored device sends a status update
- **THEN** the update is delivered in real time through the `on_status` callback
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "Real-time status updates through callbacks"
- Source: [relnote v1.19.0] "callback-driven updates (on_status, on_connect, on_disconnect)"

#### Scenario: Disconnects without an on_disconnect callback
- **WHEN** a monitored device disconnects and no `on_disconnect` callback was provided
- **THEN** the disconnect is logged silently, since the callback is opt-in
- **AND** when the callback is provided, it receives the device object and error string
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "The on_disconnect callback is opt-in — if you don't pass it, disconnects are logged silently"
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "you receive the device object and error string"

### Requirement: Buffered frame reassembly with prefix resynchronization
The monitor SHALL accumulate socket bytes per device, locate the 55AA or 6699 prefix (discarding leading garbage), parse the header to get `total_length`, dispatch only complete frames, and resynchronize (skip to the next prefix / drop the buffer) when the stream exceeds any legal frame size without a parseable header.
- Status: VERIFIED
- Evidence: commits [835514c1d96d], [27aa6986ed52] fix: correct 16 verified bugs across Cloud, core, Bulb, scanner, Monitor; doc: DESIGN.md:98 (Monitor framing mirrors `_receive()`), DESIGN.md:117 (duplication risk)
- Anchor: `tinytuya/core/Monitor.py:506-576` (_process_buffer; prefix search 522-536, corrupt-stream resync 546-564)

#### Scenario: Frame assembly via prefix scanning and header parsing
- **WHEN** bytes arrive on a monitored persistent socket
- **THEN** the monitor assembles frames from non-blocking buffered reads using prefix scanning and header parsing
- Source: doc: DESIGN.md § Key Design Decisions "duplicates `_receive()`'s framing logic for non-blocking buffered reads"
- Source: doc: DESIGN.md § Known Architectural Debt "two independent implementations of prefix scanning and header parsing"

### Requirement: Per-message decoding contract delegated to protocol-crypto
Each complete frame SHALL be unpacked via the shared `unpack_message`/`parse_header` helpers with `hmac_key = device.local_key` only for protocol ≥ 3.4; 6699/GCM frames failing authentication SHALL be dropped undecoded; null-payload frames (heartbeat acks) SHALL be ignored; surviving payloads SHALL be decoded with the device's own `_decode_payload`. This matches the per-version "Monitoring requires key" rules (3.1: no key; 3.2/3.3: key; 3.4/3.5: key after session handshake).
- Status: VERIFIED
- Evidence: commits [835514c1d96d], [8169204ef606] fix(Monitor): address Copilot review findings; doc: PROTOCOL.md:12-18 (comparison table), PROTOCOL.md:252 ("Monitoring requires key: Yes (after handshake)")
- Anchor: `tinytuya/core/Monitor.py:71-74` (imports from message_helper), `tinytuya/core/Monitor.py:578-613` (_decode_and_dispatch; hmac gate 583, GCM-auth drop 594-598, null-payload skip 601-603)

#### Scenario: Unauthenticated GCM frames are rejected
- **WHEN** a 6699/GCM frame fails its authentication tag
- **THEN** the frame is rejected instead of being passed on as raw ciphertext
- Source: [relnote v1.20.0] "6699/GCM frames that fail their authentication tag are rejected instead of being passed on as raw ciphertext"

#### Scenario: Decryption key requirement by protocol version
- **WHEN** traffic from a protocol 3.4/3.5 device is monitored
- **THEN** decoding requires the key, which is available only after the session-key handshake
- **AND** monitoring a protocol 3.1 device requires no key
- Source: doc: PROTOCOL.md § Version 3.4 "Monitoring requires key: Yes (after handshake)"
- Source: doc: PROTOCOL.md § Version 3.1 "Monitoring requires key: No"

### Requirement: Per-device heartbeat maintenance by the reactor
The reactor SHALL send a heartbeat (`device.heartbeat(nowait=True)`) to every monitored device whose interval has elapsed (default 12 s, overridable globally or per device), treating a send failure or vanished socket as a disconnect.
- Status: VERIFIED
- Evidence: commits [835514c1d96d]; doc: README.md:434-440 ("Built-in heartbeat management per device"), README.md:463 (`heartbeat_interval=12`), API.md:1043-1060 (heartbeat keeps connection alive)
- Anchor: `tinytuya/core/Monitor.py:654-680` (_send_heartbeats/_do_heartbeat), `tinytuya/core/Monitor.py:180-186` (heartbeat_interval default 12), `tinytuya/core/Monitor.py:223-234` (per-device override)

#### Scenario: Periodic heartbeat keeps connections alive
- **WHEN** a monitored device's heartbeat interval (default 12 s) elapses
- **THEN** the monitor sends that device a heartbeat to keep the persistent connection alive
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "Built-in heartbeat management per device"
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "heartbeat_interval=12"

#### Scenario: Failed heartbeat is treated as a disconnect
- **WHEN** a heartbeat send fails because the socket vanished
- **THEN** the failure is detected as a disconnect and routed through the disconnect -> auto-reconnect path
- Source: [relnote v1.20.0] "Heartbeat and queued-command send failures are now detected (vanished socket) and routed through the disconnect"
- Source: test: tests.py::TestMonitorReliability::test_heartbeat_failure_disconnects_and_enqueues_reconnect

### Requirement: Fail-fast retry ownership while monitored
While a device is registered, the monitor SHALL force its socket retry limit to 0 so failed sends fail immediately instead of blocking the reactor or silently opening replacement sockets, saving and restoring the device's original limit on removal, stop, and during blocking reconnects.
- Status: VERIFIED
- Evidence: commits [0d66872ffd97] fix(Monitor): make reconnection reliable and non-blocking; bump to v1.20.0, [8169204ef606]
- Anchor: `tinytuya/core/Monitor.py:120-124` (saved_retry_limit), `tinytuya/core/Monitor.py:276-282` (force 0), `tinytuya/core/Monitor.py:327-328` (restore on remove), `tinytuya/core/Monitor.py:759-768` (restore/re-force around reconnect connect)

#### Scenario: Monitored devices fail fast on send errors
- **WHEN** a monitored device hits a send error
- **THEN** the device is forced to fail fast (`socketRetryLimit = 0`) instead of blocking the single reactor thread
- **AND** a broken connection cannot silently open a replacement socket the selector never watches
- Source: [relnote v1.20.0] "Monitored devices are forced to fail fast on send errors"
- Source: [relnote v1.20.0] "silently open a replacement socket the selector never watches"

#### Scenario: Original retry limit is handed back
- **WHEN** a device is removed or the Monitor is stopped
- **THEN** the device's original socket retry limit is restored
- Source: [relnote v1.20.0] "Retry limits are restored when a device is removed or the Monitor is stopped"
- Source: test: tests.py::TestMonitorReliability::test_add_forces_fail_fast_and_remove_restores

### Requirement: Thread-safe command dispatch, non-blocking only
Commands queued from any thread SHALL execute on the reactor thread and always use `nowait=True`; explicitly requesting `nowait=False` SHALL raise `ValueError`, and `nowait` shall be injected only into methods that accept it (introspection-guarded). Commands for unregistered or not-yet-active devices SHALL be dropped with a warning, never sent mid-handshake.
- Status: VERIFIED
- Evidence: commits [835514c1d96d], [8169204ef606] fix(Monitor): address Copilot review findings (nowait introspection)
- Anchor: `tinytuya/core/Monitor.py:330-355` (command(); ValueError 343-347), `tinytuya/core/Monitor.py:79-92` (_accepts_nowait), `tinytuya/core/Monitor.py:829-861` (_drain_queue; fileno-gate 841-847)

#### Scenario: Commands from any thread run on the reactor
- **WHEN** a command is sent from any thread via a proxy handle
- **THEN** it is queued thread-safely and dispatched on the reactor thread
- **AND** the command proxy only injects `nowait=True` for methods that accept it
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "Thread-safe command dispatch — send commands from anywhere via proxy handles"
- Source: [relnote v1.20.0] "the command proxy only injects `nowait=True` for methods that accept it"

#### Scenario: Command for a not-yet-active device is dropped
- **WHEN** a queued command targets a device whose socket is mid-handshake or not registered with the selector
- **THEN** dispatch is gated on selector registration state rather than the device socket, so the command is not sent
- Source: [relnote v1.20.0] "Command dispatch is gated on selector registration state rather than `device.socket`"
- Source: test: tests.py::TestMonitorReliability::test_command_dropped_when_device_not_active

### Requirement: socketpair wake-up of the blocking select
The reactor SHALL be interruptible from other threads via a `socket.socketpair()` self-pipe registered with the selector (chosen over `os.pipe()` for Windows SelectSelector compatibility), written on command enqueue and on stop.
- Status: VERIFIED
- Evidence: commits [0d66872ffd97] make reconnection reliable and non-blocking, [835514c1d96d]
- Anchor: `tinytuya/core/Monitor.py:194-199` (socketpair wake registration), `tinytuya/core/Monitor.py:865-870` (_wake), `tinytuya/core/Monitor.py:353-355` and `tinytuya/core/Monitor.py:397-399` (wake on command/stop)

#### Scenario: Queueing a command wakes the blocked reactor
- **WHEN** a user command is marshalled from another thread while the selector blocks
- **THEN** a socketpair wake interrupts the wait so the reactor picks up the queued command
- Source: doc: DESIGN.md § Key Design Decisions "marshalling user commands via a locked queue + socketpair wake"

### Requirement: Optional background auto-reconnect
With `auto_reconnect=True`, a daemon connector thread SHALL reconnect disconnected devices after an interruptible backoff (default 5.0 s), hand successful sockets to the reactor for selector re-registration via a queue, re-enqueue on failure, fire `on_connect` after re-registration, and use interruptible waits so `stop()` is not delayed or raced by a second connector.
- Status: VERIFIED
- Evidence: commits [f3629a1f5985] Add Monitor auto_reconnect connector thread, [0d66872ffd97] make reconnection reliable and non-blocking; bump to v1.20.0, [121b23d41ee2] README: add auto_reconnect=True to Monitor class example; doc: README.md:434-440, README.md:496
- Anchor: `tinytuya/core/Monitor.py:180-188` (auto_reconnect/reconnect_backoff defaults), `tinytuya/core/Monitor.py:726-784` (_run_connector), `tinytuya/core/Monitor.py:785-825` (_process_register_queue), `tinytuya/core/Monitor.py:716-722` (enqueue on disconnect)

#### Scenario: Automatic reconnection on disconnect
- **WHEN** a monitored device disconnects with `auto_reconnect=True`
- **THEN** the monitor reconnects the device automatically
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "Automatic reconnection on disconnect"

#### Scenario: stop() is not delayed by reconnect backoff
- **WHEN** `stop()` is called while the connector thread is waiting in its reconnect backoff
- **THEN** stop() returns promptly because the connector thread uses an interruptible wait for its backoff
- **AND** a duplicate connector thread can no longer start
- Source: [relnote v1.20.0] "The auto-reconnect connector thread uses an interruptible wait for its backoff, so `stop()` returns promptly instead of blocking"
- Source: [relnote v1.20.0] "can no longer let a duplicate connector thread start"

### Requirement: Manual poll mode without the reactor thread
Callers SHALL be able to drive the same reactor steps (queue drain, register queue, heartbeats, one `select()`) from their own loop via `Monitor.poll(timeout)` instead of `start()`.
- Status: VERIFIED
- Evidence: commits [835514c1d96d]; doc: README.md:440 ("Optional manual poll mode"), README.md:502 (examples/monitor_poll_example.py)
- Anchor: `tinytuya/core/Monitor.py:438-457` (poll)

#### Scenario: Drive the monitor from an existing event loop
- **WHEN** an application integrates monitoring into its own loop instead of starting a background thread
- **THEN** the optional manual poll mode drives the monitor (no background thread)
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "Optional manual poll mode for integration into existing event loops"
- Source: doc: README.md § Multi-Device Monitor (Monitor Class) "manual poll mode (no background thread)"

### Requirement: Gateway sub-device routing in the decode pipeline
When a monitored gateway has children, decoded results carrying a `cid` SHALL be routed to the matching child: the child caches/processes the response and the status callback fires with the child device object (using the child's own registered state, or a derived copy if the child is not separately registered).
- Status: VERIFIED
- Evidence: commits [835514c1d96d], [27aa6986ed52]; doc: API.md § Gateway / Sub-Device Pattern (API.md:1063+)
- Anchor: `tinytuya/core/Monitor.py:615-650` (CID routing in _decode_and_dispatch)

#### Scenario: Sub-device status routed by cid
- **WHEN** a decoded result from a monitored gateway carries a cid identifying a sub-device behind it
- **THEN** gateway/cid routing delivers the update to the matching child device
- Source: [relnote v1.19.0] "gateway/cid routing"
- Source: doc: API.md § Gateway / Sub-Device Pattern "node_id / cid is the sub-device node ID"

### Requirement: Deterministic shutdown
`stop()` SHALL halt the reactor and connector threads (join with timeout), close every device socket, restore each device's original retry limit — including devices mid-reconnect — clear the reconnect/register queues, and leave devices reusable by the caller.
- Status: VERIFIED
- Evidence: commits [0d66872ffd97], [8169204ef606]
- Anchor: `tinytuya/core/Monitor.py:393-436` (stop), `tinytuya/core/Monitor.py:900-916` (__del__ safety net)

#### Scenario: stop() restores retry limits of already-disconnected devices
- **WHEN** `stop()` is called and a monitored device had already disconnected
- **THEN** that device's original socketRetryLimit is restored rather than left forced to 0
- Source: test: tests.py::TestMonitorReliability::test_stop_restores_retry_limit_for_disconnected_devices
- Source: [relnote v1.20.0] "Retry limits are restored when a device is removed or the Monitor is stopped"

### Requirement: Experimental status with self-contained framing
The Monitor SHALL be presented as experimental: its API and internals are not frozen, and it intentionally duplicates `XenonDevice._receive()` framing behavior pending a shared frame-codec refactor extracted from protocol-crypto.
- Status: VERIFIED
- Evidence: commits [f40dfb2110f8] Add Experimental note for Monitor Class, [d3bdd7078583] release notes for Monitor + community fixes; doc: README.md:430 (⚠️ Experimental), DESIGN.md:112, DESIGN.md:117
- Anchor: `tinytuya/core/Monitor.py:13-17` (module docstring note), `tinytuya/core/Monitor.py:162-164` (class docstring note)

### Requirement: CLI single-device monitor loop
The `tinytuya monitor` command SHALL connect with a persistent socket, print initial status, then loop: full status request every 30 s, heartbeat every 12 s when idle, otherwise listen for async updates via `receive()`; a receive error SHALL rate-limit retries with a 5 s sleep.
- Status: VERIFIED
- Evidence: commits [2a5ebf934067] Move CLI into new file and add monitor command, [cec1830af19a] Use persistent sockets for CLI monitor, [49dfafe96ba4] fix: correct argument description in CLI and improve device monitoring logic; doc: README.md:690-699, README.md:740-741
- Anchor: `tinytuya/cli.py:258-300` (_monitor_device; timers 265-266, loop 275-298), `tinytuya/__main__.py:58` (subcommand)

#### Scenario: tinytuya monitor persistent update loop
- **WHEN** `tinytuya monitor` is run against a device
- **THEN** it connects, prints the initial status, then enters a persistent loop that listens for asynchronous updates, sends a heartbeat every 12 seconds, and polls for a full status refresh every 30 seconds
- **AND** pressing Ctrl-C exits the loop
- Source: doc: README.md § Command Line "Connects to the device, prints the initial status, then enters a persistent loop that listens for asynchronous updates, sends a heartbeat every 12 seconds, and polls for a full status refresh every 30 seconds"
- Source: doc: README.md § Command Line "Press Ctrl-C to exit"

## Known gaps
- Framing duplication is a live contract risk, not just a note: `Monitor._process_buffer` and `XenonDevice._receive()` must be kept in sync manually until the shared codec extraction lands (DESIGN.md:112, :117). Requirement text here records the delegation to `parse_header`/`unpack_message` that the code actually performs; the "framing to protocol-crypto" ownership phrasing in recon notes is aspirational at this pin.
- `add()`/`remove()` mutate the selector directly and must run on the reactor-driving thread (or before `start()`); cross-thread registration is an open follow-up tracked in code as #713 (`tinytuya/core/Monitor.py:300-304`). Not a requirement — unsupported at the pin.
- No UDP/sniffer capture in Monitor: "attach to device traffic" means persistent TCP connections only. The old UDP-broadcast monitoring lives in the discovery capability (scanner), not here.
- Heartbeat ACK correlation is absent: acks are only skipped as null payloads (`tinytuya/core/Monitor.py:600-603`); silent-dead devices are detected via heartbeat send failures, not missed-ACK timeouts — timeout-based liveness not located.
- `__del__`-based cleanup (`tinytuya/core/Monitor.py:900-916`) is best-effort and interpreter-shutdown-order dependent; explicit `stop()` is the contract, doc silence noted.

## Scenario-ification notes
- REQ "Experimental status with self-contained framing": no doc-grounded trigger; kept as invariant. (Experimental status and the `_receive()` framing duplication are documented in README, DESIGN.md and the v1.19.0 release note as standing properties and refactoring plans, not as any WHEN -> outcome behavior.)
- REQ "Buffered frame reassembly with prefix resynchronization": partial — scenario covers prefix scanning/header parsing (DESIGN.md); the discard-leading-garbage and resynchronize/drop-buffer outcomes are code-only, found in no Tier A/B/C text.
