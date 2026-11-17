; Staggered heat-up: max 3 cold hotends (all read 0 C in batch mode).
; Batch mode does not run delayed_gcode timers, so the queue tick is called
; directly.
; EXPECT: Nexus: T3 queued (3 hotends already heating from cold)
; EXPECT: T3: 0.0 / 0 C | runout: EMPTY | queued: 220 C
; EXPECT: Nexus: T5 waits for 1 other hotend(s) to warm up
; EXPECT: T5: 0.0 / 210 C | runout: EMPTY
; EXPECT: Nexus: T3 heating to 220.0 C (from queue)
; EXPECT: T3: 0.0 / 220 C | runout: EMPTY
; EXPECT: T4: 0.0 / 0 C | runout: EMPTY
_NEXUS_CONFIG_CHECK
SET_GCODE_VARIABLE MACRO=_NEXUS_STATE VARIABLE=selftest VALUE="'passed'"
M104 T0 S220
M104 T1 S220
M104 T2 S220
M104 T3 S220
NEXUS_STATUS
M109 T5 S210
NEXUS_STATUS
M104 T5 S0
M104 T0 S0
_NEXUS_HEAT_QUEUE_TICK
NEXUS_STATUS
M104 T4 S200
TURN_OFF_HEATERS
NEXUS_STATUS
