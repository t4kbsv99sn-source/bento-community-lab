/* Emulator-only link address, deliberately not a Bento installation layout. */
SECTIONS {
  . = 0x01000000;
  .text : { *(.text*) *(.rodata*) }
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }
}
