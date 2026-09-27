/*
 * fusion.c - housing position fusion and attitude (see header).
 * Status: PROPOSED DESIGN; the p_H part is a port of the simulator (host
 * test with synthetic data); attitude is a minimal proposal (host test on
 * synthetic gravity vectors only).
 */
#include "fusion.h"

#include <math.h>
#include <string.h>

#include "mathx.h"
#include "params_gen.h"

void fusion_init(fusion_t *f, uint16_t lag_ticks)
{
    memset(f, 0, sizeof(*f));
    f->lag = (lag_ticks < FUSION_RING_LEN) ? lag_ticks : (uint16_t)(FUSION_RING_LEN - 1u);
    f->theta = PEN_THETA_NOM;
}

void fusion_imu_sample(fusion_t *f, const float a_page[2], float dt_i)
{
    for (int ax = 0; ax < 2; ax++) {
        f->vimu[ax] = (f->vimu[ax] + a_page[ax] * dt_i) * (1.0f - dt_i / PEN_IMU_LEAK_TAU);
        f->pimu[ax] += f->vimu[ax] * dt_i;
    }
}

void fusion_optical_sample(fusion_t *f, const float p_opt[2], bool ok)
{
    if (ok) {
        f->o_meas[0] = p_opt[0];
        f->o_meas[1] = p_opt[1];
    }
    f->o_valid = ok;
}

void fusion_tick(fusion_t *f, float ph[2], bool *valid)
{
    const uint32_t k = f->tick % FUSION_RING_LEN;
    f->ring[k][0] = f->pimu[0];
    f->ring[k][1] = f->pimu[1];
    const uint32_t j = (f->tick + FUSION_RING_LEN - f->lag) % FUSION_RING_LEN;
    ph[0] = f->o_meas[0] + (f->pimu[0] - f->ring[j][0]);
    ph[1] = f->o_meas[1] + (f->pimu[1] - f->ring[j][1]);
    *valid = f->o_valid;
    f->tick++;
}

void fusion_attitude(fusion_t *f, const float acc_h[3], const float gyro_h[3], float dt, float tau)
{
    const float a = dt / (tau + dt);
    for (int k = 0; k < 3; k++) {
        if (!f->g_init) {
            f->g_lp[k] = acc_h[k];
        } else {
            f->g_lp[k] += a * (acc_h[k] - f->g_lp[k]);
        }
    }
    f->g_init = true;
    /* at rest the specific force is +g n; in housing coordinates
     * n = (-cos th cos rho, cos th sin rho, sin th)  (stabpen/frames.py basis) */
    const float gx = f->g_lp[0], gy = f->g_lp[1], gz = f->g_lp[2];
    f->theta = atan2f(gz, hypotf(gx, gy));
    f->rho = atan2f(gy, -gx);
    const float gn = sqrtf(gx * gx + gy * gy + gz * gz);
    if (gn > 1e-3f) {
        /* yaw rate about the page normal: omega . n */
        const float wn = (gyro_h[0] * gx + gyro_h[1] * gy + gyro_h[2] * gz) / gn;
        f->phi = pen_wrap_pi(f->phi + wn * dt);
    }
}

void fusion_phi_reset(fusion_t *f)
{
    f->phi = 0.0f;
}
