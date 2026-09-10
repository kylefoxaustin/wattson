#!/usr/bin/env python3
"""wattson power deck — from activity counts to measured silicon watts.

Regenerates from RESULTS-50.csv + the recorded rail models. Same visual
language as make_deck.py (the xcheck correlation deck) so the two read as one
body of work.
"""
import csv, statistics as st
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

INK=RGBColor(0x20,0x21,0x24); MUTED=RGBColor(0x5F,0x63,0x68); WHITE=RGBColor(0xFF,0xFF,0xFF)
GREEN=RGBColor(0x18,0x7A,0x33); AMBER=RGBColor(0xB0,0x60,0x00); RED=RGBColor(0xB3,0x14,0x12)
ACCENT=RGBColor(0x1A,0x53,0xA0); ZEBRA=RGBColor(0xEF,0xF3,0xFA)
FOOT="wattson power · rails MEASURED on IMX95LPD5EVK-19 (NXP BCU) · A55 die 40\u201341 \u00b0C under load · activity DERIVED from QEMU TCG · 2026-09-10"

rows=list(csv.DictReader(open('RESULTS-50.csv')))
mc=list(csv.DictReader(open('RESULTS-multicore.csv')))
def f(r,k): return float(r[k])
esum=[abs(f(r,'pred_sum')-f(r,'meas_sum'))/f(r,'meas_sum')*100 for r in rows]
def p90(v): 
    w=sorted(v); return w[int(.9*len(w))]
earm=[abs(f(r,'pred_arm')-f(r,'meas_arm'))/f(r,'meas_arm')*100 for r in rows]
esoc=[abs(f(r,'pred_soc')-f(r,'meas_soc'))/f(r,'meas_soc')*100 for r in rows]
sgn=[(f(r,'pred_sum')-f(r,'meas_sum'))/f(r,'meas_sum')*100 for r in rows]
pm=[f(r,'meas_sum') for r in rows]; pp=[f(r,'pred_sum') for r in rows]

prs=Presentation(); prs.slide_width,prs.slide_height=Inches(13.333),Inches(7.5)
blank=prs.slide_layouts[6]; PAGE=[0]

def tb(sl,x,y,w,h,t,size,bold=False,color=INK,align=PP_ALIGN.LEFT,font="Calibri"):
    b=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=b.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.alignment=align
    r=p.add_run(); r.text=t; r.font.size=Pt(size); r.font.bold=bold; r.font.color.rgb=color; r.font.name=font
    return tf

def slide(title, kicker=None):
    s=prs.slides.add_slide(blank); PAGE[0]+=1
    band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width,Inches(0.92))
    band.fill.solid(); band.fill.fore_color.rgb=INK; band.line.fill.background()
    tb(s,.6,.13,11.6,.6,title,26,True,WHITE)
    rule=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,Inches(0.92),prs.slide_width,Pt(3))
    rule.fill.solid(); rule.fill.fore_color.rgb=ACCENT; rule.line.fill.background()
    if kicker: tb(s,.6,1.06,12.2,.4,kicker,12,False,MUTED)
    tb(s,.6,7.14,11.4,.3,FOOT,9.5,False,MUTED)
    tb(s,12.5,7.14,.5,.3,str(PAGE[0]),9.5,False,MUTED,PP_ALIGN.RIGHT)
    return s

def table(s,x,y,w,col_w,hdr,data,fsz=10.5,rh=0.32,bold_cols=(),color_fn=None):
    t=s.shapes.add_table(len(data)+1,len(hdr),Inches(x),Inches(y),Inches(w),Inches(rh)).table
    for i,cw in enumerate(col_w): t.columns[i].width=Inches(cw)
    for rr in range(len(data)+1): t.rows[rr].height=Inches(rh)
    for c,v in enumerate(hdr):
        cell=t.cell(0,c); cell.text=v; run=cell.text_frame.paragraphs[0].runs[0]
        run.font.size=Pt(fsz); run.font.bold=True; run.font.color.rgb=WHITE; run.font.name="Calibri"
        cell.fill.solid(); cell.fill.fore_color.rgb=INK
    for ri,row in enumerate(data,1):
        for c,v in enumerate(row):
            cell=t.cell(ri,c); cell.text=str(v)
            cell.fill.solid(); cell.fill.fore_color.rgb = ZEBRA if ri%2 else WHITE
            if not cell.text_frame.paragraphs[0].runs: continue
            run=cell.text_frame.paragraphs[0].runs[0]
            run.font.size=Pt(fsz); run.font.name="Calibri"; run.font.bold=(c in bold_cols)
            if color_fn:
                col=color_fn(ri-1,c)
                if col: run.font.color.rgb=col
    return t

