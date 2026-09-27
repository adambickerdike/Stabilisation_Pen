"""Virtual-bench experiments: each identification recovers a known hidden plant (twin test),
and the plant/controller shim reproduces M1 exactly at nominal. SIMULATION only; these check
that the method works on data whose structure is known, not that M1 matches a pen."""
import math

import numpy as np
import pytest

import s2r  # noqa: F401
from s2r import exp_b01b02, exp_b03, exp_b05, fastharness, twin
from s2r import instruments as ins
from sim.pensim import harness, model, scenarios


@pytest.fixture(scope="module")
def nominal():
    return twin.nominal_plant()


def test_shim_identity_reproduces_nominal_m1(nominal):
    ctrl = model.Controller(mode="kfosc", **twin.frozen_kf())
    ov, kw, info = twin.shim(nominal, None, ctrl, 50.0)
    assert info["kappa"] == pytest.approx(1.0, abs=1e-12)
    sc = scenarios.handwriting(seed=201, duration=1.5)
    from dataclasses import replace
    r1 = model.run(sc, ctrl, seed=201)
    r2 = model.run(sc, replace(ctrl, **kw), overrides=ov, seed=201)
    assert np.max(np.abs(r1.xy("tipx") - r2.xy("tipx"))) < 1e-12


def test_shim_keeps_firmware_current_when_kf_differs(nominal):
    pv = dict(nominal)
    pv["actuator.Kf"] = 1.2 * nominal["actuator.Kf"]
    ov, kw, info = twin.shim(pv)
    assert info["kappa"] == pytest.approx(1.2)
    P, _ = model.build_params(twin._dummy_scn(), model.Controller(), overrides=ov)
    Pn, _ = model.build_params(twin._dummy_scn(), model.Controller())
    from sim.pensim.layout import IDX
    # the current commanded for a given position error is unchanged: Kp / (n Kf) is the firmware's
    assert P[IDX["Kp"]] / P[IDX["Kf"]] == pytest.approx(Pn[IDX["Kp"]] / Pn[IDX["Kf"]])
    assert P[IDX["Kp_i"]] == pytest.approx(Pn[IDX["Kp_i"]])


def test_fastharness_matches_repository_harness(nominal):
    ov, kw, _ = twin.shim(nominal)
    case = dict(seed=203, f0=9.0, amp=3e-4, mode="kfosc", ctrl={**twin.frozen_kf(), **kw}, overrides=ov,
                duration=3.0)
    a = harness.eval_case(case)
    b = fastharness.eval_case(case)
    for k, v in a.items():
        if isinstance(v, float):
            assert v == b[k] or (math.isnan(v) and math.isnan(b[k])), k


def test_b03_recovers_coupon(nominal):
    rng = np.random.default_rng(10)
    ds = exp_b03.generate(nominal, rng)
    est = exp_b03.identify(ds, rng)["estimates"]
    for k in ("actuator.Kf", "actuator.R20", "actuator.L", "actuator.Rth_coil_amb", "actuator.Cth_coil"):
        assert abs(est[k]["value"] - nominal[k]) <= est[k]["U95"] + 1e-12, k
    assert not est["actuator.Kf"]["protocol_dT_rule_2K_met"]     # 0.6 A for 2 s heats the coil > 2 K


def test_b05_recovers_stage_on_m1(nominal):
    pv = dict(nominal)
    pv.update({"stage.k_tip": 110.0, "stage.m_eq": 0.0125, "stage.zeta_open": 0.03, "sensing.hall_delay": 150e-6})
    rng = np.random.default_rng(11)
    ds = exp_b05.generate(pv, rng, n_chirps=2, T_c=4.0)
    res = exp_b05.identify(ds, pv["actuator.Kf"], 0.003, L_hat=pv["actuator.L"], R20_hat=pv["actuator.R20"])
    e = res["estimates"]
    assert e["stage.k_tip"]["value"] == pytest.approx(110.0, rel=0.02)
    assert e["stage.m_eq"]["value"] == pytest.approx(0.0125, rel=0.03)
    assert e["stage.zeta_open"]["value"] == pytest.approx(0.03, rel=0.03)
    assert abs(e["sensing.hall_delay"]["value"] - 150e-6) < 15e-6
    assert res["diag"]["coherence_min_fit_band"] > 0.9


def test_b05_axial_and_static_fits():
    rng = np.random.default_rng(12)
    ses = ins.draw_session(rng)
    for kax, Fp in ((600.0, 0.2), (2000.0, 0.25), (9000.0, 0.35)):
        r = exp_b05.id_axial(exp_b05.ds_axial(kax, Fp, rng, ses))
        assert r["axial_k"] == pytest.approx(kax, rel=0.03)
        assert r["axial_preload"] == pytest.approx(Fp, abs=0.02)
    # a probe force that reaches the stop: the fit must use only the linear part
    st = exp_b05.id_static_tip(exp_b05.ds_static_tip(30.0, rng, ses, F_max=0.03))
    assert st["k_tip"] == pytest.approx(30.0, rel=0.03)


def test_tribometer_steady_friction_is_lugre_curve():
    c = exp_b01b02.Contact(5e4, 5.0, 0.15, 0.195, 2e-3, 1e-5)
    for v in (1e-4, 2e-3, 3e-2):
        n = int(4.0 / exp_b01b02.DT)
        t, out = exp_b01b02.simulate(c, np.full(n, v), np.zeros(n), np.full(n, 1.0), rec_hz=1000.0)
        sel = t > 3.0
        mu = np.mean(np.abs(out[sel, 3]) / out[sel, 0])
        g = c.mu_k + (c.mu_s - c.mu_k) * math.exp(-(v / c.v_s) ** 2)
        assert mu == pytest.approx(g, rel=0.01)


def test_b01b02_reduced_identification(nominal):
    rng = np.random.default_rng(13)
    ds = exp_b01b02.generate(nominal, rng, reduced=True)
    r = exp_b01b02.identify(ds, None)
    e = r["estimates"]
    assert e["writing.mu_eff"]["value"] == pytest.approx(0.15, rel=0.03)
    assert e["writing.stribeck_speed"]["value"] == pytest.approx(2e-3, rel=0.2)
    assert e["friction.x_presliding"]["value"] == pytest.approx(1e-5, rel=0.05)
    assert e["writing.paper_stiffness"]["value"] == pytest.approx(5e4, rel=0.05)
    assert r["diag"]["recip_R2_pooled"] > 0.9
