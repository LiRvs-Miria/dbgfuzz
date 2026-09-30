# Roadmap

English | [简体中文](roadmap.zh-CN.md)

> The English version is authoritative; both are updated in the same commit.

Milestones are deliberately small: each is 2–3 weekend blocks. Work on
ptrfuzz starts after [symrepl](https://github.com/LiRvs-Miria/symrepl) M2
(DAP infrastructure) — ptrfuzz depends on it from M2 onward.

## M0 — Scaffold (done)

- Repository, license (Apache-2.0 WITH LLVM-exception), CI, scope/IP
  firewall and ecosystem relationship documented in
  [ADR-0001](adr/0001-scope-ip-firewall-and-ecosystem.md).

## M1 — ptrace single-step coverage baseline

- `PTRACE_SINGLESTEP` per instruction; map PC → source lines via DWARF
  (`pyelftools`, the first real dependency).
- Acceptance: on a small C target compiled **without** any sanitizer, the
  single-step backend recovers line coverage on QEMU user mode matching a
  `gcov` ground truth, with the slowdown factor measured and reported
  honestly.
- Freeze the coverage-map contract (granularity: edge / basic-block /
  line; libFuzzer compatibility).

## M2 — LLDB backend via symrepl

- Hardware-breakpoint / trap-flag coverage orchestrated through symrepl's
  session infrastructure; symrepl becomes a library dependency.

## M3 — Compiler-side instrumentation

- LLVM SanitizerCoverage-style inline-8bit counters written to a fixed
  bitmap address — no ASan-style runtime; bitmap read on exit or via the
  debugger. Compare throughput against M1/M2 backends.

## M4 — Fuzzing loop

- Corpus management (libFuzzer-compatible), scheduler, mutator
  integration; crash triage via symrepl replay sessions.

## M5 — aarch64 / RT targets

- QEMU system mode and real-board runs (aarch64 embedded Linux); document
  the target-constraint matrix (what works without ptrace regsets, with
  limited hw breakpoints, etc.).

## Open questions

- **Coverage-map contract (blocks M1):** granularity and encoding — stay
  libFuzzer-compatible where possible; any sidecar format must be
  publicly specified here (see ADR-0001).
- **HW-breakpoint scarcity (blocks M2):** 4–6 debug registers per thread
  on typical arm64; design the breakpoint-recycling strategy before
  relying on it.
