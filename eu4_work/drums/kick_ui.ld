ENTRY(kick_ui_before)
SECTIONS { . = 0x081bb400; .text : { KEEP(*(.text.kick_*)) KEEP(*(.text.drum_ui_step)) *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }
