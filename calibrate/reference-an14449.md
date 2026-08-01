# SOURCED reference: NXP AN14449 measured power (validation anchor)

These are **NXP's own measured** i.MX 95 power numbers from AN14449 Table 4, on the
**IMX95LPD5EVK-19** (Linux LF6.12.49_2.2.0). They are **SOURCED** (measured by NXP,
not by us) — per Law 1 they may **not** be compared head-to-head against a wattson
DERIVED number as if equal. Their role here is a **sanity anchor**: when we take
our own BCU measurements on Kyle's EVK, they should land in this ballpark, and the
ordering (memory-bound > compute-bound > idle) is a shape wattson must reproduce.

## AN14449 Table 4 — total power, sum of GROUP_SOC_FULL rails (mW)

| category | use case | power (mW) |
|---|---|---:|
| core | CA55 CoreMark | 2390.34 |
| core | CA55 + CM7 CoreMark | 2468.57 |
| core | Dhrystone | 2810.06 |
| memory | Memcpy | 2462.33 |
| memory | Memset | 2677.53 |
| memory | **Stream** | **3825.18** |
| a/v | Audio Playback | 1384.48 |
| a/v | Video playback local 1080P | 1888.64 |
| a/v | Video playback local 4K | 2059.34 |
| a/v | Video playback streaming 1080P | 1929.38 |
| a/v | Video playback streaming 4K | 2094.23 |
| gpu | GLMark | 2625.42 |

Notes:
- These are the **GROUP_SOC_FULL sum** (all SoC-side rails incl. `vdd_arm` +
  `vdd_soc`), not a per-rail split. AN14449 has per-rail detail deeper in the doc;
  our own BCU runs will give us the per-rail split we regress against.
- The measured shape wattson must reproduce: **Stream (memory-bound) is the
  hog (3825)** — well above the compute cores (CoreMark 2390, Dhrystone 2810).
  This is exactly why the cache-miss DRAM proxy is the load-bearing activity
  feature.

## How this feeds calibration

1. Build **AN14449SW** (CoreMark, Dhrystone, memcpy, memset, stream) — the same
   binaries — for the EVK.
2. Measure each with BCU (per-rail mW) on our EVK → our own **MEASURED** dataset.
3. Extract the wattson activity vector for each.
4. Regress activity → measured per-rail power (`calibrate.py`).
5. Cross-check totals against the table above; investigate any large divergence.
