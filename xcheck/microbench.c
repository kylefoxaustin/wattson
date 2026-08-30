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

/* Pointer chase: a random permutation cycle walked serially. Every hop is a
 * dependent load with no spatial locality -- the cache-miss-heavy,
 * latency-bound extreme. Deterministic xorshift so both sides walk the same
 * permutation. */
static uint64_t xs(uint64_t *s) { *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17; return *s; }
static uint64_t bench_chase(size_t mib, uint64_t hops)
{
    size_t n = (mib * 1024ULL * 1024ULL) / sizeof(uint64_t);
    uint64_t *nxt = malloc(n * sizeof(uint64_t));
    if (!nxt) { perror("malloc"); exit(2); }
    for (size_t i = 0; i < n; i++) nxt[i] = i;
    uint64_t seed = 0x77A11E5;                     /* Fisher-Yates, fixed seed */
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = xs(&seed) % (i + 1);
        uint64_t t = nxt[i]; nxt[i] = nxt[j]; nxt[j] = t;
    }
    uint64_t p = 0;
    for (uint64_t h = 0; h < hops; h++) p = nxt[p];
    free(nxt);
    return p;
}

/* Blocked f64 matmul: FP/SIMD-friendly compute with L1-resident tiles --
 * high arithmetic intensity, the opposite corner from chase. */
static uint64_t bench_mm(size_t dim, uint64_t reps)
{
    double *a = malloc(dim * dim * sizeof(double));
    double *b = malloc(dim * dim * sizeof(double));
    double *c = calloc(dim * dim, sizeof(double));
    if (!a || !b || !c) { perror("malloc"); exit(2); }
    for (size_t i = 0; i < dim * dim; i++) { a[i] = (double)(i & 1023) * 0.5; b[i] = (double)(i & 511) * 0.25; }
    for (uint64_t r0 = 0; r0 < reps; r0++)
        for (size_t i = 0; i < dim; i++)
            for (size_t k = 0; k < dim; k++) {
                double av = a[i * dim + k];
                for (size_t j = 0; j < dim; j++)
                    c[i * dim + j] += av * b[k * dim + j];
            }
    double s = 0; for (size_t i = 0; i < dim * dim; i++) s += c[i];
    uint64_t out; memcpy(&out, &s, 8);
    free(a); free(b); free(c);
    return out;
}

/* qsort on pseudo-random ints: branchy, call-heavy, moderate locality --
 * the "control flow" corner. */
static int cmpi(const void *x, const void *y)
{ int a = *(const int*)x, b = *(const int*)y; return (a > b) - (a < b); }
static uint64_t bench_sort(size_t kints, uint64_t reps)
{
    size_t n = kints * 1024;
    int *v = malloc(n * sizeof(int));
    if (!v) { perror("malloc"); exit(2); }
    uint64_t sum = 0, seed;
    for (uint64_t r0 = 0; r0 < reps; r0++) {
        seed = 0x5EED + r0;
        for (size_t i = 0; i < n; i++) v[i] = (int)(xs(&seed) & 0x7fffffff);
        qsort(v, n, sizeof(int), cmpi);
        sum += (uint64_t)v[0] + v[n/2] + v[n-1];
    }
    free(v);
    return sum;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr,
            "usage: %s alu   <iters>\n"
            "       %s mem   <MiB> <passes>\n"
            "       %s chase <MiB> <hops>\n"
            "       %s mm    <dim> <reps>\n"
            "       %s sort  <Kints> <reps>\n", argv[0], argv[0], argv[0], argv[0], argv[0]);
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
    } else if (!strcmp(argv[1], "chase")) {
        size_t mib   = (argc > 2) ? strtoull(argv[2], NULL, 0) : 64;
        uint64_t hop = (argc > 3) ? strtoull(argv[3], NULL, 0) : 20000000ULL;
        r = bench_chase(mib, hop);
        printf("chase MiB=%zu hops=%llu checksum=0x%016llx\n", mib, (unsigned long long)hop, (unsigned long long)r);
    } else if (!strcmp(argv[1], "mm")) {
        size_t dim   = (argc > 2) ? strtoull(argv[2], NULL, 0) : 256;
        uint64_t rep = (argc > 3) ? strtoull(argv[3], NULL, 0) : 8;
        r = bench_mm(dim, rep);
        printf("mm dim=%zu reps=%llu checksum=0x%016llx\n", dim, (unsigned long long)rep, (unsigned long long)r);
    } else if (!strcmp(argv[1], "sort")) {
        size_t ki    = (argc > 2) ? strtoull(argv[2], NULL, 0) : 1024;
        uint64_t rep = (argc > 3) ? strtoull(argv[3], NULL, 0) : 4;
        r = bench_sort(ki, rep);
        printf("sort Kints=%zu reps=%llu checksum=0x%016llx\n", ki, (unsigned long long)rep, (unsigned long long)r);
    } else {
        fprintf(stderr, "unknown workload: %s\n", argv[1]);
        return 1;
    }
    return 0;
}
