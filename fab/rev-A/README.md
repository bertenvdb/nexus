<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Production files rev A (F7)

Generated on 2026-11-20 by `scripts/fab.py toolboard` and `scripts/fab.py dockboard` from the approved layouts (F5, F6). Regenerate after every layout change; do not edit these files by hand.

| File | Use |
|---|---|
| `<board>-gerbers.zip` | PCB order: Gerbers (F.Cu, In1, In2, B.Cu, paste, mask, silk, outline) + Excellon drill (PTH and NPTH) + job file |
| `<board>-bom-jlc.csv` | PCBA: BOM, only the parts JLC places (`Assembly = JLC`) |
| `<board>-cpl-jlc.csv` | PCBA: placement (centre of the pads, rotation corrected) |
| `<board>-rotations.txt` | Rotation correction per footprint: what to check in the placement preview |
| `<board>-handsolder.csv` | Parts to order from LCSC and solder by hand (`Assembly = SELF`) |

## PCB order settings (both boards)

| Setting | Value | Why |
|---|---|---|
| Layers | 4 | stackup L1 signal, L2 GND, L3 power/signal, L4 signal |
| Material / thickness | FR-4, 1.6 mm | |
| Stackup | JLC04161H-7628 (standard) | inner copper 0.5 oz as in `docs/calculations.md` §2 |
| Outer copper | 1 oz | open item 16: no 2 oz needed |
| Min. via / hole | 0.3 mm drill / 0.6 mm pad (power vias 0.4 / 0.8) | within the standard 4-layer capability |
| Via covering | **Plugged** (JLC standard for 4 layers; "Tented" is no longer offered). Deliberate choice: "Epoxy Filled & Capped" costs about €19 per board design (€19.63 / €18.76 on the 2026-11-20 quote). The 8 thermal vias (0.3 mm) in the exposed pad of each TPS54360B are via-in-pad; check that solder joint after the first delivery (open item 31) | |
| Surface finish | HASL lead-free or ENIG | ENIG is flatter for the LQFP-64 and the 0.65 mm pitch parts; your choice on price |
| Silkscreen / mask | any colour, white silk | |
| Order number | "Specify a location" is not prepared (no `JLCJLCJLCJLC` text); choose "Remove order number" or accept JLC's position | |
| Board size | Tools Board 140 × 90 mm, Docks Board 88 × 62 mm | |
| Panel | none: order the two boards as two separate designs (open item 18) | |

## PCBA settings

- Assembly side: **top** only. All THT connectors and the parts in `<board>-handsolder.csv` are not placed by JLC.
- Upload `<board>-bom-jlc.csv` and `<board>-cpl-jlc.csv`. Stock was checked on 2026-11-20 (all parts in stock with at least 3× the need for 5 + 5 boards; MCU STM32G0B1RBT6: 1,399).
- Unique parts placed by JLC: 57 over both boards (34 Basic, 4 Preferred, 19 Extended). Each Extended part costs about $3 per order and per board design.

## Check in the JLC placement preview

The rotations come from the default correction table of kicad-jlcpcb-tools (JLCKicadTools), corrected after Berten's check of the JLC placement preview on 2026-11-20 (pin 1 compared with the position of pad 1 in the `.kicad_pcb`). `scripts/fab_rotations.csv` has a rule per LCSC part number where JLC's model orientation differs between parts with the same footprint.

| Part | Footprint | Correction | Preview 2026-11-20 |
|---|---|---|---|
| STM32G0B1 | LQFP-64 | +270 | OK |
| SOIC-8, CD74HCT541 (SOIC-20W) | SOIC- | +270 | OK |
| TPS54360B | TI SO-PowerPAD-8 | +270 (own, by analogy with SOIC) | OK |
| BSC016N06NS | Infineon PG-TDSON-8 | +270 (own) | OK |
| ME6211, USBLC6 | SOT-23-5, SOT-23-6 | −90 | OK |
| **SN74AHCT1G125** C7484 | SOT-23-5 | **+180** (rule for the part number) | was −90: 90° off |
| **BAT54S** C408389, **PESD2CAN** C907830 | SOT-23 | **+180** (`^SOT-23$`) | was −90: 90° off |
| **LM74502** C3236215 | TSOT-23-8 | **+270** (rule for the part number) | was 180: 90° off |
| **USB-C** HRO TYPE-C-31-M-12 | | **0** | was 180: pins at the board edge. Position (centre of the pads, 1.46 mm from the footprint origin) OK; the front overhangs the edge by ≈ 1 mm as the footprint intends |
| WSD4070DN, diodes, LEDs | | 0 | OK |

The bold corrections are derived from the rotation that fixed the part in the viewer (assuming JLC counts counter-clockwise like KiCad). Checked once more with the regenerated files on 2026-11-20: all correct.

BOM: one line per LCSC part number. The LEDs have a value per function (`green 24V IN`, `red HEATER T0`, ...); as separate lines JLC set them to 0 pieces and left them unticked ("multiple lines matched to the same part").
