#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Initial placement of the Nexus Docks Board (F6 step 1, brought forward).

As small as possible, parts on the top side only, 4 layers (Berten,
2026-11-17): USB-C, CAN IN and XT30 on the left edge (1.0 mm overhang); the
vertical fan and LED connectors may sit anywhere, so the 9 fan ports form a
regular 3 x 3 grid of identical cells on the right; logic in the middle,
the three power blocks at the bottom.

Revised 2026-11-20 with the tool board lessons: the MCU stands alone with
MCU_KEEP mm free around it (its support parts are a separate block next to
it), and the diagnostic LEDs form one row along the top edge (AD-17).
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "schgen"))
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))

import dockboard as sch  # noqa: E402
from pcbgen import Pcb  # noqa: E402

import os
import pcbnew
W = float(os.environ.get("DOCK_W", "88"))
H = float(os.environ.get("DOCK_H", "62"))
HOLE = 6.1
OVERHANG = 1.0
MCU_KEEP = float(os.environ.get("DOCK_KEEP", "3.6"))   # free ring around the MCU (tool board lesson)

NETCLASSES = {
    "Default": dict(track=0.2),
    "POWER_IN": dict(track=1.6, via=0.8, drill=0.4),   # calculations.md §2.2
    "FAN_CH": dict(track=0.8),
    "POWER_LOGIC": dict(track=0.5),
    "SUPPLY_3V3": dict(track=0.3),
    "USB": dict(track=0.2, dp_w=0.2, dp_g=0.15),
    "CAN": dict(track=0.2, dp_w=0.2, dp_g=0.2),
}
NETCLASS_PATTERNS = [
    ("POWER_IN", "+24V_IN"), ("POWER_IN", "+24V_INT"), ("POWER_IN", "/power_input/VIN_RAW"),
    ("POWER_IN", "FAN_RAIL"), ("POWER_IN", "/fan_rail/FAN_BUCK"),
    ("FAN_CH", "/fans/FAN*_N"), ("FAN_CH", "FAN*_N"),
    ("POWER_LOGIC", "+5V"), ("POWER_LOGIC", "/logic_power/*"), ("POWER_LOGIC", "/fan_rail/FBK_SW"),
    ("SUPPLY_3V3", "+3V3"), ("USB", "USB_D*"), ("CAN", "CAN*"),
]


def refs_by_key():
    b = sch.build()
    b.annotate()
    return {p.key: p.ref for s in b.sheets for p in s.parts}


# targets (board mm): MCU centre + rotation, block centres; override with
# DOCK_NEAR='{"mcu": [x, y, rot], "can": [x, y], ...}'
TARGETS = dict(mcu=(30, 22, 0), swd=(62, 6), gatebuf=(48, 26), can=(40, 6), canesd=(12, 24))


