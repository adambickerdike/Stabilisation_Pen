"""Verification tests for the hand-pen-paper model H1 (sim/handpen).

They check the code against hand calculations, against the HAP-26 lumped model it is calibrated to, against its own
linear model, and against model P1 where the physics coincide.  They verify code, not physics: passing them does not
validate any model against hardware or people.
Run: python3 -m pytest sim/handpen/tests -q
"""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import sim.handpen  # noqa: E402,F401  (numba cache location)
from sim.handpen import devices as DV  # noqa: E402
from sim.handpen import evaluate as HE  # noqa: E402
from sim.handpen import grip as G  # noqa: E402
from sim.handpen import linear as L  # noqa: E402
from sim.handpen import model as HM  # noqa: E402
from sim.handpen import params as HP  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402


def _hold_scenario(duration, d=None, dt=25e-6):
    """Pen held down at a fixed page point; optional imposed hand-path disturbance d (n x 2)."""
    n = int(round(duration / dt))
    t = np.arange(n) * dt
    it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=np.ones(n, bool), lift=np.zeros(n), features=[])
    sc = scenarios._assemble(it, np.zeros((n, 2)) if d is None else d, 1.0, 50.0)
    sc.fpush = np.clip(t / 0.1, 0, 1) * 1.0
    sc.psi_disp = None
    sc.tremor_obj = None
    return sc


def _lockin(t, x, f, t_from):
    m = t >= t_from
    c = np.cos(2 * np.pi * f * t[m])
    s = np.sin(2 * np.pi * f * t[m])
    xm = x[m] - x[m].mean()
    return 2 * math.hypot(np.mean(xm * c), np.mean(xm * s))


# ------------------------------------------------------------------ calibration to HAP-26
@pytest.mark.parametrize("split", [(0.1, 0.3), (0.5, 0.3), (0.7, 0.1), (0.5, 0.6)])
def test_tip_referred_impedance_reproduces_hap26(split):
    cfg = HP.Config(r_rot=split[0], rho_w=split[1])
    lm = L.LinearModel(cfg, contact=False, massless_pen=True)
    f = np.array([0.6, 2.0, 5.0, 8.0, 12.0, 20.0, 30.0])
    ref = G.hap26_compliance(f)
    for i, nm in enumerate(("F_x", "F_y", "F_z")):
        X = lm.frf(f, lambda w: lm.input_vector(nm).astype(complex))[:, i]
        assert np.max(np.abs(X / ref - 1.0)) < 1e-4


@pytest.mark.parametrize("r_rot,rho_w", [(0.1, 0.3), (0.3, 0.3), (0.5, 0.3), (0.7, 0.3), (0.5, 0.1), (0.8, 0.1)])
def test_grip_split_definition(r_rot, rho_w):
    g = G.calibrate(r_rot=r_rot, rho_w=rho_w)
    C = g.nib_compliance()
    assert 1.0 / C == pytest.approx(575.0, rel=1e-9)
    assert 1.0 - (1.0 / g.k_t) / C == pytest.approx(r_rot, abs=1e-9)
    assert g.k_w / g.k_t == pytest.approx(rho_w)
    assert g.kappa_f >= 0.0
    # static transfer by hand: a force at the elastic centre does not tilt the pen, so it moves the nib 1/k_t
    zc = g.z_c
    K = g.K_plane()
    u = np.linalg.solve(K, np.array([1.0, zc]))
    assert u[1] == pytest.approx(0.0, abs=1e-12)
    assert u[0] == pytest.approx(1.0 / g.k_t, rel=1e-9)


def test_infeasible_split_is_refused():
    with pytest.raises(ValueError):
        G.calibrate(r_rot=0.8, rho_w=0.3)


# ------------------------------------------------------------------ energy structure of the linear model
def test_linear_model_energy_structure():
    cfg = HP.Config(device=DV.gyro_rotor(60000.0))
    lm = L.LinearModel(cfg)
    M, D, K = lm.M, lm.D, lm.K
    assert np.allclose(M, M.T) and np.allclose(K, K.T)
    assert np.all(np.linalg.eigvalsh(M) > 0)
    assert np.all(np.linalg.eigvalsh(K) > -1e-9)
    # the gyroscopic part is skew-symmetric: it does no work on any velocity
    Gm = 0.5 * (D - D.T)
    assert Gm[3, 4] == pytest.approx(cfg.device.H)
    v = np.random.default_rng(0).standard_normal(D.shape[0])
    assert abs(v @ Gm @ v) < 1e-15
    # the dissipative part is positive semi-definite
    assert np.all(np.linalg.eigvalsh(0.5 * (D + D.T)) > -1e-9)


def test_pen_mass_properties_from_cad():
    b = HP.pen_body()
    assert b.m == pytest.approx(12.2e-3 * 1.1, rel=0.01)
    assert b.z_g == pytest.approx(0.088, abs=0.001)
    # hand calculation: a uniform 166 mm rod of the same mass about its centre is an upper-order check
    assert 0.3 * b.m * 0.166 ** 2 / 12 < b.J_g < 1.2 * b.m * 0.166 ** 2 / 12


# ------------------------------------------------------------------ core: statics and linear consistency
def test_static_equilibrium():
    sc = _hold_scenario(0.8)
    r = HM.run(sc, HP.Config())
    sel = r["t"] > 0.5
    N_nib0 = 0.15 / math.sin(math.radians(50))
    assert r["Nn"][sel].mean() == pytest.approx(N_nib0, rel=1e-6)
    assert r["Ns"][sel].mean() + r["Nn"][sel].mean() == pytest.approx(1.0, rel=0.01)
    assert np.max(np.abs(r["bx"][sel] - r["bx"][sel][0])) < 1e-9
    assert abs(r["Fgx"][sel].mean()) < 5e-3 and abs(r["Fgy"][sel].mean()) < 5e-3


@pytest.mark.parametrize("split", [(0.5, 0.3), (0.1, 0.3)])
def test_core_matches_linear_model_frictionless(split):
    """Small sinusoidal hand motion along y on a frictionless page: the compiled core's steady nib amplitude equals the
    linear model's prediction (both built from the same parameters)."""
    f, A = 9.0, 0.1e-3
    dt = 25e-6
    n = int(round(2.0 / dt))
    t = np.arange(n) * dt
    ramp = np.clip(t / 0.3, 0, 1)
    d = np.column_stack([np.zeros(n), A * ramp * np.sin(2 * np.pi * f * t)])
    sc = _hold_scenario(2.0, d)
    cfg = HP.Config(r_rot=split[0], rho_w=split[1], mu_skid=0.0, mu_nib=0.0)
    r = HM.run(sc, cfg)
    amp_core = _lockin(r["t"], r["by"], f, 1.0)
    lm = L.LinearModel(cfg, paper="free")
    w = 2 * np.pi * f
    X = lm.solve(w, lm.exc_translation(np.array([0.0, 1.0, 0.0]), w) * A)
    assert amp_core == pytest.approx(abs(X[1]), rel=0.03)
    tilt_core = _lockin(r["t"], r["b2"], f, 1.0)
    assert tilt_core == pytest.approx(abs(X[4]), rel=0.05)


# ------------------------------------------------------------------ agreement with model P1
def test_unmodified_pen_agrees_with_P1_when_rotation_is_locked():
    import sim.pencil  # noqa: F401
    from sim.pencil import evaluate as E1
    from sim.pencil import model as M1
    tr = HM.Tremor(f0=8.0, amp_trans=0.3e-3)
    sc0 = HM.build_scenario(seed=200, duration=3.0, tremor=None)
    sc1 = HM.build_scenario(seed=200, duration=3.0, tremor=tr)
    cfgp = M1.PencilConfig(overrides={"hand.normal_stiffness": 575.0, "hand.normal_damping": 1.3})
    mp = E1.compare(M1.run(sc1, M1.Controller(mode="neutral"), cfgp, seed=200),
                    M1.run(sc0, M1.Controller(mode="neutral"), cfgp, seed=200))
    h = HP.Config(lock_rotation=True)
    mh = HE.compare(HM.run(sc1, h), HM.run(sc0, h))
    assert mh["ball_band_rms_um"] == pytest.approx(mp["housing_band_rms_um"], rel=0.05)
    assert mh["e_rms_um"] == pytest.approx(mp["e_rms_um"], rel=0.08)


# ------------------------------------------------------------------ device formulas against hand calculations
def test_device_hand_calculations():
    # reaction mass: F = m w^2 x
    assert DV.reaction_force(5.15e-3, 1.0e-3, 8.0) == pytest.approx(5.15e-3 * (2 * math.pi * 8) ** 2 * 1e-3)
    assert DV.mass_stroke_needed(DV.reaction_force(3e-3, 0.5e-3, 10.0), 10.0) == pytest.approx(1.5e-6)
    # tungsten slug 4.5 x 18 mm at 18 g/cm3 = 5.153 g
    assert DV.cylinder_mass(4.5e-3, 18e-3) == pytest.approx(18e3 * math.pi / 4 * 4.5e-3 ** 2 * 18e-3)
    assert DV.cylinder_mass(4.5e-3, 18e-3) * 1e3 == pytest.approx(5.153, abs=0.002)
    # ring inertia and angular momentum
    m = DV.cylinder_mass(7e-3, 6e-3, d_in=2e-3)
    J = DV.ring_inertia(m, 7e-3, 2e-3)
    assert J == pytest.approx(m * (3.5e-3 ** 2 + 1e-3 ** 2) / 2)
    assert DV.gyro_rotor(30000.0).H == pytest.approx(J * 30000 * 2 * math.pi / 60)
    # gyroscope torque H Omega; CMG pair 2 H rate cos(delta); pair limit 2 H min(rate, w delta)
    assert DV.gyro_torque(1e-4, 0.1) == pytest.approx(1e-5)
    assert DV.cmg_pair_torque(4e-5, 30.0) == pytest.approx(2.4e-3)
    assert DV.cmg_pair_torque(4e-5, 30.0, delta=0.5) == pytest.approx(2.4e-3 * math.cos(0.5))
    assert DV.cmg_pair_limit(4e-5, 4.0, 30.0, 0.6) == pytest.approx(2 * 4e-5 * 2 * math.pi * 4 * 0.6)
    assert DV.cmg_pair_limit(4e-5, 12.0, 30.0, 0.6) == pytest.approx(2 * 4e-5 * 30.0)
    # reaction wheel speed swing tau / (J w)
    assert DV.reaction_wheel_speed_swing(1e-4, 2e-8, 8.0) == pytest.approx(1e-4 / (2e-8 * 2 * math.pi * 8))
    # imbalance: F = m e w^2 with e = G / w
    w = 60000 * 2 * math.pi / 60
    assert DV.imbalance_force(1.6e-3, 2.5e-3, 60000) == pytest.approx(1.6e-3 * (2.5e-3 / w) * w * w)
    # motor friction from the datasheet (AMF-51): (C0 + Cv n) w
    P, tau = DV.motor_friction_power("0515B", 30000)
    assert tau == pytest.approx(0.033e-3 + 6.5e-7 * 1e-3 * 30000)       # datasheet: 0.033 mNm + 6.5e-7 mNm/rpm
    assert P == pytest.approx(tau * 30000 * 2 * math.pi / 60)
    assert P == pytest.approx(0.165, rel=0.01)
    P3, tau3 = DV.motor_friction_power("0308B", 60000)
    assert tau3 == pytest.approx(1.77e-6 + 1.09e-10 * 60000)             # 1.77e-3 mNm + 1.09e-7 mNm/rpm
    # spin-up t = J w / tau
    assert DV.spin_up_time(2e-8, 30000, 8.4e-5) == pytest.approx(2e-8 * 30000 * 2 * math.pi / 60 / 8.4e-5)
    # voice-coil copper loss (F/Km)^2
    assert DV.voice_coil_power(0.01, 0.05) == pytest.approx(0.04)
    # sleeve: worst transverse load N (cos th + mu sin th)
    s = DV.sleeve_holding(1.0, 50.0, 0.12, 0.04)
    assert s["worst_direction_N"] == pytest.approx(math.cos(math.radians(50)) + 0.12 * math.sin(math.radians(50)))
    assert s["moment_Nm"] == pytest.approx(0.04 * s["worst_direction_N"])


def test_reaction_mass_force_and_stroke_in_core():
    """A commanded sinusoidal actuator force reaches the moving mass unclipped; the stroke is the free-mass motion
    F/(m (w^2 - wc^2)) minus the pen's own quasi-static give at the cap under the reaction, F C_cap, with C_cap the grip
    driving-point compliance at z_d (hand calculation from grip.py; pen inertia neglected at 10 Hz)."""
    f, F0 = 10.0, 5e-3
    sc = _hold_scenario(1.5)
    dv = DV.rm_slug(axes=2)
    cfg = HP.Config(device=dv)
    n = len(sc.t)
    uff = np.zeros((n, 3))
    uff[:, 1] = F0 * np.sin(2 * np.pi * f * sc.t) * np.clip((sc.t - 0.3) / 0.2, 0, 1)
    r = HM.run(sc, cfg, uff=uff)
    Fa = _lockin(r["t"], r["Fd2"], f, 0.8)
    x = _lockin(r["t"], r["r2"], f, 0.8)
    w = 2 * math.pi * f
    wc = 2 * math.pi * 1.5
    g = G.calibrate(r_rot=0.5, rho_w=0.3)
    Cp = np.linalg.inv(g.K_plane())
    zv = np.array([1.0, dv.z])
    C_cap = float(zv @ Cp @ zv)
    x_hand = F0 * (1.0 / (dv.m * (w * w - wc * wc)) - C_cap)
    assert x == pytest.approx(x_hand, rel=0.10)
    assert Fa == pytest.approx(F0 * math.hypot(1.0, 0.0), rel=0.10)
    assert np.max(np.abs(r["r2"])) < dv.stroke[1]


def test_cmg_torque_and_gimbal_in_core():
    """Commanded torque amplitude tau0 about t1 is delivered as 2 H cos(d) d_dot, with a gimbal swing tau0 / (2 H w)."""
    f, tau0 = 10.0, 0.5e-3
    sc = _hold_scenario(1.2)
    dv = DV.cmg_pair(axes=(0, 1))
    cfg = HP.Config(device=dv)
    n = len(sc.t)
    uff = np.zeros((n, 3))
    uff[:, 1] = tau0 * np.sin(2 * np.pi * f * sc.t) * np.clip((sc.t - 0.2) / 0.2, 0, 1)
    r = HM.run(sc, cfg, uff=uff)
    tq = _lockin(r["t"], r["tq2"], f, 0.7)
    ang = _lockin(r["t"], r["dl2"], f, 0.7)
    assert tq == pytest.approx(tau0, rel=0.10)
    assert ang == pytest.approx(tau0 / (2 * dv.H * 2 * math.pi * f), rel=0.10)
    assert np.max(np.abs(r["dl2"])) <= dv.delta_max * 1.05 + 1e-9


def test_stage_never_exceeds_its_stop():
    tr = HM.Tremor(f0=10.0, amp_trans=0.5e-3)
    sc0 = HM.build_scenario(seed=201, duration=2.0, tremor=None)
    sc1 = HM.build_scenario(seed=201, duration=2.0, tremor=tr)
    base = HP.Config()
    ref = HM.run(sc0, base)
    r = HM.run(sc1, base.replace(stage=True), clean=HM.clean_at_sim_rate(ref, len(sc1.t)))
    q = np.hypot(r["q1"], r["q2"])
    assert np.max(q) <= 0.40e-3 + 1e-9
    assert HE.compare(r, ref)["e_rms_um"] < HE.compare(HM.run(sc1, base), ref)["e_rms_um"]
