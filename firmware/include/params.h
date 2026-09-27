/*
 * params.h - runtime controller parameters.
 *
 * Compile-time constants live in params_gen.h (generated from
 * config/parameters.yaml by tools/gen_params.py). The quantities a user
 * calibration (CAL_USER, ICD s3) or a bench experiment may change at run time
 * are copied into pen_ctrl_params_t, initialised from a profile.
 */
#ifndef PEN_PARAMS_H
#define PEN_PARAMS_H

#include "biquad.h"
#include "params_gen.h"
#include "pen_types.h"

/* Process-noise entries of the 5-state KF (sim/pensim/core.py _kf_step). */
enum { KFQ_00 = 0, KFQ_01, KFQ_02, KFQ_11, KFQ_12, KFQ_22, KFQ_OSC, KFQ_N };

typedef struct {
    pen_profile_t profile;
    /* ---- Kalman intent + oscillator estimator ---- */
    float kf_q[KFQ_N];   /* precomputed Q entries (SI) */
    float kf_r;          /* m^2 measurement noise */
    float kf_w0;         /* rad/s initial oscillator frequency */
    float kf_rdamp;      /* per-tick oscillator damping */
    float kf_rh;         /* rdamp^(horizon/Ts) */
    float kf_wgain, kf_wmin, kf_wmax;
    float conf_nis_hi;
    float horizon;       /* s prediction horizon */
    float f_gate;        /* Hz, 0 disables the frequency gate (CAL_USER) */
    float f_gate_width;  /* Hz (CAL_USER) */
    /* ---- band-pass baseline ---- */
    biquad_coef_t bp1, bp2;
    float bp_gain_comp;
    /* ---- authority, Jacobian, limits ---- */
    float g_assist;      /* nominal assistance gain */
    float g_max;         /* authority cap (CAL_USER) */
    float q_lim, q_taper, slew, alpha_a;
    float r_n;           /* K_n / k_ax (CAL_USER v2); gamma(theta) is computed from it at each Jacobian update */
    float kappa_s, axial_comp, axial_comp_tau;
    /* ---- servo ---- */
    float kp, kd, ki, alpha_d;
    float ff_ref, ff_accel, ff_contact;  /* ff_contact = 0 by default (DEC-011) */
    biquad_coef_t ffc;
    float i_max;
    /* ---- current loop ---- */
    float kp_i, ki_i, r_loop_ff, duty_max;
    float cur_r_ff;      /* 0: PI only (default, drive_sense design); 1: + R i_ref feedforward (simulator) */
} pen_ctrl_params_t;

void pen_params_default(pen_ctrl_params_t *p, pen_profile_t profile);

#endif /* PEN_PARAMS_H */
