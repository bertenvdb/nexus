# Nexus Tools Board — STM32G0B1RBT6 pinout

| | |
|---|---|
| **Version** | 1.0 (approved 2026-11-17) |
| **Date** | 2026-11-17 |
| **Sources** | ST DS13560 Rev 3 (Figure 6, Table 12), Klipper `src/stm32/Kconfig` + `fdcan.c` + `stm32g0.c` (commit 29d4ec2, 2026-11-10) |

The STM32G0B1**RBT6** is the "GP" LQFP64 variant (`_RxT`): pin 40/41 are PD8/PD9 (on the "N" variant they are VSS/VDDIO2).

---

## 1. Mandatory checks (work plan F2.1)

| Check | Result |
|---|---|
| VREF+ separate pin? | **Yes, pin 7.** Feed it from the filtered VREF_A (design part 1 §6.4), the same node as the thermistor pull-ups (ratiometric). VDD/VDDA (8) and VSS/VSSA (9) are shared pins on LQFP64. Open item 9 closed. |
| 9 ADC channels on analog pins not clashing with USB, SWD, FDCAN, crystal | **PA0–PA7 (ADC_IN0–7) + PC4 (ADC_IN17).** None of them carries USB (PA11/PA12), SWD (PA13/PA14), FDCAN (PB0/PB1) or the crystal (PF0/PF1). |
| 16 filament inputs on FT pins **without** analog function | All 16 are `FT`, `FT_f`, `FT_s`, `FT_c` or `FT_d`: no `_a` suffix, so 5V-tolerant as digital input. |
| FDCAN and USB pins supported by Klipper | USB **PA11/PA12** (`STM32_USB_PA11_PA12`). CAN **PB0/PB1** = FDCAN2 AF3 (`STM32_CANBUS_PB0_PB1`), visible in the normal menu **and** as the CAN side of the USB-to-CAN bridge (`STM32_USBCANBUS_PA11_PA12` + `CMENU_CANBUS_PB0_PB1`) without "low-level options". Same pair as BTT's G0B1 toolboards, so Katapult and community guides match. |
| Layout-friendly arrangement | Filament inputs on the top side (pins 47–64, 1–2), heater outputs on the right side (33–41), ADC on the bottom side (17–25). The MCU can be rotated in F5; the grouping per side stays. |

**USB-PD dead-battery pull-downs.** PA8, PB15, PD0 and PD2 carry UCPD CC functions; on the G0B1 their Rd pull-downs (≈ 5.1 kΩ) are active from reset until firmware sets `UCPDx_STROBE`. Klipper does that at startup (`stm32g0.c` line 167). Consequence: during reset and in the bootloader, PA8 (heater T3) is pulled low (= off, safe) and filament inputs PD0/PD2 read low (= "filament present"). Harmless.

**PC13–PC15** (RTC domain, weak drive) are left unused.

---

## 2. Pin table

`I/O` column from DS13560 Table 12: `_a` = analog function, `_f` = Fm+ capable, `_s`/`_c`/`_d` = see datasheet; `TT` = 3.6 V tolerant only.

