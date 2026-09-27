/*
 * guided.c - guided mode template follower (see header).
 * Status: PROPOSED DESIGN (port of the simulator; host unit test only).
 */
#include "guided.h"

#include <math.h>
#include <string.h>

void guided_init(guided_t *gd, const float (*tmpl)[2], uint32_t n)
{
    memset(gd, 0, sizeof(*gd));
    gd->tmpl = tmpl;
    gd->n = n;
    gd->reacq = true;
}

void guided_tick(guided_t *gd, const float ph[2], bool valid, bool in_contact, float q_lim)
{
    gd->corr[0] = 0.0f;
    gd->corr[1] = 0.0f;
    gd->active = false;
    if (gd->tmpl == NULL || gd->n == 0u) {
        gd->conf = 0.0f;
        return;
    }
    if (valid && in_contact) {
        float best = 1e9f;
        uint32_t bj = gd->prog;
        const uint32_t j0 = (gd->prog > 20u) ? gd->prog - 20u : 0u;
        const uint32_t span = gd->reacq ? 4000u : 200u;
        const uint32_t j1 = (gd->prog + span < gd->n) ? gd->prog + span : gd->n;
        gd->reacq = false;
        for (uint32_t j = j0; j < j1; j++) {
            const float dx = gd->tmpl[j][0] - ph[0];
            const float dy = gd->tmpl[j][1] - ph[1];
            const float dd = dx * dx + dy * dy;
            if (dd < best) {
                best = dd;
                bj = j;
            }
        }
        gd->prog = bj;
        gd->corr[0] = gd->tmpl[gd->prog][0] - ph[0];
        gd->corr[1] = gd->tmpl[gd->prog][1] - ph[1];
        gd->dhat[0] = -gd->corr[0];
        gd->dhat[1] = -gd->corr[1];
        const float dist = sqrtf(best);
        gd->conf = (dist < 2.0f * q_lim) ? 1.0f : 0.0f;
        gd->active = true;
    } else {
        gd->reacq = true;
    }
}
