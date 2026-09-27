"""Verification tests for the pencil simulator (model P1) and the shared design model.

They check the code against the A1 hand calculations (analysis/pencil_mechanisms.py and
sim/pencil/design.py) and against the existing simulator M1 where the physics coincide.
They verify code, not physics: passing them does not validate any model against hardware.
Run: python3 -m pytest sim/pencil/tests -q
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import sim.pencil  # noqa: E402,F401  (numba cache outside sim/pensim)
from sim.pencil import design as D  # noqa: E402
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from sim.pencil import power as PW  # noqa: E402
from sim.pencil.layout import IDX  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

D2R = math.pi / 180


def _air_scenario(duration, dt=25e-6, lift=5e-3):
    n = int(round(duration / dt))
    t = np.arange(n) * dt
    it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=np.zeros(n, bool), lift=np.full(n, lift), features=[])
    sc = scenarios._assemble(it, np.zeros((n, 2)), 1.0, 50.0)
    sc.fpush[:] = 0.0
    return sc


# ---------------------------------------------------------------- statics against A1
@pytest.mark.parametrize("theta", [35.0, 50.0, 75.0])
def test_static_nib_and_skid_loads_match_A1(theta):
    sc = scenarios.static_hold(duration=1.2, theta_deg=theta, N0=1.0)
    cfg = M.PencilConfig(hysteresis=False)
    r = M.run(sc, M.Controller(mode="neutral"), cfg, seed=3)
    sel = r["t"] > 0.9
    ss = M.static_state(cfg, theta * D2R, 1.0)
    F_sp = ss["F_sp0"] + ss["k_sp"] * r["s"][sel].mean()
    N_nib = r["Nn"][sel].mean()
    # axial balance (no sliding: friction in stick is ~0): N sin(theta) = F_spring
    assert N_nib == pytest.approx(F_sp / math.sin(theta * D2R), rel=0.02)
    # the stage holds the transverse load N cos(theta) (A1: F_c cot(theta)); parasitic k_par*q is included in Fa balance
    Fa = r.xy("Fa1")[sel].mean(axis=0)
    kpar_q = r.P[IDX["k_par"]] * r.xy("q1")[sel].mean(axis=0)
    assert Fa[0] - kpar_q[0] == pytest.approx(N_nib * math.cos(theta * D2R), rel=0.03)
    assert abs(Fa[1]) < 0.01
    # the skid carries the rest of the writing force
    assert r["Ns"][sel].mean() == pytest.approx(1.0 - N_nib, rel=0.03)
    # the servo holds the nib at the centre against it
    assert np.max(np.abs(r.xy("q1")[sel])) < 5e-6


def test_stroke_under_load_matches_design_load_line():
    st = D.stage("Q26")
    sc = _air_scenario(0.25)
    F = 0.17
    cfg = M.PencilConfig(hysteresis=False, overrides={"F_test0": -F, "hall_noise": 0.0})
    r_top = M.run(sc, M.Controller(mode="open", V_fixed=60.0), cfg)
    r_mid = M.run(sc, M.Controller(mode="open", V_fixed=30.0), cfg)
    q_top = r_top["q1"][-50:].mean()
    q_mid = r_mid["q1"][-50:].mean()
    k = st.k_b_nib + st.k_par_nib
    assert q_top == pytest.approx((st.F_b_nib - F) / k, rel=0.02)
    assert q_mid == pytest.approx(-F / k, rel=0.02)
    assert q_top == pytest.approx(st.stroke_under_load(F), rel=0.02)


def test_free_stage_resonance_matches_lumped_model():
    st = D.stage("Q26")
    sc = _air_scenario(0.3)
    cfg = M.PencilConfig(hysteresis=False, zeta_stage=0.002, overrides={"q_init": 1e-4, "hall_noise": 0.0})
    r = M.run(sc, M.Controller(mode="open", V_fixed=30.0), cfg, rec_hz=40000.0)
    q = r["q1"]
    zc = np.flatnonzero((q[:-1] < 0) & (q[1:] >= 0))
    f_meas = (len(zc) - 1) / (r["t"][zc[-1]] - r["t"][zc[0]])
    M_t = r.info["M_t_kg"]
    m_eff = st.m_eq_nib - st.m_couple_nib ** 2 / M_t     # housing effectively free at 190 Hz (grip mode ~33 Hz)
    f_th = math.sqrt((st.k_b_nib + st.k_par_nib) / m_eff) / (2 * math.pi)
    assert f_meas == pytest.approx(f_th, rel=0.02)
    assert st.f1 == pytest.approx(math.sqrt((st.k_b_nib + st.k_par_nib) / st.m_eq_nib) / (2 * math.pi), rel=1e-9)


def test_servo_tracks_sinusoid_in_air_and_power_bookkeeping():
    dt = 25e-6
    sc = _air_scenario(1.0)
    A, f = 1.5e-4, 10.0
    t = sc.t
    sc.dtrue = np.column_stack([-A * np.sin(2 * np.pi * f * t), np.zeros(len(t))])
    cfg = M.PencilConfig(hysteresis=False, overrides={"require_contact": 0.0, "sensing.opt_lift_max": 1.0, "hall_noise": 0.0})
    r = M.run(M.with_disturbance(sc, sc.dtrue), M.Controller(mode="oracle", q_taper=1e-5), cfg)
    sel = r["t"] > 0.5
    tt = r["t"][sel]
    B = np.column_stack([np.sin(2 * np.pi * f * tt), np.cos(2 * np.pi * f * tt)])
    cr = np.linalg.lstsq(B, r["qr1"][sel], rcond=None)[0]
    cq = np.linalg.lstsq(B, r["q1"][sel], rcond=None)[0]
    assert np.hypot(*cq) / np.hypot(*cr) == pytest.approx(1.0, abs=0.05)
    ph = math.degrees(math.atan2(cq[1], cq[0]) - math.atan2(cr[1], cr[0]))
    assert abs((ph + 180) % 360 - 180) < 10.0
    # drive power: class-B rail power of a sinusoidal drive = f C V_pp V_rail (sim/pencil/power.py)
    cv = np.linalg.lstsq(np.column_stack([B, np.ones(len(tt))]), r["V1"][sel], rcond=None)[0]
    Va = np.hypot(cv[0], cv[1])
    C = r.P[IDX["C_axis"]]
    P_expected = f * C * 2 * Va * r.P[IDX["V_rail"]]
    assert np.mean(r["PrailB"][sel]) == pytest.approx(P_expected, rel=0.10)
    assert PW.sine_drive(C, Va, f, 60.0)["P_rail_W"] == pytest.approx(P_expected, rel=0.01)


# ---------------------------------------------------------------- against model M1 (physics coincide)
def test_locked_pencil_reproduces_M1_rigid_pen():
    from sim.pensim import model as m1
    sc = scenarios.handwriting(seed=5, duration=2.0, tremor=sg.TremorSpec(f0=6.0, amp_pk=3e-4))
    a = m1.run(sc, m1.Controller(mode="rigid"), seed=5)
    b = M.run(sc, M.Controller(mode="locked"), M.PencilConfig(locked=True, skid=False, m1_match=True), seed=5)
    n = min(len(a["t"]), len(b["t"]))
    d = a.xy("tipx")[:n] - b.ink()[:n]
    assert np.sqrt(np.mean(np.sum(d ** 2, axis=1))) < 1e-8
    assert np.mean((a["contact"][:n] > 0) == (b["contact"][:n] > 0)) == 1.0


def test_kalman_step_is_M1s():
    from sim.pensim import core as m1core
    from sim.pencil import core as pcore
    rng = np.random.default_rng(0)
    x1 = np.zeros(5); P1 = np.eye(5) * 1e-6
    x2 = np.zeros(5); P2 = np.eye(5) * 1e-6
    for _ in range(200):
        y = rng.normal() * 1e-4
        a = m1core._kf_step(x1, P1, y, 5e-4, 2 * np.pi * 7, 0.999, 0.1, 1e-8, 2.5e-11)
        b = pcore._kf_step(x2, P2, y, 5e-4, 2 * np.pi * 7, 0.999, 0.1, 1e-8, 2.5e-11)
        assert a == b
    assert np.array_equal(x1, x2) and np.array_equal(P1, P2)


# ---------------------------------------------------------------- regression guards
def test_oracle_bound_and_ratio_definition():
    sc0 = scenarios.handwriting(seed=11, duration=4.0)
    sc1 = scenarios.handwriting(seed=11, duration=4.0, tremor=sg.TremorSpec(f0=6.0, amp_pk=1e-4))
    cfg = M.PencilConfig()
    ref = M.run(sc0, M.Controller(mode="neutral"), cfg, seed=11)
    rn = M.run(sc1, M.Controller(mode="neutral"), cfg, seed=11)
    ro = M.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, ref)), M.Controller(mode="oracle"), cfg, seed=11)
    base = E.compare(rn, ref)["e_rms_um"]
    assert E.compare(ro, ref)["e_rms_um"] / base < 0.4
    assert E.compare(ref, ref)["e_rms_um"] == 0.0


def test_A1_load_formulas():
    # frictionless limit = lead convention F_c cot(theta); friction raises the worst direction to F_c cot(theta - atan mu)
    th, Fc, mu = 50 * D2R, 0.15, 0.15
    assert D.load_extremes("skid", Fc, th, 0.0)["R_perp_max"] == pytest.approx(Fc / math.tan(th), rel=1e-9)
    assert D.load_extremes("skid", Fc, th, mu)["R_t1_max"] == pytest.approx(Fc / math.tan(th - math.atan(mu)), rel=1e-3)
    # conventional pen (P-6)
    assert D.load_extremes("pen", 1.0, th, 0.0)["R_perp_max"] == pytest.approx(math.cos(th), rel=1e-9)
    # protrusion: p >= r cot(theta); lead's range 1.4 mm x (cot 35 - cot 75) = 1.62 mm
    b = D.protrusion_budget(1.4e-3)
    assert b["tilt_range_simple"] == pytest.approx(1.4e-3 * (1 / math.tan(35 * D2R) - 1 / math.tan(75 * D2R)), rel=1e-9)
    assert b["tilt_range_simple"] == pytest.approx(1.62e-3, abs=0.01e-3)
