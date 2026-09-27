/*
 * test_log.c - CRC-16/CCITT-FALSE and ICD s4 log format tests; golden log
 * generator (pen_tests --golden-log <file>).
 */
#include <stdio.h>
#include <string.h>

#include "calib.h"
#include "crc16.h"
#include "log_format.h"
#include "pen_types.h"
#include "tr.h"
#include "vec.h"

void test_crc_known_answer(void)
{
    const uint8_t s[] = "123456789";
    CHECK(crc16_ccitt(s, 9) == 0x29B1u);            /* ICD s4.1 check value */
    CHECK(crc16_ccitt(s, 0) == 0xFFFFu);            /* init, empty input */
    /* incremental update equals one-shot */
    CHECK(crc16_ccitt_update(crc16_ccitt(s, 4), s + 4, 5) == 0x29B1u);
    /* independent reference: binascii.crc_hqx(data, 0xFFFF) */
    vec_t v;
    CHECK(vec_load("crc16.vec", &v));
    if (v.rows == 0u) {
        return;
    }
    const int cl = vec_col(&v, "len"), cc = vec_col(&v, "crc"), cb = vec_col(&v, "b0");
    uint32_t bad = 0;
    for (uint32_t r = 0; r < v.rows; r++) {
        uint8_t buf[64];
        const uint32_t n = (uint32_t)vec_at(&v, r, cl);
        for (uint32_t i = 0; i < n; i++) {
            buf[i] = (uint8_t)vec_at(&v, r, cb + (int)i);
        }
        if (crc16_ccitt(buf, n) != (uint16_t)vec_at(&v, r, cc)) {
            bad++;
        }
    }
    CHECK(bad == 0u);
    tr_log("CRC-16/CCITT-FALSE(\"123456789\") = 0x%04X; %u random vectors vs binascii.crc_hqx: %u mismatches",
           (unsigned)crc16_ccitt(s, 9), (unsigned)v.rows, (unsigned)bad);
}

void test_log_header_roundtrip(void)
{
    penlog_header_t h = {PENLOG_FORMAT_VERSION, 0x0123456789ABCDEFull, 42u, 1790000000123ull};
    uint8_t b[PENLOG_HEADER_LEN];
    penlog_encode_header(&h, b);
    CHECK(memcmp(b, "PENLOG\0\1", 8) == 0);
    CHECK(b[8] == 1u && b[9] == 0u);                 /* format_version little-endian */
    CHECK(b[10] == 0xEFu && b[17] == 0x01u);         /* device_id little-endian */
    penlog_header_t d;
    CHECK(penlog_decode_header(b, sizeof(b), &d) == PENLOG_OK);
    CHECK(d.device_id == h.device_id && d.session_id == h.session_id && d.start_unix_ms == h.start_unix_ms);
    b[20] ^= 0x01u;
    CHECK(penlog_decode_header(b, sizeof(b), &d) == PENLOG_E_CRC);
    b[20] ^= 0x01u;
    b[0] = 'X';
    CHECK(penlog_decode_header(b, sizeof(b), &d) == PENLOG_E_MAGIC);
    CHECK(penlog_decode_header(b, 20, &d) == PENLOG_E_SHORT);
    /* version 2 with a valid CRC is refused */
    penlog_header_t h2 = h;
    h2.format_version = 2;
    penlog_encode_header(&h2, b);
    CHECK(penlog_decode_header(b, sizeof(b), &d) == PENLOG_E_VERSION);
}

static penlog_research_t sample_research(uint32_t k)
{
    penlog_research_t r;
    memset(&r, 0, sizeof(r));
    r.t_us = 1000000u + 500u * k;
    r.q[0] = (int16_t)(1234 - (int)k * 7);
    r.q[1] = (int16_t)(-2345 + (int)k);
    r.qr[0] = (int16_t)(-32768 + (int)k);
    r.qr[1] = 32767;
    r.i[0] = 3250;
    r.i[1] = -120;
    r.iref[0] = 3300;
    r.iref[1] = -100;
    r.f_ax = 1000;
    r.p_h[0] = 123456789;
    r.p_h[1] = -98765432;
    r.opt_valid = 0x05u;
    r.dhat[0] = -3000;
    r.dhat[1] = 1500;
    r.g = 200;
    r.f_est = 81;
    r.mode = PEN_MODE_ASSIST_KF;
    r.flags = PEN_FLAG_CONTACT | PEN_FLAG_THERMAL_DERATE;
    r.vbat_mv = 3712;
    r.t_coil = 4525;
    r.imu_a[0] = -250;
    r.imu_a[1] = 1000;
    r.theta = 5000;
    r.phi = -17999;
    return r;
}

