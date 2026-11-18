# dbgfuzz

Coverage-guided fuzzing for targets that cannot run a sanitizer runtime: closed-source binaries, embedded firmware, RTOS tasks, real devices.

**Fuzz inputs. Watch for crashes. Keep the crash scene — call stack, registers, memory — exactly as the debugger left it.**

## Background

Classic fuzzing tools all break down somewhere:

- **libFuzzer / AFL++** need source or rebuildable instrumentation. Fast, but blind to anything you cannot recompile.
- **QEMU-mode fuzzing** reaches bare binaries but distorts device behavior: peripherals, timing, and hardware state go missing. On embedded ARM there is no cheap hardware-trace alternative.
- **Protocol fuzzers** (boofuzz and friends) inject structured inputs but walk blind — no coverage feedback.

Meanwhile a debugger sits right there. It can single-step, set hardware breakpoints, read registers and dump memory on any process it can attach to — including the ones no fuzzer can instrument.

dbgfuzz turns that debugger into the fuzzer's eyes and hands: coverage feedback for black-box targets, and a live crash scene the moment something breaks.

The full story lives in [docs/background.md](docs/background.md) (中文版：[docs/background.zh-CN.md](docs/background.zh-CN.md)).

## What you get

1. **Directed inputs for black-box targets.** Debugger-side coverage (single-step, hardware breakpoints, LLDB sessions) tells the mutation engine which paths were actually hit. No source, no rebuild, no sanitizer.
2. **Crash = live scene.** When a crash fires, the target is already stopped in the debugger. Call stack, registers, and memory are queryable in place, with step-by-step replay built in. No lost state, no reproduce-from-input-file ritual.

## Use cases

| Scenario | Who | Why dbgfuzz |
|---|---|---|
| Closed-source firmware on real hardware (IoT / automotive / medical) | Device security teams, researchers | Real-device behavior QEMU cannot model; ARM lacks cheap trace hardware |
| Hardware-in-the-loop testing (RTOS targets) | Vendor SDL teams | EU CRA applies from Dec 2027: vendors must test shipped binaries without sanitizer builds |
| Deep targeted testing (patch verification, hypothesis-driven) | Security responders | Coverage pinned to a region; crash scene and replay built in |
| ICS runtime / protocol fuzzing (FORTE, OpenPLC, OPC UA stacks) | OT security research | Real runtime semantics + coverage guidance (boofuzz walks blind) |
| Coverage feedback without rebuilding | Teams without coverage pipelines | Debugger-side coverage map, no recompilation |

Not a competitor to libFuzzer/AFL++: if you have source and want throughput, use them. dbgfuzz serves the intersection *real target + closed source + coverage-guided + cheap triage*.

## Status

Scaffolded; design in progress. Docs: this file (authoritative English) + [`README.zh-CN.md`](README.zh-CN.md) (Chinese mirror) + [background](docs/background.md) ([中文](docs/background.zh-CN.md)).