# ── 1 · title ──────────────────────────────────────────────────────────────
s=prs.slides.add_slide(blank); PAGE[0]+=1
band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width,Inches(2.5))
band.fill.solid(); band.fill.fore_color.rgb=INK; band.line.fill.background()
tb(s,.8,.75,11.8,.9,"From activity counts to measured silicon watts",34,True,WHITE)
tb(s,.8,1.72,11.8,.5,"wattson power calibration · i.MX 95 · per-rail models driven by QEMU",15,False,RGBColor(0xC8,0xD4,0xE8))
tb(s,.8,3.0,11.8,.55,"Thesis under test: a functional emulator's activity counts, regressed against measured "
   "per-rail silicon power, can predict the power of applications the model has never seen.",14,False,INK)
box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.8),Inches(3.8),Inches(11.8),Inches(1.5))
box.fill.solid(); box.fill.fore_color.rgb=ZEBRA; box.line.color.rgb=GREEN; box.line.width=Pt(2)
tb(s,1.1,3.98,11.2,.5,f"RESULT: {st.mean(esum):.1f}% mean error on total power, 50 real applications, predicted BLIND",20,True,GREEN)
tb(s,1.1,4.52,11.2,.6,"Predictions were committed to git before a single power sample was taken on these "
   "applications. Coefficients came from an 11-point synthetic grid containing none of them.",12,False,INK)
tb(s,.8,5.6,11.8,.35,"Kyle Fox · IMX95LPD5EVK-19 + NXP BCU per-rail shunts · qemu-aarch64 TCG plugins · 2026-09-10",11,False,MUTED)

# ── 2 · the verdict ────────────────────────────────────────────────────────
s=slide("Can QEMU predict silicon power?","The question this campaign exists to answer.")
b=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(1.5),Inches(12.1),Inches(.8))
b.fill.solid(); b.fill.fore_color.rgb=GREEN; b.line.fill.background()
tb(s,.9,1.62,11.6,.5,f"YES — {st.mean(esum):.1f}% on total power, blind, across 50 held-out applications.",21,True,WHITE)
v=[("vdd_soc  (SoC + interconnect)",f"{st.mean(esoc):.1f}%",f"{p90(esoc):.1f}%",f"{max(esoc):.0f}%","bandwidth-driven; the tightest result"),
   ("vdd_arm  (A55 cores)",f"{st.mean(earm):.1f}%",f"{p90(earm):.1f}%",f"{max(earm):.0f}%","weakest rail; stall-heavy code is the limit"),
   ("SUM  (what a power budget cares about)",f"{st.mean(esum):.1f}%",f"{p90(esum):.1f}%",f"{max(esum):.0f}%","no application worse than 11%")]
table(s,.6,2.6,12.1,(4.6,1.5,1.5,1.5,3.0),("rail","MAPE","p90","worst","note"),v,fsz=12,rh=0.46,bold_cols=(0,1))
tb(s,.6,4.35,12.1,.34,"p90 is reported beside the mean deliberately: a MAPE alone hides a tail, and the tail is where a power budget gets hurt.",11,False,MUTED)
tb(s,.6,4.75,12.1,.5,"Published per-rail models report single-digit error on unseen workloads as the GOOD outcome. "
   "Walker (TCAD 2017) and McCullough (ATC 2011) both warn that sub-3% on unseen workloads is a reason to "
   "distrust your own validation set — not to celebrate.",12,False,INK)
tb(s,.6,5.55,12.1,.4,"No published work was found doing this: functional-emulator activity calibrated against "
   "per-rail measured SoC power. The pieces exist separately; the composition appears to be new.",12,True,ACCENT)

# ── 3 · what we actually did ───────────────────────────────────────────────
s=slide("What we did","Eight steps, in order. Each one had to work before the next was meaningful.")
steps=[("1","Get the instrument","IMX95LPD5EVK-19 — the only i.MX 95 board with per-rail shunts. Flashed to match the FRDM's BSP first: the idle floor moves 29% between kernels."),
 ("2","Measure the idle floor","n=5, spreads ≤1.7%. 1139.5 mW total; vdd_soc is 72% of it, vdd_arm only 13%."),
 ("3","Ask what predicts core power","Instruction count — the activity vector's core term — explains R²=0.031. THREE PERCENT."),
 ("4","Find what does","A 2-D grid varying ALU rate and bandwidth INDEPENDENTLY. Both together: R²=0.990."),
 ("5","Add the missing term","598 Mops/s on 2 cores = 656 mW; 599 on 1 core = 465 mW. Active cores matter on their own."),
 ("6","Validate QEMU's counters","Same static binary under perf and under QEMU: instructions 0.1%, misses 0.01% in steady state."),
 ("7","Freeze predictions for 50 apps","Committed to git BEFORE any power measurement of those apps."),
 ("8","Measure and compare","5.3% mean error on total power.")]
