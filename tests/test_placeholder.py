"""Placeholder so CI has a runnable test from day one.

Real tests land with M1:
- coverage-map construction from a synthetic PTRACE_SINGLESTEP trace,
- DWARF PC→line mapping against golden fixtures,
- backend acceptance test on QEMU user mode vs gcov ground truth.
"""

import pytest


@pytest.mark.skip(reason="M1: coverage backend lands with golden fixtures")
def test_collect_coverage_map() -> None:
    assert False
