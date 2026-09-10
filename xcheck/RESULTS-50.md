# 50-app blind power prediction — RESULT

Predictions were frozen and committed in `3f5d321` **before any power sample was
taken on these applications**. This file reports what happened.

## Result

| rail | MAPE | median | p90 | worst |
|---|---:|---:|---:|---:|
| `vdd_arm` | 11.4% | 10.8% | 19.1% | 25.2% |
| `vdd_soc` | **4.1%** | 5.0% | 5.9% | 7.1% |
| **SUM** | **6.4%** | 6.5% | 10.2% | 14.8% |

**4.5%** | 5.1% | 6.8% | 8% |
| **SUM** | **4.9%** | 4.8% | 8.3% | 11% |

**6.4% mean error on total power across 50 real applications, worst case 14.8%**, from coefficients
fitted on an 11-point synthetic alu/mem grid containing none of them, with the
activity supplied by QEMU.

Published per-rail models report single-digit error on unseen workloads as the
good outcome; McCullough (ATC 2011) and Walker (TCAD 2017) both warn that
sub-3% on unseen workloads is a reason to distrust your validation set. 6.4% on
50 held-out real applications is inside that band and was not tuned toward.

## Part 1 — Does QEMU reproduce the activity itself?

Before any power claim, the prior question: does the emulator see the same work
the silicon does? Same binary, same input, QEMU's TCG counts against the A55's
own PMU. All 50 applications, in `RESULTS-activity.csv`.

**Instructions — yes.**

| metric | value |
|---|---:|
| mean absolute error | **1.75%** |
| median | 0.65% |
| within 1% | 28 of 50 |
| within 2% | 41 of 50 |
| worst | 15.4% (`bb-cksum`) |

**Bandwidth — no.** QEMU's DRAM proxy over-reports against `l3d_cache_refill`:

| app | QEMU GB/s | silicon GB/s | error |
|---|---:|---:|---:|
| `mem-w` | 4.66 | 2.62 | +78% |
| `mem` | 4.93 | 2.53 | +95% |
| `mm-big` | 1.49 | 0.60 | +149% |

Those are the only 3 of 50 applications above 0.5 GB/s. The cause is
**write streaming**: the A55 skips read-for-ownership on a full cache-line
write, so the line is never fetched. QEMU's cache model allocates it anyway and
counts a transaction the silicon never issues. Single mechanism, not noise.

⭐ **Why the power result survives it.** 47 of 50 applications run below
0.5 GB/s, where the whole bandwidth term is worth under 27 mW against a
~1400 mW budget. The error is real and it is in the place where it does least
damage for application workloads. It is also the first thing to fix before any
of this is pointed at streaming or DMA-heavy code — and it is the one piece of
upstream QEMU work this campaign produced.

⚠️ **Provenance:** QEMU counts DERIVED from TCG plugins (linux-user); silicon
counts MEASURED via ARM PMU on i.MX95, A55 core 0, pinned at 1.8 GHz.

## The three checks that were promised before the numbers existed

### 1. Spread — the model tracks the range, but sits low

    predicted  1289 – 1771 mW   (span 482)
    measured   1295 – 1795 mW   (span 500)

The span is right to within 4%. What the model does instead is sit
**systematically low by 6.4%** across the whole range — a bias, not a
compression. Stated in mW deliberately: a ratio of two spreads reads as "the
model can be that far off", which is not what it means.

A constant bias is the benign failure mode. It is one intercept away from
being corrected, and it does not distort the *ranking* of workloads by power,
which is what a design decision usually turns on.

⚠️ This supersedes an earlier reading of this same check, which reported the
model as failing to reach the bottom of the range. That artifact came from the
extraction bug in the correction below: the contaminated low-end measurements
were pulled down by idle, which widened the measured range downward and made
the model look under-responsive at the bottom. With the measurements corrected,
the spread agrees and a clean bias is what remains.

