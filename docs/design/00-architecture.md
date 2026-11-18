# Nexus Tools Board & Nexus Docks Board — Functional & Technical Architecture

| | |
|---|---|
| **Version** | 1.7 (draft) |
| **Date** | 2026-11-17 |
| **Author** | Berten |
| **Status** | Concept fixed, ready for review before detailed design (schematic/PCB) |

---

## 1. Goal and scope

A set of **two** Klipper-compatible controller boards for a hotend changer with up to 8 tools:

- **Nexus Tools Board** (*tool board*) — drives 8 hotend heaters, reads 8 thermistors and 8 filament sensors, 1 LED chain.
- **Nexus Docks Board** (*dock board*) — drives 9 fans and 1 LED chain.

The rest of the documentation abbreviates the boards as *tool board* and *dock board*. The PCB (silkscreen) and product texts always use the full name (AD-14).

Both boards are standalone Klipper MCUs that communicate directly with the Klipper host.

**In scope:** electrical architecture, interfaces, connectors, power, safety, Klipper integration at MCU level.

**Out of scope:** see §12.

### 1.1 Definition of "tool"

A *tool* = **hotend (heater) + thermistor**. Extruder motor, part cooling and other functions are not part of a tool in the sense of this document.

---

## 2. Terminology

| Term | Meaning |
|---|---|
| Host | Computer running Klipper (klippy), e.g. Raspberry Pi |
| MCU | Microcontroller running Klipper firmware |
| Tool connection | Per tool: 2-pole screw terminal (heater) + JST-XH 2-pin (thermistor) on the tool board. The per-tool connector sits in the printer panel next to the PC4 coupler (out of scope). |
| Heater rail | 24V supply line that feeds only the heater channels |
| Cutoff | Hardware switch that can disconnect the entire heater rail |
| Fan rail | Supply line for all fans, voltage selectable |

---

## 3. System overview

```
                ┌──────────────────────────┐
  PSU 24V ─XT60─►        TOOL BOARD        │
                │   MCU: STM32G0B1         │
  Host ◄─USB-C──┤   8× heater (screw term.)├──► 8× hotend via panel connector
                │   8× thermistor (JST-XH) │
       ◄─CAN────┤   8× filament (2 inputs) ├──◄ 8× filament sensor (runout/motion)
       (CAN-IN) │   1× LED port            ├──► LED chain (≤ 8× WS2812)
                │   heater cutoff          │
                └────────────┬─────────────┘
                             │ CAN-OUT: CAN-H/L + GND (no power)
                             ▼
                ┌──────────────────────────┐
  PSU 24V ─XT30─►        DOCK BOARD        │
  Host ◄─USB-C──┤                          │
                │   MCU: STM32G0B1         ├──► 9× fan
                │   fan rail 5/12/24V      ├──► LED chain (≤ 8× WS2812)
                └──────────────────────────┘
```

### 3.1 Supported topologies

| # | Topology | Host connections | Note |
|---|---|---|---|
| A | **USB** | USB → tool board, USB → dock board | No tool→dock cable needed |
| B | **CAN** | CAN adapter → tool board (CAN-IN) → dock board | Bus via daisy chain |
| C | **USB-CAN bridge** | USB → tool board; tool board acts as USB-to-CAN bridge → dock board | One host cable, no separate CAN adapter needed |

Maximum cable length host ↔ boards: **1.5 m**.

---

## 4. Architecture decisions

