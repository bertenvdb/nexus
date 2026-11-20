# Nexus

**Nexus Tools Board** and **Nexus Docks Board**: Klipper controller boards for a hotend changer with up to 8 tools.

- **Nexus Tools Board:** 8 heaters, 8 thermistors (NTC 100K / PT1000), 8 filament sensors, 1 WS2812 chain, hardware cutoff of the heater rail with startup self-test, USB + CAN.
- **Nexus Docks Board:** 9 fans (5/12/24V), 1 WS2812 chain, USB + CAN.

Both boards: STM32G0B1RBT6, Klipper + Katapult, designed in KiCad 10 for JLCPCB assembly.

Status and documentation: [`docs/README.md`](docs/README.md). Klipper configuration and macros (YUDX toolchanger): [`klipper/`](klipper/README.md). Working agreements for Claude Code: [`CLAUDE.md`](CLAUDE.md).

---

## ⚠️ Safety — read this before you build or use a board

This board drives heaters. A mistake in the design, assembly, wiring or configuration can cause a **fire**. This is a hobby project. It is **not certified**, not CE marked and not independently tested.

**Design limits**
- **24 V DC** only. Max. **70 W per heater channel** (measured at room temperature), max. 8 channels.
- Thermistors: NTC 100K or PT1000. No thermocouples or PT100.
- Only for use with **Klipper** and the included safety macros.

**Mandatory**
1. Klipper's `verify_heater` active, with sensible `max_temp` values.
2. Keep the **cutoff startup self-test** enabled (runs at every Klipper start, `NEXUS_SELFTEST`). Do not print if it fails; call `NEXUS_PRINT_START` in your `PRINT_START` so a print cannot start without it.
3. Run the **commissioning macro** `NEXUS_COMMISSION` after every (re)wiring. It checks that each heater heats the correct thermistor.
4. **Never print unattended** until the whole setup has proven itself over multiple prints.
5. One PSU, or PSUs with a common negative.
6. Check the **power cable polarity** before you plug in: on the board connector (XT60 on the Tools Board, XT30 on the Docks Board) **+ is pin 2**, marked **+** on the silkscreen. Wire your plug to match.

**Optional**
- Extra passive protection at the hotend: a PTC heater (self-limiting) and/or a thermal fuse (TCO) on the heatsink or tool holder. A TCO on the heater block itself does not work: they go up to ±240 °C, at or below print temperature.
- A smoke detector above the printer.

You build and use this design **entirely at your own risk**. See the disclaimers in the licenses.

---

## Licenses

| Part | License |
|---|---|
| Hardware (KiCad files, production files) | [CERN-OHL-S-2.0](LICENSES/CERN-OHL-S-2.0.txt) |
| Klipper macros, config, scripts | [GPL-3.0-or-later](LICENSES/GPL-3.0-or-later.txt) |
| Documentation | [CC-BY-SA-4.0](LICENSES/CC-BY-SA-4.0.txt) |

Copyright © 2026 Berten.
