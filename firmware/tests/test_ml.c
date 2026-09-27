/*
 * test_ml.c - ML predictor guard (docs/icd.md s5 v1.1, REQ-SAF-003) and the
 * time-stamped input window, with synthetic predictors.
 */
#include <math.h>
#include <string.h>

#include "biquad.h"
#include "ml_guard.h"
#include "params_gen.h"
#include "tr.h"

#define TS PEN_TS_STAGE
#define PI_D 3.141592653589793
#define N_T 12000   /* 6 s of stage ticks */

/* housing motion and its realised disturbance (same band-pass, run separately) */
static float s_p[N_T][2], s_r[N_T][2];

static void make_signal(void)
{
    const biquad_coef_t b1 = {PEN_MLG_BP1_B0, PEN_MLG_BP1_B1, PEN_MLG_BP1_B2, PEN_MLG_BP1_A1, PEN_MLG_BP1_A2};
    const biquad_coef_t b2 = {PEN_MLG_BP2_B0, PEN_MLG_BP2_B1, PEN_MLG_BP2_B2, PEN_MLG_BP2_A1, PEN_MLG_BP2_A2};
    biquad_state_t s1[2] = {{0, 0}, {0, 0}}, s2[2] = {{0, 0}, {0, 0}};
    for (int k = 0; k < N_T; k++) {
        const double t = k * (double)TS;
        s_p[k][0] = (float)(0.030 + 2e-4 * sin(2 * PI_D * 8.0 * t) + 1e-3 * sin(2 * PI_D * 0.7 * t));
        s_p[k][1] = (float)(0.010 + 1e-4 * sin(2 * PI_D * 8.0 * t + 1.0));
        for (int ax = 0; ax < 2; ax++) {
            /* local origin = first sample, as the guard does */
            const float y1 = biquad_step(&b1, &s1[ax], s_p[k][ax] - s_p[0][ax]);
            s_r[k][ax] = biquad_step(&b2, &s2[ax], y1);
        }
    }
}

typedef enum { PRED_GOOD, PRED_BAD, PRED_NONE } pred_t;

/* run ticks [k0, k1): stamps t_acq = tick time - 1 ms; predictions at 250 Hz */
static void run_guard(ml_guard_t *g, int k0, int k1, pred_t pred, int *k_fallback, int *k_admit_full)
{
    const float kf[2] = {0.0f, 0.0f};
    for (int k = k0; k < k1; k++) {
        const uint32_t t_us = (uint32_t)k * 500u + 1000000u;
        const uint32_t t_acq = t_us - 1000u;
        ml_guard_realised(g, s_p[k], t_acq, true);
        if (pred != PRED_NONE && k % PEN_ML_DECIM == 0) {
            /* target = t_acq + 6 ms = 12 ticks later */
            const int kt = (k + 12 < N_T) ? k + 12 : N_T - 1;
            const float sg = (pred == PRED_GOOD) ? 1.0f : -1.0f;
            const float d_um[2] = {sg * s_r[kt][0] * 1e6f, sg * s_r[kt][1] * 1e6f};
            ml_guard_new_output(g, d_um, false, false, t_acq, PEN_Q_LIM);
        }
        ml_guard_tick(g, kf, TS);
        if (k_fallback != NULL && *k_fallback < 0 && g->apost_fallback) {
            *k_fallback = k;
        }
        if (k_admit_full != NULL && *k_admit_full < 0 && g->mix >= 1.0f) {
            *k_admit_full = k;
        }
        g->event = false;
        g->trip = false;
    }
}

void test_ml_guard_rejects(void)
{
    ml_guard_t g;
    ml_guard_init(&g);
    const float d0[2] = {120.0f, -40.0f};
    ml_guard_new_output(&g, d0, false, false, 1000u, PEN_Q_LIM);
    CHECK(g.have && g.info == 0u);
    /* (1) NaN / Inf / saturation: that inference is rejected, previous estimate kept */
    const float dn[2] = {NAN, 0.0f};
    ml_guard_new_output(&g, dn, false, false, 5000u, PEN_Q_LIM);
    CHECK(g.n_rejected == 1u && (g.reason & MLG_R_NAN) != 0u && g.event);
    CHECK_CLOSE(g.d[0], 120e-6, 1e-10, 0.0);
    const float di[2] = {INFINITY, 0.0f};
    ml_guard_new_output(&g, di, false, false, 5000u, PEN_Q_LIM);
    CHECK(g.n_rejected == 2u);
    ml_guard_new_output(&g, d0, false, true, 5000u, PEN_Q_LIM);
    CHECK(g.n_rejected == 3u && (g.reason & MLG_R_SAT) != 0u);
    /* (2) clip to q_lim: not rejected */
    ml_guard_init(&g);
    const float dbig[2] = {700.0f, 0.0f};
    ml_guard_new_output(&g, dbig, false, false, 1000u, PEN_Q_LIM);
    CHECK(g.n_rejected == 0u && (g.info & MLG_R_CLIP) != 0u);
    CHECK_CLOSE(g.d[0], PEN_Q_LIM, 1e-9, 0.0);
    /* (3) slew limit 50 mm/s: +400 um after 4 ms -> +200 um */
    ml_guard_init(&g);
    const float da[2] = {0.0f, 0.0f}, db[2] = {400.0f, 0.0f};
    const float kf[2] = {0.0f, 0.0f};
    ml_guard_new_output(&g, da, false, false, 1000u, PEN_Q_LIM);
    for (int k = 0; k < PEN_ML_DECIM; k++) {
        ml_guard_tick(&g, kf, TS);
    }
    ml_guard_new_output(&g, db, false, false, 5000u, PEN_Q_LIM);
    CHECK(g.n_rejected == 0u && (g.info & MLG_R_SLEW) != 0u);
    CHECK_CLOSE(g.d[0], PEN_ML_RATE_MAX * 4e-3, 1e-8, 0.0);
    tr_log("v1.1 rules 1-3: NaN/Inf/saturation reject that inference only; |d| clipped to q_lim; slew limited to "
           "%.0f mm/s (400 um in 4 ms -> %.0f um)", (double)PEN_ML_RATE_MAX * 1e3, (double)g.d[0] * 1e6);
    tr_log("the v1 rule |d - d_KF| > 150 um is not implemented (removed in ICD s5 v1.1)");
}

void test_ml_guard_fallback_within_20ms(void)
{
    make_signal();
    ml_guard_t g;
    ml_guard_init(&g);
    int k_fb = -1, k_adm = -1;
    /* good predictor: admitted after band-pass settling (300 ms) + 200 ms window + fade */
    run_guard(&g, 0, 2000, PRED_GOOD, &k_fb, &k_adm);
    CHECK(k_fb < 0 && k_adm > 0);
    CHECK(g.rms_err < 0.2f * g.rms_real);
    const double t_adm = (k_adm + 1) * 0.5;
    const float rms_good = g.rms_err, rms_real = g.rms_real;
    /* bad predictor (sign inverted: RMS error = 2 x realised) from tick 2000 */
    k_fb = -1;
    int k_zero = -1;
    const float kf[2] = {0.0f, 0.0f};
    for (int k = 2000; k < 2400; k++) {
        run_guard(&g, k, k + 1, PRED_BAD, &k_fb, NULL);
        if (k_fb >= 0 && k_zero < 0 && g.mix == 0.0f) {
            k_zero = k;
        }
    }
    CHECK(k_fb > 2000 && (k_fb - 2000) * 0.5 < 100.0);
    CHECK(k_zero >= k_fb && (k_zero - k_fb + 1) * 0.5 <= 20.0 + 1e-9);   /* REQ-SAF-003 */
    CHECK(g.n_fallbacks >= 1u);
    ml_guard_tick(&g, kf, TS);
    CHECK_CLOSE(g.out[0], 0.0, 1e-12, 0.0);   /* Kalman estimate in use */
    /* good predictor again: held in fallback >= 1 s after the last failing evaluation */
    const int k_good = 2400;
    int k_readmit = -1;
    float last_fail_t = 0.0f;
    for (int k = k_good; k < 8000; k++) {
        const bool was = g.apost_fallback;
        const float tfb = g.t_fallback;
        run_guard(&g, k, k + 1, PRED_GOOD, NULL, NULL);
        if (was && g.apost_fallback && g.t_fallback < tfb) {
            last_fail_t = (float)k;   /* a failing evaluation restarted the hold */
        }
        if (k_readmit < 0 && g.mix > 0.0f) {
            k_readmit = k;
        }
    }
    CHECK(k_readmit > 0);
    CHECK(((double)k_readmit - (double)last_fail_t) * 0.5 >= 1000.0 - 1.0);
    CHECK(g.mix == 1.0f);
    tr_log("a-posteriori (rule 4): good predictor admitted at %.1f ms (RMS error %.1f um vs realised %.1f um); "
           "sign-inverted predictor -> fallback %.1f ms after the switch, Kalman fully in use %.1f ms later; "
           "re-admitted %.0f ms after the last failing evaluation (hold >= 1 s)", t_adm, (double)rms_good * 1e6,
           (double)rms_real * 1e6, (k_fb - 2000 + 1) * 0.5, (k_zero - k_fb + 1) * 0.5,
           ((double)k_readmit - (double)last_fail_t) * 0.5);
    /* staleness (REQ-SAF-003): outputs stop -> expired after 8 ms, faded within 20 ms */
    int k_stale = -1, k_out = -1;
    for (int k = 8000; k < 8100; k++) {
        run_guard(&g, k, k + 1, PRED_NONE, NULL, NULL);
        if (k_stale < 0 && g.stale) {
            k_stale = k;
        }
        if (k_stale >= 0 && k_out < 0 && g.mix == 0.0f) {
            k_out = k;
        }
    }
    CHECK(k_stale > 0 && k_out > 0 && (k_out - k_stale + 1) * 0.5 <= 20.0 + 1e-9);
    run_guard(&g, 8100, 8200, PRED_GOOD, NULL, NULL);
    CHECK(!g.stale && g.mix == 1.0f);   /* resumes without the 1 s hold (not an a-posteriori failure) */
}

void test_ml_window(void)
{
    ml_window_t w;
    ml_window_init(&w);
    float out[PEN_ML_WINDOW][2];
    uint32_t tn = 0;
    for (int k = 0; k <= PEN_ML_WINDOW; k++) {
        CHECK(!ml_window_export(&w, out, &tn) || k == PEN_ML_WINDOW + 1);
        const float p[2] = {1e-6f * (float)(k * k), -2e-6f * (float)k};
        ml_window_push(&w, p, 1000u + 4000u * (uint32_t)k);
    }
    CHECK(ml_window_export(&w, out, &tn));
    bool ok = true;
    for (int j = 0; j < PEN_ML_WINDOW; j++) {
        const float dx = (float)((j + 1) * (j + 1) - j * j);   /* um, oldest first */
        ok = ok && fabsf(out[j][0] - dx) < 1e-3f && fabsf(out[j][1] + 2.0f) < 1e-3f;
    }
    CHECK(ok);
    CHECK(tn == 1000u + 4000u * (uint32_t)PEN_ML_WINDOW);   /* acquisition time of the newest sample */
    ml_window_reset(&w);
    CHECK(!ml_window_export(&w, out, &tn));
    tr_log("input window: %d x (dx, dy) um increments, oldest first, newest acquisition stamp exported (no f_est, "
           "ICD s5 v1.1); reset on optical dropout", PEN_ML_WINDOW);
}
