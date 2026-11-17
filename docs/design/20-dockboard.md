# Nexus Docks Board — Detailed design

| | |
|---|---|
| **Version** | 0.4 (draft) |
| **Date** | 2026-11-17 |
| **Basis** | Architecture v1.6, tool board detailed design parts 1–3 |
| **Status** | Component selection, before schematic entry |

---

## 1. Function (from architecture §5.2)

- 9 independently PWM-controlled fan outputs, no tacho.
- Fan voltage selectable per board: **24V, 12V or 5V**.
- 1 LED port for up to 8 WS2812.
- USB and CAN to the host (CAN populated, AD-12).
- Own 24V input.

## 2. Design principle: reuse

The dock board uses **as many of the same parts as the tool board as possible.** If both boards are ordered together (one panel, §8), you pay the Extended fee for shared parts only once. The only new Extended part is the XT30, and you solder that yourself.

**Change from architecture (AD-08):** MCU **STM32G0B1RBT6** instead of RP2040.

| | RP2040 | STM32G0B1RBT6 (same as tool board) |
|---|---|---|
| Extra parts | External QSPI flash + 12MHz crystal (2 extra unique parts) | None |
| Extended fee when ordered together | MCU + flash + crystal = 3 new | 0 new |
| Firmware | Second Klipper build and flash procedure | Same build, same procedure |
| MCU price | ≈ $0.70 + flash | ≈ $2.10 |
| Pins | More than enough | More than enough (≈ 16 of 60 needed) |

The G0B1 is $1.40 more per board, but you save 3 × $3 fee per order and keep a single firmware flow.

---

## 3. Component summary

| Block | Component | LCSC | Shared with tool board | Qty |
|---|---|---|---|---|
| MCU | STM32G0B1RBT6 | C5143679 | ✔ | 1 |
| 24V input | **Amass XT30PW-M** (male, right-angle), 26,030 pcs, $0.38 | C431092 | ✘ (hand-soldered) | 1 |
| Input fuse | 1206, 5 A / 32 V | same as tool board | ✔ | 1 |
| TVS | SMBJ30CA | Basic | ✔ | 1 |
| Reverse polarity protection | LM74502 + 1× BSC016N06NS (ideal diode, EN tied high) | C3236215 / C454269 | ✔ | 1 + 1 |
| 5V logic | TPS54360B + 10µH inductor + SS56C catch diode *(F2)* | C524806 | ✔ | 1 |
| Fan rail buck 12V/5V | TPS54360B + 10µH inductor + SS56C catch diode (the same) | C524806 | ✔ | 1 |
| 3.3V | ME6211C33 | C82942 | ✔ | 1 |
| Fan MOSFET | WSD4070DN | C719095 | ✔ | 9 |
| Gate buffer | CD74HCT541M96 (fans 1–8) | C6560 | ✔ | 1 |
| Gate buffer fan 9 + LED shifter | SN74AHCT1G125DBVR | C7484 | ✔ | 2 |
| Flyback per fan | B5819W (40 V 1 A, Basic) *(F1)* | C8598 | ✘ | 9 |
| LED polyfuse | JK-NSMD075 | C692900 | ✔ | 1 |
| USB | USB-C 16-pin + USBLC6-2SC6 | — / C7519 | ✔ | 1 + 1 |
| Fan connectors | JST-XH 2-pin | hand-soldered | ✔ (family) | 9 |
| LED connector | JST-XH 3-pin | hand-soldered | ✔ | 1 |
| CAN | TJA1051T/3, PESD2CAN, crystal (JLC); 1× Micro-Fit 2×2 + termination jumper (self) | C38695 / … | ✔ | 1 |
| Diagnostic LEDs | 0603 LED + resistor (AD-17): 24V IN, FAN RAIL, 5V, 3V3, VBUS, MCU. No LED per fan. | Basic | ✔ | 6 |

---

## 4. Power

```
XT30 ─► fuse 5 A ─► SMBJ30CA ─► LM74502 + Q1 (reverse polarity protection) ─► 24V_INT
                                                                             │
              ┌────────────────────────────────┬─────────────────────────────┤
              ▼                                ▼                             ▼
     TPS54360B #1 → 5V (logic, LED)    TPS54360B #2 → 12V/5V          (24V direct)
              │                                │                             │
           ME6211 → 3V3                        └────── solder jumper ────────┘
                                                            ▼
                                                        FAN_RAIL
```

| Choice | Rationale |
|---|---|
| **LM74502 + 1 FET as ideal diode** | A Schottky loses ≈ 1.5 W at 3 A. LM74502 and BSC016N06NS are already in the tool board BOM. EN tied high: no cutoff needed for fans. |
| **Single-FET orientation** *(F2)* | The FET's **source faces the input** (VS and SRC on the XT30 side, drain to 24V_INT). On power-up the body diode conducts until the charge pump turns the FET on; on reverse polarity the body diode blocks and the controller holds GATE at SRC. Back-to-back FETs are only needed for load disconnect, which the dock does not use. OV pin to GND. |
| **Second TPS54360B for the fan rail** | The same part. Output 12V or 5V via a solder jumper that selects one of two FB resistors. Design current 3 A (the IC can do 3.5 A). |
| **Same 10µH inductor for both bucks** | Ripple current at 600 kHz: ≈ 1.0 A (24→12V) and ≈ 0.7 A (24→5V). MWSA0603S-100MT: Isat 5.5 A. Values: [calculations.md](../calculations.md) §1. |
| **Fan rail solder jumper: 24V direct or buck** | One choice for all fans (FR-D02). Not soldered by default, so the board cannot simply put 24V on 5V fans. **Choose deliberately at build time.** Without a jumper there is no fan voltage, so the fans do not run. State this prominently on the silkscreen. |
| **Buck #2 EN tied to the jumper** | With 24V direct, buck #2 is off (no unnecessary losses). |
| **5 A input fuse** | Worst case 3 A fans (at 24V) + ≈ 0.3 A logic + LED. XT30 can handle 15 A. |

---

## 5. Fan outputs (9×)

```
FAN_RAIL ──────┬────────────► JST-XH pin 2 (V+)
             B5819W (cathode to FAN_RAIL)
               │
               ├────────────► JST-XH pin 1 (fan−)
             drain WSD4070DN
MCU ─► 74HCT541 / 74AHCT1G125 (5 V) ─[22 Ω]─► gate     source ─► GND
          input 100 kΩ pull-down      gate 100 kΩ pull-down
```

| Choice | Rationale |
|---|---|
| **Same MOSFET and buffer as the heaters** | Shared parts. At 1 A the dissipation is negligible. |
| **Fan 9 via 74AHCT1G125** | The 74HCT541 has only 8 channels. The 1G125 is already in the BOM as LED shifter. |
| **Flyback diode per fan** | Fans are inductive. Without a diode, PWM produces voltage spikes on the MOSFET. |
| **2-wire connection** | No tacho (FR-D03). 3-wire fans work with the yellow wire left unconnected. |
| **Max. 1 A per channel, 3 A total** | According to the architecture. Limited by the buck (3.5 A) or the input fuse (5 A). |
| **JST-XH 2-pin pinout: 1 = fan−, 2 = V+** | Signal on pin 1, same convention as the tool board. |

**Confirmed (2026-11-11):** fans with JST-XH plugs.

### 5.1 Klipper

```ini
[fan_generic dock_fan_t0]
pin: dock:PXX
cycle_time: 0.010        # 100 Hz, standard for fans
kick_start_time: 0.5
off_below: 0.15
```

How the fans are linked to parked tools goes into the tool change macros.

---

## 6. LED port

Identical to the tool board (part 3, §3): 74AHCT1G125, 330 Ω, 0.75 A polyfuse, 10 µF, ESD diodes on DIN and 5V (AD-14), JST-XH 3-pin (1 = DIN, 2 = GND, 3 = 5V).

