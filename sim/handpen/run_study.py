#!/usr/bin/env python3
"""Inertial, gyroscopic, grip and paper-pivot stabilisers for the pencil-class pen (model H1).

Question: can a device in the cap, in the grip or at the paper contact reduce nib tremor, alone or with the
piezo nib stage, within the 8.9 mm envelope, the 20 g mass target and the 0.266 Wh battery?

Parts (all SIMULATION or CALCULATION on synthetic signals; nothing measured):
  1. calibration: grip zones reproduce the tip-referred HAP-26 impedance; split swept (grip.py)
  2. agreement with model P1 on the same scenarios (rotation locked and free)
  3. frequency-domain screen (linear.py): oracle bounds of every candidate at its best plausible size and the
     size needed for a 50 % reduction
  4. device budgets: mass, length, power, battery life, imbalance vibration, spin-up (devices.py)
  5. time domain with friction and actuator limits (core.py): unmodified pen, nib stage (P1 oracle), active
     reaction mass and control-moment gyroscope (iterative-learning oracle), and the stage combined with each;
     translational and rotational (wrist) tremor; passive options (friction, viscous nose, soft grip, cap mass,
     tuned mass, gyroscope) with their writing distortion; sensitivity to the unmeasured grip split
  6. 3-D replay export results/pencil/inertial_viz.json, figures, results/pencil/inertial.json
Harness conventions (sim/pencil/run_study.py): scenarios sim.pensim.scenarios.handwriting(seed 200-203,
duration 5 s, TremorSpec(f0, amp_pk), N0 1 N); reference = the same pen (device neutral) without tremor;
ratio = e_rms(controller) / e_rms(no correction), both against that reference.
Run: python3 -m sim.handpen.run_study [--workers 2] [--quick]      (about 6-10 min on 2 processes)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import sim.handpen  # noqa: E402,F401  (numba cache location)
from sim.handpen import devices as DV  # noqa: E402
from sim.handpen import evaluate as HE  # noqa: E402
from sim.handpen import grip as G  # noqa: E402
from sim.handpen import linear as L  # noqa: E402
from sim.handpen import model as HM  # noqa: E402
from sim.handpen import params as HP  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "pencil")
SEEDS = (200, 201, 202, 203)
F0S = (4.0, 6.0, 8.0, 10.0, 12.0)
AMPS = (0.1e-3, 0.3e-3, 0.5e-3)
DUR = 5.0
HELPERS = ("rm_slug3", "cmg_2ax")
ILC_SETTINGS = ((100.0, 0.9), (60.0, 1.0), (40.0, 1.0), (20.0, 1.0))
SPLITS = ((0.1, 0.3), (0.3, 0.3), (0.5, 0.3), (0.7, 0.3), (0.5, 0.1), (0.5, 0.6))
_SCN = {}


def scn(seed, tremor=None):
    key = (seed, None if tremor is None else (tremor.f0, tremor.amp_trans, tremor.amp_rot, tremor.L_p, tremor.axis,
                                               tuple(sorted(tremor.spec_kw.items()))))
    if key not in _SCN:
        _SCN[key] = HM.build_scenario(seed=seed, duration=DUR, tremor=tremor)
    return _SCN[key]


def base_cfg(**kw):
    return HP.Config(**kw)


def device(name):
    return DV.candidate_table()[name]


# ======================================================================================= time-domain helpers
def oracle_best(sc, cfg, ref, stage_cfg=None):
    """Best of the ILC projection settings (the oracle is an upper bound, so the best setting is reported)."""
    best = None
    for pct, mg in ILC_SETTINGS:
        res, u, hist = HM.ilc_oracle(sc, cfg, ref, n_iter=6, pct=pct, margin=mg)
        m = HE.compare(res, ref)
        if best is None or m["e_rms_um"] < best[1]["e_rms_um"]:
            best = (res, m, u, (pct, mg), hist)
    res, m, u, setting, hist = best
    out = {"res": res, "m": m, "u": u, "setting": setting, "ilc_history_um": [h * 1e6 for h in hist]}
    if stage_cfg is not None:
        n = len(sc.t)
        rs = HM.run(sc, stage_cfg, uff=HM.uff_at_sim_rate(u, res["t"], n), clean=HM.clean_at_sim_rate(ref, n))
        out["stage_res"] = rs
        out["stage_m"] = HE.compare(rs, ref)
    return out


def device_power(dv, res, m):
    """Mean electrical power of the device during the run (CALC from the simulated forces/torques)."""
    if dv.kind == "rm":
        F = np.column_stack([res["Fd1"], res["Fd2"], res["Fd3"]])
        return float(np.sum(np.mean(F ** 2, axis=0)) / dv.Km ** 2)
    if dv.kind == "cmg":
        return cmg_power(dv, res)
    return 0.0


def cmg_power(dv, res, n_rpm=60000.0, reduction=4.0):
    """Spin power of the rotors (0308B-class, AMF-50, at 60 krpm incl. windage) + gimbal drives (0515B-class, AMF-51,
    4:1 reduction ASSUMPTION): gimbal torque = J_g delta_ddot + H |pen tilt rate|, J_g = rotor + spin motor about the
    gimbal axis (CALC)."""
    n_rot = 2 * sum(dv.axes)
    m_rot = DV.cylinder_mass(5.5e-3, 4e-3, d_in=1.5e-3)
    tau_w, _ = DV.windage(5.5e-3, 4e-3, 0.25e-3, n_rpm)
    P_spin, _ = DV.motor_power("0308B", n_rpm, load_torque=tau_w)
    J_g = (m_rot + HP.MOTORS["0308B"]["m"]) * (3.0e-3 ** 2 + 4.0e-3 ** 2 / 12)
    Mg = HP.MOTORS["0515B"]
    P_g = 0.0
    bdot = np.gradient(np.column_stack([res["b1"], res["b2"]]), res["t"], axis=0)
    for i, (dd, rr) in enumerate((("ddl1", "dr1"), ("ddl2", "dr2"))):
        if not dv.axes[i]:
            continue
        tau = J_g * res[dd] + dv.H * np.abs(bdot[:, 1 - i])
        I = np.abs(tau) / (Mg["k_M"] * reduction)
        P_g += 2 * float(np.mean(np.abs(tau * res[rr]) + I * I * Mg["R"]))   # two gimbals per pair
    return n_rot * P_spin + P_g


def pick(m, keys=("e_rms_um", "e_band_rms_um", "ball_band_rms_um", "tilt_band_rms_mrad", "q_sat_frac", "drag_mean_N",
                  "dev_force_rms_N", "dev_stroke_peak_mm", "cmg_torque_rms_mNm", "cmg_gimbal_peak_rad", "cmg_rate_rms_rad_s")):
    return {k: m[k] for k in keys if k in m}


# ======================================================================================= per-seed studies
def grid_seed(seed):
    """Translational tremor grid: unmodified, stage, helpers (oracle), stage + helper."""
    rows = []
    base = base_cfg()
    stage = base.replace(stage=True)
    sc0 = scn(seed)
    ref0 = HM.run(sc0, base)
    helpers = {h: base.replace(device=device(h)) for h in HELPERS}
    href = {h: HM.run(sc0, c) for h, c in helpers.items()}
    for f0 in F0S:
        for amp in AMPS:
            tr = HM.Tremor(f0=f0, amp_trans=amp)
            sc1 = scn(seed, tr)
            n = len(sc1.t)
            r_un = HM.run(sc1, base)
            m_un = HE.compare(r_un, ref0)
            row = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "tremor": "trans", "unmodified": pick(m_un)}
            r_st = HM.run(sc1, stage, clean=HM.clean_at_sim_rate(ref0, n))
            m_st = HE.compare(r_st, ref0)
            row["stage"] = {**pick(m_st), "ratio": m_st["e_rms_um"] / m_un["e_rms_um"],
                            "band_ratio": m_st["e_band_rms_um"] / m_un["e_band_rms_um"]}
            for h, c in helpers.items():
                r_n = HM.run(sc1, c)
                m_n = HE.compare(r_n, href[h])
                o = oracle_best(sc1, c, href[h], stage_cfg=c.replace(stage=True))
                row[h] = {**pick(o["m"]), "neutral_e_rms_um": m_n["e_rms_um"], "neutral_band_um": m_n["e_band_rms_um"],
                          "ratio": o["m"]["e_rms_um"] / m_n["e_rms_um"], "band_ratio": o["m"]["e_band_rms_um"] / m_n["e_band_rms_um"],
                          "ratio_vs_unmodified": o["m"]["e_rms_um"] / m_un["e_rms_um"], "ilc_setting": o["setting"],
                          "power_W": device_power(c.device, o["res"], o["m"])}
                ms = o["stage_m"]
                row["stage+" + h] = {**pick(ms), "ratio": ms["e_rms_um"] / m_n["e_rms_um"],
                                     "band_ratio": ms["e_band_rms_um"] / m_n["e_band_rms_um"],
                                     "ratio_vs_unmodified": ms["e_rms_um"] / m_un["e_rms_um"]}
            rows.append(row)
    return rows


def rot_seed(seed):
    """Rotational (wrist) and mixed tremor at 0.3 mm (nib level); pivot distance sweep at 8 Hz."""
    rows = []
    base = base_cfg()
    stage = base.replace(stage=True)
    sc0 = scn(seed)
    ref0 = HM.run(sc0, base)
    helpers = {h: base.replace(device=device(h)) for h in HELPERS}
    href = {h: HM.run(sc0, c) for h, c in helpers.items()}
    cases = []
    for f0 in F0S:
        cases.append(("rot_yaw", HM.Tremor(f0=f0, amp_trans=0.0, amp_rot=0.3e-3, L_p=0.175, axis="yaw")))
        cases.append(("mixed", HM.Tremor(f0=f0, amp_trans=0.3e-3 / math.sqrt(2), amp_rot=0.3e-3 / math.sqrt(2), L_p=0.175)))
    for Lp in (0.150, 0.200):
        cases.append((f"rot_yaw_Lp{Lp * 1e3:.0f}", HM.Tremor(f0=8.0, amp_trans=0.0, amp_rot=0.3e-3, L_p=Lp, axis="yaw")))
    cases.append(("rot_pitch", HM.Tremor(f0=8.0, amp_trans=0.0, amp_rot=0.3e-3, L_p=0.175, axis="pitch")))
    for kind, tr in cases:
        sc1 = scn(seed, tr)
        n = len(sc1.t)
        m_un = HE.compare(HM.run(sc1, base), ref0)
        row = {"seed": seed, "f0": tr.f0, "amp_mm": 0.3, "tremor": kind, "L_p_mm": tr.L_p * 1e3, "unmodified": pick(m_un)}
        m_st = HE.compare(HM.run(sc1, stage, clean=HM.clean_at_sim_rate(ref0, n)), ref0)
        row["stage"] = {**pick(m_st), "ratio": m_st["e_rms_um"] / m_un["e_rms_um"]}
        for h, c in helpers.items():
            m_n = HE.compare(HM.run(sc1, c), href[h])
            o = oracle_best(sc1, c, href[h], stage_cfg=c.replace(stage=True))
            row[h] = {**pick(o["m"]), "ratio": o["m"]["e_rms_um"] / m_n["e_rms_um"],
                      "band_ratio": o["m"]["e_band_rms_um"] / m_n["e_band_rms_um"], "power_W": device_power(c.device, o["res"], o["m"])}
            ms = o["stage_m"]
            row["stage+" + h] = {**pick(ms), "ratio": ms["e_rms_um"] / m_n["e_rms_um"]}
        rows.append(row)
    return rows


def passive_variants():
    b = base_cfg()
    return {
        "unmodified": (b, "Unmodified pencil (skid mu 0.12, grip 575 N/m)"),
        "skid_frictionless": (b.replace(mu_skid=0.0, mu_nib=0.0), "Frictionless nose (reference only)"),
        "skid_mu_0.05": (b.replace(mu_skid=0.05), "Skid mu 0.05 (PTFE-like)"),
        "skid_mu_0.25": (b.replace(mu_skid=0.25), "Skid mu 0.25"),
        "skid_mu_0.40": (b.replace(mu_skid=0.40), "Skid mu 0.40 (rubbery)"),
        "viscous_3": (b.replace(c_visc=3.0), "Viscous nose 3 N s/m (idealised damped roller)"),
        "viscous_10": (b.replace(c_visc=10.0), "Viscous nose 10 N s/m"),
        "viscous_20": (b.replace(c_visc=20.0), "Viscous nose 20 N s/m"),
        "grip_soft_x0.5": (b.replace(grip_scale=0.5), "Compliant sleeve: grip stiffness x0.5"),
        "grip_soft_x0.25": (b.replace(grip_scale=0.25), "Compliant sleeve: grip stiffness x0.25"),
        "grip_visco_x0.5": (b.replace(grip_scale=0.5, grip_damp_add=3.0), "Viscoelastic sleeve: x0.5 stiffness, +3 N s/m"),
        "cap_5g": (b.replace(device=DV.cap_mass(5.15e-3)), "Heavier cap +5.15 g"),
        "cap_10g": (b.replace(device=DV.cap_mass(10.3e-3)), "Heavier cap +10.3 g"),
        "tmd_6Hz": (b.replace(device=DV.tmd_slug(6.0)), "Passive TMD 5.15 g tuned 6 Hz"),
        "tmd_8Hz": (b.replace(device=DV.tmd_slug(8.0)), "Passive TMD 5.15 g tuned 8 Hz"),
        "tmd_10Hz": (b.replace(device=DV.tmd_slug(10.0)), "Passive TMD 5.15 g tuned 10 Hz"),
        "gyro_30k": (b.replace(device=DV.gyro_rotor(30000.0)), "Passive gyroscope 30 krpm"),
        "gyro_100k": (b.replace(device=DV.gyro_rotor(100000.0)), "Passive gyroscope 100 krpm"),
    }


def passive_seed(seed):
    rows = []
    var = passive_variants()
    sc0 = scn(seed)
    base = var["unmodified"][0]
    u0 = HM.run(sc0, base)
    refs = {k: HM.run(sc0, c) for k, (c, _) in var.items()}
    dist = {k: HE.distortion(refs[k], u0) for k in var}
    clean_int = {k: HE.vs_intended(refs[k], sc0) for k in var}
    for f0 in F0S:
        sc1 = scn(seed, HM.Tremor(f0=f0, amp_trans=0.3e-3))
        r_u = HM.run(sc1, base)
        m_u = HE.compare(r_u, u0)
        i_u = HE.vs_intended(r_u, sc1)
        for k, (c, _) in var.items():
            r1 = HM.run(sc1, c)
            m_own = HE.compare(r1, refs[k])
            m_tot = HE.compare(r1, u0)
            i_k = HE.vs_intended(r1, sc1)
            rows.append({"seed": seed, "f0": f0, "variant": k, "ratio_own": m_own["e_rms_um"] / m_u["e_rms_um"],
                         "band_ratio_own": m_own["e_band_rms_um"] / m_u["e_band_rms_um"],
                         "ratio_total": m_tot["e_rms_um"] / m_u["e_rms_um"], "drag_N": m_own["drag_mean_N"],
                         "tilt_band_mrad": m_own["tilt_band_rms_mrad"],
                         "int_band_ratio": i_k["e_int_band_um"] / i_u["e_int_band_um"], "int_band_um": i_k["e_int_band_um"],
                         "int_ratio": i_k["e_int_um"] / i_u["e_int_um"], "amp_ratio_int": i_k["amp_ratio_int"],
                         "clean_int_band_um": clean_int[k]["e_int_band_um"], "clean_amp_ratio_int": clean_int[k]["amp_ratio_int"],
                         **{"dist_" + a: b for a, b in dist[k].items()}})
    return rows


def split_seed(seed):
    rows = []
    sc0 = scn(seed)
    for (r_rot, rho) in SPLITS:
        base = base_cfg(r_rot=r_rot, rho_w=rho)
        ref0 = HM.run(sc0, base)
        for f0 in (8.0, 12.0):
            sc1 = scn(seed, HM.Tremor(f0=f0, amp_trans=0.3e-3))
            m_un = HE.compare(HM.run(sc1, base), ref0)
            row = {"seed": seed, "f0": f0, "r_rot": r_rot, "rho_w": rho, "unmodified": pick(m_un)}
            for h in HELPERS:
                c = base.replace(device=device(h))
                ref = HM.run(sc0, c)
                m_n = HE.compare(HM.run(sc1, c), ref)
                o = oracle_best(sc1, c, ref)
                row[h] = {"ratio": o["m"]["e_rms_um"] / m_n["e_rms_um"], "band_ratio": o["m"]["e_band_rms_um"] / m_n["e_band_rms_um"]}
            rows.append(row)
    return rows


def ilc_check(seed=200):
    """How close the time-domain oracle gets to the linear bound: pure sine vs the TremorSpec default (AM 0.3, jitter
    0.3 Hz, 15 % harmonic), with and without paper friction (seed 200, 8 and 12 Hz, 0.3 mm)."""
    rows = []
    lin_cache = {}
    for fr_name, kw in (("friction", {}), ("frictionless", dict(mu_skid=0.0, mu_nib=0.0))):
        base = base_cfg(**kw)
        sc0 = scn(seed)
        for f0 in (8.0, 12.0):
            for lab, skw in (("tremorspec", {}), ("pure_sine", dict(am_depth=0.0, f_jitter=0.0, harmonic=0.0))):
                sc1 = scn(seed, HM.Tremor(f0=f0, amp_trans=0.3e-3, spec_kw=skw))
                for h in HELPERS:
                    c = base.replace(device=device(h))
                    ref = HM.run(sc0, c)
                    m_n = HE.compare(HM.run(sc1, c), ref)
                    o = oracle_best(sc1, c, ref)
                    key = (h, f0)
                    if key not in lin_cache:
                        cfgn = base_cfg().replace(device=device(h))
                        lm = L.LinearModel(cfgn)
                        nib = _x0(lm, cfgn, f0, "trans")[0:2]
                        names, gains, lims = _gains(lm, cfgn, f0)
                        res, auth = L.oracle_bound(nib, gains, lims)
                        lm0 = L.LinearModel(base_cfg())
                        lin_cache[key] = float(np.linalg.norm(res) / np.linalg.norm(np.abs(_x0(lm0, base_cfg(), f0, "trans")[0:2])))
                    rows.append({"seed": seed, "f0": f0, "paper": fr_name, "tremor": lab, "device": h,
                                 "ratio": o["m"]["e_rms_um"] / m_n["e_rms_um"], "linear_bound": lin_cache[key]})
    return rows


def p1_seed(seed):
    """Agreement of the unmodified H1 pen with model P1 (neutral stage) on the same scenarios."""
    import sim.pencil  # noqa: F401
    from sim.pencil import evaluate as E1
    from sim.pencil import model as M1
    rows = []
    cfgp = M1.PencilConfig(overrides={"hand.normal_stiffness": 575.0, "hand.normal_damping": 1.3})
    cfgp_def = M1.PencilConfig()
    h1 = base_cfg()
    h1l = h1.replace(lock_rotation=True)
    sc0 = scn(seed)
    refs = {"P1": M1.run(sc0, M1.Controller(mode="neutral"), cfgp, seed=seed),
            "P1_default_normal": M1.run(sc0, M1.Controller(mode="neutral"), cfgp_def, seed=seed),
            "H1_locked": HM.run(sc0, h1l), "H1": HM.run(sc0, h1)}
    for f0 in F0S:
        for amp in (0.1e-3, 0.3e-3, 0.5e-3):
            if amp != 0.3e-3 and f0 not in (6.0, 10.0):
                continue
            sc1 = scn(seed, HM.Tremor(f0=f0, amp_trans=amp))
            out = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3}
            for k in ("P1", "P1_default_normal"):
                c = cfgp if k == "P1" else cfgp_def
                m = E1.compare(M1.run(sc1, M1.Controller(mode="neutral"), c, seed=seed), refs[k])
                out[k] = {"e_rms_um": m["e_rms_um"], "e_band_rms_um": m["e_band_rms_um"], "housing_band_rms_um": m["housing_band_rms_um"]}
            for k, c in (("H1_locked", h1l), ("H1", h1)):
                m = HE.compare(HM.run(sc1, c), refs[k])
                out[k] = {"e_rms_um": m["e_rms_um"], "e_band_rms_um": m["e_band_rms_um"], "housing_band_rms_um": m["ball_band_rms_um"]}
            rows.append(out)
    return rows


# ======================================================================================= frequency domain
def _x0(lm, cfg, f, kind, A=0.3e-3):
    w = 2 * np.pi * f
    if kind == "trans":
        umaj, umin = L.tremor_direction(0.6)
        F = lm.exc_translation(umaj, w) * A + lm.exc_translation(umin, w) * (-0.4j * A)
    else:
        axis, P, lever = HM.rotation_geometry(cfg, HM.Tremor(f0=f, amp_rot=A, L_p=0.175, axis="yaw"))
        F = lm.exc_rotation(axis, P, w) * (A / lever)
    return lm.solve(w, F)


def _gains(lm, cfg, f):
    """Device input gains (nib response per unit input) and the input limits at f (force/stroke or gimbal)."""
    dv = cfg.device
    w = 2 * np.pi * f
    ins, col, lim = HM.device_inputs(cfg)
    gains, lims, names = [], [], []
    for nm in sum(ins.values(), []):
        u = lm.input_vector(nm).astype(complex)
        Xu = lm.solve(w, u)
        gains.append(Xu[0:2])
        names.append(nm)
        if dv.kind == "rm":
            c = col[nm]
            lims.append(min(dv.F_max[c], dv.stroke[c] / max(abs(Xu[8 + c]), 1e-12)))
        else:
            lims.append(DV.cmg_pair_limit(dv.H, f, dv.rate_max, dv.delta_max))
    return names, gains, lims


def linear_screen():
    cands = ["rm_cell", "rm_slug2", "rm_slug3", "tmd_8Hz", "cap_5g", "cap_10g", "gyro_30k", "cmg_lat", "cmg_2ax"]
    table = DV.candidate_table()
    out = {"ratio": {}, "notes": {}}
    for split in SPLITS:
        skey = f"r_rot {split[0]:.1f} rho_w {split[1]:.1f}"
        b0 = base_cfg(r_rot=split[0], rho_w=split[1])
        lm0 = L.LinearModel(b0)
        for kind in ("trans", "rot"):
            X0n = {f: _x0(lm0, b0, f, kind)[0:2] for f in F0S}
            out["ratio"].setdefault(skey, {}).setdefault(kind, {})["unmodified_nib_amp_mm"] = {
                f"{f:g}Hz": float(np.linalg.norm(np.abs(X0n[f]))) * 1e3 for f in F0S}
            for name in cands:
                dv = table[name]
                cfg = b0.replace(device=dv)
                lm = L.LinearModel(cfg)
                vals = {}
                for f in F0S:
                    nib = _x0(lm, cfg, f, kind)[0:2]
                    if dv.kind in ("rm", "cmg"):
                        names, gains, lims = _gains(lm, cfg, f)
                        res, auth = L.oracle_bound(nib, gains, lims)
                        vals[f"{f:g}Hz"] = float(np.linalg.norm(res) / np.linalg.norm(np.abs(X0n[f])))
                    else:
                        vals[f"{f:g}Hz"] = float(np.linalg.norm(np.abs(nib)) / np.linalg.norm(np.abs(X0n[f])))
                out["ratio"][skey][kind][name] = vals
            # reaction wheels (0515B class: rated 0.084 mNm, stall 0.4 mNm per axis), torque inputs on the plain pen
            for wname, tlim in (("wheels_rated", HP.MOTORS["0515B"]["M_rated"]), ("wheels_stall", HP.MOTORS["0515B"]["M_stall"])):
                vals = {}
                for f in F0S:
                    w = 2 * np.pi * f
                    g = [lm0.solve(w, lm0.input_vector(nm).astype(complex))[0:2] for nm in ("tau_t2", "tau_t1")]
                    res, auth = L.oracle_bound(X0n[f], g, [tlim, tlim])
                    vals[f"{f:g}Hz"] = float(np.linalg.norm(res) / np.linalg.norm(np.abs(X0n[f])))
                out["ratio"][skey][kind][wname] = vals
    out["size_for_50pct"] = size_for_50()
    out["notes"] = {"method": "single-frequency oracle bound on the frictionless linear model: each input phased optimally, "
                              "|input| <= min(force limit, stroke / |stroke per unit force|) for a reaction mass, "
                              "2 H min(rate_max, w delta_max) for a CMG pair, motor torque for wheels; passive devices: "
                              "ratio of nib amplitudes with and without the device",
                    "tremor": "0.3 mm hand-path ellipse (TremorSpec major axis 0.6 rad, ellipticity 0.4) or 0.3 mm at the nib from "
                              "a wrist yaw rotation about a pivot 175 mm behind the grip",
                    "label": "CALCULATION (linear model; optimistic: no friction, no amplitude modulation)"}
    return out


def size_for_50(split=(0.5, 0.3)):
    """Device size for a 50 % reduction of 0.3 mm tremor at the nib (linear bound, per page component)."""
    b0 = base_cfg(r_rot=split[0], rho_w=split[1])
    lm0 = L.LinearModel(b0)
    out = {}
    slug = DV.rm_slug(axes=2)
    lm_rm = L.LinearModel(b0.replace(device=slug))
    for kind in ("trans", "rot"):
        d = {}
        for f in F0S:
            w = 2 * np.pi * f
            X0 = _x0(lm0, b0, f, kind)[0:2]
            row = {}
            # reaction mass: force needed on the moving mass, lateral (y) and tilt-plane (x) components
            for comp, nm in ((1, "F_t2"), (0, "F_t1")):
                if abs(X0[comp]) < 1e-9:
                    continue
                Xu = lm_rm.solve(w, lm_rm.input_vector(nm).astype(complex))
                F50 = 0.5 * abs(X0[comp]) / max(abs(Xu[comp]), 1e-12)
                row[f"rm_{nm}_force_N"] = F50
                row[f"rm_{nm}_mass_x_stroke_g_mm"] = DV.mass_stroke_needed(F50, f) * 1e6
            # torque (CMG / wheels) about t1 (lateral) and t2 (tilt plane)
            for comp, nm in ((1, "tau_t1"), (0, "tau_t2")):
                if abs(X0[comp]) < 1e-9:
                    continue
                Xu = lm0.solve(w, lm0.input_vector(nm).astype(complex))
                T50 = 0.5 * abs(X0[comp]) / max(abs(Xu[comp]), 1e-12)
                row[f"{nm}_torque_mNm"] = T50 * 1e3
                row[f"cmg_{nm}_H_per_rotor_uNms"] = T50 / (2 * min(30.0, w * 0.6)) * 1e6
            # passive gyroscope: H for 50 % (sweep)
            Hs = np.logspace(-5, 1, 61)
            Hx = float("nan")
            for H in Hs:
                lg = L.LinearModel(b0.replace(device=HP.Device(kind="gyro", H=H)))
                if np.linalg.norm(np.abs(_x0(lg, b0, f, kind)[0:2])) <= 0.5 * np.linalg.norm(np.abs(X0)):
                    Hx = H
                    break
            row["gyro_H_Nms"] = Hx
            # heavier cap: mass for 50 % (sweep, fixed at 158 mm)
            mx = float("nan")
            for mc in np.logspace(-3, 0, 61):
                lc = L.LinearModel(b0.replace(device=DV.cap_mass(mc)))
                if np.linalg.norm(np.abs(_x0(lc, b0, f, kind)[0:2])) <= 0.5 * np.linalg.norm(np.abs(X0)):
                    mx = mc
                    break
            row["cap_mass_kg"] = mx
            d[f"{f:g}Hz"] = row
        out[kind] = d
    out["available"] = {"rm_slug_mass_x_stroke_g_mm": slug.m * slug.stroke[1] * 1e6,
                        "rm_cell_mass_x_stroke_g_mm": DV.rm_cell().m * DV.rm_cell().stroke[1] * 1e6,
                        "cmg_H_per_rotor_uNms": DV.cmg_pair().H * 1e6, "gyro_30k_H_uNms": DV.gyro_rotor(30000.0).H * 1e6,
                        "wheel_torque_rated_mNm": HP.MOTORS["0515B"]["M_rated"] * 1e3,
                        "wheel_torque_stall_mNm": HP.MOTORS["0515B"]["M_stall"] * 1e3}
    out["split"] = {"r_rot": split[0], "rho_w": split[1]}
    out["label"] = "CALCULATION (frictionless linear model, single frequency, optimal phase: a lower bound on the size needed)"
    return out


# ======================================================================================= budgets (CALC)
def budgets():
    out = {}
    tab = DV.candidate_table()
    for name, dv in tab.items():
        cfg = base_cfg(device=dv)
        body = HP.pen_with_device(cfg)
        moving = dv.m if dv.kind in ("rm", "tmd") else 0.0
        total = body.m + moving
        cell_left = 1.0 - dv.removed_cell_frac if dv.kind != "rm" or name != "rm_cell" else 1.0
        row = {"label": dv.label, "pen_mass_g": total * 1e3, "within_20g": total <= HP.BUDGET["mass_target"],
               "within_24g": total <= HP.BUDGET["mass_upper"], "cell_capacity_left": cell_left,
               "com_mm": (body.m * body.z_g + moving * dv.z) / total * 1e3}
        if dv.kind in ("rm", "tmd"):
            row["moving_mass_g"] = dv.m * 1e3
            row["stroke_mm"] = [s * 1e3 for s in dv.stroke]
            row["mass_x_stroke_lateral_g_mm"] = dv.m * dv.stroke[1] * 1e6
            row["force_available_at_4_8_12Hz_mN"] = [DV.reaction_force(dv.m, dv.stroke[1], f) * 1e3 for f in (4, 8, 12)]
        if dv.kind == "gyro":
            n = 30000.0 if "30k" in name else 100000.0
            gb = DV.gyro_budget(dv, n)
            row.update({"H_uNms": dv.H * 1e6, "rpm": n, "spin_power_W": gb["spin_power_W"], "windage_W": gb["windage_W"],
                        "imbalance_force_N_G2.5": DV.imbalance_force(DV.cylinder_mass(7e-3, 6e-3, d_in=2e-3), HP.BALANCE_G["nominal"], n),
                        "tone_Hz": n / 60, "spin_up_s_rated_torque": DV.spin_up_time(dv.H / DV.rpm_to_rad(n), n, HP.MOTORS["0515B"]["M_rated"]),
                        "torque_at_0.1rad_s_uNm": DV.gyro_torque(dv.H, 0.1) * 1e6})
        if dv.kind == "cmg":
            n = 60000.0
            m_rot = DV.cylinder_mass(5.5e-3, 4e-3, d_in=1.5e-3)
            tau_w, winfo = DV.windage(5.5e-3, 4e-3, 0.25e-3, n)
            P_spin, pinfo = DV.motor_power("0308B", n, load_torque=tau_w)
            row.update({"H_per_rotor_uNms": dv.H * 1e6, "rotors": 2 * sum(dv.axes), "rotor_mass_g": m_rot * 1e3, "rpm": n,
                        "spin_power_per_rotor_W": P_spin, "windage_per_rotor_W": tau_w * DV.rpm_to_rad(n),
                        "spin_motor_friction_torque_mNm": pinfo["friction_torque_Nm"] * 1e3,
                        "spin_motor_rated_torque_mNm": HP.MOTORS["0308B"]["M_rated"] * 1e3,
                        "pair_torque_limit_mNm_4_8_12Hz": [DV.cmg_pair_limit(dv.H, f, dv.rate_max, dv.delta_max) * 1e3 for f in (4, 8, 12)],
                        "imbalance_force_per_rotor_N_G2.5": DV.imbalance_force(m_rot, HP.BALANCE_G["nominal"], n),
                        "imbalance_force_per_rotor_N_G0.4": DV.imbalance_force(m_rot, HP.BALANCE_G["best"], n),
                        "tone_Hz": n / 60,
                        "spin_up_s": DV.spin_up_time(dv.H / DV.rpm_to_rad(n), n, HP.MOTORS["0308B"]["M_rated"] - pinfo["friction_torque_Nm"])})
        out[name] = row
    # vibration of the pen from rotor imbalance (CALC): x = F / (m_pen w^2), compared with the ink scale and HAP-27 threshold
    pen = HP.pen_body()
    for name in ("gyro_30k", "cmg_2ax"):
        r = out[name]
        F = r.get("imbalance_force_N_G2.5", r.get("imbalance_force_per_rotor_N_G2.5", 0.0))
        w = 2 * np.pi * r["tone_Hz"]
        r["pen_vibration_um_G2.5"] = F / (r["pen_mass_g"] * 1e-3 * w * w) * 1e6
        r["note_vibration"] = ("pen-body vibration at the spin frequency; the ink moves the same sub-micron amount (invisible); "
                               "HAP-27 reports 0.06 um thresholds near 320 Hz, so it is likely felt as a buzz and heard as a tone")
    # reaction wheels and the grip sleeve
    Mw = HP.MOTORS["0515B"]
    out["wheels_2ax"] = {"label": "Reaction wheels (2 axes): tungsten ring 7/2 x 6 mm on a 5 mm BLDC each (AMF-51)",
                         "torque_rated_mNm": Mw["M_rated"] * 1e3, "torque_stall_mNm": Mw["M_stall"] * 1e3,
                         "copper_power_at_rated_W": (Mw["M_rated"] / Mw["k_M"]) ** 2 * Mw["R"],
                         "copper_power_at_stall_W": (Mw["M_stall"] / Mw["k_M"]) ** 2 * Mw["R"],
                         "wheel_speed_swing_rpm_for_0.4mNm_at_8Hz": DV.reaction_wheel_speed_swing(
                             Mw["M_stall"], DV.ring_inertia(DV.cylinder_mass(7e-3, 6e-3, d_in=2e-3), 7e-3, 2e-3), 8.0) * 60 / (2 * np.pi),
                         "mass_g": 2 * (DV.cylinder_mass(7e-3, 6e-3, d_in=2e-3) + Mw["m"]) * 1e3,
                         "length_mm": 2 * 25, "fits": "no: two 25 mm modules exceed the 40 mm cell space"}
    sl = DV.sleeve_holding()
    Km_revA = 0.717 / math.sqrt(6.0)
    lever = 0.0275 / (0.075 - 0.0275)
    F_act = sl["worst_direction_N"] * lever
    out["sleeve"] = {"label": "Active grip sleeve: pen body pivots at the finger pads (z 27.5 mm) inside a finger sleeve; "
                              "2-axis actuator ring at the web end (z 75 mm)",
                     **sl, "actuator_force_N": F_act, "Km_best_NsqrtW": Km_revA,
                     "hold_power_W": (F_act / Km_revA) ** 2,
                     "stroke_at_actuator_mm_for_0.3mm_nib": 0.3 * (0.075 - 0.0275) / 0.0275,
                     "stage_design_load_N": 0.170,
                     "note": ("the sleeve moves the whole barrel, so the paper's transverse reaction N cos(theta) + friction (0.74 N at "
                              "1 N, 50 deg) passes through its actuators; the nib stage behind the skid holds 0.17 N. K_m is the Rev A "
                              "coil (0.717 N/A over sqrt(6 ohm), parameters.yaml), which needs a 15 mm grip")}
    out["labels"] = {"masses": "CAD + ASSUMPTION packaging (devices.py docstrings)", "motors": "MFR (AMF-50, AMF-51)",
                     "tungsten": "MFR (AMF-49)", "windage": "CALC (Couette + enclosed disc)", "balance": "ASSUMPTION (G2.5, G0.4 best)"}
    return out


# ======================================================================================= viz export
def viz(seed=200, f0=8.0, amp=0.3e-3, t0=1.0, t1=3.5, rate=200.0):
    base = base_cfg()
    rm = base.replace(device=device("rm_slug3"))
    cmg = base.replace(device=device("cmg_2ax"))
    sc0 = scn(seed)
    tr = HM.Tremor(f0=f0, amp_trans=amp)
    sc1 = scn(seed, tr)
    n = len(sc1.t)
    ref0 = HM.run(sc0, base)
    runs = {"unmodified": HM.run(sc1, base),
            "stage": HM.run(sc1, base.replace(stage=True), clean=HM.clean_at_sim_rate(ref0, n))}
    refs = {"unmodified": ref0, "stage": ref0}
    for key, c in (("reaction_mass", rm), ("cmg", cmg)):
        ref = HM.run(sc0, c)
        o = oracle_best(sc1, c, ref, stage_cfg=c.replace(stage=True))
        runs[key] = o["res"]
        refs[key] = ref
        runs["stage+" + key] = o["stage_res"]
        refs["stage+" + key] = ref
    desc = {
        "unmodified": "Pencil with the stage held at centre and no helper: the ink carries the hand tremor minus what the skid friction absorbs.",
        "reaction_mass": "5.15 g tungsten slug in the cap moved +/-1.0 mm sideways and +/-2 mm axially by voice coils, driven with perfect "
                         "knowledge of the tremor (iterative-learning oracle). Best inertial helper within the 20 g target.",
        "stage": "Piezo nib stage alone with perfect knowledge of the tremor (model P1 oracle, +/-0.30 mm usable, 0.40 mm stop).",
        "stage+reaction_mass": "Nib stage plus the reaction mass, both with perfect knowledge.",
        "cmg": "Two scissored pairs of control-moment gyroscopes (4 tungsten rotors at 60 000 rpm, gimbals +/-0.6 rad, 30 rad/s). "
               "Over the mass budget (about 25 g) and needs about 0.5 W; shown because gyroscopes were asked about.",
        "stage+cmg": "Nib stage plus the two CMG pairs.",
    }
    order = ["unmodified", "reaction_mass", "stage", "stage+reaction_mass", "cmg", "stage+cmg"]
    tr_ = runs["unmodified"]["t"]
    sel = np.where((tr_ >= t0) & (tr_ < t1))[0]
    dec = int(round((tr_[1] - tr_[0]) ** -1 / rate))
    sel = sel[::dec]
    a, t1v, t2v, nvec, h = HP.geometry_vectors(50.0)

    def f4(x):
        return float(f"{x:.5g}")

    def arr(x, scale=1.0):
        return [[f4(v * scale) for v in row] for row in np.asarray(x)]

    t_int = sc1.t
    intended = np.column_stack([np.interp(tr_[sel], t_int, sc1.intended[:, 0]), np.interp(tr_[sel], t_int, sc1.intended[:, 1])])
    cases = []
    for key in order:
        r = runs[key]
        ref = refs[key]
        m = HE.compare(r, ref)
        base_m = HE.compare(runs["unmodified"], ref0)
        b1, b2 = r["b1"][sel], r["b2"][sel]
        axis = a[None, :] + b1[:, None] * t1v[None, :] + b2[:, None] * t2v[None, :]
        axis /= np.linalg.norm(axis, axis=1)[:, None]
        nib = np.column_stack([r["bx"][sel], r["by"][sel], r["bz"][sel] - HP.CONTACT["r_b"]])
        grip = np.column_stack([r["gfx"][sel], r["gfy"][sel], r["gfz"][sel]])
        dev = {}
        if key in ("reaction_mass", "stage+reaction_mass"):
            dev = {"type": "reaction_mass", "r_pen_frame_m": arr(np.column_stack([r["r1"][sel], r["r2"][sel], r["r3"][sel]])),
                   "force_N": arr(np.column_stack([r["Fd1"][sel], r["Fd2"][sel], r["Fd3"][sel]]))}
        elif key in ("cmg", "stage+cmg"):
            dev = {"type": "cmg", "gimbal_rad": arr(np.column_stack([r["dl1"][sel], r["dl2"][sel]])),
                   "torque_Nm": arr(np.column_stack([r["tq1"][sel], r["tq2"][sel]])), "rotor_rpm": 60000.0}
        if key.startswith("stage"):
            dev["stage_q_m"] = arr(np.column_stack([r["q1"][sel], r["q2"][sel]]))
        cases.append({"key": key, "label": {"unmodified": "Unmodified pencil", "reaction_mass": "Reaction mass in the cap (oracle)",
                                            "stage": "Nib stage (oracle)", "stage+reaction_mass": "Nib stage + reaction mass (oracle)",
                                            "cmg": "CMG pairs in the cap (oracle, over budget)", "stage+cmg": "Nib stage + CMG (oracle)"}[key],
                      "description": desc[key],
                      "nib": arr(nib), "axis": arr(axis), "tilt_rad": arr(np.column_stack([b1, b2])), "grip": arr(grip),
                      "ink": arr(r.ink()[sel]), "pen_down": [int(v > 0) for v in r["contact"][sel]],
                      "device": dev,
                      "metrics": {"ink_err_rms_um": f4(m["e_rms_um"]), "band_rms_um": f4(m["e_band_rms_um"]),
                                  "ratio_vs_unmodified": f4(m["e_rms_um"] / base_m["e_rms_um"]), "q_sat_frac": f4(m["q_sat_frac"])}})
    g = G.from_config(base)
    meta = provenance.metadata("simulation (hand-pen-paper model H1, synthetic handwriting and tremor; nothing measured)",
                               seeds={"handwriting": seed, "tremor": seed + 1000}, p=HP_params(),
                               extra={"model_version": HM.MODEL_VERSION,
                                      "scenario": f"sim.pensim.scenarios.handwriting(seed={seed}, duration={DUR}, TremorSpec(f0={f0}, amp_pk={amp}), N0=1.0)",
                                      "window_s": [t0, t1], "rate_Hz": rate,
                                      "frames": {"page": "x right, y up the page, z out of the page (stabpen/frames.py)",
                                                 "pen": "a = axis nib->cap, altitude 50 deg, azimuth 0 (a = cos50 x + sin50 z); t1 = sin50 x - cos50 z (tilt plane); t2 = y",
                                                 "tilt_rad": "(beta1, beta2): a point z along the axis moves z (beta1 t1 + beta2 t2)",
                                                 "nib": "ball contact point (ball centre minus r_b in z), m, page frame",
                                                 "grip": "pen point at the finger-pad zone (z_f), m, page frame",
                                                 "ink": "page projection of the ball centre plus the stage correction, m",
                                                 "device.r_pen_frame_m": "reaction-mass displacement relative to the pen along t1, t2, a",
                                                 "device.gimbal_rad": "CMG pair gimbal angles (pair 1 torques about t2, pair 2 about t1)",
                                                 "device.stage_q_m": "nib-stage deflection at the nib along t1, t2 (ink moves q1/sin(theta) along x, q2 along y)"},
                                      "geometry_mm": {"length": 166.0, "od": 8.9, "bore": 7.9, "theta_deg": 50.0,
                                                      "finger_zone_z": [20.0, 35.0], "finger_zone_centre": g.z_f * 1e3,
                                                      "web_zone_z": [60.0, 90.0], "web_zone_centre": g.z_w * 1e3,
                                                      "skid_ring_radius": 1.4, "cell_z": [121.0, 161.0],
                                                      "reaction_mass": {"z_centre": 151.0, "d": 4.5, "L": 18.0, "stroke_lateral": 1.0, "stroke_axial": 2.0},
                                                      "cmg": {"z_centre": 146.0, "rotor_d": 5.5, "rotor_L": 4.0, "n_rotors": 4}},
                                      "evidence": {"grip": "LIT HAP-26 (calibration) + ASSUMPTION split r_rot 0.5, rho_w 0.3",
                                                   "contact": "ASSUMPTION (model P1 values)", "devices": "MFR AMF-49/50/51 + ASSUMPTION packaging",
                                                   "results": "SIMULATION"},
                                      "cases": {k: desc[k] for k in order}})
    return {"meta": meta, "units": {"length": "m", "time": "s", "angle": "rad", "force": "N", "torque": "N m"},
            "t": [f4(v) for v in tr_[sel]], "intended": arr(intended), "cases": cases}


def HP_params():
    from sim.pencil import design as D
    return D.Params().pencil


# ======================================================================================= aggregation
def agg(rows, keyf, valf):
    d = {}
    for r in rows:
        try:
            v = valf(r)
        except (KeyError, TypeError):
            continue
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            continue
        d.setdefault(keyf(r), []).append(v)
    return {k: {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v)} for k, v in d.items()}


def summarise_grid(rows):
    s = {}
    for case in ("stage",) + HELPERS + tuple("stage+" + h for h in HELPERS):
        for key in ("ratio", "band_ratio", "q_sat_frac", "ratio_vs_unmodified", "power_W"):
            a = agg(rows, lambda r: f"{r['f0']:g}Hz_{r['amp_mm']:g}mm", lambda r, c=case, k=key: r[c][k])
            if a:
                s.setdefault(case, {})[key] = dict(sorted(a.items()))
    for key in ("e_rms_um", "e_band_rms_um", "tilt_band_rms_mrad"):
        s.setdefault("unmodified", {})[key] = dict(sorted(agg(rows, lambda r: f"{r['f0']:g}Hz_{r['amp_mm']:g}mm", lambda r, k=key: r["unmodified"][k]).items()))
    for h in HELPERS:
        for key in ("dev_force_rms_N", "dev_stroke_peak_mm", "cmg_torque_rms_mNm", "cmg_gimbal_peak_rad", "cmg_rate_rms_rad_s"):
            a = agg(rows, lambda r: f"{r['f0']:g}Hz_{r['amp_mm']:g}mm", lambda r, k=key, hh=h: float(np.max(r[hh][k])))
            if a:
                s[h][key + "_max_axis"] = dict(sorted(a.items()))
    return s


def summarise_rot(rows):
    s = {}
    for case in ("stage",) + HELPERS + tuple("stage+" + h for h in HELPERS):
        a = agg(rows, lambda r: f"{r['tremor']}_{r['f0']:g}Hz", lambda r, c=case: r[c]["ratio"])
        s.setdefault(case, {})["ratio"] = dict(sorted(a.items()))
    s["unmodified_e_rms_um"] = dict(sorted(agg(rows, lambda r: f"{r['tremor']}_{r['f0']:g}Hz", lambda r: r["unmodified"]["e_rms_um"]).items()))
    s["unmodified_tilt_band_mrad"] = dict(sorted(agg(rows, lambda r: f"{r['tremor']}_{r['f0']:g}Hz", lambda r: r["unmodified"]["tilt_band_rms_mrad"]).items()))
    return s


def summarise_passive(rows):
    s = {}
    for key in ("ratio_own", "band_ratio_own", "ratio_total", "drag_N", "tilt_band_mrad", "int_band_ratio", "int_band_um",
                "int_ratio", "amp_ratio_int"):
        a = agg(rows, lambda r: (r["variant"], f"{r['f0']:g}Hz"), lambda r, k=key: r[k])
        for (v, f), val in a.items():
            s.setdefault(v, {}).setdefault(key, {})[f] = val
    for key in ("dist_detrended_rms_um", "dist_lag_ms", "dist_amplitude_ratio", "clean_int_band_um", "clean_amp_ratio_int"):
        a = agg(rows, lambda r: r["variant"], lambda r, k=key: r[k])
        for v, val in a.items():
            s.setdefault(v, {})[key] = val
    labels = {k: lab for k, (c, lab) in passive_variants().items()}
    for v in s:
        s[v]["label"] = labels.get(v, v)
    return s


def summarise_split(rows):
    s = {}
    for h in HELPERS:
        for key in ("ratio", "band_ratio"):
            a = agg(rows, lambda r: f"r_rot {r['r_rot']:.1f} rho_w {r['rho_w']:.1f} {r['f0']:g}Hz", lambda r, k=key, hh=h: r[hh][k])
            s.setdefault(h, {})[key] = dict(sorted(a.items()))
    return s


def headline(grid_s, rot_s, pas_s, lin, bud):
    """Compact ranges for the answer (min-max over 4-12 Hz of the seed means)."""
    def rng(d, suffix):
        v = [x["mean"] for k, x in d.items() if k.endswith(suffix)]
        return [min(v), max(v)] if v else None
    h = {"ink_error_ratio_oracle": {}, "stage_time_at_limit": {}, "rotational_0.3mm": {}, "passive_0.3mm": {}}
    for c in ("stage", "rm_slug3", "cmg_2ax", "stage+rm_slug3", "stage+cmg_2ax"):
        h["ink_error_ratio_oracle"][c] = {f"{a}mm": rng(grid_s[c]["ratio"], f"_{a}mm") for a in ("0.1", "0.3", "0.5")}
        if c.startswith("stage"):
            h["stage_time_at_limit"][c] = {f"{a}mm": rng(grid_s[c]["q_sat_frac"], f"_{a}mm") for a in ("0.1", "0.3", "0.5")}
        h["rotational_0.3mm"][c] = rng({k: v for k, v in rot_s[c]["ratio"].items() if k.startswith("rot_yaw_") and "Lp" not in k}, "Hz")
    for v in ("skid_mu_0.05", "skid_mu_0.25", "skid_mu_0.40", "viscous_3", "viscous_10", "viscous_20", "grip_soft_x0.5",
              "grip_soft_x0.25", "grip_visco_x0.5", "cap_5g", "cap_10g", "tmd_8Hz", "gyro_30k"):
        h["passive_0.3mm"][v] = {"in_band_tremor": rng(pas_s[v]["band_ratio_own"], "Hz"),
                                 "net_in_band_vs_intended": rng(pas_s[v]["int_band_ratio"], "Hz"),
                                 "letters_vs_unmodified": pas_s[v]["dist_amplitude_ratio"]["mean"],
                                 "lag_ms": pas_s[v]["dist_lag_ms"]["mean"], "drag_N": pas_s[v]["drag_N"]["8Hz"]["mean"]}
    h["size_for_50pct_available"] = lin["size_for_50pct"]["available"]
    h["budgets"] = {k: {kk: bud[k].get(kk) for kk in ("pen_mass_g", "cell_capacity_left", "spin_power_W", "hold_power_W")
                        if bud[k].get(kk) is not None} for k in ("rm_cell", "rm_slug3", "cap_10g", "gyro_30k", "cmg_2ax", "sleeve")}
    h["label"] = "SIMULATION (model H1, oracle = perfect disturbance knowledge) and CALCULATION; nothing measured"
    return h


def summarise_p1(rows):
    s = {}
    for model in ("P1", "P1_default_normal", "H1_locked", "H1"):
        for key in ("e_rms_um", "e_band_rms_um", "housing_band_rms_um"):
            a = agg(rows, lambda r: f"{r['f0']:g}Hz_{r['amp_mm']:g}mm", lambda r, m=model, k=key: r[m][k])
            s.setdefault(model, {})[key] = dict(sorted(a.items()))
    rel = {}
    for cmp_ in ("H1_locked", "H1"):
        for key in ("housing_band_rms_um", "e_rms_um"):
            a = agg(rows, lambda r: f"{r['f0']:g}Hz_{r['amp_mm']:g}mm", lambda r, m=cmp_, k=key: r[m][k] / r["P1"][k] - 1.0)
            rel[f"{cmp_}_vs_P1_{key}"] = dict(sorted(a.items()))
    s["relative_difference"] = rel
    return s


# ======================================================================================= figures
def figures(lin, grid_s, pas_s, split_s, rot_s, budget):
    plotstyle.apply()
    import matplotlib.pyplot as plt
    S = plotstyle.SERIES
    # 1. linear bounds at the nominal split, translational tremor
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.8), sharey=True)
    names = [("rm_slug3", "reaction mass, slug 3 axes"), ("rm_cell", "reaction mass, cell"), ("cmg_2ax", "CMG, 2 pairs (25 g)"),
             ("gyro_30k", "passive gyroscope"), ("cap_10g", "heavier cap +10 g"), ("tmd_8Hz", "tuned mass 8 Hz")]
    for ax, kind, title in zip(axs, ("trans", "rot"), ("hand-path tremor 0.3 mm", "wrist-rotation tremor, 0.3 mm at the nib")):
        d = lin["ratio"]["r_rot 0.5 rho_w 0.3"][kind]
        for i, (k, lab) in enumerate(names):
            y = [d[k][f"{f:g}Hz"] for f in F0S]
            ax.plot(F0S, y, color=S[i], label=lab, **plotstyle.marker_kw(S[i]) | {"linestyle": "-"})
        ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
        ax.axhline(0.5, color=plotstyle.MUTED, lw=1.0, ls="--")
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_xlabel("Tremor frequency (Hz)")
        ax.set_ylim(0, 1.15)
    axs[0].set_ylabel("Nib tremor with device / without (bound)")
    h_, l_ = axs[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, 0.04))
    fig.suptitle("Linear oracle bound of cap devices at their best plausible size (grip split r_rot 0.5, rho_w 0.3)", x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "calculation", "frictionless linear model, single frequency, optimal phase; dashed line = 50 %")
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_inertial_linear_bounds.png"))
    plt.close(fig)
    # 2. time domain, translational tremor, 0.3 mm: ratios vs frequency
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.8))
    cases = [("rm_slug3", "reaction mass (oracle)"), ("cmg_2ax", "CMG 2 pairs (oracle)"), ("stage", "nib stage (oracle)"),
             ("stage+rm_slug3", "stage + reaction mass"), ("stage+cmg_2ax", "stage + CMG")]
    for i, (c, lab) in enumerate(cases):
        y = [grid_s[c]["ratio"][f"{f:g}Hz_0.3mm"]["mean"] for f in F0S]
        axs[0].plot(F0S, y, color=S[i], label=lab, **plotstyle.marker_kw(S[i]) | {"linestyle": "-"})
    axs[0].axhline(1.0, color=plotstyle.MUTED, lw=1.0)
    axs[0].set_ylim(0, 1.1)
    axs[0].set_xlabel("Tremor frequency (Hz), 0.3 mm")
    axs[0].set_ylabel("Ink error / no correction")
    axs[0].set_title("Ink-error ratio, mean of 4 seeds", loc="left", fontsize=9)
    for i, (c, lab) in enumerate([("stage", "nib stage alone"), ("stage+rm_slug3", "stage + reaction mass"), ("stage+cmg_2ax", "stage + CMG")]):
        y = [grid_s[c]["q_sat_frac"][f"{f:g}Hz_0.3mm"]["mean"] * 100 for f in F0S]
        col = S[[2, 3, 4][i]]
        axs[1].plot(F0S, y, color=col, label=lab, **plotstyle.marker_kw(col) | {"linestyle": "-"})
    axs[1].set_xlabel("Tremor frequency (Hz), 0.3 mm")
    axs[1].set_ylabel("Time at the stage travel limit (%)")
    axs[1].set_title("Stage saturation", loc="left", fontsize=9)
    axs[1].legend(fontsize=7.5)
    h_, l_ = axs[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=5, fontsize=7.5, bbox_to_anchor=(0.5, 0.04))
    fig.suptitle("Time domain with paper friction and actuator limits (hand-path tremor)", x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "simulation", "model H1, seeds 200-203, perfect disturbance knowledge; not measured")
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_inertial_timedomain.png"))
    plt.close(fig)
    # 3. passive options: in-band tremor removed (own reference) versus net in-band error against the intended path
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.6), gridspec_kw={"width_ratios": [1.0, 1.1]})
    ax = axs[0]
    groups = [("skid friction", ["skid_mu_0.05", "skid_mu_0.25", "skid_mu_0.40"]),
              ("viscous nose", ["viscous_3", "viscous_10", "viscous_20"]),
              ("soft grip sleeve", ["grip_soft_x0.5", "grip_soft_x0.25", "grip_visco_x0.5"]),
              ("cap mass / tuned mass / gyro", ["cap_5g", "cap_10g", "tmd_6Hz", "tmd_8Hz", "tmd_10Hz", "gyro_30k", "gyro_100k"])]
    for i, (glab, vs) in enumerate(groups):
        xs = [pas_s[v]["dist_detrended_rms_um"]["mean"] for v in vs]
        ys = [pas_s[v]["band_ratio_own"]["8Hz"]["mean"] for v in vs]
        ax.plot(xs, ys, color=S[i], label=glab, **plotstyle.marker_kw(S[i]))
        for v, x_, y_ in zip(vs, xs, ys):
            if glab.startswith("cap"):
                continue
            ax.annotate(v.replace("skid_", "").replace("grip_", "").replace("viscous_", "c=").replace("_", " "), (x_, y_),
                        textcoords="offset points", xytext=(4, 3), fontsize=6.5, color=plotstyle.INK2)
    ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
    ax.set_xlabel("Writing change without tremor vs the unmodified pencil, RMS (um)")
    ax.set_ylabel("In-band tremor in the ink / unmodified (8 Hz)")
    ax.set_title("Tremor removed, measured against each pen's own writing", loc="left", fontsize=9)
    ax.legend(fontsize=7, loc="lower left")
    ax = axs[1]
    order = ["skid_frictionless", "skid_mu_0.05", "skid_mu_0.25", "skid_mu_0.40", "viscous_3", "viscous_10", "viscous_20",
             "grip_soft_x0.5", "grip_soft_x0.25", "grip_visco_x0.5", "cap_10g", "tmd_8Hz", "gyro_100k"]
    ypos = np.arange(len(order))[::-1]
    for j, f in enumerate(("4Hz", "8Hz", "12Hz")):
        xs = [pas_s[v]["int_band_ratio"][f]["mean"] for v in order]
        ax.plot(xs, ypos + (j - 1) * 0.22, color=S[j], label=f"tremor {f}", **plotstyle.marker_kw(S[j]))
    ax.axvline(1.0, color=plotstyle.MUTED, lw=1.0)
    ax.set_yticks(ypos)
    ax.set_yticklabels([v.replace("_", " ") for v in order], fontsize=7.5)
    ax.set_xlabel("3-15 Hz ink error against the intended path / unmodified pencil")
    ax.set_title("Net effect: tremor passed plus writing detail lost", loc="left", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    fig.suptitle("Passive options at the paper, in the grip and in the cap (0.3 mm hand tremor)", x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "simulation", "model H1, 4 seeds; friction, damping and grip values assumed; not measured")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_inertial_passive.png"))
    plt.close(fig)
    # 4. split sensitivity
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    rr = [0.1, 0.3, 0.5, 0.7]
    for i, (h, lab) in enumerate((("rm_slug3", "reaction mass"), ("cmg_2ax", "CMG 2 pairs"))):
        for j, f in enumerate((8, 12)):
            y = [split_s[h]["ratio"][f"r_rot {r:.1f} rho_w 0.3 {f}Hz"]["mean"] for r in rr]
            col = S[2 * i + j]
            ax.plot(rr, y, color=col, label=f"{lab}, {f} Hz", **plotstyle.marker_kw(col) | {"linestyle": "-"})
    ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
    ax.set_ylim(0.5, 1.05)
    ax.set_xlabel("Share of the nib's grip compliance from pen tilt in the grip (r_rot)")
    ax.set_ylabel("Ink error / no correction")
    ax.set_title("Unmeasured grip split decides the cap devices' effect", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5)
    plotstyle.stamp(fig, "simulation", "model H1, 0.3 mm tremor, seeds 200-201, oracle")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_inertial_split.png"))
    plt.close(fig)
    # 5. size needed for 50 % vs available (log)
    sz = lin["size_for_50pct"]
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 3.6))
    need = [sz["trans"][f"{f:g}Hz"]["rm_F_t2_mass_x_stroke_g_mm"] for f in F0S]
    axs[0].semilogy(F0S, need, color=S[0], label="needed for 50 % (lateral)", **plotstyle.marker_kw(S[0]) | {"linestyle": "-"})
    axs[0].axhline(sz["available"]["rm_slug_mass_x_stroke_g_mm"], color=S[1], lw=2, label="tungsten slug 5.15 g x 1.0 mm")
    axs[0].axhline(sz["available"]["rm_cell_mass_x_stroke_g_mm"], color=S[2], lw=2, ls="--", label="cell 3.45 g x 0.5 mm")
    axs[0].set_xlabel("Tremor frequency (Hz)")
    axs[0].set_ylabel("Mass x stroke (g mm)")
    axs[0].set_title("Reaction mass", loc="left", fontsize=9)
    axs[0].legend(fontsize=7.5)
    needH = [sz["trans"][f"{f:g}Hz"]["cmg_tau_t1_H_per_rotor_uNms"] for f in F0S]
    axs[1].semilogy(F0S, needH, color=S[0], label="needed for 50 % (lateral)", **plotstyle.marker_kw(S[0]) | {"linestyle": "-"})
    axs[1].axhline(sz["available"]["cmg_H_per_rotor_uNms"], color=S[1], lw=2, label="rotor 1.6 g at 60 krpm")
    axs[1].set_xlabel("Tremor frequency (Hz)")
    axs[1].set_ylabel("Angular momentum per rotor (uN m s)")
    axs[1].set_title("CMG scissored pair (+/-0.6 rad, 30 rad/s)", loc="left", fontsize=9)
    axs[1].legend(fontsize=7.5)
    fig.suptitle("Size needed for a 50 % reduction of 0.3 mm tremor versus what fits (split r_rot 0.5)", x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "calculation", "frictionless linear model, optimal phase: lower bound on the size needed")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_inertial_size50.png"))
    plt.close(fig)


def _r4(x):
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return float(f"{x:.4g}") if math.isfinite(x) and x != 0.0 else x
    if isinstance(x, dict):
        return {str(k): _r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r4(v) for v in x]
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def calibration_section():
    out = {"hap26_check": {}, "splits": {}}
    cfg = base_cfg()
    lm = L.LinearModel(cfg, contact=False, massless_pen=True)
    f = np.array([0.6, 2.0, 5.0, 8.0, 12.0, 20.0, 30.0])
    for i, nm in enumerate(("F_x", "F_y", "F_z")):
        X = lm.frf(f, lambda w, nm=nm: lm.input_vector(nm).astype(complex))[:, i]
        ref = G.hap26_compliance(f)
        out["hap26_check"][nm] = {"max_abs_ratio_error": float(np.max(np.abs(np.abs(X / ref) - 1))),
                                  "max_phase_error_deg": float(np.degrees(np.max(np.abs(np.angle(X / ref)))))}
    for (r, rho) in SPLITS + ((0.1, 0.1), (0.7, 0.1), (0.7, 0.6)):
        out["splits"][f"r_rot {r:.1f} rho_w {rho:.1f}"] = G.calibrate(r_rot=r, rho_w=rho).summary()
    out["r_max"] = {f"rho_w {rho:.1f}": G.r_max(rho, 0.0275, 0.075) for rho in (0.05, 0.1, 0.2, 0.3, 0.5, 0.6, 0.8)}
    out["pen"] = HP.pen_body().summary()
    out["label"] = "CALCULATION: massless-pen driving-point compliance of the calibrated grip against HAP-26 eq. (1)"
    return out


def figures_from_json(path=os.path.join(OUT, "inertial.json")):
    import json
    d = json.load(open(path))
    td = d["time_domain"]
    global F0S
    F0S = tuple(sorted({float(k.split("Hz")[0]) for k in td["translational"]["stage"]["ratio"]}))
    figures(d["linear_screen"], td["translational"], td["passive"], td["split_sensitivity"], td["rotational"], d["budgets"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--quick", action="store_true", help="2 seeds, 3 frequencies (smoke run)")
    ap.add_argument("--figures-only", action="store_true", help="redraw the figures from results/pencil/inertial.json")
    a = ap.parse_args()
    if a.figures_only:
        figures_from_json()
        return
    global SEEDS, F0S
    if a.quick:
        SEEDS, F0S = (200, 201), (4.0, 8.0, 12.0)
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    HM.run(HM.build_scenario(seed=1, duration=0.3), base_cfg())      # warm the numba cache
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        f_grid = ex.map(grid_seed, SEEDS)
        f_rot = ex.map(rot_seed, SEEDS)
        f_pas = ex.map(passive_seed, SEEDS)
        f_split = ex.map(split_seed, SEEDS[:2])
        f_p1 = ex.map(p1_seed, SEEDS)
        f_chk = ex.submit(ilc_check, SEEDS[0])
        grid = [r for rows in f_grid for r in rows]
        rot = [r for rows in f_rot for r in rows]
        pas = [r for rows in f_pas for r in rows]
        split = [r for rows in f_split for r in rows]
        p1 = [r for rows in f_p1 for r in rows]
        chk = f_chk.result()
    t_td = time.time() - t0
    lin = linear_screen()
    bud = budgets()
    cal = calibration_section()
    grid_s, rot_s, pas_s, split_s, p1_s = summarise_grid(grid), summarise_rot(rot), summarise_passive(pas), summarise_split(split), summarise_p1(p1)
    vz = viz()
    provenance.write_json(os.path.join(OUT, "inertial_viz.json"), vz)
    figures(lin, grid_s, pas_s, split_s, rot_s, bud)
    meta = provenance.metadata("simulation and calculation (hand-pen-paper model H1, synthetic handwriting and tremor; nothing measured)",
                               seeds={"test": list(SEEDS), "split": list(SEEDS[:2]), "viz": 200}, p=HP_params(),
                               extra={"model_version": HM.MODEL_VERSION, "dt_s": HM.DT, "record_Hz": HM.REC_HZ, "duration_s": DUR,
                                      "workers": a.workers, "elapsed_s": round(time.time() - t0, 1), "time_domain_s": round(t_td, 1),
                                      "script": "sim/handpen/run_study.py", "labels": {k: v for k, v in HP.LABELS.items()}})
    out = {"meta": meta,
           "protocol": {"reference": "same pen (device neutral) on the same handwriting without tremor (harness convention of model P1)",
                        "ratio": "e_rms(controller or device, tremor) / e_rms(no correction, tremor), both against that reference",
                        "oracle": "stage: cancels the true ball deviation from the clean path (P1 oracle); reaction mass / CMG: iterative "
                                  "learning on the true disturbance with projection onto the device limits, best of "
                                  f"{len(ILC_SETTINGS)} projection settings",
                        "passive": "ratio_own = tremor error against the same pen's clean ink / unmodified; ratio_total = against the "
                                   "unmodified pen's clean ink; distortion = clean ink of the variant vs the unmodified pen",
                        "tremor": "trans: hand-path TremorSpec (P1); rot_yaw: hand-frame rotation about the page normal through a wrist "
                                  "pivot L_p behind the grip, 0.3 mm peak at the nib; mixed: both at 0.21 mm",
                        "grip_split": "nominal r_rot 0.5, rho_w 0.3 (ASSUMPTION); swept in split_sensitivity"},
           "headline": headline(grid_s, rot_s, pas_s, lin, bud),
           "calibration": cal, "p1_agreement": p1_s, "linear_screen": lin, "budgets": bud,
           "oracle_method_check": {"rows": chk, "note": "time-domain oracle vs the frictionless linear bound, seed 200: pure sine "
                                                         "vs TremorSpec default, with and without paper friction"},
           "time_domain": {"translational": grid_s, "rotational": rot_s, "passive": pas_s, "split_sensitivity": split_s},
           "rows": {"grid": grid, "rot": rot, "passive": pas, "split": split, "p1": p1}}
    provenance.write_json(os.path.join(OUT, "inertial.json"), _r4(out))
    for c in ("stage",) + HELPERS + tuple("stage+" + h for h in HELPERS):
        print(c, {k: round(v["mean"], 3) for k, v in grid_s[c]["ratio"].items() if k.endswith("0.3mm")})
    print("q_sat", {c: {k: round(v["mean"], 3) for k, v in grid_s[c]["q_sat_frac"].items() if k.endswith("0.3mm")}
                    for c in ("stage", "stage+rm_slug3", "stage+cmg_2ax")})
    print("elapsed", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
