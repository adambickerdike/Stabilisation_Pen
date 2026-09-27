/*
 * guided.h - guided (known-path) mode: user-paced progress along a
 * registered template. Port of sim/pensim/core.py simulate() `mode == 6`.
 * The template is a caller-owned array of page positions (m) at the stage
 * rate (no allocation here).
 */
#ifndef PEN_GUIDED_H
#define PEN_GUIDED_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    const float (*tmpl)[2];  /* template points, page frame, m */
    uint32_t n;              /* number of points */
    uint32_t prog;           /* current progress index */
    bool reacq;              /* wide forward search after a lift */
    float corr[2];           /* page correction toward the template */
    float dhat[2];
    float conf;
    bool active;
} guided_t;

void guided_init(guided_t *gd, const float (*tmpl)[2], uint32_t n);
/* in_contact and valid as in the simulator; q_lim sets the capture radius (2 q_lim). */
void guided_tick(guided_t *gd, const float ph[2], bool valid, bool in_contact, float q_lim);

#endif /* PEN_GUIDED_H */
