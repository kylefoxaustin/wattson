#!/usr/bin/env bash
# afgen — batch activity-factor extraction: N apps in, N activity vectors out.
#
#   afgen.sh <manifest> <outdir> [profile]
#
# Manifest: one app per line,  <label>  <command...>
# (comments with #; commands run from the manifest's directory). Apps must be
# aarch64 Linux binaries that terminate; multi-threaded apps should run with
# OMP_WAIT_POLICY=passive (spin instructions are timing, not work).
#
# Output: <outdir>/<label>.af.json per app + <outdir>/SUMMARY.tsv.
# Counts are per-RUN (what E = sum(e_i x N_i) needs). Rates need a duration
# the power team supplies -- QEMU has no clock worth trusting.
set -eu
MAN="$1"; OUT="$2"; PROFILE="${3:-$(dirname "$0")/imx95.profile}"
QEMU="${QEMU:-$HOME/Documents/GitHub/95emulator/build-user/qemu-aarch64}"
PI="${PI:-$HOME/Documents/GitHub/95emulator/build-user/tests/tcg/plugins/libinsn.so}"
PC="${PC:-$HOME/Documents/GitHub/95emulator/build-user/contrib/plugins/libcache.so}"
. "$PROFILE"
mkdir -p "$OUT"
MDIR="$(cd "$(dirname "$MAN")" && pwd)"
printf "label\tinsns\tdram_rd_txn_est\tdram_wr_txn_est\tdram_rd_bytes_est\tdram_wr_bytes_est\n" > "$OUT/SUMMARY.tsv"
grep -vE '^\s*(#|$)' "$MAN" | while read -r LABEL CMD; do
    echo "── $LABEL" >&2
    LOG="$(mktemp)"
    ( cd "$MDIR" && "$QEMU" -plugin "$PI" -plugin "$PC",$GEOM -d plugin $CMD >/dev/null 2>"$LOG" ) || \
        { echo "   $LABEL FAILED (see $LOG)" >&2; continue; }
    python3 - "$LOG" "$LABEL" "$LINE_BYTES" "$RD_CORRECTION" "$WR_CORRECTION" "$OUT" <<'PY'
import sys, re, json, os
log, label, line, rc, wc, out = open(sys.argv[1]).read(), sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
insns = int(re.search(r"total insns:\s*(\d+)", log).group(1))
w = re.search(r"wattson: l3_accesses=(\d+) l3_misses=(\d+) wstream_stores=(\d+) wstream_dram_writes=(\d+) wb_dram_writes=(\d+) wb_dirty_resident=(\d+)(?: pf_issued=(\d+) pf_dram_reads=(\d+))?", log)
g = [int(x) if x else 0 for x in w.groups()]
l3m, ws_wr, wb_wr, wb_res = g[1], g[3], g[4], g[5]
rd_raw, wr_raw = l3m, ws_wr + wb_wr + wb_res
af = {
 "schema": "wattson/activity-factors/v2", "app": label,
 "provenance": "DERIVED from QEMU linux-user TCG plugins; corrections are the xcheck-MEASURED bridges; NOT silicon measurements",
 "counts_per_run": {
   "instructions": insns,
   "dram_read_txn_raw": rd_raw, "dram_write_txn_raw": wr_raw,
   "dram_read_txn_est": int(rd_raw*rc), "dram_write_txn_est": int(wr_raw*wc),
   "dram_read_bytes_est": int(rd_raw*rc)*line, "dram_write_bytes_est": int(wr_raw*wc)*line},
 "corrections": {"read": rc, "write": wc, "basis": "xcheck vs imx9_ddr0, 2026-08-30"},
 "usage": "energy_per_run = sum(coeff_i x count_i); for POWER divide by a duration YOU measured"}
json.dump(af, open(f"{out}/{label}.af.json", "w"), indent=1)
c = af["counts_per_run"]
print(f"{label}\t{c['instructions']}\t{c['dram_read_txn_est']}\t{c['dram_write_txn_est']}\t{c['dram_read_bytes_est']}\t{c['dram_write_bytes_est']}")
PY
    rm -f "$LOG"
done >> "$OUT/SUMMARY.tsv"
echo "wrote $OUT/SUMMARY.tsv + per-app .af.json" >&2
