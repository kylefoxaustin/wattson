# wattson workloads

Bounded bare-metal ARM64 images for the `qemu-imx95` machine. Each does a fixed
amount of work and then issues **PSCI `SYSTEM_OFF`** so QEMU exits cleanly and the
TCG plugins flush their counts — an infinite-loop workload never flushes.

| workload | what it exercises | activity signature |
|---|---|---|
| `bench-alu` | register-only integer churn (mul/add/eor), ~no memory | high insns, ~0 DRAM |
| `bench-mem` | streams a 256 MiB region ×4 (write + read) | moderate insns, high DRAM misses |

These two bracket the compute↔memory axis and are the P0 proof that the activity
vector discriminates workload types. The P1 suite will add idle, a mixed real
application, and an accelerator run.

## Build

```sh
make            # needs aarch64-linux-gnu binutils (as/ld/objcopy)
```

Produces `*.bin`, flat images linked at `0x80000000` (DDR base per the imx95 map).
Prebuilt `.bin`s are committed so the harness runs out of the box.

## Add a workload

Write `foo.S` (bounded; end with the PSCI `SYSTEM_OFF` sequence — copy it from
`bench-alu.S`), add `foo` to `WORKLOADS` in the Makefile, `make`, then:

```sh
../harness/run-activity.sh foo.bin foo "what it does"
```
