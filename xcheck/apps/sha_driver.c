#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sha256.h"
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb");
    static unsigned char buf[4*1024*1024];
    size_t n = fread(buf, 1, sizeof buf, f); fclose(f);
    int reps = argc > 2 ? atoi(argv[2]) : 32;
    BYTE h[32]; SHA256_CTX c;
    for (int r = 0; r < reps; r++) {
        sha256_init(&c); sha256_update(&c, buf, n); sha256_final(&c, h);
        buf[0] = h[0];                       /* chain so reps can't collapse */
    }
    for (int i = 0; i < 32; i++) printf("%02x", h[i]); puts("");
    return 0;
}