void test_log_records_roundtrip(void)
{
    uint8_t p[PENLOG_RESEARCH_LEN], rec[PENLOG_MAX_PAYLOAD + 4];
    const penlog_research_t r = sample_research(3);
    penlog_pack_research(&r, p);
    size_t n = penlog_encode_record(PENLOG_T_RESEARCH, p, sizeof(p), rec, sizeof(rec));
    CHECK(n == 56u);                                  /* 112 kB/s at 2 kHz (ICD s4.2) */
    uint8_t type, len;
    const uint8_t *pl;
    size_t used;
    CHECK(penlog_parse_record(rec, n, &type, &pl, &len, &used) == PENLOG_OK);
    CHECK(type == PENLOG_T_RESEARCH && len == 52u && used == 56u);
    penlog_research_t d;
    CHECK(penlog_unpack_research(pl, len, &d) == PENLOG_OK);
    CHECK(d.t_us == r.t_us && d.p_h[1] == r.p_h[1] && d.phi == r.phi && d.flags == r.flags && d.qr[0] == r.qr[0] &&
          d.qr[1] == r.qr[1] && d.vbat_mv == r.vbat_mv && d.i[1] == r.i[1] && d.iref[0] == r.iref[0] &&
          d.dhat[1] == r.dhat[1] && d.imu_a[0] == r.imu_a[0]);
    CHECK(d.q[0] == r.q[0] && d.q[1] == r.q[1] && d.i[0] == r.i[0] && d.iref[1] == r.iref[1] && d.f_ax == r.f_ax &&
          d.p_h[0] == r.p_h[0] && d.opt_valid == r.opt_valid && d.dhat[0] == r.dhat[0] && d.g == r.g &&
          d.f_est == r.f_est && d.mode == r.mode && d.t_coil == r.t_coil && d.imu_a[1] == r.imu_a[1] &&
          d.theta == r.theta);
    /* field offsets of ICD s4.2: t_us 0, q 4, qr 8, i 12, iref 16, f_ax 20, p_H 22, opt_valid 30,
     * dhat 31, g 35, f_est 36, mode 37, flags 38, vbat 40, t_coil 42, imu 44, theta 48, phi 50 */
    CHECK(p[30] == 0x05u && p[35] == 200u && p[36] == 81u && p[37] == (uint8_t)PEN_MODE_ASSIST_KF);
    CHECK(le_get_u16(p + 40) == 3712u && (int16_t)le_get_u16(p + 50) == -17999);

    penlog_stroke_t s = {123456u, 7u, -1500, 250000, 1234u, 100u, 45u}, s2;
    uint8_t ps[PENLOG_STROKE_LEN];
    penlog_pack_stroke(&s, ps);
    n = penlog_encode_record(PENLOG_T_STROKE, ps, sizeof(ps), rec, sizeof(rec));
    CHECK(n == 24u);
    CHECK(penlog_parse_record(rec, n, &type, &pl, &len, &used) == PENLOG_OK);
    CHECK(penlog_unpack_stroke(pl, len, &s2) == PENLOG_OK);
    CHECK(s2.t_ms == s.t_ms && s2.stroke_id == s.stroke_id && s2.x == s.x && s2.y == s.y && s2.force == s.force &&
          s2.theta == s.theta && s2.phi == s.phi);

    penlog_event_t e = {99u, PEN_EV_FAULT_SET, (int32_t)(PEN_FAULT_HALL | PEN_FAULT_LOWBAT)}, e2;
    uint8_t pe[PENLOG_EVENT_LEN];
    penlog_pack_event(&e, pe);
    n = penlog_encode_record(PENLOG_T_EVENT, pe, sizeof(pe), rec, sizeof(rec));
    CHECK(penlog_parse_record(rec, n, &type, &pl, &len, &used) == PENLOG_OK);
    CHECK(penlog_unpack_event(pl, len, &e2) == PENLOG_OK);
    CHECK(e2.t_us == 99u && e2.code == PEN_EV_FAULT_SET && e2.arg == 0x0A);

    /* wrong payload lengths are rejected */
    CHECK(penlog_unpack_research(pl, 51, &d) == PENLOG_E_LENGTH);
    uint8_t big[300];
    memset(big, 0, sizeof(big));
    CHECK(penlog_encode_record(PENLOG_T_ANNOT, big, 256, rec, sizeof(rec)) == 0u);
}

