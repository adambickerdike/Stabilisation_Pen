/*
 * ml_guard.h - firmware <-> ML predictor contract, ICD section 5.
 *
 * Input window: W = 64 samples at 250 Hz of housing page displacement
 * increments dp_H (x, y) in um, plus the Kalman phase-rate estimate f_est
 * (Hz); float32 before quantisation (ml_window_*).
 * Output: predicted disturbance d (x, y) in um at h = 6 ms after the newest
 * sample; the stage task uses it at the next tick.
 * Guard (ml_guard_*): reject if |d| > q_lim, if |d - d_KF| > 150 um for
 * > 20 ms, if the output rate exceeds 50 mm/s, on NaN/Inf or int8 output
 * saturation, or if the output is older than ML_STALE_TIME (REQ-SAF-003
 * "expired"). On reject the output cross-fades to the Kalman estimate within
 * ML_FADE_TIME (20 ms, REQ-SAF-003) and one trip is reported (event 0x0006,
 * arg = reason bits); recovery requires ML_RECOVER_OUTPUTS consecutive good
 * outputs, then fades back in over the same time.
 * Units inside the guard: metres (the ICD's um appear only at the ML I/O).
 */
#ifndef PEN_ML_GUARD_H
#define PEN_ML_GUARD_H

#include <stdbool.h>
#include <stdint.h>

#include "params_gen.h"

enum {
    MLG_R_NAN = 1u << 0,
    MLG_R_SAT = 1u << 1,
    MLG_R_RANGE = 1u << 2,
    MLG_R_DIVERGE = 1u << 3,
    MLG_R_RATE = 1u << 4,
    MLG_R_STALE = 1u << 5
};
#define ML_RECOVER_OUTPUTS 25u   /* 100 ms of good outputs before re-admitting (proposed) */

typedef struct {
    float d_ml[2];       /* last accepted-for-evaluation output, m */
    float d_prev[2];
    bool have_prev;
    bool have_output;
    float t_since_out;   /* s since the last ML output */
    float t_since_prev;  /* s between the last two outputs */
    float t_diverge;     /* s that |d_ml - d_kf| > 150 um */
    float mix;           /* 1 = ML, 0 = Kalman */
    bool rejected;       /* currently rejecting */
    uint16_t good_run;   /* consecutive good outputs while rejected */
    uint8_t reason;      /* reason bits of the last trip */
    bool trip;           /* a new trip happened this tick (log 0x0006, count bit 8) */
    uint32_t trips;      /* total trips */
    float out[2];        /* guarded disturbance estimate, m */
} ml_guard_t;

void ml_guard_init(ml_guard_t *g);
/* A new inference result (um, as the model outputs) with its int8 output
 * saturation flag. Call when the result becomes available. */
void ml_guard_new_output(ml_guard_t *g, const float d_um[2], bool saturated, float q_lim);
/* Once per stage tick: evaluates divergence and staleness against the Kalman
 * estimate and produces g->out. */
void ml_guard_tick(ml_guard_t *g, const float d_kf[2], float dt);

/* ---- input window (ICD s5) ---- */
typedef struct {
    float dp[PEN_ML_WINDOW][2];  /* um, ring buffer */
    uint16_t head;               /* next write index */
    uint16_t count;
    float p_last[2];             /* m, housing position at the last push */
    bool have_last;
} ml_window_t;

void ml_window_init(ml_window_t *w);
/* Push the housing page position (m) every ML_DECIM stage ticks (250 Hz). */
void ml_window_push(ml_window_t *w, const float p_h[2]);
/* Export oldest -> newest: out[2*W] (um) followed by f_est (Hz); returns
 * false until the window is full. */
bool ml_window_export(const ml_window_t *w, float f_est_hz, float out[2 * PEN_ML_WINDOW + 1]);

#endif /* PEN_ML_GUARD_H */
