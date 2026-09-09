# P1 pre-registration — predictions frozen BEFORE the first rail is read

**Status: FROZEN on commit. Board (IMX95LPD5EVK-19) arrives 2026-09-09.**

Everything below is written while we have **zero** measured rail data. That is the
point. A prediction written after seeing the numbers is not a prediction, and the
fitting is invisible to the person doing it — we would tune `AF_idle`/`AF_max`
until the line went through the dots and report the fit as a confirmation.

The rule for this campaign: **no edit to any predicted value in this file after
the first BCU reading.** Results go in `calibrate/RESULTS-p1.md` next to the
prediction, whichever way they fall. If a prediction is wrong, it stays wrong on
the page.

---

## 0. Two problems found while writing this, both cheaper to fix now

### 0.1 ⚠️ THE ACTIVITY VECTOR HAS NO TIME BASE — SO IT CANNOT PREDICT POWER

`samples/*.activity.json` records **totals**: instructions retired, DRAM
transactions, bytes. Power is a **rate** (mW = mJ/s). A total cannot predict a
rate without a duration, and there is no duration field in
`schema/activity-vector.schema.json`.

So a prediction of "bench-mem draws N mW" is not derivable from anything we hold,
and any such number would be smuggled in from intuition.

**Resolution — compare ENERGY, not power.** BCU accumulates (AN14449 §3.3: key
`3` resets the accumulators), so the instrument's native output already matches
the vector's native output: a total over a window. Energy per workload run is the
comparable quantity, and it is the one the activity vector can actually speak
about.

**Action before measuring:** add `wall_ns` (host-measured run duration) and
`guest_cycles` to the activity vector so a rate is available where a rate is
wanted. Until then, **every prediction here is in mJ or in dimensionless
ratios**, never mW.

### 0.2 ⚠️ NO IDLE BASELINE EXISTS, AND THE MODEL IS DEFINED IN TERMS OF ONE

The bridge is `AF_app = AF_idle + (AF_max − AF_idle) × U`. We have never measured
`AF_idle` on this or any i.MX 95 board. Two of the three terms are unmeasured.

**Action:** the FIRST measurement of the campaign is the idle floor, per rail,
board booted and quiescent, no workload. Nothing else is interpretable without
it — a DRAM rail reading is meaningless until we know what that rail draws when
no transaction is issued.

### 0.3 ⚠️ NEW: ONE BINARY CANNOT SERVE BOTH THE QEMU RUN AND THE BCU WINDOW

Found while building `bench-duty`, and it changes day-one procedure.

BCU wants roughly a **60 s** accumulation window (AN14449 §3.3). A workload sized
to run ~60 s on silicon is enormous under TCG-with-plugins; a workload sized to
finish in QEMU is over in well under a second on an A55 at ~1.8 GHz. The default
`bench-duty` (256 windows x 1M iterations, ~1.3e9 instructions) is roughly **0.7 s
of silicon** — two orders of magnitude short of a usable BCU window.

**Resolution — two builds of the same source, and scale per window.** The active
burst is identical in every window by construction, so activity per window is a
constant:

    activity_silicon_run  =  activity_per_window x WINDOWS_silicon

Collect the QEMU activity vector at the QEMU size, divide by its `WINDOWS`, and
multiply by the silicon build's `WINDOWS`.

⚠️ **That multiplication is DERIVED and must be labelled.** It assumes per-window
activity is exactly constant — true for this workload by design, false in general,
and *not* to be reused for `bench-alu`/`bench-mem`, which have no window structure.
Build both from the same `bench-duty.S` with `--defsym WINDOWS_OV=`, and record
both `WINDOWS` values next to the vector.

### 0.4 `bench-duty` NOW EXISTS AND IS VERIFIED IN QEMU (P4 prep: DONE)

Built at U ∈ {0.25, 0.50, 0.75, 1.00} from one source. Idle is a genuine **WFI
halt woken by the EL2 hypervisor timer**, not a spin loop — a polling loop retires
instructions throughout, which would hold the core at full duty while looking like
a duty sweep, and would confirm P4's linearity at every U by construction.

Verified in QEMU (smoke size, 4 windows x 4096 iters):

| duty | insns retired | wall |
|---:|---:|---:|
| 100 | 81,978 | 0.07 s |
| 50 | 82,014 | 0.09 s |
| 25 | 82,014 | 0.12 s |

Instruction counts identical to within the 36-instruction timer-arm sequence that
U=1.00 skips; wall time rises monotonically as duty falls. Active work constant,
halted time the only variable — which is the property P4 needs.

