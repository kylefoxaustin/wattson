#define QOI_IMPLEMENTATION
#include "qoi.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
int main(int argc, char **argv) {
    int reps = argc > 1 ? atoi(argv[1]) : 12;
    int w = 800, h = 600;
    unsigned char *px = malloc(w*h*4);
    uint64_t s = 7;
    for (int i = 0; i < w*h; i++) {  /* gradients + noisy patches: QOI-realistic */
        int x = i % w, y = i / w;
        s ^= s<<13; s ^= s>>7; s ^= s<<17;
        px[i*4+0] = (x*255)/w; px[i*4+1] = (y*255)/h;
        px[i*4+2] = ((x^y) & 32) ? (s & 255) : 128; px[i*4+3] = 255;
    }
    unsigned long acc = 0;
    for (int r = 0; r < reps; r++) {
        qoi_desc d = { .width = w, .height = h, .channels = 4, .colorspace = QOI_LINEAR };
        int len; void *out = qoi_encode(px, &d, &len);
        acc += len; px[0] = ((unsigned char*)out)[20]; free(out);
    }
    printf("qoi reps=%d acc=%lu\n", reps, acc);
    return 0;
}
