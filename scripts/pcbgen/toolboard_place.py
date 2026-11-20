#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial placement of the Nexus Tools Board (F5 step 1, concept A).

Board 140 x 90 mm (130 x 85 did not fit concept A, see docs/mechanical.md): power/USB/CAN on the left edge,
heater terminals at the bottom, filament ports at the top, thermistors on
the right. Functional blocks are packed into regions; fine placement is
done in KiCad afterwards.
"""
import os
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
CH_X0, CH_PITCH = 26.0, 11.22   # heater terminal pin 1 positions
BAND = (24.0, 58.8, 110.0, 65.2)  # +24V_HEATER rail band (x0, y0, x1, y1)


# Logic-area layout variants (F5 step 3 re-placement, 2026-11-18). Regions are
# (x0, y0, x1, y1) in board mm; "mcu" is (x, y, rotation).
VARIANTS = {
    # F5 step 1 placement (approved 2026-11-17)
    "orig": dict(buck=(24.0, 19.2, 56.0, 38.5), ldo=(56.5, 19.2, 92.0, 32.3),
                 mcu=(74.0, 39.6, 0), xtal=(56.5, 32.6, 67.1, 46.6),
                 swd=(81.2, 32.6, 108.4, 46.6), gatebuf=(52.5, 46.7, 91.0, 58.75)),
    # fan-out ring >= 3.5 mm around the MCU (routing, 2026-11-19); applied to
    # the approved placement by toolboard_logic_replace.py
    "fan": dict(buck=(24.0, 19.2, 56.0, 38.5), ldo=(56.5, 19.2, 92.0, 25.6),
                mcu=(74.0, 36.0, 0), xtal=(56.5, 26.0, 63.6, 46.0),
                swd=(84.4, 25.8, 108.4, 38.5), gatebuf=(52.5, 46.4, 91.0, 58.6)),
}
DEFAULT_VARIANT = "orig"

# CLAUDE.md §6 net classes. Clearance 0.15 mm everywhere: enough for 24 V
# (IPC-2221 external: 0.1 mm) and needed for the 0.65 mm pitch TSOT-23-8.
NETCLASSES = {
    "Default": dict(track=0.2),
    "POWER_25A": dict(track=0.8, via=0.8, drill=0.4),   # 25 A runs in zones
    "HEATER_CH": dict(track=2.0, via=0.8, drill=0.4),
    "POWER_LOGIC": dict(track=0.5),
    "SUPPLY_3V3": dict(track=0.3),
    "ANALOG": dict(track=0.25),
    "USB": dict(track=0.2, dp_w=0.2, dp_g=0.15),
    "CAN": dict(track=0.2, dp_w=0.2, dp_g=0.2),
}
NETCLASS_PATTERNS = [
    ("POWER_25A", "+24V_IN"), ("POWER_25A", "+24V_HEATER"),
    ("POWER_25A", "/power_input/VIN_RAW"), ("POWER_25A", "/heater_cutoff/CUTOFF_SRC"),
    ("HEATER_CH", "HEATER_T*_N"), ("HEATER_CH", "/heaters/HEATER_T*_P"),
    ("POWER_LOGIC", "+5V"), ("SUPPLY_3V3", "+3V3_*"), ("POWER_LOGIC", "/logic_power/*"),
    ("ANALOG", "THERM_*"), ("ANALOG", "/thermistors/*"), ("ANALOG", "VREF_A"),
    ("ANALOG", "RAIL_SENSE"), ("USB", "USB_D*"), ("CAN", "CAN*"),
]


def refs_by_key():
    b = sch.build()
    b.annotate()
    return {p.key: p.ref for s in b.sheets for p in s.parts}


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def zones(pcb):
    """F5 step 2: power and ground copper (docs/calculations.md §2.1).

    In1 = GND plane with an AGND island (thermistor networks + neck to the
    star point). Heater rail band on F.Cu + In2 (B.Cu stays free so the gate
    signals can cross). Trunk XT60 -> fuse -> Q1 -> Q2 -> feed on F.Cu, In2
    and B.Cu.
    """
    import pcbnew
    F, I1, I2, B = pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu
    # In1 is the GND/AGND plane: no tracks (Freerouting gets a wire keepout and
    # reaches it with vias). In2 carries the power zones (also wire keepouts in
    # the router export) and signals elsewhere.
    pcb.board.SetLayerType(I1, pcbnew.LT_POWER)   # GND plane only
    pcb.board.SetLayerType(I2, pcbnew.LT_SIGNAL)  # power zones + signals
    # ground plane and AGND island
    # AGND island (thermistor networks + neck to the star point at the MCU);
    # the GND plane leaves a 0.5 mm gap around it, so the two never overlap
    # (Freerouting does not know zone priorities).
    island = [(59.0, 39.0), (105.5, 39.0), (105.5, 23.5), (W, 23.5),
              (W, 81.0), (105.5, 81.0), (105.5, 42.5), (59.0, 42.5)]
    g = 0.5
    gnd = [(0, 0), (W, 0), (W, 23.5 - g), (105.5 - g, 23.5 - g), (105.5 - g, 39.0 - g),
           (59.0 - g, 39.0 - g), (59.0 - g, 42.5 + g), (105.5 - g, 42.5 + g),
           (105.5 - g, 81.0 + g), (W, 81.0 + g), (W, H), (0, H)]
    pcb.zone("GND", I1, gnd, priority=0, name="GND plane")
    pcb.zone("AGND", I1, island, priority=1, name="AGND island")
    # trunk: VIN_RAW (XT60 pin 2 (+) -> fuse pad 1)
    for L in (F, I2, B):
        pcb.zone("/power_input/VIN_RAW", L, rect(12.5, 59.6, 23.4, 65.2), priority=2)
    for x, y in [(18.6, 61.0), (18.6, 63.6), (20.0, 64.65), (21.3, 64.65), (22.6, 64.65)]:
        pcb.via("/power_input/VIN_RAW", x, y, 0.8, 0.4)
    # +24V_IN: fuse pad 2 -> Q1 drain (and > 4 cm2 of copper for Q1)
    pcb.zone("+24V_IN", F, rect(19.4, 49.6, 28.9, 55.9), priority=2)
    for L in (I2, B):
        pcb.zone("+24V_IN", L, rect(19.0, 36.0, 28.9, 55.9), priority=2)
    for x in (20.0, 21.5, 23.0, 24.5, 26.0, 27.5):
        for y in (49.95, 55.45):
            pcb.via("+24V_IN", x, y, 0.8, 0.4)
    # CUTOFF_SRC between the two FETs (short, F.Cu only)
    pcb.zone("/heater_cutoff/CUTOFF_SRC", F,
             [(29.0, 51.45), (31.2, 51.45), (31.2, 50.2), (32.95, 50.2), (32.95, 53.95),
              (30.9, 53.95), (30.9, 55.2), (29.0, 55.2)], priority=2)
    # +24V_HEATER: Q2 drain -> feed region (C_BULK1) -> rail band
    x0, y0, x1, y1 = BAND
    feed = [(33.25, 49.6), (50.3, 49.6), (50.3, y0), (x1, y0), (x1, y1),
            (x0, y1), (x0, y0), (33.25, y0)]
    pcb.zone("+24V_HEATER", F, feed, priority=2, name="heater rail band")
    pcb.zone("+24V_HEATER", I2, [(33.25, 49.6), (50.3, 49.6), (50.3, 57.6), (x1, 57.6),
                                 (x1, 67.0), (x0, 67.0), (x0, 57.6), (33.25, 57.6)],
             priority=2, name="heater rail band In2")
    pcb.zone("+24V_HEATER", B, rect(33.25, 49.6, 50.3, y0), priority=2)
    for x in (39.0, 40.2):
        for y in (50.2, 51.5, 52.8, 54.1, 55.4):
            pcb.via("+24V_HEATER", x, y, 0.8, 0.4)
    rail_caps = (54.0, 70.0, 86.0, 101.0)
    for i in range(int((x1 - x0 - 2) / 3.0) + 1):
        x = x0 + 1.0 + i * 3.0
        if x <= 104.0 and all(abs(x - c) > 2.0 for c in rail_caps):
            pcb.via("+24V_HEATER", x, y0 + 0.6, 0.8, 0.4)


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
    # XT60 pin 2 (+) at y 62.5 (trunk start), pin 1 (-) 7.2 mm lower (fixed 2026-11-20)
    pcb.edge(K["J_XT60"], "left", 69.7, OVERHANG, rot=90)

    # ---- bottom edge: heater terminals; per channel fixed positions:
    #      fuse under the heater rail band (pad 1 up), MOSFET above the
    #      HEATER- pin (drain down), gate R above it, LED + R right of the fuse.
    for i in range(8):
        x = CH_X0 + i * CH_PITCH
        xq = x - 5.08
        pcb.edge(K[f"J_H{i}"], "bottom", x, 0.0, rot=180)
        pcb.place(K[f"F_H{i}"], x, 66.5, rot=270)
        pcb.place(K[f"Q_H{i}"], xq, 72.0, rot=180)
        pcb.place(K[f"R_G{i}"], xq, 67.0, rot=0)
        pcb.place(K[f"R_GPD{i}"], xq, 68.9, rot=0)
        pcb.place(K[f"R_LH{i}"], x + 2.7, 70.5, rot=90)
        pcb.place(K[f"D_LH{i}"], x + 2.7, 74.6, rot=90)

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

    # ---- power trunk (CLAUDE.md §6.1): XT60 + -> 25 A fuse (vertical) ->
    #      Q1 (drain left) -> Q2 (drain right) -> down into the heater rail band
    pcb.place(K["F_MAIN"], 21.3, 57.4, rot=90)
    pcb.place(K["Q_CUT1"], 27.1, 52.7, rot=180)
    pcb.place(K["Q_CUT2"], 35.0, 52.7, rot=0)
    pcb.pack(r("C_BULK1"), (40.5, 49.8, 50.0, 58.6))
    pcb.pack(r("U_CUTOFF", "C_VCAP", "C_VS", "R_EN_PD", "TP_GATE", "D_TVS", "C_IN1",
               "C_IN2", "TP_24VIN", "TP_GND1", "TP_24VH", "R_BLEED"),
             (22.8, 39.0, 56.0, 49.4), gap=0.4)
    for i, x in enumerate([54.0, 70.0, 86.0, 101.0]):     # in the band
        pcb.place(K[f"C_RAIL{i + 1}"], x, 61.6, rot=270)
    pcb.pack(r("C_BULK2", "R_RS_TOP", "R_RS_BOT", "R_RS_SER", "C_RS", "D_RS", "TP_RS"),
             (91.5, 46.8, 108.0, 58.4), gap=0.3)
    pcb.pack(r("TP_GATE0", "TP_DRAIN0"), (9.6, 75.6, 17.5, 79.4), gap=0.6)   # below the XT60

    # ---- logic area: 5 V buck, LDOs + VREF, MCU with support, gate buffer.
    #      Regions per layout variant (VARIANTS, env TB_VARIANT).
    if "TB_VARIANT_JSON" in os.environ:          # placement trials
        import json
        V = json.loads(os.environ["TB_VARIANT_JSON"])
    else:
        V = VARIANTS[os.environ.get("TB_VARIANT", DEFAULT_VARIANT)]
    pcb.pack(r("U_BUCK", "L_BUCK", "D_CATCH", "D_REV", "C_BIN1", "C_BIN2", "C_BIN3",
               "C_BOUT1", "C_BOUT2", "C_BOUT3", "R_UV1", "R_UV2", "R_RT", "R_COMP",
               "C_COMP", "C_COMP2", "C_BOOT", "R_FB1", "R_FB2", "TP_5V"),
             V["buck"], gap=0.4)
    pcb.pack(r("D_OR_5V", "D_OR_VBUS", "C_L1IN", "U_LDO_MCU", "C_L1OUT", "C_L1OUT2",
               "TP_3V3M", "C_L2IN", "U_LDO_AUX", "C_L2OUT", "TP_3V3A",
               "R_VREF", "C_VREF1", "C_VREF2", "TP_VREF", "TP_AGND", "TP_VBUS"),
             V["ldo"], gap=0.3)

    # ---- USB and CAN support next to their connectors
    pcb.pack(r("U_USBESD", "R_CC1", "R_CC2", "R_SHIELD", "C_SHIELD"),
             (9.3, 19.2, 23.6, 24.1), gap=0.25, rot=90)
    pcb.pack(r("U_CAN", "D_CANESD", "C_CANVCC", "C_CANVIO", "R_TERM", "J_TERM",
               "TP_CANH", "TP_CANL"), (14.8, 25.9, 22.4, 50.3), gap=0.4)

    # ---- MCU with its support
    pcb.place(K["U_MCU"], *V["mcu"])
    pcb.pack(r("Y_MCU", "C_X1", "C_X2", "C_VDD1", "C_VDD2", "C_VBAT", "C_VREF3",
               "NT_AGND", "C_NRST", "R_BOOT"), V["xtal"], gap=0.3)
    pcb.pack(r("SW_RESET", "SW_BOOT", "J_SWD", "JP_VFIL", "F_VFIL", "D_VFIL", "C_VFIL"),
             V["swd"], gap=0.4)
    pcb.pack(r("U_GATEBUF", "C_GATEBUF") + [K[f"R_IN{i}"] for i in range(8)],
             V["gatebuf"], rot=V.get("gatebuf_rot", 270), gap=0.4)

    # ---- diagnostic LEDs for the rails: bottom-right, next to the channel LEDs
    pcb.pack(r("R_L24VIN", "D_L24VIN", "R_LRAIL", "D_LRAIL", "R_L5V", "D_L5V",
               "R_L3V3", "D_L3V3", "R_LVBUS", "D_LVBUS", "R_LMCU", "D_LMCU"),
             (108.6, 87.5 - 6.0, 129.0, 89.4), gap=0.3)

    zones(pcb)

    left = [x for x in pcb.unplaced()]
    if left:
        print("UNPLACED:", left)
    pcb.fill_zones()
    out = pcb.save(NETCLASSES, NETCLASS_PATTERNS)
    print(f"saved {out.relative_to(ROOT)}: {len(pcb.placed)} footprints")


if __name__ == "__main__":
    main()