Test points on all rails (+24V_INT, FAN_RAIL, +5V, +3V3, GND) per AD-14.

---

## 7. USB, CAN, clock, flashing

Identical to the tool board (part 2):
- USB-C with USBLC6. VBUS powers only the MCU via diode-OR.
- **CAN populated** (AD-12): transceiver, ESD and crystal by JLC. One Micro-Fit (CAN-IN; the dock board is the end of the bus) and termination jumper hand-soldered.
- 8 MHz crystal (needed for CAN at 1 Mbit/s). USB on HSI48.
- BOOT and RESET buttons, SWD header.
- **Diagnostic LEDs** (together along one edge, with silkscreen label):

| LED | Connected to | Shows |
|---|---|---|
| 24V IN | `+24V_INT` (after the reverse polarity protection) | Is power coming in? |
| FAN RAIL | `FAN_RAIL` | Is the fan voltage selected (solder jumper) and present? Resistor sized for 5 V, so the LED is visible at any rail voltage. At 24 V ≤ 10 mA, and check the resistor is ≥ 0.25 W. |
| 5V | `+5V` | Is the logic buck working? |
| 3V3 | `+3V3` | Is the LDO working? |
| VBUS | USB VBUS | Is the USB cable properly connected? |
| MCU | GPIO | Is the firmware running? |

---

## 8. Ordering together with the tool board

| Option | Effect |
|---|---|
| **Separate orders** | Each board pays its own setup, stencil, Extended fee and shipping. |
| **One panel, both designs** | Shared Extended parts are paid only once. One setup, one stencil, one shipment. JLC does charge a fee for "different designs" in a panel. Check that amount and how it applies to PCBA at quote time or with support. |

### 8.1 Dock board cost estimate (indicative, ±25 %)

| Item | Separate (5 pcs) | Extra in panel with tool board (5 sets) |
|---|---|---|
| PCB (2 layers is enough, ≈ 70 × 50 mm) | $5 | ≈ $10 (larger panel, 4 layers) + "different design" fee |
| Setup + stencil | $9.71 | $0 |
| Extended fee | ≈ 10 × $3.07 = $30.70 | $0 (all shared) |
| JLC parts (≈ $10.90/board, incl. CAN) | $54.50 | $54.50 |
| Hand-soldered parts (≈ $0.70/board) | $3.50 | $3.50 |
| Placement + MOQ | $5 | $3 |
| Shipping | $22 | ≈ $0–5 |
| **Subtotal** | **≈ $128** | **≈ $70–75 + fee** |
| VAT 21 % | $27 | ≈ $15 |
| **Total** | **≈ $155 (≈ $31/board)** | **≈ $85–90 extra** |

**Both boards together in one panel:** ≈ $215 + $90 ≈ **$305 for 5 sets**, or **≈ $61 per set** (tool + dock). Ordered separately the same costs ≈ $370, or ≈ $74 per set.

---

## 9. Open items for the schematic phase

1. LM74502 in a single-FET configuration (reverse polarity protection only): check the application circuit in the datasheet.
2. TPS54360B #2: FB divider for 12V and 5V, and stability at both outputs (WEBENCH). Inductor ≥ 4.5 A saturation.
3. JLC fee for "different designs" with PCBA (support or quote).
4. G0B1 pinout (9 PWM, LED, USB, SWD, FDCAN, crystal, status).
5. FAN RAIL LED resistor: sized for 5 V, check power rating at 24 V (≥ 0.25 W).

---

## Sources

- [LCSC XT30PW-M](https://www.lcsc.com/product-image/C431092.html)
- [JLCPCB: different designs in one PCB file](https://jlcpcb.com/help/article/different-design-in-your-pcb-files)
- [JLCPCB: multiple designs on one SMT stencil](https://jlcpcb.com/help/article/combine-multiple-pcb-designs-onto-one-smt-stencil)
- Other parts: see tool board detailed design parts 1–3.
