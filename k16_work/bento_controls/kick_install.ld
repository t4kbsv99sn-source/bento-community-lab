ENTRY(kick_load_entry)
SECTIONS { . = 0x081ba200; .text : { KEEP(*(.text.kick_*)) *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }
