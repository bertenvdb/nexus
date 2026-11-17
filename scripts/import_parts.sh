#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Imports symbol, footprint and 3D model from EasyEDA/LCSC into lib/nexus
# for every BOM line whose lib_source is "easyeda" (column in docs/bom-master.csv).
# Usage: scripts/import_parts.sh [C-number ...]   (default: all easyeda lines)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ $# -gt 0 ]; then
  CODES=("$@")
else
  mapfile -t CODES < <(python3 - <<'PY'
import csv
for r in csv.DictReader(open("docs/bom-master.csv")):
    if r.get("lib_source") == "easyeda" and r["lcsc"].startswith("C"):
        print(r["lcsc"])
PY
)
fi

for c in "${CODES[@]}"; do
  echo "== $c"
  easyeda2kicad --full --lcsc_id="$c" --output lib/nexus --overwrite --use-cache
  # easyeda2kicad exits 0 even when the API refuses: check the result.
  if ! grep -q "\"$c\"" lib/nexus.kicad_sym; then
    echo "import of $c failed (EasyEDA API?), stopping" >&2
    exit 1
  fi

  sleep 2
done

# Make 3D model paths relative to the KiCad project (toolboard/, dockboard/).
sed -i 's|(model "lib/nexus.3dshapes/|(model "${KIPRJMOD}/../lib/nexus.3dshapes/|' lib/nexus.pretty/*.kicad_mod
python3 "$ROOT/scripts/postprocess_lib.py"
