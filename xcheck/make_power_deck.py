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
ACT=[dict(app=r['app'],qi=float(r['qemu_insns']),si=float(r['silicon_insns']),
          ierr=float(r['insn_err']),qb=float(r['qemu_GBps']),sb=float(r['silicon_GBps']),
          berr=float(r['bw_err']) if r['bw_err'] else 0.0)
     for r in csv.DictReader(open('RESULTS-activity.csv'))]
IE=[abs(r['ierr']) for r in ACT]
HIBW=sorted([r for r in ACT if r['sb']>=0.5],key=lambda r:-r['sb'])
def f(r,k): return float(r[k])
esum=[abs(f(r,'pred_sum')-f(r,'meas_sum'))/f(r,'meas_sum')*100 for r in rows]
worst_app=max(rows,key=lambda r: abs(f(r,'pred_sum')-f(r,'meas_sum'))/f(r,'meas_sum'))['app']
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

def slide(title, kicker=None, foot=None):
    s=prs.slides.add_slide(blank); PAGE[0]+=1
    band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width,Inches(0.92))
    band.fill.solid(); band.fill.fore_color.rgb=INK; band.line.fill.background()
    _ts=26 if len(title)<=44 else (22 if len(title)<=58 else 19)
    tb(s,.6,.13,12.2,.66,title,_ts,True,WHITE)
    rule=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,Inches(0.92),prs.slide_width,Pt(3))
    rule.fill.solid(); rule.fill.fore_color.rgb=ACCENT; rule.line.fill.background()
    if kicker: tb(s,.6,1.06,12.2,.4,kicker,12,False,MUTED)
    tb(s,.6,7.14,11.4,.3,foot or FOOT,9.5,False,MUTED)
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
s=slide("Two questions","The second one is the one people ask for. The first one is the one that has to be true first.")
q=[("1","Can QEMU predict the ACTIVITY a workload generates on silicon?",
    f"YES for instruction activity \u2014 {st.mean(IE):.1f}% mean error over 50 applications, {sum(1 for x in IE if x<=2)} of 50 within 2%.",
    f"Memory bandwidth is over-reported by roughly 2x. Bounded, understood, and localised to streaming workloads."),
   ("2","Can that activity be turned into a POWER number?",
    f"YES \u2014 {st.mean(esum):.1f}% mean error on total power, {max(esum):.1f}% worst, on 50 applications the model never saw.",
    f"And {st.mean([float(r['err_qemu']) for r in mc if r['case'].startswith('e')]):.1f}% on concurrent multi-application mixes, predicted from QEMU alone.")]
y=1.62
for n,ques,ans,cav in q:
    box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.6),Inches(y),Inches(12.1),Inches(2.30))
    box.fill.solid(); box.fill.fore_color.rgb=RGBColor(0xF4,0xF7,0xFB); box.line.color.rgb=ACCENT
    num=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(.95),Inches(y+.30),Inches(.62),Inches(.62))
    num.fill.solid(); num.fill.fore_color.rgb=ACCENT; num.line.fill.background()
    tb(s,.95,y+.38,.62,.5,n,20,True,WHITE,PP_ALIGN.CENTER)
    tb(s,1.78,y+.22,10.6,.44,ques,17,True,INK)
    bar=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(1.78),Inches(y+.78),Inches(10.6),Inches(.62))
    bar.fill.solid(); bar.fill.fore_color.rgb=GREEN; bar.line.fill.background()
    tb(s,1.96,y+.86,10.3,.5,ans,14,True,WHITE)
    tb(s,1.78,y+1.48,10.6,.70,cav,12,False,MUTED)
    y+=2.54
tb(s,.6,6.62,12.1,.3,"Every number on this page is measured on silicon and predicted from an emulator that never ran on it.",11,True,ACCENT)

# ── 3 · what we actually did ───────────────────────────────────────────────
s=slide("What we did","Eight steps, in order. Each one had to work before the next was meaningful.")
steps=[("1","Get the instrument","IMX95LPD5EVK-19 — the only i.MX 95 board with per-rail shunts. Flashed to match the FRDM's BSP first: the idle floor moves 29% between kernels."),
 ("2","Measure the idle floor","n=5, spreads ≤1.7%. 1139.5 mW total; vdd_soc is 72% of it, vdd_arm only 13%."),
 ("3","Ask what predicts core power","Instruction count — the activity vector's core term — explains R²=0.031. THREE PERCENT."),
 ("4","Find what does","A 2-D grid varying ALU rate and bandwidth INDEPENDENTLY. Both together: R²=0.990."),
 ("5","Add the missing term","598 Mops/s on 2 cores = 656 mW; 599 on 1 core = 465 mW. Active cores matter on their own."),
 ("6","Validate QEMU's counters","Same static binary under perf and under QEMU: instructions 0.1%, misses 0.01% in steady state."),
 ("7","Freeze predictions for 50 apps","Committed to git BEFORE any power measurement of those apps."),
 ("8","Measure and compare",f"{st.mean(esum):.1f}% mean error on total power.")]
