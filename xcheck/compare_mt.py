#!/usr/bin/env python3
"""X3 analysis: correlation vs thread count. Per (workload, N): i_ratio and
DRAM read/write proxies vs DDR beats."""
import json, glob, re
BEAT = 32
print(f"{'wl':7} {'N':>2} {'i_ratio':>8} {'rd_ratio':>9} {'wr_ratio':>9}   (qemu rd/wr lines vs ddr)")
for wl in ("alumt", "memmt", "sgmmt"):
    for N in (1, 2, 4, 6):
        try:
            q = json.load(open(f"out/{wl}{N}.qemu.json"))
        except Exception:
            continue
        hw_i = None
        try:
            perf = open(f"out/{wl}{N}.perf").read()
            m = re.search(r"^(\d+),,instructions", perf, re.M)
            hw_i = int(m.group(1)) if m else None
        except Exception:
            pass
        rdr = wrr = ""
        try:
            dd = json.load(open(f"out/{wl}{N}.ddr.json"))
            rl = dd["rd_beats_net"] * BEAT // 64
            wlx = dd["wr_beats_net"] * BEAT // 64
            if q.get("dram_read_proxy") and rl > 500_000:
                rdr = f"{q['dram_read_proxy']/rl:9.2f}"
            if q.get("dram_write_proxy") and wlx > 500_000:
                wrr = f"{q['dram_write_proxy']/wlx:9.2f}"
        except Exception:
            pass
        ir = f"{q['insns']/hw_i:8.3f}" if hw_i else "       -"
        print(f"{wl:7} {N:>2} {ir} {rdr:>9} {wrr:>9}")
