; Startup sequence without the self-test: config check, LEDs, fan, status.
; EXPECT: Nexus: config check OK, enabled tools: T0 T1 T2 T3 T4 T5 T6 T7
; EXPECT: no tool mounted (saved state)
; EXPECT: mounted: none | rail self-test: pending
; REJECT: config error
; REJECT: Error evaluating
_NEXUS_SETUP_DISPLAY
_NEXUS_CONFIG_CHECK
_NEXUS_RESTORE_TOOL
NEXUS_STATUS
