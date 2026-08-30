#!/usr/bin/env bash
# X2b: full-board (NIC-capable) variant of run-system.sh.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
Q=~/Documents/GitHub/95emu-x2b/build-x2b/qemu-system-aarch64
PI=~/Documents/GitHub/95emu-x2b/build-x2b/tests/tcg/plugins/libinsn.so
PC=~/Documents/GitHub/95emu-x2b/build-x2b/contrib/plugins/libcache.so
SM=~/Documents/nxp/sources/imx-sm/build/mx95evk/m33_image.elf
S=$HERE/sysmode
GEOM="dcachesize=32768,dassoc=4,dblksize=64,icachesize=32768,iassoc=4,iblksize=64"
GEOM="$GEOM,l2cachesize=65536,l2assoc=4,l2blksize=64"
GEOM="$GEOM,l3=on,l3cachesize=524288,l3assoc=16,l3blksize=64,wstream=on,cores=8"
APP="$1"
LOG="$(mktemp)"; trap 'rm -f "$LOG"' EXIT
timeout "${TMO:-3600}" "$Q" -M imx95-19x19-evk -m 2G -display none -serial null \
  -kernel "$S/Image-imx95evk.bin" -dtb "$S/imx95-19x19-evk.dtb" \
  -initrd "$S/xcheck-initramfs.cpio.gz" \
  -device loader,file="$SM",cpu-num=6 \
  -netdev user,id=n0 -device virtio-net-device,netdev=n0 \
  -append "earlycon=lpuart32,mmio32,0x44380010 console=ttyLP0,115200 cpuidle.off=1 rdinit=/init xapp=$APP" \
  -plugin "$PI" -plugin "$PC",$GEOM -d plugin 2>"$LOG" || true
python3 - "$LOG" "$APP" <<'PY'
import sys, re, json
log, app = open(sys.argv[1]).read(), sys.argv[2]
by_cpu = {m.group(1): int(m.group(2)) for m in re.finditer(r"cpu (\d+) insns: (\d+)", log)}
total = int(re.search(r"total insns: (\d+)", log).group(1)) if "total insns" in log else sum(by_cpu.values())
w = re.search(r"wattson: l3_accesses=(\d+) l3_misses=(\d+) wstream_stores=(\d+) wstream_dram_writes=(\d+) wb_dram_writes=(\d+) wb_dirty_resident=(\d+)", log)
vals = (int(x) for x in w.groups()) if w else (None,)*6
l3a, l3m, ws_st, ws_wr, wb_wr, wb_res = vals
print(json.dumps({"schema": "wattson/xcheck-sys/v1", "app": app, "board": "full",
  "provenance": "DERIVED from QEMU system-mode TCG plugins (guest user+kernel+SM)",
  "insns_total": total, "insns_by_cpu": by_cpu,
  "l3_miss": l3m, "wstream_dram_writes": ws_wr, "wb_dram_writes": wb_wr,
  "wb_dirty_resident": wb_res}, indent=1))
PY
