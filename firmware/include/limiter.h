/*
 * limiter.h - correction limits (REQ-CTRL-004): radial soft limit with a
 * smooth tanh taper, command slew limit, authority fade.
 * Port of sim/pensim/core.py simulate() (radial soft limit, slew limit,
 * g_eff smoothing).
 */
#ifndef PEN_LIMITER_H
#define PEN_LIMITER_H

/* In place: radius r <= knee unchanged; beyond knee = q_lim - q_taper the
 * radius becomes knee + q_taper tanh((r - knee)/q_taper) < q_lim. */
void lim_radial_taper(float q[2], float q_lim, float q_taper);

/* Move qr toward qn by at most dmax (vector norm). */
void lim_slew(float qr[2], const float qn[2], float dmax);

/* First-order authority smoothing toward target (alpha = 1 - exp(-Ts/tau)). */
static inline float lim_authority_step(float g, float target, float alpha)
{
    return g + alpha * (target - g);
}

#endif /* PEN_LIMITER_H */
