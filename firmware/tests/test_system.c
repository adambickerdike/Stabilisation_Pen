/*
 * test_system.c - application layer (core/app.c) on the C plant through the
 * host HAL (interlock model): Hall-frozen detection latency and the fault
 * sequences of ICD s6. Evidence status: HOST TEST on a model.
 */
#include <math.h>
#include <string.h>

#include "app.h"
#include "hal_host.h"
#include "params_gen.h"
#include "plant.h"
#include "tr.h"

typedef struct {
    pen_app_t app;
    plant_t pl;
    pen_sensors_t sens;
    bool pen_down;
    double f_load;          /* transverse contact load at the tip in contact (N, x) */
    uint32_t n_rec[6];
    uint32_t n_bad;
    uint32_t ev_count[16];
    int32_t last_fault_arg;
} sys_t;

static sys_t g_sys;   /* large: keep off the (QEMU) stack */

static void sink(const uint8_t *rec, size_t len, void *ctx)
{
    sys_t *s = (sys_t *)ctx;
    uint8_t type, l;
    const uint8_t *pl;
    size_t used;
    if (penlog_parse_record(rec, len, &type, &pl, &l, &used) != PENLOG_OK || used != len) {
        s->n_bad++;
        return;
    }
    if (type >= 1u && type <= 5u) {
        s->n_rec[type]++;
    }
    if (type == PENLOG_T_EVENT) {
        penlog_event_t e;
        (void)penlog_unpack_event(pl, l, &e);
        if (e.code < 16u) {
            s->ev_count[e.code]++;
        }
        if (e.code == PEN_EV_FAULT_SET) {
            s->last_fault_arg = e.arg;
        }
    }
}

static void sys_init(sys_t *s, bool wdt_reset)
{
    memset(s, 0, sizeof(*s));
    hal_host_reset();
    g_hal.reset_was_wdt = wdt_reset;
    plant_init(&s->pl, 3.7, 25.0);
    pen_app_init(&s->app, PEN_PROFILE_BALANCED, wdt_reset);
    pen_app_set_sink(&s->app, sink, s, true);
    /* pen at 50 deg altitude, still, above/on the page origin */
    const double th = 50.0 * 3.141592653589793 / 180.0;
    s->sens.imu_acc_h[0] = (float)(-9.80665 * cos(th));
    s->sens.imu_acc_h[2] = (float)(9.80665 * sin(th));
    s->sens.imu_dt = 1.0f / 3840.0f;
    s->f_load = 0.5;
}

static void sys_tick(sys_t *s)
{
    g_hal.time_us += 500u;
    /* contact and optics */
    s->pl.f_ax = s->pen_down ? 1.0 : PEN_F_PRE;
    s->pl.f_ext[0] = s->pen_down ? s->f_load : 0.0;
    s->sens.opt_valid = s->pen_down;
    s->sens.opt_valid_bits = s->pen_down ? 0x07u : 0x00u;
    s->sens.opt_surface_lost = !s->pen_down;
    plant_hall(&s->pl, s->sens.hall_raw);
    s->sens.hall_fresh = true;
    pen_app_stage_tick(&s->app, &s->sens);
    for (int k = 0; k < PEN_PWM_PER_STAGE; k++) {
        /* VMOT exists only when ACT_EN = REQ & FAULT_N & NOCHG and the drivers are awake */
        const bool powered = hal_host_act_en() && g_hal.drv_sleep_n;
        s->pl.vm = powered ? 3.7 : 0.0;
        bridge_cmd_t cmd[2] = {g_hal.bridge[0], g_hal.bridge[1]};
        if (!powered) {
            memset(cmd, 0, sizeof(cmd));
        }
        int16_t ae[2], ac[2];
        plant_period(&s->pl, cmd, ae, ac);
        pen_app_current_isr(&s->app, ac, ae);
    }
}

static void run(sys_t *s, int ticks)
{
    for (int k = 0; k < ticks; k++) {
        sys_tick(s);
    }
}

