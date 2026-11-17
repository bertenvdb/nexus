# Nexus Tools Board

> *Draft. The specifications follow design v1.6. Dimensions and mounting holes will be fixed in phase F2. This project is open source and is not sold.*

## Eight hotends, one board

A toolchanger with eight hotends means eight heaters, eight thermistors and eight filament paths, often with a tangle of separate modules around them. The **Nexus Tools Board** brings all of that together on one Klipper board, designed for a single job: keeping up to eight hotends reliably hot and monitored.

Connect the board over USB-C or CAN, add a short config file per tool, and Klipper sees eight fully fledged hotends. Want to disable a tool temporarily? Comment out one line and restart Klipper.

Safety lives in the hardware, not only in the firmware. A **hardware cutoff** removes power from all heaters as soon as Klipper stops. A **self-test at every startup** checks that the cutoff actually switches. Per channel, an LED shows what the MOSFET is really doing, not what the software thinks it is doing.

---

## Highlights

- **8 heater channels up to 70 W each**, all eight at once from a cold start. Suitable for classic cartridges and PTC heater cores.
- **Hardware cutoff of the heater rail**, controlled by Klipper and off by default. If the firmware goes down, the heaters go down.
- **Startup self-test:** a voltage measurement on the heater rail proves at every start that the cutoff works.
- **8 thermistor inputs for NTC 100K or PT1000**, selectable per channel, with 0.1 % precision resistors.
- **Clog detection per tool:** each filament port has both a runout and a motion input. Use a simple D2F switch, or a motion sensor that notices a clogged nozzle or a slipping extruder.
- **USB-C and CAN** on the same board, including a USB-to-CAN bridge: one cable to the host is enough.
- **Diagnostic LEDs for every rail and every heater channel.** A burnt-out MOSFET is recognisable at a glance.
- **WS2812 port** for status lighting, with level shifter and current limiting.
- **Fully open source:** KiCad files, BOM and Klipper config, ready for JLCPCB assembly.

---

## Built to make faults visible

Most printer boards only show whether they have power. The Nexus Tools Board shows where things go wrong:

| LED | Tells you |
|---|---|
| **24V IN** | Power is coming in and the main fuse is intact. |
| **HEATER RAIL** | The cutoff is on: the heaters can heat. |
| **5V / 3V3** | The internal supplies are working. |
| **VBUS** | The USB cable is connected and the host supplies power. |
| **MCU** | Klipper is running. |
| **HEATER T0–T7** | This channel is actually on. If one is lit while Klipper has the channel off, you know the MOSFET is defective. |

---

## Two protection layers in the board

1. **Klipper:** `verify_heater`, temperature limits and communication monitoring.
2. **Hardware cutoff:** two 60V MOSFETs in the heater rail supply, off by default. On a shutdown, reset or hung firmware the heater rail drops out, even if a heater MOSFET has failed short. A self-test at every startup checks that the cutoff works.

If you want an additional passive layer, choose PTC heaters (which are self-limiting) or fit a thermal fuse on the heatsink or the tool holder.

On top of that:
- a fuse per heater channel;
- an input that withstands reverse polarity and voltage spikes;
- ESD protection on every external signal connector.

---

## Specifications

### General

| | |
|---|---|
| **Microcontroller** | STM32G0B1RBT6 (Arm Cortex-M0+, 64 MHz, 128 KB flash) |
| **Firmware** | Klipper, with Katapult bootloader for updates over USB or CAN |
| **Host connection** | USB-C (USB 2.0) and/or CAN 1 Mbit/s, USB-CAN bridge supported |
| **Dimensions** | *To be determined* |
| **PCB** | 4 layers |

### Power

| | |
|---|---|
| **Input** | 24 V DC via XT60 |
| **Main fuse** | 25 A |
| **Protection** | Reverse polarity protection (heater path and logic), TVS against voltage spikes |
| **Internal rails** | 5 V (buck, 60V input), 3.3 V separate for MCU and sensors |
| **Flashing without 24 V** | Yes, the MCU runs on USB power |

### Heaters

| | |
|---|---|
| **Channels** | 8 |
| **Power** | Up to 70 W per channel at 24 V (measured at room temperature) |
| **Simultaneous** | All 8 at once from a cold start (≈ 23.6 A total) |
| **Switching** | Low-side, 40V MOSFET (4.5 mΩ), 5 V gate drive |
| **Channel fuse** | 5 A per channel |
| **Cutoff** | Hardware, Klipper-controlled, off by default, with voltage measurement for the self-test |
| **Connector** | 2-pole screw terminal, 5.08 mm |

### Thermistors

| | |
|---|---|
| **Inputs** | 8 |
| **Types** | NTC 100K (default) or PT1000, per channel via solder jumper |
| **Pull-up** | 4.7 kΩ / 2.2 kΩ, 0.1 % tolerance |
| **Protection** | RC filter, clamp diode, ESD (survives 24V on the input) |
| **Connector** | JST-XH 2-pin |

### Filament sensors

| | |
|---|---|
| **Ports** | 8, each with 2 inputs: runout and motion |
| **Supported** | D2F and other switches, Hall and optical sensors, combined runout/motion sensors |
| **Sensor supply** | 5 V (default) or 3.3 V per board, with polyfuse |
| **Inputs** | 5V tolerant, with filter and ESD protection |
| **Connector** | JST-XH 4-pin: RUNOUT · GND · VCC · MOTION |

### Other connections

| | |
|---|---|
| **LED port** | 1× WS2812, up to 8 LEDs, 5V data via level shifter, 0.75 A polyfuse (JST-XH 3-pin) |
| **CAN** | 2× Micro-Fit 3.0 2×2 (in/out), 120 Ω termination via jumper |
| **Debug** | BOOT and RESET buttons, SWD header, test points on all rails |

---

## What you need

- A **24V power supply**. Budget ≥ 600 W for the Nexus Tools Board and the Nexus Docks Board together with 70W heaters. With lighter heaters or fewer tools, less will do.
- A Klipper host (e.g. a Raspberry Pi) with Mainsail, Fluidd or a similar interface.
- Optional: a CAN adapter, or use the board itself as a USB-CAN bridge.

---

## Companion: Nexus Docks Board

The **Nexus Docks Board** takes care of the rest of the dock. It uses the same MCU, the same firmware flow and the same diagnostic approach.

- **9 fan outputs**, up to 1 A per fan and 3 A in total, no tacho
- **Fan voltage 5, 12 or 24 V**, selectable per board. Nothing is selected by default, so a 5V fan never gets 24 V by accident.
- Diagnostic LEDs for every rail, USB and MCU
- WS2812 port, USB-C and CAN
- Own 24V input via XT30, with reverse polarity protection

---

## Open source

| Part | License |
|---|---|
| Hardware | CERN-OHL-S-2.0 |
| Klipper macros and config | GPL-3.0-or-later |
| Documentation | CC-BY-SA-4.0 |

The KiCad files, the complete BOM with LCSC numbers and the production files for JLCPCB are in the repository.

---

> **Caution.** This is a hobby project. The board is not certified and not CE marked. It drives heaters: a mistake in assembly, wiring or configuration can cause a fire. Read the safety section in the README before you start. You build and use it at your own risk.
