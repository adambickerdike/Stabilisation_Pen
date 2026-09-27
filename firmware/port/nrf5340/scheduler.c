/*
 * scheduler.c - one clock domain, the PWM timer (ICD s2). COMPILE-TESTED
 * ONLY; every register write is VERIFY (nrf5340_regs.h).
 *
 *   PWM0 (16 MHz, up/down, COUNTERTOP 200 -> 40 kHz, 4 channels IN1/IN2 x, y)
 *     EVENTS_PWMPERIODEND --DPPI ch 0--> TIMER1.CLEAR   (phase reference)
 *                                     \-> TIMER2.COUNT  (period counter)
 *   TIMER1 (16 MHz): CC0 = 112 (7.0 us), CC1 = 312 (19.5 us)
 *     COMPARE0/1 --DPPI ch 1--> SAADC.SAMPLE
 *       CC1: "edge" scan of ISNS_X, ISNS_Y (5 us per channel: TACQ 3 us +
 *            2 us conversion) straddling the period boundary = middle of the
 *            brake phase; CC0: "centre" scan straddling 12.5 us = middle of the
 *            drive phase (drive phase centred by the IN/IN mapping, current_loop.h)
 *   SAADC RESULT.MAXCNT = 4: END after [edge x, edge y, centre x, centre y]
 *     EVENTS_END --DPPI ch 3--> SAADC.START (re-arm the buffer)
 *     END interrupt (priority 1) -> pen_app_current_isr(): 40 kHz current loop;
 *     the new compare values are fetched by the PWM EasyDMA at the next period.
 *   TIMER2 counter: CC0 = 20, SHORTS COMPARE0_CLEAR
 *     COMPARE0 --DPPI ch 2--> EGU0.TRIGGER0 -> EGU0 interrupt (priority 3):
 *     the 2 kHz stage task (Hall read at tick start, estimator, servo, ...).
 *     Release jitter = interrupt latency only (no software counting).
 * Every 20th tick (100 Hz) the centre scan also converts VBAT (AIN2) and the
 * coil NTC (AIN3): that period's END arrives ~10 us later (still before the
 * period end; VERIFY the timing with a logic analyser, bring-up step 7).
 * Aggregate SAADC rate 160 kS/s + 200 S/s (DEC-010: limit 200 kS/s, VERIFY).
 */
#include <stddef.h>
#include <string.h>

#include "board.h"
#include "nrf5340_regs.h"
#include "params_gen.h"

#define DPPI_CH_PERIOD 0u
#define DPPI_CH_SAMPLE 1u
#define DPPI_CH_TICK 2u
#define DPPI_CH_SAADC_END 3u

#define TIMER1_CC_CENTRE 112u   /* 7.0 us: channels sampled at ~10 and ~15 us (VERIFY) */
#define TIMER1_CC_EDGE 312u     /* 19.5 us: channels sampled at ~22.5 us and ~2.5 us of the next period */

pen_app_t g_app;
extern volatile uint16_t g_pwm_seq[4];
static volatile int16_t s_adc[6];   /* edge x, edge y, centre x, centre y, [vbat, ntc] */
static volatile uint32_t s_slow_cycle;
static pen_sensors_t s_sens;

