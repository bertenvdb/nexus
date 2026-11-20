#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Silkscreen of the Nexus Docks Board (F6 step 4).

  scripts/pcbgen/dockboard_silk.py

Works on dockboard/dockboard.kicad_pcb (routed board). Idempotent: every
board-level text on the silkscreen is made by this script and replaced on
every run. Uses the placement helpers of toolboard_silk.py:

1. Reference designators off the silkscreen (they stay on F.Fab).
2. Footprint silk across or near the board edge removed.
3. Labels (AD-14, CLAUDE.md §7.8-7.9): fan number and polarity at every fan
   port, pin functions at SWD / CAN / LED, connector names, a label at every
   diagnostic LED and test point, the fan rail jumper with its warning
   (open by default = no fan voltage, design 20 §4), the FB jumper, and the
   identity block (top: name + revision; bottom: name, revision, license,
   repository).
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))
import toolboard_silk as ts  # noqa: E402

REV, DATE = "Rev A", "2026-11-20"
FANS = [f"J{6 + i}" for i in range(9)]                       # FAN 0..8
DIAG = {"D7": "24V", "D8": "RAIL", "D9": "5V", "D10": "3V3", "D11": "VBUS", "D12": "MCU"}
TPS = {"TP1": "24V", "TP2": "GND", "TP3": "5V", "TP4": "3V3", "TP5": "RAIL", "TP6": "VBUS",
       "TP7": "H", "TP8": "L"}
PINS = {
    "J2": {"+3V3": "3V3", "SWDIO": "DIO", "SWCLK": "CLK", "GND": "GND"},
    "J4": {"CANH": "H", "CANL": "L", "GND": "G"},
    "J15": {"LED_DIN": "DIN", "GND": "GND", "LED_5V": "5V"},
}
NAMES = [("J1", "24V IN"), ("J3", "USB"), ("J4", "CAN IN"), ("J5", "CAN 120R"), ("J2", "SWD"),
         ("J15", "LED"), ("SW1", "RESET"), ("SW2", "BOOT"), ("F1", "5A")]


def labels(b):
    for d in list(b.GetDrawings()):
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            b.Delete(d)
    occ = ts.Occ(b, body_hard=True)
    O = ts.O
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
        if ts.place(b, occ, *a, **k) is None:
            fails.append(a[0])
    # fan ports first (their spot is fixed): "−  FANi  +" above the connector,
    # − on the pin 1 side (FANi_N), + on the pin 2 side (FAN_RAIL); inside the
    # outline it would be under the header
    for i, r in enumerate(FANS):
        x0, y0, x1, y1 = body(r)
        P(f"−  FAN{i}  +", 0.8, ((x0 + x1) / 2, y0), [UP], maxd=2, rots=(0,), sides=(0, 0.3, -0.3))
    # fan rail warning (safety, design 20 §4), then the board name on top
    # (AD-14): no room for pad legends at the 3 pads, so the warning names the
    # pad order
    if not ts.place_block(b, occ, [("RAIL JP: 24V | RAIL | BUCK", 0.8, 0.15),
                                   ("open = no fan power", 0.8, 0.15)], ctr("JP2")):
        fails.append("fan rail warning")
    if not ts.place_block(b, occ, [("Nexus Docks Board", 1.2, 0.2), (f"{REV}  {DATE}", 0.8, 0.15)],
                          (30.0, 35.0)):
        fails.append("identity block top")
    # (no room for pointer labels at the jumpers; they are the only 3-pad and
    # 2-pad solder jumpers on the board)
    for r, txt in DIAG.items():       # 0.7 mm where 0.8 does not fit (below the 1206 of D8)
        if ts.place(b, occ, txt, 0.8, ctr(r), [DOWN, UP, LEFT, RIGHT], maxd=6, rots=(0, 90)) is None:
            P(txt, 0.7, ctr(r), [DOWN, UP, LEFT, RIGHT], maxd=6, rots=(0, 90))
    for r, m in PINS.items():
        for net, txt in m.items():
            P(txt, 0.8, pad(r, net), [UP, DOWN, RIGHT, LEFT], maxd=8)
    for r, txt in NAMES:
        x0, y0, x1, y1 = body(r)
        P(txt, 1.0, ((x0 + x1) / 2, (y0 + y1) / 2), [RIGHT, DOWN, UP, LEFT], maxd=8, rots=(0, 90))
    for r, txt in TPS.items():
        P(txt, 0.8, ctr(r), [DOWN, UP, RIGHT, LEFT], maxd=8, rots=(0, 90))
    # FB jumper legend last: no room at JP_FBSEL itself, it takes the nearest free spot
    if not ts.place_block(b, occ, [("5V JP: cut = 12V", 0.8, 0.15)], ctr("JP1")):
        fails.append("FB jumper legend")
    if not ts.place_block(b, ts.Occ(b, pcbnew.B_Cu, body_hard=True),
                          [("Nexus Docks Board", 2.0, 0.3), (f"{REV}  {DATE}", 1.2, 0.18),
                           ("CERN-OHL-S-2.0", 1.2, 0.18), ("github.com/bertenvdb/nexus", 1.0, 0.15)],
                          (44.0, 31.0), back=True):
        fails.append("identity block bottom")
    return fails


def main():
    pcb = ROOT / "dockboard" / "dockboard.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    bb = b.GetBoardEdgesBoundingBox()
    ts.O = pcbnew.ToMM(bb.GetLeft())
    ts.BW, ts.BH = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    h, r = ts.strip(b)
    fails = labels(b)
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"silk: {h} references hidden, {r} edge silk items removed")
    print("labels not placed: " + (", ".join(fails) if fails else "none"))


if __name__ == "__main__":
    sys.exit(main())
