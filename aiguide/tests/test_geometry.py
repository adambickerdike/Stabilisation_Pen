"""Writer, style estimation, templates, stroke prediction and metrics (synthetic data only)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from aiguide import metrics, stroke_predict as sp
from aiguide.glyphs import GLYPH_SET, LETTERS
from aiguide.run_style import observe
from aiguide.sentences import CALIB_SENTENCE
from aiguide.style import Prior, StyleEstimator, fit_letter
from aiguide.template import anchor_to, build_track, letter_template, template_error
from aiguide.writer import SyntheticWriter, WriterStyle, contact_runs, sample_style


# ------------------------------------------------------------------ writer
def test_writer_strokes_letters_and_micrographia():
    st = WriterStyle()
    wr = SyntheticWriter(st, seed=3).write("the cat", dt=1e-3, seed=1)
    n_strokes = sum(len(GLYPH_SET[c]) for c in "thecat")
    assert len(contact_runs(wr.intended.pen_down)) == n_strokes
    assert [L.char for L in wr.letters] == list("thecat")
    assert all(a.t1 <= b.t0 for a, b in zip(wr.letters[:-1], wr.letters[1:]))
    st_m = WriterStyle(micrographia=0.4, scale_jitter=0.0)
    wm = SyntheticWriter(st_m, seed=3).write("aaaaaaaa", dt=1e-3, seed=1)
    assert wm.letters[-1].size == pytest.approx(0.6 * wm.letters[0].size, rel=1e-6)


def test_writer_is_deterministic():
    st = sample_style(np.random.default_rng(5))
    a = SyntheticWriter(st, seed=5).write("ab", dt=1e-3, seed=2).intended.xy
    b = SyntheticWriter(st, seed=5).write("ab", dt=1e-3, seed=2).intended.xy
    assert np.array_equal(a, b)


# ------------------------------------------------------------------ style fit
@pytest.mark.parametrize("ch", ["a", "k", "s", "t"])
def test_fit_letter_recovers_exact_affine(ch):
    a, b, h, x0, y0 = 2.9e-3, 0.6e-3, 2.7e-3, 11e-3, -2e-3
    ink = [np.column_stack([x0 + a * s[:, 0] + b * s[:, 1], y0 + h * s[:, 1]]) for s in GLYPH_SET[ch]]
    ink = [np.vstack([np.linspace(p, q, 20, endpoint=False) for p, q in zip(s[:-1], s[1:])] + [s[-1:]]) for s in ink]
    f = fit_letter(ch, ink, smooth=1)
    assert f.h == pytest.approx(h, rel=6e-3)
    assert f.a == pytest.approx(a, rel=6e-3)
    assert f.b == pytest.approx(b, abs=6e-6)
    assert f.x0 == pytest.approx(x0, abs=6e-6) and f.y0 == pytest.approx(y0, abs=6e-6)
    assert f.rms < 10e-6                       # sampling floor of the nearest-point residual


def test_fit_degenerate_glyph_uses_prior():
    h = 2.5e-3
    ink = [np.column_stack([np.full(30, 1e-3), np.linspace(1.6 * h, 0, 30)])]        # an 'l': no horizontal extent
    f = fit_letter("l", ink, smooth=1, prior=Prior(h=h, width=1.1, slant=math.radians(8)))
    assert f.h == pytest.approx(h, rel=0.02)
    assert f.width == pytest.approx(1.1, rel=0.05)


def test_style_estimator_on_clean_pangram():
    # A clean affine-recovery test must disable glyph deformations: those include
    # random affine width/slant changes, so the nominal latent style is not the
    # actual written geometry when the default allograph warp is enabled.
    st = WriterStyle(x_height_mm=2.8, slant_deg=15.0, width=1.05,
                     allograph_amp=0.0, instance_amp=0.0, scale_jitter=0.0,
                     offset_jitter=0.0, baseline_wander=0.0)
    wr = SyntheticWriter(st, seed=7).write(CALIB_SENTENCE, dt=1e-3, seed=3)
    obs, _ = observe(wr, 0.0, 6.0, np.random.default_rng(0))
    est = StyleEstimator()
    for L, (strokes, times, _d) in zip(wr.letters, obs):
        est.update(L.char, strokes, t_strokes=times)
    e = est.estimate()
    assert e.h == pytest.approx(2.8e-3, rel=0.08)
    assert math.degrees(e.slant) == pytest.approx(15.0, abs=3.0)
    assert e.width == pytest.approx(1.05, rel=0.08)
    assert est.exemplar("q") is not None and len(est.exemplar("t")) == 2


# ------------------------------------------------------------------ templates
def test_template_anchor_track_and_error():
    st = WriterStyle()
    wr = SyntheticWriter(st, seed=1).write("hit", dt=1e-3, seed=0)
    est = StyleEstimator()
    obs, _ = observe(wr, 0.0, 6.0, np.random.default_rng(0))
    for L, (strokes, times, _d) in zip(wr.letters, obs):
        est.update(L.char, strokes, t_strokes=times)
    e = est.estimate()
    tl = []
    for k, L in enumerate(wr.letters):
        t = letter_template(L.char, e, 0.0, 0.0, estimator=est, mode="exemplar", glyph_index=k)
        t = anchor_to(t, L.polylines[0][0])
        assert np.allclose(t.strokes[0][0], L.polylines[0][0])
        tl.append(t)
    trk = build_track(tl, speed=0.028, air_speed=0.06, dt=5e-4)
    assert len(contact_runs(trk.pen_down)) == sum(len(t.strokes) for t in tl)
    assert set(np.unique(trk.letter_of[trk.pen_down])) <= {0, 1, 2}
    r = template_error(wr.letters[0].polylines, wr.letters[0].polylines)
    assert np.max(r["d"]) < 1e-9 and np.max(r["d_shape"]) < 1e-9


# ------------------------------------------------------------------ stroke prediction
def test_kinematic_predictors_exact_on_lines_and_circles():
    tau = (np.arange(sp.W) - (sp.W - 1)) * sp.TS
    line = np.stack([0.03 * tau, -0.01 * tau], axis=1)[None]
    want = np.array([[0.03 * h, -0.01 * h] for h in sp.HORIZONS_S])
    assert np.allclose(sp.predict_poly(line, 4, 1)[0], want, atol=1e-12)
    assert np.allclose(sp.predict_arc(line, 5)[0], want, atol=1e-12)
    R, w = 1.3e-3, 0.03 / 1.3e-3
    circ = np.stack([R * np.cos(w * tau) - R, R * np.sin(w * tau)], axis=1)[None]
    want = np.array([[R * np.cos(w * h) - R, R * np.sin(w * h)] for h in sp.HORIZONS_S])
    assert np.allclose(sp.predict_arc(circ, 9)[0], want, atol=1e-9)
    for k in (3, 8, 16):
        assert sp.poly_fir(k, 2, 0.1).sum() == pytest.approx(1.0)       # constants are preserved


def test_windows_and_budget():
    t = np.arange(0, 1.0, 1e-3)
    xy = np.stack([0.02 * t, np.zeros_like(t)], axis=1)
    pd = (t > 0.1) & (t < 0.9)
    w = sp.windows_from_path(t, xy, xy, pd, writer_id=1)
    assert w.X.shape[1:] == (sp.W, 2) and w.Y.shape[1:] == (len(sp.HORIZONS_S), 2)
    assert np.allclose(w.X[:, -1], 0.0)
    b = sp.mac_budget(3, 24, 21, sp.MLPPredictor().macs())
    assert b["mlp_float"]["mac"] < 35_000 and b["mlp_float"]["time_us_128MHz"] < 1000


# ------------------------------------------------------------------ metrics
def test_dtw_and_recogniser_on_clean_glyphs():
    A = np.random.default_rng(0).normal(size=(40, 2))
    assert metrics.dtw(A, A) == pytest.approx(0.0, abs=1e-12)
    h, wdt, sl = 2.6e-3, 1.0, math.radians(10)
    rec = metrics.GlyphRecognizer(h, wdt, sl)
    ok = 0
    for c in LETTERS:
        strokes = [np.column_stack([h * wdt * s[:, 0] + h * math.tan(sl) * s[:, 1], h * s[:, 1]]) + 5e-3
                   for s in GLYPH_SET[c]]
        ok += rec.classify(strokes)[0] == c
    assert ok == 26


def test_letter_metrics_and_travel_limit():
    P = [np.column_stack([np.linspace(0, 2e-3, 50), np.zeros(50)])]
    ink = np.vstack([P[0], P[0][::-1]])
    lm_ = metrics.letter_metrics(ink, np.ones(len(ink)), P, "l")
    assert lm_["path_rms_um"] < 2.0          # 5 um densification of the intended path
    qr = np.array([[0.0, 0.0], [0.3e-3, 0.0], [0.0, 0.29e-3], [0.1e-3, 0.0]])
    tl = metrics.travel_limit(qr, np.array([0, 0, 1, 0]), np.ones(4), 0.3e-3)
    assert tl["at_soft_limit"] == pytest.approx(0.5) and tl["on_stop"] == pytest.approx(0.25)
