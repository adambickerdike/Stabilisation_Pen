r"""The independent review's questions (29 Sep 2026, sections 5, 6 and 12), answered by calculation: CALC on the reduced
linear model (lin.py, verified against HAP-26 and the MuJoCo model: verify.py) and on designs.py; PROPOSED DESIGN
geometry; every input labelled.

  nose_static      the Rev J nose's static side load F_c cot(theta) at the ball, levered 76.5 / 11.5 onto its magnets,
                   and the coil power it costs (the review's finding 1, reproduced)
  collar_geometry  the compact collar of the review's option B (18-22 mm collar, 12-16 mm inner barrel, 40-65 g):
                   pivot position against the sleeve's clearance at the fingers, the web and the tail; masses; the
                   static moment of the writing force for two load paths (V1: the writing force passes through the
                   pivot to the ball; V2: a skid ring on the collar carries it and the ball only its refill spring)
  collar_control   controllability across grip strengths: the tip's response to the servo's reference angle (the
                   transmission; 1 = the ideal z_p x angle), its phase, the error of the controller's nominal model
                   (grip 1 x, split 0.5, web on the collar), the residual the phasor law leaves with that error, the
                   angle and motor torque one millimetre of tremor needs, with the web resting on the collar (a
                   saddle) or on the moving barrel (a short collar: does the web lock the barrel?)
  tail_gate        every tail module against the SAME MASS LOCKED and against no module, with perfect knowledge of the
                   tremor (ceilings), grip 0.5 / 1 / 2 x and split 0.3 / 0.5 / 0.7: the review's gate G5 (>= 10 %
                   incremental improvement over the locked mass)
  cmg_sizing       gyroscopes sized with stored energy, rim stress and containment, the review's two examples included,
                   and the tremor each could cancel at best
  reaction_mass    an active reaction mass on a flexure: coil force F_coil = X sqrt((k - m w^2)^2 + (c w)^2) and the
                   shell reaction m w^2 X (review section 5)
Evidence status: CALCULATION; nothing here is measured.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch

from . import ROOT  # noqa: F401
from . import designs as DS
from . import lin as L
from . import optimise as OP

TWO_PI = 2 * math.pi
GRIPS = (0.5, 1.0, 2.0)          # grip stiffness scale (sim2 HandH1.grip_scale; HAP-26 range 228-1043 N/m around 575)
SPLITS = (0.3, 0.5, 0.7)         # grip split r_rot (ASSUMPTION, EXP-I01)

# ------------------------------------------------------------------------------------------------ the nose's static load
NOSE = {"F_c": 0.15, "L_t": 76.48e-3, "L_a": 11.5e-3, "Km": 0.656,
        "label": "Rev J C1S nose (results/revJ/layout.json pivot_z 76.48 mm, magnet arm 11.5 mm; refill spring 0.15 N; "
                 "Km 0.656 N/sqrt(W): the lead's image-method value, sim2j section 8.1)"}


def nose_static(thetas=(35.0, 50.0, 75.0), F_c: float = NOSE["F_c"]) -> Dict:
    rows = []
    for th in thetas:
        side = F_c / math.tan(math.radians(th))
        F_mag = side * NOSE["L_t"] / NOSE["L_a"]
        rows.append({"theta_deg": th, "side_load_N": side, "magnet_force_N": F_mag, "P_W": (F_mag / NOSE["Km"]) ** 2})
    return {"rows": rows, "inputs": NOSE, "formula": "P = (F_c cot(theta) L_t / L_a / Km)^2 while the ball is on the paper",
            "label": "CALC (the review's finding 1; the lead reproduced 4.717 / 1.628 / 0.166 W)"}


# ------------------------------------------------------------------------------------------------ collar geometry
# PROPOSED DESIGN inputs of the compact collar (the review's envelope), labelled
COLLAR_V2 = {
    "barrel_od": 12.0e-3,        # inner barrel (the moving pen): review 12-16 mm; 12 mm keeps the collar <= 22 mm
    "wall": 0.8e-3,              # sleeve wall (aluminium or PA12-CF), ASSUMPTION
    "gap": 0.3e-3,               # running clearance at the stop, ASSUMPTION
    "z_front_v1": 20.0e-3,       # sleeve front (just ahead of the finger pads at 26-38 mm) when no skid ring is on it
    "z_front_v2": 10.0e-3,       # sleeve front when it carries the skid ring (V2)
    "z_rear": 97.0e-3,           # sleeve rear, past the thumb-index web (92 mm, results/revJ/layout.json hand)
    "length": 0.092,             # inner pen length: it ends inside the collar, its end face carrying the actuator's
                                 # magnets (the tail no longer swings in the air)
    "z_end_wall": 100.0e-3,      # the collar's rear wall carrying the two-axis coil plate
}


def collar_geometry(z_ps=(0.040, 0.045, 0.050, 0.056, 0.060), travels=(2e-3, 3e-3, 4e-3, 5e-3, 6e-3),
                    theta_deg: float = 50.0, N: float = 1.0, F_c: float = 0.15) -> Dict:
    """Sleeve diameter each (pivot, tip travel) needs, and the static moment of the two load paths."""
    g = COLLAR_V2
    th = math.radians(theta_deg)
    rows = []
    for zp in z_ps:
        for X in travels:
            phi = X / zp
            for path, zf in (("V1", g["z_front_v1"]), ("V2", g["z_front_v2"])):
                c_front = (zp - zf) * phi
                c_rear = (g["z_rear"] - zp) * phi
                c = max(c_front, c_rear)
                od = g["barrel_od"] + 2 * (c + g["gap"] + g["wall"])
                M_static = N * zp * math.cos(th) if path == "V1" else F_c / math.tan(th) * zp
                rows.append({"z_p_mm": zp * 1e3, "travel_mm": X * 1e3, "path": path, "swing_deg": math.degrees(phi),
                             "clear_front_mm": c_front * 1e3, "clear_rear_mm": c_rear * 1e3,
                             "tail_swing_mm": (g["length"] - zp) * phi * 1e3, "collar_od_mm": od * 1e3,
                             "fits_22mm": od <= 22.0e-3 + 1e-9, "static_moment_mNm": M_static * 1e3})
    return {"rows": rows, "inputs": g, "label": "CALC on PROPOSED DESIGN geometry (the review's collar envelope)",
            "note": "V1: the writing force N passes through the pivot to the ball (moment N z_p cos(theta)); V2: a skid "
                    "ring on the collar's front carries N and the ball only its refill spring F_c (moment F_c cot(theta) "
                    "z_p, the same physics as the nose's static load but with a long actuator lever)"}


def collar_masses(actuator: str = "coil") -> Dict:
    """Mass budget of the compact collar and its inner pen (PROPOSED DESIGN; CALC from volumes; catalogue parts
    labelled).  actuator 'coil' (recommended): moving magnets on the inner pen's end face (12 mm) sliding over a two-axis
    coil plate in the collar's rear wall, on a gap that stays constant as the pen tilts (the Rev J C1S actuator's
    principle, at a 40-42 mm lever instead of 11.5 mm); 'geared': two Faulhaber 0824 B motors with 06/1 heads (MFR
    AMF-120, AMF-103) - they are 8 mm across (the series name) and do not fit beside a swinging 12 mm pen inside a
    21.7 mm collar: kept only as a mass comparison."""
    g = COLLAR_V2
    od = 21.7e-3
    L_s = g["z_end_wall"] - g["z_front_v2"]
    sleeve_al = DS.RHO_AL * math.pi * od * g["wall"] * L_s
    sleeve_pa = 1150.0 * math.pi * od * 1.2e-3 * L_s              # PA12-CF 1.15 g/cm3, 1.2 mm wall (ASSUMPTION)
    parts = {"sleeve_PA12CF_1.2mm": sleeve_pa * 1e3, "gimbal_cross_flexure": 1.5, "skid_ring_V2": 0.3,
             "load_cell_and_wiring": 1.0, "board_share": 1.5}
    if actuator == "coil":
        parts.update({"coil_plate_2_axis": 4.0, "back_iron": 1.5, "magnets_on_end_face_moving": 2.4})
    else:
        parts.update({"motor_0824B_2x": 2 * 5.2, "gearhead_06_1_2x": 2 * 2.5, "output_gears_2x": 2 * 0.5})
    L = g["length"]
    tube = DS.RHO_AL * math.pi * g["barrel_od"] * 0.5e-3 * (L - 0.004) * 1e3
    moving = {"barrel_tube_al_0.5mm": tube, "refill_and_fine_nib_stage": 6.0, "cell_10280_Li_ion": 5.0,
              "board_and_sensors": 3.0, "end_caps": 1.0}
    zpos = {"barrel_tube_al_0.5mm": 0.048, "refill_and_fine_nib_stage": 0.020, "cell_10280_Li_ion": 0.072,
            "board_and_sensors": 0.038, "end_caps": 0.050, "magnets_on_end_face_moving": 0.091}
    m_col = sum(v for k, v in parts.items() if "moving" not in k)
    mv = dict(moving)
    mv.update({k: v for k, v in parts.items() if "moving" in k})
    m_mov = sum(mv.values())
    zg = sum(mv[k] * zpos.get(k, 0.05) for k in mv) / m_mov          # CALC from the placement (ASSUMPTION positions)
    Jt = sum(mv[k] * 1e-3 * (zpos.get(k, 0.05) - zg) ** 2 for k in mv) + mv["barrel_tube_al_0.5mm"] * 1e-3 * L ** 2 / 12
    return {"actuator": actuator, "collar_parts_g": parts, "moving_parts_g": moving, "collar_g": m_col, "barrel_g": m_mov,
            "total_g": m_col + m_mov, "barrel_zg_mm": zg * 1e3, "barrel_Jt_kgm2": Jt,
            "sleeve_al_g": sleeve_al * 1e3,
            "label": "PROPOSED DESIGN masses (CALC from volumes and placements; MFR AMF-120 0824 B 5.2 g, AMF-103 06/1 "
                     "gearhead; magnets, coil plate, cell and board ASSUMPTION)"}


def compact_pen(actuator: str = "coil") -> Dict:
    mm = collar_masses(actuator)
    return {"m": mm["barrel_g"] * 1e-3, "z_g": mm["barrel_zg_mm"] * 1e-3, "J_t": mm["barrel_Jt_kgm2"], "J_a": 1.0e-6,
            "length": COLLAR_V2["length"], "label": "compact inner barrel (collar_masses, PROPOSED DESIGN)"}


# ------------------------------------------------------------------------------------------------ collar controllability
def _collar_asm(pen: Dict, z_p: float, K_s: float, C_s: float, grip_scale: float, r_rot: float, web_on_collar: bool,
                m_c: float, z_cm: float, J_c: float, K_c: float = 0.02, c_c: float = 1e-4, v2: bool = True):
    """V2 (default): the skid ring on the collar, the ball on its refill spring (drag 1 N s/m at the ball, 2 N s/m at
    the skid); V1: the whole pen with its skid ring swings (stiff normal support and 3 N s/m drag at the tip)."""
    mdl = L.Model(hand=L.HandP(r_rot=r_rot, grip_scale=grip_scale), pen=dict(pen), c_paper=1.0 if v2 else 3.0,
                  collar=L.Collar(z_p=z_p, K_c=K_c + K_s, c_c=c_c + C_s, m=m_c, z_cm=z_cm, J=J_c, web_on_collar=web_on_collar,
                                  skid_on_collar=v2))
    return L.Assembly(mdl)


def _G_collar(asm, w, K_s):
    G = np.zeros((2, 2), complex)
    for j, ax in enumerate((asm.t1, asm.t2)):
        G[:, j] = K_s * asm.ink(asm.solve(w, asm.u_collar(ax))).detach().numpy()
    return G


def collar_control(pen: Optional[Dict] = None, pen_name: str = "revJ", z_p: float = 0.050, K_s: float = 4.0,
                   C_s: float = 0.035, m_c: float = 0.022, z_cm: float = 0.056, J_c: float = 1.2e-5,
                   freqs=(4.0, 5.0, 6.0, 8.0, 10.0), gains=(0.75, 1.0), grips=GRIPS, splits=SPLITS) -> Dict:
    """See the module doc.  The residual of the phasor law with the nominal model G0 and gain g at one frequency, in
    steady state: r = [I - g G (I + g (G0^-1 G - I))^-1 G0^-1] d (CALC; with g = 1 the steady state is exact whatever
    the model error, the error then shows in the loop's stability: the eigenvalues of g (G0^-1 G - I) must stay inside
    the unit circle, reported as 'loop_margin' = 1 - their largest magnitude)."""
    pen = dict(L.PEN) if pen is None else pen
    rows = []
    for f in freqs:
        w = TWO_PI * f
        a0 = _collar_asm(pen, z_p, K_s, C_s, 1.0, 0.5, True, m_c, z_cm, J_c)
        G0 = _G_collar(a0, w, K_s)
        for web in (True, False):
            for gs in grips:
                for r in splits:
                    asm = _collar_asm(pen, z_p, K_s, C_s, gs, r, web, m_c, z_cm, J_c)
                    G = _G_collar(asm, w, K_s)
                    F0 = asm.exc_tremor(w, L.tremor_dirs() * 1e-3)
                    X0 = asm.solve(w, F0)
                    d = asm.ink(X0).detach().numpy()
                    sv = np.linalg.svd(G, compute_uv=False) / z_p
                    M = np.linalg.solve(G0, G)
                    ev = np.linalg.eigvals(M)
                    th = -np.linalg.solve(G, d)                         # the reference angle that cancels 1 mm tremor
                    Xc = asm.solve(w, F0 + K_s * (asm.u_collar(asm.t1) * complex(th[0]) + asm.u_collar(asm.t2) * complex(th[1])))
                    rel = (asm.J_piv_rel.to(L.CT) @ Xc).detach().numpy()
                    rel2 = np.array([rel @ asm.t1, rel @ asm.t2])
                    tau = K_s * (th - rel2) - 1j * w * C_s * rel2
                    row = {"pen": pen_name, "f": f, "web_on_collar": web, "grip_scale": gs, "r_rot": r,
                           "d_tip_mm_per_mm_hand": float(np.max(np.abs(d))) * 1e3 / 1.0,
                           "transmission_min": float(sv[-1]), "transmission_max": float(sv[0]),
                           "model_gain_ratio": [float(abs(e)) for e in ev],
                           "model_phase_err_deg": [float(math.degrees(np.angle(e))) for e in ev],
                           "angle_mrad_per_mm_tip": float(np.max(np.abs(th))) / (L.amp(torch.tensor(d)) * 1e3) * 1e3,
                           "torque_mNm_per_mm_tip": float(np.max(np.abs(tau))) / (L.amp(torch.tensor(d)) * 1e3) * 1e3}
                    for g in gains:
                        A = np.eye(2) + g * (M - np.eye(2))
                        R = np.eye(2) - g * G @ np.linalg.solve(A, np.linalg.inv(G0))
                        res = R @ d
                        row[f"residual_g{g:g}"] = L.amp(torch.tensor(res)) / max(L.amp(torch.tensor(d)), 1e-30)
                        row[f"loop_margin_g{g:g}"] = float(1.0 - np.max(np.abs(g * (ev - 1.0))))
                    rows.append(row)
    return {"rows": rows, "pen": pen_name, "design": {"z_p": z_p, "K_s": K_s, "C_s": C_s, "m_c": m_c, "z_cm": z_cm, "J_c": J_c},
            "label": "CALC (lin.py; H1 hand, sliding tip drag 3 N s/m; the controller's model: grip 1 x, split 0.5, web on the collar)"}


def collar_power(ctrl: Dict, amps=(2e-3, 4e-3, 6e-3, 8e-3), f: float = 6.0, Km_coil_lin: float = 0.656,
                 lever: float = 0.041, Km_geared: float = 0.042, N: float = 1.0, theta_deg: float = 50.0,
                 F_c: float = 0.15, z_p: float = 0.050) -> List[Dict]:
    """Copper power of the collar's two actuators for a tremor amplitude at f (nominal grip, web on the collar), plus
    the static moment of the chosen load path (CALC).  Km: moving-magnet coil like the Rev J nose's (0.656 N/sqrt(W),
    the lead's value) at a 44 mm lever, or geared 0824 B (42 mN m/sqrt(W) at the output, designs.collar_design)."""
    row = next(r for r in ctrl["rows"] if r["f"] == f and r["web_on_collar"] and r["grip_scale"] == 1.0 and r["r_rot"] == 0.5)
    out = []
    th = math.radians(theta_deg)
    for A in amps:
        tau_pk = row["torque_mNm_per_mm_tip"] * A * 1e3 * 1e-3
        for path, Ms in (("V1", N * z_p * math.cos(th)), ("V2", F_c / math.tan(th) * z_p)):
            for act, Km in (("coil", Km_coil_lin * lever), ("geared", Km_geared)):
                P_dyn = 0.5 * (tau_pk / Km) ** 2                    # sinusoid on one axis (rms^2 = pk^2 / 2)
                P_st = (Ms / Km) ** 2
                out.append({"A_mm": A * 1e3, "f": f, "path": path, "actuator": act, "Km_Nm_sqrtW": Km,
                            "tau_peak_mNm": tau_pk * 1e3, "static_mNm": Ms * 1e3, "P_tremor_W": P_dyn, "P_static_W": P_st,
                            "P_total_W": P_dyn + P_st})
    return out


