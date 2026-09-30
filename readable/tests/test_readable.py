"""Fast tests of study F's package (python3 -m pytest -q readable/tests; well under a minute).

They check the pure pieces (residual constructions, the curve and its inversion, the predictors and their causality,
the gate calibration rule, the part-residual measure), the job runner, and the format of the published files when
they exist.  The simulation itself is checked in the runs (reproduction of R's and E's cached cases is recorded in
readable.json).
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import readable  # noqa: E402,F401
from readable import curve as CV  # noqa: E402
from readable import residual as RS  # noqa: E402

TS = 0.5e-3


def _sine(f=6.0, T=8.0, amp=1e-3, ecc=0.4):
    t = np.arange(int(T / TS)) * TS
    return t, np.column_stack([amp * np.sin(2 * np.pi * f * t), ecc * amp * np.cos(2 * np.pi * f * t)])


# ------------------------------------------------------------------ residual constructions
def test_scaled_leaves_the_share():
    t, d = _sine()
    q = -d
    r = d + RS.scaled(q, 0.3)
    assert np.allclose(r, 0.3 * d)
    assert np.allclose(RS.scaled(q, 1.0), 0.0) and np.allclose(RS.scaled(q, 0.0), q)


def test_delayed_is_a_pure_lag_and_matches_the_formula():
    t, d = _sine(f=6.0)
    tau = 10e-3
    q = RS.delayed(-d, t, tau)
    k = int(round(tau / TS))
    assert np.allclose(q[k + 5:], -d[5:len(d) - k], atol=1e-12)
    res = d + q
    m = t > 1.0
    amp = np.sqrt(2) * np.sqrt(np.mean(res[m, 0] ** 2)) / 1e-3
    assert abs(amp - RS.delay_residual_fraction(6.0, tau)) < 0.01
    assert abs(RS.delay_residual_fraction(6.0, RS.delay_for_fraction(6.0, 0.4)) - 0.4) < 1e-9


def test_band_noise_has_the_set_power_amplitude_and_band():
    from realdata import dsp as D
    n = RS.band_noise(40000, TS, 6.0, 0.4e-3, seed=7)
    pa = D.power_amplitude(n, 1 / TS, 6.0)
    assert abs(pa - 0.4e-3) / 0.4e-3 < 0.01
    assert np.allclose(n, RS.band_noise(40000, TS, 6.0, 0.4e-3, seed=7))
    f = np.fft.rfftfreq(len(n), TS)
    P = np.abs(np.fft.rfft(n[:, 0])) ** 2
    inband = P[(f > 3.5) & (f < 8.5)].sum() / P.sum()
    assert inband > 0.97


def test_variant_keys_are_stable():
    assert RS.variant_key("a", 0.27) == "E13a_0.27"
    assert RS.variant_key("b", 13.4) == "E13b_13.4ms"
    assert RS.variant_key("c", 0.4) == "E13c_0.40mm"


# ------------------------------------------------------------------ the curve
def test_curve_fit_recovers_parameters_and_inverts():
    rng = np.random.default_rng(1)
    p_true = (0.3, 6.8, 0.45, 3.0)
    r = np.tile(np.array([0.0, 0.05, 0.15, 0.3, 0.45, 0.6, 0.8, 1.1, 1.7]), 12)
    w = CV.model(r, p_true) + rng.normal(0, 0.4, len(r))
    f = CV.fit(r, w)
    assert f["ok"]
    assert abs(f["p"][2] - 0.45) < 0.08 and abs(f["p"][1] - 6.8) < 0.5
    for rr in (0.1, 0.4, 0.9):
        assert abs(CV.invert(f["p"], float(CV.model(rr, f["p"]))) - rr) < 1e-6
    assert not np.isfinite(CV.invert(f["p"], 11.0))
    th = CV.thresholds(p_true, 0.5, 6.8)
    assert abs(float(CV.model(th["r_plus2_mm"], p_true)) - 2.5) < 1e-9
    assert abs(float(CV.model(th["r_80_mm"], p_true)) - 0.8 * 6.8) < 1e-9


def test_curve_bootstrap_is_deterministic():
    rng = np.random.default_rng(2)
    pts = {}
    for k in range(6):
        r = np.array([0.0, 0.1, 0.3, 0.5, 0.8, 1.2, 1.7])
        pts[f"w{k}"] = list(zip(r, CV.model(r, (0.2, 7.0, 0.5, 3.0)) + rng.normal(0, 0.5, len(r))))
    ordw = {f"w{k}": 0.5 for k in range(6)}
    cl = {f"w{k}": 7.0 for k in range(6)}
    a = CV.fit_with_ci(pts, ordw, cl, n_boot=40)
    b = CV.fit_with_ci(pts, ordw, cl, n_boot=40)
    assert a["ci95"]["r_plus2_mm"] == b["ci95"]["r_plus2_mm"]
    assert a["ci95"]["r_plus2_mm"]["lo"] <= a["r_plus2_mm"] <= a["ci95"]["r_plus2_mm"]["hi"]


# ------------------------------------------------------------------ predictors
def test_ar_predictor_is_accurate_and_causal():
    from readable import gap as G
    t = np.arange(int(12.0 / TS)) * TS
    ph = 2 * np.pi * np.cumsum(6.0 + 0.5 * np.sin(2 * np.pi * 0.2 * t)) * TS
    d = np.column_stack([1e-3 * (1 + 0.3 * np.sin(2 * np.pi * 0.3 * t)) * np.sin(ph), 0.4e-3 * np.cos(ph)])
    lead, ds, dtau, order = 3.39e-3, 1.52e-3, 1e-3, 32
    A, b = G.normal_eq(d, t, ds, dtau, order, lead)
    coef = G.solve(A, b)
    dh = G.ar_apply(coef, d, t, ds, dtau)
    e = G.target_at(d, t, t, lead) - dh
    m = t > 1.0
    assert np.sqrt(np.mean(e[m] ** 2)) < 0.02 * np.sqrt(np.mean(d[m] ** 2))
    hold = G.hold_apply(d, t, ds)
    eh = G.target_at(d, t, t, lead) - hold
    assert np.sqrt(np.mean(eh[m] ** 2)) > 5 * np.sqrt(np.mean(e[m] ** 2))
    # causality: changing the signal after T changes no prediction before T + delta_s (one tick of interpolation)
    T = 6.0
    d2 = d.copy()
    d2[t > T] *= -3.0
    dh2 = G.ar_apply(coef, d2, t, ds, dtau)
    before = t < T + ds - TS
    assert np.array_equal(dh[before], dh2[before])


def test_page_known_is_sample_and_hold_of_valid_samples():
    from readable import gap as G

    class St:
        pos_t = np.array([0.0, 1e-3, 2e-3, 3e-3, 4e-3])
        pos = np.column_stack([np.arange(5.0), -np.arange(5.0)])
        pos_ok = np.array([1.0, 1.0, 0.0, 1.0, 1.0])
    v = G.page_known(St, np.array([-1e-3, 0.5e-3, 2.5e-3, 3.2e-3, 9e-3]))
    assert v[:, 0].tolist() == [0.0, 0.0, 1.0, 3.0, 4.0]


def test_fit_len_pads_with_the_last_value():
    from readable import gap as G
    x = np.arange(6.0).reshape(3, 2)
    y = G.fit_len(x, 5)
    assert y.shape == (5, 2) and np.array_equal(y[-1], x[-1]) and np.array_equal(G.fit_len(x, 2), x[:2])


def test_tremor_only_record_subtracts_the_clean_run(monkeypatch):
    from fusion import sensors as S
    from handwriting import tracker as TR
    from readable import gap as G
    n = 50
    t = np.arange(n) * 2.5e-4

    def rec(k):
        return S.Record(t=t, pH=np.column_stack([k * np.ones(n), 2 * k * np.ones(n), np.zeros(n)]),
                        aH=np.column_stack([k * t, k * t, np.ones(n)]), s=np.full(n, 0.5e-3), contact=np.ones(n),
                        hand_tremor=np.ones((n, 2)), intended=np.full((n, 2), 7.0), theta=0.8, phi=0.0, rho=0.0,
                        z0=0.0, s_min=0.0, n_steps=10 * n, dt=2.5e-5, sdec=20)
    seq = iter([rec(3.0), rec(1.0)])
    monkeypatch.setattr(TR, "record", lambda res, scn, td: next(seq))
    r = G.tremor_only_record(None, None, None, None, 20)
    assert np.allclose(r.pH[:, 0], 2.0) and np.allclose(r.pH[:, 1], 4.0)
    assert np.allclose(r.aH[:, :2], 2.0 * t[:, None]) and np.allclose(r.aH[:, 2], 1.0)
    assert np.allclose(r.intended, 0.0) and np.allclose(r.hand_tremor, 1.0)


# ------------------------------------------------------------------ the part-residual measure and the gate rule
def test_signal_residual_is_R_measure_on_a_sine():
    from readable import common as CM
    t1k = np.arange(8000) / 1000.0
    tick_t = np.arange(16000) * TS
    e = np.column_stack([0.8e-3 * np.sin(2 * np.pi * 6.0 * tick_t), np.zeros(len(tick_t))])
    r = CM.signal_residual_mm(e, tick_t, t1k, np.ones(len(t1k)), 6.0)
    assert abs(r - 0.8) < 0.01


def test_gate_calibration_rule():
    from readable import e11
    auth = {"a_lo": 0.5e-3, "a_hi": 1.0e-3, "tau_amp": 0.8, "tau_up": 0.03, "tau_down": 0.1, "gain": 1.2}
    st = {"q": {"0.99": 0.2e-3, "0.999": 0.3e-3, "1": 0.4e-3}}
    a = e11.calibrated(auth, st, 1.0, 1.5, "per_user")
    assert abs(a["a_lo"] - 0.6e-3) < 1e-12 and abs(a["a_hi"] / a["a_lo"] - 2.0) < 1e-12
    b = e11.calibrated(auth, st, 0.99, 1.0, "raise_only")
    assert b["a_lo"] == auth["a_lo"]
    c = e11.calibrated(auth, st, 0.99, 1.0, "per_user")
    assert abs(c["a_lo"] - 0.2e-3) < 1e-12
    assert all(c[k] == auth[k] for k in ("tau_amp", "tau_up", "tau_down", "gain"))
    assert len(e11.rules()) == 24 and e11.rule_key(1.0, 1.25, "raise_only") == "q1_k1.25_raise_only"
    assert e11._conservative_order("q1_k2_raise_only") < e11._conservative_order("q0.99_k2_raise_only")


def test_calibration_note_is_another_note_of_the_same_writer():
    from readable import e11
    from realdata import library as RL
    base = RL.writing("test", seed=0)
    s, w = e11.calibration_note("test", 0, 9, base.real["recordings"])
    assert s % 9 == 0 and s > 0
    assert w.real["writer"] == base.real["writer"]
    assert set(w.real["recordings"]).isdisjoint(base.real["recordings"])


# ------------------------------------------------------------------ the job runner
def test_job_runner_two_workers():
    from readable import jobs as JB
    specs = [JB.job(f"j{k}", "readable.residual", "delay_residual_fraction", f_hz=6.0, tau_s=k * 1e-3)
             for k in range(3)]
    out = JB.run(specs, workers=2, log=lambda *a: None)
    assert all(r["ok"] for r in out) and len(out) == 3
    got = sorted(r["result"] for r in out)
    assert abs(got[0]) < 1e-12 and abs(got[-1] - RS.delay_residual_fraction(6.0, 2e-3)) < 1e-12
    assert JB.MAX_WORKERS == 2


# ------------------------------------------------------------------ published files (when present)
RES = ROOT / "results" / "readable"


@pytest.mark.skipif(not (RES / "readable.json").exists(), reason="the full run has not written readable.json yet")
def test_provenance_block():
    import json
    d = json.loads((RES / "readable.json").read_text())
    pv = d["stabpen.provenance"]
    for k in ("git_revision", "inputs_sha256", "seeds", "parameters", "command", "python", "numpy", "generated_utc"):
        assert k in pv, k
    assert all(v is None or len(v) == 64 for v in pv["inputs_sha256"].values())
    assert "SIMULATION" in pv["evidence_status"]


@pytest.mark.skipif(not (RES / "frozen.json").exists(), reason="no freeze yet")
def test_freeze_precedes_the_test_split():
    import json
    import os
    fr = json.loads((RES / "frozen.json").read_text())
    assert "e13" in fr and "e11" in fr and "frozen_utc" in fr
    tdir = ROOT / "readable" / "build" / "cache" / "e13"
    tests = list(tdir.glob("test_*.json")) if tdir.exists() else []
    if tests:
        from datetime import datetime, timezone
        t_freeze = datetime.strptime(fr["frozen_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        assert min(os.path.getmtime(p) for p in tests) >= t_freeze - 1.0


@pytest.mark.skipif(not (RES / "evidence_rows.csv").exists(), reason="no proposed ledger rows")
def test_evidence_rows_format():
    raw = (RES / "evidence_rows.csv").read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n")
    rows = list(csv.reader(open(RES / "evidence_rows.csv", newline="", encoding="utf-8")))
    ledger = list(csv.reader(open(ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8")))
    assert rows[0] == ledger[0] and len(rows[0]) == 23
    used = {r[0] for r in ledger[1:]}
    for r in rows[1:]:
        assert len(r) == 23 and r[0] not in used
