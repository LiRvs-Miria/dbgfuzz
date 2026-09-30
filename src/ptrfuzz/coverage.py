"""Coverage backends (skeleton).

Pluggable backends, each producing a coverage map plus a PC→location
mapping derived from DWARF:

- PTraceSingleStepBackend (M1): PTRACE_SINGLESTEP per instruction, map PC
  to source lines via DWARF. Zero recompilation; slow by orders of
  magnitude — the feasibility baseline that proves coverage collection
  works on targets without any runtime support.
- LLDBBackend (M2): hardware breakpoints + session orchestration through
  symrepl (the debugger-side infrastructure this project builds on).
- InstrumentationBackend (M3): LLVM SanitizerCoverage-style inline-8bit
  counters written to a fixed bitmap address — no ASan-style runtime;
  the bitmap is read on process exit or via the debugger.

Open contract (M1): coverage granularity — edge vs basic-block vs line —
should stay libFuzzer-compatible where possible; see docs/roadmap.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CoverageMap:
    """A hit bitmap plus the PC→location table used to interpret it."""

    bitmap: bytes = b""
    locations: tuple[str, ...] = field(default_factory=tuple)


class CoverageBackend:
    """Base class for coverage collection backends."""

    name: str = "base"

    def collect(self, target: str, argv: list[str]) -> CoverageMap:
        """Run `target` once and return its coverage map. (Implemented in M1.)"""
        raise NotImplementedError(f"{self.name} backend lands with M1 — see docs/roadmap.md")
