/* xcheck net2: plain BLOCKING HTTP GET + FNV hash. No event loop, no poll --
 * instruction count is dominated by bytes processed, not by timing. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
int main(int argc, char **argv) {
    const char *ip = argc > 1 ? argv[1] : "127.0.0.1";
    int port = argc > 2 ? atoi(argv[2]) : 18930;
    int reps = argc > 3 ? atoi(argv[3]) : 8;
    uint64_t fnv = 0xcbf29ce484222325ULL; long total = 0;
    static char buf[65536];
    for (int r = 0; r < reps; r++) {
        int s = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in a = {0};
        a.sin_family = AF_INET; a.sin_port = htons(port);
        inet_pton(AF_INET, ip, &a.sin_addr);
        if (connect(s, (struct sockaddr *)&a, sizeof a)) { perror("connect"); return 2; }
        dprintf(s, "GET /data.bin HTTP/1.0\r\nHost: x\r\n\r\n");
        ssize_t n;
        while ((n = read(s, buf, sizeof buf)) > 0) {
            for (ssize_t i = 0; i < n; i++) { fnv ^= (unsigned char)buf[i]; fnv *= 0x100000001b3ULL; }
            total += n;
        }
        close(s);
    }
    printf("net2 reps=%d bytes=%ld fnv=0x%016llx\n", reps, total, (unsigned long long)fnv);
    return 0;
}
