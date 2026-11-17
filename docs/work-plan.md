# Work plan KiCad implementation

Every phase ends with a **review by Berten**. Only start the next phase after their approval. Keep the status column up to date.

| Phase | Content | Status |
|---|---|---|
| F0 | Repo and tooling | ✅ Approved 2026-11-17 |
| F1 | Parts library | 🔍 Ready for review ([library-review.md](library-review.md)) |
| F2 | Pinout and mechanical constraints | ⏳ |
| F3 | Schematic Nexus Tools Board | ⏳ |
| F4 | Schematic Nexus Docks Board | ⏳ |
| F5 | Layout Nexus Tools Board | ⏳ |
| F6 | Layout Nexus Docks Board | ⏳ |
| F7 | Production files and JLC quote | ⏳ |
| F8 | Firmware and Klipper configuration | ⏳ |

---

## F0 — Repo and tooling

**Goal:** a working environment in which `kicad-cli` can run ERC and DRC.

1. GitHub repo `nexus` under `bertenvdb` (ask Berten: public or private).
2. Structure:
   ```
   CLAUDE.md
   README.md
   .gitignore
   docs/                 (this documentation)
   lib/                  (nexus.kicad_sym, nexus.pretty/, 3dmodels/, sheets/)
   toolboard/            (KiCad project)
   dockboard/            (KiCad project)
   scripts/              (import, check and export scripts)
   fab/                  (production files per revision)
   out/                  (generated, in .gitignore)
   ```
3. Installation according to `tooling-setup.md`. Check with `kicad-cli version` that it is **10.x**.
4. `scripts/check.sh`: runs ERC and DRC on both boards and returns an exit code ≠ 0 on errors.

**Done when:** empty projects for both boards open without errors, `scripts/check.sh` runs, the first commit is pushed.

---

## F1 — Parts library

**Goal:** every part from `bom-master.csv` is in `lib/` with a checked symbol, a footprint and a 3D model.

1. First refresh the stock and Basic/Extended status of every line in `bom-master.csv` on jlcpcb.com/parts. Lines marked "TBD" get a concrete C number.
2. `scripts/import_parts.sh`: calls `easyeda2kicad --full --lcsc_id=<C> --output lib/nexus` for every C number in the CSV.
3. For generic passives (0603 R/C) and standard connectors, use the **standard KiCad libraries** (`Resistor_SMD:R_0603_1608Metric`, `Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical`, …), with the LCSC field filled in.
4. **Check every imported footprint** against the datasheet: pad dimensions, pin 1, exposed pad and thermal vias (SO8-PowerPAD of the TPS54360B, DFN3×3 of the WSD4070DN, SuperSO8 of the BSC016N06NS, WSON of the LM74502).
5. Record the results in `bom-master.csv` (columns `lib_source`, `lib_symbol`, `lib_footprint`, `verified`).

**Review F1:** list of parts with their status, plus deviations and doubtful cases.

---

## F2 — Pinout and mechanical constraints

**Goal:** pin down what determines the schematic and the layout, **before** you start drawing.

1. **STM32G0B1RBT6 pinout** for both boards in `docs/pinout-toolboard.md` and `docs/pinout-dockboard.md`. Per pin: function, net name, pin type (FT/FT_a/TT), alternate function, rationale. Mandatory checks:
   - VREF+ as a separate pin or not (datasheet, pin table)
   - 9 ADC channels (8 thermistors + RAIL_SENSE) on FT_a pins that do not clash with USB, SWD, FDCAN or the crystal
   - 16 filament inputs (8× RUNOUT + 8× MOTION) on FT pins **without** analog function
   - FDCAN and USB pins supported by Klipper (check the source code)
   - An arrangement that makes the layout logical: heater PWM on the MOSFET side, ADC on the thermistor connector side
2. **Mechanical constraints. Ask Berten for these, do not make them up:**
   - Maximum dimensions of both boards and their location in the printer
   - Mounting holes (number, diameter, position, M3?)
   - Which edges the connectors go on (wiring to the panel, the PSU and the host)
   - Height restrictions (electrolytic caps, XT60)
   - Should the boards be ordered together in one panel (see `design/20-dockboard.md` §8)?
3. **Calculations for the TPS54360B** (both applications): RT, compensation, inductor, output capacitors, FB divider. Use TI WEBENCH or the datasheet formulas. Record them in `docs/calculations.md`.
4. **Trace widths and copper:** IPC-2152 calculation for the net classes in `CLAUDE.md` §6 and the power trunk (§6.1). Decide 1 or 2 oz with Berten (cost).

**Review F2:** pinout tables, mechanical drawing or description, calculations.

---

## F3 — Schematic Nexus Tools Board

**Goal:** a complete hierarchical schematic with ERC = 0 errors.

1. Sheets in this order: `power_input` → `heater_cutoff` → `logic_power` → `mcu` → `diag_leds` → `usb_can` → `heaters` → `thermistors` → `filament_inputs` → `led_port`.
2. **Per sheet:** draw, run ERC, export PDF to `out/`, look at the render yourself, commit.
3. After every 2–3 sheets: short review by Berten with the PDF.
4. All component values, pull-ups, solder jumpers and default settings **exactly as in the design documents**. If anything deviates, raise it first.
5. Test points (AD-14): +24V_IN, +24V_HEATER, +5V, +3V3_MCU, +3V3_AUX, VREF_A, RAIL_SENSE, GND, AGND, CAN-H/L, and the gate and drain of one heater channel.
6. Title block of every sheet: title **Nexus Tools Board** (dock: **Nexus Docks Board**), revision and date.

**Done when:** ERC 0 errors, every symbol has `LCSC`/`MPN`/`Assembly`, the KiCad BOM export matches `bom-master.csv`.

**Review F3:** complete schematic PDF + BOM comparison.

---

## F4 — Schematic Nexus Docks Board

Same approach as F3. Reuse the shared sheets (CLAUDE.md §6). Extra sheets: `power_input_dock` (XT30, fuse, TVS, LM74502 with 1 FET), `fan_rail` (buck #2 + solder jumpers), `fans` (9 channels).

**Review F4:** schematic PDF + BOM comparison.

---

## F5 — Layout Nexus Tools Board

Work in four steps, **each with a review**. Render after each step (`kicad-cli pcb export svg` / `pcb render`) and look at it yourself first.

1. **Outline and placement:** board outline and mounting holes (from F2), connectors on the edges, functional blocks grouped. Mandatory: compact buck loop, AGND area around the thermistor inputs and the MCU, **power trunk according to CLAUDE.md §6.1** (XT60, main fuse and cutoff FETs side by side along one edge, trunk ≤ 40 mm, fuses + MOSFETs in a row). **Diagnostic LEDs (AD-17) together along one edge that stays visible when installed.**
2. **Power and ground:** polygons for +24V_IN, +24V_HEATER and the GND return on multiple layers, with via stitching. Trunk ≥ 7 mm per layer at 1 oz (≥ 3.5 mm at 2 oz), top + bottom. Thermal copper for the FETs (≥ 4 cm² per cutoff FET). The AGND–GND star point.
3. **Routing:** critical signals by hand first (USB pair, CAN pair, crystal, thermistor traces, buck feedback), then the rest (Freerouting if need be, **never** for power nets).
4. **Finishing:** silkscreen (board name **Nexus Tools Board** clearly legible on the top side, together with revision, date and license (AD-14); tool numbers, pin functions, polarity, solder jumper settings, a label at every diagnostic LED, warning at the fan rail jumper on the dock board), fiducials if needed, DRC = 0, 3D render.

**Review F5:** renders of all layers + 3D view + DRC report.

---

## F6 — Layout Nexus Docks Board

Same approach as F5, with **Nexus Docks Board** as the board name on the silkscreen. Extra attention: the flyback diodes close to the fan connectors, the solder jumper and silkscreen text for the fan rail.

---

## F7 — Production files and quote

1. Gerbers, drill, BOM and CPL in JLC format to `fab/rev-A/<board>/` (KiKit `fab jlcpcb` or `kicad-cli` + script).
2. Only `Assembly = JLC` in the BOM. `SELF` and `DNP` go in a separate list of hand-soldered parts, which Berten orders from LCSC.
3. Check CPL rotations and document the corrections.
4. **Berten** uploads the files to JLC for a quote and checks the placement preview. Update `design/30-cost-estimate.md` with the real figures.
5. Tag `rev-A` in git.

---

## F8 — Firmware and Klipper configuration

1. Klipper `make menuconfig` settings for both boards (STM32G0B1, 128 KB, 8MHz crystal, USB or CAN or USB-CAN bridge) in `firmware/`.
2. Katapult configuration.
3. Klipper config: `[mcu toolboard]`, `[mcu dock]`, one include per tool (heater, thermistor, `filament_switch_sensor` and/or `filament_motion_sensor`), `heater_enable` (cutoff), MCU status LED, LEDs, fans. Motion sensors: link to the physical extruder and enable only the active tool's sensor in the tool change macro (`SET_FILAMENT_SENSOR`, open item 28).
4. **Commissioning macro** (architecture §9.5): per tool, briefly turn on one heater and check that **only** the matching thermistor rises. Otherwise `M112`.
5. **Cutoff startup self-test** (§9.6) via RAIL_SENSE.
6. **`M104/M109 Tn` compatibility** (§9.7) and **staggered heat-up** (§9.8). Test with OrcaSlicer, PrusaSlicer and Cura G-code.
7. Test plan for the first prototype: power-up without load, the voltage rails and their diagnostic LEDs, flashing, USB, CAN, one heater with cutoff test (incl. heater channel LED), all channels, filament runout + motion inputs, thermal test with 8 heaters cold.
