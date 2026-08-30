# xcheck results — 2026-08-30, i.MX95 FRDM vs qemu-aarch64 + TCG plugins

Six workloads, same static aarch64 binaries both sides. QEMU: linux-user +
libinsn + libcache configured to the FRDM's own hierarchy (sysfs-read: L1D/I
32K/4w/64B; outer level modelled as the DSU's shared 512K/16w L3, so plugin
l2_miss = DRAM-transaction proxy). Silicon: perf stat, pinned to A55 core 0.
QEMU counts DERIVED; PMU counts MEASURED; ratios are the labelled bridge.

| workload | corner | i_ratio | q_dram_proxy | hw_l3_refill | dram_ratio |
|---|---|---|---|---|---|
| alu   | pure compute      | 0.999 | 912        | 3,170      | (noise floor) |
| chase | dependent loads   | 1.042 | 29,966,600 | 29,217,268 | **1.03** |
| mem   | streaming stores  | 0.978 | 16,778,218 | 8,534,963  | **1.97** |
| mm    | cache-thrash FP   | 0.996 | 2,291,420  | 5,260,091  | **0.44** |
| sgm   | real vision app   | 0.997 | 11,974,253 | 7,195,900  | **1.66** |
| sort  | branchy           | 0.994 | 4,790,664  | 1,577,599  | **3.04** |

## Findings

1. **The instruction half of the activity vector is VALIDATED, including on a
   real application.** i_ratio 0.978–1.042 across all six; 0.997 on the 10.1B-
   instruction SGM run. Same binary retires the same instructions; the ±4% is
   silicon-side kernel/IRQ time inside the perf window.
2. **The DRAM proxy is exact at the latency-bound corner** (chase 1.03 with the
   matched geometry; 0.96 even at default geometry). Where misses are
   compulsory/capacity and prefetch can't help, the functional cache IS the
   silicon.
3. **Elsewhere the proxy is within 0.4–3.0x, and the deviations have names:**
   - *mem = 1.97x over*: the A55 detects streaming stores and goes
     write-streaming (no-allocate); the plugin read-allocates every store —
     a per-class, correctable 2x.
   - *mm = 0.44x under*: the model has no intermediate 64K L2, so L1 filters
     what on silicon becomes L2-thrash traffic into L3.
   - *sort = 3.0x over*: working set > L3 both sides but silicon reuses far
     better — plausibly replacement/prefetch policy; unattributed, flagged.
4. **Verdict against the pre-registered criterion:** the DRAM ratio is NOT a
   single stable constant across workloads, so the raw one-number proxy is not
   yet P1-ready. But it is bounded (3x worst case), exact where latency-bound,
   and two of the three deviations are mechanism-attributed with concrete model
   fixes: (a) model write-streaming/no-allocate stores, (b) add the middle 64K
   L2 level (three-level model or two-pass composition). The real-app blend
   (sgm 1.66) sits inside the corner-established envelope, which is itself
   evidence the corners span app behaviour.

Reproduce: `run-qemu.sh` / `run-perf.sh` / `compare.py` + `suite.txt`;
hw records and vectors in `out/` (v1 default-geometry vectors in
`out.defaults/`). FRDM kernel 6.18.20-2.0.0, QEMU 11.0.50 @ build-user.

---
# v1 (same day): 14 applications, DDR-controller ground truth, model fixes in

M1 fixes (three-level sysfs-matched hierarchy; A55-style write-streaming with a
streak detector) plus eight real apps added: bzip2, lz4, lua, sha256, cJSON,
sqlite (in-memory DB), a genetic-AI Pac-Man trainer (seed-pinned,
bit-deterministic), and a mongoose HTTP client against a live server.
Silicon side now also reads the imx9_ddr0 DDR-controller beat counters
(system-wide, idle-window subtracted).

