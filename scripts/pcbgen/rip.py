#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rip up router copper in a box (F5 step 3, rip-up and reroute).

  scripts/pcbgen/rip.py <board> x0,y0,x1,y1 [NET ...]

Box in board mm (origin top-left of the board). Deletes every track that
runs through the box and every via in it (only the given nets if any are given);
pre-routed copper of the heater channels lies outside the boxes used. Run
cleanup.py afterwards for the dangling remains.
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    board, box = sys.argv[1], [float(v) for v in sys.argv[2].split(",")]
    nets = set(sys.argv[3:])
    pcb = ROOT / board / f"{board}.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    bb = b.GetBoardEdgesBoundingBox()
    ox, oy = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())

    def inbox(p):
        x, y = pcbnew.ToMM(p.x) - ox, pcbnew.ToMM(p.y) - oy
        return box[0] <= x <= box[2] and box[1] <= y <= box[3]
    rect = pcbnew.BOX2I(pcbnew.VECTOR2I(pcbnew.FromMM(ox + box[0]), pcbnew.FromMM(oy + box[1])),
                        pcbnew.VECTOR2L(pcbnew.FromMM(box[2] - box[0]), pcbnew.FromMM(box[3] - box[1])))
    gone = []
    for t in b.GetTracks():
        if nets and t.GetNetname() not in nets:
            continue
        if t.GetClass() == "PCB_VIA":
            hit = inbox(t.GetPosition())
        else:   # any part of the segment inside the box, not just an end
            hit = t.HitTest(rect, False, 0)
        if hit:
            gone.append(t)
    for t in gone:
        b.Delete(t)
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"rip: {len(gone)} items removed")


if __name__ == "__main__":
    main()
