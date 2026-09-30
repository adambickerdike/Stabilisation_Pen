"""Fast checks of study R (target: well under a minute).  Tests that need the downloaded datasets or the built
library caches are skipped when those are absent (fresh clone): run python3 -m realdata.run first."""
from __future__ import annotations

import math
import json

import numpy as np
import pytest

from realdata import CACHE_DIR, calib as CB, dsp as D, sources as SO


# ------------------------------------------------------------------ signal processing
def test_tremor_params_recovers_a_known_ellipse():
    fs = 1000.0
    t = np.arange(0, 20, 1 / fs)
    A, f0, e, th = 0.4e-3, 6.0, 0.3, math.radians(30)
    maj, mnr = A * np.cos(2 * np.pi * f0 * t), e * A * np.sin(2 * np.pi * f0 * t)
    x = np.column_stack([math.cos(th) * maj - math.sin(th) * mnr, math.sin(th) * maj + math.cos(th) * mnr])
    x += 0.2e-3 * np.column_stack([np.sin(2 * np.pi * 0.4 * t), np.cos(2 * np.pi * 0.3 * t)])   # slow drawing
    p = D.tremor_params(x, fs)
    assert abs(p["f0"] - f0) < 0.15
    assert abs(p["amp_median"] / A - 1) < 0.05
    assert abs(p["amp_excess"] / A - 1) < 0.15
    assert abs(p["ellipticity"] - e) < 0.05
    assert p["line_ratio"] > 50
    assert p["env_cv"] < 0.05


def test_acc_to_disp_inverts_double_differentiation():
    fs = 1000.0
    t = np.arange(0, 10, 1 / fs)
    d = 1e-3 * np.sin(2 * np.pi * 7 * t)
    a = -(2 * np.pi * 7) ** 2 * d
    r = D.acc_to_disp(a, fs, 3.0, 12.0)
    m = slice(2000, 8000)
    assert np.sqrt(np.mean((r[m] - d[m]) ** 2)) < 0.02e-3


def test_tremor_bands_keep_fundamental_and_harmonic():
    b = D.tremor_bands(6.0)
    assert b == [(4.0, 8.0), (10.0, 14.0)]
    assert D.tremor_bands(3.0) == [(1.5, 8.0)]


