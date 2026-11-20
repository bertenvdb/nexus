#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Silkscreen of the Nexus Tools Board (F5 step 4).

  scripts/pcbgen/toolboard_silk.py

Works on toolboard/toolboard.kicad_pcb (routed board, the source from step 3
on). Idempotent: every board-level text on F.Silkscreen is made by this
script and is replaced on every run.

1. Reference designators off the silkscreen (they stay on F.Fab for the
   assembly drawing): with ~300 parts on 140 x 90 mm they do not fit.
2. Footprint silk that crosses the board edge (connectors with overhang) or
   lies within EDGE_CLR of it is removed from the board copy of the
   footprint.
3. Function labels (AD-14, CLAUDE.md §7.9): see LABELS below.
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
mm = pcbnew.FromMM
O = 40.0                # board origin in KiCad coordinates
BW, BH = 140.0, 90.0    # board size (dockboard_silk.py sets its own)
EDGE_CLR = 0.35         # silk to board edge


def edge_poly(b):
    p = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(p, False)
    q = pcbnew.SHAPE_POLY_SET(p)
    q.Inflate(mm(-EDGE_CLR), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
    return q


def strip(b):
    hidden = removed = 0
    inner = edge_poly(b)
    for fp in b.GetFootprints():
        ref = fp.GetField(pcbnew.FIELD_T_REFERENCE)
        if ref.IsVisible() and ref.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            ref.SetVisible(False)
            hidden += 1
    for fp in b.GetFootprints():
        for g in list(fp.GraphicalItems()):
            if g.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                continue
            poly = pcbnew.SHAPE_POLY_SET()
            g.TransformShapeToPolygon(poly, g.GetLayer(), 0, mm(0.01), pcbnew.ERROR_OUTSIDE)
            out = pcbnew.SHAPE_POLY_SET(poly)
            out.BooleanSubtract(inner)
            if out.OutlineCount():
                fp.Delete(g)
                removed += 1
    return hidden, removed


# ---------------------------------------------------------------- labels
G = 0.1
REV, DATE = "Rev A", "2026-11-20"
HEATERS = [f"J{7 + i}" for i in range(8)]
THERMS = [f"J{15 + i}" for i in range(8)]
FILS = [f"J{23 + i}" for i in range(8)]
HLEDS = [f"D{14 + i}" for i in range(8)]
DIAG = {"D8": "24V", "D9": "RAIL", "D10": "5V", "D11": "3V3", "D12": "VBUS", "D13": "MCU"}
TPS = {"TP1": "24V", "TP2": "GND", "TP3": "CUT", "TP4": "HTR", "TP5": "RAIL", "TP6": "5V",
       "TP7": "3V3", "TP8": "3VA", "TP9": "VREF", "TP10": "AGND", "TP11": "VBUS",
       "TP14": "G0", "TP15": "D0"}
PINS = {   # connector pin labels by net (suffix match)
    "J2": {"+3V3_MCU": "3V3", "SWDIO": "DIO", "SWCLK": "CLK", "GND": "GND"},
    "J4": {"CANH": "H", "CANL": "L", "GND": "G"},
    "J5": {"CANH": "H", "CANL": "L", "GND": "G"},
    "J31": {"LED_DIN": "DIN", "GND": "GND", "LED_5V": "5V"},
}


class Occ:
    """Silk keep-out map on a 0.1 mm grid (board coordinates, origin top-left)."""

    def __init__(self, b, side=pcbnew.F_Cu, body_hard=False):
        import numpy as np
        silk, crt = (pcbnew.F_SilkS, pcbnew.F_CrtYd) if side == pcbnew.F_Cu else (pcbnew.B_SilkS, pcbnew.B_CrtYd)
        self.np = np
        self.m = np.zeros((int(BH / G) + 1, int(BW / G) + 1), np.uint8)   # 1 hard, 2 courtyard
        e = int(0.5 / G)
        self.m[:e, :] = self.m[-e:, :] = 1
        self.m[:, :e] = self.m[:, -e:] = 1
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(side) or p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                    self.box(p.GetBoundingBox(), 0.2, 1)
            for g in fp.GraphicalItems():
                if g.GetLayer() == silk:
                    self.box(g.GetBoundingBox(), 0.15, 1)
                elif g.GetLayer() == crt:
                    self.box(g.GetBoundingBox(), 0.0, 2)
            if body_hard:
                # body_hard: the part body (F.Fab outline) is hard too; silk
                # there ends up under the part or the mating plug
                fab = pcbnew.F_Fab if side == pcbnew.F_Cu else pcbnew.B_Fab
                bbs = [g.GetBoundingBox() for g in fp.GraphicalItems()
                       if g.GetLayer() == fab and g.GetClass() not in ("PCB_TEXT", "PCB_FIELD")]
                if bbs:
                    bb = bbs[0]
                    for x in bbs[1:]:
                        bb.Merge(x)
                    self.box(bb, -0.2, 1)

    def idx(self, x0, y0, x1, y1):
        ny, nx = self.m.shape
        clamp = lambda v, n: min(max(v, 0), n)
        return (clamp(int(y0 / G), ny), clamp(int(y1 / G) + 1, ny),
                clamp(int(x0 / G), nx), clamp(int(x1 / G) + 1, nx))

    def box(self, bb, inf, v):
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - O - inf, pcbnew.ToMM(bb.GetTop()) - O - inf
        x1, y1 = pcbnew.ToMM(bb.GetRight()) - O + inf, pcbnew.ToMM(bb.GetBottom()) - O + inf
        self.put(x0, y0, x1, y1, v)

    def put(self, x0, y0, x1, y1, v):
        r0, r1, c0, c1 = self.idx(x0, y0, x1, y1)
        sub = self.m[r0:r1, c0:c1]
        sub[(sub == 0) | (v == 1)] = v

    def cost(self, x0, y0, x1, y1, crtyd_ok):
        if x0 < 0 or y0 < 0 or x1 > BW or y1 > BH:
            return None
        r0, r1, c0, c1 = self.idx(x0, y0, x1, y1)
        sub = self.m[r0:r1, c0:c1]
        if (sub == 1).any():
            return None
        n = int((sub == 2).sum())
        if n and not crtyd_ok:
            return None
        return n * G * G


def text_item(b, txt, size, thick, x, y, rot=0, bold=False, back=False):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(txt)
    t.SetLayer(pcbnew.B_SilkS if back else pcbnew.F_SilkS)
    t.SetMirrored(back)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetBold(bold)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(rot)
    t.SetPosition(pcbnew.VECTOR2I(mm(O + x), mm(O + y)))
    return t


def place_block(b, occ, lines, near, back=False):
    """Several centred lines as one block at the free spot closest to `near`."""
    items = []
    for txt, sz, th in lines:
        t = text_item(b, txt, sz, th, 0, 0)
        bb = t.GetBoundingBox()
        items.append((txt, sz, th, pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())))
    W = max(i[3] for i in items) + 0.4
    H = sum(i[4] + 0.5 for i in items)
    best = None
    for y in occ.np.arange(0.6, BH - H, 0.25):
        for x in occ.np.arange(0.6, BW - W, 0.25):
            if occ.cost(x, y, x + W, y + H, False) is None:
                continue
            d = (x + W / 2 - near[0]) ** 2 + (y + H / 2 - near[1]) ** 2
            if best is None or d < best[0]:
                best = (d, x, y)
    if best is None:
        return False
    _, x, y = best
    x, y = float(x), float(y)
    cy = y + 0.25
    for txt, sz, th, w, h in items:
        b.Add(text_item(b, txt, sz, th, x + W / 2, cy + h / 2, back=back))
        cy += h + 0.5
    occ.put(x - 0.25, y - 0.25, x + W + 0.25, y + H + 0.25, 1)
    return True


