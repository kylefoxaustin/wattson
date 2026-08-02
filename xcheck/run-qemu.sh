#!/usr/bin/env bash
#
# xcheck QEMU side: run the microbench under qemu-aarch64 (linux-user) with the
# TCG activity plugins and emit a wattson activity vector (JSON). This is the
# *same binary* the board runs under perf (run-perf.sh), so the counts are
# directly comparable.
#
# Env:
#   QEMU_USER   path to qemu-aarch64 (linux-user; build with
#               ../configure --target-list=aarch64-linux-user --enable-plugins)
#   PLUGINS_*   libinsn.so / libcache.so (target-agnostic; reuse the softmmu build's)
#   LINE        cache line bytes (default 64)
#
# Usage: run-qemu.sh <label> -- <microbench args...>
#   e.g. run-qemu.sh alu-50M -- alu 50000000
#        run-qemu.sh mem-256x4 -- mem 256 4
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
QEMU_USER="${QEMU_USER:-$HOME/Documents/GitHub/95emulator/build-user/qemu-aarch64}"
PLUGINS_INSN="${PLUGINS_INSN:-$HOME/Documents/GitHub/95emulator/build/tests/tcg/plugins/libinsn.so}"
PLUGINS_CACHE="${PLUGINS_CACHE:-$HOME/Documents/GitHub/95emulator/build/contrib/plugins/libcache.so}"
LINE="${LINE:-64}"
BIN="${MICROBENCH:-$HERE/microbench}"

LABEL="$1"; shift
[ "${1:-}" = "--" ] && shift
[ -x "$QEMU_USER" ] || { echo "no qemu-aarch64 at $QEMU_USER (build linux-user target)" >&2; exit 1; }
[ -x "$BIN" ] || { echo "microbench not built ($BIN); run: aarch64-linux-gnu-gcc -static -O2 -o microbench microbench.c" >&2; exit 1; }

LOG="$(mktemp)"; trap 'rm -f "$LOG"' EXIT
"$QEMU_USER" -plugin "$PLUGINS_INSN" -plugin "$PLUGINS_CACHE" -d plugin \
    "$BIN" "$@" 2>"$LOG" 1>/dev/null || true

grep -q "total insns:" "$LOG" || { echo "plugins did not flush; qemu-user output:" >&2; tail "$LOG" >&2; exit 2; }
python3 "$HERE/../harness/parse_activity.py" "$LOG" \
    --workload "$LABEL" --line "$LINE" --note "qemu-aarch64 linux-user; args: $*"
