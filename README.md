# ptrfuzz

English | [简体中文](README.zh-CN.md)

Coverage-guided fuzzing for targets that cannot run sanitizer runtimes.

ptrfuzz collects coverage on the **debugger side** — via ptrace, hardware
breakpoints, or an LLDB session — and pairs it with **compiler-side
instrumentation** that adds nothing but a coverage map. The result: real
coverage-guided feedback on embedded Linux, RT-kernel, and legacy targets
where ASan/TSan-style runtimes are unavailable.

## Why

Coverage-guided fuzzing today assumes the target can host a sanitizer
runtime. Embedded and RT targets frequently cannot: no ASan, tight memory
budgets, missing kernel features (ptrace regsets, hardware breakpoints),
real hardware. On those targets, fuzzing degenerates to blind mutation or
slow full-system emulation.

ptrfuzz closes that gap with pluggable coverage backends:

- **debugger-side**: single-step / hardware-breakpoint coverage via ptrace
  or an LLDB session — zero recompilation, slow but universal;
- **compiler-side**: LLVM instrumentation emitting a coverage bitmap
  without pulling in a full sanitizer runtime — fast, requires
  recompilation.

## Ecosystem

ptrfuzz is to [symrepl](https://github.com/LiRvs-Miria/symrepl) what Clang
is to LLVM: symrepl provides the debugger-side infrastructure (session
orchestration, breakpoint management, state inspection), and ptrfuzz builds
the fuzzing platform on top of it. From ptrfuzz M2 onward, symrepl is a
library dependency.

## Scope and architecture rule

ptrfuzz consumes **public, standard formats only** — the same firewall as
symrepl (see
[docs/adr/0001-scope-ip-firewall-and-ecosystem.md](docs/adr/0001-scope-ip-firewall-and-ecosystem.md)):

- DWARF debug info, LLVM IR / bitcode
- libFuzzer-compatible corpora and coverage maps
- QEMU (user / system mode) as target runtime

Anything that only makes sense with knowledge of a particular private
codebase or dialect does not belong here.

## Status

Pre-MVP: scaffolding only. See the [roadmap](docs/roadmap.md) — M1
(ptrace single-step coverage baseline) is next.

## Requirements (planned)

- Linux with ptrace (x86-64 / aarch64); QEMU for cross-target runs
- LLVM with SanitizerCoverage-style instrumentation (M3+)
- Python >= 3.10; symrepl (from M2)

## License

Apache-2.0 WITH LLVM-exception — the same license as the LLVM project,
matching the ecosystem ptrfuzz lives in.
