#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""JLCPCB production files for one board (F7).

  scripts/fab.py toolboard|dockboard [REV]      (REV default rev-A)

Writes fab/<REV>/<board>/:
  <board>-gerbers.zip     Gerbers (4 copper layers, paste, mask, silk, outline)
                          + Excellon drill (PTH and NPTH separate), for the PCB order
  <board>-bom-jlc.csv     JLC BOM: Comment, Designator, Footprint, LCSC Part #
                          (only parts with Assembly = JLC, not DNP; one line
                          per LCSC part number and footprint)
  <board>-cpl-jlc.csv     JLC CPL: Designator, Mid X, Mid Y, Layer, Rotation
                          (same parts; rotation corrected, see below)
  <board>-handsolder.csv  parts with Assembly = SELF (and DNP), ordered from LCSC
                          by Berten and soldered by hand
  <board>-rotations.txt   the rotation correction applied per footprint (to check
                          against the JLC placement preview)

CPL conventions as in kicad-jlcpcb-tools: position = centre of the bounding
box of the soldered pads, X as is and Y negated (Gerber coordinates), board
aux origin ignored (Gerbers are absolute too). Rotation = KiCad orientation +
correction from scripts/fab_rotations.csv (a rule for the LCSC part number
first, else a regex on the footprint name, the longest match wins). The patterns come from the default rotation table of
JLCKicadTools (github.com/matthewlai/JLCKicadTools, cpl_rotations_db.csv),
which kicad-jlcpcb-tools downloads; only those that can match our footprints
are kept. All parts are on the top side.
"""
import collections
import csv
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")


def rotations():
    """Rows of scripts/fab_rotations.csv: a footprint-name regex, or "lcsc:C1234"
    for one part number (JLC's own model orientation differs per part, even
    for the same footprint)."""
    with open(ROOT / "scripts" / "fab_rotations.csv") as f:
        rows = list(csv.DictReader(f))
    by_lcsc = {r["Footprint pattern"][5:]: int(r["Rotation"]) for r in rows
               if r["Footprint pattern"].startswith("lcsc:")}
    by_fp = [(re.compile(r["Footprint pattern"]), int(r["Rotation"])) for r in rows
             if not r["Footprint pattern"].startswith("lcsc:")]
    return by_lcsc, by_fp


def correction(table, name, lcsc):
    """Part number rule first, then the longest matching footprint regex."""
    by_lcsc, by_fp = table
    if lcsc in by_lcsc:
        return by_lcsc[lcsc], f"lcsc:{lcsc}"
    best = None
    for rx, rot in by_fp:
        m = rx.match(name)
        if m and (best is None or len(m.group(0)) > best[0]):
            best = (len(m.group(0)), rot, rx.pattern)
    return (best[1], best[2]) if best else (0, None)


def main():
    board = sys.argv[1]
    rev = sys.argv[2] if len(sys.argv) > 2 else "rev-A"
    pcb = ROOT / board / f"{board}.kicad_pcb"
    out = ROOT / "fab" / rev / board
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Gerbers + drill
    g = out / "gerbers"
    g.mkdir()
    run(["kicad-cli", "pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask",
         "--check-zones", "-o", str(g) + "/", str(pcb)])
    run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "absolute",
         "--excellon-units", "mm", "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2",
         "-o", str(g) + "/", str(pcb)])
    with zipfile.ZipFile(out / f"{board}-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(g.iterdir()):
            z.write(f, f.name)
    shutil.rmtree(g)

    # BOM / CPL from the board (fields synced from the schematic)
    b = pcbnew.LoadBoard(str(pcb))
    table = rotations()
    jlc, self_ = collections.defaultdict(list), collections.defaultdict(list)
    cpl, used = [], collections.Counter()
    for fp in b.GetFootprints():
        fl = {x.GetName(): x.GetText() for x in fp.GetFields()}
        ref = fp.GetReference()
        if fp.IsExcludedFromBOM() or ref.startswith(("H", "TP")) and not fl.get("LCSC"):
            continue
        name = str(fp.GetFPID().GetLibItemName())
        key = (fl.get("Value", fp.GetValue()), name, fl.get("LCSC", ""), fl.get("MPN", ""))
        val = key[0]
        asm = fl.get("Assembly", "")
        if asm == "JLC" and not fp.IsDNP():
            if not fl.get("LCSC"):
                sys.exit(f"{ref}: Assembly = JLC but no LCSC number")
            # one BOM line per part number: JLC sets duplicate lines of one
            # part (LEDs with a value per function) to 0 and leaves them unticked
            jlc[(fl["LCSC"], name, fl.get("MPN", ""))].append((ref, val))
            pads = [p for p in fp.Pads() if p.GetAttribute() in (pcbnew.PAD_ATTRIB_SMD, pcbnew.PAD_ATTRIB_PTH)]
            bb = pads[0].GetBoundingBox()
            for p in pads[1:]:
                bb.Merge(p.GetBoundingBox())
            c = bb.GetCenter()
            rot, pat = correction(table, name, fl["LCSC"])
            used[(name, rot, pat)] += 1
            if fp.GetLayer() != pcbnew.F_Cu:
                sys.exit(f"{ref} is on the bottom side: not handled")
            cpl.append((ref, pcbnew.ToMM(c.x), -pcbnew.ToMM(c.y), "Top",
                        (fp.GetOrientationDegrees() + rot) % 360))
        elif asm in ("SELF", "DNP") or fp.IsDNP():
            self_[(fl.get("LCSC", ""), fl.get("MPN", ""), name, asm or "DNP")].append((ref, val))
        else:
            sys.exit(f"{ref}: Assembly field '{asm}' is not JLC/SELF/DNP")

    nat = lambda r: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", r)]
    with open(out / f"{board}-bom-jlc.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (lcsc, name, mpn), items in sorted(jlc.items(), key=lambda kv: nat(min((r for r, _ in kv[1]), key=nat))):
            vals = {v for _, v in items}
            comment = vals.pop() if len(vals) == 1 else (mpn or lcsc)
            w.writerow([comment, ",".join(sorted((r for r, _ in items), key=nat)), name, lcsc])
    with open(out / f"{board}-cpl-jlc.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, x, y, side, rot in sorted(cpl, key=lambda r: nat(r[0])):
            w.writerow([ref, f"{x:.4f}mm", f"{y:.4f}mm", side, f"{rot:.0f}" if rot == int(rot) else f"{rot:.2f}"])
    with open(out / f"{board}-handsolder.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Qty per board", "Designator", "Value", "MPN", "LCSC Part #", "Footprint", "Assembly"])
        for (lcsc, mpn, name, asm), items in sorted(self_.items(), key=lambda kv: nat(min((r for r, _ in kv[1]), key=nat))):
            refs = sorted((r for r, _ in items), key=nat)
            vals = sorted({v for _, v in items}, key=nat)
            val = vals[0] if len(vals) == 1 else f"{vals[0]} … {vals[-1]}"
            w.writerow([len(refs), ",".join(refs), val, mpn, lcsc, name, asm])
    with open(out / f"{board}-rotations.txt", "w") as f:
        f.write("parts  footprint  correction  (pattern)\n")
        for (name, rot, pat), n in sorted(used.items()):
            f.write(f"{n:5d}  {name}  {rot:+d}  ({pat or 'none'})\n")
    print(f"{board}: {sum(len(r) for r in jlc.values())} JLC parts in {len(jlc)} BOM lines, "
          f"{sum(len(r) for r in self_.values())} hand-soldered, files in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
