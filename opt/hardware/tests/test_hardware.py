"""Fast tests of the differentiable hardware model (opt/hardware).

They check code, not physics: agreement with the existing numpy model (sim/pencil/design.py, the stage-check
formulas of analysis/pencil_mechanisms.py, the CAD fit formulas and outputs), exact gradients against finite
differences, the constraint evaluation, the stage registry and the CAD overlay.  Passing them does not
validate any model against hardware.
Run: python3 -m pytest opt/hardware/tests -q
"""
import math
import os
import sys

import numpy as np
import pytest
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from opt.hardware import catalogue as CAT  # noqa: E402
from opt.hardware import model as MD  # noqa: E402
from opt.hardware import optimise as O  # noqa: E402
from opt.hardware import reference as R  # noqa: E402
from opt.hardware import registry as REG  # noqa: E402
from sim.pencil import design as D  # noqa: E402

DT = torch.float64


def _eval_current(**kw):
    x = MD.design_batch([MD.CURRENT])
    opts = MD.current_options(**kw)
    return x, opts, MD.evaluate(x, opts, with_drop=False)


# ---------------------------------------------------------------- agreement with the existing model (< 0.1 %)
def test_stage_loads_stress_match_design_py():
    _x, _o, out = _eval_current()
    ref = R.stage_reference("Q26")
    st = out["stage"]
    pairs = {"F_nom": (out["F_nom"], ref["F_nom"]), "F_b_nib": (st["F_b_nib"][0], ref["F_b_nib"]),
             "k_b_nib": (st["k_b_nib"][0], ref["k_b_nib"]), "k_par_nib": (st["k_par_nib"][0], ref["k_par_nib"]),
             "m_eq_nib": (st["m_eq_nib"][0], ref["m_eq_nib"]), "m_couple_nib": (st["m_couple_nib"][0], ref["m_couple_nib"]),
             "f1": (st["f1"][0], ref["f1"]), "C_axis": (st["C_axis"][0], ref["C_axis"]), "g_V": (st["g_V"][0], ref["g_V"]),
             "stroke_nom": (out["q_nom"][0], ref["stroke_nom"]), "stroke_wc": (out["q_wc"][0], ref["stroke_tol_35_raw"]),
             "F_b_nib_tol": (out["stage_wc"]["F_b_nib"][0], ref["F_b_nib_tol"]),
             "sig_stop": (out["sig_stop"][0], ref["sig_stop_driven"]), "sigma0": (out["sig0"][0], ref["sigma0"]),
             "leaf_sf": (out["leaf_sf"][0], ref["leaf_sf"]), "leaf_stress": (out["leaf_stress"][0], ref["leaf_stress_stop"])}
    for name, (a, b) in pairs.items():
        assert float(a) == pytest.approx(b, rel=1e-3), name          # task criterion 0.1 %
        assert float(a) == pytest.approx(b, rel=1e-9), name          # in fact identical to round-off


def test_L35_matches_design_py():
    cur = dict(MD.CURRENT, w=3.5e-3, d=2.15e-3)
    x = MD.design_batch([cur])
    out = MD.evaluate(x, MD.current_options(topology="L"), with_power=False, with_drop=False)
    st = D.stage("L35")
    assert float(out["stage"]["F_b_nib"][0]) == pytest.approx(st.F_b_nib, rel=1e-9)
    assert float(out["stage"]["f1"][0]) == pytest.approx(st.f1, rel=1e-9)
    F = D.load_extremes("skid", 0.15, 50 * math.pi / 180, 0.15)["R_perp_max"]
    assert float(out["q_nom"][0]) == pytest.approx(st.stroke_under_load(F), rel=1e-9)
    cad = R.cad_exact_gaps("L")
    for k in ("plate_to_bore", "plate_to_plate", "plate_to_refill", "snubber_min_web"):
        assert float(out["geo"]["gaps"][k][0]) * 1e3 == pytest.approx(cad[k], rel=1e-9, abs=1e-12), k


def test_fit_gaps_and_mass_match_cad():
    _x, _o, out = _eval_current()
    exact = R.cad_exact_gaps("Q")
    summ = R.cad_reference("Q")
    for k in ("plate_to_bore", "plate_to_plate", "plate_to_refill", "hall_outer_to_nose_wall", "collar_to_nose_wall",
              "refill_cone_to_skid_aperture", "optical_sensor_to_refill", "snubber_min_web"):
        v = float(out["geo"]["gaps"][k][0]) * 1e3
        assert v == pytest.approx(exact[k], rel=1e-9, abs=1e-12), k
        assert v == pytest.approx(summ[k], abs=5e-4 + 1e-3 * abs(summ[k])), k      # CAD summary rounds to 1 um
    np.testing.assert_allclose(out["geo"]["snub_gaps"][0].numpy() * 1e3, exact["snubber_gaps"], rtol=1e-9)
    assert float(out["mass"]["total_g"][0]) == pytest.approx(summ["mass_total_g"], rel=1e-3)


def test_fixed_geometry_matches_cad_parameters():
    P = R.cad_reference("Q")["parameters_mm"]
    for k in ("od", "wall", "nose_L", "skid_w", "theta_design", "theta_min", "refill_d", "refill_L", "cone_L", "ball_d",
              "socket_d", "collar_L", "collar_od", "snub_t", "clear_min", "batt_d", "cap_L", "L_total"):
        v = MD.FIX[k] / (1e-3 if k not in ("theta_design", "theta_min") else 1.0)
        assert v == pytest.approx(P[k], rel=1e-12), k
    assert tuple(P["snub_stations"]) == MD.FIX["snub_stations"]
    assert MD.FIX["snub_gap_extra"] == pytest.approx(P["snub_gap_extra"] * 1e-3)


# ---------------------------------------------------------------- exact gradients (adjoint) vs finite differences
def _scalar_outputs(x, opts):
    out = MD.evaluate(x, opts)
    return {"q_wc": out["q_wc"][0], "f1": out["stage"]["f1"][0], "mass": out["mass"]["total_g"][0],
            "P_mean": out["P_total_mean"][0], "life": out["life_assist_h"][0],
            "gap_bore": out["geo"]["gaps"]["plate_to_bore"][0], "web": out["geo"]["vec"]["snubber_web_in"][0, 1],
            "sig_stop": out["sig_stop"][0], "drop": out.get("sig_drop_2ms", out["sig_stop"])[0],
            "leaf_sf": out["leaf_sf"][0]}


@pytest.mark.parametrize("topology", ["Q", "Q2L"])
def test_gradients_match_finite_differences(topology):
    base = dict(MD.CURRENT, w=3.0e-3, t=0.9e-3, Lf=33e-3, Lc=5e-3, zg=64e-3, zc0=14e-3, leaf_t=36e-6, leaf_w=1.4e-3,
                leaf_L=6e-3, V=58.0, q_stop=0.45e-3, L_cell=38e-3, n2=0.9 if topology == "Q2L" else 1.0)
    opts = MD.Options(topology=topology, driver="recovery_lt8365", hall="drv5055a4_x2")
    xt = {k: torch.tensor([v], dtype=DT, requires_grad=True) for k, v in base.items()}
    outs = _scalar_outputs(xt, opts)
    names = [n for n in MD.NAMES if not (n == "n2" and topology != "Q2L")]
    for oname, y in outs.items():
        grads = torch.autograd.grad(y, [xt[n] for n in names], retain_graph=True, allow_unused=True)
        for n, gr in zip(names, grads):
            ga = 0.0 if gr is None else float(gr[0])
            h = 1e-6 * abs(base[n])
            xp = {k: torch.tensor([v + (h if k == n else 0.0)], dtype=DT) for k, v in base.items()}
            xm = {k: torch.tensor([v - (h if k == n else 0.0)], dtype=DT) for k, v in base.items()}
            with torch.no_grad():
                fd = (float(_scalar_outputs(xp, opts)[oname]) - float(_scalar_outputs(xm, opts)[oname])) / (2 * h)
            scale = max(abs(fd), abs(ga), 1e-12)
            assert abs(ga - fd) <= 2e-4 * scale + 1e-9 * abs(float(y.detach())) / abs(base[n]), (oname, n, ga, fd)


# ---------------------------------------------------------------- constraints
def test_constraint_evaluation_current_design():
    _x, _o, out = _eval_current()
    g = out["g"]
    # the P0.1.2 design keeps its fit clearances, resonance and mass margin ...
    for k in ("plate_to_bore", "plate_to_plate", "plate_to_refill", "hall_outer_to_nose_wall", "snubber_min_web",
              "axial_clamp_to_gimbal", "f1", "mass", "stop_stress", "leaf_buckling", "leaf_stress"):
        assert float(g[k][0]) >= 0.0, k
    # ... but its leaf is at 6.6 % of the axis stiffness (rule 5 %) and the worst-case stroke is negative
    assert float(g["leaf_cross_ratio"][0]) < 0.0
    assert float(out["q_wc"][0]) < 0.0
    assert float(out["q_nom"][0]) * 1e6 == pytest.approx(276.7, abs=0.1)
    # optimiser vector: every entry finite; epigraph rows present
    prob = O.Problem(MD.current_options(driver="recovery_lt8365", hall="drv5055a4_x2"), fixed={"Fc": 0.15})
    u = prob.u_of(MD.CURRENT, 0.1e-3)[None]
    f, G = prob.eval(u)
    assert torch.isfinite(G).all() and G.shape[1] == len(prob.names)
    assert "epi_stroke" in prob.names and "epi_stop" in prob.names
    i = prob.names.index("epi_stroke")
    assert float(G[0, i]) == pytest.approx((float(out["q_wc"][0]) - 0.1e-3) / 1e-4, rel=1e-9)


def test_power_model_calibration_and_held_out_noise():
    cal = MD.load_calibration()
    if cal is None:
        pytest.skip("results/opt/p1_power_calibration.json not built (python3 -m opt.hardware.calibrate)")
    x = MD.design_batch([MD.CURRENT])
    opts = MD.current_options()
    st = MD.stage(x, opts)
    usable = torch.minimum(MD.stroke(st, MD.skid_load(x["Fc"], 50.0, 0.15)), x["q_stop"] - 0.1e-3)
    # zero noise reproduces the P1 oracle powers (the calibration) exactly
    pw, _ = MD.drive_power(x, opts, st, usable, cal, sigma_n=0.0)
    for case, d in pw.items():
        assert float(d["P_rail_B"][0]) * 1e3 == pytest.approx(cal["cases"][case]["oracle"]["P_rail_classB_mW"], rel=1e-3)
    # held-out noise levels: within 20 % of P1
    for hn in ("3e-07", "1e-06"):
        s = cal["runs"][hn]["summary"]["oracle"]
        pw, _ = MD.drive_power(x, opts, st, usable, cal, sigma_n=float(hn))
        for case, d in pw.items():
            assert float(d["P_rail_B"][0]) * 1e3 == pytest.approx(s["P_rail_classB_mW"][case]["mean"], rel=0.20)
            assert float(d["P_rail_R"][0]) * 1e3 == pytest.approx(s["P_rail_recovery_mW"][case]["mean"], rel=0.20)


def test_scaling_laws_reproduce_catalogue_families():
    """Custom-plate scaling (delta ~ LF^2/t, F ~ w t^2/LF, f ~ t/LF^2) against the PICMA and CTS tables."""
    c = CAT.CERAMICS["PIC252"]
    # PL112.10 from PL128.10 (both PIC252): LF 12, W 9.6
    d = c["delta_f"] * (12 / 28) ** 2
    F = c["F_b"] * (9.6 / 6.15) * (28 / 12)
    f = c["fr"] * (28 / 12) ** 2
    assert d / 100e-6 == pytest.approx(1.0, abs=0.25) and F / 2.1 == pytest.approx(1.0, abs=0.25)
    assert f / 1800.0 == pytest.approx(1.0, abs=0.25)
    c1 = CAT.CERAMICS["PIC251"]
    # PL122.10 (LF 22) and PL140.10 (LF 40, W 11, t 0.55) from PL127.10
    assert c1["delta_f"] * (22 / 27) ** 2 / 310e-6 == pytest.approx(1.0, abs=0.25)
    assert c1["F_b"] * (27 / 22) / 1.25 == pytest.approx(1.0, abs=0.25)
    assert c1["delta_f"] * (40 / 27) ** 2 * (0.67 / 0.55) / 1000e-6 == pytest.approx(1.0, abs=0.25)
    assert c1["F_b"] * (11 / 9.6) * (0.55 / 0.67) ** 2 * (27 / 40) / 0.5 == pytest.approx(1.0, abs=0.25)
    # CTS NAC2224 (0.7 mm) -> NAC2221, NAC2227 (length) and NAC2225 (1.3 mm thickness); free length = L - 3.5 mm
    assert 530 * (17.5 / 28.5) ** 2 / 210 == pytest.approx(1.0, abs=0.1)
    assert 0.92 * (28.5 / 46.5) / 0.58 == pytest.approx(1.0, abs=0.1)
    assert 0.92 * (1.3 / 0.7) ** 2 / 3.4 == pytest.approx(1.0, abs=0.1)          # force ~ t^2
    assert 530 * (0.7 / 1.3) / 365 <= 1.0                                         # stroke ~ 1/t is conservative


# ---------------------------------------------------------------- registry and CAD overlay
def test_registry_roundtrip_reproduces_Q26():
    opts = MD.Options(sweep_mode="cad")
    spec = REG.stage_spec("Q26_regtest", MD.CURRENT, opts, "test", mass_total_g=12.2)
    D.register_stage("Q26_regtest", spec)
    try:
        for tol in (0.0, -0.2):
            a = D.stage("Q26", tol=tol).summary()
            b = D.stage("Q26_regtest", tol=tol).summary()
            for k in ("F_b_nib_N", "k_b_nib_N_per_m", "k_par_nib_N_per_m", "m_eq_nib_g", "m_couple_nib_g", "f1_Hz",
                      "C_axis_small_signal_uF", "lever_nib_per_collar", "free_stroke_nib_um"):
                assert b[k] == pytest.approx(a[k], rel=1e-9), k
    finally:
        D._STAGE_REGISTRY.pop("Q26_regtest", None)


