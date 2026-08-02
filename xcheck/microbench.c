/*
 * wattson cross-check microbench.
 *
 * A portable aarch64 Linux binary with the SAME workload semantics as the
 * bare-metal workloads/ (bench-alu = register churn, bench-mem = memory stream).
 * The point is to run the *identical binary* two ways and compare the activity:
 *
 *   - real silicon:  perf stat ./microbench ...      (hardware PMU counters)
 *   - QEMU:          qemu-aarch64 -plugin libinsn -plugin libcache ./microbench ...
 *
 * If QEMU's plugin counts track the hardware PMU counts (esp. cache misses vs
 * LLC misses = the DRAM-transaction proxy), wattson's activity model is
 * validated and we get a correction factor for P1. See xcheck/README.md.
 *
 * Deterministic, single-threaded, no I/O in the measured region. Prints a
 * checksum at the end so nothing is optimized away.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/* Same multiplier the bare-metal bench-alu uses. */
#define K 2654435761ULL

static uint64_t bench_alu(uint64_t iters)
{
    uint64_t acc = 0;
    for (uint64_t i = 0; i < iters; i++) {
        acc = acc * K;       /* mul */
        acc = acc + 1;       /* add */
        acc = acc ^ K;       /* eor */
    }
    return acc;              /* returned + printed -> loop not elided */
}

static uint64_t bench_mem(size_t mib, uint64_t passes)
{
    size_t n = (mib * 1024ULL * 1024ULL) / sizeof(uint64_t);
    uint64_t *buf = malloc(n * sizeof(uint64_t));
    if (!buf) { perror("malloc"); exit(2); }
    uint64_t sum = 0;
    for (uint64_t p = 0; p < passes; p++) {
        for (size_t i = 0; i < n; i++) buf[i] = i + p;   /* write sweep */
        for (size_t i = 0; i < n; i++) sum += buf[i];    /* read sweep  */
    }
    free(buf);
    return sum;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr,
            "usage: %s alu <iters>\n"
            "       %s mem <MiB> <passes>\n", argv[0], argv[0]);
        return 1;
    }
    uint64_t r;
    if (!strcmp(argv[1], "alu")) {
        uint64_t iters = (argc > 2) ? strtoull(argv[2], NULL, 0) : 500000000ULL;
        r = bench_alu(iters);
        printf("alu iters=%llu checksum=0x%016llx\n",
               (unsigned long long)iters, (unsigned long long)r);
    } else if (!strcmp(argv[1], "mem")) {
        size_t mib   = (argc > 2) ? strtoull(argv[2], NULL, 0) : 256;
        uint64_t pas = (argc > 3) ? strtoull(argv[3], NULL, 0) : 4;
        r = bench_mem(mib, pas);
        printf("mem MiB=%zu passes=%llu checksum=0x%016llx\n",
               mib, (unsigned long long)pas, (unsigned long long)r);
    } else {
        fprintf(stderr, "unknown workload: %s\n", argv[1]);
        return 1;
    }
    return 0;
}