# ------------------------------------------------------------------ calibration
def test_gravity_fit_recovers_offset_and_gain():
    rng = np.random.default_rng(1)
    u = rng.normal(size=(400, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    o, k = np.array([4.6, 4.5, 4.55]), np.array([6.7, 6.6, 6.8])
    v = u * CB.G0 / k + o + rng.normal(0, 0.002, (400, 3))
    cal = CB.gravity_fit(v)
    assert np.allclose(cal["offset"], o, atol=0.01)
    assert np.allclose(cal["gain_ms2_per_unit"], k, rtol=0.01)
    assert cal["residual_rms_ms2"] < 0.05


def test_pixel_pitch_is_the_manufacturer_value():
    assert CB.CINTIQ12WX_PITCH_M == pytest.approx(0.204e-3)
    assert CB.pixel_quantisation_rms_m() == pytest.approx(0.204e-3 / math.sqrt(12))


# ------------------------------------------------------------------ registry
def test_every_source_has_a_licence_and_a_redistribution_rule():
    for k, s in SO.SOURCES.items():
        assert s.licence and s.citation and s.url, k
        assert s.redistribute in ("excerpts", "statistics", "nothing"), k
        if "CC BY 4.0" == s.licence:
            assert s.redistribute == "excerpts"
        if "non-commercial" in s.licence or "NC" in s.licence or "research" in s.licence:
            assert s.redistribute == "statistics", k


# ------------------------------------------------------------------ writing assembly (no data needed)
def test_assemble_joins_strokes_smoothly_and_labels_letters():
    from realdata import writinglib as WL
    t = np.arange(0, 0.3, 0.01)
    s1 = WL.Stroke(t=t, xy=np.column_stack([t * 0.02, 0.002 * np.sin(20 * t)]), char=np.zeros(len(t), int))
    s2 = WL.Stroke(t=t, xy=np.column_stack([0.012 + t * 0.02, 0.002 * np.cos(20 * t)]), char=np.full(len(t), 2))
    w = WL.assemble([s1, s2], "a b", dt=1e-4, height_m=5e-3, writer="test/0", source="test")
    it = w.intended
    assert it.pen_down.any() and (~it.pen_down).any()
    step = np.hypot(*np.diff(it.xy, axis=0).T)
    assert step.max() < 5e-5                      # no jump anywhere (continuous path at 10 kHz)
    assert [L.char for L in w.letters] == ["a", "b"]
    assert w.letters[1].word_index == 1
    assert w.letters[0].strokes and w.letters[1].t0 > w.letters[0].t1


def test_quintic_hermite_meets_its_end_conditions():
    from realdata import writinglib as WL
    P = WL._quintic_hermite([0, 0], [0.01, 0], [0.003, 0.001], [0.0, 0.02], 0.1, 10000.0)
    assert np.allclose(P[0], [0, 0])
    v0 = (P[1] - P[0]) * 10000.0
    assert np.allclose(v0, [0.01, 0.0], atol=1e-4)


def test_split_is_deterministic_and_two_way():
    from realdata import writinglib as WL
    a = [WL.split_of("brush", str(i)) for i in range(200)]
    assert a == [WL.split_of("brush", str(i)) for i in range(200)]
    assert set(a) == {"tuning", "test"}
    assert 0.25 < a.count("tuning") / 200 < 0.55


def test_word_alignment_counts_exact_matches():
    from realdata import ocr as OC
    assert OC.align_words(["return", "library", "books"], ["return", "libary", "books", "."]) == [True, False, True]
    assert OC.align_words(["a", "b"], []) == [False, False]


# ------------------------------------------------------------------ built library (skipped without caches)
needs_lib = pytest.mark.skipif(not (CACHE_DIR / "tremorlib.json").exists(), reason="tremor library not built")


@needs_lib
def test_tremor_draw_has_the_class_amplitude_and_real_frequency():
    from realdata import library as RL
    for kind in ("PD", "ET"):
        dr = RL.tremor("moderate", seed=2, kind=kind, split="tuning", duration=8.0, dt=1e-3)
        assert dr.d.shape == (8000, 2)
        # the class convention: power amplitude (sqrt(2) x RMS of the major axis at f0 +- 2 Hz) after the onset ramp
        pa = D.power_amplitude(dr.d[500:], 1000.0, dr.meta["f0"])
        assert abs(pa * 1e3 / dr.meta["amp_mm"] - 1) < 0.10
        lo, hi = RL.classes()["moderate"]["range_mm"]
        assert lo <= dr.meta["amp_mm"] <= hi
        f, P = D.psd(dr.d[500:], 1000.0)
        assert abs(f[np.argmax(P)] - dr.meta["f0"]) < 1.0          # the largest line is the recording's own f0
        assert dr.meta["split"] == "tuning"


@needs_lib
def test_library_splits_are_disjoint_by_subject():
    from realdata import tremorlib as TL
    rows = TL.load()["rows"]
    for src in {r["source"] for r in rows}:
        tun = {r["subject"] for r in rows if r["source"] == src and r["split"] == "tuning"}
        tst = {r["subject"] for r in rows if r["source"] == src and r["split"] == "test"}
        assert not (tun & tst), src


@needs_lib
def test_classes_are_ordered_and_from_the_data():
    from realdata import library as RL
    c = RL.classes()
    assert c["mild"]["range_mm"][1] == pytest.approx(c["moderate"]["range_mm"][0])
    assert c["moderate"]["range_mm"][1] == pytest.approx(c["severe"]["range_mm"][0])
    assert c["mild"]["representative_mm"] < c["moderate"]["representative_mm"] < c["severe"]["representative_mm"]


_unipen_index_path = CACHE_DIR / "unipen_index.json"
_unipen_available = (
    _unipen_index_path.exists()
    and bool(json.loads(_unipen_index_path.read_text())["writers"])
)
# Index construction also writes an empty index when no licensed files exist.
# A malformed or partially populated index should still fail, not be hidden.
needs_unipen = pytest.mark.skipif(
    not _unipen_available, reason="licensed UNIPEN corpus absent or writing index empty")


@needs_unipen
def test_real_note_runs_in_hw1_and_the_clean_ink_follows_the_letters():
    from handwriting import params as PR, plant as PL
    from realdata import hw1 as H, library as RL
    wr = RL.writing("tuning", seed=0, n_words=2, dt=1e-4, max_lines=1)
    assert wr.real["source"] == "unipen" and wr.real["split"] == "tuning"
    hand, pen = PR.Hand.from_config(), PR.ordinary_pen()
    s0 = RL.hw1_scenario(wr)
    scn = PL.with_hand_path(s0, PL.adapted_path(s0.intended, s0.dt, pen, hand))
    r = PL.run(scn, pen, hand)
    assert H.path_error_um(wr, r) < 30.0
    s2 = RL.sim2_scenario(wr)
    assert s2.pref.shape[1] == 3 and len(s2.t) == len(wr.intended.t)


@needs_unipen
def test_unipen_notes_are_writer_and_text_disjoint_and_upright():
    from realdata import writinglib as WL
    idx = WL.unipen_index()
    tun, tst = WL.unipen_writers("tuning", idx), WL.unipen_writers("test", idx)
    assert tun and tst and not (set(tun) & set(tst))
    for w in tun[:1] + tst[:1]:
        v = idx["writers"][w]
        pool = WL._unipen_pool(v)
        assert pool and all(sg["text_split"] == v["split"] for sg in pool)
    ttxt = {sg["label"] for w in tun for sg in WL._unipen_pool(idx["writers"][w])}
    stxt = {sg["label"] for w in tst for sg in WL._unipen_pool(idx["writers"][w])}
    assert not (ttxt & stxt)
    n = WL.unipen_note(tst[0], seed=0, n_words=4, dt=1e-3, index=idx)
    it = n.intended
    # ruled lines go down the page: the first line's ink lies above the last line's
    a0, b0 = n.real["line_spans"][0]
    a1, b1 = n.real["line_spans"][-1]
    y0 = it.xy[(it.t >= a0) & (it.t <= b0) & it.pen_down, 1].mean()
    y1 = it.xy[(it.t >= a1) & (it.t <= b1) & it.pen_down, 1].mean()
    assert len(n.real["line_spans"]) == 1 or y0 > y1
    assert 1.5 < n.real["letter_height_mm"] < 20.0             # one test writer writes tall letters (about 15 mm)


def test_rank_split_takes_exactly_the_share():
    from realdata import writinglib as WL
    sp = WL.rank_split([f"w{i}" for i in range(14)], "salt")
    assert sum(v == "tuning" for v in sp.values()) == 5
    assert sp == WL.rank_split([f"w{i}" for i in range(14)][::-1], "salt")


# ------------------------------------------------------------------ page-sensor model and measures (no data needed)
def _toy_note():
    from realdata import writinglib as WL
    t = np.arange(0, 3.0, 0.01)
    st = [WL.Stroke(t=t, xy=np.column_stack([0.02 * t + 0.01 * k, 0.002 * np.sin(12 * t)]), char=np.zeros(len(t), int))
          for k in range(3)]
    return WL.assemble(st, "a", dt=1e-3, height_m=5e-3, writer="toy/0", source="toy")


def test_page_model_fit_reproduces_the_deltapen_statistics():
    from realdata import sensors as RS
    m = RS.fit_window_error([_toy_note()])
    assert m.fitted["median_um"] == pytest.approx(23.6, rel=0.02)
    assert m.fitted["mean_um"] == pytest.approx(68.3, rel=0.02)


def test_page_model_v2_is_saved_beside_the_version_1_fit(tmp_path, monkeypatch):
    """DEC-076: realdata.hw1.page_model() saves its version-2 fit as page_model_v2.json; the version-1 file that studies
    R, E and F used (page_model.json) is kept, not overwritten."""
    from dataclasses import asdict
    from realdata import hw1 as H
    from realdata import library as RL
    from realdata import sensors as RS
    from realdata import writinglib as WL
    v1p, v2p = tmp_path / "page_model.json", tmp_path / "page_model_v2.json"
    monkeypatch.setattr(RS, "PAGE_MODEL_JSON", v1p)
    monkeypatch.setattr(RS, "PAGE_MODEL_V2_JSON", v2p)
    monkeypatch.setattr(H, "_PAGE", {})
    monkeypatch.setattr(WL, "unipen_writers", lambda *a, **k: ["toy/0"])
    monkeypatch.setattr(RL, "writing", lambda *a, **k: _toy_note())
    v1 = {k: v for k, v in asdict(RS.PageModel(name="deltapen", c=20.48e-6, sigma=1.354)).items() if k != "version"}
    v1p.write_text(json.dumps(v1))
    before = v1p.read_bytes()
    m = H.page_model(log=lambda *a: None)
    assert m.version == 2 and v1p.read_bytes() == before and v2p.exists()
    assert RS.load_model().c == m.c and RS.load_model().version == 2
    old = RS.load_model(allow_legacy=True)
    assert old.version == 1 and old.c == 20.48e-6


def test_aggregation_refuses_mixed_page_model_versions():
    """DEC-076: every case file records its page-model version (files without it: version 1); cases of different
    versions are not aggregated together (a partial rerun on newer code must not mix them silently)."""
    from realdata import hw1 as H
    cases = [{"set": "real", "writer": f"w{w}", "kind": "PD", "class": "severe", "tremor": {"amp_mm": 1.7, "f0": 6.0},
              "devices": {"none": {"words_read": 2, "words_total": 10, "tip_tremor_mm": 1.7}}} for w in range(4)]
    assert H.page_model_version(cases[0]) == 1
    H.aggregate(cases)                                          # the existing case files: version 1
    H.aggregate([dict(c, page_model_version=2) for c in cases])
    with pytest.raises(ValueError, match="page-model versions"):
        H.aggregate(cases[:3] + [dict(cases[3], page_model_version=2)])


def test_degraded_page_stream_keeps_times_and_carries_the_window_error():
    from fusion import sensors as FS
    from realdata import sensors as RS
    n = 6000
    t = np.arange(n) / 1000.0
    P = np.column_stack([0.02 * t, 0.002 * np.sin(2 * np.pi * 1.5 * t)])
    z = np.zeros(10)
    st = FS.Streams(tick_t=t, acc_t=t, acc_av=t, acc=np.zeros((n, 2)), pos_t=t, pos_av=t + 2e-3, pos=P,
                    pos_ok=np.ones(n), con_t=z, con_av=z, con=z)
    m = RS.PageModel(c=20e-6, sigma=1.3)
    d = RS.degrade_page(st, m, seed=3)
    assert np.array_equal(d.pos_t, st.pos_t)                    # acquisition times unchanged
    assert np.all(np.diff(d.pos_av) >= 0) and np.all(d.pos_av >= d.pos_t + m.latency_s - 1e-12)
    chk = RS.window_error_check(st, d)
    assert 5.0 < chk["median_um"] < 80.0 and chk["mean_um"] > chk["median_um"]
    assert d.pos_ok.mean() < 1.0                                 # outliers and dropouts are marked invalid


def test_tip_tremor_uses_the_class_convention():
    from types import SimpleNamespace
    from realdata import hw1 as H
    fs = 2000.0
    t = np.arange(0, 6, 1 / fs)
    A, f0 = 0.5e-3, 6.0
    intended = np.column_stack([0.01 * t, np.zeros_like(t)])
    ink = intended + np.column_stack([A * np.cos(2 * np.pi * f0 * t), 0.3 * A * np.sin(2 * np.pi * f0 * t)])
    res = SimpleNamespace(t=t, ink=ink, contact=np.ones_like(t))
    scn = SimpleNamespace(dt=1 / fs, t=t, intended=intended)
    assert H.tip_tremor_mm(res, scn, f0) == pytest.approx(0.5, rel=0.03)


def test_writer_bootstrap_card_and_ratio_meaning():
    from realdata import hw1 as H
    cases = []
    for w in range(6):
        cases.append({"writer": f"w{w}", "devices": {
            "none": {"words_read": 4, "words_total": 10, "tip_tremor_mm": 1.0},
            "revJ_gated|deltapen": {"words_read": 6 + (w % 2), "words_total": 10, "tip_tremor_mm": 0.5}}})
    c = H.card(cases, ["none", "revJ_gated|deltapen"])
    g = c["revJ_gated|deltapen"]
    assert g["words_of_10"]["mean"] == pytest.approx(6.5)
    assert g["words_of_10"]["lo"] <= 6.5 <= g["words_of_10"]["hi"]
    assert g["words_of_10_gain"]["mean"] == pytest.approx(2.5)
    assert g["tip_tremor_ratio"]["mean"] == pytest.approx(0.5)
    assert g["tip_tremor_ratio"]["power_reduction_pct"] == pytest.approx(75.0)


def test_literal_word_scoring_drops_punctuation_only_targets_and_reports_cer():
    from realdata import ocr as OC
    assert OC.cer("return library", "return library") == 0.0
    assert OC.cer("abc", "abd") == pytest.approx(1 / 3)
    assert OC.align_words(["hello", "world"], ["Hello,", "word"]) == [True, False]


@needs_lib
def test_classes_are_fitted_on_tuning_subjects_and_checked_on_test():
    from realdata import library as RL
    c = RL.classes()
    assert "tuning" in c["_fitted_on"]
    v = c["_validation_test_subjects"]
    assert v["n"] > 5 and abs(v["share_mild"] + v["share_moderate"] + v["share_severe"] - 1) < 1e-9


def test_results_card_tables_render_from_fake_cases():
    from realdata import hw1 as H, report as R
    cases = []
    for w in range(4):
        dv = {"none": {"words_read": 2, "words_total": 10, "tip_tremor_mm": 1.7},
              "revJ_gated|deltapen": {"words_read": 3, "words_total": 10, "tip_tremor_mm": 1.2},
              "revJ_oracle": {"words_read": 7, "words_total": 10, "tip_tremor_mm": 0.02}}
        cases.append({"set": "real", "writer": f"w{w}", "kind": "PD", "class": "severe",
                      "tremor": {"amp_mm": 1.7, "f0": 6.0}, "devices": dv})
        cases.append({"set": "clean_real", "writer": f"w{w}", "devices": {
            "none": {"words_read": 8, "words_total": 10}, "revJ_gated|deltapen": {"words_read": 8, "words_total": 10,
                                                                                "false_correction_um": 20.0}}})
    ag = H.aggregate(cases)
    c = R.cards(ag)
    assert c and c[0]["pens"]["revJ_gated|deltapen"]["words_of_10"]["mean"] == pytest.approx(3.0)
    md = R.doc_tables({"hw1": {"aggregate": ag}})
    assert "| Parkinson's, severe (1.70 mm) | 8.0 |" in md
    assert "power -50 %" in md                      # (1.2/1.7)^2 - 1 = -0.50
