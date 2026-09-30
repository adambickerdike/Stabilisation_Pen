"""Fast tests of study L (ai2): causality of the estimators, the command and the learned models; the tremor-line
gate; the RL environments' API; sigma-lognormal recovery; the assistance-as-needed law; the evidence rows; and the
output files' schema (when they exist).  Target: well under a minute on one core."""
from __future__ import annotations

import csv
import json
import math

import numpy as np
import pytest

from ai2 import RESULTS_DIR
from ai2 import data as DA
from ai2 import evidence as EV
from ai2 import learned as LE
from ai2 import rl_env as RE
from ai2 import shared as SH
from ai2 import smoothers as SM
from ai2 import synth as SY
from fusion.sensors import Streams


# ------------------------------------------------------------------ synthetic sensor streams from a writer's path
def _streams(tremor_mm: float = 0.0, f0: float = 8.0, text: str = "minimum minimum", seed: int = 0) -> Streams:
    """Page sensor (1 kHz, 2 ms latency, 3 um noise) and accelerometer (3.84 kHz) from an aiguide writer's intended
    path plus an optional sinusoidal tremor; contact from the pen-down flag."""
    from handwriting import writers as W
    rng = np.random.default_rng(seed)
    wr = W.writer(100).write(text, dt=W.SIM_DT, seed=1)
    t, xy, down = wr.intended.t, wr.intended.xy, wr.intended.pen_down.astype(float)
    T = float(t[-1])

    def path(tq):
        p = np.column_stack([np.interp(tq, t, xy[:, 0]), np.interp(tq, t, xy[:, 1])])
        if tremor_mm > 0:
            p += tremor_mm * 1e-3 * np.column_stack([np.sin(2 * np.pi * f0 * tq), 0.5 * np.cos(2 * np.pi * f0 * tq)])
        return p
    pos_t = np.arange(0.0003, T, 1e-3)
    pos = path(pos_t) + rng.standard_normal((len(pos_t), 2)) * 3e-6
    acc_t = np.arange(0.0001, T, 1 / 3840.0)
    h = 1e-3
    acc = (path(acc_t + h) - 2 * path(acc_t) + path(acc_t - h)) / h ** 2 + rng.standard_normal((len(acc_t), 2)) * 0.02
    con_t = np.arange(0.0002, T, 1e-3)
    con = (np.interp(con_t, t, down) > 0.5).astype(float)
    return Streams(tick_t=np.arange(0, T, 5e-4), acc_t=acc_t, acc_av=acc_t + 1e-3, acc=acc, pos_t=pos_t, pos_av=pos_t + 2e-3,
                   pos=pos, pos_ok=np.ones(len(pos_t)), con_t=con_t, con_av=con_t + 1e-3, con=con)


def _cut(st: Streams, t_cut: float, scale: float = 5.0) -> Streams:
    """The same streams with every sample acquired after t_cut changed (a different future)."""
    pos = st.pos.copy(); acc = st.acc.copy()
    pos[st.pos_t > t_cut] *= scale
    acc[st.acc_t > t_cut] *= -scale
    return Streams(**{**st.__dict__, "pos": pos, "acc": acc})


@pytest.fixture(scope="module")
def st_tremor():
    return _streams(1.0, 8.0)


@pytest.fixture(scope="module")
def st_clean():
    return _streams(0.0)


# ------------------------------------------------------------------ task 1: causality of the fixed-lag smoother
def test_fixed_lag_smoother_is_causal(st_tremor):
    lags = (0.0, 0.025, 0.05)
    a = SM.rts_fixed_lag(st_tremor, {}, lags, 3.39e-3, out_every=4)
    t_cut = 3.0
    b = SM.rts_fixed_lag(_cut(st_tremor, t_cut), {}, lags, 3.39e-3, out_every=4)
    # a changed sample acquired after t_cut is available from t_cut + 0.35 ms (IMU) or + 2 ms (page sensor) at the
    # earliest (fusion.sensors latencies); no output before t_cut + 0.35 ms may change
    before = a["t"] < t_cut + 0.35e-3
    assert np.allclose(np.nan_to_num(a["tremor"][before]), np.nan_to_num(b["tremor"][before]), atol=1e-12)
    assert np.allclose(np.nan_to_num(a["handle"][before]), np.nan_to_num(b["handle"][before]), atol=1e-12)
    after = a["t"] > t_cut + 0.012
    assert not np.allclose(np.nan_to_num(a["tremor"][after]), np.nan_to_num(b["tremor"][after]))


def test_fixed_lag_smoother_tracks_a_tremor(st_tremor):
    """On a 1 mm, 8 Hz synthetic tremor the smoothed tremor estimate at 50 ms lag has the right size (0.3-3 mm peak)."""
    r = SM.rts_fixed_lag(st_tremor, {"tau_decay": 2.0, "qt": 1e-9, "qh": 3.3e-10}, (0.05,), 3.39e-3, out_every=8)
    m = r["t"] > 3.0
    pk = np.percentile(np.abs(r["tremor"][m, 0, 0]), 95)
    assert 0.3e-3 < pk < 3e-3


