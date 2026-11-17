# SPDX-License-Identifier: GPL-3.0-or-later
"""Nexus Docks Board schematic description (F4).

Shares the mcu, usb_can and led_port sheets with the tool board (same
functions, parameters for the 3V3 net and the second CAN connector).
Values: docs/design/20-dockboard.md, docs/calculations.md, docs/pinout-dockboard.md.
"""
from schgen import Board
from parts import place, two
import toolboard as tb

POWER_NETS = {"+24V_IN", "+24V_INT", "+5V", "+3V3", "VBUS", "FAN_RAIL"}
V33 = "+3V3"


def power_input(b):
    s = b.sheet("power_input", "24V input: XT30, 5 A fuse, TVS, reverse polarity (LM74502 + 1 FET)")
    place(s, "J_XT30", "XT30", (50.8, 101.6), {"1": "VIN_RAW", "2": "GND"}, rot=180)
    two(s, "F_IN", "FUSE5", 81.28, 101.6, "VIN_RAW", "+24V_IN")
    two(s, "D_TVS", "SMBJ30CA", 101.6, 101.6, "+24V_IN", "GND")
    place(s, "FLG_24VIN", "FLAG", (101.6, 78.74), {"1": "+24V_IN"})
    place(s, "FLG_GND", "FLAG", (116.84, 78.74), {"1": "GND"})
    # LM74502 as reverse-polarity switch, always on (EN to VS), OV unused
    place(s, "U_RPP", "LM74502", (152.4, 101.6), {
        "1": "+24V_IN", "2": "GND", "3": "NC", "4": "RPP_VCAP",
        "5": "+24V_IN", "6": "RPP_GATE", "7": "GND", "8": "+24V_IN"})
    two(s, "C_VCAP", "C100n", 127.0, 142.24, "RPP_VCAP", "+24V_IN")
    two(s, "C_VS", "C100n", 142.24, 142.24, "+24V_IN", "GND")
    # single FET: source to the input, drain to +24V_INT
    place(s, "Q_RPP", "BSC016", (215.9, 101.6), {
        "1": "+24V_IN", "2": "+24V_IN", "3": "+24V_IN", "4": "RPP_GATE", "5": "+24V_INT"})
    two(s, "C_BULK", "C100u63", 251.46, 101.6, "+24V_INT", "GND")
    two(s, "C_INT1", "C10u50", 266.7, 101.6, "+24V_INT", "GND")
    two(s, "C_INT2", "C100n", 281.94, 101.6, "+24V_INT", "GND")
    place(s, "TP_24VINT", "TP_S", (297.18, 93.98), {"1": "+24V_INT"})
    place(s, "TP_GND", "TP_S", (312.42, 93.98), {"1": "GND"})
    place(s, "FLG_24VINT", "FLAG", (327.66, 93.98), {"1": "+24V_INT"})
    s.text("XT30 male on the board. Input fuse 5 A 1206 (same part as the tool board channel fuse).\n"
           "Reverse polarity: one BSC016N06NS with its SOURCE at the input (design 20 §4).\n"
           "Power-up: body diode conducts, LM74502 then turns the FET on (Rds 1.6 mOhm).\n"
           "Reverse polarity: body diode blocks, GATE held at SRC. EN tied to VS (always on), OV to GND.\n"
           "Bulk electrolytic after the protection, so it never sees reverse voltage.",
           (38.1, 167.64))


