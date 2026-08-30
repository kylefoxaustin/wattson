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
