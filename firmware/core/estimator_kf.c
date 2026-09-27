/*
 * estimator_kf.c - Kalman intent + oscillator estimator (see header).
 * Status: PROPOSED DESIGN, host-tested against the simulator (float64)
 * with float32-appropriate tolerances.
 */
#include "estimator_kf.h"

#include <math.h>
#include <string.h>

#include "mathx.h"

void kf_est_init(kf_est_t *e, const pen_ctrl_params_t *p)
{
    memset(e, 0, sizeof(*e));
    for (int ax = 0; ax < 2; ax++) {
        for (int i = 0; i < KF_NX; i++) {
            e->P[ax][i][i] = PEN_KF_P_INIT;
        }
    }
    e->w = p->kf_w0;
    e->nis_f = 1.0f;
    e->need_reinit = true;
}

void kf_step5(float x[KF_NX], float P[KF_NX][KF_NX], float y, float Ts, float w, float rdamp,
              const float q[KFQ_N], float r, float *innov, float *S)
{
    const float c = cosf(w * Ts);
    const float s = sinf(w * Ts);
    float F[KF_NX][KF_NX];
    memset(F, 0, sizeof(F));
    F[0][0] = 1.0f;
    F[0][1] = Ts;
    F[0][2] = 0.5f * Ts * Ts;
    F[1][1] = 1.0f;
    F[1][2] = Ts;
    F[2][2] = 1.0f;
    F[3][3] = rdamp * c;
    F[3][4] = rdamp * s;
    F[4][3] = -rdamp * s;
    F[4][4] = rdamp * c;

    float Q[KF_NX][KF_NX];
    memset(Q, 0, sizeof(Q));
    Q[0][0] = q[KFQ_00];
    Q[0][1] = q[KFQ_01];
    Q[0][2] = q[KFQ_02];
    Q[1][0] = q[KFQ_01];
    Q[1][1] = q[KFQ_11];
    Q[1][2] = q[KFQ_12];
    Q[2][0] = q[KFQ_02];
    Q[2][1] = q[KFQ_12];
    Q[2][2] = q[KFQ_22];
    Q[3][3] = q[KFQ_OSC];
    Q[4][4] = q[KFQ_OSC];

    /* xp = F x */
    float xp[KF_NX];
    for (int i = 0; i < KF_NX; i++) {
        float acc = 0.0f;
        for (int k = 0; k < KF_NX; k++) {
            acc += F[i][k] * x[k];
        }
        xp[i] = acc;
    }
    /* Pp = F P F^T + Q */
    float FP[KF_NX][KF_NX];
    for (int i = 0; i < KF_NX; i++) {
        for (int j = 0; j < KF_NX; j++) {
            float acc = 0.0f;
            for (int k = 0; k < KF_NX; k++) {
                acc += F[i][k] * P[k][j];
            }
            FP[i][j] = acc;
        }
    }
    float Pp[KF_NX][KF_NX];
    for (int i = 0; i < KF_NX; i++) {
        for (int j = 0; j < KF_NX; j++) {
            float acc = 0.0f;
            for (int k = 0; k < KF_NX; k++) {
                acc += FP[i][k] * F[j][k];
            }
            Pp[i][j] = acc + Q[i][j];
        }
    }
    /* measurement y = p + x1 + noise */
    const float in = y - (xp[0] + xp[3]);
    const float Sv = Pp[0][0] + Pp[0][3] + Pp[3][0] + Pp[3][3] + r;
    float K[KF_NX];
    for (int i = 0; i < KF_NX; i++) {
        K[i] = (Pp[i][0] + Pp[i][3]) / Sv;
    }
    for (int i = 0; i < KF_NX; i++) {
        x[i] = xp[i] + K[i] * in;
    }
    /* P = (I - K H) Pp, symmetrised (as the reference; Joseph form omitted) */
    for (int i = 0; i < KF_NX; i++) {
        for (int j = 0; j < KF_NX; j++) {
            P[i][j] = Pp[i][j] - K[i] * (Pp[0][j] + Pp[3][j]);
        }
    }
    for (int i = 0; i < KF_NX; i++) {
        for (int j = i + 1; j < KF_NX; j++) {
            const float m = 0.5f * (P[i][j] + P[j][i]);
            P[i][j] = m;
            P[j][i] = m;
        }
    }
    *innov = in;
    *S = Sv;
}

void kf_est_tick(kf_est_t *e, const pen_ctrl_params_t *p, const float ph[2], bool valid)
{
    const float Ts = PEN_TS_STAGE;
    e->updated = false;
    if (!valid) {
        e->need_reinit = true;   /* sim: need_reinit = 1; target_g = 0 */
        return;
    }
    if (e->need_reinit) {
        for (int ax = 0; ax < 2; ax++) {
            memset(e->x[ax], 0, sizeof(e->x[ax]));
            memset(e->P[ax], 0, sizeof(e->P[ax]));
            e->x[ax][0] = ph[ax];
            e->P[ax][0][0] = PEN_KF_P0_POS;
            e->P[ax][1][1] = PEN_KF_P0_VEL;
            e->P[ax][2][2] = PEN_KF_P0_ACC;
            e->P[ax][3][3] = PEN_KF_P0_OSC;
            e->P[ax][4][4] = PEN_KF_P0_OSC;
        }
        e->need_reinit = false;
    }
    float nis_sum = 0.0f;
    for (int ax = 0; ax < 2; ax++) {
        float in, S;
        kf_step5(e->x[ax], e->P[ax], ph[ax], Ts, e->w, p->kf_rdamp, p->kf_q, p->kf_r, &in, &S);
        nis_sum += in * in / S;
    }
    e->nis_f = e->nis_f + PEN_NIS_ALPHA * (0.5f * nis_sum - e->nis_f);
    /* frequency adaptation from the oscillator phase rate (amplitude weighted) */
    const float amp0 = hypotf(e->x[0][3], e->x[0][4]);
    const float amp1 = hypotf(e->x[1][3], e->x[1][4]);
    const int axm = (amp0 >= amp1) ? 0 : 1;
    const float ampm = (axm == 0) ? amp0 : amp1;
    const float phs = atan2f(e->x[axm][4], e->x[axm][3]);
    if (e->kf_init && ampm > PEN_KF_AMP_MIN) {
        const float dph = pen_wrap_pi(phs - e->phase_prev);
        const float wm = -dph / Ts;
        e->w = e->w + p->kf_wgain * (wm - e->w);
        e->w = pen_clampf(e->w, p->kf_wmin, p->kf_wmax);
    }
    e->phase_prev = phs;
    e->kf_init = true;
    /* prediction of the oscillator component `horizon` ahead */
    const float ch = cosf(e->w * p->horizon);
    const float sh = sinf(e->w * p->horizon);
    for (int ax = 0; ax < 2; ax++) {
        e->dhat[ax] = p->kf_rh * (ch * e->x[ax][3] + sh * e->x[ax][4]);
    }
    e->conf_nis = pen_clampf(1.0f - (e->nis_f - 1.0f) / pen_maxf(p->conf_nis_hi - 1.0f, 1e-6f), 0.0f, 1.0f);
    e->gate = 1.0f;
    if (p->f_gate > 0.0f) {
        const float f_tr = kf_est_freq_hz(e);
        e->gate = pen_clampf((f_tr - (p->f_gate - 0.5f * p->f_gate_width)) / pen_maxf(p->f_gate_width, 1e-6f), 0.0f, 1.0f);
    }
    e->conf = e->conf_nis * e->gate;
    e->updated = true;
}