void test_log_unit_conversion(void)
{
    penlog_research_si_t si, back;
    memset(&si, 0, sizeof(si));
    si.q[0] = 123.45e-6f;       /* -> 1234.5 x 0.1 um -> 1234 or 1235 */
    si.q[1] = -5.0e-3f;         /* beyond +/-3.2 mm: saturates */
    si.i[0] = 0.32496f;         /* -> 3250 x 0.1 mA */
    si.f_ax = 1.0f;
    si.p_h[0] = 0.1234567f;
    si.g = 1.2f;                /* clamped to 255 */
    si.f_est = 8.14f;
    si.vbat = 3.7f;
    si.t_coil = 85.25f;
    si.imu_a[0] = 9.80665f;
    si.theta = 0.8726646f;      /* 50 deg */
    si.phi = -3.14159f;
    penlog_research_t r;
    penlog_research_from_si(&si, &r);
    CHECK(r.q[0] == 1234 || r.q[0] == 1235);
    CHECK(r.q[1] == INT16_MIN);
    CHECK(r.i[0] == 3250);
    CHECK(r.f_ax == 1000);
    CHECK(r.p_h[0] == 1234567);
    CHECK(r.g == 255u);
    CHECK(r.f_est == 81u);
    CHECK(r.vbat_mv == 3700u);
    CHECK(r.t_coil == 8525);
    CHECK(r.imu_a[0] == 1000);
    CHECK(r.theta == 5000);
    CHECK(r.phi == -18000);
    penlog_research_to_si(&r, &back);
    CHECK_CLOSE(back.q[0], si.q[0], 0.051e-6, 0.0);
    CHECK_CLOSE(back.theta, si.theta, 1e-4, 0.0);
    /* stroke: theta 0.5 deg units, phi 2 deg units mod 180 */
    penlog_stroke_t s;
    penlog_stroke_from_si(1u, 2u, 0.0105f, -0.002f, 1.2f, 0.8726646f, -1.5707963f, &s);
    CHECK(s.x == 10500 && s.y == -2000 && s.force == 1200u);
    CHECK(s.theta == 100u);          /* 50 deg / 0.5 */
    CHECK(s.phi == 135u);            /* -90 deg -> 270 deg -> 135 x 2 deg */
    penlog_stroke_from_si(1u, 2u, 0.0f, 0.0f, 0.0f, 0.0f, 6.2831850f, &s);
    CHECK(s.phi == 0u);
}

void test_log_corruption_detected(void)
{
    uint8_t p[PENLOG_RESEARCH_LEN], rec[64];
    const penlog_research_t r = sample_research(1);
    penlog_pack_research(&r, p);
    const size_t n = penlog_encode_record(PENLOG_T_RESEARCH, p, sizeof(p), rec, sizeof(rec));
    uint8_t type, len;
    const uint8_t *pl;
    size_t used;
    uint32_t detected = 0, total = 0;
    for (size_t byte = 0; byte < n; byte++) {
        for (int bit = 0; bit < 8; bit++) {
            rec[byte] ^= (uint8_t)(1u << bit);
            const penlog_status_t st = penlog_parse_record(rec, n, &type, &pl, &len, &used);
            if (st != PENLOG_OK) {
                detected++;
            }
            total++;
            rec[byte] ^= (uint8_t)(1u << bit);
        }
    }
    CHECK(detected == total);       /* every single-bit error is detected */
    CHECK(penlog_parse_record(rec, n - 1u, &type, &pl, &len, &used) == PENLOG_E_SHORT);
    tr_log("single-bit corruptions detected: %u / %u", (unsigned)detected, (unsigned)total);
}

