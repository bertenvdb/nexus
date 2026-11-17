; Tool changes are refused until docks_verified is True.
; EXPECT: Nexus: set variable_docks_verified: True in nexus.cfg
; EXIT: 255
_NEXUS_CONFIG_CHECK
SET_GCODE_VARIABLE MACRO=_NEXUS_STATE VARIABLE=selftest VALUE="'passed'"
SET_GCODE_VARIABLE MACRO=_NEXUS_CFG VARIABLE=docks_verified VALUE=False
G28
M104 T1 S220
T1
