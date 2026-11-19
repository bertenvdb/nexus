#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Remove router copper that does not belong (F5 step 3).

  scripts/pcbgen/cleanup.py <board> [--no-in1]

--no-in1  delete every track on In1 (In1 is the GND/AGND plane)
Then repeat until stable: run KiCad's DRC and delete the vias and tracks it
reports as dangling (KiCad's own definition, not a home-made one). Tracks
whose net is listed in KEEP_DANGLING are left alone.
"""
import pathlib
import re
import subprocess
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
KEEP_DANGLING = set()


def dangling(pcb):
    rpt = ROOT / "out" / "cleanup-drc.rpt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "-o", str(rpt), str(pcb)],
                   capture_output=True)
    out = []
    for blk in re.split(r"\n(?=\[)", rpt.read_text()):
        m = re.match(r"\[(track_dangling|via_dangling)\]", blk)
        if not m:
            continue
        loc = re.search(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (Track|Via) \[([^\]]*)\]", blk)
        if loc:
            out.append((m.group(1), float(loc.group(1)), float(loc.group(2)), loc.group(4)))
    return out


def main():
    board = sys.argv[1]
    pcb = ROOT / board / f"{board}.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    n_in1 = 0
    if "--no-in1" in sys.argv:
        for t in [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.In1_Cu]:
            b.Delete(t)
            n_in1 += 1
    pcbnew.SaveBoard(str(pcb), b)
    removed = 0
    for _ in range(30):
        items = dangling(pcb)
        b = pcbnew.LoadBoard(str(pcb))
        gone = 0
        for kind, x, y, net in items:
            if net in KEEP_DANGLING:
                continue
            p = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
            for t in b.GetTracks():
                if t.GetNetname() != net:
                    continue
                if kind == "via_dangling" and t.GetClass() == "PCB_VIA" and (t.GetPosition() - p).EuclideanNorm() < 1000:
                    b.Delete(t); gone += 1
                    break
                if kind == "track_dangling" and t.GetClass() == "PCB_TRACK" and (
                        (t.GetStart() - p).EuclideanNorm() < 1000 or (t.GetEnd() - p).EuclideanNorm() < 1000
                        or (t.GetPosition() - p).EuclideanNorm() < 1000):
                    b.Delete(t); gone += 1
                    break
        if not gone:
            break
        removed += gone
        pcbnew.SaveBoard(str(pcb), b)
    b = pcbnew.LoadBoard(str(pcb))
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"cleanup: {n_in1} In1 tracks, {removed} dangling items removed")


if __name__ == "__main__":
    main()
