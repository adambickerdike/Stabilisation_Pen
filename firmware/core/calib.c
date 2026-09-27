/*
 * calib.c - calibration records and tremor-frequency calibration (see header).
 * Status: PROPOSED DESIGN; host unit tests on synthetic signals only. The
 * procedure has not been evaluated with people.
 */
#include "calib.h"

#include <math.h>
#include <string.h>

#include "crc16.h"
#include "log_format.h"
#include "mathx.h"
#include "params_gen.h"
#include "state_machine.h"

/* ------------------------------------------------------------------ container */
size_t cal_record_encode(uint8_t rec_type, uint16_t version, const uint8_t *payload, uint16_t len, uint8_t *out, size_t cap)
{
    const size_t total = (size_t)len + CAL_REC_OVERHEAD;
    if (cap < total) {
        return 0;
    }
    le_put_u32(out, CAL_MAGIC);
    out[4] = rec_type;
    le_put_u16(out + 5, version);
    le_put_u16(out + 7, len);
    if (len > 0u) {
        memcpy(out + CAL_HDR_LEN, payload, len);
    }
    le_put_u16(out + CAL_HDR_LEN + len, crc16_ccitt(out, CAL_HDR_LEN + (size_t)len));
    return total;
}

cal_status_t cal_record_check(const uint8_t *in, size_t n, uint8_t *rec_type, uint16_t *version,
                              const uint8_t **payload, uint16_t *len)
{
    if (n < CAL_REC_OVERHEAD) {
        return CAL_E_SHORT;
    }
    if (le_get_u32(in) != CAL_MAGIC) {
        return CAL_E_MAGIC;
    }
    const uint16_t l = le_get_u16(in + 7);
    if (n < (size_t)l + CAL_REC_OVERHEAD) {
        return CAL_E_LENGTH;
    }
    if (crc16_ccitt(in, CAL_HDR_LEN + (size_t)l) != le_get_u16(in + CAL_HDR_LEN + l)) {
        return CAL_E_CRC;
    }
    *rec_type = in[4];
    *version = le_get_u16(in + 5);
    *payload = in + CAL_HDR_LEN;
    *len = l;
    return CAL_OK;
}

/* ------------------------------------------------------------------ CAL_USER */
void cal_user_default(cal_user_t *u)
{
    memset(u, 0, sizeof(*u));
    u->f_gate_hz = PEN_BAL_F_GATE;
    u->f_gate_width_hz = PEN_F_GATE_WIDTH;
    u->g_max = 1.0f;
    u->q_lim_m = PEN_Q_LIM;
    u->r_n = PEN_R_N_NOM;
    u->mode_perm = (uint8_t)SM_PERM_DEFAULT;
}

static bool in_range(float v, float lo, float hi)
{
    return pen_isfinitef(v) && v >= lo && v <= hi;
}

cal_status_t cal_user_validate(const cal_user_t *u)
{
    if (!in_range(u->f0_hz, 0.0f, 20.0f) || !in_range(u->f_stroke_hz, 0.0f, 20.0f) ||
        !in_range(u->f_gate_hz, 0.0f, 20.0f) || !in_range(u->f_gate_width_hz, 0.1f, 10.0f) ||
        !in_range(u->g_max, 0.0f, 1.0f) || !in_range(u->q_lim_m, 1e-6f, PEN_Q_LIM) ||
        !in_range(u->r_n, PEN_R_N_MIN, PEN_R_N_MAX) || (u->mode_perm & ~0x0Fu) != 0u || (u->flags & ~0x03u) != 0u) {
        return CAL_E_RANGE;
    }
    return CAL_OK;
}

size_t cal_user_payload(const cal_user_t *u, uint8_t out[CAL_USER_LEN])
{
    if (cal_user_validate(u) != CAL_OK) {
        return 0;
    }
    le_put_f32(out + 0, u->f0_hz);
    le_put_f32(out + 4, u->f_stroke_hz);
    le_put_f32(out + 8, u->f_gate_hz);
    le_put_f32(out + 12, u->f_gate_width_hz);
    le_put_f32(out + 16, u->g_max);
    le_put_f32(out + 20, u->q_lim_m);
    le_put_f32(out + 24, u->r_n);
    out[28] = u->mode_perm;
    out[29] = u->flags;
    return CAL_USER_LEN;
}

