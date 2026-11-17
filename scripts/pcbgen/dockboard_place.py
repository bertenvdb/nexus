#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial placement of the Nexus Docks Board (F6 step 1, brought forward).

Board 100 x 70 mm, 2 layers (docs/mechanical.md §6): USB-C, CAN IN and XT30
on the left edge (1.0 mm overhang), 9 fan ports along the top with their
channel parts below, LED port / buttons / SWD on the right, the three power
blocks in the bottom row and the diagnostic LEDs along the bottom edge.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "schgen"))
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))

import dockboard as sch  # noqa: E402
from pcbgen import Pcb  # noqa: E402

W, H = 100.0, 70.0
HOLE = 6.1
OVERHANG = 1.0
FAN_X0, FAN_PITCH = 16.0, 7.2

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
    pcb = Pcb("dockboard", ROOT / "scripts" / "pcbgen" / "template_4layer.kicad_pcb", layers=2)
    tb = pcb.board.GetTitleBlock()
    tb.SetTitle("Nexus Docks Board")
    pcb.outline(W, H)
    for i, (x, y) in enumerate([(HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)]):
        pcb.hole(f"H{i + 1}", x, y)

    # ---- left edge: USB-C, CAN IN, XT30 (1.0 mm overhang, as the tool board)
    pcb.edge(K["J_USB"], "left", 16.0, OVERHANG, rot=270)
    pcb.edge(K["J_CAN_IN"], "left", 31.0, OVERHANG, rot=90)
    pcb.edge(K["J_XT30"], "left", 50.0, OVERHANG, rot=90)

    # ---- top edge: 9 fan ports, channel parts in a column below each
    for i in range(9):
        x = FAN_X0 + i * FAN_PITCH
        pcb.edge(K[f"J_FAN{i}"], "top", x, -1.0, rot=90)
        pcb.pack(r(f"Q_F{i}", f"D_FFB{i}", f"R_FG{i}", f"R_FGPD{i}"),
                 (x - 3.5, 9.3, x + 3.5, 21.6), gap=0.3)

    # ---- middle row: USB/CAN support, gate buffers, MCU, buttons/SWD
    pcb.pack(r("U_USBESD", "R_CC1", "R_CC2", "R_SHIELD", "C_SHIELD"),
             (13.0, 22.0, 26.0, 26.6), gap=0.3, rot=90)
    pcb.pack(r("U_CAN", "D_CANESD", "C_CANVCC", "C_CANVIO", "R_TERM", "J_TERM"),
             (13.0, 27.0, 24.0, 41.6), gap=0.4)
    pcb.pack(r("U_GATEBUF", "U_GATE8", "C_GATEBUF", "C_GATE8") + [K[f"R_FIN{i}"] for i in range(9)],
             (24.5, 22.0, 46.5, 41.6), rot=270, gap=0.4)
    pcb.place(K["U_MCU"], 54.5, 31.5, rot=0)
    pcb.pack(r("Y_MCU", "C_X1", "C_X2", "C_VDD1", "C_VDD2", "C_VBAT", "C_VREF1", "C_VREF3",
               "R_VREF", "C_NRST", "R_BOOT"), (61.8, 22.0, 70.5, 41.6), gap=0.3)
    pcb.pack(r("SW_RESET", "SW_BOOT", "J_SWD", "TP_3V3", "TP_5V", "TP_VBUS",
               "TP_CANH", "TP_CANL"), (71.0, 22.0, 98.5, 41.6), gap=0.5)

    # ---- right edge: LED port
    pcb.edge(K["J_LED"], "right", 52.0, -1.0, rot=90)
    pcb.pack(r("U_LEDBUF", "C_LEDBUF", "R_LEDPD", "R_LEDSER", "F_LED", "C_LED",
               "D_LED5V", "D_LEDDIN"), (82.5, 42.0, 91.6, 60.0), gap=0.3)

    # ---- bottom row: power input + reverse polarity, 5 V buck, fan buck
    pcb.pack(r("F_IN", "D_TVS", "U_RPP", "Q_RPP", "C_BULK", "C_VCAP", "C_VS", "C_INT1",
               "C_INT2", "TP_24VINT", "TP_GND"), (17.0, 42.0, 40.0, 65.8), gap=0.4)
    pcb.pack(r("U_BUCK", "L_BUCK", "D_CATCH", "C_BIN1", "C_BIN2", "C_BIN3", "C_BOUT1",
               "C_BOUT2", "C_BOUT3", "R_UV1", "R_UV2", "R_RT", "R_COMP", "C_COMP", "C_COMP2",
               "C_BOOT", "R_FB1", "R_FB2", "D_OR_5V", "D_OR_VBUS", "C_L1IN", "U_LDO",
               "C_L1OUT", "C_L1OUT2"), (40.4, 41.8, 61.4, 66.0), gap=0.35)
    pcb.pack(r("U_FBUCK", "L_FBUCK", "D_FCATCH", "C_FIN1", "C_FIN2", "C_FIN3", "C_FOUT1",
               "C_FOUT2", "C_FOUT3", "C_FOUT4", "R_FUV1", "R_FUV2", "R_FRT", "R_FCOMP",
               "C_FCOMP", "C_FCOMP2", "C_FBOOT", "R_FFB_A", "R_FFB_B", "R_FFB_C",
               "JP_FVSEL", "JP_FRAIL", "C_FRAIL", "TP_FRAIL"), (61.8, 41.8, 82.3, 66.0), gap=0.35)

    # ---- diagnostic LEDs along the bottom edge
    pcb.pack(r("R_L24VIN", "D_L24VIN", "R_LFRAIL", "D_LFRAIL", "R_L5V", "D_L5V",
               "R_L3V3", "D_L3V3", "R_LVBUS", "D_LVBUS", "R_LMCU", "D_LMCU"),
             (10.5, 66.2, 89.5, 69.6), gap=0.6, sort=False)

    left = pcb.unplaced()
    if left:
        print("UNPLACED:", left)
    out = pcb.save(NETCLASSES, NETCLASS_PATTERNS)
    print(f"saved {out.relative_to(ROOT)}: {len(pcb.placed)} footprints")


if __name__ == "__main__":
    main()
