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
#include <pthread.h>
#include <unistd.h>
#include <sched.h>

static double now(void);

/* ---- 2-D grid workers ------------------------------------------------- */
static volatile int g_stop;
static double g_secs;
struct worker { int cpu; int kind; unsigned long long ops; unsigned long long bytes; };

static void pin(int cpu)
{
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    sched_setaffinity(0, sizeof(set), &set);
}

static void *w_alu(void *arg)
{
    struct worker *w = arg;
    /*
     * ⚠️ volatile + an asm barrier, NOT a dead `if (x == 42)`.
     * The first version kept x in a local and only "used" it in a branch the
     * optimiser could see was dead, so -O2 ELIDED THE WHOLE LOOP: the smoke
     * test reported 2.7e15 ALU ops/s on a 1.8 GHz core. A rate that exceeds
     * the clock by six orders of magnitude is the tell; a plausible-looking
     * number would not have been caught.
     */
    volatile uint64_t sink = 0;
    uint64_t x = 0, k = 2654435761ULL;
    pin(w->cpu);
    while (!g_stop) {
        for (int i = 0; i < 1000000; i++) {
            x = x * k; x += 1; x ^= k;
            __asm__ __volatile__("" : "+r"(x));   /* x is genuinely computed */
        }
        w->ops += 1000000;
        sink = x;
    }
    (void)sink;
    return NULL;
}

static void *w_mem(void *arg)
{
    struct worker *w = arg;
    size_t n = 256UL * 1024 * 1024 / sizeof(uint64_t);   /* 256 MiB per thread */
    uint64_t *buf = malloc(n * sizeof(uint64_t));
    uint64_t sum = 0;
    pin(w->cpu);
    if (!buf) return NULL;
    memset(buf, 1, n * sizeof(uint64_t));
    while (!g_stop) {
        for (size_t i = 0; i < n; i++) { buf[i] += 3; sum += buf[i]; }
        w->bytes += (unsigned long long)n * sizeof(uint64_t) * 2;
    }
    if (sum == 42) printf(" ");
    free(buf);
    return NULL;
}

static void run_grid(double secs, int n_alu, int n_mem)
{
    struct worker w[8];
    pthread_t th[8];
    int n = 0, cpu = 0;
    double t0, el;
    unsigned long long ops = 0, bytes = 0;

    printf(">>> BENCH-grid START <<< n_alu=%d n_mem=%d\n", n_alu, n_mem);
    fflush(stdout);
    g_stop = 0;
    for (int i = 0; i < n_alu; i++) { w[n] = (struct worker){cpu++, 0, 0, 0}; n++; }
    for (int i = 0; i < n_mem; i++) { w[n] = (struct worker){cpu++, 1, 0, 0}; n++; }
    t0 = now();
    for (int i = 0; i < n; i++)
        pthread_create(&th[i], NULL, w[i].kind ? w_mem : w_alu, &w[i]);
    while (now() - t0 < secs) usleep(50000);
    g_stop = 1;
    for (int i = 0; i < n; i++) pthread_join(th[i], NULL);
    el = now() - t0;
    for (int i = 0; i < n; i++) { ops += w[i].ops; bytes += w[i].bytes; }
    printf(">>> BENCH-grid DONE <<< n_alu=%d n_mem=%d %.2fs alu_ops=%llu bytes=%llu "
           "aluMps=%.1f GBps=%.3f\n", n_alu, n_mem, el, ops, bytes,
           ops / el / 1e6, bytes / el / 1e9);
    fflush(stdout);
}

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

    if (!strcmp(mode, "grid")) {
        /*
         * 2-D GRID - the design that can actually separate the two variables.
         *
         * The bandwidth sweep varied ALU rate and bandwidth on ONE core, so as
         * one rose the other fell: almost perfectly anti-correlated. Two
         * collinear predictors fit equally well (R2 0.794 vs 0.793) and cannot
         * be told apart, so that sweep could not answer which one drives
         * vdd_arm.
         *
         * Here each knob gets its OWN CORES. n_alu threads run register-only
         * work; n_mem threads stream sequentially. Every thread is fully busy on
         * its own core, so there is no idle-fraction confound either, and
         *     alu rate  ~ n_alu        bandwidth ~ n_mem
         * vary INDEPENDENTLY. The part has 6 cores, so n_alu + n_mem <= 6.
         *
         *   bench grid <seconds> <n_alu> <n_mem>
         */
        int n_alu = argc > 3 ? atoi(argv[3]) : 1;
        int n_mem = argc > 4 ? atoi(argv[4]) : 1;
        run_grid(secs, n_alu, n_mem);
        return 0;
    }

    if (!strcmp(mode, "bw")) {
        /*
         * BANDWIDTH SWEEP - the corrected P2-fix axis.
         *
         * The first attempt swept op MIX with a strided access
         * (i = (i+8191) % n) chosen to defeat the cache. It also defeated the
         * PREFETCHERS, so it saturated at ~12.4 Mops/s = ~99 MB/s and every
         * point above 25% memory sat at the same low bandwidth. Sweeping that
         * axis moved ALU rate and left memory traffic nearly constant - so it
         * could not reach the ~2-4 GB/s regime where bench-mem drew 759.8 mW on
         * vdd_arm, and its "refutations" of H1-H3 described a latency-bound
         * regime instead. A control that cannot enter the regime under study
         * is the wrong instrument.
         *
         * This mode instead interleaves SEQUENTIAL streaming passes (which the
         * prefetchers serve, so bandwidth is real) with register ALU work.
         * `pct` now sets the fraction of each round spent streaming, so
         * bandwidth genuinely spans ~0 to full-rate.
         */
        int pct = argc > 3 ? atoi(argv[3]) : 50;
        size_t n = 512UL * 1024 * 1024 / sizeof(uint64_t);
        uint64_t *buf = malloc(n * sizeof(uint64_t));
        uint64_t x = 0, k = 2654435761ULL, sum = 0, alu_ops = 0;
        uint64_t bytes = 0;
        if (!buf) { fprintf(stderr, "alloc failed\n"); return 1; }
        memset(buf, 1, n * sizeof(uint64_t));
        /* chunk = how much of the buffer one round streams; 0 pct = none */
        size_t chunk = (size_t)((double)n * pct / 100.0);
        size_t alu_per_round = (size_t)(4000000.0 * (100 - pct) / 100.0);
        size_t pos = 0;
        while (now() - t0 < secs) {
            for (size_t j = 0; j < alu_per_round; j++) {
                x = x * k; x += 1; x ^= k;
            }
            alu_ops += alu_per_round;
            /* SEQUENTIAL read+write: prefetcher-friendly, real bandwidth */
            for (size_t j = 0; j < chunk; j++) {
                size_t idx = pos + j;
                if (idx >= n) idx -= n;
                buf[idx] += 3;
                sum += buf[idx];
            }
            pos = (pos + chunk) % (n ? n : 1);
            bytes += (uint64_t)chunk * sizeof(uint64_t) * 2;   /* r+w */
        }
        t1 = now();
        double el = t1 - t0;
        printf("checksum %llu %llu\n", (unsigned long long)x, (unsigned long long)sum);
        printf(">>> BENCH-bw DONE <<< pct=%d %.2fs alu_ops=%llu bytes=%llu GBps=%.3f\n",
               pct, el, (unsigned long long)alu_ops, (unsigned long long)bytes,
               bytes / el / 1e9);
        fflush(stdout);
        return 0;
    }

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
