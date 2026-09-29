r"""Every force and moment on the nib, tip-referred, for any nib and pose; and why study N's duty model missed the static
term (CALC; SIM values quoted from results/sim2j/power.json with their label).

A nib is described by NibModel (kind 'gimbal': the ball at L_t in front of a 2-axis pivot; 'translation': the ball moves
without tilting the refill).  Loads on the nib's axes u1, u2 (the direction the actuator must push; labels.py and
contact.py define the frames):

  contact     Q = -F . u from the vector contact force (contact.py): the static side load F_s cot(theta) and, while the
              ball slides, the friction-dependent part (friction map, contact.mu_kinetic)
  gravity     gimbal: Q_g = -m g (d_cm / L_t)(n . u)  (d_cm: nib centre of mass behind the pivot, +); translation:
              Q_g = m g (n . u).  n . u1 = -cos(theta) at roll 0: a centre of mass behind a pivot ADDS to the side load,
              a translating nib's weight subtracts from it (both roll-invariant in magnitude: gravity and the side load
              both lie in the tilt plane)
  inertia     m_eff a (tip-equivalent mass x tip acceleration of the duty)
  flexure     k_tip q (suspension), minus the magnetic negative stiffness k_mag q; parasitic lateral force F_par (e.g.
              an off-centre magnetic pull, a sphere-centre offset)
  geometric   gimbal only: the contact's own stiffness through the tilting refill, dQ/dq = F_s (1 + cos^2 th)/(L_t sin^2 th)
  balance     B (balance.py): scheduled bias, counter-face, steep tip ...; it may persist during pen-up (ungated)
  pen lift    during pen-up the contact load is zero; a persisting balance or bias is then the load
  refill      a replacement refill changes F_s (tolerance, ink type), the ball's axial position (length tolerance
              +0.3 mm) and the moving mass

Time-averaged copper loss for a contact duty c (share of time with the ball on the paper):
  E[F_i^2] = c (Q_i + B_i,c + G_i)^2 + (1 - c)(B_i,u + G_i)^2 + c sigma_fric,i^2 + E[D_i^2]
  P = sum_i E[F_i^2] / Km_tip^2          (D: zero-mean dynamic force: inertia + suspension)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

import numpy as np

from . import REPO_ROOT
from . import contact as C
from .labels import C1S, CONTACT, G0, TASKS, V, c1s, val

D2R = math.pi / 180.0
THETAS = (35.0, 50.0, 60.0, 75.0)


@dataclass
class NibModel:
    name: str
    kind: str = "gimbal"                  # 'gimbal' | 'translation'
    L_t: float = 76.48e-3                 # m, pivot to ball (gimbal)
    Km_tip: float = 0.099                 # N/sqrt(W) per axis at the tip
    m_eff_tip: float = 2.1e-3             # kg tip-equivalent moving mass
    m_nib: float = 18.2e-3                # kg moving nib (for gravity)
    d_cm: float = -3.7e-3                 # m centre of mass behind the pivot (+) (gimbal); ignored for translation
    k_tip: float = 0.478                  # N/m suspension at the tip
    k_mag_tip: float = 0.0                # N/m magnetic negative stiffness at the tip (a positive number destabilises)
    F_par: float = 0.0                    # N parasitic lateral force at the tip (worst direction)
    R_coil: float = 2.47                  # ohm per axis (for currents)
    label: str = "CALC"


def c1s_model() -> NibModel:
    d = c1s()
    return NibModel(name="C1S (Rev J, study N)", kind="gimbal", L_t=d["z_p_mm"] * 1e-3, Km_tip=d["Km_tip"],
                    m_eff_tip=d["m_eff_tip_g"] * 1e-3, m_nib=18.17e-3, d_cm=d["d_cm_mm"] * 1e-3, k_tip=d["k_tip_N_m"],
                    R_coil=val(C1S["R_coil"]), label="CALC (study N design, results/nose2/nose2.json)")


def gravity_load(nib: NibModel, theta: float, phi: float = 0.0) -> np.ndarray:
    fr = C.frame(theta, phi)
    n = fr["n"]
    out = []
    for u in (fr["u1"], fr["u2"]):
        if nib.kind == "gimbal":
            out.append(-nib.m_nib * G0 * (nib.d_cm / nib.L_t) * (n @ u))
        else:
            out.append(nib.m_nib * G0 * (n @ u))
    return np.array(out)


def geometric_stiffness(nib: NibModel, theta: float, F_s: float) -> float:
    """Tilt-plane stiffness of the contact through the tilting refill (gimbal only), N/m at the tip (CALC).  A negative
    value would destabilise; this one is positive (the side load falls as the nib tilts toward the paper normal)."""
    if nib.kind != "gimbal":
        return 0.0
    return F_s * (1.0 + math.cos(theta) ** 2) / (nib.L_t * math.sin(theta) ** 2)


@dataclass
class Duty:
    """The stabilising duty shared by every candidate (CALC inputs labelled): tremor correction amplitude and frequency
    per axis, writing speed with directions uniform over the circle, contact share."""
    q_rms: float = 1.0e-3            # m rms per axis (Rev H / study N design duty: 1 mm rms at 8 Hz; ASSUMPTION)
    f: float = 8.0                   # Hz
    v_write: float = 30.5e-3         # m/s (LIT CON-20)
    contact: float = 0.70            # ASSUMPTION (review section 4)
    ink: str = "oil_common"
    paper: float = 1.0
    slide_friction: bool = True      # the refill's axial slide friction h_sl (+-h_sl cot th across the pen, sign with
                                     # the slide direction: the nib's motion makes the refill slide, ds = cot th dq)
    label: str = "ASSUMPTION duty (Rev H / study N 1 mm rms at 8 Hz; CON-20 writing speed; 70 % contact)"


def loads_at(nib: NibModel, theta: float, phi: float, F_s: float, duty: Duty, balance=None) -> Dict:
    """Every load at one pose (tip-referred, N, per nib axis) and the copper loss it costs (W)."""
    st = C.writing_load_stats(theta, phi, F_s, duty.ink, duty.paper, v=duty.v_write)
    Q_static = st["static"]
    Q_mean = st["mean_sliding"]
    sig_fric = st["rms_about_mean"]
    if duty.slide_friction:
        h_sl = val(CONTACT["slide_friction"])
        sig_sl = h_sl / math.tan(theta) * np.abs(np.array([math.cos(phi), math.sin(phi)]))
        sig_fric = np.sqrt(sig_fric ** 2 + sig_sl ** 2)
    G = gravity_load(nib, theta, phi)
    w = 2 * math.pi * duty.f
    D_inert = nib.m_eff_tip * w * w * duty.q_rms
    k_net = nib.k_tip - nib.k_mag_tip + geometric_stiffness(nib, theta, F_s)
    D_flex = k_net * duty.q_rms
    D_rms = math.sqrt(D_inert ** 2 + D_flex ** 2)
    Bc = np.zeros(2)
    Bu = np.zeros(2)
    extra = {}
    if balance is not None:
        bb = balance.balance_force(nib, theta, phi, F_s, duty)
        Bc, Bu = bb["B_contact"], bb["B_penup"]
        sig_fric = np.sqrt(sig_fric ** 2 + bb.get("sigma_extra", np.zeros(2)) ** 2)
        D_rms = math.sqrt(D_rms ** 2 + (bb.get("k_add", 0.0) * duty.q_rms) ** 2)
        extra = {k: v for k, v in bb.items() if k not in ("B_contact", "B_penup")}
    par = np.array([nib.F_par, 0.0])
    hold_c = Q_mean + Bc + G + par
    hold_u = Bu + G + par
    c = duty.contact
    EF2 = c * hold_c ** 2 + (1 - c) * hold_u ** 2 + c * sig_fric ** 2 + D_rms ** 2
    Km2 = nib.Km_tip ** 2
    out = {
        "theta_deg": theta / D2R, "phi_deg": phi / D2R, "F_s": F_s, "mu": st["mu"],
        "Q_static": Q_static.tolist(), "Q_mean_sliding": Q_mean.tolist(), "sigma_friction": sig_fric.tolist(),
        "gravity": G.tolist(), "D_inertia_rms": D_inert, "D_flexure_rms": D_flex, "k_net_tip": k_net,
        "balance_contact": Bc.tolist(), "balance_penup": Bu.tolist(), "parasitic": par.tolist(),
        "P_hold_contact_W": float(np.sum(hold_c ** 2) / Km2), "P_penup_W": float(np.sum(hold_u ** 2) / Km2),
        "P_friction_W": float(c * np.sum(sig_fric ** 2) / Km2), "P_dynamic_W": float(2 * D_rms ** 2 / Km2),
        "P_mean_W": float(np.sum(EF2) / Km2),
        "P_static_unbalanced_W": float(np.sum((Q_static + G) ** 2) / Km2),
        "I_hold_A": float(np.linalg.norm(hold_c) / (nib.Km_tip * math.sqrt(nib.R_coil))),
    }
    out.update({"balance_" + k: v for k, v in extra.items()})
    return out


def over_roll(nib: NibModel, theta: float, F_s: float, duty: Duty, balance=None, n: int = 24) -> Dict:
    rows = [loads_at(nib, theta, 2 * math.pi * k / n, F_s, duty, balance) for k in range(n)]
    P = np.array([r["P_mean_W"] for r in rows])
    H = np.array([r["P_hold_contact_W"] for r in rows])
    return {"P_mean_min": float(P.min()), "P_mean_max": float(P.max()), "P_hold_min": float(H.min()),
            "P_hold_max": float(H.max()), "rows": rows}


# ------------------------------------------------------------------------------------------------ study N's duty model
def nose2_duty_model(theta_deg: float = 50.0) -> Dict:
    """Study N's duty model (nose2/designs.duty_forces, imported read-only) for the recommended C1S design: the loads it
    counts and the copper loss it predicts (CALC, study N)."""
    import torch
    from nose2 import designs as ND
    d = c1s()
    duty = ND.Duty()
    m_eff = torch.tensor(d["m_eff_tip_g"] * 1e-3, dtype=torch.float64)
    k_tip = torch.tensor(d["k_tip_N_m"], dtype=torch.float64)
    Fg = torch.tensor(d["F_grav_tip_N"], dtype=torch.float64)
    Ftr, Faw, Fpk = ND.duty_forces(m_eff, k_tip, Fg, duty)
    Km = d["Km_tip"]
    terms = {"inertia_tremor_N": float(m_eff) * duty.tremor_a_eff, "flexure_N": float(k_tip) * duty.tremor_x_rms,
             "ball_drag_rms_N": math.sqrt(duty.aw_ink_share * (ND.MU_BALL * ND.N_BALL) ** 2 / 2.0),
             "gravity_N": float(Fg), "static_side_load_N": 0.0}
    return {"terms_tremor_duty": terms, "F_tremor_rms_N": float(Ftr), "F_autowrite_rms_N": float(Faw),
            "P_tremor_W": 2 * (float(Ftr) / Km) ** 2, "P_autowrite_W": 2 * (float(Faw) / Km) ** 2,
            "N_BALL": ND.N_BALL, "THETA_deg": ND.THETA / D2R, "MU_BALL": ND.MU_BALL,
            "missing": "the static side load N_BALL cos(THETA) = F_c cot(theta): the model counts the ball's friction "
                       "mu N_BALL but not the component of the normal force N_BALL across the tilted pen",
            "label": "CALC (nose2/designs.duty_forces with the recommended design's m_eff, k_tip and gravity; read-only)"}


def sim2j_power() -> Dict:
    """sim2j's executed power runs (results/sim2j/power.json and power_split.json, SIM) as quoted evidence."""
    p = REPO_ROOT / "results" / "sim2j" / "power.json"
    if not p.exists():
        return {}
    d = json.load(open(p))
    sim = d.get("sim", {})
    out = {}
    for k, v in sim.items():
        out[k] = {kk: v.get(kk) for kk in ("P_nose_W", "ink_err_um", "letters_read", "moved_vs_clean_um")}
    split = {}
    ps = REPO_ROOT / "results" / "sim2j" / "power_split.json"
    if ps.exists():
        dd = json.load(open(ps))
        split = {k: {kk: v.get(kk) for kk in ("P_cu_mean_W", "P_cu_ball_on_paper_W", "P_cu_lifted_W", "T_coil_end_C")}
                 for k, v in dd.get("sim", {}).items()}
    return {"rows": out, "split": split,
            "split_label": "SIM (sim2j power_split.json: writer 0 v2, seed 200, tremor-free, nose held centred): nominal "
                           "2.25 W = ~1.1 W static side load + ~0.74 W servo on unfiltered Hall noise + ~0.4 W friction and "
                           "holding; F_c 0.075 N -> 1.32 W",
            "label": "SIM (sim2j, writer 0, seed 200; results/sim2j/power.json)",
            "doc": "docs/revJ_simulation.md section 8.1: nominal 2.25 W mean (2.68 W with the ball on the paper), 1.51 W "
                   "without the Hall noise, 1.32 W with a 0.075 N spring"}


def reconcile_c1s(F_s: float = 0.15) -> Dict:
    """The C1S load list at 35/50/60/75 deg (tip-referred N and coil W), the duty model's prediction and the missing
    static term, and sim2j's measured powers (CALC + SIM)."""
    nib = c1s_model()
    duty = Duty()
    rows = []
    for th in THETAS:
        t = th * D2R
        L = loads_at(nib, t, 0.0, F_s, duty)
        rev = C.review_static_power(th, F_s)
        rows.append({"theta_deg": th, "static_side_load_N": C.static_side_load(t, F_s),
                     "static_side_load_with_gravity_N": L["Q_static"][0] + L["gravity"][0],
                     "mean_sliding_load_N": L["Q_mean_sliding"][0], "friction_rms_N": L["sigma_friction"],
                     "gravity_N": L["gravity"][0], "inertia_rms_N": L["D_inertia_rms"], "flexure_rms_N": L["D_flexure_rms"],
                     "geometric_k_N_m": geometric_stiffness(nib, t, F_s),
                     "P_static_review_W": rev["P_W"], "P_hold_contact_W": L["P_hold_contact_W"],
                     "P_mean_W": L["P_mean_W"], "I_hold_A": L["I_hold_A"]})
    nd = nose2_duty_model()
    t50 = 50 * D2R
    static50 = C.static_side_load(t50, F_s)
    Ftr = nd["F_tremor_rms_N"]
    P_with = 2 * (Ftr / nib.Km_tip) ** 2 + (static50 / nib.Km_tip) ** 2 * duty.contact
    return {"rows": rows, "duty_model": nd,
            "duty_model_plus_static_50deg_W": P_with,
            "why_missed": [
                "Study N's duty model (nose2/designs.duty_forces) sums inertia, suspension, gravity and the ball's DRAG "
                "mu N_BALL; the normal force N_BALL = F_c / sin(theta) is computed, but its component across the tilted "
                "pen, N_BALL cos(theta) = F_c cot(theta), never enters the force list.",
                "The design duties were calibrated on HW1 (a 2-D page-plane hand-pen model): HW1 has no refill spring "
                "geometry, so the calibration run could not reveal the term (docs/revJ_simulation.md section 5).",
                "The earlier Rev H nose held the same load on a 34 mm arm (0.36 / 0.13 / 0.01 W with image-method Km, "
                "CALC, claims register); C1S shortened the arm to 11.5 mm to reach 6 mm of travel, multiplying the "
                "coil force by 6.65: the term grew from a nuisance to the dominant load.",
                "sim2 (a 3-D model with the refill slide and the contact law) contains the term, and its runs measured it "
                "(about 1.1 W of 2.25 W, docs/revJ_simulation.md section 8.1; SIM)."],
            "sim2j": sim2j_power(),
            "label": "CALC (this module) + CALC (study N's model, read-only) + SIM (sim2j, quoted)"}


def load_catalogue() -> List[Dict]:
    """The list of every load on the nib, with its formula and its evidence status (for the doc and nib.yaml)."""
    return [
        {"load": "static side load", "formula": "N (n . u), N = F_s' / (sin th - mu v_h cos th): F_c cot th with no friction",
         "status": "CALC (vector statics); F_c ASSUMPTION until gate G1"},
        {"load": "ball drag and friction-dependent side load", "formula": "-mu N v_hat . u; tilt-plane band F_c cot(th -+ phi_f)",
         "status": "CALC on a friction map (LIT CON-13 base, ASSUMPTION load/speed shapes)"},
        {"load": "refill slide friction", "formula": "F_s' = F_s -+ h_sl changes N and the side load by -+h_sl cot th (the "
         "nib's motion slides the refill: ds = cot th dq), counted as a fluctuation of rms h_sl cot th in the tilt plane",
         "status": "ASSUMPTION h_sl 0.01 N (Rev J)"},
        {"load": "inertia", "formula": "m_eff (2 pi f)^2 q", "status": "CALC (mass properties of each design)"},
        {"load": "suspension (flexure)", "formula": "k_tip q", "status": "CALC (flexure.py; beam models)"},
        {"load": "magnetic negative stiffness", "formula": "-k_mag q (moving-magnet designs; zero for a moving coil)",
         "status": "CALC (magnetics.py, image method: an upper bound for ideal iron)"},
        {"load": "parasitic magnetic attraction", "formula": "axial pull F_pull on the suspension; lateral F_pull e for a "
         "centring error e (gimbal: -F e torque)", "status": "CALC (magnetics.py)"},
        {"load": "gravity (any roll)", "formula": "gimbal -m g (d_cm/L_t)(n . u); translation m g (n . u)",
         "status": "CALC (mass properties)"},
        {"load": "geometric (contact through a tilting refill)", "formula": "F_s (1 + cos^2 th) / (L_t sin^2 th)",
         "status": "CALC (gimbal only)"},
        {"load": "pen lift", "formula": "contact load -> 0 in ms; a persisting bias B_u becomes the load",
         "status": "CALC"},
        {"load": "refill replacement", "formula": "F_s +-20 % or another ink's force; ball position +0.3 mm; refill mass",
         "status": "LIT CON-22 (length tolerance) + ASSUMPTION"},
    ]
