# Prior art — has anyone done this before?

Surveyed 2026-09-09. Short answer: **the composition appears to be unpublished.**
Both halves have strong prior art; nobody has published functional-emulator
activity regressed against per-rail measured silicon power.

## The gap

- **Per-rail calibration** is done in the literature from **PMCs on the silicon
  itself**, not from an emulator.
- **QEMU-side power work** exists but never closes the loop to measured rails.
- **Simulator work that does close the loop** (Sniper/McPAT, gem5+McPAT,
  GemStone) uses TIMING-capable simulators and validates against socket or
  per-cluster energy, not rails.

So: methodological prior art for the regression side, feasibility prior art for
the non-cycle-accurate side, and nothing joining them with a purely functional
emulator.

## The closest work, and it independently confirms our P2 result

**Walker et al., "Accurate and Stable Run-Time Power Modeling for Mobile and
Embedded CPUs," IEEE TCAD 36(1) 2017.**
<https://ieeexplore.ieee.org/document/7464834/> ·
<https://www.arm.ecs.soton.ac.uk/projects/cpu-power-modeling/>

Southampton + Arm. ODROID-XU3, which carries **per-rail INA231 shunts** for the
A15 cluster, A7 cluster, GPU and DRAM — structurally the same setup as our BCU
rails. OLS regression of rail power on PMC events × V²f; 2.8% MAPE on A15.

Two findings that land directly on ours:

1. **Retired instruction count is NOT in their model.** The A15 predictors are
   cycle count, *speculatively-executed* instructions, L2D cache load, unaligned
   load/store, integer instructions, L1I access, and **bus cycles**.
2. **Their memory workloads are among the HIGHEST power on the cluster rail** —
   above the compute kernels.

That is our `bench-mem` > `bench-alu` inversion, on different silicon, years
earlier. Our R²=0.031 for instructions-alone is the expected result, not an
anomaly.

## Pitfalls the literature reports, mapped to what we hit

| pitfall | source | our encounter |
|---|---|---|
| **Collinearity silently breaks interpretability**; needs VIF-style pruning, or you get wild/negative activity factors a hardware team will reject | Walker | Hit exactly this: 1-D sweep gave corr ≈ -1, bandwidth-only R²=0.794 vs ALU-only 0.793. Fixed with a 2-D grid (corr -0.290) BEFORE knowing it was a named hazard |
| **Coefficient stability beats fit quality**; small training sets give great R² and garbage extrapolation | Walker | Why we validated out-of-sample: 8.9% / 4.8% MAPE on held-out workloads |
| **Simulator→silicon counter mapping is the dominant error, not the regression** (gem5 misjudged runtime up to 2.5x per benchmark) | GemStone / PATMOS 2017 | NOT yet addressed. QEMU's `dram_transactions_est` must be checked against the board's real PMU counters |
| **Datasheet DRAM currents overestimate measured power ~2.9x** | VAMPIRE, SIGMETRICS 2018 <https://arxiv.org/html/1807.05102> | Justifies measuring the LPDDR5 rails instead of taking vendor IDD |
| **Bottom-up analytical coefficients don't transfer**; everyone ends up regressing against silicon | Xi HPCA'15; Butko ~24%; PowerTrain; McPAT-Calib | Don't attempt McPAT-style coefficients for the i.MX 95 |
| **Expect a hard error floor**; single-digit per-rail error is the GOOD outcome, sub-3% on unseen workloads is suspicious | McCullough, USENIX ATC 2011 | Our 8.9% is a result; 1% would have been a reason to re-check the validation set |
| **Stall-power sign is microarchitecture-specific** — some cores clock-gate on stalls and draw LESS when memory-bound | MAPG, UCSD | Our coefficients are A55-specific and must not transfer |

## Nearest neighbours by family

- **PMC → per-rail on silicon**: Walker TCAD 2017; Bircher & John (trickle-down,
  per-subsystem, ISPASS 2007); Isci & Martonosi (MICRO 2003, the ancestor of
  "activity vectors"); McCullough ATC 2011 (the canonical negative result).
- **QEMU-based power/timing**: Chen/Yang et al., "Performance and Power Profiling
  for Emulated Android Systems," ACM TODAES 19(2) 2014 — the closest QEMU paper
  found; pluggable timing and power models. ⚠️ Full text was not retrievable, so
  whether it ever calibrated against measured hardware power is UNCONFIRMED;
  secondary descriptions suggest user-supplied state-machine models, no rail
  calibration. MARSSx86 bolts a cycle-accurate core onto QEMU — the community's
  answer to "QEMU has no microarchitecture" was to add one.
- **Non-cycle-accurate abstraction that still carries power**: Sniper's interval
  simulation (explicitly not cycle-accurate) + McPAT, validated at ~8.3% power
  error on SPEComp — the strongest precedent that our kind of abstraction can
  work, though validated at socket level.
- **DRAM**: DRAMPower (command counts × IDD energy — our
  `dram_transactions_est` is a coarse cousin); VAMPIRE; DRAMPower HPC
  calibration <https://arxiv.org/pdf/2411.17960>.
- **Host energy attribution**: Kepler, Scaphandre, PowerAPI — attribute MEASURED
  RAPL energy downward to containers. Same regression shape, opposite direction:
  they need real hardware energy as ground truth.
- **No upstream QEMU energy plugin exists.** The closest, CEA-LIST's
  `csram-qemu-plugin`, states its energy model is "completely artificial."

## What this means for our design

The literature's conclusion for simulators is the split we already adopted:
**the emulator supplies activity; energy-per-event comes from elsewhere.** McPAT's
failures against silicon are what forced that conclusion, and QEMU is further
from silicon than gem5 — so the posture is not conservatism, it is the only
defensible one.

The predictor QEMU fundamentally cannot supply is **cycles** (time at V,f), which
is the dominant term in every successful PMC model. The literature's answer is to
take time from the real board rather than from the emulator — which is exactly
what `timing.wall_ns` and the BCU window do.
