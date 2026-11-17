# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Tools Board schematic description (F3).

Run scripts/build_schematic.py toolboard to regenerate, verify, run ERC and
export PDFs. Values: docs/design/*, docs/calculations.md, docs/pinout-toolboard.md.
"""
from schgen import Board
from parts import place, two

POWER_NETS = {"+24V_IN", "+24V_HEATER", "+5V", "+3V3_MCU", "+3V3_AUX",
              "VREF_A", "VBUS"}


def power_input(b):
    s = b.sheet("power_input", "24V input: XT60, main fuse, TVS")
    place(s, "J_XT60", "XT60", (50.8, 101.6), {"1": "VIN_RAW", "2": "GND"}, rot=180)
    two(s, "F_MAIN", "FUSE25", 88.9, 101.6, "VIN_RAW", "+24V_IN")
    two(s, "D_TVS", "SMBJ30CA", 116.84, 101.6, "+24V_IN", "GND")
    two(s, "C_IN1", "C10u50", 139.7, 101.6, "+24V_IN", "GND")
    two(s, "C_IN2", "C100n", 157.48, 101.6, "+24V_IN", "GND")
    place(s, "TP_24VIN", "TP", (180.34, 96.52), {"1": "+24V_IN"})
    place(s, "TP_GND1", "TP", (195.58, 96.52), {"1": "GND"})
    place(s, "FLG_24VIN", "FLAG", (210.82, 96.52), {"1": "+24V_IN"})
    place(s, "FLG_GND", "FLAG", (226.06, 96.52), {"1": "GND"})
    s.text("XT60 male on the board (PSU cable carries the female plug).\n"
           "Main fuse 25 A very fast, hand-soldered, not user-replaceable\n"
           "(last safety net, design 11 §3).\n"
           "SMBJ30CA bidirectional: does not conduct on reverse polarity.\n"
           "No electrolytic here: it would see reverse polarity.\n"
           "Bulk electrolytics sit on +24V_HEATER, after the cutoff.",
           (40.64, 139.7))


def heater_cutoff(b):
    s = b.sheet("heater_cutoff", "Heater cutoff (AD-10), rail sense (AD-13), heater rail bulk")
    # LM74502 controller
    place(s, "U_CUTOFF", "LM74502", (88.9, 76.2), {
        "1": "HEATER_EN", "2": "GND", "3": "NC", "4": "VCAP",
        "5": "+24V_IN", "6": "CUTOFF_GATE", "7": "GND", "8": "CUTOFF_SRC"})
    two(s, "C_VCAP", "C100n", 50.8, 116.84, "VCAP", "+24V_IN")
    two(s, "C_VS", "C100n", 68.58, 116.84, "+24V_IN", "GND")
    two(s, "R_EN_PD", "R100k", 86.36, 116.84, "HEATER_EN", "GND")
    # back-to-back N-FETs: Q1 blocks reverse polarity, Q2 switches the rail
    place(s, "Q_CUT1", "BSC016", (154.94, 76.2), {
        "1": "CUTOFF_SRC", "2": "CUTOFF_SRC", "3": "CUTOFF_SRC",
        "4": "CUTOFF_GATE", "5": "+24V_IN"})
    place(s, "Q_CUT2", "BSC016", (190.5, 76.2), {
        "1": "CUTOFF_SRC", "2": "CUTOFF_SRC", "3": "CUTOFF_SRC",
        "4": "CUTOFF_GATE", "5": "+24V_HEATER"})
    place(s, "TP_GATE", "TP", (215.9, 66.04), {"1": "CUTOFF_GATE"})
    # heater rail bulk (distributed along the channel row in the layout)
    for i, x in enumerate([241.3, 256.54]):
        two(s, f"C_BULK{i + 1}", "C100u63", x, 76.2, "+24V_HEATER", "GND")
    for i, x in enumerate([271.78, 287.02, 302.26, 317.5]):
        two(s, f"C_RAIL{i + 1}", "C10u50", x, 76.2, "+24V_HEATER", "GND")
    two(s, "R_BLEED", "R4k7_1206", 335.28, 76.2, "+24V_HEATER", "GND")
    place(s, "TP_24VH", "TP", (350.52, 66.04), {"1": "+24V_HEATER"})
    place(s, "FLG_24VH", "FLAG", (365.76, 66.04), {"1": "+24V_HEATER"})
    # rail sense divider 100k/10k -> 2.18 V at 24 V
    two(s, "R_RS_TOP", "R100k", 154.94, 152.4, "+24V_HEATER", "RAIL_DIV")
    two(s, "R_RS_BOT", "R10k", 172.72, 152.4, "RAIL_DIV", "AGND")
    place(s, "R_RS_SER", "R1k", (195.58, 152.4), {"1": "RAIL_DIV", "2": "RAIL_SENSE"}, rot=90)
    two(s, "C_RS", "C100n", 218.44, 152.4, "RAIL_SENSE", "AGND")
    place(s, "D_RS", "BAT54S", (241.3, 152.4), {"1": "AGND", "2": "VREF_A", "3": "RAIL_SENSE"})
    place(s, "TP_RS", "TP", (266.7, 144.78), {"1": "RAIL_SENSE"})
    s.text("Q1 drain at +24V_IN, Q2 drain at +24V_HEATER, sources joined (back-to-back).\n"
           "EN low (MCU reset, Klipper shutdown) -> gate pulled to SRC within ~2 us.\n"
           "Default off: 100k pull-down on HEATER_EN. Klipper: output_pin heater_enable,\n"
           "value 1, shutdown_value 0. Slow gate drive (60 uA) = soft start of the bulk caps.",
           (40.64, 190.5))
    s.text("Rail sense (AD-13): 24 V -> 2.18 V, clamp ~36 V. Bleeder 4.7k: <2 V within ~0.25 s\n"
           "after the cutoff opens (recheck with the final rail capacitance).",
           (154.94, 190.5))


def logic_power(b):
    s = b.sheet("logic_power", "5V buck, 3V3 LDOs, VBUS diode-OR, VREF_A")
    # reverse polarity diode + TPS54360B input
    two(s, "D_REV", "SS56C", 38.1, 63.5, "VIN_BUCK", "+24V_IN")
    two(s, "C_BIN1", "C10u50", 55.88, 63.5, "VIN_BUCK", "GND")
    two(s, "C_BIN2", "C10u50", 71.12, 63.5, "VIN_BUCK", "GND")
    two(s, "C_BIN3", "C100n", 86.36, 63.5, "VIN_BUCK", "GND")
    two(s, "R_UV1", "R1M", 101.6, 63.5, "VIN_BUCK", "BUCK_EN")
    two(s, "R_UV2", "R68k", 116.84, 63.5, "BUCK_EN", "GND")
    place(s, "FLG_VINB", "FLAG", (38.1, 40.64), {"1": "VIN_BUCK"})
    place(s, "U_BUCK", "TPS54360", (165.1, 76.2), {
        "1": "BUCK_BOOT", "2": "VIN_BUCK", "3": "BUCK_EN", "4": "BUCK_RT",
        "5": "BUCK_FB", "6": "BUCK_COMP", "7": "GND", "8": "BUCK_SW", "9": "GND"})
    two(s, "R_RT", "R160k", 109.22, 116.84, "BUCK_RT", "GND")
    two(s, "R_COMP", "R6k8", 124.46, 116.84, "BUCK_COMP", "COMP_RC")
    two(s, "C_COMP", "C22n", 139.7, 116.84, "COMP_RC", "GND")
    two(s, "C_COMP2", "C100p", 154.94, 116.84, "BUCK_COMP", "GND")
    two(s, "C_BOOT", "C100n", 208.28, 63.5, "BUCK_BOOT", "BUCK_SW")
    two(s, "D_CATCH", "SS56C", 223.52, 88.9, "BUCK_SW", "GND")
    place(s, "L_BUCK", "L10u", (248.92, 76.2), {"1": "BUCK_SW", "2": "+5V"}, rot=90)
    two(s, "R_FB1", "R36k", 271.78, 88.9, "+5V", "BUCK_FB")
    two(s, "R_FB2", "R6k8", 287.02, 88.9, "BUCK_FB", "GND")
    for i, x in enumerate([304.8, 320.04, 335.28]):
        two(s, f"C_BOUT{i + 1}", "C22u25", x, 88.9, "+5V", "GND")
    place(s, "FLG_5V", "FLAG", (350.52, 76.2), {"1": "+5V"})
    place(s, "TP_5V", "TP", (365.76, 76.2), {"1": "+5V"})
    s.text("TPS54360B, 604 kHz (RT 160k), Vout = 0.8 x (1 + 36k/6.8k) = 5.04 V.\n"
           "UVLO 1M/68k: start 17.6 V, stop 14.3 V. Compensation 6.8k + 22nF // 100pF.\n"
           "Catch diode SS56C: non-synchronous buck. Values: docs/calculations.md §1.",
           (38.1, 139.7))
    # 3V3 rails
    two(s, "D_OR_5V", "B5819W", 50.8, 177.8, "+5V_OR", "+5V")
    two(s, "D_OR_VBUS", "B5819W", 66.04, 177.8, "+5V_OR", "VBUS")
    place(s, "FLG_5VOR", "FLAG", (50.8, 160.02), {"1": "+5V_OR"})
    two(s, "C_L1IN", "C1u", 86.36, 177.8, "+5V_OR", "GND")
    place(s, "U_LDO_MCU", "ME6211", (114.3, 180.34), {
        "1": "+5V_OR", "2": "GND", "3": "+5V_OR", "4": "NC", "5": "+3V3_MCU"})
    two(s, "C_L1OUT", "C1u", 142.24, 177.8, "+3V3_MCU", "GND")
    two(s, "C_L1OUT2", "C100n", 157.48, 177.8, "+3V3_MCU", "GND")
    place(s, "TP_3V3M", "TP", (172.72, 170.18), {"1": "+3V3_MCU"})
    two(s, "C_L2IN", "C1u", 198.12, 177.8, "+5V", "GND")
    place(s, "U_LDO_AUX", "ME6211", (226.06, 180.34), {
        "1": "+5V", "2": "GND", "3": "+5V", "4": "NC", "5": "+3V3_AUX"})
    two(s, "C_L2OUT", "C1u", 254.0, 177.8, "+3V3_AUX", "GND")
    place(s, "TP_3V3A", "TP", (269.24, 170.18), {"1": "+3V3_AUX"})
    # VREF_A: filtered 3V3 for the ADC reference and thermistor pull-ups
    two(s, "R_VREF", "R10", 299.72, 177.8, "+3V3_MCU", "VREF_A")
    two(s, "C_VREF1", "C1u", 314.96, 177.8, "VREF_A", "AGND")
    two(s, "C_VREF2", "C100n", 330.2, 177.8, "VREF_A", "AGND")
    place(s, "FLG_VREF", "FLAG", (345.44, 170.18), {"1": "VREF_A"})
    place(s, "TP_VREF", "TP", (360.68, 170.18), {"1": "VREF_A"})
    place(s, "TP_AGND", "TP", (375.92, 170.18), {"1": "AGND"})
    place(s, "FLG_AGND", "FLAG", (391.16, 170.18), {"1": "AGND"})
    s.text("3V3_MCU: diode-OR of +5V and USB VBUS, so the MCU runs on USB alone\n"
           "(flashing without 24 V). VBUS feeds nothing else. 3V3_AUX: sensors, status LEDs.\n"
           "VREF_A = 3V3_MCU through 10R + 1uF + 100nF to AGND (ratiometric ADC).",
           (38.1, 213.36))


def build():
    b = Board("toolboard", "Nexus Tools Board")
    b.power_nets = POWER_NETS
    # nets that will connect to sheets drawn later: keep them global now
    b.force_global = {"HEATER_EN", "RAIL_SENSE"}
    power_input(b)
    heater_cutoff(b)
    logic_power(b)
    return b
