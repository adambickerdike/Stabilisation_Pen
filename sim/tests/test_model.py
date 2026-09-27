"""Verification tests for the simulator (model M1).

These check the implementation against independent analytic results.  They
verify code, not physics: passing them does not validate the contact, hand or
actuator models against hardware (see docs/sim_report.md, validation plan).
Run: python3 -m pytest sim/tests -q
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from sim.pensim import bench, evaluate, model, scenarios  # noqa: E402
from sim.pensim.layout import IDX  # noqa: E402
from stabpen import contact, frames  # noqa: E402
from stabpen import signals as sg  # noqa: E402


def test_jacobian_analytic_matches_vector_construction():
    rng = np.random.default_rng(0)
    for _ in range(50):
        th, ph, ro = rng.uniform(0.3, 1.5), rng.uniform(-3, 3), rng.uniform(-3, 3)
        assert np.allclose(frames.jacobian(th, ph, ro), frames.jacobian_numeric(th, ph, ro), atol=1e-12)
        assert np.allclose(frames.jacobian(th, ph, ro) @ frames.inverse_jacobian(th, ph, ro), np.eye(2), atol=1e-12)
        assert math.isclose(abs(np.linalg.det(frames.jacobian(th, ph, ro))), 1 / math.sin(th), rel_tol=1e-12)


def test_transverse_load_limits():
    # upright pen, no friction: no transverse load
    assert contact.transverse_load(1.0, 0.0, 0.0, math.pi / 2) < 1e-12
    # frictionless: |R_perp| = N cos theta
    for th in (0.6, 0.9, 1.2):
        assert math.isclose(contact.transverse_load(1.3, 0.0, 0.4, th), 1.3 * math.cos(th), rel_tol=1e-12)


@pytest.mark.parametrize("theta", [35.0, 55.0, 75.0])
def test_static_contact_load_matches_statics(theta):
    sc = scenarios.static_hold(duration=1.2, theta_deg=theta, N0=1.0)
    r = model.run(sc, model.Controller(mode="neutral"), seed=2)
    sel = r["t"] > 0.9
    n = r.info["reduction"]["n_lever"]
    Kf = r.P[IDX["Kf"]]
    F_tip = -n * Kf * r.xy("i1")[sel].mean(axis=0)
    N = r["N"][sel].mean()
    lam = 1 - r["s"][sel].mean() / r.P[IDX["L1"]]
    R = contact.reaction_components(N, 0.0, 0.0, math.radians(theta))
    # static friction may carry part of the load in stick; allow 10 %
    assert F_tip[0] == pytest.approx(-lam * R["R_x"], rel=0.10)
    assert abs(F_tip[1]) < 0.02


def test_rigid_mode_tip_follows_housing():
    sc = scenarios.handwriting(seed=5, duration=2.0)
    r = model.run(sc, model.Controller(mode="rigid"))
    assert np.max(np.abs(r.xy("tipx") - r.xy("pHx"))) < 1e-12


def test_free_vibration_frequency():
    """Pen in the air, coils open: lever rings at sqrt(k/m_eq)/2pi."""
    dt = 25e-6
    n = int(0.6 / dt)
    t = np.arange(n) * dt
    it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=np.zeros(n, bool), lift=np.full(n, 3e-3), features=[])
    sc = scenarios._assemble(it, np.zeros((n, 2)), 1.0, 50.0)
    sc.fpush[:] = 0.0
    ov = {"q_init": 2e-4, "stage.zeta_open": 0.001, "hand.effective_mass": 5.0}
    r = model.run(sc, model.Controller(mode="unpowered"), overrides=ov)
    q = r["q1"]
    zc = np.flatnonzero((q[:-1] < 0) & (q[1:] >= 0))
    f_meas = (len(zc) - 1) / (r["t"][zc[-1]] - r["t"][zc[0]])
    m_eq = r.info["reduction"]["m_eq"]
    k = r.P[IDX["k_tip"]]
    f_th = math.sqrt(k / m_eq) / (2 * math.pi)
    assert f_meas == pytest.approx(f_th, rel=0.02)


def test_sliding_friction_magnitude():
    """Constant-velocity stroke well above the Stribeck speed: |f| = mu_k N."""
    sc = scenarios.constant_velocity(duration=0.8, speed=0.03, direction_deg=90.0, theta_deg=50.0, N0=1.0)
    r = model.run(sc, model.Controller(mode="neutral"))
    sel = (r["t"] > 0.5) & (r["contact"] > 0)
    f = np.linalg.norm(r.xy("fx")[sel], axis=1)
    mu = r.P[IDX["mu_k"]]
    assert np.median(f / r["N"][sel]) == pytest.approx(mu, rel=0.05)


def test_copper_power_bookkeeping():
    sc = scenarios.static_hold(duration=0.8, theta_deg=40.0, N0=1.2)
    r = model.run(sc, model.Controller(mode="neutral"))
    i = r.xy("i1")
    R = r.P[IDX["R20"]] * (1 + r.P[IDX["alpha_cu"]] * (r.rec[:, [r.rec.shape[1] * 0 + i for i in [
        __import__("sim.pensim.layout", fromlist=["RIDX"]).RIDX["T1"]]]][:, 0] - 20))
    # coil 1 dominates at rho = 0; compare within 2 % using coil-1 temperature for both
    P_est = (i ** 2).sum(axis=1) * R
    sel = r["t"] > 0.5
    assert np.allclose(P_est[sel], r["Pcu"][sel], rtol=0.02)


def test_servo_tracks_reference_in_air():
    """Oracle path in air: q follows a 10 Hz page reference with small lag."""
    dt = 25e-6
    n = int(1.0 / dt)
    t = np.arange(n) * dt
    it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=np.zeros(n, bool), lift=np.full(n, 3e-3), features=[])
    sc = scenarios._assemble(it, np.zeros((n, 2)), 1.0, 90.0)
    sc.fpush[:] = 0.0
    A, f = 2e-4, 10.0
    sc.dtrue = np.column_stack([-A * np.sin(2 * np.pi * f * t), np.zeros(n)])  # clean path; d = pH - clean
    ov = {"require_contact": 0.0, "sensing.opt_lift_max": 1.0, "hand.effective_mass": 5.0}
    r = model.run(bench.with_disturbance(sc, sc.dtrue), model.Controller(mode="oracle", q_taper=1e-5), overrides=ov)
    sel = r["t"] > 0.4
    qr, q = r["qr1"][sel], r["q1"][sel]
    # amplitude ratio and phase of q relative to q_ref at 10 Hz
    tt = r["t"][sel]
    basis = np.column_stack([np.sin(2 * np.pi * f * tt), np.cos(2 * np.pi * f * tt)])
    cr_ = np.linalg.lstsq(basis, qr, rcond=None)[0]
    cq = np.linalg.lstsq(basis, q, rcond=None)[0]
    gain = np.hypot(*cq) / np.hypot(*cr_)
    phase = math.degrees(math.atan2(cq[1], cq[0]) - math.atan2(cr_[1], cr_[0]))
    phase = (phase + 180.0) % 360.0 - 180.0
    assert gain == pytest.approx(1.0, abs=0.05)
    assert abs(phase) < 10.0


def test_oracle_bound_regression_guard():
    tr = sg.TremorSpec(f0=6.0, amp_pk=3e-4)
    sc0 = scenarios.handwriting(seed=11, duration=5.0)
    sc1 = scenarios.handwriting(seed=11, duration=5.0, tremor=tr)
    out, _, _ = bench.compare_modes(sc0, sc1, modes=("neutral", "oracle"))
    assert out["oracle"]["ratio_vs_neutral"] < 0.3


def _transitions(r):
    c = (r["contact"] > 0).astype(int)
    return int(np.sum(np.diff(c) != 0))


def test_contact_feedforward_does_not_chatter_at_light_force():
    """Regression for the Monte Carlo finding (sim/diag_ff_chatter.py): a
    contact-load feedforward from the delayed axial-force signal makes the nib
    bounce at light force with stiff paper and axial path.  With the default
    controller (feedforward disabled, DEC-011) the powered-neutral pen must
    not bounce."""
    ov = {"writing.paper_stiffness": 2.0e5, "stage.axial_k": 1.0e4, "hand.normal_stiffness": 3000.0,
          "stage.k_tip": 50.0, "writing.mu_eff": 0.05}
    # low altitude, light force: the regime where the Monte Carlo found the bounce
    sc = scenarios.handwriting(seed=208, duration=3.0, theta_deg=36.3, N0=0.41)
    rr = model.run(sc, model.Controller(mode="rigid"), overrides=ov, seed=208)
    rf = model.run(sc, model.Controller(mode="neutral"), overrides=ov, seed=208)
    ru = model.run(sc, model.Controller(mode="neutral", ff_contact=1.0, ff_contact_fc=0.0), overrides=ov, seed=208)
    assert _transitions(ru) > 10 * max(_transitions(rr), 1)      # the defect is reproduced
    assert _transitions(rf) < 6 * max(_transitions(rr), 1)       # and removed by the filter
