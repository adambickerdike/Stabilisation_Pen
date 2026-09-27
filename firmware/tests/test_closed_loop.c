/*
 * test_closed_loop.c - 2 kHz stage servo + 40 kHz current loop on the C plant
 * (switched bridge, RL coil, lever, stage, delayed noisy Hall).
 * Evidence status: HOST TEST on a model (in air, no paper contact), not hardware.
 */
#include <math.h>
#include <string.h>

#include "current_loop.h"
#include "hall.h"
#include "params.h"
#include "plant.h"
#include "servo.h"
#include "tr.h"

#define PI_D 3.141592653589793

typedef struct {
    plant_t pl;
    curloop_t cl;
    servo_t sv;
    pen_ctrl_params_t p;
    cal_hall_t cal;
    bridge_cmd_t cmd[2];
    bool vsat_tick;
    uint32_t vsat_ticks;
    float duty_tick_max, duty_max;
    uint32_t isat_ticks;
    float i_mean[2];
    double inj;          /* force injected after the servo, x axis (N) */
    double f_servo;      /* servo force this tick (x) */
} rig_t;

static void rig_init(rig_t *r, double vm, double temp_c, bool ff_ref, bool noise)
{
    memset(r, 0, sizeof(*r));
    plant_init(&r->pl, vm, temp_c);
    if (!noise) {
        r->pl.adc_noise_a = 0.0;
        r->pl.hall_noise_m = 0.0;
    }
    cl_init(&r->cl);
    r->cl.enabled = true;
    servo_init(&r->sv);
    pen_params_default(&r->p, PEN_PROFILE_BALANCED);
    r->p.ff_ref = ff_ref ? 1.0f : 0.0f;
    r->p.ff_accel = 0.0f;
    cal_hall_default(&r->cal);
}

static void rig_tick(rig_t *r, const float qr[2])
{
    int16_t raw[3];
    plant_hall(&r->pl, raw);
    float q[2], s, fa;
    hall_convert(&r->cal, raw, r->i_mean, q, &s, &fa);
    servo_push_ref(&r->sv, qr);
    servo_in_t in;
    memset(&in, 0, sizeof(in));
    in.qm[0] = q[0];
    in.qm[1] = q[1];
    in.fa = fa;
    in.lam_hat = 1.0f;
    in.ct = cosf(0.8726646f);
    in.st = sinf(0.8726646f);
    in.cr = 1.0f;
    in.v_sat = r->vsat_tick;
    in.i_max = PEN_I_MAX;
    servo_step(&r->sv, &r->p, &in);
    r->f_servo = (double)r->sv.force[0];
    float iref[2] = {r->sv.iref[0], r->sv.iref[1]};
    if (r->inj != 0.0) {
        const double ft = r->f_servo + r->inj;
        iref[0] = (float)(-ft / ((double)PEN_N_LEVER * (double)PEN_KF20));
    }
    if (r->sv.sat_i[0] || r->sv.sat_i[1]) {
        r->isat_ticks++;
    }
    r->vsat_tick = false;
    r->duty_tick_max = 0.0f;
    double isum[2] = {0.0, 0.0};
    int16_t ae[2], ac[2];
    for (int k = 0; k < PEN_PWM_PER_STAGE; k++) {
        plant_period(&r->pl, r->cmd, ae, ac);
        cl_step(&r->cl, &r->p, iref, ac, ae, (float)r->pl.vm, NULL, r->cmd);
        if (r->cl.vsat[0] || r->cl.vsat[1]) {
            r->vsat_tick = true;
        }
        for (int ax = 0; ax < 2; ax++) {
            const float d = fabsf(r->cl.duty[ax]);
            r->duty_tick_max = d > r->duty_tick_max ? d : r->duty_tick_max;
            isum[ax] += (double)r->cl.i_meas[ax];
        }
    }
    r->i_mean[0] = (float)(isum[0] / PEN_PWM_PER_STAGE);
    r->i_mean[1] = (float)(isum[1] / PEN_PWM_PER_STAGE);
    if (r->vsat_tick) {
        r->vsat_ticks++;
    }
    r->duty_max = r->duty_tick_max > r->duty_max ? r->duty_tick_max : r->duty_max;
}