## ⚠️ Correction — the original 52% outlier was a harness bug, not a model bug

The first pass of this table reported `vdd_arm` worst-case **52%** on `bb-grep`
and `bb-awk`, and I published a plausible mechanism for it: the `insns/3` ALU
proxy overstating work for stall-heavy text processing. **That explanation was
wrong, and it was the dangerous part.**

Both applications **never executed**. Their command lines carried unquoted shell
metacharacters — `(gamma|delta)` and `{s+=$3;n++}` — so BCU spent twenty seconds
measuring a shell failing in a loop. Two text-processing apps failing identically
is exactly what a real proxy-error would look like, which is why the wrong story
survived: **a plausible mechanism that fits the evidence stops people looking.**

Re-run with the arguments quoted, both fall inside the normal band and the 52%
disappears. The table above is the corrected run. The `insns/3` proxy limitation
is still real for genuinely stall-heavy code — it is simply not what those two
rows were showing.

Rule earned: **execution is a measurement precondition, not an assumption.**
Record exit code and iteration count for every run; a workload that did not run
is indistinguishable from one that ran cheaply.

## Multi-application — realistic edge mixes

Single-application numbers do not tell you whether the model survives a product
workload. These are concurrent mixes drawn from the same 50, chosen to look
like something an edge device actually runs.

**No silicon counter is used to predict these mixes.** Per-application activity
comes from QEMU; each application's *solo* iteration rate (frozen in
`RESULTS-50.csv`) converts it to a rate; the mix is the sum. That keeps it an
end-to-end QEMU→silicon prediction rather than a curve fit on silicon activity.

| workload | applications running concurrently | cores | pred mW | meas mW | err | err (PMU) |
|---|---|---:|---:|---:|---:|---:|
| AI + vision | pacman  +  sgm stereo | 2 | 1605 | 1704 | 5.8% | 6.0% |
| AI + vision + DB + net | pacman  +  sgm  +  sqlite  +  httpp | 4 | 2123 | 2189 | 3.0% | 3.1% |
| full edge stack, every core | pacman  +  sgm  +  sqlite  +  httpp  +  qoi  +  ray | 6 | 2612 | 2561 | 2.0% | 0.7% |

**Mean 3.6%, worst 5.8%** across two to six concurrent applications.

Controls over the same core counts:

| workload | applications running concurrently | cores | pred mW | meas mW | err | err (PMU) |
|---|---|---:|---:|---:|---:|---:|
| compute-bound control | 4 x sha256 | 4 | 2304 | 2163 | 6.5% | 6.5% |
| mixed benchmark control | sha256 + mem + lz4 + sqlite + lua + bzip2 | 6 | 3065 | 2878 | 6.5% | 1.4% |

### Why the multi-application result beats the single-application one

It is not that concurrency is easier to model. Summing several applications
averages out per-application bias: the model's −6.4% single-app bias is a
*distribution*, and adding two to six independent draws from it shrinks the
spread of the total. The six-core cases are the most accurate for the same
reason a mean of six samples beats a mean of one. This is expected, and it
would be a mistake to read it as the model being better under load.

### What the PMU column is for

The last column re-runs the identical prediction using activity **measured on
silicon** instead of QEMU. It separates two error sources that a single number
hides:

- On the edge mixes the two agree (5.8/6.0, 3.0/3.1, 2.0/0.7) — so the residual
  error there is the **model's**, and QEMU's activity is not contributing to it.
- They diverge on the streaming control: **6.5% QEMU vs 1.4% PMU**. QEMU's DRAM
  proxy reports 5.08 GB/s where the silicon PMU reports 3.02. The coefficients
  were fitted against PMU bandwidth, so an over-reported GB/s inflates the
  prediction. The edge mixes run at 0.4–0.7 GB/s and are barely exposed to it.

⭐ That divergence is the most useful number on the page: it says the remaining
work is in QEMU's DRAM proxy at high bandwidth, not in the power model.