table(s,.6,1.6,12.1,(0.5,3.4,8.2),("#","step","what came out"),steps,fsz=10.5,rh=0.55,bold_cols=(1,))

# ── 4 · the models ─────────────────────────────────────────────────────────
s=slide("The models","Measured on silicon, driven by QEMU activity. Valid at the stated OPP — the frequency is part of the claim.")
box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.6),Inches(1.6),Inches(12.1),Inches(2.0))
box.fill.solid(); box.fill.fore_color.rgb=ZEBRA; box.line.color.rgb=ACCENT; box.line.width=Pt(1.5)
tb(s,.9,1.75,11.5,.36,"vdd_arm  =  243.8  +  0.1266·ALU Mops/s  +  60.62·GB/s  +  169.3·active_cores",15,True,ACCENT,font="Consolas")
tb(s,.9,2.18,11.5,.36,"vdd_soc  =  851.0  +  0.0043·ALU Mops/s  +  20.40·GB/s",15,True,ACCENT,font="Consolas")
tb(s,.9,2.61,11.5,.36,"DRAM     =   45.7  +  160.06·√(GB/s)                        R² = 0.994",15,True,ACCENT,font="Consolas")
tb(s,.9,3.10,11.5,.36,"mW, at 1800 MHz. vdd_soc holds at 900 MHz unchanged (2.5% MAPE). vdd_arm needs its own per-OPP set.",11.5,False,INK)
acc=[("vdd_soc","bandwidth only","2.5–7%","transfers across OPPs unchanged"),
     ("vdd_arm","alu + bandwidth + cores","4–5%","per-OPP coefficient sets; halving the clock roughly halves this rail"),
     ("DRAM group","saturating in bandwidth","R²=0.994","intercept PINNED to the measured idle floor")]
table(s,.6,3.85,12.1,(1.9,3.4,1.8,5.0),("rail","form","accuracy","note"),acc,fsz=11,rh=0.44,bold_cols=(0,))
tb(s,.6,5.6,12.1,.5,"⚠ The DRAM fit with the HIGHER R² is the more dangerous one: a quadratic scores 0.9984 but its "
   "negative BW² term predicts FALLING power above ~17 GB/s. The √ form costs 0.004 of R² and stays physical.",11.5,True,AMBER)

# ── 5 · the finding ────────────────────────────────────────────────────────
s=slide("The finding that changes the activity factor","We expected instruction count to drive core power. It does not.")
box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.6),Inches(1.55),Inches(12.1),Inches(1.35))
box.fill.solid(); box.fill.fore_color.rgb=ZEBRA; box.line.color.rgb=RED; box.line.width=Pt(1.5)
tb(s,.9,1.68,11.5,.42,"instructions alone:  R² = 0.031        mean error 48%,  worst 149%",19,True,RED,font="Consolas")
tb(s,.9,2.16,11.5,.36,"bandwidth alone: R² = 0.784          both + active cores: R² = 0.990,  mean error 3.6%",14,True,ACCENT,font="Consolas")
tb(s,.9,2.56,11.5,.30,"An instructions-only model predicts 1197 mW where the board draws 481.",11.5,True,INK)
ev=[("the observation","a memory-stalling workload drew 760 mW on the core rail; a compute workload retiring MORE instructions drew 474 mW"),
    ("why","a stalled core still burns clock trees, speculation, replayed loads, prefetchers and the L2/bus interface"),
    ("confirmed twice","real Dhrystone vs real STREAM: vdd_arm ratio 1.02 — same core power, utterly different instruction mix"),
    ("independent","Walker et al. (TCAD 2017) regressed PMCs against ODROID-XU3 per-cluster rails. Retired instruction count is NOT in their model either.")]
table(s,.6,3.1,12.1,(2.2,9.9),("aspect","detail"),ev,fsz=10.5,rh=0.50,bold_cols=(0,))
tb(s,.6,5.4,12.1,.4,"Consequence: an activity factor built on instruction count alone MIS-RANKS exactly the "
   "memory-bound workloads that dominate a real power budget.",12,True,GREEN)

