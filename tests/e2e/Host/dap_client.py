#!/usr/bin/env python3
"""Host-side DAP driver -- Python stand-in for the future dbgfuzz core.

Drives lldb-dap over stdio (standard DAP framing: Content-Length + JSON).
lldb-dap then speaks RSP to lldb-server on the Device side over the debug
channel. This script owns the debug channel only; fuzz data goes through
inject_fuzz_data.py (the input-channel seam, no port yet by design).
"""

import argparse
import json
import os
import pathlib
import queue
import shutil
import subprocess
import sys
import threading
import time

TIMEOUT = 10.0


def find_lldb_dap():
    p = shutil.which("lldb-dap")
    if p:
        return p
    for cand in ("/usr/lib/llvm-22/bin/lldb-dap", "/usr/lib/llvm-21/bin/lldb-dap"):
        if os.path.exists(cand):
            return cand
    sys.exit("[host] lldb-dap not found (looked in PATH and /usr/lib/llvm-*/bin)")


class DapSession:
    """Minimal stdio DAP session: framing, request/response matching, events."""

    def __init__(self, proc):
        self.proc = proc
        self.seq = 1
        self.messages = queue.Queue()
        self.stash = []  # messages seen while waiting for something else
        self.write_lock = threading.Lock()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    def _read_loop(self):
        f = self.proc.stdout
        try:
            while True:
                length = self._read_headers(f)
                if length is None:
                    self.messages.put({"type": "event", "event": "__eof__"})
                    break  # EOF
                body = f.read(length)
                self.messages.put(json.loads(body))
        except Exception as exc:
            self.messages.put(
                {"type": "event", "event": "__reader_error__", "body": repr(exc)}
            )

    @staticmethod
    def _read_headers(f):
        length = None
        while True:
            line = f.readline()
            if not line:
                return None
            text = line.decode("utf-8", "replace").strip()
            if not text:
                break  # blank line ends the header block
            key, _, val = text.partition(":")
            if key.strip().lower() == "content-length":
                length = int(val.strip())
        return length

    def send(self, command, arguments=None):
        with self.write_lock:
            msg = {"seq": self.seq, "type": "request", "command": command}
            if arguments is not None:
                msg["arguments"] = arguments
            self.seq += 1
            self.last_request_seq = msg["seq"]
            body = json.dumps(msg).encode()
            self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
            self.proc.stdin.flush()
        print(f"--> {command}")
        return msg["seq"]

    def _take(self, pred, timeout):
        deadline = time.time() + timeout
        while True:
            for i, m in enumerate(self.stash):
                if pred(m):
                    return self.stash.pop(i)
            remaining = deadline - time.time()
            if remaining <= 0:
                kinds = [f"{m.get('type')}:{m.get('event') or m.get('command')}"
                         for m in self.stash]
                raise TimeoutError(
                    f"timed out waiting for DAP message; stashed={kinds}")
            try:
                m = self.messages.get(timeout=remaining)
            except queue.Empty:
                kinds = [f"{m.get('type')}:{m.get('event') or m.get('command')}"
                         for m in self.stash]
                raise TimeoutError(
                    f"timed out waiting for DAP message; stashed={kinds}")
            if m.get("type") == "event" and m.get("event") == "__reader_error__":
                raise RuntimeError(f"lldb-dap stream error: {m.get('body')}")
            if m.get("type") == "event" and m.get("event") == "__eof__":
                raise RuntimeError("lldb-dap stream ended (lldb-dap exited?)")
            # live console echo: shows how far lldb-dap got before stalling
            if m.get("type") == "event" and m.get("event") == "output":
                sys.stdout.write(m.get("body", {}).get("output", ""))
                sys.stdout.flush()
            if pred(m):
                return m
            self.stash.append(m)

    def wait_response(self, seq, label="request", timeout=TIMEOUT):
        resp = self._take(
            lambda m: m.get("type") == "response" and m.get("request_seq") == seq,
            timeout,
        )
        if not resp.get("success"):
            raise RuntimeError(f"{label} failed: {resp.get('message') or resp.get('body')}")
        print(f"<-- {label} ok")
        return resp.get("body") or {}

    def request(self, command, arguments=None, timeout=TIMEOUT):
        seq = self.send(command, arguments)
        return self.wait_response(seq, label=command, timeout=timeout)

    def wait_event(self, *names, timeout=TIMEOUT):
        ev = self._take(
            lambda m: m.get("type") == "event" and m.get("event") in names, timeout
        )
        print(f"<-- ev {ev.get('event')}")
        return ev

    def drain_output(self, quiet=0.5):
        """Print queued target/console output events (best effort)."""
        while True:
            try:
                m = self.messages.get(timeout=quiet)
            except queue.Empty:
                return
            if m.get("type") == "event" and m.get("event") == "__reader_error__":
                raise RuntimeError(f"lldb-dap stream error: {m.get('body')}")
            if m.get("type") == "event" and m.get("event") == "output":
                sys.stdout.write(m.get("body", {}).get("output", ""))
            else:
                self.stash.append(m)


