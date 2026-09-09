# P1 results — measured against the predictions in PREREGISTRATION-p1.md

Results go here beside the predictions they answer, whichever way they fall. No
value in the pre-registration has been edited since it was frozen.

---

## Step 1 — THE IDLE FLOOR (pre-registration §5 item 1) — **DONE**

Provenance: **MEASURED** on IMX95LPD5EVK-19 silicon, 2026-09-09.

### Census (rides with the number, per Law 1)

| | |
|---|---|
| board | IMX95LPD5EVK-19, ECID `0x6E5F04E000000006000C070D322DE99D` |
| SM | Build 763, `mx95evk`, i.MX95 B0 MIMX9596XVZXNAC |
| kernel | `6.18.20-2.0.0-gb096ce610e95` — read live from the board, not assumed |
| BSP | LF_v6.18.20-2.0.0, flashed 2026-09-09 (matches the FRDM exactly) |
| state | idle at a root shell, up 10 min, 6 CPUs, load 0.19/0.18/0.15, 1 of 208 procs running |
| instrument | BCU (local build, `uuu_1.5.243` era deps), `-board=imx95evk19`, ~147 samples/s |
| method | 5 independent captures, ~35 s each; per-rail MEDIAN of the 5 run-medians |

⚠️ "Idle" here means a quiescent Linux, NOT a dead board: load average 0.19.
`AF_idle` therefore includes whatever that background activity costs, and any
later use of this floor inherits that definition.

### The floor

| rail | median mW (n=5) | min | max | spread |
|---|---:|---:|---:|---:|
| `vdd_soc` | **822.6** | 821.6 | 823.1 | 0.2% |
| `vdd_arm` | **144.6** | 144.4 | 146.0 | 1.1% |
| `vdd_ddr` | 118.9 | 118.4 | 119.2 | 0.6% |
| `lpd5_vdd2` | 42.2 | 41.9 | 42.2 | 0.5% |
| VDDQ (`vddq_ddr` + `lpd5_vddq`, summed) | 7.6 | 7.5 | 7.7 | 3.0% |
| `lpd5_vdd1` | 3.5 | 3.5 | 3.5 | 1.7% |
| `vdd2_ddr` | 0.2 | 0.2 | 0.2 | 7.1% |
| **TOTAL** | **1139.5** | | | |

VDDQ is summed because SJ3–SJ9 jumper-short `vddq_ddr` and `lpd5_vddq` on this
board (AN14449). They read equal, as predicted; counting both would double-count.
`vdd2_ddr`'s 7.1% spread is noise on a 0.2 mW value, not instability.

### ⭐ THE FLOOR MOVES WITH THE BSP — WHICH IS WHY IT WAS RE-MEASURED

A smoke-test capture taken BEFORE flashing, on the board's shipped 6.12.49 BSP:

| rail | 6.12.49 (shipped) | 6.18.20 (flashed) | change |
|---|---:|---:|---:|
| `vdd_arm` | 112.0 | **144.6** | **+29%** |
| `vdd_ddr` | 135.0 | 118.9 | −12% |
| `vdd_soc` | 825.4 | 822.6 | −0.3% |

Taking the floor before flashing would have put `AF_idle` 29% wrong on the exact
rail P2 and P4 are built around. A baseline must match the configuration it
describes; here that is not a principle, it is a 29% error.

### What this says before any workload runs

**`vdd_soc` is 72% of the idle floor; `vdd_arm` is 13%.** Per AN14449 Fig 1,
NPUMIX/GPUMIX/VPUMIX all sit in VDD_SOC, so the largest term at idle is also the
one whose activity is least attributable. P2 compares `vdd_arm` between two
workloads — a real test, but of ~13% of what the board draws.

---

## Still open

