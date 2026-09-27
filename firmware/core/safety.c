/*
 * safety.c - fault detections and the over-current latch clear sequence.
 * Status: PROPOSED DESIGN; host unit tests (including a behavioural model of
 * the 74AUP1G74 latch in port/host/hal_host.c). Not validated on hardware.
 */
#include "safety.h"

#include <math.h>
#include <string.h>

#include "hal.h"
#include "mathx.h"
#include "params_gen.h"

#define TS PEN_TS_STAGE

void safety_init(safety_t *s)
{
    memset(s, 0, sizeof(*s));
}

void safety_tick_begin(safety_t *s)
{
    s->ticks++;
    s->t_now += TS;
}

static void set_active(safety_t *s, uint16_t bit, bool on)
{
    if (on) {
        s->active = (uint16_t)(s->active | bit);
    } else {
        s->active = (uint16_t)(s->active & (uint16_t)~bit);
    }
}

static bool latch(safety_t *s, uint16_t bit)
{
    const bool is_new = (s->faults & bit) == 0u;
    s->faults = (uint16_t)(s->faults | bit);
    return is_new;
}

void safety_boot(safety_t *s, bool reset_by_watchdog)
{
    if (reset_by_watchdog) {
        (void)latch(s, PEN_FAULT_WATCHDOG);
    }
}

bool safety_hall_check(safety_t *s, const int16_t raw[3], bool fresh, const float q[2], const float i_meas[2])
{
    bool cond = false;
    /* stale data: no new conversion or frame CRC error */
    if (!fresh) {
        if (s->hall_stale < 0xFFFFu) {
            s->hall_stale++;
        }
    } else {
        s->hall_stale = 0;
    }
    if (s->hall_stale >= 2u) {
        cond = true;
    }
    /* stuck value: bit-identical triple */
    if (s->hall_have_last && raw[0] == s->hall_last[0] && raw[1] == s->hall_last[1] && raw[2] == s->hall_last[2]) {
        if (s->hall_same < 0xFFFFu) {
            s->hall_same++;
        }
    } else {
        s->hall_same = 0;
    }
    s->hall_last[0] = raw[0];
    s->hall_last[1] = raw[1];
    s->hall_last[2] = raw[2];
    s->hall_have_last = true;
    if (s->hall_same >= (uint16_t)PEN_HALL_STUCK_TICKS) {
        cond = true;
    }
    /* range: beyond the mechanical stop is physically impossible */
    if (hypotf(q[0], q[1]) > PEN_Q_STOP + PEN_HALL_RANGE_MARGIN) {
        if (s->hall_range_cnt < 0xFFFFu) {
            s->hall_range_cnt++;
        }
    } else {
        s->hall_range_cnt = 0;
    }
    if (s->hall_range_cnt >= 2u) {
        cond = true;
    }
    /* model residual: second difference vs predicted acceleration */
    if (s->q_n >= 2u) {
        bool exceed = false;
        for (int ax = 0; ax < 2; ax++) {
            const float d2 = q[ax] - 2.0f * s->q1[ax] + s->q2[ax];
            const float res = d2 - TS * TS * s->a1[ax];
            const float ares = pen_absf(res);
            if (ares > s->hall_resid_max) {
                s->hall_resid_max = ares;
            }
            if (ares > PEN_HALL_JUMP_MAX) {
                exceed = true;
            }
        }
        if (exceed) {
            if (s->hall_resid_cnt < 0xFFFFu) {
                s->hall_resid_cnt++;
            }
        } else {
            s->hall_resid_cnt = 0;
        }
        if (s->hall_resid_cnt >= 2u) {
            cond = true;
        }
    }
    for (int ax = 0; ax < 2; ax++) {
        s->q2[ax] = s->q1[ax];
        s->q1[ax] = q[ax];
        /* simulator sign convention: stage force = -n Kf i */
        s->a1[ax] = (-PEN_N_LEVER * PEN_KF20 * i_meas[ax] - PEN_K_TIP * q[ax]) / PEN_M_EQ;
    }
    if (s->q_n < 2u) {
        s->q_n++;
    }
    set_active(s, PEN_FAULT_HALL, cond);
    if (cond && latch(s, PEN_FAULT_HALL)) {
        s->hall_trip_tick = s->ticks;
        return true;
    }
    return false;
}

bool safety_headroom_check(safety_t *s, float duty_abs_max_tick)
{
    if (duty_abs_max_tick > PEN_DUTY_HEADROOM) {
        if (s->headroom_ticks < 0xFFFFu) {
            s->headroom_ticks++;
        }
    } else {
        s->headroom_ticks = 0;
    }
    const bool cond = (float)s->headroom_ticks * TS > PEN_HEADROOM_TIME + 0.5f * TS;
    set_active(s, PEN_FAULT_HEADROOM, s->headroom_ticks > 0u);
    return cond && latch(s, PEN_FAULT_HEADROOM);
}

