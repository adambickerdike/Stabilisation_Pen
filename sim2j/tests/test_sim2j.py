"""Fast checks of the Rev J closed-loop study (about 30-60 s with a warm numba cache): pytest sim2j/tests -q"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

import sim2j
from sim2j import ROOT, RESULTS


# ----------------------------------------------------------------------------- tracker port
def test_online_akf_is_bit_exact_with_fusion():
    """sim2j.akf_online runs the fusion AKF per firmware tick; on the same streams it must equal fusion's batch run."""
    from fusion import estimators as ES
    from fusion.sensors import Streams
    from sim2j import akf_online as AO
    from sim2 import sensors as SS
    rng = np.random.default_rng(3)
    T = 3.0
    tick = np.arange(0.0, T, 0.5e-3)
    ta = np.arange(0.0, T, 1.0 / 3840.0)
    tr = 0.5e-3 * np.column_stack([np.sin(2 * np.pi * 8.0 * ta), np.cos(2 * np.pi * 8.0 * ta)])
    acc = -(2 * np.pi * 8.0) ** 2 * tr + 0.02 * rng.standard_normal((len(ta), 2))
    tp = np.arange(0.0, T, 1e-3)
    wr = np.column_stack([0.02 * tp, 0.002 * np.sin(2 * np.pi * 1.5 * tp)])
    pos = wr + 0.5e-3 * np.column_stack([np.sin(2 * np.pi * 8.0 * tp), np.cos(2 * np.pi * 8.0 * tp)])
    st = Streams(tick_t=tick, acc_t=ta, acc_av=ta + 0.35e-3, acc=acc, pos_t=tp, pos_av=tp + 2e-3, pos=pos,
                 pos_ok=np.ones(len(tp)), con_t=tp, con_av=tp + 1e-3, con=np.ones(len(tp)))
    prm = SS.revh_params()
    a, info_a = ES.akf(st, prm)
    b, info_b = AO.run_batch_equivalent(st, prm)
    assert np.max(np.abs(a - b)) == 0.0
    assert np.max(np.abs(info_a["f_est"] - info_b["f_est"])) == 0.0


def test_line_detector_opens_on_a_tremor_line_and_not_on_a_ramp():
    from sim2j.akf_online import LineDetector
    for amp, want in ((0.5e-3, 1.0), (0.0, 0.0)):
        det = LineDetector()
        t = np.arange(0.0, 6.0, 1e-3)
        y = np.column_stack([0.02 * t + amp * np.sin(2 * np.pi * 8.0 * t), 0.001 * np.sin(2 * np.pi * 1.0 * t)])
        g = 0.0
        for k in range(len(t)):
            det.push(t[k], y[k], True)
            if k % 50 == 0:
                g, f, r = det.update(t[k])
        assert g == want
    assert abs(det.f_line - 8.0) < 1.0 or want == 0.0


# ----------------------------------------------------------------------------- writers
def test_v2_writer_kinematics_are_in_the_fitted_range():
    from sim2j import writers as WV
    wr = WV.writer(1010, "v2").write("return", dt=1e-3, seed=7)
    k = WV.kinematics(WV.written_items([wr]))
    assert 12.0 < k["speed_mm_s"]["mean"] < 55.0  # CON-20 target about 30 mm/s (writers drawn from N(30.5, 7.9))
    assert k["beta"]["mean"] is None or 0.3 < k["beta"]["mean"] < 1.3   # speed-curvature exponent (2/3 law target)
    assert WV.writer(1010, "v1") is not None


# ----------------------------------------------------------------------------- assembly
def test_revj_assembly_mass_properties():
    from sim2 import params as P
    from sim2j import revj as RJ
    if RJ.lead_available():
        hp, npar, rf, _ = RJ.lead_parts()
        H = P.rigid_props(hp)
        lead = RJ.lead()["sp"]["handle"]
        assert H["m"] == pytest.approx(lead["mass_base_kg"]["value"], rel=1e-3)
        assert H["z_g"] == pytest.approx(lead["com_base_m"]["value"][2], abs=0.2e-3)
        hp_e, _, _, _ = RJ.lead_parts(endcap=True)
        assert P.rigid_props(hp_e)["m"] == pytest.approx(lead["mass_with_endcap_kg"]["value"], rel=2e-3)
        R = P.rigid_props(rf)
        assert R["m"] == pytest.approx(RJ.lead()["sp"]["refill"]["moving_mass_kg"]["value"], rel=1e-3)
    hp, npar, rf, info = RJ.revj_parts()
    assert P.rigid_props(hp)["m"] * 1e3 == pytest.approx(RJ.MASS["handle_g"] + 6.6 * 1.1, rel=0.02)


