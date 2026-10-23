ENTRY(controls_dispatch)
SECTIONS {
 . = 0x081b4100;
 .text : { *(.text.controls_dispatch) *(.text*) *(.rodata*) }
 .mixer 0x081b5000 : { KEEP(*(.mixer)) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
