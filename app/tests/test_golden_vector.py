"""Cross-check with the firmware team's independently written golden log.

firmware/tests/vectors/golden_log_v1.bin is produced by the C encoder
(firmware/tests/test_log.c, golden_build).  The expected values below are
transcribed from that C source, so this test compares two independent
implementations of ICD section 4 (v1.3: CAL_USER v2 snapshot, pen-up boundary
sample, timestamp-wrap event, exported ML model hash 0xa57d81f6).  If the firmware's JSON decode
(golden_log_v1.json) exists, it is cross-checked as well (best effort, its
schema is owned by the firmware team).
"""
from __future__ import annotations

import json

import pytest

from penapp.logfmt import EventCode, read_log

from conftest import ROOT

GOLDEN = ROOT / "firmware" / "tests" / "vectors" / "golden_log_v1.bin"
GOLDEN_JSON = GOLDEN.with_suffix(".json")

pytestmark = pytest.mark.skipif(not GOLDEN.exists(), reason="firmware golden vector not present")


def test_golden_log_parses_strictly():
    p = read_log(GOLDEN, strict=True)
    assert (p.header.device_id, p.header.session_id, p.header.start_unix_ms) == (
        0x0123456789ABCDEF, 0x42, 1790000000000)
    assert p.counts == {1: 3, 2: 4, 3: 7, 4: 1, 5: 2}
    assert not p.issues


def test_golden_log_values_match_c_source():
    p = read_log(GOLDEN, strict=True)
    assert [tuple(r) for r in p.strokes.tolist()] == [
        (1000, 1, 0, 0, 950, 100, 0),
        (1005, 1, 152, -37, 1010, 101, 179),
        (1007, 1, 188, -41, 400, 101, 179),                               # pen-up boundary sample
        (4294967295, 4294967295, -2147483647, 2147483647, 65535, 180, 90)]  # range extremes
    ev = [(e.t_us, e.code, e.arg) for _, e, _ in p.events]
    assert ev == [(1000000, EventCode.MODE_CHANGE, 3 | (2 << 8)),     # ASSIST_KF | NEUTRAL_HOLD << 8
                  (1000500, EventCode.PEN_DOWN, 0),
                  (1002000, EventCode.FAULT_SET, 1 << 1),              # PEN_FAULT_HALL
                  (1500000, EventCode.FAULT_CLEARED, 1 << 1),
                  (1500500, EventCode.ML_MODEL_LOADED, 0xA57D81F6 - (1 << 32)),  # exported model hash as i32
                  (1600000, EventCode.AUTHORITY_CAPPED, 16),        # MLG_R_APOST: a-posteriori fallback
                  (1234, EventCode.TIMESTAMP_WRAP, 1)]              # first wrap, cumulative count
    ann = [r.annotation() for _, r in p.raw if r.annotation() is not None]
    assert ann == [(2000000, "bench session 1: 50 deg, 1 N"), (2000500, "UTF-8 µm °")]
    cal = [r.calibration() for _, r in p.raw if r.calibration() is not None]
    assert len(cal) == 1 and cal[0][:2] == (5, 2) and len(cal[0][2]) == 30   # CAL_USER, cal_version 2, 30 B
    assert p.research["t_us"].tolist() == [1000000, 1000500, 1001000]


def test_golden_log_imports_into_note_store(tmp_path):
    from penapp.notes import NoteStore
    from penapp._util import file_sha256
    st = NoteStore(tmp_path / "s")
    note = st.import_log(read_log(GOLDEN), source_name=GOLDEN.name, source_sha256=file_sha256(GOLDEN))
    orig = st.get_original(note["original_sha256"])
    assert orig.n_samples == 4 and sorted(orig.stroke_ids) == [1, 4294967295]
    assert [a["text"] for a in note["annotations"]] == ["bench session 1: 50 deg, 1 N", "UTF-8 µm °"]
    assert st.verify()["ok"]


@pytest.mark.skipif(not GOLDEN_JSON.exists(), reason="firmware JSON decode of the golden vector not present")
def test_golden_log_matches_firmware_json():      # pragma: no cover - depends on the firmware team's file
    ref = json.loads(GOLDEN_JSON.read_text())
    p = read_log(GOLDEN, strict=True)
    text = json.dumps(ref)
    assert str(p.header.start_unix_ms) in text
    recs = ref.get("records") if isinstance(ref, dict) else None
    if isinstance(recs, list):
        assert len(recs) == sum(p.counts.values())
