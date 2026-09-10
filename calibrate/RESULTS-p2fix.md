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

---

## A second OPP — 900 MHz

### ⚠️ FIRST, A CORRECTION TO EVERY EARLIER "FREQUENCY CONSTANT" CLAIM

The earlier sweeps reported "frequency constant at 1800 MHz across every point"
and treated that as a pinned condition. It was not. The board's governor is
`ondemand`, and it simply sat at max under full load. Every earlier result is
still valid AT 1800 MHz, but frequency was an **observed** constant, not a
controlled one. This run pins it properly (`userspace` governor +
`scaling_setspeed`), verified by reading `scaling_cur_freq` back.

Available OPPs: **500 / 900 / 1404 / 1800 MHz**.

### 🔴 THE 900 MHz FIT IS UNPHYSICAL, AND THE CAUSE IS MINE

    vdd_arm @900 = 143.7 − 4.6246·aluM/s − 207.2·GB/s + 772.6·cores   R² = 0.9984

R² of 0.998 with **negative coefficients on both ALU rate and bandwidth** — more
work drawing less power. Nonsense.

Cause: I cut the grid from 11 points to 7 to save time, dropping (1,1) and (3,3)
— the asymmetric points whose whole purpose was breaking the collinearity
between `active_cores` and the op rates. For ALU-only points `aluM/s` is
*perfectly* proportional to core count, so with 7 points the fit distributes
weight arbitrarily between them and still reports a near-perfect R².

**A high R² on collinear regressors is not evidence of anything**, and this is
the third time that has bitten this campaign. The 11-point design existed for
exactly this reason and I reduced it anyway.

### What the RAW measurements say — no fitting needed

| point | arm@1800 | arm@900 | ratio | soc@1800 | soc@900 | ratio |
|---|---:|---:|---:|---:|---:|---:|
| (1,0) | 481.0 | 238.3 | 2.02 | 831.5 | 826.2 | 1.006 |
| (2,0) | 656.3 | 307.0 | 2.14 | 832.9 | 828.0 | 1.006 |
| (3,0) | 898.1 | 384.3 | 2.34 | 833.5 | 827.9 | 1.007 |
| (0,1) | 638.3 | 323.0 | 1.98 | 991.6 | 942.7 | 1.052 |
| (0,3) | 1657.5 | 749.2 | 2.21 | 1118.2 | 1029.6 | 1.086 |
| (2,2) | 1641.0 | 716.7 | 2.29 | 1078.1 | 992.8 | 1.086 |
| (1,3) | 1860.1 | 824.7 | 2.26 | 1125.6 | 1032.3 | 1.090 |

    frequency ratio 2.00x
    vdd_arm power ratio  median 2.21   (1.98–2.34)  → core-frequency dependent
    vdd_soc power ratio  median 1.05   (1.006–1.090) → frequency-INDEPENDENT

⭐ And `vdd_soc`'s residual frequency sensitivity is INDIRECT: the ratio is
**1.006 on ALU-only points** (no traffic) and **1.086 on memory-heavy ones**. It
has no direct clock term at all — it responds to bandwidth, and bandwidth is
lower at 900 MHz because the cores issue slower.

### ⭐ THE `vdd_soc` MODEL TRANSFERS ACROSS OPPs UNCHANGED

Applying the 1800 MHz coefficients to the 900 MHz data, never fitted on it:

| point | GB/s | measured | predicted | err |
|---|---:|---:|---:|---:|
| (1,0) | 0.000 | 826.2 | 851.6 | 3.1% |
| (0,3) | 8.313 | 1029.6 | 1020.6 | 0.9% |
| (2,2) | 5.566 | 992.8 | 965.8 | 2.7% |
| (1,3) | 8.297 | 1032.3 | 1020.9 | 1.1% |

**MAPE 2.5%, worst 3.7%** — better than its own out-of-sample error at 1800 MHz.
`vdd_soc` is a pure bandwidth model and needs no frequency term.

### Where that leaves the models

    vdd_soc ≈ 851.0 + 0.0043·aluM/s + 20.4·GB/s
      → valid at BOTH 900 and 1800 MHz as-is (2.5–7% across both)

    vdd_arm ≈ 243.8 + 0.1266·aluM/s + 60.6·GB/s + 169.3·cores      @1800 MHz only
      → needs an explicit frequency term; measured scaling 2.21x per 2x clock

⚠️ Do NOT take 2.21x as a coefficient. It is the ratio of total rail power at
matched activity points, which mixes the frequency effect with the fact that the
same workload achieves different op rates at different clocks. Deriving a proper
frequency term needs the full 11-point grid at each OPP — and the 500/1404 MHz
points exist, so four OPPs are available when it is worth the time.

---

## The QEMU miss "+25% bias" — identified, and it is not a bias

### The geometry hypothesis was wrong, and the test that refuted it was nearly useless

QEMU's cache plugin defaults to L1D = 16 KB / 8-way with **`use_l2` OFF**, so
`data_misses` is an L1D count. The real A55 on this part is L1D 32 KB / 4-way,
L2 64 KB / 4-way per core, L3 512 KB / 16-way shared, all 64 B lines. Two
apparent problems: wrong geometry, and comparing QEMU's L1 count against
silicon's `l2d_cache_refill` (an L2 quantity).

Re-ran with the real geometry and `l2=on`:

| quantity | count | vs theory | vs silicon |
|---|---:|---:|---:|
| theory (first principles) | 4,194,304 | 100% | |
| silicon `l2d_cache_refill` | 4,283,525 | 102% | 100% |
| QEMU L1D misses, default geometry | 5,243,303 | 125% | 122% |
| QEMU L1D misses, **real geometry** | 5,243,285 | 125% | 122% |
| QEMU L2 misses, real geometry, `l2=on` | 5,243,781 | 125% | 122% |

⚠️ **Fixing the geometry changed the answer by 18 counts in 5.2 million
(0.0003%).** L1 misses, L2 misses and the wrong-geometry run agree to four
significant figures, because a 256 MiB stream has NO REUSE: every level misses
on every line regardless of size, associativity or how many levels are modelled.
**The workload is blind to the very parameters being corrected** — it would have
"confirmed" correct geometry just as happily as it refuted the fix.

### The actual mechanism: WRITE STREAMING

The excess is 5,243,285 − 4,194,304 = **1,048,981 ≈ 1,048,576 = 64 MiB / 64 B**,
exactly one full pass over the buffer. Tested by varying passes:

| passes | QEMU | theory | excess |
|---:|---:|---:|---:|
| 2 | 3,146,149 | 2,097,152 | **1,048,997** |
| 4 | 5,243,303 | 4,194,304 | **1,048,999** |
| 8 | 9,437,611 | 8,388,608 | **1,049,003** |

The excess is **constant to 6 counts while the workload quadruples**. It is the
one-time `memset` that faults the buffer in:

- **QEMU** counts all 1,048,576 line allocations.
- **Silicon does not** — the A55 detects full-cache-line writes and uses **write
  streaming**, skipping the read-for-ownership entirely.

Subtract it: QEMU 4,194,709 vs theory 4,194,304 — **0.01%**.

### What this means

**There is no +25% bias.** QEMU's miss counts are accurate to 0.01% in
steady state. The discrepancy is a specific, bounded modelling gap: the cache
plugin has no write-streaming, so it over-counts allocations for full-line write
patterns (`memset`, `memcpy`, page zeroing, buffer init).

- **Sign is known** (QEMU always over-counts), so it is a ceiling not a mystery.
- **Today's fits are unaffected** — the measured workloads are steady-state
  streaming, not initialisation.
- **It is countable if needed**: full-line writes are detectable in the plugin,
  and this is a legitimate upstream contribution to `contrib/plugins/cache.c`.
- ⚠️ It WILL matter for init-heavy or allocation-heavy real applications, in
  proportion to how much of their write traffic is full-line.

### Counter validation, final state

| counter | QEMU vs silicon |
|---|---|
| instructions retired | **0.1%** (compute), 3.6% (memory) |
| cache misses, steady state | **0.01%** after accounting for write streaming |
| cache misses, including buffer init | +25%, entirely the un-modelled write streaming |

---

## Closing the frequency question — PER-OPP COEFFICIENT SETS, not one scaling law

The full 11-point grid was re-run at 900 MHz (the earlier 7-point attempt was
under-determined and produced negative coefficients). Both OPPs now have the
same design.

    vdd_arm @1800 MHz = 243.8 + 0.1266·aluM/s + 60.62·GB/s + 169.3·cores   R² = 0.9924
    vdd_arm @ 900 MHz = 130.2 + 0.3826·aluM/s + 63.05·GB/s +  29.6·cores   R² = 0.9973

**Both fits have all-positive, physically interpretable coefficients.**

### Why there is no single frequency law here

The coefficient ratios between OPPs are incoherent:

| term | @1800 | @900 | ratio |
|---|---:|---:|---:|
| intercept | 243.8 | 130.2 | 1.87 |
| alu | 0.1266 | 0.3826 | **0.33** |
| bandwidth | 60.62 | 63.05 | 0.96 |
| cores | 169.3 | 29.6 | **5.72** |

`alu` falls and `cores` rises by wildly different factors. That is not physics —
it is the ALU/cores collinearity: on ALU-only points `aluM/s` is proportional to
core count, so the two fits split the same variance differently. Bandwidth, which
is *not* collinear with either, scales sensibly (0.96 — a memory-side quantity,
correctly almost frequency-independent).

### The pooled fit is MORE ACCURATE AND LESS USABLE

Pooling all 22 points with frequency and a `cores×freq` interaction:

    R² = 0.9950, MAPE 4.4%  —  but  alu = −0.0135  and  cores = −63.35

Both negative. The interaction term absorbs them, so the *combination* is
physical while the individual terms are not. ⚠️ **A hardware team plugging
activity factors into a spreadsheet cannot use a negative per-core cost**, and
Walker et al. name exactly this — collinearity producing "wild or negative
activity factors a hardware team will rightly reject even when total-power
predictions look fine."

**So the deliverable is per-OPP coefficient sets, which is also what the
published PMC models do** (Walker's is per-(V,f)). Two accurate, interpretable
models beat one accurate uninterpretable one.

### What it would take to get a real frequency law

Break the ALU/cores collinearity: run N cores at a *fraction* of full rate, so
op-rate and core-count vary independently. That needs throttling, which
introduces an idle-fraction confound that must then be measured and modelled.
The board also offers 500 and 1404 MHz, so four OPPs are available — but more
frequencies do not fix collinearity, only a better design does.

⚠️ Until then: **do not interpolate between the two coefficient sets.** Use the
set for the OPP you are at.
