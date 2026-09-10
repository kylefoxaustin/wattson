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

---

## Step 3b — RE-RUN WITH CACHES ON — **AND A RETRACTION OF THE P2 PASS ABOVE**

The caches-off runs in Step 3 were invalidated by their own delivery mechanism.
Re-run as Linux userspace processes on the booted board (`workloads/linux/bench.c`):
caches on, no MMU games, TIME-BOUNDED so both runs are exactly 60 s and their
mean-power ratio is directly comparable.

Provenance: **MEASURED** on IMX95LPD5EVK-19, 2026-09-09, same census
(kernel `6.18.20-2.0.0-gb096ce610e95`, BCU ~147 Hz). Both runs 60.0 s.
`mem` streams a 512 MiB buffer, far larger than any cache: ~17.0e9 element-ops,
roughly 4.5 GB/s of real DRAM traffic.

| rail | idle floor | bench-alu | bench-mem |
|---|---:|---:|---:|
| `vdd_arm` | 144.6 | 474.0 | **759.8** |
| `vdd_soc` | 822.6 | 817.8 | 1000.2 |
| `vdd_ddr` | 118.9 | 120.8 | **539.1** |
| `lpd5_vdd1` | 3.5 | 3.4 | **72.6** |
| `lpd5_vdd2` | 42.2 | 41.8 | **328.4** |

### 🔴 RETRACTION: THE P2 "PASS" IN STEP 3 IS WITHDRAWN

Step 3 reported P2 as a PASS at 1.416 and argued it survived the caches-off
problem because "`bench-alu` is register-only and cache-independent, which is why
P2 is reported as a result while P1b/P3 are not."

**That argument was wrong.** P2 is a RATIO, and its denominator is `bench-mem` —
which was measured under exactly the method Step 3 had just declared invalid.
Cache-independence of the numerator does not rescue a ratio whose denominator is
contaminated. With the method fixed:

| prediction | caches OFF (invalid) | caches ON (valid) | effect of the harness |
|---|---:|---:|---|
| P2 `vdd_arm` alu/mem | 1.416 → "PASS" | **0.624 → FAIL** | crosses the band |
| P3 SoC ratio mem/alu | 0.907 → FAIL | **1.852 → FAIL** | inverts direction |

**The broken harness did not add noise. It INVERTED both results** — turning a
refutation into a false PASS on P2, and a too-high ratio into a too-low one on
P3. Only P1a, which never involves `bench-mem` at all, survives from Step 3.

### P1a — **PASS** (again, and this one was never in doubt)
`bench-alu` leaves GROUP_DRAM within **1.0%** of the idle floor.

### P1b — **DISCRIMINATES**, but the prediction was mis-formulated
    GROUP_DRAM   idle 45.7    alu 45.2 (-0.46 mW, at noise)    mem 401.0 (+355.3 mW)

The memory workload raises the DRAM rails ~8.8x above the floor; the compute
workload does not move them at all. The substance of P1b — "the DRAM rails
discriminate the two workloads" — is confirmed emphatically.

⚠️ But the prediction asked for a ratio `(mem-idle)/(alu-idle) >= 10x` whose
DENOMINATOR THE PREDICTION ITSELF EXPECTED TO BE ~ZERO (P1a says `alu` sits at
the floor). A ratio against a predicted-zero denominator is not evaluable; that
is a defect in how P1b was written, not in the result. The replacement check
requires a positive denominator above a stated noise floor (0.5 mW) and reports
a NULL otherwise — which is what caught the Step 3 false PASS.

### P2 — **FAIL**, 0.624 (predicted 1.05–1.60)
`bench-mem` draws MORE core power (759.8 mW) than `bench-alu` (474.0 mW).

The pre-registration named this outcome in advance: *"Refuted if the ratio is
< 1.0 — would mean stall cycles cost more than issue cycles, and the insn-count
proxy is the wrong core activity metric."* That interpretation was fixed before
the number existed, so it is a finding rather than a rationalisation:
**instructions retired is the wrong proxy for `vdd_arm` activity on this part.**

