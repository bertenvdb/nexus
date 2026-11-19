#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Re-place only the logic area of the approved tool board placement (F5 step 3).

The routing showed that the MCU had about 1 mm between its pins and the
neighbouring blocks: no room to fan out 50 pins (2026-11-19). This takes the
approved placement (toolboard.placed.kicad_pcb) and moves only the logic
parts (5 V buck, LDOs, MCU, crystal group, SWD/buttons group, gate buffer) to
the positions of layout variant "fan" in toolboard_place.py, which keeps a
>= 3.5 mm ring around the MCU. Every other block stays where it was approved.

  scripts/pcbgen/toolboard_logic_replace.py
"""
import json
import os
import pathlib
import subprocess
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pcbgen"))
import toolboard_place as tp  # noqa: E402

LOGIC = ["U_BUCK", "L_BUCK", "D_CATCH", "D_REV", "C_BIN1", "C_BIN2", "C_BIN3",
         "C_BOUT1", "C_BOUT2", "C_BOUT3", "R_UV1", "R_UV2", "R_RT", "R_COMP",
         "C_COMP", "C_COMP2", "C_BOOT", "R_FB1", "R_FB2", "TP_5V",
         "D_OR_5V", "D_OR_VBUS", "C_L1IN", "U_LDO_MCU", "C_L1OUT", "C_L1OUT2",
         "TP_3V3M", "C_L2IN", "U_LDO_AUX", "C_L2OUT", "TP_3V3A",
         "R_VREF", "C_VREF1", "C_VREF2", "TP_VREF", "TP_AGND", "TP_VBUS",
         "U_MCU", "Y_MCU", "C_X1", "C_X2", "C_VDD1", "C_VDD2", "C_VBAT", "C_VREF3",
         "NT_AGND", "C_NRST", "R_BOOT",
         "SW_RESET", "SW_BOOT", "J_SWD", "JP_VFIL", "F_VFIL", "D_VFIL", "C_VFIL",
         "U_GATEBUF", "C_GATEBUF"] + [f"R_IN{i}" for i in range(8)]


def main():
    K = tp.refs_by_key()
    trial = ROOT / "out" / "trial" / "logic_fan.kicad_pcb"
    trial.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PCB_OUT=str(trial), TB_VARIANT="fan")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "pcbgen" / "toolboard_place.py")],
                   env=env, check=True, capture_output=True)
    new = pcbnew.LoadBoard(str(trial))
    dst = ROOT / "toolboard" / "toolboard.placed.kicad_pcb"
    b = pcbnew.LoadBoard(str(dst))
    for k in LOGIC:
        ref = K[k]
        a, n = b.FindFootprintByReference(ref), new.FindFootprintByReference(ref)
        a.SetOrientation(n.GetOrientation())
        a.SetPosition(n.GetPosition())
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(dst), b)
    print(f"moved {len(LOGIC)} logic parts in {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
