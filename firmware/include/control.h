/*
 * control.h - 2 kHz stage tick: estimator -> authority -> axial compensation
 * -> page-to-stage Jacobian -> radial soft limit -> slew -> servo -> current
 * references. The order and arithmetic follow the control tick of
 * sim/pensim/core.py simulate() line by line; with g_cap = 1 and the
 * simulator's inputs the outputs match the simulator (tests/test_replay.c).
 * Firmware additions (identity when disabled): authority cap g_cap (state
 * machine, thermal derate, CAL_USER g_max, training schedule), ML estimate
 * with Kalman fallback, derated current limit.
 */
#ifndef PEN_CONTROL_H
#define PEN_CONTROL_H

#include <stdbool.h>

#include "estimator_bpf.h"
#include "estimator_kf.h"
#include "guided.h"
#include "jacobian.h"
#include "params.h"
#include "servo.h"

typedef struct {
    float qm[2];        /* measured stage position (tip-equivalent), m */
    float fa;           /* measured axial force, N */
    float ph[2];        /* fused housing page position, m */
    bool opt_valid;     /* optical valid */
    float a_page[2];    /* IMU page-plane acceleration, m/s^2 */
    float theta, phi, rho;
    bool v_sat;         /* current loop clamped since the last tick */
    float g_cap;        /* authority cap 0..1 (1 = simulator behaviour) */
    float i_max;        /* A */
    pen_est_t est;      /* estimator in use */
    const float *d_ml;  /* ML (guarded) disturbance estimate, m; used when est == PEN_EST_ML */
    bool servo_on;      /* false: servo not evaluated (coast / hold) */
} ctrl_in_t;

typedef struct {
    pen_ctrl_params_t prm;
    kf_est_t kf;
    bpf_est_t bpf;
    guided_t guided;
    servo_t servo;
    jac_t jac;
    float g_eff;          /* smoothed authority */
    float target_g;
    float conf;
    float dhat[2];        /* estimate used for the correction (page, m) */
    float corr[2];
    float qn[2];          /* limited stage reference before slew */
    float s_lp;           /* axial compensation state */
    bool was_contact;
    bool in_contact;
    bool valid_prev;
    float lam_hat;
    float ax_c[2];
    /* Local origin of the estimator input (firmware option, default on):
     * the estimators see p_H - origin, origin = p_H at each optical
     * re-acquisition. The Kalman filter is shift invariant (its position state
     * is initialised at the measurement), so its output is unchanged; the
     * band-pass baseline loses the re-initialisation step transient of the
     * simulator (README discrepancy D9) and float32 keeps sub-nm resolution
     * anywhere on the page. Off = exact simulator behaviour (replay tests). */
    bool local_origin;
    float origin[2];
} ctrl_t;

void ctrl_init(ctrl_t *c, pen_profile_t profile);
void ctrl_tick(ctrl_t *c, const ctrl_in_t *in);
static inline bool ctrl_contact(float fa) { return fa > PEN_F_PRE + PEN_CONTACT_DF; }

#endif /* PEN_CONTROL_H */