void test_closed_loop_step_response(void)
{
    rig_t r;
    rig_init(&r, 3.7, 25.0, false, false);
    const double A = 50e-6;
    static double qlog[600];
    const float zero[2] = {0.0f, 0.0f}, step[2] = {(float)A, 0.0f};
    for (int k = 0; k < 200; k++) {
        rig_tick(&r, zero);
    }
    for (int k = 0; k < 600; k++) {
        rig_tick(&r, step);
        qlog[k] = r.pl.q[0];
    }
    int k10 = -1, k90 = -1, k_set = 0;
    double peak = 0.0;
    for (int k = 0; k < 600; k++) {
        if (k10 < 0 && qlog[k] >= 0.1 * A) k10 = k;
        if (k90 < 0 && qlog[k] >= 0.9 * A) k90 = k;
        peak = qlog[k] > peak ? qlog[k] : peak;
    }
    for (int k = 599; k >= 0; k--) {
        if (fabs(qlog[k] - A) > 0.02 * A) {
            k_set = k + 1;
            break;
        }
    }
    const double tr_ms = (k90 - k10) * 0.5, ts_ms = k_set * 0.5, os = 100.0 * (peak - A) / A;
    const double ss = qlog[599] - A;
    CHECK(k10 >= 0 && k90 >= 0);
    CHECK(tr_ms > 1.0 && tr_ms < 10.0);
    CHECK(os < 60.0);
    CHECK(ts_ms < 100.0);
    CHECK(fabs(ss) < 0.01 * A);
    CHECK(r.vsat_ticks == 0u && r.isat_ticks == 0u);
    tr_log("50 um step, feedback only (ff_ref = 0), 3.7 V, noise off: 10-90%% rise %.1f ms, overshoot %.1f %%, "
           "2%% settling %.1f ms, final error %.3f um; no current or voltage saturation", tr_ms, os, ts_ms, 1e6 * ss);
    tr_log("(the PID acts on the error, so its zeros at ~0.38 x pos_bw give overshoot even with zeta 0.7;"
           " the firmware reference passes the 0.08 m/s slew limit and the reference feedforward)");
}

static void freq_response(bool ff_ref, double f, double *gain, double *phase_deg)
{
    rig_t r;
    rig_init(&r, 3.7, 25.0, ff_ref, false);
    const double A = 10e-6, w = 2.0 * PI_D * f;
    const int n_settle = 200;
    double cycles = ceil(0.25 * f);
    if (cycles < 8.0) {
        cycles = 8.0;
    }
    const int per = (int)lround(cycles * 2000.0 / f);
    double sr = 0.0, cr = 0.0, sq = 0.0, cq = 0.0;
    for (int k = 0; k < n_settle + per; k++) {
        const double t = k * 5e-4;
        const float qr[2] = {(float)(A * sin(w * t)), 0.0f};
        rig_tick(&r, qr);
        if (k >= n_settle) {
            sq += r.pl.q[0] * sin(w * t);
            cq += r.pl.q[0] * cos(w * t);
            sr += (double)qr[0] * sin(w * t);
            cr += (double)qr[0] * cos(w * t);
        }
    }
    *gain = hypot(sq, cq) / hypot(sr, cr);
    *phase_deg = (atan2(cq, sq) - atan2(cr, sr)) * 180.0 / PI_D;
    while (*phase_deg > 180.0) *phase_deg -= 360.0;
    while (*phase_deg < -180.0) *phase_deg += 360.0;
}

