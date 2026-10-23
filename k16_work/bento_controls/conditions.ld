ENTRY(condition_decide)
SECTIONS {
 . = 0x080d2400;
 .text : { KEEP(*(.text.condition_loop)) KEEP(*(.text.condition_decide)) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