def main():
    ap = argparse.ArgumentParser(description="E2E debug-channel probe: DAP requests to lldb-dap")
    ap.add_argument("--port", type=int, default=51317,
                    help="lldb-server gdb-remote port on the device side")
    ap.add_argument("--program", required=True, help="target binary built on the Device side")
    ap.add_argument("--source",
                    default=str(pathlib.Path(__file__).resolve().parent.parent
                                / "Device" / "helloworld.cpp"))
    ap.add_argument("--lldb-dap", default=None, help="path to lldb-dap (default: autodetect)")
    ap.add_argument("--init-commands", default="",
                    help="comma-separated LLDB commands -> lldb-dap initCommands")
    ap.add_argument("--attach-cmds", default="",
                    help="comma-separated LLDB commands -> lldb-dap attachCommands")
    ap.add_argument("--attach-pid", type=int, default=None,
                    help="attach by system pid (bisection path: no gdb-remote, no launch)")
    args = ap.parse_args()

    lldb_dap = args.lldb_dap or find_lldb_dap()
    program = pathlib.Path(args.program).resolve()
    if not program.exists():
        sys.exit(f"[host] program not found: {program}")

    proc = subprocess.Popen(
        [lldb_dap, "--no-lldbinit"],  # deterministic probe: never source user init files
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,  # pass through: lldb-dap diagnostics are evidence
    )
    session = DapSession(proc)

    try:
        # 1. initialize
        session.request("initialize", {
            "adapterID": "dbgfuzz-e2e",
            "clientID": "dbgfuzz-host",
            "locale": "en",
        })

        # 2. attach through the debug channel: lldb-dap connects to lldb-server.
        # Debian lldb-dap 22.1.8 wire quirks (validated against its own error
        # message): it expects 'program'/'attachCommands'/'pid'/'coreFile' as
        # TOP-LEVEL keys and the port as kebab-case 'gdb-remote-port' -- an
        # intermediate state of the upstream protocol rework. Newer/older
        # builds use camelCase gdbRemotePort and/or nested "configuration";
        # we send both spellings of the harmless fields to stay portable.
        program_str = str(program)
        conf: dict = {"program": program_str}
        attach_args: dict = {"program": program_str, "configuration": conf}
        if args.init_commands:
            init_cmds = [c.strip() for c in args.init_commands.split(",")]
            attach_args["initCommands"] = init_cmds
            conf["initCommands"] = init_cmds
        if args.attach_pid:
            attach_args["pid"] = args.attach_pid
        else:
            # Breakpoint goes INSIDE attachCommands: it binds during handler
            # execution, before any resume. A setBreakpoints queued before the
            # target exists never binds on this build, and after the response
            # the process has already auto-resumed -- too late.
            cmds = args.attach_cmds.split(",") if args.attach_cmds else [
                "platform select remote-linux",
                f"target create {program_str}",
                f"gdb-remote 127.0.0.1:{args.port}",
                "breakpoint set -n greet",
            ]
            attach_args["attachCommands"] = [c.strip() for c in cmds if c.strip()]
        attach_seq = session.send("attach", attach_args)
        session.wait_event("initialized", timeout=20.0)
        session.request("configurationDone")
        session.wait_response(attach_seq, label="attach", timeout=30.0)

        # 3. resume; the breakpoint was bound inside attachCommands before any
        # resume, so the next stop must be greet(). The entry stop (reason=exception)
        # may arrive first -- continue past non-breakpoint stops.
        tid = None
        bp_hit = False
        for _ in range(4):
            ev = session.wait_event("stopped", "exited", "terminated", timeout=20.0)
            if ev.get("event") in ("exited", "terminated"):
                break
            body = ev.get("body", {})
            reason = body.get("reason")
            tid = body.get("threadId") or tid
            print(f"    stopped: reason={reason}")
            if reason == "breakpoint":
                bp_hit = True
                break
            if tid:
                try:
                    session.request("continue", {"threadId": tid}, timeout=5.0)
                except RuntimeError as exc:
                    print(f"    (process already running: {exc}; waiting for next stop)")
        if not bp_hit:
            print("[host] FAIL: never stopped at greet() breakpoint")
            return 1

        if tid is None:
            threads = session.request("threads").get("threads", [])
            tid = threads[0].get("id") if threads else 1
        trace = session.request("stackTrace", {"threadId": tid, "startFrame": 0, "levels": 10})
        for i, fr in enumerate(trace.get("stackFrames", [])):
            print(f"    #{i} {fr.get('name')}  {fr.get('source', {}).get('path', '?')}:{fr.get('line')}")
        if trace.get("stackFrames") and "greet" not in str(trace["stackFrames"][0].get("name")):
            print("[host] FAIL: expected to stop in greet()")
            return 1

        # 5. continue to exit; the greet() breakpoint fires once per loop
        # iteration (5 stops), so keep consuming intermediate breakpoint stops
        for _ in range(6):
            session.request("continue", {"threadId": tid})
            ev = session.wait_event("stopped", "exited", "terminated", timeout=15.0)
            if ev.get("event") in ("exited", "terminated"):
                break
            tid = ev.get("body", {}).get("threadId") or tid
            print(f"    stopped again: reason={ev.get('body', {}).get('reason')}")
        session.drain_output()

        # 6. clean shutdown
        session.request("disconnect", {"terminateDebuggee": False})
        proc.terminate()
        proc.wait(timeout=5)
        print("[host] PASS: attach -> breakpoint stop -> stack trace -> continue -> exit -> disconnect")
        return 0
    finally:
        proc.kill()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
