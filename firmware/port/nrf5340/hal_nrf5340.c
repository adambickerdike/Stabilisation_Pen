/*
 * hal_nrf5340.c - hal.h on the nRF5340 application core (register level).
 * Status: COMPILE-TESTED ONLY. Every register access is VERIFY (see
 * nrf5340_regs.h); nothing here has run on silicon.
 */
#include <stddef.h>

#include "board.h"
#include "hal.h"
#include "nrf5340_regs.h"
#include "params_gen.h"

#define P0 NRF_P0_BASE
#define P1 NRF_P1_BASE

/* PWM EasyDMA sequence buffer: IN1_X, IN2_X, IN1_Y, IN2_Y (must be in RAM) */
volatile uint16_t g_pwm_seq[4];

static volatile int16_t s_vbat_code, s_ntc_code;
static bool s_reset_wdt, s_reset_read;

static inline void pin_out(uint32_t port, uint32_t pin, bool high)
{
    REG32(port + (high ? GPIO_OUTSET : GPIO_OUTCLR)) = 1u << pin;
}

void board_gpio_init(void)
{
    /* safe levels first: actuator request low, drivers asleep, latch clear idle high */
    pin_out(P0, PIN_ACT_EN_REQ, false);
    pin_out(P0, PIN_DRV_SLEEP_N, false);
    pin_out(P1, PIN_FAULT_CLR_N, true);
    REG32(P0 + GPIO_PIN_CNF(PIN_ACT_EN_REQ)) = PIN_CNF_OUTPUT;
    REG32(P0 + GPIO_PIN_CNF(PIN_DRV_SLEEP_N)) = PIN_CNF_OUTPUT;
    REG32(P1 + GPIO_PIN_CNF(PIN_FAULT_CLR_N)) = PIN_CNF_OUTPUT;
    REG32(P1 + GPIO_PIN_CNF(PIN_FAULT_N)) = PIN_CNF_INPUT;
    REG32(P1 + GPIO_PIN_CNF(PIN_CHG_DET)) = PIN_CNF_INPUT;
    /* bridge inputs low (coast) until the PWM owns them */
    const uint32_t in_pins[4] = {PIN_IN1_X, PIN_IN2_X, PIN_IN1_Y, PIN_IN2_Y};
    for (int k = 0; k < 4; k++) {
        pin_out(P0, in_pins[k], false);
        REG32(P0 + GPIO_PIN_CNF(in_pins[k])) = PIN_CNF_OUTPUT;
    }
}

void board_timebase_init(void)
{
    REG32(NRF_TIMER0_BASE + TIMER_MODE) = 0u;       /* timer */
    REG32(NRF_TIMER0_BASE + TIMER_BITMODE) = 3u;    /* 32 bit */
    REG32(NRF_TIMER0_BASE + TIMER_PRESCALER) = 4u;  /* 16 MHz / 2^4 = 1 MHz */
    REG32(NRF_TIMER0_BASE + TIMER_TASKS_START) = 1u;
}

void board_wdt_init(void)
{
    /* 5 ms timeout; the stage task reloads it only while the 40 kHz ISR is alive */
    REG32(NRF_WDT0_BASE + WDT_CRV) = (uint32_t)(0.005f * 32768.0f) - 1u;
    REG32(NRF_WDT0_BASE + WDT_RREN) = 1u;
    REG32(NRF_WDT0_BASE + WDT_CONFIG) = 1u;         /* keep running in sleep; pause when halted (VERIFY) */
    REG32(NRF_WDT0_BASE + WDT_TASKS_START) = 1u;
}

void board_slow_adc_store(int16_t vbat_code, int16_t ntc_code)
{
    s_vbat_code = vbat_code;
    s_ntc_code = ntc_code;
}

/* ------------------------------------------------------------------ hal.h */
void hal_act_en_req(bool on) { pin_out(P0, PIN_ACT_EN_REQ, on); }
void hal_drv_sleep_n(bool awake) { pin_out(P0, PIN_DRV_SLEEP_N, awake); }
bool hal_fault_n(void) { return (REG32(P1 + GPIO_IN) & (1u << PIN_FAULT_N)) != 0u; }
bool hal_chg_det(void) { return (REG32(P1 + GPIO_IN) & (1u << PIN_CHG_DET)) != 0u; }

void hal_fault_clr_pulse(void)
{
    /* >= 1 us low (74AUP1G74 t_w(CLR) is ns-class; 2 us for margin) */
    pin_out(P1, PIN_FAULT_CLR_N, false);
    const uint32_t t0 = hal_time_us();
    while ((uint32_t)(hal_time_us() - t0) < 3u) {
    }
    pin_out(P1, PIN_FAULT_CLR_N, true);
}

/* in_high counts (0..COUNTERTOP) high, centred on the period edge ->
 * PWM value: polarity "falling edge first" (output starts high, goes low at
 * the compare value on the way up, high again on the way down). Constant
 * levels use a compare value the counter never reaches. VERIFY with a scope. */
static uint16_t pwm_value(uint16_t in_high)
{
    if (in_high == 0u) {
        return (uint16_t)(PWM_POLARITY_RISING | 0x7FFFu);   /* always low */
    }
    if (in_high >= (uint16_t)PEN_PWM_COUNTERTOP) {
        return 0x7FFFu;                                       /* always high */
    }
    return in_high;
}

void hal_bridge_set(const bridge_cmd_t cmd[2])
{
    /* picked up by EasyDMA at the next period (VERIFY loading instant) */
    g_pwm_seq[0] = pwm_value(cmd[0].in1_high);
    g_pwm_seq[1] = pwm_value(cmd[0].in2_high);
    g_pwm_seq[2] = pwm_value(cmd[1].in1_high);
    g_pwm_seq[3] = pwm_value(cmd[1].in2_high);
}

float hal_vbat_volts(void)
{
    /* single-ended, gain 1/6, internal 0.6 V: full scale 3.6 V over 4096 (VERIFY) */
    return (float)s_vbat_code * (PEN_SAADC_SE_FS_V / 4096.0f) / PEN_VBAT_DIV;
}

float hal_ntc_ratio(void)
{
    /* REFSEL VDD/4, gain 1/4: full scale = VDD, ratiometric with the +3V0A divider (VERIFY) */
    return (float)s_ntc_code / 4096.0f;
}

void hal_watchdog_kick(void) { REG32(NRF_WDT0_BASE + WDT_RR(0)) = WDT_RELOAD_VALUE; }

bool hal_reset_was_watchdog(void)
{
    if (!s_reset_read) {
        const uint32_t r = REG32(NRF_CLOCK_BASE + RESET_RESETREAS);
        s_reset_wdt = (r & (RESETREAS_DOG0 | RESETREAS_DOG1)) != 0u;
        REG32(NRF_CLOCK_BASE + RESET_RESETREAS) = r;   /* write 1 to clear */
        s_reset_read = true;
    }
    return s_reset_wdt;
}

uint32_t hal_time_us(void)
{
    REG32(NRF_TIMER0_BASE + TIMER_TASKS_CAPTURE(1)) = 1u;
    return REG32(NRF_TIMER0_BASE + TIMER_CC(1));
}

uint32_t hal_irq_save(void)
{
    uint32_t primask;
    __asm volatile("mrs %0, primask\n cpsid i" : "=r"(primask)::"memory");
    return primask;
}

void hal_irq_restore(uint32_t state)
{
    __asm volatile("msr primask, %0" ::"r"(state) : "memory");
}
