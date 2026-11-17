#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Post-process lib/nexus after easyeda2kicad imports.

Applies the corrections from the F1 footprint review (docs/library-review.md),
so that re-running scripts/import_parts.sh does not lose them:

- upgrade the symbol library to the current KiCad format
- rename the easyeda field "LCSC Part" to "LCSC", add "Assembly"
- set real pin electrical types (easyeda exports everything "unspecified")
- replace rejected easyeda footprints by KiCad standard footprints
- replace easyeda symbols by copies of KiCad standard symbols where better
- fix footprint pads that deviate from the datasheet land pattern
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"
SYM = LIB / "nexus.kicad_sym"
PRETTY = LIB / "nexus.pretty"
SHAPES = LIB / "nexus.3dshapes"
KICAD_SYM = pathlib.Path("/usr/share/kicad/symbols")

# Symbol -> footprint override (KiCad standard library).
FOOTPRINT = {
    "LM74502DDFR": "Package_TO_SOT_SMD:TSOT-23-8",
}

# Rejected easyeda footprints (and 3D models): replaced by standard ones.
REJECTED = [
    "SOT-23-8_L2.9-W1.6-P0.65-LS2.8-BL",          # LM74502 -> TSOT-23-8
    "TSOT-23-8_L2.9-W1.6-H1.1-LS2.8-P0.65",
    "PG-TDSON-8-FL_L5.0-W6.0-P1.27-LS6.2-BL",     # BSC016N06NS: stray pad
    "PG-TDSON-8-FL_L5.0-W6.0-H1.0-P1.27-LS6.2-BL",
    "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",          # PESD2CAN -> SOT-23
    "SOT-23-3P_L2.9-W1.3-H1.0-LS2.4-P0.95",
]
DROP_SYMBOLS = ["BSC016N06NS", "PESD2CAN_C907830", "WSD4070DN",
                "0456025.ER", "MWSA0603-100MT"]

# Copies of KiCad standard symbols: new name -> (lib, source, properties).
COPIES = {
    "BSC016N06NS": ("Transistor_FET", "Q_NMOS_SSSGD_AvalancheRated", {
        "Value": "BSC016N06NS",
        "Footprint": "Package_SON:Infineon_PG-TDSON-8_6.15x5.15mm",
        "Datasheet": "https://www.lcsc.com/datasheet/C454269.pdf",
        "Description": "60V 1.6mOhm N-MOSFET, PG-TDSON-8 FL (SuperSO8)",
        "LCSC": "C454269", "MPN": "BSC016N06NS", "Assembly": "JLC",
    }),
    "PESD2CAN": ("Power_Protection", "NUP2105L", {
        "Value": "PESD2CAN",
        "Footprint": "Package_TO_SOT_SMD:SOT-23",
        "Datasheet": "https://www.lcsc.com/datasheet/C907830.pdf",
        "Description": "CAN bus ESD protection, 2 lines, 24V Vrwm, SOT-23",
        "LCSC": "C907830", "MPN": "PESD2CAN", "Assembly": "JLC",
    }),
    "WSD4070DN": ("Transistor_FET", "Q_NMOS_SSSGD_AvalancheRated", {
        "Value": "WSD4070DN33",
        "Footprint": "nexus:PDFN3333-8_L3.1-W3.2-P0.65-LS3.4-BL",
        "Datasheet": "https://www.lcsc.com/datasheet/C719095.pdf",
        "Description": "40V 4.5mOhm N-MOSFET, DFN3x3-8L",
        "LCSC": "C719095", "MPN": "WSD4070DN33", "Assembly": "JLC",
    }),
    "0456025.ER": ("Device", "Fuse", {
        "Value": "25A",
        "Footprint": "nexus:FUSE-SMD_L10.1-W3.1",
        "Datasheet": "https://www.lcsc.com/datasheet/C315877.pdf",
        "Description": "Fuse 25A 125V very fast, Littelfuse NANO2 456",
        "LCSC": "C315877", "MPN": "0456025.ER", "Assembly": "SELF",
    }),
    "MWSA0603-100MT": ("Device", "L", {
        "Value": "10uH",
        "Footprint": "nexus:IND-SMD_L7.1-W6.6",
        "Datasheet": "https://www.lcsc.com/datasheet/C132141.pdf",
        "Description": "Power inductor 10uH 4.5A sat, 7x6.6mm shielded",
        "LCSC": "C132141", "MPN": "MWSA0603S-100MT", "Assembly": "JLC",
    }),
}

