#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial placement of the Nexus Tools Board (F5 step 1, concept A).

Board 140 x 90 mm (130 x 85 did not fit concept A, see docs/mechanical.md): power/USB/CAN on the left edge,
heater terminals at the bottom, filament ports at the top, thermistors on
the right. Functional blocks are packed into regions; fine placement is
done in KiCad afterwards.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "schgen"))
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))

import toolboard as sch  # noqa: E402
from pcbgen import Pcb  # noqa: E402

W, H = 140.0, 90.0
HOLE = 6.1           # hole centre from both edges (mechanical.md §2)
OVERHANG = 1.0       # connector front past the edge (M5)


# CLAUDE.md §6 net classes. Clearance 0.15 mm everywhere: enough for 24 V
# (IPC-2221 external: 0.1 mm) and needed for the 0.65 mm pitch TSOT-23-8.
NETCLASSES = {
    "Default": dict(track=0.2),
    "POWER_25A": dict(track=2.0, via=0.8, drill=0.4),
    "HEATER_CH": dict(track=2.0, via=0.8, drill=0.4),
    "POWER_LOGIC": dict(track=0.5),
    "ANALOG": dict(track=0.25),
    "USB": dict(track=0.2, dp_w=0.2, dp_g=0.15),
    "CAN": dict(track=0.2, dp_w=0.2, dp_g=0.2),
}
NETCLASS_PATTERNS = [
    ("POWER_25A", "+24V_IN"), ("POWER_25A", "+24V_HEATER"),
    ("POWER_25A", "/power_input/VIN_RAW"), ("POWER_25A", "/heater_cutoff/CUTOFF_SRC"),
    ("HEATER_CH", "HEATER_T*_N"), ("HEATER_CH", "/heaters/HEATER_T*_P"),
    ("POWER_LOGIC", "+5V"), ("POWER_LOGIC", "+3V3_*"), ("POWER_LOGIC", "/logic_power/*"),
    ("ANALOG", "THERM_*"), ("ANALOG", "/thermistors/*"), ("ANALOG", "VREF_A"),
    ("ANALOG", "RAIL_SENSE"), ("USB", "USB_D*"), ("CAN", "CAN*"),
]


def refs_by_key():
    b = sch.build()
    b.annotate()
    return {p.key: p.ref for s in b.sheets for p in s.parts}


def main():
    K = refs_by_key()
    r = lambda *keys: [K[k] for k in keys]
    pcb = Pcb("toolboard", ROOT / "scripts" / "pcbgen" / "template_4layer.kicad_pcb")
    pcb.outline(W, H)
    for i, (x, y) in enumerate([(HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)]):
        pcb.hole(f"H{i + 1}", x, y)

    # ---- left edge: USB-C, CAN IN, CAN OUT, XT60 (1.0 mm overhang)
    pcb.edge(K["J_USB"], "left", 15.0, OVERHANG, rot=270)
    pcb.edge(K["J_CAN_IN"], "left", 31.5, OVERHANG, rot=90)
    pcb.edge(K["J_CAN_OUT"], "left", 44.5, OVERHANG, rot=90)
    pcb.edge(K["J_XT60"], "left", 62.5, OVERHANG, rot=90)

    # ---- bottom edge: heater terminals, channel parts in a column above each
    for i in range(8):
        x = 24.0 + i * 11.25
        pcb.edge(K[f"J_H{i}"], "bottom", x, 0.0, rot=180)
        pcb.pack(r(f"Q_H{i}", f"F_H{i}", f"R_G{i}", f"R_GPD{i}", f"R_IN{i}",
                   f"R_LH{i}", f"D_LH{i}"), (max(x - 6.1, 19.2), 64.2, x + 5.0, 78.6), gap=0.4)

    # ---- top edge: filament ports (pitch 14 > 13.5 courtyard), networks below
    for i in range(8):
        x = 13.5 + i * 14.0
        pcb.edge(K[f"J_F{i}"], "top", x, -1.0, rot=0)
        pcb.pack(r(f"D_FR{i}", f"R_FSR{i}", f"R_FPR{i}", f"C_FR{i}",
                   f"D_FM{i}", f"R_FSM{i}", f"R_FPM{i}", f"C_FM{i}"),
                 (x - 1.5, 8.5, x + 12.0, 18.5), gap=0.3)

    # ---- right edge: LED port at the top, thermistor ports below (pitch 7 mm)
    pcb.edge(K["J_LED"], "right", 15.0, -1.0, rot=0)
    pcb.pack(r("U_LEDBUF", "C_LEDBUF", "R_LEDPD", "R_LEDSER", "F_LED", "C_LED",
               "D_LED5V", "D_LEDDIN"), (92.5, 19.0, 129.6, 24.4), gap=0.3)
    for i in range(8):
        y = 28.0 + i * 6.9
        pcb.edge(K[f"J_T{i}"], "right", y, -1.0, rot=0)
        pcb.pack(r(f"R_PU{i}", f"JP_PT{i}", f"R_PT{i}", f"D_TESD{i}",
                   f"C_TIN{i}", f"R_TS{i}", f"C_TADC{i}", f"D_TCL{i}"),
                 (108.6, y - 3.4, 130.3, y + 3.45), gap=0.25)

    # ---- power trunk: XT60 -> fuse -> cutoff FETs -> heater rail (left)
    pcb.pack(r("F_MAIN", "Q_CUT1", "Q_CUT2", "D_TVS", "U_CUTOFF", "C_IN1", "C_IN2",
               "C_VCAP", "C_VS", "R_EN_PD", "C_RAIL1", "C_RAIL2", "C_RAIL3", "C_RAIL4",
               "R_BLEED", "TP_24VIN", "TP_GND1", "TP_GATE", "TP_24VH"),
             (21.0, 46.8, 52.3, 63.8), gap=0.4)
    pcb.pack(r("C_BULK1"), (9.0, 71.6, 18.0, 80.3))
    pcb.pack(r("C_BULK2", "R_RS_TOP", "R_RS_BOT", "R_RS_SER", "C_RS", "D_RS",
               "TP_RS", "TP_GATE0", "TP_DRAIN0"), (91.5, 46.8, 108.0, 63.8), gap=0.3)

    # ---- logic power (5 V buck), LDOs + VREF, below the filament band
    pcb.pack(r("U_BUCK", "L_BUCK", "D_CATCH", "D_REV", "C_BIN1", "C_BIN2", "C_BIN3",
               "C_BOUT1", "C_BOUT2", "C_BOUT3", "R_UV1", "R_UV2", "R_RT", "R_COMP",
               "C_COMP", "C_COMP2", "C_BOOT", "R_FB1", "R_FB2", "TP_5V"),
             (24.0, 19.2, 56.0, 38.5), gap=0.4)
    pcb.pack(r("D_OR_5V", "D_OR_VBUS", "C_L1IN", "U_LDO_MCU", "C_L1OUT", "C_L1OUT2",
               "TP_3V3M", "C_L2IN", "U_LDO_AUX", "C_L2OUT", "TP_3V3A",
               "R_VREF", "C_VREF1", "C_VREF2", "TP_VREF", "TP_AGND", "TP_VBUS"),
             (56.5, 19.2, 92.0, 32.3), gap=0.3)

    # ---- USB and CAN support next to their connectors
    pcb.pack(r("U_USBESD", "R_CC1", "R_CC2", "R_SHIELD", "C_SHIELD"),
             (9.3, 19.2, 23.6, 24.1), gap=0.25, rot=90)
    pcb.pack(r("U_CAN", "D_CANESD", "C_CANVCC", "C_CANVIO", "R_TERM", "J_TERM",
               "TP_CANH", "TP_CANL"), (14.8, 25.9, 22.4, 50.3), gap=0.4)

    # ---- MCU in the middle, support around it
    pcb.place(K["U_MCU"], 74.0, 39.6, rot=0)
    pcb.pack(r("Y_MCU", "C_X1", "C_X2", "C_VDD1", "C_VDD2", "C_VBAT", "C_VREF3",
               "NT_AGND", "C_NRST", "R_BOOT"), (56.5, 32.6, 67.1, 46.6), gap=0.3)
    pcb.pack(r("SW_RESET", "SW_BOOT", "J_SWD", "JP_VFIL", "F_VFIL", "D_VFIL", "C_VFIL"),
             (81.2, 32.6, 108.4, 46.6), gap=0.4)
    pcb.pack(r("U_GATEBUF", "C_GATEBUF"), (52.8, 46.8, 91.0, 63.8), rot=90)

    # ---- diagnostic LEDs for the rails: bottom-right, next to the channel LEDs
    pcb.pack(r("R_L24VIN", "D_L24VIN", "R_LRAIL", "D_LRAIL", "R_L5V", "D_L5V",
               "R_L3V3", "D_L3V3", "R_LVBUS", "D_LVBUS", "R_LMCU", "D_LMCU"),
             (108.6, 87.5 - 6.0, 129.0, 89.4), gap=0.3)

    left = [x for x in pcb.unplaced()]
    if left:
        print("UNPLACED:", left)
    out = pcb.save(NETCLASSES, NETCLASS_PATTERNS)
    print(f"saved {out.relative_to(ROOT)}: {len(pcb.placed)} footprints")


if __name__ == "__main__":
    main()
