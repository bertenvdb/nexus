; Batch mode: no thermistor rises, so the first tool must fail.
; EXPECT: Nexus: commissioning T0: heating for 20 s
; EXPECT: Nexus commissioning FAILED for T0: own thermistor +0.0 C
; EXIT: 255
_NEXUS_CONFIG_CHECK
SET_GCODE_VARIABLE MACRO=_NEXUS_STATE VARIABLE=selftest VALUE="'passed'"
NEXUS_COMMISSION
