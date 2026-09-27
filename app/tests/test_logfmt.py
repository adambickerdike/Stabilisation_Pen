"""ICD v1.0 section 4 binary format: layout, CRC, round trip, resync, time unwrap."""
from __future__ import annotations

import json
import struct

import numpy as np
import pytest

from penapp import logfmt as lf
from penapp import vectors
from penapp.logfmt import (Event, EventCode, Header, RawRecord, ResearchFrame, StrokeSample, encode_log,
                           encode_record, iter_record_spans, read_log, record_type_of)

from conftest import ROOT

H = Header(device_id=0x1122334455667788, session_id=0x0102030405060708, start_unix_ms=1790000000123)


def crc_bitwise(data: bytes, crc: int = 0xFFFF) -> int:
    """Independent bit-by-bit CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection)."""
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def test_crc_catalogue_check_value():
    assert lf.crc16_ccitt_false(b"123456789") == 0x29B1
    assert crc_bitwise(b"123456789") == 0x29B1


def test_crc_matches_independent_implementation():
    rng = np.random.default_rng(1)
    for n in (0, 1, 2, 20, 52, 255, 1000):
        data = rng.integers(0, 256, n, dtype=np.uint8).tobytes()
        assert lf.crc16_ccitt_false(data) == crc_bitwise(data)


def test_header_layout_by_hand():
    b = H.encode()
    assert len(b) == lf.HEADER_SIZE == 36
    assert b[:8] == b"PENLOG\x00\x01"
    assert b[8:10] == b"\x01\x00"                                   # format_version = 1, LE
    assert b[10:18] == bytes.fromhex("8877665544332211")          # device_id LE
    assert b[18:26] == bytes.fromhex("0807060504030201")          # session_id LE
    assert int.from_bytes(b[26:34], "little") == 1790000000123
    assert int.from_bytes(b[34:36], "little") == crc_bitwise(b[:34])
    assert Header.decode(b) == H


def test_stroke_record_layout_by_hand():
    s = StrokeSample(t_ms=0x01020304, stroke_id=7, x_um=-2, y_um=300, force_mN=950, theta_raw=104, phi_raw=18)
    r = encode_record(0x02, s.encode())
    assert (r[0], r[1], len(r)) == (0x02, 20, 24)
    assert r[2:6] == (0x01020304).to_bytes(4, "little")
    assert r[6:10] == (7).to_bytes(4, "little")
    assert r[10:14] == (-2).to_bytes(4, "little", signed=True)
    assert r[14:18] == (300).to_bytes(4, "little", signed=True)
    assert r[18:20] == (950).to_bytes(2, "little")
    assert (r[20], r[21]) == (104, 18)
    assert int.from_bytes(r[22:24], "little") == crc_bitwise(r[:22])   # CRC covers type + length + payload


def test_event_and_research_layout_by_hand():
    e = encode_record(0x03, Event(123456, EventCode.PEN_UP, -5).encode())
    assert (e[0], e[1], len(e)) == (0x03, 10, 14)
    assert e[2:6] == (123456).to_bytes(4, "little") and e[6:8] == b"\x08\x00"
    assert e[8:12] == (-5).to_bytes(4, "little", signed=True)
    f = ResearchFrame(t_us=1, q1=-2, f_ax=3, p_Hx=-4, p_Hy=5, opt_valid=6, dhat_y=-7, g=8, f_est=9, mode=10,
                      flags=0x0102, vbat_mV=3700, t_coil=-11, imu_ay=12, theta=13, phi=-14).encode()
    assert len(f) == 52
    le = lambda v, n, s=True: v.to_bytes(n, "little", signed=s)  # noqa: E731
    assert f[0:4] == le(1, 4, False) and f[4:6] == le(-2, 2) and f[20:22] == le(3, 2)
    assert f[22:26] == le(-4, 4) and f[26:30] == le(5, 4) and f[30] == 6 and f[33:35] == le(-7, 2)
    assert (f[35], f[36], f[37]) == (8, 9, 10) and f[38:40] == le(0x0102, 2, False)
    assert f[40:42] == le(3700, 2, False) and f[42:44] == le(-11, 2) and f[46:48] == le(12, 2)
    assert f[48:50] == le(13, 2) and f[50:52] == le(-14, 2)


