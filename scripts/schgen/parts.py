# SPDX-License-Identifier: GPL-3.0-or-later
"""Part catalogue: one place for value, footprint, LCSC and MPN.

Keys are used in the sheet descriptions; LCSC numbers come from
docs/bom-master.csv (F1/F2). Generic Basic passives are listed here too.
"""
R0603 = "Resistor_SMD:R_0603_1608Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"

# key: (lib_id, value, footprint, lcsc, mpn, assembly)
P = {
    # resistors 0603 1 % (Basic unless marked)
    "R10":   ("Device:R", "10R", R0603, "C22859", "0603WAF100JT5E", "JLC"),
    "R470":  ("Device:R", "470R", R0603, "C23179", "0603WAF4700T5E", "JLC"),
    "R1k":   ("Device:R", "1k", R0603, "C21190", "0603WAF1001T5E", "JLC"),
    "R6k8":  ("Device:R", "6.8k", R0603, "C23212", "0603WAF6801T5E", "JLC"),
    "R10k":  ("Device:R", "10k", R0603, "C25804", "0603WAF1002T5E", "JLC"),
    "R36k":  ("Device:R", "36k", R0603, "C23147", "0603WAF3602T5E", "JLC"),   # Preferred
    "R68k":  ("Device:R", "68k", R0603, "C23231", "0603WAF6802T5E", "JLC"),
    "R100k": ("Device:R", "100k", R0603, "C25803", "0603WAF1003T5E", "JLC"),
    "R160k": ("Device:R", "160k", R0603, "C22813", "0603WAF1603T5E", "JLC"),  # Preferred
    "R1M":   ("Device:R", "1M", R0603, "C22935", "0603WAF1004T5E", "JLC"),
    "R4k7_1206": ("Device:R", "4.7k 0.25W", R1206, "C17936", "1206W4F4701T5E", "JLC"),
    # capacitors
    "C30p":  ("Device:C", "30pF C0G", C0603, "C1658", "0603CG300J500NT", "JLC"),
    "C100p": ("Device:C", "100pF C0G", C0603, "C14858", "CL10C101JB8NNNC", "JLC"),
    "C22n":  ("Device:C", "22nF", C0603, "C21122", "CL10B223KB8NNNC", "JLC"),
    "C100n": ("Device:C", "100nF 50V", C0603, "C14663", "CC0603KRX7R9BB104", "JLC"),
    "C1u":   ("Device:C", "1uF 50V", C0603, "C15849", "CL10A105KB8NNNC", "JLC"),
    "C10u50": ("Device:C", "10uF 50V", C1206, "C13585", "CL31A106KBHNNNE", "JLC"),
    "C22u25": ("Device:C", "22uF 25V", C1206, "C12891", "CL31A226KAHNNNE", "JLC"),
    "C100u63": ("Device:C_Polarized", "100uF 63V", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
                "C88747", "63ZLH100MEFC8X16", "SELF"),
    # semiconductors
    "SS56C": ("Device:D_Schottky", "SS56C", "Diode_SMD:D_SMC", "C24138", "SS56C", "JLC"),
    "B5819W": ("Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598", "B5819W SL", "JLC"),
    "SMBJ30CA": ("Device:D_TVS", "SMBJ30CA", "Diode_SMD:D_SMB", "C2925441", "SMBJ30CA", "JLC"),
    "BAT54S": ("Diode:BAT54S", "BAT54S", "Package_TO_SOT_SMD:SOT-23", "C408389", "BAT54S", "JLC"),
    "LM74502": ("nexus:LM74502DDFR", "LM74502DDFR", None, "C3236215", "LM74502DDFR", "JLC"),
    "BSC016": ("nexus:BSC016N06NS", "BSC016N06NS", None, "C454269", "BSC016N06NS", "JLC"),
    "TPS54360": ("Regulator_Switching:TPS54360DDA", "TPS54360B", "Package_SO:TI_SO-PowerPAD-8_ThermalVias",
                 "C524806", "TPS54360BDDAR", "JLC"),
    "L10u": ("nexus:MWSA0603-100MT", "10uH", None, "C132141", "MWSA0603S-100MT", "JLC"),
    "ME6211": ("Regulator_Linear:ME6211C33M5", "ME6211C33", "Package_TO_SOT_SMD:SOT-23-5",
               "C82942", "ME6211C33M5G-N", "JLC"),
    # protection, connectors
    "FUSE25": ("nexus:0456025.ER", "25A", None, "C315877", "0456025.ER", "SELF"),
    "XT60": ("Connector_Generic:Conn_01x02", "XT60PW-M",
             "Connector_AMASS:AMASS_XT60PW-M_1x02_P7.20mm_Horizontal", "C98732", "XT60PW-M", "SELF"),
    "TP": ("Connector:TestPoint", "TP", "TestPoint:TestPoint_Pad_D1.5mm", "", "", "NONE"),
    "FLAG": ("power:PWR_FLAG", "PWR_FLAG", "", "", "", "NONE"),
    # F3 batch 2
    "R120":  ("Device:R", "120R", R0603, "C22787", "0603WAF1200T5E", "JLC"),
    "R5k1":  ("Device:R", "5.1k", R0603, "C23186", "0603WAF5101T5E", "JLC"),
    "C4n7":  ("Device:C", "4.7nF", C0603, "C53987", "0603B472K500NT", "JLC"),
    "C4u7":  ("Device:C", "4.7uF 16V", C0603, "C19666", "CL10A475KO8NNNC", "JLC"),
    "STM32": ("MCU_ST_STM32G0:STM32G0B1RBTx", "STM32G0B1RBT6", "Package_QFP:LQFP-64_10x10mm_P0.5mm",
              "C5143679", "STM32G0B1RBT6", "JLC"),
    "XTAL8": ("Device:Crystal", "8MHz 20pF", "Crystal:Crystal_SMD_5032-2Pin_5.0x3.2mm",
              "C115962", "X50328MSB2GI", "JLC"),
    "BTN": ("Switch:SW_Push", "TS-1187A", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
            "C318884", "TS-1187A-B-A-B", "JLC"),
    "SWD": ("Connector_Generic:Conn_01x04", "SWD", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "C32713270", "HX PZ2.54-1x4P ZZ", "SELF"),
    "NETTIE": ("Device:NetTie_2", "AGND-GND", "NetTie:NetTie-2_SMD_Pad0.5mm", "", "", "NONE"),
    "USBC": ("Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
             "C165948", "TYPE-C-31-M-12", "JLC"),
    "USBLC6": ("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
               "C7519", "USBLC6-2SC6", "JLC"),
    "TJA1051": ("Interface_CAN_LIN:TJA1051T-3", "TJA1051T/3", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                "C38695", "TJA1051T/3/1J", "JLC"),
    "PESD2CAN": ("nexus:PESD2CAN", "PESD2CAN", None, "C907830", "PESD2CAN", "JLC"),
    "MICROFIT": ("Connector_Generic:Conn_02x02_Odd_Even", "Micro-Fit 2x2",
                 "Connector_Molex:Molex_Micro-Fit_3.0_43045-0400_2x02_P3.00mm_Horizontal",
                 "C122413", "43045-0400", "SELF"),
    "HDR2": ("Connector_Generic:Conn_01x02", "CAN TERM", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
             "C492401", "PZ254V-11-02P", "SELF"),
    "LED_G": ("Device:LED", "green", "LED_SMD:LED_0805_2012Metric", "C2297", "KT-0805G", "JLC"),
    "LED_R": ("Device:LED", "red", "LED_SMD:LED_0603_1608Metric", "C2286", "KT-0603R", "JLC"),
    # F3 batch 3
    "R22":   ("Device:R", "22R", R0603, "C23345", "0603WAF220JT5E", "JLC"),
    "R4k7":  ("Device:R", "4.7k", R0603, "C23162", "0603WAF4701T5E", "JLC"),
    "R4k7p": ("Device:R", "4.7k 0.1%", R0603, "C666997", "TD03G4701BT", "JLC"),
    "R4k12p": ("Device:R", "4.12k 0.1%", R0603, "C2984354", "AR03BTCX4121", "JLC"),
    "SMF30CA": ("Device:D_TVS", "SMF30CA", "Diode_SMD:D_SOD-123F", "C19077519", "SMF30CA", "JLC"),
    "FUSE5": ("Device:Fuse", "5A", "Fuse:Fuse_1206_3216Metric", "C57525", "0466005.NRHF", "SELF"),
    "WSD": ("nexus:WSD4070DN", "WSD4070DN33", None, "C719095", "WSD4070DN33", "JLC"),
    "HCT541": ("74xx:74HCT541", "CD74HCT541M96", "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm",
               "C6560", "CD74HCT541M96", "JLC"),
    "SCREW2": ("Connector_Generic:Conn_01x02", "WJ500V-5.08-2P",
               "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
               "C8465", "WJ500V-5.08-2P", "SELF"),
    "XH2": ("Connector_Generic:Conn_01x02", "JST-XH 2", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
            "C158012", "B2B-XH-A(LF)(SN)", "SELF"),
    "SJ2": ("Jumper:SolderJumper_2_Open", "PT1000", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
            "", "", "NONE"),
    # F3 batch 4
    "R330":  ("Device:R", "330R", R0603, "C23138", "0603WAF3300T5E", "JLC"),
    "ESD5V": ("Device:D_TVS", "PESD5V0S1BA", "Diode_SMD:D_SOD-323", "C2827694", "PESD5V0S1BA", "JLC"),
    "PPTC":  ("Device:Polyfuse", "0.75A", "Fuse:Fuse_1206_3216Metric", "C409806", "JK-nSMD075-16", "JLC"),
    "AHCT125": ("74xGxx:74AHCT1G125", "SN74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5",
                "C7484", "SN74AHCT1G125DBVR", "JLC"),
    "XH4": ("Connector_Generic:Conn_01x04", "JST-XH 4", "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
            "C144395", "B4B-XH-A(LF)(SN)", "SELF"),
    "XH3": ("Connector_Generic:Conn_01x03", "JST-XH 3", "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical",
            "C144394", "B3B-XH-A(LF)(SN)", "SELF"),
    "SJ3": ("Jumper:SolderJumper_3_Bridged12", "VCC_FIL 5V|3V3",
            "Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm", "", "", "NONE"),
    # F4 dock board
    "R7k5":  ("Device:R", "7.5k", R0603, "C23234", "0603WAF7501T5E", "JLC"),
    "R12k":  ("Device:R", "12k", R0603, "C22790", "0603WAF1202T5E", "JLC"),
    "R39k":  ("Device:R", "39k", R0603, "C23153", "0603WAF3902T5E", "JLC"),
    "C8n2":  ("Device:C", "8.2nF", C0603, "C1322360", "0603B822K500NT", "JLC"),
    "C47p":  ("Device:C", "47pF C0G", C0603, "C1671", "CL10C470JB8NNNC", "JLC"),
    "XT30": ("Connector_Generic:Conn_01x02", "XT30PW-M",
             "Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal", "C431092", "XT30PW-M30.G.Y", "SELF"),
    "SJ2B": ("Jumper:SolderJumper_2_Bridged", "5V (cut = 12V)",
             "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", "", "", "NONE"),
    "SJ3O": ("Jumper:SolderJumper_3_Open", "FAN RAIL 24V|BUCK",
             "Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm", "", "", "NONE"),
}


