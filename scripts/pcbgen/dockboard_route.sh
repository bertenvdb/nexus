#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Placement, planes, complete routing, pours and silkscreen of the Nexus
# Docks Board (F6 steps 1-4), from scratch. Overwrites dockboard/dockboard.kicad_pcb. About 10 minutes.
set -euo pipefail
cd "$(dirname "$0")/../.."
q() { grep -v "Debug: Adding duplicate image handler" || true; }
B=dockboard
export MAZE_WMAX=0.8                 # power tracks the router lays: <= 0.8 mm (calculations.md §2.2)
export MAZE_SKIP=/power_input/VIN_RAW # laid by dockboard_preroute.py
export MAZE_SOFT_PLANES=1            # vias may pass the In2 power planes
export MAZE_FIRST=/fan_rail/FBK_FB,/logic_power/BUCK_FB   # buck feedback first: short and direct

# 1-2. placement and planes
python3 scripts/pcbgen/dockboard_place.py 2>&1 | q
python3 scripts/pcbgen/dockboard_zones.py 2>&1 | q
# 3. high-current copper by script, then plane-net pads to their planes
python3 scripts/pcbgen/dockboard_preroute.py 2>&1 | q
STITCH_B_PLANE=1 python3 scripts/pcbgen/stitch.py $B GND +24V_INT FAN_RAIL /fan_rail/FAN_BUCK 2>&1 | q
# 4. everything else: negotiated congestion
NEG_ALL=1 NEG_ITER=${NEG_ITER:-80} NEG_PRES_MAX=20 NEG_HIST=1.0 \
    python3 scripts/pcbgen/negotiate.py $B 2>&1 | q
python3 scripts/pcbgen/cleanup.py $B 2>&1 | q
# 5. what negotiation left in conflict
MAZE_FONLY= python3 scripts/pcbgen/maze.py $B 2>&1 | q
python3 scripts/pcbgen/cleanup.py $B 2>&1 | q
# 6. finishing as done on 2026-11-20: one +5V segment 0.11 mm from U8 pin 1
#    (grid rounding next to the pad), ripped and rerouted
python3 scripts/pcbgen/rip.py $B 43.0,44.4,44.0,45.2 +5V 2>&1 | q
python3 scripts/pcbgen/cleanup.py $B 2>&1 | q
MAZE_FONLY= MAZE_NETS=+5V python3 scripts/pcbgen/maze.py $B 2>&1 | q
python3 scripts/pcbgen/cleanup.py $B 2>&1 | q
# 7. finishing (F6 step 4): GND pours on F.Cu / In2 / B.Cu, silkscreen
python3 scripts/pcbgen/pours.py $B 2>&1 | q
python3 scripts/pcbgen/dockboard_silk.py 2>&1 | q
# 8. checks
kicad-cli pcb drc --severity-all --schematic-parity -o out/drc_dock.rpt "$PWD/$B/$B.kicad_pcb" > /dev/null || true
grep -o '^\[[a-z_]*\]' out/drc_dock.rpt | sort | uniq -c | sort -rn
