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


MCU_PINS = {
    "1": "FIL_MOTION_T0", "2": "FIL_RUNOUT_T0", "3": "NC", "4": "NC", "5": "NC",
    "6": "+3V3_MCU", "7": "VREF_A", "8": "+3V3_MCU", "9": "GND",
    "10": "OSC_IN", "11": "OSC_OUT", "12": "NRST",
    "13": "NC", "14": "NC", "15": "NC", "16": "NC",
    **{str(17 + i): f"THERM_T{i}" for i in range(8)},
    "25": "RAIL_SENSE", "26": "NC", "27": "CAN_RX", "28": "CAN_TX",
    "29": "NC", "30": "NC", "31": "NC", "32": "HEATER_EN",
    "33": "HEATER_T0_CTRL", "34": "HEATER_T1_CTRL", "35": "HEATER_T2_CTRL",
    "36": "HEATER_T3_CTRL", "37": "NC", "38": "HEATER_T4_CTRL",
    "39": "HEATER_T5_CTRL", "40": "HEATER_T6_CTRL", "41": "HEATER_T7_CTRL",
    "42": "NC", "43": "USB_DM", "44": "USB_DP", "45": "SWDIO", "46": "SWCLK",
    "47": "FIL_MOTION_T7", "48": "FIL_RUNOUT_T7", "49": "FIL_MOTION_T6",
    "50": "FIL_RUNOUT_T6", "51": "FIL_MOTION_T5", "52": "FIL_RUNOUT_T5",
    "53": "FIL_MOTION_T4", "54": "FIL_RUNOUT_T4", "55": "FIL_MOTION_T3",
    "56": "FIL_RUNOUT_T3", "57": "LED_DATA", "58": "LED_MCU",
    "59": "FIL_MOTION_T2", "60": "NC", "61": "NC", "62": "FIL_RUNOUT_T2",
    "63": "FIL_MOTION_T1", "64": "FIL_RUNOUT_T1",
}


def mcu(b):
    s = b.sheet("mcu", "STM32G0B1RBT6, crystal, reset/boot, SWD, AGND star point")
    place(s, "U_MCU", "STM32", (203.2, 127.0), MCU_PINS)
    # supply decoupling, next to pins 6/8 in the layout
    two(s, "C_VDD1", "C4u7", 63.5, 63.5, "+3V3_MCU", "GND")
    two(s, "C_VDD2", "C100n", 78.74, 63.5, "+3V3_MCU", "GND")
    two(s, "C_VBAT", "C100n", 93.98, 63.5, "+3V3_MCU", "GND")
    two(s, "C_VREF3", "C100n", 109.22, 63.5, "VREF_A", "AGND")
    # AGND-GND star point at pin 9 (CLAUDE.md §7.4)
    place(s, "NT_AGND", "NETTIE", (134.62, 58.42), {"1": "AGND", "2": "GND"}, rot=0)
    # 8 MHz crystal, CL 20 pF -> 2 x 30 pF (AN2867)
    place(s, "Y_MCU", "XTAL8", (76.2, 116.84), {"1": "OSC_IN", "2": "OSC_OUT"}, rot=0)
    two(s, "C_X1", "C30p", 63.5, 134.62, "OSC_IN", "GND")
    two(s, "C_X2", "C30p", 88.9, 134.62, "OSC_OUT", "GND")
    # reset and boot
    two(s, "C_NRST", "C100n", 63.5, 175.26, "NRST", "GND")
    place(s, "SW_RESET", "BTN", (81.28, 175.26), {"1": "NRST", "2": "GND"}, rot=90)
    place(s, "SW_BOOT", "BTN", (106.68, 175.26), {"1": "+3V3_MCU", "2": "SWCLK"}, rot=90)
    two(s, "R_BOOT", "R10k", 124.46, 175.26, "SWCLK", "GND")
    # SWD header 3V3 - SWDIO - SWCLK - GND
    place(s, "J_SWD", "SWD", (342.9, 101.6), {"1": "+3V3_MCU", "2": "SWDIO", "3": "SWCLK", "4": "GND"})
    s.text("PA14 = SWCLK / BOOT0. BOOT button pulls it to 3V3; 10k pull-down keeps SWD usable.\n"
           "DFU: hold BOOT, press RESET. An empty flash boots into the ROM bootloader anyway.\n"
           "Check option byte nBOOT_SEL on the first board if the button has no effect (F8).\n"
           "Unused GPIO: no-connect (13 spare, docs/pinout-toolboard.md).",
           (38.1, 215.9))


def usb_can(b):
    s = b.sheet("usb_can", "USB-C (USB 2.0 device), CAN transceiver, CAN connectors")
    place(s, "J_USB", "USBC", (63.5, 101.6), {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
        "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A5": "USB_CC1", "B5": "USB_CC2", "A6": "USB_DP", "B6": "USB_DP",
        "A7": "USB_DM", "B7": "USB_DM", "A8": "NC", "B8": "NC", "SH": "USB_SHIELD"})
    two(s, "R_CC1", "R5k1", 116.84, 76.2, "USB_CC1", "GND")
    two(s, "R_CC2", "R5k1", 132.08, 76.2, "USB_CC2", "GND")
    two(s, "R_SHIELD", "R1M", 116.84, 139.7, "USB_SHIELD", "GND")
    two(s, "C_SHIELD", "C4n7", 132.08, 139.7, "USB_SHIELD", "GND")
    place(s, "U_USBESD", "USBLC6", (165.1, 101.6), {
        "1": "USB_DM", "6": "USB_DM", "3": "USB_DP", "4": "USB_DP",
        "2": "GND", "5": "VBUS"})
    place(s, "FLG_VBUS", "FLAG", (195.58, 76.2), {"1": "VBUS"})
    place(s, "TP_VBUS", "TP", (210.82, 76.2), {"1": "VBUS"})
    # CAN
    place(s, "U_CAN", "TJA1051", (101.6, 205.74), {
        "1": "CAN_TX", "2": "GND", "3": "+5V", "4": "CAN_RX",
        "5": "+3V3_MCU", "6": "CANL", "7": "CANH", "8": "GND"})
    two(s, "C_CANVCC", "C100n", 50.8, 238.76, "+5V", "GND")
    two(s, "C_CANVIO", "C100n", 66.04, 238.76, "+3V3_MCU", "GND")
    place(s, "D_CANESD", "PESD2CAN", (152.4, 200.66), {"1": "CANH", "2": "CANL", "3": "GND"})
    place(s, "J_CAN_IN", "MICROFIT", (213.36, 195.58),
          {"1": "GND", "2": "NC", "3": "CANL", "4": "CANH"}, value="CAN IN")
    place(s, "J_CAN_OUT", "MICROFIT", (256.54, 195.58),
          {"1": "GND", "2": "NC", "3": "CANL", "4": "CANH"}, value="CAN OUT")
    place(s, "R_TERM", "R120", (299.72, 195.58), {"1": "CANH", "2": "CAN_TERM"}, rot=90)
    place(s, "J_TERM", "HDR2", (342.9, 195.58), {"1": "CAN_TERM", "2": "CANL"})
    place(s, "TP_CANH", "TP", (370.84, 187.96), {"1": "CANH"})
    place(s, "TP_CANL", "TP", (386.08, 187.96), {"1": "CANL"})
    s.text("USB: device, CC1/CC2 5.1k (Rd). VBUS only feeds the 3V3_MCU diode-OR.\n"
           "Shield to GND via 1M // 4.7nF (no hard ground loop over the cable shield).",
           (38.1, 160.02))
    s.text("CAN connectors, seen into the mating face (PCB below), as on BTT EBB boards:\n"
           "  top row:    CAN-H (pad 4) | CAN-L (pad 3)\n"
           "  bottom row: 24V (pad 2, NOT CONNECTED, AD-07) | GND (pad 1)\n"
           "Termination 120R: fit the jumper only at the end of the bus.\n"
           "TJA1051T/3: VCC 5 V, VIO 3.3 V, S to GND (normal mode).",
           (38.1, 254.0))


def diag_leds(b):
    s = b.sheet("diag_leds", "Diagnostic LEDs (AD-17)")
    rails = [("24VIN", "+24V_IN", "R10k", "24V IN"), ("RAIL", "+24V_HEATER", "R10k", "HEATER RAIL"),
             ("5V", "+5V", "R1k", "5V"), ("3V3", "+3V3_MCU", "R470", "3V3"),
             ("VBUS", "VBUS", "R1k", "VBUS")]
    x = 50.8
    for key, rail, rcat, label in rails:
        two(s, f"R_L{key}", rcat, x, 63.5, rail, f"LED_{key}_A")
        two(s, f"D_L{key}", "LED_G", x, 88.9, f"LED_{key}_A", "GND", value=f"green {label}")
        x += 22.86
    two(s, "R_LMCU", "R470", x, 63.5, "LED_MCU", "LED_MCU_A")
    two(s, "D_LMCU", "LED_R", x, 88.9, "LED_MCU_A", "GND", value="red MCU")
    # one LED per heater channel at the MOSFET drain (design part 1 §4.3)
    for i in range(8):
        x = 50.8 + i * 22.86
        two(s, f"R_LH{i}", "R10k", x, 152.4, "+24V_HEATER", f"LED_H{i}_A")
        two(s, f"D_LH{i}", "LED_R", x, 177.8, f"LED_H{i}_A", f"HEATER_T{i}_N", value=f"red HEATER T{i}")
    s.text("Rails: green 0805 (Basic). Heater channels and MCU: red 0603.\n"
           "Channel LED from +24V_HEATER to the drain: lit = MOSFET really on.\n"
           "Lit while Klipper has the channel off = MOSFET failed short (design part 1 §4.3).\n"
           "All LEDs together along one visible board edge, each with a silkscreen label.",
           (38.1, 215.9))


