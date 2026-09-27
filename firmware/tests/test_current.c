/*
 * test_current.c - 40 kHz current loop on the switched-bridge plant.
 */
#include <math.h>
#include <string.h>

#include "current_loop.h"
#include "params.h"
#include "plant.h"
#include "tr.h"

static float clamp_duty(float d)
{
    return d > PEN_DUTY_MAX ? PEN_DUTY_MAX : (d < -PEN_DUTY_MAX ? -PEN_DUTY_MAX : d);
}

void test_current_loop_bridge_mapping(void)
{
    const float duties[] = {-1.2f, -0.97f, -0.5f, -0.004f, 0.0f, 0.0025f, 0.3f, 0.5f, 0.949f, 0.97f, 1.2f};
    uint32_t bad = 0;
    for (size_t k = 0; k < sizeof(duties) / sizeof(duties[0]); k++) {
        bridge_cmd_t b;
        float da;
        cl_duty_to_bridge(duties[k], PEN_DUTY_MAX, &b, &da);
        /* count forward / reverse / brake / coast clock ticks as the plant does */
        int fwd = 0, rev = 0, brk = 0, cst = 0, first_fwd = -1, last_fwd = -1;
        for (int t = 0; t < PLANT_TICKS; t++) {
            const bool in1 = (t < b.in1_high) || (t >= PLANT_TICKS - b.in1_high);
            const bool in2 = (t < b.in2_high) || (t >= PLANT_TICKS - b.in2_high);
            if (in1 && !in2) {
                fwd++;
                if (first_fwd < 0) first_fwd = t;
                last_fwd = t;
            } else if (!in1 && in2) {
                rev++;
            } else if (in1 && in2) {
                brk++;
            } else {
                cst++;
            }
        }
        const float mean = (float)(fwd - rev) / (float)PLANT_TICKS;
        if (fabsf(mean - da) > 1e-6f) bad++;                         /* applied duty = mean bridge voltage / V_M */
        if (cst != 0) bad++;                                         /* never coasts while regulating */
        if (fwd > 0 && rev > 0) bad++;                               /* one direction per period */
        if (fabsf(da) > PEN_DUTY_MAX + 1e-6f) bad++;                 /* duty <= 0.97 */
        if (fabsf(da - clamp_duty(duties[k])) > 0.5f / (float)PEN_PWM_COUNTERTOP + 1e-6f) bad++; /* quantisation */
        if (fwd > 0 && (first_fwd + last_fwd) != PLANT_TICKS - 1) bad++;   /* drive phase centred on the period centre */
    }
    CHECK(bad == 0u);
    bridge_cmd_t b0;
    float d0;
    cl_duty_to_bridge(0.0f, PEN_DUTY_MAX, &b0, &d0);
    CHECK(b0.in1_high == PEN_PWM_COUNTERTOP && b0.in2_high == PEN_PWM_COUNTERTOP);   /* zero volts = brake, not coast */
    tr_log("duty -> IN1/IN2: drive/brake slow decay, drive phase centred, duty clamped to %.2f, resolution 1/%d",
           (double)PEN_DUTY_MAX, PEN_PWM_COUNTERTOP);
}

/* run the loop against the plant; the stage is locked (large mass) */
static void run_current(plant_t *pl, curloop_t *cl, const pen_ctrl_params_t *p, float iref, int periods, double *i_log,
                        double *duty_max)
{
    bridge_cmd_t cmd[2] = {{0, 0}, {0, 0}};
    int16_t ae[2], ac[2];
    const float ir[2] = {iref, 0.0f};
    for (int k = 0; k < periods; k++) {
        plant_period(pl, cmd, ae, ac);
        cl_step(cl, p, ir, ac, ae, (float)pl->vm, NULL, cmd);
        if (i_log != NULL) {
            i_log[k] = pl->i_sum[0] * PEN_F_PWM_HZ;   /* period-mean true current */
        }
        if (duty_max != NULL && fabs((double)cl->duty[0]) > *duty_max) {
            *duty_max = fabs((double)cl->duty[0]);
        }
    }
}

static void step_metrics(float cur_r_ff, double *os, double *t_rise_us, double *err_ss)
{
    pen_ctrl_params_t p;
    pen_params_default(&p, PEN_PROFILE_BALANCED);
    p.cur_r_ff = cur_r_ff;
    plant_t pl;
    plant_init(&pl, 3.7, 25.0);
    pl.m_eq = 1e6;   /* lock the stage: no back-EMF */
    pl.adc_noise_a = 0.0;
    curloop_t cl;
    cl_init(&cl);
    cl.enabled = true;
    static double ilog[400];
    run_current(&pl, &cl, &p, 0.0f, 40, NULL, NULL);
    run_current(&pl, &cl, &p, 0.30f, 400, ilog, NULL);   /* 10 ms */
    int k10 = -1, k90 = -1;
    double peak = 0.0;
    for (int k = 0; k < 400; k++) {
        if (k10 < 0 && ilog[k] >= 0.03) k10 = k;
        if (k90 < 0 && ilog[k] >= 0.27) k90 = k;
        peak = ilog[k] > peak ? ilog[k] : peak;
    }
    double mean_end = 0.0;
    for (int k = 360; k < 400; k++) {
        mean_end += ilog[k] / 40.0;
    }
    *os = 100.0 * (peak - 0.30) / 0.30;
    *t_rise_us = (k10 >= 0 && k90 >= 0) ? (double)(k90 - k10 + 1) * 25.0 : 1e9;
    *err_ss = mean_end - 0.30;
}

void test_current_loop_step_response(void)
{
    double os, tr, ess, os_ff, tr_ff, ess_ff;
    step_metrics(0.0f, &os, &tr, &ess);         /* firmware default: PI, zero on the electrical pole */
    step_metrics(1.0f, &os_ff, &tr_ff, &ess_ff); /* simulator form: + R i_ref feedforward */
    CHECK(tr <= 250.0);
    CHECK(os < 20.0);
    CHECK(fabs(ess) < 2e-3);
    CHECK(os_ff > 40.0);   /* documents README D10: the simulator form overshoots with the Rev A delay */
    tr_log("current step 0 -> 0.30 A (3.7 V, 25 degC, stage locked, period-mean true current, noise off):");
    tr_log("  PI (default, drive_sense design): 10-90%% rise %.0f us, overshoot %.1f %%, steady error %.2f mA", tr, os,
           1e3 * ess);
    tr_log("  PI + R i_ref feedforward (simulator form): rise %.0f us, overshoot %.1f %%, steady error %.2f mA", tr_ff,
           os_ff, 1e3 * ess_ff);
}

void test_current_loop_voltage_clamp(void)
{
    pen_ctrl_params_t p;
    pen_params_default(&p, PEN_PROFILE_BALANCED);
    plant_t pl;
    plant_init(&pl, 3.0, 85.0);        /* low battery, hot coil */
    pl.m_eq = 1e6;
    curloop_t cl;
    cl_init(&cl);
    cl.enabled = true;
    static double ilog[800];
    double dmax = 0.0;
    run_current(&pl, &cl, &p, 0.60f, 400, ilog, &dmax);      /* needs ~4.9 V: saturates */
    CHECK(cl.vsat_sticky);
    CHECK(dmax <= (double)PEN_DUTY_MAX + 1e-6);
    CHECK_CLOSE(dmax, PEN_DUTY_MAX, 0.006, 0.0);
    const double i_sat = ilog[399];
    /* anti-windup: after the reference drops inside the feasible range the
     * current settles without a long saturated hang-over */
    run_current(&pl, &cl, &p, 0.20f, 800, ilog, NULL);
    int k_settle = -1;
    for (int k = 0; k < 800; k++) {
        if (fabs(ilog[k] - 0.20) < 0.005) {
            bool ok = true;
            for (int j = k; j < 800 && j < k + 40; j++) {
                ok = ok && fabs(ilog[j] - 0.20) < 0.005;
            }
            if (ok) {
                k_settle = k;
                break;
            }
        }
    }
    CHECK(k_settle >= 0 && k_settle * 25 <= 1000);
    tr_log("3.0 V, 85 degC coil, i_ref 0.60 A: duty clamped at %.3f, current %.3f A (voltage limited); "
           "reference 0.20 A reached within +/-5 mA after %d us (conditional-integration anti-windup)",
           dmax, i_sat, k_settle * 25);
}

void test_current_loop_offset_calibration(void)
{
    pen_ctrl_params_t p;
    pen_params_default(&p, PEN_PROFILE_BALANCED);
    plant_t pl;
    plant_init(&pl, 3.7, 25.0);
    pl.m_eq = 1e6;
    pl.isns_offset_a[0] = 8e-3;
    pl.isns_offset_a[1] = -5e-3;
    curloop_t cl;
    cl_init(&cl);
    cl.enabled = true;
    static double ilog[400];
    run_current(&pl, &cl, &p, 0.0f, 400, ilog, NULL);
    const double i_before = ilog[399];      /* loop regulates the sensed current: true current = -offset */
    cl_request_offset_cal(&cl);
    int periods = 0;
    while (cl.cal_state != CL_CAL_IDLE && periods < 100) {
        run_current(&pl, &cl, &p, 0.0f, 1, NULL, NULL);
        periods++;
    }
    CHECK(cl.cal_done && cl.cal_ok);
    CHECK_CLOSE(cl.offset[0], 8e-3, 0.6e-3, 0.0);
    CHECK_CLOSE(cl.offset[1], -5e-3, 0.6e-3, 0.0);
    run_current(&pl, &cl, &p, 0.0f, 400, ilog, NULL);
    double mean = 0.0;
    for (int k = 200; k < 400; k++) {
        mean += ilog[k] / 200.0;
    }
    CHECK(fabs(mean) < 0.6e-3);
    tr_log("ISNS offset (+8, -5 mA injected): before cal true current %.2f mA; coast window %d periods (%.0f us); "
           "estimated %.2f / %.2f mA; after cal true current %.3f mA", 1e3 * i_before, periods, periods * 25.0,
           1e3 * (double)cl.offset[0], 1e3 * (double)cl.offset[1], 1e3 * mean);
    /* implausible offset: rejected, previous value kept */
    pl.isns_offset_a[0] = 0.040;
    const float keep = cl.offset[0];
    cl_request_offset_cal(&cl);
    for (int k = 0; k < 40; k++) {
        run_current(&pl, &cl, &p, 0.0f, 1, NULL, NULL);
    }
    CHECK(!cl.cal_ok);
    CHECK(cl.offset[0] == keep);
}
