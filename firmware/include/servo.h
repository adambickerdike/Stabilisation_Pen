/*
 * servo.h - 2 kHz stage position servo (tip-equivalent force), port of
 * sim/pensim/core.py simulate() "position servo":
 *   F = Kp e + Kd d(e)/dt (filtered) + Ki int(e)
 *     + ff_ref   (m_eq q_r'' + k_tip q_r + c_tip q_r')           reference FF
 *     + ff_contact lam (N_hat cos th cos rho, -N_hat cos th sin rho)  contact FF
 *       with N_hat = biquad_60Hz(F_ax / sin th)   (DEC-011: gain 0 by default)
 *     - ff_accel m_couple (a_page . x_H, a_page . y_H)          base-accel FF
 *   i_ref = -F / (n Kf), clamped to +/- i_max.
 * Integrator anti-windup: no integration while the current reference is
 * clamped or while the current loop reported voltage saturation.
 * Sign convention of the simulator: stage force on q = -n Kf i
 * (README discrepancy D2: the ICD s1 text says +n Kf i).
 */
#ifndef PEN_SERVO_H
#define PEN_SERVO_H

#include <stdbool.h>

#include "biquad.h"
#include "params.h"

typedef struct {
    float qr[2], qr_prev[2], qr_prev2[2];  /* reference history, m */
    float eint[2], eprev[2], ed_f[2];
    biquad_state_t ffs;                     /* contact-force filter state */
    float nh_f;                             /* filtered N_hat, N */
    float force[2];                         /* tip-equivalent force command, N */
    float iref[2];                          /* A */
    bool sat_i[2];
} servo_t;

typedef struct {
    float qm[2];          /* measured stage position, m */
    float fa;             /* measured axial force, N */
    bool in_contact;
    float lam_hat;        /* lever-arm shortening estimate */
    float ct, st, cr, sr; /* orientation terms */
    float xH[2], yH[2];   /* page x,y components of the housing axes */
    float a_page[2];      /* IMU page-plane acceleration, m/s^2 */
    bool v_sat;           /* current loop voltage saturation since last tick */
    float i_max;          /* current limit (A), may be derated */
} servo_in_t;

void servo_init(servo_t *s);
/* Shift the reference history and apply the new (already limited) reference. */
void servo_push_ref(servo_t *s, const float qr_new[2]);
/* Run the servo for one tick; writes s->iref. */
void servo_step(servo_t *s, const pen_ctrl_params_t *p, const servo_in_t *in);
/* Freeze the servo (hold/coast): clears derivative memory so that resuming
 * does not produce a derivative kick; keeps the integrator. */
void servo_resync(servo_t *s, const float qm[2]);

#endif /* PEN_SERVO_H */
