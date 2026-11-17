# Mechanical constraints and board outline

| | |
|---|---|
| **Version** | 1.0 (approved 2026-11-17) |
| **Date** | 2026-11-17 |

## 1. Requirements (Berten, 2026-11-17)

| # | Requirement |
|---|---|
| M1 | Dimensions are free. Compact is better, but **budget has the highest priority**. |
| M2 | Mounting holes in the corners, for **M3** screws. At least 3 mm between hole edge and board edge, 4–5 mm preferred. |
| M3 | No height restrictions. |
| M4 | Tool connectors either **in a row per type**, or **grouped per tool**. Groups may be split over **two opposite edges**. |
| M5 | USB-C, CAN and XT60 (dock: XT30) side by side on **one edge**, all overhanging the board edge by the **same** amount, as much as possible (ideal 3–4 mm). |
| M6 | Both boards are mounted **outside the heated chamber** (Berten, 2026-11-17): room-temperature ambient. Basis for the fuse derating and the thermal checks (calculations.md §7). |

## 2. Derived rules

| Item | Value | Why |
|---|---|---|
| Mounting hole | Ø 3.2 mm, **non-plated, no copper** (`MountingHole:MountingHole_3.2mm_M3`) | Plated holes tied to GND would ground the board through the printer frame: a second ground path next to the PSU negative (ground loop). |
| Hole position | Centre **6.1 mm** from both edges (1.6 mm radius + 4.5 mm) | M2, middle of "4–5 mm" |
| Keep-out around hole | Ø 7.5 mm, no parts, no copper on any layer | M3 washer Ø 7 mm + margin |
| Edge clearance copper | ≥ 0.5 mm (JLC minimum 0.3 mm) | |
| Connector overhang (M5) | **1.0 mm** for all edge connectors | See §3 |

## 3. Connector overhang (M5)

How far a horizontal connector can stick out over the edge is limited by its front-most pad: every pad must stay on the board with ≥ 0.5 mm copper-to-edge clearance. Measured from the KiCad 10 footprints:

| Connector | Footprint | Front-most pad | Max. overhang |
|---|---|---|---|
| USB-C | `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | front shell legs | **1.35 mm** |
| CAN | `Molex_Micro-Fit_3.0_43045-0400_..._Horizontal` | mounting peg | 2.75 mm |
| XT30 (dock) | `AMASS_XT30PW-M_..._Horizontal` | mounting pegs | 1.95 mm |
| XT60 (tool) | `AMASS_XT60PW-M_..._Horizontal` | mounting pegs | 8.9 mm |

The USB-C sets the limit. **Proposal: all fronts 1.0 mm past the board edge** (0.35 mm reserve on the USB-C for board-cutting tolerance, JLC ±0.2 mm). 3–4 mm would need a USB-C whose shell legs sit further back (a "sink"/mid-mount type), which costs board area and an extra Extended part, so it is not worth it.

## 4. Size of the tool connector rows

Connector widths (incl. 1 mm gap): screw terminal 5.08 mm 2-pole 10.2 mm, JST-XH 2-pin 6.0 mm, JST-XH 4-pin 13.4 mm.

| Row | Width |
|---|---|
| 8 × heater screw terminal | ≈ 82 mm |
| 8 × thermistor JST-XH 2 | ≈ 48 mm |
| 8 × filament JST-XH 4 | ≈ 107 mm |
| Per tool (terminal + XH2 + XH4) | ≈ 31 mm → 4 tools ≈ 124 mm |
| Power edge: XT60 + USB-C + 2 × Micro-Fit | ≈ 52 mm |
| Corner reserved for a mounting hole | ≈ 10 mm per corner per edge |

**Consequence:** the filament row (107 mm) or a 4-tool group (124 mm) plus two corners does not fit in 100 mm. A tool board ≤ 100 × 100 mm (the cheapest JLC size class) is **not possible** with M4. Expected size **≈ 130 × 85 mm**. The cost estimate assumed 110 × 80 mm: plan for **+$5–15 on the 5-board PCB price** (to be confirmed with the JLC calculator in F7).

## 5. Tool board concepts

### Concept A — rows per type (recommended)

```
          ┌─ filament JST-XH 4 ×8 (T0 … T7, ≈107 mm) ─┐
   ┌──○─────────────────────────────────────────────────○──┐
 U │                                                     │ T
 S │        5V buck     MCU (filament side up,            │ h
 B │        LDOs         ADC side right)        AGND area │ e
   │                                                     │ r
 C │  CAN       diag LEDs                                 │ m
 A │  transc.                                             │ ×8
 N │                                                      │
 ×2│  cutoff   ─── 74HCT541 ── gate drive ───             │ L
 X │  fuse 25A   [F MOSFET][F MOSFET] … ×8                 │ E
 T │                                                      │ D
 60└──○─────────────────────────────────────────────────○──┘
          └─ heater screw terminals ×8 (≈82 mm) ──┘
             power trunk: XT60 → fuse → cutoff → split  (bottom-left corner, ≤ 40 mm)
