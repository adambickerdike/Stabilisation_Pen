/*
 * app.c - firmware application layer (see header).
 * Status: PROPOSED DESIGN; exercised on the host with the C plant
 * (tests/test_system.c) and compiled for the nRF5340. Not run on hardware.
 */
#include "app.h"

#include <math.h>
#include <string.h>

#include "hal.h"
#include "mathx.h"

#define TS PEN_TS_STAGE

/* ------------------------------------------------------------------ logging */
static void emit(pen_app_t *a, uint8_t type, const uint8_t *payload, size_t len)
{
    if (a->sink == NULL) {
        return;
    }
    uint8_t rec[PENLOG_MAX_PAYLOAD + PENLOG_REC_OVERHEAD];
    const size_t n = penlog_encode_record(type, payload, len, rec, sizeof(rec));
    if (n == 0u) {
        a->log_drops++;
        return;
    }
    a->sink(rec, n, a->sink_ctx);
}

static void log_event(pen_app_t *a, uint32_t t_us, uint16_t code, int32_t arg)
{
    penlog_event_t e = {t_us, code, arg};
    uint8_t p[PENLOG_EVENT_LEN];
    penlog_pack_event(&e, p);
    emit(a, PENLOG_T_EVENT, p, sizeof(p));
}

void pen_app_set_sink(pen_app_t *a, pen_log_sink_t sink, void *ctx, bool research_frames)
{
    a->sink = sink;
    a->sink_ctx = ctx;
    a->log_research = research_frames;
}

/* ------------------------------------------------------------------ ML hook */
__attribute__((weak)) bool pen_ml_predict(const float dp_um[PEN_ML_WINDOW][2], float d_um[2], bool *nan_or_inf,
                                          bool *saturated)
{
    (void)dp_um;
    d_um[0] = 0.0f;
    d_um[1] = 0.0f;
    *nan_or_inf = false;
    *saturated = false;
    return false;   /* no model linked */
}

/* ------------------------------------------------------------------ init */
void pen_app_init(pen_app_t *a, pen_profile_t profile, bool reset_by_watchdog)
{
    memset(a, 0, sizeof(*a));
    ctrl_init(&a->ctrl, profile);
    cl_init(&a->cl);
    thermal_init(&a->th, PEN_T_AMB);
    safety_init(&a->sf);
    safety_boot(&a->sf, reset_by_watchdog);
    sm_init(&a->sm);
    ml_guard_init(&a->mlg);
    ml_window_init(&a->mlw);
    fusion_init(&a->fu, (uint16_t)PEN_FUSION_LAG_TICKS);
    cal_hall_default(&a->hall_cal);
    cal_user_default(&a->user);
    a->ctrl.prm.f_gate = a->user.f_gate_hz;
    a->ctrl.prm.f_gate_width = a->user.f_gate_width_hz;
    a->ctrl.prm.g_max = a->user.g_max;
    a->ctrl.prm.q_lim = a->user.q_lim_m;
    a->ctrl.prm.gamma = a->user.gamma;
    a->req.assist = PEN_MODE_NEUTRAL_HOLD;
    a->vbat_f = PEN_V_BAT_NOM;
    a->pen_up = true;
    a->mode_logged = PEN_MODE_OFF;
    a->offset_cal_pending = true;
    penlog_clock_start(&a->clk, hal_time_us());
    hal_act_en_req(false);
    hal_drv_sleep_n(false);
}

bool pen_app_apply_user_cal(pen_app_t *a, const cal_user_t *u)
{
    if (cal_user_validate(u) != CAL_OK) {
        return false;
    }
    a->user = *u;
    a->ctrl.prm.f_gate = u->f_gate_hz;
    a->ctrl.prm.f_gate_width = u->f_gate_width_hz;
    a->ctrl.prm.g_max = u->g_max;
    a->ctrl.prm.q_lim = u->q_lim_m;
    a->ctrl.prm.gamma = u->gamma;
    (void)penlog_clock_update(&a->clk, hal_time_us());
    log_event(a, penlog_clock_us32(&a->clk), PEN_EV_CAL_APPLIED, CAL_USER);
    return true;
}

