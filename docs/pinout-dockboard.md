# Nexus Docks Board — STM32G0B1RBT6 pinout

| | |
|---|---|
| **Version** | 0.1 (F2, for review) |
| **Date** | 2026-11-17 |
| **Sources** | As [pinout-toolboard.md](pinout-toolboard.md) |

**Principle:** every function the dock board shares with the tool board uses the **same pin**: USB, CAN, crystal, SWD/BOOT, NRST, LED data, status LED. The 8 fan outputs driven by the 74HCT541 use the 8 heater pins of the tool board. So the `mcu`, `usb_can` and `led_port` sheets are identical, and the gate-driver sheet maps one-to-one. The checks of the tool board pinout §1 apply unchanged.

| Pin | Name | I/O | Function | Net | Note |
|---|---|---|---|---|---|
| 6, 8 | VBAT, VDD/VDDA | S | Supply | `+3V3` | |
| 7 | VREF+ | S | ADC reference | `+3V3` (via 10 Ω + 1 µF) | ADC not used; tie to supply |
| 9 | VSS/VSSA | S | Ground | `GND` | |
| 10, 11 | PF0, PF1 | FT | Crystal 8 MHz | `OSC_IN`, `OSC_OUT` | Needed for CAN |
| 12 | PF2-NRST | RST | Reset button | `NRST` | |
| 27, 28 | PB0, PB1 | FT_ea | FDCAN2 RX/TX | `CAN_RX`, `CAN_TX` | Same as tool board |
| 32 | PB12 | FT_fa | Fan 8 (9th fan) | `FAN8_CTRL` | Via 74AHCT1G125, 100 kΩ pull-down. On the tool board this pin is `HEATER_EN` |
| 33 | PB13 | FT_fs | Fan 0 | `FAN0_CTRL` | 74HCT541 A1 |
| 34 | PB14 | FT_fs | Fan 1 | `FAN1_CTRL` | |
| 35 | PB15 | FT_fcs | Fan 2 | `FAN2_CTRL` | |
| 36 | PA8 | FT_fcs | Fan 3 | `FAN3_CTRL` | Dead-battery pull-down = off at reset |
| 38 | PC6 | FT_s | Fan 4 | `FAN4_CTRL` | |
| 39 | PC7 | FT_s | Fan 5 | `FAN5_CTRL` | |
| 40 | PD8 | FT_s | Fan 6 | `FAN6_CTRL` | |
| 41 | PD9 | FT_s | Fan 7 | `FAN7_CTRL` | |
| 43, 44 | PA11, PA12 | FT | USB D−/D+ | `USB_DM`, `USB_DP` | |
| 45, 46 | PA13, PA14-BOOT0 | FT | SWDIO, SWCLK/BOOT0 | `SWDIO`, `SWCLK` | |
| 57 | PB3 | FT_a | LED data | `LED_DATA` | |
| 58 | PB4 | FT_a | Status LED | `LED_MCU` | |
| all others | | | — (unused) | — | 41 spare GPIO |

Fans are numbered 0–8 (net `FAN0_N` … `FAN8_N`, CLAUDE.md §6), connectors silkscreened FAN 0–8.

## Klipper names (for F8)

| Function | Klipper pin |
|---|---|
| Fan 0–8 | `dock:PB13`, `PB14`, `PB15`, `PA8`, `PC6`, `PC7`, `PD8`, `PD9`, `PB12` |
| LED chain | `dock:PB3` |
| Status LED | `dock:PB4` |
| `make menuconfig` | Identical to the tool board |
