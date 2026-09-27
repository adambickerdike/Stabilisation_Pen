/*
 * estimator_kf.h - Kalman intent + oscillator disturbance estimator.
 *
 * Port of sim/pensim/core.py: _kf_step() and the `mode == 3` block of
 * simulate() (frequency tracking from the oscillator phase rate, NIS
 * confidence, frequency gate, prediction over the horizon).
 * States per page axis: p, v, a (intended motion, white jerk) and x1, x2
 * (damped rotating oscillator = tremor). Measurement y = p + x1 + noise.
 * float32 only. Verified against golden vectors from the numba reference
 * (tests/test_kf.c, tests/test_replay.c).
 */
#ifndef PEN_ESTIMATOR_KF_H
#define PEN_ESTIMATOR_KF_H

#include <stdbool.h>

#include "params.h"

#define KF_NX 5

typedef struct {
    float x[2][KF_NX];
    float P[2][KF_NX][KF_NX];
    float w;           /* tracked oscillator frequency, rad/s (shared by both axes) */
    float phase_prev;  /* rad */
    float nis_f;       /* filtered normalised innovation squared */
    bool kf_init;      /* at least one update since power-up */
    bool need_reinit;  /* reinitialise at the next valid sample */
    /* outputs of the last tick */
    float dhat[2];     /* predicted disturbance at t + horizon, page frame, m (held when invalid) */
    float conf_nis;    /* NIS confidence before the gate, 0..1 */
    float gate;        /* frequency gate factor, 0..1 */
    float conf;        /* conf_nis * gate */
    bool updated;      /* dhat refreshed this tick (optical valid) */
} kf_est_t;

void kf_est_init(kf_est_t *e, const pen_ctrl_params_t *p);

/* One predict + update of the 5-state filter (exact port of _kf_step).
 * q: precomputed process noise (KFQ_*). Returns innovation and its variance. */
void kf_step5(float x[KF_NX], float P[KF_NX][KF_NX], float y, float Ts, float w, float rdamp,
              const float q[KFQ_N], float r, float *innov, float *S);

/* One 2 kHz tick. ph: fused housing page position (m); valid: optical valid. */
void kf_est_tick(kf_est_t *e, const pen_ctrl_params_t *p, const float ph[2], bool valid);

/* Tracked frequency in Hz. */
static inline float kf_est_freq_hz(const kf_est_t *e) { return e->w * 0.159154943091895336f; }

#endif /* PEN_ESTIMATOR_KF_H */