def main():
    import json
    T = dict(TARGETS, **json.loads(os.environ.get("DOCK_NEAR", "{}")))
    K = refs_by_key()
    r = lambda *keys: [K[k] for k in keys]
    pcb = Pcb("dockboard", ROOT / "scripts" / "pcbgen" / "template_4layer.kicad_pcb", layers=4)
    tb = pcb.board.GetTitleBlock()
    tb.SetTitle("Nexus Docks Board")
    pcb.outline(W, H)
    for i, (x, y) in enumerate([(HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)]):
        pcb.hole(f"H{i + 1}", x, y)

    # ---- left edge: USB-C, CAN IN, XT30 (1.0 mm overhang, as the tool board)
    # stacked between the corner-hole keep-outs (hole courtyard + 0.3 mm),
    # remaining space shared equally
    stack = [("J_USB", 270), ("J_CAN_IN", 90), ("J_XT30", 90)]
    spans = []
    for key, rot in stack:
        fp = pcb.edge(K[key], "left", 0.0, OVERHANG, rot=rot)
        b0 = pcb.crt_box(fp)
        spans.append((b0[1], b0[3]))              # y extent relative to `along` = 0
    top, bottom = HOLE + 4.0, H - HOLE - 4.0
    total = sum(s1 - s0 for s0, s1 in spans)
    g = (bottom - top - total) / (len(stack) + 1)
    if g < 0.3:
        raise RuntimeError(f"left edge too short: need {total + 1.2 + 2 * (HOLE + 4.0):.1f} mm")
    y = top + g
    for (key, rot), (s0, s1) in zip(stack, spans):
        pcb.edge(K[key], "left", y - s0, OVERHANG, rot=rot)
        y += (s1 - s0) + g
    obstacles = [pcb.crt_box(pcb.fps[K[k]]) for k in ("J_USB", "J_CAN_IN", "J_XT30")]
    obstacles += [(x - 4.0, y - 4.0, x + 4.0, y + 4.0) for x, y in
                  [(HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)]]

    # ---- diagnostic LEDs in one row along the top edge, between the corner holes (AD-17)
    leds = [("D_L24VIN", "R_L24VIN"), ("D_LFRAIL", "R_LFRAIL"), ("D_L5V", "R_L5V"),
            ("D_L3V3", "R_L3V3"), ("D_LVBUS", "R_LVBUS"), ("D_LMCU", "R_LMCU")]
    only = os.environ.get("DOCK_LEDS")          # trial: e.g. "24VIN,FRAIL,5V,MCU"
    if only:
        leds = [l for l in leds if l[0][3:] in only.split(",")]
    x = HOLE + 4.6
    for d, rr in leds:
        pcb.place(K[d], x + 1.0, 1.2, 0)
        db = pcb.crt_box(pcb.fps[K[d]])
        pcb.place(K[rr], x + 1.0, 3.2, 0)
        rb = pcb.crt_box(pcb.fps[K[rr]])
        pcb.place(K[rr], x + 1.0, 3.2 + (db[3] + 0.02 - rb[1]), 0)    # right below its LED
        obstacles += [db, pcb.crt_box(pcb.fps[K[rr]])]
        x += 4.4

    # ---- MCU at a fixed spot with MCU_KEEP free around it; crystal and
    # decoupling packed right outside that ring, on the side of the OSC pins
    mx, my, mrot = T["mcu"]
    pcb.place(K["U_MCU"], mx, my, mrot)
    c = pcb.crt_box(pcb.fps[K["U_MCU"]])
    keep = (c[0] - MCU_KEEP, c[1] - MCU_KEEP, c[2] + MCU_KEEP, c[3] + MCU_KEEP)
    osc = [p for p in pcb.fps[K["U_MCU"]].Pads() if "OSC" in p.GetNetname()]
    ox = sum(pcbnew.ToMM(p.GetPosition().x) for p in osc) / len(osc) - pcb.ox
    oy = sum(pcbnew.ToMM(p.GetPosition().y) for p in osc) / len(osc) - pcb.oy
    D = T.get("xtal_depth", 7.0)
    dy = T.get("xtal_dy", -3.0)       # shifted up: room for the CAN ESD diode next to J4
    if abs(ox - mx) > abs(oy - my):
        reg = ((keep[2], oy - 7 + dy, keep[2] + D, oy + 7 + dy) if ox > mx
               else (keep[0] - D, oy - 7 + dy, keep[0], oy + 7 + dy))
    else:
        reg = (ox - 7, keep[3], ox + 7, keep[3] + D) if oy > my else (ox - 7, keep[1] - D, ox + 7, keep[1])
    xtal = r("Y_MCU", "C_X1", "C_X2", "C_VDD1", "C_VDD2", "C_VBAT", "C_VREF1", "C_VREF3", "R_VREF",
             "C_NRST", "R_BOOT")
    pcb._pack_obstacles(xtal, reg, list(obstacles), 0.3)
    xb = [pcb.crt_box(pcb.fps[k]) for k in xtal]
    obstacles += [keep, (min(b_[0] for b_ in xb), min(b_[1] for b_ in xb),
                         max(b_[2] for b_ in xb), max(b_[3] for b_ in xb))]

    # ---- fan ports: one fixed cell repeated in a regular 3 x 3 grid against
    # the right edge, centred between the corner holes; FAN0..FAN8 in reading
    # order, all connectors the same way round (Berten: "netjes", 2026-11-20).
    # Cell: connector on top; below it the MOSFET under pin 1 (drain facing
    # the connector), its gate pull-down next to the gate pin and the flyback
    # diode under pin 2 (FAN_RAIL). The 22R gate series resistors sit at the
    # driver (U_GATEBUF block): series damping belongs at the source end.
    def put(ref, rot, x0, y0, pin_up=None):
        fp = pcb.place(ref, 0, 0, rot)
        if pin_up:                       # rotate until that pad is on top
            for rr in (rot, rot + 90, rot + 180, rot + 270):
                fp = pcb.place(ref, 0, 0, rr % 360)
                pads = {p.GetNumber(): p.GetPosition().y for p in fp.Pads()}
                if pads[pin_up] == min(pads.values()) and len(set(pads.values())) > 1:
                    rot = rr % 360
                    break
        bx = pcb.crt_box(fp)
        pcb.place(ref, x0 - bx[0], y0 - bx[1], rot)
        return pcb.crt_box(pcb.fps[ref])

    CG, FAN_GAP = 0.3, float(os.environ.get("DOCK_FANGAP", "1.0"))
    def fan_cell(i, x0, y0):
        j = put(K[f"J_FAN{i}"], 0, x0, y0)
        q = put(K[f"Q_F{i}"], 0, x0, j[3] + CG)
        r2 = put(K[f"R_FGPD{i}"], 90, q[2] + CG, j[3] + CG)
        d = put(K[f"D_FFB{i}"], 90, r2[2] + CG, j[3] + CG, pin_up="1")
        bs = [j, d, q, r2]
        return (min(b_[0] for b_ in bs), min(b_[1] for b_ in bs),
                max(b_[2] for b_ in bs), max(b_[3] for b_ in bs))
    c0 = fan_cell(0, 0, 0)
    cw, ch = c0[2] - c0[0], c0[3] - c0[1]
    gx1 = W - 0.6
    gx0 = gx1 - 3 * cw - 2 * FAN_GAP
    gy0 = (HOLE + 4.0 + H - HOLE - 4.0) / 2 - (3 * ch + 2 * FAN_GAP) / 2
    for i in range(9):
        fan_cell(i, gx0 + (i % 3) * (cw + FAN_GAP), gy0 + (i // 3) * (ch + FAN_GAP))
    obstacles.append((gx0, gy0, gx1, gy0 + 3 * ch + 2 * FAN_GAP))
    print(f"fan grid: cell {cw:.2f} x {ch:.2f} mm, grid x {gx0:.1f}..{gx1:.1f}, "
          f"y {gy0:.1f}..{gy0 + 3 * ch + 2 * FAN_GAP:.1f}")

    # ---- functional blocks, each packed compactly, then packed on the board
    B = pcb.block

    def near(blk, x, y):
        blk["near"] = (x, y)
        return blk
    # targets: next to their connector / their neighbours (routing)
    blocks = [
        near(B(r("SW_RESET", "SW_BOOT", "J_SWD", "TP_3V3", "TP_5V")), *T["swd"]),
        near(B(r("U_GATEBUF", "U_GATE8", "C_GATEBUF", "C_GATE8") + [K[f"R_FIN{i}"] for i in range(9)]
                 + [K[f"R_FG{i}"] for i in range(9)]),
             *T["gatebuf"]),
        near(B(r("U_USBESD", "R_CC1", "R_CC2", "R_SHIELD", "C_SHIELD", "TP_VBUS")), 15, 13),
        near(B(r("U_CAN", "C_CANVCC", "C_CANVIO", "R_TERM", "J_TERM", "TP_CANH",
                 "TP_CANL")), *T["can"]),
        # CAN ESD right behind the CAN connector, not at the transceiver
        dict(near(B(r("D_CANESD")), *T["canesd"]), prio=1),
        # power input first, right next to the XT30: the unfused VIN_RAW
        # stays short and does not run under the 5 V buck
        dict(near(B(r("F_IN", "D_TVS", "U_RPP", "Q_RPP", "C_BULK", "C_VCAP", "C_VS", "C_INT1",
                 "C_INT2", "TP_24VINT", "TP_GND")), 20, 46), prio=1),
        near(B(r("U_BUCK", "L_BUCK", "D_CATCH", "C_BIN1", "C_BIN2", "C_BIN3", "C_BOUT1",
                 "C_BOUT2", "C_BOUT3", "R_UV1", "R_UV2", "R_RT", "R_COMP", "C_COMP", "C_COMP2",
                 "C_BOOT", "R_FB1", "R_FB2", "D_OR_5V", "D_OR_VBUS", "C_L1IN", "U_LDO",
                 "C_L1OUT", "C_L1OUT2")), 32, 50),
        near(B(r("U_FBUCK", "L_FBUCK", "D_FCATCH", "C_FIN1", "C_FIN2", "C_FIN3", "C_FOUT1",
                 "C_FOUT2", "C_FOUT3", "C_FOUT4", "R_FUV1", "R_FUV2", "R_FRT", "R_FCOMP",
                 "C_FCOMP", "C_FCOMP2", "C_FBOOT", "R_FFB_A", "R_FFB_B", "R_FFB_C",
                 "JP_FVSEL", "JP_FRAIL", "C_FRAIL", "TP_FRAIL")), 50, 50),
        near(B(r("J_LED", "U_LEDBUF", "C_LEDBUF", "R_LEDPD", "R_LEDSER", "F_LED", "C_LED",
                 "D_LED5V", "D_LEDDIN")), W - 14, H - 10),
    ]
    pcb.place_blocks(blocks, (0.6, 0.6, W - 0.6, H - 0.6), obstacles, gap=0.6)

    left = pcb.unplaced()
    if left:
        print("UNPLACED:", left)
    out = pcb.save(NETCLASSES, NETCLASS_PATTERNS)
    print(f"saved {out.relative_to(ROOT)}: {len(pcb.placed)} footprints")


if __name__ == "__main__":
    main()
