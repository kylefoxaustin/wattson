/* Multi-threaded xcheck kernels (OpenMP): parallel ALU churn and parallel
 * memory stream. Deterministic totals regardless of thread count (per-thread
 * work is index-partitioned; reductions are order-insensitive: xor / add). */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <omp.h>
#define K 2654435761ULL
int main(int argc, char **argv)
{
    if (argc < 4) { fprintf(stderr, "usage: %s alu|mem <size> <arg> [threads]\n", argv[0]); return 1; }
    int nt = argc > 4 ? atoi(argv[4]) : 1;
    omp_set_num_threads(nt);
    uint64_t r = 0;
    if (!strcmp(argv[1], "alu")) {
        uint64_t iters = strtoull(argv[2], NULL, 0);
        (void)argv[3];
        uint64_t acc_all = 0;
        #pragma omp parallel reduction(^:acc_all)
        {
            int t = omp_get_thread_num(), n = omp_get_num_threads();
            uint64_t per = iters / n, acc = 0x9E3779B9 + t;
            for (uint64_t i = 0; i < per; i++) { acc = acc * K; acc = acc + 1; acc = acc ^ K; }
            acc_all ^= acc;
        }
        r = acc_all;
        printf("alu-mt iters=%llu threads=%d checksum=0x%016llx\n",
               (unsigned long long)iters, nt, (unsigned long long)r);
    } else if (!strcmp(argv[1], "mem")) {
        size_t mib = strtoull(argv[2], NULL, 0);
        uint64_t passes = strtoull(argv[3], NULL, 0);
        size_t n = mib * 1024ULL * 1024ULL / 8;
        uint64_t *buf = malloc(n * 8);
        if (!buf) { perror("malloc"); return 2; }
        uint64_t sum = 0;
        for (uint64_t p = 0; p < passes; p++) {
            #pragma omp parallel for schedule(static)
            for (size_t i = 0; i < n; i++) buf[i] = i + p;
            uint64_t s = 0;
            #pragma omp parallel for schedule(static) reduction(+:s)
            for (size_t i = 0; i < n; i++) s += buf[i];
            sum += s;
        }
        free(buf); r = sum;
        printf("mem-mt MiB=%zu passes=%llu threads=%d checksum=0x%016llx\n",
               mib, (unsigned long long)passes, nt, (unsigned long long)r);
    } else { fprintf(stderr, "unknown\n"); return 1; }
    return 0;
}
