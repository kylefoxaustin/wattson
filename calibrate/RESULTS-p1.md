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