| Pin | Name | I/O | Function | Net | Rationale |
|---|---|---|---|---|---|
| 1 | PC11 | FT | Filament T0 MOTION | `FIL_MOTION_T0` | Top-left, next to T0 connector |
| 2 | PC12 | FT | Filament T0 RUNOUT | `FIL_RUNOUT_T0` | |
| 3 | PC13 | FT | — (unused) | — | RTC domain |
| 4 | PC14-OSC32_IN | FT | — (unused) | — | No 32 kHz crystal |
| 5 | PC15-OSC32_OUT | FT | — (unused) | — | |
| 6 | VBAT | S | Supply | `+3V3_MCU` | No backup battery |
| 7 | VREF+ | S | ADC reference | `VREF_A` | Filtered 3V3 (ferrite/10 Ω + 1 µF + 100 nF) |
| 8 | VDD/VDDA | S | Supply | `+3V3_MCU` | 100 nF + 4.7 µF |
| 9 | VSS/VSSA | S | Ground | `GND` | AGND star point next to this pin |
| 10 | PF0-OSC_IN | FT | Crystal | `OSC_IN` | 8 MHz |
| 11 | PF1-OSC_OUT | FT | Crystal | `OSC_OUT` | |
| 12 | PF2-NRST | RST | Reset button | `NRST` | 100 nF to GND |
| 13 | PC0 | FT_a | — (spare) | — | |
| 14 | PC1 | FT_a | — (spare) | — | |
| 15 | PC2 | FT | — (spare) | — | |
| 16 | PC3 | FT | — (spare) | — | |
| 17 | PA0 | FT_a | ADC_IN0 thermistor T0 | `THERM_T0` | ADC group on one side |
| 18 | PA1 | FT_ea | ADC_IN1 thermistor T1 | `THERM_T1` | |
| 19 | PA2 | FT_a | ADC_IN2 thermistor T2 | `THERM_T2` | |
| 20 | PA3 | FT_ea | ADC_IN3 thermistor T3 | `THERM_T3` | |
| 21 | PA4 | TT_a | ADC_IN4 thermistor T4 | `THERM_T4` | TT: input clamped by BAT54S to VREF_A |
| 22 | PA5 | TT_ea | ADC_IN5 thermistor T5 | `THERM_T5` | idem |
| 23 | PA6 | FT_ea | ADC_IN6 thermistor T6 | `THERM_T6` | |
| 24 | PA7 | FT_a | ADC_IN7 thermistor T7 | `THERM_T7` | |
| 25 | PC4 | FT_a | ADC_IN17 heater rail sense | `RAIL_SENSE` | AD-13 |
| 26 | PC5 | FT_a | — (spare) | — | |
| 27 | PB0 | FT_ea | FDCAN2_RX (AF3) | `CAN_RX` | Klipper `PB0/PB1` |
| 28 | PB1 | FT_ea | FDCAN2_TX (AF3) | `CAN_TX` | |
| 29 | PB2 | FT_ea | — (spare) | — | |
| 30 | PB10 | FT_fa | — (spare) | — | |
| 31 | PB11 | FT_fa | — (spare) | — | |
| 32 | PB12 | FT_fa | Heater cutoff enable | `HEATER_EN` | 100 kΩ pull-down at LM74502 EN |
| 33 | PB13 | FT_fs | Heater T0 | `HEATER_T0_CTRL` | To 74HCT541 A1 |
| 34 | PB14 | FT_fs | Heater T1 | `HEATER_T1_CTRL` | |
| 35 | PB15 | FT_fcs | Heater T2 | `HEATER_T2_CTRL` | |
| 36 | PA8 | FT_fcs | Heater T3 | `HEATER_T3_CTRL` | Dead-battery pull-down = off at reset |
| 37 | PA9 | FT_fds | — (spare) | — | |
| 38 | PC6 | FT_s | Heater T4 | `HEATER_T4_CTRL` | |
| 39 | PC7 | FT_s | Heater T5 | `HEATER_T5_CTRL` | |
| 40 | PD8 | FT_s | Heater T6 | `HEATER_T6_CTRL` | |
| 41 | PD9 | FT_s | Heater T7 | `HEATER_T7_CTRL` | |
| 42 | PA10 | FT_fds | — (spare) | — | |
| 43 | PA11 | FT | USB D− | `USB_DM` | |
| 44 | PA12 | FT | USB D+ | `USB_DP` | |
| 45 | PA13 | FT_es | SWDIO | `SWDIO` | |
| 46 | PA14-BOOT0 | FT | SWCLK / BOOT0 | `SWCLK` | BOOT button with pull-down (CLAUDE.md §7.2) |
| 47 | PA15 | FT_s | Filament T7 MOTION | `FIL_MOTION_T7` | |
| 48 | PC8 | FT_s | Filament T7 RUNOUT | `FIL_RUNOUT_T7` | |
| 49 | PC9 | FT_s | Filament T6 MOTION | `FIL_MOTION_T6` | |
| 50 | PD0 | FT_cs | Filament T6 RUNOUT | `FIL_RUNOUT_T6` | Dead-battery pull-down until Klipper starts |
| 51 | PD1 | FT_ds | Filament T5 MOTION | `FIL_MOTION_T5` | |
| 52 | PD2 | FT_cs | Filament T5 RUNOUT | `FIL_RUNOUT_T5` | idem |
| 53 | PD3 | FT_ds | Filament T4 MOTION | `FIL_MOTION_T4` | |
| 54 | PD4 | FT_s | Filament T4 RUNOUT | `FIL_RUNOUT_T4` | |
| 55 | PD5 | FT | Filament T3 MOTION | `FIL_MOTION_T3` | |
| 56 | PD6 | FT | Filament T3 RUNOUT | `FIL_RUNOUT_T3` | |
| 57 | PB3 | FT_a | LED data | `LED_DATA` | To 74AHCT1G125; 3.3 V output only, so `_a` is fine |
| 58 | PB4 | FT_a | Status LED | `LED_MCU` | |
| 59 | PB5 | FT | Filament T2 MOTION | `FIL_MOTION_T2` | |
| 60 | PB6 | FT_fa | — (spare) | — | |
| 61 | PB7 | FT_fa | — (spare) | — | |
| 62 | PB8 | FT_f | Filament T2 RUNOUT | `FIL_RUNOUT_T2` | |
| 63 | PB9 | FT_f | Filament T1 MOTION | `FIL_MOTION_T1` | |
| 64 | PC10 | FT | Filament T1 RUNOUT | `FIL_RUNOUT_T1` | |

**Used:** 44 of 64 pins (16 filament, 8 heater, 9 ADC, cutoff, LED, status, USB 2, CAN 2, SWD 2, crystal 2, NRST, VREF+, VDD, VSS, VBAT). **Spare:** 13 GPIO (PC0–PC3, PC5, PB2, PB6, PB7, PB10, PB11, PA9, PA10, PC13). Two of them (PB6, PB7) could go to test pads for debugging; no connector is planned.

---

## 3. Klipper names (for F8)

| Function | Klipper pin |
|---|---|
| Heater T0–T7 | `toolboard:PB13`, `PB14`, `PB15`, `PA8`, `PC6`, `PC7`, `PD8`, `PD9` |
| Thermistor T0–T7 | `toolboard:PA0` … `PA7` |
| Rail sense | `toolboard:PC4` |
| Cutoff | `toolboard:PB12` |
| Filament T*n* runout / motion | see table (external pull-up, so no `^`) |
| LED chain | `toolboard:PB3` |
| Status LED | `toolboard:PB4` |
| `make menuconfig` | STM32G0B1, 8 MHz crystal, 8 KiB bootloader (Katapult), USB on PA11/PA12 **or** CAN on PB0/PB1 **or** USB-to-CAN bridge (USB PA11/PA12, CAN PB0/PB1), 1 Mbit/s |
