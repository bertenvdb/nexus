# Nexus Tools Board — Detailed design part 1: heater channels, cutoff, thermistor input

| | |
|---|---|
| **Version** | 0.3 (draft) |
| **Date** | 2026-11-17 |
| **Basis** | Architecture document v1.6 |
| **Status** | Component selection, before schematic entry |

---

## 1. Scope and constraints

This document fixes the critical components for three blocks of the tool board:

1. the 8 heater channels,
2. the heater cutoff (including reverse polarity protection of the heater rail),
3. the 8 thermistor inputs.

The MCU choice is also covered here, because stock availability influences that choice.

**Sourcing rule**
- Everything must be in stock at JLCPCB/LCSC.
- Passives and generic parts come from the Basic library.
- As few unique Extended parts as possible.
- Stock checked on 2026-11-10.

**Change from v0.1:** the USB-C tool ports are gone (architecture v0.6, AD-02/03). The heaters now switch low-side with ordinary N-MOSFETs instead of high-side with the BTT6050-2ERA.

---

## 2. Summary

| Block | Component | LCSC | Stock | Price (approx.) | Qty |
|---|---|---|---|---|---|
| MCU | **STM32G0B1RBT6** (LQFP-64, 128 KB) | C5143679 | 827 | $2.10 | 1 |
| Heater MOSFET | **Winsok WSD4070DN** (40 V, 4.5 mΩ @ 10 V, DFN3×3) | C719095 | 11,723 | $0.17 | 8 |
| Gate buffer | **CD74HCT541M96** (octal buffer, 5 V, TTL inputs) | C6560 | 987 | $0.64 | 1 |
| Channel fuse | 1206 SMD fuse, 5 A / 32 V | e.g. C311004 | 85 (pick alternative) | $0.16 | 8 |
| Cutoff controller | **TI LM74502DDFR** | C3236215 | 1,880 | $0.57 | 1 |
| Cutoff FETs | **Infineon BSC016N06NS** (60 V, 1.6 mΩ) | C454269 | 6,793 | $0.62 | 2 |
| Pull-up NTC | 4.7 kΩ 0.1 % 25 ppm 0603 | C666997 | 12,610 | $0.015 | 8 |
| Pull-up PT1000 (parallel) | 4.12 kΩ 0.1 % 0603 | *TBD* | — | — | 8 |
| ADC clamp | BAT54S (SOT-23) | *Basic if available* | — | — | 9 (8 thermistor + RAIL_SENSE) |
| Heater connector | 2-pole screw terminal, 5.08 mm | *Basic or cheap, hand-soldered* | — | ~$0.08 | 8 |
| Thermistor connector | JST-XH 2-pin, straight | *hand-soldered* | — | ~$0.03 | 8 |
| Thermistor ESD | SMF30CA (≥ 26 V working voltage) | *Basic if available* | — | — | 8 |
| Channel diagnostic LED | 0603 LED + ≈ 11 kΩ (AD-17, §4.3) | Basic | — | — | 8 |
| Rail sense + bleeder | 100k/10k 1 %, 1 kΩ, 100 nF + 4.7 kΩ ≥ 0.25 W (§5.1) | Basic | — | — | 1 set |

### 2.1 Rejected candidates

| Candidate | Reason |
|---|---|
| Infineon BTT6050-2ERA (high-side) | No longer needed without USB-C ports. ≈ $9.50 more expensive per board. |
| AO3400A (Basic, 30 V) | 30 V is too tight on a 24V rail whose TVS clamps up to 48 V |
| MOSFET directly on 3.3V GPIO | The WSD4070DN has V_GS(th) up to ≈ 2.5 V. At 3.3 V it is not guaranteed fully on. The buffer provides 5 V gate voltage. |
| STM32G0B1CBT6 / CET6 / RET6 | Sold out or insufficient stock |

---

## 3. MCU: STM32G0B1RBT6

Unchanged from v0.1:
- LQFP-64 with 128 KB flash. Klipper and Katapult fit comfortably.
- **To check in the schematic phase:**
  - Does the LQFP-64 have a separate VREF+ pin?
  - Does Klipper's G0B1 build handle a 128 KB variant correctly?
  - Pin choice for the 9 ADC inputs (8 thermistors + RAIL_SENSE), USB and FDCAN (CAN is populated, AD-12).

---

## 4. Heater channels

### 4.1 Circuit per channel

