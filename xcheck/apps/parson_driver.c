#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "parson.h"
int main(int argc, char **argv) {
    int items = argc > 1 ? atoi(argv[1]) : 15000, reps = argc > 2 ? atoi(argv[2]) : 5;
    unsigned long acc = 0;
    for (int r = 0; r < reps; r++) {
        JSON_Value *root = json_value_init_array();
        JSON_Array *arr = json_value_get_array(root);
        for (int i = 0; i < items; i++) {
            JSON_Value *o = json_value_init_object();
            JSON_Object *ob = json_value_get_object(o);
            json_object_set_number(ob, "id", i);
            char nm[32]; snprintf(nm, sizeof nm, "node-%d", i*7%9973);
            json_object_set_string(ob, "name", nm);
            json_object_set_boolean(ob, "ok", i & 1);
            json_array_append_value(arr, o);
        }
        char *s = json_serialize_to_string(root);
        JSON_Value *back = json_parse_string(s);
        acc += json_array_get_count(json_value_get_array(back)) + strlen(s);
        json_free_serialized_string(s); json_value_free(back); json_value_free(root);
    }
    printf("parson items=%d reps=%d acc=%lu\n", items, reps, acc);
    return 0;
}