def place(b, occ, txt, size, anchor, dirs, maxd=6.0, rots=(0, 90), crtyd_ok=True, thick=None,
          sides=(0, 0.4, -0.4, 0.8, -0.8, 1.5, -1.5, 2.5, -2.5)):
    """Put `txt` at the cheapest free spot near `anchor`, moving out along
    one of `dirs` (unit vectors). Returns the text or None."""
    thick = thick or max(0.15, size * 0.15)
    best = None
    for rot in rots:
        t = text_item(b, txt, size, thick, 0, 0, rot)
        bb = t.GetBoundingBox()
        w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        for k, (dx, dy) in enumerate(dirs):
            d = 0.2
            while d <= maxd:
                for side in sides:
                    cx = anchor[0] + dx * (d + w / 2) + (-dy) * side
                    cy = anchor[1] + dy * (d + h / 2) + dx * side
                    c = occ.cost(cx - w / 2 - 0.1, cy - h / 2 - 0.1, cx + w / 2 + 0.1, cy + h / 2 + 0.1, crtyd_ok)
                    if c is None:
                        continue
                    score = d + 0.6 * abs(side) + 1.5 * k + (2.0 if rot else 0) + 3.0 * c
                    if best is None or score < best[0]:
                        best = (score, cx, cy, rot, w, h)
                d += 0.2
    if best is None:
        return None
    _, cx, cy, rot, w, h = best
    t = text_item(b, txt, size, thick, cx, cy, rot)
    b.Add(t)
    occ.put(cx - w / 2 - 0.25, cy - h / 2 - 0.25, cx + w / 2 + 0.25, cy + h / 2 + 0.25, 1)
    return t


