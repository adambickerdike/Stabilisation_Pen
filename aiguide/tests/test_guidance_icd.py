"""Closed-loop helpers on the unmodified M1 simulator, the proposed 0x06 record, and the adapter spec."""
from __future__ import annotations

import numpy as np
import pytest

from aiguide import adapter, guidance as G, icd_template as IT
from aiguide.glyphs import GLYPH_SET
from aiguide.writer import SyntheticWriter, WriterStyle
from stabpen import signals as sg


@pytest.fixture(scope="module")
def short_case():
    wr = SyntheticWriter(WriterStyle(), seed=2).write("on", dt=G.SIM_DT, seed=4)
    cfg = G.CONFIGS["pencil_0.3N"]
    scn = G.make_scenario(wr, sg.TremorSpec(f0=6.0, amp_pk=3e-4), cfg["N0"], seed=9)
    neutral = G.arrays(G.run(scn, cfg, "neutral", seed=3))
    guided = G.arrays(G.run(scn, cfg, "guided", seed=3))
    return wr, cfg, scn, neutral, guided


def test_guided_mode_engages_with_default_template(short_case):
    wr, cfg, scn, neutral, guided = short_case
    c = guided["contact"] > 0
    assert c.any() and guided["g"][c].max() > 0.9                 # authority reaches full scale in contact
    assert np.hypot(*guided["qr"].T).max() <= cfg["ctrl"]["q_lim"] + 1e-9
    assert neutral["g"].max() == 0.0


def test_splice_of_identical_runs_is_identity(short_case):
    wr, cfg, scn, neutral, guided = short_case
    wins = G.letter_windows(wr, float(neutral["t"][-1]))
    out, info = G.splice({0.0: neutral, 1.0: neutral}, [0.0, 1.0], wins)
    assert info["max_housing_jump_um"] == 0.0
    for k in ("tip", "pH", "q", "contact"):
        assert np.array_equal(out[k], neutral[k])
    mixed, _ = G.splice({0.0: neutral, 1.0: guided}, [0.0, 1.0], wins)
    m = neutral["t"] >= wins[1][0]
    assert np.array_equal(mixed["tip"][m], guided["tip"][m]) and np.array_equal(mixed["tip"][~m], neutral["tip"][~m])


def test_nib_offset_matches_simulated_ink_minus_housing(short_case):
    wr, cfg, scn, neutral, guided = short_case
    c = neutral["contact"] > 0
    measured = np.mean(neutral["tip"][c] - neutral["pH"][c, :2], axis=0)
    o = G.nib_offset(cfg)
    assert o[0] == pytest.approx(measured[0], rel=0.35) and abs(measured[1]) < 20e-6


def test_authority_rule():
    assert G.authority(0.2) == 0.0                                  # below c_min
    assert G.authority(0.6) == pytest.approx(0.6 / G.C_FULL)
    assert G.authority(0.95) == 1.0
    assert G.quantise(0.6) == 0.5 and G.quantise(0.75) == 0.75 and G.quantise(0.1) == 0.0


def test_template_record_roundtrip_and_legacy_reader():
    from penapp import logfmt
    h = 2.6e-3
    strokes = [np.column_stack([10e-3 + h * s[:, 0], 5e-3 + h * s[:, 1]]) for s in GLYPH_SET["k"]]
    recs = IT.encode_letter(strokes, seg_id=7, glyph="k", confidence=0.83, t_from_ms=1000, t_to_ms=1800,
                            speed_mm_s=28)
    assert all(len(r.payload()) <= 255 for r in recs) and recs[-1].last and not recs[0].last
    back = [IT.TemplateRecord.from_payload(r.payload()) for r in recs]
    dec = IT.decode_letter(back)
    assert len(dec) == len(strokes)
    origin = strokes[0][0]
    from scipy.spatial import cKDTree
    from aiguide.metrics import dense
    for s_ref, s_dec in zip(strokes, dec):
        d, _ = cKDTree(dense([(s_ref - origin) * 1e6], step=1.0)).query(s_dec)      # to the reference polyline
        assert d.max() < IT.RES_UM                                   # quantisation with error feedback
    assert back[0].glyph == "k" and back[0].confidence == pytest.approx(0.83, abs=1 / 255)
    hdr = logfmt.Header(device_id=1, session_id=2, start_unix_ms=0)
    data = logfmt.encode_log(hdr, [r.raw_record() for r in recs])
    parsed = logfmt.read_log(data)
    raws = [r for _, r in parsed.raw if r.rtype == IT.RTYPE_TEMPLATE]
    assert [r.payload for r in raws] == [r.payload() for r in recs]
    assert {i.kind for i in parsed.issues} == {"unknown_type"}          # kept, not data loss


def test_bandwidth_calculation():
    h = 2.6e-3
    letters = [([np.column_stack([h * s[:, 0], h * s[:, 1]]) for s in GLYPH_SET[c]], 0.9) for c in "hello"]
    bw = IT.bandwidth(letters, writing_time_s=5 * 0.57)
    assert 20 < bw["points_per_letter"] < 150
    assert bw["bytes_per_s_with_resends"] < bw["uplink_stroke_samples_bytes_per_s"]


def test_adapter_protocol_and_spec():
    class Dummy:
        model_id, is_local = "dummy", True

        def glyph_ahead(self, text, d=1):
            return np.ones(44) / 44

        def next_words(self, text, k=3):
            return []

        def complete_word(self, text, k=3):
            return []
    assert isinstance(Dummy(), adapter.TextPredictorProtocol)
    with pytest.raises(NotImplementedError):
        adapter.CLOUD_LLM_SPEC.glyph_ahead("abc", 2)
    assert adapter.CLOUD_LLM_SPEC.requires_consent and not adapter.CLOUD_LLM_SPEC.is_local
    b = adapter.LatencyBudget()
    assert b.margin() > 0 and b.total() < b.template_lead
