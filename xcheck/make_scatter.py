#!/usr/bin/env python3
import json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows = json.load(open("scatter.json"))
BEAT = 32
fig, ax = plt.subplots(figsize=(7.6, 6.8))
xs, ys, ls = [], [], []
for r in rows:
    if not r.get("q_rd") or not r.get("ddr_rd") or r["label"] in ("alu", "net"): continue
    if r["q_rd"] < 1_000_000: continue   # below the DDR noise floor: classified, not fitted
    x = r["ddr_rd"] * BEAT / 64; y = r["q_rd"]
    xs.append(x); ys.append(y); ls.append(r["label"])
lo, hi = min(xs+ys)*0.5, max(xs+ys)*2
ax.plot([lo, hi], [lo, hi], "--", color="#D93025", lw=1.5, label="perfect 1:1")
gm = math.exp(sum(math.log(y/x) for x, y in zip(xs, ys))/len(xs))
ax.plot([lo, hi], [lo*gm, hi*gm], ":", color="#5F6368", lw=1.5, label=f"fit: proxy = {gm:.2f} × DDR")
ax.scatter(xs, ys, s=90, color="#4C8BF5", zorder=5)
for x, y, l in zip(xs, ys, ls):
    ax.annotate(l, (x, y), textcoords="offset points", xytext=(8, -4), fontsize=10)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("silicon DRAM reads — DDR-controller beats × 32 B / 64 B lines (MEASURED)")
ax.set_ylabel("QEMU DRAM-read proxy — modelled L3 misses (DERIVED)")
ax.set_title("QEMU DRAM-read proxy vs the DDR controller, per application")
ax.legend(loc="upper left", frameon=False)
ax.grid(alpha=.25, which="both")
fig.tight_layout(); fig.savefig("scatter.png", dpi=150)
print("wrote scatter.png, fit", round(gm, 3))