def test_registered_stage_runs_in_P1_like_the_builtin():
    """PencilConfig(stage_key=<registered key>) runs the pencil simulator P1 exactly as the built-in stage it copies."""
    from sim.pencil import model as M
    from sim.pensim import scenarios
    opts = MD.Options(sweep_mode="cad")
    D.register_stage("Q26_p1test", REG.stage_spec("Q26_p1test", MD.CURRENT, opts, "test", mass_total_g=12.2))
    try:
        sc = scenarios.handwriting(seed=3, duration=0.25)
        a = M.run(sc, M.Controller(mode="neutral"), M.PencilConfig(stage_key="Q26"), seed=3)
        b = M.run(sc, M.Controller(mode="neutral"), M.PencilConfig(stage_key="Q26_p1test"), seed=3)
        assert np.allclose(a["q1"], b["q1"], rtol=1e-9, atol=1e-15)
    finally:
        D._STAGE_REGISTRY.pop("Q26_p1test", None)


def test_registered_P02_matches_the_torch_model():
    """The P0.2 entry written by run_study (results/opt/stage_registry.json) reproduces the optimiser's stage."""
    reg = D.registered_stages()
    if "P02" not in reg:
        pytest.skip("no P02 in results/opt/stage_registry.json (run python3 -m opt.hardware.run_study)")
    spec = reg["P02"]
    opts = MD.Options(**{k: v for k, v in spec["options"].items() if k in MD.Options.__dataclass_fields__})
    x = spec["design_SI"]
    st_np = D.stage("P02", V_rail=x["V"])
    st_t = MD.stage(MD.design_batch([x]), opts)
    for F_load in (0.0, 0.10, 0.20):
        assert st_np.stroke_under_load(F_load) == pytest.approx(float(MD.stroke(st_t, torch.tensor(F_load, dtype=DT))),
                                                                rel=1e-6)
    assert st_np.F_b_nib == pytest.approx(float(st_t["F_b_nib"]), rel=1e-6)
    assert st_np.f1 == pytest.approx(float(st_t["f1"]), rel=0.03)      # CAD part list vs model geometry


def test_cad_overlay_default_is_identity():
    pytest.importorskip("cadquery")
    import importlib.util
    spec = importlib.util.spec_from_file_location("pencil_revP", os.path.join(ROOT, "mechanics", "cad", "pencil_revP.py"))
    cadm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cadm)
    assert cadm.parameters("Q") == cadm.parameters("Q", None) == cadm.parameters("Q", {})
    P = cadm.parameters("Q", {"plate_w": 3.0, "z_gimbal": 64.0, "collar_z0": 14.0})
    assert P["plate_w"] == 3.0 and P["lever"] == pytest.approx(64.0 / (64.0 - 15.5))
    with pytest.raises(KeyError):
        cadm.parameters("Q", {"lever": 2.0})
    ov = REG.cad_overlay(MD.CURRENT, MD.Options())
    P2 = cadm.parameters("Q", {k: v for k, v in ov.items()})
    assert P2["hall_gap_extra"] == pytest.approx(0.1)
    # the Hall sensor face moves out by the overlay gap
    assert cadm.hall_nose(P2)[1] - cadm.hall_nose(cadm.parameters("Q"))[1] == pytest.approx(
        0.1 + (P2["nib_travel"] / P2["lever"] - 0.40 / cadm.parameters("Q")["lever"]), abs=1e-9)
    assert P2["z_clamp1"] == pytest.approx((MD.CURRENT["zc0"] + 3e-3 + MD.CURRENT["leaf_L"] + 36e-3) * 1e3)


# ---------------------------------------------------------------- optimiser machinery
def test_augmented_lagrangian_improves_a_small_problem():
    opts = MD.Options(driver="recovery_lt8365", hall="drv5055a4_x2")
    fixed = {k: MD.CURRENT[k] for k in MD.NAMES if k not in ("t", "w", "q_stop")}
    prob = O.Problem(opts, fixed=fixed)
    U0 = prob.u_of(MD.CURRENT, 0.0)[None].repeat(3, 1)
    U0[1:, :-1] = torch.rand(2, prob.n - 1, dtype=DT, generator=torch.Generator().manual_seed(0))
    U, f, G, lam = O.adam_al(prob, U0, iters=200, al_every=50)
    v = O.violation(torch.nan_to_num(G, nan=-10.0))
    assert (v < 0.1).any()
    assert float(f[v < 0.1].max()) > 0.0
