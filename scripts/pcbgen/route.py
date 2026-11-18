#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Freerouting round trip for a board (F5 step 3).

  scripts/pcbgen/route.py export toolboard   -> out/<board>.dsn
  (run Freerouting: java -jar freerouting.jar -de out/<b>.dsn -do out/<b>.ses -mp 30)
  scripts/pcbgen/route.py import toolboard   -> tracks/vias into <board>.kicad_pcb,
                                                zones refilled
Zones are exported as planes, so Freerouting connects to them with vias.
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
import os
# In1 below this stays plane only; 0 = all of In1 (default: the 2026-11-18 run
# showed long slots under USB and the MCU when the top part was free)
IN1_FREE_ABOVE_MM = float(os.environ.get("IN1_FREE_ABOVE_MM", "0"))
# extra In1 wire keepouts "x0,y0,x1,y1;..." in board mm (connector area,
# MCU/crystal/USB pins): In1 stays solid under the fast and sensitive nets
IN1_KEEP = [tuple(map(float, r.split(","))) for r in
            os.environ.get("IN1_KEEP", "").split(";") if r]
# Freerouting ignores the 0.5 mm copper-to-edge rule; an edge strip (and a
# keepout over outer-layer zones) also covers pads, which the router then
# leaves unrouted (2026-11-18: 161 instead of 61 open). Off by default.
EDGE_KEEP_MM = float(os.environ.get("EDGE_KEEP_MM", "0"))
OUTER_ZONE_KEEP = os.environ.get("OUTER_ZONE_KEEP", "0") == "1"


def patch_planes(b, dsn):
    """Router export rules for the plane layers.

    Power-type layers make Freerouting ignore the planes and plain signal
    layers make it cut them. So every layer is exported as a signal layer and
    gets a wire keepout where copper must stay whole: In1 (GND/AGND plane)
    and every zone on the other layers (trunk, heater rail band). Vias stay
    allowed, so Freerouting connects to the planes with vias. A strip along
    the board edge is kept free on every layer.
    """
    text = dsn.read_text()
    to_dsn = lambda x, y: f"{pcbnew.ToMM(x) * 1000:.0f} {-pcbnew.ToMM(y) * 1000:.0f}"
    bb = b.GetBoardEdgesBoundingBox()
    keep = ""
    corners = [(bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
               (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())]
    # In1: keep the heater return path (bottom part, MOSFET sources -> XT60)
    # and the AGND island whole; the digital top part may carry short tracks.
    ret_top = bb.GetTop() + pcbnew.FromMM(IN1_FREE_ABOVE_MM)
    ret = [(bb.GetLeft(), ret_top), (bb.GetRight(), ret_top),
           (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())]
    keep += ('    (wire_keepout "" (polygon In1.Cu 0  '
             + "  ".join(to_dsn(x, y) for x, y in ret) + "))\n")
    for x0, y0, x1, y1 in IN1_KEEP:
        X0, Y0 = bb.GetLeft() + pcbnew.FromMM(x0), bb.GetTop() + pcbnew.FromMM(y0)
        X1, Y1 = bb.GetLeft() + pcbnew.FromMM(x1), bb.GetTop() + pcbnew.FromMM(y1)
        keep += ('    (wire_keepout "" (polygon In1.Cu 0  '
                 + "  ".join(to_dsn(x, y) for x, y in [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]) + "))\n")
    for z in b.Zones():
        if z.GetLayer() == pcbnew.In1_Cu and z.GetNetname() == "AGND":
            ol = z.Outline().Outline(0)
            pts = "  ".join(to_dsn(ol.CPoint(k).x, ol.CPoint(k).y) for k in range(ol.PointCount()))
            keep += f'    (wire_keepout "" (polygon In1.Cu 0  {pts}))\n'
        if z.GetLayer() == pcbnew.In1_Cu:
            continue
        if z.GetLayer() != pcbnew.In2_Cu and not OUTER_ZONE_KEEP:
            continue
        ol = z.Outline().Outline(0)
        pts = "  ".join(to_dsn(ol.CPoint(k).x, ol.CPoint(k).y) for k in range(ol.PointCount()))
        keep += f'    (wire_keepout "" (polygon {z.GetLayerName()} 0  {pts}))\n'
    e = pcbnew.FromMM(EDGE_KEEP_MM)
    L, T, R, Bo = bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()
    strips = [(L, T, R, T + e), (L, Bo - e, R, Bo), (L, T, L + e, Bo), (R - e, T, R, Bo)]
    for layer in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu") if EDGE_KEEP_MM else ():
        for x0, y0, x1, y1 in strips:
            pts = "  ".join(to_dsn(x, y) for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            keep += f'    (wire_keepout "" (polygon {layer} 0  {pts}))\n'
    text = text.replace("(layer In1.Cu\n      (type power)", "(layer In1.Cu\n      (type signal)")
    i = text.index("    (plane ")
    dsn.write_text(text[:i] + keep + text[i:])


def main():
    action, board = sys.argv[1], sys.argv[2]
    pcb = ROOT / board / f"{board}.kicad_pcb"
    b = pcbnew.LoadBoard(str(pcb))
    if action == "export":
        out = ROOT / "out" / f"{board}.dsn"
        if not pcbnew.ExportSpecctraDSN(b, str(out)):
            sys.exit("DSN export failed")
        patch_planes(b, out)
        print(f"exported {out.relative_to(ROOT)}")
    elif action == "import":
        ses = ROOT / "out" / f"{board}.ses"
        if not pcbnew.ImportSpecctraSES(b, str(ses)):
            sys.exit("SES import failed")
        b.BuildConnectivity()
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        pro = pcb.with_suffix(".kicad_pro")
        keep = pro.read_text()          # SaveBoard rewrites the net classes
        pcbnew.SaveBoard(str(pcb), b)
        pro.write_text(keep)
        print(f"imported {ses.relative_to(ROOT)}: {len(b.GetTracks())} tracks/vias")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
