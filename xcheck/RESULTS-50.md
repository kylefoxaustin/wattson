# 50-app blind power prediction — RESULT

Predictions were frozen and committed in `3f5d321` **before any power sample was
taken on these applications**. This file reports what happened.

## Result

| rail | MAPE | median | worst |
|---|---:|---:|---:|
| `vdd_arm` | 9.4% | 7.2% | 52% |
| `vdd_soc` | **4.5%** | 5.1% | 8% |
| **SUM** | **5.3%** | 4.9% | 16% |

**5.3% mean error on total power across 50 real applications**, from coefficients
fitted on an 11-point synthetic alu/mem grid containing none of them, with the
activity supplied by QEMU.

Published per-rail models report single-digit error on unseen workloads as the
good outcome; McCullough (ATC 2011) and Walker (TCAD 2017) both warn that
sub-3% on unseen workloads is a reason to distrust your validation set. 5.3% on
50 held-out real applications is inside that band and was not tuned toward.

## The three checks that were promised before the numbers existed

### 1. Spread — the model IS slightly under-responsive

    predicted  1289 – 1771 mW   ratio 1.37x
    measured   1156 – 1808 mW   ratio 1.56x

It compresses the range: the top end is close, the **bottom end is not reached**.
A good MAPE alone would have hidden this, which is why the check was written into
the prediction file in advance.

### 2. Bias — predictions run systematically LOW

    mean signed error  −3.9%

A correctable offset rather than scatter. Not corrected here: the frozen model is
reported as it was frozen.

### 3. Worst cases are DIAGNOSTIC, not random

The two 16% misses are `bb-grep` and `bb-awk`, and they fail identically:

| app | pred `vdd_arm` | meas `vdd_arm` |
|---|---:|---:|
| `bb-grep` | 493 | **324** |
| `bb-awk` | 483 | **322** |
| `chase` | 443 | **369** |
| `chase-big` | 445 | **383** |

`bb-grep` and `bb-awk` are the only two apps in the whole corpus drawing under
1200 mW. All four are **latency-bound** — pointer chasing and irregular text
processing, where the core stalls constantly.

⭐ **This is the assumption flagged in the prediction file as most likely to
hurt**, and it broke exactly where predicted: `aluMops/s` was taken as `insns/3`
because the grid's ALU op was a 3-instruction mul/add/eor body. For a stalling
workload that proxy badly overstates real ALU work, so `vdd_arm` is
over-predicted. Naming it in advance is what turns a 52% outlier from an
embarrassment into a diagnosis.

## What holds up best

`vdd_soc` at **4.5% MAPE with a worst case of 8%** — the tightest result of the
campaign. It is bandwidth-driven, and bandwidth is what QEMU estimates well
(`dram_bytes_proxy`, validated to 0.01% in steady state after accounting for
write streaming).

## What this demonstrates

QEMU predicted the per-rail power of 50 real applications on silicon it never
ran on, blind, to 5.3%. The emulator supplied the activity; the coefficients came
from measured rails; no power measurement of these applications informed the
prediction.

⚠️ **Scope, stated:** 1800 MHz, single-threaded, `insns/3` ALU proxy, time taken
from silicon cycle counts (`t = cycles / 1.8 GHz`) because QEMU's wall clock is
emulation speed and is never trusted. Fixing the ALU proxy for stall-heavy code
is the clearest next improvement, and the data to do it is in `RESULTS-50.csv`.

Raw BCU captures (82 MB) are not committed; `RESULTS-50.csv` carries the
per-app predicted/measured pairs.
