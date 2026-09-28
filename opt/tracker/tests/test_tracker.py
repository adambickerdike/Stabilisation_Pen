"""Fast tests of opt.tracker (python3 -m pytest -q opt/tracker/tests).  SIMULATION tooling only.

torch AKF == numba AKF (fusion.estimators.akf) on the same streams; the numba discrete adjoint == PyTorch autograd;
finite differences == adjoint; causality of every tracker; the seed plan never touches the test data.
"""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest
import torch

import opt.tracker as OT
from opt.tracker import adjoint as AD
from opt.tracker import data as DA
from opt.tracker import losses as LS
from opt.tracker import schedule as SCH
from opt.tracker import torch_akf as TA

from fusion import data as FD
from fusion import estimators as ES
from fusion import sensors as S

torch.set_num_threads(1)

SETS = {
    # grid-tuned-like: 2nd harmonic, frequency and amplitude gates, low output low-pass
    "grid_like": {"qj": 0.0221, "qt": 1.81e-9, "qh": 4.4e-11, "qb": 3.9e-9, "ra": 0.0515, "rp": 5.75e-12, "tau_decay": 0.466,
                  "tau_w": 0.157, "wmin_hz": 3.1, "horizon": 1.6e-4, "g": 0.9, "tau_amp": 0.254, "harm": 1.0, "f_gate": 6.04,
                  "f_gate_w": 2.2, "a_lo": 4.2e-5, "a_hi": 1.7e-4, "lp_hz": 20.6},
    # robust-like: no harmonic, slow-motion amplitude cap
    "robust_like": {"qj": 0.0173, "qt": 1.56e-10, "qh": 3.5e-11, "qb": 4.1e-6, "ra": 0.0721, "rp": 5.3e-10, "tau_decay": 0.153,
                    "tau_w": 0.302, "wmin_hz": 3.79, "horizon": 9.3e-4, "g": 1.14, "tau_amp": 1.05, "harm": 0.0, "lp_hz": 56.5,
                    "f_gate": 6.3, "f_gate_w": 2.05, "a_lo": 5.5e-6, "a_hi": 1.64e-4, "cap_k": 3.0, "v_slow": 9.8e-3, "tau_ref": 0.556},
}


@pytest.fixture(scope="module")
def pair():
    """1.5 s P1 pair (8 Hz, 0.3 mm tremor) on the nominal pen: sigma-lognormal writing with pen lifts."""
    spec = FD.nominal_spec(4243, 8.0, 0.3e-3, duration=1.5)
    return FD.pair_records(spec, use_cache=False)


def _streams(rec, n, page="1k", seed=11):
    return [S.make_streams(rec, S.config(page=page), seed + i) for i in range(n)]


def _rel(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)) / max(np.sqrt(np.mean(b ** 2)), 1e-30))


# ------------------------------------------------------------------ agreement with the numba AKF
@pytest.mark.parametrize("name,page", [("grid_like", "1k"), ("robust_like", "1k"), ("grid_like", "120")])
def test_torch_akf_reproduces_numba(pair, name, page):
    r1, _ = pair
    p = SETS[name]
    sts = _streams(r1, 2, page)
    out, parts = TA.run_numba_equivalent(sts, p)
    for b, st in enumerate(sts):
        ref, info = ES.akf(st, p)
        assert np.max(np.abs(ref)) > 1e-7
        assert _rel(out[b].numpy(), ref) < 1e-9           # the requirement is < 1 % RMS
        assert np.max(np.abs(parts["f_est"][b].numpy() - info["f_est"])) < 1e-8
        assert np.max(np.abs(parts["authority"][b].numpy() - info["authority"])) < 1e-9


@pytest.mark.parametrize("name,page", [("grid_like", "1k"), ("robust_like", "120")])
def test_adjoint_core_reproduces_numba(pair, name, page):
    r1, _ = pair
    p = SETS[name]
    sts = _streams(r1, 3, page, seed=31)
    sch = [SCH.build(s) for s in sts]
    ev = TA.EventBatch.from_schedules(sch)
    pk = AD.Packed(sch)
    with torch.no_grad():
        out = AD.forward(pk, ev, TA.numba_to_values(p), TA.static_of(p))
    for b, st in enumerate(sts):
        assert _rel(out[b].numpy(), ES.akf(st, p)[0]) < 1e-9


def test_trained_values_round_trip():
    """TRAIN_KEYS values -> numba dict -> the same filter (a_c/a_w become a_lo/a_hi)."""
    p = SETS["robust_like"]
    v = TA.trainable_start(p)
    q = TA.to_numba(v, TA.static_of(p))
    for k in ("qj", "qt", "ra", "rp", "tau_decay", "g", "lp_hz", "cap_k", "v_slow", "tau_ref", "f_gate", "f_gate_w"):
        assert q[k] == pytest.approx(p[k], rel=1e-12)
    assert q["a_lo"] == pytest.approx(p["a_lo"], rel=1e-9) and q["a_hi"] == pytest.approx(p["a_hi"], rel=1e-9)


# ------------------------------------------------------------------ gradients
def _short_set(pair, n=2, ticks=900, keep=False):
    r1, r0 = pair
    items = []
    for i in range(n):
        for rec, clean in ((r1, False), (r0, True)):
            st = S.make_streams(rec, S.config(), 41 + 2 * i + int(clean))
            st.tick_t = st.tick_t[:ticks]
            d = np.zeros((ticks, 2)) if clean else S.truth_at(st.tick_t, r1, r0)
            m = (np.interp(st.tick_t, rec.t, rec.contact) > 0.5) & (st.tick_t > 0.2)
            items.append({"st": st, "d": d, "m": m, "clean": clean, "glyph": bool(i % 2), "meta": {}})
    return DA.build_set(items, full_events=True, keep_streams=keep)


def test_adjoint_gradient_equals_autograd(pair):
    rs = _short_set(pair)
    p = SETS["grid_like"]
    static = TA.static_of(p)
    start = TA.trainable_start(p)
    lcfg = LS.LossCfg(lam_fc=0.5)
    th1 = TA.to_theta(start).requires_grad_(True)
    J1, _, _, _ = DA.evaluate(rs, TA.from_theta(th1), static, ("leaky", 0.1), lcfg, grad=True)
    J1.backward()
    th2 = TA.to_theta(start).requires_grad_(True)
    dh = TA.forward(rs.ev, TA.from_theta(th2), static, gate_beta=("leaky", 0.1), chunk=None)
    t = LS.terms(dh, rs.d, rs.db, rs.m, rs.clean)
    J2, _ = LS.objective(t, rs.clean, rs.glyph, lcfg)
    J2.backward()
    assert float(J1.detach()) == pytest.approx(float(J2.detach()), rel=1e-10)
    g1, g2 = th1.grad.numpy(), th2.grad.numpy()
    scale = np.max(np.abs(g2))
    assert scale > 0
    assert np.max(np.abs(g1 - g2)) < 1e-7 * scale


def test_gradient_matches_finite_differences(pair):
    rs = _short_set(pair, n=1, ticks=1400)
    p = SETS["robust_like"]
    static = TA.static_of(p)
    th = TA.to_theta(TA.trainable_start(p)).requires_grad_(True)
    lcfg = LS.LossCfg(lam_fc=0.5)
    J, _, _, _ = DA.evaluate(rs, TA.from_theta(th), static, None, lcfg, grad=True)
    J.backward()
    for k in ("qt", "tau_decay", "g", "lp_hz", "horizon"):
        i = TA.TRAIN_KEYS.index(k)
        h = 1e-4
        tp = th.detach().clone(); tp[i] += h
        tm = th.detach().clone(); tm[i] -= h
        Jp = float(DA.evaluate(rs, TA.from_theta(tp), static, None, lcfg)[0])
        Jm = float(DA.evaluate(rs, TA.from_theta(tm), static, None, lcfg)[0])
        fd = (Jp - Jm) / (2 * h)
        g = float(th.grad[i])
        assert abs(fd - g) <= 2e-3 * max(abs(g), 1e-6) + 1e-9, (k, fd, g)


# ------------------------------------------------------------------ causality
def _perturbed(st, T):
    s2 = copy.copy(st)
    s2.acc = st.acc.copy(); s2.pos = st.pos.copy()
    s2.acc[st.acc_av > T] += 5.0
    s2.pos[st.pos_av > T] += 1e-3
    return s2


def test_torch_and_adjoint_trackers_are_causal(pair):
    r1, _ = pair
    p = SETS["grid_like"]
    st = _streams(r1, 1)[0]
    T = 0.9
    s2 = _perturbed(st, T)
    a, _ = TA.run_numba_equivalent([st], p)
    b, _ = TA.run_numba_equivalent([s2], p)
    a, b = a[0].numpy(), b[0].numpy()
    k = st.tick_t < T
    # the output low-pass is an FFT convolution: causal up to floating-point rounding (1e-16 of the signal)
    assert np.max(np.abs(a[k] - b[k])) < 1e-12 * np.max(np.abs(a))
    assert np.max(np.abs(a[~k] - b[~k])) > 1e-9
    sch = [SCH.build(st), SCH.build(s2)]
    with torch.no_grad():
        o = AD.forward(AD.Packed(sch), DA.light_events(sch), TA.numba_to_values(p), TA.static_of(p)).numpy()
    # the FFT convolution of the output low-pass rounds at 1e-16: causality holds to rounding
    assert np.max(np.abs(o[0][k] - o[1][k])) < 1e-12 * np.max(np.abs(o[0]))
    assert np.max(np.abs(o[0][~k] - o[1][~k])) > 1e-9


@pytest.mark.parametrize("kind", ["gru", "hybrid"])
def test_learned_trackers_are_causal(pair, kind):
    from opt.tracker import learned as LN
    r1, _ = pair
    st = _streams(r1, 1)[0]
    torch.manual_seed(0)
    n_in = LN.N_IN_GRU if kind == "gru" else LN.N_IN_GATE
    m = LN.GRUTracker(n_in, 8, 2 if kind == "gru" else 1, gate=kind == "hybrid")
    torch.nn.init.normal_(m.head.weight, std=0.5)
    m.eval()
    name = f"_test_{kind}"
    LN._MODELS[name] = (m, {"kind": kind, "out_scale": LN.OUT_S, "lp_hz": 60.0, "akf_params": SETS["robust_like"]})
    try:
        T = 0.9
        a, _ = LN.estimate(name, st)
        b, _ = LN.estimate(name, _perturbed(st, T))
        k = st.tick_t < T
        assert np.max(np.abs(a[k] - b[k])) < 1e-12 * max(np.max(np.abs(a)), 1e-12)
        assert np.max(np.abs(a[~k] - b[~k])) > 1e-12
    finally:
        LN._MODELS.pop(name)


# ------------------------------------------------------------------ building blocks
def test_sosfiltfilt_operator_is_scipys():
    from scipy.signal import butter, sosfiltfilt
    from opt.tracker.personal import SosFiltFilt
    sos = butter(4, [3.0, 15.0], btype="band", fs=1000.0, output="sos")
    op = SosFiltFilt(sos, 3000)
    rng = np.random.default_rng(0)
    for n in (60, 400, 2500):
        x = rng.standard_normal(n)
        pl = min(39, n - 1)
        ref = sosfiltfilt(sos, x, padlen=pl)
        got = op(torch.as_tensor(x, dtype=torch.float64), pl).numpy()
        assert np.max(np.abs(got - ref)) < 1e-9 * np.max(np.abs(ref))


def test_lowpass_impulse_response_is_fusions():
    from scipy.signal import lfilter
    b, a = ES._lp2_coef(37.0, 0.5e-3)
    imp = np.zeros(400); imp[0] = 1.0
    ref = lfilter(b, a, imp)
    got = TA.lp2_ir(torch.tensor([37.0], dtype=torch.float64), 0.5e-3, 400)[0].numpy()
    assert np.max(np.abs(got - ref)) < 1e-12


# ------------------------------------------------------------------ seed plan
def test_seed_plan_never_uses_test_data():
    from fusion import learned as FL
    test = set(OT.TEST_SEEDS) | {s + 1000 for s in OT.TEST_SEEDS}
    train = {FL._spec(i, "train").seed for i in range(OT.TRAIN_PAIRS)}
    val = {FL._spec(j, "val").seed for j in range(OT.VAL_PAIRS)}
    used = train | val | set(OT.TUNE_SEEDS)
    assert not (used & test) and not ({s + 1000 for s in used} & test)
    assert not (set(OT.AIGUIDE_TUNE_WRITERS) & set(OT.AIGUIDE_TEST_WRITERS))
    # glyph training writers: style / writer seeds (seed + 555, + 20000) never an aiguide writer seed (0-5, 100-105)
    glyph = [FL._spec(i, "train").seed for i in range(OT.TRAIN_PAIRS) if FL._spec(i, "train").writer == "glyph"]
    assert min(glyph) + 555 > 105
    # the training / validation sets of this package are built from exactly these specs and the tuning seeds
    assert set(DA.train_indices(96, 64)) <= set(range(OT.TRAIN_PAIRS))
    assert sum((i % 10) in FL.GLYPH_EVERY for i in DA.train_indices(96, 64)) / len(DA.train_indices(96, 64)) >= 0.3
    # personal calibration: test seed + 40000 (never the test recording's own seeds)
    assert all(s + OT.CALIB_SEED_OFFSET not in test for s in OT.TEST_SEEDS)


def test_realdata_compensation_is_fusions_gyro_option(pair):
    """Raw body-frame IMU readings -> page-frame nib acceleration exactly as fusion.sensors' 'gyro' option."""
    import math as _m
    from opt.tracker import realdata as RD
    r1, _ = pair
    cfg = S.config(page="1k", comp="gyro")
    t_a = np.arange(0.0, r1.t[-1], 1.0 / cfg.acc.odr)
    ref = S.nib_acceleration(r1, cfg, np.random.default_rng(5), t_a)
    rng = np.random.default_rng(5)
    sig = S.body_signals(r1, cfg)
    fb = S._accel_readings(sig["board"], r1.t, t_a, cfg.acc, rng)
    wb = S._gyro_readings(sig["rate"], r1.t, t_a, cfg.gyro, cfg.acc.odr, rng)
    got = RD.compensate(t_a, fb, wb, _m.degrees(r1.theta), _m.degrees(r1.phi), cfg.r_board, odr=cfg.acc.odr,
                        rho_deg=_m.degrees(r1.rho))
    assert np.max(np.abs(got - ref)) < 1e-9 * np.max(np.abs(ref))