size_t cal_user_encode(const cal_user_t *u, uint8_t *out, size_t cap)
{
    uint8_t p[CAL_USER_LEN];
    if (cal_user_payload(u, p) == 0u) {
        return 0;
    }
    return cal_record_encode(CAL_USER, CAL_USER_VERSION, p, CAL_USER_LEN, out, cap);
}

float cal_rn_from_gamma(float gamma, float theta)
{
    const float s = sinf(theta);
    return gamma / ((1.0f - gamma) * s * s);
}

cal_status_t cal_user_from_payload(uint16_t version, const uint8_t *p, uint16_t len, cal_user_t *u)
{
    if (version != CAL_USER_VERSION && version != CAL_USER_VERSION_V1) {
        return CAL_E_VERSION;
    }
    if (len != CAL_USER_LEN) {
        return CAL_E_LENGTH;
    }
    cal_user_t v;
    memset(&v, 0, sizeof(v));
    v.f0_hz = le_get_f32(p + 0);
    v.f_stroke_hz = le_get_f32(p + 4);
    v.f_gate_hz = le_get_f32(p + 8);
    v.f_gate_width_hz = le_get_f32(p + 12);
    v.g_max = le_get_f32(p + 16);
    v.q_lim_m = le_get_f32(p + 20);
    v.mode_perm = p[28];
    v.flags = p[29];
    const float f24 = le_get_f32(p + 24);
    if (version == CAL_USER_VERSION_V1) {
        /* ICD s3 v1.3: r_n derived from the v1 gamma at the nominal 50 deg tilt */
        if (!in_range(f24, 0.0f, 1.0f)) {
            return CAL_E_RANGE;
        }
        if (f24 >= 1.0f) {
            v.r_n = PEN_R_N_MAX;   /* gamma = 1 (rigid page) has no finite r_n */
            v.from_v1_clamped = true;
        } else {
            const float r = cal_rn_from_gamma(f24, PEN_THETA_NOM);
            v.r_n = pen_clampf(r, PEN_R_N_MIN, PEN_R_N_MAX);
            v.from_v1_clamped = (r < PEN_R_N_MIN) || (r > PEN_R_N_MAX);
        }
    } else {
        v.r_n = f24;
    }
    if (cal_user_validate(&v) != CAL_OK) {
        return CAL_E_RANGE;
    }
    *u = v;
    return CAL_OK;
}

cal_status_t cal_user_decode(const uint8_t *in, size_t n, cal_user_t *u)
{
    uint8_t type;
    uint16_t ver, len;
    const uint8_t *p;
    const cal_status_t st = cal_record_check(in, n, &type, &ver, &p, &len);
    if (st != CAL_OK) {
        return st;
    }
    if (type != CAL_USER) {
        return CAL_E_TYPE;
    }
    return cal_user_from_payload(ver, p, len, u);
}

/* ------------------------------------------------------------------ spectrum */
void cal_spec_init(cal_spec_t *c, uint16_t n_samples)
{
    memset(c, 0, sizeof(*c));
    c->n_target = n_samples;
    for (int k = 0; k < CAL_NBINS; k++) {
        const float f = CAL_F_LO + CAL_F_STEP * (float)k;
        c->coef[k] = 2.0f * cosf(PEN_TWO_PI_F * f / CAL_FS);
    }
}