def collar_static(thetas=(35.0, 50.0, 75.0), F_c: float = 0.15, z_p: float = 0.050, Km_coil_lin: float = 0.656,
                  lever: float = 0.041, Km_geared: float = 0.042) -> Dict:
    """The V2 collar's holding power while the ball is on the paper: the refill spring's side load F_c cot(theta) at the
    ball, times the pivot-to-tip distance, held by the actuator (CALC; the Rev J nose's equivalent in nose_static)."""
    rows = []
    for th in thetas:
        Ms = F_c / math.tan(math.radians(th)) * z_p
        rows.append({"theta_deg": th, "moment_mNm": Ms * 1e3, "P_coil_W": (Ms / (Km_coil_lin * lever)) ** 2,
                     "P_geared_W": (Ms / Km_geared) ** 2, "P_revJ_nose_W": nose_static((th,))["rows"][0]["P_W"]})
    return {"rows": rows, "Km_coil_Nm_sqrtW": Km_coil_lin * lever, "Km_geared_Nm_sqrtW": Km_geared,
            "formula": "P = (F_c cot(theta) z_p / Km)^2; coil Km = 0.656 N/sqrt(W) (the lead's C1S value) x the 41 mm lever"}


# ------------------------------------------------------------------------------------------------ tail modules vs locked
def _tmd_ceiling(m, z, f, A, r_rot, gs, X_max, F_max, k=None, c=None):
    """Active reaction mass on a flexure (k, c) at z: perfect-knowledge ceiling within the stroke X_max and the coil
    force F_max (F_coil = the actuator force pair between mass and pen)."""
    k = m * (TWO_PI * 3.0) ** 2 if k is None else k
    c = 2 * 0.1 * math.sqrt(k * m) if c is None else c
    mdl = L.Model(hand=L.HandP(r_rot=r_rot, grip_scale=gs), tail=OP.pen_with_tail(12e-3, z), c_paper=3.0,
                  tmd=L.TMD(m=m, z=z, k=k, c=c))
    asm = L.Assembly(mdl)
    w = TWO_PI * f
    X0 = asm.solve(w, asm.exc_tremor(w, L.tremor_dirs() * A))
    x0 = asm.tip(X0).detach().numpy()
    G = np.zeros((2, 2), complex)
    S = np.zeros((2, 2), complex)
    for j in range(2):
        Xu = asm.solve(w, asm.u_tmd(j))
        G[:, j] = asm.tip(Xu).detach().numpy()
        S[:, j] = (asm.E_tmd.to(L.CT) @ Xu).detach().numpy()
    s0 = (asm.E_tmd.to(L.CT) @ X0).detach().numpy()
    u = -np.linalg.solve(G, x0)
    stroke = s0 + S @ u
    sc = min(1.0, F_max / max(np.max(np.abs(u)), 1e-30), X_max / max(np.max(np.abs(stroke)), 1e-30))
    r = x0 + G @ (u * sc)
    return {"res": L.amp(torch.tensor(r)), "free": L.amp(torch.tensor(x0)), "F_needed": float(np.max(np.abs(u))),
            "stroke_needed": float(np.max(np.abs(stroke))), "scale": sc}


def tail_gate(conds=((5.0, 3e-3), (6.0, 3e-3), (9.0, 3e-3), (5.0, 8e-3), (6.0, 8e-3)), grips=GRIPS, splits=SPLITS,
              cmg_masses=(60, 100)) -> Dict:
    """The review's gate G5 on perfect-knowledge ceilings.  Rows per module, condition and grip: tip tremor with no
    module, with the same mass locked, and with the module active; 'gain_vs_locked' = 1 - active / locked."""
    rows = []
    for gs in grips:
        for r in splits:
            for f, A in conds:
                base = OP.ceiling_cmg_turret(1e-12, f, A, r, 0.0, grip_scale=gs)["x0"]
                # CMG turret pairs (designs.cmg_design): locked = same tail mass, gimbals held (a scissored pair's
                # net momentum is zero, so a locked pair is a plain mass)
                for mg in cmg_masses:
                    d = DS.cmg_design(mg, mode="turret")
                    c = OP.ceiling_cmg_turret(d["h_Nms"], f, A, r, mg * 1e-3, J_g=d["J_g"], grip_scale=gs)
                    rows.append({"module": f"CMG pair {mg} g", "grip_scale": gs, "r_rot": r, "f": f, "A_mm": A * 1e3,
                                 "tip_none_mm": base * 1e3, "tip_locked_mm": c["x0"] * 1e3, "tip_active_mm": c["res"] * 1e3,
                                 "limit": "torque/gimbal" if c["scale"] < 0.999 else "none"})
                # tuned mass 40 g at z 160 mm on its flexure, tuned to the tremor (passive; semi-active retuning)
                t = OP.tmd_response(0.040, f, 0.08, f, r, A=A, grip_scale=gs)
                rows.append({"module": "tuned mass 40 g (tuned to f)", "grip_scale": gs, "r_rot": r, "f": f, "A_mm": A * 1e3,
                             "tip_none_mm": base * 1e3, "tip_locked_mm": t["x_rigid"] * 1e3, "tip_active_mm": t["x"] * 1e3,
                             "limit": "passive"})
                # active reaction mass 30 g, +-4 mm, coil 0.6 N peak (study K's end-cap class), soft 3 Hz flexure
                am = _tmd_ceiling(0.030, 0.153, f, A, r, gs, X_max=4e-3, F_max=0.6)
                lk = OP.tmd_response(0.030, 150.0, 0.08, f, r, A=A, z=0.153, grip_scale=gs)
                rows.append({"module": "reaction mass 30 g (active)", "grip_scale": gs, "r_rot": r, "f": f, "A_mm": A * 1e3,
                             "tip_none_mm": base * 1e3, "tip_locked_mm": lk["x_rigid"] * 1e3, "tip_active_mm": am["res"] * 1e3,
                             "limit": "stroke/force" if am["scale"] < 0.999 else "none"})
    for r_ in rows:
        r_["gain_vs_locked"] = 1.0 - r_["tip_active_mm"] / max(r_["tip_locked_mm"], 1e-12)
        r_["gain_vs_none"] = 1.0 - r_["tip_active_mm"] / max(r_["tip_none_mm"], 1e-12)
        r_["locked_vs_none"] = r_["tip_locked_mm"] / max(r_["tip_none_mm"], 1e-12)
        r_["passes_gate"] = r_["gain_vs_locked"] >= 0.10
    summ = {}
    for mod in sorted(set(r["module"] for r in rows)):
        rr = [r for r in rows if r["module"] == mod]
        summ[mod] = {"gain_vs_locked_mean": float(np.mean([r["gain_vs_locked"] for r in rr])),
                     "gain_vs_locked_min": float(np.min([r["gain_vs_locked"] for r in rr])),
                     "gain_vs_none_mean": float(np.mean([r["gain_vs_none"] for r in rr])),
                     "locked_vs_none_mean": float(np.mean([r["locked_vs_none"] for r in rr])),
                     "share_passing_gate": float(np.mean([r["passes_gate"] for r in rr]))}
    return {"rows": rows, "summary": summ,
            "label": "CALC (lin.py, perfect knowledge of the tremor: an upper bound for any causal controller)"}


# ------------------------------------------------------------------------------------------------ gyroscope sizing
def _torque_per_mm(f: float, m_tail: float, r_rot: float = 0.5, gs: float = 1.0) -> float:
    """Torque amplitude (N m) the best-directed pair needs per mm of tip tremor it cancels fully (lin.py)."""
    c = OP.ceiling_cmg_turret(1.0, f, 1e-3, r_rot, m_tail, grip_scale=gs, tau_g_max=1e9)
    return c["tau_needed"] / (c["x0"] * 1e3)


def cmg_sizing(freqs=(5.0, 6.0, 9.0)) -> Dict:
    rot = []
    # the review's examples: solid rotors (kappa 0)
    for name, m, r_o, rpm in (("review 20 g, r 6 mm, 30 000 rpm (solid)", 0.020, 6e-3, 30000.0),
                              ("review h 5 mN m s: 20 g, 25.2 mm dia, 30 000 rpm (solid)", 0.020, 12.6e-3, 30000.0)):
        J = 0.5 * m * r_o ** 2
        w_s = rpm * TWO_PI / 60
        rot.append({"name": name, "rotor_g": m * 1e3, "r_o_mm": r_o * 1e3, "rpm": rpm, "n_rotors": 1, "module_g": None,
                    "h_Nms": J * w_s, "E_J_per_rotor": 0.5 * J * w_s ** 2, "v_rim_m_s": w_s * r_o})
    for mg in (40, 60, 80, 100):
        d = DS.cmg_design(mg, mode="turret")
        if not d.get("feasible"):
            continue
        rot.append({"name": f"study W turret pair, {mg} g module, 25 000 rpm (ring)", "rotor_g": d["rotor_g"],
                    "r_o_mm": d["rotor_r_o_mm"], "rpm": d["rpm"], "n_rotors": 2, "module_g": mg, "h_Nms": d["h_Nms"],
                    "E_J_per_rotor": d["E_stored_J"] / 2, "v_rim_m_s": d["v_rim_m_s"], "stress_margin": d["stress_margin"],
                    "burst_rpm": d["burst_rpm"], "tail_od_mm": d["od_mm"], "tail_length_mm": d["length_mm"]})
    for r in rot:
        h = r["h_Nms"]
        n = r["n_rotors"]
        m_tail = (r["module_g"] or 60.0) * 1e-3
        r["E_J_total"] = r["E_J_per_rotor"] * n
        r["drop_height_equiv_m_for_100g"] = r["E_J_total"] / (0.1 * 9.81)
        r["torque_5Hz_20deg_mNm_one_rotor"] = h * TWO_PI * 5.0 * math.radians(20.0) * 1e3
        for f in freqs:
            cap_pair = DS.pair_torque(h, f, 1.0, 60.0)             # a scissored pair of such rotors, +-1 rad
            tpm = _torque_per_mm(f, m_tail)
            r[f"pair_torque_{f:g}Hz_mNm"] = cap_pair * 1e3
            r[f"tip_tremor_cancellable_{f:g}Hz_mm"] = cap_pair / tpm
            r[f"torque_needed_per_mm_{f:g}Hz_mNm"] = tpm * 1e3
    return {"rows": rot, "containment": {
        "fragment_translation_share": 0.68,
        "note": "A burst ring rotor in three 120-degree pieces carries about 68 % of its energy as translation (CALC: "
                "centroid radius 0.827 r). A pen cannot be made to contain 5-12 J reliably with a thin wall; the design "
                "must exclude a burst (rim stress margin >= 3 at the running speed, over-speed trip, balanced rotor) and "
                "the housing is a debris shield only (ASSUMPTION: engineering practice, no pen-scale standard found)"},
        "label": "CALC (designs.py; lin.py torque per mm: perfect knowledge, H1 hand, split 0.5, grip 1 x)"}


