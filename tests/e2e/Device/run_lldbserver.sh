#!/usr/bin/env bash
# Device side: spawn the target under lldb-server in gdb-remote mode.
# Usage: run_lldbserver.sh <target-binary> [port]
# Runs in the foreground; Ctrl+C tears down lldb-server (and the inferior).
set -euo pipefail

TARGET="$(realpath "$1")"
PORT="${2:-${E2E_PORT:-51317}}"

echo "[device] lldb-server gdbserver 127.0.0.1:${PORT} -- ${TARGET}"
exec lldb-server gdbserver "127.0.0.1:${PORT}" -- "${TARGET}"
