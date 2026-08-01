# wattson methodology

## The problem

Power teams estimate a block's dynamic power as, roughly,

```
P_dynamic ≈ Σ_events ( energy_per_event × event_count )      (+ leakage, handled separately)
```

They have the **energy_per_event** side (from synthesis, SPICE, prior silicon,
and their process/uarch models) — it's what lets them say *"if the activity factor
is 5%, the core is XYZ mW."* What they often lack early — especially for a chip
that doesn't exist yet — is a credible **event_count / activity factor** for a
*real* software use-case.

wattson produces that activity side from a functional QEMU run.

## Why a functional emulator is allowed to do this

QEMU is not cycle-accurate and never will be. But dynamic power is driven by
*how much architectural work happens*, and a lot of that work **is** visible
functionally:

- instructions retired (and, with a classifier plugin, by class),
- memory transactions — and, with a functional cache model, the **misses** that
  actually reach DRAM,
- which accelerator/peripheral blocks are invoked, and for how long.

What QEMU cannot see is *microarchitecture* (speculation, pipeline, cache
replacement subtleties, DVFS residency) and *leakage*. So wattson is a
**coarse, block-level, relative** activity estimator, calibrated against real
silicon — not a gate-level switching-activity tool.

## The division of labour (the load-bearing idea)

> **wattson = activity (α). Power team = energy-per-event. Never cross the streams.**

wattson must never emit watts. It emits counts and duty cycles. The power team
multiplies by their coefficients. This keeps every number honest about what it is
and is what lets the method extend to an unbuilt chip.

## What wattson extracts (the activity vector)

Per run, per block (see `schema/activity-vector.schema.json`):

- **cores**: instructions per active core, active-core count. (Duty cycle —
  active vs WFI-halted — is a P1 addition via an `-icount` timeline; QEMU already
  knows halted time precisely.)
- **memory**: data accesses, **data misses** (= DRAM read/write transactions),
  miss rate, instruction fetches/misses, and derived `dram_transactions_est` and
  `dram_bytes_est` (misses × cache line).
- **accelerators** (P1+): per-modeled-block active-cycle fraction, harvested from
  the device models that already track job start→done (e.g. the Neutron FSM, DPU
  frame timing).

## Calibration (P1)

1. On real i.MX95, run a **workload suite spanning the activity space** — idle,
   compute-bound (`bench-alu`), memory-bound (`bench-mem`), a mixed real app, an
   accelerator run.
2. Measure **per-rail silicon power** for each (see
   `calibrate/power-measurement.md` — PAC1934 + BCU).
3. Extract the wattson activity vector for each of the same runs.
4. **Regress**: fit `energy_per_event` so `Σ(energy × activity)` matches measured
   per-domain power. Map activity → rail:
   - core insns / duty → `vdd_arm` (+ `vdd_soc`)
   - `dram_transactions_est` → the `lpd5_*` / DDR group
5. **Validate** on held-out workloads; report the error band.

Expected block-level accuracy with the cache model included: **≈ ±20%**.

## Extrapolation to an unbuilt chip (P2, "Zebra")

For a chip that only exists as a QEMU model:

- wattson supplies the **activity** for use-case N on the Zebra QEMU model.
- The power team supplies **Zebra's** energy-per-event (their pre-silicon model).
- Multiply, for the **QEMU-visible blocks only** (cores, DRAM, modeled
  accelerators). Analog / PLL / PHY / leakage stay entirely on the power-team
  side.

**The rule that keeps this honest:** transfer the *methodology* (how activity is
extracted), never the i.MX95-fitted *coefficients*. A different node/uarch has
different joules-per-event; only the power team's Zebra model may supply those.

## Known limitations (state these every time)

- **No leakage** — invisible to any functional method.
- **No microarchitecture / DVFS** — coarse and relative, not gate-level.
- **Cache is the dominant error source** for the CPU↔DRAM split; wattson uses a
  functional cache model to mitigate, but replacement/prefetch differences from
  real silicon remain. Calibration absorbs the systematic part.
- **Live control registers are not reset/activity oracles** — a general fleet
  lesson: only read-only counters and modeled events are valid inputs.
- **QEMU-visible blocks only.** If QEMU doesn't touch it, wattson can't factor it.