def place(sheet, key, cat, at, nets, rot=0, value=None, **kw):
    lib_id, val, fp, lcsc, mpn, asm = P[cat]
    prefix = None
    if lib_id == "Connector:TestPoint":
        prefix = "TP"
    if lib_id == "power:PWR_FLAG":
        prefix = "#FLG"
    if lib_id.startswith("Jumper:"):
        prefix = "JP"
    if lib_id == "Device:NetTie_2":
        prefix = "NT"
    if lib_id.startswith("Connector_Generic") or lib_id.startswith("Connector:USB"):
        prefix = "J"
    if lib_id == "Device:Polyfuse":
        prefix = "F"
    if cat.startswith("C") and lib_id.startswith("Device:C"):
        prefix = "C"
    return sheet.part(key, lib_id, value or val, at, rot=rot, nets=nets, fp=fp,
                      lcsc=lcsc, mpn=mpn, assembly=asm, prefix=prefix, **kw)


def two(sheet, key, cat, x, y, top, bottom, rot=0, value=None):
    """Two-pin part, vertical: pin 1 to `top`, pin 2 to `bottom`.

    For polarised parts and diodes the caller passes the right order.
    """
    lib_id = P[cat][0]
    if lib_id == "Device:LED":
        # LED symbol is horizontal (K=1 left, A=2 right): rot 90 -> A at top
        return place(sheet, key, cat, (x, y), {"2": top, "1": bottom}, rot=90, value=value)
    if lib_id in ("Device:D_Schottky", "Device:D_TVS"):
        # D symbols are horizontal (K=1 left, A=2 right): rot 270 -> K at top
        return place(sheet, key, cat, (x, y), {"1": top, "2": bottom}, rot=270, value=value)
    return place(sheet, key, cat, (x, y), {"1": top, "2": bottom}, rot=rot, value=value)
