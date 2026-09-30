"""Tests of study B (bnib): statics, balance, models, optimiser chain, interface file, evidence rows (< 1 min)."""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

import bnib  # noqa: F401  (paths, one BLAS thread)
from bnib import balance as BL
from bnib import candidates as CD
from bnib import contact as C
from bnib import flexure as FX
from bnib import loads as LD
from bnib import thermal as TH

D2R = math.pi / 180.0


def test_review_static_power_reproduced():
    P = [C.review_static_power(t)["P_W"] for t in (35.0, 50.0, 75.0)]
    assert P == pytest.approx([4.7165, 1.6282, 0.1660], abs=2e-3)
    t = TH.review_check()
    assert t["1.628W"] == pytest.approx(43.8, abs=0.2)
    assert t["2.68W"] == pytest.approx(21.9, abs=0.2)


@pytest.mark.parametrize("th", [35.0, 50.0, 75.0])
def test_vector_statics_frictionless(th):
    t = th * D2R
    c = C.contact_force(t, 0.15)
    assert c["N"] == pytest.approx(0.15 / math.sin(t))
    q = C.nib_load(t, 0.0, 0.15)
    assert q[0] == pytest.approx(0.15 / math.tan(t))
    assert q[1] == pytest.approx(0.0, abs=1e-12)


def test_friction_band_and_vectorised_stats():
    t = 50 * D2R
    lo, hi = C.side_load_friction_band(t, 0.15, 0.15)
    assert lo < 0.15 / math.tan(t) < hi
    st = C.writing_load_stats(t, 0.3, 0.15, "oil_common", 1.0, n_dir=36, v=30e-3)
    mu = st["mu"]
    Q = []
    for k in range(36):
        ang = 2 * math.pi * k / 36
        fr = C.frame(t, 0.0)
        v = math.cos(ang) * fr["h"] + math.sin(ang) * fr["t2"]
        Q.append(C.nib_load(t, 0.3, 0.15, mu, v))
    assert np.allclose(np.mean(Q, axis=0), st["mean_sliding"], rtol=1e-9, atol=1e-12)


def test_contact_jacobian():
    for th in (35.0, 60.0):
        t = th * D2R
        J = C.contact_jacobian(t, 0.0)
        assert np.allclose(J["J_ink_per_nib"], np.diag([1 / math.sin(t), 1.0]), atol=1e-12)
        assert J["slide_per_nib"][0] == pytest.approx(math.cos(t) / math.sin(t))


def test_counterface_cancels_static_load_exactly():
    cf = BL.CounterFace(tilt_err=0.0, roll_err=0.0, comp_weight=False)
    rng = np.random.default_rng(1)
    for _ in range(20):
        th, ph = rng.uniform(35, 75) * D2R, rng.uniform(0, 2 * math.pi)
        b = cf.balance_force(None, th, ph, 0.15, LD.Duty())
        q = C.nib_load(th, ph, 0.15)
        assert np.allclose(b["B_contact"] + q, 0.0, atol=1e-12)
        assert np.allclose(b["B_penup"], 0.0)


def test_counterface_weight_compensation():
    nib = LD.NibModel(name="t", kind="translation", m_nib=3.5e-3, m_eff_tip=3.5e-3)
    cf = BL.CounterFace(tilt_err=0.0, roll_err=0.0, comp_weight=True, F_s_nom=0.15)
    for th in (35.0, 50.0, 75.0):
        t = th * D2R
        b = cf.balance_force(nib, t, 0.4, 0.15, LD.Duty())
        q = C.nib_load(t, 0.4, 0.15)
        g = LD.gravity_load(nib, t, 0.4)
        assert np.allclose(b["B_contact"] + q + g, 0.0, atol=1e-10)


def test_duty_model_had_no_static_term():
    nd = LD.nose2_duty_model()
    assert nd["terms_tremor_duty"]["static_side_load_N"] == 0.0
    assert nd["P_tremor_W"] < 0.5


def test_surrogate_calibration_quality():
    from bnib import actuators as A
    cal = A.calibration()
    assert cal.get("fitted")
    assert cal["rel_rms_holdout"] < 0.02


def test_wire_stiffness_limits():
    E, I, L = 114e9, math.pi * (0.15e-3) ** 4 / 64, 25e-3
    k0 = FX.k_wire_lateral(E, I, L, 0.0)
    assert k0 == pytest.approx(12 * E * I / L ** 3)
    assert FX.k_wire_lateral(E, I, L, 1e-6) == pytest.approx(k0, rel=1e-3)
    assert FX.k_wire_lateral(E, I, L, 0.5) > k0 > FX.k_wire_lateral(E, I, L, -0.05)


