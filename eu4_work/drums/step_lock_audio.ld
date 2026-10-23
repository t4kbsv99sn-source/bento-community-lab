ENTRY(edited_evaluate)
SECTIONS { . = 0x080d3400; .text : { KEEP(*(.entry)) KEEP(*(.text.lock_*)) KEEP(*(.text.sends_*)) *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }
