"""Fast tests of the fusion package (python3 -m pytest -q fusion/tests).  SIMULATION tooling only."""
from __future__ import annotations

import csv
import math
import os

import numpy as np
import pytest

import fusion
from fusion import context as CX
from fusion import data as FD
from fusion import estimators as ES
from fusion import parts as PT
from fusion import sensors as S


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module")
def short_pair():
    """A 1.5 s scenario pair (tremor 8 Hz, 0.3 mm) on the nominal pen: (tremor record, clean record)."""
    spec = FD.nominal_spec(4242, 8.0, 0.3e-3, duration=1.5)
    return FD.pair_records(spec, use_cache=False)


def _synthetic_streams(f0=8.0, amp=0.3e-3, dur=3.0, seed=1):
    rng = np.random.default_rng(seed)
    fs = 20000.0
    t = np.arange(0, dur, 1 / fs)
    tr = np.column_stack([amp * np.cos(2 * np.pi * f0 * t), 0.4 * amp * np.sin(2 * np.pi * f0 * t)]) * np.clip(t / 0.3, 0, 1)[:, None]
    it = np.column_stack([0.004 * np.sin(2 * np.pi * 1.5 * t), 0.002 * np.sin(2 * np.pi * 2.3 * t + 0.3)])
    p = tr + it
    a = np.gradient(np.gradient(p, 1 / fs, axis=0), 1 / fs, axis=0)
    ta = np.arange(0, dur, 1 / 3840.0)
    acc = np.column_stack([np.interp(ta - 1.04e-3, t, a[:, j]) for j in range(2)]) + rng.standard_normal((len(ta), 2)) * 0.02
    tp = np.arange(0.0003, dur, 1e-3)
    pos = np.column_stack([np.interp(tp, t, p[:, j]) for j in range(2)]) + rng.standard_normal((len(tp), 2)) * 3e-6
    tick = np.arange(0, dur, 0.5e-3)
    st = S.Streams(tick_t=tick, acc_t=ta, acc_av=ta + 0.35e-3, acc=acc, pos_t=tp, pos_av=tp + 2e-3, pos=pos,
                   pos_ok=np.ones(len(tp)), con_t=tp, con_av=tp + 1e-3, con=np.ones(len(tp)), meta={"page_latency": 2e-3})
    truth = np.column_stack([np.interp(tick, t, tr[:, j]) for j in range(2)])
    return st, truth


# ------------------------------------------------------------------ data
def test_fast_handwriting_equals_reference():
    from stabpen import signals as sg
    a = sg.lognormal_handwriting(25e-6, 2.0, np.random.default_rng(3))
    b = FD.fast_lognormal_handwriting(25e-6, 2.0, np.random.default_rng(3))
    assert np.max(np.abs(a.xy - b.xy)) < 1e-12
    assert np.array_equal(a.pen_down, b.pen_down)


def test_test_scenario_is_harness_scenario():
    from sim.pensim import scenarios
    from stabpen import signals as sg
    a = FD.test_scenario(77, 6.0, 0.3e-3, duration=1.2)
    b = scenarios.handwriting(seed=77, duration=1.2, tremor=sg.TremorSpec(f0=6.0, amp_pk=0.3e-3), N0=1.0)
    for k in ("pref", "vref", "fpush", "dtrue", "intended"):
        assert np.array_equal(getattr(a, k), getattr(b, k)), k


def test_seed_plan_is_disjoint_from_test_seeds():
    from fusion import learned as L
    from fusion import tune as TU
    test = set(fusion.TEST_SEEDS) | {s + 1000 for s in fusion.TEST_SEEDS}
    used = set(fusion.TUNE_SEEDS) | set(fusion.VAL_SEEDS) | set(range(fusion.TRAIN_SEEDS_BASE, fusion.TRAIN_SEEDS_BASE + 1000))
    used |= {s + 100 for s in fusion.VAL_SEEDS}
    used |= {L._spec(i, "train").seed for i in range(0, 1000, 3)} | {L._spec(i, "val").seed for i in range(24)}
    used |= {s + 1000 for s in used}
    assert not (test & used)
    assert not (set(fusion.AIGUIDE_TUNE_WRITERS) & set(range(6)))
    assert {w for w, _ in TU.AI_TUNE} <= set(fusion.AIGUIDE_TUNE_WRITERS)
    # glyph training writers: style / writer seeds never those of the aiguide writers (0-5 test, 100-105 tuning)
    glyph = [L._spec(i, "train").seed for i in range(0, 1000, 3) if (i % 10) in L.GLYPH_EVERY]
    assert min(glyph) + 555 > 1000 and min(glyph) + 20000 > 1000


# ------------------------------------------------------------------ sensors
def test_streams_are_causal_and_consistent(short_pair):
    r1, _ = short_pair
    st = S.make_streams(r1, S.config(page="120"), 5)
    assert np.all(st.acc_av >= st.acc_t) and np.all(np.diff(st.acc_av) > 0)
    assert np.all(st.pos_av - st.pos_t == pytest.approx(10e-3))
    assert np.all(np.diff(st.tick_t) == pytest.approx(0.5e-3))
    assert st.acc.shape == (len(st.acc_t), 2)
    assert set(np.unique(st.pos_ok)) <= {0.0, 1.0}


def test_compensation_options(short_pair):
    """No rotation: every option reports the nib acceleration; with rotation the gyroscope removes most of the error."""
    from scipy.signal import butter, sosfiltfilt
    r1, _ = short_pair

    def err(comp, rho):
        cfg = S.config(comp=comp, rho_t=rho, rho_w=rho)
        t_a = np.arange(0.0, r1.t[-1], 1 / cfg.acc.odr)
        est, tru = S.nib_acceleration(r1, cfg, np.random.default_rng(1), t_a, return_truth=True)
        sos = butter(4, [3, 15], btype="band", fs=cfg.acc.odr, output="sos")
        m = t_a > 0.4
        e = sosfiltfilt(sos, est[:, :2] - tru[:, :2], axis=0)[m]
        return float(np.sqrt(np.mean(e ** 2)) / np.sqrt(np.mean(sosfiltfilt(sos, tru[:, :2], axis=0)[m] ** 2)))
    assert err("none", 0.0) < 0.1
    assert err("none", 0.5) > 0.3
    assert err("gyro", 0.5) < 0.2 * err("none", 0.5)
    assert err("dual", 0.5) < 0.5 * err("none", 0.5)


def test_expand_to_steps():
    d = np.arange(10.0).reshape(5, 2)
    e = S.expand_to_steps(d, 97, 20)
    assert e.shape == (97, 2) and e[0, 0] == 0.0 and e[20, 0] == 2.0 and e[96, 1] == 9.0


def test_parts_snr_arithmetic():
    p = PT.PARTS["LSM6DSV16X"]
    assert p.acc_nd() == pytest.approx(60e-6 * 9.80665)
    # a 0.1 mm line at 6 Hz: A w^2 / sqrt 2 / (n sqrt 1 Hz)
    assert PT.tremor_snr(p.acc_nd(), 0.1e-3, 6.0) == pytest.approx(0.1e-3 * (2 * math.pi * 6) ** 2 / math.sqrt(2) / p.acc_nd())
    assert PT.crossover_hz(p.acc_nd(), 3e-6, 1000.0) > 0


# ------------------------------------------------------------------ estimators
def test_kf_step_is_the_core_copy():
    from sim.pencil import core
    rng = np.random.default_rng(0)
    for _ in range(5):
        x = rng.normal(size=5) * 1e-4; P = np.eye(5) * 1e-6
        x2, P2 = x.copy(), P.copy()
        a = ES._kf_step(x, P, 1e-4, 5e-4, 40.0, 0.999, 0.1, 1e-8, 2.5e-11)
        b = core._kf_step.py_func(x2, P2, 1e-4, 5e-4, 40.0, 0.999, 0.1, 1e-8, 2.5e-11)
        assert np.allclose(x, x2) and np.allclose(P, P2) and np.allclose(a, b)


@pytest.mark.parametrize("name,params", [("akf", {"qj": 0.1, "qt": 1e-8, "tau_decay": 0.5, "rp": 2.5e-11, "ra": 3e-3, "harm": 0.0}),
                                         ("wflc", {}), ("bmflc", {}), ("kfosc", {"f_gate": 0.0})])
def test_estimators_are_causal(name, params):
    """Changing sensor samples that become available after T must not change any output at ticks before T."""
    st, _ = _synthetic_streams(dur=1.5)
    a, _ = ES.run_estimator(name, st, params)
    T = 0.9
    st2, _ = _synthetic_streams(dur=1.5)
    st2.acc = st2.acc.copy(); st2.pos = st2.pos.copy()
    st2.acc[st2.acc_av > T] += 5.0
    st2.pos[st2.pos_av > T] += 1e-3
    b, _ = ES.run_estimator(name, st2, params)
    k = st.tick_t < T
    assert np.array_equal(a[k], b[k])
    assert not np.array_equal(a[~k], b[~k])


def test_learned_estimator_is_causal():
    """The GRU path (features, network, output low-pass) with a small random network: no output before T may change
    when samples that become available after T change."""
    torch = pytest.importorskip("torch")
    from fusion import learned as L
    torch.manual_seed(0)
    m = L.build_model(8)
    torch.nn.init.normal_(m.head.weight, std=0.5)
    m.eval()
    L._MODELS["_tiny_test"] = (m, {"net_hz": 1000.0, "out_scale": 100e-6, "lp_hz": 60.0, "hidden": 8})
    st, _ = _synthetic_streams(dur=1.5)
    a, _ = L.estimate(st, {"model": "_tiny_test"})
    st2, _ = _synthetic_streams(dur=1.5)
    st2.acc = st2.acc.copy(); st2.pos = st2.pos.copy()
    T = 0.9
    st2.acc[st2.acc_av > T] += 5.0
    st2.pos[st2.pos_av > T] += 1e-3
    b, _ = L.estimate(st2, {"model": "_tiny_test"})
    k = st.tick_t < T
    assert np.array_equal(a[k], b[k])
    assert not np.array_equal(a[~k], b[~k])
    L._MODELS.pop("_tiny_test")


def test_akf_tracks_a_sinusoid_with_the_accelerometer():
    st, truth = _synthetic_streams(f0=9.0)
    prm = {"qj": 0.1, "qt": 1e-8, "tau_decay": 0.5, "rp": 2.5e-11, "ra": 1e-2, "harm": 0.0, "horizon": 0.0, "lp_hz": 0.0}
    d, info = ES.akf(st, prm)
    m = st.tick_t > 1.5
    rr = np.sqrt(np.sum((d[m] - truth[m]) ** 2) / np.sum(truth[m] ** 2))
    assert rr < 0.15
    assert abs(np.median(info["f_est"][m]) - 9.0) < 0.3


def test_wflc_converges_to_the_tremor_frequency():
    st, _ = _synthetic_streams(f0=11.0, dur=3.0)
    st.acc = st.acc.copy()
    _, info = ES.flc(st, {"mu": 0.002, "mu0": 0.02, "harm": 1.0}, mode="wflc")
    assert abs(np.median(info["f_est"][st.tick_t > 2.0]) - 11.0) < 0.5


def test_output_lowpass_is_unity_at_dc():
    b, a = ES._lp2_coef(60.0, 0.5e-3)
    assert (b.sum() / a.sum()) == pytest.approx(1.0)
    assert ES._lp2_delay(60.0) == pytest.approx(math.sqrt(2) / (2 * math.pi * 60.0))


# ------------------------------------------------------------------ context estimator
@pytest.mark.parametrize("opts", [{}, {"xtrack": 1.0, "v_xt": 4e-3}, {"cap_k": 1.5, "v_slow": 8e-3, "tau_ref": 0.3}])
def test_context_without_template_equals_akf(opts):
    st, _ = _synthetic_streams(dur=1.5)
    prm = dict({"qj": 0.1, "qt": 1e-8, "tau_decay": 0.5, "rp": 2.5e-11, "ra": 3e-3, "harm": 1.0, "qh": 1e-9}, **opts)
    a, _ = ES.akf(st, prm)
    b, _ = CX.estimate(st, prm, None)
    assert np.max(np.abs(a - b)) < 1e-12
    assert np.max(np.abs(a)) > 1e-6


def test_amplitude_cap_blocks_output_without_slow_motion_tremor():
    """No tremor while the pen is slow: the cap keeps the output at zero whatever the filter believes during fast motion."""
    st, _ = _synthetic_streams(f0=9.0, amp=0.0)
    prm = {"qj": 1e-3, "qt": 1e-8, "tau_decay": 0.5, "rp": 2.5e-11, "ra": 1e-2, "harm": 0.0, "lp_hz": 0.0}
    free, _ = ES.akf(st, prm)                                  # a stiff intent model misreads the writing as tremor
    capped, _ = ES.akf(st, dict(prm, cap_k=1.0, v_slow=1e-4, tau_ref=0.3))
    m = st.tick_t > 0.5
    assert np.max(np.abs(free[m])) > 5e-6
    assert np.max(np.abs(capped[m])) < 0.02 * np.max(np.abs(free[m]))


def test_template_arrays_geometry():
    from aiguide.template import LetterTemplate
    L = LetterTemplate("o", [np.array([[0, 0], [1e-3, 0], [1e-3, 1e-3]], float)], 1.0)
    tp = CX.template_arrays([L], [0.7])
    assert len(tp["xy"]) > 50
    assert np.allclose(np.linalg.norm(tp["nrm"], axis=1), 1.0)
    tg = np.gradient(tp["xy"], axis=0)
    assert np.max(np.abs(np.sum(tg * tp["nrm"], axis=1))) < 1e-9 + 1e-3 * np.max(np.abs(tg))
    assert np.all(tp["conf"] == 0.7)


def test_context_template_prior_helps_and_wrong_template_is_bounded():
    """Intent that is exactly the template: the prior must not make the tremor estimate worse; a template far from
    the path is gated/dropped, so the estimate stays close to the no-template one."""
    from aiguide.template import LetterTemplate
    st, truth = _synthetic_streams(f0=5.0, dur=3.0)
    fs = 20000.0
    t = np.arange(0, 3.0, 1 / fs)
    it = np.column_stack([0.004 * np.sin(2 * np.pi * 1.5 * t), 0.002 * np.sin(2 * np.pi * 2.3 * t + 0.3)])
    good = LetterTemplate("x", [it[::20]], 1.0)
    bad = LetterTemplate("x", [it[::20] + np.array([2e-3, -2e-3])], 1.0)
    prm = {"qj": 0.1, "qt": 1e-8, "tau_decay": 0.5, "rp": 2.5e-11, "ra": 3e-3, "harm": 0.0, "horizon": 0.0, "lp_hz": 0.0,
           "sigma_t": 30e-6, "t_rate": 250.0, "win_fwd": 400.0, "win_reacq": 20000.0, "tb0": 100e-6}
    m = st.tick_t > 1.5

    def rr(tpl):
        d, info = CX.estimate(st, prm, {"template": None if tpl is None else CX.template_arrays([tpl], [1.0])})
        return np.sqrt(np.sum((d[m] - truth[m]) ** 2) / np.sum(truth[m] ** 2)), info
    r0, _ = rr(None)
    r1, i1 = rr(good)
    r2, i2 = rr(bad)
    assert i1["template_updates"] > 100
    assert r1 < r0
    assert r2 < r0 + 0.1


# ------------------------------------------------------------------ personalisation
def test_calibration_label_recovers_the_tremor_without_timing():
    """The phone's calibration analysis on a synthetic tracing of the known shapes (timing jittered, an offset, a
    direction-dependent lag and an 8 Hz elliptical tremor): frequency within 0.4 Hz, label close to the tremor."""
    from fusion import personal as PS
    it = PS.calibration_path(dt=1e-3)
    t = it.t
    rng = np.random.default_rng(3)
    # the writer's progress runs 5 % slow with a slow wobble: the phone does not know it
    u = np.clip(t * 0.95 + 0.02 * np.sin(2 * np.pi * 0.3 * t), 0, t[-1])
    xy = np.column_stack([np.interp(u, t, it.xy[:, 0]), np.interp(u, t, it.xy[:, 1])])
    down = np.interp(u, t, it.pen_down.astype(float)) > 0.5
    v = np.gradient(xy, t, axis=0)
    lag = -0.3 * v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-3) * np.minimum(1.0, np.linalg.norm(v, axis=1, keepdims=True) / 2e-3) * 1e-4
    ph = 2 * np.pi * 8.0 * t
    trem = np.column_stack([120e-6 * np.cos(ph), 50e-6 * np.sin(ph)])
    pos = xy + lag + trem + np.array([3e-4, -2e-4]) + rng.standard_normal(xy.shape) * 3e-6
    st = S.Streams(tick_t=np.arange(0, t[-1], 0.5e-3), acc_t=t, acc_av=t, acc=np.zeros_like(pos), pos_t=t, pos_av=t + 2e-3,
                   pos=pos, pos_ok=np.ones(len(t)), con_t=t, con_av=t, con=down.astype(float), meta={"page_rate": 1000.0})
    pl = PS.page_label(st, it.xy[it.pen_down])
    est = PS.tremor_from_calibration(pl)
    assert abs(est["f_hat_hz"] - 8.0) < 0.4
    assert 60.0 < est["amp_rms_um"] < 140.0          # 2-D RMS of the tremor is 92 um
    m = pl["use"]
    tn = np.sum(trem * pl["normal"], axis=1)
    tb = np.full(len(tn), np.nan)
    from scipy.signal import sosfiltfilt
    for a, b in pl["segments"]:
        tb[a:b] = sosfiltfilt(pl["sos"], tn[a:b] - tn[a:b].mean(), padlen=min(39, b - a - 1))
    err = np.sqrt(np.nanmean((pl["label"][m] - tb[m]) ** 2))
    assert m.sum() > 5000 and err < 0.25 * np.sqrt(np.nanmean(tb[m] ** 2))


# ------------------------------------------------------------------ budget and ledger rows
def test_budget_is_positive():
    from fusion import budget as B
    c = B.estimator_costs()
    for k in ("kfosc", "akf", "context", "bmflc", "wflc", "gru"):
        assert c[k]["cpu_fraction_f32"] > 0


def test_evidence_rows_format():
    p = os.path.join(fusion.RESULTS, "evidence_rows.csv")
    if not os.path.exists(p):
        pytest.skip("results/fusion/evidence_rows.csv not generated yet")
    head = open(os.path.join(fusion.ROOT, "docs", "evidence.csv"), encoding="utf-8").readline().strip().split(",")
    rows = list(csv.reader(open(p, encoding="utf-8")))
    assert rows[0] == head
    allowed = ({f"ACT-{i}" for i in range(40, 50)} | {f"OPT-{i}" for i in range(37, 50)} | {f"EML-{i}" for i in range(31, 40)}
               | {f"PDT-{i}" for i in range(32, 40)})
    ids = [r[0] for r in rows[1:]]
    assert ids and set(ids) <= allowed and len(ids) == len(set(ids))
    assert all(len(r) == len(head) for r in rows[1:])