| ID | Decision | Rationale |
|---|---|---|
| AD-01 | **No central main board.** Each board is its own Klipper MCU. | Klipper supports multi-MCU natively. A custom translation protocol between boards would bypass Klipper's timing, verification and shutdown mechanisms. |
| AD-02 | **Heater via 2-pole screw terminal (5.08 mm), thermistor via JST-XH 2-pin.** Per tool one keyed connector in a panel next to the PC4 coupler; fixed wiring from panel to board. *(Changed in v0.6: was USB-C tool port.)* | The board cannot be mounted such that the umbilicals plug in directly. The panel → board wiring does not move, so screw terminals (with ferrules) are sufficient. The risk of swapping heater/thermistor during wiring is covered by the commissioning macro (§9.5). |
| AD-03 | **Low-side N-MOSFET per heater channel, gate driven at 5 V via an octal buffer.** *(Changed in v0.6: was high-side smart switch.)* | Without USB-C, the reason for high-side switching is gone. Low-side is the common, cheap solution. Consequence: a short from heater− to ground bypasses the MOSFET; the cutoff catches that (AD-10). |
| AD-04 | **Thermistor return to analog ground (AGND)**, separate from the heater return. | Thermistor measurement shares no return current with the heater. |
| AD-05 | **Host data connector = USB-C** on both boards. *(Changed in v0.6: was USB-B.)* | USB-B was only needed to avoid confusion with the USB-C tool ports. Those no longer exist. |
| AD-06 | **Tool board always powered via XT60.** | Up to ~24 A does not fit through a Micro-Fit CAN connector (≈5–8 A per pin). |
| AD-07 | **Dock board has its own 24V input (XT30) directly from the PSU.** The tool → dock CAN link carries only CAN-H/L + GND. *(Changed in v0.2: was pass-through via tool board.)* | With the worst case of the heater rail (~24 A), an additional 5 A pass-through would load the XT60 (30 A) without margin. |
| AD-08 | **MCU on both boards: STM32G0B1RBT6.** *(Changed in v0.7: dock board was RP2040.)* | G0B1: enough ADC channels, native FDCAN + USB, proven in Klipper. On the dock board: no external flash and crystal needed, shared Extended parts when ordered together, one firmware flow. |
| AD-09 | **Inactive tools = commented out of the config + restart.** | No hardware presence detection. Klipper's default behaviour (shutdown on a missing thermistor of a configured heater) is preserved. |
| AD-10 | **Two layers of thermal safety on the board** (Klipper + hardware cutoff with self-test), plus an **optional** passive third layer at the hotend (see §8). The hardware cutoff is **mandatory**. *(Changed in v1.3: layer 3 was "thermal fuse on the hotend, mandatory"; not feasible because TCOs go up to ±240 °C, at or below print temperature.)* | A shorted MOSFET or a short from heater− to ground cannot be stopped by software or by the MOSFET. Only the cutoff on the positive side then removes the voltage. |
| AD-11 | **Board hardware (channels, heater rail, cutoff, input) sized for 8 heaters on at once from cold (100 %). The usage scenario (§7.2) is used only for PSU sizing.** | The scenario "max. 3 heaters cold at once" is a usage convention that Klipper does not enforce. A macro or slicer error can start all 8 at once; the board must not fail then. Copper and switches for 24 A cost little at board level. Rejected alternative: a fuse or electronic breaker (~15 A) as a limit. That does not limit but disconnects, reacts slowly or unpredictably at 1.5× overload, and gives false trips when PWM pulses of warm heaters coincide in normal use. |
| AD-12 | **CAN hardware populated on both boards** (transceiver, ESD, crystal by JLC; Micro-Fit connectors and termination jumper hand-soldered). Both USB and CAN available. *(Changed in v0.8: was DNP.)* | Extra cost ≈ $3 per board (tool), ≈ $0.70 per board (dock, when ordered together). All three topologies (§3.1) usable out of the box. |
| AD-13 | **Voltage measurement on the heater rail** (divider to an ADC pin) and a **startup self-test** that demonstrably switches the cutoff. | A safety function that is never tested does not exist in practice. Costs 2 resistors and 1 ADC pin. At the same time a demonstrable measure for an open-source publication. |
| AD-14 | **ESD protection on all external signal connectors** (thermistor, filament, LED). Test points on all rails. Board name (**Nexus Tools Board** / **Nexus Docks Board**), revision, date and license on the silkscreen. | Other builders wire differently. Test points are needed during commissioning. The revision prevents confusion between rev A and rev B. |
| AD-15 | **Open source:** hardware CERN-OHL-S-2.0, macros and config GPL-3.0-or-later, documentation CC-BY-SA-4.0. **Not for sale** and no commission (not even a paid PCBWay share). | Keeps derivatives open. Without commercial activity, the designer's liability risk stays as small as possible (see README, safety). |
| AD-16 | **All heater power through one tool board**, with a short power trunk (XT60 → fuse → cutoff → split) as a copper polygon on 2 layers (≥ 7 mm per layer at 1 oz). No separate power modules per tool, no passive panel PCB. | Only the trunk (≈ 40 mm) carries the full 23.6 A; after that ≤ 2.9 A per channel. Modules do not solve this as long as the cutoff is central; a cutoff per module costs 8× extra safety electronics and self-tests. |
| AD-17 | **Diagnostic LEDs** on both boards: 24V IN, rail after the cutoff or the fan rail, 5V, 3V3, VBUS, MCU, plus **one LED per heater channel on the MOSFET drain** (tool). No LED per fan on the dock board (2026-11-17: not needed). BOOT and RESET buttons on both boards. | Each LED answers a fault question without a measuring instrument. The drain LED shows the actual state of the channel, so also a failed-short MOSFET. Basic parts only. |