# Pin electrical types by pin number.
PIN_TYPES = {
    "LM74502DDFR": {"1": "input", "2": "power_in", "3": "no_connect",
                    "4": "passive", "5": "power_in", "6": "output",
                    "7": "input", "8": "passive"},
}

# Footprint pad fixes: footprint -> (pad size, pad x offsets).
# MWSA0603S recommended land pattern: I=2.35, J=3.7, H=3.5 (datasheet p.2).
PAD_FIX = {
    "IND-SMD_L7.1-W6.6": {"size": (2.35, 3.5), "x": {"1": -3.025, "2": 3.025}},
}

# Pad renumbering: all drain pads become "5", like KiCad's own power FETs,
# so the footprint matches the Q_NMOS_SSSGD symbol (S=1-3, G=4, D=5).
RENUMBER = {
    "PDFN3333-8_L3.1-W3.2-P0.65-LS3.4-BL": {"6": "5", "7": "5", "8": "5",
                                           "9": "5"},
}
COURTYARD_MARGIN = 0.25  # mm, IPC-7351 nominal

# Component body (x, y) in mm from the datasheets, centred on the origin.
# The courtyard covers pads + body; easyeda's F.Fab layer is not reliable.
BODY = {
    "PDFN3333-8_L3.1-W3.2-P0.65-LS3.4-BL": (3.2, 3.45),   # D max, E max
    "IND-SMD_L7.1-W6.6": (6.8, 7.3),                    # A, B max (MWSA0603S)
    "FUSE-SMD_L10.1-W3.1": (10.08, 3.05),               # 0456 20-30A
}


def top_blocks(text):
    """Yield (name, start, end) of top-level symbols in a KiCad 10 library."""
    for m in re.finditer(r'^\t\(symbol "([^"]+)"\n.*?^\t\)\n', text,
                         re.M | re.S):
        yield m.group(1), m.start(), m.end()


def get_block(text, name):
    for n, s, e in top_blocks(text):
        if n == name:
            return text[s:e]
    return None


def set_property(block, key, value):
    pat = re.compile(r'(\(property "' + re.escape(key) + r'" )"[^"]*"')
    if pat.search(block):
        return pat.sub(lambda m: m.group(1) + '"' + value + '"', block, 1)
    # add a hidden property after the last existing top-level property
    idx = block.rfind("\n\t\t(property ")
    end = block.find("\n\t\t)", idx) + len("\n\t\t)")
    prop = (f'\n\t\t(property "{key}" "{value}"\n\t\t\t(at 0 0 0)\n'
            f'\t\t\t(hide yes)\n\t\t\t(effects\n\t\t\t\t(font\n'
            f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)')
    return block[:end] + prop + block[end:]


def set_pin_types(block, types):
    def repl(m):
        num = re.search(r'\(number "([^"]+)"', m.group(0)).group(1)
        t = types.get(num)
        return m.group(0) if t is None else re.sub(
            r'^\(pin \w+', f"(pin {t}", m.group(0))
    return re.sub(r'\(pin \w+ \w+.*?\(number "[^"]+"', repl, block,
                  flags=re.S)


def copy_symbol(lib, src, new, props):
    text = (KICAD_SYM / f"{lib}.kicad_sym").read_text()
    block = get_block(text, src)
    parent = re.search(r'\(extends "([^"]+)"\)', block)
    if parent:  # flatten: take the parent's graphics, keep child's props
        base = get_block(text, parent.group(1))
        block = base.replace(f'"{parent.group(1)}', f'"{src}')
    block = block.replace(f'(symbol "{src}', f'(symbol "{new}')
    for k, v in props.items():
        block = set_property(block, k, v)
    return block