/* ------------------------------------------------------------------ 40 kHz */
void pen_app_current_isr(pen_app_t *a, const int16_t adc_c[2], const int16_t adc_e[2])
{
    float iref[2] = {a->iref_cmd[0], a->iref_cmd[1]};
    a->cl.enabled = a->cl_enable;
    bridge_cmd_t cmd[2];
    cl_step(&a->cl, &a->ctrl.prm, iref, adc_c, adc_e, a->vbat_f, a->r_extra, cmd);
    hal_bridge_set(cmd);
    for (int ax = 0; ax < 2; ax++) {
        a->acc.i_sum[ax] += a->cl.i_meas[ax];
        a->acc.v_sum[ax] += a->cl.duty[ax] * a->cl.vm;
        const float ad = pen_absf(a->cl.duty[ax]);
        if (ad > a->acc.duty_abs_max) {
            a->acc.duty_abs_max = ad;
        }
    }
    if (a->cl.vsat[0] || a->cl.vsat[1]) {
        a->acc.vsat = true;
    }
    a->acc.n++;
    a->isr_count++;
}

/* ------------------------------------------------------------------ 2 kHz */
static pen_est_t est_for_mode(pen_mode_t m)
{
    switch (m) {
    case PEN_MODE_ASSIST_KF:
    case PEN_MODE_TRAINING_FADE:
        return PEN_EST_KF;
    case PEN_MODE_ASSIST_ML:
        return PEN_EST_ML;
    case PEN_MODE_GUIDED:
        return PEN_EST_GUIDED;
    default:
        return PEN_EST_NONE;
    }
}

