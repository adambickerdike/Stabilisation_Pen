/*
 * safety.h - fault detections, ICD section 6 (fault bits in pen_types.h).
 *
 * Detections (thresholds in params_gen.h; "proposed" ones are marked there):
 *  bit 0 over-current : FAULT_N low (hardware latch). Clear sequence
 *                       ACT_EN_REQ low -> pulse FAULT_CLR_N -> read FAULT_N
 *                       (electronics/gen/design_revA.py sheet_fault_handling).
 *  bit 1 Hall         : stuck value (bit-identical X/Y/Z for HALL_STUCK_TICKS
 *                       ticks = 4 ms < 5 ms), stale data (no new conversion /
 *                       CRC error on 2 consecutive ticks), range (|q| beyond
 *                       the mechanical stop + margin), model residual (second
 *                       difference of q minus the acceleration predicted from
 *                       the measured coil current exceeds HALL_JUMP_MAX).
 *  bit 2 over-temp    : thermal observer condition (thermal.h).
 *  bit 3 low battery  : filtered VBAT < v_bat_min for VBAT_DEBOUNCE.
 *  bit 4 optical      : optical invalid while in contact with assistance
 *                       active for > 300 ms.
 *  bit 5 watchdog     : reset cause read at boot.
 *  bit 6 headroom     : max |duty| > 0.95 on every tick for > 50 ms.
 *  bit 7 charging     : CHG_DET high (hardware removes VMOT through NOCHG).
 *  bit 8 ML guard     : more than ML_TRIP_COUNT guard trips in ML_TRIP_WINDOW.
 * Latched bits are cleared only through safety_clear(), called by the state
 * machine on SAFE_PASSIVE -> STANDBY after pen-up and a successful self-check.
 */
#ifndef PEN_SAFETY_H
#define PEN_SAFETY_H

#include <stdbool.h>
#include <stdint.h>

#include "pen_types.h"

#define SAFETY_ML_TRIP_RING 8

typedef enum {
    OC_CLR_IDLE = 0,
    OC_CLR_REQ_LOW,    /* ACT_EN_REQ driven low, bridges coast */
    OC_CLR_PULSED,     /* FAULT_CLR_N pulsed, FAULT_N read next tick */
    OC_CLR_OK,
    OC_CLR_FAILED
} oc_clr_state_t;

typedef struct {
    uint16_t faults;           /* latched fault bits */
    uint16_t active;           /* conditions currently present (for self-check) */
    /* Hall */
    int16_t hall_last[3];
    bool hall_have_last;
    uint16_t hall_same;        /* consecutive repeats of the raw triple */
    uint16_t hall_stale;       /* consecutive non-fresh reads */
    float q1[2], q2[2];        /* q at k-1, k-2 */
    float a1[2];               /* model acceleration at k-1 (m/s^2) */
    uint8_t q_n;               /* history depth available */
    uint16_t hall_resid_cnt, hall_range_cnt;
    float hall_resid_max;      /* diagnostics */
    uint32_t hall_trip_tick;   /* tick count at detection */
    /* headroom */
    uint16_t headroom_ticks;
    /* optical */
    uint16_t opt_ticks;
    /* battery */
    float vbat_f;
    bool vbat_init;
    uint16_t lowbat_ticks;
    /* over-current clear sequencer */
    oc_clr_state_t oc_clr;
    uint8_t oc_retries;
    /* ML trips */
    float ml_trip_t[SAFETY_ML_TRIP_RING];
    uint8_t ml_trip_head, ml_trip_n;
    uint32_t ticks;            /* stage ticks since init */
    float t_now;               /* s since init */
} safety_t;

void safety_init(safety_t *s);
/* Call once per 2 kHz tick first (advances the time base). */
void safety_tick_begin(safety_t *s);

/* bit 5, at boot */
void safety_boot(safety_t *s, bool reset_by_watchdog);
/* bit 1: returns true when the Hall fault is detected this tick.
 * i_meas: measured coil currents (A) over the last tick. */
bool safety_hall_check(safety_t *s, const int16_t raw[3], bool fresh, const float q[2], const float i_meas[2]);
/* bit 6 */
bool safety_headroom_check(safety_t *s, float duty_abs_max_tick);
/* bit 4 */
bool safety_optical_check(safety_t *s, bool opt_valid, bool in_contact, bool monitoring);
/* bit 3; returns true on fault. vbat: volts (raw, filtered here) */
bool safety_battery_check(safety_t *s, float vbat, float dt);
bool safety_battery_ok(const safety_t *s);
/* bit 2 */
bool safety_thermal_check(safety_t *s, bool over_temp);
/* bit 0: reads FAULT_N through the HAL */
bool safety_overcurrent_check(safety_t *s);
/* bit 7 */
bool safety_charging_check(safety_t *s, bool chg_det);
/* bit 8: report one ML guard trip; returns true when the count is exceeded */
bool safety_ml_trip(safety_t *s);

/* Over-current latch clear sequencer, one step per tick. Starts when called
 * in OC_CLR_IDLE; returns the state (OK / FAILED are terminal until
 * safety_oc_clear_reset()). Uses hal_act_en_req/hal_fault_clr_pulse/hal_fault_n. */
oc_clr_state_t safety_oc_clear_step(safety_t *s);
void safety_oc_clear_reset(safety_t *s);

/* Self-check for SAFE_PASSIVE -> STANDBY (pen-up): true when no latched
 * fault condition is still present. */
bool safety_self_check(const safety_t *s);
void safety_clear(safety_t *s);

#endif /* PEN_SAFETY_H */
