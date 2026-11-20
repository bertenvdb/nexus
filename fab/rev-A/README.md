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
| Via covering | Tented (default). The 8 thermal vias (0.3 mm) in the exposed pad of each TPS54360B are via-in-pad: if JLC offers "Epoxy Filled & Capped" at no or small extra cost, take it (no solder wicking); otherwise tented is acceptable | |
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

The rotations come from the default correction table of kicad-jlcpcb-tools (JLCKicadTools, `scripts/fab_rotations.csv`). They are not verified for our parts. In the preview, check pin 1 / polarity of every part listed with a non-zero correction in `<board>-rotations.txt`, and in any case:

| Part | Correction | Watch |
|---|---|---|
| LQFP-64 (MCU) | +270 | pin 1 dot |
| SOIC-8, SOIC-20W | +270 | pin 1 |
| SOT-23, SOT-23-5, SOT-23-6 | −90 | the default table rule `^SOT-23` also catches the 5- and 6-pin variants: check those separately |
| TSOT-23-8 (LM74502) | +180 | pin 1 |
| TI SO-PowerPAD-8 (TPS54360B) | +270 | **own addition by analogy with SOIC**: check |
| Infineon PG-TDSON-8 (BSC016N06NS) | +270 | **own addition by analogy with TDSON-8-1**: check |
| USB-C HRO TYPE-C-31-M-12 | +180 | position as well: the CPL uses the centre of the pads, 1.46 mm from the footprint origin |
| WSD4070DN (easyeda footprint), diodes, LEDs, electrolytic polarity | 0 | cathode / pin 1 side |

Write every correction that turns out wrong (and every one that was right) into `scripts/fab_rotations.csv` and this table, then regenerate.
