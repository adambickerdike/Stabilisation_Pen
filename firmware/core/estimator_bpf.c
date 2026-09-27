/*
 * estimator_bpf.c - band-pass baseline estimator (see header).
 * Status: PROPOSED DESIGN, host-tested against the simulator.
 */
#include "estimator_bpf.h"

#include <string.h>

void bpf_est_init(bpf_est_t *e)
{
    memset(e, 0, sizeof(*e));
    e->need_reinit = true;
}

void bpf_est_tick(bpf_est_t *e, const pen_ctrl_params_t *p, const float ph[2], bool valid)
{
    const float Ts = PEN_TS_STAGE;
    if (e->need_reinit && valid) {
        for (int ax = 0; ax < 2; ax++) {
            biquad_reset(&e->s1[ax]);
            biquad_reset(&e->s2[ax]);
            if (e->reset_deriv) {
                e->y_prev[ax] = 0.0f;
                e->yd[ax] = 0.0f;
            }
        }
        e->need_reinit = false;
    }
    for (int ax = 0; ax < 2; ax++) {
        const float y1 = biquad_step(&p->bp1, &e->s1[ax], ph[ax]);
        float y2 = biquad_step(&p->bp2, &e->s2[ax], y1);
        y2 = y2 * p->bp_gain_comp;
        const float yd = (y2 - e->y_prev[ax]) / Ts;
        e->yd[ax] = e->yd[ax] + PEN_BP_DERIV_ALPHA * (yd - e->yd[ax]);
        e->y_prev[ax] = y2;
        e->dhat[ax] = y2 + p->horizon * e->yd[ax];
    }
}