# ------------------------------------------------------------------ task 1/2: the tremor-line gate
def test_detector_gate_closed_on_writing_open_on_tremor(st_clean, st_tremor):
    p = {"win": 4.0, "seg": 2.0, "every": 0.05, "min_win": 4.0, "mode": "hyst", "r_on": 5.0, "r_off": 2.5, "t_on": 0.5, "t_off": 1.0}
    d0 = SM.detector(st_clean, p)
    d1 = SM.detector(st_tremor, p)
    assert float(np.max(d0["gate"])) == 0.0
    assert float(np.mean(d1["gate"] > 0.5)) > 0.5
    k = d1["gate"] > 0.5
    assert abs(float(np.median(d1["f_hat"][k])) - 8.0) < 0.5


def test_detector_is_causal(st_tremor):
    p = {"min_win": 4.0}
    a = SM.detector(st_tremor, p)
    t_cut = 6.0
    b = SM.detector(_cut(st_tremor, t_cut), p)
    before = a["t"] < t_cut + 2e-3 - 1e-9
    assert np.allclose(a["ratio"][before], b["ratio"][before]) and np.allclose(a["gate"][before], b["gate"][before])


# ------------------------------------------------------------------ task 2: learned models are causal
@pytest.mark.parametrize("arch", ["tcn", "transformer"])
def test_learned_models_are_causal(arch):
    import torch
    torch.manual_seed(0)
    m = LE.make_tcn(7, 8) if arch == "tcn" else LE.make_transformer(7, 8, d=16, heads=2, window=64, ff=32)
    x = torch.randn(1, 600, 7)
    x2 = x.clone(); x2[0, 400:] += 3.0
    with torch.no_grad():
        y, y2 = m(x), m(x2)
    assert torch.allclose(y[0, :400], y2[0, :400], atol=1e-6)
    assert not torch.allclose(y[0, 400:], y2[0, 400:])


def test_transformer_chunked_inference_matches_full():
    import torch
    torch.manual_seed(1)
    m = LE.make_transformer(7, 8, d=16, heads=2, window=64, ff=32)
    Z = np.random.default_rng(0).standard_normal((1500, 7)).astype(np.float32)
    with torch.no_grad():
        full = m(torch.from_numpy(Z)[None])[0].numpy()
    ch = LE.predict(m, Z, chunk=300).reshape(1500, -1) / LE.OUT_S
    assert np.abs(ch - full).max() < 1e-4


def test_hold_extrapolate_is_causal_and_accurate():
    tk = np.arange(0, 1, 0.002)
    Y = np.sin(2 * np.pi * 10 * tk)[:, None, None] * np.ones((1, 1, 2)) * 1e-3
    t = np.arange(0.01, 0.99, 0.0005)
    Z = LE.hold_extrapolate(tk, Y, t)
    assert np.abs(Z[:, 0, 0] - 1e-3 * np.sin(2 * np.pi * 10 * t)).max() < 12e-6     # CALC bound ~10 um
    Y2 = Y.copy(); Y2[tk > 0.5] = 0.0
    Z2 = LE.hold_extrapolate(tk, Y2, t)
    assert np.allclose(Z[t < 0.5], Z2[t < 0.5])


def test_base_estimate_falls_back_to_revh_when_gate_closed():
    T = 400
    mb = {"gate": np.zeros(T), "amp": np.zeros(T), "D": np.ones((T, 4, 2)), "dh": np.full((T, 2), 0.5)}
    B, g = LE.base_estimate(mb)
    assert np.allclose(B[:, 0], 0.5) and np.all(g == 0)
    mb["gate"] = np.ones(T); mb["amp"] = np.full(T, 1e-3)
    B, g = LE.base_estimate(mb, 0.15e-3, 0.35e-3)
    assert np.allclose(B, 1.0)


# ------------------------------------------------------------------ task 3: RL environments
def _episode(T=3000, seed=0, amp=1e-3):
    rng = np.random.default_rng(seed)
    t = np.arange(T) / 500.0
    d = amp * np.column_stack([np.sin(2 * np.pi * 8 * t), np.cos(2 * np.pi * 8 * t)])
    Y = np.repeat(d[:, None, :], len(DA.LAGS), axis=1).astype(np.float32)
    D = (Y + rng.standard_normal(Y.shape) * 1e-4).astype(np.float32)
    return {"X": rng.standard_normal((T, 7)).astype(np.float32), "Y": Y, "mask": np.ones(T, np.float32), "D": D,
            "dh": (0.5 * d).astype(np.float32), "ratio": np.full(T, 8.0, np.float32), "amp": np.full(T, amp, np.float32),
            "f_hat": np.full(T, 8.0, np.float32), "gate": np.ones(T, np.float32), "spec": {"amp": amp, "f0": 8.0}}


