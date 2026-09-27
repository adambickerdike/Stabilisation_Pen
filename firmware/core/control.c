/*
 * control.c - stage tick orchestration (see header).
 * Status: PROPOSED DESIGN; replayed against the numba simulator
 * (tests/test_replay.c) with float32 tolerances.
 */
#include "control.h"

#include <math.h>
#include <string.h>

#include "limiter.h"
#include "mathx.h"

void ctrl_init(ctrl_t *c, pen_profile_t profile)
{
    memset(c, 0, sizeof(*c));
    pen_params_default(&c->prm, profile);
    kf_est_init(&c->kf, &c->prm);
    bpf_est_init(&c->bpf);
    guided_init(&c->guided, NULL, 0);
    servo_init(&c->servo);
    jac_update(&c->jac, PEN_THETA_NOM, 0.0f, 0.0f, c->prm.gamma);
    c->lam_hat = 1.0f;
}

void ctrl_tick(ctrl_t *c, const ctrl_in_t *in)
{
    const float Ts = PEN_TS_STAGE;
    pen_ctrl_params_t *p = &c->prm;
    const bool valid = in->opt_valid;
    const bool in_contact = ctrl_contact(in->fa);
    c->in_contact = in_contact;
    /* optical 0 -> 1 transition: estimators reinitialise (sim: need_reinit) */
    if (valid && !c->valid_prev) {
        c->kf.need_reinit = true;
        c->bpf.need_reinit = true;
    }
    c->valid_prev = valid;

    jac_update(&c->jac, in->theta, in->phi, in->rho, p->gamma);

    /* ---- disturbance estimate and page correction ---- */
    float corr0 = 0.0f, corr1 = 0.0f;
    float target_g = 0.0f;
    const float g_as = p->g_assist;
    /* the Kalman filter always runs: fallback for ML, f_est for the log */
    kf_est_tick(&c->kf, p, in->ph, valid);
    switch (in->est) {
    case PEN_EST_BPF:
        bpf_est_tick(&c->bpf, p, in->ph, valid);
        c->dhat[0] = c->bpf.dhat[0];
        c->dhat[1] = c->bpf.dhat[1];
        corr0 = -c->dhat[0];
        corr1 = -c->dhat[1];
        target_g = (valid && in_contact) ? g_as : 0.0f;
        c->conf = 1.0f;
        break;
    case PEN_EST_KF:
    case PEN_EST_ML:
        if (c->kf.updated) {
            const float *d = c->kf.dhat;
            if (in->est == PEN_EST_ML && in->d_ml != NULL) {
                d = in->d_ml;
            }
            c->dhat[0] = d[0];
            c->dhat[1] = d[1];
            c->conf = c->kf.conf;
            corr0 = -c->dhat[0];
            corr1 = -c->dhat[1];
            target_g = in_contact ? g_as * c->conf : 0.0f;
        }
        break;
    case PEN_EST_GUIDED:
        guided_tick(&c->guided, in->ph, valid, in_contact, p->q_lim);
        if (c->guided.active) {
            corr0 = c->guided.corr[0];
            corr1 = c->guided.corr[1];
            c->dhat[0] = c->guided.dhat[0];
            c->dhat[1] = c->guided.dhat[1];
            c->conf = c->guided.conf;
            target_g = in_contact ? g_as * c->conf : 0.0f;
        }
        break;
    case PEN_EST_NONE:
    default:
        break;
    }
    /* firmware authority cap (identity at 1) */
    target_g = pen_minf(target_g, pen_minf(in->g_cap, p->g_max));
    c->target_g = target_g;
    c->g_eff = lim_authority_step(c->g_eff, target_g, p->alpha_a);

    /* ---- axial-slide compensation (off by default, as the simulator) ---- */
    const float s_meas = pen_maxf(0.0f, (in->fa - PEN_F_PRE) / PEN_K_AX);
    if (in_contact && c->was_contact) {
        c->s_lp += (Ts / pen_maxf(p->axial_comp_tau, 1e-3f)) * (s_meas - c->s_lp);
    } else if (in_contact && !c->was_contact) {
        c->s_lp = 0.0f;
    }
    c->was_contact = in_contact;
    float ax_c0 = 0.0f, ax_c1 = 0.0f;
    if (p->axial_comp > 0.5f && in_contact) {
        const float ds = s_meas - c->s_lp;
        ax_c0 = -ds * c->jac.ct * c->jac.cp;
        ax_c1 = -ds * c->jac.ct * c->jac.sp;
        const float am = hypotf(ax_c0, ax_c1);
        if (am > PEN_AXIAL_COMP_MAX) {
            ax_c0 *= PEN_AXIAL_COMP_MAX / am;
            ax_c1 *= PEN_AXIAL_COMP_MAX / am;
        }
    }
    c->ax_c[0] = ax_c0;
    c->ax_c[1] = ax_c1;

    /* ---- page correction -> stage, lever-arm shortening ---- */
    const float s_hat = s_meas;
    c->lam_hat = pen_maxf(PEN_LAM_MIN, 1.0f - p->kappa_s * s_hat / PEN_L1);
    const float (*Ji)[2] = c->jac.ji;
    float qn[2];
    qn[0] = (c->g_eff * (Ji[0][0] * corr0 + Ji[0][1] * corr1) + (Ji[0][0] * ax_c0 + Ji[0][1] * ax_c1)) / c->lam_hat;
    qn[1] = (c->g_eff * (Ji[1][0] * corr0 + Ji[1][1] * corr1) + (Ji[1][0] * ax_c0 + Ji[1][1] * ax_c1)) / c->lam_hat;
    c->corr[0] = corr0;
    c->corr[1] = corr1;
    lim_radial_taper(qn, p->q_lim, p->q_taper);
    c->qn[0] = qn[0];
    c->qn[1] = qn[1];
    float qr_new[2] = {c->servo.qr[0], c->servo.qr[1]};
    lim_slew(qr_new, qn, p->slew * Ts);
    servo_push_ref(&c->servo, qr_new);

    /* ---- position servo ---- */
    if (in->servo_on) {
        servo_in_t si;
        si.qm[0] = in->qm[0];
        si.qm[1] = in->qm[1];
        si.fa = in->fa;
        si.in_contact = in_contact;
        si.lam_hat = c->lam_hat;
        si.ct = c->jac.ct;
        si.st = c->jac.st;
        si.cr = c->jac.cr;
        si.sr = c->jac.sr;
        si.xH[0] = c->jac.xH[0];
        si.xH[1] = c->jac.xH[1];
        si.yH[0] = c->jac.yH[0];
        si.yH[1] = c->jac.yH[1];
        si.a_page[0] = in->a_page[0];
        si.a_page[1] = in->a_page[1];
        si.v_sat = in->v_sat;
        si.i_max = in->i_max;
        servo_step(&c->servo, p, &si);
    } else {
        c->servo.iref[0] = 0.0f;
        c->servo.iref[1] = 0.0f;
    }
}
