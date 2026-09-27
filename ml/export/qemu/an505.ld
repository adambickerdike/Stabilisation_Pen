/* Linker script for QEMU mps2-an505 (Cortex-M33): everything in SSRAM1 (secure alias). */
MEMORY
{
  SSRAM1 (rwx) : ORIGIN = 0x10000000, LENGTH = 4M
}
ENTRY(Reset_Handler)
SECTIONS
{
  .text : {
    KEEP(*(.vectors))
    *(.text*)
    *(.rodata*)
    . = ALIGN(4);
  } > SSRAM1
  .ARM.exidx : { *(.ARM.exidx*) } > SSRAM1
  .preinit_array : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > SSRAM1
  .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > SSRAM1
  .fini_array : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > SSRAM1
  .data : { *(.data*) . = ALIGN(4); } > SSRAM1
  .bss (NOLOAD) : { __bss_start__ = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end__ = .; } > SSRAM1
  . = ALIGN(8);
  end = .;
  _end = .;
  __end__ = .;
  __stack_top = ORIGIN(SSRAM1) + LENGTH(SSRAM1);
  __HeapLimit = __stack_top - 0x10000;
}
