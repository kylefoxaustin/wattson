# Measuring real i.MX95 per-rail power (the P1 calibration ground truth)

wattson activity vectors become trustworthy only once regressed against **measured
silicon power**. Authoritative source: **NXP AN14449, *i.MX 95 Power Consumption
Measurement*** (Rev 1.0, Feb 2026). This page distills it for wattson.

## Which board

- **Calibration board = IMX95LPD5EVK-19** (i.MX 95 19x19 LPDDR5 EVK; main board
  87753 Rev B + CPU board 87754 Rev B). It carries the on-board measurement
  circuitry: PMICs **PF56 + PF09 + PF53** with per-rail shunts.
- **FRDM-IMX95-PRO has NO power-measurement circuits** — it cannot self-measure.
  Use the EVK for all P1 calibration. (A more fully instrumented board, if it
  breaks out NPU/GPU/VPU rails, would sharpen accelerator AF — see below.)

## Hardware path

On-board shunts → PMIC/monitor circuitry → read from the host over the EVK's
debug USB. No SoC involvement, so it doesn't perturb the workload. (This is the
same idea as the PAC1934/FTDI-I2C path on other i.MX EVKs.)

## Software: BCU (Board Control Utility)

Open source, NXP: <https://github.com/nxp-imx/bcu> (AN14449 used **v1.1.128**).
Procedure (AN14449 §3.3):

```sh
# Type-C cable: host PC  <->  J31 USB on the IMX95LPD5EVK-19 base board
bcu monitor -board=imx95evk19       # live per-rail V / I / mW
# once the use case is running:
#   press "3"  -> reset the accumulators
#   press "4"  -> switch precision (mA / auto / uA)
#   wait ~1 minute, record
```

BCU reports per-rail power in **mW** and holds the rail↔domain map.

## Authoritative rail ↔ domain map (AN14449 Table 3)

| wattson activity | power group | rails (BCU) | domain |
|---|---|---|---|
| **DRAM transactions** (cache misses) | `GROUP_DRAM` | `lpd5_vdd1`, `lpd5_vdd2`, `lpd5_vddq` | LPDDR5 VDD1/VDD2/VDDQ |
| **core insns / core duty** | `GROUP_SOC_FULL` | **`vdd_arm`** | i.MX95 A55 cores |
| SoC logic + accelerators | `GROUP_SOC_FULL` | **`vdd_soc`** | i.MX95 SOC power |
| DRAM interface | `GROUP_SOC_FULL` | `vdd_ddr`, `vdd2_ddr`, `vddq_ddr` | DRAM interface VDD/VDD2/VDDQ |

Other `GROUP_SOC_FULL` rails (`nvcc_3v3`, `nvcc_bbsm_1v8`, `nvcc_enet_ccm`,
`nvcc_sdio2`, `nvcc_wakeup`, `vdd_ana_0v8`, `vdd_ana_1v8`, `vdd_usb_3v3`) are
I/O / analog / always-on — **not** wattson targets.

> ⚠️ **`vddq_ddr` and `lpd5_vddq` are jumper-shorted (SJ3–SJ9 on the SOM back)**
> in this EVK version, so BCU reports them as ~equal; **sum them** for total VDDQ,
> or open SJ3–SJ9 to separate.
>
> ⚠️ **No dedicated NPU/GPU/VPU rail.** Per AN14449 Figure 1, NPUMIX / GPUMIX /
> VPUMIX all sit in the **VDD_SOC** domain — accelerator power folds into
> `vdd_soc`, so accelerator-AF calibration is coarse (shared rail).

## VDD_ARM operating points (for the energy model)

`vdd_arm` is a dedicated rail with DVFS OPPs (AN14449 Table 1) — the power team's
energy coefficients scale with V²·f, so record the OPP a workload ran at:

| mode | VDD_ARM typ |
|---|---|
| super-overdrive | 1.00 V |
| overdrive | 0.90 V |
| nominal | 0.85 V |
| low-drive | 0.80 V |
| suspend | 0 V (core rail gated off) |

## The calibration workload suite

AN14449 ships **AN14449SW** with the exact use-case binaries NXP measured —
**CoreMark, Dhrystone, memcpy, memset, stream**, plus audio/video/GLMark. These
are the P1 suite: run them on the EVK under BCU *and* in wattson, then regress.
wattson's shipped workloads already mirror the endpoints:
`bench-alu` ↔ CoreMark/Dhrystone (compute-bound), `bench-mem` ↔ Stream/memcpy
(memory-bound). See `reference-an14449.md` for NXP's measured numbers (SOURCED),
which serve as an independent sanity anchor for our own EVK measurements.

## Reference software build (matches AN14449)

Linux **LF6.12.49_2.2.0**, Yocto (`DISTRO=fsl-imx-xwayland`,
`MACHINE=imx95-19x19-lpddr5-evk`), `bitbake imx-image-full`, booted from eMMC.

## References

- NXP **AN14449** *i.MX 95 Power Consumption Measurement* (Rev 1.0) + **AN14449SW**.
- BCU: <https://github.com/nxp-imx/bcu>.
- i.MX 95 Data Sheet **IMX95CEC** (actual electrical values).