def test_static_ball_load_needs_coil_power():
    """CALC: the refill spring's transverse ball load F_c cot(theta) held by the C1S nose's coils."""
    from sim2j import revj as RJ
    cfg = RJ.config(dt=50e-6)
    th = math.radians(cfg.geom.theta_deg)
    tau = cfg.geom.z_p * cfg.refill.F_c / math.tan(th)
    P = (tau / (cfg.nose.Km_act * (cfg.geom.z_a - cfg.geom.z_p))) ** 2
    assert 1.0 < P < 2.5                            # about 1.6 W at 0.15 N, 50 deg (Rev H's long arm: about 0.13 W)


# ----------------------------------------------------------------------------- closed loop
@pytest.fixture(scope="module")
def pm():
    from sim2j import revj as RJ
    return RJ.build(RJ.config(heel=True, dt=50e-6))


def _short_scenario(T=0.6, v=0.02):
    from sim.pensim import scenarios as PS
    from stabpen import signals as sg
    dt = 50e-6
    t = np.arange(0.0, T, dt)
    xy = np.column_stack([v * np.clip(t - 0.1, 0, None), np.zeros_like(t)])
    it = sg.Intended(t, xy, np.ones(len(t), bool), np.zeros(len(t)), [])
    sc = PS._assemble(it, np.zeros_like(xy), 1.0, 50.0)
    sc.psi_disp = np.zeros(len(t))
    sc.tremor_obj = None
    return sc


def test_closed_loop_runs_with_wheel_nose_and_relaxed_writer(pm):
    from sim2j import stepper as ST
    from sim2j.firmware import FWConfig
    from sim2 import sensors as SS
    sc = _short_scenario()
    fw = FWConfig(nose="tremor", wheel="tremor", akf=SS.revh_params(), seed=1)
    r = ST.run(pm, sc, fw, {}, mu=0.9, seed=1)
    assert np.all(np.isfinite(r.ink()))
    c = r["contact"] > 0.5
    assert c.mean() > 0.5
    N = r["wN"][c]
    assert 0.3 < float(np.median(N)) < 1.0         # the pod's preload 0.55 N (+ spring)
    r2 = ST.run(pm, sc, FWConfig(seed=2), {}, mu=0.9, seed=2, relaxed={"tau": 0.25, "tau_air": 0.05})
    assert np.all(np.isfinite(r2.ink()))


def test_false_correction_reference_is_exact_for_the_device_off_pen(pm):
    """The same seed and the device off give the same ink (the false correction is measured against it)."""
    from sim2j import stepper as ST
    from sim2j import tasks as TK
    from sim2j.firmware import FWConfig
    sc = _short_scenario(0.4)
    a = ST.run(pm, sc, FWConfig(seed=3), {}, mu=0.9, seed=3)
    b = ST.run(pm, sc, FWConfig(seed=3), {}, mu=0.9, seed=3)
    assert TK.moved(a, b) == 0.0


# ----------------------------------------------------------------------------- results
def test_results_carry_provenance():
    if not os.path.isdir(RESULTS):
        pytest.skip("no results yet")
    for fn in os.listdir(RESULTS):
        if fn.endswith(".json") and fn not in ("samples.json",):
            d = json.load(open(os.path.join(RESULTS, fn)))
            assert "stabpen.provenance" in d or "meta" in d, fn


def test_deltapen_page_error_model():
    """The DeltaPen-like page error (sensing.py, ASSUMPTION on LIT OPT-02): lognormal magnitude with median 23.6 um and
    mean 68.3 um per 10 ms window."""
    import math
    from sim2j import sensing as SE
    assert abs(SE.DP_MEDIAN - 23.6e-6) < 1e-12
    assert abs(SE.DP_MEDIAN * math.exp(0.5 * SE.DP_SIGMA ** 2) - 68.3e-6) < 1e-9
