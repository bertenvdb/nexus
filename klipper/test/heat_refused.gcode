; Heating is refused while the rail self-test has not passed.
; EXPECT: Nexus: heater rail is off, self-test state: pending
; EXIT: 255
_NEXUS_CONFIG_CHECK
M104 T0 S220
