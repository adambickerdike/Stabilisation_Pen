"""Rev H model checks: masses and geometry, the architecture-A bias, the adjoint gradients, the add-on feed-forward and the
tracker streams.  Code verification only."""
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import sim.handpen  # noqa: E402,F401
from sim.handpen import model as HM  # noqa: E402
from sim.handpen import params as HP  # noqa: E402
from opt.inertial import addon as AD  # noqa: E402
from opt.inertial import adjoint as AJ  # noqa: E402
from opt.inertial import catalog as CT  # noqa: E402
from opt.inertial import control as CL  # noqa: E402
from opt.inertial import geometry as GE  # noqa: E402
from opt.inertial import revh as RH  # noqa: E402
from opt.inertial import tracker as TK  # noqa: E402


def test_masses_and_body_mod():
    d = RH.RevH()
    ms = RH.masses(d)
    body = HP.pen_with_device(RH.config_B(d))
    assert body.m * 1e3 == pytest.approx(ms["total_g"], rel=1e-9)
    assert 60 < ms["total_g"] < 100          # lead's guide: <= 100 g
    assert ms["moving_mass_at_tip_g"] == pytest.approx(ms["nose_inertia_about_pivot_g_mm2"] * 1e-9 / d.z_p ** 2 * 1e3, rel=1e-9)
    # removing every CAD part leaves only the Rev H parts
    names = [p[0] for p in body.parts]
    assert "barrel" not in names and "revh_cell" in names and "revh_pcb" in names and "revh_refill_D1" in names


def test_geometry_fit_checks_pass():
    g = GE.layout(RH.RevH())
    assert g["fit_checks"]["all_pass"]
    ids = [c["id"] for c in g["components"]]
    assert len(ids) == len(set(ids))
    for c in g["components"]:
        assert c["group"] in ("structure", "grip", "moving_nose", "refill", "actuator", "mechanism", "sensor", "electronics", "power",
                              "haptic", "inertial", "magnet")
        assert c["moves_with"] in ("nose", "handle", "inertial_mass")
        assert c["z1"] > c["z0"]


def test_lever_and_km_tip():
    d = RH.RevH(z_p=0.04, z_a=0.08, Km_act=0.5)
    assert d.lever == pytest.approx(1.0)
    assert d.Km_tip == pytest.approx(0.5)


def test_arch_A_bias_holds_static_writing_load():
    """With the bias -N cos(theta) lever on the nose at z_a the servo effort in static writing is small (CALC sign check)."""
    d = RH.RevH(arch="A")
    ms = RH.masses(d)
    m_act = ms["nose_inertia_about_pivot_g_mm2"] * 1e-9 / (d.z_a - d.z_p) ** 2
    blocks, _ = CL.tip_servo_A(d.lever, 50.0, m_act, f_bw=80.0)
    cfg = RH.config_A(d).replace(ctl=CL.ctl_spec(blocks, Ts=2e-4, imu=dict(acc_nd=0.0, gyr_nd=0.0, pos_nd=0.0, lat_ticks=1),
                                                 ulim=[0, 0, 0, d.F_peak_act, d.F_peak_act, 0, 0]))
    assert cfg.sleeve.preload[0] < 0
    sc0 = HM.build_scenario(seed=311, duration=1.5)
    r = HM.run(sc0, cfg, uff=np.zeros((len(sc0.t), 7)))
    sel = (r["t"] > 0.6) & (r["contact"] > 0)
    assert abs(np.mean(r["u4"][sel])) < 0.35 * abs(cfg.sleeve.preload[0])
    assert abs(np.mean(r["pd1"][sel])) < 50e-6


def test_adjoint_gradients_match_finite_differences():
    g = AJ.nose_grad_check()
    for k, (ad, fd) in g.items():
        assert ad == pytest.approx(fd, rel=1e-4, abs=1e-9), k


def test_ff_phasor_is_causal_and_capped():
    d = RH.RevH()
    rm = AD.rm_rear(m_slug=19.8e-3, d_slug=10e-3, f_c=5.0, F_max=0.5)
    n = 4000
    t = np.arange(n) * 5e-4
    e = np.column_stack([3e-4 * np.sin(2 * np.pi * 8 * t), 2e-4 * np.cos(2 * np.pi * 8 * t)])
    f = np.full(n, 8.0)
    u1 = AD.ff_phasor(e, f, d, rm)
    e2 = e.copy(); e2[2500:] *= 5.0          # change the future
    u2 = AD.ff_phasor(e2, f, d, rm)
    assert np.array_equal(u1[:2500], u2[:2500])
    cap = min(rm.F_max[0], 0.7 * rm.m * (2 * np.pi * 8) ** 2 * rm.stroke[0])
    assert np.max(np.abs(u2)) <= cap + 1e-12


def test_tracker_streams_and_causality():
    sc = HM.build_scenario(seed=312, duration=1.5, tremor=HM.Tremor(f0=10.0, amp_trans=0.5e-3))
    cfg = RH.config_B(RH.RevH())
    r = HM.run(sc, cfg, rec_hz=TK.REC_HZ)
    st = TK.make_streams(r, sc, seed=1)
    assert st.acc.shape[1] == 2 and len(st.tick_t) == int(math.ceil(1.5 / 5e-4 - 1e-9))
    assert np.all(st.acc_av > st.acc_t)
    dh, info, _ = TK.estimate(r, sc, seed=1)
    assert dh.shape == (len(st.tick_t), 2) and np.all(np.isfinite(dh))


def test_catalogue_units():
    assert CT.VCAS["LVCM-016-010-01"].Km == pytest.approx(1.1 / math.sqrt(1.8))
    assert CT.CELLS["LIR14500"].Wh == pytest.approx(0.75 * 3.7 * 0.8)
    assert CT.below_resonance_transmission(8.0, 65.0) == pytest.approx(0.0154, abs=5e-4)


def test_board_magnet_keel_clearance_formula():
    """The keel's paper clearance uses the plane through the skid-ring heel: at the heel itself the height is zero."""
    from opt.inertial import board_magnet as BM
    geo = GE.layout(RH.RevH())
    pm = dict(BM.placement(), z_c=geo["ball_protrusion_mm"] + 1.585 + 0.5, x_c=-geo["skid_contact_radius"] + 3.175 + 0.5, h=3.17, d=6.35)
    # front-bottom corner of the keel sits exactly on the heel point -> zero height at every tilt
    for t in (35.0, 50.0, 75.0):
        assert BM.keel_clearance(t, geo, pm) == pytest.approx(0.0, abs=1e-9)


def test_front_end_closes_over_writing_tilts():
    """Front-end closure (CALC): at the design contact radius the ring lip, the nozzle and the sleeve front clear over 35-75 deg."""
    from opt.inertial import front_end as FE
    ru = FE.FrontRules()
    d = RH.RevH()
    c = FE.check(d.skid_r * 1e3, d, ru, n_theta=5, n_phi=12)
    assert c["passes"]
    assert c["ring_wall_mm"] >= ru.ring_wall_min
    assert c["nozzle_clear_usable_min_mm"] >= ru.c_paper
    assert c["ball_travel_usable_min_mm"] >= 2.5            # REQ-RVH-002
    # the first layout's 5.5 mm contact radius leaves no wall for the ring
    assert FE.check(5.5, d, ru, n_theta=3, n_phi=8)["ring_wall_mm"] < ru.ring_wall_min
    # sizing returns the design value
    assert FE.size_R(d, ru)["R_mm"] == pytest.approx(d.skid_r * 1e3)


def test_front_end_pose_rest_and_slide():
    """At rest the ball sits on the paper with no slide at the nominal tilt; the slide at other tilts is the protrusion change."""
    from opt.inertial import front_end as FE
    ru = FE.FrontRules()
    d = RH.RevH()
    R = d.skid_r * 1e3
    dm = dict(FE.dims(R, d, ru), nozzle_r_front=ru.nozzle_r_front)
    assert FE.pose(50.0, dm, 0.0, 0.0, ru)["slide"] == pytest.approx(0.0, abs=1e-9)
    for t in (35.0, 75.0):
        assert FE.pose(t, dm, 0.0, 0.0, ru)["slide"] == pytest.approx(FE.protrusion(t, R) - FE.protrusion(50.0, R), abs=1e-9)
    # the layout's ring starts at the contact plane and its outer radius is the contact radius
    g = GE.layout(d)
    ring = [c for c in g["components"] if c["id"] == "skid_ring"][0]
    assert ring["z0"] == pytest.approx(g["ball_protrusion_mm"], abs=0.01) and ring["d0"] / 2 == pytest.approx(R, abs=0.01)
