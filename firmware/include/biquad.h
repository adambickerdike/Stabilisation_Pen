/*
 * biquad.h - second-order section, direct form II transposed, float32.
 * Port of sim/pensim/core.py _biquad():
 *     y  = b0 x + s1
 *     s1 = b1 x - a1 y + s2
 *     s2 = b2 x - a2 y
 */
#ifndef PEN_BIQUAD_H
#define PEN_BIQUAD_H

typedef struct {
    float b0, b1, b2, a1, a2;
} biquad_coef_t;

typedef struct {
    float s1, s2;
} biquad_state_t;

static inline float biquad_step(const biquad_coef_t *c, biquad_state_t *st, float x)
{
    const float y = c->b0 * x + st->s1;
    st->s1 = c->b1 * x - c->a1 * y + st->s2;
    st->s2 = c->b2 * x - c->a2 * y;
    return y;
}

static inline void biquad_reset(biquad_state_t *st)
{
    st->s1 = 0.0f;
    st->s2 = 0.0f;
}

#endif /* PEN_BIQUAD_H */
