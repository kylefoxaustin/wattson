#!/usr/bin/env python3
"""The 50-app verdict: do the corrections fitted on 14 apps hold on the
held-out population? Reads from the pf pass, writes from the base pass,
DDR-controller ground truth, noise-floor classification as established."""
import json, glob, math, re, sys

TRAIN = {"alu","mem","chase","mm","sort","sgm","bzip2","lz4","lua","sha256","cjson","sqlite","pacman","net"}
BEAT = 32
RD_FLOOR = 1_000_000
rows = []
for hf in sorted(glob.glob("out50/*.hw.json")):
    label = hf.split("/")[-1].replace(".hw.json","")
    try:
        h = json.load(open(hf))
        pf = json.load(open(f"out50/{label}.pf.json"))
        base = json.load(open(f"out50/{label}.base.json"))
        dd = json.load(open(f"out50/{label}.ddr.json"))
    except Exception:
        continue
    rows.append(dict(label=label, train=label in TRAIN,
        ir=pf["insns"]/h["instructions"] if h.get("instructions") else None,
        q_rd=pf.get("dram_read_proxy"),
        q_wr=(base.get("wstream_dram_writes") or 0)+(base.get("wb_dram_writes") or 0)+(base.get("wb_dirty_resident") or 0),
        d_rd=dd["rd_beats_net"]*BEAT//64, d_wr=dd["wr_beats_net"]*BEAT//64))

def geo(vals):
    ls = [math.log(v) for v in vals]
    gm = math.exp(sum(ls)/len(ls))
    sd = math.exp((sum((x-math.log(gm))**2 for x in ls)/len(ls))**0.5)
    return gm, sd, len(ls)

print(f"{'app':13} {'set':5} {'i_ratio':>8} {'rd_ratio':>9} {'wr_ratio':>9}")
stats = {}
for r in sorted(rows, key=lambda r: (not r["train"], r["label"])):
    rr = r["q_rd"]/r["d_rd"] if (r["q_rd"] and r["q_rd"]>=RD_FLOOR and r["d_rd"]) else None
    wr = r["q_wr"]/r["d_wr"] if (r["q_wr"] and r["q_wr"]>=RD_FLOOR and r["d_wr"]) else None
    grp = "TRAIN" if r["train"] else "HOLD"
    stats.setdefault(grp, {"i":[], "r":[], "w":[]})
    if r["ir"]: stats[grp]["i"].append(r["ir"])
    if rr: stats[grp]["r"].append(rr)
    if wr: stats[grp]["w"].append(wr)
    print(f"{r['label']:13} {grp:5} {r['ir']:8.3f} {f'{rr:9.2f}' if rr else '        -'} {f'{wr:9.2f}' if wr else '        -'}")

print()
for grp in ("TRAIN","HOLD"):
    s = stats.get(grp, {})
    for key, name in (("i","insns"),("r","reads"),("w","writes")):
        if s.get(key):
            gm, sd, n = geo(s[key])
            print(f"{grp:5} {name:7}: geo {gm:.3f}  x/÷ {sd:.2f}  (n={n})")
json.dump(rows, open("out50/scatter50.json","w"), indent=1)
print("wrote out50/scatter50.json")
