# wattson

**Dead-reckoning silicon power from QEMU activity.**

Watt (power) + Watson (deduce the unknown from the evidence). *Dead reckoning* is
estimating your position from known speed and heading when you have no fix on
land — which is exactly what this does: estimate a chip's power from activity
proxies when the silicon doesn't exist yet.

wattson turns a functional QEMU run into an **activity vector** — per-core
instruction work and cache-derived DRAM traffic — that a power team can multiply
by their own per-event energy model to get a power estimate. It does **not**
output watts, and it never will. That is the point.

---

## The one idea that makes this work

> **QEMU supplies the activity (α). The power engineers supply the energy-per-event.**

QEMU is a *functional* emulator: it knows *what* work a workload does
(instructions retired, memory transactions, which blocks are busy and for how
long) but nothing about *how* the silicon does it (no gates, no capacitance, no
voltage, no clock/power-gating residency, no leakage). So wattson never tries to
compute power. It produces the **activity** half of `P ≈ Σ (energy_per_event ×
event_count)`; the power team owns the **energy** half — the same coefficients
behind "if your activity factor is 5%, core power is XYZ."

That division of labour is what makes the estimate defensible, and what lets it
extend to a chip that only exists in QEMU:

| Phase | Who supplies activity | Who supplies energy | Output |
|---|---|---|---|
| **P0 — activity** *(built)* | wattson (QEMU plugins) | — | activity vectors |
| **P1 — calibrate** *(needs instrumented board)* | wattson, on i.MX95 | measured per-rail silicon power | fitted energy-per-event coefficients + error band |
| **P2 — Zebra** *(future chip)* | wattson, on the QEMU model of an unbuilt chip | the power team's Zebra energy model | full-chip power estimate for QEMU-visible blocks |

**Golden rule for P2:** reuse the *activity-extraction methodology* on the new
chip, **never** the *energy coefficients* fitted on i.MX95 — different node/uarch.
Borrow the α, not the joules.

---

## What it measures (and what it can't)

**Measures well** — QEMU-visible, activity-driven blocks:
- **CPU cores** — instructions retired per core, and active-vs-halted duty cycle.
- **DRAM** — cache **misses** from a functional cache model = DRAM-transaction
  proxy (× line size = bytes). This is the key to a meaningful memory AF.
- **Accelerators QEMU models** (VPU/NPU/DPU) — block-active duty cycle, even
  though the compute itself is faked. Duty cycle is exactly what you can't
  cycle-model but *can* calibrate.

**Cannot measure** — own these on the energy side, not here:
- Leakage (not activity-driven → invisible to any functional method).
- Microarchitecture (speculation, pipeline, real DVFS/frequency residency).
- Analog, PLLs, PHYs, always-on domains.

**Honest accuracy:** block-level, well-calibrated, cache model included — expect
roughly **±20%**. Useful for pre-silicon architectural power exploration and
"which use-case is the hog"; **not** for power signoff.

---

## What's built today (P0)

A working activity-extraction harness on top of the `qemu-imx95` machine, using
stock QEMU TCG plugins (`libinsn` + `libcache`) — no QEMU core changes.

```
wattson/
  harness/run-activity.sh      # run a workload under the plugins -> activity vector (JSON)
  harness/parse_activity.py    # parse plugin output -> schema
  schema/activity-vector.schema.json
  workloads/                   # bounded bare-metal workloads (PSCI-off so plugins flush)
    bench-alu.S                #   compute-bound (register churn)
    bench-mem.S                #   memory-bound (256 MiB stream)
  samples/                     # real activity vectors from the two workloads
  calibrate/                   # P1: regress activity vs measured silicon power (stub + how-to)
  docs/methodology.md          # the full method + caveats + Zebra extrapolation
  docs/roadmap.md              # P0/P1/P2
```

### Quickstart

```sh
# needs a qemu-imx95 built with -Dplugins=true
bash harness/run-activity.sh workloads/bench-mem.bin bench-mem "256MiB stream" > my.activity.json
```

### The two shipped samples discriminate cleanly (measured on this host)

| workload | insns | cache data misses (= DRAM txns) | DRAM bytes est |
|---|---:|---:|---:|
| **bench-alu** (compute) | 2.68 B | 3 | ~0 |
| **bench-mem** (memory) | 940 M | 33.5 M | 2.1 GB |

`bench-mem`'s 12.5% miss rate is exactly 8-byte-access / 64-byte-line, and
33.5M misses × 64B = 2.1 GB — matching the 256 MiB × 4 passes × 2 the workload
actually streams. The cache model is behaving physically.

---

## Next: calibration (P1)

The calibration board is the **IMX95LPD5EVK-19** (the FRDM-IMX95-PRO has no
power-measurement circuits). It carries on-board per-rail monitors read host-side
by NXP's open-source **BCU** tool — rails including **`vdd_arm`** (A55 cores) and
the **`lpd5_*`** LPDDR5 group, a near-perfect match for wattson's CPU and DRAM
activity. NXP's app note **AN14449** is the authoritative rail map + procedure, and
**AN14449SW** ships the exact calibration workloads (CoreMark, Dhrystone, Stream,
memcpy/memset) — which our `bench-alu`/`bench-mem` already mirror. See
[`calibrate/power-measurement.md`](calibrate/power-measurement.md) and the SOURCED
measured anchor in [`calibrate/reference-an14449.md`](calibrate/reference-an14449.md).

---

*Provenance (Law 1): every wattson number is **DERIVED** from a functional
emulator. Silicon power is **MEASURED**. The fitted coefficients are the labelled
bridge between them. A DERIVED activity factor is never reported as a measured
silicon one.*
