"""Fast tests of study E (python3 -m pytest -q realtrack/tests; under a minute).

Causality of every estimator family (a change of the streams after time T never changes an output before T), the
authority's causality, the gate re-implementation against ai2's detector gate, the fast tip-tremor measure against R's,
the surrogate against the full HW1 plant (if the tuning cache exists), the ledger rows' format."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pytest

import realtrack  # noqa: F401  (environment: numba cache, threads)
from realtrack import estimators as E

ROOT = Path(__file__).resolve().parents[2]


def synth_streams(T: float = 8.0, f0: float = 6.0, amp: float = 1e-3, seed: int = 0):
    """Synthetic fusion Streams: handle = slow writing-like motion + tremor; IMU = its second derivative + noise."""
    from fusion import sensors as S
    rng = np.random.default_rng(seed)
    Ts = 0.5e-3
    tick = np.arange(0.0, T, Ts)
    ta = np.arange(0.0, T, 1.0 / 3840.0)
    w = 2 * math.pi * f0

    def pos(t):
        return np.column_stack([2e-3 * np.sin(2 * math.pi * 1.3 * t) + amp * np.sin(w * t),
                                1.5e-3 * np.cos(2 * math.pi * 0.9 * t) + 0.5 * amp * np.cos(w * t)])

    def acc(t):
        return np.column_stack([-(2 * math.pi * 1.3) ** 2 * 2e-3 * np.sin(2 * math.pi * 1.3 * t) - w * w * amp * np.sin(w * t),
                                -(2 * math.pi * 0.9) ** 2 * 1.5e-3 * np.cos(2 * math.pi * 0.9 * t)
                                - 0.5 * w * w * amp * np.cos(w * t)])
    a = acc(ta) + rng.normal(0, 0.003, (len(ta), 2))
    tp = np.arange(0.0, T, 1e-3)
    p = pos(tp) + rng.normal(0, 3e-6, (len(tp), 2))
    tc = np.arange(0.0, T, 1e-3)
    return S.Streams(tick_t=tick, acc_t=ta, acc_av=ta + 1.39e-3, acc=a, pos_t=tp, pos_av=tp + 2e-3, pos=p,
                     pos_ok=np.ones(len(tp)), con_t=tc, con_av=tc + 1e-3, con=np.ones(len(tc)))


def perturb_after(st, T0: float):
    """A copy whose samples AVAILABLE after T0 are changed."""
    from fusion import sensors as S
    acc = st.acc.copy(); pos = st.pos.copy()
    acc[st.acc_av > T0] += 5.0
    pos[st.pos_av > T0] += 1e-3
    return S.Streams(tick_t=st.tick_t, acc_t=st.acc_t, acc_av=st.acc_av, acc=acc, pos_t=st.pos_t, pos_av=st.pos_av,
                     pos=pos, pos_ok=st.pos_ok, con_t=st.con_t, con_av=st.con_av, con=st.con)


@pytest.mark.parametrize("design", [
    {"family": "akf", "params": {"qt": 3e-8, "qh": 1e-8, "qj": 0.004, "ra": 0.1, "tau_decay": 0.21, "tau_w": 0.3,
                                 "harm": 0.6, "lp_hz": 55.0, "g": 1.0, "f_gate": 0.0}},
    {"family": "wflc", "params": {}},
    {"family": "bmflc", "params": {}},
    {"family": "bmflc_kf", "params": {}},
    {"family": "epll", "params": {}},
    {"family": "akf", "params": {"g": 1.0, "f_gate": 0.0}, "auth": {"a_lo": 0.3e-3, "a_hi": 0.8e-3, "tau_amp": 0.3}},
])
def test_estimators_are_causal(design):
    st = synth_streams()
    T0 = 5.0
    d0, _ = E.estimate(design, st, horizon=3.4e-3)
    d1, _ = E.estimate(design, perturb_after(st, T0), horizon=3.4e-3)
    k = st.tick_t <= T0 - 1e-9
    assert np.allclose(d0[k], d1[k], atol=1e-15)
    assert not np.allclose(d0[~k], d1[~k])            # the perturbation does reach the later outputs


def test_epll_locks_on_a_sinusoid():
    st = synth_streams(T=10.0, f0=6.0, amp=1e-3)
    d, info = E.epll(st, {}, horizon=0.0)
    f = info["f_est"][st.tick_t > 6.0]
    assert abs(np.median(f) - 6.0) < 0.3


def test_authority_is_causal_and_bounded():
    rng = np.random.default_rng(1)
    d = rng.normal(0, 1e-3, (4000, 2))
    a, g, A = E.authority(d, 0.5e-3, {"a_lo": 0.5e-3, "a_hi": 1.0e-3})
    d2 = d.copy(); d2[2000:] *= 10
    b, g2, _ = E.authority(d2, 0.5e-3, {"a_lo": 0.5e-3, "a_hi": 1.0e-3})
    assert np.allclose(a[:2000], b[:2000]) and np.all((g >= 0) & (g <= 1))


def test_hysteresis_gate_equals_ai2_detector_gate():
    from ai2 import smoothers as SM
    from realtrack import search as SR
    st = synth_streams(T=10.0)
    dp = dict(SM.DET_DEFAULTS); dp.update({"r_on": 5.0, "r_off": 2.5, "t_on": 0.5, "t_off": 1.0, "ramp": 0.2})
    det = SM.detector(st, dp)
    g = SR.hyst_gate(det["t"], det["ratio"], det["amp"], {"r_on": 5.0, "r_off_frac": 0.5, "t_on": 0.5, "t_off": 1.0,
                                                           "ramp": 0.2, "amp_lo": -1.0, "amp_hi_mult": 0.5})
    assert np.allclose(g, det["gate"])


def test_fast_tip_tremor_equals_R():
    from realdata import hw1 as H
    from realtrack import servo as SV

    class Res:
        pass
    rng = np.random.default_rng(3)
    t = np.arange(0, 6.0, 1e-3)
    ink = np.column_stack([1e-3 * np.sin(2 * math.pi * 6 * t), 0.4e-3 * np.cos(2 * math.pi * 6 * t)])
    ink += rng.normal(0, 2e-5, ink.shape)
    con = np.ones(len(t)); con[2000:2300] = 0
    r = Res(); r.t = t; r.ink = ink; r.contact = con

    class Scn:
        pass
    Scn.dt = 1e-3
    Scn.t = t
    Scn.intended = np.zeros((len(t), 2))
    a = H.tip_tremor_mm(r, Scn, 6.0)
    b = SV.tip_tremor_mm(t, ink, np.zeros_like(ink), con, 6.0)
    assert abs(a - b) < 1e-12


def test_surrogate_matches_full_plant_on_a_cached_case():
    from realtrack import cases as C
    p = C.CASE_DIR / "tune_n0_PD_severe.npz"
    if not p.exists():
        pytest.skip("tuning cache not built (python3 -m realtrack.run --stages cases)")
    from realtrack import servo as SV
    c = C.load_case("tune_n0_PD_severe")
    m = SV.fast_measures(c, -c.dh_revh("deltapen"))
    full = c.meta["ref"]["revh_tip_tremor_mm_deltapen"]
    assert abs(m["tip_tremor_mm"] / full - 1) < 0.01


def test_polyphase_tick_index():
    from realtrack import learned as LE
    tick = np.arange(0, 0.1, 0.5e-3)
    k, p = LE.tick_index(tick)
    assert np.all(k * (1 / LE.FS_IN) <= tick + 1e-12) and np.all(p >= 0) and np.all(p < LE.N_PH)
    assert np.all(np.abs(k / LE.FS_IN + p / LE.TICK_HZ - tick) < 1e-9)


def test_evidence_rows_format():
    f = ROOT / "results" / "realtrack" / "evidence_rows.csv"
    if not f.exists():
        pytest.skip("evidence rows not written yet")
    raw = f.read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n")
    hdr = next(csv.reader(open(ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8")))
    rows = list(csv.reader(open(f, newline="", encoding="utf-8")))
    assert rows[0] == hdr and all(len(r) == 23 for r in rows)
    ok = {f"EML-{i}" for i in range(100, 110)} | {f"PDT-{i}" for i in range(90, 95)} | \
         {f"ACT-{i}" for i in range(140, 145)} | {f"OPT-{i}" for i in range(95, 100)}
    assert all(r[0] in ok for r in rows[1:])


def test_mcu_table_positive():
    from realtrack import mcu as MC
    t = MC.table()
    for k, v in t.items():
        if isinstance(v, dict) and "cpu_share_128MHz" in v:
            assert 0 < v["cpu_share_128MHz"] < 1
