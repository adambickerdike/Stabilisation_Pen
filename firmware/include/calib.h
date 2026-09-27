/*
 * calib.h - calibration records (ICD s3) and the per-user tremor-frequency
 * calibration that sets the frequency gate (REQ-CTRL-007, DEC-009).
 *
 * Flash record container (little-endian; docs/icd.md s3 v1.3 adopted it):
 *   off 0  magic u32 = 'P','C','A','L'
 *   off 4  rec_type u8 (CAL_HALL 1, CAL_ACT 2, CAL_ISNS 3, CAL_AXIAL 4, CAL_USER 5)
 *   off 5  cal_version u16
 *   off 7  length u16 (payload bytes)
 *   off 9  payload
 *   end    crc16 CCITT-FALSE over bytes 0 .. 9+length-1
 * CAL_USER payload, cal_version 2 (30 bytes, ICD s3 v1.3):
 *   f0_hz f32 | f_stroke_hz f32 | f_gate_hz f32 | f_gate_width_hz f32 |
 *   g_max f32 | q_lim_m f32 | r_n f32 | mode_perm u8 | flags u8
 *   r_n = K_n / k_ax (0.02-10); gamma(theta) = r_n sin^2 th / (r_n sin^2 th + 1)
 *   is evaluated at every Jacobian update (control.c, jac_gamma()).
 *   cal_version 1 has gamma f32 in place of r_n; it is read with
 *   r_n = gamma / ((1 - gamma) sin^2 theta_nom), theta_nom = 50 deg, and the
 *   result is clamped to the r_n range (a v1 gamma outside 0.0116-0.854
 *   cannot be represented; cal_user_t.from_v1_clamped reports it).
 *   flags: bit0 tremor and writing separable in frequency, bit1 tremor found.
 *   mode_perm: bit0 ASSIST_KF, bit1 ASSIST_ML, bit2 GUIDED, bit3 TRAINING_FADE.
 * Log snapshot (record 0x04, ICD s4.1 v1.3): rec_type u8 | cal_version u16 |
 * the container payload only (cal_user_payload()).
 *
 * Tremor-frequency calibration (proposed procedure, to be validated in the
 * human calibration study): two windows of housing page motion at 250 Hz,
 * (a) HOLD: nib resting on the page, no intended motion -> tremor peak f0;
 * (b) WRITE: standard loops at a comfortable speed -> stroke peak f_stroke.
 * Each window: 1 Hz high-pass, Hann window, Goertzel bank 2.0-14.0 Hz in
 * 0.1 Hz steps on both axes (power summed), parabolic peak interpolation.
 * Gate rule: if f0 - f_stroke >= f_gate_width + CAL_SEP_MARGIN the gate is
 * placed midway, f_gate = (f0 + f_stroke)/2, clamped so that it is fully open
 * at f0 (f_gate <= f0 - w/2); otherwise tremor and handwriting are not
 * separable in frequency (COR-11): ASSIST_KF permission is withdrawn and the
 * tuned default gate is kept.
 */
#ifndef PEN_CALIB_H
#define PEN_CALIB_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define CAL_MAGIC 0x4C414350u  /* "PCAL" little-endian */
#define CAL_HDR_LEN 9u
#define CAL_REC_OVERHEAD 11u

enum { CAL_HALL = 1, CAL_ACT = 2, CAL_ISNS = 3, CAL_AXIAL = 4, CAL_USER = 5 };

#define CAL_USER_VERSION 2u      /* r_n (ICD s3 v1.3) */
#define CAL_USER_VERSION_V1 1u   /* gamma at 50 deg; read-only (converted) */
#define CAL_USER_LEN 30u

typedef enum {
    CAL_OK = 0,
    CAL_E_SHORT = -1,
    CAL_E_MAGIC = -2,
    CAL_E_TYPE = -3,
    CAL_E_VERSION = -4,
    CAL_E_LENGTH = -5,
    CAL_E_CRC = -6,
    CAL_E_RANGE = -7
} cal_status_t;

