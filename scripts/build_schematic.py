#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate a board schematic, verify connectivity, run ERC, export PDF/PNG.

Usage: scripts/build_schematic.py toolboard
"""
import importlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "schgen"))


def main():
    board_name = sys.argv[1] if len(sys.argv) > 1 else "toolboard"
    mod = importlib.import_module(board_name)
    board = mod.build()
    board.write()
    problems = board.verify()
    print(f"{board_name}: {len(board.sheets)} sheets, "
          f"{sum(len(s.parts) for s in board.sheets)} parts")
    if problems:
        print("CONNECTIVITY PROBLEMS:")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("connectivity: KiCad netlist matches the description")

    out = ROOT / "out"
    sch = ROOT / board_name / f"{board_name}.kicad_sch"
    erc = subprocess.run(["kicad-cli", "sch", "erc", "--severity-all",
                          "-o", str(out / f"{board_name}-erc.rpt"), str(sch)],
                         capture_output=True, text=True)
    print((erc.stdout.strip().splitlines() or ["ERC done"])[-1])
    subprocess.run(["kicad-cli", "sch", "export", "pdf", "-o",
                    str(out / f"{board_name}-schematic.pdf"), str(sch)],
                   check=True, capture_output=True)
    subprocess.run(["pdftoppm", "-r", "75", "-png",
                    str(out / f"{board_name}-schematic.pdf"),
                    str(out / f"{board_name}-sheet")], check=True)
    print(f"PDF: out/{board_name}-schematic.pdf")


if __name__ == "__main__":
    main()