void pen_app_stage_tick(pen_app_t *a, const pen_sensors_t *sens)
{
    const uint32_t t_hw = hal_time_us();
    const bool wrapped = penlog_clock_update(&a->clk, t_hw);
    const uint32_t t_us = penlog_clock_us32(&a->clk);   /* us since session start (log time base) */
    if (wrapped) {
        log_event(a, t_us, PEN_EV_TIME_WRAP, (int32_t)a->clk.wraps);   /* arg = cumulative wrap count */
    }
    safety_tick_begin(&a->sf);

    /* ---- 1. current-loop accumulators of the last 20 PWM periods ---- */
    float v_mean[2] = {0.0f, 0.0f};
    float duty_max;
    bool vsat;
    {
        const uint32_t st = hal_irq_save();
        const uint32_t n = a->acc.n;
        for (int ax = 0; ax < 2; ax++) {
            if (n > 0u) {
                a->i_mean[ax] = a->acc.i_sum[ax] / (float)n;
                v_mean[ax] = a->acc.v_sum[ax] / (float)n;
            }
        }
        duty_max = a->acc.duty_abs_max;
        vsat = a->acc.vsat;
        memset(&a->acc, 0, sizeof(a->acc));
        hal_irq_restore(st);
    }

    /* ---- 2. Hall -> q, s, F_ax and Hall checks ---- */
    hall_convert(&a->hall_cal, sens->hall_raw, a->i_mean, a->q, &a->s, &a->f_ax);
    (void)safety_hall_check(&a->sf, sens->hall_raw, sens->hall_fresh, a->q, a->i_mean);

    /* ---- 3. housing position fusion and attitude ---- */
    const uint8_t n_imu = (sens->imu_n <= 8u) ? sens->imu_n : 8u;
    for (uint8_t k = 0; k < n_imu; k++) {
        fusion_imu_sample(&a->fu, sens->imu_a_page_seq[k], sens->imu_dt);
    }
    fusion_optical_sample(&a->fu, sens->opt_p, sens->opt_valid);
    fusion_tick(&a->fu, a->ph, &a->opt_valid);
    fusion_attitude(&a->fu, sens->imu_acc_h, sens->imu_gyro_h, TS, 0.2f);

    /* ---- 4. contact and pen-up ---- */
    const bool hall_fault = (a->sf.faults & PEN_FAULT_HALL) != 0u;
    const bool contact_now = ctrl_contact(a->f_ax);
    if (contact_now != a->in_contact) {
        log_event(a, t_us, contact_now ? PEN_EV_PEN_DOWN : PEN_EV_PEN_UP, 0);
        if (contact_now) {
            a->stroke_id++;
        }
    }
    a->in_contact = contact_now;
    a->t_no_contact = contact_now ? 0.0f : a->t_no_contact + TS;
    a->t_lost = sens->opt_surface_lost ? a->t_lost + TS : 0.0f;
    if (hall_fault) {
        /* F_ax comes from the same (failed) sensor: use the optical lift */
        a->pen_up = a->t_lost >= PEN_PENUP_DEBOUNCE;
    } else {
        const bool was_up = a->pen_up;
        a->pen_up = a->t_no_contact >= PEN_PENUP_DEBOUNCE;
        if (a->pen_up && !was_up) {
            a->offset_cal_pending = true;   /* ISNS offset at every pen-lift */
        }
    }

    /* ---- 5. slow channels at 100 Hz: VBAT, NTC, thermal ---- */
    if ((a->tick % APP_SLOW_DECIM) == 0u) {
        const float dt_slow = TS * (float)APP_SLOW_DECIM;
        const float vb = hal_vbat_volts();
        (void)safety_battery_check(&a->sf, vb, dt_slow);
        a->vbat_f = a->sf.vbat_f;
        float t_ntc = 0.0f;
        const bool ntc_ok = thermal_ntc_degC(hal_ntc_ratio(), &t_ntc);
        const float speed = 0.0f;   /* stage speed from the servo derivative would go here */
        thermal_step(&a->th, dt_slow, a->i_mean, v_mean, speed, t_ntc, ntc_ok);
        for (int ax = 0; ax < 2; ax++) {
            a->r_extra[ax] = PEN_R20 * PEN_ALPHA_CU * (a->th.T[ax] - 20.0f);
        }
    }

    /* ---- 6. remaining detections ---- */
    const bool assisting = a->sm.g_cap > 0.0f;
    (void)safety_thermal_check(&a->sf, a->th.over_temp);
    (void)safety_overcurrent_check(&a->sf);
    (void)safety_charging_check(&a->sf, hal_chg_det());
    (void)safety_headroom_check(&a->sf, duty_max);
    (void)safety_optical_check(&a->sf, a->opt_valid, a->in_contact, assisting);
    /* ML predictor (ICD s5 v1.1): samples stamped at acquisition = tick time
     * minus the IMU group delay the fusion leaves */
    const uint32_t t_acq = t_hw - (uint32_t)lrintf(PEN_IMU_DELAY * 1e6f);
    ml_guard_realised(&a->mlg, a->ph, t_acq, a->opt_valid);
    if (!a->opt_valid) {
        ml_window_reset(&a->mlw);
    } else if ((a->tick % (uint32_t)PEN_ML_DECIM) == 0u) {
        ml_window_push(&a->mlw, a->ph, t_acq);
        static float dp[PEN_ML_WINDOW][2];
        uint32_t t_newest;
        if (a->ml_available && ml_window_export(&a->mlw, dp, &t_newest)) {
            float d_um[2];
            bool bad = false, sat = false;
            if (pen_ml_predict(dp, d_um, &bad, &sat)) {
                ml_guard_new_output(&a->mlg, d_um, bad, sat, t_newest, a->ctrl.prm.q_lim);
            }
        }
    }
    ml_guard_tick(&a->mlg, a->ctrl.kf.dhat, TS);
    if (a->mlg.event) {
        log_event(a, t_us, PEN_EV_AUTHORITY_CAPPED, (int32_t)a->mlg.reason);
        a->mlg.event = false;
    }
    if (a->mlg.trip) {
        (void)safety_ml_trip(&a->sf);
        a->mlg.trip = false;
    }
    if ((a->sf.faults & PEN_FAULT_OVERCURRENT) != 0u && a->sm.act == SM_ACT_OFF && a->pen_up) {
        (void)safety_oc_clear_step(&a->sf);
    }

    /* ---- 7. state machine ---- */
    sm_in_t si;
    memset(&si, 0, sizeof(si));
    si.dt = TS;
    si.boot_ok = true;
    si.pen_up = a->pen_up;
    si.arm_req = a->req.arm;
    si.disarm_req = a->req.disarm;
    si.off_req = a->req.off;
    si.assist_req = a->req.assist;
    si.faults = a->sf.faults;
    si.self_check_ok = safety_self_check(&a->sf);
    si.power_ok = safety_battery_ok(&a->sf) && !hal_chg_det();
    si.mode_perm = a->user.mode_perm;
    si.ml_available = a->ml_available;
    sm_step(&a->sm, &si);
    a->req.arm = false;
    a->req.disarm = false;
    a->req.off = false;
    if (a->sf.faults != a->faults_logged && a->sf.faults != 0u) {
        log_event(a, t_us, PEN_EV_FAULT_SET, (int32_t)a->sf.faults);
    }
    if (a->sm.clear_faults) {
        log_event(a, t_us, PEN_EV_FAULT_CLEARED, (int32_t)a->sf.faults);
        safety_clear(&a->sf);
        a->hold_captured = false;
    }
    a->faults_logged = a->sf.faults;
    if (a->sm.mode != a->mode_logged) {
        log_event(a, t_us, PEN_EV_MODE_CHANGE, (int32_t)((uint32_t)a->sm.mode | ((uint32_t)a->mode_logged << 8)));
        a->mode_logged = a->sm.mode;
    }

    /* ---- 8. control tick ---- */
    ctrl_in_t ci;
    memset(&ci, 0, sizeof(ci));
    ci.qm[0] = a->q[0];
    ci.qm[1] = a->q[1];
    ci.fa = a->f_ax;
    ci.ph[0] = a->ph[0];
    ci.ph[1] = a->ph[1];
    ci.opt_valid = a->opt_valid;
    ci.a_page[0] = sens->imu_a_page[0];
    ci.a_page[1] = sens->imu_a_page[1];
    ci.theta = a->fu.theta;
    ci.phi = a->fu.phi;
    ci.rho = a->fu.rho;
    ci.v_sat = vsat;
    ci.g_cap = pen_minf(a->sm.g_cap, a->th.derate);
    ci.i_max = a->ctrl.prm.i_max;
    ci.est = est_for_mode(a->sm.mode);
    ci.d_ml = a->mlg.d;
    ci.ml_mix = a->mlg.have ? a->mlg.mix : 0.0f;
    const bool hall_ok = (a->sf.faults & PEN_FAULT_HALL) == 0u;
    ci.servo_on = hall_ok && (a->sm.act == SM_ACT_SERVO || a->sm.act == SM_ACT_NEUTRAL || a->sm.act == SM_ACT_RAMP);
    if (a->cl.cal_state != CL_CAL_IDLE) {
        ci.servo_on = false;   /* bridges coast during the offset window */
    }
    ctrl_tick(&a->ctrl, &ci);

    /* ---- 9. actuator policy -> current references ---- */
    if (a->sf.faults & PEN_FAULT_HALL) {
        if (!a->hold_captured) {
            /* "last current references" (ICD s6): the mean of the APP_HOLD_AVG
             * references computed with a fresh sensor, i.e. before the stuck
             * run; a single sample carries the derivative-amplified Hall noise
             * (~6 mA rms), which the flexure alone (6.7 um/mN) would turn into
             * tens of um of drift */
            const uint32_t back = (uint32_t)PEN_HALL_STUCK_TICKS + 1u;
            if (a->iref_hist_n > back + APP_HOLD_AVG) {
                float s0 = 0.0f, s1 = 0.0f;
                for (uint32_t j = 0; j < APP_HOLD_AVG; j++) {
                    const uint32_t idx = (a->iref_hist_n - 1u - back - j) % APP_IREF_HIST;
                    s0 += a->iref_hist[idx][0];
                    s1 += a->iref_hist[idx][1];
                }
                a->iref_hold[0] = s0 / (float)APP_HOLD_AVG;
                a->iref_hold[1] = s1 / (float)APP_HOLD_AVG;
            } else {
                a->iref_hold[0] = a->iref_out[0];
                a->iref_hold[1] = a->iref_out[1];
            }
            a->hold_captured = true;
        }
    }
    float iref[2] = {0.0f, 0.0f};
    switch (a->sm.act) {
    case SM_ACT_SERVO:
    case SM_ACT_NEUTRAL:
        iref[0] = a->ctrl.servo.iref[0];
        iref[1] = a->ctrl.servo.iref[1];
        break;
    case SM_ACT_HOLD_OL:
        iref[0] = a->iref_hold[0];
        iref[1] = a->iref_hold[1];
        break;
    case SM_ACT_RAMP: {
        const float *base = hall_ok ? a->ctrl.servo.iref : a->iref_hold;
        iref[0] = base[0] * a->sm.ramp;
        iref[1] = base[1] * a->sm.ramp;
        break;
    }
    case SM_ACT_OFF:
    default:
        break;
    }
    const bool power = a->sm.act_en_req;
    hal_act_en_req(power && (a->sf.faults & PEN_FAULT_OVERCURRENT) == 0u);
    hal_drv_sleep_n(power);
    a->iref_out[0] = iref[0];
    a->iref_out[1] = iref[1];
    if (a->sm.act == SM_ACT_SERVO || a->sm.act == SM_ACT_NEUTRAL) {
        const uint32_t idx = a->iref_hist_n % APP_IREF_HIST;
        a->iref_hist[idx][0] = iref[0];
        a->iref_hist[idx][1] = iref[1];
        a->iref_hist_n++;
    }
    a->iref_cmd[0] = iref[0];
    a->iref_cmd[1] = iref[1];
    a->cl_enable = power;
    /* ISNS offset: coast window only when the stage is unloaded */
    if (a->offset_cal_pending && a->pen_up && a->cl.cal_state == CL_CAL_IDLE &&
        (a->sm.act == SM_ACT_OFF || a->sm.act == SM_ACT_SERVO || a->sm.act == SM_ACT_NEUTRAL)) {
        cl_request_offset_cal(&a->cl);
        a->offset_cal_pending = false;
    }

    /* ---- 10. watchdog: kick only if the current ISR is alive ---- */
    if (a->isr_count != a->isr_count_seen) {
        hal_watchdog_kick();
        a->isr_count_seen = a->isr_count;
    }

    /* ---- 11. logging ---- */
    if (a->log_research) {
        penlog_research_si_t r;
        memset(&r, 0, sizeof(r));
        r.t_us = t_us;
        for (int ax = 0; ax < 2; ax++) {
            r.q[ax] = a->q[ax];
            r.qr[ax] = a->ctrl.servo.qr[ax];
            r.i[ax] = a->i_mean[ax];
            r.iref[ax] = iref[ax];
            r.p_h[ax] = a->ph[ax] - a->page_origin[ax];   /* page-origin relative (ICD s4 note) */
            r.dhat[ax] = a->ctrl.dhat[ax];
            r.imu_a[ax] = sens->imu_a_page[ax];
        }
        r.f_ax = a->f_ax;
        r.opt_valid = sens->opt_valid_bits;
        r.g = a->ctrl.g_eff;
        r.f_est = kf_est_freq_hz(&a->ctrl.kf);
        r.mode = (uint8_t)a->sm.mode;
        uint16_t fl = 0;
        if (a->in_contact) fl |= PEN_FLAG_CONTACT;
        if (a->pen_up) fl |= PEN_FLAG_LIFT;
        if (vsat) fl |= PEN_FLAG_VSAT;
        if (hypotf(a->q[0], a->q[1]) >= PEN_Q_STOP) fl |= PEN_FLAG_STOP;
        if (a->sf.faults != 0u) fl |= PEN_FLAG_FAULT;
        if (a->sm.mode == PEN_MODE_ASSIST_ML && a->mlg.mix > 0.0f) fl |= PEN_FLAG_ML_ACTIVE;
        if (a->sm.mode == PEN_MODE_ASSIST_ML && a->mlg.fallback) fl |= PEN_FLAG_ML_REJECTED;
        if (a->th.derate < 1.0f) fl |= PEN_FLAG_THERMAL_DERATE;
        r.flags = fl;
        r.vbat = a->vbat_f;
        r.t_coil = thermal_max(&a->th);
        r.theta = a->fu.theta;
        r.phi = a->fu.phi;
        penlog_research_t raw;
        penlog_research_from_si(&r, &raw);
        if (!a->page_origin_set) {
            penlog_research_ph_undefined(&raw);
        }
        uint8_t p[PENLOG_RESEARCH_LEN];
        penlog_pack_research(&raw, p);
        emit(a, PENLOG_T_RESEARCH, p, sizeof(p));
    }
    /* ---- 12. capture layer (ICD s4.3): 200 Hz inside a stroke, plus one sample
     * at the pen-down tick and one at the last in-contact tick (pen-up) ---- */
    if (a->in_contact) {
        /* deposited-ink position = p_H + J q (page frame, origin = first pen-down) */
        float dpage[2];
        jac_stage_to_page(&a->ctrl.jac, a->q, dpage);
        const float x = a->ph[0] + dpage[0];
        const float y = a->ph[1] + dpage[1];
        if (!a->page_origin_set) {
            a->page_origin[0] = x;
            a->page_origin[1] = y;
            a->page_origin_set = true;
        }
        penlog_stroke_t s;
        penlog_stroke_from_si(penlog_clock_ms32(&a->clk), a->stroke_id, x - a->page_origin[0],
                              y - a->page_origin[1], a->f_ax, a->fu.theta, a->fu.phi, &s);
        const bool down_edge = !a->cap_prev_contact;
        if (down_edge) {
            a->cap_phase = 0;
        }
        a->cap_last_emitted = (a->cap_phase % 10u) == 0u;   /* includes the pen-down tick */
        if (a->cap_last_emitted) {
            uint8_t p[PENLOG_STROKE_LEN];
            penlog_pack_stroke(&s, p);
            emit(a, PENLOG_T_STROKE, p, sizeof(p));
            if (down_edge) {
                a->n_stroke_boundary++;
            }
        }
        a->cap_phase++;
        a->cap_last = s;
    } else if (a->cap_prev_contact && !a->cap_last_emitted) {
        uint8_t p[PENLOG_STROKE_LEN];
        penlog_pack_stroke(&a->cap_last, p);   /* pen-up boundary sample */
        emit(a, PENLOG_T_STROKE, p, sizeof(p));
        a->n_stroke_boundary++;
    }
    a->cap_prev_contact = a->in_contact;
    a->tick++;
}
