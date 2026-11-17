# Connectors — overview

Reference for schematic, layout and silkscreen. In case of discrepancies the detailed design documents take precedence; update this overview as well.

## Nexus Tools Board (tool board)

| Connector | Type | Qty | Pinout | Connects to | Assembly |
|---|---|---|---|---|---|
| Power | XT60 male, right-angle (XT60PW-M) | 1 | + / − | 24V PSU | SELF |
| USB | USB-C 16-pin (USB 2.0) | 1 | standard | Klipper host. VBUS powers only the MCU (flashing without 24V) | JLC |
| CAN IN | Micro-Fit 3.0 2×2, right-angle | 1 | bottom row 24V (**not connected**, pad 2) · GND (pad 1); top row CAN-H (pad 4) · CAN-L (pad 3), seen into the mating face | Host CAN adapter or previous node | SELF |
| CAN OUT | Micro-Fit 3.0 2×2, right-angle | 1 | same | Dock board | SELF |
| CAN termination | 2-pin header + jumper | 1 | — | Jumper = 120 Ω (only at the end of the bus) | SELF |
| Heater T0–T7 | 2-pole screw terminal, 5.08 mm | 8 | +24V (fused, behind cutoff) · HEATER− | Heater via the panel connector | SELF |
| Thermistor T0–T7 | JST-XH 2-pin | 8 | 1 THERM · 2 AGND | NTC 100K / PT1000 via the panel connector | SELF |
| Filament T0–T7 | JST-XH 4-pin | 8 | 1 RUNOUT · 2 GND · 3 VCC · 4 MOTION | D2F (pins 1 + 2) or runout/motion sensor | SELF |
| LED | JST-XH 3-pin | 1 | 1 DIN · 2 GND · 3 5V | WS2812, max. 8 LEDs | SELF |
| SWD (optional) | Pin header 1×4, 2.54 mm | 1 | 3V3 · SWDIO · SWCLK · GND | Debugger/programmer | SELF |

## Nexus Docks Board (dock board)

| Connector | Type | Qty | Pinout | Connects to | Assembly |
|---|---|---|---|---|---|
| Power | XT30 male, right-angle (XT30PW-M) | 1 | + / − | 24V PSU (own cable) | SELF |
| USB | USB-C 16-pin (USB 2.0) | 1 | standard | Klipper host (without CAN) | JLC |
| CAN IN | Micro-Fit 3.0 2×2, right-angle | 1 | bottom row 24V (**not connected**, pad 2) · GND (pad 1); top row CAN-H (pad 4) · CAN-L (pad 3), seen into the mating face | CAN OUT of the tool board | SELF |
| CAN termination | 2-pin header + jumper | 1 | — | Normally fitted (end of the bus) | SELF |
| Fan 0–8 | JST-XH 2-pin | 9 | 1 FAN− · 2 V+ | 2-/3-wire fans (tacho left unconnected) | SELF |
| LED | JST-XH 3-pin | 1 | 1 DIN · 2 GND · 3 5V | WS2812, max. 8 LEDs | SELF |
| SWD (optional) | Pin header 1×4, 2.54 mm | 1 | 3V3 · SWDIO · SWCLK · GND | Debugger/programmer | SELF |

## Solder jumpers

| Board | Jumper | Default | Option |
|---|---|---|---|
| Tool | PT1000 per thermistor (8×) | Open = NTC 100K | Closed = PT1000 (`pullup_resistor: 2195`) |
| Tool | VCC filament sensors | 5 V | 3.3 V (max. 100 mA total) |
| Dock | Fan rail source | **Open: fans get no power** | 24 V direct or via the buck |
| Dock | Fan buck voltage | — | 12 V or 5 V |

Total: tool board 38 connectors, dock board 15. Only the USB-C is placed by JLC.
