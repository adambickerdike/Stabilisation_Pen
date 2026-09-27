/*
 * ml_guard.h - firmware <-> ML predictor contract, docs/icd.md s5 v1.1.
 *
 * Input (ml_window_*): W = 64 samples at 250 Hz of housing page displacement
 * increments dp_H (x, y) in um, oldest first, each time-stamped at sensor
 * acquisition (for the fused p_H: stage-tick time minus the IMU group delay,
 * the latency the fusion leaves). f_est is no longer an input (v1.1).
 * Output: d_hat (x, y) in um at h = 6 ms after the acquisition time of the
 * newest input sample; used from the next stage tick.
 *
 * Guard v1.1 (this file implements exactly these rules):
 *  (1) NaN/Inf or output saturation reported by the kernel -> reject that
 *      inference (the previous accepted estimate stays in use);
 *  (2) clip |d_hat| to q_lim (no rejection);
 *  (3) slew-limit d_hat at 50 mm/s (no rejection);
 *  (4) a-posteriori check: each accepted prediction is kept with its target
 *      time (newest acquisition + h) and compared, when that time has been
 *      acquired, with the realised disturbance = fused housing displacement
 *      band-passed 3-15 Hz (2nd-order Butterworth sections, local origin).
 *      If the running RMS prediction error over the last 200 ms exceeds the
 *      running RMS of the realised disturbance (worse than predicting zero),
 *      fall back to the Kalman estimate for >= 1 s and log event 0x0006.
 *  The v1 rule |d_hat - d_KF| > 150 um for 20 ms is removed.
 * Firmware additions (REQ-SAF-003): an output older than ML_STALE_TIME is
 * expired (fallback until outputs resume); every fallback and re-admission is
 * a cross-fade completed within ML_FADE_TIME (20 ms). The ML output is used
 * only after the 200 ms a-posteriori window has filled and passes.
 * Units inside the guard: metres and microsecond time stamps.
 */
#ifndef PEN_ML_GUARD_H
#define PEN_ML_GUARD_H

#include <stdbool.h>
#include <stdint.h>

#include "biquad.h"
#include "params_gen.h"

enum {
    MLG_R_NAN = 1u << 0,    /* (1) inference rejected */
    MLG_R_SAT = 1u << 1,    /* (1) inference rejected */
    MLG_R_CLIP = 1u << 2,   /* (2) informational */
    MLG_R_SLEW = 1u << 3,   /* (3) informational */
    MLG_R_APOST = 1u << 4,  /* (4) fallback >= 1 s */
    MLG_R_STALE = 1u << 5   /* expired output, fallback until outputs resume */
};

#define MLG_EVAL_N 50u      /* 200 ms of 250 Hz predictions */
#define MLG_PEND_N 8u       /* predictions waiting for their target time */

typedef struct {
    uint32_t t_target_us;
    float d[2];
} mlg_pending_t;

typedef struct {
    /* accepted (clipped, slew-limited) ML estimate */
    float d[2];
    bool have;
    float t_since_out;        /* s since the last accepted output */
    /* realised disturbance */
    biquad_state_t bp1[2], bp2[2];
    float origin[2];
    bool real_valid;
    float real_settle;        /* s since the band-pass (re)start */
    float real[2], real_prev[2];
    uint32_t real_t_us, real_prev_t_us;
    /* a-posteriori statistics */
    mlg_pending_t pend[MLG_PEND_N];
    uint8_t pend_n;
    float e2[MLG_EVAL_N], r2[MLG_EVAL_N];
    uint16_t eval_head, eval_n;
    float rms_err, rms_real;  /* last running values (m) */
    /* state */
    bool apost_fallback;      /* rule (4): held >= ML_FALLBACK_HOLD */
    float t_fallback;         /* s in the rule-(4) fallback */
    bool stale;               /* no accepted output for > ML_STALE_TIME */
    bool fallback;            /* apost_fallback || stale (for flags/logging) */
    float mix;                /* 1 = ML, 0 = Kalman */
    uint8_t reason;           /* reason bits of the last event */
    uint8_t info;             /* clip/slew bits of the last accepted output */
    bool event;               /* event 0x0006 pending (arg = reason); the caller logs and clears it */
    bool trip;                /* pending trip toward fault bit 8; the caller counts and clears it */
    uint32_t n_rejected, n_fallbacks, n_eval;
    float out[2];             /* guarded disturbance estimate (m) */
} ml_guard_t;

void ml_guard_init(ml_guard_t *g);
/* Every stage tick: fused housing page position (m), its acquisition time
 * and the optical validity. Feeds the realised-disturbance band-pass and
 * evaluates predictions whose target time has been reached. */
void ml_guard_realised(ml_guard_t *g, const float p_h[2], uint32_t t_acq_us, bool valid);
/* A new inference: d_hat in um, kernel status (NaN/Inf, output saturation),
 * acquisition time of the newest input sample, travel limit (m). */
void ml_guard_new_output(ml_guard_t *g, const float d_um[2], bool nan_or_inf, bool saturated, uint32_t t_acq_newest_us,
                         float q_lim);
/* Every stage tick: staleness, fallback timing, cross-fade; writes g->out. */
void ml_guard_tick(ml_guard_t *g, const float d_kf[2], float dt);
static inline bool ml_guard_admitted(const ml_guard_t *g) { return g->mix > 0.0f; }

/* ---- input window (ICD s5 v1.1) ---- */
typedef struct {
    float dp[PEN_ML_WINDOW][2];   /* um, ring buffer */
    uint32_t t_us[PEN_ML_WINDOW]; /* acquisition time of each sample */
    uint16_t head;                /* next write index */
    uint16_t count;
    float p_last[2];              /* m, housing position at the last push */
    bool have_last;
} ml_window_t;

void ml_window_init(ml_window_t *w);
void ml_window_reset(ml_window_t *w);   /* optical dropout: increments across it are meaningless */
/* Push the housing page position (m) every ML_DECIM stage ticks (250 Hz). */
void ml_window_push(ml_window_t *w, const float p_h[2], uint32_t t_acq_us);
/* Export oldest -> newest (um); returns false until full. *t_newest_us = acquisition time of the newest sample. */
bool ml_window_export(const ml_window_t *w, float out[PEN_ML_WINDOW][2], uint32_t *t_newest_us);

#endif /* PEN_ML_GUARD_H */