def fix_footprints():
    """Pad fixes, renumbering and courtyards on the KiCad 10 text format.

    pcbnew is only used read-only (bounding boxes): modifying footprints
    through the SWIG API crashes in KiCad 10.
    """
    import pcbnew
    subprocess.run(["kicad-cli", "fp", "upgrade", "--force", str(PRETTY)],
                   check=True, capture_output=True)
    for path in sorted(PRETTY.glob("*.kicad_mod")):
        name = path.stem
        t = path.read_text()

        def pad_block(m):
            blk = m.group(0)
            num = m.group(1)
            if name in PAD_FIX and num in PAD_FIX[name]["x"]:
                w, h = PAD_FIX[name]["size"]
                x = PAD_FIX[name]["x"][num]
                blk = re.sub(r"\(at [-\d.]+ ", f"(at {x} ", blk, count=1)
                blk = re.sub(r"\(size [\d.]+ [\d.]+\)",
                             f"(size {w} {h})", blk, count=1)
            if name in RENUMBER and num in RENUMBER[name]:
                blk = blk.replace(f'(pad "{num}"',
                                  f'(pad "{RENUMBER[name][num]}"', 1)
            return blk
        t = re.sub(r'^\t\(pad "([^"]*)".*?^\t\)\n', pad_block, t,
                   flags=re.M | re.S)
        # drop existing courtyard graphics
        t = re.sub(r'^\t\(fp_\w+\n.*?^\t\)\n',
                   lambda m: "" if '(layer "F.CrtYd")' in m.group(0)
                   else m.group(0), t, flags=re.M | re.S)
        path.write_text(t)

        # courtyard = bounding box of pads and component body + margin
        fp = pcbnew.FootprintLoad(str(PRETTY), name)
        xs, ys = [], []
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            xs += [pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetRight())]
            ys += [pcbnew.ToMM(b.GetTop()), pcbnew.ToMM(b.GetBottom())]
        if name not in BODY:
            sys.exit(f"no body size for footprint {name}: add it to BODY")
        bw, bh = BODY[name]
        xs += [-bw / 2, bw / 2]
        ys += [-bh / 2, bh / 2]
        m = COURTYARD_MARGIN
        x0, x1 = round(min(xs) - m, 2), round(max(xs) + m, 2)
        y0, y1 = round(min(ys) - m, 2), round(max(ys) + m, 2)
        rect = (f'\t(fp_rect\n\t\t(start {x0:.2f} {y0:.2f})\n'
                f'\t\t(end {x1:.2f} {y1:.2f})\n\t\t(stroke\n'
                f'\t\t\t(width 0.05)\n\t\t\t(type solid)\n\t\t)\n'
                f'\t\t(fill no)\n\t\t(layer "F.CrtYd")\n\t)\n')
        t = path.read_text()
        idx = t.rfind(")")
        path.write_text(t[:idx] + rect + t[idx:])


def main():
    subprocess.run(["kicad-cli", "sym", "upgrade", "--force", str(SYM)],
                   check=True, capture_output=True)
    text = SYM.read_text()
    text = text.replace('(property "LCSC Part"', '(property "LCSC"')

    keep = []
    for name, s, e in top_blocks(text):
        if name in DROP_SYMBOLS or name in COPIES:
            continue
        block = text[s:e]
        if name in FOOTPRINT:
            block = set_property(block, "Footprint", FOOTPRINT[name])
        if name in PIN_TYPES:
            block = set_pin_types(block, PIN_TYPES[name])
        block = set_property(block, "Assembly", "JLC")
        keep.append(block)
    for new, (lib, src, props) in COPIES.items():
        keep.append(copy_symbol(lib, src, new, props))
    # library skeleton (header + closing paren) without any symbol
    blocks = list(top_blocks(text))
    head = text[:blocks[0][1]] if blocks else text[:text.rfind(")")]
    SYM.write_text(head + "".join(keep) + ")\n")

    for stem in REJECTED:
        for f in [PRETTY / f"{stem}.kicad_mod", SHAPES / f"{stem}.step",
                  SHAPES / f"{stem}.wrl"]:
            f.unlink(missing_ok=True)

    fix_footprints()

    subprocess.run(["kicad-cli", "sym", "upgrade", "--force", str(SYM)],
                   check=True, capture_output=True)
    subprocess.run(["kicad-cli", "fp", "upgrade", "--force", str(PRETTY)],
                   check=True, capture_output=True)
    print("lib/nexus post-processed")


if __name__ == "__main__":
    sys.exit(main())
