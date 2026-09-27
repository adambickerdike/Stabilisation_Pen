/*
 * ml_guard.c - ML predictor guard v1.1 and input window (see header).
 * Status: PROPOSED DESIGN; host unit tests with synthetic predictors and
 * injected faults. The inference kernel (ml/export) is not linked here.
 */
#include "ml_guard.h"

#include <math.h>
#include <string.h>

#include "mathx.h"

static const biquad_coef_t MLG_BP1 = {PEN_MLG_BP1_B0, PEN_MLG_BP1_B1, PEN_MLG_BP1_B2, PEN_MLG_BP1_A1, PEN_MLG_BP1_A2};
static const biquad_coef_t MLG_BP2 = {PEN_MLG_BP2_B0, PEN_MLG_BP2_B1, PEN_MLG_BP2_B2, PEN_MLG_BP2_A1, PEN_MLG_BP2_A2};

void ml_guard_init(ml_guard_t *g)
{
    memset(g, 0, sizeof(*g));
}

static void raise_event(ml_guard_t *g, uint8_t reason)
{
    g->reason = reason;
    g->event = true;
    g->trip = true;
}

static void enter_apost_fallback(ml_guard_t *g)
{
    if (!g->apost_fallback) {
        g->n_fallbacks++;
        raise_event(g, MLG_R_APOST);
    }
    g->apost_fallback = true;
    g->t_fallback = 0.0f;   /* hold >= 1 s from the last failing evaluation */
}

/* signed 32-bit difference of wrapping microsecond stamps */
static int32_t dt_us(uint32_t a, uint32_t b)
{
    return (int32_t)(a - b);
}

static void evaluate(ml_guard_t *g, const float e[2], const float r[2])
{
    g->e2[g->eval_head] = e[0] * e[0] + e[1] * e[1];
    g->r2[g->eval_head] = r[0] * r[0] + r[1] * r[1];
    g->eval_head = (uint16_t)((g->eval_head + 1u) % MLG_EVAL_N);
    if (g->eval_n < MLG_EVAL_N) {
        g->eval_n++;
    }
    g->n_eval++;
    float se = 0.0f, sr = 0.0f;
    for (uint16_t k = 0; k < g->eval_n; k++) {
        se += g->e2[k];
        sr += g->r2[k];
    }
    g->rms_err = sqrtf(se / (float)g->eval_n);
    g->rms_real = sqrtf(sr / (float)g->eval_n);
    if (g->eval_n >= MLG_EVAL_N && g->rms_err > g->rms_real) {
        enter_apost_fallback(g);   /* worse than predicting zero */
    }
}

void ml_guard_realised(ml_guard_t *g, const float p_h[2], uint32_t t_acq_us, bool valid)
{
    if (!valid) {
        g->real_valid = false;
        g->pend_n = 0;          /* no realised value can be formed for them */
        return;
    }
    if (!g->real_valid) {
        /* (re)start: local origin removes the coordinate step, states zeroed */
        g->origin[0] = p_h[0];
        g->origin[1] = p_h[1];
        for (int ax = 0; ax < 2; ax++) {
            biquad_reset(&g->bp1[ax]);
            biquad_reset(&g->bp2[ax]);
        }
        g->real_settle = 0.0f;
        g->real_valid = true;
        g->real_t_us = t_acq_us;
        g->real[0] = 0.0f;
        g->real[1] = 0.0f;
    }
    g->real_prev[0] = g->real[0];
    g->real_prev[1] = g->real[1];
    g->real_prev_t_us = g->real_t_us;
    for (int ax = 0; ax < 2; ax++) {
        const float y1 = biquad_step(&MLG_BP1, &g->bp1[ax], p_h[ax] - g->origin[ax]);
        g->real[ax] = biquad_step(&MLG_BP2, &g->bp2[ax], y1);
    }
    g->real_t_us = t_acq_us;
    g->real_settle += PEN_TS_STAGE;
    /* evaluate every pending prediction whose target time has been acquired */
    uint8_t keep = 0;
    for (uint8_t k = 0; k < g->pend_n; k++) {
        const mlg_pending_t *pp = &g->pend[k];
        if (dt_us(g->real_t_us, pp->t_target_us) >= 0) {
            if (g->real_settle >= PEN_ML_REAL_SETTLE && dt_us(pp->t_target_us, g->real_prev_t_us) >= 0) {
                /* linear interpolation of the realised disturbance at the target time */
                const float span = (float)dt_us(g->real_t_us, g->real_prev_t_us);
                const float a = (span > 0.0f) ? (float)dt_us(pp->t_target_us, g->real_prev_t_us) / span : 1.0f;
                float r[2], e[2];
                for (int ax = 0; ax < 2; ax++) {
                    r[ax] = g->real_prev[ax] + a * (g->real[ax] - g->real_prev[ax]);
                    e[ax] = pp->d[ax] - r[ax];
                }
                evaluate(g, e, r);
            }
        } else {
            g->pend[keep++] = *pp;
        }
    }
    g->pend_n = keep;
}

void ml_guard_new_output(ml_guard_t *g, const float d_um[2], bool nan_or_inf, bool saturated, uint32_t t_acq_newest_us,
                         float q_lim)
{
    const bool bad_num = nan_or_inf || !pen_isfinitef(d_um[0]) || !pen_isfinitef(d_um[1]);
    if (bad_num || saturated) {
        /* (1) reject this inference */
        g->n_rejected++;
        raise_event(g, (uint8_t)((bad_num ? MLG_R_NAN : 0u) | (saturated ? MLG_R_SAT : 0u)));
        return;
    }
    float d[2] = {d_um[0] * 1e-6f, d_um[1] * 1e-6f};
    uint8_t info = 0;
    /* (2) clip to the travel limit */
    const float m = hypotf(d[0], d[1]);
    if (m > q_lim) {
        d[0] *= q_lim / m;
        d[1] *= q_lim / m;
        info |= MLG_R_CLIP;
    }
    /* (3) slew limit 50 mm/s against the previous accepted estimate, over the
     * acquisition-time interval between the two predictions */
    if (g->have) {
        const int32_t dt_acq = dt_us(t_acq_newest_us, g->t_acq_last_us);
        const float dmax = PEN_ML_RATE_MAX * ((dt_acq > 0) ? (float)dt_acq * 1e-6f : 0.0f);
        const float dx = d[0] - g->d[0], dy = d[1] - g->d[1];
        const float dm = hypotf(dx, dy);
        if (dm > dmax) {
            d[0] = g->d[0] + dx * dmax / dm;
            d[1] = g->d[1] + dy * dmax / dm;
            info |= MLG_R_SLEW;
        }
    }
    g->d[0] = d[0];
    g->d[1] = d[1];
    g->have = true;
    g->info = info;
    g->t_acq_last_us = t_acq_newest_us;
    g->t_expiry_us = t_acq_newest_us + (uint32_t)lrintf(PEN_ML_STALE_TIME * 1e6f);
    g->stale = false;             /* outputs resumed */
    /* (4) keep the prediction with its target time */
    const uint32_t target = t_acq_newest_us + (uint32_t)lrintf(PEN_ML_HORIZON * 1e6f);
    if (g->pend_n >= MLG_PEND_N) {
        memmove(&g->pend[0], &g->pend[1], sizeof(g->pend[0]) * (MLG_PEND_N - 1u));
        g->pend_n--;
    }
    g->pend[g->pend_n].t_target_us = target;
    g->pend[g->pend_n].d[0] = d[0];
    g->pend[g->pend_n].d[1] = d[1];
    g->pend_n++;
}

void ml_guard_tick(ml_guard_t *g, const float d_kf[2], float dt, uint32_t now_us)
{
    if (g->have && !g->stale && dt_us(now_us, g->t_expiry_us) > 0) {
        g->stale = true;          /* expired (REQ-SAF-003) */
        g->n_fallbacks++;
        raise_event(g, MLG_R_STALE);
    }
    if (g->apost_fallback) {
        g->t_fallback += dt;
        if (g->t_fallback >= PEN_ML_FALLBACK_HOLD && g->eval_n >= MLG_EVAL_N && g->rms_err <= g->rms_real) {
            g->apost_fallback = false;   /* >= 1 s elapsed and the predictor beats zero again */
        }
    }
    g->fallback = g->apost_fallback || g->stale;
    const bool admit = g->have && !g->fallback && g->eval_n >= MLG_EVAL_N && g->rms_err <= g->rms_real;
    const float step = dt / PEN_ML_FADE_TIME;
    if (admit) {
        g->mix = g->mix + step;
        if (g->mix > 1.0f - 0.5f * step) {
            g->mix = 1.0f;
        }
    } else {
        g->mix = g->mix - step;
        if (g->mix < 0.5f * step) {
            g->mix = 0.0f;
        }
    }
    for (int ax = 0; ax < 2; ax++) {
        const float dm = g->have ? g->d[ax] : d_kf[ax];
        g->out[ax] = g->mix * dm + (1.0f - g->mix) * d_kf[ax];
    }
}

/* ------------------------------------------------------------------ input window */
void ml_window_init(ml_window_t *w)
{
    memset(w, 0, sizeof(*w));
}

void ml_window_reset(ml_window_t *w)
{
    w->count = 0;
    w->have_last = false;
}

void ml_window_push(ml_window_t *w, const float p_h[2], uint32_t t_acq_us)
{
    if (w->have_last) {
        w->dp[w->head][0] = (p_h[0] - w->p_last[0]) * 1e6f;
        w->dp[w->head][1] = (p_h[1] - w->p_last[1]) * 1e6f;
        w->t_us[w->head] = t_acq_us;
        w->head = (uint16_t)((w->head + 1u) % (uint16_t)PEN_ML_WINDOW);
        if (w->count < (uint16_t)PEN_ML_WINDOW) {
            w->count++;
        }
    }
    w->p_last[0] = p_h[0];
    w->p_last[1] = p_h[1];
    w->have_last = true;
}

bool ml_window_export(const ml_window_t *w, float out[PEN_ML_WINDOW][2], uint32_t *t_newest_us)
{
    if (w->count < (uint16_t)PEN_ML_WINDOW) {
        return false;
    }
    for (uint16_t k = 0; k < (uint16_t)PEN_ML_WINDOW; k++) {
        const uint16_t idx = (uint16_t)((w->head + k) % (uint16_t)PEN_ML_WINDOW);
        out[k][0] = w->dp[idx][0];
        out[k][1] = w->dp[idx][1];
    }
    const uint16_t newest = (uint16_t)((w->head + (uint16_t)PEN_ML_WINDOW - 1u) % (uint16_t)PEN_ML_WINDOW);
    *t_newest_us = w->t_us[newest];
    return true;
}
