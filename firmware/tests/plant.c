/*
 * plant.c - switched-bridge coil + stage plant (see header). Test infrastructure.
 */
#include "plant.h"

#include <math.h>
#include <string.h>

#include "params_gen.h"

void plant_init(plant_t *p, double vm, double coil_temp_c)
{
    memset(p, 0, sizeof(*p));
    p->m_eq = PEN_M_EQ;
    p->k_tip = PEN_K_TIP;
    p->c_tip = PEN_C_TIP;
    p->n = PEN_N_LEVER;
    p->kf = PEN_KF20 * (1.0 + PEN_ALPHA_B * (coil_temp_c - 20.0));
    p->r_coil = PEN_R20 * (1.0 + PEN_ALPHA_CU * (coil_temp_c - 20.0));
    p->r_ext = PEN_R_BRIDGE + PEN_R_SHUNT;
    p->L = PEN_L_COIL;
    p->vm = vm;
    p->v_diode = 0.7;
    p->q_stop = PEN_Q_STOP;
    p->k_stop = 2.0e5;
    p->adc_noise_a = 0.55e-3;       /* drive_sense total_noise_mA_rms_per_sample */
    p->hall_noise_m = 1.0e-6;       /* config sensing.hall_noise_tip */
    p->hall_delay_periods = 4;      /* 0.1 ms, config sensing.hall_delay */
    p->f_ax = PEN_F_PRE;
    tr_rng_seed(&p->rng, 12345u);
    cal_hall_default(&p->cal);
}

static int16_t adc_code(plant_t *p, double vaa)
{
    const double lsb = PEN_SAADC_DIFF_FS_V / 2048.0;
    const double v = (vaa - PEN_ISNS_VREF) + tr_rng_normal(&p->rng) * p->adc_noise_a * PEN_ISNS_V_PER_A;
    double c = floor(v / lsb + 0.5);
    if (c > 2047.0) {
        c = 2047.0;
    }
    if (c < -2048.0) {
        c = -2048.0;
    }
    return (int16_t)c;
}

void plant_period(plant_t *p, const bridge_cmd_t cmd[2], int16_t adc_e[2], int16_t adc_c[2])
{
    const double dt = 1.0 / (PEN_F_PWM_HZ * PLANT_TICKS);
    const double r_tot = p->r_coil + p->r_ext;
    const double ex = exp(-dt * r_tot / p->L);
    const double tau_aa = 1.0e3 * 10.0e-9;
    const double eaa = exp(-dt / tau_aa);
    for (int ax = 0; ax < 2; ax++) {
        p->i_sum[ax] = 0.0;
    }
    for (int k = 0; k < PLANT_TICKS; k++) {
        for (int ax = 0; ax < 2; ax++) {
            if (k == 0) {
                adc_e[ax] = adc_code(p, p->vaa[ax]);
            } else if (k == PLANT_TICKS / 2) {
                adc_c[ax] = adc_code(p, p->vaa[ax]);
            }
            const int hi1 = cmd[ax].in1_high, hi2 = cmd[ax].in2_high;
            const bool in1 = (k < hi1) || (k >= PLANT_TICKS - hi1);
            const bool in2 = (k < hi2) || (k >= PLANT_TICKS - hi2);
            const double emf = -p->n * p->kf * p->qd[ax];
            double i = p->i[ax];
            if (in1 && !in2) {
                i = i * ex + (p->vm - emf) / r_tot * (1.0 - ex);
            } else if (!in1 && in2) {
                i = i * ex + (-p->vm - emf) / r_tot * (1.0 - ex);
            } else if (in1 && in2) {
                i = i * ex + (0.0 - emf) / r_tot * (1.0 - ex);
            } else {
                /* coast: body diodes return the current to V_M until it reaches zero */
                if (i != 0.0) {
                    const double v = -(i > 0.0 ? 1.0 : -1.0) * (p->vm + 2.0 * p->v_diode);
                    const double inew = i * ex + (v - emf) / r_tot * (1.0 - ex);
                    i = (inew * i <= 0.0) ? 0.0 : inew;
                }
            }
            p->i[ax] = i;
            p->i_sum[ax] += i * dt;
            const double visns = PEN_ISNS_VREF + PEN_ISNS_V_PER_A * (i + p->isns_offset_a[ax]);
            p->vaa[ax] = p->vaa[ax] * eaa + visns * (1.0 - eaa);
        }
    }
    /* mechanics, semi-implicit Euler over the period with the mean current */
    const double T = 1.0 / PEN_F_PWM_HZ;
    const double rq = hypot(p->q[0], p->q[1]);
    for (int ax = 0; ax < 2; ax++) {
        const double imean = p->i_sum[ax] / T;
        double f = -p->n * p->kf * imean - p->k_tip * p->q[ax] - p->c_tip * p->qd[ax] + p->f_ext[ax];
        if (rq > p->q_stop) {
            f += -p->k_stop * (rq - p->q_stop) * p->q[ax] / rq;
        }
        p->qd[ax] += f / p->m_eq * T;
        p->q[ax] += p->qd[ax] * T;
    }
    const uint32_t h = p->periods % PLANT_QHIST;
    p->q_hist[h][0] = p->q[0];
    p->q_hist[h][1] = p->q[1];
    p->periods++;
    p->t += T;
}

void plant_hall(plant_t *p, int16_t raw[3])
{
    if (p->hall_frozen) {
        memcpy(raw, p->hall_frozen_raw, sizeof(p->hall_frozen_raw));
        return;
    }
    const uint32_t d = (uint32_t)p->hall_delay_periods;
    const uint32_t idx = (p->periods + PLANT_QHIST - 1u - d) % PLANT_QHIST;
    /* inverse of the default (diagonal) CAL_HALL map */
    const double s = (p->f_ax > PEN_F_PRE) ? (p->f_ax - PEN_F_PRE) / PEN_K_AX : 0.0;
    const double y[3] = {p->q_hist[idx][0] + p->hall_noise_m * tr_rng_normal(&p->rng),
                         p->q_hist[idx][1] + p->hall_noise_m * tr_rng_normal(&p->rng),
                         s + 0.2e-6 * tr_rng_normal(&p->rng)};
    for (int k = 0; k < 3; k++) {
        const double B = y[k] / (double)p->cal.m[k][k];
        double c = floor(B / (double)p->cal.lsb_T + 0.5);
        c = c > 32767.0 ? 32767.0 : (c < -32768.0 ? -32768.0 : c);
        raw[k] = (int16_t)c;
    }
    memcpy(p->hall_frozen_raw, raw, sizeof(p->hall_frozen_raw));
}
