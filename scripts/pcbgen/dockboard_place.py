#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial placement of the Nexus Docks Board (F6 step 1, brought forward).

As small as possible, parts on the top side only, 4 layers (Berten,
2026-11-17): USB-C, CAN IN and XT30 on the left edge (1.0 mm overhang); the
vertical fan and LED connectors may sit anywhere, so the 9 fan ports form a
3 x 3 block top-right with their channel parts below; logic in the middle,
the three power blocks at the bottom.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "schgen"))
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))

import dockboard as sch  # noqa: E402
from pcbgen import Pcb  # noqa: E402

import os
W = float(os.environ.get("DOCK_W", "88"))
H = float(os.environ.get("DOCK_H", "62"))
HOLE = 6.1
OVERHANG = 1.0

NETCLASSES = {
    "Default": dict(track=0.2),
    "POWER_IN": dict(track=1.5, via=0.8, drill=0.4),
    "FAN_CH": dict(track=0.8),
    "POWER_LOGIC": dict(track=0.5),
    "SUPPLY_3V3": dict(track=0.3),
    "USB": dict(track=0.2, dp_w=0.2, dp_g=0.15),
    "CAN": dict(track=0.2, dp_w=0.2, dp_g=0.2),
}
NETCLASS_PATTERNS = [
    ("POWER_IN", "+24V_IN"), ("POWER_IN", "+24V_INT"), ("POWER_IN", "/power_input/VIN_RAW"),
    ("POWER_IN", "FAN_RAIL"), ("POWER_IN", "/fan_rail/FAN_BUCK"),
    ("FAN_CH", "/fans/FAN*_N"), ("FAN_CH", "FAN*_N"),
    ("POWER_LOGIC", "+5V"), ("POWER_LOGIC", "/logic_power/*"), ("POWER_LOGIC", "/fan_rail/FBK_SW"),
    ("SUPPLY_3V3", "+3V3"), ("USB", "USB_D*"), ("CAN", "CAN*"),
]


def refs_by_key():
    b = sch.build()
    b.annotate()
    return {p.key: p.ref for s in b.sheets for p in s.parts}


