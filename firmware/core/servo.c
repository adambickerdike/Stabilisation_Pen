/*
 * servo.c - stage position servo (see header).
 * Status: PROPOSED DESIGN, host-tested (replay against the simulator and a
 * closed loop with the C plant in tests/plant.c).
 */
#include "servo.h"

#include <string.h>

#include "mathx.h"

void servo_init(servo_t *s)
{
    memset(s, 0, sizeof(*s));
}

void servo_push_ref(servo_t *s, const float qr_new[2])
{
    for (int ax = 0; ax < 2; ax++) {
        s->qr_prev2[ax] = s->qr_prev[ax];
        s->qr_prev[ax] = s->qr[ax];
        s->qr[ax] = qr_new[ax];
    }
}

void servo_resync(servo_t *s, const float qm[2])
{
    for (int ax = 0; ax < 2; ax++) {
        s->eprev[ax] = s->qr[ax] - qm[ax];
        s->ed_f[ax] = 0.0f;
    }
}

void servo_step(servo_t *s, const pen_ctrl_params_t *p, const servo_in_t *in)
{
    const float Ts = PEN_TS_STAGE;
    const float invTs = 1.0f / Ts;
    float F[2];
    float em[2];
    for (int ax = 0; ax < 2; ax++) {
        em[ax] = s->qr[ax] - in->qm[ax];
        const float ed = (em[ax] - s->eprev[ax]) * invTs;
        s->ed_f[ax] += p->alpha_d * (ed - s->ed_f[ax]);
        s->eprev[ax] = em[ax];
        F[ax] = p->kp * em[ax] + p->kd * s->ed_f[ax] + p->ki * s->eint[ax];
        if (p->ff_ref > 0.0f) {
            const float qdd = (s->qr[ax] - 2.0f * s->qr_prev[ax] + s->qr_prev2[ax]) * (invTs * invTs);
            F[ax] += p->ff_ref * (PEN_M_EQ * qdd + PEN_K_TIP * s->qr[ax] + PEN_C_TIP * (s->qr[ax] - s->qr_prev[ax]) * invTs);
        }
    }
    /* contact-load feedforward: the filter always runs so its state is
     * continuous when the gain is changed on the bench (DEC-011) */
    s->nh_f = biquad_step(&p->ffc, &s->ffs, in->in_contact ? (in->fa / in->st) : 0.0f);
    if (p->ff_contact > 0.0f && in->in_contact) {
        const float nh = s->nh_f;
        F[0] += p->ff_contact * in->lam_hat * (nh * in->ct * in->cr);
        F[1] += p->ff_contact * in->lam_hat * (-nh * in->ct * in->sr);
    }
    if (p->ff_accel > 0.0f) {
        F[0] += -p->ff_accel * PEN_M_COUPLE * (in->a_page[0] * in->xH[0] + in->a_page[1] * in->xH[1]);
        F[1] += -p->ff_accel * PEN_M_COUPLE * (in->a_page[0] * in->yH[0] + in->a_page[1] * in->yH[1]);
    }
    const float k_i = -1.0f / (PEN_N_LEVER * PEN_KF20);
    for (int ax = 0; ax < 2; ax++) {
        s->force[ax] = F[ax];
        const float i = F[ax] * k_i;
        s->sat_i[ax] = pen_absf(i) > in->i_max;
        s->iref[ax] = pen_clampf(i, -in->i_max, in->i_max);
        if (!s->sat_i[ax] && !in->v_sat) {
            s->eint[ax] += em[ax] * Ts;
        }
    }
}
