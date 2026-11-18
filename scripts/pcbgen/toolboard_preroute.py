#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scripted routing of the regular parts of the tool board (F5 step 3a).

Always starts from toolboard/toolboard.placed.kicad_pcb (placement + zones,
no tracks) and writes toolboard/toolboard.kicad_pcb. Per heater channel:
  P   fuse pad 2 -> terminal pin 1, 2 mm, F.Cu
  N   MOSFET drain -> terminal pin 2, 2 mm, F.Cu
  S   source pins tied, 2 vias 0.8/0.4 to the In1 GND plane
  G   gate -> pull-down -> 22R on one vertical line (22R turned 180 deg)
  G_B 22R -> via -> B.Cu stub under the heater rail band (Freerouting
      continues to the buffer)
  LED R_LH turned so +24V is on top (short to the band); LED cathode via
      B.Cu to the N track
plus GND vias for the rail capacitors in the band and two placement
fixes (rail capacitors 2/4, SWD header), plus In2 supply strips for
VCC_FIL, +3V3_MCU and VREF_A. The rest is routed by
Freerouting (scripts/pcbgen/route.py).
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "schgen"))
import toolboard as sch  # noqa: E402

O = 40.0
mm = pcbnew.FromMM


def main():
    b_sch = sch.build()
    b_sch.annotate()
    K = {p.key: p.ref for s in b_sch.sheets for p in s.parts}
    src = ROOT / "toolboard" / "toolboard.placed.kicad_pcb"
    dst = ROOT / "toolboard" / "toolboard.kicad_pcb"
    brd = pcbnew.LoadBoard(str(src))

    def P(x, y):
        return pcbnew.VECTOR2I(mm(O + x), mm(O + y))

    def pad(key, num):
        fp = brd.FindFootprintByReference(K[key])
        ps = [p for p in fp.Pads() if p.GetNumber() == num]
        q = ps[0].GetPosition()
        return pcbnew.ToMM(q.x) - O, pcbnew.ToMM(q.y) - O, ps[0].GetNetname()

    def track(net, layer, pts, w):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(brd)
            t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1))
            t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(brd.FindNet(net))
            brd.Add(t)

    def via(net, x, y, size=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(brd)
        v.SetPosition(P(x, y)); v.SetWidth(mm(size)); v.SetDrill(mm(drill))
        v.SetNet(brd.FindNet(net))
        brd.Add(v)

    F, B = pcbnew.F_Cu, pcbnew.B_Cu

    # B.Cu part of the heater feed zone narrowed: it blocked the gate stubs
    for z in brd.Zones():
        if z.GetLayer() == B and z.GetNetname() == "+24V_HEATER":
            ol = z.Outline()
            ol.RemoveAllContours()
            ol.NewOutline()
            for x, y in [(34.6, 49.6), (41.5, 49.6), (41.5, 58.8), (34.6, 58.8)]:
                ol.Append(mm(O + x), mm(O + y))

    # In2 supply strips (2026-11-18): the longest ratsnest trees were supply
    # nets; as strips on In2 they leave the router (643 -> ~470 crossings)
    # while the middle of In2 stays free for signals
    def zone(net, layer, pts, name):
        z = pcbnew.ZONE(brd)
        z.SetNet(brd.FindNet(net)); z.SetLayer(layer); z.SetAssignedPriority(2)
        z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetZoneName(name)
        ol = z.Outline(); ol.NewOutline()
        for x, y in pts:
            ol.Append(mm(O + x), mm(O + y))
        brd.Add(z)
    rect = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    I2 = pcbnew.In2_Cu
    zone("/filament_inputs/VCC_FIL", I2, rect(10.5, 0.6, 129.5, 6.4), "VCC_FIL strip")
    zone("+3V3_MCU", I2, rect(10.5, 6.9, 129.5, 13.8), "3V3 strip")
    zone("VREF_A", I2, rect(110.6, 23.5, 132.0, 79.0), "VREF_A strip")

    for i in range(8):
        # orientation fixes (see docstring)
        brd.FindFootprintByReference(K[f"R_G{i}"]).SetOrientationDegrees(180)
        brd.FindFootprintByReference(K[f"R_LH{i}"]).SetOrientationDegrees(270)

        fx, fy, pnet = pad(f"F_H{i}", "2")
        jx1, jy1, _ = pad(f"J_H{i}", "1")
        jx2, jy2, nnet = pad(f"J_H{i}", "2")
        track(pnet, F, [(fx, fy), (jx1, jy1)], 2.0)                       # P
        dx = pad(f"Q_H{i}", "5")[0]
        track(nnet, F, [(jx2, 73.53), (jx2, jy2)], 2.0)                    # N
        s1 = pad(f"Q_H{i}", "1"); s3 = pad(f"Q_H{i}", "3")
        vx = s1[0] + 1.35
        track("GND", F, [(s3[0], s3[1]), (vx, s1[1])], 0.4)                # S row
        track("GND", F, [(vx, 69.95), (vx, 71.15)], 0.6)
        via("GND", vx, 69.95, 0.8, 0.4)
        via("GND", vx, 71.15, 0.8, 0.4)
        gx, gy, gnet = pad(f"Q_H{i}", "4")
        pd1 = pad(f"R_GPD{i}", "1"); pd2 = pad(f"R_GPD{i}", "2")
        rg2 = pad(f"R_G{i}", "2"); rg1 = pad(f"R_G{i}", "1")
        track(gnet, F, [(gx, gy), (gx, gy - 0.6), (pd1[0], pd1[1])], 0.3)  # gate
        track(gnet, F, [(pd1[0], pd1[1]), (rg2[0], rg2[1])], 0.3)
        track("GND", F, [(pd2[0], pd2[1]), (s1[0], s1[1])], 0.3)           # pull-down GND
        bx, by, bnet = rg1
        via(bnet, bx, 66.0)
        track(bnet, F, [(bx, by), (bx, 66.0)], 0.3)
        if i == 0:   # around the VIN_RAW copper on B.Cu
            track(bnet, B, [(bx, 66.0), (24.2, 65.6), (24.2, 58.0)], 0.3)
        else:
            track(bnet, B, [(bx, 66.0), (bx, 58.0)], 0.3)
        r1 = pad(f"R_LH{i}", "1"); r2 = pad(f"R_LH{i}", "2")
        a = pad(f"D_LH{i}", "2"); k = pad(f"D_LH{i}", "1")
        track("+24V_HEATER", F, [(r1[0], r1[1]), (r1[0], 64.9)], 0.3)     # into the band
        track(r2[2], F, [(r2[0], r2[1]), (a[0], a[1])], 0.3)
        via(nnet, k[0], 76.5)
        track(nnet, F, [(k[0], k[1]), (k[0], 76.5)], 0.3)
        track(nnet, B, [(k[0], 76.5), (jx2, 76.5)], 0.3)
        via(nnet, jx2, 76.5)

    # rail capacitors 2 and 4 sat too close to channel fuses 4 and 7: move them
    # between two channels (x 65.3 and 99.0), clear of the band stitching vias
    for key, x in (("C_RAIL2", 65.3), ("C_RAIL4", 99.0)):
        fp = brd.FindFootprintByReference(K[key])
        fp.SetPosition(P(x, pcbnew.ToMM(fp.GetPosition().y) - O))
    # SWD header sat across the In1 AGND finger (island -> MCU VREF): its THT
    # pads cut the 3.5 mm finger, so the part towards the MCU was not filled
    j2 = brd.FindFootprintByReference(K["J_SWD"])
    j2.SetPosition(j2.GetPosition() + pcbnew.VECTOR2I(0, mm(-6.0)))
    for i in range(4):   # rail capacitors in the band: GND via below pad 2
        x, y, _ = pad(f"C_RAIL{i + 1}", "2")
        track("GND", F, [(x, y), (x, y + 1.4)], 0.5)
        via("GND", x, y + 1.4)

    brd.BuildConnectivity()
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    pro = dst.with_suffix(".kicad_pro")
    keep = pro.read_text()
    pcbnew.SaveBoard(str(dst), brd)
    pro.write_text(keep)
    print(f"pre-routed {dst.relative_to(ROOT)}: {len(brd.GetTracks())} tracks/vias")


if __name__ == "__main__":
    main()
