# Roadmap → "How well does QEMU correlate with activity factors?" (the deck)

Final deliverable: a PowerPoint a power engineer can act on — instrument,
evidence, correction factors with error bands, and an explicit statement of
what to trust and what not to. The deck is built at v0 TODAY from M0 data and
re-generated at every milestone (`make_deck.py`); iteration happens on the
living deck, not at the end.

## M0 — DONE (2026-08-30): instrument + first correlation
Six workloads, same binaries, QEMU TCG plugins vs FRDM PMUs.
Result: instructions validated (0.978–1.042, incl. 0.997 on a 10.1B-insn real
app); DRAM proxy exact at the latency corner (1.03), bounded 0.44–3.0x
elsewhere; write-streaming (~2x) and missing-middle-L2 mechanisms named.

## M1 — kill the named mechanisms (model fixes, re-run)
- a. Three-level cache: extend contrib/plugins/cache.c with an L3 (we own the
     QEMU tree) → L1 32K/4w, L2 64K/4w, L3 512K/16w; l3_miss = DRAM proxy.
- b. Store-streaming: model no-allocate for streaming stores (or post-correct
     the store class with the measured 2x until modelled).
- Exit: mem → ~1.0, mm → closer to 1; the band across corners tightens.
- Re-run suite; deck gains a before/after slide.

## M2 — widen to a real-app population
- 6–10 third-party apps from the code-sweep corpus (zlib, bzip2, lua, sqlite,
  brotli, base64…), static aarch64, deterministic inputs.
- Deliverable: scatter q_dram vs hw_dram across all apps, r², fitted
  per-class correction factor + error band. This is the deck's money chart.

## M3 — silicon-side depth
- imx9_ddr0 DDR-controller PMU as system-level ground truth (idle-corrected
  bytes) vs L3-refill×64B — closes the "is L3-refill really DRAM?" gap.
- Multi-core: same apps at -t 6 vs QEMU system-mode plugins (boot-differential
  method) — does the correlation survive SMP contention?
- Duty cycle: active-fraction validation (wattson P1's other axis).

## M4 — the deck, final pass
- Method → instrument validation → per-corner results → before/after model
  fixes → real-app scatter with fitted corrections → what P1 may trust
  (instructions: yes; DRAM: with class corrections; what remains open).
- Every number tagged MEASURED/DERIVED; QEMU counts never called silicon.

Cost estimate: M1 ~a session (plugin C work + re-runs), M2 ~a session (builds
+ runs), M3 ~a session. Deck regenerates in seconds at each step.

---
# Rev 2 roadmap — closing the gaps the deck names (M0–M4 above: DONE 2026-08-30)

Ordered by payoff-per-effort. Each milestone has an exit criterion measured the
same way the original campaign was: against silicon, with the ratio published
whichever way it falls.

## X1 — writeback model (the DRAM-write gap)
Add dirty bits + eviction-writeback counting to the cache plugin (same file as
the L3/wstream patch). DRAM-write proxy becomes wstream bursts + dirty
evictions. Exit: write ratios vs imx9_ddr0 wr_beats move from ~0.05 (scattered
apps) toward the streaming class's 0.80+ across the 14-app suite.

## X2 — system-mode boot-differential harness (kernel, DMA, duty cycle)
Boot the imx95 machine model (kernel + busybox initramfs exist) with plugins;
activity(app) = run(app-as-init) − run(null-init). Brings kernel instruction
share (net's missing 20%), DMA-adjacent traffic, and WFI-residency duty cycle
(schema field active_fraction_by_cpu) into scope. Exit: net's i-ratio computed
against full user+kernel counts lands 0.95–1.05.

## X3 — multi-core sweep
Suite at 1/2/4/6 threads: plugin cores=N per-core caches vs pinned silicon
core-sets, DDR PMU alongside. Exit: per-thread-count correlation table; the
single 4-thread point (within 2%) becomes a curve.

## X4 — prefetch model (tighten the read band)
Next-line/stride prefetcher in the plugin, iterated against DDR ground truth;
per-class fitted factors as the fallback if a simple model won't converge.
Exit: bzip2/mm/sqlite move toward 1.0 and the population geo-sd drops below
x/1.15.

## P1 — power calibration (hardware-blocked)
Unchanged: needs the IMX95LPD5EVK-19 (BCU rails, AN14449 procedure). X1–X4
sharpen the activity vectors P1 will regress against measured rail power.
