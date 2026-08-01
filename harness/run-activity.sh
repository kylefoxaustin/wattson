#!/usr/bin/env bash
#
# wattson activity-extraction harness.
#
# Runs a workload under qemu-imx95 with the TCG activity plugins (libinsn +
# libcache) and emits a wattson activity vector (JSON) to stdout.
#
# The workload is a flat bare-metal image (-kernel) that MUST terminate with a
# PSCI SYSTEM_OFF so QEMU exits cleanly and the plugins flush their counts (an
# infinite-loop workload never flushes). The workloads/ dir ships two:
# bench-alu (compute-bound) and bench-mem (memory-bound).
#
# Env overrides:
#   QEMU     path to qemu-system-aarch64 (must be built with -Dplugins=true)
#   PLUGINS  dir holding libinsn.so / libcache.so
#   MEM      guest DRAM size (default 2G)
#   TMO      timeout seconds (default 300)
#   LINE     cache line bytes for the byte estimate (default 64)
#
# Usage: run-activity.sh <workload.bin> <label> [note]
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
QEMU="${QEMU:-$HOME/Documents/GitHub/95emulator/build/qemu-system-aarch64}"
PLUGINS_INSN="${PLUGINS_INSN:-$HOME/Documents/GitHub/95emulator/build/tests/tcg/plugins/libinsn.so}"
PLUGINS_CACHE="${PLUGINS_CACHE:-$HOME/Documents/GitHub/95emulator/build/contrib/plugins/libcache.so}"
MEM="${MEM:-2G}"
TMO="${TMO:-300}"
LINE="${LINE:-64}"

BIN="$1"; LABEL="$2"; NOTE="${3:-}"
[ -x "$QEMU" ] || { echo "no qemu at $QEMU (build with -Dplugins=true)" >&2; exit 1; }
[ -f "$BIN" ] || { echo "no workload at $BIN" >&2; exit 1; }

LOG="$(mktemp)"; trap 'rm -f "$LOG"' EXIT
timeout "$TMO" "$QEMU" -M imx95-19x19-evk -nographic -m "$MEM" -kernel "$BIN" \
    -plugin "$PLUGINS_INSN" \
    -plugin "$PLUGINS_CACHE" \
    -d plugin 2>"$LOG" || true

grep -q "total insns:" "$LOG" || { echo "plugins did not flush -- did the workload PSCI-off?" >&2; exit 2; }
python3 "$HERE/parse_activity.py" "$LOG" --workload "$LABEL" --line "$LINE" --note "$NOTE"
