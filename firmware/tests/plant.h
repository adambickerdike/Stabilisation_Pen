/*
 * plant.h - C plant for closed-loop host tests (test infrastructure, double
 * precision). Evidence status of anything measured with it: HOST TEST on a
 * model, not hardware.
 *
 * Per axis: tip-equivalent stage m_eq q'' = -n Kf i - k_tip q - c_tip q' + F_ext
 * (+ stop), simulator sign convention; coil L di/dt = V - R_tot i - e,
 * e = -n Kf q'. The H-bridge is switched at the PWM clock (400 ticks of
 * 62.5 ns per 25 us period, centre-aligned) from the IN1/IN2 high times:
 * forward +V_M, reverse -V_M, brake 0 V (both low sides), coast = body-diode
 * freewheel into V_M. Exact exponential RL step per clock tick. The sense
 * voltage VREF + 1 V/A i passes the 1 k / 10 n anti-alias RC and is sampled
 * at the period edge (tick 0) and centre (tick 200) by a 12-bit differential
 * SAADC model (+/-1.2 V, gaussian noise). The Hall sensor samples q with a
 * delay and noise and returns raw codes through the inverse of the default
 * CAL_HALL map.
 */
#ifndef PEN_TEST_PLANT_H
#define PEN_TEST_PLANT_H

#include <stdbool.h>
#include <stdint.h>

#include "current_loop.h"
#include "hall.h"
#include "tr.h"

#define PLANT_TICKS 400
#define PLANT_QHIST 64

typedef struct {
    /* parameters */
    double m_eq, k_tip, c_tip, n, kf, r_coil, r_ext, L, vm, v_diode;
    double f_ext[2];
    double q_stop, k_stop;
    double adc_noise_a;      /* rms, amps */
    double isns_offset_a[2]; /* sense offset (amps) */
    double hall_noise_m;
    int hall_delay_periods;
    double f_ax;             /* axial force for the Hall z channel, N */
    /* state */
    double q[2], qd[2], i[2], vaa[2];
    double t;
    double i_sum[2];         /* integral of i over the period (for averages) */
    double q_hist[PLANT_QHIST][2];
    uint32_t periods;
    bool hall_frozen;
    int16_t hall_frozen_raw[3];
    tr_rng_t rng;
    cal_hall_t cal;
} plant_t;

void plant_init(plant_t *p, double vm, double coil_temp_c);
/* Advance one PWM period with the given bridge commands; returns the SAADC
 * codes of the period edge (start) and centre. */
void plant_period(plant_t *p, const bridge_cmd_t cmd[2], int16_t adc_e[2], int16_t adc_c[2]);
/* Hall raw codes for the current tick (delayed, noisy; frozen if requested). */
void plant_hall(plant_t *p, int16_t raw[3]);

#endif /* PEN_TEST_PLANT_H */