```
HEATER RAIL (behind cutoff) ─► fuse 5 A ─► screw terminal pin 1 (+24V)
                                           screw terminal pin 2 (heater−) ─► drain WSD4070DN
MCU GPIO ─► 74HCT541 (5 V) ─[22 Ω]─► gate                                    source ─► PGND
              input: 100 kΩ pull-down        gate: 100 kΩ pull-down
```

### 4.2 Choices

| Choice | Rationale |
|---|---|
| **WSD4070DN** (40 V) | 40 V gives margin above 24 V. At 2.9 A and ≈ 7 mΩ (5 V gate, warm) the dissipation is ≈ 60 mW per channel. No heatsink is needed, just a normal copper area. Cheap, and widely used on Chinese printer boards. |
| **74HCT541 as gate driver** | One IC for all 8 channels. TTL inputs recognise 3.3 V as high. The outputs provide 5 V to the gate. |
| **Pull-downs on buffer input and gate** | During an MCU reset, the bootloader or the 5V rail start-up all MOSFETs are guaranteed off. The OE pins are tied to GND. |
| **No flyback diode** | Heaters are resistive. |
| **5 A fuse in the +24V line** | On a short from heater+ to ground somewhere in the wiring it protects the wires to the panel and umbilical. The main fuse (25 A) is too large for that. |

### 4.3 Diagnostic LED per channel

An LED with ≈ 11 kΩ in series, from `+24V_HEATER` to the drain of each MOSFET:
- **MOSFET on:** the LED is lit.
- **MOSFET off, heater connected:** both sides of the LED are at 24 V, so the LED is off.
- **No heater connected:** the drain floats, the LED leakage current pulls it up, so the LED is off.
- **MOSFET failed short:** the LED is lit while Klipper has the channel off. You see the fault immediately.

Because the LED shows the **actual** state of the drain and not the control signal, it also reveals a fault the MCU cannot see.

### 4.4 What the MOSFET does not cover

With low-side switching, heater+ is permanently at 24V. If heater− touches ground (for example a damaged wire against the frame), current flows through the heater, bypassing the MOSFET. Klipper then detects overheating (`verify_heater`/`max_temp`) and shuts down. **The cutoff (§5) then removes the voltage.** That makes the cutoff mandatory (AD-10).

---

## 5. Heater cutoff: LM74502 + 2× BSC016N06NS

Unchanged from v0.1.

```
XT60 ─► main fuse 25 A ─► TVS SMBJ30CA (bidir.) ─┬─► [Q1]──[Q2] ─► HEATER RAIL ─► 8× fuse ─► screw terminals
                                                 │    ▲ back-to-back N-FET
                                                 │    └─ LM74502 (EN ◄─ MCU GPIO, 100 kΩ pull-down)
                                                 └─► SS56C ─► 5V buck ─► 3.3V
```

| Parameter | Value | OK |
|---|---|---|
| LM74502 V_IN | 3.2–65 V | ✔ |
| EN threshold | 1.24 V (3.3V GPIO) | ✔ |
| EN low → gate off | ≈ 2 µs | ✔ |
| Turn-on | Slow (60 µA gate current), acts as soft start | ✔ |
| FETs | 60 V, 1.6 mΩ, V_GS ±20 V | ✔ |
| Dissipation average scenario (14 A) | ≈ 0.9 W total | copper ≥ 4 cm² per FET |
| Dissipation worst case (23.6 A, brief) | ≈ 2.7 W total | same |

Klipper: `output_pin heater_enable`, `value: 1`, `shutdown_value: 0`.
There is a "HEATER RAIL LIVE" LED on the heater rail, so you can check the cutoff visually.

### 5.1 Heater rail voltage measurement (AD-13)

```
+24V_HEATER ──[100 kΩ 1 %]──┬──[1 kΩ]──┬──► ADC pin (RAIL_SENSE)
                            │          │
                       [10 kΩ 1 %]   100 nF   BAT54S (clamp to VREF_A / AGND)
                            │          │
                           AGND       AGND
```

| Parameter | Value |
|---|---|
| Division ratio | 11 (100 k / 10 k) |
| 24 V → ADC | 2.18 V |
| Range up to clamp | ≈ 36 V (above the 30 V TVS standoff) |
| Resolution | ≈ 9 mV on the rail per LSB, more than sufficient |
| Rail load | ≈ 0.22 mA, negligible |

**Discharge time after cutoff.** With the heaters off, the rail capacitance discharges only through the divider and the LED. A **4.7 kΩ / 0.25 W bleeder resistor** (≈ 5 mA, 0.12 W at 24 V; 1206 or larger) keeps the discharge time below ≈ 0.1 s at ≈ 20 µF rail capacitance. The exact rail capacitance follows from the schematic; recalculate the time constant then. The LED resistor can serve as bleeder if the current is ≥ 5 mA.