static void saadc_init(void)
{
    const uint32_t s = NRF_SAADC_BASE;
    REG32(s + SAADC_RESOLUTION) = 2u;       /* 12 bit */
    REG32(s + SAADC_OVERSAMPLE) = 0u;
    REG32(s + SAADC_SAMPLERATE) = 0u;       /* task driven */
    const uint32_t diff = SAADC_CFG_GAIN1_2 | SAADC_CFG_REF_INT | SAADC_CFG_TACQ3 | SAADC_CFG_DIFF;
    REG32(s + SAADC_CH_PSELP(0)) = SAADC_AIN(PIN_ISNS_X_AIN);
    REG32(s + SAADC_CH_PSELN(0)) = SAADC_AIN(PIN_VREF_AIN);
    REG32(s + SAADC_CH_CONFIG(0)) = diff;
    REG32(s + SAADC_CH_PSELP(1)) = SAADC_AIN(PIN_ISNS_Y_AIN);
    REG32(s + SAADC_CH_PSELN(1)) = SAADC_AIN(PIN_VREF_AIN);
    REG32(s + SAADC_CH_CONFIG(1)) = diff;
    /* slow channels: configured, enabled only for the 100 Hz scan (PSELP = 0 disables) */
    REG32(s + SAADC_CH_PSELP(2)) = 0u;
    REG32(s + SAADC_CH_CONFIG(2)) = SAADC_CFG_GAIN1_6 | SAADC_CFG_REF_INT | SAADC_CFG_TACQ10;
    REG32(s + SAADC_CH_PSELP(3)) = 0u;
    REG32(s + SAADC_CH_CONFIG(3)) = SAADC_CFG_GAIN1_4 | SAADC_CFG_REF_VDD4 | SAADC_CFG_TACQ10;
    REG32(s + SAADC_RESULT_PTR) = (uint32_t)(uintptr_t)&s_adc[0];
    REG32(s + SAADC_RESULT_MAXCNT) = 4u;
    REG32(s + SAADC_ENABLE) = 1u;
    /* offset calibration of the SAADC itself at start-up (VERIFY sequence) */
    REG32(s + SAADC_TASKS_CALIBRATEOFFSET) = 1u;
    for (uint32_t k = 0; k < 100000u && REG32(s + SAADC_EVENTS_CALIBRATEDONE) == 0u; k++) {
    }
    REG32(s + SAADC_EVENTS_CALIBRATEDONE) = 0u;
    REG32(s + SAADC_SUBSCRIBE_SAMPLE) = DPPI_CH_SAMPLE | DPPI_EN;
    REG32(s + SAADC_PUBLISH_END) = DPPI_CH_SAADC_END | DPPI_EN;
    REG32(s + SAADC_SUBSCRIBE_START) = DPPI_CH_SAADC_END | DPPI_EN;
    REG32(s + SAADC_INTENSET) = SAADC_INT_END;
    REG32(s + SAADC_TASKS_START) = 1u;
}

static void pwm_init(void)
{
    const uint32_t p = NRF_PWM0_BASE;
    const uint32_t pins[4] = {PIN_IN1_X, PIN_IN2_X, PIN_IN1_Y, PIN_IN2_Y};
    for (uint32_t k = 0; k < 4u; k++) {
        REG32(p + PWM_PSEL_OUT(k)) = PSEL(0u, pins[k]);
        g_pwm_seq[k] = (uint16_t)(PWM_POLARITY_RISING | 0x7FFFu);   /* all low = coast */
    }
    REG32(p + PWM_MODE) = 1u;                                  /* up and down: centre aligned */
    REG32(p + PWM_COUNTERTOP) = (uint32_t)PEN_PWM_COUNTERTOP;  /* 200 -> 40 kHz */
    REG32(p + PWM_PRESCALER) = 0u;                             /* 16 MHz */
    REG32(p + PWM_DECODER) = 2u;                               /* individual, refresh count */
    for (uint32_t n = 0; n < 2u; n++) {                        /* both sequences play the same 1-step buffer */
        REG32(p + PWM_SEQ_PTR(n)) = (uint32_t)(uintptr_t)&g_pwm_seq[0];
        REG32(p + PWM_SEQ_CNT(n)) = 4u;
        REG32(p + PWM_SEQ_REFRESH(n)) = 0u;
        REG32(p + PWM_SEQ_ENDDELAY(n)) = 0u;
    }
    REG32(p + PWM_LOOP) = 1u;
    REG32(p + PWM_SHORTS) = PWM_SHORTS_LOOPSDONE_SEQSTART0;    /* endless playback (VERIFY gapless) */
    REG32(p + PWM_PUBLISH_PWMPERIODEND) = DPPI_CH_PERIOD | DPPI_EN;
    REG32(p + PWM_ENABLE) = 1u;
}

