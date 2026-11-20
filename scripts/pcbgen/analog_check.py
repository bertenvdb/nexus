#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coupling check of the analog traces (F5 step 4).

  scripts/pcbgen/analog_check.py <board.kicad_pcb>

For every analog track (THERM_*, the thermistor sub-nets, VREF_A, RAIL_SENSE)
the length that runs within 0.5 mm and within 1.0 mm (copper edge to copper
edge) of a switching net: the buck switch node and bootstrap, heater drains,
gates, gate-buffer inputs and the cutoff gate. Same layer, and the coupled
layer pair In2/B.Cu (0.2 mm prepreg apart). F.Cu sits over the solid In1
plane, so F.Cu over In2 does not count. Sampled every 0.1 mm.
"""
import re
import sys

import numpy as np
import pcbnew

ANALOG = re.compile(r"^(THERM_T\d|/thermistors/THERM_T\d_.*|VREF_A|RAIL_SENSE)$")
AGGR = re.compile(r"^(/logic_power/BUCK_(SW|BOOT)|HEATER_T\d_(N|CTRL)|/heaters/GATE_T\d(_B)?|/heater_cutoff/CUTOFF_GATE)$")
COUPLED = {pcbnew.F_Cu: [pcbnew.F_Cu], pcbnew.In2_Cu: [pcbnew.In2_Cu, pcbnew.B_Cu],
           pcbnew.B_Cu: [pcbnew.B_Cu, pcbnew.In2_Cu]}
mm = pcbnew.ToMM


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, ab)), axis=1)


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    aggr = {}   # layer -> list of (a, b, half width)
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and AGGR.match(t.GetNetname()):
            aggr.setdefault(t.GetLayer(), []).append((
                np.array([mm(t.GetStart().x), mm(t.GetStart().y)]),
                np.array([mm(t.GetEnd().x), mm(t.GetEnd().y)]), mm(t.GetWidth()) / 2))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if not AGGR.match(p.GetNetname()):
                continue
            c = np.array([mm(p.GetPosition().x), mm(p.GetPosition().y)])
            r = min(mm(p.GetBoundingBox().GetWidth()), mm(p.GetBoundingBox().GetHeight())) / 2
            for L in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(L):
                    aggr.setdefault(L, []).append((c, c, r))
    res = {}
    for t in b.GetTracks():
        n = t.GetNetname()
        if t.GetClass() != "PCB_TRACK" or not ANALOG.match(n):
            continue
        a = np.array([mm(t.GetStart().x), mm(t.GetStart().y)])
        e = np.array([mm(t.GetEnd().x), mm(t.GetEnd().y)])
        ln = np.linalg.norm(e - a)
        k = max(int(ln / 0.1), 1)
        pts = a + np.outer(np.linspace(0, 1, k + 1), e - a)
        d = np.full(len(pts), 1e9)
        for L in COUPLED.get(t.GetLayer(), []):
            for sa, sb, hw in aggr.get(L, []):
                d = np.minimum(d, seg_dist(pts, sa, sb) - hw - mm(t.GetWidth()) / 2)
        step = ln / k
        r = res.setdefault(n, [0.0, 0.0, 9e9])
        r[0] += step * (d[:-1] < 0.5).sum()
        r[1] += step * (d[:-1] < 1.0).sum()
        r[2] = min(r[2], d.min())
    print(f"{'net':28s} {'<0.5mm':>8s} {'<1.0mm':>8s} {'min gap':>8s}")
    for n, (a5, a10, dm) in sorted(res.items(), key=lambda x: -x[1][1]):
        print(f"{n.split('/')[-1]:28s} {a5:8.1f} {a10:8.1f} {dm:8.2f}")


if __name__ == "__main__":
    main()
