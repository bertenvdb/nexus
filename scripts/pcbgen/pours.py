#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ground pours on the routing layers (F5 step 4).

  scripts/pcbgen/pours.py <board> [LAYER ...]   (default F.Cu In2.Cu B.Cu)
  scripts/pcbgen/pours.py <board> --remove       remove the pours (to reroute)

Copies the outlines of the In1 ground zones (GND plane, AGND island) to the
given layers, below the existing power zones in priority, so the AGND/GND
split is the same on every layer and the star point stays the only joint.
Pour clearance 0.3 mm, SMD pads solid (reflow), thermal reliefs on THT
pads (hand-soldered connectors), solid on vias and exposed-pad thermal vias, islands
without a connection removed. Existing pours made by this script are
replaced (zone name prefix "pour ").
"""
import pathlib
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
mm = pcbnew.FromMM


def main():
    board = sys.argv[1]
    layers = sys.argv[2:] or ["F.Cu", "In2.Cu", "B.Cu"]
    pcb = ROOT / board / f"{board}.kicad_pcb"
    pro = pcb.with_suffix(".kicad_pro")
    keep = pro.read_text()
    b = pcbnew.LoadBoard(str(pcb))
    zones = list(b.Zones())
    src = [z for z in zones if not z.GetZoneName().startswith("pour ")
           and z.GetLayerSet().Contains(pcbnew.In1_Cu) and z.GetNetname() in ("GND", "AGND")]
    for z in zones:
        if z.GetZoneName().startswith("pour "):
            b.Delete(z)
    n = 0
    if "--remove" in layers:          # only take the pours away (before rerouting)
        layers, src = [], []
    for z in src:
        for ln in layers:
            L = b.GetLayerID(ln)
            nz = pcbnew.ZONE(b)
            nz.SetLayer(L)
            nz.SetNet(z.GetNet())
            nz.SetZoneName(f"pour {z.GetNetname()} {ln}")
            nz.Outline().Append(z.Outline())
            nz.SetAssignedPriority(z.GetAssignedPriority())   # GND 0, AGND 1; power zones are 2
            nz.SetLocalClearance(mm(0.3))
            nz.SetMinThickness(mm(0.2))
            nz.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
            nz.SetThermalReliefGap(mm(0.3))
            nz.SetThermalReliefSpokeWidth(mm(0.3))
            nz.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            b.Add(nz)
            n += 1
    # thermal vias of exposed pads (PTH pads sharing the number of an SMD pad): solid
    for fp in b.GetFootprints():
        smd = {p.GetNumber() for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD}
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and p.GetNumber() in smd:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(pcb), b)
    pro.write_text(keep)
    print(f"pours: {n} zones on {', '.join(layers)}")


if __name__ == "__main__":
    main()
