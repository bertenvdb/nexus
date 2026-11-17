#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Query the JLCPCB parts library (stock, Basic/Extended, package, price).

Usage:
  scripts/jlc_parts.py lookup C719095 C6560 ...      # exact LCSC numbers
  scripts/jlc_parts.py search "XT60PW" [-n 10] [--basic]

Library type: Basic = no fee, Preferred = "Preferred Extended" (no fee with
Economic PCBA), Extended = ~$3 fee per unique part per order.

Uses the public endpoint behind jlcpcb.com/parts. Unofficial: may change.
"""
import argparse
import json
import sys
import time
import urllib.request

URL = ("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/"
       "smtGood/selectSmtComponentList")


def query(keyword, page_size=10):
    body = json.dumps({"keyword": keyword, "currentPage": 1,
                       "pageSize": page_size}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            info = (data.get("data") or {}).get("componentPageInfo") or {}
            return info.get("list") or []
        except Exception as e:  # network hiccup: retry
            if attempt == 2:
                print(f"error querying {keyword}: {e}", file=sys.stderr)
                return []
            time.sleep(2)


def libtype(p):
    if p.get("componentLibraryType") == "base":
        return "Basic"
    if p.get("preferredComponentFlag"):
        return "Preferred"
    return "Extended"


def unit_price(p, qty=10):
    for tier in p.get("componentPrices") or []:
        end = tier["endNumber"]
        if tier["startNumber"] <= qty and (end == -1 or qty <= end):
            return tier["productPrice"]
    return None


def row(p):
    return {
        "lcsc": p.get("componentCode"),
        "mpn": p.get("componentModelEn"),
        "brand": p.get("componentBrandEn"),
        "package": p.get("componentSpecificationEn"),
        "type": libtype(p),
        "stock": p.get("stockCount"),
        "price10": unit_price(p),
        "describe": (p.get("describe") or "")[:90],
        "datasheet": p.get("dataManualUrl"),
        "datasheet_pdf": p.get("dataManualFileAccessIdUrl"),
    }


def show(rows, as_json):
    if as_json:
        print(json.dumps(rows, indent=1))
        return
    for r in rows:
        print(f"{r['lcsc']:<10} {r['type']:<9} stock {r['stock']!s:>8}  "
              f"${r['price10']!s:<7} {r['mpn']} [{r['package']}] "
              f"{r['brand']} | {r['describe']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("lookup")
    lk.add_argument("codes", nargs="+")
    sr = sub.add_parser("search")
    sr.add_argument("keyword")
    sr.add_argument("-n", type=int, default=10)
    sr.add_argument("--basic", action="store_true",
                    help="only Basic/Preferred parts")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = []
    if a.cmd == "lookup":
        for code in a.codes:
            hits = [p for p in query(code, 5) if p.get("componentCode") == code]
            if hits:
                rows.append(row(hits[0]))
            else:
                rows.append({"lcsc": code, "mpn": "NOT FOUND", "brand": "",
                             "package": "", "type": "-", "stock": 0,
                             "price10": None, "describe": "", "datasheet": ""})
            time.sleep(0.3)
    else:
        rows = [row(p) for p in query(a.keyword, 50)]
        if a.basic:
            rows = [r for r in rows if r["type"] in ("Basic", "Preferred")]
        rows = sorted(rows, key=lambda r: -(r["stock"] or 0))[:a.n]
    show(rows, a.json)


if __name__ == "__main__":
    main()