---

## 5. Functional requirements

### 5.1 Tool board

| ID | Requirement |
|---|---|
| FR-T01 | 8 independently PWM-controlled heater channels, 24V, suitable for heaters up to **70 W @ 24V at room temperature** (cold current ≤ 2.9 A), PTC or classic cartridge. Target: Bambu Lab X1-type heater cores (original 40–48 W, aftermarket up to 70 W). Heater not chosen yet. |
| FR-T02 | Usage scenario: max. **3 heaters heating up from room temperature at once**, the other 5 held at temperature. In addition, the hardware must survive 8 heaters cold at 100 % at once (AD-11). |
| FR-T03 | 8 thermistor inputs, selectable per channel **NTC 100K** or **PT1000**. |
| FR-T04 | 8 filament sensor connections, each with 2 inputs (runout + motion): suitable for a passive switch (D2F) or a combined runout and motion sensor for clog detection (3.3V or 5V). |
| FR-T05 | 1 LED port for a chain of max. 8 WS2812 LEDs. |
| FR-T06 | Hardware cutoff of the entire heater rail, controlled by Klipper. |
| FR-T07 | Communication with the host via USB **or** CAN; USB-to-CAN bridge must be possible. |
| FR-T08 | Pass the CAN bus through to the dock board (no power). |
| FR-T09 | Firmware flashable via USB (DFU) and SWD; updates via CAN possible (Katapult). |

### 5.2 Dock board

| ID | Requirement |
|---|---|
| FR-D01 | 9 independently PWM-controlled fan outputs. |
| FR-D02 | Fan voltage **5V, 12V or 24V**, selectable per board (one choice for all fans). |
| FR-D03 | No tacho readout. 2- and 3-wire fans must work (tacho wire unused). |
| FR-D04 | 1 LED port for a chain of max. 8 WS2812 LEDs. |
| FR-D05 | Communication with the host via USB **or** CAN. |
| FR-D06 | Own 24V power input, directly from the PSU. |
| FR-D07 | Firmware flashable via USB (DFU) and SWD; updates via CAN possible (Katapult). |

---

## 6. Technical specification

### 6.1 Tool board

#### 6.1.1 Power

| Item | Specification |
|---|---|
| Input | XT60, 24V DC |
| Main fuse | 25 A |
| Protection | Reverse polarity protection, TVS, bulk capacitors |
| Internal rails | 5V buck (LED + logic), 2× 3.3V LDO (3V3_MCU: MCU, analog; 3V3_AUX: sensors) |
| ADC reference | Filtered 3.3V analog rail, separated from digital noise |

#### 6.1.2 Heater channels

| Item | Specification |
|---|---|
| Count | 8 |
| Switching | Low-side N-MOSFET, per channel (5 V gate via buffer) |
| Heater type | Design envelope: max. 70 W @ 24V at room temperature, PTC or classic |
| Cold resistance | ≈ 8.2 Ω (24² / 70) |
| Cold current | ≈ 2.9 A, decreases as the heater warms up (PTC) |
| Channel rating | ≥ 4 A continuous (MOSFET 40 V, a few mΩ) |
| Fuse per channel | 5 A in the +24V line to the screw terminal (detailed design part 1) |
| PWM | Klipper standard heater PWM (slow, ~10 Hz), so little EMI |
| Supply | Via heater rail, behind the cutoff |

#### 6.1.3 Tool connections

| Function | Connector | Pins |
|---|---|---|
| Heater (8×) | 2-pole screw terminal, 5.08 mm | +24V (fused, behind cutoff) / heater− (MOSFET drain) |
| Thermistor (8×) | JST-XH 2-pin | Signal → ADC / AGND |

**Thermistor input**

| Item | Specification |
|---|---|
| Pull-up | Solder jumper per channel: NTC 100K setting (4.7 kΩ) or PT1000 setting (4.7 kΩ ∥ 4.12 kΩ = 2195 Ω). Record the value for `pullup_resistor` in the config. See detailed design part 1 §6. |
| Tolerances | Precision resistors (≤ 0.1 %) |
| Filter | RC low-pass per channel + ESD protection |

#### 6.1.4 Filament inputs

| Item | Specification |
|---|---|
| Count | 8 connectors, 16 inputs |
| Connector | JST-XH 4-pin: 1 RUNOUT / 2 GND / 3 VCC / 4 MOTION |
| VCC | Solder jumper per board: 5V (default) or 3.3V (max. 100 mA total) |
| Input | External 10 kΩ pull-up to 3.3V, 1 kΩ series + 100 nF (RC filter), ESD; on 5V-tolerant FT pins (no clamp needed, 5V sensor outputs safe) |
| Compatible | D2F and other passive switches; Hall, optical and combined runout/motion sensors (clog detection) at 3.3V or 5V |

#### 6.1.5 LED port

| Item | Specification |
|---|---|
| Connector | JST-XH 3-pin: 1 DIN / 2 GND / 3 5V |
| Load | Max. 8 WS2812 (≤ 0.5 A), port limited to 1 A |
| Data level | Level shifter 3.3V → 5V. WS2812 requires ≥ 0.7×VDD, so 3.3V is marginal. |
| Protection | 0.75 A polyfuse on 5V, ESD on DIN and 5V |

#### 6.1.6 Heater cutoff

| Item | Specification |
|---|---|
| Position | High-side, in series with the entire heater rail (not the logic) |
| Rating | ≥ 25 A (8 × cold current, AD-11) |
| Control | MCU pin via gate driver; pull-down so that the default state is **off** |
| Klipper | `output_pin` with `value: 1` and `shutdown_value: 0` |

#### 6.1.7 Host and bus connectors

| Connector | Type | Pins |
|---|---|---|
| Host USB | USB-C (USB 2.0 only) | Data; VBUS powers only the MCU rail (detailed design part 2) |
| CAN-IN | Micro-Fit 3.0 2×2 | CAN-H, CAN-L, GND, 24V (24V not connected as input) |
| CAN-OUT | Micro-Fit 3.0 2×2 | CAN-H, CAN-L, GND, 24V pin not connected (no pass-through, AD-07) |
| Termination | Jumper | 120 Ω between CAN-H/CAN-L |

#### 6.1.8 STM32G0B1 pin budget

| Function | Pins |
|---|---|
| Heater PWM | 8 |
| Thermistor ADC | 8 |
| Filament inputs (runout + motion) | 16 |
| LED data | 1 |
| Cutoff | 1 |
| Rail voltage measurement (ADC) | 1 |
| FDCAN | 2 |
| USB | 2 |
| SWD | 2 |
| Crystal | 2 |
| Status LED (MCU) | 1 |
| **Total** | **44** of ≈ 60 GPIO on LQFP-64 (detailed design part 3 §4) |

### 6.2 Dock board

#### 6.2.1 Power

| Item | Specification |
|---|---|
| Input | XT30, 24V DC, directly from the PSU |
| Input fuse | 5 A |
| Protection | Reverse polarity protection, TVS |
| Internal rails | 5V buck (LED + logic), 3.3V LDO (MCU) |
| Fan rail | Selectable via solder jumper: **24V** direct, or one buck with selectable output **12V / 5V**, 3 A |

#### 6.2.2 Fan outputs

| Item | Specification |
|---|---|
| Count | 9 |
| Switching | Low-side MOSFET + flyback diode |
| Current per channel | Max. 1 A |
| Fan rail total | Max. 3 A |
| Connector | JST-XH 2-pin |
| Tacho | None |

#### 6.2.3 LED port

Identical to §6.1.5.

#### 6.2.4 Host and bus connectors

| Connector | Type | Note |
|---|---|---|
| Host USB | USB-C | Data only |
| CAN | Micro-Fit 3.0 2×2 | CAN-H, CAN-L, GND; 24V pin not connected |
| Termination | Jumper | 120 Ω (the dock board is normally the end of the bus) |
| Flashing | BOOT and RESET buttons + SWD header | |

#### 6.2.5 STM32G0B1 pin budget

9 fan PWM + 1 LED + USB (2) + SWD (2) + FDCAN (2) + crystal (2) + status. ≈ 16 of ≈ 60 GPIO.

Details: 20-dockboard.md.

---

## 7. Power budget

### 7.1 Heater cores: PTC behaviour

- Design envelope 70 W **at room temperature**: R_cold ≈ 8.2 Ω, I_cold ≈ 2.9 A. An original X1 heater (≈ 12 Ω, ≈ 48 W) falls well within that.
- The hardware sizing (8 × I_cold) applies regardless of heater type or R(T) curve. A classic cartridge always draws ≈ I_cold during an on-pulse; a PTC less. Only the PSU sizing (§7.5) depends on the chosen heater.
- Indicative (one forum measurement, different brand): a PTC delivers ≈ 60 % of its cold power at 200 °C.
- As it heats up the resistance rises, so the **available** power and the current during a PWM on-pulse drop.
- The **required** power to stay at temperature is determined by heat loss (sock, airflow, environment), not by the PTC. Fans blowing on parked hotends increase that.
- The R(T) curve of the heater core is unknown. See risk in §11.

### 7.2 Tool board: usage scenario (basis for PSU)

| State | Power | Current @ 24V |
|---|---|---|
| 3 heaters heating up from room temperature (start, 100 %) | 3 × 70 = 210 W | 8.8 A |
| 5 heaters at temperature, average (assumed 15–25 W each) | 75–125 W | 3.1–5.2 A |
| LED + logic | ≈ 5 W | 0.2 A |
| **Average total** | **≈ 290–340 W** | **≈ 12–14 A** |
| **Short peak** (5 warm heaters coincidentally in PWM on-phase together) | ≤ 565 W | ≤ 23.6 A |

The peak occurs because Klipper drives each heater with slow PWM (~10 Hz) without phase coordination: on-pulses can coincide. As long as I_warm has not been measured, I_warm ≤ I_cold applies as the upper bound.

### 7.3 Tool board: hardware worst case (AD-11)

| Consumer | Current @ 24V |
|---|---|
| Heaters 8 × I_cold | 23.4 A |
| LED + logic | 0.2 A |
| **Total** | **≈ 23.6 A**, hence XT60 (30 A), 25 A main fuse, cutoff and heater rail ≥ 25 A |

### 7.4 Dock board

| Consumer | Current @ 24V |
|---|---|
| Fan rail | max. 3 A |
| LEDs | ≈ 0.1 A |
| Logic | < 0.1 A |
| **Total** | **≈ 3.2 A**, own XT30 input with 5 A fuse |

### 7.5 PSU sizing

| | Tool board | Dock board | Total |
|---|---|---|---|
| Average (scenario) | ≈ 340 W | ≈ 77 W | ≈ 420 W |
| Short peak | ≈ 565 W | ≈ 77 W | ≈ 640 W |

Recommendation: **24V / ≥ 600 W** for both boards together, excluding the rest of the printer. The peak of ≈ 640 W lasts hundreds of milliseconds; check that the chosen PSU allows this briefly. Recalculate once R_warm has been measured; the peak will almost certainly turn out lower.

---

## 8. Safety concept

Two independent layers on the board, plus an optional passive layer:

| Layer | Mechanism | Covers |
|---|---|---|
| 1. Software | Klipper `verify_heater` per heater, `min_temp`/`max_temp`, MCU ↔ host communication timeout | Thermal runaway, detached thermistor, hung host |
| 2. Hardware cutoff | Heater rail disconnected on every Klipper shutdown, MCU reset or watchdog (default state = off) | Shorted heater MOSFET, firmware fault |
| 3. *Optional:* passive protection at the hotend | A **PTC heater** (self-limiting), and/or a **TCO on the heatsink or tool holder** (e.g. 130–150 °C) | Partially: failure of both layer 1 and 2. Reacts late; prevents fire, not necessarily damage to the hotend. |

A TCO **on the heater block** is not feasible: common TCOs go up to ±240 °C, which is at or below print temperature (PETG, ABS/ASA).

Additionally:
- Fuse per heater channel (short in cable or heater).
- Short from heater− to ground (e.g. damaged wire against the frame): heater turns on bypassing the MOSFET → Klipper detects overheating → shutdown → cutoff (layer 2).
- Reverse polarity protection and TVS on every power input.
- Startup self-test (AD-13): Klipper turns the cutoff off and on again and checks via the voltage measurement that the heater rail actually drops and comes back. If the test fails, no print.

---

## 9. Klipper integration

Implemented in [`klipper/`](../../klipper/README.md) (F8). This section records the decisions; the README is the user documentation.

### 9.1 MCU definition

```ini
[mcu nexus_tools]
canbus_uuid: ...        # or serial: /dev/serial/by-id/...

[mcu nexus_docks]
canbus_uuid: ...        # or serial: /dev/serial/by-id/...
```

*(Changed in v1.7: was `toolboard` / `dock`. A YUDX toolhead often already has a CAN toolhead board called `toolboard`.)*

### 9.2 Enabling and disabling tools

One block per tool in `klipper/nexus.cfg`: an include with the fixed pins (`nexus/tools/tN.cfg`) plus the user settings (dock position, offsets, thermistor, PID, filament sensors).

Deactivating a tool = comment out its block + `FIRMWARE_RESTART` (AD-09). **Klipper limitation (found in F8):** Klipper loads `extruder`, `extruder1`, … up to the first missing number. A disabled tool in the middle therefore gets a placeholder (`nexus/tools/tN_disabled.cfg`): the heater drives a spare MCU pin, the "thermistor" is the MCU temperature, and the macros refuse to heat or select it. Tools at the end can simply be left out.

### 9.3 Behaviour with a disconnected tool

A **configured** tool whose thermistor drops out leads to a Klipper shutdown (default behaviour, deliberately preserved). The cutoff then disconnects the heater rail.

### 9.4 Cutoff

```ini
[output_pin nexus_heater_enable]
pin: nexus_tools:PB12
value: 0
shutdown_value: 0
```

*(Changed in v1.7: `value: 0`, was 1.)* The rail stays off after boot; only a passed self-test (§9.6) switches it on. The macros refuse `M104`/`M109` while the self-test has not passed.

### 9.5 Commissioning macro

`NEXUS_COMMISSION [TOOL=n]`: all heaters off and below 60 °C, then per active tool the heater is set to start + 40 °C for 20 s. The tool's own thermistor must rise ≥ 5 °C and no other thermistor ≥ 2 °C. Otherwise emergency stop with the tool and the measured rises. Klipper has no runtime PWM limit, so the heater runs under normal PID control; `verify_heater` covers a heater that heats another tool.

### 9.6 Cutoff startup self-test (AD-13)

At every Klipper start (`[delayed_gcode]`) and on demand (`NEXUS_SELFTEST`):
1. `nexus_heater_enable` = 0, wait 1.5 s, the rail voltage must be < 2 V.
2. `nexus_heater_enable` = 1, wait 1.5 s, the rail voltage must be between 20 and 28 V.
3. If a step fails: cutoff off, message, emergency stop.

RAIL_SENSE is read as a `[temperature_sensor]` with a linear `[adc_temperature]` table (0 V → 0, 3.3 V → 36.3, `adc_voltage: 3.3`), so its "temperature" is the rail voltage. `min_temp: -10` / `max_temp: 40`: a 0 V rail never causes a shutdown. Thresholds and wait time are settings in `nexus.cfg` (discharge time: open item 8b).

### 9.7 Slicer compatibility: `M104/M109 Tn`

**Decided in v1.7:** the hotends are `[extruder]` … `[extruder7]` **without a stepper**; the physical drive on the toolhead is `[extruder_stepper nexus_extruder]`, synced (`SYNC_EXTRUDER_MOTION`) to the tool that is mounted. Klipper's own `M104/M109 Tn` then work, `min_extrude_temp` protects the active tool, and Mainsail/Fluidd/KlipperScreen show 8 extruders. Consequences, handled in the macros:

- `SET_PRESSURE_ADVANCE` without `EXTRUDER=` has no handler when `[extruder]` has no stepper; a macro routes it to `nexus_extruder`.
- A `[filament_motion_sensor]` must reference `extruder_stepper nexus_extruder`: a stepperless extruder always reports position 0.

### 9.8 Staggered heat-up (current rule)

The macro layer (`M104`/`M109` override) enforces the usage scenario, regardless of the slicer: **at most `max_cold_heaters` (default 3) hotends heating from cold at once.** A hotend counts as cold below min(150 °C, target − 10 °C). `M104` that does not fit is queued and started as soon as a slot is free; `M109` waits for enough other hotends to warm up. `SET_HEATER_TEMPERATURE` bypasses the rule.

---

## 10. Installation requirements

- **Common ground:** all boards on the same PSU, or the negatives of multiple PSUs connected to each other. Without a shared GND, CAN and USB communication are unreliable and return current can flow over cable shields.
- Tool board (XT60) and dock board (XT30) each with their own power cable from the PSU.
- CAN bus as a line (daisy chain), not a star; termination only at both ends.
- Optional: passive protection at the hotend (layer 3, §8).
- A smoke detector above the printer.
- Never commission unattended. First the startup self-test (§9.6) and the commissioning macro (§9.5).
- Panel connector per tool: keyed, ≥ 4 pins, ≥ 3 A per pin. Do not plug or unplug under power (certainly applies to GX12 type).
- Panel → board wiring: ferrules in the screw terminals; heater and thermistor wires labelled per tool.
- After every (re)wiring: run the commissioning macro (§9.5).

---

## 11. Risks and points of attention

| Risk | Impact | Mitigation |
|---|---|---|
| Heater and thermistor of different tools swapped during wiring | Heater heats uncontrolled until `verify_heater` intervenes | Labelling + commissioning macro (§9.5) |
| Short from heater− to frame | Heater on, bypassing the MOSFET | Cutoff (AD-10); insulation and strain relief of the wiring |
| Noise on thermistor measurement | Temperature fluctuations, spurious shutdown | Twisted pair, separate return, RC filter, Klipper oversampling. **Validate on prototype.** |
| Heater not chosen yet; R(T) curve unknown (not published by Bambu) | PSU possibly over- or undersized; board not (AD-11) | Choose heater, then **measure:** resistance at room temperature and at ~250 °C (or current during an on-pulse at temperature). Then recalculate §7. |
| Holding power higher than assumed (fans on parked hotends) | Average power higher than 340 W | Measure on prototype: PWM duty × power per parked tool |
| Heat dissipation of switches (8 × 2.9 A + cutoff up to 24 A) | Thermal | Low-RDS(on) components, copper area; validate during detailed design |
| Klipper mapping hotends ↔ extruder | Slicer `T` commands and `M104 Tn` must drive the correct heater | Separate implementation in config/macros; the board imposes no restriction here |

