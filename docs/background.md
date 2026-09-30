# Background — five minutes

English | [简体中文](background.zh-CN.md)

This page assumes nothing. If you already fuzz daily, skim the glossary
and jump back to the [README](../README.md).

## How coverage-guided fuzzing works — and why it needs the target's help

A fuzzer generates inputs and throws them at a target. Blindly, this is
a needle in a haystack. Coverage feedback is what makes it smart: the
fuzzer tracks *which branches and functions each input reached*, and
spends its effort on inputs that explored something new. Nearly every
production fuzzer (libFuzzer, AFL, honggfuzz, OSS-Fuzz) works this way.

The catch: **the target must report its own coverage**. In practice that
means compiling the target with a sanitizer runtime (ASan/UBSan/TSan) or
at least coverage counters — code and data injected into the target
process, plus a runtime library to collect it.

## The constrained-target reality

Huge classes of interesting targets cannot do that:

- **Embedded Linux / gateways** — no ASan (memory budget, dated glibc),
  no room for instrumentation overhead.
- **Real-time kernels and boards** — missing kernel features (ptrace
  regsets for hardware debug registers, as on many arm64 RT builds),
  only 4–6 hardware breakpoints per thread.
- **Legacy, closed-source binaries** — cannot be recompiled, so no
  instrumentation can be added at all.

Full-system emulation (QEMU) does work everywhere — at a 10–100x
slowdown. The consequence today: **most deployed attack surfaces
(industrial controllers, OT/IoT devices, firmware) have no practical
coverage-guided fuzzing story.** Blind mutation on a protocol parser is
what passes for fuzzing there.

## ptrfuzz's answer

Move coverage collection out of the target:

- **debugger-side backends** — observe the target from outside:
  `PTRACE_SINGLESTEP` (trap after every instruction; universal, slow) or
  hardware breakpoints (fast, scarce), optionally orchestrated through
  [symrepl](https://github.com/LiRvs-Miria/symrepl). Zero recompilation.
- **compiler-side minimal instrumentation** — an LLVM pass that emits a
  coverage bitmap without an ASan-style runtime (the bitmap is read on
  process exit or via the debugger). Fast, needs recompilation.

Same coverage-guided loop as libFuzzer; different place the feedback
comes from. Targets that never had a fuzzer story get one.

## Who is this for

- **Product security teams** fuzzing their own firmware, gateways, and
  protocol parsers on the hardware they actually ship.
- **OT / IoT researchers** auditing device classes the mainstream tools
  cannot reach.
- **QA / reliability engineers** on embedded targets, where "find the
  input that hangs the event loop" matters as much as memory safety.

## Glossary

| Term | Meaning |
|---|---|
| sanitizer runtime (消毒器运行时) | Compiler-injected libraries (ASan/UBSan/TSan) living inside the target to detect bugs and report coverage — what constrained targets cannot host |
| coverage map (覆盖图) | Bitmap/counters recording which branches or basic blocks executed |
| single-step (单步) | Trap after every instruction (`PTRACE_SINGLESTEP`) — works on any target, orders of magnitude slower |
| hw breakpoint (硬件断点) | Address comparators in the CPU's debug registers — fast but scarce (4–6 per thread on typical arm64) |
| corpus (语料库) | The set of interesting inputs the fuzzer keeps and mutates |