```

- **Left edge:** XT60 (bottom), CAN IN, CAN OUT, USB-C, all 1.0 mm overhang (M5).
- **Bottom edge:** 8 heater screw terminals. Directly behind them the row of channel fuses and MOSFETs (CLAUDE.md §6.1). The trunk starts at the XT60 in the bottom-left corner and stays ≤ 40 mm.
- **Top edge:** 8 filament connectors.
- **Right edge:** 8 thermistor connectors, LED port, SWD header.
- **Why recommended:** heater current (bottom) and the thermistor inputs (right) are on different edges, and the AGND area (top right, around the ADC side of the MCU) stays free of heater return current (CLAUDE.md §7.4). Wiring per type is also easy to label.

### Concept B — groups per tool on two opposite edges

```
   ┌──○─[T0: H th fil][T1: H th fil][T2 …][T3 …]──○──┐
 U │                                                  │
 S │           MCU, logic, CAN, diag LEDs             │ LED
 B │                                                  │ SWD
 C │                                                  │
 A │  trunk ── splits into 2 heater rows (top/bottom) │
 N │                                                  │
 X └──○─[T4: H th fil][T5 …][T6 …][T7 …]─────────○──┘
 T60
```

- Each tool: screw terminal + thermistor + filament side by side; tools T0–T3 at the top, T4–T7 at the bottom.
- **Drawbacks:** heater power and thermistor inputs sit next to each other in every group, so heater return current runs past the analog inputs; the trunk must split into two heater rows (two copper buses instead of one); the board becomes ≈ 135 × 95 mm.
- **Advantage:** one cable bundle per tool.

## 6. Dock board

```
   ┌──○──[FAN 0][FAN 1] … [FAN 8]  (JST-XH 2 ×9, ≈ 54 mm)──○──┐
 U │                                                         │
 S │   MCU   CAN transc.   fan buck   5V buck   74HCT541     │ LED
 B │                                                         │ SWD
 C │                         fan-rail solder jumper + warning│
 A │                                                         │
 N └──○───────────────────────────────────────────────────○──┘
 X
 T30
```

- **Left edge:** XT30, CAN IN, USB-C, 1.0 mm overhang.
- **Top edge:** 9 fan connectors in one row. **Right edge:** LED port and SWD.
- Expected size **≈ 75 × 55 mm**, within 100 × 100 mm. 2 layers (unless panelled with the tool board, see design 20 §8).

## 7. Decisions (Berten, 2026-11-17)

| Item | Decision |
|---|---|
| Tool board layout | **Concept A: rows per type** |
| Connector overhang | **1.0 mm** for USB-C, CAN and XT60/XT30 |
| Copper | **1 oz** outer, power trunk 12 mm on L1 + L3 + L4 ([calculations.md](calculations.md) §2.1) |
| JST-XH | **Straight (vertical)** |
| Screw terminal | WJ500V-5.08-2P (C8465) on KiCad `TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal`: checked against the Kangnex drawing (pitch 5.08, recommended hole 1.2 mm vs 1.3 mm drill, pin row 4.5 vs 4.65 mm from the back, width 10.16 vs 10.26 mm) |

## 8. Board size after placement (F5 step 1, 2026-11-17)

The tool board is **140 × 90 mm**, not the ≈ 130 × 85 mm estimated in §4. With concept A the rows did not fit:

| Constraint | Need |
|---|---|
| 8 filament JST-XH 4 at a pitch ≥ 13.6 mm (courtyard 13.5 mm) between the top corner keep-outs | ≥ 109 mm + 2 × ~10 mm corners |
| 8 thermistor JST-XH 2 at 6.9 mm pitch + LED port on the right edge, clear of the corner holes | ≥ 72 mm between the keep-outs |
| Filament input networks under the top row, thermistor networks along the right edge, without overlap | ≈ 10 mm extra width |

Area +14 % (12,600 vs 11,050 mm²). Cost effect: to be checked with the JLC quote in F7; expected a few dollars on 5 boards.
