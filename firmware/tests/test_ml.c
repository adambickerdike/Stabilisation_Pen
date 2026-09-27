/*
 * test_ml.c - ML predictor guard (ICD s5, REQ-SAF-003) and input window.
 */
#include <math.h>
#include <string.h>

#include "ml_guard.h"
#include "params_gen.h"
#include "tr.h"

#define TS PEN_TS_STAGE

/* feed a steady, good ML stream at 250 Hz until admitted */
static void admit(ml_guard_t *g, const float d_um[2], const float d_kf[2])
{
    for (int k = 0; k < 400; k++) {
        if (k % PEN_ML_DECIM == 0) {
            ml_guard_new_output(g, d_um, false, PEN_Q_LIM);
        }
        ml_guard_tick(g, d_kf, TS);
    }
}

void test_ml_guard_rejects(void)
{
    const float good[2] = {120.0f, -40.0f}, kf[2] = {118e-6f, -41e-6f};
    ml_guard_t g;
    ml_guard_init(&g);
    admit(&g, good, kf);
    CHECK(!g.rejected && g.mix == 1.0f);
    CHECK_CLOSE(g.out[0], 120e-6, 1e-9, 0.0);

    struct {
        const char *name;
        float d[2];
        bool sat;
        uint8_t reason;
    } cases[4] = {{"NaN", {NAN, 0.0f}, false, MLG_R_NAN},
                  {"int8 saturation", {120.0f, -40.0f}, true, MLG_R_SAT},
                  {"|d| > q_lim", {600.0f, 0.0f}, false, MLG_R_RANGE},
                  {"rate > 50 mm/s", {330.0f, -40.0f}, false, MLG_R_RATE}};   /* 210 um in 4 ms = 52 mm/s */
    for (int k = 0; k < 4; k++) {
        ml_guard_init(&g);
        admit(&g, good, kf);
        const uint32_t trips0 = g.trips;
        ml_guard_new_output(&g, cases[k].d, cases[k].sat, PEN_Q_LIM);
        CHECK(g.rejected && (g.reason & cases[k].reason) != 0u && g.trips == trips0 + 1u);
        tr_log("reject %-16s -> reason 0x%02X", cases[k].name, (unsigned)g.reason);
    }
    /* divergence from the Kalman estimate: > 150 um for > 20 ms */
    ml_guard_init(&g);
    admit(&g, good, kf);
    const float far_kf[2] = {-60e-6f, -41e-6f};   /* 180 um apart */
    int k_trip = -1;
    for (int k = 0; k < 100 && k_trip < 0; k++) {
        if (k % PEN_ML_DECIM == 0) {
            ml_guard_new_output(&g, good, false, PEN_Q_LIM);
        }
        ml_guard_tick(&g, far_kf, TS);
        if (g.trip) {
            k_trip = k;
        }
    }
    CHECK(g.rejected && (g.reason & MLG_R_DIVERGE) != 0u);
    CHECK(k_trip == 40);   /* 41 ticks = 20.5 ms > 20 ms */
    /* staleness: no output for > 8 ms */
    ml_guard_init(&g);
    admit(&g, good, kf);
    k_trip = -1;
    for (int k = 0; k < 40 && k_trip < 0; k++) {
        ml_guard_tick(&g, kf, TS);
        if (g.trip) {
            k_trip = k;
        }
    }
    CHECK(g.rejected && (g.reason & MLG_R_STALE) != 0u);
    tr_log("divergence trip after %.1f ms (> 20 ms); stale trip %.1f ms after the last output (> %.0f ms)",
           41 * 0.5, (k_trip + 1 + 7) * 0.5, (double)PEN_ML_STALE_TIME * 1e3);
}

void test_ml_guard_fallback_within_20ms(void)
{
    const float good[2] = {200.0f, 0.0f}, kf[2] = {150e-6f, 0.0f};
    ml_guard_t g;
    ml_guard_init(&g);
    admit(&g, good, kf);
    CHECK(g.mix == 1.0f);
    const float bad[2] = {NAN, NAN};
    ml_guard_new_output(&g, bad, false, PEN_Q_LIM);
    int n = 0;
    double max_step = 0.0, prev = (double)g.out[0];
    while (g.mix > 0.0f && n < 200) {
        ml_guard_tick(&g, kf, TS);
        max_step = fmax(max_step, fabs((double)g.out[0] - prev));
        prev = (double)g.out[0];
        n++;
    }
    CHECK((double)n * (double)TS <= (double)PEN_ML_FADE_TIME + 1e-6);
    CHECK_CLOSE(g.out[0], 150e-6, 1e-9, 0.0);   /* Kalman estimate */
    /* smooth: no jump larger than the fade step times the ML-KF gap */
    CHECK(max_step <= 50e-6 * (TS / PEN_ML_FADE_TIME) * 1.01);
    /* recovery: 25 good outputs, then fade back in */
    int k_rec = -1;
    for (int k = 0; k < 400 && k_rec < 0; k++) {
        if (k % PEN_ML_DECIM == 0) {
            ml_guard_new_output(&g, good, false, PEN_Q_LIM);
        }
        ml_guard_tick(&g, kf, TS);
        if (g.mix >= 1.0f) {
            k_rec = k;
        }
    }
    CHECK(k_rec > 0);
    tr_log("NaN output: cross-fade to the Kalman estimate in %.1f ms (REQ-SAF-003: within 20 ms), max step %.2f um; "
           "re-admitted after %u good outputs + fade (%.1f ms)", n * 0.5, max_step * 1e6, (unsigned)ML_RECOVER_OUTPUTS,
           (k_rec + 1) * 0.5);
}

void test_ml_window(void)
{
    ml_window_t w;
    ml_window_init(&w);
    float out[2 * PEN_ML_WINDOW + 1];
    for (int k = 0; k <= PEN_ML_WINDOW; k++) {
        CHECK(!ml_window_export(&w, 8.0f, out) || k == PEN_ML_WINDOW + 1);
        const float p[2] = {1e-6f * (float)(k * k), -2e-6f * (float)k};
        ml_window_push(&w, p);
    }
    CHECK(ml_window_export(&w, 8.25f, out));
    bool ok = true;
    for (int j = 0; j < PEN_ML_WINDOW; j++) {
        const float dx = (float)((j + 1) * (j + 1) - j * j);   /* um, oldest first */
        ok = ok && fabsf(out[2 * j] - dx) < 1e-3f && fabsf(out[2 * j + 1] + 2.0f) < 1e-3f;
    }
    CHECK(ok);
    CHECK(out[2 * PEN_ML_WINDOW] == 8.25f);
    tr_log("input window: %d increments (um, oldest first) + f_est, as ICD s5", PEN_ML_WINDOW);
}
