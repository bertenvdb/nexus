# Nexus Klipper configuration for the YUDX toolchanger

Klipper configuration and macros for the **Nexus Tools Board** and **Nexus Docks Board** on a [YUDX tool changer](https://github.com/dumplinglab/YUDX-tool-changer) (up to 8 tools, one toolhead with one extruder drive).

> ⚠️ **Not tested on hardware yet.** The configuration loads in Klipper and the macros pass the batch-mode tests (see [Tests](#tests)), but no board exists yet. Read the [safety section](../README.md#️-safety--read-this-before-you-build-or-use-a-board) first. Stay at the printer for every first test.

## What it does

| Function | How |
|---|---|
| 8 hotends (heater + thermistor) | `[extruder]` … `[extruder7]` **without stepper**. Slicer `M104/M109 Tn` and `Tn` work natively. |
| One extruder drive on the toolhead | `[extruder_stepper nexus_extruder]`, synced to the mounted tool at every change |
| Tool change | `T0` … `T7`: dock the mounted tool, pick up the new one. The YUDX latch is opened and closed with extruder moves; the sequence is a configurable move list (default = the YUDX author's RRF files) |
| Status LEDs | One LED per tool on **both** boards, same colours |
| Dock fans | Per tool a `[heater_fan]` (on while the tool is above 50 °C or has a target), plus the supply fan |
| Filament sensors | Per tool a runout switch (D2F) and/or a motion (clog) sensor |
| Heater rail cutoff | Off at boot. A self-test at every start switches it off and on and checks the rail voltage; only then can heaters be used |
| Staggered heat-up | At most 3 (configurable) hotends heat from cold at the same time (PSU limit) |
| Commissioning | `NEXUS_COMMISSION` checks that each heater heats its own thermistor |

## Files

```
klipper/
├── nexus.cfg              ← the only file you edit
└── nexus/                 ← code and board pinout, do not edit
    ├── core.cfg           state, startup, config check, NEXUS_STATUS
    ├── safety.cfg         cutoff, rail voltage, self-test, commissioning
    ├── toolchange.cfg     tool change, SET_PRESSURE_ADVANCE routing
    ├── temperature.cfg    M104/M109 with staggered heat-up
    ├── leds.cfg           LED chains, colours, supply fan
    ├── filament.cfg       runout/motion handling
    ├── tools/tN.cfg       pins of tool N (generated)
    ├── tools/tN_disabled.cfg  placeholder for a disabled tool (generated)
    └── filament/tN_*.cfg  sensor sections per tool (generated)
```

The generated files come from [`scripts/gen_klipper_tools.py`](../scripts/gen_klipper_tools.py), which holds the pin table of both boards ([pinout-toolboard.md](../docs/pinout-toolboard.md), [pinout-dockboard.md](../docs/pinout-dockboard.md)).

## Installation

1. **Firmware.** Build Klipper for both boards with `make menuconfig`:

   | Setting | Value |
   |---|---|
   | Micro-controller | STMicroelectronics STM32, STM32G0B1 |
   | Bootloader offset | 8KiB (Katapult) |
   | Clock reference | 8 MHz crystal |
   | Communication | USB (PA11/PA12), **or** CAN bus (PB0/PB1), **or** USB to CAN bus bridge (USB on PA11/PA12, CAN on PB0/PB1) |
   | CAN bus speed | 1000000 |

2. **Files.** Clone this repository on the Klipper host and link the code; copy the user file (it is yours from then on):

   ```bash
   cd ~/printer_data/config
   ln -s ~/nexus/klipper/nexus nexus
   cp ~/nexus/klipper/nexus.cfg nexus.cfg
   ```

3. **printer.cfg:**
   - add `[include nexus.cfg]`;
   - **remove the old `[extruder]` section** (stepper and hotend). `[extruder]` is now hotend T0; the stepper settings move to `[extruder_stepper nexus_extruder]` in `nexus.cfg`. Move a `[tmc2209 extruder]` section the same way (`[tmc2209 extruder_stepper nexus_extruder]`);
   - the toolhead hotend fan must list **all** configured extruders (example in `nexus.cfg`);
   - in `PRINT_START`, call `NEXUS_PRINT_START` before heating. It refuses to print when the config check or the self-test failed.
   - Nexus overrides `M104`, `M109`, `TURN_OFF_HEATERS` and `SET_PRESSURE_ADVANCE`. Remove your own overrides of these, or merge them.

4. **nexus.cfg:** fill in the MCU ids, the extruder drive and, per tool, the dock position and hotend settings. Then `FIRMWARE_RESTART` and look for `Nexus: config check OK` and `heater rail self-test passed` in the console.

## First start, in this order

1. **Self-test.** Runs automatically at every Klipper start. It fails with an emergency stop if the rail does not drop below 2 V with the cutoff off, or is not between 20 and 28 V with the cutoff on. Repeat by hand: `NEXUS_SELFTEST`.
2. **Commissioning.** `NEXUS_COMMISSION` (all tools) or `NEXUS_COMMISSION TOOL=3`. Each tool is heated for 20 s by 40 °C; its own thermistor must rise ≥ 5 °C and no other ≥ 2 °C. Run it after every (re)wiring.
3. **PID.** Per tool `PID_CALIBRATE HEATER=extruder3 TARGET=240` and copy the values into the tool's block in `nexus.cfg`. **Do not `SAVE_CONFIG` these**: Klipper refuses to save over values that come from an include.
4. **Mounted tool.** There is no tool detection. Tell Klipper what is on the toolhead: `NEXUS_SET_TOOL TOOL=0` (or `TOOL=-1` for none). It is saved across restarts.
5. **Dock positions.** Home, heat a tool, and move to each dock by hand at low speed to find `dock_x`/`dock_y` (fully engaged position). Only then set `variable_docks_verified: True`. Until then every tool change is refused.
6. **First changes** at reduced speed (lower the `f` values in the move lists), with a hand on the emergency stop.

## Configuration

Everything is in [`nexus.cfg`](nexus.cfg), with comments. The main parts:

### Tool change sequence

YUDX opens and closes the latch on the toolhead with extruder moves, so the tool being docked or picked up must be hot (≥ `min_extrude_temp`). A pickup waits for that, a dock of a cold tool is refused.

Before each sequence the toolhead goes to the **travel lane** (`travel_lane` mm in front of the dock) and then sideways to the dock. Then it runs `dock_moves` or `pickup_moves`. Each move:

| Key | Meaning |
|---|---|
| `d` | distance from the engaged dock position along the dock axis (0 = fully in, positive = out) |
| `e` | extruder move, relative, mm (optional) |
| `f` | feed rate, mm/min (as `F` in G-code) |

The defaults translate the YUDX author's `tfree0.g` (dock) and `tpost0.g` (pickup) with the dock at Y-13 and the lane at Y30:

| RRF | `d` / `e` / `f` |
|---|---|
| `G1 Y20` · `G1 Y-9 E-4 F12000` · `G1 Y-13 E-3 F5000` · `G1 Y30` | dock: 33 · 4/−4/12000 · 0/−3/5000 · 43 |
| `G1 Y0 E8 F18000` · `G1 Y-11 E-8 F10000` · `G1 Y-13 F3000` · `G1 Y20 E7 F10000` | pickup: 13/8/18000 · 2/−8/10000 · 0/–/3000 · 33/7/10000 |

`dock_direction` is the direction the toolhead moves to **enter** a dock (`Y-` for docks at the front). After the change the toolhead returns to where it started (`restore_position`), with the new tool's offsets. A Z baby-step (`SET_GCODE_OFFSET Z_ADJUST`) is kept across changes. After `NEXUS_PARK_TOOL` the toolhead stays in the travel lane.

### Temperatures and the slicer

RepRapFirmware has an *active* and a *standby* temperature per tool and switches between them itself at a tool change (`G10 P<n> S<active> R<standby>`; the YUDX RRF files use this). **Klipper has no such concept**: the slicer sets every temperature with `M104 Tn S<temp>`. Nexus does not change temperatures on its own at a tool change.

Slicer setup (OrcaSlicer / PrusaSlicer, printer with 8 extruders):
- Enable **ooze prevention** with an idle/standby temperature per filament, and **preheat** (OrcaSlicer: *Preheat time* / *Preheat steps*). The slicer then sends `M104 Tn` for a parked tool and preheats the next tool ahead of the change.
- Tool change G-code: just `T[next_extruder]`.
- Per-filament pressure advance (`SET_PRESSURE_ADVANCE ADVANCE=…`) works: Nexus routes it to the drive.
- `wait_after_pickup: True` waits after a pickup until the tool is within `temp_tolerance` of its target, so a late preheat never prints too cold.

**Staggered heat-up.** At most `max_cold_heaters` hotends draw full power at the same time. A hotend counts as cold below min(`cold_threshold`, target − `cold_margin`). An `M104` that does not fit is queued (`NEXUS_STATUS` shows it) and starts as soon as a slot is free. An `M109` waits for enough other hotends to warm up. `M104 Tn S0` and `TURN_OFF_HEATERS` clear queue entries. `SET_HEATER_TEMPERATURE` bypasses the rule. The heaters only work after a passed self-test.

### Status LEDs

LED *n* on both chains shows one tool (order configurable with `led_order_tools` / `led_order_docks`, `-1` = off):

| Colour | State |
|---|---|
| 🟢 green | below `cool_temp` (50 °C) and not heating |
| 🟠 orange | heating: more than `temp_tolerance` below the target |
| 🟡 yellow | at target, target ≤ `standby_temp` (150 °C) |
| 🔴 red | at target, target > `standby_temp` |
| 🔵 blue | cooling: more than `temp_tolerance` above the target and at least `cool_temp` |

The colours are Klipper display templates, rendered by the host every 0.5 s. They keep updating during `M109` and other waits.

### Fans

- **Dock fan *n*** (dock board FAN 0–7): `[heater_fan nexus_dock_fan_tN]`, on while tool *n* is above 50 °C or has a target. It also runs while the tool is on the toolhead: the robust choice (host timer, no macro).
- **Supply fan** (dock board FAN 8): on while any tool is above `supply_fan_temp` or has a target.
- The fan voltage is set with the solder jumper on the dock board (open by default).

### Filament sensors

Per tool, in its block in `nexus.cfg`:

```ini
[include nexus/filament/t3_runout.cfg]    # D2F/switch on connector pin 1
[include nexus/filament/t3_motion.cfg]    # motion (clog) sensor on pin 4
```

- **Runout switch:** D2F with COM on pin 2 (GND) and NO on pin 1: low = filament. For a sensor with the opposite logic, override `switch_pin` without `!` (see the generated file).
- **Runout on the mounted tool:** pause.
- **Runout on a parked tool:** `runout_parked: 'defer'` marks the tool empty and pauses right after that tool is picked up (load filament, then `RESUME`). `'pause'` pauses immediately. At the pickup the live switch decides: filament reloaded in the meantime clears the mark. `NEXUS_CLEAR_EMPTY` clears it by hand.
- **Motion sensor:** only the mounted tool's sensor is enabled, because all tools share one drive. Change `detection_length` by overriding the section below the include. Klipper limitation: there is no command to reset a motion sensor, and a parked tool's sensor has seen the shared drive move without pulses. After a pickup it therefore only watches for a clog after its first pulse. The filament moves of the pickup sequence (`e` > 0) probably give that pulse; to be confirmed on the prototype.

### Disabling a tool

- **Last tool(s):** comment out the whole block.
- **A tool in the middle:** Klipper loads `extruder`, `extruder1`, … only up to the first missing number. Comment out the block, but replace the first include with `[include nexus/tools/tN_disabled.cfg]`. The placeholder drives an unused MCU pin and reads the MCU temperature; `Tn` and `M104 Tn` are refused.

Then `FIRMWARE_RESTART`.

## Commands

| Command | Function |
|---|---|
| `T0` … `T7` | Change to that tool |
| `NEXUS_CHANGE_TOOL TOOL=n` | Same; `TOOL=-1` only docks |
| `NEXUS_PARK_TOOL` | Dock the mounted tool |
| `NEXUS_SET_TOOL TOOL=n` | Declare the mounted tool (no movement), `-1` = none |
| `NEXUS_STATUS` | Mounted tool, self-test, rail voltage, per tool temperature, target, sensors, queue |
| `NEXUS_SELFTEST` | Repeat the heater rail self-test (all heaters off) |
| `NEXUS_COMMISSION [TOOL=n]` | Heater ↔ thermistor wiring check |
| `NEXUS_PRINT_START` | Call in `PRINT_START`: refuses when the config check or self-test failed |
| `NEXUS_CLEAR_EMPTY [TOOL=n]` | Forget the "empty" mark after reloading filament |

## Limitations

- **No tool detection.** After a crash or manual intervention, check `NEXUS_STATUS` and correct with `NEXUS_SET_TOOL`.
- `SET_HEATER_TEMPERATURE` bypasses staggered heat-up and the self-test check (but not the cutoff: with the rail off, the heater gets no power and `verify_heater` shuts Klipper down).
- PID values must be copied into `nexus.cfg` by hand (no `SAVE_CONFIG`).
- The rail self-test thresholds and the wait time (1.5 s) still have to be confirmed on the prototype (rail capacitance, open item 8b).
- The move lists are a direct translation of the RRF files and have not run on a YUDX yet.
- A motion sensor only arms after its first pulse following a pickup (see [Filament sensors](#filament-sensors)).

## Tests

Without hardware, the configuration can be run through Klipper in batch mode. That checks the config syntax, the pins against the real MCU data dictionaries, and the macros (moves, queue, errors). Temperatures read 0 °C and timers (`delayed_gcode`, display templates) do not run in batch mode, so the LED and fan logic has its own test.

```bash
# once: Klipper checkout + Python env, and two firmware builds for the dictionaries
#   STM32G0B1 (as above)  → out/klipper.dict → g0b1.dict
#   STM32F446 (any main board, e.g. 12 MHz crystal, USART1) → f446.dict
KLIPPER_DIR=~/klipper PYTHON=~/klippy-env/bin/python \
DICT_MAIN=f446.dict DICT_NEXUS=g0b1.dict klipper/test/run_tests.sh
python3 klipper/test/test_templates.py      # needs jinja2
```

The scenarios are in [`test/`](test/): each `.gcode` file lists its expected output (`; EXPECT:`), forbidden output (`; REJECT:`), exit code and changes to `nexus.cfg` (`; SED:`). `KEEP=1` keeps the logs.
