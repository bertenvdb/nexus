; Runout on a parked tool (defer and pause), motion sensor only on the
; mounted tool.
; SED: s|^#\[include nexus/filament/t1_motion.cfg\]|[include nexus/filament/t1_motion.cfg]|
; SED: s|^#\[include nexus/filament/t2_motion.cfg\]|[include nexus/filament/t2_motion.cfg]|
; EXPECT: T1: 0.0 / 220 C | runout: EMPTY | motion: enabled
; EXPECT: T2: 0.0 / 0 C | runout: EMPTY | motion: disabled
; EXPECT: the print pauses when T2 is picked up
; EXPECT: T2: 0.0 / 0 C | runout: EMPTY | motion: disabled | marked empty
; EXPECT: Nexus: filament detected on T2
; EXPECT: Nexus: filament runout on parked T3, pausing
; EXPECT: Nexus: filament motion sensor triggered on T1 (mounted tool), pausing
; REJECT: Error evaluating
_NEXUS_CONFIG_CHECK
_NEXUS_RESTORE_TOOL
SET_GCODE_VARIABLE MACRO=_NEXUS_STATE VARIABLE=selftest VALUE="'passed'"
G28
M104 T1 S220
T1
NEXUS_STATUS
_NEXUS_RUNOUT TOOL=2 SENSOR=runout
NEXUS_STATUS
_NEXUS_INSERT TOOL=2
SET_GCODE_VARIABLE MACRO=_NEXUS_CFG VARIABLE=runout_parked VALUE="'pause'"
_NEXUS_RUNOUT TOOL=3 SENSOR=runout
RESUME
_NEXUS_RUNOUT TOOL=1 SENSOR=motion