# ------------------------------------------------------------------------------------------------ reaction mass
def reaction_mass(m: float = 0.030, X: float = 4e-3, f_tunes=(0.0, 5.0, 8.0), zeta: float = 0.05,
                  freqs=(1.0, 3.0, 5.0, 8.0, 10.0, 12.0)) -> Dict:
    rows = []
    for ft in f_tunes:
        k = m * (TWO_PI * ft) ** 2
        c = 2 * zeta * math.sqrt(k * m) if k > 0 else 0.02
        for f in freqs:
            w = TWO_PI * f
            rows.append({"f_tune_Hz": ft, "f": f, "shell_force_N": m * w * w * X,
                         "coil_force_N": X * math.sqrt((k - m * w * w) ** 2 + (c * w) ** 2),
                         "half_stroke_for_0.5N_mm": 0.5 / (m * w * w) * 1e3})
    return {"m_g": m * 1e3, "X_mm": X * 1e3, "rows": rows,
            "label": "CALC (review section 5: F_shell = m w^2 X on a fixed base; F_coil = X sqrt((k - m w^2)^2 + (c w)^2))"}


def run_all() -> Dict:
    ctrl_revj = collar_control()
    ctrl_compact = collar_control(pen=compact_pen("coil"), pen_name="compact 12 mm inner pen", m_c=collar_masses("coil")["collar_g"] * 1e-3)
    return {"nose_static": nose_static(), "collar_geometry": collar_geometry(), "collar_masses": {a: collar_masses(a) for a in ("coil", "geared")},
            "collar_control_revJ": ctrl_revj, "collar_control_compact": ctrl_compact,
            "collar_power_revJ": collar_power(ctrl_revj), "collar_power_compact": collar_power(ctrl_compact),
            "collar_static": collar_static(),
            "tail_gate": tail_gate(), "cmg_sizing": cmg_sizing(), "reaction_mass": reaction_mass()}
