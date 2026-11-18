# ptrfuzz design: core skeleton — Driver/Engine, four dialects, milestones

> Status: draft v2, Driver/Engine split per author ruling (2026-11-18). Scope: module
> decomposition, the four artifact dialects, pass families, build order. Deployment view:
> [architecture.md](architecture.md) (中文: [architecture.zh-CN.md](architecture.zh-CN.md)).
> 中文镜像：[core-modules.zh-CN.md](core-modules.zh-CN.md)。

## Binding decisions

1. **The artifact IR is real MLIR (option a).** Ruling by the author of mlir-opt-fuzzer:
   infrastructure costs (PassManager, verifier, textual round-trip, TableGen) are pre-paid
   expertise. Provenance = pass-pipeline string (`seed S + pipeline P` reproduces the artifact).
2. **Four dialects, not one**: `ptrf.seed` (seeds), `ptrf.mut` (mutants), `ptrf.dbg`
   (debugger-side results: stops, PCs, register dumps, coverage hits), `ptrf.report`
   (reports). The dialect vocabulary is the shared language; the passes are the brains.
3. **Two top-level parts**:
   - **Engine** — the pure MLIR world: the four dialects and all pass families. No sockets,
     no processes. Coverage analysis, mutation transforms, mutation analysis (strategy
     selection driven by `ptrf.dbg`), result analysis, report transforms, corpus store.
   - **Driver** — the live world, three responsibilities: fuzzing-data injection (input
     channel), fuzzed-target result return (stdout/response collection), debug interaction
     (lldb-server: BPs, stops, register/memory reads), plus target lifecycle and crash
     capture mechanics.

## Boundary laws (binding)

1. **The Driver loop is imperative; passes live inside Engine stages.** The loop — take
   mutant bytes → inject → wait debug events → collect results → hand to Engine → apply
   Engine's next pipeline → repeat — is orchestration, not a transform pipeline.
2. **No IR on the per-hit path.** Individual BP hits stay raw address-keyed bitmap math.
   Debug hits are *batched once per run iteration* into `ptrf.dbg` IR and handed to Engine —
   IR at run-batch granularity, never per event.
3. **Every dialect ships a parser/emitter pair.** Targets consume bytes; each dialect lowers
   to wire format and ingests wire bytes back. RawBytes is the default dialect (byte-level
   targets pay zero IR tax); protocol dialects (OPC UA, Modbus, ...) arrive with structured
   targets.
4. **Purity is structural.** Engine links MLIR only — no sockets, no processes. Driver links
   liblldb/OS only — **no MLIR** (default, veto-able): Engine hands Driver lowered bytes and
   pipeline specs; Driver hands Engine raw facts as `ptrf.dbg` IR (built via Engine's parse
   API) plus target results. Review/CI checks include graphs: MLIR headers in Driver or
   socket headers in Engine = rejected.
5. **Single-ABI rule**: one LLVM build in the process — liblldb and MLIR from the same
   LLVM 22 tree (M0 spike verified: MLIR context + SBDebugger co-run, exit 0).

## Modules

```
 ┌────────────────────── CLI / config (thin) ──────────────────────┐
 │                                                                 │
 └──► Driver (the loop; the only live world)     Engine (pure MLIR)
 ┌───────────────────────────┐            ┌───────────────────────────┐
 │ fuzz-loop (imperative)     │ seed IR    │ dialects: seed / mut /     │
 │  ├ input: inject bytes     │ + dbg IR ─►│           dbg / report     │
 │  ├ debug: BP/stops/regs    │◄─ bytes + ─│ passes:                    │
 │  ├ target result return    │  pipeline  │  · mutation transforms     │
 │  ├ lifecycle / restart     │    spec    │  · mutation analysis       │
 │  └ crash capture mechanics │            │    (strategy ← ptrf.dbg)   │
 └───────────────────────────┘            │  · coverage analysis       │
 ┌──────────────┐                          │  · result analysis         │
 │ symbolization │── sites, build-id ────► │  · report transforms       │
 └──────────────┘                          │ corpus store               │
                                           └───────────────────────────┘
```

| Module | Owns | Must-not | Depends |
|---|---|---|---|
| **Driver** | the loop; input injection; target result return; debug interaction (SB API wrapper: BPs, stops, reg/mem reads, stop classification); target lifecycle & restarts; crash capture mechanics | any MLIR (default, veto-able); any strategy/analysis logic | liblldb, OS |
| **Engine** | the four dialects; all pass families (mutation transforms; mutation analysis = strategy selection from `ptrf.dbg`; coverage analysis = map/novelty; result analysis; report transforms); corpus store; hw-slot ledger | sockets, processes, live connections | MLIR |
| **symbolization** | ELF/DWARF asset policy: same-build invariant (build-id), site enumeration, address-chain fallback tier | touching connections (parses the ELF copy directly) | LLVM DWARF libs |
| **reporting / config / CLI** | report serialization, campaign stats, config parsing, entry | holding connections | snapshots (pull model) |

Pass families inside Engine (from the ruling, verbatim intent):

- **mutation transforms** — bitflip/arith/splice/havoc over `ptrf.seed`/`ptrf.mut`
- **mutation analysis** — which strategy next, computed from `ptrf.dbg` (the feedback brain,
  as an MLIR analysis with caching/invalidation)
- **coverage analysis** — `ptrf.dbg` → map/bitmap annotation, novelty signal
- **result analysis** — `ptrf.dbg` + target results → findings/crash classification
- **report transforms** — `ptrf.report` dedup/aggregate/emission forms

## Invariants

1. **The two connections never talk.** Input and debug connections are mechanics inside
   Driver; nothing routes data between them (architecture.md's permanent rejection).
2. **Engine is socket-free; Driver is MLIR-free** (law 4) — the purity boundary is an
   include-graph property, CI-checkable.
3. **Module interfaces are data-shaped**: IR (serialized or in-memory), lowered bytes,
   pipeline specs, plain structs — engines and dialects testable offline.
4. **Regression nets are architecture-congruent**: pure-core net = Engine fed `ptrf.dbg`
   IR directly, no services; probe net = Driver against live lldb-server (the E2E
   environment); manual client stays human acceptance.

## Toolchain (Debian 13, all 22.1.8)

`llvm-22-dev`, `libmlir-22-dev`, `mlir-22-tools` (dev cmake targets reference its binaries),
`liblldb-22-dev`. CMake: `find_package(LLVM REQUIRED CONFIG)` + MLIR CONFIG with
`CMAKE_PREFIX_PATH=/usr/lib/llvm-22`; LLVM's version check is major.minor exact (22.1.8 ≠
"22"); **LLDB ships no cmake package** — link `liblldb-22.so` directly, headers at
`/usr/lib/llvm-22/include`.

## Milestones

- **M0** — skeleton compiles (root CMake: LLVM+MLIR+LLDB linkage, spike already green);
  Driver's debug-interaction half replicates the proven E2E flow via SB API. Oracles live:
  CLI control run + `dap_client.py`.
- **M1** — four dialects minimal forms + RawBytes; first mutation transform + coverage
  analysis pass; Driver loop closed against a stdin-shim parser target.
- **M2** — SIGSEGV target; crash capture (Driver) → `ptrf.report` IR (Engine) with
  provenance strings.
- **M3** — corpus + full mutation transform set + mutation analysis (strategy selection);
  first protocol dialect decision.
- **M4** — symbolization build-id enforcement; hw-BP / single-step tiers behind the site
  ledger; reporting export.
