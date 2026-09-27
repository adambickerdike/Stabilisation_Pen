/*
 * estimator_bpf.h - band-pass + linear extrapolation baseline estimator.
 * Port of sim/pensim/core.py simulate() `mode == 2`: two cascaded biquads
 * (2nd-order Butterworth high-pass at bp_lo, low-pass at bp_hi), gain
 * compensation at bp_tune_hz, smoothed derivative, extrapolation by the
 * prediction horizon.
 */
#ifndef PEN_ESTIMATOR_BPF_H
#define PEN_ESTIMATOR_BPF_H

#include <stdbool.h>

#include "biquad.h"
#include "params.h"

typedef struct {
    biquad_state_t s1[2], s2[2];
    float y_prev[2];
    float yd[2];
    bool need_reinit;
    float dhat[2];
} bpf_est_t;

void bpf_est_init(bpf_est_t *e);
/* One 2 kHz tick. The filter always runs (as the simulator); the states are
 * reset on the first valid sample after an optical dropout (need_reinit). */
void bpf_est_tick(bpf_est_t *e, const pen_ctrl_params_t *p, const float ph[2], bool valid);

#endif /* PEN_ESTIMATOR_BPF_H */
