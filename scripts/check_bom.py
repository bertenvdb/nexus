#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare the KiCad BOM of a board with docs/bom-master.csv.

Usage: scripts/check_bom.py toolboard|dockboard

Checks:
- every BOM part (in_bom) has LCSC, MPN and Assembly fields;
- quantity per LCSC number matches qty_tool / qty_dock in the master CSV
  (rows with a single C-number; generic passive rows are listed, not checked);
- LCSC numbers in the schematic that are missing from the master CSV.
"""
import collections
import csv
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    board = sys.argv[1] if len(sys.argv) > 1 else "toolboard"
    col = {"toolboard": "qty_tool", "dockboard": "qty_dock"}[board]
    out = ROOT / "out" / f"{board}-bom.csv"
    subprocess.run(["kicad-cli", "sch", "export", "bom",
                    "--fields", "Reference,Value,Footprint,LCSC,MPN,Assembly,${QUANTITY}",
                    "--group-by", "LCSC,Value,Footprint", "--exclude-dnp",
                    "-o", str(out), str(ROOT / board / f"{board}.kicad_sch")],
                   check=True, capture_output=True)
    rows = list(csv.DictReader(out.open()))
    problems = []
    sch = collections.Counter()
    sch_asm = {}
    for r in rows:
        n = int(r["QUANTITY"])
        if not r["LCSC"] or not r["MPN"] or not r["Assembly"]:
            problems.append(f"missing LCSC/MPN/Assembly: {r['Reference']} ({r['Value']})")
            continue
        sch[r["LCSC"]] += n
        sch_asm[r["LCSC"]] = r["Assembly"]

    master = {}
    generic = set()
    for r in csv.DictReader((ROOT / "docs" / "bom-master.csv").open()):
        codes = re.findall(r"C\d+", r["lcsc"])
        if len(codes) == 1 and re.fullmatch(r"\d+", r[col] or ""):
            q, asm, grp = master.get(codes[0], (0, r["assembly"], ""))
            master[codes[0]] = (q + int(r[col]), asm,
                                (grp + " + " if grp else "") + r["group"])
        else:
            generic.update(codes)

    print(f"{'LCSC':<10} {'sch':>4} {'csv':>4}  group / value")
    for code in sorted(set(sch) | {c for c, v in master.items() if v[0] > 0}):
        got = sch.get(code, 0)
        want, asm, group = master.get(code, (None, None, None))
        mark = ""
        if want is None:
            mark = "  (generic / not a master row)" if code in generic else "  NOT IN MASTER"
            if code not in generic:
                problems.append(f"{code} ({got}x) is not in bom-master.csv")
        elif got != want:
            mark = "  <-- MISMATCH"
            problems.append(f"{code} {group}: schematic {got}, master {want}")
        elif asm and sch_asm.get(code) and asm != sch_asm[code]:
            mark = f"  <-- assembly {sch_asm[code]} vs {asm}"
            problems.append(f"{code} {group}: assembly {sch_asm[code]} vs master {asm}")
        print(f"{code:<10} {got:>4} {'' if want is None else want:>4}  {group or ''}{mark}")
    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("BOM matches bom-master.csv")


if __name__ == "__main__":
    main()
