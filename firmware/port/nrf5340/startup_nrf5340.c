/*
 * startup_nrf5340.c - vector table and reset handler for the nRF5340
 * application core (bare metal). Status: compile-tested only; the vector
 * count and IRQ names are VERIFY against the PS / MDK. The vendor
 * SystemInit() errata workarounds (nrfx system_nrf5340_application.c) are
 * NOT reproduced here: VERIFY before running on silicon.
 */
#include <stdint.h>
#include <string.h>

#include "nrf5340_regs.h"

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
int main(void);
void Reset_Handler(void);
void Default_Handler(void);
void SystemInit(void);

#define WEAK_ALIAS __attribute__((weak, alias("Default_Handler")))
void NMI_Handler(void) WEAK_ALIAS;
void HardFault_Handler(void) WEAK_ALIAS;
void MemManage_Handler(void) WEAK_ALIAS;
void BusFault_Handler(void) WEAK_ALIAS;
void UsageFault_Handler(void) WEAK_ALIAS;
void SecureFault_Handler(void) WEAK_ALIAS;
void SVC_Handler(void) WEAK_ALIAS;
void DebugMon_Handler(void) WEAK_ALIAS;
void PendSV_Handler(void) WEAK_ALIAS;
void SysTick_Handler(void) WEAK_ALIAS;
void SPIM4_IRQHandler(void) WEAK_ALIAS;
void SAADC_IRQHandler(void) WEAK_ALIAS;
void TIMER0_IRQHandler(void) WEAK_ALIAS;
void TIMER1_IRQHandler(void) WEAK_ALIAS;
void TIMER2_IRQHandler(void) WEAK_ALIAS;
void WDT0_IRQHandler(void) WEAK_ALIAS;
void EGU0_IRQHandler(void) WEAK_ALIAS;
void PWM0_IRQHandler(void) WEAK_ALIAS;

typedef void (*vector_t)(void);

/* 16 system exceptions + NRF_IRQ_COUNT external interrupts */
__attribute__((section(".isr_vector"), used)) const vector_t g_vectors[16 + NRF_IRQ_COUNT] = {
    (vector_t)(uintptr_t)&_estack,
    Reset_Handler,
    NMI_Handler,
    HardFault_Handler,
    MemManage_Handler,
    BusFault_Handler,
    UsageFault_Handler,
    SecureFault_Handler,
    0,
    0,
    0,
    SVC_Handler,
    DebugMon_Handler,
    0,
    PendSV_Handler,
    SysTick_Handler,
    [16 + SPIM4_IRQn] = SPIM4_IRQHandler,
    [16 + SAADC_IRQn] = SAADC_IRQHandler,
    [16 + TIMER0_IRQn] = TIMER0_IRQHandler,
    [16 + TIMER1_IRQn] = TIMER1_IRQHandler,
    [16 + TIMER2_IRQn] = TIMER2_IRQHandler,
    [16 + WDT0_IRQn] = WDT0_IRQHandler,
    [16 + EGU0_IRQn] = EGU0_IRQHandler,
    [16 + PWM0_IRQn] = PWM0_IRQHandler,
};

void Default_Handler(void)
{
    /* unexpected interrupt: stop here; the watchdog resets the MCU and the
     * hardware interlock (R71 pull-down on ACT_EN_REQ) removes VMOT */
    for (;;) {
        __asm volatile("nop");
    }
}

void SystemInit(void)
{
    /* FPU: full access to CP10/CP11 before any float instruction */
    REG32(SCB_CPACR) |= (0xFu << 20);
    __asm volatile("dsb\n isb" ::: "memory");
    /* HFCLK from the 32 MHz crystal, core at 128 MHz (VERIFY: HFCLKCTRL, errata) */
    REG32(NRF_CLOCK_BASE + CLOCK_TASKS_HFCLKSTART) = 1u;
    for (uint32_t k = 0; k < 1000000u && REG32(NRF_CLOCK_BASE + CLOCK_EVENTS_HFCLKSTARTED) == 0u; k++) {
    }
    REG32(NRF_CLOCK_BASE + CLOCK_HFCLKCTRL) = 0u;
}

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    for (uint32_t *dst = &_sdata; dst < &_edata;) {
        *dst++ = *src++;
    }
    for (uint32_t *dst = &_sbss; dst < &_ebss;) {
        *dst++ = 0u;
    }
    SystemInit();
    (void)main();
    for (;;) {
    }
}
