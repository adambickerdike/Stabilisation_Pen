/*
 * nrf5340_regs.h - minimal register map of the nRF5340 APPLICATION core used
 * by the Rev A port. Written from memory of the nRF5340 Product
 * Specification; NOT checked against the document or nrfx headers.
 * EVERY address, offset, bit position and IRQ number below is VERIFY.
 * (Production code should use the vendor MDK: nrf5340_application.h.)
 * The secure (0x5xxx_xxxx) aliases are used: the port runs in secure mode
 * without TF-M.
 */
#ifndef PEN_NRF5340_REGS_H
#define PEN_NRF5340_REGS_H

#include <stdint.h>

#define REG32(addr) (*(volatile uint32_t *)(uintptr_t)(addr))

/* ---- peripheral base addresses (secure), VERIFY PS "Memory map" ---- */
#define NRF_CLOCK_BASE 0x50005000u   /* CLOCK, POWER, RESET share peripheral ID 5 (VERIFY) */
#define NRF_SPIM2_BASE 0x5000B000u   /* SPIB: IMU, optional ADS1220 (VERIFY instance) */
#define NRF_SPIM4_BASE 0x5000A000u   /* high-speed SPIM: Hall + optics */
#define NRF_SAADC_BASE 0x5000E000u
#define NRF_TIMER0_BASE 0x5000F000u  /* free-running 1 MHz time base */
#define NRF_TIMER1_BASE 0x50010000u  /* SAADC trigger phase inside the PWM period */
#define NRF_TIMER2_BASE 0x50011000u  /* counts PWM periods -> 2 kHz tick */
#define NRF_DPPIC_BASE 0x50017000u
#define NRF_WDT0_BASE 0x50018000u
#define NRF_EGU0_BASE 0x5001B000u    /* software interrupt for the 2 kHz stage task */
#define NRF_PWM0_BASE 0x50021000u
#define NRF_P0_BASE 0x50842500u
#define NRF_P1_BASE 0x50842800u

/* ---- IRQ numbers = peripheral ID (VERIFY) ---- */
#define SPIM4_IRQn 10
#define SAADC_IRQn 14
#define TIMER0_IRQn 15
#define TIMER1_IRQn 16
#define TIMER2_IRQn 17
#define WDT0_IRQn 24
#define EGU0_IRQn 27
#define PWM0_IRQn 33
#define NRF_IRQ_COUNT 69            /* up to CRYPTOCELL (ID 68), VERIFY */

/* ---- common task/event layout (nRF53: SUBSCRIBE = task + 0x80, PUBLISH = event + 0x80) ---- */
#define DPPI_EN (1u << 31)

/* CLOCK (VERIFY) */
#define CLOCK_TASKS_HFCLKSTART 0x000u
#define CLOCK_EVENTS_HFCLKSTARTED 0x100u
#define CLOCK_HFCLKCTRL 0x558u       /* 0 = 128 MHz (Div1), 1 = 64 MHz (Div2) */
#define RESET_RESETREAS 0x400u
#define RESETREAS_DOG0 (1u << 1)
#define RESETREAS_DOG1 (1u << 25)

/* GPIO (VERIFY) */
#define GPIO_OUTSET 0x008u
#define GPIO_OUTCLR 0x00Cu
#define GPIO_IN 0x010u
#define GPIO_DIRSET 0x018u
#define GPIO_PIN_CNF(n) (0x200u + 4u * (uint32_t)(n))
#define PIN_CNF_OUTPUT 0x00000003u   /* DIR = output, INPUT = disconnect */
#define PIN_CNF_INPUT 0x00000000u    /* DIR = input, INPUT = connect, no pull */
#define PSEL(port, pin) ((uint32_t)(pin) | ((uint32_t)(port) << 5))   /* CONNECT = 0 */
#define PSEL_DISCONNECTED 0x80000000u

/* PWM (VERIFY) */
#define PWM_TASKS_STOP 0x004u
#define PWM_TASKS_SEQSTART0 0x008u
#define PWM_EVENTS_PWMPERIODEND 0x118u
#define PWM_PUBLISH_PWMPERIODEND 0x198u
#define PWM_SHORTS 0x200u
#define PWM_SHORTS_LOOPSDONE_SEQSTART0 (1u << 2)
#define PWM_ENABLE 0x500u
#define PWM_MODE 0x504u              /* 1 = UpAndDown (centre aligned) */
#define PWM_COUNTERTOP 0x508u
#define PWM_PRESCALER 0x50Cu         /* 0 = 16 MHz */
#define PWM_DECODER 0x510u           /* LOAD = 2 (Individual), MODE = 0 (RefreshCount) */
#define PWM_LOOP 0x514u
#define PWM_SEQ_PTR(n) (0x520u + 0x20u * (uint32_t)(n))
#define PWM_SEQ_CNT(n) (0x524u + 0x20u * (uint32_t)(n))
#define PWM_SEQ_REFRESH(n) (0x528u + 0x20u * (uint32_t)(n))
#define PWM_SEQ_ENDDELAY(n) (0x52Cu + 0x20u * (uint32_t)(n))
#define PWM_PSEL_OUT(n) (0x560u + 4u * (uint32_t)(n))
#define PWM_POLARITY_RISING 0x8000u  /* bit 15: 1 = first edge rising (output starts low); VERIFY */