def _mixed_records(n: int = 40, seed: int = 0):
    rng = np.random.default_rng(seed)
    recs = [RawRecord(0x05, b"SYNTHETIC test log"), Event(0, EventCode.MODE_CHANGE, 3)]
    for k in range(n):
        recs.append(StrokeSample(5 * k, k // 10, int(rng.integers(-10**6, 10**6)), int(rng.integers(-10**6, 10**6)),
                                 int(rng.integers(0, 2000)), int(rng.integers(0, 181)), int(rng.integers(0, 180))))
        if k % 7 == 0:
            recs.append(ResearchFrame(t_us=5000 * k, q1=int(rng.integers(-3000, 3000)), p_Hx=int(rng.integers(-10**7, 10**7)),
                                      flags=1))
        if k % 10 == 0:
            recs.append(Event(5000 * k, EventCode.PEN_DOWN, k // 10))
        if k % 13 == 0:
            recs.append(RawRecord(0x04, rng.integers(0, 256, int(rng.integers(1, 40)), dtype=np.uint8).tobytes()))
    return recs


def _pairs(recs):
    return [(record_type_of(r), bytes(r.encode())) for r in recs]


def test_round_trip_all_record_types():
    recs = _mixed_records()
    data = encode_log(H, recs)
    p = read_log(data, strict=True)
    assert p.header == H
    assert _pairs([r for _, r in p.records]) == _pairs(recs)
    strokes = [r for r in recs if isinstance(r, StrokeSample)]
    assert p.strokes["x_um"].tolist() == [s.x_um for s in strokes]
    assert p.stroke_payload == b"".join(s.encode() for s in strokes)
    assert not p.issues and not p.data_loss


def test_encoder_rejects_out_of_range_and_wrong_lengths():
    with pytest.raises(ValueError):
        StrokeSample(0, 0, 2**31, 0, 0, 0, 0).encode()
    with pytest.raises(ValueError):
        StrokeSample(0, 0, 0, 0, -1, 0, 0).encode()
    with pytest.raises(ValueError):
        StrokeSample(0, 0, 0, 0, 0, 256, 0).encode()
    with pytest.raises(ValueError):
        ResearchFrame(t_us=0, q1=40000).encode()
    with pytest.raises(ValueError):
        encode_record(0x02, b"\x00" * 19)
    with pytest.raises(ValueError):
        encode_record(0x05, b"\x00" * 256)


def test_header_errors():
    good = encode_log(H, [])
    with pytest.raises(lf.LogFormatError, match="magic"):
        read_log(b"XENLOG\x00\x01" + good[8:])
    bad = bytearray(good)
    bad[12] ^= 0xFF
    with pytest.raises(lf.LogFormatError, match="CRC"):
        read_log(bytes(bad))
    v2 = bytearray(good[:34])
    v2[8] = 2
    v2 = bytes(v2) + struct.pack("<H", lf.crc16_ccitt_false(bytes(v2)))
    with pytest.raises(lf.LogFormatError, match="format_version"):
        read_log(v2)
    with pytest.raises(lf.LogFormatError):
        read_log(good[:20])


@pytest.mark.parametrize("k", [0, 3, 17, -1])
@pytest.mark.parametrize("where", ["type", "length", "payload", "crc"])
def test_single_corruption_loses_only_that_record(k, where):
    recs = _mixed_records()
    data = encode_log(H, recs)
    spans = iter_record_spans(data)
    k = k % len(spans)
    off, end, _ = spans[k]
    pos = {"type": off, "length": off + 1, "payload": (off + 2 + end - 2) // 2, "crc": end - 1}[where]
    x = bytearray(data)
    x[pos] ^= 0x04
    p = read_log(bytes(x))
    assert _pairs([r for _, r in p.records]) == _pairs([r for i, r in enumerate(recs) if i != k])
    assert p.data_loss
    with pytest.raises(lf.StrictParseError):
        read_log(bytes(x), strict=True)


def _is_subsequence(sub, full) -> bool:
    it = iter(full)
    return all(any(s == f for f in it) for s in sub)


@pytest.mark.parametrize("seed", range(6))
def test_random_corruption_never_yields_false_records(seed):
    rng = np.random.default_rng(100 + seed)
    recs = _mixed_records(80, seed)
    data = bytearray(encode_log(H, recs))
    n_ops = int(rng.integers(1, 12))
    for _ in range(n_ops):
        op = rng.integers(3)
        pos = int(rng.integers(lf.HEADER_SIZE, len(data)))
        if op == 0:
            data[pos] ^= 1 << int(rng.integers(8))
        elif op == 1:
            data[pos:pos] = rng.integers(0, 256, int(rng.integers(1, 30)), dtype=np.uint8).tobytes()
        else:
            del data[pos:pos + int(rng.integers(1, 30))]
    p = read_log(bytes(data))
    got = _pairs([r for _, r in p.records])
    assert _is_subsequence(got, _pairs(recs)), "a record not present in the original log was accepted"
    assert len(got) >= len(recs) - 4 * n_ops         # each corruption costs at most a few records
    assert sum(i.skipped for i in p.issues) == p.bytes_skipped


def test_garbage_that_looks_like_a_record_header_is_rejected():
    recs = _mixed_records(10)
    data = encode_log(H, recs)
    off = iter_record_spans(data)[5][0]
    fake = b"\x02\x14" + b"\x00" * 20 + b"\xab\xcd"          # plausible type/length, wrong CRC
    p = read_log(data[:off] + fake + data[off:])
    assert _pairs([r for _, r in p.records]) == _pairs(recs)
    assert p.bytes_skipped == len(fake)


def test_variable_length_candidate_needs_a_valid_successor():
    # garbage forming an annotation with a *valid* CRC but followed by more garbage must not be accepted
    recs = _mixed_records(10)
    data = encode_log(H, recs)
    trap = encode_record(0x05, b"trap") + b"\xff\xfe\xfd"
    off = iter_record_spans(data)[4][0]
    corrupted = bytearray(data[:off] + b"\x99" + trap + data[off:])
    p = read_log(bytes(corrupted))
    got = _pairs([r for _, r in p.records])
    assert (0x05, b"trap") not in got
    assert _pairs(recs) == got


def test_truncated_tail_and_unknown_type():
    recs = _mixed_records(10) + [RawRecord(0x7E, b"future")]
    data = encode_log(H, recs)
    p = read_log(data)
    assert [i.kind for i in p.issues] == ["unknown_type"] and not p.data_loss
    q = read_log(data[:-5])
    assert _pairs([r for _, r in q.records]) == _pairs(recs[:-1])
    assert {"truncated", "trailing_garbage"} <= {i.kind for i in q.issues}


def test_t_us_wrap_explicit_event():
    top = (1 << 32) - 1000
    recs = [ResearchFrame(t_us=top), Event(200, EventCode.TIMESTAMP_WRAP, 1), ResearchFrame(t_us=500)]
    p = read_log(encode_log(H, recs), strict=True)
    assert p.research_t_us.tolist() == [top, (1 << 32) + 500]
    assert p.events[0][2] == (1 << 32) + 200
    assert (p.t_us_wraps_total, p.t_us_wraps_explicit) == (1, 1)


def test_t_us_wrap_inferred_without_event():
    recs = [ResearchFrame(t_us=(1 << 32) - 10), ResearchFrame(t_us=990), Event(1990, EventCode.PEN_UP, 0)]
    p = read_log(encode_log(H, recs))
    assert p.research_t_us.tolist() == [(1 << 32) - 10, (1 << 32) + 990]
    assert p.events[0][2] == (1 << 32) + 1990
    assert p.t_us_wraps_inferred == 1


def test_t_us_multiple_wraps_during_silent_gap_use_event_count():
    recs = [ResearchFrame(t_us=100), Event(50, EventCode.TIMESTAMP_WRAP, 2), ResearchFrame(t_us=60)]
    p = read_log(encode_log(H, recs))
    assert p.research_t_us.tolist() == [100, 2 * (1 << 32) + 60]


def test_wrap_count_mismatch_is_reported_and_event_wins():
    recs = [ResearchFrame(t_us=3_000_000_000), ResearchFrame(t_us=1_000), ResearchFrame(t_us=3_000_000_000),
            ResearchFrame(t_us=2_000), Event(2_500, EventCode.TIMESTAMP_WRAP, 1), ResearchFrame(t_us=3_000)]
    p = read_log(encode_log(H, recs))
    assert "wrap_count_mismatch" in {i.kind for i in p.issues}
    assert p.research_t_us[-1] == (1 << 32) + 3_000


def test_wrap_marker_arg0_as_emitted_by_firmware():
    # firmware/core/app.c logs PEN_EV_TIME_WRAP with arg 0 on the first tick after the wrap
    top = (1 << 32) - 500
    recs = [ResearchFrame(t_us=top), Event(0, EventCode.TIMESTAMP_WRAP, 0), ResearchFrame(t_us=0),
            ResearchFrame(t_us=500)]
    p = read_log(encode_log(H, recs), strict=True)
    assert p.research_t_us.tolist() == [top, 1 << 32, (1 << 32) + 500]
    assert p.t_us_wraps_total == 1                     # heuristic and marker count the same wrap once


def test_wrap_marker_after_silent_gap_counts_one_wrap():
    # no t_us record for most of a period: the heuristic sees a forward jump, the marker supplies the wrap
    recs = [Event(1_000_000_000, EventCode.PEN_UP, 0), Event(2_000_000_000, EventCode.TIMESTAMP_WRAP, 0),
            Event(2_000_000_100, EventCode.PEN_DOWN, 0)]
    p = read_log(encode_log(H, recs), strict=True)
    assert [t for _, _, t in p.events] == [1_000_000_000, (1 << 32) + 2_000_000_000, (1 << 32) + 2_000_000_100]


def test_stroke_t_ms_derived_from_wrapping_t_us_is_corrected():
    # firmware/core/app.c writes t_ms = t_us / 1000 from the 32-bit us counter: t_ms restarts at 4294967 ms
    recs = []
    true_ms = []
    for k in range(-6, 6):
        t_true = (1 << 32) + k * 5000                 # us, around the wrap
        t_us = t_true % (1 << 32)
        if k == 0:
            recs.append(Event(t_us, EventCode.TIMESTAMP_WRAP, 0))
        recs.append(StrokeSample(t_us // 1000, 1, k, 0, 900, 100, 0))
        true_ms.append(t_true // 1000)
    p = read_log(encode_log(H, recs))
    assert np.max(np.abs(p.stroke_t_ms - np.array(true_ms))) <= 1
    assert np.all(np.diff(p.stroke_t_ms) > 0)
    assert "t_ms_follows_t_us_wrap" in {i.kind for i in p.issues} and not p.data_loss


def test_annotation_and_calibration_layouts():
    a = lf.annotation_record("bench \u00b5m", 1234)
    assert a.payload[:4] == (1234).to_bytes(4, "little") and a.annotation() == (1234, "bench \u00b5m")
    c = lf.calibration_record(5, 1, b"PCAL")
    assert c.payload == b"\x05\x01\x00PCAL" and c.calibration() == (5, 1, b"PCAL")
    assert RawRecord(0x05, b"\x00").annotation() is None


def test_t_ms_wrap_of_stroke_samples():
    recs = [StrokeSample((1 << 32) - 5, 0, 0, 0, 0, 0, 0), StrokeSample(0, 0, 1, 1, 0, 0, 0)]
    p = read_log(encode_log(H, recs))
    assert p.stroke_t_ms.tolist() == [(1 << 32) - 5, 1 << 32]


def test_angle_encoding_interpretation():
    assert StrokeSample.angles_to_raw(0, 0) == (0, 0)
    assert StrokeSample.angles_to_raw(90, 358) == (180, 179)
    assert StrokeSample.angles_to_raw(52.2, 35.0) == (104, 18)
    assert StrokeSample.angles_to_raw(120, 360) == (180, 0)         # theta clipped to 90 deg, phi wraps
    s = StrokeSample(0, 0, 0, 0, 0, 104, 18)
    assert (s.theta_deg, s.phi_deg) == (52.0, 36.0)


def test_example_vector_is_reproducible():
    path = ROOT / "data" / "samples" / "icd_v1_example.penlog"
    assert path.exists(), "run app/demo.py to (re)generate data/samples/icd_v1_example.*"
    assert vectors.example_log() == path.read_bytes()
    expected = json.loads((ROOT / "data" / "samples" / "icd_v1_example.json").read_text())
    assert vectors.describe() == expected
    p = read_log(path.read_bytes())
    assert [i.kind for i in p.issues] == ["unknown_type"]
    assert p.t_us_wraps_total == 2            # one marker wrap + one counted wrap after a silent gap
    assert p.events[-1][2] == 2 * (1 << 32) + 300