def logic_power(b):
    s = b.sheet("logic_power", "5V buck, 3V3 LDO, VBUS diode-OR")
    two(s, "C_BIN1", "C10u50", 55.88, 63.5, "+24V_INT", "GND")
    two(s, "C_BIN2", "C10u50", 71.12, 63.5, "+24V_INT", "GND")
    two(s, "C_BIN3", "C100n", 86.36, 63.5, "+24V_INT", "GND")
    two(s, "R_UV1", "R1M", 101.6, 63.5, "+24V_INT", "BUCK_EN")
    two(s, "R_UV2", "R68k", 116.84, 63.5, "BUCK_EN", "GND")
    place(s, "U_BUCK", "TPS54360", (165.1, 76.2), {
        "1": "BUCK_BOOT", "2": "+24V_INT", "3": "BUCK_EN", "4": "BUCK_RT",
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
    place(s, "TP_5V", "TP_S", (365.76, 76.2), {"1": "+5V"})
    s.text("Same 5 V converter as the tool board (docs/calculations.md §1, §4, §5),\n"
           "fed from +24V_INT (after the reverse-polarity FET), so no series diode.",
           (38.1, 139.7))
    two(s, "D_OR_5V", "B5819W", 50.8, 177.8, "+5V_OR", "+5V")
    two(s, "D_OR_VBUS", "B5819W", 66.04, 177.8, "+5V_OR", "VBUS")
    place(s, "FLG_5VOR", "FLAG", (50.8, 160.02), {"1": "+5V_OR"})
    two(s, "C_L1IN", "C1u", 86.36, 177.8, "+5V_OR", "GND")
    place(s, "U_LDO", "ME6211", (114.3, 180.34), {
        "1": "+5V_OR", "2": "GND", "3": "+5V_OR", "4": "NC", "5": V33})
    two(s, "C_L1OUT", "C1u", 142.24, 177.8, V33, "GND")
    two(s, "C_L1OUT2", "C100n", 157.48, 177.8, V33, "GND")
    place(s, "TP_3V3", "TP_S", (172.72, 170.18), {"1": V33})
    s.text("+3V3: diode-OR of +5V and USB VBUS (flashing without 24 V). One LDO: no analog sensors.",
           (38.1, 213.36))


def fan_rail(b):
    s = b.sheet("fan_rail", "Fan rail: second buck (12 V / 5 V) and rail selection jumper")
    two(s, "C_FIN1", "C10u50", 55.88, 63.5, "+24V_INT", "GND")
    two(s, "C_FIN2", "C10u50", 71.12, 63.5, "+24V_INT", "GND")
    two(s, "C_FIN3", "C100n", 86.36, 63.5, "+24V_INT", "GND")
    two(s, "R_FUV1", "R1M", 101.6, 63.5, "+24V_INT", "FBK_EN")
    two(s, "R_FUV2", "R68k", 116.84, 63.5, "FBK_EN", "GND")
    place(s, "U_FBUCK", "TPS54360", (165.1, 76.2), {
        "1": "FBK_BOOT", "2": "+24V_INT", "3": "FBK_EN", "4": "FBK_RT",
        "5": "FBK_FB", "6": "FBK_COMP", "7": "GND", "8": "FBK_SW", "9": "GND"})
    two(s, "R_FRT", "R160k", 109.22, 116.84, "FBK_RT", "GND")
    two(s, "R_FCOMP", "R12k", 124.46, 116.84, "FBK_COMP", "FBK_RC")
    two(s, "C_FCOMP", "C8n2", 139.7, 116.84, "FBK_RC", "GND")
    two(s, "C_FCOMP2", "C47p", 154.94, 116.84, "FBK_COMP", "GND")
    two(s, "C_FBOOT", "C100n", 208.28, 63.5, "FBK_BOOT", "FBK_SW")
    two(s, "D_FCATCH", "SS56C", 223.52, 88.9, "FBK_SW", "GND")
    place(s, "L_FBUCK", "L10u", (248.92, 76.2), {"1": "FBK_SW", "2": "FAN_BUCK"}, rot=90)
    # feedback: 7.5k bottom; 39k (+ 68k when the jumper is cut)
    two(s, "R_FFB_A", "R68k", 271.78, 63.5, "FAN_BUCK", "FBK_FBM")
    place(s, "JP_FVSEL", "SJ2B", (271.78, 38.1), {"1": "FAN_BUCK", "2": "FBK_FBM"})
    two(s, "R_FFB_B", "R39k", 287.02, 88.9, "FBK_FBM", "FBK_FB")
    two(s, "R_FFB_C", "R7k5", 302.26, 88.9, "FBK_FB", "GND")
    for i, x in enumerate([320.04, 335.28, 350.52, 365.76]):
        two(s, f"C_FOUT{i + 1}", "C22u25", x, 88.9, "FAN_BUCK", "GND")
    place(s, "FLG_FBK", "FLAG", (381.0, 76.2), {"1": "FAN_BUCK"})
    # rail selection: 1-2 = 24 V direct, 2-3 = buck. Default OPEN: no fan voltage.
    place(s, "JP_FRAIL", "SJ3O", (127.0, 177.8), {"1": "+24V_INT", "2": "FAN_RAIL", "3": "FAN_BUCK"})
    two(s, "C_FRAIL", "C10u50", 165.1, 177.8, "FAN_RAIL", "GND")
    place(s, "TP_FRAIL", "TP_S", (182.88, 170.18), {"1": "FAN_RAIL"})
    place(s, "FLG_FRAIL", "FLAG", (198.12, 170.18), {"1": "FAN_RAIL"})
    s.text("Buck 2: same converter as the 5 V rail. JP_FVSEL bridged (default) = 0.8 x (1 + 39k/7.5k) = 4.96 V;\n"
           "cut = 0.8 x (1 + 107k/7.5k) = 12.2 V. Compensation 12k + 8.2nF // 47pF (calculations.md §5).",
           (38.1, 139.7))
    s.text("FAN RAIL jumper is OPEN by default: no fan voltage until a choice is made (FR-D02).\n"
           "Bridge 1-2 = 24 V direct, 2-3 = buck (5 V or 12 V). Silkscreen warning next to the jumper.\n"
           "With 24 V direct the buck runs unloaded (pulse skipping, a few mA).",
           (38.1, 205.74))


def fans(b):
    s = b.sheet("fans", "9 fan outputs: gate buffer, low-side MOSFET, flyback diode")
    buf = {"1": "GND", "19": "GND", "10": "GND", "20": "+5V"}
    for i in range(8):
        buf[str(2 + i)] = f"FAN{i}_CTRL"
        buf[str(18 - i)] = f"FAN_GATE{i}_B"
    place(s, "U_GATEBUF", "HCT541", (45.72, 101.6), buf)
    two(s, "C_GATEBUF", "C100n", 30.48, 152.4, "+5V", "GND")
    place(s, "U_GATE8", "AHCT125", (45.72, 205.74), {
        "1": "GND", "2": "FAN8_CTRL", "3": "GND", "4": "FAN_GATE8_B", "5": "+5V"})
    two(s, "C_GATE8", "C100n", 30.48, 243.84, "+5V", "GND")
    for i in range(9):
        y = 35.56 + i * 25.4
        place(s, f"R_FIN{i}", "R100k", (101.6, y), {"1": f"FAN{i}_CTRL", "2": "GND"}, rot=90)
        place(s, f"R_FG{i}", "R22", (144.78, y), {"1": f"FAN_GATE{i}_B", "2": f"FAN_GATE{i}"}, rot=90)
        place(s, f"R_FGPD{i}", "R100k", (187.96, y), {"1": f"FAN_GATE{i}", "2": "GND"}, rot=90)
        place(s, f"Q_F{i}", "WSD", (228.6, y), {
            "1": "GND", "2": "GND", "3": "GND", "4": f"FAN_GATE{i}", "5": f"FAN{i}_N"}, rot=90)
        place(s, f"D_FFB{i}", "B5819W", (281.94, y), {"1": "FAN_RAIL", "2": f"FAN{i}_N"})
        place(s, f"J_FAN{i}", "XH2", (342.9, y + 1.27), {"1": f"FAN{i}_N", "2": "FAN_RAIL"},
              value=f"FAN {i}")
    s.text("Fans 0-7: 74HCT541, fan 8: 74AHCT1G125 (same 5 V gate drive). Same MOSFET as the heaters.\n"
           "B5819W flyback per fan (cathode to FAN_RAIL). Connector: pin 1 = FAN-, pin 2 = V+.\n"
           "Max 1 A per fan, 3 A total. 2- and 3-wire fans (tacho not connected).",
           (20.32, 271.78))


def diag_leds(b):
    s = b.sheet("diag_leds", "Diagnostic LEDs (AD-17)")
    rails = [("24VIN", "+24V_INT", "R10k", "24V IN"), ("FRAIL", "FAN_RAIL", "R4k7_1206", "FAN RAIL"),
             ("5V", "+5V", "R1k", "5V"), ("3V3", V33, "R470", "3V3"), ("VBUS", "VBUS", "R1k", "VBUS")]
    x = 50.8
    for key, rail, rcat, label in rails:
        two(s, f"R_L{key}", rcat, x, 63.5, rail, f"LED_{key}_A")
        two(s, f"D_L{key}", "LED_G", x, 88.9, f"LED_{key}_A", "GND", value=f"green {label}")
        x += 22.86
    two(s, "R_LMCU", "R470", x, 63.5, "LED_MCU", "LED_MCU_A")
    two(s, "D_LMCU", "LED_R", x, 88.9, "LED_MCU_A", "GND", value="red MCU")
    s.text("FAN RAIL LED: 4.7k 1206 so it is visible at 5 V (0.6 mA) and safe at 24 V (4.7 mA, 0.1 W).\n"
           "No LED per fan (AD-17). All LEDs along one visible edge with silkscreen labels.",
           (38.1, 127.0))


DOCK_PINS = {str(n): "NC" for n in range(1, 65)}
DOCK_PINS.update({
    "6": V33, "7": "VREF_D", "8": V33, "9": "GND",
    "10": "OSC_IN", "11": "OSC_OUT", "12": "NRST",
    "27": "CAN_RX", "28": "CAN_TX", "32": "FAN8_CTRL",
    "33": "FAN0_CTRL", "34": "FAN1_CTRL", "35": "FAN2_CTRL", "36": "FAN3_CTRL",
    "38": "FAN4_CTRL", "39": "FAN5_CTRL", "40": "FAN6_CTRL", "41": "FAN7_CTRL",
    "43": "USB_DM", "44": "USB_DP", "45": "SWDIO", "46": "SWCLK",
    "57": "LED_DATA", "58": "LED_MCU",
})


def build():
    b = Board("dockboard", "Nexus Docks Board")
    b.power_nets = POWER_NETS
    b.force_global = set()
    power_input(b)
    logic_power(b)
    fan_rail(b)
    tb.mcu(b, pins=DOCK_PINS, v33=V33, star=False, spare=41, pinout_doc="pinout-dockboard.md",
           button="BTN_S")
    tb.usb_can(b, v33=V33, can_out=False)
    diag_leds(b)
    fans(b)
    tb.led_port(b)
    return b