/* SAADC (VERIFY) */
#define SAADC_TASKS_START 0x000u
#define SAADC_TASKS_SAMPLE 0x004u
#define SAADC_TASKS_CALIBRATEOFFSET 0x00Cu
#define SAADC_SUBSCRIBE_START 0x080u
#define SAADC_SUBSCRIBE_SAMPLE 0x084u
#define SAADC_EVENTS_END 0x104u
#define SAADC_EVENTS_CALIBRATEDONE 0x110u
#define SAADC_PUBLISH_END 0x184u
#define SAADC_INTENSET 0x304u
#define SAADC_INT_END (1u << 1)
#define SAADC_ENABLE 0x500u
#define SAADC_CH_PSELP(n) (0x510u + 0x10u * (uint32_t)(n))
#define SAADC_CH_PSELN(n) (0x514u + 0x10u * (uint32_t)(n))
#define SAADC_CH_CONFIG(n) (0x518u + 0x10u * (uint32_t)(n))
#define SAADC_RESOLUTION 0x5F0u      /* 2 = 12 bit */
#define SAADC_OVERSAMPLE 0x5F4u
#define SAADC_SAMPLERATE 0x5F8u
#define SAADC_RESULT_PTR 0x62Cu
#define SAADC_RESULT_MAXCNT 0x630u
#define SAADC_AIN(n) ((uint32_t)(n) + 1u)  /* PSELP/PSELN code of AINn */
#define SAADC_CFG_GAIN1_6 (0u << 8)
#define SAADC_CFG_GAIN1_4 (2u << 8)
#define SAADC_CFG_GAIN1_2 (4u << 8)
#define SAADC_CFG_REF_INT (0u << 12)
#define SAADC_CFG_REF_VDD4 (1u << 12)
#define SAADC_CFG_TACQ3 (0u << 16)
#define SAADC_CFG_TACQ10 (2u << 16)
#define SAADC_CFG_DIFF (1u << 20)

/* TIMER (VERIFY) */
#define TIMER_TASKS_START 0x000u
#define TIMER_TASKS_CLEAR 0x00Cu
#define TIMER_TASKS_CAPTURE(n) (0x040u + 4u * (uint32_t)(n))
#define TIMER_SUBSCRIBE_COUNT 0x088u
#define TIMER_SUBSCRIBE_CLEAR 0x08Cu
#define TIMER_EVENTS_COMPARE(n) (0x140u + 4u * (uint32_t)(n))
#define TIMER_PUBLISH_COMPARE(n) (0x1C0u + 4u * (uint32_t)(n))
#define TIMER_SHORTS 0x200u
#define TIMER_SHORTS_COMPARE0_CLEAR (1u << 0)
#define TIMER_MODE 0x504u            /* 0 timer, 1 counter */
#define TIMER_BITMODE 0x508u         /* 0 16 bit, 3 32 bit */
#define TIMER_PRESCALER 0x510u
#define TIMER_CC(n) (0x540u + 4u * (uint32_t)(n))

/* EGU (VERIFY) */
#define EGU_SUBSCRIBE_TRIGGER(n) (0x080u + 4u * (uint32_t)(n))
#define EGU_EVENTS_TRIGGERED(n) (0x100u + 4u * (uint32_t)(n))
#define EGU_INTENSET 0x304u

/* DPPIC (VERIFY) */
#define DPPIC_CHENSET 0x504u

/* WDT (VERIFY) */
#define WDT_TASKS_START 0x000u
#define WDT_CRV 0x504u
#define WDT_RREN 0x508u
#define WDT_CONFIG 0x50Cu
#define WDT_RR(n) (0x600u + 4u * (uint32_t)(n))
#define WDT_RELOAD_VALUE 0x6E524635u

/* SPIM (VERIFY) */
#define SPIM_TASKS_START 0x010u
#define SPIM_EVENTS_END 0x118u
#define SPIM_ENABLE 0x500u           /* 7 = enabled */
#define SPIM_PSEL_SCK 0x508u
#define SPIM_PSEL_MOSI 0x50Cu
#define SPIM_PSEL_MISO 0x510u
#define SPIM_PSEL_CSN 0x514u         /* hardware CSN (SPIM4) */
#define SPIM_FREQUENCY 0x524u
#define SPIM_FREQ_M8 0x80000000u
#define SPIM_FREQ_M16 0x0A000000u    /* SPIM4 only, VERIFY */
#define SPIM_RXD_PTR 0x534u
#define SPIM_RXD_MAXCNT 0x538u
#define SPIM_TXD_PTR 0x544u
#define SPIM_TXD_MAXCNT 0x548u
#define SPIM_CONFIG 0x554u

/* ---- Cortex-M33 system registers (architectural) ---- */
#define SCB_CPACR 0xE000ED88u
#define SCB_VTOR 0xE000ED08u
#define NVIC_ISER(n) (0xE000E100u + 4u * (uint32_t)(n))
#define NVIC_IPR_BYTE(irq) (*(volatile uint8_t *)(uintptr_t)(0xE000E400u + (uint32_t)(irq)))
#define NRF_PRIO_BITS 3u              /* nRF5340 implements 3 priority bits (VERIFY) */

static inline void nvic_enable(int irq, uint32_t prio)
{
    NVIC_IPR_BYTE(irq) = (uint8_t)(prio << (8u - NRF_PRIO_BITS));
    REG32(NVIC_ISER((uint32_t)irq >> 5)) = 1u << ((uint32_t)irq & 31u);
}

#endif /* PEN_NRF5340_REGS_H */