static void timers_init(void)
{
    const uint32_t t1 = NRF_TIMER1_BASE;
    REG32(t1 + TIMER_MODE) = 0u;
    REG32(t1 + TIMER_BITMODE) = 0u;
    REG32(t1 + TIMER_PRESCALER) = 0u;                          /* 16 MHz, locked to the PWM clock */
    REG32(t1 + TIMER_CC(0)) = TIMER1_CC_CENTRE;
    REG32(t1 + TIMER_CC(1)) = TIMER1_CC_EDGE;
    REG32(t1 + TIMER_SUBSCRIBE_CLEAR) = DPPI_CH_PERIOD | DPPI_EN;
    REG32(t1 + TIMER_PUBLISH_COMPARE(0)) = DPPI_CH_SAMPLE | DPPI_EN;
    REG32(t1 + TIMER_PUBLISH_COMPARE(1)) = DPPI_CH_SAMPLE | DPPI_EN;
    const uint32_t t2 = NRF_TIMER2_BASE;
    REG32(t2 + TIMER_MODE) = 1u;                               /* counter */
    REG32(t2 + TIMER_BITMODE) = 0u;
    REG32(t2 + TIMER_CC(0)) = (uint32_t)PEN_PWM_PER_STAGE;     /* every 20th PWM period */
    REG32(t2 + TIMER_SHORTS) = TIMER_SHORTS_COMPARE0_CLEAR;
    REG32(t2 + TIMER_SUBSCRIBE_COUNT) = DPPI_CH_PERIOD | DPPI_EN;
    REG32(t2 + TIMER_PUBLISH_COMPARE(0)) = DPPI_CH_TICK | DPPI_EN;
    REG32(NRF_EGU0_BASE + EGU_SUBSCRIBE_TRIGGER(0)) = DPPI_CH_TICK | DPPI_EN;
    REG32(NRF_EGU0_BASE + EGU_INTENSET) = 1u;
    REG32(t1 + TIMER_TASKS_START) = 1u;
    REG32(t2 + TIMER_TASKS_START) = 1u;
}

void sched_init(void)
{
    saadc_init();
    pwm_init();
    timers_init();
    REG32(NRF_DPPIC_BASE + DPPIC_CHENSET) = (1u << DPPI_CH_PERIOD) | (1u << DPPI_CH_SAMPLE) | (1u << DPPI_CH_TICK) |
                                            (1u << DPPI_CH_SAADC_END);
    nvic_enable(SAADC_IRQn, 1u);   /* current loop: highest application priority */
    nvic_enable(EGU0_IRQn, 3u);    /* stage task */
    REG32(NRF_PWM0_BASE + PWM_TASKS_SEQSTART0) = 1u;   /* the PWM period is now the system clock */
}

/* 40 kHz: current loop */
void SAADC_IRQHandler(void)
{
    REG32(NRF_SAADC_BASE + SAADC_EVENTS_END) = 0u;
    const int16_t ae[2] = {s_adc[0], s_adc[1]};
    const int16_t ac[2] = {s_adc[2], s_adc[3]};
    if (REG32(NRF_SAADC_BASE + SAADC_RESULT_MAXCNT) == 6u) {
        /* slow scan finished: store and fall back to the 2-channel scans */
        board_slow_adc_store(s_adc[4], s_adc[5]);
        REG32(NRF_SAADC_BASE + SAADC_CH_PSELP(2)) = 0u;
        REG32(NRF_SAADC_BASE + SAADC_CH_PSELP(3)) = 0u;
        REG32(NRF_SAADC_BASE + SAADC_RESULT_MAXCNT) = 4u;
    }
    pen_app_current_isr(&g_app, ac, ae);
}

/* 2 kHz: stage task (EGU0 software interrupt fired by TIMER2 through DPPI) */
void EGU0_IRQHandler(void)
{
    REG32(NRF_EGU0_BASE + EGU_EVENTS_TRIGGERED(0)) = 0u;
    sensors_read(&s_sens);
    pen_app_stage_tick(&g_app, &s_sens);
    if (++s_slow_cycle >= 20u) {
        /* arm a slow scan (VBAT, NTC) for the next centre conversion (VERIFY:
         * reconfiguring between scans; the buffer holds 6 results then) */
        s_slow_cycle = 0u;
        REG32(NRF_SAADC_BASE + SAADC_CH_PSELP(2)) = SAADC_AIN(PIN_VBAT_AIN);
        REG32(NRF_SAADC_BASE + SAADC_CH_PSELP(3)) = SAADC_AIN(PIN_NTC_AIN);
        REG32(NRF_SAADC_BASE + SAADC_RESULT_MAXCNT) = 6u;
    }
}
