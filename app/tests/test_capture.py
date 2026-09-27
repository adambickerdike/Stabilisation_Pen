"""Segmentation, resampling, Frechet distance and capture-fidelity analysis."""
from __future__ import annotations

import math

import numpy as np
import pytest

from penapp import capture as cp
from penapp import logfmt
from penapp.notes import OriginalLayer

from conftest import TRACE


def _orig(rows):
    arr = np.zeros(len(rows), dtype=logfmt.STROKE_DTYPE)
    for k, r in enumerate(rows):
        arr[k] = r
    return OriginalLayer(arr.tobytes())


def test_contact_intervals():
    assert cp.contact_intervals(np.array([0, 1, 1, 0, 1, 0, 0, 1], bool)) == [(1, 3), (4, 5), (7, 8)]
    assert cp.contact_intervals(np.zeros(3, bool)) == []


def test_stroke_table_flags():
    rows = [(0, 0, 0, 0, 900, 100, 0), (5, 0, 10, 0, 900, 100, 0), (10, 0, 20, 0, 900, 100, 0),
            (30, 0, 30, 0, 900, 100, 0),                                      # 20 ms gap: dropout
            (100, 1, 0, 0, 900, 100, 0),                                      # single sample
            (200, 2, 0, 0, 900, 100, 0), (205, 2, 5, 0, 900, 100, 0)]         # short (5 ms)
    t = {s.stroke_id: s for s in cp.stroke_table(_orig(rows))}
    assert "dropout" in t[0].flags and t[0].length_um == 30
    assert {"single_sample", "short"} <= set(t[1].flags)
    assert "short" in t[2].flags and "dropout" not in t[2].flags
    ev = [{"code": 7, "t_us": 0}, {"code": 8, "t_us": 31000}]
    t = {s.stroke_id: s for s in cp.stroke_table(_orig(rows), events=ev)}
    assert "no_pen_down_event" not in t[0].flags and "no_pen_down_event" in t[1].flags


def test_segmentation_recovers_ground_truth_words(session_a, session_b):
    for ses in (session_a, session_b):
        p = logfmt.read_log(ses.encode())
        orig = OriginalLayer(p.stroke_payload)
        payload, _ = cp.segmentation_payload(orig)
        got = [s["stroke_ranges"] for s in payload["spans"] if s["level"] == "word"]
        want = [w["stroke_ranges"] for l in ses.truth["lines"] for w in l["words"]]
        assert got == want
        assert sum(s["level"] == "line" for s in payload["spans"]) == len(ses.truth["lines"])


def test_resampling_and_densify():
    t = np.array([0.0, 10.0, 25.0])
    xy = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 15.0]])
    tn, xn = cp.resample_time(t, xy, 200.0)
    assert tn[0] == 0 and tn[-1] == 25 and np.allclose(np.diff(tn)[:-1], 5.0)
    assert np.allclose(xn[2], [10.0, 0.0])
    xa = cp.resample_arclength(xy, 2.5)
    assert np.allclose(xa[0], xy[0]) and np.allclose(xa[-1], xy[-1])
    assert np.all(np.hypot(*np.diff(xa, axis=0).T) <= 2.5 + 1e-9)
    xd, td = cp.densify(xy, 3.0, t=t)
    assert np.all(np.hypot(*np.diff(xd, axis=0).T) <= 3.0 + 1e-9)
    assert all(any(np.allclose(v, w) for w in xd) for v in xy)            # original vertices kept
    assert np.all(np.diff(td) >= 0) and td[-1] == 25


def test_frechet_known_values():
    a = np.column_stack([np.linspace(0, 100, 50), np.zeros(50)])
    assert cp.discrete_frechet(a, a) == 0.0
    assert cp.discrete_frechet(a, a + [0.0, 7.0]) == pytest.approx(7.0)
    b = np.array([[0.0, 0.0], [100.0, 0.0]])
    # sparse vertices: discrete Frechet is inflated by the spacing, densification removes it
    assert cp.discrete_frechet(a, b) == pytest.approx(50.0, abs=1.1)
    assert cp.discrete_frechet(cp.densify(a, 0.5), cp.densify(b, 0.5)) < 0.6


