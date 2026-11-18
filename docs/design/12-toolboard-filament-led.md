# Nexus Tools Board — Detailed design part 3: filament inputs and LED port

| | |
|---|---|
| **Version** | 0.3 (draft) |
| **Date** | 2026-11-17 |
| **Basis** | Architecture v1.6, detailed design part 1 v0.3 and part 2 v0.4 |
| **Status** | Component selection, before schematic entry |

---

## 1. Summary

| Block | Component | LCSC | Stock | Price (approx.) | Qty | Type |
|---|---|---|---|---|---|---|
| Filament connector | JST-XH **4-pin**, straight | *hand-soldered* | — | ~$0.04 | 8 | — |
| LED connector | JST-XH 3-pin, straight | same | — | ~$0.03 | 1 | — |
| LED level shifter | **SN74AHCT1G125DBVR** | C7484 | 4,815 | $0.05 | 1 | Extended |
| Polyfuse (sensors and LED) | **JK-NSMD075**, 1206, 0.75 A hold / 1.5 A trip, 6 V | C692900 | *check at schematic stage* | ~$0.05 | 2 | Extended |
| Pull-ups, series resistors, capacitors | 0603 | Basic | — | — | ≈ 50 (16 inputs × 3 + LED port) | Basic |
| Signal ESD diodes | **PESD5V0S1BA** (Vrwm 5 V, Vbr ≈ 7 V, SOD-323; 16 inputs + VCC_FIL + LED DIN + LED 5V) | C2827694 | 316,355 | $0.04 | 19 | Extended |
| VCC selection solder jumper | 3 pads, on the PCB | — | — | free | 1 | — |

This part adds **2 unique Extended parts**. They were already in the cost estimate as "LED shifter + PPTC".

---

## 2. Filament inputs (8×, each with runout + motion)

One **JST-XH 4-pin** connector per tool. The user chooses per tool:
- **a D2F (or other switch)** for simple filament detection, connected to pins 1 + 2;
- **a combined runout and motion sensor** (e.g. BTT SFS v2 type) that also detects clogs and a slipping extruder, connected to all 4 pins;
- or only a motion sensor (pins 2, 3, 4).

*(Changed in v0.3: was 3-pin, runout only.)*

### 2.1 Circuit per channel (2 identical inputs: RUNOUT and MOTION)

```
              VCC_FIL (5V default, or 3V3_AUX via solder jumper; fused 0.75 A for all 8)
                 │
JST-XH pin 3 ●───┘                                      3V3_MCU          3V3_MCU
                                                           │                │
                                                        [10 kΩ]          [10 kΩ]
                                                           │                │
JST-XH pin 1 (RUNOUT) ●───[1 kΩ]───────────────────────────┼──► FT GPIO     │
                                                         100 nF             │
JST-XH pin 4 (MOTION) ●───[1 kΩ]────────────────────────────────────────────┼──► FT GPIO
                                                                          100 nF
JST-XH pin 2 (GND)    ●──────────────────────────────────────────────────── GND
(+ ESD diode per signal line at the connector)
```

**Pinout (on the silkscreen):** 1 = RUNOUT, 2 = GND, 3 = VCC, 4 = MOTION.
A D2F uses only pins 1 and 2 (adjacent). Check the pinout of common sensors (e.g. BTT SFS v2) in F1. If it differs, the user makes an adapter cable. The board pinout stays consistent: signal on pin 1, GND next to it.

### 2.2 Choices

| Choice | Rationale |
|---|---|
| **4 pins per tool instead of 3** | The user can choose between a simple switch and clog detection without changing hardware. Costs 1 extra input network per channel (2 resistors, 1 capacitor, 1 ESD diode) and 1 MCU pin. |
| **10 kΩ pull-up to 3.3 V** (MCU rail, not VCC_FIL) | A passive switch pulls to GND. Open-collector sensor outputs also work. The logic stays at 3.3 V, whatever the VCC choice. An unconnected input stays high, so no floating pin. |
| **1 kΩ + 100 nF (τ ≈ 0.1 ms)** | Filters bounce and interference. Motion sensors give a few to a few dozen pulses per second, well below the limit of this filter. |
| **FT pins only (5V tolerant, without analog function)** | Active 5V sensors may connect directly to the input. ST: FT pins are 5V tolerant as digital input, not in analog mode. |
| **ESD diode per signal line** (AD-14) | Vrwm ≥ 5 V and Vbr ≥ 6 V, so it never conducts at 5 V + 5 %. Also on VCC_FIL. *(Changed 2026-11-17: was "working voltage ≥ 5.5 V"; no Basic or low-leakage part met that, see library-review §4.2.)* |
| **VCC_FIL default 5 V** *(changed: was 3.3 V)* | 8 active motion sensors (≈ 20–25 mA each) draw ≈ 0.2 A. From 3V3_AUX the ME6211 (SOT-23-5) would have to dissipate ≈ 0.3 W, which is too hot. From the 5V buck it is no problem. A D2F works on both. 3.3 V remains possible via the solder jumper, but max. 100 mA in total (silkscreen). |
| **Shared 0.75 A polyfuse on VCC_FIL** | A short in a sensor cable does not pull down the MCU supply. |

### 2.3 Klipper

Per tool in the include file: one or both sections, depending on the sensor.

