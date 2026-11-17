# Nexus Tools Board — Detailed design part 2: power, CAN and USB

| | |
|---|---|
| **Version** | 0.4 (draft) |
| **Date** | 2026-11-17 |
| **Basis** | Architecture document v1.6, detailed design part 1 v0.3 |
| **Status** | Component selection, before schematic entry |

---

## 1. Scope

This part describes:

1. the 24V input: connector, main fuse, TVS and bulk capacitors,
2. the 5V and 3.3V rails and the current budget,
3. the CAN interface,
4. the USB interface to the host,
5. clock, flashing and debug.

Same sourcing rule as part 1: everything in stock at LCSC/JLCPCB, passives from the Basic library, as few unique Extended parts as possible. Stock checked on 2026-11-10.

---

## 2. Summary

| Block | Component | LCSC | Stock | Price (approx.) | Qty | Type |
|---|---|---|---|---|---|---|
| 24V input | **Amass XT60PW-M** (male, right-angle, PCB) | C98732 | 12,120 | $0.46 | 1 | Extended |
| Main fuse | **Littelfuse 0456025.ER** (25 A, 125 V, SMD) | C315877 | 2,574 | $1.07 | 1 | Extended |
| Input TVS | SMBJ30CA (bidirectional) | Basic | — | $0.04 | 1 | Basic |
| Logic reverse polarity protection | SS36 (60 V, 3 A, SMA) | *pick Basic variant* | plenty | — | 1 | Basic/Ext. |
| 5V buck | **TI TPS54360BDDAR** (4.5–60 V, 3.5 A) | C524806 | 58,193 | $0.63 | 1 | Extended |
| 3.3V LDO | **ME6211C33M5G-N** (500 mA) | C82942 | 334,460 | $0.04 | 2 | *likely Basic* |
| CAN transceiver | **NXP TJA1051T/3/1J** (5 V, VIO 3.3 V) | C38695 | 149,768 | $0.32 | 1 | Extended |
| CAN ESD | PESD2CAN class (SOT-23) | e.g. C907830 | *pick by stock* | ~$0.05 | 1 | Extended |
| CAN connectors | **Molex 43045-0400** Micro-Fit 2×2, right-angle | C122413 | 53,790 | $0.21 | 2 | Extended |
| USB connector | **USB-C 16-pin** (USB 2.0), SMD with THT legs | *pick Basic variant* | plenty | ~$0.10 | 1 | Basic/Ext. |
| USB ESD | **USBLC6-2SC6** | C7519 | 27,880 | $0.08 | 1 | *likely Basic* |
| Crystal | **8 MHz, 20 pF, 5032** (YXC X50328MSB2GI) | C115962 | 273,790 | $0.13 | 1 | *likely Basic* |

"Likely Basic" means: widely used and very large stock, but I could not check the Basic status directly. That happens during schematic entry.

**CAN is populated (AD-12, v0.8): TJA1051, PESD2CAN and crystal by JLC; Micro-Fit connectors and termination jumper hand-soldered.** THT connectors are soldered by hand, see §10.

**Unique Extended parts in this part: about 8, of which about 4 are still placed by JLC once the connectors are hand-soldered (incl. TJA1051 and PESD2CAN).** Together with part 1 the tool board comes to about **15 unique Extended parts**, or about $45 fixed JLC fee per order. For a prototype of 5 boards that is a large share of the cost, but it is a fixed amount per order.

---

## 3. 24V input

```
XT60PW-M ─► 0456025.ER (25 A) ─► SMBJ30CA ─► bulk C ─┬─► cutoff (part 1) ─► heater rail
                                                      │
                                                      └─► SS36 ─► TPS54360B ─► 5V rail
```

