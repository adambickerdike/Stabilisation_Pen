/*
 * log_format.c - ICD section 4 binary formats (see header).
 * Status: PROPOSED DESIGN; host round-trip and CRC known-answer tests, and a
 * golden file cross-checked with an independent Python decoder
 * (tools/pen_log.py).
 */
#include "log_format.h"

#include <math.h>
#include <string.h>

#include "crc16.h"
#include "mathx.h"

const uint8_t PENLOG_MAGIC[PENLOG_MAGIC_LEN] = {'P', 'E', 'N', 'L', 'O', 'G', 0x00u, 0x01u};

/* ------------------------------------------------------------------ LE helpers */
void le_put_u16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)(v & 0xFFu);
    p[1] = (uint8_t)(v >> 8);
}

void le_put_u32(uint8_t *p, uint32_t v)
{
    for (int k = 0; k < 4; k++) {
        p[k] = (uint8_t)((v >> (8 * k)) & 0xFFu);
    }
}

void le_put_u64(uint8_t *p, uint64_t v)
{
    for (int k = 0; k < 8; k++) {
        p[k] = (uint8_t)((v >> (8 * k)) & 0xFFu);
    }
}

uint16_t le_get_u16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
}

uint32_t le_get_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

uint64_t le_get_u64(const uint8_t *p)
{
    uint64_t v = 0;
    for (int k = 7; k >= 0; k--) {
        v = (v << 8) | (uint64_t)p[k];
    }
    return v;
}

void le_put_f32(uint8_t *p, float v)
{
    uint32_t u;
    memcpy(&u, &v, sizeof(u));
    le_put_u32(p, u);
}

float le_get_f32(const uint8_t *p)
{
    const uint32_t u = le_get_u32(p);
    float v;
    memcpy(&v, &u, sizeof(v));
    return v;
}

static void put_i16(uint8_t *p, int16_t v) { le_put_u16(p, (uint16_t)v); }
static void put_i32(uint8_t *p, int32_t v) { le_put_u32(p, (uint32_t)v); }
static int16_t get_i16(const uint8_t *p) { return (int16_t)le_get_u16(p); }
static int32_t get_i32(const uint8_t *p) { return (int32_t)le_get_u32(p); }

/* ------------------------------------------------------------------ session clock */
void penlog_clock_start(penlog_clock_t *c, uint32_t now32)
{
    const uint64_t t = c->init ? c->t64_us + (uint64_t)(uint32_t)(now32 - c->last32) : (uint64_t)now32;
    c->t64_us = t;
    c->t0_us = t;
    c->last32 = now32;
    c->wraps = 0;
    c->init = true;
}

bool penlog_clock_update(penlog_clock_t *c, uint32_t now32)
{
    if (!c->init) {
        penlog_clock_start(c, now32);
        return false;
    }
    c->t64_us += (uint64_t)(uint32_t)(now32 - c->last32);   /* modular difference: hardware wrap safe */
    c->last32 = now32;
    const uint32_t w = (uint32_t)((c->t64_us - c->t0_us) >> 32);
    if (w != c->wraps) {
        c->wraps = w;
        return true;
    }
    return false;
}

uint32_t penlog_clock_us32(const penlog_clock_t *c)
{
    return (uint32_t)((c->t64_us - c->t0_us) & 0xFFFFFFFFull);
}

uint32_t penlog_clock_ms32(const penlog_clock_t *c)
{
    return (uint32_t)(((c->t64_us - c->t0_us) / 1000u) & 0xFFFFFFFFull);
}

/* ------------------------------------------------------------------ header */
void penlog_encode_header(const penlog_header_t *h, uint8_t out[PENLOG_HEADER_LEN])
{
    memcpy(out, PENLOG_MAGIC, PENLOG_MAGIC_LEN);
    le_put_u16(out + 8, h->format_version);
    le_put_u64(out + 10, h->device_id);
    le_put_u64(out + 18, h->session_id);
    le_put_u64(out + 26, h->start_unix_ms);
    le_put_u16(out + 34, crc16_ccitt(out, 34));
}

