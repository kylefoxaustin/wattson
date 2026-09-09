/*
 * wattson userspace workloads: the cache-enabled counterparts of bench-alu.S
 * and bench-mem.S.
 *
 * WHY THESE EXIST. The bare-metal images must be started with U-Boot `go`,
 * which needs `dcache off` - that drops the MMU and the data cache. With caches
 * disabled a streaming workload CANNOT stream: every access is a slow,
 * unpipelined transaction, DRAM utilisation stays near zero and the core stalls
 * instead of issuing. Measured consequence on silicon: bench-mem showed NO DRAM
 * rail activity (P1b untestable) and drew LESS total power than the compute
 * workload (P3 failed, 0.907 against a predicted 1.15-1.55). Those cells
 * indicted the delivery mechanism, not the model.
 *
 * Both modes are TIME-BOUNDED, not iteration-bounded, so the two runs have
 * identical duration and their mean-power ratio is directly comparable without
 * an energy normalisation step.
 *
 *   bench alu <seconds>
 *   bench mem <seconds> [MiB]
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

static double now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "alu";
    double secs = argc > 2 ? atof(argv[2]) : 60.0;
    size_t mib = argc > 3 ? (size_t)atoi(argv[3]) : 512;
    double t0, t1;
    uint64_t ops = 0;

    printf(">>> BENCH-%s START <<<\n", mode);
    fflush(stdout);
    t0 = now();

    if (!strcmp(mode, "alu")) {
        /* register-only churn: same body as bench-alu.S, no memory traffic */
        uint64_t x = 0, k = 2654435761ULL;
        while (now() - t0 < secs) {
            for (int i = 0; i < 4000000; i++) {
                x = x * k; x += 1; x ^= k;
            }
            ops += 4000000;
        }
        printf("checksum %llu\n", (unsigned long long)x);
    } else {
        /*
         * Stream a buffer far larger than any cache so every pass really does
         * go to DRAM. 512 MiB by default; the i.MX95 LLC is orders of magnitude
         * smaller, so this cannot be served from cache.
         */
        size_t n = mib * 1024 * 1024 / sizeof(uint64_t);
        uint64_t *buf = malloc(n * sizeof(uint64_t));
        uint64_t sum = 0;
        if (!buf) { fprintf(stderr, "alloc failed\n"); return 1; }
        memset(buf, 1, n * sizeof(uint64_t));      /* fault it all in first */
        while (now() - t0 < secs) {
            for (size_t i = 0; i < n; i++) buf[i] += 3;      /* read+write */
            for (size_t i = 0; i < n; i += 8) sum += buf[i]; /* read */
            ops += n;
        }
        printf("checksum %llu\n", (unsigned long long)sum);
    }

    t1 = now();
    printf(">>> BENCH-%s DONE <<< %.2fs ops=%llu\n", mode, t1 - t0,
           (unsigned long long)ops);
    fflush(stdout);
    return 0;
}