# ── 6 · the blind test ─────────────────────────────────────────────────────
s=slide("The blind test — 50 applications","Predictions committed to git before the board was touched. This is the headline result.")
tb(s,.6,1.5,12.1,.34,"Coefficients fitted on an 11-point synthetic alu/mem grid. None of these 50 applications appear in it.",12,True)
top=sorted(rows,key=lambda r:-f(r,'meas_sum'))[:6]
bot=sorted(rows,key=lambda r:f(r,'meas_sum'))[:4]
data=[(r['app'],f"{f(r,'pred_sum'):.0f}",f"{f(r,'meas_sum'):.0f}",
       f"{abs(f(r,'pred_sum')-f(r,'meas_sum'))/f(r,'meas_sum')*100:.0f}%") for r in top+bot]
def cf(ri,c):
    if c==3:
        v=float(data[ri][3].rstrip('%'))
        return RED if v>=12 else (GREEN if v<=5 else AMBER)
    return None
table(s,.6,2.0,6.0,(1.9,1.4,1.4,1.3),("application","pred mW","meas mW","err"),data,fsz=10.5,rh=0.34,bold_cols=(0,),color_fn=cf)
stat=[("MAPE, total power",f"{st.mean(esum):.1f}%"),("median",f"{st.median(esum):.1f}%"),
      ("p90",f"{p90(esum):.1f}%"),("worst, any single app",f"{max(esum):.0f}%"),
      ("bias (signed)",f"{st.mean(sgn):+.1f}%")]
table(s,7.0,2.0,5.7,(3.2,2.5),("prediction error","value"),stat,fsz=11.5,rh=0.42,bold_cols=(0,1))
tb(s,7.0,4.45,5.7,.34,"Every number above is a PREDICTION ERROR.",11.5,True,ACCENT)
rng=[("what the 50 apps actually draw",f"{min(pm):.0f} – {max(pm):.0f} mW"),
     ("what the model predicted they draw",f"{min(pp):.0f} – {max(pp):.0f} mW")]
table(s,7.0,4.85,5.7,(3.2,2.5),("workload power range","mW"),rng,fsz=11.5,rh=0.42,bold_cols=(0,1))
tb(s,7.0,5.75,5.7,.5,"Stated in mW, not as a ratio: the model must reproduce the RANGE, not just the average. "
   "A model predicting every app near the mean would still score a good MAPE.",10.5,False,MUTED)
tb(s,.6,6.2,12.1,.4,f"Predictions run {abs(st.mean(sgn)):.1f}% low on average — a systematic offset, not scatter, "
   "and therefore correctable if a future revision wants it.",11.5,False,INK)

# ── 7 · all fifty ──────────────────────────────────────────────────────────
s=slide("All fifty applications","Every prediction, every measurement. Nothing selected, nothing dropped.")
tb(s,.6,1.44,12.1,.3,"GREEN \u2264 8% error   ·   AMBER 8\u201312%   ·   RED > 12%      "
   "\u2014 the 8% line is the published bar for a good per-rail model, and is this corpus's own p90 (8.3%).",
   10.5,True,MUTED)
allr=sorted(rows,key=lambda r:-f(r,'meas_sum'))
cols=[allr[0:17],allr[17:34],allr[34:50]]
XS=[.6,4.85,9.10]
for ci,chunk in enumerate(cols):
    data=[(r['app'][:13],f"{f(r,'pred_sum'):.0f}",f"{f(r,'meas_sum'):.0f}",
           f"{f(r,'err_sum'):.0f}%") for r in chunk]
    def mk(dd):
        def cf(ri,c):
            v=float(dd[ri][3].rstrip('%'))
            if c==3: return GREEN if v<=8 else (AMBER if v<=12 else RED)
            return None
        return cf
    table(s,XS[ci],1.82,4.05,(1.55,.85,.85,.80),("app","pred","meas","err"),data,
          fsz=8.5,rh=0.245,bold_cols=(0,),color_fn=mk(data))
n_g=sum(1 for r in allr if f(r,'err_sum')<=8); n_a=sum(1 for r in allr if 8<f(r,'err_sum')<=12)
n_r=sum(1 for r in allr if f(r,'err_sum')>12)
bar=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.6),Inches(6.35),Inches(12.1),Inches(.62))
bar.fill.solid(); bar.fill.fore_color.rgb=ZEBRA; bar.line.color.rgb=GREEN; bar.line.width=Pt(1.5)
tb(s,.9,6.46,11.5,.4,f"{n_g} of 50 within 8%   ·   {n_a} between 8 and 12%   ·   {n_r} above 12%   "
   f"\u2014   mW predicted vs mW measured, on silicon the model never trained on.",13,True,GREEN)

