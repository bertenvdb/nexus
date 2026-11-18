#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Placement quality estimate: ratsnest length and ratsnest crossings.

  scripts/pcbgen/placement_score.py <board.kicad_pcb> [...]

Per net a minimum spanning tree over its pads (plane nets left out: they
connect through zones). Prints total MST length, the number of crossing MST
edge pairs (a rough measure of how hard the board is to route) and the nets
with the longest trees.
"""
import itertools
import math
import sys

import pcbnew

PLANE = {"GND", "AGND", "+24V_IN", "+24V_HEATER", "/power_input/VIN_RAW",
         "/heater_cutoff/CUTOFF_SRC"}


def mst(pts):
    if len(pts) < 2:
        return []
    inside, edges = {0}, []
    best = {i: (math.dist(pts[0], pts[i]), 0) for i in range(1, len(pts))}
    while best:
        j = min(best, key=lambda k: best[k][0])
        d, i = best.pop(j)
        edges.append((pts[i], pts[j]))
        inside.add(j)
        for k in best:
            dk = math.dist(pts[j], pts[k])
            if dk < best[k][0]:
                best[k] = (dk, j)
    return edges


def cross(a, b):
    (p1, p2), (p3, p4) = a, b
    if {p1, p2} & {p3, p4}:
        return False
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(p1, p2, p3) * o(p1, p2, p4) < 0) and (o(p3, p4, p1) * o(p3, p4, p2) < 0)


def score(path):
    b = pcbnew.LoadBoard(path)
    nets = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            n = p.GetNetname()
            if not n or n in PLANE or n.startswith("unconnected"):
                continue
            q = p.GetPosition()
            nets.setdefault(n, []).append((pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)))
    edges, per = [], {}
    for n, pts in nets.items():
        e = mst(sorted(set(pts)))
        edges += e
        per[n] = sum(math.dist(*x) for x in e)
    total = sum(per.values())
    # crossings: bucket by bounding box to keep it fast
    crossings = sum(1 for a, c in itertools.combinations(edges, 2)
                    if max(a[0][0], a[1][0]) >= min(c[0][0], c[1][0])
                    and max(c[0][0], c[1][0]) >= min(a[0][0], a[1][0])
                    and max(a[0][1], a[1][1]) >= min(c[0][1], c[1][1])
                    and max(c[0][1], c[1][1]) >= min(a[0][1], a[1][1])
                    and cross(a, c))
    return total, crossings, sorted(per.items(), key=lambda x: -x[1])[:8]


if __name__ == "__main__":
    for path in sys.argv[1:]:
        t, c, top = score(path)
        print(f"{path}: length {t:.0f} mm, crossings {c}")
        print("   longest: " + ", ".join(f"{n.split('/')[-1]} {l:.0f}" for n, l in top))
