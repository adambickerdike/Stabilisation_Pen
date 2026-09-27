/*
 * limiter.c - radial soft limit and slew limit (see header).
 * Status: PROPOSED DESIGN, host property tests.
 */
#include "limiter.h"

#include <math.h>

void lim_radial_taper(float q[2], float q_lim, float q_taper)
{
    const float rq = hypotf(q[0], q[1]);
    const float knee = q_lim - q_taper;
    if (rq > knee && rq > 0.0f && q_taper > 0.0f) {
        const float rnew = knee + q_taper * tanhf((rq - knee) / q_taper);
        const float k = rnew / rq;
        q[0] *= k;
        q[1] *= k;
    }
}

void lim_slew(float qr[2], const float qn[2], float dmax)
{
    float dq0 = qn[0] - qr[0];
    float dq1 = qn[1] - qr[1];
    const float dm = hypotf(dq0, dq1);
    if (dm > dmax) {
        const float k = dmax / dm;
        dq0 *= k;
        dq1 *= k;
    }
    qr[0] += dq0;
    qr[1] += dq1;
}
