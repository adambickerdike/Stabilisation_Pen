"""Unit tests of the measurement models, identification tools, truth draws and file format.
These verify code, not physics (SIMULATION/CALCULATION only)."""
import math
import os

import numpy as np
import pytest

import s2r  # noqa: F401
from s2r import ident, io
from s2r import instruments as ins
from s2r import truth as tr


def test_every_instrument_number_is_labelled():
    rows = ins.provenance_table()
    assert rows
    for r in rows:
        assert any(tag in r["origin"] for tag in ("PROTOCOL", "ASSUMPTION", "CONFIG", "DESIGN")), r


def test_measure_applies_gain_latency_and_quantisation():
    t = np.arange(0, 1.0, 1e-5)
    x = np.sin(2 * np.pi * 5 * t)
    ch = ins.Channel("probe", "u", fs=1000.0, lsb=1e-3, latency=2e-3, src={"all": "ASSUMPTION test"})
    ses = ins.Session({"probe": 1.02}, {"probe": 0.1}, {}, 0.0)
    tr_, y = ins.measure(ch, t, x, np.random.default_rng(0), ses)
    expect = 1.02 * np.sin(2 * np.pi * 5 * (tr_ - 2e-3)) + 0.1
    assert np.max(np.abs(y - expect)) <= 0.5e-3 + 1e-9
    assert np.allclose(np.diff(tr_), 1e-3)


def test_session_systematics_within_protocol_bounds():
    rng = np.random.default_rng(1)
    for _ in range(50):
        s = ins.draw_session(rng)
        assert abs(s.gain(ins.FT_SENSOR) - 1) <= ins.FT_SENSOR.gain_bound
        assert abs(s.sync_offset) <= ins.SYNC_BOUND


def test_ols_and_laplace_coverage():
    rng = np.random.default_rng(2)
    hits = 0
    for _ in range(200):
        x = np.linspace(0, 1, 20)
        y = 2.0 * x + 0.5 + 0.1 * rng.standard_normal(20)
        r = ident.ols(np.column_stack([x, np.ones_like(x)]), y)
        hits += abs(r["b"][0] - 2.0) <= 1.96 * r["se"][0]
    assert 0.9 <= hits / 200 <= 0.99


def test_nls_recovers_exponential():
    t = np.linspace(0, 5, 200)
    y = 3.0 * (1 - np.exp(-t / 0.7)) + 0.01 * np.random.default_rng(3).standard_normal(200)
    r = ident.nls(lambda p: p[0] * (1 - np.exp(-t / p[1])) - y, [1.0, 1.0])
    assert r["p"] == pytest.approx([3.0, 0.7], rel=0.01)


def _so_response(a, fn, z, fs, u):
    from scipy import signal as sps
    wn = 2 * math.pi * fn
    b, a_ = sps.bilinear([-a], [1, 2 * z * wn, wn * wn], fs=fs)
    return sps.lfilter(b, a_, u)


def test_frf_fit_second_order_and_iv_unbiased_with_input_noise():
    rng = np.random.default_rng(4)
    fs = 2000.0
    ur, yr, rr = [], [], []
    for _ in range(6):
        r = rng.standard_normal(8000)
        y = _so_response(100.0, 20.0, 0.05, fs, r)
        ur.append(r + 0.5 * rng.standard_normal(8000))       # noisy measured input
        yr.append(y + 1e-4 * rng.standard_normal(8000))
        rr.append(r)
    f, H, coh, sig = ident.frf_iv(rr, ur, yr, fs, 2, 200)
    fit = ident.fit_second_order(f, H, sig, fit_delay=False)
    assert fit["p"][1] == pytest.approx(20.0, rel=0.01)
    assert fit["p"][2] == pytest.approx(0.05, rel=0.1)
    f1, H1, _, _ = ident.frf_h1(ur, yr, fs, 2, 200)
    k = np.argmin(np.abs(f1 - 5.0))
    assert np.abs(H1[k]) < 0.9 * np.abs(H[k])                  # H1 is biased low by input noise


def test_whiteness_and_drift_tests():
    rng = np.random.default_rng(5)
    white = rng.standard_normal(5000)
    ar = np.zeros(5000)
    for i in range(1, 5000):
        ar[i] = 0.5 * ar[i - 1] + white[i]
    assert ident.ljung_box(white)["white_at_1pct"]
    assert not ident.ljung_box(ar)["white_at_1pct"]
    assert ident.drift_test(np.array([1.0, 1.01, 0.99]), np.array([0.02, 0.02, 0.02]))["constant_at_1pct"]
    assert not ident.drift_test(np.array([1.0, 1.2, 1.4]), np.array([0.02, 0.02, 0.02]))["constant_at_1pct"]


def test_combine_rectangular_bound():
    c = ident.combine(1.0, 0.0, rel_bounds=[0.02])
    assert c["u"] == pytest.approx(0.02 / math.sqrt(3))


def test_truth_draws_inside_and_outside():
    ts = tr.batch(7, 6, 6)
    for t in ts[:6]:
        assert all(tr.in_range(k, v) for k, v in t["values"].items())
    n_out = sum(len(t["outside"]) for t in ts[6:])
    assert n_out > 0
    for t in ts[6:]:
        for k in t["outside"]:
            assert not tr.in_range(k, t["values"][k]) or k in tr.LIMITS
            assert t["values"][k] > 0
    assert tr.commitment(ts) == tr.commitment(tr.batch(7, 6, 6))


def test_io_roundtrip_npz_and_csv(tmp_path):
    rng = np.random.default_rng(6)
    ds = {"_hidden": {"x": 1.0}, "scalar": 3.5,
          "group": {"records": [{"t": np.arange(10.0), "F_a": rng.standard_normal(10), "theta": 50.0,
                                 "fine": rng.standard_normal(25)}], "bench_s": 12.0},
          "single": {"R_ohm": rng.standard_normal(5), "T_nominal_C": 20.0, "points": [{"I": 0.1, "F": 0.2}]},
          "lst": [{"daq": {"i_A": rng.standard_normal(7)}, "pen": {"iref_A": rng.standard_normal(3)}}]}
    for fmt in ("npz", "csv"):
        d = os.path.join(tmp_path, fmt)
        io.save(ds, d, "TEST", fmt=fmt)
        back = io.load(d)
        assert "_hidden" not in back
        assert back["scalar"] == 3.5
        assert np.allclose(back["group"]["records"][0]["F_a"], ds["group"]["records"][0]["F_a"])
        assert np.allclose(back["group"]["records"][0]["fine"], ds["group"]["records"][0]["fine"])
        assert back["single"]["points"][0]["F"] == 0.2
        assert np.allclose(back["lst"][0]["pen"]["iref_A"], ds["lst"][0]["pen"]["iref_A"])
