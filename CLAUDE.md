# CLAUDE.md — Nexus Tools Board & Nexus Docks Board

Instructions for Claude Code in this repository. Read this file completely before doing anything. Then read `docs/README.md`.

---

## 1. What this project is

Two Klipper-compatible controller boards for a **hotend changer with up to 8 tools**, designed in **KiCad 10**, manufactured and assembled by **JLCPCB**.

| Board | Function | MCU |
|---|---|---|
| **Nexus Tools Board** — *tool board* (`toolboard/`) | 8 heaters (low-side), 8 thermistors, 8 filament sensors, 1 LED chain, hardware cutoff of the heater rail, USB + CAN | STM32G0B1RBT6 |
| **Nexus Docks Board** — *dock board* (`dockboard/`) | 9 fans (voltage 5/12/24V selectable), 1 LED chain, USB + CAN | STM32G0B1RBT6 |

The documentation abbreviates the boards as *tool board* and *dock board*. The silkscreen and product texts always use the full name.

A "tool" here is **hotend (heater) + thermistor**. Extruders, part cooling and the like are out of scope.

The **concept design and component selection are done.** They are in `docs/design/`. The next step is the **implementation in KiCad**: library, pinout, schematic, layout and production files. Follow `docs/work-plan.md`.

---

## 2. Owner and way of working

- Owner: **Berten** (GitHub `bertenvdb`). Senior software developer, maker. **No experience with KiCad or PCB layout**, but experienced with 3D printers, Klipper and hobby embedded work.
- **Language:** conversations in Dutch (Flemish). Documentation, code, commit messages and KiCad net names in English.
- **Attitude:** be a critical, honest mentor, not a cheerleader. If something is a bad idea, say so plainly and explain why.
- **When in doubt: ask first.** Ask clarifying questions before making assumptions that are hard to reverse.
- **Concept first, then implementation.** For a new idea or a design change, do not work anything out until you agree on the concept.
- **Documents** are always Markdown files (`.md`). No Word and no plain text.
- **Review points are mandatory** (see `docs/work-plan.md`). Do not move on to the next phase after a phase without Berten's approval.
- **Only Berten places JLC orders.** Never place an order or upload anything to a manufacturer without an explicit instruction.

---

## 3. Fixed design decisions

Do not change these without discussion. The rationale is in `docs/design/00-architecture.md` (section 4, AD-xx).

| ID | Decision |
|---|---|
| AD-01 | No central main board. Each board is its own Klipper MCU. |
| AD-02 | Heater via 2-pole screw terminal 5.08 mm, thermistor via JST-XH 2-pin. Per tool a panel connector in the printer (out of scope). |
| AD-03 | Heaters **low-side** with N-MOSFET WSD4070DN, gate at 5 V via CD74HCT541. |
| AD-04 | Thermistor return to AGND, separate from the heater return. |
| AD-05 | Host USB = USB-C (USB 2.0 only) on both boards. |
| AD-06 | Tool board always powered via XT60. |
| AD-07 | Dock board has its own 24V input (XT30). The CAN cable carries no power. |
| AD-08 | MCU on both boards: STM32G0B1RBT6 (LQFP-64). |
| AD-09 | An inactive tool = comment out the include in the Klipper config + restart. No hardware detection. |
| AD-10 | Two layers of thermal safety on the board (Klipper + hardware cutoff with self-test), plus an optional passive layer at the hotend. The **hardware cutoff is mandatory** (LM74502 + 2× BSC016N06NS back-to-back). Never call a thermal fuse "mandatory". |
| AD-11 | Board sized for 8 heaters on at once from cold (≈ 23.6 A). The usage scenario (max. 3 cold) applies only to the PSU. |
| AD-12 | CAN populated on both boards (transceiver, ESD and crystal by JLC; connectors hand-soldered). |
| AD-13 | Voltage measurement on the heater rail (divider 100k/10k → ADC) + startup self-test of the cutoff. |
| AD-14 | ESD on all external signal connectors, test points on all rails, board name (Nexus Tools Board / Nexus Docks Board), revision/date/license on the silkscreen. |
| AD-15 | Open source: CERN-OHL-S-2.0 (hardware), GPL-3.0-or-later (macros/config), CC-BY-SA-4.0 (docs). Not for sale, no commission. |
| AD-16 | All heater power through one tool board, with a short power trunk (see §6.1). |
| AD-17 | Diagnostic LEDs: 24V IN, rail after the cutoff/fan rail, 5V, 3V3, VBUS, MCU, + per heater channel (drain, tool board). No LED per fan on the dock board. LEDs together along one visible edge. |

**Heater design envelope:** max. 70 W at 24 V cold (PTC or classic), I_cold ≤ 2.9 A per channel.

---

## 4. Sourcing and assembly rules

