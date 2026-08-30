#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "http_parser.h"
static unsigned long acc;
static int on_url(http_parser *p, const char *at, size_t n){ (void)p; acc += n + at[0]; return 0; }
static int on_hdr(http_parser *p, const char *at, size_t n){ (void)p; acc += n + (n ? at[n-1] : 0); return 0; }
int main(int argc, char **argv) {
    int reps = argc > 1 ? atoi(argv[1]) : 2000;
    char req[2048]; http_parser_settings st; http_parser_settings_init(&st);
    st.on_url = on_url; st.on_header_field = on_hdr; st.on_header_value = on_hdr;
    for (int r = 0; r < reps; r++)
        for (int i = 0; i < 64; i++) {
            int m = snprintf(req, sizeof req,
                "GET /api/v1/items/%d?q=abc&page=%d HTTP/1.1\r\nHost: h%d.example.com\r\n"
                "User-Agent: xcheck/1.0\r\nAccept: application/json\r\nX-Trace: %08x\r\n"
                "Cookie: session=%016x; theme=dark\r\n\r\n", i*r, i, i, i*2654435761u, (unsigned)(r*31+i));
            http_parser p; http_parser_init(&p, HTTP_REQUEST);
            acc += http_parser_execute(&p, &st, req, m);
        }
    printf("httpp reps=%d acc=%lu\n", reps, acc);
    return 0;
}
