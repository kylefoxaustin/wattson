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