1. **All parts must be in stock at LCSC/JLCPCB.** Check stock again just before freezing the BOM.
2. **Passives and generic parts from the JLC Basic library** (no fee). If a Basic variant is available, use it.
3. **As few unique Extended parts as possible.** Each unique Extended part costs ≈ $3 fee per order. Reuse parts between both boards.
4. **Hand-solder (do not have JLC place):** all THT connectors (XT60, XT30, screw terminals, JST-XH, Micro-Fit, pin headers), and the large SMD fuses if that turns out cheaper. Mark this in KiCad with a dedicated field (see §6).
5. **Source of truth for parts:** `docs/bom-master.csv`. Every symbol in KiCad gets an `LCSC` field with the C number from that file.

---

## 5. Tooling

Installation: see `docs/tooling-setup.md`.

| Tool | Use |
|---|---|
| KiCad **10.x** (PPA `kicad/kicad-10.0-releases`) | Schematic and PCB. **Do not use KiCad 7/8/9**: older versions cannot open the files. |
| `kicad-cli` | ERC, DRC, PDF/SVG export, Gerbers, drill, position files, BOM |
| `easyeda2kicad` | Import symbol, footprint and 3D model per LCSC number into `lib/` |
| Freerouting | Autorouter for signal nets (never for power nets) |
| KiKit (if compatible with KiCad 10) | Panelization + JLC production files from the command line |
| kicad-jlcpcb-tools (GUI plugin) | For Berten: LCSC assignment and production files from the KiCad GUI |

### Mandatory checks after every change

```bash
kicad-cli sch erc  --severity-all --exit-code-violations -o out/erc.rpt toolboard/toolboard.kicad_sch
kicad-cli pcb drc  --severity-all --exit-code-violations -o out/drc.rpt toolboard/toolboard.kicad_pcb
```

- **A phase is only done when ERC and DRC report 0 errors.** Assess and document each warning individually.
- After every schematic or layout change, export a **PDF or SVG** to `out/` and **look at it yourself** (Read tool on a PNG render). Do not rely blindly on the file.

---

## 6. KiCad conventions

- **Project structure:** `toolboard/toolboard.kicad_pro`, `dockboard/dockboard.kicad_pro`. Shared library in `lib/` (`nexus.kicad_sym`, `nexus.pretty/`, `3dmodels/`), via a relative path `${KIPRJMOD}/../lib/...`.
- **Hierarchical schematics**, one sheet per functional block, with the same structure as the design documents:
  - `power_input` (XT60, fuse, TVS, bulk)
  - `heater_cutoff` (LM74502 + FETs)
  - `logic_power` (SS36, TPS54360B, ME6211 ×2, USB VBUS diode-OR)
  - `mcu` (STM32, crystal, BOOT/RESET, SWD, MCU LED)
  - `diag_leds` (rail, VBUS and channel LEDs; AD-17)
  - `usb_can`
  - `heaters` (8 channels, with hierarchical repetition where sensible)
  - `thermistors`
  - `filament_inputs`
  - `led_port`
- The dock board **reuses** the sheets `logic_power`, `mcu`, `usb_can` and `led_port`. Shared sheets live as shared `.kicad_sch` files in `lib/sheets/`, or they are copied with a note. Pick one, document the choice and ask Berten.
- **Symbol fields** (mandatory on every placed part): `LCSC`, `MPN`, `Assembly` (`JLC` | `SELF` | `DNP`).
- **Net names:** English, upper case. For example `+24V_IN`, `+24V_HEATER`, `+5V`, `+3V3_MCU`, `+3V3_AUX`, `VREF_A`, `AGND`, `GND`, `HEATER_T0_N`, `THERM_T0`, `FIL_RUNOUT_T0`, `FIL_MOTION_T0`, `FAN_RAIL`, `FAN0_N`.
- **Net classes** (starting values, refine with an IPC-2152 calculation):

| Net class | Nets | Trace (1 oz outer layer) |
|---|---|---|
| `POWER_25A` | `+24V_IN`, `+24V_HEATER`, heater GND return | **Copper polygon** on ≥ 2 layers + via stitching. No traces. |
| `HEATER_CH` | per channel +24V and heater− | ≥ 2.0 mm |
| `FAN_CH` | fan outputs, `FAN_RAIL` | ≥ 0.8 mm (channel), polygon for the rail |
| `POWER_LOGIC` | +5V, +3V3 | ≥ 0.5 mm |
| `ANALOG` | `THERM_*`, `VREF_A` | 0.25 mm, away from heater and buck traces |
| `USB` | USB D+/D− | 90 Ω differential (calculate for the JLC stackup) |
| `CAN` | CAN-H/L | Differential pair, 120 Ω |
| `Default` | rest | 0.2 mm / clearance 0.2 mm |

### 6.1 Tool board power trunk (hard requirements)

The full current (worst case 23.6 A, average 12–14 A) flows only through the **trunk**: XT60 → main fuse → cutoff FETs → split to the 8 channel fuses. After that at most 2.9 A per channel.