table(s,.6,1.6,12.1,(0.5,3.4,8.2),("#","step","what came out"),steps,fsz=10.5,rh=0.55,bold_cols=(1,))

# ── 4 · PART 1 · instruction activity ──────────────────────────────────────
AFOOT=("wattson activity \u00b7 QEMU counts DERIVED from TCG plugins \u00b7 silicon counts MEASURED via ARM PMU "
       "on i.MX95 (A55 core 0, pinned 1.8 GHz) \u00b7 2026-09-10")
s=slide("Part 1 \u2014 Does QEMU see the work the silicon does?",
        "Instruction activity: QEMU's count against the A55's own inst_retired counter, same binary, same input, 50 applications.",foot=AFOOT)
band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(1.62),Inches(12.1),Inches(.62))
band.fill.solid(); band.fill.fore_color.rgb=GREEN; band.line.fill.background()
tb(s,.9,1.70,11.6,.44,f"{st.mean(IE):.2f}% mean error, {st.median(IE):.2f}% median. QEMU counts the work.",18,True,WHITE)
buckets=[("within 0.5%",sum(1 for x in IE if x<=0.5)),("within 1%",sum(1 for x in IE if x<=1)),
         ("within 2%",sum(1 for x in IE if x<=2)),("within 5%",sum(1 for x in IE if x<=5)),
         ("above 5%",sum(1 for x in IE if x>5))]
x=.6
for lab,cnt in buckets:
    col=GREEN if 'within' in lab else AMBER
    bx=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(2.46),Inches(2.32),Inches(1.16))
    bx.fill.solid(); bx.fill.fore_color.rgb=RGBColor(0xF4,0xF7,0xFB); bx.line.color.rgb=col
    tb(s,x,2.60,2.32,.62,f"{cnt}",34,True,col,PP_ALIGN.CENTER)
    tb(s,x,3.20,2.32,.32,f"of 50 {lab}",11,False,MUTED,PP_ALIGN.CENTER)
    x+=2.45
tb(s,.6,3.82,12.1,.32,"The ten applications that agree least well \u2014 the whole tail, nothing hidden:",11.5,True,INK)
w=sorted(ACT,key=lambda r:-abs(r['ierr']))[:10]
d=[(r['app'],f"{r['qi']/1e9:.2f}",f"{r['si']/1e9:.2f}",f"{r['ierr']:+.1f}%") for r in w]
def cfi(ri,c):
    if c==3:
        v=abs(float(d[ri][3].rstrip('%'))); return GREEN if v<=2 else (AMBER if v<=8 else RED)
    return None
half=len(d)//2
table(s,.6,4.20,5.9,(1.9,1.35,1.35,1.3),("application","QEMU G-insn","silicon G-insn","error"),d[:half],fsz=11,rh=.36,bold_cols=(0,3),color_fn=cfi)
def cfi2(ri,c):
    if c==3:
        v=abs(float(d[half+ri][3].rstrip('%'))); return GREEN if v<=2 else (AMBER if v<=8 else RED)
    return None
table(s,6.8,4.20,5.9,(1.9,1.35,1.35,1.3),("application","QEMU G-insn","silicon G-insn","error"),d[half:],fsz=11,rh=.36,bold_cols=(0,3),color_fn=cfi2)
tb(s,.6,6.55,12.1,.5,"This is the activity factor a power model consumes. It is also, on its own, the thing you want when you are "
   "reading code flows and usage \u2014 how much work a workload does, where it does it, and how that changes when the code changes.",11,False,ACCENT)

# ── 5 · PART 1 · bandwidth, the honest limit ───────────────────────────────
s=slide("Part 1 \u2014 Where QEMU does not see the same work",
        "Memory bandwidth. QEMU's DRAM proxy against the A55's l3d_cache_refill counter.",foot=AFOOT)
band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(1.62),Inches(12.1),Inches(.62))
band.fill.solid(); band.fill.fore_color.rgb=AMBER; band.line.fill.background()
tb(s,.9,1.72,11.6,.46,"QEMU over-reports DRAM bandwidth by roughly 2x \u2014 the one place it does not match the silicon.",17,True,WHITE)
d=[(r['app'],f"{r['qb']:.2f}",f"{r['sb']:.2f}",f"{r['berr']:+.0f}%",f"{(r['qb']-r['sb'])*60.62:.0f} mW") for r in HIBW]
def cfb(ri,c):
    return RED if c==3 else None
table(s,.6,2.50,12.1,(2.4,2.3,2.5,2.0,2.9),
      ("application","QEMU GB/s","silicon GB/s","error","core-rail impact"),d,fsz=12,rh=.44,bold_cols=(0,3),color_fn=cfb)
