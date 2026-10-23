ENTRY(lock_command)
SECTIONS {
 . = 0x080d1400;
 .text : { KEEP(*(.text.lock_command)) KEEP(*(.text.lock_sequence)) KEEP(*(.text.lock_evaluate)) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
