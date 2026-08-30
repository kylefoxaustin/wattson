#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "md5.h"
#include "aes.h"
#include "blowfish.h"
#include "arcfour.h"
#include "base64.h"
static unsigned char buf[4*1024*1024];
int main(int argc, char **argv) {
    FILE *f = fopen(argv[2], "rb");
    size_t n = fread(buf, 1, sizeof buf, f); fclose(f);
    int reps = argc > 3 ? atoi(argv[3]) : 4;
    unsigned long long acc = 0;
    if (!strcmp(argv[1], "md5")) {
        BYTE h[16]; MD5_CTX c;
        for (int r = 0; r < reps*4; r++) { md5_init(&c); md5_update(&c, buf, n); md5_final(&c, h); buf[0]=h[0]; }
        for (int i = 0; i < 16; i++) acc = acc*31 + h[i];
    } else if (!strcmp(argv[1], "aes")) {
        WORD ks[60]; BYTE key[32] = "wattson-xcheck-aes-key-32bytes!!";
        aes_key_setup(key, ks, 256);
        BYTE out[16];
        for (int r = 0; r < reps; r++)
            for (size_t i = 0; i + 16 <= n; i += 16) { aes_encrypt(buf+i, out, ks, 256); acc += out[0]; buf[i] = out[15]; }
    } else if (!strcmp(argv[1], "blowfish")) {
        BLOWFISH_KEY k; BYTE key[16] = "bf-key-16-bytes!";
        blowfish_key_setup(key, &k, 16);
        BYTE out[8];
        for (int r = 0; r < reps; r++)
            for (size_t i = 0; i + 8 <= n; i += 8) { blowfish_encrypt(buf+i, out, &k); acc += out[0]; buf[i] = out[7]; }
    } else if (!strcmp(argv[1], "rc4")) {
        BYTE state[256], key[16] = "rc4-key-16bytes!";
        static BYTE stream[sizeof buf];
        for (int r = 0; r < reps*2; r++) {
            arcfour_key_setup(state, key, 16);
            arcfour_generate_stream(state, stream, n);
            for (size_t i = 0; i < n; i += 4096) acc += stream[i];
        }
    } else if (!strcmp(argv[1], "b64")) {
        static BYTE enc[6*1024*1024];
        for (int r = 0; r < reps*2; r++) { size_t m = base64_encode(buf, enc, n, 0); acc += enc[m-2]; buf[0] = enc[0]; }
    } else return 1;
    printf("%s reps=%d acc=%llu\n", argv[1], reps, acc);
    return 0;
}