/* boot, arm at pen-up, pen down, ASSIST_KF for 1 s */
static void to_assist(sys_t *s, bool wdt)
{
    sys_init(s, wdt);
    s->pen_down = false;
    run(s, 100);
    s->app.req.arm = true;
    run(s, 10);
    s->app.req.assist = PEN_MODE_ASSIST_KF;
    s->pen_down = true;
    run(s, 2000);
}

void test_system_hall_frozen_detect(void)
{
    sys_t *s = &g_sys;
    to_assist(s, false);
    CHECK(s->app.sm.mode == PEN_MODE_ASSIST_KF);
    CHECK(s->app.in_contact && hal_host_act_en());
    const float i_before = s->app.iref_out[0];
    const double q_before = s->pl.q[0];
    CHECK(fabs((double)i_before - s->f_load / (PEN_N_LEVER * PEN_KF20)) < 0.02);
    /* the TMAG5170 output freezes */
    s->pl.hall_frozen = true;
    int k_det = -1;
    for (int k = 0; k < 40; k++) {
        sys_tick(s);
        if ((s->app.sf.faults & PEN_FAULT_HALL) != 0u) {
            k_det = k;
            break;
        }
    }
    CHECK(k_det >= 0);
    const double latency_ms = (k_det + 1) * 0.5;
    CHECK(latency_ms <= 5.0);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE && s->app.sm.act == SM_ACT_HOLD_OL);
    CHECK(fabsf(s->app.iref_out[0] - i_before) < 0.02f);   /* last good references, open loop */
    CHECK(hal_host_act_en());                             /* not de-energised in contact */
    run(s, 400);                                          /* 200 ms holding */
    const double q_drift = fabs(s->pl.q[0] - q_before);
    CHECK(q_drift < 20e-6);
    CHECK(s->app.sm.act == SM_ACT_HOLD_OL);
    /* pen-up (optical surface lost, since F_ax is from the frozen sensor) -> ramp -> off */
    s->pen_down = false;
    run(s, 40 + 60 + 4);
    CHECK(s->app.sm.act == SM_ACT_OFF && !hal_host_act_en());
    /* self-check fails while the sensor stays frozen */
    run(s, 100);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE);
    /* sensor alive again -> STANDBY */
    s->pl.hall_frozen = false;
    run(s, 20);
    CHECK(s->app.sm.mode == PEN_MODE_STANDBY && s->app.sf.faults == 0u);
    CHECK(s->ev_count[PEN_EV_FAULT_SET] >= 1u && (s->last_fault_arg & PEN_FAULT_HALL) != 0);
    CHECK(s->ev_count[PEN_EV_FAULT_CLEARED] >= 1u);
    CHECK(s->n_bad == 0u && s->n_rec[PENLOG_T_RESEARCH] > 2000u && s->n_rec[PENLOG_T_STROKE] > 100u);
    tr_log("system (app + plant): frozen TMAG5170 detected %.1f ms after the freeze (budget 5 ms); held i_ref %.3f A "
           "(before %.3f A); stage drift over 200 ms of open-loop hold under a constant %.2f N load %.2f um; "
           "de-energised only after the optical pen-up + %.0f ms ramp; recovery via self-check",
           latency_ms, (double)s->app.iref_out[0], (double)i_before, s->f_load, q_drift * 1e6,
           (double)PEN_RAMP_DOWN_TIME * 1e3);
    tr_log("log stream: %u research frames, %u stroke samples, %u events, %u bad records", (unsigned)s->n_rec[1],
           (unsigned)s->n_rec[2], (unsigned)s->n_rec[3], (unsigned)s->n_bad);
}

