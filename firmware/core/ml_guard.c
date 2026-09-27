/*
 * ml_guard.c - ML predictor guard and input window (see header).
 * Status: PROPOSED DESIGN; host unit tests with injected faults. No model
 * exists yet (ml/export is empty); the inference kernel is out of scope.
 */
#include "ml_guard.h"

#include <math.h>
#include <string.h>

#include "mathx.h"

void ml_guard_init(ml_guard_t *g)
{
    memset(g, 0, sizeof(*g));
    g->rejected = true;           /* nothing admitted until good outputs arrive */
    g->t_since_out = 1e3f;
}

static void do_trip(ml_guard_t *g, uint8_t reason)
{
    g->reason = reason;
    if (!g->rejected) {
        g->trip = true;
        g->trips++;
    }
    g->rejected = true;
    g->good_run = 0;
}

void ml_guard_new_output(ml_guard_t *g, const float d_um[2], bool saturated, float q_lim)
{
    uint8_t reason = 0;
    const float d0 = d_um[0] * 1e-6f, d1 = d_um[1] * 1e-6f;
    if (!pen_isfinitef(d0) || !pen_isfinitef(d1)) {
        reason |= MLG_R_NAN;
    }
    if (saturated) {
        reason |= MLG_R_SAT;
    }
    if (reason == 0u) {
        if (hypotf(d0, d1) > q_lim) {
            reason |= MLG_R_RANGE;
        }
        if (g->have_prev && g->t_since_out > 0.0f) {
            const float rate = hypotf(d0 - g->d_prev[0], d1 - g->d_prev[1]) / g->t_since_out;
            if (rate > PEN_ML_RATE_MAX) {
                reason |= MLG_R_RATE;
            }
        }
    }
    g->t_since_prev = g->t_since_out;
    g->t_since_out = 0.0f;
    if ((reason & MLG_R_NAN) == 0u) {
        g->d_prev[0] = d0;
        g->d_prev[1] = d1;
        g->have_prev = true;
        g->d_ml[0] = d0;
        g->d_ml[1] = d1;
    }
    g->have_output = true;
    if (reason != 0u) {
        do_trip(g, reason);
    } else if (g->rejected) {
        if (g->good_run < 0xFFFFu) {
            g->good_run++;
        }
        if (g->good_run >= ML_RECOVER_OUTPUTS) {
            g->rejected = false;
            g->t_diverge = 0.0f;
        }
    }
}

void ml_guard_tick(ml_guard_t *g, const float d_kf[2], float dt)
{
    g->trip = false;
    g->t_since_out += dt;
    if (g->have_output && g->t_since_out > PEN_ML_STALE_TIME) {
        do_trip(g, MLG_R_STALE);
        g->have_output = false;
    }
    if (g->have_output) {
        const float dd = hypotf(g->d_ml[0] - d_kf[0], g->d_ml[1] - d_kf[1]);
        g->t_diverge = (dd > PEN_ML_DHAT_DIFF_MAX) ? g->t_diverge + dt : 0.0f;
        if (g->t_diverge > PEN_ML_DIFF_TIME) {
            do_trip(g, MLG_R_DIVERGE);
        }
    }
    /* cross-fade: full swing within ML_FADE_TIME */
    const float step = dt / PEN_ML_FADE_TIME;
    if (g->rejected) {
        g->mix = pen_maxf(g->mix - step, 0.0f);
    } else {
        g->mix = pen_minf(g->mix + step, 1.0f);
    }
    for (int ax = 0; ax < 2; ax++) {
        const float dm = g->have_prev ? g->d_ml[ax] : d_kf[ax];
        g->out[ax] = g->mix * dm + (1.0f - g->mix) * d_kf[ax];
    }
}

void ml_window_init(ml_window_t *w)
{
    memset(w, 0, sizeof(*w));
}

void ml_window_push(ml_window_t *w, const float p_h[2])
{
    if (w->have_last) {
        w->dp[w->head][0] = (p_h[0] - w->p_last[0]) * 1e6f;
        w->dp[w->head][1] = (p_h[1] - w->p_last[1]) * 1e6f;
        w->head = (uint16_t)((w->head + 1u) % (uint16_t)PEN_ML_WINDOW);
        if (w->count < (uint16_t)PEN_ML_WINDOW) {
            w->count++;
        }
    }
    w->p_last[0] = p_h[0];
    w->p_last[1] = p_h[1];
    w->have_last = true;
}

bool ml_window_export(const ml_window_t *w, float f_est_hz, float out[2 * PEN_ML_WINDOW + 1])
{
    if (w->count < (uint16_t)PEN_ML_WINDOW) {
        return false;
    }
    for (uint16_t k = 0; k < (uint16_t)PEN_ML_WINDOW; k++) {
        const uint16_t idx = (uint16_t)((w->head + k) % (uint16_t)PEN_ML_WINDOW);
        out[2u * k] = w->dp[idx][0];
        out[2u * k + 1u] = w->dp[idx][1];
    }
    out[2 * PEN_ML_WINDOW] = f_est_hz;
    return true;
}