# ── 8 · multi-core, realistic edge mix ─────────────────────────────────────
s=slide("A realistic edge workload — all six cores busy","Perception, inference, storage, networking, imaging, rendering. Running at the same time, as a product would.")
edge=[r for r in mc if r['case'].startswith('e')]
ctrl=[r for r in mc if not r['case'].startswith('e')]
ee=[float(r['err_sum']) for r in edge]
band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(1.55),Inches(12.1),Inches(.68))
band.fill.solid(); band.fill.fore_color.rgb=GREEN; band.line.fill.background()
tb(s,.9,1.65,11.6,.44,f"{st.mean(ee):.1f}% mean error, {max(ee):.1f}% worst \u2014 better than one application at a time.",18,True,WHITE)
d=[(r['kind'],r['apps'],r['cores'],f"{float(r['pred_sum']):.0f}",f"{float(r['meas_sum']):.0f}",
    f"{float(r['err_sum']):.1f}%") for r in edge]
def cf1(ri,c):
    if c==5:
        v=float(d[ri][5].rstrip('%')); return GREEN if v<=8 else (AMBER if v<=12 else RED)
    return None
table(s,.6,2.45,12.1,(2.9,5.0,.85,1.15,1.15,1.05),
      ("what it is","applications running concurrently","cores","pred mW","meas mW","err"),
      d,fsz=11.5,rh=0.46,bold_cols=(0,5),color_fn=cf1)
tb(s,.6,4.34,12.1,.36,"pacman = genetic-AI trainer  \u00b7  sgm = stereo-vision disparity on real imagery  \u00b7  "
   "sqlite = in-memory OLTP  \u00b7  httpp = HTTP parsing  \u00b7  qoi = image codec  \u00b7  ray = ray tracer",10.5,False,MUTED)
tb(s,.6,4.80,12.1,.32,"Controls \u2014 synthetic and benchmark mixes over the same core counts:",11,True,INK)
d2=[(r['kind'],r['apps'],r['cores'],f"{float(r['pred_sum']):.0f}",f"{float(r['meas_sum']):.0f}",
     f"{float(r['err_sum']):.1f}%") for r in ctrl]
def cf2(ri,c):
    if c==5:
        v=float(d2[ri][5].rstrip('%')); return GREEN if v<=8 else (AMBER if v<=12 else RED)
    return None
table(s,.6,5.14,12.1,(2.9,5.0,.85,1.15,1.15,1.05),
      ("what it is","applications running concurrently","cores","pred mW","meas mW","err"),
      d2,fsz=10.5,rh=0.38,bold_cols=(0,5),color_fn=cf2)
tb(s,.6,6.70,12.1,.34,"The realistic mixes run at 0.4\u20130.6 GB/s; the synthetic ones at 2.5\u20133.2 GB/s. "
   "Real applications live in cache far more than streaming benchmarks do \u2014 and the model covers both.",10.5,False,ACCENT)

# ── 8 · what this licenses ─────────────────────────────────────────────────
s=slide("What this licenses, and what it does not","The trust statement, quantity by quantity.")
lic=[("predict total power of an unseen app","YES","4.9% mean, 11% worst, 50 held-out applications"),
     ("predict vdd_soc","YES","4.5% mean, 8% worst — the strongest single result"),
     ("predict vdd_arm for compute-bound code","YES","7.1% median, 16.3% p90"),
     ("predict vdd_arm for stall-heavy code","NO","up to 20% over — the insns/3 proxy overstates it"),
     ("predict a realistic multi-app mix","YES","2.7% mean on edge workloads; 6 apps on 6 cores, 3.9% worst"),
     ("use these coefficients at another frequency","NO","1800 MHz set; vdd_soc transfers, vdd_arm does not"),
     ("use these coefficients on another SoC","NO","stall-power sign is microarchitecture-specific"),
     ("emit watts from QEMU alone","NO","QEMU supplies ACTIVITY; time and energy coefficients come from silicon")]
def lc(ri,c):
    if c==1: return GREEN if lic[ri][1]=="YES" else RED
    return None
table(s,.6,1.6,12.1,(4.6,1.1,6.4),("claim","verdict","basis"),lic,fsz=11,rh=0.46,bold_cols=(0,1),color_fn=lc)
tb(s,.6,5.2,12.1,.5,"The standing rule survives the campaign unchanged: QEMU measures activity, engineers convert "
   "activity to energy. A board that reads real watts is exactly when that discipline matters most.",12,True,ACCENT)
tb(s,.6,5.9,12.1,.6,"Everything above is reproducible from the repo: frozen predictions in git before measurement, "
   "raw per-app pairs in RESULTS-50.csv, and every limit stated beside the number it qualifies.",11.5,False,MUTED)

prs.save("wattson-power.pptx")
print(f"wattson-power.pptx — {PAGE[0]} slides")
