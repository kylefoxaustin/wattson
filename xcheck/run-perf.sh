#!/usr/bin/env sh
# xcheck silicon side: run one workload under perf stat on the board, pinned to
# one core, and emit a compact JSON of MEASURED PMU counts.
# Usage: run-perf.sh <label> -- <binary> [args...]
set -eu
LABEL="$1"; shift; [ "$1" = "--" ] && shift
EV="instructions,cycles,cache-misses,l1d_cache,l1d_cache_refill,l2d_cache,l2d_cache_refill,l3d_cache,l3d_cache_refill"
OUT="$(mktemp)"
taskset -c 0 perf stat -x, -e "$EV" -o "$OUT" -- "$@" >/dev/null 2>&1 || true
awk -F, -v label="$LABEL" 'BEGIN {
    printf "{\n \"schema\": \"wattson/xcheck-hw/v1\",\n \"workload\": \"%s\",\n \"provenance\": \"MEASURED PMU counts on i.MX95 FRDM (A55 core 0, pinned)\",\n", label }
  /^[0-9<]/ {
    v=$1; ev=$3; gsub(/[^a-z0-9_-]/, "_", ev)
    if (v ~ /^</) printf " \"%s\": null,\n", ev
    else          printf " \"%s\": %s,\n", ev, v }
  END { print " \"end\": 1\n}" }' "$OUT"
rm -f "$OUT"
