# F1 — Parts library review

| | |
|---|---|
| **Date** | 2026-11-17 |
| **Phase** | F1, parts library (see [work-plan.md](work-plan.md)) |
| **Status** | Ready for review |

Stock, prices and Basic/Extended status come from the JLCPCB parts library on 2026-11-17 (`scripts/jlc_parts.py`). All parts are in [`bom-master.csv`](bom-master.csv).

---

## 1. Where symbols and footprints come from

| Source | Parts | Why |
|---|---|---|
| **KiCad 10 standard library** | MCU, 74HCT541, 74AHCT1G125, TPS54360B, ME6211, TJA1051T/3, USBLC6, USB-C (HRO), crystal, diodes, TVS, fuses 1206, polyfuse, LEDs, R/C, all connectors, button | Reviewed by the KiCad library team. Footprints follow IPC-7351 and the manufacturer drawings. |
| **easyeda2kicad → `lib/nexus`** | WSD4070DN33, 0456025.ER, MWSA0603S-100MT | No equivalent footprint in the KiCad library. Checked against the datasheet, corrected where needed. |
| **Copies of standard symbols in `lib/nexus`** | BSC016N06NS (`Q_NMOS_SSSGD_AvalancheRated`), PESD2CAN (`NUP2105L`), WSD4070DN33 (same FET symbol), 0456025.ER (`Fuse`), MWSA0603S (`L`) | The easyeda symbols were unusable (box symbols, reference `U?` on a fuse, all pins "unspecified"). |
| **easyeda symbol kept** | LM74502DDFR | Not in the KiCad library. Pin electrical types set by hand. |

Every `lib/nexus` symbol has the fields `LCSC`, `MPN` and `Assembly`. The corrections are in `scripts/postprocess_lib.py`, which `scripts/import_parts.sh` runs after every import, so a re-import does not lose them.

---

## 2. Footprint verification against the datasheet

| Part | Footprint | Check | Result |
|---|---|---|---|
| WSD4070DN33 | `nexus:PDFN3333-8_…` (easyeda) | Datasheet has **no land pattern**, only package dimensions. Pitch 0.65 ✔. Pads 0.4 × 0.75 over leads b = 0.3, L = 0.4, with toe extension ✔. Exposed pad 2.6 × 2.0 merges with drain pads 5–8 ✔. 0.49 mm to the source pads ✔. Pinout S = 1–3, G = 4, D = 5–8 ✔. | ✔ Drain pads renumbered to "5" so the standard FET symbol fits. Courtyard regenerated (body + 0.25 mm). |
| BSC016N06NS | `Package_SON:Infineon_PG-TDSON-8_6.15x5.15mm` | Easyeda footprint **rejected**: an extra 3.3 mm "pad 3" strip reaches to 0.48 mm from the gate pad. KiCad `TDSON-8-1` rejected too: its 0.85 mm pads do not cover the inner part of the FL leads. Chosen footprint: pads 1.2 × 0.65 over L = 0.74–0.84, b = 0.34–0.54 ✔; drain pad 4.5 × 4.7 (D2 ≤ 4.4, E2 ≤ 3.8, same net) ✔. | ✔ |
| LM74502DDFR | `Package_TO_SOT_SMD:TSOT-23-8` | Pinout checked against TI table 5-1 (1 EN/UVLO, 2 GND, 3 NC, 4 VCAP, 5 VS, 6 GATE, 7 OV, 8 SRC) ✔. DDF = TSOT-23-8, 0.65 pitch. | ✔ Easyeda footprint replaced by the standard one. |
| PESD2CAN | `Package_TO_SOT_SMD:SOT-23` | Pinout from datasheet p.1: 1 and 2 = lines, 3 = common ✔. | ✔ |
| 0456025.ER (25 A) | `nexus:FUSE-SMD_L10.1-W3.1` (easyeda) | Littelfuse recommended pad layout: pads 3.25 × 3.43, gap 6.10, total 12.60. Footprint: 3.25 × 3.43, gap 6.15, total 12.65 (0.05 mm difference). | ✔ |
| MWSA0603S-100MT | `nexus:IND-SMD_L7.1-W6.6` (easyeda) | Sunlord recommended land: I = 2.35, J = 3.7, H = 3.5. Easyeda had 2.15 × 3.32 with gap 3.67. | ✔ **Corrected** to 2.35 × 3.5, gap 3.7. Courtyard was too small (body 6.6 × 7.1 not on F.Fab): regenerated. |

Standard-library footprints were not re-measured. Their pin mapping is checked when the symbol is placed in the schematic (F3), against the datasheet pin table.

---

## 3. Surprises in stock and status

| Part | Expected | Found | Action |
|---|---|---|---|
| STM32G0B1RBT6 | 827 in stock | **593** | Enough for 10 boards. Order the prototypes without long delay. |
| ME6211C33 | Likely Basic | **Extended** | Decision 1 below. |
| USBLC6-2SC6 | Likely Basic | **Extended** | No Basic equivalent. Kept. |
| SMBJ30CA | Basic | Not Basic; **Preferred Extended** (C2925441) | No fee with Economic PCBA. |
| SMF30CA | TBD | **Preferred Extended** (C19077519) | No fee. |
| Channel fuse C311004 | 85 in stock | **39** | Replaced by Littelfuse 0466005.NRHF (C57525, 23,580). |
| Polyfuse JK-NSMD075 C692900 | In stock | **0** | Replaced by JK-nSMD075-16 (C409806, 62,329), same maker, 16 V. |
| 4.7 kΩ 0.1 % C666997 | 12,610 | 5,489 | Enough. |
| Green 0603 LED | Basic | Basic C72043 has **0** stock | Decision 3 below. |
| 10 µF 50 V 1206 X7R | Basic | Only **X5R** is Basic (C13585) | Kept X5R; DC-bias derating to account for in F2. |

**Extended count.** 20 unique Extended parts are placed by JLC, against ≈ 15 assumed in the cost estimate. That is ≈ $61 fee per order instead of ≈ $46. Main reasons: ME6211, USBLC6, USB-C, SS36, BAT54S and the signal ESD diode turned out not to be Basic.

---

## 4. Decisions for Berten

1. **3.3 V LDO.** ME6211C33 is Extended. Basic alternative: **XC6206P332MR-G** (C5446): 200 mA, SOT-23-3, max. 6 V input.
   - For: saves ≈ $3 per order; 200 mA is enough (3V3_MCU ≈ 60 mA, 3V3_AUX ≤ 100 mA by design).
   - Against: lower PSRR and higher noise; VREF_A hangs off 3V3_MCU (ratiometric measurement cancels much of it); 3V3_AUX at 100 mA dissipates ≈ 0.14 W in SOT-23-3 (≈ +35 °C).
   - My advice: **keep ME6211.** $3 per order does not outweigh a noisier ADC reference.
2. **Signal ESD diode** (filament inputs, VCC_FIL, LED port; 21 pcs). The design asked for a working voltage ≥ 5.5 V.
   - **PESD5V0S1BA** (C2827694, Extended): Vrwm 5 V, breakdown ≈ 7 V, leakage 100 nA. Strictly below the 5.5 V requirement, but it does not conduct at 5.25 V (5 V + 5 %).
   - **SMF6.0A** (C19077499, Preferred, no fee): Vrwm 6 V, but leakage up to 400 µA at Vrwm. On a 10 kΩ pull-up input that could pull the signal low.
   - My advice: **PESD5V0S1BA**, and relax the requirement in design part 3 to "Vrwm ≥ 5 V, Vbr ≥ 6 V".
3. **LED colours.** Basic red 0603 (C2286) is in stock; green is only Basic as 0805 (C2297).
   - Proposal: green 0805 for the rails (24V IN, HEATER/FAN RAIL, 5V, 3V3, VBUS), red 0603 for the heater channels and MCU. Red for "heater on" also reads naturally.

---

## 5. Left for F2

- Buck inductor value and the bulk electrolytic (ripple current): WEBENCH and calculations.
- Screw terminal footprint (WJ500V-5.08-2P or KF128) and straight versus right-angle JST-XH: follow from the mechanical layout.
- WSD4070DN33: R_DS(on) at V_GS = 4.5 V (open item 13).
- **Main fuse and power trunk:** Littelfuse states ≥ 100 µm copper (≈ 3 oz) and ≥ 10 mm trace width for the 20–30 A ratings to keep the fuse body below 90 °C. Our plan is 7 mm per layer on 2 layers at 1 oz. To be included in the IPC-2152 calculation (open item 16).

---

## 6. Tooling added in F1

| Script | Purpose |
|---|---|
| `scripts/jlc_parts.py` | Look up stock, Basic/Extended/Preferred, price and datasheet by C number, or search by keyword. |
| `scripts/import_parts.sh` | easyeda2kicad import for the `lib_source = easyeda` lines, stops if the EasyEDA API refuses (it returns exit code 0 on failure). |
| `scripts/postprocess_lib.py` | All library corrections from §2, idempotent. |
| `scripts/bom_to_md.py` | Regenerates the table in `bom-master.md` from the CSV. |