def heaters(b):
    s = b.sheet("heaters", "8 heater channels: gate buffer, low-side MOSFET, 5 A fuse, screw terminal")
    buf = {"1": "GND", "19": "GND", "10": "GND", "20": "+5V"}
    for i in range(8):
        buf[str(2 + i)] = f"HEATER_T{i}_CTRL"
        buf[str(18 - i)] = f"GATE_T{i}_B"
    place(s, "U_GATEBUF", "HCT541", (45.72, 120.65), buf)
    two(s, "C_GATEBUF", "C100n", 30.48, 167.64, "+5V", "GND")
    for i in range(8):
        y = 38.1 + i * 27.94
        place(s, f"R_IN{i}", "R100k", (101.6, y), {"1": f"HEATER_T{i}_CTRL", "2": "GND"}, rot=90)
        place(s, f"R_G{i}", "R22", (144.78, y), {"1": f"GATE_T{i}_B", "2": f"GATE_T{i}"}, rot=90)
        place(s, f"R_GPD{i}", "R100k", (187.96, y), {"1": f"GATE_T{i}", "2": "GND"}, rot=90)
        place(s, f"Q_H{i}", "WSD", (228.6, y), {
            "1": "GND", "2": "GND", "3": "GND", "4": f"GATE_T{i}", "5": f"HEATER_T{i}_N"}, rot=90)
        place(s, f"F_H{i}", "FUSE5", (281.94, y), {"1": "+24V_HEATER", "2": f"HEATER_T{i}_P"}, rot=90)
        place(s, f"J_H{i}", "SCREW2", (342.9, y + 1.27),
              {"1": f"HEATER_T{i}_P", "2": f"HEATER_T{i}_N"}, value=f"HEATER T{i}")
    place(s, "TP_GATE0", "TP", (370.84, 30.48), {"1": "GATE_T0"})
    place(s, "TP_DRAIN0", "TP", (386.08, 30.48), {"1": "HEATER_T0_N"})
    s.text("74HCT541: TTL inputs (3.3 V = high), 5 V gate drive. OE (G1/G2) tied to GND.\n"
           "100k pull-downs on inputs and gates: all MOSFETs off during reset/boot.\n"
           "Low-side WSD4070DN33 (40 V, 7.6 mOhm max at 4.5 V); fuse 5 A in the +24 V lead.\n"
           "Terminal: pin 1 = +24V (fused, behind the cutoff), pin 2 = HEATER- (drain).",
           (20.32, 205.74))


def thermistors(b):
    s = b.sheet("thermistors", "8 thermistor inputs (NTC 100K / PT1000), RC filter, clamp, ESD")
    for i in range(8):
        y = 38.1 + i * 27.94
        c, n = f"THERM_T{i}_C", f"THERM_T{i}"
        place(s, f"R_PU{i}", "R4k7p", (45.72, y), {"1": "VREF_A", "2": c}, rot=90)
        place(s, f"JP_PT{i}", "SJ2", (88.9, y), {"1": "VREF_A", "2": f"THERM_T{i}_PT"})
        place(s, f"R_PT{i}", "R4k12p", (134.62, y), {"1": f"THERM_T{i}_PT", "2": c}, rot=90)
        place(s, f"D_TESD{i}", "SMF30CA", (175.26, y), {"1": c, "2": "AGND"})
        place(s, f"C_TIN{i}", "C100n", (213.36, y), {"1": c, "2": "AGND"}, rot=90)
        place(s, f"R_TS{i}", "R4k7", (254.0, y), {"1": c, "2": n}, rot=90)
        place(s, f"C_TADC{i}", "C100n", (294.64, y), {"1": n, "2": "AGND"}, rot=90)
        place(s, f"D_TCL{i}", "BAT54S", (335.28, y), {"1": "AGND", "2": "VREF_A", "3": n})
        place(s, f"J_T{i}", "XH2", (378.46, y + 1.27), {"1": c, "2": "AGND"}, value=f"THERM T{i}")
    s.text("Pull-up 4.7k 0.1 % (NTC 100K, pullup_resistor: 4700). Close JP = PT1000:\n"
           "4.7k // 4.12k = 2195 Ohm (pullup_resistor: 2195). Pull-ups on VREF_A = ADC reference.\n"
           "24 V on the input (heater wire touching the thermistor wire): 4.7k + BAT54S limit\n"
           "the ADC pin current to ~4 mA; SMF30CA does not conduct at 24 V. Connector pin 2 = AGND.",
           (20.32, 266.7))


def build():
    b = Board("toolboard", "Nexus Tools Board")
    b.power_nets = POWER_NETS
    # nets that will connect to sheets drawn later: keep them global now
    b.force_global = ({"HEATER_EN", "RAIL_SENSE", "LED_DATA"}
                      | {f"THERM_T{i}" for i in range(8)}
                      | {f"HEATER_T{i}_CTRL" for i in range(8)}
                      | {f"HEATER_T{i}_N" for i in range(8)}
                      | {f"FIL_{k}_T{i}" for k in ("RUNOUT", "MOTION") for i in range(8)})
    power_input(b)
    heater_cutoff(b)
    logic_power(b)
    mcu(b)
    usb_can(b)
    diag_leds(b)
    heaters(b)
    thermistors(b)
    return b
