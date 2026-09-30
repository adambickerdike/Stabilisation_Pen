"""Independent mechanics invariants, numerical checks and physical regressions."""
import math
from dataclasses import replace

import numpy as np
import pytest

from revk.feasibility import (CoilShape, electrical_allocation, harmonic_force_rms,
                              page_to_nib_matrix, radial_project, thrust_guide,
                              winding_map, wire_anchor)


@pytest.mark.parametrize("theta", [35., 50., 75.])
def test_page_ellipse_and_virtual_work(theta):
    J = page_to_nib_matrix(theta, 23.)
    for a in np.linspace(0, 2 * math.pi, 33):
        q = .0015 * np.array([math.cos(a), math.sin(a)])
        page = np.linalg.solve(J, q)
        assert np.linalg.norm(J @ page) == pytest.approx(.0015)
        f = np.array([.12, -.07])
        assert (J.T @ f) @ page == pytest.approx(f @ q)


def test_radial_projection_is_not_square_clipping():
    assert np.linalg.norm(radial_project([1, 1], 1)) == pytest.approx(1)
    assert radial_project([.2, -.3], 1) == pytest.approx([.2, -.3])
    with pytest.raises(ValueError):
        radial_project([float("nan"), 0], 1)


@pytest.mark.parametrize("frequency", [0., 4., 8., 12., 40.])
def test_harmonic_force_matches_time_domain(frequency):
    m, k, c, q = .0035, 3.79, .013, .001
    phase = np.linspace(0, 2 * math.pi, 20000, endpoint=False)
    w = 2 * math.pi * frequency
    force = math.sqrt(2) * q * ((k - m * w * w) * np.sin(phase) + c * w * np.cos(phase))
    assert harmonic_force_rms(m, k, c, frequency, q) == pytest.approx(np.sqrt(np.mean(force ** 2)), rel=1e-12)


def test_harmonic_resonance_not_false_copper_loss():
    from bnib import loads
    m, k = .004, 4.
    f = math.sqrt(k / m) / (2 * math.pi)
    n = loads.NibModel("test", kind="translation", m_eff_tip=m, k_tip=k, m_nib=0)
    r = loads.loads_at(n, math.radians(50), 0, .15, loads.Duty(f=f, q_rms=.001))
    assert r["P_dynamic_W"] == pytest.approx(0., abs=1e-25)
    # A negative stiffness increases inertial demand; it cannot be RSS-discarded.
    n.k_tip = -k
    assert loads.loads_at(n, math.radians(50), 0, .15, loads.Duty(f=f, q_rms=.001))["D_dynamic_rms"] == pytest.approx(.008)


def test_wire_compatibility_and_zero_deflection():
    r = wire_anchor(.0017, length=.032, anchor_stiffness=1000.)
    assert r["elongation_m"] == pytest.approx(r["anchor_motion_m"] + r["wire_stretch_m"], rel=1e-9)
    assert .5 * .0017 ** 2 / .032 < r["elongation_m"] < .61 * .0017 ** 2 / .032
    z = wire_anchor(0.)
    assert z["lateral_force_N"] == z["extra_tension_N"] == z["elastic_energy_J"] == 0.


@pytest.mark.parametrize("anchor_k", [100., 1000., 10000., 1e8])
def test_wire_force_is_energy_derivative(anchor_k):
    q, h = .0012, 1e-8
    r = wire_anchor(q, anchor_stiffness=anchor_k)
    ep = wire_anchor(q + h, anchor_stiffness=anchor_k)["elastic_energy_J"]
    em = wire_anchor(q - h, anchor_stiffness=anchor_k)["elastic_energy_J"]
    assert r["lateral_force_N"] == pytest.approx((ep - em) / (2 * h), rel=2e-6)


def test_softer_anchor_reduces_geometric_force_without_free_energy():
    stiff = wire_anchor(.0012587, anchor_stiffness=10000.)
    soft = wire_anchor(.0012587, anchor_stiffness=1000.)
    assert soft["lateral_force_N"] < stiff["lateral_force_N"]
    assert soft["extra_tension_N"] < stiff["extra_tension_N"]
    assert soft["anchor_motion_m"] > stiff["anchor_motion_m"]
    assert soft["goodman_sf_conservative"] > stiff["goodman_sf_conservative"]


def test_preload_causes_drag_at_zero_external_moment():
    r = thrust_guide([0., 0.])
    assert r["loads_per_ball_N"] == pytest.approx([4/6] * 12)
    assert r["rolling_force_N"] == pytest.approx(.008)
    assert r["max_hertz_GPa"] > 0
    assert r["unloaded_contacts"] == 0


def test_guide_equilibrium_and_rotation_invariance():
    x = thrust_guide([.011, 0])
    y = thrust_guide([0, .011])
    assert x["equilibrium_residual_N"] < 1e-8
    assert y["equilibrium_residual_N"] < 1e-8
    # Six discrete balls are not perfectly isotropic at finite tilt.
    assert x["total_normal_load_N"] == pytest.approx(y["total_normal_load_N"], rel=2e-4)
    assert np.linalg.eigvalsh(np.array(x["stiffness_matrix"])).min() > 0
    high = thrust_guide([.03, 0], preload_per_race=.1)
    assert high["unloaded_contacts"] > 0


def test_hertz_contact_stiffness_matches_finite_difference():
    r = thrust_guide([.005, .003])
    a = thrust_guide([.005 + 1e-7, .003])
    b = thrust_guide([.005 - 1e-7, .003])
    compliance = np.linalg.inv(np.array(r["stiffness_matrix"]))
    dt = (np.array(a["tilt_rad"]) - b["tilt_rad"]) / 2e-7
    assert dt == pytest.approx(compliance[1:, 1], rel=1e-5)


def test_current_allocation_preserves_direction_and_respects_limits():
    K = np.array([[.3, -.08], [.04, .24]])
    r = electrical_allocation(K, [.4, -.2], [.02, -.03], copper_power_limit=.08)
    assert r["feasible"] and 0 < r["authority"] < 1
    assert r["force_N"] == pytest.approx(np.array([.4, -.2]) * r["authority"])
    assert max(abs(x) for x in r["voltage_V"]) <= 3.3 + 1e-12
    assert max(abs(x) for x in r["current_A"]) <= 1.0 + 1e-12
    assert r["copper_power_W"] <= .08 + 1e-12


def test_electrical_reciprocity():
    Km = np.array([[.3, -.04], [.02, .24]])
    f, v = np.array([.01, -.02]), np.array([.02, .03])
    r = electrical_allocation(Km, f, v)
    assert r["authority"] == 1.
    assert np.array(r["current_A"]) @ np.array(r["back_emf_V"]) == pytest.approx(f @ v)


def test_back_emf_alone_can_make_request_infeasible():
    r = electrical_allocation(np.eye(2), [0, 0], [10, 0])
    assert not r["feasible"]


def test_magnetic_scale_and_interlayer_copper_accounting():
    from bnib.magnetics import ChkGeom
    g = ChkGeom(w=.005, e=.002, t_x=.0008, t_y=.0008)
    s = CoilShape(.002, .0004, .002, .0048)
    p = np.array([[0., 0.]])
    a = winding_map(g, s, p, "xy", quadrature=(2, 1, 8))
    b = winding_map(g, s, p, "xy", field_scale=.7, quadrature=(2, 1, 8))
    c = winding_map(g, s, p, "xyyx", quadrature=(2, 1, 8))
    assert b["wrench_per_sqrtW"] == pytest.approx(a["wrench_per_sqrtW"] * .7)
    assert c["copper_mass_kg"].sum() < a["copper_mass_kg"].sum()
    assert np.diag(a["wrench_per_sqrtW"][0,:2,:]).min() > 0


def test_clean_checkout_uses_recorded_design_and_calibration(tmp_path,monkeypatch):
    from bnib import actuators as A, sim as S, interface as I
    import json
    from bnib import REPO_ROOT
    monkeypatch.setattr(A,'CAL_PATH',tmp_path/'absent.json')
    monkeypatch.setattr(A,'_CAL',None)
    monkeypatch.setattr(S,'BUILD',tmp_path)
    cal=A.calibration()
    assert cal['recovery']['matrix_rank']==9
    assert cal['recovery']['max_log_residual']<1e-9
    assert cal['rel_max_holdout']<.03
    d,x=I.recommended_design()
    recorded=json.loads((REPO_ROOT/'results/bnib/bnib.json').read_text())['recommended']
    assert x==recorded['x']
    km=float(A.vc_axial(d.w,d.t_m,d.t_c,d.travel+.0002)['Km0'])
    assert km==pytest.approx(recorded['Km_tip'],rel=1e-9)