**Three bugs were found by running it, none by reading it**, and they are recorded
because each would have cost hours with the board on the desk:
1. redistributor base was `0x48040000` (the **ITS**); the real GICR is `0x48060000`
2. a hand-built `S3_6_C12_C12_5` meant to be `ICC_SRE_EL1` is **`ICC_SRE_EL3`** —
   undefined at EL2, where this machine actually starts a `-kernel` image. The
   disassembly printed `icc_sre_el3` in plain text the whole time. Symbolic
   register names now, so the assembler checks intent rather than encoding
   arithmetic faithfully.
3. PPIs reset to **Group 0** while only Group 1 was enabled on the CPU interface.
   An enabled, pending, correctly-prioritised Group 0 interrupt is never
   delivered, and the symptom is silent: no exception, no guest error, and
   `-d int` shows nothing because there is nothing to show. WFI slept forever.

### 0.5 ⭐ VALIDATED AGAINST REAL i.MX 95 SILICON (FRDM-IMX95-PRO, 2026-09-08)

The FRDM has no power circuits and cannot do P1 — but it is the same SoC, so it
answers the *constants* question without waiting for the EVK. Read from the
running board (`ssh imx95`), provenance **MEASURED on FRDM-IMX95-PRO silicon**:

| constant | silicon says | our code had |
|---|---|---|
| GICD base / size | `0x48000000` / 64 KiB | ✅ same |
| **GICR base / size** | **`0x48060000` / 768 KiB** | ✅ same *(after the ITS-address fix)* |
| timer PPIs | sec-phys 29, **EL1-phys 30**, virt 27, **hyp 26** | ✅ hyp INTID 26 |
| **CNTFRQ_EL0** | **24 MHz** | *(was unstated)* |
| 1M iterations of the burst loop, A55 | **85,028 ticks = 3.543 ms** | *(was unstated)* |

⚠️ **This confirms ADDRESSES AND FREQUENCIES read from Linux. It does NOT confirm
the bare-metal GIC/timer/WFI sequence runs on silicon** — that needs the images
actually booted on hardware, which is still §1's open question.

### 0.6 🔴 THE SILICON MEASUREMENT KILLED THE ORIGINAL DUTY DESIGN

Worth the trip on its own. With the active phase bounded by an ITERATION COUNT
and idle bounded by TIMER TICKS, the real duty cycle on silicon came out:

    nominal DUTY   25     50     75    100
    ACTUAL U      0.221  0.460  0.718  1.000

Not a calibration offset — **U was a function of execution speed.** The active
phase took 3.543 ms on an A55; under TCG the same iterations take far longer in
wall time while idle still costs 4.167 ms, so every QEMU variant would have sat
near U = 1.0. **The same binary would have had a different duty cycle in QEMU
than on silicon** — fatal for a sweep whose entire purpose is correlating
QEMU-side activity with silicon-side power, and invisible from either side alone.

It would also have biased P4 specifically: fitting against nominal U while the
true U was 0.221/0.460/0.718 puts a systematic error on the x-axis, and the
intercept is the term P4 uses to tell a prediction from a fit.

**Fixed by bounding BOTH phases in generic-timer ticks**, so

    U = ACTIVE_TICKS / (ACTIVE_TICKS + IDLE_TICKS)

exactly, at any execution speed. Re-verified in QEMU at 8 windows: measured idle
over the U=1.0 baseline was +40 ms and +100 ms for U=0.5 and U=0.25, against
33.3 ms and 100 ms predicted. Instruction count per window now varies with
platform — which is fine, because instructions are measured, not assumed.

### 0.7 🔴 RUN ON REAL SILICON: THE BARE-METAL IMAGES BOOT, BUT **WFI NEVER WAKES**

Run on the FRDM-IMX95-PRO (2026-09-08), which answers §1's open question and
overturns §0.4's QEMU-only verification. Loaded from U-Boot:
`fatload mmc 1:1 0x90000000 bench-duty50.bin` → `dcache off` → `go`.

| build | QEMU | **silicon** |
|---|---|---|
| `bench-duty100` (no WFI in the loop) | START + DONE | **START + DONE** ✅ |
| `bench-duty50` (WFI each window) | START + DONE | **START, then HANGS** 🔴 |

DUTY=50 should finish in ~2.1 s (256 windows x 8.33 ms); it was still silent after
55 s. Both builds run the identical GIC bring-up, and the only difference between
them is the WFI, so:

- ✅ **bare-metal images DO run on real i.MX 95 silicon** — §1's biggest schedule
  risk is retired
- ✅ **the GICv3 bring-up does not hang on hardware**
- 🔴 **the timer interrupt does not wake WFI on silicon**, though it does in QEMU

