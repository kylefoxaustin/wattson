#!/usr/bin/env bash
# xcheck QEMU side: run one workload under qemu-aarch64 (linux-user) with the
# libinsn + libcache TCG plugins, emit a compact activity JSON on stdout.
# L2 is enabled in the cache model so its misses are the DRAM-transaction proxy.
# Usage: run-qemu.sh <label> -- <binary> [args...]
set -eu
QEMU="${QEMU:-$HOME/Documents/GitHub/95emulator/build-user/qemu-aarch64}"
PI="${PI:-$HOME/Documents/GitHub/95emulator/build-user/tests/tcg/plugins/libinsn.so}"
PC="${PC:-$HOME/Documents/GitHub/95emulator/build-user/contrib/plugins/libcache.so}"
LINE="${LINE:-64}"
LABEL="$1"; shift; [ "$1" = "--" ] && shift
LOG="$(mktemp)"; trap 'rm -f "$LOG"' EXIT
# Cache geometry matched to the i.MX95 A55 path (read from the FRDM's sysfs):
# L1D/L1I 32K 4-way 64B. The plugin's single "l2" models the OUTERMOST level
# before DRAM -- the DSU's shared 512K 16-way L3 -- so l2_miss = DRAM proxy.
# M1: full three-level hierarchy matching the FRDM's sysfs, plus the
# write-streaming model. l3_misses = DRAM READ proxy (same semantics as the
# silicon's l3d_cache_refill); wstream_dram_writes = DRAM WRITE proxy.
GEOM="dcachesize=32768,dassoc=4,dblksize=64,icachesize=32768,iassoc=4,iblksize=64"
GEOM="$GEOM,l2cachesize=65536,l2assoc=4,l2blksize=64"
GEOM="$GEOM,l3=on,l3cachesize=524288,l3assoc=16,l3blksize=64,wstream=on"
[ -n "${PFETCH:-}" ] && GEOM="$GEOM,pfetch=on,pfdegree=${PFETCH}"
[ -n "${CORES:-}" ] && GEOM="$GEOM,cores=$CORES"
"$QEMU" -plugin "$PI" -plugin "$PC",l2=on,$GEOM -d plugin "$@" 2>"$LOG" >/dev/null
python3 - "$LOG" "$LABEL" "$LINE" <<'PY'
import sys, re, json
log, label, line = open(sys.argv[1]).read(), sys.argv[2], int(sys.argv[3])
insns = int(re.search(r"total insns:\s*(\d+)", log).group(1))
# libcache CSV header then one row per core:
# core #, data accesses, data misses, dmiss rate, insn accesses, insn misses, imiss rate, l2 accesses, l2 misses, l2 miss rate
row = None
for ln in log.splitlines():
    m = re.match(r"^0\s+(\d+)\s+(\d+)\s+[\d.]+%\s+(\d+)\s+(\d+)\s+[\d.]+%\s+(\d+)\s+(\d+)\s+[\d.]+%\s*$", ln)
    if m: row = [int(x) for x in m.groups()]; break
if row is None: sys.exit("libcache row not found")
d_acc, d_miss, i_acc, i_miss, l2_acc, l2_miss = row
w = re.search(r"wattson: l3_accesses=(\d+) l3_misses=(\d+) wstream_stores=(\d+) wstream_dram_writes=(\d+) wb_dram_writes=(\d+) wb_dirty_resident=(\d+)(?: pf_issued=(\d+) pf_dram_reads=(\d+))?", log)
if w:
    g = [int(x) if x is not None else 0 for x in w.groups()]
    l3_acc, l3_miss, ws_st, ws_wr, wb_wr, wb_res, pf_iss, pf_rd = g
else:
    l3_acc = l3_miss = ws_st = ws_wr = wb_wr = wb_res = pf_iss = pf_rd = None
print(json.dumps({
  "schema": "wattson/xcheck-qemu/v1", "workload": label,
  "provenance": "DERIVED from QEMU TCG plugins (linux-user); NOT silicon",
  "insns": insns, "l1d_access": d_acc, "l1d_miss": d_miss,
  "l1i_access": i_acc, "l1i_miss": i_miss,
  "l2_access": l2_acc, "l2_miss": l2_miss,
  "l3_access": l3_acc, "l3_miss": l3_miss,
  "wstream_stores": ws_st, "wstream_dram_writes": ws_wr,
  "wb_dram_writes": wb_wr, "wb_dirty_resident": wb_res,
  "pf_issued": pf_iss, "pf_dram_reads": pf_rd,
  "dram_read_proxy": l3_miss,
  "dram_write_proxy": (ws_wr + wb_wr + wb_res) if ws_wr is not None else ws_wr,
  "dram_transactions_proxy": (l3_miss + ws_wr) if l3_miss is not None else l2_miss,
  "dram_bytes_proxy": ((l3_miss + ws_wr) * line) if l3_miss is not None else l2_miss * line}, indent=1))
PY
