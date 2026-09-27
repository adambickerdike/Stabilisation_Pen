/*
 * mathx.h - small float32 helpers (no double arithmetic anywhere in the
 * control core; checked with -Wdouble-promotion).
 */
#ifndef PEN_MATHX_H
#define PEN_MATHX_H

#include <math.h>
#include <stdbool.h>

#define PEN_PI_F 3.14159265358979323846f
#define PEN_TWO_PI_F 6.28318530717958647692f

static inline float pen_clampf(float x, float lo, float hi)
{
    return (x < lo) ? lo : ((x > hi) ? hi : x);
}

static inline float pen_minf(float a, float b) { return (a < b) ? a : b; }
static inline float pen_maxf(float a, float b) { return (a > b) ? a : b; }
static inline float pen_absf(float a) { return (a < 0.0f) ? -a : a; }

/* Wrap an angle difference into (-pi, pi] exactly as the simulator's
 * while-loops do (at most a few iterations for bounded inputs). */
static inline float pen_wrap_pi(float a)
{
    int guard = 0;
    while (a > PEN_PI_F && guard < 64) {
        a -= PEN_TWO_PI_F;
        guard++;
    }
    while (a < -PEN_PI_F && guard < 128) {
        a += PEN_TWO_PI_F;
        guard++;
    }
    return a;
}

static inline bool pen_isfinitef(float x)
{
    return isfinite(x) != 0;
}

#endif /* PEN_MATHX_H */
