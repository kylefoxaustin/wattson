/* xcheck network app: HTTP GET a payload from a local server, FNV-hash every
 * byte as it arrives, repeat N times. Real network stack usage (sockets, event
 * loop, HTTP parsing) with the processing loop bounded by the payload. */
#include "mongoose.h"
static uint64_t fnv = 0xcbf29ce484222325ULL;
static long grabbed = 0; static int done_flag = 0;
static void cb(struct mg_connection *c, int ev, void *ev_data) {
    if (ev == MG_EV_CONNECT) {
        struct mg_str host = mg_url_host((char *)c->fn_data);
        mg_printf(c, "GET %s HTTP/1.0\r\nHost: %.*s\r\n\r\n",
                  mg_url_uri((char *)c->fn_data), (int)host.len, host.buf);
    } else if (ev == MG_EV_READ) {
        for (size_t i = 0; i < c->recv.len; i++) {
            fnv ^= c->recv.buf[i]; fnv *= 0x100000001b3ULL;
        }
        grabbed += c->recv.len; mg_iobuf_del(&c->recv, 0, c->recv.len);
    } else if (ev == MG_EV_CLOSE || ev == MG_EV_ERROR) {
        done_flag = 1;
    }
}
int main(int argc, char **argv) {
    const char *url = argc > 1 ? argv[1] : "http://127.0.0.1:8765/data.bin";
    int reps = argc > 2 ? atoi(argv[2]) : 8;
    for (int r = 0; r < reps; r++) {
        struct mg_mgr mgr; mg_mgr_init(&mgr);
        done_flag = 0;
        struct mg_connection *c = mg_connect(&mgr, url, cb, (void *)url);
        if (!c) { fprintf(stderr, "connect failed\n"); return 2; }
        while (!done_flag) mg_mgr_poll(&mgr, 50);
        mg_mgr_free(&mgr);
    }
    printf("net reps=%d bytes=%ld fnv=0x%016llx\n", reps, grabbed, (unsigned long long)fnv);
    return 0;
}