void test_closed_loop_bandwidth(void)
{
    const double fr[] = {5.0, 10.0, 20.0, 40.0, 60.0, 80.0, 100.0, 130.0, 160.0, 200.0, 250.0, 300.0};
    const int nf = (int)(sizeof(fr) / sizeof(fr[0]));
    double g_fb[12], p_fb[12], g_ff[12], p_ff[12];
    for (int k = 0; k < nf; k++) {
        freq_response(false, fr[k], &g_fb[k], &p_fb[k]);
        freq_response(true, fr[k], &g_ff[k], &p_ff[k]);
    }
    double f3 = -1.0, peak = 0.0, fpk = 0.0;
    for (int k = 0; k < nf; k++) {
        if (g_fb[k] > peak) {
            peak = g_fb[k];
            fpk = fr[k];
        }
        if (f3 < 0.0 && k > 0 && g_fb[k] < 0.70710678 && g_fb[k - 1] >= 0.70710678) {
            const double a = log(g_fb[k - 1]), b = log(g_fb[k]), t = (log(0.70710678) - a) / (b - a);
            f3 = exp(log(fr[k - 1]) + t * (log(fr[k]) - log(fr[k - 1])));
        }
    }
    for (int k = 0; k < nf; k++) {
        tr_log("f %5.1f Hz: feedback only |T| %.3f (%7.1f deg) | with reference FF |T| %.3f (%7.1f deg)", fr[k],
               g_fb[k], p_fb[k], g_ff[k], p_ff[k]);
    }
    /* tremor band 4-12 Hz: tracking within a few % with the reference FF */
    CHECK(fabs(g_ff[0] - 1.0) < 0.03 && fabs(g_ff[1] - 1.0) < 0.03);
    CHECK(fabs(p_ff[0]) < 5.0 && fabs(p_ff[1]) < 5.0);
    CHECK(f3 > 60.0 && f3 < 300.0);          /* stable, band-limited */
    CHECK(20.0 * log10(peak) < 6.0);
    tr_log("closed-loop q/q_r (feedback only): -3 dB at %.0f Hz, resonance peak %.2f dB at %.0f Hz; "
           "design pos_bw %.0f Hz is the PID natural frequency", f3, 20.0 * log10(peak), fpk, (double)PEN_POS_BW_HZ);
}

/* loop gain L(jw) = -F_servo / F_total by force injection after the servo */
static void loop_gain(double f, double *mag, double *ph_deg)
{
    rig_t r;
    rig_init(&r, 3.7, 25.0, false, false);
    const double D = 0.02, w = 2.0 * PI_D * f;
    const float zero[2] = {0.0f, 0.0f};
    double cycles = ceil(0.3 * f);
    if (cycles < 10.0) {
        cycles = 10.0;
    }
    const int per = (int)lround(cycles * 2000.0 / f);
    double ss = 0.0, cs = 0.0, st = 0.0, ct = 0.0;
    for (int k = 0; k < 300 + per; k++) {
        const double t = k * 5e-4;
        r.inj = D * sin(w * t);
        rig_tick(&r, zero);
        if (k >= 300) {
            const double fs = r.f_servo, ftot = r.f_servo + r.inj;
            ss += fs * sin(w * t);
            cs += fs * cos(w * t);
            st += ftot * sin(w * t);
            ct += ftot * cos(w * t);
        }
    }
    /* complex ratio -FS/FT */
    const double re_s = ss, im_s = cs, re_t = st, im_t = ct;
    const double den = re_t * re_t + im_t * im_t;
    const double re = -(re_s * re_t + im_s * im_t) / den, im = -(im_s * re_t - re_s * im_t) / den;
    *mag = hypot(re, im);
    *ph_deg = atan2(im, re) * 180.0 / PI_D;
}

