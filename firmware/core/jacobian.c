/*
 * jacobian.c - compliance-aware Jacobian (see header).
 * Status: PROPOSED DESIGN, host-tested against stabpen/frames.py and the
 * simulator's closed form.
 */
#include "jacobian.h"

#include <math.h>

#include "mathx.h"

float jac_gamma(float r_n, float theta)
{
    const float th = pen_clampf(theta, JAC_THETA_MIN, 0.5f * PEN_PI_F);
    const float s = sinf(th);
    const float k = r_n * s * s;
    return k / (k + 1.0f);
}

void jac_update(jac_t *J, float theta, float phi, float rho, float gamma)
{
    const float th = pen_clampf(theta, JAC_THETA_MIN, 0.5f * PEN_PI_F);
    const float ct = cosf(th), st = sinf(th);
    const float hx = cosf(phi), hy = sinf(phi);
    const float cr = cosf(rho), sr = sinf(rho);
    J->ct = ct;
    J->st = st;
    J->cp = hx;
    J->sp = hy;
    J->cr = cr;
    J->sr = sr;
    /* basis vectors in the page frame (stabpen/frames.py basis()) */
    const float t1x = st * hx, t1y = st * hy, t1z = -ct;
    const float t2x = -hy, t2y = hx, t2z = 0.0f;
    J->xH[0] = cr * t1x + sr * t2x;
    J->xH[1] = cr * t1y + sr * t2y;
    J->xH[2] = cr * t1z + sr * t2z;
    J->yH[0] = -sr * t1x + cr * t2x;
    J->yH[1] = -sr * t1y + cr * t2y;
    J->yH[2] = -sr * t1z + cr * t2z;
    J->a[0] = ct * hx;
    J->a[1] = ct * hy;
    J->a[2] = st;
    /* inverse (sim/pensim/core.py): diag(1/J_t1, 1) Rot(-phi), then Rot(-rho) */
    const float jt1 = st + gamma * ct * ct / st;
    J->jt1 = jt1;
    const float a00 = hx / jt1, a01 = hy / jt1;
    const float a10 = -hy, a11 = hx;
    J->ji[0][0] = cr * a00 + sr * a10;
    J->ji[0][1] = cr * a01 + sr * a11;
    J->ji[1][0] = -sr * a00 + cr * a10;
    J->ji[1][1] = -sr * a01 + cr * a11;
    /* forward: Rot(phi) diag(J_t1, 1) Rot(rho) */
    const float b00 = jt1 * cr, b01 = -jt1 * sr;   /* diag(jt1,1) Rot(rho) */
    const float b10 = sr, b11 = cr;
    J->j[0][0] = hx * b00 - hy * b10;
    J->j[0][1] = hx * b01 - hy * b11;
    J->j[1][0] = hy * b00 + hx * b10;
    J->j[1][1] = hy * b01 + hx * b11;
}

void jac_page_to_stage(const jac_t *J, const float d_page[2], float q[2])
{
    const float d0 = d_page[0], d1 = d_page[1];
    q[0] = J->ji[0][0] * d0 + J->ji[0][1] * d1;
    q[1] = J->ji[1][0] * d0 + J->ji[1][1] * d1;
}

void jac_stage_to_page(const jac_t *J, const float q[2], float d_page[2])
{
    const float q0 = q[0], q1 = q[1];
    d_page[0] = J->j[0][0] * q0 + J->j[0][1] * q1;
    d_page[1] = J->j[1][0] * q0 + J->j[1][1] * q1;
}