@pytest.mark.parametrize("seed", range(4))
def test_frechet_implementations_agree(seed):
    rng = np.random.default_rng(seed)
    P = np.cumsum(rng.normal(size=(int(rng.integers(5, 40)), 2)), axis=0)
    Q = np.cumsum(rng.normal(size=(int(rng.integers(5, 40)), 2)), axis=0)
    ref = cp.discrete_frechet_reference(P, Q)
    assert cp._frechet_antidiagonal(P, Q) == pytest.approx(ref, abs=1e-12)
    # large, nearly aligned curves exercise the banded + certified path
    t = np.linspace(0, 1, 800)
    A = np.column_stack([t * 3000, 200 * np.sin(9 * t)]) + rng.normal(0, 2, (800, 2))
    B = A[::3] + rng.normal(0, 4, (len(A[::3]), 2))
    full = cp._frechet_antidiagonal(A, B)
    assert cp.discrete_frechet(A, B) == pytest.approx(full, abs=1e-9)
    assert cp.discrete_frechet(A, B, keys=(t, t[::3]), width=1e-6) == pytest.approx(full, abs=1e-9)


def _line_trace(speed_mm_s=40.0, n=400, curve=None):
    t_ms = np.arange(n)
    if curve is None:
        xy = np.column_stack([t_ms * speed_mm_s + 0.3, 0.2 * t_ms + 0.1])     # um (1 um/ms == 1 mm/s)
    else:
        xy = curve(t_ms)
    c = np.zeros(n, bool)
    c[20:n - 20] = True
    return cp.Trace("t", "-", "-", t_ms, xy - xy[20], c)


def test_fidelity_straight_line_only_rounding_and_end_truncation():
    tr = _line_trace()
    for ph in range(5):
        r = cp.stroke_fidelity(tr, 20, 380, "format_point", ph)
        assert r["interior_max_dev_um"] <= math.sqrt(0.5) + 1e-9          # straight: only 1 um rounding
        assert r["end_truncation_max_um"] <= 4 * 40.0 * 1.001 + 1          # <= 4 ms at 40 mm/s
    e = cp.stroke_fidelity(tr, 20, 380, "format_point_endpoints", 3)
    assert e["end_truncation_max_um"] == 0.0 and e["max_dev_um"] <= math.sqrt(0.5) + 1e-9


def test_fidelity_circle_matches_chord_sagitta():
    r_um, w = 3000.0, 2 * math.pi * 2.0 / 1000            # 3 mm radius, 2 rev/s (37.7 mm/s)
    tr = _line_trace(n=1000, curve=lambda t: np.column_stack([r_um * np.cos(w * t), r_um * np.sin(w * t)]))
    r = cp.stroke_fidelity(tr, 20, 980, "sampling_only", 0)
    th = w * 5.0                                          # angle subtended by one 5 ms chord
    arc = lambda a: r_um * np.array([math.cos(a), math.sin(a)])      # noqa: E731
    # exact time-aligned deviation at the 1 kHz points inside a chord (f = 1..4 ms / 5 ms)
    expected = max(np.hypot(*(arc(f * th) - ((1 - f) * arc(0.0) + f * arc(th)))) for f in (0.2, 0.4, 0.6, 0.8))
    assert r["interior_max_dev_um"] == pytest.approx(expected, rel=1e-3)
    assert expected < r_um * (1 - math.cos(th / 2))                  # below the chord sagitta
    assert r["interior_max_dev_um"] <= r["interp_bound_um"] + 1e-9


def test_quantisation_only_rms_matches_uniform_rounding_theory():
    rng = np.random.default_rng(3)
    tr = _line_trace(n=20000, curve=lambda t: np.column_stack([np.cumsum(rng.normal(0, 3, len(t))),
                                                                np.cumsum(rng.normal(0, 3, len(t)))]))
    r = cp.stroke_fidelity(tr, 20, 19980, "quantisation_only", 0, frechet=False)
    assert r["rms_dev_um"] == pytest.approx(math.sqrt(2 / 12), rel=0.03)  # sqrt(1/12) per axis
    assert r["max_dev_um"] <= math.sqrt(0.5) + 1e-9