tb(s,.6,4.30,12.1,.34,f"Those are the only {len(HIBW)} applications of 50 that exceed 0.5 GB/s.",12,True,INK)
tb(s,.6,4.72,12.1,1.05,"The cause is write streaming: the A55 skips read-for-ownership on a full cache-line write, so the line is "
   "never fetched from DRAM. QEMU's cache model allocates it anyway and counts a transaction the silicon never issued. "
   "It is a known, single-mechanism gap \u2014 not noise \u2014 and it is the one piece of upstream work this campaign produced.",11.5,False,MUTED)
box=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(.6),Inches(5.86),Inches(12.1),Inches(1.06))
box.fill.solid(); box.fill.fore_color.rgb=RGBColor(0xF4,0xF7,0xFB); box.line.color.rgb=ACCENT
tb(s,.9,5.98,11.5,.84,"Why the power result survives it: 47 of 50 applications run below 0.5 GB/s, where the entire bandwidth term is "
   "worth under 27 mW of a ~1400 mW budget. The error is real, it is in the right place to be harmless for application "
   "workloads, and it is the first thing to fix before this is pointed at streaming or DMA-heavy code.",12,False,INK)

# ── 4 · the models ─────────────────────────────────────────────────────────
s=slide("Part 2 \u2014 The power models","Measured on silicon, driven by QEMU activity. Valid at the stated OPP — the frequency is part of the claim.")
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
s=slide("Part 2 \u2014 The finding that changes the model","We expected instruction count to drive core power. It does not.")
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
s=slide("Part 2 — The blind test, 50 applications","Predictions committed to git before the board was touched. This is the headline result.")
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
s=slide("Part 2 \u2014 All fifty applications","Every prediction, every measurement. Nothing selected, nothing dropped.")
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
MFOOT=("wattson power \u00b7 rails MEASURED on IMX95LPD5EVK-19 (NXP BCU) \u00b7 A55 die 40\u201341 \u00b0C \u00b7 "
       "activity DERIVED from QEMU TCG; PMU column MEASURED on silicon \u00b7 2026-09-10")
s=slide("Part 2 \u2014 A realistic edge workload, all six cores busy",
        "Perception, inference, storage, networking, imaging, rendering, running at the same time. "
        "Predicted from QEMU alone: no silicon counter is used for these mixes.",foot=MFOOT)
edge=[r for r in mc if r['case'].startswith('e')]
ctrl=[r for r in mc if not r['case'].startswith('e')]
eq=[float(r['err_qemu']) for r in edge]
band=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(1.72),Inches(12.1),Inches(.6))
band.fill.solid(); band.fill.fore_color.rgb=GREEN; band.line.fill.background()
tb(s,.9,1.80,11.6,.44,f"{st.mean(eq):.1f}% mean error, {max(eq):.1f}% worst, across two to six concurrent applications.",18,True,WHITE)
def mk(rows):
    return [(r['kind'],r['apps'],r['cores'],f"{float(r['pred_qemu']):.0f}",
             f"{float(r['meas_sum']):.0f}",f"{float(r['err_qemu']):.1f}%",f"{float(r['err_pmu']):.1f}%") for r in rows]
d=mk(edge)
def cf1(ri,c):
    if c in (5,6):
        v=float(d[ri][c].rstrip('%')); return GREEN if v<=8 else (AMBER if v<=12 else RED)
    return None
COLS=(2.75,4.55,.72,1.05,1.05,1.0,1.0)
HDR=("what it is","applications running concurrently","cores","pred mW","meas mW","err","err (PMU)")
table(s,.6,2.48,12.1,COLS,HDR,d,fsz=11.5,rh=0.46,bold_cols=(0,5),color_fn=cf1)
tb(s,.6,4.34,12.1,.36,"pacman = genetic-AI trainer  \u00b7  sgm = stereo-vision disparity on real imagery  \u00b7  "
   "sqlite = in-memory OLTP  \u00b7  httpp = HTTP parsing  \u00b7  qoi = image codec  \u00b7  ray = ray tracer",10.5,False,MUTED)
tb(s,.6,4.80,12.1,.32,"Controls \u2014 synthetic and benchmark mixes over the same core counts:",11,True,INK)
d2=mk(ctrl)
def cf2(ri,c):
    if c in (5,6):
        v=float(d2[ri][c].rstrip('%')); return GREEN if v<=8 else (AMBER if v<=12 else RED)
    return None
