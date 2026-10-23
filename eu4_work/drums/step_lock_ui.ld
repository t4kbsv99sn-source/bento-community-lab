ENTRY(locks_header_before)
SECTIONS { . = 0x081b7400; .text : { KEEP(*(.text.locks_*)) *(.text*) } .proj 0x081b8c00 : { KEEP(*(.proj)) } .clear 0x081b8d00 : { KEEP(*(.clear)) } .padclear 0x081b8e00 : { KEEP(*(.padclear)) } .leds 0x081b9000 : { KEEP(*(.leds)) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }
