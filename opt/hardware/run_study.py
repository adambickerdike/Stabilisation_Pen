#!/usr/bin/env python3
"""Hardware optimisation study of the pencil nib stage (opt/hardware).

    python3 -m opt.hardware.run_study                 # everything (heavy steps cached in results/opt/_cache)
    python3 -m opt.hardware.run_study --force         # recompute every cached step
    python3 -m opt.hardware.run_study --skip-p1       # no P1 validation (fast)
    python3 -m opt.hardware.run_study --no-step       # CAD without STEP export

Pipeline: P1 power calibration and drop-stress surrogate (built if missing) -> the current design in the
differentiable model and its agreement with the numpy model -> exhaustive enumeration of the discrete choices
with gradient-based optimisation of the continuous variables -> driver x Hall-sensor enumeration -> CMA-ES global
check -> epsilon-constraint Pareto front -> F_c sweep -> gradients and multipliers at the recommended design ->
FE verification (drop, modes) -> stage registry, P0.2 overlay and CAD rebuild -> P1 validation against the
current design -> figures, results/opt/hardware.json, results/opt/hardware_evidence_rows.csv.
Evidence status: CALCULATION and SIMULATION; nothing is measured.
Runtime: about 1.5-2 h from scratch on one core (enumeration about 1 h); minutes with the caches.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
import warnings

import numpy as np
import torch

from . import OUT, ROOT
from . import catalogue as CAT
from . import model as MD
from . import optimise as O
from . import reference as R
from . import registry as REG
from . import study as S
from sim.pencil import design as D  # noqa: E402
from stabpen import provenance  # noqa: E402

warnings.filterwarnings("ignore", message="The balance properties of Sobol")
CAD_OUT = os.path.join(OUT, "cad")
KEY_REC = "P02"
RING_KEEP = 0.05          # keep the P0.1.2 skid ring if a larger ring buys less than 5 % of the worst-case stroke


def F(v):
    return float(v.reshape(-1)[0]) if isinstance(v, torch.Tensor) else float(v)


def r4(x):
    if isinstance(x, float):
        return float(f"{x:.4g}") if math.isfinite(x) and x != 0.0 else x
    if isinstance(x, dict):
        return {str(k): r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r4(v) for v in x]
    if isinstance(x, (np.floating,)):
        return r4(float(x))
    return x


# ------------------------------------------------------------------------------------------------------------
def ensure_inputs(force=False):
    from . import calibrate, drop_surrogate
    if force or not os.path.exists(MD.CAL_FILE):
        calibrate.main([])
    if force or drop_surrogate.load() is None:
        drop_surrogate.build()
    MD._DROP.clear()


def current_design_checks():
    """The P0.1.2 design in the torch model against design.py / pencil_mechanisms.py / CAD, and the power
    model's held-out check against P1."""
    x = MD.design_batch([MD.CURRENT])
    opts = MD.current_options()
    out = MD.evaluate(x, opts)
    ref = R.stage_reference("Q26")
    cad = R.cad_exact_gaps("Q")
    cadsum = R.cad_reference("Q")
    st = out["stage"]
    agree = {}
    for name, a, b in (("load_design_N", out["F_nom"], ref["F_nom"]), ("F_b_nib_N", st["F_b_nib"], ref["F_b_nib"]),
                       ("k_b_nib", st["k_b_nib"], ref["k_b_nib"]), ("f1_Hz", st["f1"], ref["f1"]),
                       ("stroke_nominal_m", out["q_nom"], ref["stroke_nom"]),
                       ("stroke_worstcase_raw_m", out["q_wc"], ref["stroke_tol_35_raw"]),
                       ("clamp_stress_stop_Pa", out["sig_stop"], ref["sig_stop_driven"]),
                       ("sigma0_Pa", out["sig0"], ref["sigma0"]), ("leaf_buckling_SF", out["leaf_sf"], ref["leaf_sf"])):
        agree[name] = {"model": F(a), "reference": b, "rel_err": F(a) / b - 1.0}
    for k in ("plate_to_bore", "plate_to_plate", "plate_to_refill", "hall_outer_to_nose_wall", "collar_to_nose_wall",
              "refill_cone_to_skid_aperture", "optical_sensor_to_refill", "snubber_min_web"):
        m = F(out["geo"]["gaps"][k]) * 1e3
        agree["gap_" + k + "_mm"] = {"model": m, "reference": cad[k], "rel_err": m / cad[k] - 1.0,
                                     "cad_summary_rounded": cadsum[k]}
    agree["mass_g"] = {"model": F(out["mass"]["total_g"]), "reference": cadsum["mass_total_g"],
                       "rel_err": F(out["mass"]["total_g"]) / cadsum["mass_total_g"] - 1.0,
                       "note": "CAD part masses are rounded to 1 mg"}
    # power model on held-out Hall-noise levels (P1 calibration runs of Q26)
    cal = MD.load_calibration()
    pw_check = {}
    usable = torch.minimum(out["q_nom"], out["q_lim"])
    errs = {"B": [], "R": []}
    for hn in ("3e-07", "1e-06"):
        s = cal["runs"][hn]["summary"]["oracle"]
        pw, _ = MD.drive_power(x, opts, st, usable, cal, sigma_n=float(hn))
        for case, d in pw.items():
            eB = F(d["P_rail_B"]) * 1e3 / s["P_rail_classB_mW"][case]["mean"] - 1.0
            eR = F(d["P_rail_R"]) * 1e3 / s["P_rail_recovery_mW"][case]["mean"] - 1.0
            errs["B"].append(eB)
            errs["R"].append(eR)
            pw_check[f"{hn}_{case}"] = {"model_B_mW": F(d["P_rail_B"]) * 1e3, "P1_B_mW": s["P_rail_classB_mW"][case]["mean"],
                                        "model_R_mW": F(d["P_rail_R"]) * 1e3, "P1_R_mW": s["P_rail_recovery_mW"][case]["mean"]}
    pw_summary = {k: {"mean": float(np.mean(v)), "rms": float(np.sqrt(np.mean(np.square(v)))),
                      "max_abs": float(np.max(np.abs(v)))} for k, v in errs.items()}
    prob = O.Problem(MD.current_options(), fixed={"Fc": 0.15})
    cur = S.summarise(prob, prob.u_of(MD.CURRENT, 0.0).numpy())
    return {"agreement": agree, "power_model_check": {"summary_rel_err": pw_summary, "cases": pw_check,
                                                      "note": "held-out Hall-noise levels 0.3 and 1 um (the model is "
                                                              "calibrated on the zero-noise P1 runs only)"},
            "current_design": cur}


def scaling_check():
    """Custom-plate scaling laws against the catalogue families (AMF-11/AMF-53 PICMA; AMF-54 CTS)."""
    rows = []
    c2, c1 = CAT.CERAMICS["PIC252"], CAT.CERAMICS["PIC251"]
    def picma(name, c, LF, W, T, d_ds, F_ds, f_ds):
        d = c["delta_f"] * (LF / (c["L_free"] * 1e3)) ** 2 * (c["t"] * 1e3 / T)
        Fb = c["F_b"] * (W / (c["w"] * 1e3)) * (T / (c["t"] * 1e3)) ** 2 * (c["L_free"] * 1e3 / LF)
        fr = c["fr"] * (T / (c["t"] * 1e3)) * (c["L_free"] * 1e3 / LF) ** 2
        rows.append({"part": name, "ref": c["ref"], "stroke_pred_over_ds": d / d_ds, "force_pred_over_ds": Fb / F_ds,
                     "resonance_pred_over_ds": fr / f_ds})
    picma("PL112.10", c2, 12, 9.6, 0.67, 100e-6, 2.1, 1800)
    picma("PL122.10", c1, 22, 9.6, 0.67, 310e-6, 1.25, 600)
    picma("PL140.10", c1, 40, 11.0, 0.55, 1000e-6, 0.5, 160)
    # CTS NAC222x from NAC2224 (0.7 mm, L 32, LF 28.5)
    base = dict(d=530e-6, F=0.92, C=170e-9, f=340.0, LF=28.5, t=0.7)
    for name, L, t, d_ds, F_ds, C_ds, f_ds in (("NAC2221", 21, 0.7, 210e-6, 1.5, 105e-9, 920), ("NAC2227", 50, 0.7, 1490e-6, 0.58, 280e-9, 130),
                                                ("NAC2225", 32, 1.3, 365e-6, 3.4, 350e-9, 620), ("NAC2226", 32, 1.8, 250e-6, 6.2, 520e-9, 890),
                                                ("NAC2229", 50, 1.8, 700e-6, 4.0, 860e-9, 330)):
        LF = L - 3.5
        rows.append({"part": name, "ref": "NAC2224",
                     "stroke_pred_over_ds": base["d"] * (LF / base["LF"]) ** 2 * (base["t"] / t) / d_ds,
                     "force_pred_over_ds": base["F"] * (t / base["t"]) ** 2 * (base["LF"] / LF) / F_ds,
                     "capacitance_pred_over_ds": base["C"] * (LF / base["LF"]) * (t / base["t"]) / C_ds,
                     "resonance_pred_over_ds": base["f"] * (t / base["t"]) * (base["LF"] / LF) ** 2 / f_ds})
    return {"rows": rows, "law": "delta_f ~ LF^2/t, F_b ~ w t^2/LF, C ~ w L_el t, f ~ t/LF^2 (fixed layer thickness and "
                                 "field; Euler-Bernoulli bimorph)",
            "note": "thicker CTS plates give MORE stroke than 1/t predicts (NAC2225/2226): the law is conservative for "
                    "thick plates; the PICMA pairs differ by up to 20 % (the datasheet tolerance)", "label": "CALC"}


def p1_statics_check(key, r, F_load=0.17):
    """The differentiable model against the numba P1 core for a registered design (as sim/pencil/tests):
    open-loop drive against a test load F_load in air gives the loaded stroke (the drive is reduced so the stage stays
    off its stops); a released stage rings at f1."""
    from sim.pencil import model as M
    from sim.pensim import scenarios
    from stabpen import signals as sg
    from . import p1_harness as H

    def air(duration, dt=25e-6):
        n = int(round(duration / dt))
        t = np.arange(n) * dt
        it = sg.Intended(t=t, xy=np.zeros((n, 2)), pen_down=np.zeros(n, bool), lift=np.full(n, 5e-3), features=[])
        sc = scenarios._assemble(it, np.zeros((n, 2)), 1.0, 50.0)
        sc.fpush[:] = 0.0
        return sc
    V = r["x"]["V"]
    st = D.stage(key, V_rail=V)
    x = MD.design_batch([r["x"]])
    ms = MD.stage(x, S.opts_from(r["options"]))
    # partial drive so that the loaded stroke stays at 60 % of the stop travel (full drive would end on the stop)
    Fb, kt = F(ms["F_b_nib"]), F(ms["k_tot"])
    phi = min(1.0, (F_load + 0.6 * r["x"]["q_stop"] * kt) / Fb)
    cfg = H.pencil_config(key, V_rail=V, hysteresis=False, overrides={"F_test0": -F_load, "hall_noise": 0.0})
    top = M.run(air(0.25), M.Controller(mode="open", V_fixed=0.5 * V * (1.0 + phi)), cfg)
    q_top = float(top["q1"][-50:].mean())
    cfg2 = H.pencil_config(key, V_rail=V, hysteresis=False, zeta_stage=0.002, overrides={"q_init": 1e-4, "hall_noise": 0.0})
    ring = M.run(air(0.3), M.Controller(mode="open", V_fixed=V / 2), cfg2, rec_hz=40000.0)
    q = ring["q1"]
    zc = np.flatnonzero((q[:-1] < 0) & (q[1:] >= 0))
    f_meas = (len(zc) - 1) / (ring["t"][zc[-1]] - ring["t"][zc[0]])
    m_eff = st.m_eq_nib - st.m_couple_nib ** 2 / ring.info["M_t_kg"]
    f_th = math.sqrt((st.k_b_nib + st.k_par_nib) / m_eff) / (2 * math.pi)
    q_model = (phi * Fb - F_load) / kt
    q_np = (phi * st.F_b_nib - F_load) / (st.k_b_nib + st.k_par_nib)
    return {"load_N": F_load, "drive_fraction": phi, "stroke_P1_um": q_top * 1e6, "stroke_model_um": q_model * 1e6,
            "stroke_design_py_um": q_np * 1e6, "rel_err_P1_vs_model": q_top / q_model - 1.0,
            "f_ring_P1_Hz": f_meas, "f_theory_housing_free_Hz": f_th, "f1_model_Hz": F(ms["f1"]),
            "rel_err_ring": f_meas / f_th - 1.0, "label": "SIMULATION (P1 numba core) vs CALCULATION (torch model)"}


def hall_field_check(travel_col=None, gaps=(0.0, 0.1e-3, 0.2e-3, 0.3e-3)):
    """magpylib: P0.1.2 collar magnet (0.6 x 1 x 1 mm, Br 1.32 T ASSUMPTION) and the nose Hall sensor moved out by a
    gap; peak field over the collar travel and the sensitivities (as analysis/pencil_mechanisms.hall_sensitivity).
    The catalogue table HALL_GAP_TABLE holds these values."""
    import magpylib as magpy
    travel_col = travel_col or 0.40e-3 / 1.3626
    rows = []
    for ge in gaps:
        mag = magpy.magnet.Cuboid(polarization=(1.32, 0, 0), dimension=(0.6e-3, 1.0e-3, 1.0e-3), position=(2.0e-3, 0, 0))
        sensor = np.array([2.74e-3 + 0.3e-3 + ge, 0.0, 0.0])
        h = 5e-6

        def B(dx, dy):
            mag.position = (2.0e-3 + dx, dy, 0.0)
            return mag.getB(sensor)
        grid = np.linspace(-travel_col, travel_col, 7)
        sx = [abs((B(gx + h, gy)[0] - B(gx - h, gy)[0]) / (2 * h)) for gx in grid for gy in grid]
        sy = [abs((B(gx, gy + h)[1] - B(gx, gy - h)[1]) / (2 * h)) for gx in grid for gy in grid]
        Bmax = max(np.linalg.norm(B(gx, gy)) for gx in grid for gy in grid)
        rows.append({"gap_extra_mm": ge * 1e3, "B_max_mT": Bmax * 1e3,
                     "S_x_centre_T_per_m": abs((B(h, 0)[0] - B(-h, 0)[0]) / (2 * h)),
                     "S_y_centre_T_per_m": abs((B(0, h)[1] - B(0, -h)[1]) / (2 * h)), "S_min_over_travel_T_per_m": min(min(sx), min(sy))})
    return {"rows": rows, "travel_collar_mm": travel_col * 1e3,
            "ranges_mT": {"TMAG5170-A2 (x_RANGE 00b)": 150, "DRV5055A4": 169},
            "choice": "sensor moved out 0.1 mm: peak 131 mT inside both ranges, weak-axis sensitivity 72 T/m",
            "label": "SIMULATION (magpylib, linear magnet) with ASSUMPTIONS (Br 1.32 T, 0.3 mm element depth)"}


# ------------------------------------------------------------------------------------------------------------
def pick_recommended(enum_rows, drv_rows, life_min=2.0):
    """Best worst-case usable stroke among feasible designs that meet the life target; ties (within 5 um) go
    to lower power, then lower mass."""
    cands = [r for r in drv_rows + enum_rows if r["feasible"] and r.get("life_assist_h", 0) >= life_min]
    best = max(cands, key=lambda r: r["usable_wc_um"])
    close = [r for r in cands if r["usable_wc_um"] >= best["usable_wc_um"] - 5.0]
    return min(close, key=lambda r: (r["P_total_mean_mW"], r["mass_with_margin_g"]))


def tidy(rec, L_cell=40e-3):
    """Variables that do not act on the stage are returned to their P0.1.2 values when that stays feasible:
    the cell length (it only moves mass and battery life)."""
    x2 = dict(rec["x"], L_cell=L_cell)
    opts = S.opts_from(rec["options"])
    prob = O.Problem(opts, fixed={"Fc": 0.15})
    s = rec["usable_wc_um"] * 1e-6
    row = S.summarise(prob, prob.u_of(x2, s).numpy())
    if row["viol"] < S.FEAS_TOL:
        out = dict(rec)
        out.update({k: v for k, v in row.items() if k not in ("u",)})
        out["tidy"] = f"cell length set to {L_cell * 1e3:.0f} mm (was {rec['x']['L_cell'] * 1e3:.1f} mm)"
        return out
    return dict(rec, tidy="cell length kept (40 mm infeasible)")


def alternatives(rec, enum_rows, force=False, qlim_b=0.40e-3):
    """(a) the same combination with a 0.40 mm nominal soft limit (stops 0.50 mm): more authority in typical writing
    for less worst-case stroke; the skid ring is free (the refill cone needs a larger aperture for longer stops);
    (b) one catalogue-thickness plate per position (0.67 mm, the PICMA layer count: custom width and length only, the
    lowest-risk custom part), the better of the two ceramics; (c) when the recommended design stacks two plates per
    position, the best one-plate-per-position design. The cell length is returned to 40 mm where feasible (tidy).
    Each alternative is cached separately (results/opt/_cache/alt_<a|b|c>.json)."""
    rows = []
    a = None if force else S._load("alt_a")
    if a is None:
        o = dict(rec["options"], q_lim_min=qlim_b)
        fixed = {"Fc": 0.15, **{k: v for k, v in S.FIXED_EXTRA.items() if k != "r_ring"}}
        a = S.solve_combo(S.opts_from(o), fixed=fixed, n_starts=8, iters=900, extra_start=rec["x"],
                          warm=[dict(rec["x"], q_stop=qlim_b + 0.1e-3, r_ring=2.0e-3)])
        a["alt"] = f"soft limit {qlim_b * 1e3:.2f} mm (stops {(qlim_b + 0.1e-3) * 1e3:.2f} mm), skid ring free"
        a = dict(tidy(a), alt=a["alt"])
        S._save("alt_a", a)
    rows.append(a)
    b = None if force else S._load("alt_b")
    if b is None:
        bs = []
        for cer in ("PIC252", "PIC251"):
            o = dict(rec["options"], ceramic=cer, stack=1)
            bs.append(S.solve_combo(S.opts_from(o), fixed={"Fc": 0.15, "t": 0.67e-3, **S.FIXED_EXTRA}, n_starts=8,
                                    iters=900, extra_start=dict(rec["x"], t=0.67e-3)))
        feas = [r for r in bs if r["feasible"]]
        b = dict(max(feas, key=lambda r: r["usable_wc_um"]) if feas else min(bs, key=lambda r: r["viol"]))
        b["alt"] = (f"catalogue plate thickness 0.67 mm, one plate per position, {b['options']['ceramic']} "
                    "(custom width and length only)")
        b["alt_candidates"] = [{"ceramic": r["options"]["ceramic"], "usable_wc_um": r["usable_wc_um"],
                                "feasible": r["feasible"]} for r in bs]
        b = dict(tidy(b), alt=b["alt"])
        S._save("alt_b", b)
    rows.append(b)
    if int(rec["options"]["stack"]) > 1:
        c = None if force else S._load("alt_c")
        if c is None:
            # (c) the best one-plate-per-position combination (no stacked plates), recommended electronics
            single = [r for r in enum_rows if r.get("feasible") and int(r["options"]["stack"]) == 1
                      and r["options"]["topology"] == rec["options"]["topology"]]
            if single:
                s0 = max(single, key=lambda r: r["usable_wc_um"])
                o = dict(s0["options"], **{k: rec["options"][k] for k in ("driver", "hall", "clamp_electroded")})
                x0 = dict(s0["x"], **S.FIXED_EXTRA)
                c = S.solve_combo(S.opts_from(o), fixed={"Fc": 0.15, **S.FIXED_EXTRA}, n_starts=4, iters=600, polish=2,
                                  extra_start=x0, warm=[x0])
                c["alt"] = f"one plate per position ({o['ceramic']}, custom thickness): no stacked plates"
                c = dict(tidy(c), alt=c["alt"])
                S._save("alt_c", c)
        if c is not None:
            rows.append(c)
    return rows


def sensitivities_block(rec):
    opts = S.opts_from(rec["options"])
    sens = O.sensitivities(opts, rec["x"])
    lev = O.lever_derivative(opts, rec["x"])
    # physically named derivatives
    g = sens["q_wc"]["grad"]
    named = {"d_qwc_d_Fc_um_per_10mN": g["Fc"]["d_dx"] * 1e6 * 0.01,
             "d_qwc_d_V_um_per_V": g["V"]["d_dx"] * 1e6,
             "d_qwc_d_t_um_per_0.1mm": g["t"]["d_dx"] * 1e6 * 1e-4,
             "d_qwc_d_w_um_per_0.1mm": g["w"]["d_dx"] * 1e6 * 1e-4,
             "d_qwc_d_Lf_um_per_mm": g["Lf"]["d_dx"] * 1e6 * 1e-3,
             "d_qwc_d_zg_um_per_mm": g["zg"]["d_dx"] * 1e6 * 1e-3,
             "d_qwc_d_zc0_um_per_mm": g["zc0"]["d_dx"] * 1e6 * 1e-3,
             "d_qwc_d_leaf_t_um_per_um": g["leaf_t"]["d_dx"] * 1e6 * 1e-6,
             "d_qwc_d_lever": lev["q_wc"]["d_dn"] * 1e6, "lever": lev["q_wc"]["n"],
             "d_qnom_d_lever": lev["q_nom"]["d_dn"] * 1e6}
    # the same at the current design, for comparison
    cur = O.sensitivities(MD.current_options(), MD.CURRENT)
    levc = O.lever_derivative(MD.current_options(), MD.CURRENT)
    gc = cur["q_wc"]["grad"]
    named_cur = {"d_qwc_d_Fc_um_per_10mN": gc["Fc"]["d_dx"] * 1e6 * 0.01, "d_qwc_d_V_um_per_V": gc["V"]["d_dx"] * 1e6,
                 "d_qwc_d_t_um_per_0.1mm": gc["t"]["d_dx"] * 1e6 * 1e-4, "d_qwc_d_w_um_per_0.1mm": gc["w"]["d_dx"] * 1e6 * 1e-4,
                 "d_qwc_d_Lf_um_per_mm": gc["Lf"]["d_dx"] * 1e6 * 1e-3, "d_qwc_d_lever": levc["q_wc"]["d_dn"] * 1e6,
                 "lever": levc["q_wc"]["n"], "d_qnom_d_lever": levc["q_nom"]["d_dn"] * 1e6}
    def n_star(x, opts):
        xb = MD.design_batch([x])
        st = MD.stage(xb, opts)
        stw = MD.stage(xb, opts, tol=opts.tol_wc)
        Fw = MD.skid_load(xb["Fc"], opts.theta_wc, opts.mu_wc)
        Fn = MD.skid_load(xb["Fc"], opts.theta_nom, opts.mu_nom)
        return {"lever": F(st["n"]),
                "n_star_worst_case": F(stw["k_eff_col"] * stw["delta_col"] / (2 * Fw)),
                "n_star_nominal": F(st["k_eff_col"] * st["delta_col"] / (2 * Fn)),
                "note": "n* = k_eff,collar delta_free / (2 F) maximises the loaded stroke (gimbal stiffness neglected)"}
    named["optimal_lever"] = n_star(rec["x"], opts)
    named_cur["optimal_lever"] = n_star(MD.CURRENT, MD.current_options())
    return {"recommended": sens, "named_recommended": named, "current": cur, "named_current": named_cur,
            "label": "CALCULATION (reverse-mode automatic differentiation of the design model = its adjoint)"}


def verify_fe(rec_like, pulses=(0.5e-3, 1e-3, 2e-3)):
    """True FE drop stress (analysis/pencil_mechanisms.drop_sim) and FE modes at a design, vs the surrogate."""
    from . import drop_surrogate as DS
    pm = DS._pm()
    opts = S.opts_from(rec_like["options"])
    x = MD.design_batch([rec_like["x"]])
    out = MD.evaluate(x, opts)
    st, b = out["stage"], out["stage"]["b"]
    m_tip = F(st["nib"]["m_eq_col"]) / (st["ppa"] * float(opts.stack)) * F(st["n2"]) ** 2
    E = F(b["E_eff"])
    xx = rec_like["x"]
    u_s = F(out["geo"]["u_tip"])
    rows = []
    for T in pulses:
        s = DS.fe_drop(xx["t"], xx["Lf"], xx["w"], u_s, m_tip / (F(b["m_free"]) / opts.stack), E, T=T, pm=pm)
        rows.append({"pulse_ms": T * 1e3, "fe_MPa": s / 1e6, "P_fail": 1 - math.exp(-(s / F(out["sig0"])) ** 8)})
    ds = DS.load()
    mu, sd = ds.predict(conservative=False, return_std=True, t=x["t"], Lf=x["Lf"], w=x["w"], u_s=out["geo"]["u_tip"],
                        mu_tip=torch.tensor([m_tip / (F(b["m_free"]) / opts.stack)], dtype=torch.float64), E=b["E_eff"])
    # FE modes of one plate with the collar share and the parasitic stiffness share at its tip
    kpl = F(b["k1"]) * 3.0 / 3.0
    bender = D.Bender("fe", xx["w"], xx["t"], xx["Lf"], xx["Lf"] + xx["Lc"], 1.0, kpl, 1e-6, float("nan"))
    k_other = F(st["k_par_col"]) / (st["ppa"] * float(opts.stack))
    modes = pm.fe_modes(bender, tip_mass=m_tip, tip_k=k_other)
    return {"drop_fe": rows, "surrogate_mean_2ms_MPa": F(mu) / 1e6 if not isinstance(mu, float) else mu,
            "surrogate_sd_log": F(sd), "surrogate_constraint_value_MPa": F(out["sig_drop_2ms"]) / 1e6,
            "sigma_allow_MPa": F(out["sig_allow"]) / 1e6, "sigma0_MPa": F(out["sig0"]) / 1e6,
            "fe_modes_Hz_one_plate": [float(v) for v in modes], "lumped_f1_Hz": F(st["f1"]),
            "note": "FE modes: one plate with its share of the collar inertia and of the parasitic stiffness at the tip "
                    "(pencil_mechanisms.stage_check convention)", "label": "SIMULATION (FE beam) / CALCULATION"}


# ------------------------------------------------------------------------------------------------------------
def rebuild_cad(key, r, no_step=True):
    """mechanics/cad/pencil_revP.py with the overlay; returns the summary path (or None)."""
    opts = S.opts_from(r["options"])
    if opts.topology not in ("Q", "L"):
        return None, "CAD overlay supports the Q and L layouts only"
    variant = "Q" if opts.topology == "Q" else "L"
    os.makedirs(CAD_OUT, exist_ok=True)
    ov = REG.cad_overlay(r["x"], opts)
    ypath = os.path.join(OUT, f"pencil_{key}_cad_overlay.yaml" if key != KEY_REC else "pencil_P0.2_proposed.yaml")
    if key != KEY_REC:
        import yaml
        with open(ypath, "w") as f:
            yaml.safe_dump({"cad_parameters_mm": ov}, f, sort_keys=False)
    tag = f"pencil_revP{variant}_{key}"
    cmd = [sys.executable, os.path.join(ROOT, "mechanics", "cad", "pencil_revP.py"), "--variant", variant,
           "--overlay", ypath, "--tag", tag, "--out", CAD_OUT] + (["--no-step"] if no_step else [])
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if p.returncode != 0:
        return None, p.stderr[-2000:]
    return os.path.join(CAD_OUT, f"{tag}_summary.json"), f"{time.time() - t0:.1f} s"


def cad_vs_model(summary_path, r):
    d = json.load(open(summary_path))
    s = d["summary"]
    sc = s["section_checks"]
    opts = S.opts_from(r["options"])
    x = MD.design_batch([r["x"]])
    out = MD.evaluate(x, opts, with_power=False, with_drop=False)
    comp = {}
    for k, ck in (("plate_to_bore", "plate_to_bore_mm"), ("plate_to_plate", "plate_to_plate_mm"),
                  ("plate_to_refill", "plate_to_refill_mm"), ("hall_outer_to_nose_wall", "hall_outer_to_nose_wall_mm"),
                  ("collar_to_nose_wall", "collar_to_nose_wall_mm"),
                  ("refill_cone_to_skid_aperture", "refill_cone_to_skid_aperture_at_theta_min_mm"),
                  ("optical_sensor_to_refill", "optical_sensor_to_refill_mm"), ("snubber_min_web", "snubber_min_web_mm")):
        comp[k] = {"model_mm": F(out["geo"]["gaps"][k]) * 1e3, "cad_mm": sc[ck]}
    comp["mass_g"] = {"model": F(out["mass"]["total_g"]), "cad": s["mass_total_g"]}
    comp["lever"] = {"model": F(out["stage"]["n"]), "cad": s["lever_nib_per_collar"]}
    comp["all_ok"] = sc.get("all_ok")
    comp["interference"] = s.get("nib_assembly_interference")
    comp["com_z_mm"] = s.get("com_z_mm")
    return comp


# ------------------------------------------------------------------------------------------------------------
def p1_validate(designs, quick=False, force=False):
    """P1 on the harness grid for each design: seeds 200-203, 4-12 Hz x 0.1/0.3/0.5 mm, neutral and oracle; plus
    the worst-case condition (35 deg, -20 % tolerance, 0.3 mm, seeds 200-201)."""
    from . import p1_harness as H
    H.warm()
    res = {}
    for key, r, label in designs:
        cache = S._load(f"p1_{key}")
        if cache and not force and (key == "Q26" or "grid_hall_1um_0.3mm" in cache):
            res[key] = cache
            continue
        t0 = time.time()
        if key == "Q26":
            cfg_kw, ctrl_kw, pov, info = {}, {}, None, {"hall_noise_m": 1e-6, "V_rail": 60.0, "q_lim_m": 0.30e-3,
                                                        "note": "P0.1.2 as documented (P1 defaults)"}
        else:
            opts = S.opts_from(r["options"])
            sig = r.get("sigma_nib_um", 1.0) * 1e-6
            cfg_kw = {"V_rail": r["x"]["V"], "overrides": {"hall_noise": sig}}
            ctrl_kw = {"q_lim": r["x"]["q_stop"] - opts.servo_margin}
            pov = {"skid.ring_radius": r["x"]["r_ring"]} if abs(r["x"]["r_ring"] - 1.4e-3) > 1e-9 else None
            info = {"hall_noise_m": sig, "V_rail": r["x"]["V"], "q_lim_m": ctrl_kw["q_lim"], "skid_ring_m": r["x"]["r_ring"],
                    "sensor": opts.hall}
        seeds = (200, 201) if quick else H.SEEDS
        f0s = (6.0, 10.0) if quick else H.F0S
        if cache and not force:                     # only the 1 um Hall-noise block is missing
            res[key] = cache
            el = el2 = 0.0
        else:
            rows, el = H.run_grid(key, seeds=seeds, f0s=f0s, modes=("oracle",), cfg_kw=cfg_kw, ctrl_kw=ctrl_kw,
                                  params_overrides=pov)
            wc_cfg = dict(cfg_kw, tol=-0.2)
            rows_wc, el2 = H.run_grid(key, seeds=(200, 201), f0s=f0s, amps=(0.3e-3,), modes=("oracle",), cfg_kw=wc_cfg,
                                      ctrl_kw=ctrl_kw, scn_kw={"theta_deg": 35.0}, params_overrides=pov)
            res[key] = {"label": label, "settings": info, "grid": H.summarise(rows),
                        "worst_case_35deg_minus20pct": H.summarise(rows_wc), "rows": rows, "rows_worst_case": rows_wc,
                        "elapsed_s": el + el2}
        if key != "Q26":
            # sensor-controlled comparison: the recommended stage with the 1 um Hall noise of the P0.1.2 documentation
            cfg1 = dict(cfg_kw, overrides={"hall_noise": 1e-6})
            rows_h, el3 = H.run_grid(key, seeds=(200, 201), f0s=f0s, amps=(0.3e-3,), modes=("oracle",), cfg_kw=cfg1,
                                     ctrl_kw=ctrl_kw, params_overrides=pov)
            res[key]["grid_hall_1um_0.3mm"] = H.summarise(rows_h)
            res[key]["elapsed_s"] += el3
        S._save(f"p1_{key}", res[key])
        print(f"P1 {key}: {el + el2:.0f} s", flush=True)
    return res


def p1_table(p1):
    """Compact comparison: oracle ratio, time at the travel limit, rail powers per grid case."""
    out = {}
    for key, d in p1.items():
        g = d["grid"]
        o = g["oracle"]
        t = {}
        for case in o["ratio"]:
            t[case] = {"oracle_ratio": o["ratio"][case]["mean"], "oracle_ratio_sd": o["ratio"][case]["sd"],
                       "time_at_limit": o["q_sat_frac"][case]["mean"],
                       "P_rail_classB_mW": o["P_rail_classB_mW"][case]["mean"],
                       "P_rail_recovery_mW": o["P_rail_recovery_mW"][case]["mean"],
                       "neutral_e_rms_um": g["neutral"]["e_rms_um"][case]["mean"]}
        w = d["worst_case_35deg_minus20pct"]["oracle"]
        wc = {case: {"oracle_ratio": w["ratio"][case]["mean"], "time_at_limit": w["q_sat_frac"][case]["mean"]}
              for case in w["ratio"]}
        extra = {}
        if "grid_hall_1um_0.3mm" in d:
            gh = d["grid_hall_1um_0.3mm"]["oracle"]
            extra["hall_1um_0.3mm"] = {c: {"oracle_ratio": gh["ratio"][c]["mean"], "P_rail_classB_mW": gh["P_rail_classB_mW"][c]["mean"],
                                           "P_rail_recovery_mW": gh["P_rail_recovery_mW"][c]["mean"]} for c in gh["ratio"]}
        out[key] = {"grid": t, "worst_case": wc, "settings": d["settings"], **extra,
                    "mean_oracle_ratio": float(np.mean([v["oracle_ratio"] for v in t.values()])),
                    "mean_time_at_limit": float(np.mean([v["time_at_limit"] for v in t.values()])),
                    "mean_worstcase_ratio": float(np.mean([v["oracle_ratio"] for v in wc.values()])),
                    "mean_worstcase_time_at_limit": float(np.mean([v["time_at_limit"] for v in wc.values()]))}
    return out


# ------------------------------------------------------------------------------------------------------------
def bom(rec):
    o = rec["options"]
    x = rec["x"]
    drv = CAT.DRIVERS[o["driver"]]
    hall = CAT.HALL[o["hall"]]
    lm = CAT.LEAF_MATERIALS[o["leaf_mat"]]
    cer = CAT.CERAMICS[o["ceramic"]]
    n_pos = 4 if o["topology"] in ("Q", "Q2L") else 2
    n_pl = n_pos * int(o["stack"])
    return [
        {"part": f"{n_pl} x custom PICMA-class multilayer bender {x['w'] * 1e3:.2f} x {(x['Lf'] + x['Lc']) * 1e3:.1f} x "
                 f"{x['t'] * 1e3:.2f} mm, free length {x['Lf'] * 1e3:.1f} mm, {o['ceramic']}"
                 + (", inactive clamp zone" if not o["clamp_electroded"] else "")
                 + (f" ({int(o['stack'])} per position, clamped together with a 0.05 mm spacer; tips not joined to each "
                    "other, each drives the collar through its own leaf half: ASSUMPTION, EXP-Q04)" if int(o["stack"]) > 1 else ""),
         "source": f"PI (custom designs on request, {cer['ledger']}); CTS/Noliac as second source (AMF-54)",
         "status": "custom (supplier standard process)", "key_spec": f"free stroke {rec['free_stroke_nib_um'] / rec['lever']:.0f} um "
         f"(tip, 60 V), per position blocking force at 60 V from the scaling law (CALC)", "ledger": f"{cer['ledger']}; AMF-54; AMF-63"},
        {"part": f"{n_pos} x decoupling leaf {o['leaf_mat']} {x['leaf_t'] * 1e6:.0f} um x {x['leaf_w'] * 1e3:.2f} mm x "
                 f"{x['leaf_L'] * 1e3:.2f} mm span"
                 + (f", slit into {int(o['stack'])} halves at the plate end (one per plate)" if int(o["stack"]) > 1 else ""), "source": "photo-etch service (VACCO / PEI class)", "status": "build",
         "key_spec": lm["label"], "ledger": lm["ledger"] + "; AMF-59"},
        {"part": "piezo drive: " + drv["label"], "source": drv["ledger"], "status": drv["status"], "key_spec": drv["note"],
         "ledger": drv["ledger"]},
        {"part": "stage position sensing: " + hall["label"], "source": hall["ledger"], "status": hall["status"],
         "key_spec": hall["note"], "ledger": hall["ledger"]},
        {"part": "collar (Ti-6Al-4V) with PTFE liner, magnets, etched cross-strip gimbal, PEEK snubber frames, Ti clamp block",
         "source": "CAD mechanics/cad/pencil_revP.py", "status": "build", "key_spec": "as P0.1.2 with the new positions",
         "ledger": "-"},
        {"part": f"cell: custom 6.5 x {x['L_cell'] * 1e3:.1f} mm Li-ion (about {float(MD.cell_capacity_mAh(torch.tensor(x['L_cell']))):.0f} mAh)",
         "source": "cell maker (custom); fallback 3 x Panasonic CG-425A", "status": "custom",
         "key_spec": "capacity ASSUMPTION scaled from AMF-42/43", "ledger": "AMF-42; AMF-43"},
        {"part": "bench prototype plates: PiezoDrive BA3502 (35 x 2.5 x 0.8 mm, LF 28 mm)", "source": "piezodrive.com",
         "status": "catalogue", "key_spec": "USD 11.80 each (seen 2026-09-28); 150 V; for fit, assembly and servo "
                                           "bring-up of the Q stage before custom plates arrive", "ledger": "AMF-55"},
        {"part": "bench driver: TI DRV2700 EVM or DRV8662", "source": "ti.com", "status": "catalogue",
         "key_spec": "105 V boost; 72 mW quiescent for two", "ledger": "AMF-16; AMF-57"},
    ]


def evidence_rows(rec=None, p1tab=None, cur=None, static=None, selection=None):
    base = {"access_level": "full text", "participants_or_bench": "not applicable (manufacturer data; test method not published)",
            "transferability": "medium", "retrieved": CAT.RETRIEVED, "stream": "AMF", "lead_verification": ""}
    rows = [
        dict(base, id="AMF-53", topic="Piezo bender - PI PICMA PL112-PL140: remaining lengths, ceramics and custom designs (supplement to AMF-11)",
             citation="Physik Instrumente (PI). PICMA Bender PL112 - PL140 datasheet, 31.07.2020.", year="2020",
             doi_or_url="https://www.pi-usa.us/fileadmin/user_upload/physik_instrumente/files/datasheets/PL112-PL140-Datasheet.pdf",
             source_type="datasheet", evidence_class="manufacturer statement", task_or_setup="Specifications table; ordering information",
             comparator="CTS NAC222x (AMF-54)",
             key_quantitative_findings="Remaining (free) length LF: PL112 12, PL122 22, PL127 27, PL128 28, PL140 40 mm (lengths 18/25/31/36/45 mm). Height 0.67 mm (PL140 0.55) +/-0.1 mm; width 9.60 +/-0.2 (PL128 6.15 +/-0.1; PL140 11.00). Piezo ceramic PIC252 (PL112, PL128; -20 to 150 degC) or PIC251 (PL122, PL127, PL140; -20 to 85 degC). 0-60 V (+/-30 V) differential; displacement, blocking force, capacitance and resonance +/-20 %. 'Custom designs or different specifications on request.' MY CALC: at equal geometry PIC251 (PL127) gives 24 % more blocking force, 7.5 % more stroke and 2.1x the capacitance of PIC252 (PL128).",
             units_and_conditions="Capacitance at 1 Vpp, 1 kHz, RT, clamped with remaining length LF, no load; resonance at 1 Vpp",
             locator="p. 2 Specifications; p. 4 Ordering information",
             limitations="Custom thickness (layer count) and length are 'on request', not catalogue; no strength data.",
             relevance_to_design="Reference parts for the scaling of custom plates in opt/hardware; free-length and ceramic data fix the reference.",
             transferability="high", transferability_reason="Same supplier and process as the proposed custom plates.",
             design_implication="Specify custom plates by width, free length, clamp length and layer count; quote both PIC252 and PIC251; confirm by EXP-Q04.",
             search_query="WebSearch: PI PICMA bender PL128.10 free length datasheet custom dimensions; WebFetch datasheet PDF (text via pdftotext)"),
        dict(base, id="AMF-54", topic="Piezo bender - CTS (Noliac) NAC222x multilayer plate benders",
             citation="CTS Corporation. Bending Actuators - Plate Benders, datasheet RevC_0524 (2024).", year="2024",
             doi_or_url="https://www.ctscorp.com/Files/DataSheets/Piezoelectric/Multilayer/CTS-Piezoelectric-Multilayer-Plate-Benders-Datasheet.pdf",
             source_type="datasheet", evidence_class="manufacturer statement", task_or_setup="Specification tables (cantilever, nominal clamping length)",
             comparator="PI PICMA (AMF-11, AMF-53)",
             key_quantitative_findings="Width 7.8 mm; lengths 21/32/50 mm; heights 0.7/1.3/1.8 mm; Vmax 200 V; inactive clamping length 3.5 mm; material NCE51F; max 150 degC. NAC2224 (32 x 0.7): +/-530 um, 0.92 N, 2 x 170 nF, 1.7 N/mm, 340 Hz. NAC2225 (32 x 1.3): +/-365 um, 3.4 N, 2 x 350 nF, 9.3 N/mm, 620 Hz. NAC2226 (32 x 1.8): +/-250 um, 6.2 N, 2 x 520 nF, 24.8 N/mm, 890 Hz. NAC2221 (21 x 0.7): +/-210 um, 1.5 N, 2 x 105 nF, 920 Hz. NAC2227 (50 x 0.7): +/-1490 um, 0.58 N, 2 x 280 nF, 130 Hz. Stroke +/-15 %, force +/-20 %, capacitance +/-15 %. 'All the CTS multilayer products can be custom designed.'",
             units_and_conditions="Room temperature, cantilever, nominal clamping", locator="pp. 1-4",
             limitations="200 V drive; 7.8 mm width; blocking force quoted 0 to Vmax.",
             relevance_to_design="Shows multilayer benders are made 0.7-1.8 mm thick with an inactive 3.5 mm clamp zone; checks the thickness and length scaling.",
             transferability_reason="Different material and voltage class; geometry trends transfer.",
             design_implication="Use as scaling evidence and second source for custom plates (low-voltage layer design on request).",
             search_query="WebSearch: Noliac CTS multilayer bender plate CMBP datasheet; curl CTS datasheet PDF"),
        dict(base, id="AMF-55", topic="Piezo bender - PiezoDrive BA series bimorphs (2.5 mm wide BA3502)",
             citation="PiezoDrive. Piezo Bender Actuators (BA series) product table and BA3502 product page.", year="n.d.",
             doi_or_url="https://www.piezodrive.com/actuators/piezo-bender-actuators/ ; https://www.piezodrive.com/product/0-6mm-range-piezo-bender-actuator-ba3502/",
             source_type="manufacturer", evidence_class="manufacturer statement", task_or_setup="Web specification table",
             comparator="PICMA custom 2.6 mm plates (config/pencil.yaml)",
             key_quantitative_findings="BA3502: 35 x 2.5 x 0.8 mm, free length 28 mm, +150 V or +/-90 V AC, deflection 0.7 mm, blocked force 0.08 N, 20 nF, 220 N/m, 230 Hz, 0.3 g, USD 11.80 (available, seen 2026-09-28). BA3610: 36 x 10, 0.85 mm, 0.20 N, 90 nF. BA4010: 40 x 10, 1.1 mm, 0.18 N. BA5010: 50 x 10, 1.5 mm, 0.3 N. BA6020: 60 x 20, 2.6 mm, 0.3 N. Parallel-poled bimorphs with resin coating.",
             units_and_conditions="As listed", locator="Product table", limitations="150 V; about 1/4 of the work of the custom PICMA-class 2.6 mm plate; test method not stated.",
             relevance_to_design="Only catalogue bender found with the Q-plate footprint (2.5 mm wide, 28 mm free).",
             transferability_reason="Real, cheap and available; lower work density and higher voltage.",
             design_implication="Buy for a fit, assembly and servo mock-up of the Q stage before custom plates arrive.",
             search_query="WebSearch: APC International piezo bimorph bender specifications (returned PiezoDrive); curl piezodrive.com pages"),
        dict(base, id="AMF-56", topic="Piezo tube scanners (PI PT230 quartered tubes)",
             citation="PI Ceramic. PT120 - PT140 Piezo Tube Actuators datasheet, R1 13/08/23.", year="2013",
             doi_or_url="https://www.pi-usa.us/fileadmin/user_upload/pi_us/files/product_datasheets/PT120_Piezo_Tube_Actuator.pdf",
             source_type="datasheet", evidence_class="manufacturer statement", task_or_setup="Scanner-tube table",
             comparator="bender stage", key_quantitative_findings="PT230.94 30 x 3.2 x 2.2 mm +/-35 um XY; PT230.14 30 x 6.35 x 5.35 mm +/-16 um; PT230.24 30 x 10 x 9 mm +/-10 um; all +/-250 V, PIC255. Custom: L max 70 mm, OD 2-80 mm, ID 0.8-74 mm, min wall 0.30 mm. Formula dx = 2 sqrt(2) d31 U L^2/(pi ID d).",
             units_and_conditions="Max XY deflection with +250/-250 V on opposite electrodes", locator="p. 1 tables",
             limitations="High voltage; tens of um only.", relevance_to_design="A tube around the refill is the only other 2-axis piezo topology that fits.",
             transferability_reason="Catalogue data.", design_implication="Reject: best custom tube at 60 V gives about 10 um (CALC).",
             search_query="WebSearch: PI PT130 piezo tube lateral deflection datasheet; curl PDF"),
        dict(base, id="AMF-57", topic="Piezo driver IC with boost (TI DRV8662)",
             citation="Texas Instruments. DRV8662 Piezo Haptic Driver with Integrated Boost Converter, SLOS709C (June 2011, revised December 2022).",
             year="2022", doi_or_url="https://www.ti.com/lit/ds/symlink/drv8662.pdf", source_type="datasheet",
             evidence_class="manufacturer statement", task_or_setup="Recommended operating conditions; electrical characteristics",
             comparator="DRV2700 (AMF-16)", key_quantitative_findings="105 V boost switch and diode, fully differential amplifier, gains 28.8-40.7 dB, 3.3-5.5 V supply, 4 x 4 x 0.9 mm QFN-20. Load capacitance: 100 nF at 200 Vpp/300 Hz, 150 nF at 150 Vpp, 330 nF at 100 Vpp, 680 nF at 50 Vpp, 1 uF at 40 Vpp, 3 uF at 20 Vpp (300 Hz). IDDQ 24/13/9/5 mA at VBST 105/80/55/30 V (VDD 3.6 V, no signal).",
             units_and_conditions="TA 25 degC", locator="p. 1; Sec. 6.3 and 6.5", limitations="Haptic part; same quiescent power as DRV2700.",
             relevance_to_design="Alternative prototype driver.", transferability="high", transferability_reason="Same supply range.",
             design_implication="No power advantage over DRV2700; the product needs a charge-recovery driver.",
             search_query="WebFetch https://www.ti.com/lit/ds/symlink/drv8662.pdf (pdftotext)"),
        dict(base, id="AMF-58", topic="Low-Iq 150 V boost converter for a full 60 V piezo rail (Analog Devices LT8365)",
             citation="Analog Devices. LT8365 Low IQ Boost/SEPIC/Inverting Converter with 1.5A, 150V Switch (via radiolocman.com mirror).",
             year="n.d.", doi_or_url="https://www.radiolocman.com/datasheet/data.html?di=609103", source_type="datasheet",
             evidence_class="manufacturer statement", access_level="secondary account", task_or_setup="Features",
             comparator="LT8330 (AMF-47)", key_quantitative_findings="1.5 A, 150 V switch; input 2.8-60 V; Burst Mode IQ 9 uA; programmable 100-500 kHz with sync; 16-lead MSOP with exposed pad.",
             units_and_conditions="Datasheet features", locator="Title and features (mirror page)",
             limitations="analog.com returned HTTP 503; efficiency at 1-50 mW not retrieved; MSOP-16 larger than the LT8330 packages.",
             relevance_to_design="Rail for the full 60 V bender range with switch margin (LT8330's 60 V switch limits the rail to about 55 V).",
             transferability_reason="Input range matches a 1S cell.", design_implication="Product rail 60 V: +9 % stroke and force over 55 V; EXP-Q05.",
             search_query="WebSearch: LT8365 low IQ boost 150V switch quiescent; WebFetch radiolocman mirror"),
        dict(base, id="AMF-59", topic="Photo-chemical etching capability for flexures (BeCu, titanium)",
             citation="VACCO Industries. Photo Chemical Etching design guide (web); Photofabrication Engineering Inc. Beryllium copper etching page (web).",
             year="n.d.", doi_or_url="https://vacco-etch.com/photo-etching-guide/ ; https://www.photofabrication.com/materials/beryllium-copper/",
             source_type="website", evidence_class="manufacturer statement", task_or_setup="Design rules", comparator="-",
             key_quantitative_findings="VACCO: tolerances +/-10 % of metal thickness; hole or slot >= 1.1 x thickness; bar widths about equal to thickness (down to half) below 0.005 in; materials include beryllium copper and titanium grades. PEI BeCu: thickness 0.0005-0.200 in; +/-10 % of thickness, no less than +/-0.001 in; hole >= 0.005 in or 110 % of thickness; spacing >= 120 %; inside radii = thickness.",
             units_and_conditions="Supplier design rules", locator="Design-rule text on each page",
             limitations="Leaf thickness tolerance comes from the strip, not the etch; fatigue after etching not given.",
             relevance_to_design="The 30-50 um decoupling leaves are within the process (width tolerance about +/-25 um).",
             transferability="high", transferability_reason="Standard commercial process.",
             design_implication="Specify leaf width tolerance +/-25 um; k_cross ~ t^3 makes strip thickness tolerance the dominant spread (+/-10 % -> +/-33 %).",
             search_query="WebSearch: photochemical etching design guide tolerance material thickness beryllium copper"),
        dict(base, id="AMF-60", topic="Write-test machines for gel pens cover low loads (ISO 27668-1:2017 preview)",
             citation="ISO 27668-1:2017 Gel ink ball pens and refills - Part 1: General use (iTeh preview), clause 3.6 citing ISO 12756:2016 3.1.7.",
             year="2017", doi_or_url="https://cdn.standards.iteh.ai/samples/73281/4f2ac60ba6b145c292142c99d1edc3ca/ISO-27668-1-2017.pdf",
             source_type="standard", evidence_class="review", access_level="abstract only", task_or_setup="Definitions (preview pages)",
             comparator="-", key_quantitative_findings="Write test machine: writing angle 60-90 deg, writing load 0.1-5 N, writing speed 1-10 m/min, line pitch 1-5 mm, continuous spiral line (100 mm circumference).",
             units_and_conditions="Definition only; the test load used for conformity is not in the preview", locator="Clause 3.6",
             limitations="No line-quality-versus-force data for D1 refills found anywhere in this search.",
             relevance_to_design="EXP-Q02 (lowest nib force with an acceptable line) can run on a standard write tester down to 0.1 N.",
             transferability_reason="Standard equipment definition.", design_implication="Run EXP-Q02 on an ISO 12756 write tester at 0.05-0.3 N and 35-75 deg (tilt below 60 deg needs a fixture).",
             search_query="WebSearch: ISO 27668-1 gel ink ball pen writing test load angle; curl iTeh preview PDF"),
        dict(base, id="AMF-61", topic="Piezo bender - Thorlabs PB4NB2W construction (supplement to AMF-12)",
             citation="Thorlabs PB4NB2W product page (title) and search-result summary.", year="n.d.",
             doi_or_url="https://www.thorlabs.com/item/PB4NB2W", source_type="manufacturer", evidence_class="manufacturer statement",
             access_level="secondary account", task_or_setup="Product listing", comparator="PICMA (AMF-11)",
             key_quantitative_findings="150 V; +/-450 um; 28 mm active free length; multiple co-fired piezoceramic layers; three wires (top, middle, bottom). Blocking force and capacitance not retrieved (JavaScript page).",
             units_and_conditions="-", locator="Search summary", limitations="Key force data missing.",
             relevance_to_design="Catalogue multilayer bender class at 150 V.", transferability="low", transferability_reason="Incomplete data.",
             design_implication="Not used (voltage; no force data).", search_query="WebSearch: Thorlabs PB4NB2W bimorph specifications"),
        dict(base, id="AMF-62", topic="Piezo bender - Steminc bimorph (checked for narrow parts)",
             citation="STEMINC. PZT Bimorph Actuator 35mm SMBA3531T06 product page.", year="n.d.",
             doi_or_url="https://www.steminc.com/PZT/en/pzt-bimorph-actuator-35mm", source_type="manufacturer",
             evidence_class="manufacturer statement", task_or_setup="Product page", comparator="-",
             key_quantitative_findings="35 x 31 x 0.57 mm; displacement >= 1.2 (units not given) and blocking force >= 100 (units not given) at 200 V; 8 +/- 5 nF; -30 to 65 degC; USD 26.14 per 2 (out of stock, seen 2026-09-28).",
             units_and_conditions="As listed", locator="Specification list", limitations="Units missing; wide single-layer bimorph.",
             relevance_to_design="No narrow multilayer bender found at Steminc.", transferability="low", transferability_reason="Wrong size class.",
             design_implication="Not used.", search_query="WebSearch: Steminc piezo bimorph bender multilayer datasheet"),
        dict(base, id="AMF-63", topic="Custom multilayer bender scaling laws checked against the PICMA and CTS families (this study)",
             citation="This ledger's calculation: opt/hardware/run_study.py scaling_check (results/opt/hardware.json model_checks.scaling).",
             year="2026", doi_or_url="results/opt/hardware.json", source_type="report", evidence_class="analytical derivation",
             access_level="full text", participants_or_bench="not applicable", task_or_setup="Euler-Bernoulli bimorph at fixed layer thickness and field",
             comparator="AMF-11, AMF-53, AMF-54",
             key_quantitative_findings="delta_f ~ LF^2/t, F_b ~ w t^2/LF, C ~ w L_el t, f ~ t/LF^2 reproduce PL112 from PL128 and PL122/PL140 from PL127 within the +/-20 % datasheet tolerance, and the CTS length series within 5 %; for thickness the force ~ t^2 holds (3.7x vs 3.45x) while thick plates give more stroke than 1/t predicts (conservative).",
             units_and_conditions="Datasheet nominal values", locator="hardware.json model_checks.scaling",
             limitations="Inactive layers and clamp effects not modelled; strength of thick custom plates unknown.",
             relevance_to_design="Justifies optimising thickness, length and width of custom plates.", transferability="medium",
             transferability_reason="Law verified on catalogue families; custom parts still need EXP-Q04.",
             design_implication="Treat custom-plate stroke/force as CALC +/-20 % until EXP-Q04.", search_query="-"),
        dict(base, id="AMF-64", topic="Hardware optimisation of the pencil nib stage (this study)",
             citation="This ledger's calculation and simulation: opt/hardware (results/opt/hardware.json, docs/opt_hardware.md).",
             year="2026", doi_or_url="results/opt/hardware.json", source_type="report", evidence_class="simulation",
             access_level="full text", participants_or_bench="not applicable", task_or_setup="Differentiable design model, gradient and global optimisation, P1 validation",
             comparator="Rev P0.1.2 stage", key_quantitative_findings=_amf64_findings(rec, p1tab, cur, static, selection),
             units_and_conditions="Model assumptions as labelled", locator="hardware.json", limitations="Nothing measured; plate scaling and drop model to confirm (EXP-Q04/Q07).",
             relevance_to_design="Rev P0.2 stage proposal.", transferability="medium", transferability_reason="Model-based.",
             design_implication="Quote custom plates and run EXP-Q04/Q06/Q07 on the P0.2 geometry.", search_query="-"),
        dict(base, id="OPT-44", topic="Stage-position sensor: TI TMAG5170 3-D Hall noise and rate",
             citation="Texas Instruments. TMAG5170 High-Precision 3D Linear Hall-Effect Sensor With SPI, SBASAF4 (September 2021).",
             year="2021", doi_or_url="https://www.ti.com/lit/ds/symlink/tmag5170.pdf", source_type="datasheet", evidence_class="manufacturer statement",
             task_or_setup="Electrical and magnetic characteristics", comparator="DRV5055 (OPT-46)", stream="OPT",
             key_quantitative_findings="A1: +/-25/50/100 mT; A2: +/-75/150/300 mT. RMS noise (CONV_AVG=000, 25 degC): A1 XY 140 uT typ (191 max), Z 61 uT; A2 XY 160 uT (236), Z 72 uT; CONV_AVG=101 (32x): A1 XY 24 uT, Z 11 uT. Rate 20/13.3/10 kSPS for 1/2/3 axes (000), 1.2/0.6/0.4 kSPS (101). IACT 3.4 mA; 12-bit; SPI 10 MHz; VSSOP-8 3 x 3 mm.",
             units_and_conditions="VCC 5.5 V for currents", locator="Sec. 6.5 tables; Table 7-x conversion rates",
             limitations="At the >= 10 kSPS servo rate only the fastest (noisiest) mode is usable.",
             relevance_to_design="Baseline sensor: 2.3 um rms at the nib on the weaker axis at the P0.1.2 magnet position (95 T/m), about 3 um once the sensor is moved out 0.1 mm to keep the 169 mT peak field inside the range (CALC with the magpylib sensitivity).",
             transferability="high", transferability_reason="Direct part data.", design_implication="Noise drives servo power; consider the analog DRV5055 pair.",
             search_query="WebFetch https://www.ti.com/lit/ds/symlink/tmag5170.pdf (pdftotext)"),
        dict(base, id="OPT-45", topic="Stage-position sensor: TI TMAG5273 (I2C) noise and interface",
             citation="Texas Instruments. TMAG5273 Low-Power Linear 3D Hall-Effect Sensor With I2C Interface, SLYS045C (June 2021, revised April 2026).",
             year="2026", doi_or_url="https://www.ti.com/lit/ds/symlink/tmag5273.pdf", source_type="datasheet", evidence_class="manufacturer statement",
             task_or_setup="Electrical characteristics", comparator="TMAG5170 (OPT-44)", stream="OPT",
             key_quantitative_findings="RMS noise XY 125 uT (LP_LN 0) / 110 uT (1) at CONV_AVG=000, 22 uT at 101; Z 68/66 and 11/9 uT. 20 kSPS single axis; I2C up to 1 MHz; active 2.3 mA (3.0 mA low noise); SOT-23-6 2.9 x 2.8 mm.",
             units_and_conditions="25 degC", locator="Sec. 5.5-5.10", limitations="I2C bandwidth: about 90 us per multi-byte read at 1 MHz.",
             relevance_to_design="Cannot serve the 10 kSPS two-axis servo.", transferability="high", transferability_reason="Direct part data.",
             design_implication="Reject for the stage servo.", search_query="WebFetch https://www.ti.com/lit/ds/symlink/tmag5273.pdf (pdftotext)"),
        dict(base, id="OPT-46", topic="Stage-position sensor: TI DRV5055 analog linear Hall noise",
             citation="Texas Instruments. DRV5055 Ratiometric Linear Hall-Effect Sensor, SBAS640C (January 2018, revised June 2026).",
             year="2026", doi_or_url="https://www.ti.com/lit/ds/symlink/drv5055.pdf", source_type="datasheet", evidence_class="manufacturer statement",
             task_or_setup="Electrical characteristics", comparator="TMAG5170 (OPT-44)", stream="OPT",
             key_quantitative_findings="Sensitivity 100/50/25/12.5/66 mV/mT (A1/A2/A3/A4/A8; ranges +/-21/42/85/169/75 mT); bandwidth 20 kHz; input-referred noise density 130 nT/sqrt(Hz) at 5 V, 215 at 3.3 V; ICC 2 mA typ at 3.3 V (4 max); SOT-23 2.92 x 2.37 mm or TO-92. MY CALC: with a 3 kHz RC filter 14.8 uT rms, plus 12-bit ADC quantisation at 12.5 mV/mT 18.5 uT -> 23.6 uT rms (7x below TMAG5170).",
             units_and_conditions="VCC 3.3 or 5 V", locator="Sec. 5.5", limitations="One axis per part; needs a clean ADC; offset drift not handled here.",
             relevance_to_design="Lower stage-position noise at the servo rate -> lower servo drive power.",
             transferability="high", transferability_reason="Direct part data.", design_implication="Two DRV5055A4 (one per axis) for the P0.2 servo; magnet re-sized so the peak field stays within +/-169 mT (magpylib check).",
             search_query="WebFetch https://www.ti.com/lit/ds/symlink/drv5055.pdf (pdftotext)"),
    ]
    return rows


def _amf64_findings(rec, p1tab, cur=None, static=None, selection=None):
    if rec is None:
        return "See results/opt/hardware.json."
    o = rec["options"]
    x = rec["x"]
    c = cur or {"usable_wc_um": float("nan"), "q_nom_um": float("nan"), "F_b_nib_N": float("nan"), "f1_Hz": float("nan"),
                "mass_with_margin_g": float("nan")}
    txt = (f"Recommended P0.2 ({o['topology']}, {o['ceramic']}, {o['leaf_mat']} leaves, {o['driver']}, {o['hall']}): plates "
           f"{x['w'] * 1e3:.2f} x {(x['Lf'] + x['Lc']) * 1e3:.1f} x {x['t'] * 1e3:.2f} mm (free {x['Lf'] * 1e3:.1f} mm), lever "
           f"{rec['lever']:.3f}, stops {x['q_stop'] * 1e3:.2f} mm. CALC: worst-case usable stroke (-20 %, 35 deg, mu 0.15, "
           f"F_c 0.15 N) {rec['usable_wc_um']:.0f} um (P0.1.2: {max(c['usable_wc_um'], 0):.0f}); nominal loaded stroke "
           f"{rec['q_nom_um']:.0f} um (P0.1.2: {c['q_nom_um']:.0f}); blocking force at the nib {rec['F_b_nib_N']:.3f} N "
           f"({c['F_b_nib_N']:.3f}); f1 {rec['f1_Hz']:.0f} Hz ({c['f1_Hz']:.0f}); mass incl. 10 % "
           f"{rec['mass_with_margin_g']:.1f} g ({c['mass_with_margin_g']:.1f}); assist life "
           f"{rec.get('life_assist_h', float('nan')):.2f} h ({c.get('life_assist_h', float('nan')):.2f} h with the P0.1.2 "
           f"electronics).")
    if p1tab and "P02" in p1tab and "Q26" in p1tab:
        a, b = p1tab["Q26"], p1tab["P02"]
        txt += (f" SIM (P1, seeds 200-203): mean oracle ratio over the grid {b['mean_oracle_ratio']:.3f} vs "
                f"{a['mean_oracle_ratio']:.3f}; time at the travel limit {b['mean_time_at_limit']:.2f} vs "
                f"{a['mean_time_at_limit']:.2f}; at 35 deg and -20 % tolerance (seeds 200-201) "
                f"{b['mean_worstcase_ratio']:.3f} vs {a['mean_worstcase_ratio']:.3f}.")
    if static is not None and selection:
        so = static["options"]
        s_row = next((d for d in selection["rows"] if d["key"] == "P02s"), None)
        txt += (f" The static-stroke optimum ({so['ceramic']}, {int(so['stack'])} plates per position) reaches "
                f"{static['usable_wc_um']:.0f} um worst case (CALC) but is more compliant "
                f"({static['k_tot_nib']:.0f} vs {rec['k_tot_nib']:.0f} N/m at the nib)")
        if s_row:
            txt += f"; in P1 its worst-case oracle ratio is {s_row['p1_worstcase_ratio']:.3f}"
        txt += ". Finalists were ranked by the P1 worst case."
    return txt


