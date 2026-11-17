# Documentation — Nexus Tools Board & Nexus Docks Board

## Status (2026-11-17)

| Item | Status |
|---|---|
| Concept architecture | ✅ Done (v1.6) |
| Component selection Nexus Tools Board | ✅ Done (parts 1–3) |
| Component selection Nexus Docks Board | ✅ Done |
| Cost estimate | ✅ Estimate, no JLC quote yet |
| KiCad implementation | 🔄 F0–F2 done, F3 (tool board schematic) in review, see [work plan](work-plan.md) |

## Reading order

1. [`../CLAUDE.md`](../CLAUDE.md): working agreements and fixed decisions
2. [`design/00-architecture.md`](design/00-architecture.md): functional and technical architecture, decisions AD-01 to AD-17
3. [`design/10-toolboard-heaters-cutoff-thermistor.md`](design/10-toolboard-heaters-cutoff-thermistor.md): MCU, heater channels, cutoff, thermistor input
4. [`design/11-toolboard-power-can-usb.md`](design/11-toolboard-power-can-usb.md): 24V input, 5V/3.3V, CAN, USB, clock, assembly strategy
5. [`design/12-toolboard-filament-led.md`](design/12-toolboard-filament-led.md): filament inputs, LED port, pin budget
6. [`design/20-dockboard.md`](design/20-dockboard.md): Nexus Docks Board, complete
7. [`design/30-cost-estimate.md`](design/30-cost-estimate.md): cost estimate for 5 units
8. [`bom-master.md`](bom-master.md) / [`bom-master.csv`](bom-master.csv): all parts, both boards
9. [`open-items.md`](open-items.md): everything that still needs to be checked or decided
10. [`work-plan.md`](work-plan.md): implementation phases with review points
11. [`tooling-setup.md`](tooling-setup.md): installing KiCad and the tools
12. [`connectors.md`](connectors.md): all connectors, pinouts and solder jumpers
13. [`product-description.md`](product-description.md): product-style description of both boards, for the README or a project page
14. [`library-review.md`](library-review.md): F1 parts library review (sources, footprint checks, stock)
15. [`pinout-toolboard.md`](pinout-toolboard.md) / [`pinout-dockboard.md`](pinout-dockboard.md): STM32G0B1 pin assignment
16. [`mechanical.md`](mechanical.md): mechanical constraints, layout concepts, connector overhang
17. [`calculations.md`](calculations.md): buck converters, copper widths, LED resistors

## One minute of context

- **Names:** the two boards are called **Nexus Tools Board** (heaters, thermistors, filament) and **Nexus Docks Board** (fans). The technical documents abbreviate them as *tool board* and *dock board*. The full name is on the silkscreen of each PCB.
- **Why this architecture:** Klipper supports multiple MCUs natively, so each board is its own MCU (no custom protocol). The heaters switch low-side, as on standard boards. Because a short from heater− to ground bypasses the MOSFET, there is a hardware cutoff on the positive side. Klipper turns it off on every shutdown.
- **Why these parts:** everything is in stock at LCSC. As many parts as possible are shared between both boards, to limit JLC's Extended fee (≈ $3 per unique part per order).
- **Open source (AD-15):** CERN-OHL-S-2.0 / GPL-3.0-or-later / CC-BY-SA-4.0. Not for sale. Safety section in the root README.
- **History:** the concept started with three boards and USB-C ports as heater connectors. That was abandoned. The reasoning is in the architecture's change history (v0.1 → v1.6). Do not propose it again without new arguments.
