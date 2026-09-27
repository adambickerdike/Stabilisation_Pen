/*
 * hal_host.h - host implementation of hal.h for unit/system tests.
 * Models the Rev A fault-handling logic (electronics/gen/design_revA.py
 * sheet_fault_handling): window comparator OC_N -> 74AUP1G74 PRE, firmware
 * FAULT_CLR_N -> CLR, FAULT_N = ~Q, ACT_EN = ACT_EN_REQ & FAULT_N & NOCHG.
 */
#ifndef PEN_HAL_HOST_H
#define PEN_HAL_HOST_H

#include <stdbool.h>
#include <stdint.h>

#include "hal.h"

typedef struct {
    bool act_en_req;
    bool drv_sleep_n;
    bool oc_n;          /* comparator output: false = over-current present (PRE low) */
    bool latch_q;       /* flip-flop Q; FAULT_N = !Q */
    bool chg_det;
    bridge_cmd_t bridge[2];
    uint32_t bridge_writes;
    float vbat;
    float ntc_ratio;
    hal_hall_t hall;
    bool hall_ok;
    bool reset_was_wdt;
    uint32_t time_us;
    uint32_t wdt_kicks;
    uint32_t clr_pulses;
    uint32_t irq_depth;
} hal_host_state_t;

extern hal_host_state_t g_hal;

void hal_host_reset(void);
/* comparator trip (true) / release (false); a trip sets the latch */
void hal_host_set_overcurrent(bool present);
/* ACT_EN as computed by the U23 AND gate */
bool hal_host_act_en(void);

#endif /* PEN_HAL_HOST_H */
