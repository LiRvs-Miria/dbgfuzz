# E2E test environment: Device / Host

> Status: **live** (2026-11-18). Split along the deployment line in
> [design/architecture.md](../../docs/design/architecture.md): **Device** = the side where
> `lldb-server` runs (target), **Host** = the side where LLDB runs (workstation). The Host
> Python script stands in for ptrfuzz core (C++), which does not exist yet.
>
> Verified end to end on this machine: remote attach → breakpoint stop in `greet()` →
> stack trace → resume through 5 breakpoint hits → exit → clean disconnect. (`lldb` /
> `lldb-server` / `lldb-dap` 22.1.8, Debian 13.)

## Layout

```
Device/   lldb-server side (target stand-in)
  helloworld.cpp      test target (-g: line table needed for DAP breakpoints; greet() = BP symbol, loop of 5)
  CMakeLists.txt      builds helloworld + `spawn` custom target that runs lldb-server
  run_lldbserver.sh   the spawn script; standalone or via the cmake target
Host/     lldb-dap side (ptrfuzz stand-in, Python stdlib only)
  dap_client.py       DAP driver over stdio: initialize -> attach(gdb-remote) -> breakpoint stop -> stack -> exit
  inject_fuzz_data.py input-channel stub: pours fuzz data to a file; opens no port (by design)
```

## Run (two shells)

```sh
# terminal 1 -- device side
cd tests/e2e/Device
cmake -S . -B build && cmake --build build
cmake --build build --target spawn      # or: ./run_lldbserver.sh build/helloworld

# terminal 2 -- host side
python3 tests/e2e/Host/dap_client.py --port 51317 --program tests/e2e/Device/build/helloworld
```

Exit 0 + `[host] PASS: ...` = debug channel closed loop verified. Port: script arg / env
`E2E_PORT` / cmake `-DE2E_PORT=...` (default 51317). `--attach-pid PID` is a diagnostic
variant that bypasses gdb-remote entirely.

## lldb-dap 22.1.8 field notes (paid for in debugging time — read before extending)

- **Request sequencing is NOT "send attach, wait response".** The official client's order:
  send attach (fire-and-forget) → wait `initialized` event → send breakpoint requests →
  `configurationDone` → *then* the attach response arrives. Waiting on the response first
  deadlocks the session (every thread parked on a futex, no console output).
- **Breakpoints must be set inside `attachCommands`** (e.g. `breakpoint set -n greet`, bound
  during handler execution before any resume). A `setBreakpoints` sent before the target
  exists is queued and never binds (`verified: false` forever); after the attach response the
  process has already auto-resumed — too late.
- **Wire-format quirks vs upstream docs.** The arg validator wants top-level `program`,
  `attachCommands`, `pid`, `coreFile`, and **kebab-case `gdb-remote-port`** (the error message
  lists them); the release/22.x sources show camelCase `gdbRemotePort` + nested
  `configuration` — this Debian build sits mid-way through the upstream protocol rework.
  Unknown fields are tolerated, so both spellings can be sent when in doubt.
- **After `configurationDone` the process auto-resumes.** An entry stop (`reason: exception`,
  SIGSTOP at the dynamic loader) may arrive before the resume; `continue` on an already-running
  process fails with `notStopped` — treat it as expected, not an error.
- `stopOnEntry` (both camelCase and kebab-case) was **not honored** for attach on this build.
- **Symbol vs line breakpoints:** without `-g`, a line breakpoint cannot bind (no line table);
  symbol breakpoints work regardless. The CLI control used `b greet` and masked this.
- The only working connection mode is stdio (`--connection listen://` also exists but was not
  needed); `lldb-dap --help` with no stdin attached will hang — it reads stdio.

## Design notes

- **Transport.** Host drives `lldb-dap` as a stdio subprocess (DAP framing: Content-Length +
  JSON, ~80 lines of protocol code, stdlib only). lldb-dap then speaks RSP to lldb-server —
  same topology as the architecture doc (lldb on the workstation, lldb-server on the target).
- **Remote attach** uses `attachCommands` (`platform select remote-linux`, `target create`,
  `gdb-remote 127.0.0.1:PORT`, `breakpoint set -n greet`). The command echo streams back as
  `output` events and doubles as a progress trace.
- **Channel separation.** One connection per channel: `dap_client.py` owns the debug path only;
  `inject_fuzz_data.py` is the input-channel seam and deliberately opens no port yet. When the
  target gains a real interface (TCP/serial), it becomes the fuzz-data sender — never the
  debug channel.
- **CMake spawn.** `add_custom_target(spawn ... USES_TERMINAL)` runs the spawn script in the
  foreground; a long-running server as a build target is fine as a terminal task (Ctrl+C stops
  it). Answer to "can CMake do it": yes — it is just a custom target invoking the script.
- **Known cosmetic gap:** the DAP client does not verify packet-level fields it does not use
  (checksum-free DAP framing is standard; the earlier raw-RSP client plan was dropped when the
  plan moved to DAP).

## Open items

- `inject_fuzz_data.py` has no transport yet: helloworld reads no input. First input-channel
  step = give the target a stdin/TCP shim, then pour fuzz data across it while the debug
  channel holds the process — the two-channel choreography ptrfuzz core will own.
- Crash-path target (SIGSEGV variant) for exercising the crash-scene flow comes with the first
  core increment.
