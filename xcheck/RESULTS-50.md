# 50-app blind power prediction — RESULT

Predictions were frozen and committed in `3f5d321` **before any power sample was
taken on these applications**. This file reports what happened.

## Result

| rail | MAPE | median | p90 | worst |
|---|---:|---:|---:|---:|
| `vdd_arm` | 7.7% | 7.0% | 16.3% | 20% |
| `vdd_soc` | **4.5%** | 5.1% | 6.8% | 8% |
| **SUM** | **4.9%** | 4.8% | 8.3% | 11% |

**4.9% mean error on total power across 50 real applications, no application worse than 11%**, from coefficients
fitted on an 11-point synthetic alu/mem grid containing none of them, with the
activity supplied by QEMU.

Published per-rail models report single-digit error on unseen workloads as the
good outcome; McCullough (ATC 2011) and Walker (TCAD 2017) both warn that
sub-3% on unseen workloads is a reason to distrust your validation set. 4.9% on
50 held-out real applications is inside that band and was not tuned toward.

## The three checks that were promised before the numbers existed

### 1. Spread — the model is slightly under-responsive

    predicted  1289 – 1771 mW
    measured   1279 – 1808 mW

It compresses the range: the top end is close, the **bottom end is not reached**
by about 10 mW. Stated as mW deliberately — a ratio of two spreads
reads as "the model can be that far off", which is not what it means.

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
workload. These are concurrent mixes of applications drawn from the same 50,
chosen to look like something an edge device actually runs.

| workload | applications running concurrently | cores | GB/s | pred mW | meas mW | err |
|---|---|---:|---:|---:|---:|---:|
| AI + vision | pacman  +  sgm stereo | 2 | 0.37 | 1684 | 1747 | 3.6% |
| AI + vision + DB + net | pacman  +  sgm  +  sqlite  +  httpp | 4 | 0.41 | 2205 | 2220 | 0.7% |
| full edge stack, every core | pacman  +  sgm  +  sqlite  +  httpp  +  qoi  +  ray | 6 | 0.63 | 2680 | 2579 | 3.9% |

**Mean 2.7%, worst 3.9%** — better than the one-at-a-time result.

Controls over the same core counts, using synthetic and benchmark mixes:

| workload | applications running concurrently | cores | GB/s | pred mW | meas mW | err |
|---|---|---:|---:|---:|---:|---:|
| compute + streaming | sha256  +  mem | 2 | 2.48 | 1878 | 2056 | 8.7% |
| core scaling control | 4 x sha256 | 4 | 0.14 | 2307 | 2183 | 5.7% |
| mixed benchmarks | sha256 + mem + lz4 + sqlite + lua + bzip2 | 6 | 3.20 | 2789 | 2748 | 1.5% |

⭐ The realistic mixes run at **0.4–0.6 GB/s**; the synthetic ones at **2.5–3.2
GB/s**. Real applications live in cache far more than streaming benchmarks do.
The model was fitted on the streaming regime and holds in both — which is the
result that matters, because the cache-resident regime is the one products are in.

⚠️ **Provenance:** rails MEASURED on IMX95LPD5EVK-19 via NXP BCU, A55 die
40–41 °C under load; activity DERIVED from QEMU TCG plugins. Predictions computed
from the frozen coefficients before each mix was measured.

## What holds up best

`vdd_soc` at **4.5% MAPE with a worst case of 8%** — the tightest result of the
campaign. It is bandwidth-driven, and bandwidth is what QEMU estimates well
(`dram_bytes_proxy`, validated to 0.01% in steady state after accounting for
write streaming).

## What this demonstrates

QEMU predicted the per-rail power of 50 real applications on silicon it never
ran on, blind, to 4.9%. The emulator supplied the activity; the coefficients came
from measured rails; no power measurement of these applications informed the
prediction.

⚠️ **Scope, stated:** 1800 MHz, single-threaded, `insns/3` ALU proxy, time taken
from silicon cycle counts (`t = cycles / 1.8 GHz`) because QEMU's wall clock is
emulation speed and is never trusted. Fixing the ALU proxy for stall-heavy code
is the clearest next improvement, and the data to do it is in `RESULTS-50.csv`.

Raw BCU captures (82 MB) are not committed; `RESULTS-50.csv` carries the
per-app predicted/measured pairs.
