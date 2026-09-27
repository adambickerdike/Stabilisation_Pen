/*
 * nrf5340_app.ld - nRF5340 APPLICATION core, bare metal, secure, no TF-M.
 * Memory sizes from the nRF5340 PS as recalled: 1 MB flash at 0x00000000,
 * 512 kB RAM at 0x20000000 (VERIFY; the network core has its own memories).
 * Research build: no bootloader offset (VERIFY against the chosen MCUboot /
 * DFU layout before release).
 */
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 1024K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 512K
}

_stack_size = 0x4000;   /* 16 kB main stack (ISRs nest on it) */

ENTRY(Reset_Handler)

SECTIONS
{
  .isr_vector ORIGIN(FLASH) :
  {
    KEEP(*(.isr_vector))
  } > FLASH

  .text :
  {
    . = ALIGN(4);
    *(.text .text.*)
    *(.rodata .rodata.*)
    . = ALIGN(4);
  } > FLASH

  .ARM.exidx :
  {
    *(.ARM.exidx* .gnu.linkonce.armexidx.*)
  } > FLASH

  _sidata = LOADADDR(.data);

  .data :
  {
    . = ALIGN(4);
    _sdata = .;
    *(.data .data.*)
    *(.ramfunc .ramfunc.*)
    . = ALIGN(4);
    _edata = .;
  } > RAM AT > FLASH

  .bss (NOLOAD) :
  {
    . = ALIGN(4);
    _sbss = .;
    *(.bss .bss.*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > RAM

  .stack (NOLOAD) :
  {
    . = ALIGN(8);
    _sstack = .;
    . = . + _stack_size;
    . = ALIGN(8);
    _estack = .;
  } > RAM

  end = _ebss;
  _end = _ebss;
}