⚠️ **THEREFORE P4 CANNOT BE RUN ON THE EVK AS THINGS STAND.** The duty sweep needs
the core to genuinely halt and resume; on silicon it halts and stays there. Every
U < 1.0 point is unobtainable until this is fixed, which leaves P1/P2/P3 runnable
tomorrow and P4 blocked.

**What this says about the method, and it is the whole reason the FRDM trip was
worth it:** the sequence was verified in QEMU at four duty points, with matching
idle-time deltas, and it was still wrong on hardware. QEMU's GIC and timer models
accept a bring-up that real GIC-600 silicon does not. A model can only refute a
guest's assumptions where the model is stricter than the hardware — and here it
was more permissive, so the test passed and the silicon disagreed.

Candidates to chase (untested): the EL2 hypervisor timer PPI may be claimed or
routed differently under ATF on real firmware; the GIC-600 may need
redistributor/affinity-routing state QEMU tolerates being incomplete; or the
running core's redistributor frame may not be RD0 after U-Boot `go`.

⚠️ **Do NOT "fix" this by replacing WFI with a spin loop.** That makes the sweep
run and destroys what it measures — a spinning core is at full duty, and P4 would
then confirm its own linearity at every U by construction.

---

## 1. What is fixed in advance

| item | value |
|---|---|
| board | IMX95LPD5EVK-19 (base 87753 Rev B + CPU 87754 Rev B) |
| instrument | BCU v1.1.128, `bcu monitor -board=imx95evk19`, USB-C to J31 |
| window | accumulators reset (key `3`), workload runs to completion, read totals |
| repeats | n = 5 per workload; report median and full spread, not mean alone |
| rails read | `lpd5_vdd1`, `lpd5_vdd2`, `lpd5_vddq`, `vdd_arm`, `vdd_soc`, `vdd_ddr`, `vdd2_ddr`, `vddq_ddr` |
| workloads | idle, `bench-alu`, `bench-mem` (+ duty sweep, §4) |

**Known instrument quirks, recorded now so they are not discovered as anomalies:**
- `vddq_ddr` and `lpd5_vddq` are **jumper-shorted (SJ3–SJ9)**. They will read
  ~equal. That is the board, not a fault. Sum them, or open the jumpers.
- **No dedicated NPU/GPU/VPU rail** — NPUMIX/GPUMIX/VPUMIX all sit in `vdd_soc`
  (AN14449 Fig 1). Accelerator AF is therefore coarse by construction, and no
  amount of care in this campaign fixes it.

**⚠️ OPEN PRACTICAL QUESTION, not yet resolved:** `bench-alu`/`bench-mem` are
bare-metal flat images linked at `0x80000000` ending in PSCI `SYSTEM_OFF`, built
for `qemu-imx95`. Whether they boot as-is on the real EVK (and whether
`SYSTEM_OFF` behaves) has never been tried. If they do not, the comparison needs
a Linux-hosted equivalent pair — and then the QEMU-side vectors must be
re-collected under Linux too, or we are comparing two different workloads. This
is the single biggest schedule risk for day one.

---

## 2. The measured inputs the predictions come from

QEMU activity, already collected — provenance **DERIVED (TCG functional counters,
NOT silicon)**:

| workload | insns retired | DRAM bytes est | d-miss rate |
|---|---:|---:|---:|
| `bench-alu` | 2,684,354,571 | 320 | 0.60 (of 5 accesses) |
| `bench-mem` | 939,524,132 | 2,147,484,032 | 0.125 |

Ratios that matter: `bench-alu` retires **2.86×** the instructions;
`bench-mem` moves **6.7 million×** the DRAM bytes.

Reference anchors — provenance **SOURCED (AN14449 Table 4, GROUP_SOC_FULL sums,
mW)**. These are *not* our board's numbers and are used only to set expected
magnitude:

| use case | mW |
|---|---:|
| Dhrystone | 2810.06 |
| CA55 CoreMark | 2390.34 |
| Memcpy | 2462.33 |
| Memset | 2677.53 |
| **Stream** | **3825.18** |

Memory-bound / core-bound in the vendor's own data: **3825.18 / 2810.06 = 1.36×**.

---

## 3. The predictions

Each is stated so that a specific outcome would **refute** it.

### P1 — the DRAM rails discriminate the two workloads
`bench-alu` issues ~0 DRAM traffic (320 B total).

- **P1a:** `GROUP_DRAM` energy for `bench-alu` sits within **±10%** of the idle
  floor over the same window.
