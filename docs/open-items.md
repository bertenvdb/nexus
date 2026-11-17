# Open items

Close an item with date and result. If the result changes a design document, update that document too.

## Before or during F1 (parts)

| # | Item | Source | Status |
|---|---|---|---|
| 1 | Refresh stock and Basic/Extended status of every line in `bom-master.csv` | CLAUDE.md §4 | ✅ 2026-11-17: done, see [library-review.md](library-review.md) §3 |
| 2 | Check Basic status: ME6211, USBLC6-2SC6, crystal C115962, SS36, SMBJ30CA, BAT54S, SMF30CA, electrolytic caps, USB-C 16-pin, buttons | part 1/2/3 | ✅ 2026-11-17: only crystal and button are Basic; SMBJ30CA and SMF30CA Preferred; rest Extended. LDO: ME6211 kept (2026-11-17) |
| 3 | 4.12 kΩ 0.1 % 0603: concrete LCSC number | part 1 §7 | ✅ 2026-11-17: C2984354 (Viking AR03BTCX4121, 25 ppm) |
| 4 | Channel fuse 5 A 1206: alternative with more stock than 85 pcs (C311004) | part 1 §7 | ✅ 2026-11-17: C311004 down to 39; replaced by Littelfuse 0466005.NRHF C57525 |
| 5 | PESD2CAN: variant with the largest stock | part 2 | ✅ 2026-11-17: C907830 (89,116 pcs) |
| 6 | PPTC JK-NSMD075 (C692900): check stock, otherwise a 0.75 A alternative in 1206 | part 3 §6 | ✅ 2026-11-17: out of stock; replaced by JK-nSMD075-16 C409806 |
| 7 | 2-pole screw terminal 5.08 mm and JST-XH 2/3/4-pin: concrete parts (straight or right-angle follows from F2) | part 1/3 | 🟡 JST-XH chosen (vertical + right-angle alternatives in the BOM); screw terminal C8465 chosen, footprint in F2 |
| 8 | Inductor 10 µH ≥ 4.5 A saturation, shared by all bucks | dock §4 | 🟡 C132141 chosen and footprint verified; value to be confirmed in F2 (WEBENCH) |
| 8a | ESD diode for filament and LED lines (working voltage ≥ 5.5 V, Basic variant) | part 3, AD-14 | ✅ 2026-11-17: PESD5V0S1BA C2827694; requirement relaxed to Vrwm ≥ 5 V, Vbr ≥ 6 V (part 3 updated) |
| 8b | Heater rail bleeder resistor (4.7 kΩ, ≥ 0.25 W): recalculate discharge time with the real rail capacitance | part 1 §5.1 | ⏳ Part chosen (C17936); calculation after the schematic |
| 8c | Bulk electrolytic 100 µF 50 V: no Basic part; choose with the ripple-current calculation | F1 | ⏳ F2 |
| 8d | Main fuse: Littelfuse asks ≥ 100 µm copper and ≥ 10 mm trace at 20–30 A; include in the trunk calculation | F1, datasheet 0456 | ⏳ F2, with item 16 |

## F2 (pinout, mechanics, calculations)

