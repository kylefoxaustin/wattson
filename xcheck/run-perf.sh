#!/usr/bin/env bash
#
# xcheck BOARD side: run ON the real i.MX95 (aarch64 Linux) and capture hardware
# PMU counters for the microbench via perf. Emits a HW activity record (JSON) in
# a shape comparable to the QEMU activity vector, so compare.py can check whether
# QEMU's plugin counts track real silicon.
#
# Copy microbench + this script to the board (scp), then run there:
#   ./run-perf.sh alu-50M   -- alu 50000000
#   ./run-perf.sh mem-256x4 -- mem 256 4
#
# Requires perf (linux-tools) on the board. Provenance: MEASURED (real PMU).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="${MICROBENCH:-$HERE/microbench}"
LABEL="$1"; shift
[ "${1:-}" = "--" ] && shift
command -v perf >/dev/null || { echo "perf not found on this board (install linux-tools)" >&2; exit 1; }
[ -x "$BIN" ] || { echo "microbench not built/copied ($BIN)" >&2; exit 1; }

# A robust event set; some may be unavailable on a given PMU (perf reports
# <not supported> and we tolerate it). LLC / last-level misses are the DRAM
# transaction proxy to line up against QEMU's cache-miss count.
EVENTS="instructions,cycles,cache-references,cache-misses,L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses,LLC-stores,LLC-store-misses"
CSV="$(mktemp)"; trap 'rm -f "$CSV"' EXIT

# freq/OPP at run time (for the V^2 f energy side later)
FREQ_KHZ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo 0)
GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown)

perf stat -x, -o "$CSV" -e "$EVENTS" -- "$BIN" "$@" >/dev/null 2>/tmp/xcheck.stdout || true

python3 - "$CSV" "$LABEL" "$FREQ_KHZ" "$GOV" "$*" <<'PY'
import sys, json, csv
csvf, label, freq, gov, args = sys.argv[1:6]
counters = {}
with open(csvf) as f:
    for row in csv.reader(f):
        if len(row) < 3 or row[0].startswith('#') or not row[0]:
            continue
        val, ev = row[0].strip(), row[2].strip()
        try:
            counters[ev] = int(val)
        except ValueError:
            counters[ev] = None            # <not supported> / <not counted>
# DRAM-transaction proxy: last-level misses (loads + stores if available), else cache-misses
llc = 0; have_llc = False
for k in ("LLC-load-misses", "LLC-store-misses"):
    if counters.get(k) is not None:
        llc += counters[k]; have_llc = True
dram_txn = llc if have_llc else counters.get("cache-misses")
out = {
    "schema": "wattson/hw-activity/v1",
    "workload": label,
    "provenance": "MEASURED (real i.MX95 PMU via perf)",
    "note": f"args: {args}; cpu0 {int(freq)/1000:.0f} MHz gov={gov}",
    "freq_khz": int(freq),
    "pmu": counters,
    "activity": {
        "instructions": counters.get("instructions"),
        "cycles": counters.get("cycles"),
        "dram_transactions": dram_txn,       # compare to QEMU dram_transactions_est
        "l1d_load_misses": counters.get("L1-dcache-load-misses"),
    },
}
json.dump(out, sys.stdout, indent=2); print()
PY