@pytest.mark.parametrize("cls", ["GateEnv", "ResidualEnv"])
def test_rl_env_api(cls):
    from gymnasium.utils.env_checker import check_env
    env = getattr(RE, cls)(RE.ReplayBackend([_episode(), _episode(seed=1)]))
    check_env(env, skip_render_check=True)


def test_gate_env_rewards_trusting_a_good_estimate():
    ep = _episode()
    env = RE.GateEnv(RE.ReplayBackend([ep]))
    tot = {}
    for w in (0.0, 1.0):
        env.reset(seed=0, options={"episode": 0, "full": True})
        s, done = 0.0, False
        while not done:
            _, r, terminated, truncated, _ = env.step(np.array([w], np.float32)); s += r
            done = terminated or truncated
        tot[w] = s
    assert tot[1.0] > tot[0.0] + 1.0          # the listening estimate is better than Rev H here


def test_policy_weights_and_residual_are_causal():
    ep = _episode(T=1200)
    ep2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in ep.items()}
    for k in ("X", "D", "dh", "ratio", "amp", "gate"):
        ep2[k][800:] *= 3.0
    pf = lambda o: np.array([np.tanh(o[0] + o[4])], np.float32)            # noqa: E731
    w1, w2 = RE.policy_weights(pf, ep), RE.policy_weights(pf, ep2)
    assert np.allclose(w1[:800], w2[:800])
    pr = lambda o: np.tanh(o[:2] * 0.1)                                      # noqa: E731
    a1, a2 = RE.residual_actions(pr, ep), RE.residual_actions(pr, ep2)
    assert np.allclose(a1[:800], a2[:800])


# ------------------------------------------------------------------ task 5: sigma-lognormal recovery
def test_sigma_lognormal_recovery():
    t = np.arange(0, 1.2, 1 / SY.FS)
    P = np.array([[0.004, 0.00, -1.6, 0.30, 0.2, 1.0], [0.006, 0.25, -1.5, 0.25, 1.5, 2.6], [0.005, 0.55, -1.7, 0.30, 3.0, 4.0]])
    xy = SY.trajectory(t, P, np.zeros(2))
    r = SY.extract(t, xy)
    assert r["snr_db"] > 25.0
    xy_hat = SY.trajectory(t, r["P"], r["start"])
    assert np.sqrt(np.mean(np.sum((xy_hat - xy) ** 2, axis=1))) < 0.2e-3


# ------------------------------------------------------------------ task 6: assistance as needed
def test_aan_gain_law():
    pol = {"kind": "aan", "f": 0.8, "kappa": 4.0, "e_tol": 0.10, "g_max": 1.0, "g0": 0.5}
    e = np.array([0.05] * 10 + [0.4] * 3 + [0.05] * 10)
    g = SH.gain_schedule(pol, e)
    assert np.all((g >= 0) & (g <= 1.0))
    assert g[9] < 0.1                              # fades while the writer is within tolerance
    assert g[12] > 0.9                             # rises after errors above tolerance (next letters)
    assert g[10] < 0.1                             # letter 10's gain does not use letter 10's own error (causal)
    assert g[-1] < 0.2                             # hands control back again
    fixed = SH.gain_schedule({"kind": "fixed", "g": 0.5}, e)
    assert np.all(fixed == 0.5)


# ------------------------------------------------------------------ evidence rows
def test_evidence_rows_header_and_ids():
    hdr = EV.header()
    assert len(hdr) == 23
    rows = EV.literature() + EV.derived({})
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    allowed = {("EML", a) for a in range(44, 70)} | {("PDT", a) for a in range(43, 53)} | {("CON", a) for a in range(46, 53)} | \
              {("HAP", a) for a in range(90, 95)}
    for i in ids:
        s, n = i.split("-")
        assert (s, int(n)) in allowed, i
    for r in rows:
        assert set(r) == set(hdr)
        assert r["access_level"] in ("full text", "abstract only", "full text (PMC)")


# ------------------------------------------------------------------ outputs (only when the study has been run)
def test_output_files_schema():
    p = RESULTS_DIR / "ai2.json"
    if not p.exists():
        pytest.skip("results/ai2 not built yet")
    doc = json.loads(p.read_text())
    for k in ("evidence_status", "git_revision", "parameters_version", "seeds", "generated_utc"):
        assert k in doc["meta"]
    s = json.loads((RESULTS_DIR / "samples.json").read_text())
    assert s["panels"] and all({"id", "title", "intended", "ink", "metrics", "evidence"} <= set(pn) for pn in s["panels"])
    with open(RESULTS_DIR / "evidence_rows.csv", newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == EV.header()
    for png in RESULTS_DIR.glob("fig_*.png"):
        assert png.with_suffix(".csv").exists(), png.name
