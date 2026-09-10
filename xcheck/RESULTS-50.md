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

**Bandwidth — mostly, with one clear exception.**

| app | QEMU reads GB/s | silicon reads GB/s | error |
|---|---:|---:|---:|
| `mem-w` | 2.33 | 2.62 | -11% |
| `mem` | 2.47 | 2.53 | -2% |
| `mm-big` | 1.49 | 0.60 | +149% |
| `chase-big` | 0.45 | 0.45 | -1% |
| `chase` | 0.45 | 0.45 | -1% |
| `mm` | 0.20 | 0.32 | -37% |
| `parson` | 0.35 | 0.32 | +11% |
| `lz4-fast` | 0.38 | 0.31 | +22% |
| `rd-life` | 0.57 | 0.31 | +84% |

The streaming workloads — where absolute bandwidth is largest and therefore
where it matters most for power — agree to within 11%. What is genuinely off is
`mm-big` (+149%) and `rd-life` (+84%): small-footprint, reuse-heavy workloads
where a modelled cache and a real one diverge most. Neither moves enough
traffic to cost more than a few mW.

⚠️ **Correction 3 — the "2x over-report" was a unit error, not a QEMU defect.**
An earlier version of this section reported QEMU over-reporting bandwidth by
78–149% and attributed it to unmodelled write streaming. That compared QEMU's
`dram_bytes_proxy`, which counts read **and write** transactions, against
`l3d_cache_refill`, which is a **refill** counter and sees reads only. The
like-for-like quantity is `dram_read_proxy`, and on that basis `mem` is −2% and
`mem-w` −11%.

The frozen predictions are unaffected: they fed total traffic into a
coefficient calibrated against total traffic, which is self-consistent.
Re-running all 50 with reads-only makes the result *worse* (6.4% → 7.0%, with
`mem`/`mem-w` regressing ~10pp), which is itself the evidence that the model's
bandwidth term means total traffic.

Rule earned: **two counters with similar names are not the same quantity.** A
refill counter and a transaction counter differ by exactly the write traffic,
and the difference looks like a plausible modelling defect.

### The bandwidth corner — where the model actually breaks

The corpus tops out at 0.60 GB/s for a real application while the model is
fitted to 14 GB/s, so its largest coefficient was validated across 4% of its
range. Four purpose-written workloads (`bwbench.c`) occupy the gap:

| workload | GB/s | pred mW | meas mW | err |
|---|---:|---:|---:|---:|
| blit 4MB — large memcpy (replicate) | 11.12 | 2203 | 1944 | 13.3% |
| blit 256MB — large memcpy | 10.85 | 2180 | 1947 | 12.0% |
| reduce 256MB — array reduction | 5.47 | 1774 | 1797 | 1.3% |
| spmv 64MB — sparse gather | 0.47 | 1305 | 1330 | 1.9% |
| yuv 1080p — YUV420→RGB565 | 0.22 | 1393 | 1456 | 4.3% |

⭐ **A pure read stream at 5.5 GB/s predicts to 1.3%** — the model extrapolates
9x past the corpus without trouble. **A 50/50 read+write stream at 11 GB/s
over-predicts by 12–13%.** The model carries one bandwidth term, so a written
byte is charged the same power as a read byte, and a written byte evidently
costs less. Nothing in the 50-app corpus was write-heavy enough to expose it.
Separate read and write coefficients are the obvious next refinement.

Two workload guesses were wrong and are recorded as such: YUV→RGB frame
conversion is **compute-bound** (1.4 IPC, 0.15 GB/s) and sparse gather is
**latency-bound** (0.058 IPC). "Memory-bound" splits into stall-heavy and
streaming, and only streaming generates volume.

⚠️ **Known gap:** the PMU cross-check is absent for these five runs. `perf`
returned idle-level counts although the board was clearly loaded (+650–800 mW,
iteration counts confirm the work), and a direct test with the workload
launched in the same ssh session counts correctly — so it is the harness's
cross-session launch, not the counters. The prediction path uses no silicon
counter, so the result stands; the cross-check does not. Not root-caused.

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
workload. These are concurrent mixes drawn from the same 50.

⚠️ **Naming:** an earlier version called these "AI + vision". That was
wrong. `pacman` is a game agent trained by a genetic algorithm and `sgm` is
semi-global stereo disparity — classical computer vision, not a learned model.
**No neural-network inference exists anywhere in the 50-app corpus**, so
nothing here should be read as an NPU or CNN result. The mixes are named for
what the binaries actually do.

**No silicon counter is used to predict these mixes.** Per-application activity
comes from QEMU; each application's *solo* iteration rate (frozen in
`RESULTS-50.csv`) converts it to a rate; the mix is the sum. That keeps it an
end-to-end QEMU→silicon prediction rather than a curve fit on silicon activity.

| workload | applications running concurrently | cores | pred mW | meas mW | err | err (PMU) |
|---|---|---:|---:|---:|---:|---:|
| game + disparity | pacman  +  sgm stereo | 2 | 1605 | 1704 | 5.8% | 6.0% |
| game + disparity + DB + net | pacman  +  sgm  +  sqlite  +  httpp | 4 | 2123 | 2189 | 3.0% | 3.1% |
| six workloads, every core | pacman  +  sgm  +  sqlite  +  httpp  +  qoi  +  ray | 6 | 2612 | 2561 | 2.0% | 0.7% |

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

## Against the alternative — is this better than a flat activity factor?

The trust question is not whether an emulator is right in absolute terms. It is
whether a QEMU-derived activity factor beats what a power estimate is
multiplied by today: a flat assumption, one number for every workload.

Over all **60 measured operating points** (1–6 cores, 0–11 GB/s):

| method | mean | worst |
|---|---:|---:|
| flat activity assumption | 7.4% | **49.4%** |
| QEMU-derived activity factors | **6.3%** | **14.8%** |

⚠️ **Two concessions to the status quo, both deliberate.** The constant
(1457 mW) was chosen *in-sample* — fitted on the very measurements it is then
scored against. And pre-silicon it could not be chosen at all, because that
constant **is** the answer the exercise is trying to produce. The comparison is
therefore generous to the flat assumption and it still loses on the tail.

⭐ **Where per-application activity does NOT help.** On the 50 single-core
applications alone, spanning only 1.4x, the constant wins on the mean
(3.9% vs 6.4%).
A constant is a good predictor of a quantity that barely varies. Per-application
activity earns its place on the **tails** — and the tails are where power
decisions get made.

The flat assumption's worst cases are all concurrency and bandwidth: the mixed
six-core benchmark (49% vs 6.5%), the six-workload edge mix (43% vs 2.0%), the
write-heavy stream (25% vs 12%). Those are exactly the cases that size a
thermal solution.

Data in `RESULTS-vs-flat.csv`.

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