void test_closed_loop_margins(void)
{
    const double fr[] = {30.0, 45.0, 60.0, 75.0, 90.0, 110.0, 130.0, 160.0, 200.0, 250.0, 320.0, 400.0};
    const int nf = (int)(sizeof(fr) / sizeof(fr[0]));
    double m[12], ph[12];
    for (int k = 0; k < nf; k++) {
        loop_gain(fr[k], &m[k], &ph[k]);
        /* unwrap to a continuous phase below 0 */
        while (ph[k] > 0.0) ph[k] -= 360.0;
        if (k > 0) {
            while (ph[k] > ph[k - 1] + 180.0) ph[k] -= 360.0;
            while (ph[k] < ph[k - 1] - 180.0) ph[k] += 360.0;
        }
    }
    double fc = -1.0, pm = 0.0, fg = -1.0, gm_db = 0.0;
    for (int k = 1; k < nf; k++) {
        if (fc < 0.0 && m[k - 1] >= 1.0 && m[k] < 1.0) {
            const double t = log(m[k - 1]) / (log(m[k - 1]) - log(m[k]));
            fc = exp(log(fr[k - 1]) + t * (log(fr[k]) - log(fr[k - 1])));
            pm = 180.0 + ph[k - 1] + t * (ph[k] - ph[k - 1]);
        }
        if (fg < 0.0 && ph[k - 1] > -180.0 && ph[k] <= -180.0) {
            const double t = (ph[k - 1] + 180.0) / (ph[k - 1] - ph[k]);
            fg = exp(log(fr[k - 1]) + t * (log(fr[k]) - log(fr[k - 1])));
            gm_db = -20.0 * (log10(m[k - 1]) + t * (log10(m[k]) - log10(m[k - 1])));
        }
    }
    for (int k = 0; k < nf; k++) {
        tr_log("L(j2pi %5.1f Hz): |L| %.3f  phase %7.1f deg", fr[k], m[k], ph[k]);
    }
    CHECK(fc > 0.0);
    CHECK(pm > 20.0);          /* robustly stable on the model */
    CHECK(fg < 0.0 || gm_db > 3.0);
    const bool req = pm >= 40.0 && (fg < 0.0 || gm_db >= 6.0);
    tr_log("loop margins (unloaded host plant; Hall 0.1 ms delay, 2 kHz ZOH, 40 kHz current loop, derivative filter): "
           "crossover %.1f Hz, phase margin %.1f deg, phase crossover %.1f Hz, gain margin %.1f dB -> REQ-CTRL-002 "
           "(PM >= 40 deg, GM >= 6 dB) %s on this model", fc, pm, fg, gm_db, req ? "met" : "NOT MET");
}

typedef struct {
    double i_hold, v_need, duty_dc;
    float dmax_static, dmax_motion;
    uint32_t clamp_static, clamp_motion;
    uint32_t headroom_run_max;   /* longest run of ticks with max |duty| > 0.95 */
    double qerr;
} hold_res_t;

static void hold_case(double vm, double temp_c, bool noise, hold_res_t *h)
{
    const double F = (double)PEN_I_HOLD_DESIGN * PEN_N_LEVER * PEN_KF20;
    rig_t r;
    rig_init(&r, vm, temp_c, true, noise);
    r.pl.f_ext[0] = F;
    const float zero[2] = {0.0f, 0.0f};
    for (int k = 0; k < 600; k++) {
        rig_tick(&r, zero);
    }
    memset(h, 0, sizeof(*h));
    r.duty_max = 0.0f;
    r.vsat_ticks = 0;
    for (int k = 0; k < 200; k++) {
        rig_tick(&r, zero);
        h->i_hold += r.pl.i_sum[0] * PEN_F_PWM_HZ / 200.0;
        h->qerr = fmax(h->qerr, fabs(r.pl.q[0]));
    }
    h->dmax_static = r.duty_max;
    h->clamp_static = r.vsat_ticks;
    r.duty_max = 0.0f;
    r.vsat_ticks = 0;
    uint32_t run = 0;
    for (int k = 0; k < 2000; k++) {
        const double t = k * 5e-4;
        const float qr[2] = {(float)(3e-4 * sin(2.0 * PI_D * 8.0 * t)), 0.0f};
        rig_tick(&r, qr);
        run = (r.duty_tick_max > PEN_DUTY_HEADROOM) ? run + 1u : 0u;
        h->headroom_run_max = run > h->headroom_run_max ? run : h->headroom_run_max;
    }
    h->dmax_motion = r.duty_max;
    h->clamp_motion = r.vsat_ticks;
    h->v_need = h->i_hold * (r.pl.r_coil + r.pl.r_ext);
    h->duty_dc = h->v_need / (vm - (double)PEN_R_LOAD_SWITCH * h->i_hold);
}

