// SPDX-License-Identifier: GPL-3.0-or-later
// Fast kernels for scripts/pcbgen/negotiate.py (compiled on first use into out/).
//
// astar(): A* over (layer, row, col) on the routing grid with a per-cell cost
//   multiplier and additive congestion cost (PathFinder), turn cost via the
//   direction of best arrival, preferred layer directions and vias.
// paint(): add `delta` to an occupancy map in discs around copper centre
//   cells, counting every cell at most once per call (one net = one count).
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static float *best;
static int32_t *prev, *seen;
static uint8_t *dirv, *closed_;
static int32_t gen;
static size_t cap;

typedef struct { float f; int32_t i; } HE;
static HE *heap;
static size_t hn, hcap;

static void hpush(float f, int32_t i) {
    if (hn == hcap) { hcap = hcap ? hcap * 2 : 1 << 16; heap = realloc(heap, hcap * sizeof(HE)); }
    size_t k = hn++;
    while (k) { size_t p = (k - 1) / 2; if (heap[p].f <= f) break; heap[k] = heap[p]; k = p; }
    heap[k].f = f; heap[k].i = i;
}
static HE hpop(void) {
    HE top = heap[0], last = heap[--hn];
    size_t k = 0;
    for (;;) {
        size_t c = 2 * k + 1;
        if (c >= hn) break;
        if (c + 1 < hn && heap[c + 1].f < heap[c].f) c++;
        if (heap[c].f >= last.f) break;
        heap[k] = heap[c]; k = c;
    }
    if (hn) heap[k] = last;
    return top;
}

static void ensure(size_t n) {
    if (n <= cap) return;
    free(best); free(prev); free(seen); free(dirv); free(closed_);
    best = malloc(n * sizeof(float)); prev = malloc(n * sizeof(int32_t));
    seen = calloc(n, sizeof(int32_t)); dirv = malloc(n); closed_ = malloc(n);
    cap = n; gen = 0;
}

