#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regenerate the table in docs/bom-master.md from docs/bom-master.csv.

The CSV is the source of truth. Everything between the markers
<!-- BOM:START --> and <!-- BOM:END --> in the Markdown file is replaced.
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV = ROOT / "docs" / "bom-master.csv"
MD = ROOT / "docs" / "bom-master.md"
COLS = ["group", "description", "mpn", "lcsc", "qty_tool", "qty_dock",
        "assembly", "jlc_type", "stock_2026_11_17", "price10_usd",
        "verified", "notes"]
HEAD = ["Group", "Description", "MPN", "LCSC", "Tool", "Dock", "Assembly",
        "JLC type", "Stock 17/11", "Price $ (10)", "Verified", "Notes"]


def main():
    rows = list(csv.DictReader(CSV.open()))
    lines = ["| " + " | ".join(HEAD) + " |",
             "|" + "---|" * len(HEAD)]
    for r in rows:
        lines.append("| " + " | ".join(
            r[c].replace("|", "/") for c in COLS) + " |")

    ext = sorted({r["mpn"] for r in rows
                  if r["assembly"] == "JLC" and r["jlc_type"] == "Extended"})
    lines += ["", f"**Unique Extended parts placed by JLC: {len(ext)}** "
              f"(≈ ${len(ext) * 3.07:.0f} fee per order): " + ", ".join(ext)
              + ".", ""]

    text = MD.read_text()
    start = text.index("<!-- BOM:START -->") + len("<!-- BOM:START -->")
    end = text.index("<!-- BOM:END -->")
    MD.write_text(text[:start] + "\n" + "\n".join(lines) + "\n" + text[end:])
    print(f"{MD.relative_to(ROOT)}: {len(rows)} rows, {len(ext)} Extended")


if __name__ == "__main__":
    main()