| prediction | state |
|---|---|
| P1 (DRAM rails discriminate) | not yet run — needs `bench-alu`/`bench-mem` on silicon |
| P2 (`vdd_arm` tracks core activity) | not yet run |
| P3 (SoC ratio vs AN14449's 1.36x) | not yet run |
| P4 (bridge linear in U) | **BLOCKED** — WFI does not wake on silicon (§0.7) |

`AF_idle` is now MEASURED. `AF_max` needs the U=1.0 point, which requires the
bare-metal workloads to run on this board — the U-Boot + `fastboot` path proven
during the BSP flash is the mechanism.

---

## Steps 3 — P1, P2, P3 ON SILICON — **RUN, MIXED RESULT, ONE RETRACTION**

Provenance: **MEASURED** on IMX95LPD5EVK-19, 2026-09-09, same census as the idle
floor above (kernel `6.18.20-2.0.0-gb096ce610e95`, BCU ~147 Hz). Workloads are
the bare-metal `bench-alu-silicon` / `bench-mem-silicon` builds, loaded from
U-Boot with `fatload` and started with `go`.

| rail | idle floor | bench-alu | bench-mem |
|---|---:|---:|---:|
| `vdd_arm` | 144.6 | **409.9** | **289.5** |
| `vdd_soc` | 822.6 | 780.1 | 775.9 |
| `vdd_ddr` | 118.9 | 119.9 | 119.3 |
| `lpd5_vdd2` | 42.2 | 42.0 | 41.7 |

### P1a — **PASS**
`bench-alu` leaves GROUP_DRAM within **0.6%** of the idle floor (45.4 vs 45.7 mW),
against a predicted ±10%. The compute workload provably does not touch DRAM.

### P1b — **NOT TESTED. THE CHECKER PRINTED A FALSE PASS AND IT IS RETRACTED.**

The evaluation script printed `ratio infx PASS`. It is wrong. The inputs were:

    bench-alu GROUP_DRAM - idle = -0.29 mW
    bench-mem GROUP_DRAM - idle = -0.57 mW

**Both negative.** The DRAM rails during the memory workload sit BELOW the idle
floor. The script divided by a near-zero denominator, got infinity, and compared
it against ">= 10x". A gate that reports PASS on a negative numerator cannot
fail, which is the exact defect class this campaign keeps finding in other
people's tests and which I then wrote into my own.

The real result is a NULL: **`bench-mem` produced no measurable DRAM rail
activity.** P1b is untested, not passed.

### P2 — **PASS**
`vdd_arm` ratio alu/mem = **1.416**, inside the predicted 1.05–1.60. The
compute-bound workload draws more core power than the memory-bound one, by
roughly the predicted margin.

### P3 — **FAIL**
SoC-group ratio mem/alu = **0.907**, predicted 1.15–1.55 (bracketing AN14449's
own 1.36x). `bench-mem` draws LESS total power than `bench-alu` — opposite in
direction, not merely outside the band.

### 🔴 P1b AND P3 SHARE ONE CAUSE, AND IT IS THE METHOD, NOT THE MODEL

`go` on a flat binary requires `dcache off` in U-Boot, which drops the MMU and
the data cache — otherwise the jump takes an instruction-fetch translation fault.
**With caches disabled `bench-mem` cannot stream.** Every access becomes a slow,
unpipelined transaction, so DRAM utilisation stays near zero and the core spends
its time stalled rather than issuing. That predicts exactly what was measured:
flat DRAM rails (P1b null) and lower total power than the compute workload
(P3 fail).

⚠️ **THEREFORE THESE TWO CELLS DO NOT INDICT THE PREDICTIONS.** They indict the
delivery mechanism. A bare-metal `go` with caches off is not a valid vehicle for
a memory-bandwidth workload, and any conclusion about memory power drawn from it
would be a statement about the harness.

`vdd_arm` (P2) is unaffected by this reasoning — the compute workload is
register-only and does not depend on the cache — which is why P2 is reported as
a result and P1b/P3 are not.

### What has to change before P1b and P3 can be answered

The workload must run WITH caches enabled. Options, in order of preference:
1. run the workloads as a Linux userspace program on the booted board — caches
   on, no `go`, no MMU games, and the same BCU window
2. have the bare-metal image enable the MMU and caches itself before the
   measured region
3. accept that bare-metal `go` measures only cache-independent workloads

Option 1 also fixes the wall-clock problem: a Linux process can be timed and
repeated n=5 without a reboot between runs.

### Scoreboard

| prediction | result |
|---|---|
| P1a — DRAM flat for compute workload | **PASS** (0.6% of floor) |
| P1b — DRAM discriminates >= 10x | **UNTESTED** — false PASS retracted; method invalid |
| P2 — vdd_arm ratio 1.05–1.60 | **PASS** (1.416) |
| P3 — SoC ratio 1.15–1.55 | **FAIL** (0.907) — attributed to caches-off, not to the model |
| P4 — bridge linear in U | **BLOCKED** — WFI does not wake on silicon |