table(s,.6,5.14,12.1,COLS,HDR,d2,fsz=10.5,rh=0.38,bold_cols=(0,5),color_fn=cf2)
tb(s,.6,6.36,12.1,.66,"The last column re-runs each prediction using activity measured on silicon instead of QEMU, "
   "which separates the model from the emulator. They agree on the edge mixes \u2014 so the error there is the "
   "model's, not QEMU's. They diverge only on the streaming control (6.5% vs 1.4%), where QEMU's DRAM proxy "
   "over-reports bandwidth. Edge workloads run at 0.4\u20130.7 GB/s and are barely exposed to it.",10.5,False,ACCENT)

# ── 8 · what this licenses ─────────────────────────────────────────────────
s=slide("What this licenses, and what it does not","The trust statement, quantity by quantity.")
lic=[("predict the INSTRUCTION activity of an unseen app","YES",f"{st.mean(IE):.2f}% mean, {sum(1 for x in IE if x<=2)} of 50 within 2%"),
     ("predict DRAM BANDWIDTH","NO","over-reports ~2x; write streaming is not modelled"),
     ("predict total power of an unseen app","YES",f"{st.mean(esum):.1f}% mean, {max(esum):.1f}% worst, 50 held-out applications"),
     ("predict vdd_soc","YES",f"{st.mean(esoc):.1f}% mean, {max(esoc):.1f}% worst \u2014 the strongest single result"),
     ("predict vdd_arm on its own","PARTLY",f"{st.median(earm):.1f}% median but {max(earm):.1f}% worst; use the SUM, not this rail alone"),
     ("predict a concurrent multi-app mix","YES",f"{st.mean([float(r['err_qemu']) for r in mc if r['case'].startswith('e')]):.1f}% mean, "
      f"{max(float(r['err_qemu']) for r in mc if r['case'].startswith('e')):.1f}% worst, 2\u20136 apps"),
     ("predict streaming or DMA-heavy code","NO","the bandwidth gap lands directly on it"),
     ("use these coefficients at another frequency","NO","1800 MHz set; vdd_soc transfers, vdd_arm does not"),
     ("use these coefficients on another SoC","NO","stall-power sign is microarchitecture-specific"),
     ("emit watts from QEMU alone","NO","QEMU supplies ACTIVITY; energy coefficients come from silicon")]
def lc(ri,c):
    if c==1: return {"YES":GREEN,"PARTLY":AMBER}.get(lic[ri][1],RED)
    return None
table(s,.6,1.58,12.1,(4.7,1.15,6.25),("claim","verdict","basis"),lic,fsz=10.5,rh=0.40,bold_cols=(0,1),color_fn=lc)
tb(s,.6,6.02,12.1,.5,"The standing rule survives the campaign unchanged: QEMU measures activity, engineers convert "
   "activity to energy. A board that reads real watts is exactly when that discipline matters most.",12,True,ACCENT)
tb(s,.6,6.60,12.1,.5,"Everything above is reproducible from the repo: frozen predictions in git before measurement, "
   "raw per-app pairs in RESULTS-50.csv, and every limit stated beside the number it qualifies.",11.5,False,MUTED)


# ── 11 · what this means ───────────────────────────────────────────────────
s=slide("What this actually means","The result is not the point. What it licenses us to do next is the point.")
pts=[("1","Predicting power on working silicon is not, by itself, worth much.",
      "If the part exists, you can put a meter on it. Everything in this deck was validated against a board we already had \u2014 "
      "that is what makes it evidence, not what makes it useful."),
     ("2","So the value has to be collected BEFORE there is silicon.",
      "Which sets a hard prerequisite on the program: a settled architecture and memory map, early, well ahead of tapeout \u2014 "
      "enough to stand up a QEMU model and boot a full Linux BSP on it. That is the gate. Not the power work; the model underneath it."),
     ("3","Once that exists, this campaign says both halves work.",
      "QEMU predicts the activity factors \u2014 usable on their own for reading code flows, usage and where the work lands. "
      "And those activity factors, fed to a power model carrying estimated gate power, produce power estimates that held to "
      "single digits against real rails.")]
y=1.58
for n,head,body in pts:
    num=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(.62),Inches(y+.04),Inches(.62),Inches(.62))
    num.fill.solid(); num.fill.fore_color.rgb=ACCENT; num.line.fill.background()
    tb(s,.62,y+.12,.62,.5,n,20,True,WHITE,PP_ALIGN.CENTER)
    tb(s,1.45,y,11.3,.46,head,16,True,INK)
    tb(s,1.45,y+.48,11.3,.92,body,12,False,MUTED)
    y+=1.62
box=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(6.32),Inches(12.1),Inches(.80))
box.fill.solid(); box.fill.fore_color.rgb=INK; box.line.fill.background()
tb(s,.9,6.44,11.6,.62,"The division of labour: QEMU supplies the activity. The power model supplies the energy. "
   "Neither one is asked to do the other's job.",14,True,WHITE)

prs.save("wattson-power.pptx")
print(f"wattson-power.pptx — {PAGE[0]} slides")
