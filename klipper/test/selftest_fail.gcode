; Batch mode reads 0 V: the "off" check passes, the "on" check must fail,
; switch the cutoff off and shut Klipper down.
; EXPECT: self-test FAILED: rail is 0.0 V with the cutoff on
; EXPECT: Nexus heater rail self-test failed
; EXIT: 255
_NEXUS_SELFTEST_START