enum { CAL_FLAG_SEPARABLE = 1u << 0, CAL_FLAG_TREMOR_FOUND = 1u << 1 };

typedef struct {
    float f0_hz;         /* tremor frequency estimate (0 = none detected) */
    float f_stroke_hz;   /* handwriting stroke frequency estimate (0 = none) */
    float f_gate_hz;     /* 0 disables the gate */
    float f_gate_width_hz;
    float g_max;         /* authority cap 0..1 */
    float q_lim_m;       /* <= design soft limit PEN_Q_LIM */
    float r_n;           /* compliance ratio K_n / k_ax, PEN_R_N_MIN..PEN_R_N_MAX */
    uint8_t mode_perm;   /* SM_PERM_* */
    uint8_t flags;       /* CAL_FLAG_* */
    bool from_v1_clamped;  /* decoded from a v1 record whose gamma fell outside the r_n range (not stored) */
} cal_user_t;

void cal_user_default(cal_user_t *u);
cal_status_t cal_user_validate(const cal_user_t *u);
/* Encode a complete flash record (cal_version 2); returns bytes written (0 on error). */
size_t cal_user_encode(const cal_user_t *u, uint8_t *out, size_t cap);
/* Decode + validate (magic, type, version 1 or 2, length, CRC, ranges). */
cal_status_t cal_user_decode(const uint8_t *in, size_t n, cal_user_t *u);
/* The 30-byte cal_version-2 payload (flash record body, log record 0x04); returns CAL_USER_LEN or 0. */
size_t cal_user_payload(const cal_user_t *u, uint8_t out[CAL_USER_LEN]);
/* Parse + validate a payload of the given cal_version (1: gamma converted to r_n, 2: r_n). */
cal_status_t cal_user_from_payload(uint16_t version, const uint8_t *p, uint16_t len, cal_user_t *u);
/* v1 conversion: r_n from gamma at theta (rad); not clamped. */
float cal_rn_from_gamma(float gamma, float theta);
/* Generic container helpers */
size_t cal_record_encode(uint8_t rec_type, uint16_t version, const uint8_t *payload, uint16_t len, uint8_t *out, size_t cap);
cal_status_t cal_record_check(const uint8_t *in, size_t n, uint8_t *rec_type, uint16_t *version,
                              const uint8_t **payload, uint16_t *len);

/* ---- spectral calibration ---- */
#define CAL_F_LO 2.0f
#define CAL_F_STEP 0.1f
#define CAL_NBINS 121            /* 2.0 .. 14.0 Hz */
#define CAL_FS 250.0f            /* input rate (every 8 stage ticks) */
#define CAL_SEP_MARGIN 0.5f      /* Hz, proposed */
#define CAL_F_GATE_MIN 3.0f      /* Hz, proposed */
#define CAL_PEAK_RATIO 10.0f     /* peak / median power to accept a peak (proposed) */

typedef struct {
    float coef[CAL_NBINS];
    float s1[CAL_NBINS][2], s2[CAL_NBINS][2];
    float hp_y[2], hp_x[2];
    bool hp_init;
    uint16_t n, n_target;
    float power[CAL_NBINS];
    bool done;
} cal_spec_t;

void cal_spec_init(cal_spec_t *c, uint16_t n_samples);
/* Push one housing position sample (m). Returns true when the window is complete. */
bool cal_spec_push(cal_spec_t *c, const float p_m[2]);
/* Peak frequency (Hz) in [f_lo, f_hi]; 0 if none passes CAL_PEAK_RATIO. */
float cal_spec_peak(const cal_spec_t *c, float f_lo, float f_hi);

/* Gate rule (see header comment). u must hold defaults/current values. */
void cal_user_apply_frequencies(cal_user_t *u, float f0, float f_stroke);

#endif /* PEN_CALIB_H */
