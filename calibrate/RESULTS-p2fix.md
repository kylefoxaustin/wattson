# P2-fix results — what actually predicts `vdd_arm`

Answers PREREGISTRATION-p2fix.md. Provenance **MEASURED** on IMX95LPD5EVK-19,
2026-09-09, kernel `6.18.20-2.0.0-gb096ce610e95`, BCU ~147 Hz, **CPU pinned at
1800 MHz across every point** (recorded per point, not assumed).

## The question

P2 failed because `bench-mem` drew 759.8 mW on `vdd_arm` while `bench-alu` drew
474.0 — the memory workload cost MORE core power while retiring FEWER
instructions. `total_insns` is the activity vector's core term. What does track
core power?

## Two failed designs first, because both were mine

**1-D op-mix sweep — WRONG AXIS.** Strided access (`i = (i+8191) % n`) to defeat
the cache also defeated the PREFETCHERS: throughput saturated at ~99 MB/s while
`bench-mem` ran at GB/s. It swept ALU rate while holding bandwidth pinned and
low, so it never entered the regime it was meant to explain.

**1-D bandwidth sweep — COLLINEAR.** Sequential streaming fixed the bandwidth
range (0 → 3.99 GB/s), but on ONE core more streaming means less ALU: the two
predictors came out at correlation ≈ -1. Bandwidth-only R²=0.794 and ALU-only
R²=0.793 — a 0.001 gap. **Two collinear predictors fit identically and cannot be
separated**, so that sweep could not answer the question either. (The literature
names this: Walker et al. use VIF pruning for exactly this hazard.)

## The design that worked: a 2-D grid

`n_alu` threads doing register-only work and `n_mem` threads streaming
sequentially, each pinned to its own core, all fully busy — so ALU rate and
bandwidth are driven by INDEPENDENT knobs with no idle-fraction confound.
11 points, `n_alu + n_mem <= 6`.

**Measured correlation between the knobs: -0.290** (was ≈ -1). Separable.

| n_alu | n_mem | aluM/s | GB/s | `vdd_arm` mW | `vdd_soc` mW |
|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 299.0 | 0.000 | 481.0 | 831.5 |
| 2 | 0 | 598.5 | 0.000 | 656.3 | 832.9 |
| 3 | 0 | 897.9 | 0.000 | 898.1 | 833.5 |
| 0 | 1 | 0.0 | 5.533 | 638.3 | 991.6 |
| 0 | 2 | 0.0 | 10.854 | 1243.2 | 1070.2 |
| 0 | 3 | 0.0 | 14.101 | 1657.5 | 1118.2 |
| 1 | 1 | 297.6 | 5.555 | 979.8 | 1000.2 |
| 2 | 2 | 595.4 | 10.863 | 1641.0 | 1078.1 |
| 3 | 3 | 822.9 | 13.541 | 2129.7 | 1121.7 |
| 1 | 3 | 294.4 | 14.096 | 1860.1 | 1125.6 |
| 3 | 1 | 893.9 | 5.532 | 1365.6 | 1008.4 |

## ⭐ THE ANSWER

| model for `vdd_arm` | R² |
|---|---:|
| instructions (ALU rate) alone | **0.031** |
| bandwidth alone | 0.784 |
| **both** | **0.990** |

**Instruction count explains 3% of core-rail power.** Not "less than hoped" —
essentially nothing. Adding memory traffic takes it to 99%.

    vdd_arm ≈ 206.1 + 0.7320·(ALU Mops/s) + 98.0·(GB/s)     mW @ 1800 MHz
    vdd_soc ≈ 851.0 + 0.0043·(ALU Mops/s) + 20.4·(GB/s)     mW @ 1800 MHz

`vdd_soc` is almost purely bandwidth-driven (0.959 from bandwidth alone); its ALU
coefficient is negligible.

## Out-of-sample validation — the test that matters

The literature's warning (Walker et al.): **coefficient stability beats fit
quality**; a small training set gives a great R² and garbage extrapolation. So
the grid-fitted coefficients were used to predict the earlier 1-D bandwidth
sweep — SINGLE-threaded, different loop structure, measured before the grid
existed and not part of the fit.

| rail | MAPE | worst point |
|---|---:|---:|
| `vdd_arm` | **8.9%** | 15.2% |
| `vdd_soc` | **4.8%** | 7.3% |

That is in the credible band. McCullough et al. (ATC 2011) and Walker both report
single-digit per-rail error as the GOOD published outcome, and Walker warns that
anything under ~3% across unseen workloads should make you suspicious of your own
validation set. 8.9% is a result; 1% would have been a reason to re-examine.

## ⚠️ Limits, stated rather than discovered later

- **Valid at 1800 MHz only.** Every point was taken at that OPP and it is part of
  the claim. The coefficients must not be reused at another frequency.
- **The model does NOT extrapolate to idle.** At (0 ALU, 0 GB/s) it predicts
  206.1 mW for `vdd_arm` against a measured floor of 144.6 — **43% over**. It is
  an interpolation over the fitted range, not a physical model down to zero.
  (`vdd_soc` extrapolates well: 851.0 predicted vs 822.6 measured, 3%.)
