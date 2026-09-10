# 50-app blind power prediction — FROZEN BEFORE MEASUREMENT

**These predictions were committed before a single power sample was taken on
these applications.** That is the entire point: it makes the comparison a blind
out-of-sample test rather than a fit.

## What is frozen

**The coefficients**, fitted days earlier on an 11-point synthetic grid
(alu/mem thread combinations) that contains none of these 50 applications:

    vdd_arm = 243.8 + 0.1266·aluMops/s + 60.62·GB/s + 169.3·active_cores
    vdd_soc = 851.0 + 0.0043·aluMops/s + 20.40·GB/s

**The activity**, from QEMU TCG plugins (`out50/*.base.json`), collected in an
earlier campaign with no power measurement involved:
`insns` and `dram_bytes_proxy` per app.

**The predictions**: `xcheck/PREDICTIONS-50.csv`, 50 rows.

## The one input that is not from QEMU, and why

The models take RATES; QEMU produces COUNTS. Converting needs a duration, and
QEMU's own wall-clock is emulation speed, not silicon speed — it is explicitly
not trusted anywhere in this project.

Time therefore comes from the silicon **cycle counts already in
`out50/*.hw.json`** (measured on i.MX 95, A55 pinned), as `t = cycles / 1.8 GHz`.

⚠️ This is consistent with wattson's design — *QEMU supplies activity, time comes
from elsewhere* — and it is **blind to the quantity under test**, which is power.
No power measurement of any kind informs these numbers. But it is worth stating
plainly rather than implying the prediction is QEMU-only: **it is not.** A
fully-QEMU-only prediction would additionally need a runtime model, which would
add an error source unrelated to the power model being tested.

## Assumptions, stated so they can be blamed later

- `aluMops/s` is taken as `insns / 3 / t` — the grid's "ALU op" was a
  3-instruction body (mul/add/eor), so this converts app instructions into the
  same unit the coefficient was fitted in. **Real apps are not that instruction
  mix**, and this is the assumption most likely to hurt.
- `active_cores = 1` — all 50 are single-threaded.
- Coefficients are the **1800 MHz** set; the board must be pinned there when
  measured, or the comparison is invalid.
- `dram_bytes_proxy` is QEMU's estimate. Its write-streaming behaviour is
  modelled in this plugin variant (`wstream_*` fields), but it has never been
  validated per-app against the DDR PMU.

## Predicted range

    sum(vdd_arm + vdd_soc):  1289 – 1771 mW,  median 1349 mW

Highest: `mem`, `mem-w` (bandwidth-bound). Lowest: `chase`, `rd-ray`
(latency-bound pointer chasing — few ops, little bandwidth).

⚠️ **The predicted spread is narrow (≈1.4x top to bottom).** If the measured
spread is much wider, the model is under-responsive to whatever separates these
applications, and a good MAPE would be hiding that. Check the SPREAD, not just
the error.
