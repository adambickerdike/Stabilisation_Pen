/*
 * startup_m33.c - minimal bare-metal start-up for QEMU "mps2-an505" (Arm Cortex-M33,
 * secure boot, VTOR_S = 0x10000000).  Used only to run test_host.c on an emulated
 * Cortex-M33 (ISA-level bit-exactness check and instruction counting).
 * QEMU is not cycle accurate: SysTick under -icount measures executed instructions,
 * not Cortex-M33 cycles, flash wait states or cache behaviour.
 */
#include <stdint.h>

extern uint32_t __bss_start__, __bss_end__, __stack_top;
extern int main(int argc, char **argv);
extern void initialise_monitor_handles(void);
extern void exit(int status);

void Reset_Handler(void);
static void Default_Handler(void)
{
    for (;;) {
    }
}

__attribute__((section(".vectors"), used)) const void *const g_vectors[16] = {
    (const void *)&__stack_top, (const void *)Reset_Handler, (const void *)Default_Handler,
    (const void *)Default_Handler, (const void *)Default_Handler, (const void *)Default_Handler,
    (const void *)Default_Handler, 0, 0, 0, 0, (const void *)Default_Handler, (const void *)Default_Handler, 0,
    (const void *)Default_Handler, (const void *)Default_Handler};

void Reset_Handler(void)
{
    *(volatile uint32_t *)0xE000ED88u |= (0xFu << 20); /* CPACR: enable CP10/CP11 (FPU) */
    __asm volatile("dsb\n isb" ::: "memory");
    for (uint32_t *p = &__bss_start__; p < &__bss_end__; ++p) {
        *p = 0u;
    }
    initialise_monitor_handles();
    exit(main(0, 0));
}

void _init(void) {}
void _fini(void) {}

#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)

uint32_t tcn_bench_ticks(void (*fn)(void), uint32_t reps)
{
    SYST_RVR = 0x00FFFFFFu;
    SYST_CVR = 0u;
    SYST_CSR = 5u; /* enable, processor clock, no interrupt */
    const uint32_t t0 = SYST_CVR;
    for (uint32_t i = 0; i < reps; ++i) {
        fn();
    }
    const uint32_t t1 = SYST_CVR;
    SYST_CSR = 0u;
    return (t0 - t1) & 0x00FFFFFFu;
}

/* calibration: 2 instructions (subs, bne) per iteration */
uint32_t tcn_bench_loop_ticks(uint32_t n)
{
    SYST_RVR = 0x00FFFFFFu;
    SYST_CVR = 0u;
    SYST_CSR = 5u;
    const uint32_t t0 = SYST_CVR;
    __asm volatile("1: subs %0, %0, #1\n bne 1b" : "+r"(n)::"cc");
    const uint32_t t1 = SYST_CVR;
    SYST_CSR = 0u;
    return (t0 - t1) & 0x00FFFFFFu;
}
