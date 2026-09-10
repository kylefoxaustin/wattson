#!/usr/bin/env python3
"""Edit the CANONICAL hand-edited deck in place.

wattson_power_results_final_KF_9_10_2026.pptx carries the maintainer's own
edits and is the source of truth from 2026-09-10 onward. make_power_deck.py
must NOT be re-run against it: that regenerates from scratch and would discard
those edits. This script applies deltas to the existing file instead.

Idempotent: re-running detects slides it has already inserted and skips them.
"""
import csv, copy, statistics as st, sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# BASE is the maintainer's own file, kept pristine. Every run rebuilds DECK
# from it, so edits here can be iterated without stacking. When a new
# hand-edited deck arrives, replace BASE with it.
BASE = 'wattson_power_KF.base.pptx'
DECK = 'wattson_power_results_final_KF_9_10_2026.pptx'
import shutil; shutil.copyfile(BASE, DECK)
INK = RGBColor(0x20, 0x21, 0x24); MUTED = RGBColor(0x5F, 0x63, 0x68)
WHITE = RGBColor(0xFF, 0xFF, 0xFF); GREEN = RGBColor(0x18, 0x7A, 0x33)
AMBER = RGBColor(0xB0, 0x60, 0x00); RED = RGBColor(0xB3, 0x14, 0x12)
ACCENT = RGBColor(0x1F, 0x5C, 0xA8); ZEBRA = RGBColor(0xEF, 0xF3, 0xF9)
FOOT = ("wattson power · rails MEASURED on IMX95LPD5EVK-19 (NXP BCU) · A55 die 40–41 °C under load · "
        "activity DERIVED from QEMU TCG · 2026-09-10")

prs = Presentation(DECK)

def tb(sl, x, y, w, h, t, size, bold, color, align=PP_ALIGN.LEFT, font="Verdana"):
    b = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = t
    r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = font
    return tf

def new_slide(title, kicker=None, foot=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.92))
    band.fill.solid(); band.fill.fore_color.rgb = INK; band.line.fill.background()
    ts = 26 if len(title) <= 44 else (22 if len(title) <= 58 else 19)
    tb(s, .6, .13, 12.2, .66, title, ts, True, WHITE)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(0.92), prs.slide_width, Pt(3))
    rule.fill.solid(); rule.fill.fore_color.rgb = ACCENT; rule.line.fill.background()
    if kicker: tb(s, .6, 1.06, 12.2, .4, kicker, 12, False, MUTED)
    tb(s, .6, 7.14, 11.4, .3, foot or FOOT, 9.5, False, MUTED)
    tb(s, 12.5, 7.14, .5, .3, "", 9.5, False, MUTED, PP_ALIGN.RIGHT)   # page no, filled later
    return s

def table(s, x, y, w, col_w, hdr, data, fsz=10.5, rh=0.32, bold_cols=(), color_fn=None):
    t = s.shapes.add_table(len(data) + 1, len(hdr), Inches(x), Inches(y), Inches(w), Inches(rh)).table
    for i, cw in enumerate(col_w): t.columns[i].width = Inches(cw)
    for rr in range(len(data) + 1): t.rows[rr].height = Inches(rh)
    for c, v in enumerate(hdr):
        cell = t.cell(0, c); cell.text = v
        run = cell.text_frame.paragraphs[0].runs[0]
        run.font.size = Pt(fsz); run.font.bold = True; run.font.color.rgb = WHITE; run.font.name = "Calibri"
        cell.fill.solid(); cell.fill.fore_color.rgb = INK
    for ri, row in enumerate(data, 1):
        for c, v in enumerate(row):
            cell = t.cell(ri, c); cell.text = str(v)
            cell.fill.solid(); cell.fill.fore_color.rgb = ZEBRA if ri % 2 else WHITE
            if not cell.text_frame.paragraphs[0].runs: continue
            run = cell.text_frame.paragraphs[0].runs[0]
            run.font.size = Pt(fsz); run.font.name = "Calibri"; run.font.bold = (c in bold_cols)
            if color_fn:
                col = color_fn(ri - 1, c)
                if col: run.font.color.rgb = col
    return t


def tables(slide_idx):
    return [sh.table for sh in prs.slides[slide_idx].shapes if sh.has_table]

def set_cell(tbl, ri, ci, text, bold=None, color=None, fsz=None):
    cell = tbl.cell(ri, ci); para = cell.text_frame.paragraphs[0]
    if para.runs:
        keep = para.runs[0]
        keep.text = text
        for r in para.runs[1:]: r.text = ''
        if bold is not None: keep.font.bold = bold
        if color is not None: keep.font.color.rgb = color
        if fsz is not None: keep.font.size = Pt(fsz)
    else:
        cell.text = text

def clone_row(tbl):
    """Append a copy of the last row (keeps fill/format) and blank its text."""
    last = tbl._tbl.tr_lst[-1]
    new = copy.deepcopy(last)
    tbl._tbl.append(new)
    ri = len(tbl.rows) - 1
    for ci in range(len(tbl.columns)): set_cell(tbl, ri, ci, '')
    return ri


def drop_shape(slide_idx, sh):
    sh._element.getparent().remove(sh._element)

def titles():
    out = []
    for sl in prs.slides:
        t = [sh.text_frame.text for sh in sl.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
        out.append(t[0] if t else '')
    return out

def replace_text(slide_idx, old, new, exact_prefix=False):
    """Swap the text of the first run whose paragraph contains `old`."""
    hit = False
    for sh in prs.slides[slide_idx].shapes:
        if not sh.has_text_frame: continue
        for p in sh.text_frame.paragraphs:
            joined = ''.join(r.text for r in p.runs)
            if old in joined and p.runs:
                p.runs[0].text = joined.replace(old, new)
                for r in p.runs[1:]: r.text = ''
                hit = True
    return hit

def move_slide(frm, to):
    xml = prs.slides._sldIdLst
    ids = list(xml)
    xml.remove(ids[frm]); xml.insert(to, ids[frm])

def renumber():
    for i, sl in enumerate(prs.slides, 1):
        for sh in sl.shapes:
            if not sh.has_text_frame: continue
            t = sh.text_frame.text.strip()
            if (t.isdigit() or t == '') and sh.left > Inches(12) and sh.top > Inches(7):
                p = sh.text_frame.paragraphs[0]
                if p.runs: p.runs[0].text = str(i)
                else:
                    r = p.add_run(); r.text = str(i)
                    r.font.size = Pt(9.5); r.font.color.rgb = MUTED; r.font.name = "Verdana"
                    p.alignment = PP_ALIGN.RIGHT

# ── deltas ────────────────────────────────────────────────────────────────
# 1 · precise language: QEMU supplies activity, never watts
replace_text(1, "And 3.6% on concurrent multi-application mixes, predicted from QEMU alone.",
             "And 3.6% on concurrent multi-application mixes. In both cases QEMU supplies the ACTIVITY; "
             "the mW-per-unit-activity always comes from measured silicon.")
replace_text(1, "predicted from an QEMU emulator", "predicted from a QEMU emulator")
replace_text(9, "Predicted from QEMU alone: no silicon counter is used for these mixes.",
             "No silicon ACTIVITY counter feeds these predictions — the activity is QEMU's.")
replace_text(11, "And those activity factors, fed to a power model carrying estimated gate power, produce power "
                 "estimates that held to single digits against real rails.",
             "And fed to a power model, those activity factors produced power estimates that held to single "
             "digits against real rails. The half still to prove is the model itself: here its coefficients "
             "were measured on silicon, and pre-tapeout they must come from gate-level estimation instead. "
             "That is the engineers' half, and it is the remaining risk.")

# 2 · anatomy slide
act = list(csv.DictReader(open('RESULTS-activity.csv')))
IE = [abs(float(r['insn_err'])) for r in act]
s = new_slide("Where the number actually comes from",
              "QEMU never emits a milliwatt. It is worth being precise about which half of the prediction it supplies.")
eq = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(.6), Inches(1.56), Inches(12.1), Inches(1.24))
eq.fill.solid(); eq.fill.fore_color.rgb = RGBColor(0xF4, 0xF7, 0xFB); eq.line.color.rgb = ACCENT
_tf = s.shapes.add_textbox(Inches(.68), Inches(1.70), Inches(11.95), Inches(.5)).text_frame
_tf.word_wrap = True; _p = _tf.paragraphs[0]; _p.alignment = PP_ALIGN.CENTER
for _t, _c in [("power  =  ", INK), ("243.8", RED), ("  +  ", INK), ("0.1266", RED), (" · ", INK),
               ("ALU Mops/s", GREEN), ("  +  ", INK), ("60.62", RED), (" · ", INK), ("GB/s", GREEN),
               ("  +  ", INK), ("169.3", RED), (" · ", INK), ("cores", GREEN)]:
    _r = _p.add_run(); _r.text = _t; _r.font.size = Pt(17); _r.font.bold = True
    _r.font.color.rgb = _c; _r.font.name = "Verdana"
tb(s, .9, 2.20, 5.6, .30, "MEASURED on silicon rails", 12, True, RED, PP_ALIGN.CENTER)
tb(s, .9, 2.47, 5.6, .28, "mW per unit of activity", 10.5, False, MUTED, PP_ALIGN.CENTER)
tb(s, 6.7, 2.20, 5.6, .30, "DERIVED from QEMU", 12, True, GREEN, PP_ALIGN.CENTER)
tb(s, 6.7, 2.47, 5.6, .28, "the activity itself", 10.5, False, MUTED, PP_ALIGN.CENTER)
d = [("the activity a workload generates", "QEMU", "proven here",
      f"{st.mean(IE):.2f}% vs the A55's own PMU, 50 applications"),
     ("mW per unit of activity", "measured silicon rails", "stood in for the spreadsheet",
      "11-point calibration grid on a real board"),
     ("mW per unit of activity, BEFORE silicon exists", "gate-level power estimation", "NOT tested here",
      "this is the engineers' half, and it is the open link")]
def cf(ri, c):
    if c == 2: return {"proven here": GREEN, "stood in for the spreadsheet": AMBER}.get(d[ri][2], RED)
    return None
table(s, .6, 3.06, 12.1, (4.0, 2.6, 2.5, 3.0), ("quantity", "where it came from", "status", "basis"),
      d, fsz=11, rh=.48, bold_cols=(0, 2), color_fn=cf)
box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(.6), Inches(5.10), Inches(12.1), Inches(1.30))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xFD, 0xF6, 0xEC); box.line.color.rgb = AMBER
tb(s, .9, 5.22, 11.5, 1.10,
   "In a real program that middle row is a power-estimation spreadsheet. Here we stood in for it by having the actual "
   "silicon. That is what makes this evidence rather than a proposal — with the energy side known-good, any error left "
   "over belongs to the activity side, which is the half under test. It is also why this does not replace the "
   "engineers: before tapeout there is no rail to measure, and the coefficients come from their estimates instead.",
   12, False, INK)
tb(s, .6, 6.52, 12.1, .5, "What this campaign de-risks is the QEMU half — so that when gate-power estimates arrive, "
   "the activity being fed into them is already known to be right.", 12, True, ACCENT)

# 3 · what this replaces
s = new_slide("What this actually replaces",
              "A power estimate is two numbers multiplied together. Only one of them has ever had a way to get better.")
for name, src, body, col, tag, y in [
    ("gate power per toggle", "the engineers' power-estimation spreadsheet",
     "Wide error bars early, and everyone knows it — but it REFINES as the design matures. Synthesis, then "
     "place-and-route, then silicon.", GREEN, "refines over time", 1.60),
    ("activity factor", "a flat assumption: 1%, 2%, 3%, 5%, 10%",
     "Does not refine. Nothing connects a toggle rate to a workload, so there is no mechanism by which the guess "
     "improves.", RED, "never refines", 3.16)]:
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(.6), Inches(y), Inches(12.1), Inches(1.42))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF7, 0xF8, 0xFA); box.line.color.rgb = col
    tb(s, .92, y + .14, 5.2, .36, name, 16, True, INK)
    tb(s, .92, y + .54, 5.2, .34, src, 12, False, MUTED)
    chip = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(.92), Inches(y + .94), Inches(2.3), Inches(.34))
    chip.fill.solid(); chip.fill.fore_color.rgb = col; chip.line.fill.background()
    tb(s, .92, y + .98, 2.3, .28, tag, 10.5, True, WHITE, PP_ALIGN.CENTER)
    tb(s, 6.35, y + .20, 6.1, 1.05, body, 12, False, INK)
bx = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.6), Inches(4.66), Inches(12.1), Inches(.78))
bx.fill.solid(); bx.fill.fore_color.rgb = INK; bx.line.fill.background()
tb(s, .9, 4.76, 11.6, .62, "How do you correlate a 3% toggling assumption to a real use case? "
   "You cannot — there has been no instrument for it.", 15, True, WHITE)
tb(s, .6, 5.50, 12.1, .32, "That is the gap this closes:", 12, True, INK)
for i, (a_, b_) in enumerate([
        ("name an application", "get its activity factor, per workload, with a stated error against silicon"),
        ("change the code", "see the activity factor move, and by how much"),
        ("compare two use cases", "on the same measured basis, not two different guesses")]):
    yy = 5.82 + i * .32
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(.72), Inches(yy + .07), Inches(.16), Inches(.16))
    dot.fill.solid(); dot.fill.fore_color.rgb = ACCENT; dot.line.fill.background()
    tb(s, 1.02, yy, 3.3, .32, a_, 12, True, INK)
    tb(s, 4.15, yy, 8.5, .32, b_, 12, False, MUTED)
tb(s, .6, 6.80, 12.1, .3, "The spreadsheet keeps its job. It just stops being multiplied by a number nobody can "
   "trace to anything.", 11.5, True, ACCENT)


# 5 · the mixes were mislabelled as AI/inference. pacman is a genetic-algorithm
#     game-agent trainer (GP evolution) and sgm is semi-global stereo matching.
#     Neither is neural-network inference, and no NN/NPU workload exists in the
#     50-app corpus at all. Relabelled to what the binaries actually are.
_t = tables(9)[0]
set_cell(_t, 1, 0, "game + disparity", fsz=10.5)
set_cell(_t, 2, 0, "game + disparity + DB + net", fsz=10.5)
set_cell(_t, 3, 0, "six workloads, every core", fsz=10.5)
replace_text(9, "Perception, inference, storage, networking, imaging, rendering, running at the same time.",
             "Game, stereo disparity, storage, networking, imaging and rendering, all at once.")
replace_text(9, "pacman = genetic-AI trainer", "pacman = game agent trained by genetic algorithm")
replace_text(9, "sgm = stereo-vision disparity on real imagery",
             "sgm = semi-global stereo disparity on real imagery")

# 6 · the title claimed an "edge workload"; these are ordinary concurrent
#     applications, so the title says that instead.
replace_text(9, "A more realistic edge workload", "Several real applications at once")


# 7 · slide 10 geometry: the honest labels are longer than the ones they
#     replaced, so widen the first column out of column 2's slack.
for _tb2 in tables(9):
    _tb2.columns[0].width = Inches(3.35)
    _tb2.columns[1].width = Inches(3.95)
replace_text(9, "Several real applications at once", "Several apps at once")

# 8 · per-app DDR bandwidth belongs on the per-app slide. Rebuild the three
#     tables with a MEASURED GB/s column; the originals had no room for it.
_act = {r['app']: r for r in csv.DictReader(open('RESULTS-activity.csv'))}
_rows = list(csv.DictReader(open('RESULTS-50.csv')))
def _fv(r, k): return float(r[k])
_allr = sorted(_rows, key=lambda r: -_fv(r, 'meas_sum'))
for _sh in [x for x in prs.slides[8].shapes if x.has_table]:
    drop_shape(8, _sh)
_XS = [.6, 4.85, 9.10]
for _ci, _chunk in enumerate([_allr[0:17], _allr[17:34], _allr[34:50]]):
    _d = [(r['app'][:12], f"{_fv(r,'pred_sum'):.0f}", f"{_fv(r,'meas_sum'):.0f}",
           f"{_fv(r,'err_sum'):.0f}%", f"{float(_act[r['app']]['silicon_GBps']):.2f}")
          for r in _chunk]
    def _mk(dd):
        def cf(ri, c):
            if c == 3:
                v = float(dd[ri][3].rstrip('%'))
                return GREEN if v <= 8 else (AMBER if v <= 12 else RED)
            if c == 4:
                return ACCENT if float(dd[ri][4]) >= 0.25 else MUTED
            return None
        return cf
    table(prs.slides[8], _XS[_ci], 1.82, 4.05, (1.30, .70, .70, .66, .69),
          ("app", "pred", "meas", "err", "GB/s"), _d, fsz=8.5, rh=0.245,
          bold_cols=(0,), color_fn=_mk(_d))
replace_text(8, "GREEN ≤ 8% error   ·   AMBER 8–12%   ·   RED > 12%      — the 8% line is the published bar "
                "for a good per-rail model, and is this corpus's own p90 (8.3%).",
             "GREEN ≤ 8%  ·  AMBER 8–12%  ·  RED > 12%   (8% = the published bar for a good per-rail model)"
             "   ·   GB/s = DDR bandwidth, MEASURED on silicon")

# both new slides land before the closing slide
move_slide(12, 11)   # anatomy   -> index 11
move_slide(13, 12)   # replaces  -> index 12
renumber()
prs.save(DECK)
print(f"{DECK} — {len(prs.slides._sldIdLst)} slides")
for i, t in enumerate(titles(), 1): print(f"  {i:2} {t[:62]}")