---

## 12. Out of scope / open for detailed design

- Form factor, dimensions, mounting holes, connector orientation.
- Component selection: see detailed design documents.
- Klipper macros for tool changes and slicer integration.
- Mechanical design of dock and tools.
- Panel connector per tool and the umbilical to the hotend.

---

## 13. Change history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-11-09 | First draft after concept review: main board dropped, multi-MCU, USB-C tool ports, three-layer safety |
| 0.2 | 2026-11-09 | Heaters: 70 W PTC heater cores (Bambu Lab type) instead of 40 W. Usage scenario 3 cold / 5 warm fixed. Hardware sized for 8 × cold (AD-11). Channels 4 A, cutoff ≥ 25 A, main fuse 25 A. Dock board own supply (AD-07 changed). Power budget revised. |
| 0.3 | 2026-11-09 | Heater as design envelope (≤ 70 W cold, PTC or classic) instead of a fixed 70W Bambu heater; original X1 = 40–48 W. Hardware unchanged. |
| 0.3 | 2026-11-09 | (addition) Rationale AD-11: fuse/breaker as power limit rejected. |
| 0.4 | 2026-11-10 | Channel fuse 5 A; component selection see 10-toolboard-heaters-cutoff-thermistor.md (STM32G0B1RBT6, BTT6050-2ERA, LM74502 + BSC016N06NS). |
| 0.5 | 2026-11-10 | AD-12: CAN parts DNP; USB is the default topology. |
| 0.6 | 2026-11-10 | USB-C tool ports dropped: heater via screw terminal, thermistor via JST-XH, panel connector per tool out of scope. Low-side MOSFET + 5V buffer instead of BTT6050 (AD-03). Cutoff mandatory (AD-10). Host USB = USB-C (AD-05). Commissioning macro (§9.5). |
| 0.7 | 2026-11-10 | AD-08: dock board also STM32G0B1RBT6 (instead of RP2040). Fan connector JST-XH; CAN on dock board DNP. Details in 20-dockboard.md. |
| 0.8 | 2026-11-10 | AD-12: CAN populated on both boards (was DNP). |
| 0.9 | 2026-11-11 | AD-13 rail voltage measurement + startup self-test; AD-14 ESD on all signal connectors, test points, revision on the silkscreen; AD-15 open-source licenses, not for sale. §9.6–9.8 added (self-test, M104/M109, staggered heat-up). |
| 1.0 | 2026-11-17 | AD-16: power through one board with a short trunk; modular power modules and passive panel PCB rejected. Layout requirements in CLAUDE.md §6.1. |
| 1.1 | 2026-11-17 | Filament connectors 4-pin (runout + motion) to choose between D2F and clog detection; VCC_FIL default 5V. |
| 1.2 | 2026-11-17 | AD-17: diagnostic LEDs (rails, VBUS, MCU, per heater/fan channel) and BOOT/RESET on both boards. |
| 1.3 | 2026-11-17 | AD-10: layer 3 (thermal fuse on the hotend) changed from mandatory to optional. A TCO on the heater block is not feasible at print temperatures. Alternatives: PTC heater, TCO on heatsink/holder. |
| 1.4 | 2026-11-17 | AD-17: no LED per fan on the dock board. |
| 1.5 | 2026-11-17 | Board names fixed: Nexus Tools Board and Nexus Docks Board. AD-14: full board name on the silkscreen. |
| 1.6 | 2026-11-17 | Consistency pass: PT1000 pull-up 2195 Ω (§6.1.3), filament input without clamp on FT pins (§6.1.4), LED port pinout + protection (§6.1.5), pin budget 44 incl. crystal (§6.1.8), 2× LDO (§6.1.1), §12 decided items removed. |
| 1.7 | 2026-11-17 | §9 implemented in `klipper/` (F8 software): MCU names `nexus_tools`/`nexus_docks`, placeholder for a disabled tool in the middle (Klipper extruder numbering), cutoff `value: 0` until the self-test passes, hotends as stepperless extruders (§9.7 decided), staggered heat-up with queue. |
