/*
 * fusion.h - housing page position p_H: optical (delayed) + IMU over the
 * optical latency gap, exactly as sim/pensim/core.py simulate():
 *   IMU (each sample, dt_i):  v <- (v + a dt_i)(1 - dt_i/0.5 s);  p <- p + v dt_i
 *   stage tick k:             p_H = o_meas + (p_imu(k) - p_imu(k - lag)),
 *                             lag = (opt_delay - imu_delay)/Ts ticks
 * o_meas is the most recent optical page position (already delayed by the
 * sensor). The ring keeps FUSION_RING_LEN ticks (the simulator keeps 1024;
 * 64 covers opt_delay - imu_delay up to 32 ms).
 * Attitude: theta, rho from the low-passed gravity direction in the housing
 * frame (page assumed horizontal); phi (page azimuth) integrates the gyro
 * about the page normal from phi = 0 at the first contact of a page session.
 * Optical module combination (3 modules, sensor-specific) is pending sensor
 * selection (EXP-S01): fusion_optical_sample() takes the combined page-frame
 * position and a validity flag.
 */
#ifndef PEN_FUSION_H
#define PEN_FUSION_H

#include <stdbool.h>
#include <stdint.h>

#define FUSION_RING_LEN 64u

typedef struct {
    float vimu[2], pimu[2];
    float ring[FUSION_RING_LEN][2];
    uint32_t tick;
    float o_meas[2];
    bool o_valid;
    uint16_t lag;
    /* attitude */
    float g_lp[3];      /* low-passed specific force in the housing frame */
    bool g_init;
    float theta, rho, phi;
} fusion_t;

void fusion_init(fusion_t *f, uint16_t lag_ticks);
void fusion_imu_sample(fusion_t *f, const float a_page[2], float dt_i);
void fusion_optical_sample(fusion_t *f, const float p_opt[2], bool ok);
/* Stage tick: returns the fused position and the validity (optical valid). */
void fusion_tick(fusion_t *f, float ph[2], bool *valid);

/* attitude from the accelerometer (housing frame, m/s^2) and gyro (rad/s) */
void fusion_attitude(fusion_t *f, const float acc_h[3], const float gyro_h[3], float dt, float tau);
void fusion_phi_reset(fusion_t *f);

#endif /* PEN_FUSION_H */