def labels(b):
    for d in list(b.GetDrawings()):
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            b.Delete(d)
    occ = Occ(b)
    fp = b.FindFootprintByReference
    ctr = lambda r: (pcbnew.ToMM(fp(r).GetPosition().x) - O, pcbnew.ToMM(fp(r).GetPosition().y) - O)

    def pad(r, net):
        for p in fp(r).Pads():
            if p.GetNetname().split("/")[-1] == net:
                return pcbnew.ToMM(p.GetPosition().x) - O, pcbnew.ToMM(p.GetPosition().y) - O

    def body(r):
        bb = fp(r).GetBoundingBox(False)
        return [pcbnew.ToMM(v) - O for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
    UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
    fails = []

    def P(*a, **k):
        if place(b, occ, *a, **k) is None:
            fails.append(a[0])
    # heater terminals: tool number and +24V / HEATER- above the body
    for i, r in enumerate(HEATERS):
        x0, y0, x1, y1 = body(r)
        P(f"T{i}", 1.2, ((x0 + x1) / 2, y0), [UP], maxd=4, rots=(0,))
        xp, _ = pad(r, f"HEATER_T{i}_P"); xn, _ = pad(r, f"HEATER_T{i}_N")
        P("+24V", 0.9, (xp, y0), [UP], maxd=6)
        P("HEATER−", 0.9, (xn, y0), [UP], maxd=6)
    for i, r in enumerate(THERMS):
        x0, y0, x1, y1 = body(r)
        P(f"T{i}", 1.2, (x0, (y0 + y1) / 2), [LEFT, UP], maxd=4, rots=(0,))
    P("THERMISTOR", 1.0, ((body(THERMS[0])[0] + body(THERMS[0])[2]) / 2, body(THERMS[0])[1]), [UP, LEFT], maxd=5, rots=(0, 90))
    for i, r in enumerate(FILS):
        x0, y0, x1, y1 = body(r)
        for net, txt in ((f"FIL_RUNOUT_T{i}_C", "RUN"), ("GND", "GND"), ("VCC_FIL", "VCC"), (f"FIL_MOTION_T{i}_C", "MOT")):
            x, _ = pad(r, net)
            P(txt, 0.8, (x, y1), [DOWN], maxd=9, rots=(0,), sides=(0,))
        P(f"T{i}", 1.2, ((x0 + x1) / 2, y1), [DOWN], maxd=10, rots=(0,), sides=(0, 0.5, -0.5))
    for r, m in PINS.items():
        for net, txt in m.items():
            P(txt, 0.9, pad(r, net), [UP, DOWN, RIGHT, LEFT], maxd=7)
    for r, txt in [("J1", "24V IN"), ("J3", "USB"), ("J4", "CAN IN"), ("J5", "CAN OUT"), ("J6", "CAN 120R"),
                   ("J2", "SWD"), ("J31", "LED"), ("SW1", "RESET"), ("SW2", "BOOT"), ("F1", "25A")]:
        x0, y0, x1, y1 = body(r)
        P(txt, 1.0, ((x0 + x1) / 2, (y0 + y1) / 2), [RIGHT, DOWN, UP, LEFT], maxd=8, rots=(0, 90))
    # XT60 polarity: the footprint's + mark at pin 2 stays; its - mark lies outside the
    # board and went with the edge silk, and there is no room for one next to pin 1
    for r, txt in DIAG.items():
        P(txt, 0.8, ctr(r), [UP, DOWN], maxd=3, rots=(0, 90))
    for i, r in enumerate(HLEDS):
        P(f"T{i}", 0.8, ctr(r), [LEFT, RIGHT, UP, DOWN], maxd=3, rots=(0,))
    for r, txt in TPS.items():
        P(txt, 0.8, ctr(r), [DOWN, UP, RIGHT, LEFT], maxd=3, rots=(0, 90))
    # solder jumpers: PT1000 column legend, filament supply jumper
    x0, y0, x1, y1 = body("JP1")
    P("PT1000", 0.8, ((x0 + x1) / 2, y0), [UP, DOWN], maxd=4, rots=(0, 90))
    P("JP closed", 0.8, ((x0 + x1) / 2, y0), [UP, DOWN], maxd=6, rots=(0, 90))
    P("5V", 0.8, pad("JP9", "+5V"), [LEFT, RIGHT, DOWN], maxd=3)
    P("3V3", 0.8, pad("JP9", "+3V3_AUX"), [LEFT, RIGHT, UP], maxd=3)
    P("FIL VCC", 0.8, ctr("JP9"), [LEFT, RIGHT, UP, DOWN], maxd=5, rots=(90, 0))
    # identity block last, in the largest free spot closest to the top centre
    # (top: name + revision; bottom: the full block incl. license and repo, AD-14)
    if not place_block(b, occ, [("Nexus Tools Board", 1.6, 0.25), (f"{REV}  {DATE}", 1.0, 0.15)], (70.0, 20.0)):
        fails.append("identity block top")
    if not place_block(b, Occ(b, pcbnew.B_Cu), [("Nexus Tools Board", 2.0, 0.3), (f"{REV}  {DATE}", 1.2, 0.18),
                                                 ("CERN-OHL-S-2.0", 1.2, 0.18),
                                                 ("github.com/bertenvdb/nexus", 1.0, 0.15)], (70.0, 30.0), back=True):
        fails.append("identity block bottom")
    return fails


def main():
    pcb = ROOT / "toolboard" / "toolboard.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    h, r = strip(b)
    fails = labels(b)
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"silk: {h} references hidden, {r} edge silk items removed")
    print("labels not placed: " + (", ".join(fails) if fails else "none"))


if __name__ == "__main__":
    sys.exit(main())
