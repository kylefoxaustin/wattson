# The DRAM rails — a saturating bandwidth model

Provenance **MEASURED** on IMX95LPD5EVK-19, 2026-09-09, kernel
`6.18.20-2.0.0-gb096ce610e95`, BCU ~147 Hz, CPU at 1800 MHz. Derived from the
same 11-point 2-D grid used for `vdd_arm`/`vdd_soc` — no extra board time.

## The rails respond almost entirely to bandwidth

| GB/s | `lpd5_vdd1` | `lpd5_vdd2` | `lpd5_vddq` | `vdd_ddr` | `vdd2_ddr` | `vddq_ddr` |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 3.7 | 43.0 | 3.9 | 123.5 | 0.2 | 3.8 |
| 5.53 | 68.9 | 310.5 | 15.2 | 536.4 | 4.1 | 15.0 |
| 10.86 | 98.0 | 455.8 | 19.3 | 588.8 | 7.3 | 18.9 |
| 14.10 | 114.1 | 527.4 | 21.6 | 617.6 | 9.1 | 21.3 |

`lpd5_vdd2` is the big one: **43 → 527 mW**, a 12x swing. `vdd_ddr` nearly
quintuples. These are not small terms.

## 🔴 A LINEAR FIT LOOKS FINE AND CONTRADICTS THE MEASURED IDLE FLOOR

    GROUP_DRAM = 90.7 + 43.26·GB/s      R² = 0.9677

R² of 0.97 — and its zero-bandwidth intercept is **90.7 mW against a measured
idle floor of 45.7 mW: 98% wrong**. Per-rail it is just as bad (`lpd5_vdd2`
72.8 vs 42.2; `vdd_ddr` 208.5 vs 118.9).

**A good R² inside the measured range says nothing about the intercept**, and
here the intercept is a quantity we had already measured independently at n=5.
The fit was free to contradict a measurement, and did.

## The cause: DRAM rail power is CONCAVE in bandwidth

Marginal cost per GB/s across adjacent grid points:

    0.00 →  5.53 GB/s :  62.2 mW per GB/s
    5.55 → 10.85 GB/s :  33.8
   10.86 → 13.54 GB/s :  31.2
   13.54 → 14.10 GB/s :  11.4

Saturating, and physically so: at low bandwidth each transaction pays a full
row activation; at high bandwidth row-buffer hits amortise it. A straight line
cannot express that and pays for the misfit at the intercept.

## Competing forms, with the intercept PINNED to the measured floor

| form | R² | intercept |
|---|---:|---|
| linear, free intercept | 0.9677 | 90.7 — **98% off the floor** |
| linear, pinned | 0.9550 | 45.7 by construction |
| **quadratic, pinned** | **0.9984** | 45.7 |
| sqrt, pinned | 0.9943 | 45.7 |

    GROUP_DRAM ≈ 45.7 + 72.88·BW − 2.089·BW²     R² = 0.9984   (BW in GB/s, mW)
    GROUP_DRAM ≈ 45.7 + 160.06·√BW               R² = 0.9943

⭐ **Pinning the intercept to the independently measured idle floor is the
point.** `AF_idle` was measured at n=5 with ≤1.7% spread; a regression has no
business inventing a different one. Constraining it costs 0.013 of R² on the
linear form and gains a model that agrees with the board at zero activity.

## ⚠️ Which form to use, and the trap in the better one

**The quadratic has the higher R² and MUST NOT be extrapolated.** Its BW² term
is negative, so it peaks at BW = 72.88 / (2 × 2.089) ≈ **17.4 GB/s** and predicts
FALLING DRAM power above that — unphysical. Measured data reaches 14.1 GB/s, so
it is sound inside the range and wrong immediately outside it.

**The sqrt form is monotonic and saturating**, costs 0.004 of R², and stays
physical at any bandwidth. **Prefer sqrt for anything that might extrapolate;
use the quadratic only within 0–14 GB/s.**

## Per-rail slopes (linear, for apportioning between rails)

| rail | idle mW | mW per GB/s | R² |
|---|---:|---:|---:|
| `lpd5_vdd2` | 42.2 | 34.28 | 0.971 |
| `vdd_ddr` | 118.9 | 33.74 | 0.804 |
| `lpd5_vdd1` | 3.5 | 7.75 | 0.955 |
| `lpd5_vddq` | 3.8 | 1.23 | 0.932 |
| `vddq_ddr` | 3.8 | 1.21 | 0.931 |
| `vdd2_ddr` | 0.2 | 0.64 | 0.998 |

`vddq_ddr` and `lpd5_vddq` agree to 2% as expected — SJ3–SJ9 jumper-short them
on this board (AN14449). Do not count both.

⚠️ `vdd_ddr`'s R² of 0.804 is the weakest here: it is the DRAM *interface* rail
and its first step (123 → 536 mW) is far steeper than everything after, so it
saturates hardest. It needs its own curvature term rather than the group slope.

## Why measured rails beat the datasheet here

VAMPIRE (SIGMETRICS 2018) found **datasheet IDD values overestimate measured DRAM
power by ~2.9x on average**, and that re-simulating with measured currents cut
deviation to ~18.8%. So a DRAMPower-style model fed with LPDDR5 vendor IDD
numbers would be expected to overstate these rails substantially. The rails above
are measured on this board, which is the correction that paper calls for.
