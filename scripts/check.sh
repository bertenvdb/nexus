#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Usage: scripts/check.sh [board ...]   (default: toolboard dockboard)
# Runs ERC and DRC on both boards. Exit code != 0 if any board has violations.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/out"
if [ $# -gt 0 ]; then BOARDS=("$@"); else BOARDS=(toolboard dockboard); fi
mkdir -p "$OUT"

status=0
for b in "${BOARDS[@]}"; do
  sch="$ROOT/$b/$b.kicad_sch"
  pcb="$ROOT/$b/$b.kicad_pcb"

  echo "== $b: ERC"
  if kicad-cli sch erc --severity-all --exit-code-violations \
       -o "$OUT/$b-erc.rpt" "$sch" >/dev/null 2>&1; then
    echo "   OK"
  else
    echo "   FAIL (see out/$b-erc.rpt)"; status=1
  fi

  echo "== $b: DRC"
  if kicad-cli pcb drc --severity-all --exit-code-violations --schematic-parity \
       -o "$OUT/$b-drc.rpt" "$pcb" >/dev/null 2>&1; then
    echo "   OK"
  else
    echo "   FAIL (see out/$b-drc.rpt)"; status=1
  fi
done

exit $status
