"""Fast checks of study R (target: well under a minute).  Tests that need the downloaded datasets or the built
library caches are skipped when those are absent (fresh clone): run python3 -m realdata.run first."""
from __future__ import annotations

import math

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
        p = D.tremor_params(dr.d[500:], 1000.0)
        assert abs(p["amp_median"] * 1e3 / dr.meta["amp_mm"] - 1) < 0.15
        lo, hi = RL.classes()["moderate"]["range_mm"]
        assert lo <= dr.meta["amp_mm"] <= hi
        assert abs(p["f0"] - dr.meta["f0"]) < 1.0
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


@pytest.mark.skipif(not (CACHE_DIR / "brush_writers.json").exists(), reason="BRUSH statistics not built")
def test_real_note_runs_in_hw1_and_the_clean_ink_follows_the_letters():
    from handwriting import params as PR, plant as PL
    from realdata import hw1 as H, library as RL
    wr = RL.writing("tuning", seed=0, n_words=3, dt=1e-4)
    hand, pen = PR.Hand.from_config(), PR.ordinary_pen()
    s0 = RL.hw1_scenario(wr)
    scn = PL.with_hand_path(s0, PL.adapted_path(s0.intended, s0.dt, pen, hand))
    r = PL.run(scn, pen, hand)
    assert H.path_error_um(wr, r) < 30.0
    s2 = RL.sim2_scenario(wr)
    assert s2.pref.shape[1] == 3 and len(s2.t) == len(wr.intended.t)