BAT54S and the 0603 resistors are the same parts as in the thermistor input. No new unique parts are added.

---

## 6. Thermistor input (8×)

### 6.1 Circuit per channel

```
VREF_A (filtered 3.3V = ADC reference)
   │
  [4.7 kΩ 0.1 %]──[solder jumper]──[4.12 kΩ 0.1 %]──┐
   ├────────────────────────────────────────────────┘
   │
JST-XH pin 1 ●──┬───────────┬───[4.7 kΩ]───┬──► ADC pin
                │           │              │
            ESD diode    100 nF         100 nF   BAT54S (clamp to VREF_A / AGND)
                │           │              │
               AGND        AGND           AGND
JST-XH pin 2 ●── AGND (star to GND at the MCU)
```

| Setting | Pull-up | Klipper |
|---|---|---|
| Jumper open (default) | 4.7 kΩ → NTC 100K | `pullup_resistor: 4700` |
| Jumper closed | 2,195 Ω → PT1000 | `pullup_resistor: 2195` |

### 6.2 Resolution (12-bit, 1 LSB = 0.81 mV)

| Sensor | Pull-up | 25 °C | 250 °C | 300 °C |
|---|---|---|---|---|
| NTC 100K (B 3950) | 4.7 kΩ | 7.8 LSB/°C | 3.7 LSB/°C | 1.7 LSB/°C |
| PT1000 | 4.7 kΩ | 2.2 LSB/°C | 1.6 LSB/°C | 1.5 LSB/°C |
| PT1000 | 2.2 kΩ | 3.2 LSB/°C | 1.9 LSB/°C | 1.7 LSB/°C |

The PT1000 jumper gives only 15–20 % extra resolution, but costs almost nothing. Use PT1000 only above ≈ 280 °C.

### 6.3 Protection

The severe 24V fault scenarios of the USB-C variant no longer apply. One realistic fault remains: a heater wire touching a thermistor wire at the hotend. Then 24V is on the input. Against that:
- **4.7 kΩ in series and a BAT54S clamp.** These limit the current into the ADC pin to ≈ 4.3 mA.
- **ESD diode at the connector,** with a working voltage ≥ 26 V (e.g. SMF30CA). A 5V ESD diode would conduct at 24V and burn out.
- **Klipper sees the ADC at full scale** and shuts down. The cutoff disconnects the heater rail. There is no permanent damage.

### 6.4 Layout

- AGND and power ground meet at a single point, at the MCU.
- The heater return current (up to 24 A to the MOSFET sources) does not flow through the AGND area.
- The thermistor traces run as a pair and do not cross heater traces.
- VREF_A is filtered with a ferrite or 10 Ω and 1 µF + 100 nF.

---

## 7. Open items for the schematic phase

1. Pinout of the STM32G0B1RBT6 (see §3), including a 9th ADC pin for RAIL_SENSE.
2. WSD4070DN datasheet: R_DS(on) at V_GS = 4.5 V and the SOA for PWM at 10 Hz.
3. Basic status of BAT54S, SMF30CA, screw terminal and JST-XH.
4. 4.12 kΩ 0.1 %: concrete LCSC number.
5. Channel fuse: a 5A/32V 1206 type with larger stock.

---

## Sources

- [LCSC WSD4070DN](https://www.lcsc.com/product-detail/C719095.html)
- [LCSC CD74HCT541M96](https://www.lcsc.com/product-detail/C6560.html)
- [JLCPCB AO3400A](https://jlcpcb.com/partdetail/AO3400A/C20917)
- [TI LM74502/LM74502H datasheet](https://ti.com/lit/gpn/lm74502)
- [LCSC LM74502DDFR](https://www.lcsc.com/product-detail/C3236215.html)
- [LCSC BSC016N06NS](https://www.lcsc.com/product-detail/C454269.html)
- [LCSC STM32G0B1RBT6](https://lcsc.com/product-detail/Microcontrollers-MCU-MPU-SOC_STMicroelectronics-STM32G0B1RBT6_C5143679.html)
- [LCSC 5A 1206 fuse](https://www.lcsc.com/product-detail/C311004.html)
- [LCSC 4.7 kΩ 0.1 %](https://www.lcsc.com/product-detail/C666997.html)
- [Infineon BTT6050-2ERA datasheet (rejected)](https://www.farnell.com/datasheets/2873426.pdf)
