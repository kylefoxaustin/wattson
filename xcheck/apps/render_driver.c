/* soft-render pack: classic embedded/demoscene pixel workloads rendered into a
 * memory framebuffer (RGBA), FNV-checksummed. Real pixel pushing, no display
 * needed for activity purposes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#define W 640
#define H 480
static uint32_t fb[W*H];
static uint64_t fnv = 0xcbf29ce484222325ULL;
static void sum(void){ for (int i = 0; i < W*H; i++){ fnv ^= fb[i]; fnv *= 0x100000001b3ULL; } }
int main(int argc, char **argv) {
    int frames = argc > 2 ? atoi(argv[2]) : 30;
    if (!strcmp(argv[1], "mandel")) {
        for (int f = 0; f < frames; f++) {
            double cx = -0.7 + f*0.001, zoom = 1.0 + f*0.05;
            for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
                double zr = 0, zi = 0, cr = cx + (x-W/2)/(200.0*zoom), ci = (y-H/2)/(200.0*zoom);
                int it = 0;
                while (it < 64 && zr*zr+zi*zi < 4) { double t = zr*zr-zi*zi+cr; zi = 2*zr*zi+ci; zr = t; it++; }
                fb[y*W+x] = 0xFF000000 | (it*4 << 16) | (it*2 << 8) | it;
            }
            sum();
        }
    } else if (!strcmp(argv[1], "plasma")) {
        for (int f = 0; f < frames; f++) {
            for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
                int v = (int)(128 + 127*sin(x*0.04+f*0.1) + 128 + 127*sin(y*0.03-f*0.07) +
                              128 + 127*sin((x+y)*0.02+f*0.05)) / 3;
                fb[y*W+x] = 0xFF000000 | (v << 16) | ((255-v) << 8) | ((v*3) & 255);
            }
            sum();
        }
    } else if (!strcmp(argv[1], "ray")) {
        for (int f = 0; f < frames; f++) {
            double lx = cos(f*0.2), ly = -0.7, lz = sin(f*0.2);
            for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
                double dx = (x-W/2)/240.0, dy = (y-H/2)/240.0, dz = 1.0;
                double n = sqrt(dx*dx+dy*dy+dz*dz); dx/=n; dy/=n; dz/=n;
                /* sphere at (0,0,4) r=1.5; plane y=1.5 */
                double b = -(dz*4.0)* -1.0; double ocx=0, ocy=0, ocz=-4.0;
                double bq = dx*ocx+dy*ocy+dz*ocz, cq = ocx*ocx+ocy*ocy+ocz*ocz - 2.25;
                double disc = bq*bq - cq; int v = 16;
                if (disc > 0) {
                    double t = -bq - sqrt(disc);
                    if (t > 0) {
                        double px = dx*t, py = dy*t, pz = dz*t;
                        double nx = px, ny = py, nz = pz+4.0; double nn = sqrt(nx*nx+ny*ny+nz*nz);
                        double d = (nx*lx+ny*ly+nz*lz)/nn; if (d < 0) d = 0;
                        v = 40 + (int)(d*200);
                    }
                } else if (dy > 0.12) {
                    double t = 1.5/dy; int cxi = (int)(dx*t*2+100), czi = (int)(2.0*t/1);
                    v = ((cxi ^ czi) & 1) ? 90 : 50;
                }
                (void)b; fb[y*W+x] = 0xFF000000 | (v << 16) | (v << 8) | v;
            }
            sum();
        }
    } else if (!strcmp(argv[1], "life")) {
        static uint8_t g[2][H][W]; uint64_t s = 0x5EED;
        for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) { s ^= s<<13; s ^= s>>7; s ^= s<<17; g[0][y][x] = s & 1; }
        int cur = 0;
        for (int f = 0; f < frames; f++) {
            for (int y = 1; y < H-1; y++) for (int x = 1; x < W-1; x++) {
                int nb = g[cur][y-1][x-1]+g[cur][y-1][x]+g[cur][y-1][x+1]+g[cur][y][x-1]+g[cur][y][x+1]+g[cur][y+1][x-1]+g[cur][y+1][x]+g[cur][y+1][x+1];
                g[1-cur][y][x] = (nb == 3) || (g[cur][y][x] && nb == 2);
                fb[y*W+x] = g[1-cur][y][x] ? 0xFF00FF66 : 0xFF101018;
            }
            cur = 1-cur; sum();
        }
    } else return 1;
    printf("%s frames=%d fnv=0x%016llx\n", argv[1], frames, (unsigned long long)fnv);
    return 0;
}