def main():
    K = refs_by_key()
    r = lambda *keys: [K[k] for k in keys]
    pcb = Pcb("dockboard", ROOT / "scripts" / "pcbgen" / "template_4layer.kicad_pcb", layers=4)
    tb = pcb.board.GetTitleBlock()
    tb.SetTitle("Nexus Docks Board")
    pcb.outline(W, H)
    for i, (x, y) in enumerate([(HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)]):
        pcb.hole(f"H{i + 1}", x, y)

    # ---- left edge: USB-C, CAN IN, XT30 (1.0 mm overhang, as the tool board)
    # stacked between the corner-hole keep-outs (hole courtyard + 0.3 mm),
    # remaining space shared equally
    stack = [("J_USB", 270), ("J_CAN_IN", 90), ("J_XT30", 90)]
    spans = []
    for key, rot in stack:
        fp = pcb.edge(K[key], "left", 0.0, OVERHANG, rot=rot)
        b0 = pcb.crt_box(fp)
        spans.append((b0[1], b0[3]))              # y extent relative to `along` = 0
    top, bottom = HOLE + 4.0, H - HOLE - 4.0
    total = sum(s1 - s0 for s0, s1 in spans)
    g = (bottom - top - total) / (len(stack) + 1)
    if g < 0.3:
        raise RuntimeError(f"left edge too short: need {total + 1.2 + 2 * (HOLE + 4.0):.1f} mm")
    y = top + g
    for (key, rot), (s0, s1) in zip(stack, spans):
        pcb.edge(K[key], "left", y - s0, OVERHANG, rot=rot)
        y += (s1 - s0) + g
    obstacles = [pcb.crt_box(pcb.fps[K[k]]) for k in ("J_USB", "J_CAN_IN", "J_XT30")]
    obstacles += [(x - 4.0, y - 4.0, x + 4.0, y + 4.0) for x, y in
                  [(HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)]]

    # ---- functional blocks, each packed compactly, then packed on the board
    B = pcb.block

    def near(blk, x, y):
        blk["near"] = (x, y)
        return blk
    # targets: next to their connector / their neighbours (routing)
    blocks = [near(B(r(f"J_FAN{i}", f"Q_F{i}", f"D_FFB{i}", f"R_FG{i}", f"R_FGPD{i}"),
                     widths=(9, 10, 11, 12)), W - 8 - 11 * (i % 3), 10 + 12 * (i // 3))
              for i in range(9)]
    blocks += [
        near(B(r("U_MCU", "Y_MCU", "C_X1", "C_X2", "C_VDD1", "C_VDD2", "C_VBAT", "C_VREF1",
                 "C_VREF3", "R_VREF", "C_NRST", "R_BOOT", "SW_RESET", "SW_BOOT", "J_SWD",
                 "TP_3V3", "TP_5V"), first=K["U_MCU"], widths=(18, 20, 22, 24, 26)), 30, 30),
        near(B(r("U_GATEBUF", "U_GATE8", "C_GATEBUF", "C_GATE8") + [K[f"R_FIN{i}"] for i in range(9)]),
             46, 30),
        near(B(r("U_USBESD", "R_CC1", "R_CC2", "R_SHIELD", "C_SHIELD", "TP_VBUS")), 15, 13),
        near(B(r("U_CAN", "D_CANESD", "C_CANVCC", "C_CANVIO", "R_TERM", "J_TERM", "TP_CANH",
                 "TP_CANL")), 18, 26),
        near(B(r("F_IN", "D_TVS", "U_RPP", "Q_RPP", "C_BULK", "C_VCAP", "C_VS", "C_INT1",
                 "C_INT2", "TP_24VINT", "TP_GND")), 20, 46),
        near(B(r("U_BUCK", "L_BUCK", "D_CATCH", "C_BIN1", "C_BIN2", "C_BIN3", "C_BOUT1",
                 "C_BOUT2", "C_BOUT3", "R_UV1", "R_UV2", "R_RT", "R_COMP", "C_COMP", "C_COMP2",
                 "C_BOOT", "R_FB1", "R_FB2", "D_OR_5V", "D_OR_VBUS", "C_L1IN", "U_LDO",
                 "C_L1OUT", "C_L1OUT2")), 32, 50),
        near(B(r("U_FBUCK", "L_FBUCK", "D_FCATCH", "C_FIN1", "C_FIN2", "C_FIN3", "C_FOUT1",
                 "C_FOUT2", "C_FOUT3", "C_FOUT4", "R_FUV1", "R_FUV2", "R_FRT", "R_FCOMP",
                 "C_FCOMP", "C_FCOMP2", "C_FBOOT", "R_FFB_A", "R_FFB_B", "R_FFB_C",
                 "JP_FVSEL", "JP_FRAIL", "C_FRAIL", "TP_FRAIL")), 50, 50),
        near(B(r("J_LED", "U_LEDBUF", "C_LEDBUF", "R_LEDPD", "R_LEDSER", "F_LED", "C_LED",
                 "D_LED5V", "D_LEDDIN")), W - 14, H - 10),
        B(r("R_L24VIN", "D_L24VIN", "R_LFRAIL", "D_LFRAIL", "R_L5V", "D_L5V",
            "R_L3V3", "D_L3V3", "R_LVBUS", "D_LVBUS", "R_LMCU", "D_LMCU")),
    ]
    pcb.place_blocks(blocks, (0.6, 0.6, W - 0.6, H - 0.6), obstacles, gap=0.6)

    left = pcb.unplaced()
    if left:
        print("UNPLACED:", left)
    out = pcb.save(NETCLASSES, NETCLASS_PATTERNS)
    print(f"saved {out.relative_to(ROOT)}: {len(pcb.placed)} footprints")


if __name__ == "__main__":
    main()
