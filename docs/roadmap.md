# wattson roadmap

## P0 — activity extraction · **DONE**
- [x] TCG-plugin harness on `qemu-imx95` (`libinsn` + `libcache`), no core changes.
- [x] Bounded bare-metal workloads that PSCI-off so plugins flush (`bench-alu`,
      `bench-mem`).
- [x] `parse_activity.py` → versioned activity-vector JSON (`schema/`).
- [x] Real sample vectors that discriminate compute vs memory (`samples/`).

## P1 — calibrate on the IMX95LPD5EVK-19 · **blocked on the EVK (~2 weeks)**
- [ ] Per-rail silicon power via BCU on the EVK (`calibrate/power-measurement.md`);
      FRDM-PRO has no power circuits, so calibration uses the EVK.
- [ ] Reuse the **AN14449SW** suite (CoreMark / Dhrystone / Stream / memcpy /
      memset + a/v + GLMark) so results cross-check against NXP's measured Table 4
      (`calibrate/reference-an14449.md`); add idle + a mixed real app.
- [ ] Instruction-class breakdown (add the `howvec` classifier plugin) so ALU vs
      load/store vs FP/NEON get distinct energy coefficients.
- [ ] Core duty-cycle (active vs WFI) via an `-icount` timeline.
- [ ] Accelerator active-fraction harvested from the device models (Neutron FSM,
      DPU frame timing) for duty-cycle AF.
- [ ] Regress activity → measured per-domain power; report held-out error band
      (`calibrate/calibrate.py`).

## P2 — extrapolate to an unbuilt chip ("Zebra")
- [ ] Run use-cases on the QEMU model of the future chip → activity vectors.
- [ ] Power team applies **Zebra's** energy-per-event to wattson's activity for the
      QEMU-visible blocks (cores, DRAM, modeled accelerators).
- [ ] Deliver a per-use-case, per-block power estimate with an explicit error band
      and an explicit list of what's out of scope (leakage, analog, PLL/PHY).
- [ ] **Rule:** transfer the methodology, never the i.MX95 coefficients.

## Nice-to-haves
- [ ] Address-stream → bank/row locality for a better DRAM energy model.
- [ ] Peripheral register-access / DMA-descriptor counts as extra activity signals.
- [ ] A single `wattson run <suite>` driver that produces a full activity report.
