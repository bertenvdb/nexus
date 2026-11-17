#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run the Nexus Klipper config through Klipper in batch mode (no hardware).
#
# Needs a Klipper checkout with a Python env (cffi, greenlet, jinja2,
# markupsafe) and two MCU data dictionaries (out/klipper.dict after a
# firmware build): one for an STM32F446 main board and one for the
# STM32G0B1 (Nexus boards). See klipper/README.md, section "Tests".
#
#   KLIPPER_DIR=~/klipper PYTHON=~/klippy-env/bin/python \
#   DICT_MAIN=f446.dict DICT_NEXUS=g0b1.dict klipper/test/run_tests.sh [scenario.gcode ...]
#
# Scenario files (*.gcode) may contain:
#   ; EXPECT: text      text that must appear in the klippy log
#   ; REJECT: text      text that must NOT appear
#   ; EXIT: n           expected exit code (default 0; a G-code error gives 255)
#   ; SED: expr         sed expression applied to the test copy of nexus.cfg

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
KLIPPER_DIR="${KLIPPER_DIR:-$HOME/klipper}"
PYTHON="${PYTHON:-python3}"
: "${DICT_MAIN:?set DICT_MAIN to the main MCU klipper.dict}"
: "${DICT_NEXUS:?set DICT_NEXUS to the STM32G0B1 klipper.dict}"

scenarios=("$@")
[ ${#scenarios[@]} -eq 0 ] && scenarios=("$HERE"/*.gcode)

fail=0
for scenario in "${scenarios[@]}"; do
    scenario="$(realpath "$scenario")"
    name="$(basename "$scenario" .gcode)"
    work="$(mktemp -d)"
    cp "$HERE/printer.cfg" "$work/"
    ln -s "$HERE/../nexus" "$work/nexus"
    # Batch mode cannot emulate CAN: use the serial lines.
    sed -e 's/^canbus_uuid/#canbus_uuid/' -e 's/^#serial/serial/' \
        "$HERE/../nexus.cfg" > "$work/nexus.cfg"
    while IFS= read -r expr; do
        sed -i -e "$expr" "$work/nexus.cfg"
    done < <(sed -n 's/^; SED: //p' "$scenario")
    sed -i "s|/tmp/nexus_test_sd|$work|" "$work/printer.cfg"

    log="$work/klippy.log"
    (cd "$work" && timeout 300 "$PYTHON" "$KLIPPER_DIR/klippy/klippy.py" printer.cfg \
        -i "$scenario" -o "$work/out.serial" -d "$DICT_MAIN" \
        -d "nexus_tools=$DICT_NEXUS" -d "nexus_docks=$DICT_NEXUS") > "$log" 2>&1
    code=$?

    errors=()
    want="$(sed -n 's/^; EXIT: //p' "$scenario")"
    [ "$code" -eq "${want:-0}" ] || errors+=("exit code $code, expected ${want:-0}")
    while IFS= read -r text; do
        grep -qF -- "$text" "$log" || errors+=("missing: $text")
    done < <(sed -n 's/^; EXPECT: //p' "$scenario")
    while IFS= read -r text; do
        grep -qF -- "$text" "$log" && errors+=("unexpected: $text")
    done < <(sed -n 's/^; REJECT: //p' "$scenario")

    if [ ${#errors[@]} -eq 0 ]; then
        echo "PASS $name"
        [ -n "${KEEP:-}" ] && echo "     log: $log" || rm -rf "$work"
    else
        echo "FAIL $name (log: $log)"
        printf '     %s\n' "${errors[@]}"
        fail=1
    fi
done
exit $fail
