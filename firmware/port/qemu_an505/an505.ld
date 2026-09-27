/*
 * an505.ld - unit-test image for QEMU `-M mps2-an505` (Arm AN505 FPGA image:
 * Cortex-M33 + SSE-200), secure state. TEST INFRASTRUCTURE, not firmware.
 * Memory map as emulated by QEMU hw/arm/mps2-tz.c: 4 MB SSRAM1 at
 * 0x10000000 (secure alias; the reset vector table is read from here) and
 * 4 MB SSRAM2/3 at 0x38000000 (secure alias). The golden-vector arena
 * (1.6 MB) and the system-test state live in .bss; newlib's heap (printf)
 * grows from `end` towards the stack.
 */
MEMORY
{
  CODE (rx)  : ORIGIN = 0x10000000, LENGTH = 4M
  RAM  (rwx) : ORIGIN = 0x38000000, LENGTH = 4M
}

_stack_size = 0x10000;   /* 64 kB main stack */

ENTRY(Reset_Handler)

SECTIONS
{
  .isr_vector ORIGIN(CODE) :
  {
    KEEP(*(.isr_vector))
  } > CODE

  .text :
  {
    . = ALIGN(4);
    *(.text .text.*)
    *(.rodata .rodata.*)
    KEEP(*(.init))
    KEEP(*(.fini))
    . = ALIGN(4);
  } > CODE

  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } > CODE
  .ARM.exidx :
  {
    __exidx_start = .;
    *(.ARM.exidx* .gnu.linkonce.armexidx.*)
    __exidx_end = .;
  } > CODE

  .preinit_array : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > CODE
  .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > CODE
  .fini_array : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > CODE

  _sidata = LOADADDR(.data);

  .data :
  {
    . = ALIGN(4);
    _sdata = .;
    *(.data .data.*)
    . = ALIGN(4);
    _edata = .;
  } > RAM AT > CODE

  .bss (NOLOAD) :
  {
    . = ALIGN(4);
    _sbss = .;
    __bss_start__ = .;
    *(.bss .bss.*)
    *(COMMON)
    . = ALIGN(8);
    _ebss = .;
    __bss_end__ = .;
  } > RAM

  end = ALIGN(8);
  _end = end;
  __end__ = end;

  _estack = ORIGIN(RAM) + LENGTH(RAM);
  _sstack = _estack - _stack_size;
  ASSERT(_ebss + 0x40000 <= _sstack, "an505.ld: less than 256 kB left for the heap")
}
