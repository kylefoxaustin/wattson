# xcheck — activity-model cross-check (QEMU vs real silicon)

Validates wattson's load-bearing assumption **before** power calibration: does
QEMU's functional activity (esp. the cache-miss DRAM proxy) track what real
silicon actually does? This needs **no power measurement** — just PMU counters —
so it can run on any i.MX95 board (including ones without power circuits), and it
de-risks P1 by giving a QEMU→hardware **correction factor**.

## The idea: same binary, both sides

`microbench.c` (ALU churn + memory stream — same semantics as `workloads/`) is
built once as a portable aarch64 Linux binary and run two ways:

- **QEMU** — `run-qemu.sh` under `qemu-aarch64` (linux-user) + `libinsn`/`libcache`
  → a wattson activity vector.
- **Real silicon** — `run-perf.sh` on the board under `perf stat`
  → a HW activity record (PMU counters).

`compare.py` lines them up:

```
insn_ratio = QEMU insns            / HW instructions        (~1.0 expected)
dram_ratio = QEMU dram_transactions / HW LLC misses          <-- the calibration target
```

A **stable `dram_ratio` across workloads** means QEMU's cache model tracks the
real hierarchy up to a constant we can correct for → the proxy is sound. A
workload-dependent ratio means the cache model needs work before P1.

## Build

```sh
aarch64-linux-gnu-gcc -static -O2 -Wall -o microbench microbench.c
```
(Static so the same binary runs on the board and under qemu-user.) The QEMU side
also needs a linux-user QEMU:
```sh
../configure --target-list=aarch64-linux-user --enable-plugins && ninja qemu-aarch64
```

## Run

```sh
# QEMU side (host):
./run-qemu.sh mem-256x4 -- mem 256 4 > mem.qemu.json
./run-qemu.sh alu-500M  -- alu 500000000 > alu.qemu.json

# board side (scp microbench + run-perf.sh to the i.MX95, then on the board):
./run-perf.sh mem-256x4 -- mem 256 4 > mem.hw.json
./run-perf.sh alu-500M  -- alu 500000000 > alu.hw.json

# compare (host):
./compare.py mem.qemu.json mem.hw.json
```

## Status

- **QEMU side: working now.** `samples/xcheck/` holds real dry-run vectors; the
  DRAM proxy is exact (mem 64 MiB×2 → 268 MB estimated = 256 MiB streamed ×
  write+read). No board needed for this half.
- **Board side: runs on any i.MX95 with `perf`** — the FRDM-PRO qualifies for the
  *activity* cross-check even though it can't do power. When a board is available,
  scp two files and run.

## Provenance (Law 1)

QEMU counts are **DERIVED**; PMU counts are **MEASURED**; the ratio is the
labelled bridge. The ratio is never reported as a measured silicon activity
factor, and the microbench prints a checksum so nothing is optimized away.