- Instructions: 0.98–1.06 on ALL 14 (net 0.80 — expected: linux-user cannot see
  the app's ~20% kernel share; compare with :u events in a follow-up).
- DRAM reads vs the DDR controller: **proxy = 0.81 × silicon, ×/÷ 1.26** over
  the 8 apps above the counter's ~0.4M-line noise floor; chase 0.97, mem 0.98,
  cjson 0.96, sort 0.96, sgm 0.88, sha256 0.77, mm 0.65, bzip2 0.49. The five
  DRAM-quiet apps (alu, lua, lz4, pacman, sqlite) are correctly classified
  quiet. Residual under-prediction = prefetcher overfetch (unmodelled, named).
- KEY INSTRUMENT LESSON: l3d_cache_refill counts only DEMAND refills — sha256
  read "15x wrong" against it while the DDR controller showed the proxy nearly
  right. Pick ground truth at the DRAM boundary, not inside the hierarchy.
- Writes: streaming class 0.80; scattered writes leave via dirty evictions the
  model does not count yet (writeback model = next plugin iteration). net's
  DRAM (kernel+ethernet DMA) invisible to linux-user — system-mode work.
- Multi-core first point: 4-thread SGM totals within 2% of 1-thread on silicon.

Deck: make_deck.py -> xcheck-correlation.pptx (v1, 6 slides, regenerable).

---
# X1 (same day): the writeback model closes the DRAM-write gap

Dirty-line tracking + last-level eviction counting added to the cache plugin
(write proxy = streaming bursts + dirty writebacks + still-resident dirty
lines). Silicon side unchanged (banked DDR wr_beats). Full-suite re-run:

- **Write proxy = 0.90 x silicon, x/÷ 1.09** over the six apps above the write
  noise floor — TIGHTER than the read side. Per app: cjson 0.08→1.03,
  bzip2 0.03→0.96, sort 0.82→0.91, chase 0.09→0.90, sgm 0.06→0.85, mem 0.80.
- Read ratios unchanged (0.81 x/÷1.26) — the model change was surgical.
- Zero-write apps (sha256, alu) and near-floor rows (lz4/sqlite/pacman)
  correctly sit at/below the DDR write noise floor (~0.1–0.2M lines/window).

Verdict-slide consequence: "DRAM writes" moves from GAP to USABLE (x1.11
correction, x/÷1.09). Remaining open: prefetch model (reads), system-mode
(kernel/DMA/duty), multi-core sweep.

---
# X3 (same day): the multi-core sweep — correlation survives SMP

Shared-L3 topology fix in the plugin (the DSU's 512K is ONE cache, not one per
core), deterministic OpenMP workloads (per-N checksums), 1/2/4/6 threads on
both sides, DDR beats captured per N.

    wl      N   i_ratio  rd_ratio  wr_ratio
    alu-mt  1-6 0.998-1.000   (compute: exact at every N)
    mem-mt  1-6 0.967-0.976  0.98 flat  0.75 flat
    sgm-mt  1,2 0.997/1.009  0.85-0.86  0.84
    sgm-mt  4,6 1.231/1.182  0.88      0.96-0.98

- **DRAM proxies are thread-count-invariant**: mem's read ratio is 0.98 at
  every N; sgm's write ratio tightens to 0.96-0.98 under contention. Bus
  contention does not degrade the model.
- **Instruction inflation at sgm 4/6T (+18-23%) is OpenMP spin-wait**: barrier
  spins are timing-dependent instructions, inflated by instrumentation skew.
  Mitigation measured with OMP_WAIT_POLICY=passive (result appended below).
- Silicon-side confirmation of the artifact's size: silicon itself only adds
  1-4% instructions from 1->6T (10.15B -> 10.59B); the delta is QEMU-side spin.

Verdict-slide consequence: multi-core moves from INSUFFICIENT DATA to USABLE
for DRAM proxies (thread-invariant) and instructions (with passive waiting or
spin-aware accounting for barrier-heavy code).

**Spin-wait mechanism PROVEN (appended):** sgm-mt 4T re-run with
OMP_WAIT_POLICY=passive: i_ratio 1.231 -> **0.985**; DRAM proxies unchanged.
The entire inflation was barrier spin — timing-dependent instructions, not
work. Recommendation now carries a measured basis: extract MT activity vectors
with passive waiting (or subtract spin separately) on barrier-heavy code.

---
# X2a (same day): system-mode boot-differential — kernel share measured

Harness: the imx95 machine (6xA55 + the real NXP SM on the M33) boots a
busybox initramfs whose /init selects the app from the kernel cmdline and
powers off; activity(app) = run(app) − run(null), per-vcpu. NXP boot artifacts
are operator-supplied (never committed); run-system.sh + the initramfs recipe
are in-repo.

- **sha256: kernel+system share = 10.0%** over its user-mode instruction count
  (2.35B work-core differential vs 2.11B linux-user), plus ~10% idle-poll from
  cpuidle.off=1 (this machine's SCMI-wake workaround pins idle cores in the
  kernel poll loop — a machine constraint, decomposed per-cpu, not hidden).
- **Differential noise floor: ±60M insns/cpu boot-to-boot** — chase (370M
  total) sits below it; apps need ≳0.5B insns for a resolvable differential.
- **sgm-mt in-guest reads 32%** — spin+poll, not kernel work: the in-guest run
  lacked OMP_WAIT_POLICY=passive and pinning; X3's proven spin mechanism,
  reappearing exactly where predicted.
- Free byproduct: the M33 SM burns 824M insns during a 2.4s boot and ~1.5-3.8B
  during app runs — the known upstream WFE/WFI idle-spin, measured here as an
  activity number for the first time (the wfe_halt fix exists out-of-tree).

Verdict movement: kernel share = MEASURABLE (one clean number, method + noise
floor stated). DMA/network still needs the full-board build (X2b: the minimal
machine has no NIC). Duty cycle: cpuidle.off=1 makes duty degenerate (idle
cores never sleep) — proper duty needs the cpuidle path modelled, noted for P1.

---
# X2b (same day): network/DMA on the full board — characterized, boundary named

Full-board build (NIC via virtio-mmio + slirp), plugins ported; the guest
fetches 33.5 MB from a live host server and hashes it, boot-differentially
instrumented. Three findings, none fudged:

1. **DMA visibility boundary, confirmed by numbers**: the virtio DMA write
   into guest RAM bypasses TCG (invisible to the cache model, by construction),
   but every CPU-side touch is visible and coherent — read-miss differential
   ≈ 2× payload (DMA buffer → skb → user copies), writeback differential ≈
   the CPU-written copies.
2. **Event-loop clients have timing-dependent instruction counts** (mongoose
   poll: linux-user 0.80 vs boot-diff 1.51 bracket silicon). A blocking-socket
   client did NOT fully converge the system side (1.66 → 1.42 idle-corrected)
   — poll-spin partially falsified as the dominant term; recorded.
3. **Kernel network share is DEVICE-PATH-DEPENDENT**: silicon (real NIC,
   HW offloads) kernel share = 16.7%; guest virtio+slirp = 41% idle-corrected
   (~2.4× kernel instructions — software checksum of the payload, different
   driver, softirq cadence). This is the emulated machine's true activity,
   not an error: model the TARGET's NIC for the target's numbers.

Verdict: network CPU-side activity MEASURABLE end-to-end; DMA traffic needs
accounting outside the cache model (payload bytes are known exactly from the
transfer itself); cross-machine kernel comparison requires matching NIC paths.

---
# X4 (same day): stride prefetcher — read band closes to ×/÷1.14

Three rounds, each mechanism-driven:
- r1 (naive d16, single-stream then 8-stream table, trains on all accesses):
  mm 0.65→0.97 but bzip2 EXPLODED to 4.27 (loose matching aliases near-random
  accesses into phantom streams), mem doubled (training on stores fights the
  write-streaming model), writes wrecked by pollution.
- r2 (train on LOAD L1-MISSES only, strict +1 advance, ramped depth 2→16):
  **reads geo 0.98 ×/÷ 1.14 over the 8 above-floor apps** — the roadmap's
  <×/÷1.15 exit criterion, met. bzip2 0.49→1.26, mm 1.07, chase/mem/cjson/sort
  0.96–0.98, sgm 0.88, sha256 0.77.
- r3 (prefetch installs to L3 only, probing L2): reads unchanged (locked);
  hypothesis "L2 pollution causes lz4's phantom writebacks" FALSIFIED — the
  writeback inflation under the prefetcher persists (L3 turnover recycles hot
  dirty lines). Open refinement, named.

**Shipping shape: two-pass extraction** (afgen does this): READS from the
prefetcher pass (correction ~1.02, band ×/÷1.14); WRITES from the base pass
(0.90 ×/÷1.09, X1). Each quantity from the configuration that models it best;
the lz4 prefetch×writeback interaction is the recorded open item.