def write_evidence_csv(path, rows):
    cols = open(os.path.join(ROOT, "docs", "evidence.csv"), encoding="utf-8").readline().strip().split(",")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    return cols


# ------------------------------------------------------------------------------------------------------------
def select_recommended(cands, table):
    """The finalist with the lowest mean P1 oracle ratio in the worst-case condition (35 deg, -20 % parts, 0.3 mm
    tremor, seeds 200-201): the closed-loop counterpart of the design objective. The static worst-case stroke of the
    design model ranks designs by force and compliance only; P1 adds the stage stiffness and resonance, which set how
    well the servo rejects the fluctuating nib and skid forces."""
    rows = []
    for key, r, label in cands:
        t = table.get(key)
        if not t:
            continue
        rows.append({"key": key, "label": label, "combination": r["key"], "p1_worstcase_ratio": t["mean_worstcase_ratio"],
                     "p1_grid_ratio": t["mean_oracle_ratio"], "p1_time_at_limit": t["mean_time_at_limit"],
                     "p1_worstcase_time_at_limit": t["mean_worstcase_time_at_limit"],
                     "usable_wc_um": r["usable_wc_um"], "q_nom_um": r["q_nom_um"], "k_tot_nib": r["k_tot_nib"],
                     "f1_Hz": r["f1_Hz"], "skid_ring_mm": r["x"]["r_ring"] * 1e3, "life_assist_h": r.get("life_assist_h")})
    best = min(rows, key=lambda d: d["p1_worstcase_ratio"])
    return best["key"], {"rule": "lowest mean P1 oracle ratio at 35 deg, -20 % parts, 0.3 mm tremor (seeds 200-201, "
                                  "4-12 Hz)", "rows": rows, "selected": best["key"]}