penlog_status_t penlog_decode_header(const uint8_t *in, size_t n, penlog_header_t *h)
{
    if (n < PENLOG_HEADER_LEN) {
        return PENLOG_E_SHORT;
    }
    if (memcmp(in, PENLOG_MAGIC, PENLOG_MAGIC_LEN) != 0) {
        return PENLOG_E_MAGIC;
    }
    if (crc16_ccitt(in, 34) != le_get_u16(in + 34)) {
        return PENLOG_E_CRC;
    }
    h->format_version = le_get_u16(in + 8);
    h->device_id = le_get_u64(in + 10);
    h->session_id = le_get_u64(in + 18);
    h->start_unix_ms = le_get_u64(in + 26);
    if (h->format_version != PENLOG_FORMAT_VERSION) {
        return PENLOG_E_VERSION;
    }
    return PENLOG_OK;
}

/* ------------------------------------------------------------------ records */
size_t penlog_encode_record(uint8_t type, const uint8_t *payload, size_t len, uint8_t *out, size_t cap)
{
    if (len > PENLOG_MAX_PAYLOAD || cap < len + PENLOG_REC_OVERHEAD) {
        return 0;
    }
    out[0] = type;
    out[1] = (uint8_t)len;
    if (len > 0u) {
        memcpy(out + 2, payload, len);
    }
    le_put_u16(out + 2 + len, crc16_ccitt(out, 2u + len));
    return len + PENLOG_REC_OVERHEAD;
}

static bool length_ok(uint8_t type, uint8_t len)
{
    switch (type) {
    case PENLOG_T_RESEARCH: return len == PENLOG_RESEARCH_LEN;
    case PENLOG_T_STROKE: return len == PENLOG_STROKE_LEN;
    case PENLOG_T_EVENT: return len == PENLOG_EVENT_LEN;
    case PENLOG_T_CALSNAP: return len >= PENLOG_CALSNAP_MIN;
    case PENLOG_T_ANNOT: return len >= PENLOG_ANNOT_MIN;
    default: return true;   /* unknown types are skippable (forward compatibility) */
    }
}

penlog_status_t penlog_parse_record(const uint8_t *in, size_t n, uint8_t *type, const uint8_t **payload,
                                    uint8_t *len, size_t *consumed)
{
    if (n < PENLOG_REC_OVERHEAD) {
        return PENLOG_E_SHORT;
    }
    const uint8_t l = in[1];
    if (n < (size_t)l + PENLOG_REC_OVERHEAD) {
        return PENLOG_E_SHORT;
    }
    if (crc16_ccitt(in, 2u + l) != le_get_u16(in + 2 + l)) {
        return PENLOG_E_CRC;
    }
    *type = in[0];
    *payload = in + 2;
    *len = l;
    *consumed = (size_t)l + PENLOG_REC_OVERHEAD;
    if (!length_ok(in[0], l)) {
        return PENLOG_E_LENGTH;
    }
    return PENLOG_OK;
}

/* ------------------------------------------------------------------ payloads */
void penlog_pack_research(const penlog_research_t *r, uint8_t out[PENLOG_RESEARCH_LEN])
{
    uint8_t *p = out;
    le_put_u32(p, r->t_us); p += 4;
    put_i16(p, r->q[0]); p += 2;
    put_i16(p, r->q[1]); p += 2;
    put_i16(p, r->qr[0]); p += 2;
    put_i16(p, r->qr[1]); p += 2;
    put_i16(p, r->i[0]); p += 2;
    put_i16(p, r->i[1]); p += 2;
    put_i16(p, r->iref[0]); p += 2;
    put_i16(p, r->iref[1]); p += 2;
    put_i16(p, r->f_ax); p += 2;
    put_i32(p, r->p_h[0]); p += 4;
    put_i32(p, r->p_h[1]); p += 4;
    *p++ = r->opt_valid;
    put_i16(p, r->dhat[0]); p += 2;
    put_i16(p, r->dhat[1]); p += 2;
    *p++ = r->g;
    *p++ = r->f_est;
    *p++ = r->mode;
    le_put_u16(p, r->flags); p += 2;
    le_put_u16(p, r->vbat_mv); p += 2;
    put_i16(p, r->t_coil); p += 2;
    put_i16(p, r->imu_a[0]); p += 2;
    put_i16(p, r->imu_a[1]); p += 2;
    put_i16(p, r->theta); p += 2;
    put_i16(p, r->phi);
}

penlog_status_t penlog_unpack_research(const uint8_t *in, size_t len, penlog_research_t *r)
{
    if (len != PENLOG_RESEARCH_LEN) {
        return PENLOG_E_LENGTH;
    }
    const uint8_t *p = in;
    r->t_us = le_get_u32(p); p += 4;
    r->q[0] = get_i16(p); p += 2;
    r->q[1] = get_i16(p); p += 2;
    r->qr[0] = get_i16(p); p += 2;
    r->qr[1] = get_i16(p); p += 2;
    r->i[0] = get_i16(p); p += 2;
    r->i[1] = get_i16(p); p += 2;
    r->iref[0] = get_i16(p); p += 2;
    r->iref[1] = get_i16(p); p += 2;
    r->f_ax = get_i16(p); p += 2;
    r->p_h[0] = get_i32(p); p += 4;
    r->p_h[1] = get_i32(p); p += 4;
    r->opt_valid = *p++;
    r->dhat[0] = get_i16(p); p += 2;
    r->dhat[1] = get_i16(p); p += 2;
    r->g = *p++;
    r->f_est = *p++;
    r->mode = *p++;
    r->flags = le_get_u16(p); p += 2;
    r->vbat_mv = le_get_u16(p); p += 2;
    r->t_coil = get_i16(p); p += 2;
    r->imu_a[0] = get_i16(p); p += 2;
    r->imu_a[1] = get_i16(p); p += 2;
    r->theta = get_i16(p); p += 2;
    r->phi = get_i16(p);
    return PENLOG_OK;
}

void penlog_pack_stroke(const penlog_stroke_t *s, uint8_t out[PENLOG_STROKE_LEN])
{
    le_put_u32(out + 0, s->t_ms);
    le_put_u32(out + 4, s->stroke_id);
    put_i32(out + 8, s->x);
    put_i32(out + 12, s->y);
    le_put_u16(out + 16, s->force);
    out[18] = s->theta;
    out[19] = s->phi;
}

penlog_status_t penlog_unpack_stroke(const uint8_t *in, size_t len, penlog_stroke_t *s)
{
    if (len != PENLOG_STROKE_LEN) {
        return PENLOG_E_LENGTH;
    }
    s->t_ms = le_get_u32(in + 0);
    s->stroke_id = le_get_u32(in + 4);
    s->x = get_i32(in + 8);
    s->y = get_i32(in + 12);
    s->force = le_get_u16(in + 16);
    s->theta = in[18];
    s->phi = in[19];
    return PENLOG_OK;
}

void penlog_pack_event(const penlog_event_t *e, uint8_t out[PENLOG_EVENT_LEN])
{
    le_put_u32(out + 0, e->t_us);
    le_put_u16(out + 4, e->code);
    put_i32(out + 6, e->arg);
}

penlog_status_t penlog_unpack_event(const uint8_t *in, size_t len, penlog_event_t *e)
{
    if (len != PENLOG_EVENT_LEN) {
        return PENLOG_E_LENGTH;
    }
    e->t_us = le_get_u32(in + 0);
    e->code = le_get_u16(in + 4);
    e->arg = get_i32(in + 6);
    return PENLOG_OK;
}

size_t penlog_pack_calsnap(uint8_t cal_type, uint16_t cal_version, const uint8_t *data, size_t n, uint8_t *out, size_t cap)
{
    const size_t len = n + 3u;
    if (len > PENLOG_MAX_PAYLOAD || cap < len) {
        return 0;
    }
    out[0] = cal_type;
    le_put_u16(out + 1, cal_version);
    if (n > 0u) {
        memcpy(out + 3, data, n);
    }
    return len;
}

size_t penlog_pack_annot(uint32_t t_us, const char *text, size_t n, uint8_t *out, size_t cap)
{
    const size_t len = n + 4u;
    if (len > PENLOG_MAX_PAYLOAD || cap < len) {
        return 0;
    }
    le_put_u32(out, t_us);
    if (n > 0u) {
        memcpy(out + 4, text, n);
    }
    return len;
}

/* ------------------------------------------------------------------ units */
static int16_t sat_i16(float v)
{
    if (!pen_isfinitef(v)) {
        return 0;
    }
    const float r = rintf(v);
    if (r >= 32767.0f) {
        return INT16_MAX;
    }
    if (r <= -32768.0f) {
        return INT16_MIN;
    }
    return (int16_t)r;
}

static int32_t sat_i32(float v)
{
    if (!pen_isfinitef(v)) {
        return 0;
    }
    const float r = rintf(v);
    if (r >= 2147483520.0f) {   /* largest float below 2^31 */
        return INT32_MAX;
    }
    if (r <= -2147483648.0f) {
        return INT32_MIN + 1;   /* INT32_MIN is reserved: PENLOG_PH_UNDEFINED */
    }
    return (int32_t)r;
}

static uint8_t sat_u8(float v)
{
    if (!pen_isfinitef(v)) {
        return 0;
    }
    const float r = rintf(v);
    if (r >= 255.0f) {
        return 255u;
    }
    if (r <= 0.0f) {
        return 0u;
    }
    return (uint8_t)r;
}

static uint16_t sat_u16(float v)
{
    if (!pen_isfinitef(v)) {
        return 0;
    }
    const float r = rintf(v);
    if (r >= 65535.0f) {
        return 65535u;
    }
    if (r <= 0.0f) {
        return 0u;
    }
    return (uint16_t)r;
}

#define RAD2CDEG 5729.57795130823208768f   /* 0.01 deg per rad */
#define G0 9.80665f

void penlog_research_from_si(const penlog_research_si_t *si, penlog_research_t *r)
{
    r->t_us = si->t_us;
    for (int k = 0; k < 2; k++) {
        r->q[k] = sat_i16(si->q[k] * 1e7f);
        r->qr[k] = sat_i16(si->qr[k] * 1e7f);
        r->i[k] = sat_i16(si->i[k] * 1e4f);
        r->iref[k] = sat_i16(si->iref[k] * 1e4f);
        r->p_h[k] = sat_i32(si->p_h[k] * 1e7f);
        r->dhat[k] = sat_i16(si->dhat[k] * 1e7f);
        r->imu_a[k] = sat_i16(si->imu_a[k] / G0 * 1e3f);
    }
    r->f_ax = sat_i16(si->f_ax * 1e3f);
    r->opt_valid = si->opt_valid;
    r->g = sat_u8(pen_clampf(si->g, 0.0f, 1.0f) * 255.0f);
    r->f_est = sat_u8(si->f_est * 10.0f);
    r->mode = si->mode;
    r->flags = si->flags;
    r->vbat_mv = sat_u16(si->vbat * 1e3f);
    r->t_coil = sat_i16(si->t_coil * 100.0f);
    r->theta = sat_i16(si->theta * RAD2CDEG);
    r->phi = sat_i16(si->phi * RAD2CDEG);
}

void penlog_research_ph_undefined(penlog_research_t *r)
{
    r->p_h[0] = PENLOG_PH_UNDEFINED;
    r->p_h[1] = PENLOG_PH_UNDEFINED;
}

void penlog_research_to_si(const penlog_research_t *r, penlog_research_si_t *si)
{
    si->t_us = r->t_us;
    for (int k = 0; k < 2; k++) {
        si->q[k] = (float)r->q[k] * 1e-7f;
        si->qr[k] = (float)r->qr[k] * 1e-7f;
        si->i[k] = (float)r->i[k] * 1e-4f;
        si->iref[k] = (float)r->iref[k] * 1e-4f;
        si->p_h[k] = (float)r->p_h[k] * 1e-7f;
        si->dhat[k] = (float)r->dhat[k] * 1e-7f;
        si->imu_a[k] = (float)r->imu_a[k] * 1e-3f * G0;
    }
    si->f_ax = (float)r->f_ax * 1e-3f;
    si->opt_valid = r->opt_valid;
    si->g = (float)r->g / 255.0f;
    si->f_est = (float)r->f_est * 0.1f;
    si->mode = r->mode;
    si->flags = r->flags;
    si->vbat = (float)r->vbat_mv * 1e-3f;
    si->t_coil = (float)r->t_coil * 0.01f;
    si->theta = (float)r->theta / RAD2CDEG;
    si->phi = (float)r->phi / RAD2CDEG;
}

void penlog_stroke_from_si(uint32_t t_ms, uint32_t stroke_id, float x_m, float y_m, float force_n, float theta_rad,
                           float phi_rad, penlog_stroke_t *s)
{
    s->t_ms = t_ms;
    s->stroke_id = stroke_id;
    s->x = sat_i32(x_m * 1e6f);
    s->y = sat_i32(y_m * 1e6f);
    s->force = sat_u16(force_n * 1e3f);
    s->theta = sat_u8(theta_rad * (RAD2CDEG / 50.0f));            /* 0.5 deg units */
    float phi_deg = phi_rad * (RAD2CDEG / 100.0f);
    phi_deg = fmodf(phi_deg, 360.0f);
    if (phi_deg < 0.0f) {
        phi_deg += 360.0f;
    }
    uint32_t pk = (uint32_t)lrintf(phi_deg * 0.5f);
    s->phi = (uint8_t)(pk % 180u);
}