void test_closed_loop_hold_no_vsat(void)
{
    /* design point (drive_sense.json): 0.76 N transverse tip load (50 deg, 1 N,
     * mu 0.15, worst direction), plus a 0.3 mm 8 Hz correction on top */
    const double F = (double)PEN_I_HOLD_DESIGN * PEN_N_LEVER * PEN_KF20;
    hold_res_t nom, cor, cor_q;
    hold_case(3.7, 25.0, true, &nom);   /* nominal cell, cool coil */
    hold_case(3.3, 85.0, true, &cor);   /* minimum actuation voltage, hot coil */
    hold_case(3.3, 85.0, false, &cor_q);
    /* nominal: no clamp at all, duty well inside the headroom threshold */
    CHECK(nom.clamp_static == 0u && nom.clamp_motion == 0u);
    CHECK(nom.dmax_motion < PEN_DUTY_HEADROOM);
    CHECK(nom.qerr < 10e-6);
    /* corner: the DC operating point is inside the headroom threshold and the
     * ICD headroom fault (> 0.95 on every tick for > 50 ms) is not reached */
    CHECK(cor.duty_dc < PEN_DUTY_HEADROOM);
    CHECK(cor_q.clamp_static == 0u && cor_q.dmax_static < PEN_DUTY_HEADROOM);
    CHECK((double)cor.headroom_run_max * 0.5 < 50.0);
    tr_log("design hold force %.3f N (i = %.3f A at Kf20):", F, (double)PEN_I_HOLD_DESIGN);
    tr_log("  3.7 V, 25 degC: mean %.3f A, DC duty %.3f; max |duty| static %.3f, with 0.3 mm 8 Hz motion %.3f; "
           "clamp ticks %u/%u", nom.i_hold, nom.duty_dc, (double)nom.dmax_static, (double)nom.dmax_motion,
           (unsigned)nom.clamp_static, (unsigned)nom.clamp_motion);
    tr_log("  3.3 V, 85 degC (R x1.255, Kf x0.922 magnet tempco): mean %.3f A, V %.2f V, DC duty %.3f; noise off: "
           "max |duty| %.3f, clamp ticks %u", cor.i_hold, cor.v_need, cor.duty_dc, (double)cor_q.dmax_static,
           (unsigned)cor_q.clamp_static);
    tr_log("  3.3 V, 85 degC with Hall/ADC noise: max |duty| static %.3f (clamp ticks %u); with 0.3 mm 8 Hz motion "
           "%.3f, clamp ticks %u of 2000, longest run > 0.95: %.1f ms (fault needs > 50 ms)", (double)cor.dmax_static,
           (unsigned)cor.clamp_static, (double)cor.dmax_motion, (unsigned)cor.clamp_motion,
           (double)cor.headroom_run_max * 0.5);
    if (cor.clamp_motion > 0u || cor.dmax_motion > PEN_DUTY_HEADROOM) {
        tr_log("  FINDING: at the 3.3 V / 85 degC corner the correction peaks exceed the %.2f headroom threshold%s; "
               "drive_sense.py's headroom check omits the magnet tempco (+8.5 %% current) and the flexure/inertia "
               "force of the correction", (double)PEN_DUTY_HEADROOM, cor.clamp_motion > 0u ? " and reach the clamp" : "");
    } else {
        tr_log("  3.3 V / 85 degC corner: correction peaks stay below the %.2f headroom threshold (margin %.3f of "
               "duty); drive_sense.py's headroom check still omits the magnet tempco (+8.5 %% current) and the "
               "correction force", (double)PEN_DUTY_HEADROOM, (double)(PEN_DUTY_HEADROOM - cor.dmax_motion));
    }
}