def _strip(r, extra=()):
    return {k: v for k, v in r.items() if k not in ("u", "power_cases_mW") + tuple(extra)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-p1", action="store_true")
    ap.add_argument("--quick-p1", action="store_true")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--no-robustness", action="store_true",
                    help="do not compute the stop, firmware-clamp, Hall-position and leaf-gauge studies around the "
                         "recommended design; use cached ones, else the static optimum's (labelled)")
    a = ap.parse_args(argv)
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    ensure_inputs(a.force)
    checks = current_design_checks()
    scal = scaling_check()
    print("model checks done", flush=True)
    # 1. design-model optimisation: enumeration, refinement, electronics, the static-stroke optimum
    screen_rows = S.step_enumerate(force=a.force)
    ref_rows = S.step_refine(screen_rows, force=a.force)
    refined = {r["key"]: r for r in ref_rows}
    enum_rows = [refined.get(r["key"], r) for r in screen_rows]
    drv_rows = S.step_drivers(enum_rows, force=a.force)
    static = tidy(pick_recommended(enum_rows, drv_rows))
    print("static-stroke optimum", static["key"], round(static["usable_wc_um"]), "um", static.get("tidy"), flush=True)
    # the skid ring: keep the P0.1.2 ring (1.4 mm) unless a larger one buys more than RING_KEEP of the stroke; the ring
    # also sets the nib's axial travel between tilts, which the touchdown work (EXP-Q08) depends on
    ringf = S.step_ring_fixed(static, force=a.force)
    ring_decision = {"free_ring_design": _strip(static), "fixed_ring_usable_wc_um": ringf["row"]["usable_wc_um"],
                     "threshold_frac": RING_KEEP}
    if (abs(static["x"]["r_ring"] - 1.4e-3) > 1e-6 and ringf["row"]["feasible"]
            and ringf["row"]["usable_wc_um"] >= (1.0 - RING_KEEP) * static["usable_wc_um"]):
        static = tidy(dict(ringf["row"], options=static["options"], key=static["key"]))
        S.FIXED_EXTRA["r_ring"] = 1.4e-3
        ring_decision["adopted"] = "fixed 1.4 mm ring (P0.1.2 skid unchanged)"
    else:
        ring_decision["adopted"] = "optimised ring %.2f mm" % (static["x"]["r_ring"] * 1e3)
    print("skid ring:", ring_decision["adopted"], round(static["usable_wc_um"]), "um", flush=True)
    alts = alternatives(static, enum_rows, force=a.force)
    # 2. finalists: registry, CAD, P1 (closed loop) -> the recommendation
    cands = [("P02s", static, "P0.2s: static-stroke optimum (two plates per position)")] + \
        [(f"P02{c}", r, f"P0.2{c}: {r.get('alt', 'alternative')}") for c, r in zip("abc", alts)]
    entries = {}
    for key, r, label in cands:
        opts = S.opts_from(r["options"])
        entries[key] = REG.stage_spec(key, r["x"], opts, label=f"{label}: {opts.key()}", mass_total_g=r["mass_g"],
                                      fit_note="opt/hardware fit constraints (CAD formulas) satisfied")
    REG.write_registry(entries)
    cad = {}
    for key, r, _label in cands:
        path, msg = rebuild_cad(key, r, no_step=True)
        cad[key] = {"summary": os.path.relpath(path, ROOT) if path else None, "message": msg,
                    "compare": cad_vs_model(path, r) if path else None}

    def spec_with_cad(key, r, label):
        opts = S.opts_from(r["options"])
        cs = os.path.join(ROOT, cad[key]["summary"]) if cad[key]["summary"] else None
        mass = json.load(open(cs))["summary"]["mass_total_g"] if cs else r["mass_g"]
        return REG.stage_spec(key, r["x"], opts, label=f"{label}: {opts.key()}", mass_total_g=mass, cad_summary=cs,
                              fit_note="opt/hardware fit constraints; CAD rebuild %s" % (
                                  "all_ok" if cad[key]["compare"] and cad[key]["compare"]["all_ok"] else "see hardware.json"))
    REG.write_registry({key: spec_with_cad(key, r, label) for key, r, label in cands})
    statics = {}
    for key, r, _label in cands:
        try:
            statics[key] = p1_statics_check(key, r)
        except Exception as e:  # pragma: no cover
            statics[key] = {"error": str(e)}
    p1, table, selection = {}, {}, None
    if not a.skip_p1:
        p1 = p1_validate([("Q26", None, "P0.1.2 current")] + cands, quick=a.quick_p1, force=a.force)
        table = p1_table(p1)
        win_key, selection = select_recommended(cands, table)
    else:
        win_key = "P02s"
    win = next((k, r, lab) for k, r, lab in cands if k == win_key)
    rec = dict(win[1], candidate=win_key, cache_tag=f"{win[1]['key']}__{win_key}" if win_key != "P02s" else None)
    print("recommended (P1 selection):", win_key, rec["key"], round(rec["usable_wc_um"]), "um", flush=True)
    # 3. studies around the recommended design (and the static optimum's, where cached)
    cma = S.step_cmaes(rec, force=a.force)
    par = S.step_pareto(rec, force=a.force)
    par = S.repair_pareto(rec, force=a.force) or par
    fcs = S.step_fc_sweep(rec, force=a.force)
    fcs = S.repair_fc_sweep(rec, force=a.force) or fcs
    robust_src = {}

    def robustness(step, fn):
        if not a.no_robustness:
            robust_src[step] = "P02"
            return fn(rec, force=a.force)
        d = S._load(S._nm(step, rec))
        if d and d.get("complete", True):
            robust_src[step] = "P02"
            return d
        robust_src[step] = "P02s"
        return S._load(S._nm(step, static))
    stops = robustness("stop_sweep", S.step_stop_sweep)
    fwc = robustness("firmware_clamp", S.step_firmware_clamp)
    hrear = robustness("hall_rear", S.step_hall_rear)
    gauge = robustness("leaf_gauge", S.step_leaf_gauge)
    ltol = S.leaf_tolerance(rec)
    strip = ("u", "power_cases_mW", "active")
    static_studies = {}
    if win_key != "P02s":
        for step in ("pareto", "fc_sweep", "stop_sweep", "firmware_clamp", "leaf_gauge", "cmaes"):
            d = S._load(S._nm(step, static))
            if d:
                rk = "points" if "points" in d else ("rows" if "rows" in d else None)
                static_studies[step] = {rk: [_strip(r, ("active",)) for r in d[rk]]} if rk else d
        static_studies["leaf_tolerance"] = S.leaf_tolerance(static)
    sens = sensitivities_block(rec)
    sens_static = sensitivities_block(static) if win_key != "P02s" else None
    fe = {"recommended": verify_fe(rec), "candidates": {k: verify_fe(r) for k, r, _ in cands},
          "current": verify_fe({"options": {"topology": "Q", "ceramic": "PIC252", "stack": 1, "leaf_mat": "C17200",
                                            "driver": "drv2700", "hall": "tmag5170_a2", "sweep_mode": "cad",
                                            "hall_gap_extra": 0.0},
                                "x": MD.CURRENT})}
    tube = MD.tube_best()
    front = MD.front_pivot_check()
    hall = hall_field_check(travel_col=rec["x"]["q_stop"] / rec["lever"])
    # 4. the recommended design as P02: registry, P0.2 overlay yaml, CAD with STEP
    ov_path = os.path.join(OUT, "pencil_P0.2_proposed.yaml")
    rec_opts = S.opts_from(rec["options"])
    ev = MD.evaluate(MD.design_batch([rec["x"]]), rec_opts)
    notes = ["recommended = candidate %s (%s), selected by the P1 closed-loop worst case" % (win_key, win[2]),
             "worst-case usable stroke %.0f um (P0.1.2: 0) at F_c 0.15 N, 35 deg, mu 0.15, -20 %%" % rec["usable_wc_um"],
             "generated by python3 -m opt.hardware.run_study"]
    REG.overlay_yaml(ov_path, rec["x"], rec_opts, ev, key=KEY_REC, extra_notes=notes)
    path, msg = rebuild_cad(KEY_REC, rec, no_step=a.no_step)
    cad[KEY_REC] = {"summary": os.path.relpath(path, ROOT) if path else None, "message": msg,
                    "compare": cad_vs_model(path, rec) if path else None}
    rec_label = f"P0.2 recommended (= {win_key})"
    REG.write_registry({KEY_REC: spec_with_cad(KEY_REC, rec, rec_label)})
    try:
        statics[KEY_REC] = p1_statics_check(KEY_REC, rec)
    except Exception as e:  # pragma: no cover
        statics[KEY_REC] = {"error": str(e)}
    if p1:                      # P02 is the same stage specification as the selected candidate
        p1[KEY_REC] = dict(p1[win_key], label=rec_label)
        table[KEY_REC] = dict(table[win_key])
    ev_rows = evidence_rows(rec, table, checks["current_design"], static=static, selection=selection)
    write_evidence_csv(os.path.join(OUT, "hardware_evidence_rows.csv"), ev_rows)
    meta = provenance.metadata("calculation and simulation (differentiable design model, FE drop model, pencil model P1); "
                               "nothing measured", p=D.Params().pencil,
                               seeds={"p1": [200, 201, 202, 203], "sobol_starts": 0, "cmaes": [0, 1, 2]},
                               extra={"script": "opt/hardware/run_study.py", "torch": torch.__version__,
                                      "elapsed_s": round(time.time() - t0, 1), "git_note": "results depend on sim/pencil "
                                      "P1 (core.py/model.py edited concurrently by another agent; defaults unchanged)"})
    others = [(k, r) for k, r, _ in cands if k != win_key]
    result = {
        "meta": meta,
        "labels_legend": {"CALC": "calculation from labelled inputs", "SIM": "numerical model (FE, P1)",
                          "MFR (id)": "manufacturer statement, ledger id", "LIT (id)": "literature, ledger id",
                          "ASSUMPTION": "stated with the experiment that measures it", "PROPOSED DESIGN": "not built"},
        "problem": {"objective": "maximise the worst-case usable stroke min(stroke at -20 % tolerance, 35 deg, worst stroke "
                                 "direction, mu_wc; q_stop - 0.10 mm); finalists ranked by the P1 closed-loop worst case",
                    "constraints": sorted(checks["current_design"]["g"].keys()),
                    "variables": [{"name": v.name, "lo": v.lo, "hi": v.hi, "unit": v.unit, "desc": v.desc} for v in MD.VARS],
                    "fixed": {"Fc_N": 0.15, "mu_wc": 0.15, "theta_wc_deg": 35.0, "tol_wc": -0.2},
                    "discrete": ["topology Q/L/Q2L", "ceramic PIC252/PIC251", "stack 1/2", "leaf C17200/Ti6Al4V",
                                 "clamp electrodes yes/no", "driver", "Hall sensor"]},
        "catalogue": CAT.PARTS,
        "model_checks": {**checks, "scaling": scal},
        "enumeration": [_strip(r) for r in enum_rows],
        "drivers_halls": [_strip(r) for r in drv_rows],
        "selection": selection,
        "recommended": {**{k: v for k, v in rec.items() if k != "u"}, "stage_key": KEY_REC, "bom": bom(rec)},
        "static_optimum": {**{k: v for k, v in static.items() if k != "u"}, "stage_key": "P02s"},
        "alternatives": [{**{k: v for k, v in r.items() if k != "u"}, "stage_key": k} for k, r in others],
        "other_topologies": {"tube": tube, "front_pivot": front},
        "hall_field_check": hall,
        "cmaes_check": cma, "pareto": {"points": [_strip(r, ("active",)) for r in par["points"]], "key": par["key"]},
        "fc_sweep": [_strip(r, ("active",)) for r in fcs["rows"]],
        "stop_sweep": [_strip(r, ("active",)) for r in stops["rows"]],
        "firmware_stop_clamp": [_strip(r, ("active",)) for r in fwc["rows"]],
        "hall_behind_collar": {"row": _strip(hrear["row"]), "nose_usable_wc_um": hrear["nose_usable_wc_um"]},
        "skid_ring_fixed_1.4mm": {"row": _strip(ringf["row"]), "free_ring_usable_wc_um": ringf["free_ring_usable_wc_um"],
                                  "decision": ring_decision, "note": "computed for the static-stroke optimum"},
        "leaf_gauge": [_strip(r, ("active",)) for r in gauge["rows"]],
        "leaf_tolerance": ltol,
        "robustness_studies_design": robust_src,
        "static_optimum_studies": static_studies,
        "sensitivities": sens, "sensitivities_static_optimum": sens_static,
        "fe_verification": fe, "cad": cad, "p1_statics_check": statics,
        "p1_validation": table,
        "files": {"registry": os.path.relpath(REG.REGISTRY_FILE, ROOT), "overlay": os.path.relpath(ov_path, ROOT),
                  "evidence_rows": "results/opt/hardware_evidence_rows.csv"},
    }
    provenance.write_json(os.path.join(OUT, "hardware.json"), r4(result))
    if not a.no_figures:
        from . import figures
        figures.make_all(result, p1)
    print("done", round(time.time() - t0, 1), "s")
    return result


if __name__ == "__main__":
    main()
