; T3 disabled with the placeholder; T4..T7 must stay available.
; SED: /^#--- T3/,/^#--- T4/ s/^\([^#]\)/#\1/
; SED: s|^#\[include nexus/tools/t3.cfg\]|[include nexus/tools/t3_disabled.cfg]|
; EXPECT: Nexus: config check OK, enabled tools: T0 T1 T2 T4 T5 T6 T7
; EXPECT: T3: disabled (placeholder)
; EXPECT: T7: 0.0 / 200 C
; EXPECT: Nexus: T3 is not enabled
; EXIT: 255
_NEXUS_CONFIG_CHECK
_NEXUS_SETUP_DISPLAY
SET_GCODE_VARIABLE MACRO=_NEXUS_STATE VARIABLE=selftest VALUE="'passed'"
M104 T7 S200
NEXUS_STATUS
M104 T3 S0
M104 T3 S200
