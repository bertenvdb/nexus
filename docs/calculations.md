# Calculations (F2)

| | |
|---|---|
| **Version** | 1.0 (approved 2026-11-17; WEBENCH cross-check still open) |
| **Date** | 2026-11-17 |
| **Script** | `scripts/calc_f2.py` (tables below are its output; re-run after changing inputs) |

---

## 1. TPS54360B buck converters

Method: TI datasheet SNVSB93, §8.2.2 (equations 25–51). WEBENCH was not used; the result should be cross-checked with WEBENCH before F3 is closed, and the loop measured on the prototype (load step).

**Inputs:** VIN 24 V nominal, 28 V steady-state maximum, 48.4 V transient (SMBJ30CA clamp), 18 V minimum (UVLO). Inductor MWSA0603S-100MT (10 µH, Isat 5.5 A, Irms 4.5 A, 67 mΩ). Catch diode Vf 0.7 V at 5 A. Output capacitors 22 µF 25 V X5R 1206 (Basic C12891), effective capacitance after DC bias assumed 55 % at 5 V and 35 % at 12 V.

### 1.1 Common values

- Switching frequency 600 kHz: RT = 161 kOhm -> **162 kOhm** (eq. 27).
- UVLO start 18 V / stop 15 V: RUVLO1 = 882 k -> **887 k**, RUVLO2 = 59.6 k -> **59.0 k** (eq. 40-41). Prevents the 5 V rails from starting on a sagging or wrong PSU; with a 24 V system there is no reason to run below 15 V.
- Bootstrap capacitor 100 nF X7R, ≥ 10 V (datasheet §8.2.2.7).
- Input capacitors: ≥ 3 µF **effective** at 28 V per converter. 10 µF 50 V X5R 1206 (Basic C13585) keeps ≈ 30–40 % at 28 V, so **2 × 10 µF per converter**, close to VIN/GND of the IC. RMS ripple ≤ 1.4 A, within two 1206 MLCCs.

### 1.2 Per converter

| Quantity | Tool 5V (logic, LED, sensors) | Dock 5V (logic, LED) | Dock fan rail 12V | Dock fan rail 5V |
|---|---|---|---|---|
| Vout / Iout (design) | 5 V / 1.5 A | 5 V / 1.0 A | 12 V / 3.0 A | 5 V / 3.0 A |
| Duty cycle at 28 V | 0.18 | 0.18 | 0.43 | 0.18 |
| fsw limit pulse skip @48 V (eq. 25) | 878 kHz | 872 kHz | 1957 kHz | 895 kHz |
| fsw limit foldback @48 V (eq. 26) | 1425 kHz | 1425 kHz | 1425 kHz | 1425 kHz |
| Inductor ripple (eq. 29) | 0.68 A (K = 0.46) | 0.68 A (K = 0.68) | 1.14 A (K = 0.38) | 0.68 A (K = 0.23) |
| Inductor peak / RMS (eq. 30-31) | 1.84 / 1.51 A | 1.34 / 1.02 A | 3.57 / 3.02 A | 3.34 / 3.01 A |
| Cout needed, 50 % step, 4 % (eq. 32-33) | 12.5 µF | 8.3 µF | 10.4 µF | 25.0 µF |
| Cout chosen (effective) | 3 × 22 µF 25 V (36 µF) | 3 × 22 µF 25 V (36 µF) | 4 × 22 µF 25 V (31 µF) | 4 × 22 µF 25 V (48 µF) |
| Output ripple | 5.1 mV | 5.1 mV | 9.2 mV | 3.8 mV |
| Catch diode loss (eq. 37) | 0.94 W | 0.65 W | 1.27 W | 1.80 W |
| Input ripple current @18 V (eq. 38) | 0.67 A | 0.45 A | 1.41 A | 1.34 A |
| RHS (RLS = 10 k, eq. 42) | 52.5 k -> 52.3 k (4.98 V) | 52.5 k -> 52.3 k (4.98 V) | 140.0 k -> 140.0 k (12.00 V) | 52.5 k -> 52.3 k (4.98 V) |
| Modulator pole / crossover (eq. 44-47) | 1.32 / 19.9 kHz | 0.88 / 16.2 kHz | 1.29 / 19.7 kHz | 1.97 / 24.3 kHz |
| R4 (eq. 48) | 6.7 k -> 6.8 k | 5.5 k -> 5.5 k | 13.6 k -> 13.7 k | 11.0 k -> 11.0 k |
| C5 (eq. 49) | 17.77 nF -> 18.0 nF | 33.06 nF -> 33.0 nF | 8.99 nF -> 8.2 nF | 7.33 nF -> 6.8 nF |
| C8 (eq. 50-51) | 77.9 pF -> 82 pF | 96.6 pF -> 100 pF | 38.7 pF -> 39 pF | 48.2 pF -> 47 pF |

