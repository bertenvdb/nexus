#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Loop-gain check of the TPS54360B designs (replaces a WEBENCH run).

Model: TI SNVSB93 §7.3.15-7.3.16 (peak-current-mode power stage gmps,
transconductance error amplifier gmEA with output resistance Ro, type 2A
compensation) plus the current-mode sampling double pole at fsw/2
(Ridley). The quality factor Q of that pole depends on TI's internal slope
compensation, which is not published: it is swept from 0.5 to 1.5.

Prints crossover frequency, phase margin and gain margin for every
converter at minimum and maximum load. Targets: PM >= 45 deg,
fc <= fsw/10, GM >= 6 dB.
"""
import cmath
import math

FSW = 604e3
GMEA = 350e-6
RO = 10000 / GMEA          # EA DC gain 10,000 V/V
GMPS = 12.0
VREF = 0.8

# name, Vout, Iout range, Cout effective, ESR, R4, C5, C8
CASES = [
    ("Tool 5V", 5.0, (0.15, 1.5), 36e-6, 0.005 / 3, 6.8e3, 22e-9, 100e-12),
    ("Dock 5V", 5.0, (0.10, 1.0), 36e-6, 0.005 / 3, 6.8e3, 22e-9, 100e-12),
    ("Dock fan rail 12V", 12.0, (0.10, 3.0), 31e-6, 0.005 / 4, 12e3, 8.2e-9, 47e-12),
    ("Dock fan rail 5V", 5.0, (0.10, 3.0), 48e-6, 0.005 / 4, 12e3, 8.2e-9, 47e-12),
]


def loop(f, vout, iout, cout, esr, r4, c5, c8, q):
    s = 2j * math.pi * f
    rl = vout / iout
    zc = 1 / (1 / RO + 1 / (r4 + 1 / (s * c5)) + s * c8)
    gps = GMPS * rl * (1 + s * esr * cout) / (1 + s * rl * cout)
    wn = math.pi * FSW
    hs = 1 / (1 + s / (wn * q) + (s / wn) ** 2)
    return (VREF / vout) * GMEA * zc * gps * hs


def analyse(case, iout, q):
    name, vout, _, cout, esr, r4, c5, c8 = case
    freqs = [10 ** (1 + i / 400) for i in range(int(5.6 * 400))]
    vals = [loop(f, vout, iout, cout, esr, r4, c5, c8, q) for f in freqs]
    fc = pm = gm = None
    for f, a, b in zip(freqs[1:], vals, vals[1:]):
        if fc is None and abs(a) >= 1 > abs(b):
            fc = f
            pm = 180 + math.degrees(cmath.phase(b))
            if pm > 180:
                pm -= 360
        pa, pb = math.degrees(cmath.phase(a)), math.degrees(cmath.phase(b))
        if gm is None and pa < 0 and pb > 0 and abs(pa) > 90:  # -180 crossing
            gm = -20 * math.log10(abs(b))
    return fc, pm, gm


def main():
    print("| Converter | Load | fc | PM (Q 0.5 / 1.0 / 1.5) | GM (Q 0.5 / 1.0 / 1.5) |")
    print("|---|---|---|---|---|")
    worst = []
    for case in CASES:
        for iout in case[2]:
            res = [analyse(case, iout, q) for q in (0.5, 1.0, 1.5)]
            fc = res[1][0]
            pms = " / ".join(f"{r[1]:.0f}°" for r in res)
            gms = " / ".join("—" if r[2] is None else f"{r[2]:.0f} dB" for r in res)
            print(f"| {case[0]} | {iout:g} A | {fc / 1e3:.1f} kHz | {pms} | {gms} |")
            worst.append((min(r[1] for r in res), case[0], iout))
    w = min(worst)
    print(f"\nWorst phase margin: {w[0]:.0f}° ({w[1]}, {w[2]:g} A).")


if __name__ == "__main__":
    main()