void test_system_fault_sequences(void)
{
    sys_t *s = &g_sys;
    /* (a) over-current latch in contact: hardware removes VMOT, firmware coasts */
    to_assist(s, false);
    hal_host_set_overcurrent(true);
    run(s, 2);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE && s->app.sm.act == SM_ACT_OFF);
    CHECK(!hal_host_act_en() && !g_hal.act_en_req);
    hal_host_set_overcurrent(false);   /* comparator released (the latch stays set) */
    run(s, 50);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE);   /* waits for pen-up */
    s->pen_down = false;
    run(s, 60);
    CHECK(s->app.sm.mode == PEN_MODE_STANDBY && hal_fault_n() && g_hal.clr_pulses >= 1u &&
          g_hal.clr_while_req_high == 0u);
    tr_log("(a) over-current: coast within 1 tick, latch cleared at pen-up (ACT_EN_REQ low -> FAULT_CLR_N -> "
           "FAULT_N high), STANDBY");

    /* (b) low battery in contact: fade, stay energised until pen-up, then ramp */
    to_assist(s, false);
    g_hal.vbat = 3.20f;
    int k_f = -1;
    for (int k = 0; k < 1000 && k_f < 0; k++) {
        sys_tick(s);
        if ((s->app.sf.faults & PEN_FAULT_LOWBAT) != 0u) {
            k_f = k;
        }
    }
    CHECK(k_f > 0);
    run(s, 400);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE && s->app.sm.act == SM_ACT_NEUTRAL);
    CHECK(hal_host_act_en() && s->app.ctrl.g_eff < 0.01f);
    CHECK(fabs(s->pl.q[0]) < 30e-6);   /* still holding the contact load */
    s->pen_down = false;
    run(s, 40 + 62);
    CHECK(s->app.sm.act == SM_ACT_OFF && !hal_host_act_en());
    run(s, 20);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE);   /* battery still low */
    g_hal.vbat = 3.70f;
    run(s, 100);
    CHECK(s->app.sm.mode == PEN_MODE_STANDBY);
    tr_log("(b) low battery at 3.20 V: fault after %.0f ms, neutral hold in contact (stage held, authority 0), "
           "de-energised after pen-up + ramp, STANDBY when VBAT recovers", (k_f + 1) * 0.5);

    /* (c) soft fault, pen stays down: timeout 5 s, then ramp in contact */
    to_assist(s, false);
    s->app.sf.faults = (uint16_t)(s->app.sf.faults | PEN_FAULT_OPTICAL);   /* inject the latched fault */
    run(s, 10);
    CHECK(s->app.sm.act == SM_ACT_NEUTRAL);
    run(s, (int)(PEN_PENUP_TIMEOUT / PEN_TS_STAGE));
    CHECK(s->app.sm.act == SM_ACT_OFF && !hal_host_act_en());
    tr_log("(c) soft fault with the pen kept down: de-energised after the %.0f s timeout (ICD s6)",
           (double)PEN_PENUP_TIMEOUT);

    /* (d) watchdog reset: fault bit 5 at boot, STANDBY after pen-up self-check */
    sys_init(s, true);
    run(s, 2);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE && (s->app.sf.faults & PEN_FAULT_WATCHDOG) != 0u);
    run(s, 60);
    CHECK(s->app.sm.mode == PEN_MODE_STANDBY);

    /* (e) charging interlock: VMOT removed by hardware, re-arming refused while charging */
    to_assist(s, false);
    g_hal.chg_det = true;
    run(s, 2);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE && s->app.sm.act == SM_ACT_OFF && !hal_host_act_en());
    s->pen_down = false;
    run(s, 100);
    CHECK(s->app.sm.mode == PEN_MODE_SAFE_PASSIVE);
    g_hal.chg_det = false;
    run(s, 20);
    CHECK(s->app.sm.mode == PEN_MODE_STANDBY);
    s->app.req.arm = true;
    run(s, 5);
    CHECK(s->app.sm.mode == PEN_MODE_NEUTRAL_HOLD);
    CHECK(s->n_bad == 0u);
    CHECK(g_hal.wdt_kicks > 1000u);
    tr_log("(d) watchdog-reset boot -> SAFE_PASSIVE -> STANDBY; (e) charging: off, re-arm only after unplug; "
           "watchdog kicked %u times (only while the current ISR runs)", (unsigned)g_hal.wdt_kicks);
}
