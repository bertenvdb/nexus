#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the LED colour and supply fan templates with fake temperatures.

Klipper renders display templates on a timer that does not run in batch
mode, so run_tests.sh cannot check them. Needs only jinja2.
    python3 klipper/test/test_templates.py
"""
import ast
import configparser
import sys
from pathlib import Path

import jinja2

KLIPPER = Path(__file__).resolve().parent.parent


def read_cfg(path, text=None):
    cp = configparser.RawConfigParser(strict=False,
                                      inline_comment_prefixes=('#', ';'))
    cp.read_string(text if text is not None else path.read_text())
    return cp


def user_settings():
    # Includes are not followed: only the _NEXUS_CFG section is needed.
    text = (KLIPPER / "nexus.cfg").read_text().replace("[include", "#[include")
    cp = read_cfg(None, text)
    return {k[len("variable_"):]: ast.literal_eval(v)
            for k, v in cp.items("gcode_macro _NEXUS_CFG")
            if k.startswith("variable_")}


def template(name):
    cp = read_cfg(KLIPPER / "nexus" / "leds.cfg")
    env = jinja2.Environment("{%", "%}", "{", "}")
    return env.from_string(cp.get("display_template " + name, "text"))


def printer(cfg, tools):
    p = {"gcode_macro _NEXUS_CFG": cfg}
    for t, (temp, target) in tools.items():
        p["gcode_macro _NEXUS_T%d" % t] = {"enabled": True}
        p["extruder" + (str(t) if t else "")] = {"temperature": temp,
                                                  "target": target}
    return p


def main():
    cfg = user_settings()
    led = template("_nexus_tool_led")
    fan = template("_nexus_supply_fan")
    names = {tuple(c): k for k, c in cfg["led_colors"].items()}
    failures = 0

    # (temperature, target, expected state)
    led_cases = [
        (22, 0, "cold"), (49, 0, "cold"), (40, 30, "cold"),
        (22, 150, "heating"), (120, 150, "heating"), (150, 220, "heating"),
        (30, 40, "heating"),
        (149, 150, "standby"), (151, 150, "standby"),
        (219, 220, "active"), (223, 220, "active"),
        (230, 220, "cooling"), (220, 150, "cooling"), (180, 0, "cooling"),
        (51, 0, "cooling"),
    ]
    for temp, target, want in led_cases:
        out = led.render(printer=printer(cfg, {0: (temp, target)}),
                         param_tool=0)
        rgb = tuple(round(float(x) / cfg["led_brightness"], 3)
                    for x in out.strip().split(",")[:3])
        got = names.get(rgb, rgb)
        if got != want:
            failures += 1
            print("FAIL led temp %s target %s: %s, expected %s"
                  % (temp, target, got, want))

    # A disabled or missing tool, or LED without tool: off.
    p = printer(cfg, {0: (200, 200)})
    p["gcode_macro _NEXUS_T0"]["enabled"] = False
    for params in [(p, 0), (printer(cfg, {}), 3), (printer(cfg, {}), -1)]:
        out = led.render(printer=params[0], param_tool=params[1])
        if [float(x) for x in out.strip().split(",")] != [0, 0, 0, 0]:
            failures += 1
            print("FAIL led off for tool %s: %s" % (params[1], out.strip()))

    # Supply fan: (tools, expected speed)
    speed = cfg["supply_fan_speed"]
    fan_cases = [
        ({0: (22, 0), 1: (25, 0)}, 0.0),
        ({0: (22, 0), 1: (25, 200)}, speed),
        ({0: (60, 0), 1: (25, 0)}, speed),
        ({0: (49, 0)}, 0.0),
    ]
    for tools, want in fan_cases:
        got = float(fan.render(printer=printer(cfg, tools)).strip())
        if got != want:
            failures += 1
            print("FAIL fan %s: %s, expected %s" % (tools, got, want))

    total = len(led_cases) + 3 + len(fan_cases)
    print("%d/%d template checks passed" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