| Part | Choice | Explanation |
|---|---|---|
| Connector | XT60PW-M, **male on the board** | The PSU cable gets the female plug. That way there are no exposed live pins on the cable. 30 A continuous. |
| Main fuse | 0456025.ER, 25 A, very fast, 500 A breaking capacity | Average scenario 12–14 A (≈ 55 %). Worst case 23.6 A (≈ 95 %) only lasts seconds. By standard a fuse only opens well above 100 %, so this is acceptable. |
| TVS | SMBJ30CA, bidirectional | Working voltage 30 V, clamp 48.4 V. Stays below the 60 V of the buck and the LM74502. Does not conduct on reverse polarity. |
| Bulk | 2× 100 µF / 50 V electrolytic + 4× 10 µF / 50 V X7R 1206, distributed along the heater rail near the channel fuses and MOSFETs | Absorbs the current steps of the heater PWM (up to 8 × 2.9 A). Electrolytics from the Basic library if available. |

**Deliberate trade-off:** the main fuse is an SMD part and therefore not user-replaceable. That is acceptable, because it is only the last safety net. Normal faults are caught earlier by the channel fuses, the hardware cutoff and Klipper. If the main fuse blows, something is seriously wrong and the board must be inspected anyway.

---

## 4. Logic power

### 4.1 Structure

```
24V ─► SS36 ─► TPS54360B ─► 5V_RAIL ──┬─► LED port (part 3, own limiting)
                                      ├─► filament sensors 5V option (part 3)
                                      ├─► TJA1051 VCC
                                      ├─► ME6211 #2 ─► 3V3_AUX (sensors 3.3V option, status LEDs)
                                      └─► Schottky ─┐
USB VBUS ────────────────────────────► Schottky ─┴─► ME6211 #1 ─► 3V3_MCU (MCU, TJA1051 VIO)
                                                                   └─► filter ─► VREF_A (part 1)
```

### 4.2 Choices

| Choice | Rationale |
|---|---|
| **TPS54360B** (60 V) instead of a cheaper 36V buck | The TVS clamps at 48 V. A 36V buck therefore cannot survive a transient. Stock and price are excellent. |
| 5V rail design current: **1.5 A** | See §4.3. The TPS54360B can do 3.5 A, so there is plenty of margin. Switching frequency ≈ 600 kHz. Inductor ≈ 10 µH / ≥ 2.5 A. Exact values with TI WEBENCH at the schematic stage. |
| **Two ME6211s** instead of one | A SOT-23-5 dissipates (4.7 − 3.3) × I. With MCU and active 3.3V sensors together (≈ 130 mA, 0.18 W), a single LDO gets too hot. Using the same part twice costs no extra Extended fee. It also keeps sensor noise away from the MCU and ADC rail. |
| **USB VBUS diode-OR to 3V3_MCU** | The MCU runs on USB alone. That lets you flash and configure without 24V. VBUS powers nothing else, so no LEDs or sensors. The host port is never overloaded. The 5V rail cannot back-feed into the host. |
| **SS36 before the buck** | Reverse polarity protection of the logic path (part 1, §5: the heater path is protected by the back-to-back cutoff FETs). 60 V reverse voltage, well above the TVS clamp. |

### 4.3 5V rail current budget

| Consumer | Max. current |
|---|---|
| LED port: 8 × WS2812 full white | 0.48 A |
| 8 filament sensors at 5V (active runout + motion, ≈ 25 mA) | 0.20 A |
| TJA1051 (dominant) | 0.07 A |
| ME6211 #1: MCU + crystal + CAN VIO | 0.06 A |
| ME6211 #2: 3.3V sensors (alternative to 5V) + status LEDs | 0.10 A |
| **Total** | **≈ 0.9 A**, design for 1.5 A |

That is ≈ 0.25 A on the 24V side, negligible in the architecture's power budget.

---

## 5. CAN interface

**Population:** transceiver, ESD, crystal and load capacitors by JLC. The 2 Micro-Fit connectors and the termination jumper (THT) hand-soldered. Klipper build: "Clock Reference: 8 MHz crystal".