// returns path length written to out (flat indices, source -> target) or -1
int astar(int L, int NY, int NX,
          const uint8_t *hard, const uint8_t *src, const uint8_t *tgt,
          const uint8_t *vb, const float *mult, const float *add,
          const float *vcost, const uint8_t *penh, const uint8_t *penv,
          int layers_mask, const float *layer_cost, const int *dirpref,
          float dir_pen, float turn_cost, int max_expand,
          int32_t *out, int outcap) {
    size_t plane = (size_t)NY * NX, n = plane * L;
    ensure(n);
    if (++gen == 0x7fffffff) { memset(seen, 0, n * sizeof(int32_t)); gen = 1; }
    // target centroid and spread for the heuristic
    double sy = 0, sx = 0; long cnt = 0; int ymin = NY, ymax = -1, xmin = NX, xmax = -1;
    for (size_t i = 0; i < n; i++) if (tgt[i]) {
        int r = (i % plane) / NX, c = i % NX;
        sy += r; sx += c; cnt++;
        if (r < ymin) ymin = r; if (r > ymax) ymax = r;
        if (c < xmin) xmin = c; if (c > xmax) xmax = c;
    }
    if (!cnt) return -1;
    double ty = sy / cnt, tx = sx / cnt;
    double spread = ((ymax - ymin) > (xmax - xmin) ? (ymax - ymin) : (xmax - xmin)) / 2.0;
    #define H(r, c) ({ double dy = fabs((r) - ty), dx = fabs((c) - tx); \
        double hh = (dy > dx ? dy : dx) + 0.414 * (dy < dx ? dy : dx) - spread; hh > 0 ? hh : 0; })
    hn = 0;
    for (size_t i = 0; i < n; i++) if (src[i] && (layers_mask >> (i / plane) & 1)) {
        seen[i] = gen; best[i] = 0; prev[i] = -1; dirv[i] = 8; closed_[i] = 0;
        hpush((float)H((double)((i % plane) / NX), (double)(i % NX)), (int32_t)i);
    }
    static const int dr[8] = {-1, 1, 0, 0, -1, -1, 1, 1};
    static const int dc[8] = {0, 0, -1, 1, -1, 1, -1, 1};
    static const float dk[8] = {1, 1, 1, 1, 1.41421f, 1.41421f, 1.41421f, 1.41421f};
    int expanded = 0;
    while (hn) {
        HE e = hpop();
        int32_t i = e.i;
        if (closed_[i]) continue;
        closed_[i] = 1;
        int li = i / plane, r = (i % plane) / NX, c = i % NX;
        if (tgt[i]) {
            int k = 0;
            for (int32_t j = i; j >= 0; j = prev[j]) { if (k >= outcap) return -2; out[k++] = j; }
            for (int a = 0, b = k - 1; a < b; a++, b--) { int32_t t = out[a]; out[a] = out[b]; out[b] = t; }
            return k;
        }
        if (++expanded > max_expand) return -1;
        float cost = best[i];
        int d = dirv[i];
        int here_src = src[i];
        for (int di = 0; di < 8; di++) {
            int rr = r + dr[di], cc = c + dc[di];
            if (rr < 0 || rr >= NY || cc < 0 || cc >= NX) continue;
            size_t j = (size_t)li * plane + (size_t)rr * NX + cc;
            if (hard[j]) continue;
            if (src[j] && !here_src) continue;
            if (li == 0 && ((dr[di] == 0 && penh[(size_t)rr * NX + cc]) ||
                            (dc[di] == 0 && penv[(size_t)rr * NX + cc]))) continue;
            float k = dk[di];
            if ((dirpref[li] == 1 && dr[di] != 0) || (dirpref[li] == 2 && dc[di] != 0)) k *= dir_pen;
            float nc = cost + k * layer_cost[li] * mult[j] + add[j] * dk[di]
                       + ((d != 8 && d != di) ? turn_cost : 0);
            if (seen[j] != gen) { seen[j] = gen; best[j] = 1e30f; closed_[j] = 0; }
            if (!closed_[j] && nc < best[j]) {
                best[j] = nc; prev[j] = i; dirv[j] = di;
                hpush(nc + (float)H((double)rr, (double)cc), (int32_t)j);
            }
        }
        size_t pc = (size_t)r * NX + c;
        if (!vb[pc]) {
            for (int l2 = 0; l2 < L; l2++) {
                if (l2 == li || !(layers_mask >> l2 & 1)) continue;
                size_t j = (size_t)l2 * plane + pc;
                if (hard[j]) continue;
                float nc = cost + vcost[pc];
                if (seen[j] != gen) { seen[j] = gen; best[j] = 1e30f; closed_[j] = 0; }
                if (!closed_[j] && nc < best[j]) {
                    best[j] = nc; prev[j] = i; dirv[j] = 8;
                    hpush(nc + (float)H((double)r, (double)c), (int32_t)j);
                }
            }
        }
    }
    return -1;
}

// occ: int16 [L*NY*NX]; mark: int32 scratch of the same size; entries
// (layer, row, col, radius in cells). Each covered cell gets +delta once.
void paint(int L, int NY, int NX, int16_t *occ, int32_t *mark, int32_t stamp,
           int n, const int32_t *li, const int32_t *row, const int32_t *col,
           const float *rad, int delta) {
    size_t plane = (size_t)NY * NX;
    for (int e = 0; e < n; e++) {
        int R = (int)ceilf(rad[e]);
        float r2 = rad[e] * rad[e];
        for (int dy = -R; dy <= R; dy++) {
            int rr = row[e] + dy;
            if (rr < 0 || rr >= NY) continue;
            for (int dx = -R; dx <= R; dx++) {
                if (dy * dy + dx * dx > r2) continue;
                int cc = col[e] + dx;
                if (cc < 0 || cc >= NX) continue;
                size_t j = (size_t)li[e] * plane + (size_t)rr * NX + cc;
                if (mark[j] == stamp) continue;
                mark[j] = stamp;
                occ[j] += delta;
            }
        }
    }
    (void)L;
}