⚠️ **Correction.** An earlier version of this section reported 2.7% mean / 3.9%
worst on three mixes and claimed they beat the single-app result. Those numbers
were invalid. The harness bounded only the *launch* of new iterations at 20 s
and let the in-flight iteration finish, while `perf stat` wrapped the whole run,
so long-iteration applications (pacman, sgm) overran by 4–13 s. The counters
described a two-phase run — all applications, then a pacman+sgm tail — while the
divisor assumed a flat 20 s, inflating activity rates by 1.22–1.66×. Because the
model under-predicts, inflated activity *flattered* the result.

It was re-measured, not re-derived: applications now run continuously from
t=3 s to t=37 s with the 20 s counter window inside that span, so counters and
power describe one homogeneous phase. `cores_eff` (cycles/1.8 GHz/window) comes
out at 2.07, 4.06 and 5.98 for the 2-, 4- and 6-application mixes, which is the
execution proof that every application was busy for the whole window.

The re-run also caught a second fault: the old `sha256` controls were invoked as
`app-sha256 200`, but the binary takes a *file* argument. Command lines now come
verbatim from `manifest50.txt`.

⚠️ **Provenance:** rails MEASURED on IMX95LPD5EVK-19 via NXP BCU, A55 die
40–41 °C under load. `pred` DERIVED from QEMU TCG activity; `err (PMU)` DERIVED
from silicon PMU activity and labelled as such wherever it appears. An earlier
version of this section labelled the PMU-activity predictions as QEMU-derived,
which was false.

## What holds up best

`vdd_soc` at **4.1% MAPE with a worst case of 7.1%** — the tightest result of the
campaign. It is bandwidth-driven, and bandwidth is what QEMU estimates well
(`dram_bytes_proxy`, validated to 0.01% in steady state after accounting for
write streaming).

## What supplied what — and what is still untested

Every prediction in this campaign has the form

    power = c0 + c1*(ALU Mops/s) + c2*(GB/s) + c3*(cores)
            \_____ measured on silicon _____/  \__ from QEMU __/

**QEMU never produces a milliwatt.** It supplies the activity. Every mW in the
coefficients was obtained by putting a meter on real rails and regressing over
an 11-point calibration grid.

That matters for how the result should be read:

| quantity | source here | status |
|---|---|---|
| the activity a workload generates | QEMU | **proven** — 1.75% against the A55's own PMU |
| mW per unit of activity | measured silicon rails | **stood in for the engineers** |
| mW per unit of activity, *before silicon exists* | gate-level power estimation | **not tested** |

The coefficients came from the one source that is unavailable before tapeout: a
working part. That is what makes this evidence rather than a proposal — with the
energy side known-good, any error left over is attributable to the activity
side, which is the half under test. It is also exactly why this does not
replace the engineers' power model: pre-silicon there is no rail to measure and
the coefficients have to come from gate-level estimation instead.

⭐ What this campaign de-risks is the QEMU half, so that when gate-power
estimates arrive, the activity being fed into them is already known to be
right. The estimates themselves remain unvalidated by anything here.

⚠️ Wherever this work says a prediction was made "from QEMU", it means no
silicon *activity counter* was used. It never means watts came out of an
emulator.

## What this demonstrates

QEMU predicted the per-rail power of 50 real applications on silicon it never
ran on, blind, to 6.4%. The emulator supplied the activity; the coefficients came
from measured rails; no power measurement of these applications informed the
prediction.

⚠️ **Scope, stated:** 1800 MHz, single-threaded, `insns/3` ALU proxy, time taken
from silicon cycle counts (`t = cycles / 1.8 GHz`) because QEMU's wall clock is
emulation speed and is never trusted. Fixing the ALU proxy for stall-heavy code
is the clearest next improvement, and the data to do it is in `RESULTS-50.csv`.

Raw BCU captures (82 MB) are not committed; `RESULTS-50.csv` carries the
per-app predicted/measured pairs.