| Part | Choice | Explanation |
|---|---|---|
| Transceiver | TJA1051T/3: VCC 5 V, VIO 3.3 V | The same transceiver as in most Klipper toolboards. The VIO pin makes a level shifter unnecessary. |
| ESD | PESD2CAN class on CAN-H/CAN-L | Pick the variant with the largest stock. The Littelfuse SM24CANB has only 155 pcs. |
| Connectors | 2× Micro-Fit 43045-0400 (IN and OUT), right-angle | Internally passed through. |
| Pinout | **24V – GND – CAN-H – CAN-L**, the common layout on Klipper toolboards | So existing CAN cables and adapters work. The 24V pin is **not connected** on both connectors (AD-07). |
| Termination | 120 Ω via 2-pin header + jumper | Fit on the board at the end of the bus. |
| MCU pins | FDCAN1 | Pin choice in the schematic phase. Must be compatible with Klipper's G0B1 options for CAN, and for USB-CAN bridge together with USB on PA11/PA12. |
| Bitrate | 1 Mbit/s (Klipper default) | Hence a crystal (§7). The internal HSI16 is not accurate enough over the temperature range for reliable CAN at 1 Mbit/s. |

**Watch out for the 24V pin.** A CAN adapter (e.g. BTT U2C) or a cable from another toolboard may put 24V on that pin. On this board that pin is deliberately not connected, so that is harmless. If you make your own cables: the tool board power **always** comes via the XT60.

---

## 6. USB interface

| Part | Choice | Explanation |
|---|---|---|
| Connector | USB-C 16-pin, USB 2.0 | AD-05 (v0.6): no more tool ports, so USB-C is allowed. CC1/CC2 each with 5.1 kΩ to GND (device identification). |
| ESD | USBLC6-2SC6 on D+/D− and VBUS | Standard solution. |
| Data | PA11/PA12 directly (internal pull-up of the G0B1) | No series resistors needed. USB runs on HSI48 with CRS, so no second crystal. |
| VBUS | Only to the diode-OR for 3V3_MCU (§4.2) | No VBUS detection needed in USB device mode. |
| Shield | Shell via 1 MΩ ∥ 4.7 nF to GND | Limits ESD and prevents a hard ground loop through the shield. |

**Installation note.** USB connects the host's ground to the board's ground. The architecture requirement of a common ground (§10) therefore also applies when using USB. The Pi and the board are best on the same PSU negative.

---

## 7. Clock, flashing, debug, status

| Part | Choice |
|---|---|
| Crystal | 8 MHz, 20 pF (C115962). Load capacitors ≈ 2 × 30 pF, exactly per ST AN2867 at the schematic stage. Klipper: "8 MHz crystal". |
| DFU mode | BOOT button on PA14-BOOT0, with pull-down, plus RESET button on NRST. On the G0B1, PA14 is shared with SWCLK. SWD still works, as long as the button is not pressed. |
| SWD | 4-pin header (3V3, SWDIO, SWCLK, GND), 2.54 mm. Can be left unpopulated to save space and cost. |
| Katapult | After the first flash via DFU or SWD you can update over CAN or USB. |
| Diagnostic LEDs | See §7.1. All Basic LEDs with Basic resistors, 1–2 mA per LED. |

### 7.1 Tool board diagnostic LEDs

Each LED answers a concrete fault question. All LEDs **together along one edge**, visible when the board is installed, each with a silkscreen label.

| LED | Connected to | Shows |
|---|---|---|
| 24V IN | `+24V_IN` (before the cutoff) | Is power coming in? Is the main fuse intact? |
| HEATER RAIL | `+24V_HEATER` (after the cutoff) | Is the cutoff on? (part 1 §5) |
| 5V | `+5V` | Is the buck working? |
| 3V3 | `+3V3_MCU` | Is the LDO working? |
| VBUS | USB VBUS (before the diode-OR) | Is the USB cable properly connected and does the host supply power? |
| MCU | GPIO, via Klipper (`output_pin`) | Is the firmware running? For example on at "ready". |
| HEATER T0–T7 (8×) | From `+24V_HEATER` via a resistor to the **MOSFET drain** | Is that channel **actually** on? See part 1 §4.3. |

