/*
 * hal_host.c - host HAL (see header). Test infrastructure, not firmware.
 */
#include "hal_host.h"

#include <string.h>

#include "params_gen.h"

hal_host_state_t g_hal;

void hal_host_reset(void)
{
    memset(&g_hal, 0, sizeof(g_hal));
    g_hal.oc_n = true;
    g_hal.latch_q = false;
    g_hal.vbat = PEN_V_BAT_NOM;
    g_hal.ntc_ratio = 0.5f;   /* 25 degC with a 10k/10k divider */
    g_hal.hall_ok = true;
    g_hal.hall.fresh = true;
}

void hal_host_set_overcurrent(bool present)
{
    g_hal.oc_n = !present;
    if (present) {
        g_hal.latch_q = true;  /* PRE low sets Q */
    }
}

bool hal_host_act_en(void)
{
    return g_hal.act_en_req && !g_hal.latch_q && !g_hal.chg_det;
}

void hal_act_en_req(bool on) { g_hal.act_en_req = on; }
void hal_drv_sleep_n(bool awake) { g_hal.drv_sleep_n = awake; }
bool hal_fault_n(void) { return !g_hal.latch_q; }

void hal_fault_clr_pulse(void)
{
    g_hal.clr_pulses++;
    /* CLR low: Q -> 0 unless PRE is also low (then Q = ~Q = 1 during the
     * pulse and PRE wins after CLR is released) */
    if (g_hal.oc_n) {
        g_hal.latch_q = false;
    } else {
        g_hal.latch_q = true;
    }
}

bool hal_chg_det(void) { return g_hal.chg_det; }

void hal_bridge_set(const bridge_cmd_t cmd[2])
{
    g_hal.bridge[0] = cmd[0];
    g_hal.bridge[1] = cmd[1];
    g_hal.bridge_writes++;
}

float hal_vbat_volts(void) { return g_hal.vbat; }
float hal_ntc_ratio(void) { return g_hal.ntc_ratio; }

bool hal_hall_read(hal_hall_t *h)
{
    *h = g_hal.hall;
    return g_hal.hall_ok;
}

void hal_watchdog_kick(void) { g_hal.wdt_kicks++; }
bool hal_reset_was_watchdog(void) { return g_hal.reset_was_wdt; }
uint32_t hal_time_us(void) { return g_hal.time_us; }

uint32_t hal_irq_save(void)
{
    g_hal.irq_depth++;
    return 0u;
}

void hal_irq_restore(uint32_t state)
{
    (void)state;
    if (g_hal.irq_depth > 0u) {
        g_hal.irq_depth--;
    }
}
