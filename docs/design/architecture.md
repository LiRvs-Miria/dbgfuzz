# dbgfuzz design: architecture

> Status: draft (2026-11-18). Scope: how dbgfuzz works internally — components, channels, coverage backends, symbolization, crash handling. For why dbgfuzz exists, read [background](../background.md) (中文：[background.zh-CN.md](../background.zh-CN.md)). 中文镜像：[architecture.zh-CN.md](architecture.zh-CN.md)。

## Components and deployment

dbgfuzz runs on the workstation; a small companion, `lldb-server`, runs on the target side (cross-compiled for the device, or native on Linux targets). Debug info — the ELF/DWARF copy — is a workstation asset. The target runs whatever binary ships: stripped release builds are fine.

```
workstation                                       target
├─ mutation engine                                └─ lldb-server (companion)
├─ coverage engine                                    (Linux: ptrace-based;
├─ symbolization (target ELF + DWARF copy)             RTOS/bare-metal: JTAG gdbserver)
├─ crash handler (stop, capture, replay)
└─ reporting (coverage map, campaign stats)
        ↑
   input driver (user-written; shims for TCP/UDP/serial/file)
```

## Two channels, one brain

The debug channel and the input channel never talk to each other. dbgfuzz owns both connections and sequences them; `lldb-server` and the input driver are both unaware of each other's existence.

**The input channel is the real attack surface.** Fuzz inputs enter through the target's actual interface — network, serial, file — never through the debug channel. Injecting through the debug channel would measure the debug path, not the target.

**Channel separation is permanent**, not an implementation accident: any future feature that blurs the two channels (e.g., "fast mode" that smuggles inputs over the debugger) is rejected by design.

## The fuzz loop over the debug channel

The debug channel speaks the standard LLDB remote protocol (GDB RSP family). One loop iteration:

1. `Z0` packet — set a breakpoint (software or hardware) at address X.
2. `c` packet — resume the target.
3. Input channel — write the fuzz case into the real interface. The input driver is a dumb byte-forwarder; all intelligence lives host-side.
4. Wait for the stop reply. The stop packet carries the stop reason:
   - **Breakpoint hit** → `g` packet reads registers (PC) → update the coverage map → next iteration.
   - **Signal (SIGSEGV/SIGBUS/SIGILL…)** → this is a crash. Do not detach, do not kill: the process stays stopped under debugger control. That stopped process *is* the crash scene.
5. Crash handling — `g` reads all registers, `m` reads stack memory; the host unwinds the call stack. The scene supports step-by-step replay and state inspection.

The reason a crash scene is "live": the process has been under debugger control for its whole life. A crash stops it; nothing kills it.

## Coverage backends

Coverage is tiered; granularity and speed trade against each other, and the choice is per-campaign configuration:

| Backend | Target type | Cost | Granularity |
|---|---|---|---|
| Software breakpoints (ptrace text patching) | Linux targets | medium | function/region-level |
| Hardware breakpoints | real devices (flash/XN targets) | constrained (~6–16 BP slots on ARM) | function-level |
| Single-step | any, key paths only | prohibitive (~10² execs/s) | instruction-level |

Note on flash/XN targets: software breakpoints require patching executable memory, which is impossible when code lives in write-protected flash — hardware breakpoints are the only option there, and slot scarcity makes coverage a budgeted resource.

## Symbolization

Symbolization happens host-side. The workflow: `target create` the unstripped ELF copy on the workstation, connect via `gdb-remote`; the target keeps running the stripped release build. Address → function/line resolution is pure host-side DWARF parsing; the target never cooperates and never carries symbols.

**The one dangerous failure mode**: the workstation's symbol file must be from the *same build* as the binary running on the device. A mismatched DWARF does not error — it silently produces wrong function names. Vendors control their build pipeline and satisfy this naturally; pure reverse-engineering scenarios without a matching file degrade to the address-chain tier, which is still fully coverage-guided.

## Crash handling

A crash is any stop caused by a signal that is not one of our breakpoints. Handling is deliberately boring:

1. Stay attached. The stopped process is the evidence.
2. Capture: general registers, stack memory, the input that fired.
3. Replay: step-by-step replay and state dumps, driven from the captured scene.
4. Only after capture is complete may the campaign move on (or restart the target).

## Constraints and failure modes

- Remote single-stepping is slow — every step is a protocol round trip. Single-step coverage is reserved for key paths; campaigns are targeted/nightly by design.
- Hardware breakpoint slots are scarce; coverage granularity on real devices is a budgeted resource, not a free good.
- `lldb-server` on the target is itself attack surface and footprint: test builds only, never production images.
- Interpreted targets are out of scope: where an interpreter can run, existing interpreter-aware fuzzers (Atheris-class) already win.
- The harness problem (getting bytes into a closed target) is out of scope; dbgfuzz covers everything downstream of the input channel.