LEDs on 24V nets: resistor ≈ 10–12 kΩ (≈ 2 mA, ≈ 50 mW, 0603 is sufficient; 0805 if margin is desired). On 5V/3.3V: resistor for 1–2 mA, depending on colour.

---

## 8. Changes from architecture v0.4

| Item | Was | New | Reason |
|---|---|---|---|
| Main fuse | 25 A, type open | 0456025.ER SMD, not user-replaceable | Stock. It is only the last safety net. |
| 3.3V rail | 1× LDO | 2× ME6211 (MCU and AUX separate) | Dissipation and noise separation |
| USB power | Not used | VBUS powers only the MCU rail (diode-OR) | Flashing and configuring without 24V |
| CAN pinout | Not defined | 24V–GND–CAN-H–CAN-L, 24V pin not connected | Compatible with existing cables |

---

## 9. Assembly strategy (cost control)

JLC charges ≈ $3 per order for each unique Extended part they place, plus a fixed setup fee. Parts JLC does not place incur no fee.

| Group | Parts | Placed by |
|---|---|---|
| Fine-pitch SMD and ICs with exposed pad | STM32G0B1RBT6, WSD4070DN, CD74HCT541, SN74AHCT1G125, LM74502, BSC016N06NS, TPS54360B, 0.1 % resistors, inductor, USB-C host port | JLC |
| Basic parts | Passives, diagnostic LEDs, Basic diodes (incl. signal ESD if Basic), ME6211, USBLC6 (if Basic) | JLC (free) |
| THT connectors | XT60, screw terminals, JST-XH (thermistor, filament, LED), (Micro-Fit) | **Hand-soldered** |
| Large SMD fuses | 0456025.ER (25 A), 8× 5A 1206 | Self (easy) or JLC, depending on the price in the quote |
| CAN | TJA1051, PESD2CAN, crystal | JLC |
| CAN connectors | 2× Micro-Fit, termination jumper | Hand-soldered |

Extra saving: tool board and dock board together in one order (or one panel). Shared parts then pay their fee only once.

## 10. Open items for the schematic phase

1. Values around the TPS54360B (RT, compensation, inductor, capacitors) via TI WEBENCH. Pick inductor and electrolytics from Basic where possible.
2. G0B1 pinout: FDCAN1, USB, SWD, BOOT0, crystal, 9 ADC pins (8 thermistors + RAIL_SENSE), 8 PWM outputs to the heaters, cutoff EN, 16 filament inputs (runout + motion), LED data and status LED.
3. Check Basic status: ME6211, USBLC6-2SC6, crystal, SS36, SMBJ30CA, electrolytics.
4. Pick PESD2CAN variant based on stock.
5. Order on the connector edge and mechanical arrangement: part 4 (layout).

---

## Sources

- [LCSC XT60PW-M](https://www.lcsc.com/product-detail/C98732.html)
- [LCSC Littelfuse 0456025.ER](https://www.lcsc.com/product-detail/C315877.html)
- [LCSC TPS54360BDDAR](https://www.lcsc.com/product-image/C524806.html)
- [LCSC TPS54560DDAR (alternative)](https://www.lcsc.com/product-detail/C31966.html)
- [LCSC TJA1051T/3/1J](https://www.lcsc.com/product-detail/C38695.html)
- [LCSC Molex 43045-0400](https://www.lcsc.com/product-detail/C122413.html)
- [LCSC USBLC6-2SC6](https://www.lcsc.com/product-detail/C7519.html)
- [LCSC ME6211C33M5G-N](https://www.lcsc.com/product-detail/C82942.html)
- [LCSC 8 MHz crystal X50328MSB2GI](https://lcsc.com/product-detail/Crystals_YXC-X50328MSB2GI_C115962.html)
- [LCSC SM24CANB-02HTG](https://www.lcsc.com/product-detail/C151237.html)
- [LCSC PESD2CAN (Tech Public)](https://www.lcsc.com/product-detail/C907830.html)
- [JLCPCB SS36](https://jlcpcb.com/partdetail/SS36/C391251)
