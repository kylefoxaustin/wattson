# P2-fix pre-registration — what predicts `vdd_arm`, if not instructions?

**FROZEN before the sweep is run.** Same rule as PREREGISTRATION-p1.md: no
predicted value edited after the first measurement.

## What P2 established

`bench-mem` drew **759.8 mW** on `vdd_arm`; `bench-alu` drew **474.0 mW** — while
retiring FEWER instructions. Ratio 0.624 against a predicted 1.05–1.60. So
`total_insns`, the activity vector's core term, does not track core power.

## Why two points cannot fix it

We have exactly two measurements. Any two-parameter model fits two points
perfectly, and the fit would be meaningless — it would confirm whatever model
was proposed. **The experiment must sweep**, so that a model has more points to
fit than it has parameters.

## The sweep

One workload, `bench mix <pct>`, where `pct` is the fraction of its inner loop
spent on memory access rather than register ALU work. Seven points:
`pct ∈ {0, 10, 25, 50, 75, 90, 100}`, 30 s each, caches on, single-threaded,
Linux userspace on the EVK. `pct=0` reduces to `bench alu`; `pct=100` to
`bench mem`.

The program reports its OWN exact counts — ALU ops and memory ops — so no
perf-counter access or estimation is needed.

## Predictions

**H1 — instructions alone do not explain `vdd_arm`.**
A least-squares fit of `vdd_arm` against ALU-op rate alone gives **R² < 0.5**.
*Refuted if* R² ≥ 0.5 — which would mean the P2 result was an artifact of the
two specific workloads rather than a property of the proxy.

**H2 — a two-term model does explain it.**
`vdd_arm ≈ c0 + c1·(alu_ops/s) + c2·(mem_ops/s)` fits with **R² ≥ 0.90**, and
**c2 > c1** (a memory op costs more core power than an ALU op).
*Refuted if* R² < 0.90, or if c2 ≤ c1 — the latter would mean memory ops are not
individually more expensive and the P2 inversion needs a different explanation
(e.g. frequency scaling, or the LLC/interconnect sitting on `vdd_arm`).

**H3 — `vdd_arm` rises monotonically with memory fraction.**
Every step up in `pct` raises `vdd_arm`.
*Refuted if* any step falls by more than the idle-floor noise (±1.1% on this
rail, from the n=5 floor).

## Stated in advance: what would make this whole approach wrong

If `vdd_arm` turns out to be dominated by **DVFS** — the governor raising clock
or voltage under load — then neither op-rate term is causal and the right model
is frequency-based. The sweep therefore also records `scaling_cur_freq` per
point. **If frequency is not constant across the sweep, H2's fit is confounded
and must be reported as such rather than as a activity model.**

---

## AMENDMENT (2026-09-09, after the first sweep) — THE AXIS WAS WRONG

The op-mix sweep above was run and its results are recorded in RESULTS-p1.md.
It refuted H1, H2 and H3 — and those refutations are **not trustworthy**, because
the workload could not enter the regime under study.

Its memory mode strided `i = (i + 8191) % n` to defeat the cache. That also
defeated the **prefetchers**, so memory throughput saturated at ~12.4 Mops/s
(~99 MB/s) and stayed flat from pct=25 upward. `bench-mem`, whose 759.8 mW on
`vdd_arm` is the whole reason P2 failed, ran at ~2–4 GB/s — **20–45x more
traffic**. So the sweep varied ALU rate while holding bandwidth pinned and low.
H1's R²=0.976 for ALU-alone is an artifact of that: with bandwidth constant,
ALU rate is the only variable left.

⚠️ A control that cannot enter the regime it is meant to explain is the wrong
instrument, and this one was chosen by me.

**What the first sweep does support**, narrowly: at 1.8 GHz, in a LATENCY-BOUND
memory regime, `vdd_arm` tracks ALU rate and memory ops slightly REDUCE it
(stalls idle the pipeline). That is a real result about a different regime.

### Corrected axis: sweep BANDWIDTH

`bench bw <pct>` interleaves SEQUENTIAL streaming (prefetcher-friendly, real
bandwidth) with register ALU work. Verified to span **0 → 3.9 GB/s**.

Points: `pct ∈ {0, 1, 2, 5, 10, 25, 100}` — weighted low, because bandwidth
saturates by pct≈25. The regression x-axis is the **measured GB/s**, not `pct`,
so uneven spacing costs nothing.

### Predictions, restated against the corrected axis

**H1b — `vdd_arm` rises with memory BANDWIDTH.** Fitting `vdd_arm ≈ c0 + c1·GB/s`
gives **R² ≥ 0.80** with **c1 > 0**.
*Refuted if* c1 ≤ 0, or R² < 0.80 — either would mean bandwidth is not the
variable that explains the P2 inversion either, and the cause lies elsewhere
(LLC/interconnect placement on the rail, or something not yet considered).

**H2b — bandwidth beats instruction count.** The bandwidth-only fit has a HIGHER
R² than an ALU-rate-only fit over the same seven points.
*Refuted if* ALU-rate alone fits as well or better.

**H3b — the fit reaches P2's operating point.** The model, extrapolated to
`bench-mem`'s measured bandwidth, predicts `vdd_arm` within **±15%** of the
759.8 mW actually measured there.
*Refuted if* outside ±15% — the model would then fit the sweep but fail to
explain the very observation that motivated it, which is the outcome most worth
catching.

Frequency is pinned by observation at 1800 MHz across all points and recorded
per point; any model stated from this data is valid AT THAT OPP and must say so.
