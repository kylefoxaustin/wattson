#!/usr/bin/env python3
"""xcheck compare (M1+): read-side proxy vs silicon L3 refills, write proxy,
instruction validation, fitted correction factor, and scatter.json for the deck.
QEMU counts DERIVED; PMU counts MEASURED; ratios are the labelled bridge."""
import json, glob, math

rows = []
for qf in sorted(glob.glob("out/*.qemu.json")):
    label = qf.split("/")[-1].replace(".qemu.json", "")
    try:
        q, h = json.load(open(qf)), json.load(open(f"out/{label}.hw.json"))
    except Exception:
        continue
    d = dict(label=label, qi=q["insns"], hi=h.get("instructions"),
             q_rd=q.get("dram_read_proxy"), q_wr=q.get("dram_write_proxy"),
             h_rd=h.get("l3d_cache_refill"), cyc=h.get("cycles"))
    try:
        dd = json.load(open(f"out/{label}.ddr.json"))
        d["ddr_rd"], d["ddr_wr"] = dd.get("rd_beats_net"), dd.get("wr_beats_net")
    except Exception:
        d["ddr_rd"] = d["ddr_wr"] = None
    rows.append(d)

# DDR beats: 32B/beat measured on this part (mem sweep: 537MB read = 17.0M
# beats). DDR lines = beats/2. l3d_cache_refill counts only DEMAND refills, so
# the DDR controller is the true DRAM ground truth; the refill column is kept
# to show the prefetch gap.
BEAT = 32
print(f"{'workload':8} {'i_ratio':>8} | {'q_rd_lines':>12} {'ddr_rd_lines':>12} {'RATIO':>7} {'l3_refill':>11} | {'q_wr_lines':>11} {'ddr_wr_lines':>12} {'wr_ratio':>8}")
lr = []
for r in rows:
    ir = r["qi"]/r["hi"] if r["hi"] else None
    ddr_rdl = r["ddr_rd"]*BEAT//64 if r["ddr_rd"] else None
    ddr_wrl = r["ddr_wr"]*BEAT//64 if r["ddr_wr"] else None
    rr = (r["q_rd"]/ddr_rdl) if (r["q_rd"] and ddr_rdl) else None
    wrr = (r["q_wr"]/ddr_wrl) if (r["q_wr"] and ddr_wrl) else None
    # Fit only apps with traffic clearly above the DDR noise floor (~0.4M
    # lines/window, calibrated by alu, a true-zero app). Below it the proxy's
    # job is classification -- "DRAM-quiet" -- and each of those is checked
    # separately. net is excluded: kernel+DMA traffic is invisible to
    # linux-user QEMU (its own finding).
    if rr and r["q_rd"] >= 1_000_000 and r["label"] not in ("alu", "net"):
        lr.append(math.log(rr))
    print(f"{r['label']:8} {ir:8.3f} | {r['q_rd'] if r['q_rd'] is not None else 0:>12,} "
          f"{ddr_rdl if ddr_rdl else 0:>12,} {f'{rr:7.2f}' if rr else '      -'} "
          f"{r['h_rd'] if r['h_rd'] else 0:>11,} | "
          f"{r['q_wr'] if r['q_wr'] is not None else 0:>11,} {ddr_wrl if ddr_wrl else 0:>12,} "
          f"{f'{wrr:8.2f}' if wrr else '       -'}")
if lr:
    gm = math.exp(sum(lr)/len(lr))
    sd = math.exp((sum((x-math.log(gm))**2 for x in lr)/len(lr))**0.5)
    print(f"\nDRAM-read proxy vs DDR controller, apps above the noise floor "
          f"(geo-mean over {len(lr)}): {gm:.2f}  x/÷ {sd:.2f} (geo-sd)")
    quiet = [r2["label"] for r2 in rows if r2["q_rd"] is not None and r2["q_rd"] < 1_000_000
             and r2["label"] != "net"]
    print(f"DRAM-quiet apps, proxy correctly < 1M lines (silicon at/near its "
          f"noise floor): {', '.join(quiet)}")
json.dump(rows, open("scatter.json","w"), indent=1)
print("wrote scatter.json")
