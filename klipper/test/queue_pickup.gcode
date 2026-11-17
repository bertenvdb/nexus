; Slicer preheat that is still queued when the tool change arrives: the
; change must wait for a slot (M109) and pick up, not abort the print.
; EXPECT: Nexus: T3 queued (3 hotends already heating from cold)
; EXPECT: Nexus: T3 waits for 1 other hotend(s) to warm up
; EXPECT: MOVE G1 X160.0 F18000
; EXPECT: MOVE G1 Y-11.0 E-8.000 F10000
; REJECT: Error evaluating
_NEXUS_CONFIG_CHECK
_NEXUS_RESTORE_TOOL
SET_GCODE_VARIABLE MACRO=_NEXUS_STATE VARIABLE=selftest VALUE="'passed'"
G28
M104 T0 S220
M104 T1 S220
M104 T2 S220
M104 T3 S220
T3
NEXUS_STATUS
