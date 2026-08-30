#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pcg_variants.h"
int main(int argc, char **argv) {
    long n = argc > 1 ? atol(argv[1]) : 80000000L;
    pcg32_random_t rng; pcg32_srandom_r(&rng, 42u, 54u);
    static unsigned long hist[256]; unsigned long acc = 0;
    for (long i = 0; i < n; i++) hist[pcg32_random_r(&rng) & 255]++;
    for (int i = 0; i < 256; i++) acc = acc*31 + hist[i];
    printf("pcg n=%ld acc=%lu\n", n, acc);
    return 0;
}