### 1.3 Decisions and remarks

| Item | Decision |
|---|---|
| **Catch diode (new)** | The TPS54360B is **non-synchronous** and needs an external Schottky from SW to GND (datasheet §8.2.2.5). This was **missing** from the design and the BOM. Choice: **SS56C** (60 V, 5 A, SMC, C24138, Extended). Worst-case loss 1.8 W (dock fan rail at 5 V / 3 A): SMC with ≥ 3 cm² copper on the cathode (SW) and anode (GND). |
| SS36 in the logic path | Replaced by the same **SS56C**: one unique part instead of two, the Extended count stays the same. |
| Inductor | MWSA0603S-100MT kept for all bucks: Isat 5.5 A equals the switch current limit (TI's most conservative criterion); highest peak in normal operation 3.6 A. |
| Output capacitors | Tool 5 V: 3 × 22 µF. Dock 5 V: 3 × 22 µF. Fan rail: 4 × 22 µF 25 V (12 V needs the 25 V rating). |
| Feedback | RLS 10 k. 5 V: RHS **52.3 k** (4.98 V). Fan rail: RHS 52.3 k (5 V) or **140 k** (12 V), selected by the solder jumper. |
| Compensation, 5 V logic (tool and dock) | One design for both: **R4 6.8 k, C5 18 nF, C8 82 pF** (crossover ≈ 20 kHz, compensation zero 1.3 kHz). At the dock's 1 A the modulator pole drops to 0.9 kHz, below the zero: slightly less phase margin. To confirm with WEBENCH. |
| Compensation, fan rail | One network must serve 12 V and 5 V. Compromise **R4 12.1 k, C5 8.2 nF, C8 47 pF**: crossover ≈ 17 kHz at 12 V and ≈ 27 kHz at 5 V (eq. 48 inverted), both below fsw/10 = 60 kHz; compensation zero 1.6 kHz between the two modulator poles (1.3 and 2.0 kHz). **Confirm with WEBENCH and verify on the prototype.** |
| Switching frequency | 600 kHz (RT 162 k): well below the pulse-skip and foldback limits, also at the 48 V transient. |

---

## 2. Copper widths (IPC-2221, outer layers)

IPC-2221 is conservative for wide copper with planes nearby; IPC-2152 gives smaller widths. Using IPC-2221 is on the safe side.

| Net | Current | ΔT | 1 oz (35 µm) | 2 oz (70 µm) |
|---|---|---|---|---|
| Heater trunk, per outer layer (2 layers share 23.6 A) | 11.8 A | 20 K | 5.9 mm | 3.0 mm |
| Heater trunk, single outer layer | 23.6 A | 20 K | 15.4 mm | 7.7 mm |
| Heater channel (I_cold) | 2.9 A | 10 K | 1.3 mm | 0.7 mm |
| Fan rail | 3.0 A | 10 K | 1.4 mm | 0.7 mm |
| Fan channel | 1.0 A | 10 K | 0.3 mm | 0.2 mm |
| Dock input | 3.3 A | 10 K | 1.6 mm | 0.8 mm |

### 2.1 Power trunk (CLAUDE.md §6.1) and main fuse

- The IPC-2221 result (5.9 mm per outer layer at 1 oz) confirms the earlier ≥ 7 mm.
- **But the main fuse sets a stricter rule.** Littelfuse 456 series, "PCB recommendation for thermal management": **≥ 100 µm copper and ≥ 10 mm trace width** for the 20–30 A ratings, to keep the fuse body below 90 °C. That is ≈ 1.0 mm² of copper cross-section at the fuse.
- Our stack (JLC 4-layer: 35 µm outer, inner layers to be confirmed for the chosen stackup, typically 17.5 µm):

| Option | Cross-section | Meets Littelfuse? | Cost |
|---|---|---|---|
| 7 mm on L1 + L4, 1 oz | 0.49 mm² | ✘ | — |
| **12 mm on L1 + L4 + L3 polygon, 1 oz outer** | 2 × 12 × 0.035 + 12 × 0.0175 = **1.05 mm²** | ✔ | none |
| 7 mm on L1 + L4, 2 oz outer | 0.98 mm² | ≈ | +$10–20 per order |

**Proposal: 1 oz outer copper, trunk 12 mm wide on L1, L3 and L4, stitched with vias every ≈ 3 mm.** No 2 oz needed. Trunk resistance ≈ 0.7 mΩ over 40 mm, ≈ 0.4 W at 23.6 A, spread over the polygon.

- After the split, the heater rail runs as a polygon behind the channel row and narrows from 12 mm (all 8 channels) to ≥ 2 mm (last channel).
- Heater channels: ≥ 2 mm (IPC-2221 needs 1.3 mm at ΔT 10 K). Unchanged.
- GND return of the heaters: full plane L2 + polygon on L4 at the MOSFET sources (CLAUDE.md §6.1.5).

### 2.2 Dock board

Fan rail and input: ≥ 1.6 mm, polygon preferred. Fan channels ≥ 0.8 mm (net class `FAN_CH`), well above the 0.3 mm needed.

---

## 3. Other values

| Item | Value | Basis |
|---|---|---|
| 24V LED resistors (24V IN, HEATER RAIL, heater channels) | 10 kΩ 0603 → ≈ 2.2 mA (green/red Vf ≈ 2.0–2.8 V), 48 mW | ≤ 0.1 W rating of 0603 |
| FAN RAIL LED (5–24 V) | 2.2 kΩ 0805 → 1.0 mA at 5 V (visible), 9.6 mA / 0.21 W at 24 V: **use 1206 (0.25 W)** | design 20 §7 |
| 5 V / 3V3 / VBUS LEDs | 1 kΩ (5 V) / 470 Ω (3V3) → ≈ 2 mA | |
| Crystal load capacitors | CL = 20 pF, Cstray ≈ 5 pF → C = 2 × (20 − 5) = **30 pF** (C0G) | ST AN2867 |
| Bleeder (heater rail) | 4.7 kΩ 1206: τ = 4.7 kΩ × 20 µF ≈ 94 ms, < 2 V after ≈ 0.25 s | design 1 §5.1; recheck with real rail capacitance in F3 |

---

## 4. Values used in the schematic (F3, Basic parts)

Calculated values were rounded to JLC Basic/Preferred parts; an Extended resistor costs the same $3 fee as an IC.

| Item | Calculated | Schematic | Effect |
|---|---|---|---|
| RT | 162 k | **160 k** (Preferred) | fsw ≈ 604 kHz |
| UVLO | 887 k / 59 k | **1 M / 68 k** | start 17.6 V, stop 14.3 V |
| FB 5 V | 52.3 k / 10 k | **36 k / 6.8 k** | 5.04 V |
| Compensation 5 V | 6.8 k, 18 nF, 82 pF | **6.8 k, 22 nF, 100 pF** | zero 1.06 kHz (was 1.3 kHz), pole 234 kHz |
| LM74502 VCAP | — | **100 nF** | datasheet typical/minimum |
| Crystal load | 30 pF | **30 pF C0G** | |
