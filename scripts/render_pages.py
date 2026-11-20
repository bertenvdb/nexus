#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Photo-style 3D renders of both boards for the product page (docs/img/).

  scripts/render_pages.py [--views top,iso] [--width 2400]

KiCad 10.0.8's library has no 3D model for the XT60PW-M, XT30PW-M, the HRO
TYPE-C-31-M-12 USB-C, the horizontal Micro-Fit 43045-0400 (open item 30), the
Infineon PG-TDSON-8 and the XKB TS-1187A button; the TPS54360B's footprint
points to a model name that does not exist. This script adds the EasyEDA/LCSC
models (lib/nexus.3dshapes, fetched with easyeda2kicad) or the library model
of the same package to a copy of each board in out/ and renders that copy with
KiCad's raytracer. The boards themselves and the production files are not
touched.

Models: the VRML exports of easyeda2kicad (gzipped, .wrz); its STEP exports
have a different origin and do not fit. In the XT30 export every material had
"transparency 1.0" (fully transparent in KiCad): set to 0.0. Model placement: the EasyEDA model
sits on the EasyEDA footprint; our boards use the KiCad library footprint. The rotation (multiple of 90 degrees) and
offset that map the EasyEDA pads onto the KiCad pads (all common pads, 0.000 mm
error) are applied to the model: footprint-local offset (x, y) with y down,
written as KiCad model offset (x, -y), model rotation z = EasyEDA rz + angle
(checked on the XT60, the only connector turned by 90 degrees).
Checked by putting every model part below the board surface (pins, pegs,
shell legs) into a drilled hole of the footprint.
"""
import argparse
import pathlib
import subprocess

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "lib" / "nexus.3dshapes"

# KiCad footprint name: (model file, angle (y-down, clockwise), tx, ty, EasyEDA rz)
FIXES = {
    "AMASS_XT60PW-M_1x02_P7.20mm_Horizontal": ("CONN-TH_XT60PW-M.wrz", 90, 3.6, -3.0, 0),
    "AMASS_XT30PW-M_1x02_P2.50mm_Horizontal": ("CONN-TH_XT30PW-M.wrz", 180, -2.5, -5.0, 0),
    # USB-C: the pads fit at ty -1.575, but the EasyEDA model sits 2.37 mm off its
    # own footprint; ty from the shell legs in their slots (0.01 mm)
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": ("USB-C_SMD-TYPE-C-31-M-12_1.wrz", 0, 0.0, 0.795, 180),
    "Molex_Micro-Fit_3.0_43045-0400_2x02_P3.00mm_Horizontal": ("CONN-TH_0430450400.wrz", 180, 1.5, 1.5, 0),
    "Infineon_PG-TDSON-8_6.15x5.15mm": ("PG-TDSON-8-FL_L5.0-W6.0-H1.0-P1.27-LS6.2-BL.wrz", 90, -0.01, 0.0, 0),
    "SW_Push_1P1T_XKB_TS-1187A": ("SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5.wrz", 0, 0.0, 0.0, 0),
    # same package in the KiCad library under another name
    "TI_SO-PowerPAD-8_ThermalVias": ("/usr/share/kicad/3dmodels/Package_SO.3dshapes/TI_SO-PowerPAD-8.step", 0, 0.0, 0.0, 0),
}

VIEWS = {   # name: extra kicad-cli render arguments
    "top": ["--side", "top"],
    "iso": ["--side", "top", "--perspective", "--rotate", "-35,0,-25", "--zoom", "0.9"],
}


def with_models(board):
    src = ROOT / board / f"{board}.kicad_pcb"
    b = pcbnew.LoadBoard(str(src))
    n = 0
    for fp in b.GetFootprints():
        models = fp.Models()
        fix = FIXES.get(str(fp.GetFPID().GetLibItemName()))
        if not fix:
            # the copy lives in out/render: project-relative model paths must be absolute
            keep = []
            for m in models:
                c = pcbnew.FP_3DMODEL()
                for k in ("m_Offset", "m_Rotation", "m_Scale", "m_Opacity", "m_Show"):
                    setattr(c, k, getattr(m, k))
                c.m_Filename = m.m_Filename.replace("${KIPRJMOD}", str(ROOT / board))
                keep.append(c)
            models.clear()
            for c in keep:
                models.push_back(c)
            continue
        name, angle, tx, ty, rz = fix
        models.clear()
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = str(MODELS / name)       # absolute names stay as they are
        m.m_Offset = pcbnew.VECTOR3D(tx, -ty, 0.0)
        m.m_Rotation = pcbnew.VECTOR3D(0.0, 0.0, (rz + angle) % 360)   # KiCad: +z turns clockwise in the footprint view
        m.m_Scale = pcbnew.VECTOR3D(1.0, 1.0, 1.0)
        models.push_back(m)
        n += 1
    out = ROOT / "out" / "render" / f"{board}.render.kicad_pcb"
    out.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(out), b)
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", default="top,iso")
    ap.add_argument("--width", type=int, default=2400)
    a = ap.parse_args()
    for board in ("toolboard", "dockboard"):
        pcb, n = with_models(board)
        for v in a.views.split(","):
            png = ROOT / "out" / "render" / f"{board}-{v}.png"
            subprocess.run(["kicad-cli", "pcb", "render", *VIEWS[v], "--quality", "high", "--floor",
                            "--width", str(a.width), "--height", str(int(a.width * 0.66)),
                            "--background", "transparent", "-o", str(png), str(pcb)],
                           check=True, capture_output=True)
            print(f"{board}: {n} models added, {png.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