def test_torch_chain_matches_evaluator_and_gradients():
    import torch
    from dataclasses import replace
    from bnib import optimise as OP
    x = OP.x0_for("c_counterface", "pen24", OP.SPACES["translation"])
    d = OP.build("c_counterface", "pen24", x)
    r = CD.evaluate(replace(d, km_scale=OP.KM_OBJ), detail=False, fast=True)
    z = {k: torch.tensor(x[k], dtype=torch.float64) for k in ("w", "t_m", "t_c")}
    assert float(OP.p_cont_torch("c_counterface", "pen24", x, z)["P"]) == pytest.approx(r["P_cont_W"], rel=1e-9)
    gc = OP.gradient_check("c_counterface", "pen24", x)
    assert max(v["rel_err"] for v in gc.values()) < 1e-5


def test_counterface_beats_unbalanced():
    g = CD.pen24()
    rc = CD.evaluate(CD.make("c_counterface", g), detail=False, fast=True)
    rf = CD.evaluate(CD.make("f_translation", g), detail=False, fast=True)
    assert rc["P_cont_W"] < 0.3 * rf["P_cont_W"]
    assert rc["travel_under_load_mm"] >= 0.99


def test_governor_caps_skin():
    tn = TH.TwoNode(C_c=0.5, C_s=6.0, R_cs=15.0, R_sa=40.0, T_room=30.0)
    r = tn.simulate(np.full(60000, 1.0), 0.05, governor=True)
    assert r["T_skin"].max() <= tn.T_s_target + 0.2
    assert r["T_coil"].max() <= tn.T_c_max


def test_deltapen_calibration():
    from bnib import sim as SM
    cal = SM.deltapen_calibration(n=100000)
    assert cal["window_diff_median_um"] == pytest.approx(23.6, rel=0.02)
    assert cal["window_diff_mean_um"] == pytest.approx(68.3, rel=0.02)


def test_interface_file_consistent():
    from bnib import CONFIG_NIB
    from bnib import interface as IF
    if not os.path.exists(CONFIG_NIB):
        pytest.skip("config/nib.yaml not generated yet")
    doc = IF.load()
    assert doc["schema"] == IF.SCHEMA
    assert IF.leaves_missing_status(doc) == []
    d, _ = IF.recommended_design()
    ev = CD.evaluate(d, detail=False, fast=True)
    assert doc["actuator"]["Km_tip_centre"]["value"] == pytest.approx(ev["Km_tip"], rel=1e-4)
    assert doc["ink_force"]["spring_force_along_pen_F_s"]["value"] == pytest.approx(d.F_s)


def test_evidence_rows_header_and_ids():
    from bnib import evidence as EV
    assert EV.check_header()
    allowed = {"ACT": range(140, 155), "AMF": range(200, 220), "OPT": range(75, 85), "CON": range(95, 100),
               "HAP": range(135, 140), "PAT": range(55, 60)}
    for r in EV.rows():
        pre, num = r["id"].split("-")
        assert int(num) in allowed[pre]
        assert r["lead_verification"] == ""


def test_layout_fits():
    from bnib import interface as IF
    from bnib import layout as LY
    d, _ = IF.recommended_design()
    ev = CD.evaluate(d, detail=False, fast=True)
    geo = LY.geometry(d, ev)
    assert geo["fit_checks"]["all_pass"]


def test_sim_builds_and_steps():
    from bnib import sim as SM
    import sim2j.tasks as TK
    designs = SM.sim_designs()
    sd = designs["B1"]
    pm = SM.build(sd, 50.0)
    assert pm.info["bnib"]["m_tip_equiv_g"] == pytest.approx(sd.ev["hw"]["m_move"] * 1e3, rel=0.05)
    case = TK.WriterCase(0, version="v2", text="r", pre_s=0.2)
    env = SM.case_env(0, 200)
    r = SM.run(pm, case.scenario(), SM.fw_config("none", 200, 0), sd, seed=200, ink=env["ink"], paper=env["paper"],
               face_err=env["face_err"], t_end=0.15)
    assert np.all(np.isfinite(r["q1"]))
    c = r["contact"] > 0.5
    assert c.mean() > 0.5
    assert np.mean(r["Fface"][c]) == pytest.approx(0.15 / math.sin(50 * D2R), rel=0.05)