- **P1b:** `GROUP_DRAM` energy for `bench-mem`, **idle floor subtracted**, is at
  least **10×** that of `bench-alu` with the same subtraction.
- **Refuted if:** `bench-alu` shows DRAM energy well above idle (means our
  "~0 DRAM" claim is wrong, or the bare-metal image touches memory we did not
  model), or the ratio is < 3× (means the DRAM rail is dominated by something
  other than transactions — refresh, or the interface rails idling hot).

### P2 — `vdd_arm` tracks core activity, and `bench-alu` is the harder core load
Both run one A55 at full duty; `bench-alu` retires 2.86× the instructions and
never stalls on memory.

- **P2:** `vdd_arm` **average power** over the run is **higher for `bench-alu`**,
  with ratio `bench-alu / bench-mem` in **1.05 – 1.60**.
- **Refuted if:** the ratio is < 1.0 (memory-bound draws more core power than
  compute-bound — would mean stall cycles cost more than issue cycles, and the
  insn-count proxy is the wrong core activity metric), or > 2.0 (the proxy is
  far more sensitive than the model assumes).
- ⚠️ This one needs the §0.1 time base. Without `wall_ns` it is not computable.

### P3 — total SoC ratio lands near the vendor's memory/core ratio
- **P3:** `GROUP_SOC_FULL` energy ratio `bench-mem / bench-alu`, normalised to
  equal wall time, falls in **1.15 – 1.55** (brackets the SOURCED 1.36×).
- **Refuted if:** outside that band. Note our workloads are not Stream and
  Dhrystone, so a miss here is weaker evidence than a miss on P1 or P2 — it
  indicts the comparison, not necessarily the model.
- **This is a SOURCED-anchored prediction.** The result will be MEASURED. The
  comparison is legitimate *as a prediction test* but the two numbers may never
  be quoted side by side as if equally grounded.

### P4 — the gate-activity bridge is linear in duty cycle
The deck's recommendation, and the only prediction that tests the bridge itself:

    AF_app = AF_idle + (AF_max − AF_idle) × U

- **P4:** with `bench-alu` run at duty **U ∈ {0.25, 0.50, 0.75, 1.00}**,
  `vdd_arm` energy is linear in U with **R² ≥ 0.95**, and the U→0 intercept
  agrees with the separately measured idle floor within **±15%**.
- **Refuted if:** R² < 0.95 (the bridge is not linear and the spreadsheet line
  cannot be filled this way), or the intercept misses the measured idle floor
  (the model is linear but not *this* line — fitted, not predicted).
- ⚠️ **Prep needed:** no duty-parameterised workload exists. `bench-alu` runs
  flat out. A `bench-duty` variant (WFI/WFE for a fraction of each window) must
  be written and its QEMU vectors collected **before** the board arrives, or P4
  cannot be tested on day one.

---

## 4. What we will not claim, whatever the numbers say

- **QEMU will not emit watts.** It measures activity; engineers convert activity
  to energy with a calibration this campaign produces. A QEMU-derived wattage
  compared against a BCU wattage is a DERIVED-vs-MEASURED comparison — the
  precise thing Law 1 forbids, and the temptation is strongest exactly now that
  a board reads real watts.
- **A fitted coefficient is not a validated model.** If P4's R² comes out high
  only after choosing `AF_idle`/`AF_max` from the same data, that is a fit. The
  intercept check exists to make that distinguishable.
- **Accelerator AF stays coarse.** No NPU/GPU/VPU rail exists on this board. We
  will not report a per-accelerator activity factor derived from `vdd_soc`.
- **n = 5 with the spread published.** A single reading per workload is not a
  measurement, and a median without its spread hides a bimodal rail.

---

## 5. Day-one order of operations

1. Idle floor, all rails, n = 5. *(Nothing below is interpretable without it.)*
2. ~~Confirm the bare-metal images boot on real silicon~~ **DONE on the FRDM
   2026-09-08: they boot and run (§0.7). But WFI does not wake on silicon, so
   P4's U < 1.0 points are BLOCKED until that is fixed.** P1/P2/P3 are unaffected
   — they need no idle phase.
3. `bench-alu`, `bench-mem`, n = 5 each → P1, P2, P3.
4. `bench-duty` sweep → P4. *(Only if the workload exists by then.)*

Prep status: `wall_ns` schema field (§0.1) **DONE** — schema, `run-activity.sh`
and `parse_activity.py` all carry it, labelled HOST wall time under TCG.
`bench-duty` (§3 P4) **DONE and verified in QEMU** — see §0.4.
Remaining before the board: build the silicon-sized `bench-duty` variants (§0.3)
and collect their QEMU vectors.
