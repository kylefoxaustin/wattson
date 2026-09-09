/*
 * COUNTER-VALIDATION PROBE.
 *
 * Fixed, deterministic work - no timers, no thread count, no wall-clock
 * dependence - so the SAME static binary produces the SAME architectural counts
 * whether it runs on the EVK under perf or under qemu-aarch64 with TCG plugins.
 * That is what makes QEMU's estimates comparable to the silicon's own PMU.
 *
 *   probe alu <Miters>     register-only, ~0 memory traffic
 *   probe mem <MiB> <passes>  streams a buffer: known, countable DRAM traffic
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "alu";
    if (!strcmp(mode, "alu")) {
        long m = argc > 2 ? atol(argv[2]) : 200;
        uint64_t x = 0, k = 2654435761ULL;
        for (long i = 0; i < m * 1000000L; i++) {
            x = x * k; x += 1; x ^= k;
            __asm__ __volatile__("" : "+r"(x));
        }
        printf("alu Miters=%ld checksum=%llu\n", m, (unsigned long long)x);
    } else {
        long mib = argc > 2 ? atol(argv[2]) : 64;
        long passes = argc > 3 ? atol(argv[3]) : 4;
        size_t n = (size_t)mib * 1024 * 1024 / sizeof(uint64_t);
        uint64_t *b = malloc(n * sizeof(uint64_t)), s = 0;
        if (!b) return 1;
        memset(b, 1, n * sizeof(uint64_t));
        for (long p = 0; p < passes; p++)
            for (size_t i = 0; i < n; i++) { b[i] += 3; s += b[i]; }
        /* expected DRAM traffic = mib * passes * 2 (read+write), in MiB */
        printf("mem MiB=%ld passes=%ld expect_MiB=%ld checksum=%llu\n",
               mib, passes, mib * passes * 2, (unsigned long long)s);
        free(b);
    }
    return 0;
}