1. **XT60, main fuse and cutoff FETs sit side by side along one board edge.** Trunk length ≤ ≈ 40 mm.
2. **Trunk = copper polygon on top and bottom layer**, connected with via stitching. Width **≥ 7 mm per layer at 1 oz** (IPC-2221, 12.5 A per layer, ΔT 20 °C → 6.4 mm). With 2 oz outer copper ≥ 3.5 mm. Verify with IPC-2152 and document in `docs/calculations.md`.
3. **2 oz outer copper only if the layout gets tight.** Costs extra at JLC; put the choice to Berten.
4. **Channel fuses and MOSFETs in a row along the split**, so each channel stays short after the split. Channel traces ≥ 2 mm (net class `HEATER_CH`).
5. GND return via the full ground plane L2, with an extra polygon on L4 at the MOSFET sources.

Rejected alternative (2026-11-16/17): spreading the power over separate modules per tool. With a central cutoff the current still flows through one board. A cutoff per module costs 8× extra safety electronics and 8 rail measurements. There will also be no passive panel PCB; the panel connector per tool remains out of scope.

- **Tool board stackup:** 4 layers, JLC standard (for example JLC04161H-7628). L1 signal + power, L2 solid GND, L3 +24V polygon / power, L4 signal + power. If 2 oz outer copper costs more, calculate whether it is needed and put it to Berten.
- **Dock board:** 2 layers is enough, unless a panel with the tool board requires a uniform stackup.

---

## 7. Pitfalls (read this)

1. **STM32G0B1 pinout:** ADC pins (FT_a) are **not** 5V tolerant in analog mode. **Filament inputs must be on FT pins without analog function** (digital 5V tolerant). Check whether VREF+ is a separate pin on LQFP-64. The thermistor pull-ups hang off the same node as the ADC reference (ratiometric measurement).
2. **BOOT0 on PA14** shares that pin with SWCLK. Set up the BOOT button with a pull-down so that SWD keeps working.
3. **Klipper compatibility:** choose FDCAN and USB pins that Klipper's `make menuconfig` supports for the STM32G0B1. Check this in the Klipper source code (`src/stm32/Kconfig`, `src/stm32/fdcan.c`), not from memory.
4. **Ground separation:** AGND and GND meet at **one point** at the MCU. The heater return current (up to 24 A to the MOSFET sources) must not flow through the AGND area.
5. **easyeda2kicad footprints are not always correct.** Check every footprint against the land pattern in the datasheet: pin 1, exposed pad and the orientation of the 3D models.
6. **JLC rotations:** the CPL often needs rotation corrections. After generating, check the JLC preview on screen (Berten does this when ordering). Document the corrections.
7. **Solder jumpers** (PT1000 selection, VCC for the filament sensors, fan voltage, FB selection of buck #2): use KiCad footprints `SolderJumper_2_Open` / `SolderJumper_3_Bridged12` and set the **default state** in the footprint as in the design documents.
8. **The dock board fan rail jumper is OPEN by default.** Put clear silkscreen text next to the jumper.
9. **Silkscreen:** put the pin function and tool number (T0–T7) at every connector. At the screw terminals: "+24V" and "HEATER−". Mandatory on every board (AD-14): board name (**Nexus Tools Board** / **Nexus Docks Board**), **revision + date**, repo URL, license "CERN-OHL-S-2.0" and the OSHW logo (only if the project meets the OSHWA certification requirements; otherwise leave it out). **No** CE logo and no words like "safe" or "certified".
10. **Editing KiCad files by hand:** allowed (S-expressions), but always validate afterwards by loading the file with `kicad-cli` and running ERC/DRC. Corrupt files are a real risk. Work in small commits.

---

## 8. Licenses and safety communication

- SPDX headers: KiCad files and hardware → `CERN-OHL-S-2.0`; scripts, macros and config → `GPL-3.0-or-later`; documentation → `CC-BY-SA-4.0`. Full texts are in `LICENSES/`.
- The README contains a **safety section** (limits, self-test, commissioning macro, never unattended during commissioning, optional passive protection). Keep it up to date with every design change that affects safety.
- No sales, no commissions, no paid services around the boards without discussing with Berten (liability, AD-15).

## 9. Git

- Repo: `nexus` on GitHub under `bertenvdb` (local folder `~/src/nexus`). Commits with `1568251+bertenvdb@users.noreply.github.com`.
- Commit **in English**, short and descriptive, one logical block per commit (for example `toolboard: add heater_cutoff sheet`).
- Do **not** commit generated files except releases: `out/` is in `.gitignore`. Production files per revision go in `fab/rev-A/`.
- KiCad backups and lock files (`*-backups/`, `*.lck`, `fp-info-cache`) are in `.gitignore`.

---

## 10. Keeping documentation up to date

- If a design decision changes during implementation, first update the relevant document in `docs/design/` (version + change history). Only then change the schematic.
- Keep `docs/bom-master.csv` in sync with the placed parts.
- Update `docs/open-items.md`: close items with date and result.
- The status per phase is in `docs/work-plan.md`.
