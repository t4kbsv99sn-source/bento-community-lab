ENTRY(step_match)
SECTIONS {
 . = 0x081b6800;
 .text : { KEEP(*(.text.step_press)) KEEP(*(.text.step_touch)) KEEP(*(.text.step_match)) KEEP(*(.text.step_selected)) KEEP(*(.text.step_edit)) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