| # | Item | Source | Status |
|---|---|---|---|
| 9 | STM32G0B1RBT6: does the LQFP-64 have a separate VREF+ pin? | part 1 §3, §6.3 | ✅ 2026-11-17: yes, pin 7 ([pinout-toolboard.md](pinout-toolboard.md)) |
| 10 | FDCAN/USB pin choice according to Klipper support (source code) | part 2 §5 | ✅ 2026-11-17: USB PA11/PA12, CAN PB0/PB1 (FDCAN2), also as USB-CAN bridge |
| 11 | Klipper build for the 128KB variant (flash offset with Katapult) | part 1 §3 | ✅ 2026-11-17: Klipper assumes 128 KiB (`FLASH_SIZE` 0x20000) for every STM32G0; Katapult 8 KiB offset. Confirm by building in F8 |
| 12 | 9 ADC pins (FT_a; 8 thermistor + RAIL_SENSE) and **16** filament pins (FT, without analog function) | part 3 §4 | ✅ 2026-11-17: PA0–PA7 + PC4; 16 filament pins without `_a` |
| 12a | Compare the pinout of common runout/motion sensors (e.g. BTT SFS v2) with the board pinout 1 RUNOUT / 2 GND / 3 VCC / 4 MOTION | part 3 §2.1 | ⏳ Before F3 sheet `filament_inputs` |
| 13 | WSD4070DN: R_DS(on) at V_GS = 4.5 V and the SOA under PWM | part 1 §7 | ✅ 2026-11-17: 5.3 mΩ typ / 7.6 mΩ max at 4.5 V; ≈ 0.08 W per channel hot. 10 Hz PWM: switching losses negligible, SOA not a concern |
| 14 | LM74502 in a single-FET configuration (dock board reverse polarity protection) | dock §9 | ✅ 2026-11-17: possible; FET source to the input, body diode conducts first, controller then turns it on; EN tied high, OV to GND (dock §4 updated) |
| 15 | TPS54360B: component values for 5V/1.5 A and 12V/5V at 3 A (WEBENCH) | part 2 §9, dock §9 | ✅ 2026-11-17: TI equations + loop-gain check with TI's small-signal model ([calculations.md](calculations.md) §5): PM ≥ 60°, GM ≥ 11 dB in all cases. WEBENCH not run (no browser access). Load-step test on the prototype |
| 16 | Trace widths and 1 oz or 2 oz copper (IPC-2152) | CLAUDE.md §6 | ✅ 2026-11-17: 1 oz, trunk 12 mm on L1+L3+L4 |
| 17 | **Mechanics: dimensions, mounting holes, connector edges, height. Ask Berten.** | work plan F2 | ✅ 2026-11-17: concept A (rows per type), 1.0 mm overhang, straight JST-XH ([mechanical.md](mechanical.md) §7) |

## F3 (schematic)

| # | Item | Source | Status |
|---|---|---|---|
| 29 | CAN Micro-Fit pin numbering: check against BTT EBB/U2C cables before layout | design 11 §5, sheet `usb_can` | ✅ 2026-11-17: EBB photo (Berten). Mating face, PCB below: bottom 24V · GND, top CAN-H · CAN-L → KiCad pads 1 GND, 2 24V (NC), 3 CAN-L, 4 CAN-H. The first assumption (1 24V, 2 GND, 3 CAN-H, 4 CAN-L) was wrong and is corrected |
| 30 | STM32G0 option byte nBOOT_SEL: does the BOOT button select DFU on a fresh chip? (empty flash boots to DFU regardless) | sheet `mcu` | ⏳ F8, first board |

## F7 (ordering)

| # | Item | Source |
|---|---|---|
| 18 | JLC fee for "different designs" in one panel with PCBA | dock §8 |
| 19 | Real JLC quote → update cost estimate | cost estimate |

## Outside the boards (later)

| # | Item | Source |
|---|---|---|
| 20 | Heater choice. Then measure the R(T) curve (cold and ~250 °C) and recalculate the PSU | architecture §7, §11 |
| 21 | Power needed to keep a parked hotend warm: measure on the prototype | architecture §11 |
| 22 | Panel connector per tool (keyed, ≥ 4 pins, ≥ 3 A/pin) | architecture §10 |
| 23 | Klipper macros: tool change, dock fans per parked tool, commissioning macro | architecture §9.5 |
| 24 | Reading RAIL_SENSE in Klipper (temperature_sensor + adc_temperature table or QUERY_ADC); no shutdown at 0 V | architecture §9.6 |
| 25 | `M104/M109 Tn` → hotends: macro override with `[heater_generic]` or hotends as `[extruder<n>]`. Also what Mainsail/Fluidd/KlipperScreen display | architecture §9.7 |
| 26 | Staggered heat-up: max. 3 heaters cold at once, in the macro layer, with and without `is_extruder_used` | architecture §9.8 |
| 27 | OSHW logo on the silkscreen only if OSHWA certification is applied for/met | CLAUDE.md §7.9 |
| 28 | Motion sensors in Klipper: link to the physical extruder and enable only the active tool's sensor (`SET_FILAMENT_SENSOR`) in the tool change macro | part 3 §2.3 |
