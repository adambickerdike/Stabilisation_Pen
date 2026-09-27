/*
 * jacobian.h - compliance-aware page <-> stage Jacobian.
 *
 *   delta_page = J q,  J = Rot(phi) diag(J_t1, 1) Rot(rho),
 *   J_t1 = sin(theta) + gamma cos^2(theta) / sin(theta)
 *   q = J^-1 delta_page = Rot(-rho) diag(1/J_t1, 1) Rot(-phi) delta_page
 *
 * This is the form implemented in sim/pensim/core.py (Ji00..Ji11) and it
 * reduces to stabpen/frames.py jacobian() for gamma = 1 (rigid page,
 * J_t1 = 1/sin theta). NOTE: docs/icd.md s1 writes diag(1/J_t1, 1) in J,
 * which contradicts both (README discrepancy D1); the firmware follows the
 * simulator and frames.py.
 * gamma = fraction of the tilt-coupled axial accommodation taken by the
 * axial suspension (1) rather than the hand (0), from CAL_USER.
 */
#ifndef PEN_JACOBIAN_H
#define PEN_JACOBIAN_H

typedef struct {
    float ji[2][2];   /* page -> stage */
    float j[2][2];    /* stage -> page */
    float ct, st;     /* cos/sin theta (theta clamped, see JAC_THETA_MIN) */
    float cp, sp;     /* cos/sin phi */
    float cr, sr;     /* cos/sin rho */
    float xH[3], yH[3], a[3];  /* housing axes in the page frame */
    float jt1;
} jac_t;

/* Altitude is clamped to [JAC_THETA_MIN, pi/2] before use (sin(theta) in a
 * denominator); the simulator never goes below 35 deg. */
#define JAC_THETA_MIN 0.34906585f  /* 20 deg, proposed */

void jac_update(jac_t *J, float theta, float phi, float rho, float gamma);
void jac_page_to_stage(const jac_t *J, const float d_page[2], float q[2]);
void jac_stage_to_page(const jac_t *J, const float q[2], float d_page[2]);

#endif /* PEN_JACOBIAN_H */