bool cal_spec_push(cal_spec_t *c, const float p_m[2])
{
    if (c->done) {
        return true;
    }
    /* first-order high-pass at 1 Hz on um (drift of intended motion) */
    const float a = 1.0f / (1.0f + PEN_TWO_PI_F * 1.0f / CAL_FS);
    float xw[2];
    const float N1 = (float)(c->n_target - 1u);
    const float w = 0.5f - 0.5f * cosf(PEN_TWO_PI_F * (float)c->n / N1);
    for (int ax = 0; ax < 2; ax++) {
        const float x = p_m[ax] * 1e6f;
        if (!c->hp_init) {
            c->hp_x[ax] = x;
            c->hp_y[ax] = 0.0f;
        }
        c->hp_y[ax] = a * (c->hp_y[ax] + x - c->hp_x[ax]);
        c->hp_x[ax] = x;
        xw[ax] = w * c->hp_y[ax];
    }
    c->hp_init = true;
    for (int k = 0; k < CAL_NBINS; k++) {
        for (int ax = 0; ax < 2; ax++) {
            const float s = xw[ax] + c->coef[k] * c->s1[k][ax] - c->s2[k][ax];
            c->s2[k][ax] = c->s1[k][ax];
            c->s1[k][ax] = s;
        }
    }
    c->n++;
    if (c->n >= c->n_target) {
        for (int k = 0; k < CAL_NBINS; k++) {
            float pw = 0.0f;
            for (int ax = 0; ax < 2; ax++) {
                const float s1 = c->s1[k][ax], s2 = c->s2[k][ax];
                pw += s1 * s1 + s2 * s2 - c->coef[k] * s1 * s2;
            }
            c->power[k] = pw;
        }
        c->done = true;
    }
    return c->done;
}

float cal_spec_peak(const cal_spec_t *c, float f_lo, float f_hi)
{
    if (!c->done) {
        return 0.0f;
    }
    int k0 = (int)ceilf((f_lo - CAL_F_LO) / CAL_F_STEP - 1e-3f);
    int k1 = (int)floorf((f_hi - CAL_F_LO) / CAL_F_STEP + 1e-3f);
    if (k0 < 0) {
        k0 = 0;
    }
    if (k1 > CAL_NBINS - 1) {
        k1 = CAL_NBINS - 1;
    }
    if (k1 < k0) {
        return 0.0f;
    }
    int kb = k0;
    for (int k = k0; k <= k1; k++) {
        if (c->power[k] > c->power[kb]) {
            kb = k;
        }
    }
    /* median of the full bank as the noise floor (insertion sort on a copy) */
    float tmp[CAL_NBINS];
    memcpy(tmp, c->power, sizeof(tmp));
    for (int i = 1; i < CAL_NBINS; i++) {
        const float v = tmp[i];
        int j = i - 1;
        while (j >= 0 && tmp[j] > v) {
            tmp[j + 1] = tmp[j];
            j--;
        }
        tmp[j + 1] = v;
    }
    const float med = tmp[CAL_NBINS / 2];
    if (!(c->power[kb] > CAL_PEAK_RATIO * med)) {
        return 0.0f;
    }
    float delta = 0.0f;
    if (kb > 0 && kb < CAL_NBINS - 1) {
        /* parabola on log power */
        const float la = logf(pen_maxf(c->power[kb - 1], 1e-30f));
        const float lb = logf(pen_maxf(c->power[kb], 1e-30f));
        const float lc = logf(pen_maxf(c->power[kb + 1], 1e-30f));
        const float den = la - 2.0f * lb + lc;
        if (den < 0.0f) {
            delta = pen_clampf(0.5f * (la - lc) / den, -0.5f, 0.5f);
        }
    }
    return CAL_F_LO + CAL_F_STEP * ((float)kb + delta);
}

void cal_user_apply_frequencies(cal_user_t *u, float f0, float f_stroke)
{
    u->f0_hz = f0;
    u->f_stroke_hz = f_stroke;
    u->flags = 0;
    if (f0 > 0.0f) {
        u->flags = (uint8_t)(u->flags | CAL_FLAG_TREMOR_FOUND);
    }
    const float w = u->f_gate_width_hz;
    if (!(f0 > 0.0f && f_stroke > 0.0f)) {
        return;   /* a window without a clear peak: keep the tuned defaults */
    }
    if ((f0 - f_stroke) >= w + CAL_SEP_MARGIN) {
        float fg = 0.5f * (f0 + f_stroke);
        fg = pen_minf(fg, f0 - 0.5f * w);
        fg = pen_maxf(fg, CAL_F_GATE_MIN);
        u->f_gate_hz = fg;
        u->flags = (uint8_t)(u->flags | CAL_FLAG_SEPARABLE);
        u->mode_perm = (uint8_t)(u->mode_perm | SM_PERM_KF);
    } else {
        /* tremor inside the handwriting band: cannot cancel without distorting intent */
        u->mode_perm = (uint8_t)(u->mode_perm & (uint8_t)~SM_PERM_KF);
    }
}