def test_servo_gate_gets_the_firmware_contact():
    """DEC-076: the servo's bias/authority gate gets the firmware's delayed measured contact, as sim2j's RevJStepper;
    the true contact force only with contact_source 'legacy_force'."""
    from bnib import sim as SM
    import sim2j.tasks as TK
    sd = SM.sim_designs()["B1"]
    pm = SM.build(sd, 50.0)
    case = TK.WriterCase(0, version="v2", text="r", pre_s=0.2)
    env = SM.case_env(0, 200)
    for source in ("measured", "legacy_force"):
        st = SM.BStepper(pm, case.scenario(), SM.fw_config("none", 200, 0), sd, seed=200, ink=env["ink"],
                         paper=env["paper"], face_err=env["face_err"], t_end=0.05)
        st.contact_source = source
        seen, ref_tick = [], st.servo.ref_tick

        def spy(t, tick, tip, in_contact, direct_q=None, st=st, seen=seen, ref_tick=ref_tick):
            seen.append((bool(in_contact), bool(st.fw.contact), bool(st._in_c)))
            return ref_tick(t, tick, tip, in_contact, direct_q=direct_q)
        st.servo.ref_tick = spy
        st.advance(st.n)
        gate, firmware, true = np.array(seen).T
        if source == "measured":
            assert np.array_equal(gate, firmware) and np.any(gate != true)
        else:
            assert np.array_equal(gate, true)


def _refill_lateral(theta, face, F, h, fh, ft2=0.0):
    """Solve the refill's force balance (unknowns N, R1, R2: bushing forces along t1, t2) for a face push -F n
    (face=True) or a spring push -F a from the carrier (face=False), axial guide friction h along a, and the ball's
    drag f = fh h_hat + ft2 t2 in the paper (independent 3-D statics)."""
    fr = C.frame(theta, 0.0)
    a, n, h_, t1, t2 = fr["a"], fr["n"], fr["h"], fr["t1"], fr["t2"]
    ext = (-F * n if face else -F * a) + h * a + fh * h_ + ft2 * t2
    A = np.column_stack([n, t1, t2])            # N n + R1 t1 + R2 t2 = -ext
    N, R1, R2 = np.linalg.solve(A, -ext)
    return N, R1, R2


@pytest.mark.parametrize("th", [35.0, 50.0, 75.0])
def test_counterface_statics_independent(th):
    t = th * D2R
    # no friction: the face leaves nothing across the pen; the spring leaves F cot(theta)
    N, R1, R2 = _refill_lateral(t, True, 0.2, 0.0, 0.0)
    assert abs(R1) < 1e-12 and abs(R2) < 1e-12 and N == pytest.approx(0.2)
    N, R1, R2 = _refill_lateral(t, False, 0.15, 0.0, 0.0)
    assert abs(R1) == pytest.approx(0.15 / math.tan(t))
    # the drag term f_h / sin(theta) and the guide term h cot(theta) are the same in both designs
    _, R1f, _ = _refill_lateral(t, True, 0.2, 0.01, 0.03)
    _, R1s, _ = _refill_lateral(t, False, 0.15, 0.01, 0.03)
    assert abs(R1f) == pytest.approx(abs(0.03 / math.sin(t) + 0.01 * math.cos(t) / math.sin(t)), rel=1e-9)
    # the two designs differ by exactly the static side load F_s cot(theta): same drag, same guide friction
    assert abs(R1s - R1f) == pytest.approx(0.15 / math.tan(t), rel=1e-9)


def test_travel_summary_and_sim_findings(tmp_path):
    from bnib import docgen as DG
    from bnib import sim as SM
    rows = SM.Rows(str(tmp_path / "rows.json"))
    base = dict(kind="ET", f0=8.0, amp_mm=2.0, w=0, seed=200)
    for pre, nm, ratio, P in (("test", "B1", 0.7, 0.012), ("travel", "B1w", 0.5, 0.02)):
        for ctl in ("nose", "oracle"):
            rows.rows[f"{pre}|{nm}|ET|8|2|0|200|deltapen|{ctl}"] = dict(
                base, ctl=ctl, design=nm, ratio=ratio - (0.2 if ctl == "oracle" else 0.0), P_nib_W=P, words_app=0.5,
                ink_err_um=100.0)
    tv = SM._travel_summary(rows)
    o = tv["cells"]["ET 8 Hz 2 mm"]["oracle"]
    assert o["ratio_B1"] == pytest.approx(0.5) and o["ratio_B1w"] == pytest.approx(0.3)
    assert tv["cells"]["ET 8 Hz 2 mm"]["nose"]["P_B1w_mW"] == pytest.approx(20.0)
    sim = {"cards": {"B1": {"by_cell": {"ET 8 Hz 1 mm": {"ratio_mean": 0.72, "ratio_oracle": 0.27},
                                        "ET 4 Hz 1 mm": {"ratio_mean": 1.0, "ratio_oracle": 0.35},
                                        "ET 8 Hz 2 mm": {"ratio_mean": 0.7, "ratio_oracle": 0.53}}}}, "travel": tv}
    F = DG.sim_findings(sim)
    assert [k for k, _ in F["active"]] == ["ET 8 Hz 2 mm", "ET 8 Hz 1 mm"]
    assert F["idle_rng"] == "1.00" and F["o_small_rng"] == "0.27-0.35" and F["o_big_rng"] == "0.53"
    assert "ET 8 Hz 2 mm" in F["travel"]
