#include <stdio.h>
#include <stdlib.h>
#include "heatshrink_encoder.h"
static unsigned char in[4*1024*1024], out[8*1024*1024];
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb"); size_t n = fread(in, 1, sizeof in, f); fclose(f);
    int reps = argc > 2 ? atoi(argv[2]) : 6;
    unsigned long acc = 0;
    for (int r = 0; r < reps; r++) {
        heatshrink_encoder *e = heatshrink_encoder_alloc(10, 5);
        size_t ip = 0, op = 0, sz;
        while (ip < n) {
            heatshrink_encoder_sink(e, in+ip, n-ip, &sz); ip += sz;
            while (heatshrink_encoder_poll(e, out+op, sizeof(out)-op, &sz) == HSER_POLL_MORE) op += sz;
            op += sz;
        }
        heatshrink_encoder_finish(e);
        while (heatshrink_encoder_poll(e, out+op, sizeof(out)-op, &sz) == HSER_POLL_MORE) op += sz;
        op += sz; acc += op; in[0] = out[0];
        heatshrink_encoder_free(e);
    }
    printf("heatshrink reps=%d acc=%lu\n", reps, acc);
    return 0;
}
