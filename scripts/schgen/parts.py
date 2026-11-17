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
}


def place(sheet, key, cat, at, nets, rot=0, value=None, **kw):
    lib_id, val, fp, lcsc, mpn, asm = P[cat]
    prefix = None
    if lib_id == "Connector:TestPoint":
        prefix = "TP"
    if lib_id == "power:PWR_FLAG":
        prefix = "#FLG"
    if cat.startswith("C") and lib_id.startswith("Device:C"):
        prefix = "C"
    return sheet.part(key, lib_id, value or val, at, rot=rot, nets=nets, fp=fp,
                      lcsc=lcsc, mpn=mpn, assembly=asm, prefix=prefix, **kw)


def two(sheet, key, cat, x, y, top, bottom, rot=0, value=None):
    """Two-pin part, vertical: pin 1 to `top`, pin 2 to `bottom`.

    For polarised parts and diodes the caller passes the right order.
    """
    lib_id = P[cat][0]
    if lib_id in ("Device:D_Schottky", "Device:D_TVS"):
        # D symbols are horizontal (K=1 left, A=2 right): rot 270 -> K at top
        return place(sheet, key, cat, (x, y), {"1": top, "2": bottom}, rot=270, value=value)
    return place(sheet, key, cat, (x, y), {"1": top, "2": bottom}, rot=rot, value=value)
