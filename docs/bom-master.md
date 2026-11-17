# BOM master — Nexus Tools Board and Nexus Docks Board

Source of truth: [`bom-master.csv`](bom-master.csv). This is a readable view, generated with `scripts/bom_to_md.py`; do not edit the table by hand. Status: stock and library refreshed in F1 (2026-11-17), see [`library-review.md`](library-review.md).

Column **Tool** = Nexus Tools Board, **Dock** = Nexus Docks Board.

**Assembly:** `JLC` = placed by JLC, `SELF` = hand-soldered, `DNP` = do not populate.
**JLC type:** `Basic` = no fee, `Preferred` = Preferred Extended (no fee with Economic PCBA), `Extended` = ≈ $3 fee per unique part per order.
**Verified:** a date = footprint and pinout checked against the datasheet in F1; `stdlib` = KiCad standard library part, pin mapping checked when placing in the schematic; `F2` = part or footprint still to be chosen in F2.
Rows marked **DECISION** in the notes wait for Berten's choice.

<!-- BOM:START -->
| Group | Description | MPN | LCSC | Tool | Dock | Assembly | JLC type | Stock 17/11 | Price $ (10) | Verified | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MCU | STM32G0B1 MCU LQFP-64 128KB | STM32G0B1RBT6 | C5143679 | 1 | 1 | JLC | Extended | 593 | 2.96 | stdlib | Shared. Stock down from 827 (2026-11-10). CBT6/CET6 sold out |
| Heater/Fan switch | N-MOSFET 40V 4.5mOhm DFN3x3 | WSD4070DN33 | C719095 | 8 | 9 | JLC | Extended | 13019 | 0.28 | 2026-11-17 | Shared. Datasheet has no land pattern: checked vs package dims. Drain pads renumbered to 5. Verify RDS(on) at VGS=4.5V (F2) |
| Gate buffer | Octal buffer HCT 5V TTL inputs SOIC-20 | CD74HCT541M96 | C6560 | 1 | 1 | JLC | Extended | 820 | 0.64 | stdlib | Shared. Inputs 100k pull-down; OE to GND. Stock 820 (was 987) |
| Single buffer | Single buffer AHCT SOT-23-5 | SN74AHCT1G125DBVR | C7484 | 1 | 2 | JLC | Extended | 31384 | 0.10 | stdlib | Tool: LED shifter. Dock: LED shifter + fan 9 gate |
| Cutoff/RPP controller | Ideal diode / high-side switch controller | LM74502DDFR | C3236215 | 1 | 1 | JLC | Extended | 6844 | 0.86 | 2026-11-17 | Pinout checked vs TI table 5-1. Easyeda footprint replaced by KiCad TSOT-23-8. Tool: cutoff back-to-back. Dock: reverse polarity, EN tied high |
| Cutoff/RPP FET | N-MOSFET 60V 1.6mOhm SuperSO8 | BSC016N06NS | C454269 | 2 | 1 | JLC | Extended | 6258 | 0.94 | 2026-11-17 | Easyeda footprint rejected (stray pad). KiCad footprint checked vs PG-TDSON-8 FL outline. Symbol = copy of Q_NMOS_SSSGD_AvalancheRated |
| Buck | Buck 4.5-60V 3.5A SO8-PowerPAD | TPS54360BDDAR | C524806 | 1 | 2 | JLC | Extended | 39035 | 0.63 | stdlib | Tool: 5V. Dock: 5V + fan rail 12/5V |
| Buck inductor | 10uH 4.5A sat 7x6.6mm shielded | MWSA0603S-100MT | C132141 | 1 | 2 | JLC | Extended | 21595 | 0.09 | 2026-11-17 | Pads corrected to datasheet land pattern (2.35x3.5 gap 3.7). Value to be confirmed with WEBENCH (F2). Alt: C436568 |
| LDO | LDO 3.3V 500mA SOT-23-5 | ME6211C33M5G-N | C82942 | 2 | 1 | JLC | Extended | 274773 | 0.06 | stdlib | Extended (not Basic as assumed). Kept over Basic XC6206 for ADC reference noise (decided 2026-11-17) |
| CAN transceiver | CAN transceiver 5V with VIO | TJA1051T/3/1J | C38695 | 1 | 1 | JLC | Extended | 141248 | 0.46 | stdlib | AD-12 populated |
| CAN ESD | CAN bus ESD SOT-23 24V | PESD2CAN | C907830 | 1 | 1 | JLC | Extended | 89116 | 0.05 | 2026-11-17 | Pinout 1/2 = lines 3 = GND (datasheet p1). Symbol = copy of NUP2105L |
| Crystal | 8MHz 20pF 5032 | X50328MSB2GI | C115962 | 1 | 1 | JLC | Basic | 507464 | 0.25 | stdlib | Load caps per AN2867 |
| USB ESD | USB ESD SOT-23-6 | USBLC6-2SC6 | C7519 | 1 | 1 | JLC | Extended | 39686 | 0.16 | stdlib | Extended (not Basic as assumed). No Basic equivalent found |
| USB connector | USB-C 16-pin USB2.0 SMD | TYPE-C-31-M-12 | C165948 | 1 | 1 | JLC | Extended | 514955 | 0.19 | stdlib | No Basic USB-C found. CC1/CC2 5.1k to GND |
| Input TVS | TVS 30V bidirectional SMB | SMBJ30CA | C2925441 | 1 | 1 | JLC | Preferred | 139589 | 0.05 | stdlib | Preferred Extended (no fee with Economic PCBA) |
| Schottky 60V 5A | Schottky 60V 5A SMC (buck catch diode + logic reverse polarity) | SS56C | C24138 | 2 | 2 | JLC | Extended | 90070 | 0.10 | stdlib | Added in F2: TPS54360B is non-synchronous and needs a catch diode (was missing). Replaces SS36. Tool: catch + logic path. Dock: 2 catch. Up to 1.8 W: >= 3 cm2 copper |
| Schottky 40V 1A | Schottky 40V 1A SOD-123 (fan flyback, 3V3 diode-OR) | B5819W SL | C8598 | 2 | 11 | JLC | Basic | 720194 | 0.03 | stdlib | Tool: diode-OR of +5V and VBUS into 3V3_MCU. Dock: 9 fan flyback + 2 diode-OR. 40V > 24V fan rail |
| Analog clamp | Dual Schottky SOT-23 | BAT54S | C408389 | 9 | 0 | JLC | Extended | 641231 | 0.02 | stdlib | No Basic found. 8 thermistor + 1 RAIL_SENSE |
| Thermistor ESD | TVS 30V bidirectional SOD-123FL | SMF30CA | C19077519 | 8 | 0 | JLC | Preferred | 575614 | 0.03 | stdlib | Preferred Extended. Must not conduct at 24V |
| Signal ESD | ESD diode 5V bidirectional SOD-323 | PESD5V0S1BA | C2827694 | 19 | 2 | JLC | Extended | 316355 | 0.04 | stdlib | Vrwm 5V / Vbr 7V: requirement relaxed to Vrwm >= 5V and Vbr >= 6V (decided 2026-11-17). AD-14 |
| Pull-up NTC | 4.7k 0.1% 25ppm 0603 | TD03G4701BT | C666997 | 8 | 0 | JLC | Extended | 5489 | 0.02 | stdlib | Stock down from 12610 |
| Pull-up PT1000 parallel | 4.12k 0.1% 25ppm 0603 | AR03BTCX4121 | C2984354 | 8 | 0 | JLC | Extended | 5214 | 0.03 | stdlib | Bridge closed = 2195 ohm |
| Rail bleeder | 4.7k 0.25W 1206 | 1206W4F4701T5E | C17936 | 1 | 1 | JLC | Basic | 2068489 | 0.01 | stdlib | Tool: heater rail bleeder. Dock: FAN RAIL LED resistor (visible at 5 V, 0.1 W at 24 V) |
| Channel fuse | Fuse 1206 5A 32V fast | 0466005.NRHF | C57525 | 8 | 1 | SELF | Extended | 23580 | 0.10 | stdlib | Replaces C311004 (only 39 left). Dock: input fuse (same part) |
| Main fuse | Fuse 25A 125V SMD very fast | 0456025.ER | C315877 | 1 | 0 | SELF | Extended | 2264 | 0.79 | 2026-11-17 | Pads match Littelfuse recommended layout (3.25x3.43 gap 6.10) within 0.05 mm. Littelfuse: >=100um copper and >=10mm trace at 20-30A (F2) |
| PPTC | PPTC 1206 0.75A hold 1.5A trip 16V | JK-nSMD075-16 | C409806 | 2 | 1 | JLC | Extended | 62329 | 0.03 | stdlib | Replaces JK-NSMD075 C692900 (out of stock). Tool: VCC_FIL + LED. Dock: LED |
| Bulk electrolytic | 100uF 63V THT low impedance 8x16mm | 63ZLH100MEFC8X16 | C88747 | 2 | 1 | SELF | Extended | 29445 | 0.14 | stdlib | Rubycon ZLH. Hand-soldered: no JLC fee. 63V gives margin over the 48.4V TVS clamp (a 50V part would not) |
| Bulk ceramic | 10uF 50V X5R 1206 | CL31A106KBHNNNE | C13585 | 9 | 7 | JLC | Basic | 4379572 | 0.12 | stdlib | X5R (Basic); X7R C89632 is Extended. DC-bias derating at 24V. Tool: input 1, heater rail 4, buck input 2, VCC_FIL 1, LED port 1. Dock: input 1, 5V buck input 2, fan buck input 2, FAN_RAIL 1, LED port 1 |
| Buck output cap | 22uF 25V X5R 1206 | CL31A226KAHNNNE | C12891 | 3 | 7 | JLC | Basic | 2642645 | 0.10 | stdlib | Tool 5V: 3. Dock 5V: 3, fan rail: 4 (25V needed for 12V). See calculations.md |
| Power input tool | XT60 male right angle PCB | XT60PW-M | C98732 | 1 | 0 | SELF | Extended | 141599 | 0.55 | stdlib |  |
| Power input dock | XT30 male right angle PCB | XT30PW-M30.G.Y | C431092 | 0 | 1 | SELF | Extended | 101327 | 0.34 | stdlib |  |
| CAN connector | Micro-Fit 3.0 2x2 right angle | 43045-0400 | C122413 | 2 | 1 | SELF | Extended | 49412 | 0.37 | stdlib | Pads 1 GND / 2 24V(NC) / 3 CANL / 4 CANH = EBB layout (bottom row 24V GND, top row CANH CANL) |
| Heater connector | Screw terminal 2-pole 5.08mm | WJ500V-5.08-2P | C8465 | 8 | 0 | SELF | Extended | 280498 | 0.14 | 2026-11-17 | Phoenix MKDS 1,5 clone: footprint checked against the Kangnex drawing (F3). Alt KF128-5.08-2P C474952 |
| Thermistor connector | JST-XH 2-pin vertical | B2B-XH-A(LF)(SN) | C158012 | 8 | 0 | SELF | Extended | 480587 | 0.04 | stdlib | Right-angle S2B-XH-A C157931 if F2 requires |
| Filament connector | JST-XH 4-pin vertical | B4B-XH-A(LF)(SN) | C144395 | 8 | 0 | SELF | Extended | 523031 | 0.05 | stdlib | Pin1 RUNOUT 2 GND 3 VCC 4 MOTION. Right-angle S4B-XH-A C157925 |
| LED connector | JST-XH 3-pin vertical | B3B-XH-A(LF)(SN) | C144394 | 1 | 1 | SELF | Extended | 82785 | 0.05 | stdlib | Pin1 DIN 2 GND 3 5V |
| Fan connector | JST-XH 2-pin vertical | B2B-XH-A(LF)(SN) | C158012 | 0 | 9 | SELF | Extended | 480587 | 0.04 | stdlib | Pin1 FAN- 2 V+ |
| CAN termination | 2-pin header + jumper cap + 120R | PZ254V-11-02P, jumper cap | C492401 | 1 | 1 | SELF | Extended | 743995 | 0.02 | stdlib | Jumper cap C100114. 120R C22787 Basic (JLC) |
| SWD header | 1x4 2.54mm | HX PZ2.54-1x4P ZZ | C32713270 | 1 | 1 | SELF | Extended | 113702 | 0.03 | stdlib | Optional populate |
| Buttons | Tactile switch SMD 5.1x5.1 (BOOT + RESET) | TS-1187A-B-A-B | C318884 | 2 | 0 | JLC | Basic | 785115 | 0.02 | stdlib | Tool board only (dock uses TS-1088 to save space) |
| Buttons small | Tactile switch SMD 4x3 (BOOT + RESET) | TS-1088-AR02016 | C720477 | 0 | 2 | JLC | Basic | 852756 | 0.05 | stdlib | Dock board (F6 size reduction) |
| LED red | 0603 LED red (diagnostics, AD-17) | KT-0603R | C2286 | 9 | 1 | JLC | Basic | 5511325 | 0.01 | stdlib | Red for heater channels and MCU (decided 2026-11-17). Tool: 8 heater-drain + MCU. Dock: MCU |
| LED green | 0805 LED green (diagnostics, AD-17) | KT-0805G | C2297 | 5 | 5 | JLC | Basic | 3158185 | 0.02 | stdlib | Green for rails (decided 2026-11-17). No Basic green 0603 in stock. Rails: 24V IN / HEATER RAIL or FAN RAIL / 5V / 3V3 / VBUS |
| Capacitor 30pF C0G | Capacitor 30pF C0G 0603 | 0603CG300J500NT | C1658 | 2 | 2 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 100pF C0G | Capacitor 100pF C0G 0603 | CL10C101JB8NNNC | C14858 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 4.7nF | Capacitor 4.7nF 0603 | 0603B472K500NT | C53987 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 22nF | Capacitor 22nF 0603 | CL10B223KB8NNNC | C21122 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 100nF 50V | Capacitor 100nF 50V 0603 | CC0603KRX7R9BB104 | C14663 | 48 | 17 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 1uF 50V | Capacitor 1uF 50V 0603 | CL10A105KB8NNNC | C15849 | 5 | 3 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 4.7uF 16V | Capacitor 4.7uF 16V 0603 | CL10A475KO8NNNC | C19666 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 10R | Resistor 10R 0603 | 0603WAF100JT5E | C22859 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 22R | Resistor 22R 0603 | 0603WAF220JT5E | C23345 | 8 | 9 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 120R | Resistor 120R 0603 | 0603WAF1200T5E | C22787 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 330R | Resistor 330R 0603 | 0603WAF3300T5E | C23138 | 1 | 1 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 470R | Resistor 470R 0603 | 0603WAF4700T5E | C23179 | 2 | 2 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 1k | Resistor 1k 0603 | 0603WAF1001T5E | C21190 | 19 | 2 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 4.7k | Resistor 4.7k 0603 | 0603WAF4701T5E | C23162 | 8 | 0 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 5.1k | Resistor 5.1k 0603 | 0603WAF5101T5E | C23186 | 2 | 2 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 6.8k | Resistor 6.8k 0603 | 0603WAF6801T5E | C23212 | 2 | 2 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 10k | Resistor 10k 0603 | 0603WAF1002T5E | C25804 | 28 | 2 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 36k | Resistor 36k 0603 | 0603WAF3602T5E | C23147 | 1 | 1 | JLC | Preferred |  |  | stdlib | Generic passive |
| Resistor 68k | Resistor 68k 0603 | 0603WAF6802T5E | C23231 | 1 | 3 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 100k | Resistor 100k 0603 | 0603WAF1003T5E | C25803 | 19 | 19 | JLC | Basic |  |  | stdlib | Generic passive |
| Resistor 160k | Resistor 160k 0603 | 0603WAF1603T5E | C22813 | 1 | 2 | JLC | Preferred |  |  | stdlib | Generic passive |
| Resistor 1M | Resistor 1M 0603 | 0603WAF1004T5E | C22935 | 2 | 3 | JLC | Basic |  |  | stdlib | Generic passive |
| Capacitor 8.2nF | Capacitor 8.2nF 0603 | 0603B822K500NT | C1322360 | 0 | 1 | JLC | Basic |  |  | stdlib | Generic passive (fan rail buck) |
| Capacitor 47pF C0G | Capacitor 47pF C0G 0603 | CL10C470JB8NNNC | C1671 | 0 | 1 | JLC | Basic |  |  | stdlib | Generic passive (fan rail buck) |
| Resistor 12k | Resistor 12k 0603 | 0603WAF1202T5E | C22790 | 0 | 1 | JLC | Basic |  |  | stdlib | Generic passive (fan rail buck) |
| Resistor 39k | Resistor 39k 0603 | 0603WAF3902T5E | C23153 | 0 | 1 | JLC | Basic |  |  | stdlib | Generic passive (fan rail buck) |
| Resistor 7.5k | Resistor 7.5k 0603 | 0603WAF7501T5E | C23234 | 0 | 1 | JLC | Basic |  |  | stdlib | Generic passive (fan rail buck) |

**Unique Extended parts placed by JLC: 19** (≈ $58 fee per order): AR03BTCX4121, BAT54S, BSC016N06NS, CD74HCT541M96, JK-nSMD075-16, LM74502DDFR, ME6211C33M5G-N, MWSA0603S-100MT, PESD2CAN, PESD5V0S1BA, SN74AHCT1G125DBVR, SS56C, STM32G0B1RBT6, TD03G4701BT, TJA1051T/3/1J, TPS54360BDDAR, TYPE-C-31-M-12, USBLC6-2SC6, WSD4070DN33.

<!-- BOM:END -->

With **one panel containing both boards** you pay the Extended fee only once.
