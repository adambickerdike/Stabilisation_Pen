/*
 * params.c - fill runtime parameters from the generated constants.
 * Status: PROPOSED DESIGN (values from config/parameters.yaml and the
 * simulator's design rules; see include/params_gen.h for every source).
 */
#include "params.h"

#include <string.h>

void pen_params_default(pen_ctrl_params_t *p, pen_profile_t profile)
{
    memset(p, 0, sizeof(*p));
    p->profile = profile;
    if (profile == PEN_PROFILE_ASSERTIVE) {
        p->kf_q[KFQ_00] = PEN_ASR_KF_Q00;
        p->kf_q[KFQ_01] = PEN_ASR_KF_Q01;
        p->kf_q[KFQ_02] = PEN_ASR_KF_Q02;
        p->kf_q[KFQ_11] = PEN_ASR_KF_Q11;
        p->kf_q[KFQ_12] = PEN_ASR_KF_Q12;
        p->kf_q[KFQ_22] = PEN_ASR_KF_Q22;
        p->kf_q[KFQ_OSC] = PEN_ASR_KF_QOSC;
        p->kf_w0 = PEN_ASR_KF_W0;
        p->f_gate = PEN_ASR_F_GATE;
        p->bp1 = (biquad_coef_t){PEN_ASR_BP1_B0, PEN_ASR_BP1_B1, PEN_ASR_BP1_B2, PEN_ASR_BP1_A1, PEN_ASR_BP1_A2};
        p->bp2 = (biquad_coef_t){PEN_ASR_BP2_B0, PEN_ASR_BP2_B1, PEN_ASR_BP2_B2, PEN_ASR_BP2_A1, PEN_ASR_BP2_A2};
        p->bp_gain_comp = PEN_ASR_BP_GAIN_COMP;
    } else {
        p->kf_q[KFQ_00] = PEN_BAL_KF_Q00;
        p->kf_q[KFQ_01] = PEN_BAL_KF_Q01;
        p->kf_q[KFQ_02] = PEN_BAL_KF_Q02;
        p->kf_q[KFQ_11] = PEN_BAL_KF_Q11;
        p->kf_q[KFQ_12] = PEN_BAL_KF_Q12;
        p->kf_q[KFQ_22] = PEN_BAL_KF_Q22;
        p->kf_q[KFQ_OSC] = PEN_BAL_KF_QOSC;
        p->kf_w0 = PEN_BAL_KF_W0;
        p->f_gate = PEN_BAL_F_GATE;
        p->bp1 = (biquad_coef_t){PEN_BAL_BP1_B0, PEN_BAL_BP1_B1, PEN_BAL_BP1_B2, PEN_BAL_BP1_A1, PEN_BAL_BP1_A2};
        p->bp2 = (biquad_coef_t){PEN_BAL_BP2_B0, PEN_BAL_BP2_B1, PEN_BAL_BP2_B2, PEN_BAL_BP2_A1, PEN_BAL_BP2_A2};
        p->bp_gain_comp = PEN_BAL_BP_GAIN_COMP;
    }
    p->kf_r = PEN_KF_R;
    p->kf_rdamp = PEN_KF_RDAMP;
    p->kf_rh = PEN_KF_RH;
    p->kf_wgain = PEN_KF_WGAIN;
    p->kf_wmin = PEN_KF_WMIN;
    p->kf_wmax = PEN_KF_WMAX;
    p->conf_nis_hi = PEN_CONF_NIS_HI;
    p->horizon = PEN_HORIZON;
    p->f_gate_width = PEN_F_GATE_WIDTH;

    p->g_assist = PEN_G_ASSIST;
    p->g_max = 1.0f;
    p->q_lim = PEN_Q_LIM;
    p->q_taper = PEN_Q_TAPER;
    p->slew = PEN_SLEW;
    p->alpha_a = PEN_ALPHA_A;
    p->r_n = PEN_R_N_NOM;
    p->kappa_s = PEN_KAPPA_S;
    p->axial_comp = PEN_AXIAL_COMP;
    p->axial_comp_tau = PEN_AXIAL_COMP_TAU;

    p->kp = PEN_KP;
    p->kd = PEN_KD;
    p->ki = PEN_KI;
    p->alpha_d = PEN_ALPHA_D;
    p->ff_ref = PEN_FF_REF;
    p->ff_accel = PEN_FF_ACCEL;
    p->ff_contact = PEN_FF_CONTACT;
    p->ffc = (biquad_coef_t){PEN_FFC_B0, PEN_FFC_B1, PEN_FFC_B2, PEN_FFC_A1, PEN_FFC_A2};
    p->i_max = PEN_I_MAX;

    p->kp_i = PEN_KP_I;
    p->ki_i = PEN_KI_I;
    p->r_loop_ff = PEN_R_LOOP_FF;
    p->duty_max = PEN_DUTY_MAX;
    p->cur_r_ff = PEN_CUR_R_FF;
}
