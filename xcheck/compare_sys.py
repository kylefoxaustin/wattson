#!/usr/bin/env python3
"""X2a: boot-differential analysis. App activity = sys(app) - sys(null),
A55 cpus (0-5) only; the M33's SM spin is reported separately, not subtracted
into app numbers. Kernel share = 1 - user_insns/differential."""
import json
null = json.load(open("out/sys-null.json"))
def a55(d): return sum(v for k, v in d["insns_by_cpu"].items() if int(k) < 6)
def m33(d): return d["insns_by_cpu"].get("6", 0)
n_a55, n_l3 = a55(null), null["l3_miss"]
print(f"{'app':8} {'diff insns (A55)':>17} {'user insns':>15} {'kernel share':>13} {'diff l3miss':>12} {'M33 delta':>12}")
USER = {"sha256": "out/sha8.qemu.json", "chase": "out/chase.qemu.json", "sgm": "out/sgmmt4p.qemu.json"}
for app, uf in USER.items():
    try:
        s = json.load(open(f"out/sys-{app}.json")); u = json.load(open(uf))
    except Exception:
        continue
    di = a55(s) - n_a55
    dl3 = (s["l3_miss"] or 0) - (n_l3 or 0)
    ks = 1 - u["insns"]/di if di else 0
    print(f"{app:8} {di:>17,} {u['insns']:>15,} {ks:>12.1%} {dl3:>12,} {m33(s)-m33(null):>12,}")
