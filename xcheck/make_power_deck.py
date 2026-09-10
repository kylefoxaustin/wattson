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
FOOT="wattson power · rails MEASURED on IMX95LPD5EVK-19 (NXP BCU) · activity DERIVED from QEMU TCG · 2026-09-10"

rows=list(csv.DictReader(open('RESULTS-50.csv')))
def f(r,k): return float(r[k])
esum=[abs(f(r,'pred_sum')-f(r,'meas_sum'))/f(r,'meas_sum')*100 for r in rows]
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
tb(s,.9,1.62,11.6,.5,"YES — 5.3% on total power, blind, across 50 held-out applications.",21,True,WHITE)
v=[("vdd_soc  (SoC + interconnect)",f"{st.mean(esoc):.1f}%",f"{max(esoc):.0f}%","bandwidth-driven; the tightest result"),
   ("vdd_arm  (A55 cores)",f"{st.mean(earm):.1f}%",f"{max(earm):.0f}%","needs ALU rate, bandwidth AND active cores"),
   ("SUM  (what a power budget cares about)",f"{st.mean(esum):.1f}%",f"{max(esum):.0f}%","5.3% mean, 4.9% median")]
table(s,.6,2.6,12.1,(5.0,1.7,1.6,3.8),("rail","MAPE","worst","note"),v,fsz=12,rh=0.46,bold_cols=(0,1))
tb(s,.6,4.5,12.1,.5,"Published per-rail models report single-digit error on unseen workloads as the GOOD outcome. "
   "Walker (TCAD 2017) and McCullough (ATC 2011) both warn that sub-3% on unseen workloads is a reason to "
   "distrust your own validation set — not to celebrate.",12,False,INK)
tb(s,.6,5.3,12.1,.4,"No published work was found doing this: functional-emulator activity calibrated against "
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
     ("vdd_arm","alu + bandwidth + cores","4–5%","per-OPP coefficients; scales 2.21x per 2x clock"),
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
ev=[("the observation","a memory-stalling workload drew 1.6x the core power of a compute workload retiring MORE instructions"),
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
      ("worst",f"{max(esum):.0f}%"),("bias (signed)",f"{st.mean(sgn):+.1f}%"),
      ("predicted spread",f"{max(pp)/min(pp):.2f}x"),("measured spread",f"{max(pm)/min(pm):.2f}x")]
table(s,7.0,2.0,5.7,(3.2,2.5),("statistic","value"),stat,fsz=11.5,rh=0.42,bold_cols=(0,1))
tb(s,7.0,4.9,5.7,.9,"The SPREAD check was written into the prediction file in advance, precisely because a good "
   "MAPE can hide an under-responsive model. It is under-responsive: 1.37x predicted vs 1.56x measured.",11,False,AMBER)
tb(s,.6,6.2,12.1,.4,"Predictions run 3.9% LOW on average — a correctable offset, deliberately left uncorrected so "
   "the frozen model is reported exactly as it was frozen.",11.5,False,INK)

# ── 7 · where it breaks ────────────────────────────────────────────────────
s=slide("Where it breaks, and why that was predicted","The worst cases are diagnostic, not random.")
bad=[("bb-grep","493","324","52%"),("bb-awk","483","322","50%"),("chase","443","369","20%"),("chase-big","445","383","16%")]
table(s,.6,1.6,7.2,(2.2,1.7,1.7,1.6),("application","pred vdd_arm","meas vdd_arm","err"),bad,fsz=11.5,rh=0.42,bold_cols=(0,))
tb(s,8.1,1.65,4.6,1.6,"All four are LATENCY-BOUND: pointer chasing and irregular text processing, where the core "
   "stalls constantly. bb-grep and bb-awk are the only two apps in the corpus under 1200 mW.",11.5,False,INK)
box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.6),Inches(3.6),Inches(12.1),Inches(1.5))
box.fill.solid(); box.fill.fore_color.rgb=ZEBRA; box.line.color.rgb=AMBER; box.line.width=Pt(1.5)
tb(s,.9,3.75,11.5,.4,"This is the assumption the prediction file flagged IN ADVANCE as most likely to hurt.",14,True,AMBER)
tb(s,.9,4.20,11.5,.75,"ALU Mops/s was taken as insns/3, because the calibration grid's \"ALU op\" was a 3-instruction "
   "mul/add/eor body. For stalling code that proxy badly overstates real ALU work, so vdd_arm is over-predicted. "
   "Naming it before the run turns a 52% outlier from an embarrassment into a diagnosis — and points at the fix.",11.5,False,INK)
tb(s,.6,5.4,12.1,.4,"Fix: replace the insns/3 proxy with a stall-aware term. QEMU's activity vector already carries "
   "the cache-miss and DRAM-transaction counts needed to build one.",12,True,GREEN)

# ── 8 · what this licenses ─────────────────────────────────────────────────
s=slide("What this licenses, and what it does not","The trust statement, quantity by quantity.")
lic=[("predict total power of an unseen app","YES","5.3% mean, 16% worst, 50 held-out applications"),
     ("predict vdd_soc","YES","4.5% mean, 8% worst — the strongest single result"),
     ("predict vdd_arm for compute-bound code","YES","~7% median"),
     ("predict vdd_arm for stall-heavy code","NO","up to 52% over — the insns/3 proxy fails; fix identified"),
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
