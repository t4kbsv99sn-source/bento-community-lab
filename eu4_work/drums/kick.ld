ENTRY(kick_render)
SECTIONS { . = 0x080d6000; .text : { KEEP(*(.text.kick_*)) *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }
