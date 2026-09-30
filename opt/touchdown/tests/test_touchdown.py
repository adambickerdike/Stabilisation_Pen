"""Fast tests of opt/touchdown (about 30 s).  They verify code and kinematics, not physics: passing them does not
validate the pencil model against hardware.  Run: python3 -m pytest -q opt/touchdown/tests"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import sim.pencil  # noqa: E402,F401
from sim.pencil import model as M  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

from opt.touchdown import bo, law as L, metrics as MT, runs, servo as S  # noqa: E402

D2R = math.pi / 180
NOISE_OFF = {"hall_noise": 0.0, "sensing.axial_noise": 0.0}


# ---------------------------------------------------------------- kinematics (CALC)
@pytest.mark.parametrize("theta", [35.0, 50.0, 75.0])
def test_kinematic_law_holds_ink_and_air_fixed_point(theta):
    th = theta * D2R
    s_ref, margin = 5e-6, 0.3e-3
    # ball on the page: any housing height h, stage from the law -> ink at its working position
    for h in (0.0, 0.1e-3, 0.3e-3):
        s_h = -h / math.sin(th)
        q = math.sin(th) * math.cos(th) * (s_ref - s_h)
        s = L.slide(h, q, th)
        assert L.ink_shift(h, q, th) == pytest.approx(s_ref * math.cos(th), abs=1e-12)
        assert q * math.sin(th) + s * math.cos(th) == pytest.approx(s_ref * math.cos(th), abs=1e-12)
        # the same law from the measured slide and the Hall reading, with the stage-induced slide removed
        qv = L.q_ff_ideal(s, [q, 0.0], th, s_ref=s_ref)
        assert qv[0] == pytest.approx(q, abs=1e-12) and qv[1] == 0.0
    # refill on its stop: the formula's fixed point is the pre-position, and the iteration converges (gain cos^2)
    q = 0.0
    for _ in range(200):
        q = L.q_ff_ideal(-margin, [q, 0.0], th, s_ref=s_ref)[0]
    assert q == pytest.approx(L.q_pre(margin, th, s_ref), rel=1e-9)
    assert L.air_loop_gain(th) == pytest.approx(math.cos(th) ** 2)
    # the pre-positioned ball touches when the housing is (margin + s_ref)/sin(th) + ... above writing height
    hc = L.contact_height(margin, th, pre=1.0, s_ref=s_ref)
    assert L.slide(hc, L.q_pre(margin, th, s_ref), th) == pytest.approx(-margin, abs=1e-12)
    # 0.30 mm margin at 50 deg: 0.25 mm of pre-positioning, not the 0.15 mm (sin cos margin) estimate
    if theta == 50.0:
        assert L.q_pre(0.3e-3, th) == pytest.approx(0.2517e-3, rel=1e-3)


def test_roll_direction_of_the_law():
    th, rho = 50 * D2R, 0.4
    q = L.q_ff_ideal(-0.3e-3, [0.0, 0.0], th, rho=rho, kappa=0.0)
    assert q[0] / q[1] == pytest.approx(-math.cos(rho) / math.sin(rho))


# ---------------------------------------------------------------- the law inside P1
def test_quasi_static_touchdown_holds_the_contact_point():
    """Hand lowering the pen at 1 mm/s, no tremor, ideal gains: the ink point stays within a few um of its
    working position under the housing (the brief's kinematic check), against ~0.2 mm without the feed-forward."""
    sc = runs.quasi_static_touchdown(50.0, v_down=1e-3, t_hold=0.2)
    th = 50 * D2R
    ff = L.TouchdownLaw(margin=0.3e-3, dz=0.0, lead_s=0.0)
    r = M.run(sc, M.Controller(mode="neutral"), ff.pencil_config(overrides=NOISE_OFF, hysteresis=False), seed=1)
    s_ref = r.info["touchdown_ff"]["s_ref"]
    c = r["contact"] > 0
    dev = (r["Cx"] - r["pHx"] - s_ref * math.cos(th))
    d = runs.contact_point_drift(r, s_ref, 50.0)
    assert d["rms_dev_um"] < 8.0
    # while the refill slides (the kinematic part of the law) and at rest on the page
    sliding = c & (r["s"] > -0.28e-3) & (r["s"] < s_ref - 5e-6)
    assert sliding.sum() > 100
    assert np.median(np.abs(dev[sliding])) < 8e-6 and np.max(np.abs(dev[sliding])) < 20e-6
    assert abs(dev[-1]) < 2e-6
    off = M.run(sc, M.Controller(mode="neutral"), L.adaptive_stop(0.3e-3).pencil_config(overrides=NOISE_OFF, hysteresis=False), seed=1)
    assert runs.contact_point_drift(off, s_ref, 50.0)["max_abs_dev_um"] > 150.0


def test_stage_induced_slide_is_removed_during_correction():
    """Pen held on the page while the stage cancels a synthetic 6 Hz disturbance estimate (mode external): the stage
    moves about 0.1 mm, the refill slides cot(th) times that, and the feed-forward's housing-slide estimate stays at
    the working slide, so the feed-forward stays silent (sensor noise on)."""
    sc = scenarios.static_hold(duration=1.2, theta_deg=50.0)
    dhat = np.column_stack([1.5e-4 * np.sin(2 * np.pi * 6.0 * sc.t), np.zeros(len(sc.t))])
    ff = L.TouchdownLaw(margin=0.3e-3, dz=20e-6)
    r = M.run(M.with_estimate(sc, dhat), M.Controller(mode="external"), ff.pencil_config(), seed=2)
    sel = (r["t"] > 0.6) & (r["contact"] > 0)
    assert np.ptp(r["q1"][sel]) > 0.15e-3                          # the stage corrects
    assert np.ptp(r["s"][sel]) > 0.12e-3                           # so the refill slides
    s_ref = r.info["touchdown_ff"]["s_ref"]
    assert np.max(np.abs(r["td_sh"][sel] - s_ref)) < 15e-6         # ... but not the housing-slide estimate
    assert np.max(np.abs(r["qff1"][sel])) < 3e-6                   # so the feed-forward stays silent


def test_default_config_has_no_feedforward():
    sc = scenarios.handwriting(seed=300, duration=0.4)
    Pv, info = M.build_params(sc, M.Controller(mode="neutral"), M.PencilConfig())
    assert Pv[M.IDX["td_on"]] == 0.0 and "touchdown_ff" not in info


# ---------------------------------------------------------------- metrics
def test_ink_metrics_of_a_run_against_itself_are_zero():
    sc = scenarios.handwriting(seed=301, duration=2.2)
    rig = M.run(sc, M.Controller(mode="neutral"), M.PencilConfig(locked=True), seed=302)
    m = MT.ink_vs_rigid(rig, rig, T_end=2.0)
    assert m["extra_mm"] == 0.0 and m["missing_mm"] == 0.0 and m["ink_mm"] > 5.0


# ---------------------------------------------------------------- optimisers
def test_gp_bo_and_cmaes_on_toy_problems():
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 1, (25, 2))
    f = lambda X: np.sum((X - 0.3) ** 2, axis=1)   # noqa: E731
    gp = bo.GP(X, f(X), rng=rng)
    Xt = rng.uniform(0, 1, (50, 2))
    assert np.max(np.abs(gp.predict(Xt, std=False) - f(Xt))) < 0.03
    u, ei = bo.propose(gp, 2, rng, n_rand=500, n_polish=2)
    assert np.linalg.norm(u - 0.3) < 0.2
    xb, fb, _ = bo.cmaes(lambda x: float(np.sum((x - 0.6) ** 2)), np.full(3, 0.2), iters=25, seed=1)
    assert fb < 1e-4
    F = np.array([[1, 2], [2, 1], [1.5, 1.5], [2, 2]])
    assert bo.pareto_mask(F).tolist() == [True, True, True, False]
    sp = bo.Space({"a": (1.0, 100.0), "b": (0.0, 2.0)}, log=("a",))
    x = np.array([10.0, 1.5])
    assert np.allclose(sp.from_unit(sp.to_unit(x)), x)


# ---------------------------------------------------------------- servo margins
def test_loop_margins_reproduce_the_p1_servo_check():
    from sim.pencil.run_study import servo_check
    ref = servo_check()["margins"]["zeta_open_0.05"]
    m = S.loop_margins(**S.DEFAULT, zeta_open=(0.05,), k_scales=(1.0,))
    assert m["pm_min_deg"] == pytest.approx(min(ref["phase_margins_deg"]), abs=0.5)
    assert m["gm_min_db"] == pytest.approx(min(ref["gain_margin_dB"]), abs=0.3)
    assert S.loop_margins(**S.DEFAULT)["feasible_nominal"]
    assert not S.loop_margins(**dict(S.DEFAULT, servo_kp=1.0))["feasible_nominal"]


# ---------------------------------------------------------------- adjoint gradient of the reduced model
def test_reduced_model_adjoint_gradient_matches_finite_differences():
    torch = pytest.importorskip("torch")
    from opt.touchdown import reduced as R
    sc = R.p1_event_scenario(0.0, T=0.1)
    Pv, _ = M.build_params(sc, M.Controller(mode="neutral"), L.TouchdownLaw(margin=0.3e-3).pencil_config())
    model = R.ReducedTouchdown(Pv)
    ev = R.make_events(T=0.1, vx=(0.0,), t_up=1.0)
    law = {"gain": 1.0, "lead_s": 0.8e-3, "k_load": 1.0}
    z = {k: torch.tensor(v, requires_grad=True, dtype=torch.float64) for k, v in law.items()}
    loss = model.simulate(ev, dict(z))["rms_ink"].mean() * 1e6
    loss.backward()
    # the loss of the event-driven model is rough at the scale of a few % of a gain (contact and stop switching), so
    # the check uses a small step: central differences converge to the adjoint value as the step shrinks
    # (gain: -15.8 / -17.0 / -24.3 / -27.9 / -29.1 / -29.3 at steps 0.04 ... 0.001 against -29.34 from the adjoint)
    for k, h in (("gain", 1e-3), ("k_load", 1e-3)):
        vals = []
        for sgn in (1, -1):
            l2 = dict(law); l2[k] += sgn * h
            with torch.no_grad():
                vals.append(float(model.simulate(ev, {kk: torch.tensor(v, dtype=torch.float64) for kk, v in l2.items()})["rms_ink"].mean()) * 1e6)
        fd = (vals[0] - vals[1]) / (2 * h)
        assert float(z[k].grad) == pytest.approx(fd, rel=0.05, abs=0.2)
