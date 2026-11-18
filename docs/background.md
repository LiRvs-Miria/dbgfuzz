# Background: why ptrfuzz exists

*A five-minute read. 中文版：[background.zh-CN.md](background.zh-CN.md)。*

## The job

You have a binary you cannot rebuild. It runs on real hardware — an IoT device, a vehicle ECU, a PLC, an RTOS task. You want to throw inputs at it, know which paths those inputs actually exercised, and — when it crashes — keep the scene: the call stack, the registers, the memory, right where the debugger stopped it.

No source. No rebuild. No sanitizer runtime. That constraint kills the standard workflow.

## Why the standard tools fall short

**Source-required fuzzers** (libFuzzer, AFL++ with instrumentation) are the gold standard for throughput — if you can rebuild the target. Closed-source firmware and third-party binaries are out of reach.

**Emulation-based fuzzing** (AFL++ QEMU mode) handles bare binaries, but emulation is a model, and models leak: peripherals are missing or approximated, timing is wrong, hardware state does not exist. On x86 you can fall back to Intel PT for trace-based coverage on real silicon. On embedded ARM there is no cheap equivalent — hardware trace (ETM) needs probes and targets most engineers do not have.

**Protocol fuzzers** (boofuzz and friends) generate structured inputs over a channel and detect hangs and crashes. But they walk blind: no feedback on which parser states were reached, so mutation is guesswork, and deep logic past the front door is rarely hit.

## The insight

A debugger is already attached to the problem space. It can single-step any process it can reach. It can set hardware breakpoints. It can read registers and dump memory without asking the target for cooperation.

So use it as the fuzzer's **eyes** — debugger-side coverage feedback for targets that cannot be instrumented — and as the fuzzer's **hands** — when a crash fires, the target is already stopped in the debugger. The scene is not a saved input file you must replay; it is the live process: call stack, registers, memory, queryable in place, replayable step by step through [symrepl](https://github.com/LiRvs-Miria/symrepl).

## The architecture

ptrfuzz runs on your workstation. The target runs a small companion — `lldb-server` — and the two are connected by a debug channel. Fuzz inputs go in through the target's real interface (network, serial, file): the same door the world would use. Two channels, one brain:

```
workstation                                    target
├─ ptrfuzz                                     └─ lldb-server (companion)
│    (fuzzer, coverage, reports)
└─ target binary + debug info copy
        ← debug channel: breakpoints, stops, state reads
        ← input channel (network / serial): the real attack surface
```

What this placement gives you:

1. **Devices stay clean.** They run the stripped release build; the debug info copy lives on your workstation. Devices never need to carry symbols.
2. **Works with or without debug info.** With it, reports show functions and lines; without it, address chains and disassembly. Coverage guidance is unaffected either way.
3. **Crashes are captured, not reproduced.** The whole campaign runs under debugger control, so at crash time the target is already stopped, scene intact. For stateful targets that may never reproduce the same crash twice, capture is the only dependable evidence.

## What each buyer gets

- **Device and RTOS vendors (SDL, CRA compliance).** Build once, keep the unstripped artifact on your side; the devices in your test farm run stripped release builds. Nightly campaigns produce crash scenes with function-level call stacks — and campaign reports double as testing evidence.
- **Security researchers on third-party firmware.** No symbols anywhere? Coverage guidance still steers the fuzzer, and crash scenes come back as address chains with disassembly for triage. A stateful device may never reproduce the same crash twice — live capture beats replay.
- **OT / ICS researchers (PLC runtimes, OPC UA stacks).** Attach to the runtime on the real controller or gateway, inject through the real protocol port, and get crash scenes on the actual stack — not on an emulator that distorts the device.
- **Responders verifying patches.** Pin coverage to the patched region, replay the proof-of-vulnerability inputs, assert the crash path is gone — with state replay to back the claim.

## The niche, stated honestly

ptrfuzz is not competing with libFuzzer or AFL++. If you have source and want throughput, use them — they are faster by orders of magnitude. ptrfuzz serves the intersection:

> **real target + closed source + coverage-guided + cheap triage**

That intersection is real: firmware security research, vendor SDL for shipped binaries (a legal obligation in the EU from December 2027 under the Cyber Resilience Act), and ICS runtime research where the runtime itself is the target.

What ptrfuzz is **not**: a throughput tool. Debugger-side coverage on real hardware is slow, and that is accepted by design — campaigns are targeted and nightly, not bulk. The input-channel harness (getting bytes into a closed target) remains the user's job; ptrfuzz covers everything downstream of the channel.
