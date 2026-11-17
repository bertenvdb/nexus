# Open items

Close an item with date and result. If the result changes a design document, update that document too.

## Before or during F1 (parts)

| # | Item | Source |
|---|---|---|
| 1 | Refresh stock and Basic/Extended status of every line in `bom-master.csv` | CLAUDE.md §4 |
| 2 | Check Basic status: ME6211, USBLC6-2SC6, crystal C115962, SS36, SMBJ30CA, BAT54S, SMF30CA, electrolytic caps, USB-C 16-pin, buttons | part 1/2/3 |
| 3 | 4.12 kΩ 0.1 % 0603: concrete LCSC number | part 1 §7 |
| 4 | Channel fuse 5 A 1206: alternative with more stock than 85 pcs (C311004) | part 1 §7 |
| 5 | PESD2CAN: variant with the largest stock | part 2 |
| 6 | PPTC JK-NSMD075 (C692900): check stock, otherwise a 0.75 A alternative in 1206 | part 3 §6 |
| 7 | 2-pole screw terminal 5.08 mm and JST-XH 2/3/4-pin: concrete parts (straight or right-angle follows from F2) | part 1/3 |
| 8 | Inductor 10 µH ≥ 4.5 A saturation, shared by all bucks | dock §4 |
| 8a | ESD diode for filament and LED lines (working voltage ≥ 5.5 V, Basic variant) | part 3, AD-14 |
| 8b | Heater rail bleeder resistor (4.7 kΩ, ≥ 0.25 W): recalculate discharge time with the real rail capacitance | part 1 §5.1 |

## F2 (pinout, mechanics, calculations)

| # | Item | Source |
|---|---|---|
| 9 | STM32G0B1RBT6: does the LQFP-64 have a separate VREF+ pin? | part 1 §3, §6.3 |
| 10 | FDCAN/USB pin choice according to Klipper support (source code) | part 2 §5 |
| 11 | Klipper build for the 128KB variant (flash offset with Katapult) | part 1 §3 |
| 12 | 9 ADC pins (FT_a; 8 thermistor + RAIL_SENSE) and **16** filament pins (FT, without analog function) | part 3 §4 |
| 12a | Compare the pinout of common runout/motion sensors (e.g. BTT SFS v2) with the board pinout 1 RUNOUT / 2 GND / 3 VCC / 4 MOTION | part 3 §2.1 |
| 13 | WSD4070DN: R_DS(on) at V_GS = 4.5 V and the SOA under PWM | part 1 §7 |
| 14 | LM74502 in a single-FET configuration (dock board reverse polarity protection) | dock §9 |
| 15 | TPS54360B: component values for 5V/1.5 A and 12V/5V at 3 A (WEBENCH) | part 2 §9, dock §9 |
| 16 | Trace widths and 1 oz or 2 oz copper (IPC-2152) | CLAUDE.md §6 |
| 17 | **Mechanics: dimensions, mounting holes, connector edges, height. Ask Berten.** | work plan F2 |

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
