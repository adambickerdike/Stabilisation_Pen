"""Checks of the sim/handpen extension (grip sleeve + actuated pivot, stage command source, in-loop controller hook,
IMU model) against hand calculations and against the original model.  Code verification only (not physics validation)."""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import sim.handpen  # noqa: E402,F401
from sim.handpen import core  # noqa: E402
from sim.handpen import devices as DV  # noqa: E402
from sim.handpen import evaluate as HE  # noqa: E402
from sim.handpen import linear as L  # noqa: E402
from sim.handpen import model as HM  # noqa: E402
from sim.handpen import params as HP  # noqa: E402
from opt.inertial import control as CL  # noqa: E402
from opt.inertial import linear_ext as LE  # noqa: E402

SEED = 311
DUR = 1.5


@pytest.fixture(scope="module")
def scns():
    sc0 = HM.build_scenario(seed=SEED, duration=DUR)
    sc = HM.build_scenario(seed=SEED, duration=DUR, tremor=HM.Tremor(f0=8.0, amp_trans=0.3e-3))
    return sc0, sc


def _rigid_pair(m=8e-3, z=0.05):
    Lc, r2 = 0.015, 2.25e-3 ** 2 / 4
    J = m * (Lc ** 2 / 12 + r2)
    cfgA = HP.Config(device=DV.cap_mass(m, z))
    sl = HP.Sleeve(m=m, z_g=z, J_g=J, z_p=0.02, k_pt=2e5, k_pa=2e5, k_pr=0.0, beta_p=2e-5, z_a=0.075, act="piezo", k_a=2e4,
                   c_a=0.5, stroke=0.5e-3, F_max=10.0)
    return cfgA, HP.Config(sleeve=sl)


def test_stiff_sleeve_equals_rigid_mass(scns):
    """A stiff pivot and piezo make the sleeve + pen behave like the pen with the same mass fixed to it (H1 time domain)."""
    sc0, sc = scns
    cfgA, cfgB = _rigid_pair()
    rA, rB = HM.run(sc, cfgA), HM.run(sc, cfgB)
    eA = HE.compare(rA, HM.run(sc0, cfgA))["e_rms_um"]
    eB = HE.compare(rB, HM.run(sc0, cfgB))["e_rms_um"]
    assert eB == pytest.approx(eA, rel=0.03)
    d = rA.ink() - rB.ink()
    assert np.sqrt(np.mean(np.sum(d[1000:] ** 2, axis=1))) < 15e-6


def test_pivot_carries_the_static_writing_load(scns):
    """With the push routed through the sleeve, the actuator holds the moment of N cos(theta) about the pivot (CALC):
    F_act = N cos(theta) z_p / (z_a - z_p) at N ~ 0.8-1 N, 50 deg."""
    sc0, _ = scns
    _, cfgB = _rigid_pair()
    r = HM.run(sc0, cfgB)
    sel = (r["t"] > 0.7) & (r["contact"] > 0)
    N = (r["Ns"] + r["Nn"])[sel].mean()
    F_expect = N * math.cos(math.radians(50)) * 0.02 / (0.075 - 0.02)
    assert abs(r["pf1"][sel].mean()) == pytest.approx(F_expect, rel=0.25)


def test_linear_ext_reproduces_original_and_rigid_sleeve():
    for dv in (HP.Device(), DV.rm_slug(axes=3), DV.gyro_rotor(30000.0)):
        cfg = HP.Config(device=dv)
        a, b = L.LinearModel(cfg), LE.LinearExt(cfg)
        assert np.array_equal(a.M, b.M) and np.array_equal(a.D, b.D) and np.array_equal(a.K, b.K)
    m, z = 8e-3, 0.05
    J = m * (0.015 ** 2 / 12 + 2.25e-3 ** 2 / 4)
    la = LE.LinearExt(HP.Config(device=DV.cap_mass(m, z)))
    lb = LE.LinearExt(HP.Config(sleeve=HP.Sleeve(m=m, z_g=z, J_g=J, z_p=0.02, k_pt=1e7, k_pa=1e7, k_pr=0.0, beta_p=0, z_a=0.075,
                                                 act="piezo", k_a=1e6, c_a=0.0)))
    for f in (4.0, 8.0, 12.0):
        xa, xb = LE.x0_trans(la, f)[0:2], LE.x0_trans(lb, f)[0:2]
        assert np.allclose(np.abs(xa), np.abs(xb), rtol=2e-3)


def test_stage_external_and_controller_sources_are_identical(scns):
    sc0, sc = scns
    n = len(sc.t)
    base = HP.Config()
    ref = HM.run(sc0, base)
    un = HM.run(sc, base)
    d = un.ball() - ref.ball()[:len(un.ball())]
    X = HM.uff_at_sim_rate(d, un["t"], n)
    r1 = HM.run(sc, base.replace(stage=True, stage_src=1), clean=X)
    D = np.zeros((CL.NO, CL.NYE)); D[5, CL.NY] = 1.0; D[6, CL.NY + 1] = 1.0
    ctl = dict(Ts=5e-4, D=D, imu=dict(acc_nd=0.0, gyr_nd=0.0, pos_nd=0.0, lat_ticks=0))
    u = np.zeros((n, 7)); u[:, 3:5] = X
    r2 = HM.run(sc, base.replace(stage=True, stage_src=2, ctl=ctl), uff=u)
    assert np.array_equal(r1.ink(), r2.ink())


def test_imu_model_matches_kinematics(scns):
    """Noise-free, zero-latency body IMU = the IMU point's acceleration below 100 Hz (after the 400 Hz anti-aliasing filter)."""
    from scipy.signal import butter, sosfiltfilt
    _, sc = scns
    ctl = dict(Ts=5e-4, imu=dict(acc_nd=0.0, gyr_nd=0.0, pos_nd=0.0, lat_ticks=0, z_b=0.1))
    r = HM.run(sc, HP.Config(ctl=ctl), uff=np.zeros((len(sc.t), 7)))
    a, t1, t2, n, h = HP.geometry_vectors(50.0)
    pos = np.column_stack([r["bx"], r["by"]]) + 0.1 * (r["b1"][:, None] * t1[None, :2] + r["b2"][:, None] * t2[None, :2])
    dt = r["t"][1] - r["t"][0]
    acc = np.gradient(np.gradient(pos, dt, axis=0), dt, axis=0)
    sos = butter(4, 100, fs=1 / dt, output="sos")
    am, af = sosfiltfilt(sos, r["ia1"]), sosfiltfilt(sos, acc[:, 0])
    sel = slice(1200, 2800)
    c = max(np.corrcoef(am[sel.start + k:sel.stop + k], af[sel])[0, 1] for k in range(4))
    assert c > 0.995
    assert np.std(am[sel]) == pytest.approx(np.std(af[sel]), rel=0.05)


def test_controller_embedding_and_zoh():
    """embed(): a pure integrator from e0 to u3 discretised by ZOH integrates a constant input exactly."""
    Ts = 1e-3
    A, B, C, D = CL.embed(np.zeros((1, 1)), np.ones((1, 1)), np.ones((1, 1)), np.zeros((1, 1)), [CL.E_EST[0]], [CL.U_PIV[0]], Ts)
    x = np.zeros(1)
    for _ in range(100):
        v = np.zeros(CL.NI); v[CL.E_EST[0]] = 2.0
        x = A @ x + B @ v
    assert (C @ x)[CL.U_PIV[0]] == pytest.approx(0.2, rel=1e-12)


def test_afc_table_layout():
    G = np.array([np.diag([1.0 + 1.0j, 2.0]) for _ in range(3)])
    tab = CL.afc_table(np.array([4.0, 5.0, 6.0]), G, umax=[0.1, 0.2, 0.3])
    assert tab.shape == (3, 9)
    assert tab[0, 0] == pytest.approx(0.5) and tab[0, 1] == pytest.approx(-0.5) and tab[0, 6] == pytest.approx(0.5)
    assert tab[2, 8] == pytest.approx(0.3)
