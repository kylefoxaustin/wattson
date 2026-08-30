#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"
int main(int argc, char **argv) {
    int items = argc > 1 ? atoi(argv[1]) : 20000, reps = argc > 2 ? atoi(argv[2]) : 6;
    /* synthesize a deterministic JSON document */
    size_t cap = (size_t)items * 64 + 64; char *doc = malloc(cap); char *p = doc;
    p += sprintf(p, "[");
    for (int i = 0; i < items; i++)
        p += sprintf(p, "%s{\"id\":%d,\"name\":\"item-%d\",\"v\":[%d,%d,%d],\"ok\":%s}",
                     i ? "," : "", i, i * 7 % 1000, i % 17, i % 23, i % 29, i & 1 ? "true" : "false");
    sprintf(p, "]");
    unsigned long sum = 0;
    for (int r = 0; r < reps; r++) {
        cJSON *j = cJSON_Parse(doc);
        char *out = cJSON_PrintUnformatted(j);
        sum += strlen(out) + (unsigned)cJSON_GetArraySize(j);
        free(out); cJSON_Delete(j);
    }
    printf("cjson items=%d reps=%d sum=%lu\n", items, reps, sum);
    return 0;
}
