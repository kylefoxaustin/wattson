#include <stdio.h>
#include <stdlib.h>
#include "tommath.h"
int main(int argc, char **argv) {
    int bits = argc > 1 ? atoi(argv[1]) : 1024, reps = argc > 2 ? atoi(argv[2]) : 60;
    mp_int base, expo, mod, res;
    mp_init_multi(&base, &expo, &mod, &res, NULL);
    mp_rand(&base, bits/MP_DIGIT_BIT); mp_rand(&expo, bits/MP_DIGIT_BIT); mp_rand(&mod, bits/MP_DIGIT_BIT);
    if (mp_iseven(&mod)) mp_add_d(&mod, 1, &mod);
    unsigned long acc = 0;
    for (int r = 0; r < reps; r++) { mp_exptmod(&base, &expo, &mod, &res); acc += res.dp[0] & 0xff; mp_add_d(&base, 1, &base); }
    printf("tommath bits=%d reps=%d acc=%lu\n", bits, reps, acc);
    return 0;
}
