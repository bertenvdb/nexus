#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""F2 calculations: TPS54360B buck converters and copper widths.

Prints Markdown tables that are pasted into docs/calculations.md.
Equations: TI TPS54360B datasheet SNVSB93 section 8.2.2 (eq. 25-51),
IPC-2221 for trace widths. Re-run after changing any input below.
"""
import math

E96 = [1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27,
       1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65,
       1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15,
       2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80,
       2.87, 2.94, 3.01, 3.09, 3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65,
       3.74, 3.83, 3.92, 4.02, 4.12, 4.22, 4.32, 4.42, 4.53, 4.64, 4.75,
       4.87, 4.99, 5.11, 5.23, 5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19,
       6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06,
       8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76]
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]


def nearest(value, series):
    exp = math.floor(math.log10(value))
    cands = [s * 10 ** e for e in (exp - 1, exp, exp + 1) for s in series]
    return min(cands, key=lambda c: abs(c - value))


# ---------------------------------------------------------------- inputs --
FSW = 600e3          # Hz
TON_MIN = 135e-9     # s, typical minimum on-time
L = 10e-6            # H, MWSA0603S-100MT (Isat 5.5 A, Irms 4.5 A, 67 mOhm)
L_DCR = 0.067
RDS_ON = 0.092       # Ohm, high-side switch
I_CL = 5.5           # A, switch current limit (typ)
VF = 0.7             # V, catch diode SS56C at 5 A
CJ = 300e-12         # F, diode junction capacitance (B560C-class)
VIN_MAX = 28.0       # V, steady state (24 V PSU set high + tolerance)
VIN_TRANSIENT = 48.4  # V, SMBJ30CA clamp
VIN_MIN = 18.0       # V, UVLO start
VIN_STOP = 15.0      # V, UVLO stop
VREF = 0.8
GMPS = 12.0          # A/V
GMEA = 350e-6        # A/V
I_HYS = 3.4e-6       # A, EN hysteresis current
I1 = 1.2e-6          # A, EN pull-up current
R_LS = 10e3          # Ohm, low side of FB divider

# Output capacitors: (nominal F, count, ESR Ohm, effective fraction at Vout).
# 22 uF 25 V X5R 1206: ~55 % left at 5 V, ~35 % at 12 V (typical DC bias).
CASES = [
    # name, Vout, Iout design, output caps
    ("Tool 5V (logic, LED, sensors)", 5.0, 1.5, (22e-6, 3, 0.005, 0.55)),
    ("Dock 5V (logic, LED)", 5.0, 1.0, (22e-6, 3, 0.005, 0.55)),
    ("Dock fan rail 12V", 12.0, 3.0, (22e-6, 4, 0.005, 0.35)),
    ("Dock fan rail 5V", 5.0, 3.0, (22e-6, 4, 0.005, 0.55)),
]


def buck(name, vout, iout, caps):
    c_nom, n, esr_one, frac = caps
    cout = c_nom * n * frac
    esr = esr_one / n
    d = vout / VIN_MAX
    f_skip = 1 / TON_MIN * (iout * L_DCR + vout + VF) / (
        VIN_TRANSIENT - iout * RDS_ON + VF)
    f_shift = 8 / TON_MIN * (I_CL * L_DCR + 0.1 + VF) / (
        VIN_TRANSIENT - I_CL * RDS_ON + VF)
    i_rip = vout * (VIN_MAX - vout) / (VIN_MAX * L * FSW)
    i_pk = iout + i_rip / 2
    i_rms = math.sqrt(iout ** 2 + i_rip ** 2 / 12)
    k_ind = i_rip / iout
    d_iout = iout / 2                       # 50 % load step
    c_tr = 2 * d_iout / (FSW * 0.04 * vout)  # eq. 32, 4 % deviation
    c_os = L * ((0.75 * iout) ** 2 - (0.25 * iout) ** 2) / (
        (1.04 * vout) ** 2 - vout ** 2)     # eq. 33
    v_rip = i_rip / (8 * FSW * cout) + i_rip * esr
    p_diode = (VIN_MAX - vout) * iout * VF / VIN_MAX + \
        CJ * FSW * (VIN_MAX + VF) ** 2 / 2  # eq. 37
    icin = iout * math.sqrt(vout / VIN_MIN * (VIN_MIN - vout) / VIN_MIN)
    r_hs = R_LS * (vout - VREF) / VREF
    r_hs_std = nearest(r_hs, E96)
    vout_real = VREF * (1 + r_hs_std / R_LS)
    fp = iout / (2 * math.pi * vout * cout)
    fz = 1 / (2 * math.pi * esr * cout)
    fco = min(math.sqrt(fp * fz), math.sqrt(fp * FSW / 2))
    r4 = (2 * math.pi * fco * cout / GMPS) * (vout / (VREF * GMEA))
    r4_std = nearest(r4, E96)
    c5 = 1 / (2 * math.pi * r4_std * fp)
    c8 = max(cout * esr / r4_std, 1 / (math.pi * r4_std * FSW))
    return dict(name=name, vout=vout, iout=iout, d=d, f_skip=f_skip,
                f_shift=f_shift, i_rip=i_rip, k_ind=k_ind, i_pk=i_pk,
                i_rms=i_rms, cout=cout, c_need=max(c_tr, c_os), v_rip=v_rip,
                p_diode=p_diode, icin=icin, r_hs=r_hs, r_hs_std=r_hs_std,
                vout_real=vout_real, fp=fp, fco=fco, r4=r4, r4_std=r4_std,
                c5=c5, c5_std=nearest(c5, E12), c8=c8,
                c8_std=nearest(c8, E12), n=n, c_nom=c_nom)


def ipc2221_width(i, dt, oz, external=True):
    """Trace width in mm for current i (A), temperature rise dt (K)."""
    k = 0.048 if external else 0.024
    area_mil2 = (i / (k * dt ** 0.44)) ** (1 / 0.725)
    thick_mil = 1.378 * oz
    return area_mil2 / thick_mil * 0.0254


def main():
    rt = 101756 / (FSW / 1e3) ** 1.008
    print(f"Switching frequency {FSW / 1e3:.0f} kHz: RT = {rt:.0f} kOhm "
          f"-> **{nearest(rt, E96):.0f} kOhm** (eq. 27).\n")
    r1 = (VIN_MIN - VIN_STOP) / I_HYS
    r1s = nearest(r1, E96)
    r2 = 1.2 / ((VIN_MIN - 1.2) / r1s + I1)
    r2s = nearest(r2, E96)
    print(f"UVLO start {VIN_MIN:.0f} V / stop {VIN_STOP:.0f} V: RUVLO1 = "
          f"{r1 / 1e3:.0f} k -> **{r1s / 1e3:.0f} k**, RUVLO2 = "
          f"{r2 / 1e3:.1f} k -> **{r2s / 1e3:.1f} k** (eq. 40-41).\n")

    rows = [buck(*c) for c in CASES]
    hdr = ["Quantity"] + [r["name"] for r in rows]
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))

    def line(label, fmt):
        print("| " + label + " | " + " | ".join(fmt(r) for r in rows) + " |")
    line("Vout / Iout (design)", lambda r: f"{r['vout']:.0f} V / {r['iout']:.1f} A")
    line("Duty cycle at 28 V", lambda r: f"{r['d']:.2f}")
    line("fsw limit pulse skip @48 V (eq. 25)", lambda r: f"{r['f_skip'] / 1e3:.0f} kHz")
    line("fsw limit foldback @48 V (eq. 26)", lambda r: f"{r['f_shift'] / 1e3:.0f} kHz")
    line("Inductor ripple (eq. 29)", lambda r: f"{r['i_rip']:.2f} A (K = {r['k_ind']:.2f})")
    line("Inductor peak / RMS (eq. 30-31)", lambda r: f"{r['i_pk']:.2f} / {r['i_rms']:.2f} A")
    line("Cout needed, 50 % step, 4 % (eq. 32-33)", lambda r: f"{r['c_need'] * 1e6:.1f} µF")
    line("Cout chosen (effective)", lambda r: f"{r['n']} × {r['c_nom'] * 1e6:.0f} µF 25 V ({r['cout'] * 1e6:.0f} µF)")
    line("Output ripple", lambda r: f"{r['v_rip'] * 1e3:.1f} mV")
    line("Catch diode loss (eq. 37)", lambda r: f"{r['p_diode']:.2f} W")
    line("Input ripple current @18 V (eq. 38)", lambda r: f"{r['icin']:.2f} A")
    line("RHS (RLS = 10 k, eq. 42)", lambda r: f"{r['r_hs'] / 1e3:.1f} k -> {r['r_hs_std'] / 1e3:.1f} k ({r['vout_real']:.2f} V)")
    line("Modulator pole / crossover (eq. 44-47)", lambda r: f"{r['fp'] / 1e3:.2f} / {r['fco'] / 1e3:.1f} kHz")
    line("R4 (eq. 48)", lambda r: f"{r['r4'] / 1e3:.1f} k -> {r['r4_std'] / 1e3:.1f} k")
    line("C5 (eq. 49)", lambda r: f"{r['c5'] * 1e9:.2f} nF -> {r['c5_std'] * 1e9:.1f} nF")
    line("C8 (eq. 50-51)", lambda r: f"{r['c8'] * 1e12:.1f} pF -> {r['c8_std'] * 1e12:.0f} pF")
    print()

    print("| Net | Current | ΔT | 1 oz (35 µm) | 2 oz (70 µm) |")
    print("|---|---|---|---|---|")
    for net, i, dt, ext in [
            ("Heater trunk, per outer layer (2 layers share 23.6 A)", 11.8, 20, True),
            ("Heater trunk, single outer layer", 23.6, 20, True),
            ("Heater channel (I_cold)", 2.9, 10, True),
            ("Fan rail", 3.0, 10, True),
            ("Fan channel", 1.0, 10, True),
            ("Dock input", 3.3, 10, True)]:
        print(f"| {net} | {i} A | {dt} K | {ipc2221_width(i, dt, 1, ext):.1f} mm"
              f" | {ipc2221_width(i, dt, 2, ext):.1f} mm |")


if __name__ == "__main__":
    main()