- **Coefficients are A55/i.MX 95-specific.** The sign of the stall-power effect
  is microarchitecture-dependent — some cores clock-gate on stalls and draw LESS
  when memory-bound. These numbers do not transfer to another SoC.
- **Bandwidth here is a MEASURED host-side quantity**, not something QEMU
  produces. Closing the loop needs QEMU's `dram_transactions_est` validated
  against the board's own PMU counters for the same workload — the literature
  identifies that mapping, not the regression, as the dominant error term.

## What this changes for the activity vector

The vector's core term is `total_insns`, and this says that term is nearly
uncorrelated with core-rail power. It already carries `data_misses` and
`dram_transactions_est`; those are the analogs of the L2/bus-cycle events that
published PMC models actually use. **The core AF must be built on memory traffic
as well as instruction count, or it will mis-rank exactly the workloads that
matter.**

---

## Loop closure — QEMU counters through the model — AND A CORE-COUNT TERM

### First: does QEMU's activity match the silicon's own PMU?

Same deterministic static binary (`workloads/linux/probe.c`, fixed iteration
counts, no wall-clock dependence) run on the EVK under `perf` and under
`qemu-aarch64` with the TCG insn + cache plugins.

| workload | counter | silicon PMU | QEMU | error |
|---|---|---:|---:|---:|
| alu | `inst_retired` / `total_insns` | 1,201,601,070 | 1,200,039,789 | **0.1%** |
| mem | `inst_retired` / `total_insns` | 213,267,051 | 205,561,916 | **3.6%** |
| mem | `l2d_cache_refill` / `data_misses` | 4,283,525 | 5,243,303 | **+22.4%** |

**QEMU's instruction counts are essentially exact.** Its miss count runs ~25%
high, and first principles say the silicon is the correct one: the `mem` workload
streams 64 MiB x 4 passes and, with write-allocate, `b[i] += 3; s += b[i]` costs
ONE line fill per 64 B → 4,194,304 expected. Silicon measured 4,283,525 = **102%
of theory**; QEMU's 5,243,303 = **125%**. A consistent correctable bias, not noise.

⚠️ The `alu` miss comparison shows "99% error" (silicon 46,679 vs QEMU 375) and
means nothing: that workload has no memory traffic, `perf` counts the whole
process including libc startup and kernel entries, and a percentage error on a
near-zero denominator is exactly the trap that produced the retracted P1b PASS.

### Then: drive the model from QEMU and compare to the rails

QEMU supplies COUNTS; the board supplies TIME (`timing.wall_ns`) — QEMU has no
clock worth trusting, which is the whole design.

⭐ **QEMU-driven and PMU-driven predictions agree with each other** (644.1 vs
644.9 mW on the alu case). Feeding the model the emulator's counters gives
essentially the same answer as feeding it the silicon's own counters. **The
emulator half works.**

But both were 38–55% off the measured `vdd_arm` — so the error was in the MODEL,
not in QEMU.

### The missing term: ACTIVE CORES

Direct evidence: grid point `(2,0)` ran **598 aluM/s on 2 cores → 656 mW**; the
single-core probe ran **599 aluM/s on 1 core → 465 mW**. Same aggregate op rate,
40% different power. Aggregate rate cannot express it; each active core carries
fixed overhead (clock tree, pipeline, L1).

| rail | model | in-sample R² | out-of-sample (alu / mem) |
|---|---|---:|---|
| `vdd_arm` | 2-term | 0.9896 | 38.5% / 54.6% |
| `vdd_arm` | **3-term** | **0.9924** | **5.1% / 4.2%** |
| `vdd_soc` | **2-term** | 0.9596 | **3.2% / 6.5%** |
| `vdd_soc` | 3-term | 0.9709 | 11.3% / 14.1% |

### 🔴 AND `vdd_soc`'s 3-TERM FIT IS A TEXTBOOK OVERFIT, CAUGHT LIVE

Its in-sample R² **rose** (0.9596 → 0.9709) while out-of-sample error **tripled**
(3.2% → 11.3%). Its core coefficient came out **negative (−73.1 mW per core)**,
which is unphysical — more active cores cannot reduce SoC power. Cause: in the
grid `active_cores = n_alu + n_mem`, partly collinear with the other two
regressors, so the fit bought R² by absorbing variance into a meaningless term.

That is Walker et al.'s warning — **coefficient stability beats fit quality** —
reproduced in our own data within an hour of reading it. The higher R² was the
wrong thing to optimise and only the held-out test exposed it.

## THE MODELS (both @ 1800 MHz, both QEMU-drivable)

    vdd_arm ≈ 243.8 + 0.1266·(ALU Mops/s) + 60.6·(GB/s) + 169.3·(active cores)
    vdd_soc ≈ 851.0 + 0.0043·(ALU Mops/s) + 20.4·(GB/s)

    out-of-sample: vdd_arm 4–5%,  vdd_soc 3–7%

Different term counts per rail, deliberately: the core term earns its place on
`vdd_arm` and fails the held-out test on `vdd_soc`. Using the same functional
form for both would have looked tidier and been wrong.
