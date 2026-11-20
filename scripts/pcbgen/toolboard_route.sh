#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Complete routing of the Nexus Tools Board (F5 step 3), from the approved
# placement toolboard/toolboard.placed.kicad_pcb to toolboard/toolboard.kicad_pcb.
# Takes about 30 minutes. Overwrites toolboard/toolboard.kicad_pcb.
set -euo pipefail
cd "$(dirname "$0")/../.."
q() { grep -v "Debug: Adding duplicate image handler" || true; }

# 1. heater channels by script, GND/AGND vias to the In1 plane
python3 scripts/pcbgen/toolboard_preroute.py 2>&1 | q
python3 scripts/pcbgen/stitch.py toolboard 2>&1 | q
# 2. all signal nets: negotiated congestion; analog traces keep 1 mm from switching nets
NEG_ALL=1 NEG_ITER=80 NEG_PRES_MAX=20 NEG_HIST=1.0 NEG_AVOID_MM=1.0 \
    python3 scripts/pcbgen/negotiate.py toolboard 2>&1 | q
python3 scripts/pcbgen/cleanup.py toolboard 2>&1 | q
# 3. what negotiation left in conflict (USB pair: one via allowed, the USB-C pads alternate)
MAZE_FONLY= MAZE_AVOID_MM=0.5 python3 scripts/pcbgen/maze.py toolboard 2>&1 | q
# 4. small branches of the power nets (test points, sense, LED, LM74502 pins)
MAZE_SKIP=/power_input/VIN_RAW MAZE_NETS="+24V_IN,+24V_HEATER,/heater_cutoff/CUTOFF_SRC" \
    python3 scripts/pcbgen/maze.py toolboard 2>&1 | q
#    what is left of them carries only mA: 0.3 mm
MAZE_SKIP=/power_input/VIN_RAW MAZE_NETS="+24V_IN,+24V_HEATER,/heater_cutoff/CUTOFF_SRC" NEG_ITER=1 \
    python3 -c "
import sys; sys.argv = ['negotiate.py', 'toolboard']; sys.path.insert(0, 'scripts/pcbgen')
import maze, negotiate
maze.width_of = lambda: (lambda n: 0.3)
negotiate.main()" 2>&1 | q
# 5. finishing as done on 2026-11-20 (run of the steps above left USB_DM, VREF_A
#    and the two U1 branches open; LED_MCU's via blocked MCU pin 43)
NEG_ALL=1 NEG_ITER=40 NEG_PRES_MAX=20 NEG_HIST=1.0 MAZE_FONLY= MAZE_NETS="USB_DM,VREF_A" \
    python3 scripts/pcbgen/negotiate.py toolboard 2>&1 | q
MAZE_SKIP=/power_input/VIN_RAW MAZE_NETS="+24V_IN,/heater_cutoff/CUTOFF_SRC" NEG_ALL=1 NEG_ITER=40 \
    NEG_PRES_MAX=20 NEG_HIST=1.0 python3 -c "
import sys; sys.argv = ['negotiate.py', 'toolboard']; sys.path.insert(0, 'scripts/pcbgen')
import maze, negotiate
maze.width_of = lambda: (lambda n: 0.3)
negotiate.main()" 2>&1 | q
python3 scripts/pcbgen/rip.py toolboard 80.7,34.2,81.5,35.0 2>&1 | q
python3 scripts/pcbgen/cleanup.py toolboard 2>&1 | q
NEG_ALL=1 NEG_ITER=40 NEG_PRES_MAX=20 NEG_HIST=1.0 NEG_AVOID_MM=1.0 MAZE_FONLY= MAZE_NETS="USB_DM,LED_MCU" \
    python3 scripts/pcbgen/negotiate.py toolboard 2>&1 | q
# 6. checks
kicad-cli pcb drc --severity-all -o out/drc.rpt toolboard/toolboard.kicad_pcb > /dev/null
grep -o '^\[[a-z_]*\]' out/drc.rpt | sort | uniq -c | sort -rn
python3 scripts/pcbgen/analog_check.py toolboard/toolboard.kicad_pcb 2>&1 | q | head -12