/* ------------------------------------------------------------------ golden log */
static size_t golden_build(uint8_t *buf, size_t cap)
{
    size_t off = 0;
    penlog_header_t h = {PENLOG_FORMAT_VERSION, 0x0123456789ABCDEFull, 0x0000000000000042ull, 1790000000000ull};
    penlog_encode_header(&h, buf);
    off += PENLOG_HEADER_LEN;
    uint8_t p[PENLOG_MAX_PAYLOAD];
    size_t n;
    /* research frames */
    for (uint32_t k = 0; k < 3; k++) {
        const penlog_research_t r = sample_research(k);
        penlog_pack_research(&r, p);
        off += penlog_encode_record(PENLOG_T_RESEARCH, p, PENLOG_RESEARCH_LEN, buf + off, cap - off);
    }
    /* stroke samples */
    const penlog_stroke_t st[3] = {{1000u, 1u, 0, 0, 950u, 100u, 0u},
                                   {1005u, 1u, 152, -37, 1010u, 101u, 179u},
                                   {1010u, 2u, -2147483647, 2147483647, 65535u, 180u, 90u}};
    for (int k = 0; k < 3; k++) {
        penlog_pack_stroke(&st[k], p);
        off += penlog_encode_record(PENLOG_T_STROKE, p, PENLOG_STROKE_LEN, buf + off, cap - off);
    }
    /* events */
    const penlog_event_t ev[5] = {{1000000u, PEN_EV_MODE_CHANGE, (int32_t)(PEN_MODE_ASSIST_KF | (PEN_MODE_NEUTRAL_HOLD << 8))},
                                  {1000500u, PEN_EV_PEN_DOWN, 0},
                                  {1002000u, PEN_EV_FAULT_SET, (int32_t)PEN_FAULT_HALL},
                                  {1500000u, PEN_EV_FAULT_CLEARED, (int32_t)PEN_FAULT_HALL},
                                  {1500500u, PEN_EV_AUTHORITY_CAPPED, -1}};
    for (int k = 0; k < 5; k++) {
        penlog_pack_event(&ev[k], p);
        off += penlog_encode_record(PENLOG_T_EVENT, p, PENLOG_EVENT_LEN, buf + off, cap - off);
    }
    /* calibration snapshot: a CAL_USER flash record */
    cal_user_t u;
    cal_user_default(&u);
    cal_user_apply_frequencies(&u, 8.2f, 4.4f);
    uint8_t calrec[64];
    const size_t nc = cal_user_encode(&u, calrec, sizeof(calrec));
    n = penlog_pack_calsnap(CAL_USER, CAL_USER_VERSION, calrec, nc, p, sizeof(p));
    off += penlog_encode_record(PENLOG_T_CALSNAP, p, n, buf + off, cap - off);
    /* annotations */
    const char *t1 = "bench session 1: 50 deg, 1 N";
    n = penlog_pack_annot(2000000u, t1, strlen(t1), p, sizeof(p));
    off += penlog_encode_record(PENLOG_T_ANNOT, p, n, buf + off, cap - off);
    const char *t2 = "UTF-8 \xc2\xb5m \xc2\xb0";
    n = penlog_pack_annot(2000500u, t2, strlen(t2), p, sizeof(p));
    off += penlog_encode_record(PENLOG_T_ANNOT, p, n, buf + off, cap - off);
    return off;
}

int pen_write_golden_log(const char *path)
{
    static uint8_t buf[2048];
    const size_t n = golden_build(buf, sizeof(buf));
    FILE *f = fopen(path, "wb");
    if (f == NULL) {
        return 2;
    }
    const size_t w = fwrite(buf, 1, n, f);
    fclose(f);
    printf("wrote %s (%u bytes)\n", path, (unsigned)n);
    return w == n ? 0 : 2;
}

void test_log_golden_file(void)
{
    static uint8_t ref[2048], file[2048];
    const size_t n = golden_build(ref, sizeof(ref));
    FILE *f = fopen(tr_vec_path("golden_log_v1.bin"), "rb");
    CHECK(f != NULL);
    if (f == NULL) {
        return;
    }
    const size_t m = fread(file, 1, sizeof(file), f);
    fclose(f);
    CHECK(m == n);
    CHECK(memcmp(ref, file, n) == 0);   /* regression: encoder output unchanged */
    /* decode the file with the C decoder */
    penlog_header_t h;
    CHECK(penlog_decode_header(file, m, &h) == PENLOG_OK);
    size_t off = PENLOG_HEADER_LEN;
    uint32_t counts[6] = {0, 0, 0, 0, 0, 0};
    while (off < m) {
        uint8_t type, len;
        const uint8_t *pl;
        size_t used;
        const penlog_status_t st = penlog_parse_record(file + off, m - off, &type, &pl, &len, &used);
        CHECK(st == PENLOG_OK);
        if (st != PENLOG_OK) {
            break;
        }
        if (type >= 1u && type <= 5u) {
            counts[type]++;
        }
        if (type == PENLOG_T_CALSNAP) {
            cal_user_t u;
            CHECK(pl[0] == CAL_USER && le_get_u16(pl + 1) == CAL_USER_VERSION);
            CHECK(cal_user_decode(pl + 3, (size_t)len - 3u, &u) == CAL_OK);
            CHECK_CLOSE(u.f0_hz, 8.2, 1e-6, 0.0);
        }
        off += used;
    }
    CHECK(counts[1] == 3u && counts[2] == 3u && counts[3] == 5u && counts[4] == 1u && counts[5] == 2u);
    tr_log("golden_log_v1.bin: %u bytes, records research %u stroke %u event %u calsnap %u annot %u", (unsigned)m,
           (unsigned)counts[1], (unsigned)counts[2], (unsigned)counts[3], (unsigned)counts[4], (unsigned)counts[5]);
}
