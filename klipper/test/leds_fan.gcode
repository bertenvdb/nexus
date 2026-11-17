; LED and supply fan templates are accepted, also with a custom LED order.
; Batch mode does not run the template timer; the colour logic itself is
; tested by test_templates.py.
; SED: s/^variable_led_order_docks: .*/variable_led_order_docks: [7, 6, 5, 4, 3, 2, 1, 0]/
; REJECT: display_template
; REJECT: Error evaluating
_NEXUS_CONFIG_CHECK
_NEXUS_SETUP_DISPLAY