@pytest.mark.skipif(not TRACE.exists(), reason="simulator traces not present")
def test_fidelity_on_simulator_trace_is_self_consistent():
    res = cp.fidelity_analysis([TRACE], phases=(0, 2), variants=("format_point", "quantisation_only"))
    s = res["summary"]["format_point"]
    n_ok, n = map(int, s["interior_within_interp_bound"].split("/"))
    assert n_ok == n > 0
    assert s["frechet_max_um"] <= s["max_dev_um"] + 2.0 + 1e-6            # time-aligned coupling bounds Frechet
    assert res["summary"]["quantisation_only"]["max_dev_um"] <= math.sqrt(0.5) + 1e-9
    assert res["meta"]["inputs"][0]["sha256"] and "SIMULATION" in res["meta"]["evidence_status"]


def _research(t_us, px_um, py_um, q1_um=None, q2_um=None):
    fr = np.zeros(len(t_us), dtype=logfmt.RESEARCH_DTYPE)
    fr["t_us"] = t_us
    fr["p_Hx"] = np.rint(np.asarray(px_um) * 10)
    fr["p_Hy"] = np.rint(np.asarray(py_um) * 10)
    if q1_um is not None:
        fr["q1"] = np.rint(np.asarray(q1_um) * 10)
        fr["q2"] = np.rint(np.asarray(q2_um) * 10)
    return fr


def test_hand_path_fit_recovers_origin_and_jacobian():
    # firmware relation: ink = p_H + J q - origin; p_H in a fusion frame far from the page origin
    rng = np.random.default_rng(0)
    t_us = np.arange(2000) * 500                                  # 2 kHz research frames
    tm = t_us / 1000.0
    ph = np.column_stack([5000 + 20 * tm + 150 * np.sin(2 * np.pi * 9 * tm / 1000), -2000 + 5 * tm])
    q = np.column_stack([120 + 250 * np.sin(2 * np.pi * 9 * tm / 1000 + 0.3), 40 * np.cos(2 * np.pi * 7 * tm / 1000)])
    J = np.array([[1.3, 0.1], [-0.05, 1.0]])
    origin = np.array([5100.0, -1990.0])
    ink = ph + q @ J.T - origin
    k = np.arange(0, 2000, 10)                                    # 200 Hz stroke samples
    rows = [(int(tm[i]), 1, int(round(ink[i, 0])), int(round(ink[i, 1])), 900, 100, 0) for i in k]
    fr = _research(t_us, ph[:, 0], ph[:, 1], q[:, 0], q[:, 1])
    pl = cp.hand_path_payload(_orig(rows), fr, t_us)
    al = pl["origin_alignment"]
    assert al["mode"] == "fit" and al["residual_rms_um"] < 1.0
    assert np.allclose(al["offset_um"], origin, atol=1.0)
    assert np.allclose(al["J_est"], J, atol=0.01)
    hand = np.column_stack([pl["strokes"][0]["x_um"], pl["strokes"][0]["y_um"]])
    assert np.allclose(hand, ph[k] - origin, atol=1.0)            # housing path in stroke page coordinates


def test_hand_path_other_origin_modes():
    rows = [(k * 5, 1, 1000 * k, 0, 900, 100, 0) for k in range(10)]
    t_us = np.arange(50) * 1000
    px = 5000 + (t_us / 1000) * 200 + 30 * np.sin(t_us / 3000.0)     # fusion frame + 30 um wobble
    fr = _research(t_us, px, np.full(50, -2000.0))
    first = cp.hand_path_payload(_orig(rows), fr, t_us, origin="first_contact")
    assert first["origin_alignment"]["offset_um"] == [5000.0, -2000.0]
    wob = np.array(first["strokes"][0]["x_um"]) - np.array([r[2] for r in rows])
    assert 5 < np.max(np.abs(wob)) <= 30.1
    fit = cp.hand_path_payload(_orig(rows), fr, t_us)                # q == 0: offset = mean difference
    assert fit["origin_alignment"]["J_est"] is None
    shared = cp.hand_path_payload(_orig(rows), fr, t_us, origin="shared")
    assert shared["strokes"][0]["x_um"][0] == pytest.approx(5000.0, abs=0.1)