### P3 — **FAIL**, 1.852 (predicted 1.15–1.55, bracketing AN14449's 1.36x)
Now overshooting rather than inverting. Per the pre-registration, a P3 miss is
weaker evidence than P1/P2 because our workloads are not Stream and Dhrystone —
`bench-mem` at ~4.5 GB/s may simply be more memory-intense than NXP's Stream
configuration. It indicts the comparison, not necessarily the model.

### Scoreboard after the method fix

| prediction | result |
|---|---|
| P1a | **PASS** — 1.0% of floor |
| P1b | **CONFIRMED IN SUBSTANCE** (+355 mW vs +0), ratio form not evaluable |
| P2 | **FAIL** — 0.624; insn-count is the wrong `vdd_arm` proxy |
| P3 | **FAIL** — 1.852; weaker evidence, different workloads |
| P4 | **BLOCKED** — WFI does not wake on silicon |

### What P2's failure means for the campaign

The activity vector's core term is `total_insns`. P2 says that term does not
track `vdd_arm`: a stalling memory workload burned 1.6x the core power of a
workload retiring more instructions. Any AF built on instruction count alone
will mis-rank these two workloads. The vector already carries `data_misses`
and `dram_transactions_est`; the core model likely needs them, not just insns.

---

## P4 — UNBLOCKED. Root cause found on silicon.

Ran `bench-wfi-diag` on the EVK (same SoC as the FRDM, and its console is
reliable where the FRDM's bridge kept serving stale buffer). Provenance
**MEASURED** on IMX95LPD5EVK-19, 2026-09-10.

| register | QEMU (passing) | **silicon** |
|---|---|---|
| `IGROUPR0` | `0x04000000` | **`0x00000000`** |
| `ISENABLER0` | `0x04000000` | `0x04000000` |
| `ICC_IGRPEN1_EL1` | 1 | 1 |
| `ICC_SRE_EL2` | 0xf | 0xf |
| `CNTFRQ_EL0` | 24 MHz | 24 MHz |
| `CNTHP_CTL` ISTATUS | SET | **SET** |
| WFI | **WOKE** | **HANGS** |

### The mechanism

Everything works except one write. The timer **fires** (`ISTATUS` set). The
interrupt is **enabled** (`ISENABLER0` bit 26). The CPU interface has **Group 1
enabled**. But `IGROUPR0` reads back **zero**: our non-secure write to move
PPI 26 into Group 1 was **silently discarded**, so the interrupt stays in
**Group 0** — and a CPU interface with only Group 1 enabled never receives it.
WFI sleeps forever.

**ATF owns PPI 26 as a Secure Group 0 interrupt on real firmware.** QEMU accepted
the identical write because it models no secure GIC state and runs no ATF, so
the sequence passed there and failed here.

⭐ This is row 1 of the decision table written into the runbook BEFORE the run:
*"`IGROUPR0` reads back 0 → ATF owns PPI 26 as Secure Group 0; our NS write is
discarded → switch to PSCI `CPU_SUSPEND`, or use CNTP/PPI 30."* Fixing the
interpretation in advance is what made a one-shot run conclusive instead of a
starting point for rationalisation.

### What P4 needs to actually run

1. **PSCI `CPU_SUSPEND`** — the sanctioned idle path on real firmware, and what
   Linux cpuidle uses. ATF then owns the GIC/timer plumbing we are failing to do
   by hand from EL2. Also the more faithful experiment: a bare WFI is a shallow
   halt, while `CPU_SUSPEND` drives real power-domain transitions through the SM
   — which is the thing P4 is trying to measure.
2. Or the **EL1 physical timer (CNTP, PPI 30)** — Linux drives it successfully on
   this board, so it is demonstrably available to non-secure software.

⚠️ Not a QEMU bug so much as a fidelity gap: QEMU's GICv3 has no secure/non-secure
ownership model for PPIs, so it will accept any group assignment. **A guest
sequence validated only under QEMU can be wrong about interrupt ownership on
silicon** — which is exactly the class of thing this emulator exists to catch,
and did not.