bool safety_optical_check(safety_t *s, bool opt_valid, bool in_contact, bool monitoring)
{
    if (monitoring && in_contact && !opt_valid) {
        if (s->opt_ticks < 0xFFFFu) {
            s->opt_ticks++;
        }
    } else {
        s->opt_ticks = 0;
    }
    const bool cond = (float)s->opt_ticks * TS > PEN_OPT_INVALID_TIME + 0.5f * TS;
    set_active(s, PEN_FAULT_OPTICAL, cond);
    return cond && latch(s, PEN_FAULT_OPTICAL);
}

bool safety_battery_check(safety_t *s, float vbat, float dt)
{
    if (!s->vbat_init) {
        s->vbat_f = vbat;
        s->vbat_init = true;
    } else {
        s->vbat_f += (dt / (PEN_VBAT_LPF_TAU + dt)) * (vbat - s->vbat_f);
    }
    if (s->vbat_f < PEN_V_BAT_MIN) {
        if (s->lowbat_ticks < 0xFFFFu) {
            s->lowbat_ticks++;
        }
    } else {
        s->lowbat_ticks = 0;
    }
    const bool cond = (float)s->lowbat_ticks * dt >= PEN_VBAT_DEBOUNCE;
    set_active(s, PEN_FAULT_LOWBAT, s->vbat_f < PEN_VBAT_RECOVER);
    return cond && latch(s, PEN_FAULT_LOWBAT);
}

bool safety_battery_ok(const safety_t *s)
{
    return s->vbat_init && s->vbat_f >= PEN_VBAT_RECOVER;
}

bool safety_thermal_check(safety_t *s, bool over_temp)
{
    set_active(s, PEN_FAULT_OVERTEMP, over_temp);
    return over_temp && latch(s, PEN_FAULT_OVERTEMP);
}

bool safety_overcurrent_check(safety_t *s)
{
    const bool cond = !hal_fault_n();
    if (s->oc_clr == OC_CLR_IDLE || s->oc_clr == OC_CLR_OK) {
        set_active(s, PEN_FAULT_OVERCURRENT, cond);
    }
    return cond && latch(s, PEN_FAULT_OVERCURRENT);
}

bool safety_charging_check(safety_t *s, bool chg_det)
{
    set_active(s, PEN_FAULT_CHARGING, chg_det);
    return chg_det && latch(s, PEN_FAULT_CHARGING);
}

bool safety_ml_trip(safety_t *s)
{
    s->ml_trip_t[s->ml_trip_head] = s->t_now;
    s->ml_trip_head = (uint8_t)((s->ml_trip_head + 1u) % SAFETY_ML_TRIP_RING);
    if (s->ml_trip_n < SAFETY_ML_TRIP_RING) {
        s->ml_trip_n++;
    }
    int n_recent = 0;
    for (uint8_t k = 0; k < s->ml_trip_n; k++) {
        if (s->t_now - s->ml_trip_t[k] <= PEN_ML_TRIP_WINDOW) {
            n_recent++;
        }
    }
    const bool cond = n_recent > PEN_ML_TRIP_COUNT;
    return cond && latch(s, PEN_FAULT_MLGUARD);
}

oc_clr_state_t safety_oc_clear_step(safety_t *s)
{
    switch (s->oc_clr) {
    case OC_CLR_IDLE:
        /* 1: request low first: PRE and CLR both low would give Q = ~Q = 1 */
        hal_act_en_req(false);
        s->oc_clr = OC_CLR_REQ_LOW;
        break;
    case OC_CLR_REQ_LOW:
        /* 2: pulse FAULT_CLR_N low (>= 1 us) */
        hal_fault_clr_pulse();
        s->oc_clr = OC_CLR_PULSED;
        break;
    case OC_CLR_PULSED:
        /* 3: FAULT_N must read high with CLR released; otherwise OC_N is still low */
        if (hal_fault_n()) {
            s->oc_clr = OC_CLR_OK;
            set_active(s, PEN_FAULT_OVERCURRENT, false);
        } else {
            s->oc_retries++;
            s->oc_clr = ((float)s->oc_retries >= PEN_OC_CLEAR_RETRIES) ? OC_CLR_FAILED : OC_CLR_REQ_LOW;
            set_active(s, PEN_FAULT_OVERCURRENT, true);
        }
        break;
    case OC_CLR_OK:
    case OC_CLR_FAILED:
    default:
        break;
    }
    return s->oc_clr;
}

void safety_oc_clear_reset(safety_t *s)
{
    s->oc_clr = OC_CLR_IDLE;
    s->oc_retries = 0;
}

bool safety_self_check(const safety_t *s)
{
    if (s->active != 0u) {
        return false;
    }
    if ((s->faults & PEN_FAULT_OVERCURRENT) != 0u && s->oc_clr != OC_CLR_OK) {
        return false;
    }
    if ((s->faults & PEN_FAULT_LOWBAT) != 0u && !safety_battery_ok(s)) {
        return false;
    }
    return true;
}

void safety_clear(safety_t *s)
{
    s->faults = 0;
    s->hall_same = 0;
    s->hall_stale = 0;
    s->hall_resid_cnt = 0;
    s->hall_range_cnt = 0;
    s->q_n = 0;
    s->headroom_ticks = 0;
    s->opt_ticks = 0;
    s->ml_trip_n = 0;
    s->ml_trip_head = 0;
    safety_oc_clear_reset(s);
}
