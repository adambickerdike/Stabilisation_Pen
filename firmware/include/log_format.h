/*
 * log_format.h - binary log encoders/decoders, ICD section 4 (format_version 1).
 *
 * All multi-byte fields little-endian, packed explicitly byte by byte (no
 * reliance on struct layout or host endianness).
 *   header (36 B): "PENLOG\0\1" | format_version u16 | device_id u64 |
 *                  session_id u64 | start_unix_ms u64 | header_crc u16
 *                  (CRC-16/CCITT-FALSE over the first 34 bytes)
 *   record: type u8 | length u8 | payload | crc16 (over type..payload)
 * Record payloads:
 *   0x01 research frame, 52 B (ICD s4.2)
 *   0x02 stroke sample,  20 B (ICD s4.3)
 *   0x03 event,          10 B (ICD s4.4)
 *   0x04 calibration snapshot: NOT DEFINED in the ICD. Proposed here:
 *        cal_type u8 | cal_version u16 | record bytes as stored in flash (calib.h)
 *   0x05 annotation: NOT DEFINED in the ICD. Proposed here:
 *        t_us u32 | UTF-8 text (no terminator)
 * Stroke phi: u8 in 2-degree steps, round(phi_deg / 2) mod 180 (0-358 deg);
 * theta u8 in 0.5-degree steps. (ICD s4.3 v1.0 wrote "0.5 deg ... phi/2",
 * which does not fit a u8; ICD v1.2 now specifies the 2-degree coding,
 * README D5, resolved.)
 * Time: research t_us = us since session start (wraps every 71.6 min; event
 * 0x0009 carries the cumulative wrap count); stroke t_ms = ms since session
 * start from a 64-bit time base (wraps only after 49.7 days). penlog_clock_t
 * extends the 32-bit hardware microsecond counter to 64 bits.
 * Positions: stroke x/y and research p_H are relative to the session page
 * origin = deposited-ink position at the first pen-down of the session
 * (research p_H = INT32_MIN before that origin exists).
 */
#ifndef PEN_LOG_FORMAT_H
#define PEN_LOG_FORMAT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PENLOG_MAGIC_LEN 8
#define PENLOG_HEADER_LEN 36
#define PENLOG_FORMAT_VERSION 1u
#define PENLOG_REC_OVERHEAD 4u
#define PENLOG_RESEARCH_LEN 52u
#define PENLOG_STROKE_LEN 20u
#define PENLOG_EVENT_LEN 10u
#define PENLOG_CALSNAP_MIN 3u
#define PENLOG_ANNOT_MIN 4u
#define PENLOG_MAX_PAYLOAD 255u

enum {
    PENLOG_T_RESEARCH = 0x01,
    PENLOG_T_STROKE = 0x02,
    PENLOG_T_EVENT = 0x03,
    PENLOG_T_CALSNAP = 0x04,
    PENLOG_T_ANNOT = 0x05
};

extern const uint8_t PENLOG_MAGIC[PENLOG_MAGIC_LEN];

typedef enum {
    PENLOG_OK = 0,
    PENLOG_E_SHORT = -1,
    PENLOG_E_MAGIC = -2,
    PENLOG_E_VERSION = -3,
    PENLOG_E_CRC = -4,
    PENLOG_E_LENGTH = -5,
    PENLOG_E_TYPE = -6
} penlog_status_t;

typedef struct {
    uint16_t format_version;
    uint64_t device_id;
    uint64_t session_id;
    uint64_t start_unix_ms;
} penlog_header_t;

/* raw (log-unit) research frame, field order of ICD s4.2 */
typedef struct {
    uint32_t t_us;
    int16_t q[2];       /* 0.1 um */
    int16_t qr[2];      /* 0.1 um */
    int16_t i[2];       /* 0.1 mA */
    int16_t iref[2];    /* 0.1 mA */
    int16_t f_ax;       /* mN */
    int32_t p_h[2];     /* 0.1 um */
    uint8_t opt_valid;  /* bit per module */
    int16_t dhat[2];    /* 0.1 um */
    uint8_t g;          /* authority x 255 */
    uint8_t f_est;      /* 0.1 Hz */
    uint8_t mode;
    uint16_t flags;
    uint16_t vbat_mv;
    int16_t t_coil;     /* 0.01 degC */
    int16_t imu_a[2];   /* mg */
    int16_t theta, phi; /* 0.01 deg */
} penlog_research_t;

