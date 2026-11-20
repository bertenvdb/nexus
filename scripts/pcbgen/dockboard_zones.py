#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Power and ground planes of the Nexus Docks Board (F6 step 2).

  scripts/pcbgen/dockboard_zones.py      (after dockboard_place.py)

Stackup: F.Cu signals + parts, In1 solid GND plane, In2 power planes +
signals, B.Cu signals. The dock board carries at most 3.3 A (input) and
3 A (fan rail) (docs/calculations.md §2.2), so the outer-layer power paths
are tracks of >= 1.6 mm (net class POWER_IN) laid by the router, not
polygons: on this dense placement an F.Cu polygon would enclose pads of
other nets (Q1 gate, U1 pins). The planes:

  In1  GND over the whole board (no AGND on the dock board).
  In2  +24V_INT under the power input and the 5 V buck (bottom left) and
       under the fan buck (top middle); the two are joined by a routed
       track (the fan buck draws <= 1.7 A from 24 V).
       FAN_RAIL under the 3 x 3 fan grid (the THT connector pins land on
       it directly) with a band to the rail jumper JP_FRAIL, C_FRAIL and
       TP_FRAIL.
  B.Cu FAN_BUCK under the fan buck (inductor -> output capacitors -> JP_FRAIL
       pin 3, F6 step 3).
The MCU escape ring (MCU_KEEP) stays free on In2.

Zones are separated by >= 0.5 mm, so no priorities are needed. THT pads
get thermal reliefs (hand-soldered connectors), SMD pads and vias solid.
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
mm = pcbnew.FromMM
W, H = 88.0, 62.0


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def box(b, ref):
    fp = next(f for f in b.GetFootprints() if f.GetReference() == ref)
    c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    return (pcbnew.ToMM(c.GetLeft()), pcbnew.ToMM(c.GetTop()),
            pcbnew.ToMM(c.GetRight()), pcbnew.ToMM(c.GetBottom()))


def main():
    pcb = ROOT / "dockboard" / "dockboard.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    bb = b.GetBoardEdgesBoundingBox()
    ox, oy = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    for z in list(b.Zones()):
        b.Delete(z)
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)    # GND plane only
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_SIGNAL)   # power planes + signals

    def zone(net, layer, pts, name):
        z = pcbnew.ZONE(b)
        z.SetNet(b.FindNet(net))
        z.SetLayer(layer)
        z.SetZoneName(name)
        z.SetAssignedPriority(0)
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.6))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(mm(ox + x), mm(oy + y))
        b.Add(z)
        return z

    # MCU escape ring and the fan grid, from the placement
    u = box(b, "U5")
    ring = (u[0] - ox - 3.6, u[1] - oy - 3.6, u[2] - ox + 3.6, u[3] - oy + 3.6)
    js = [box(b, f"J{i}") for i in range(6, 15)]          # J6..J14 = FAN 0..8
    qs = [box(b, f"Q{i}") for i in range(2, 11)]
    gx0 = min(j[0] for j in js) - ox - 0.3
    gy0 = min(j[1] for j in js) - oy - 0.3
    gy1 = max(q[3] for q in qs) - oy + 0.3
    G = 0.5                                               # gap between planes

    zone("GND", pcbnew.In1_Cu, rect(0, 0, W, H), "GND plane")

    # +24V_INT, bottom left: power input, bulk, 5 V buck (below the MCU ring)
    zone("+24V_INT", pcbnew.In2_Cu, rect(14.6, ring[3] + G, 41.5, H - 0.6),
         "24V_INT power")
    # +24V_INT, top middle: fan buck input (U_FBUCK, C_FIN*)
    fx0 = ring[2] + G
    #   (down to y 23 so the via above JP_FRAIL pin 1 lands on it)
    zone("+24V_INT", pcbnew.In2_Cu,
         [(fx0, 11.8), (gx0 - G, 11.8), (gx0 - G, 28.0), (53.5, 28.0), (53.5, 23.0),
          (fx0, 23.0)], "24V_INT fan buck")
    # FAN_RAIL: fan grid + band to JP_FRAIL / C_FRAIL / TP_FRAIL, with a tab
    # up to the two vias below JP_FRAIL pin 2 (between the pads of C_FOUT)
    zone("FAN_RAIL", pcbnew.In2_Cu,
         [(gx0, gy0), (W - 0.6, gy0), (W - 0.6, gy1), (gx0, gy1), (gx0, 35.0),
          (fx0, 35.0), (fx0, 28.0 + G), (50.3, 28.0 + G), (50.3, 25.0), (52.9, 25.0),
          (52.9, 28.0 + G), (gx0, 28.0 + G)], "fan rail")
    # FAN_BUCK (fan buck output, <= 3 A) on B.Cu under the fan buck: on F.Cu
    # it would have to cross the switch node between U_FBUCK and D_FCATCH
    #   with a notch below the U_FBUCK FB/COMP pins: their tracks to the
    #   compensation network (R_FCOMP, C_FCOMP2) need a way past C_FOUT
    zone("/fan_rail/FAN_BUCK", pcbnew.B_Cu,
         [(fx0, 14.3), (58.6, 14.3), (58.6, 31.0), (48.5, 31.0), (48.5, 22.3), (46.3, 22.3),
          (46.3, 31.0), (fx0, 31.0)], "fan buck out")

    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    for z in b.Zones():
        a = z.GetFilledPolysList(z.GetFirstLayer()).Area() / 1e12
        print(f"{z.GetZoneName():18s} {z.GetNetname():10s} {b.GetLayerName(z.GetFirstLayer()):6s} {a:7.1f} mm2")


if __name__ == "__main__":
    sys.exit(main())