```ini
# Switch (D2F: COM → GND, NO → RUNOUT): low = filament present
[filament_switch_sensor t0_runout]
switch_pin: !nexus_tools:PXX      # external pull-up, so no ^
pause_on_runout: True

# Motion sensor: clog / slipping extruder
[filament_motion_sensor t0_motion]
switch_pin: nexus_tools:PYY
detection_length: 10            # mm of extrusion without a pulse → runout_gcode
extruder: extruder              # the physical extruder that pushes the filament
pause_on_runout: True
```

**Important:** `[filament_motion_sensor]` is tied to an `[extruder]`. If the hotends have no extruder stepper of their own, all sensors point to the physical extruder. The tool change macro uses `SET_FILAMENT_SENSOR SENSOR=tN_motion ENABLE=1/0` to enable only the sensor of the active tool. Otherwise a parked tool raises an alarm. To be worked out in F8 (open item 28).

**Limitation:** a motion sensor sees complete clogs and an extruder grinding filament (after `detection_length`). It does not see a partial clog where the filament still moves.

---

## 3. LED port

### 3.1 Circuit

```
5V_RAIL ──[polyfuse 0.75 A]──┬──────────────► JST-XH pin 3 (5V)
                             │
                           10 µF
                             │
MCU GPIO ──► 74AHCT1G125 (VCC = 5 V, OE = GND) ──[330 Ω]──► JST-XH pin 1 (DIN)
GND ─────────────────────────────────────────► JST-XH pin 2 (GND)
```

**Pinout:** 1 = DIN, 2 = GND, 3 = 5V. Same convention as the filament connectors: signal on pin 1, GND on pin 2.

### 3.2 Choices

| Choice | Rationale |
|---|---|
| **74AHCT1G125 at 5 V** | WS2812 requires V_IH ≥ 0.7 × 5 V = 3.5 V. Driving it directly at 3.3 V sometimes works, but not always. The AHCT input recognises 3.3 V as high and outputs 5 V. |
| **Why not the 74HCT541** | All 8 of its channels already drive the heater MOSFETs. |
| **Pull-down on the input (100 kΩ)** | No floating data during a reset, so no random colours. |
| **330 Ω in series** | Damps reflections on the data line and protects the output in case of a short. |
| **0.75 A polyfuse** | 8 × WS2812 full white = 0.48 A. 0.75 A gives margin. On a short the 5V rail (and therefore the MCU) does not drop out. |
| **Same polyfuse as for the filament sensors** | One unique part for both. |
| **10 µF at the connector** | Buffer for the current peaks of the LEDs. |
| **ESD diode on DIN and 5V** (AD-14) | Same type as on the filament inputs. |

### 3.3 Klipper

```ini
[neopixel toolboard_leds]
pin: nexus_tools:PXX
chain_count: 8
color_order: GRB
```

---

## 4. Updated STM32G0B1RBT6 pin budget

| Function | Pins | Requirement |
|---|---|---|
| Heater PWM (to 74HCT541) | 8 | Any GPIO |
| Thermistor ADC | 8 | ADC channel |
| Rail voltage measurement | 1 | ADC channel (AD-13) |
| Filament inputs (runout + motion) | 16 | **FT pin**, no analog function |
| LED data | 1 | Any GPIO |
| Cutoff EN | 1 | Any GPIO |
| USB | 2 | PA11/PA12 |
| FDCAN | 2 | According to Klipper options |
| SWD / BOOT0 | 2 | PA13/PA14 |
| Crystal | 2 | PF0/PF1 (OSC) |
| Status LED | 1 | Any GPIO |
| **Total** | **44** | LQFP-64 has ≈ 60 GPIO, so plenty |

---

## 5. The tool board is functionally complete

After parts 1 to 3, all functional requirements from the architecture (FR-T01 to FR-T09) have been translated into components. Two small things still need to be aligned between the documents:

1. **Cost estimate:** unchanged. The items of part 3 were already included.
2. **Architecture §6.1.4 and §6.1.5:** the connector types (JST-XH) are already in there. The pinout from this document becomes the reference in the schematic phase.

---

## 6. Open items for the schematic phase

1. Check stock of the JK-NSMD075 polyfuse. Alternative: another 0.75A 1206 PPTC from the same list.
2. STM32G0B1RBT6 datasheet (Table "Pin definitions"): choose the 16 filament pins as FT or FT_f, and the 9 ADC pins (8 thermistors + RAIL_SENSE) as FT_a or TT_a.
3. JST-XH: choose right-angle or straight depending on the mechanical installation (part 4, layout).

---

## Sources

- [LCSC SN74AHCT1G125DBVR](https://www.lcsc.com/product-detail/C7484.html)
- [JLCPCB JK-NSMD075](https://jlcpcb.com/partdetail/726297-JKNSMD075/C692900)
- [ST Community: 5V tolerance of FT_a pins on the STM32G0](https://community.st.com/t5/stm32-mcus-products/in-g0-what-s-the-input-voltage-range-of-ft-a-pin-when-analog/td-p/650209)
- [ST AN4899: GPIO configuration](https://www.st.com/resource/en/application_note/an4899-generalpurpose-io-gpio-configuration-for-stm32-mcus-stmicroelectronics.pdf)
- [STM32G0B1RE datasheet](https://www.st.com/resource/en/datasheet/stm32g0b1re.pdf)