/* SI view of a research frame (encoder input / decoder output) */
typedef struct {
    uint32_t t_us;
    float q[2], qr[2];          /* m */
    float i[2], iref[2];        /* A */
    float f_ax;                 /* N */
    float p_h[2];               /* m */
    uint8_t opt_valid;
    float dhat[2];              /* m */
    float g;                    /* 0..1 */
    float f_est;                /* Hz */
    uint8_t mode;
    uint16_t flags;
    float vbat;                 /* V */
    float t_coil;               /* degC */
    float imu_a[2];             /* m/s^2 */
    float theta, phi;           /* rad */
} penlog_research_si_t;

typedef struct {
    uint32_t t_ms;
    uint32_t stroke_id;
    int32_t x, y;       /* um, page frame, deposited ink */
    uint16_t force;     /* mN */
    uint8_t theta;      /* 0.5 deg */
    uint8_t phi;        /* 2 deg (see D5) */
} penlog_stroke_t;

typedef struct {
    uint32_t t_us;
    uint16_t code;
    int32_t arg;
} penlog_event_t;

/* ---- session clock ---- */
typedef struct {
    uint64_t t64_us;     /* extended hardware time */
    uint64_t t0_us;      /* session start */
    uint32_t last32;
    uint32_t wraps;      /* wraps of the session-relative 32-bit us time */
    bool init;
} penlog_clock_t;

/* Start a session at the current 32-bit hardware microsecond count. */
void penlog_clock_start(penlog_clock_t *c, uint32_t now32);
/* Advance with the hardware counter (call at least once per 71 min). Returns
 * true when the session-relative 32-bit microsecond time wrapped: log event
 * 0x0009 with arg = c->wraps. */
bool penlog_clock_update(penlog_clock_t *c, uint32_t now32);
uint32_t penlog_clock_us32(const penlog_clock_t *c);   /* research frame / event t_us */
uint32_t penlog_clock_ms32(const penlog_clock_t *c);   /* stroke t_ms */

#define PENLOG_PH_UNDEFINED INT32_MIN   /* research p_H before the page origin exists */

/* ---- header ---- */
void penlog_encode_header(const penlog_header_t *h, uint8_t out[PENLOG_HEADER_LEN]);
penlog_status_t penlog_decode_header(const uint8_t *in, size_t n, penlog_header_t *h);

/* ---- records ---- returns bytes written (0 if cap too small / len > 255) */
size_t penlog_encode_record(uint8_t type, const uint8_t *payload, size_t len, uint8_t *out, size_t cap);
/* Parse one record at in[0..n): checks length and CRC. */
penlog_status_t penlog_parse_record(const uint8_t *in, size_t n, uint8_t *type, const uint8_t **payload,
                                    uint8_t *len, size_t *consumed);

/* ---- payloads ---- */
void penlog_pack_research(const penlog_research_t *r, uint8_t out[PENLOG_RESEARCH_LEN]);
penlog_status_t penlog_unpack_research(const uint8_t *in, size_t len, penlog_research_t *r);
void penlog_pack_stroke(const penlog_stroke_t *s, uint8_t out[PENLOG_STROKE_LEN]);
penlog_status_t penlog_unpack_stroke(const uint8_t *in, size_t len, penlog_stroke_t *s);
void penlog_pack_event(const penlog_event_t *e, uint8_t out[PENLOG_EVENT_LEN]);
penlog_status_t penlog_unpack_event(const uint8_t *in, size_t len, penlog_event_t *e);
/* calibration snapshot / annotation (proposed layouts); return payload length or 0 */
size_t penlog_pack_calsnap(uint8_t cal_type, uint16_t cal_version, const uint8_t *data, size_t n, uint8_t *out, size_t cap);
size_t penlog_pack_annot(uint32_t t_us, const char *text, size_t n, uint8_t *out, size_t cap);

/* ---- unit conversion (saturating, round to nearest) ---- */
/* si->p_h must already be relative to the page origin; pass ph_defined =
 * false before the origin exists (p_H = PENLOG_PH_UNDEFINED). */
void penlog_research_from_si(const penlog_research_si_t *si, penlog_research_t *r);
void penlog_research_ph_undefined(penlog_research_t *r);
void penlog_research_to_si(const penlog_research_t *r, penlog_research_si_t *si);
void penlog_stroke_from_si(uint32_t t_ms, uint32_t stroke_id, float x_m, float y_m, float force_n, float theta_rad,
                           float phi_rad, penlog_stroke_t *s);

/* little-endian helpers (exported for calib.c and tests) */
void le_put_u16(uint8_t *p, uint16_t v);
void le_put_u32(uint8_t *p, uint32_t v);
void le_put_u64(uint8_t *p, uint64_t v);
uint16_t le_get_u16(const uint8_t *p);
uint32_t le_get_u32(const uint8_t *p);
uint64_t le_get_u64(const uint8_t *p);
void le_put_f32(uint8_t *p, float v);
float le_get_f32(const uint8_t *p);

#endif /* PEN_LOG_FORMAT_H */
