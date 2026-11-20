#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""High-current copper of the Nexus Docks Board, laid by script (F6 step 3).

  scripts/pcbgen/dockboard_preroute.py     (after dockboard_zones.py, before stitch.py)

The paths that carry amperes, drawn on purpose instead of by the router
(docs/calculations.md §2.2: input 3.3 A, fan rail 3 A):

  VIN_RAW    XT30 + -> fuse: 1.6 mm track around the input parts
  +24V_IN    fuse -> RPP FET source pins, TVS, LM74502 sense pins: F.Cu
             polygon; the FET gate pin it surrounds escapes through a via
  +24V_INT   RPP FET drain -> bulk capacitor, 6 vias 0.8/0.4 to the In2 plane
  BUCK_SW    5 V buck: SW pin -> catch diode -> inductor -> BOOT capacitor
  FBK_SW     fan buck: the same
  FAN_BUCK   fan buck inductor -> 3 vias 0.8/0.4 to the B.Cu FAN_BUCK plane
  USB        USB-C pin pairs joined (DM left, DP right of the pads), to U_USBESD
  JP_FRAIL   pin 1 (+24V_INT) via 0.8/0.4 to In2; pin 2 (FAN_RAIL) 1.0 mm
             track between the pads of C_FOUT to 2 vias 0.8/0.4 to the In2
             FAN_RAIL plane; pin 3 (FAN_BUCK) via 0.8/0.4 to the B.Cu plane
  catch diodes  anode pads of D_CATCH / D_FCATCH: GND polygon + 3 vias 0.8/0.4

Coordinates are board mm for the placement of dockboard_place.py
(2026-11-20); the script checks every pad it means to touch.
Polygons: priority 1 (above the step 4 ground pours), clearance 0.2 mm,
solid pad connection.
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
mm = pcbnew.FromMM

