#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Connect plane-net pads that the router left floating (F5 step 3).

  scripts/pcbgen/stitch.py toolboard [NET ...]     (default: GND AGND)

For every SMD pad of a plane net whose copper island holds no zone, try via
positions on rings around the pad and take the first one where the via and a
short track from the pad clear all other-net copper (board clearance + 0.05
mm) and the via lands inside a filled zone of that net on an inner layer
(or on B.Cu: the dock board's FAN_BUCK plane).
Prints the pads it could not stitch.
"""
import math
import os
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
VIA, DRILL, TRACK = 0.6, 0.3, 0.3
CLEAR = 0.25            # 0.2 board clearance + margin
mm = pcbnew.FromMM


def main():
    board = sys.argv[1]
    nets = sys.argv[2:] or ["GND", "AGND"]
    pcb = ROOT / board / f"{board}.kicad_pcb"
    b = pcbnew.LoadBoard(str(pcb))
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    cu = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    edge = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]

    def obstacles(netcode):
        out = []
        for t in b.GetTracks():
            if t.GetNetCode() != netcode:
                out.append(t)
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetCode() != netcode:
                    out.append(p)
        # zones on the inner layers refill around a new via; only outer-layer
        # zones (trunk, heater band) block. STITCH_B_PLANE=1: a B.Cu zone is a
        # plane that refills around vias too (dock board FAN_BUCK)
        outer = (pcbnew.F_Cu,) if os.environ.get("STITCH_B_PLANE") else (pcbnew.F_Cu, pcbnew.B_Cu)
        for z in b.Zones():
            if (z.GetNetCode() != netcode and not z.GetIsRuleArea()
                    and any(z.IsOnLayer(L) for L in outer)):
                out.append(z)
        return out

    def hits(shape, layers, obs):
        for o in obs:
            for L in layers:
                if not o.IsOnLayer(L):
                    continue
                if o.GetClass() == "ZONE":
                    if L not in (pcbnew.F_Cu, pcbnew.B_Cu):
                        continue
                    fill = o.GetFilledPolysList(L)
                    if fill.Collide(shape, mm(CLEAR)):
                        return True
                elif o.GetEffectiveShape(L).Collide(shape, mm(CLEAR)):
                    return True
        return False

    def in_plane(netcode, pos):
        # the whole via pad (plus margin) must lie inside the filled plane
        r = mm(VIA / 2 + 0.15)
        pts = [pos] + [pos + pcbnew.VECTOR2I(int(r * math.cos(a)), int(r * math.sin(a)))
                       for a in [k * math.pi / 4 for k in range(8)]]
        for z in b.Zones():
            if z.GetNetCode() != netcode:
                continue
            for L in (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                if z.IsOnLayer(L) and all(z.GetFilledPolysList(L).Contains(q) for q in pts):
                    return True
        return False

    done, failed, mine = 0, [], []
    for name in nets:
        net = b.FindNet(name)
        obs = obstacles(net.GetNetCode())
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetCode() != net.GetNetCode() or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                    continue
                if any(i.GetClass() in ("ZONE", "PCB_VIA") for i in conn.GetConnectedItems(p)):
                    continue
                layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
                c = p.GetPosition()
                placed = False
                for r in (0.9, 1.1, 1.3, 1.6, 2.0, 2.5, 3.0):
                    for k in range(24):
                        a = 2 * math.pi * k / 24
                        v = pcbnew.VECTOR2I(c.x + int(mm(r) * math.cos(a)), c.y + int(mm(r) * math.sin(a)))
                        if not in_plane(net.GetNetCode(), v):
                            continue
                        via_s = pcbnew.SHAPE_CIRCLE(v, mm(VIA / 2))
                        if hits(via_s, cu, obs):
                            continue
                        if any((v - m).EuclideanNorm() < mm(VIA + 0.3) for m in mine):
                            continue
                        if any(e.GetEffectiveShape().Collide(via_s, mm(0.5)) for e in edge):
                            continue
                        seg = pcbnew.SHAPE_SEGMENT(c, v, mm(TRACK))
                        if hits(seg, [layer], obs):
                            continue
                        t = pcbnew.PCB_TRACK(b)
                        t.SetStart(c); t.SetEnd(v); t.SetWidth(mm(TRACK))
                        t.SetLayer(layer); t.SetNet(net)
                        b.Add(t)
                        via = pcbnew.PCB_VIA(b)
                        via.SetPosition(v); via.SetWidth(mm(VIA)); via.SetDrill(mm(DRILL))
                        via.SetNet(net)
                        b.Add(via)
                        mine.append(v)
                        placed = True
                        break
                    if placed:
                        break
                if placed:
                    done += 1
                else:
                    failed.append(f"{fp.GetReference()}-{p.GetNumber()} [{name}]")
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"stitched {done} pads; not stitched: {', '.join(failed) or 'none'}")


if __name__ == "__main__":
    main()
