# Measuring real i.MX95 per-rail power (the P1 calibration ground truth)

wattson's activity vectors are only trustworthy once regressed against **measured
silicon power**. The good news: the i.MX95 EVK / FRDM boards already ship the
instrumentation, and it's read from the *host* (independent of the workload).

## Hardware: PAC1934 monitors

- The board carries **Microchip PAC1934** power/energy monitor ICs (labelled
  **M1..M8**), each measuring up to 4 rails via shunt resistors — **27 power rails**
  total on the i.MX95 EVK.
- Critically, the PAC1934s sit on the **FTDI I2C bus**, *not* the SoC's I2C. So
  power is read over the debug channel from the host PC — it keeps working in SoC
  sleep/low-power states and does **not** perturb the workload under measurement.
- Sampling: ~**20 ms/sample (50 S/s)** for all 27 rails at once, or **4 ms/sample
  (250 S/s)** for the 4 rails on a single PAC1934.

## Software: BCU (Board Control Utility)

Open source, NXP: <https://github.com/nxp-imx/bcu> (Linux + Windows; Snap or
prebuilt binaries). Command-line, host-side. It reads the PAC1934s and reports
per-rail voltage / current / **power (mW)**, and holds the per-board rail↔domain
mapping in `board.c`.

Typical flow (confirm exact syntax against the BCU README / `bcu -h`):

```sh
bcu lsftdi                       # find the board's FTDI adapter
bcu monitor  -board=imx95evk19   # live per-rail V / I / mW
bcu monitor  -board=imx95evk19 -rpath=... -hz=50   # log to file for a run
```

Wrap a workload: start `bcu monitor` logging → run the workload to completion →
stop → integrate power over the window per rail.

## Rails that matter for wattson (i.MX95 EVK, from bcu `board.c`)

| wattson activity | i.MX95 rail(s) | group |
|---|---|---|
| core insns / core duty cycle | **`vdd_arm`** (A55 cores), `vdd_soc` (logic) | GROUP_SOC |
| DRAM transactions (cache misses) | **`lpd5_vdd1`, `lpd5_vdd2`, `lpd5_vddq`** (LPDDR5); `vdd_ddr`, `vdd2_ddr`, `vddq_ddr` | GROUP_DRAM |
| SoC / un-broken-out accelerators | `vdd_soc` | GROUP_SOC |

Other rails present (`nvcc_3v3`, `vdd_usb_3v3`, `vdd_ana_0v8/1v8`, `nvcc_enet*`,
`nvcc_wakeup`, `nvcc_bbsm_1v8`, `nvcc_sd*`) are I/O / analog / always-on and are
**not** wattson calibration targets (not activity-driven, or not QEMU-visible).

> ⚠️ On the EVK there is **no dedicated NPU/GPU/VPU rail** — accelerator power
> folds into `vdd_soc`, so accelerator-AF calibration is coarse (shared rail). A
> more fully instrumented board that breaks these out would sharpen P2 for the
> accelerators. (Kyle is sourcing one, ~2 weeks out.)

## Board caveat

The rail list above is confirmed for the **i.MX95 EVK** boards in BCU
(`imx95evk19`, `imx95evk15`). The **FRDM-IMX95** is a lower-cost variant — verify
its rail set with `bcu -board=<frdm-name> lsftdi/monitor` on the actual board
before trusting the mapping. If the FRDM's instrumentation is thinner, the
purpose-built instrumented board covers P1.

## References

- NXP AN14449, *i.MX 95 Power Consumption Measurement* (rail↔domain mapping,
  measurement procedure).
- BCU: <https://github.com/nxp-imx/bcu> (`board.c` = per-board rail defs).
- NXP AN13917, *i.MX 93 Power Consumption Measurement* (same method, sibling SoC).
