"""ptrfuzz command-line entry point (skeleton)."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ptrfuzz",
        description="Coverage-guided fuzzing without sanitizer runtimes.",
    )
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="fuzz a target (M4)")
    p_run.add_argument("--target", help="path to the target binary")
    p_run.add_argument("--corpus", default="corpus", help="corpus directory")
    p_run.add_argument("--backend", default="ptrace-singlestep",
                       choices=["ptrace-singlestep", "lldb", "instrumentation"],
                       help="coverage backend")

    p_cov = sub.add_parser("coverage", help="collect one coverage map (M1)")
    p_cov.add_argument("--target", help="path to the target binary")
    p_cov.add_argument("inputs", nargs="*", help="input files for one run")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    print(f"ptrfuzz: '{args.command}' is not implemented yet (see docs/roadmap.md)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
