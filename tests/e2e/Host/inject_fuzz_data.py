#!/usr/bin/env python3
"""Input-channel stand-in (stub): pour fuzz data toward the target.

Per plan, no port is opened yet: the payload lands in a local file that a
future target-facing input shim can forward. When the target gains a real
interface (TCP/serial/file), this script becomes the sender -- the seam
dbgfuzz's input driver will occupy. Keep it out of the debug channel.
"""

import argparse
import pathlib
import sys

DEFAULT_PAYLOAD = b"A" * 64


def main():
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(here.parent / "Device" / "fuzz_input.bin"),
                    help="where to pour the payload (file for now, TCP later)")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--payload", help="literal string payload")
    src.add_argument("--hex", help="payload as a hex string")
    src.add_argument("--from-file", help="read payload from this file")
    args = ap.parse_args()

    if args.hex:
        payload = bytes.fromhex(args.hex)
    elif args.from_file:
        payload = pathlib.Path(args.from_file).read_bytes()
    elif args.payload is not None:
        payload = args.payload.encode()
    else:
        payload = DEFAULT_PAYLOAD

    out = pathlib.Path(args.out)
    out.write_bytes(payload)
    print(f"[host] poured {len(payload)} bytes -> {out}")
    print("[host] no transport yet (no port by design); this file is the input-channel seam")
    return 0


if __name__ == "__main__":
    sys.exit(main())