ZONES = {
    "+24V_IN": [[(14.25, 42.2), (16.75, 42.2), (16.75, 51.45), (21.7, 51.45), (21.7, 54.3),
                 (19.4, 54.3), (19.4, 53.66), (14.25, 53.66)]],
    "+24V_INT": [[(16.7, 36.3), (18.6, 36.3), (18.6, 39.0), (22.4, 39.0), (22.4, 47.1),
                  (17.1, 47.1), (17.1, 39.0), (16.7, 39.0)]],
    "/logic_power/BUCK_SW": [
        [(24.27, 37.8), (28.3, 37.8), (28.3, 40.2), (24.27, 40.2)],     # C_BOOT pin 2
        [(25.95, 37.8), (28.3, 37.8), (28.3, 41.6), (25.95, 41.6)],     # L_BUCK pin 1
        [(25.95, 41.3), (39.95, 41.3), (39.95, 43.9), (25.95, 43.9)],   # band
        [(31.2, 43.5), (39.95, 43.5), (39.95, 45.13), (31.2, 45.13)]],  # SW pin, D_CATCH
    "/fan_rail/FBK_SW": [
        [(41.25, 14.6), (43.6, 14.6), (43.6, 18.4), (55.25, 18.4), (55.25, 21.91),
         (51.9, 21.91), (51.9, 21.75), (46.5, 21.75), (46.5, 20.7), (41.25, 20.7)],
        [(39.57, 18.4), (41.6, 18.4), (41.6, 20.85), (39.57, 20.85)]],   # C_FBOOT pin 2
    "/fan_rail/FAN_BUCK": [[(47.3, 14.5), (51.0, 14.5), (51.0, 18.0), (47.3, 18.0)]],
    # catch diode anodes (up to 3 A during the off time): solid copper and
    # 3 vias 0.8/0.4 each to the In1 GND plane, on the side away from the SW node
    "GND": [[(51.95, 10.9), (55.25, 10.9), (55.25, 15.11), (51.95, 15.11)],
            [(36.65, 34.4), (39.95, 34.4), (39.95, 38.33), (36.65, 38.33)]],
}
# zone net -> pads (ref, pad) it must touch
TOUCH = {
    "+24V_IN": [("F1", "2"), ("Q1", "1"), ("Q1", "2"), ("Q1", "3"), ("D1", "1"),
                ("U1", "1"), ("U1", "8")],
    "+24V_INT": [("Q1", "5"), ("C3", "1")],
    "/logic_power/BUCK_SW": [("U2", "8"), ("D2", "1"), ("L1", "1"), ("C11", "2")],
    "/fan_rail/FBK_SW": [("U4", "8"), ("D5", "1"), ("L2", "1"), ("C23", "2")],
    "/fan_rail/FAN_BUCK": [("L2", "2")],
    "GND": [("D5", "2"), ("D2", "2")],
}
TRACKS = [  # net, width, points
    ("/power_input/VIN_RAW", 1.6, [(12.2, 45.9), (12.2, 59.0), (20.675, 59.0), (20.675, 56.4)]),
    ("/power_input/RPP_GATE", 0.3, [(15.95, 46.575), (15.95, 47.75)]),
    ("+24V_INT", 0.8, [(49.875, 23.77), (49.875, 22.4)]),
    ("FAN_RAIL", 1.0, [(51.15, 23.77), (51.15, 27.1)]),
    ("/fan_rail/FAN_BUCK", 1.0, [(52.425, 23.77), (52.425, 24.95)]),
    # catch diode anode vias also tied by track (KiCad's via_dangling check
    # does not count the F.Cu polygon alone)
    ("GND", 0.8, [(52.5, 11.85), (54.7, 11.85)]),
    ("GND", 0.8, [(53.6, 11.85), (53.6, 13.86)]),
    ("GND", 0.8, [(37.2, 34.95), (39.4, 34.95)]),
    ("GND", 0.8, [(38.3, 34.95), (38.3, 37.08)]),
    # USB-C: the pins alternate B7 DM, A6 DP, A7 DM, B6 DP. DM pins joined
    # by a loop left of the pads (under the receptacle), DP pins by a loop
    # right of them; then both to the ESD array U_USBESD (DM pin 1, DP pin 3)
    ("USB_DM", 0.2, [(6.2, 16.13), (5.65, 16.13), (5.65, 17.13), (6.2, 17.13)]),
    ("USB_DP", 0.2, [(7.4, 16.63), (8.3, 16.63), (8.3, 17.63), (7.4, 17.63)]),
    ("USB_DM", 0.2, [(7.4, 16.13), (9.0, 16.13), (9.0, 7.85), (11.69, 7.85)]),
    ("USB_DP", 0.2, [(8.3, 16.63), (9.6, 16.63), (9.6, 9.75), (11.69, 9.75)]),
]
VIAS = [  # net, x, y, size, drill
    ("/power_input/RPP_GATE", 15.95, 47.75, 0.6, 0.3),
    ("+24V_INT", 49.875, 22.4, 0.8, 0.4),
    ("FAN_RAIL", 51.15, 26.0, 0.8, 0.4),
    ("FAN_RAIL", 51.15, 27.1, 0.8, 0.4),
] + [("+24V_INT", x, y, 0.8, 0.4) for x in (18.0, 19.4, 20.8) for y in (39.8, 41.2)] \
  + [("/fan_rail/FAN_BUCK", 50.5, y, 0.8, 0.4) for y in (15.0, 16.2, 17.4)] \
  + [("/fan_rail/FAN_BUCK", 52.425, 24.95, 0.8, 0.4)] \
  + [("GND", x, 11.85, 0.8, 0.4) for x in (52.5, 53.6, 54.7)] \
  + [("GND", x, 34.95, 0.8, 0.4) for x in (37.2, 38.3, 39.4)]
# pads a track must start/end on
PADS = {(12.2, 45.9): ("J1", "2"), (20.675, 56.4): ("F1", "1"), (15.95, 46.575): ("Q1", "4"),
        (49.875, 23.77): ("JP2", "1"), (51.15, 23.77): ("JP2", "2"),
        (52.425, 23.77): ("JP2", "3"), (53.6, 13.86): ("D5", "2"), (38.3, 37.08): ("D2", "2"),
        (6.2, 16.13): ("J3", "B7"), (6.2, 17.13): ("J3", "A7"), (7.4, 16.63): ("J3", "A6"),
        (7.4, 17.63): ("J3", "B6"), (7.4, 16.13): ("J3", "B7"), (11.69, 7.85): ("U6", "1"),
        (11.69, 9.75): ("U6", "3")}


def main():
    pcb = ROOT / "dockboard" / "dockboard.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    bb = b.GetBoardEdgesBoundingBox()
    ox, oy = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    P = lambda x, y: pcbnew.VECTOR2I(mm(ox + x), mm(oy + y))
    fps = {f.GetReference(): f for f in b.GetFootprints()}

    def pad(ref, num):
        return [p for p in fps[ref].Pads() if p.GetNumber() == num]

    # the placement this was drawn for
    errors = []
    for net, polys in ZONES.items():
        for ref, num in TOUCH[net]:
            ps = pad(ref, num)
            if not ps or ps[0].GetNetname() != net:
                errors.append(f"{ref}.{num} is not {net}")
                continue
            ok = False
            for poly in polys:
                sp = pcbnew.SHAPE_LINE_CHAIN()
                for x, y in poly:
                    sp.Append(P(x, y))
                sp.SetClosed(True)
                for p_ in ps:                 # pad centre or a bbox corner inside
                    bx = p_.GetBoundingBox()
                    pts = [p_.GetPosition(), bx.GetOrigin(), bx.GetEnd(),
                           pcbnew.VECTOR2I(bx.GetLeft(), bx.GetBottom()),
                           pcbnew.VECTOR2I(bx.GetRight(), bx.GetTop())]
                    if any(sp.PointInside(q, 1) for q in pts):
                        ok = True
            if not ok:
                errors.append(f"{ref}.{num} not inside its {net} polygon")
    for xy, (ref, num) in PADS.items():
        ps = pad(ref, num)
        if not ps or not ps[0].HitTest(P(*xy)):
            errors.append(f"track end {xy} not on {ref}.{num}")
    if errors:
        sys.exit("placement changed:\n  " + "\n  ".join(errors))

    for z in list(b.Zones()):
        if z.GetZoneName().startswith("preroute "):
            b.Delete(z)
    for net, polys in ZONES.items():
        # one zone per net: the union of its polygons (overlapping zones of
        # one net are a DRC error)
        u = pcbnew.SHAPE_POLY_SET()
        for poly in polys:
            q = pcbnew.SHAPE_POLY_SET()
            q.NewOutline()
            for x, y in poly:
                q.Append(P(x, y))
            u.BooleanAdd(q)
        u.Simplify()
        z = pcbnew.ZONE(b)
        z.SetNet(b.FindNet(net))
        z.SetLayer(pcbnew.F_Cu)
        z.SetZoneName(f"preroute {net.split('/')[-1]}")
        z.SetAssignedPriority(1)
        z.SetLocalClearance(mm(0.2))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.Outline().Append(u)
        b.Add(z)
    for net, w, pts in TRACKS:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetWidth(mm(w))
            t.SetLayer(pcbnew.F_Cu); t.SetNet(b.FindNet(net))
            b.Add(t)
    for net, x, y, size, drill in VIAS:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(P(x, y)); v.SetWidth(mm(size)); v.SetDrill(mm(drill))
        v.SetNet(b.FindNet(net))
        b.Add(v)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"preroute: {sum(len(p) for p in ZONES.values())} polygons, "
          f"{sum(len(t[2]) - 1 for t in TRACKS)} tracks, {len(VIAS)} vias")


if __name__ == "__main__":
    main()
