r"""The candidate nibs (a)-(h) for both grip classes, designed with the same models and judged on the same task, load and
uncertainty distributions (CALC on PROPOSED DESIGNS; every input labelled in labels.py or here).

Grip classes: 'pen24' (the user's bigger grip, DEC-029: 24 mm, the Rev J.1 base pen without its C1S nose and heel drive)
and 'slim' (the review's trade-study core: 12-16 mm, 25-40 g; nominal 14 mm).

Nib hardware families
  translation  (f and b, c, d, e, g): the refill is carried by a short carrier that translates on four wires parallel to
               the pen axis (optical-pickup style suspension, flexure.py); a MOVING-COIL annular axial-gap actuator
               (magnetics.py, actuators.vc_axial) drives it directly (tip motion = coil motion); the refill translates
               whole, its holder stiffened by a titanium sleeve.
  gimbal       (a): the Rev H / C1S idea with a small travel and a long arm: a cross-strip gimbal L_t behind the ball and a
               moving-magnet spherical-gap actuator L_a behind the gimbal (nose2's topology), lever L_t / L_a.
  piezo        (h): PICMA-class multilayer benders in push-pull pairs per axis drive the refill's front collar; the refill
               pivots at a rear gimbal (the pencil's Q layout, DEC-019/030), lever lambda.
Balance options: none, (b) scheduled bias (balance.BiasSpring), (c) contact-driven counter-face (balance.CounterFace),
(d) a lower ink force, (e) a steeper tip (a short cartridge bent by beta toward the paper normal, its roll scheduled).
(g) is (c)'s fine nib at +-0.5 mm with study W's pivot collar for the large motion (wholepen.designs, read-only).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, List, Optional

import numpy as np

from . import actuators as A
from . import balance as BL
from . import contact as C
from . import flexure as FX
from . import loads as LD
from . import thermal as TH
from .labels import CONTACT, DRIVE, FAT, G0, MAT, POSITIONER, SENSORS, TASKS, THERMAL, val

D2R = math.pi / 180.0
THETAS = (35.0, 50.0, 60.0, 75.0)
# the duties every candidate is judged on (ASSUMPTION: sinusoidal correction per axis at 8 Hz, writing directions uniform,
# CON-20 writing speed, 70 % contact): A fits every candidate's loaded travel; B is the +-1 mm nibs' design duty
DUTY_A = LD.Duty(q_rms=0.20e-3)
DUTY_B = LD.Duty(q_rms=0.50e-3)


# ------------------------------------------------------------------------------------------------ grip classes
@dataclass
class Grip:
    name: str
    od: float
    wall: float
    fixed_parts: List = field(default_factory=list)     # (name, kg, z m) of the parts that do not move with the nib
    cell_Wh: float = 2.22
    electronics_W: float = 0.047
    L_base: float = 0.144

    @property
    def bore_r(self) -> float:
        return self.od / 2 - self.wall


def pen24() -> Grip:
    """The Rev J.1 base pen (results/revJ1/layout.json, CALC) without its C1S nose, gimbal, pen-lift drum and heel drive:
    shell, front sleeve, skid ring, cap, spreader, board with IMU and nose Hall, page sensor, USB, cell, LRA (45.9 g before
    the +10 % wiring allowance)."""
    parts = [("skid_ring", 0.27e-3, 0.010), ("front_sleeve", 7.77e-3, 0.030), ("shell", 8.62e-3, 0.095),
             ("rear_cap", 1.06e-3, 0.142), ("heat_spreader", 0.21e-3, 0.040), ("main_board", 5.5e-3, 0.061),
             ("page_sensor", 1.0e-3, 0.013), ("usb", 0.5e-3, 0.138), ("battery_LIR14500", 20.0e-3, 0.116),
             ("lra", 1.0e-3, 0.096)]
    return Grip("pen24", 24e-3, 1.0e-3, parts, cell_Wh=val(DRIVE["cell_Wh_usable"]), electronics_W=float(np.mean(val(DRIVE["electronics_W"]))),
                L_base=0.144)


def slim(od: float = 14e-3) -> Grip:
    """A slim core (the review's 12-16 mm, 25-40 g trade-study target): PEEK shell 0.8 mm, a 10440-class cell
    (ASSUMPTION), a narrow board, the same page sensor and IMU (masses ASSUMPTION scaled from Rev J.1)."""
    L = 0.140
    shell = math.pi * od * 0.8e-3 * L * val(MAT["PEEK_rho"])
    parts = [("skid_ring", 0.15e-3, 0.008), ("shell", shell, 0.075), ("rear_cap", 0.5e-3, 0.138), ("main_board", 3.0e-3, 0.070),
             ("page_sensor", 0.7e-3, 0.012), ("usb_pads", 0.3e-3, 0.136), ("battery_10440", val(DRIVE["cell_slim_mass"]), 0.112),
             ("lra", 0.6e-3, 0.090)]
    return Grip(f"slim{od * 1e3:.0f}", od, 0.8e-3, parts, cell_Wh=val(DRIVE["cell_slim_Wh_usable"]),
                electronics_W=float(np.mean(val(DRIVE["electronics_W"]))), L_base=L)


# ------------------------------------------------------------------------------------------------ design record
@dataclass
class Design:
    key: str                         # candidate id, e.g. 'c_counterface'
    title: str
    grip: Grip
    family: str                      # 'translation' | 'gimbal' | 'piezo'
    travel: float = 1.0e-3           # usable tip travel (m, radius)
    F_s: float = 0.15
    # translation / voice coil
    w: float = 5.0e-3
    t_m: float = 2.0e-3
    t_c: float = 0.45e-3
    wire: FX.WireStage = field(default_factory=lambda: FX.WireStage(n_w=4, d=0.20e-3, L=25e-3, mat="Ti6Al4V"))
    z_act: float = 0.032             # actuator centre from the ball
    # gimbal
    L_t: float = 0.040
    L_a: float = 0.040
    # piezo
    piezo: Optional[A.PiezoStage] = None
    piezo_plate: Optional[Dict] = None
    # balance
    balance: object = field(default_factory=BL.NoBalance)
    balance_mass: float = 0.0
    balance_z: float = 0.075
    # steep tip
    bend: float = 0.0                # rad (e)
    tip_roll: str = "scheduled"      # 'scheduled' | 'keyed'
    # the collar (g)
    collar: Optional[Dict] = None
    km_scale: float = 1.0            # Km uncertainty (image-method magnetics is an upper bound: 0.7-1.0, DEC-041)
    notes: Dict = field(default_factory=dict)


# ------------------------------------------------------------------------------------------------ hardware models
TI_SLEEVE = 0.35e-3          # kg titanium stiffening sleeve over the refill holder (PROPOSED DESIGN, EI 0.39 N m^2)
CARRIER = 0.30e-3            # kg carrier tube, bushings and the coil former's hub (ASSUMPTION)
HALL_MAGNET = 0.05e-3        # kg the carrier's sensing magnet (1 x 1 mm N52 cylinder; ASSUMPTION)


def translation_hw(D: Design) -> Dict:
    s_stop = D.travel + 0.2e-3
    act = A.vc_axial(D.w, D.t_m, D.t_c, s_stop, moving="coil")
    Km0, Km_min = float(act["Km0"]) * D.km_scale, float(act["Km_min"]) * D.km_scale
    refill_m = val(CONTACT["refill_mass"]) if D.bend == 0 else 0.35e-3        # (e): a short custom cartridge (ASSUMPTION)
    m_move = float(act["m_move"]) + CARRIER + refill_m + 0.5e-3 + TI_SLEEVE + HALL_MAGNET
    ws = D.wire
    fx = FX.wire_stage(ws, D.travel, s_stop, m_move)
    m_eff = m_move + fx["mass_g"] * 1e-3 / 3
    r_need = float(act["r_out"]) + 0.6e-3                                    # coil end turns + keeper rim + 0.3 mm running clearance
    stator = float(act["m_stat"]) + 0.5e-3 + 0.3e-3                           # + housing + wire anchor ring
    return {"act": {k: (float(v) if hasattr(v, "item") else v) for k, v in act.items()}, "Km_tip": Km0, "Km_tip_min": Km_min,
            "m_eff": m_eff, "m_move": m_move, "k_tip": fx["k_lat_N_m"], "flex": fx, "r_need": r_need, "stator_mass": stator,
            "m_cu": float(act["m_cu"]), "s_stop": s_stop, "L_src": float(act["length"]), "k_mag": 0.0}


ARM_TUBE = (4.0e-3, 3.0e-3)   # m Ti-6Al-4V arm tube od / id from the gimbal to the magnets (PROPOSED DESIGN)


def gimbal_hw(D: Design) -> Dict:
    """Candidate (a): a small-travel gimbal with a longer magnet arm (Rev H's layout: ball 45 mm in front of the pivot,
    magnets 34 mm behind it, lever 1.32; DEC-034 era), a moving-magnet checkerboard (study N's topology through
    actuators.vc_axial with moving='magnet'; the arm, not the refill, passes the actuator: hole for a 1 mm rod), a
    75 um cross-strip gimbal (revj1.gimbal), the arm a titanium tube (bending mode reported)."""
    lam = D.L_a / D.L_t                                                        # actuator motion per tip motion
    s_stop = (D.travel + 0.2e-3) * lam
    act = A.vc_axial(D.w, D.t_m, D.t_c, s_stop, moving="magnet", refill_r=0.5e-3)
    Km0, Km_min = float(act["Km0"]) * lam * D.km_scale, float(act["Km_min"]) * lam * D.km_scale
    # nose inertia about the gimbal: titanium carrier tube (7/6 mm) from the ball to the gimbal, the refill (67 mm from
    # the ball: the part behind the gimbal moves opposite), the nozzle, the arm tube and the magnets at L_a
    rho_ti = val(MAT["Ti_rho"])
    L_t = D.L_t
    m_tube = rho_ti * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * L_t
    m_arm = rho_ti * math.pi / 4 * (ARM_TUBE[0] ** 2 - ARM_TUBE[1] ** 2) * D.L_a
    items = [(m_tube, -L_t / 2, L_t), (val(CONTACT["refill_mass"]), 0.0335 - L_t, 0.067), (0.4e-3, -L_t + 0.004, 0.0),
             (float(act["m_move"]), D.L_a, 0.0), (m_arm, D.L_a / 2, D.L_a)]
    I = sum(m * (z * z + Lr * Lr / 12.0) for m, z, Lr in items)
    m_nib = sum(m for m, _, _ in items)
    d_cm = sum(m * z for m, z, _ in items) / m_nib
    from revj1 import gimbal as G
    st = G.Strip(t=75e-6, b=2.55e-3, L=3.8e-3)
    k_r = G.k_elastic_closed(st)
    k_tip = k_r / L_t ** 2
    # pull of the moving magnets toward the plate iron loads the gimbal axially (magnetics.keeper_pull scale: 12.7 N for
    # 5 mm poles over a 1.35 mm gap; scaled by the pole area x B^2 here, CALC)
    B = float(act["B"])
    pull = 12.7 * (D.w / 5e-3) ** 2 * (B / 0.57) ** 2
    alpha_u = D.travel / L_t
    gb = FX.gimbal_check(t=75e-6, F_pull=pull, alpha_usable=alpha_u, alpha_stop=(D.travel + 0.2e-3) / L_t)
    r_need = float(act["r_out"]) + 0.6e-3 + s_stop
    E_ti = val(MAT["Ti_E"])
    I_arm = math.pi / 64 * (ARM_TUBE[0] ** 4 - ARM_TUBE[1] ** 4)
    k_arm = 3 * E_ti * I_arm / D.L_a ** 3
    f_arm = math.sqrt(k_arm / (float(act["m_move"]) + 0.24 * m_arm)) / (2 * math.pi)
    return {"act": {k: (float(v) if hasattr(v, "item") else v) for k, v in act.items()}, "Km_tip": Km0, "Km_tip_min": Km_min,
            "m_eff": I / L_t ** 2, "m_nib": m_nib, "d_cm": d_cm, "k_tip": k_tip, "gimbal": gb, "pull_N": pull,
            "r_need": r_need, "stator_mass": float(act["m_stat"]) + 2.0e-3 + 0.5e-3, "m_cu": float(act["m_cu"]),
            "lever_tip_per_act": 1 / lam, "s_stop": s_stop, "L_src": float(act["length"]), "k_mag": 0.0,
            "f_arm_Hz": f_arm, "m_arm_g": m_arm * 1e3}


def piezo_hw(D: Design, F_static: float, duty: Optional[LD.Duty] = None) -> Dict:
    ps = D.piezo or A.PiezoStage()
    duty = duty or DUTY_A
    return A.piezo_stage(ps, F_static, q_rms=duty.q_rms, f=duty.f)


# ------------------------------------------------------------------------------------------------ evaluation
def _nib_model(D: Design, hw: Dict) -> LD.NibModel:
    if D.family == "gimbal":
        return LD.NibModel(name=D.key, kind="gimbal", L_t=D.L_t, Km_tip=hw["Km_tip"], m_eff_tip=hw["m_eff"], m_nib=hw["m_nib"],
                           d_cm=hw["d_cm"], k_tip=hw["k_tip"], R_coil=2.5)
    return LD.NibModel(name=D.key, kind="translation", Km_tip=hw["Km_tip"], m_eff_tip=hw["m_eff"], m_nib=hw["m_eff"],
                       k_tip=hw["k_tip"], R_coil=2.5)


def _pose_theta(D: Design, theta: float) -> float:
    """(e): the contact angle at the bent tip (bend in the tilt plane, roll kept by the scheduler or the grip)."""
    if D.bend == 0:
        return theta
    err = 2.0 * D2R if D.tip_roll == "scheduled" else 15.0 * D2R
    s = math.cos(D.bend) * math.sin(theta) + math.sin(D.bend) * math.cos(err) * math.cos(theta)
    th = math.asin(min(1.0, s))
    return th if th > 0 else 1e-3


def _mirror_theta(th_tip: float) -> float:
    # a tip past the paper normal (> 90 deg) mirrors: the side load reverses; magnitude cot of the acute angle
    return th_tip if th_tip <= 0.5 * math.pi else math.pi - th_tip


def evaluate(D: Design, duty: Optional[LD.Duty] = None, detail: bool = True, fast: bool = False) -> Dict:
    """All metrics of one design at one duty.  detail: a 30-min thermal run with its trace (else 5 min); fast: the
    thermal steady state only and no roll sweep (the optimiser's inner loop)."""
    duty = duty or DUTY_A
    g = D.grip
    out: Dict = {"key": D.key, "title": D.title, "grip": g.name, "family": D.family, "travel_mm": D.travel * 1e3, "F_s_N": D.F_s,
                 "balance": D.balance.describe() if hasattr(D.balance, "describe") else {"mechanism": "none"}}
    # ---------------------------------------------------------------- hardware
    if D.family == "translation":
        hw = translation_hw(D)
    elif D.family == "gimbal":
        hw = gimbal_hw(D)
    else:
        hw = None
    rows = []
    if D.family in ("translation", "gimbal"):
        nib = _nib_model(D, hw)
        for th in THETAS:
            t = th * D2R
            t_tip = _mirror_theta(_pose_theta(D, t))
            L = LD.loads_at(nib, t_tip, 0.0, D.F_s, duty, D.balance)
            ro = LD.over_roll(nib, t_tip, D.F_s, duty, D.balance, n=12) if not fast else \
                {"P_mean_max": L["P_mean_W"], "P_hold_max": L["P_hold_contact_W"]}
            rows.append({"theta_deg": th, "theta_tip_deg": t_tip / D2R, "P_hold_W": L["P_hold_contact_W"],
                         "P_penup_W": L["P_penup_W"], "P_friction_W": L["P_friction_W"], "P_dynamic_W": L["P_dynamic_W"],
                         "P_mean_W": L["P_mean_W"], "P_mean_roll_max_W": ro["P_mean_max"], "P_hold_roll_max_W": ro["P_hold_max"],
                         "I_hold_A": L["I_hold_A"], "hold_N": float(np.linalg.norm(np.array(L["Q_mean_sliding"]) + np.array(L["balance_contact"]) + np.array(L["gravity"]))),
                         "static_unbalanced_N": float(np.linalg.norm(L["Q_static"])), "k_net_tip": L["k_net_tip"]})
        Km_min = hw["Km_tip_min"]
        # peak force at the worst corner, hot coil and a low battery (3.3 V, R x 1.35 at +90 K)
        R_hot = 2.5 * (1 + val(MAT["Cu_alpha"]) * 90)
        I_pk = min(val(DRIVE["I_peak"]), val(DRIVE["V_low"]) / R_hot)
        F_pk = Km_min * math.sqrt(2.5) * I_pk
        hold35 = rows[0]["hold_N"]
        k_net = rows[0]["k_net_tip"]
        w12 = 2 * math.pi * 12.0
        F_need_full = hold35 + abs(k_net) * D.travel + hw["m_eff"] * w12 * w12 * D.travel + 0.05
        x_load = min(D.travel, max(0.0, (F_pk - hold35 - 0.05) / max(abs(k_net) + hw["m_eff"] * w12 * w12, 1e-9)))
        P_peak = (F_need_full / Km_min) ** 2
        out.update({"Km_tip": hw["Km_tip"], "Km_tip_min": Km_min, "m_eff_tip_g": hw["m_eff"] * 1e3, "k_tip_N_m": hw["k_tip"],
                    "F_peak_hot_lowV_N": F_pk, "F_need_full_travel_12Hz_N": F_need_full, "travel_under_load_mm": x_load * 1e3,
                    "P_peak_W": P_peak, "r_need_mm": hw["r_need"] * 1e3, "fits_bore": hw["r_need"] <= g.bore_r + 1e-9})
    else:
        # piezo: the static load consumes stroke instead of power
        rows = []
        for th in THETAS:
            t = th * D2R
            st = C.writing_load_stats(t, 0.0, D.F_s, duty.ink, duty.paper)
            bal = D.balance.balance_force(None, t, 0.0, D.F_s, duty) if not isinstance(D.balance, BL.NoBalance) else None
            hold = st["mean_sliding"] + (bal["B_contact"] if bal else 0.0)
            F_st = float(np.linalg.norm(hold))
            pz = piezo_hw(D, F_st, duty)
            rows.append({"theta_deg": th, "static_N": F_st, "loaded_usable_mm": pz["loaded_usable_mm"],
                         "P_mean_W": pz["P_drive_2axes_W"], "P_hold_W": val(A.PIEZO["boost_Iq_W"]),
                         "P_dynamic_W": pz["P_drive_2axes_W"] - val(A.PIEZO["boost_Iq_W"]),
                         "P_mean_roll_max_W": pz["P_drive_2axes_W"], "f_loaded_Hz": pz["f_loaded_Hz"],
                         "duty_feasible": pz["duty_feasible"]})
        pz0 = piezo_hw(D, rows[0]["static_N"], duty)
        pz_full = piezo_hw(D, rows[0]["static_N"], LD.Duty(q_rms=pz0["loaded_usable_mm"] * 1e-3 / math.sqrt(2)))
        out.update({"piezo": pz0, "travel_under_load_mm": min(r["loaded_usable_mm"] for r in rows),
                    "m_eff_tip_g": pz0["m_eff_tip_g"], "P_peak_W": pz_full["P_drive_2axes_W"],
                    "fits_bore": True, "Km_tip": None, "duty_feasible": all(r["duty_feasible"] for r in rows)})
    out["rows"] = rows
    Pm = {r["theta_deg"]: r["P_mean_W"] for r in rows}
    out["P_mean_W_by_theta"] = Pm
    out["P_cont_W"] = float(np.mean([Pm[35.0], Pm[50.0], Pm[60.0], Pm[75.0]]))
    out["P_cont_worst_W"] = float(max(Pm.values()))
    # ---------------------------------------------------------------- ink force sensitivity (gate G1)
    if D.family in ("translation", "gimbal"):
        nib = _nib_model(D, hw)
        sens = {}
        for Fs in (0.05, 0.10, 0.15, 0.30, 0.50):
            t = _mirror_theta(_pose_theta(D, 35 * D2R))
            sens[f"{Fs:.2f}"] = LD.loads_at(nib, t, 0.0, Fs, duty, D.balance)["P_mean_W"]
        out["P_mean_35deg_vs_Fs"] = sens
    # ---------------------------------------------------------------- thermal (two nodes, governor)
    if D.family in ("translation", "gimbal"):
        tn = TH.model_for(g.od, max(hw["L_src"], 5e-3), hw["m_cu"], spreader=TH.GRAPHITE_30, wall=g.wall)
        P35c = rows[0]["P_hold_W"] + rows[0]["P_friction_W"] / max(duty.contact, 1e-6) + rows[0]["P_dynamic_W"]
        P35u = rows[0]["P_penup_W"] + rows[0]["P_dynamic_W"]
        st = tn.steady(Pm[35.0])
        if fast:
            g_ss = min(1.0, st["P_allow_skin_W"] / max(Pm[35.0], 1e-12), st["P_allow_coil_W"] / max(Pm[35.0], 1e-12))
            run = {"T_skin_peak_C": min(st["T_skin_C"], tn.T_s_target), "T_coil_peak_C": tn.steady(Pm[35.0] * g_ss)["T_coil_C"],
                   "g_min": math.sqrt(g_ss), "trace": None, "note": "steady state (fast mode)"}
        else:
            run = TH.duty_run(tn, P35c, P35u, minutes=30 if detail else 5, dt=0.02)
        out["thermal"] = {"R_sa_K_W": tn.R_sa, "C_coil_J_K": tn.C_c, "steady_35deg": st,
                          "run_35deg_30min": {k: v for k, v in run.items() if k != "trace"},
                          "trace": run["trace"] if detail else None}
        out["T_skin_C"] = run["T_skin_peak_C"]
        out["T_coil_C"] = run["T_coil_peak_C"]
        out["governor_authority_min"] = run["g_min"]
    else:
        tn = TH.model_for(g.od, 20e-3, 0.0, spreader=None)
        st = tn.steady(Pm[35.0])
        out["thermal"] = {"steady_35deg": st, "note": "piezo losses are in the drive electronics and the plates' dielectric loss; "
                                                      "no coil"}
        out["T_skin_C"] = st["T_skin_C"]
        out["T_coil_C"] = None
        out["governor_authority_min"] = 1.0
    # ---------------------------------------------------------------- structure, fatigue, shock, modes
    if D.family == "translation":
        fx = hw["flex"]
        out["fatigue"] = {"goodman_SF_full_travel": fx["goodman_SF"], "static_SF_stop": fx["static_SF_stop"], "Kt": D.wire.Kt,
                          "material": D.wire.mat, "cycles": val(FAT["cycles"])}
        out["shock"] = FX.shock(D.wire, hw["m_move"])
        beam = FX.RefillBeam(EI=0.385)
        th50 = 50 * D2R
        mf = FX.loaded_modes(beam, hw["m_move"] - val(CONTACT["refill_mass"]) - 0.5e-3 - TI_SLEEVE, 3e-8, D.z_act,
                             D.z_act - 6e-3, D.z_act + 6e-3, hw["k_tip"], fx["k_tilt_Nm_rad"], 0.0, D.F_s, 0.0)
        mc = FX.loaded_modes(beam, hw["m_move"] - val(CONTACT["refill_mass"]) - 0.5e-3 - TI_SLEEVE, 3e-8, D.z_act,
                             D.z_act - 6e-3, D.z_act + 6e-3, hw["k_tip"], fx["k_tilt_Nm_rad"], 0.0, D.F_s,
                             FX.stick_stiffness(D.F_s, th50))
        out["modes"] = {"pen_up_Hz": mf["f_Hz"], "ball_stuck_Hz": mc["f_Hz"], "suspension_Hz": fx["f_suspension_Hz"],
                        "violin_Hz": fx["f_violin_Hz"]}
        f_par = min(mf["f_Hz"][1], mc["f_Hz"][1], fx["f_violin_Hz"])
        out["bandwidth_Hz"] = f_par / 3.0
        out["flexure"] = fx
    elif D.family == "gimbal":
        gb = hw["gimbal"]
        out["fatigue"] = {"goodman_SF_full_travel": gb["goodman_SF"], "buckling_N": gb["buckling_N"], "pull_N": hw["pull_N"],
                          "buckling_SF": gb["buckling_N"] / max(hw["pull_N"], 1e-9), "strain_stop": gb["strain_stop"],
                          "Kt": val(FAT["Kt_etched_strip"]), "material": "301 FH strips 75 um", "cycles": val(FAT["cycles"])}
        out["shock"] = {"note": "Rev J.1's rule: axial stops <= 5 um rear / 20 um front keep buckled strips elastic (revj1.gimbal.shock_check)"}
        # parasitic mode: carrier tube bending (nose2.designs.carrier_mode) scaled
        E_ti = val(MAT["Ti_E"])
        I_a = math.pi / 64 * (0.007 ** 4 - 0.006 ** 4)
        k = 3 * E_ti * I_a / (D.L_t - 0.005) ** 3
        f_carrier = math.sqrt(k / (1.3e-3 + 0.24 * val(MAT["Ti_rho"]) * math.pi / 4 * (0.007 ** 2 - 0.006 ** 2) * D.L_t)) / (2 * math.pi)
        out["modes"] = {"carrier_bending_Hz": f_carrier, "arm_bending_Hz": hw["f_arm_Hz"]}
        out["bandwidth_Hz"] = min(f_carrier, hw["f_arm_Hz"]) / 3.0
    else:
        pz = out["piezo"]
        out["fatigue"] = {"note": "PZT plates: fatigue by the manufacturer's rating; the decoupling leaves (C17200, pencil P0.2: "
                                  "38 um x 1.55 x 6.3 mm) carry the collar motion; see docs/opt_hardware.md"}
        out["shock"] = {"note": "brittle ceramic: the pencil study's finite-element drop surrogate (opt/hardware/drop_surrogate.py) "
                                "sized snubbers at 4 stations; a 1 m drop is the dominant risk (EXP-Q04 plate strength)"}
        out["modes"] = {"loaded_Hz": pz["f_loaded_Hz"]}
        out["bandwidth_Hz"] = pz["f_loaded_Hz"] / 3.0
    # ---------------------------------------------------------------- mass, size, centre of mass, battery
    parts = list(g.fixed_parts)
    if D.family == "translation":
        parts += [("nib_moving", hw["m_move"], 0.035), ("nib_stator", hw["stator_mass"], D.z_act),
                  ("suspension_wires", hw["flex"]["mass_g"] * 1e-3, D.z_act - 0.012)]
    elif D.family == "gimbal":
        parts += [("nib_moving", hw["m_nib"], D.L_t + hw["d_cm"]), ("nib_stator", hw["stator_mass"], D.L_t + D.L_a)]
    else:
        pz = out["piezo"]
        parts += [("piezo_plates", pz["plates_mass_g"] * 1e-3, 0.040), ("refill_collar", 1.6e-3, 0.035),
                  ("piezo_driver_boost", 0.8e-3, 0.065)]
    if D.balance_mass > 0:
        parts.append(("balance", D.balance_mass, D.balance_z))
    m = sum(p[1] for p in parts) * 1.10                                       # +10 % wiring and adhesives (P0/H1 convention)
    zcm = sum(p[1] * p[2] for p in parts) / sum(p[1] for p in parts)
    out["mass_g"] = m * 1e3
    out["com_mm"] = zcm * 1e3
    out["od_mm"] = g.od * 1e3
    extra_len = 0.0 if D.balance_mass == 0 else 0.004
    out["length_mm"] = (g.L_base + extra_len) * 1e3
    P_aux = 0.0
    if hasattr(D.balance, "balance_force"):
        try:
            P_aux = float(D.balance.balance_force(_nib_model(D, hw) if hw else None, 50 * D2R, 0.0, D.F_s, duty).get("P_aux_W", 0.0))
        except Exception:
            P_aux = 0.0
    drive_eff = 1.0 if D.family == "piezo" else val(DRIVE["driver_eff"])      # the piezo figure is already battery-side
    P_bat = g.electronics_W + out["P_cont_W"] / drive_eff + P_aux
    out["P_battery_W"] = P_bat
    out["battery_h"] = g.cell_Wh / P_bat
    out["P_aux_W"] = P_aux
    # ---------------------------------------------------------------- sensing, manufacture, failure state
    out["sensing"] = sensing(D, hw)
    out["failure_state"] = failure_state(D, hw, rows)
    out["manufacture"] = manufacture(D)
    out["hw"] = {k: v for k, v in (hw or {}).items() if k not in ("flex", "gimbal")} if hw else None
    return out


def sensing(D: Design, hw) -> Dict:
    """Internal (nib) and page-relative sensing (CALC on MFR/LIT inputs)."""
    # nib position: a 1 mm N52 magnet on the carrier and a 3-D Hall (TMAG5170, MFR OPT-44/OPT-53) on the stator; the
    # magnet is placed so the stop-to-stop stroke uses 80 % of the +-50 mT range: noise 140 uT rms (1x averaging,
    # 20 kSPS) -> 2 s_stop / (0.8 x 100 mT) per uT; filtered to 1 kHz: / sqrt(10)
    s_stop = (D.travel + 0.2e-3) * (hw["lever_tip_per_act"] ** -1 if hw and "lever_tip_per_act" in hw else 1.0) if hw else D.travel
    grad = 0.8 * 100e-3 / (2 * max(s_stop, 1e-4))              # T per m at the magnet
    tip_per_mag = hw.get("lever_tip_per_act", 1.0) if hw else 1.0
    noise_20k = 140e-6 / grad * tip_per_mag
    out = {"nib_hall_noise_um_20kSPS": noise_20k * 1e6, "nib_hall_noise_um_1kHz": noise_20k / math.sqrt(20) * 1e6,
           "nib_sensor": "TMAG5170-A1 3-D Hall (MFR OPT-44/OPT-53) over a 1 mm N52 magnet on the carrier; coil-field "
                         "cross-talk calibrated by current (EXP-B24)",
           "page_sensor": "dual lens-less optical flow near the tip (DeltaPen class, LIT OPT-01): MEASURED-style error "
                          "23.6 um median / 68.3 um mean per 10 ms window (LIT OPT-02), used in the simulations (sim.py)",
           "balance_sensing": "IMU tilt/roll (LSM6DSV16X, MFR OPT-37) for the face or bias schedule: 1 deg / 2 deg (ASSUMPTION)"
                              if not isinstance(D.balance, BL.NoBalance) else "none"}
    if D.family == "piezo":
        out["nib_sensor"] = "two DRV5055A4 linear Hall sensors on the collar magnet (pencil P0.2, MFR OPT-46)"
        out["nib_hall_noise_um_1kHz"] = 0.44
    return out


def failure_state(D: Design, hw, rows) -> Dict:
    """What the nib does unpowered (CALC): the static residual sags it by residual / k until a stop; the pen then
    writes like an ordinary pen with the ball offset."""
    if D.family == "piezo":
        return {"state": "unpowered plates relax to 0 V: the refill sits at the stage centre shifted by the static load / "
                         "plate stiffness; writes as a normal pen", "benign": True}
    k = max(hw["k_tip"], 1e-6)
    res = rows[0]["hold_N"]
    sag = min(res / k, D.travel + 0.2e-3)
    on_stop = res / k >= D.travel + 0.2e-3
    passive = isinstance(D.balance, BL.CounterFace) or D.bend != 0
    return {"sag_35deg_mm": sag * 1e3, "on_stop": bool(on_stop), "balance_passive": passive,
            "state": ("centred by the suspension, the counter-face still balancing: writes as a normal pen" if passive and not on_stop
                      else "the nib sags onto its soft stop (ball offset <= travel + 0.2 mm): writes as a normal pen"),
            "benign": True, "stale_command": "the supervisor zeroes the servo reference on reset (never replays a stroke)"}


def manufacture(D: Design) -> Dict:
    common = ["D1 refill (ISO 12757-1 type D, LIT CON-22), user-replaceable from the front"]
    if D.family == "translation":
        m = ["4 x Ti-6Al-4V wires, laser-welded or crimped into ring clamps with a 0.1 mm radius (Kt ~1.3-1.8)",
             "two-layer flat racetrack coils (self-bonding 0.10 mm wire) on a polyimide former, or a 4-layer flex PCB coil",
             "4 x N52 cuboid magnets on a laser-cut 1010 plate; a 1010 keeper; both bonded in the stator housing",
             "flexible polyimide leads to the moving coils (the Ti wires do not carry current: 100 x copper's resistivity)"]
    elif D.family == "gimbal":
        m = ["75 um 301 FH cross-strip gimbal (photo-etched, AMF-59), axial shock stops (Rev J.1 rule)",
             "spherical magnet cap and coil plate (study N's C1S parts, custom curved faces)"]
    else:
        m = ["4 custom PICMA-class multilayer plates (supplier's standard process, custom width; MFR AMF-11/53/63)",
             "C17200 decoupling leaves (38 um), snubbers, a 60 V boost with charge-recovery half-bridges (MFR AMF-57/58)"]
    if isinstance(D.balance, BL.CounterFace):
        m += ["counter-face: a 6 mm hardened steel disc on a 2-axis flexure gimbal behind the refill, a 3 mm rolling ball in the "
              "refill holder's end, a constant-force spring (fatigue-rated, EXP-N06) and a viscous follower stop",
              "two slow positioners with zero holding power (New Scale SQL-RV-1.8, MFR AMF-15/AMF-106: sold only in volume; "
              "fallback a micro-stepper leadscrew)" if getattr(D.balance, "driver", "") == "imu2" else
              "a slide cam (no motor for the tilt) " + ("and one roll positioner" if getattr(D.balance, "driver", "") == "slidecam" else "and a keyed grip")]
    if isinstance(D.balance, BL.BiasSpring):
        m += ["bias leaf spring pair with a 2-axis anchor moved by two SQL-RV-1.8 (MFR AMF-15)",
              "electro-permanent clutch (custom; switching energy ASSUMPTION)" if D.balance.gated == "epm" else "no clutch"]
    if D.bend:
        m += ["a custom short cartridge (about 20 mm) in a bent tip section; one slow rotary positioner for the tip's roll"]
    return {"parts": common + m}


# ------------------------------------------------------------------------------------------------ the candidates
def make(key: str, grip: Grip, **kw) -> Design:
    """Default (hand-sized) design of each candidate; the optimiser (optimise.py) then trades their continuous
    parameters.  Values PROPOSED DESIGN unless labelled."""
    slim_ = grip.name.startswith("slim")
    bore = grip.bore_r
    # the largest pole side that fits: r_out = sqrt(2) (w + e) + 0.6 mm <= bore
    e = (A.R_CARRIER + 1.2e-3 + 0.3e-3) / math.sqrt(2)
    w_fit = max((bore - 0.6e-3) / math.sqrt(2) - e, 1.2e-3)
    w = min(5.5e-3, w_fit)
    wire = FX.WireStage(n_w=4, d=0.20e-3 if not slim_ else 0.15e-3, L=25e-3 if not slim_ else 20e-3, mat="Ti6Al4V")
    base = dict(grip=grip, family="translation", w=w, t_m=2.0e-3 if not slim_ else 1.5e-3, t_c=0.45e-3 if not slim_ else 0.35e-3,
                wire=wire, travel=1.0e-3, z_act=0.032)
    if key == "a_long_arm":
        L_t, L_a = (0.035, 0.030) if slim_ else (0.045, 0.034)                # Rev H: 45 mm / 34 mm (lever 1.32)
        s_stop = (1.0e-3 + 0.2e-3) * L_a / L_t
        w_g = max((bore - 0.5e-3 - 2 * s_stop - 0.9e-3) / math.sqrt(2), 1.0e-3)
        d = Design(key=key, title="(a) longer-arm gimbal (Rev H layout, +-1 mm), no balance", **{**base, "family": "gimbal"},
                   L_t=L_t, L_a=L_a)
        d.w = min(5.5e-3, w_g)
    elif key == "b_bias":
        d = Design(key=key, title="(b) tilt/roll-scheduled bias spring (ungated)", **base,
                   balance=BL.BiasSpring(k_b=40.0, gated="none"), balance_mass=0.9e-3, balance_z=0.040)
    elif key == "b_bias_epm":
        d = Design(key=key, title="(b') scheduled bias with an electro-permanent clutch", **base,
                   balance=BL.BiasSpring(k_b=40.0, gated="epm"), balance_mass=1.3e-3, balance_z=0.040)
    elif key == "c_counterface":
        d = Design(key=key, title="(c) contact-driven counter-face balance (IMU-scheduled face)", **base,
                   balance=BL.CounterFace(driver="imu2", R_skid=7e-3 if not slim_ else 4.5e-3), balance_mass=1.2e-3, balance_z=0.076)
    elif key == "c_counterface_cam":
        d = Design(key=key, title="(c') counter-face with a slide cam and one roll positioner", **base,
                   balance=BL.CounterFace(driver="slidecam", R_skid=7e-3 if not slim_ else 4.5e-3), balance_mass=1.0e-3, balance_z=0.076)
    elif key == "c_counterface_keyed":
        d = Design(key=key, title="(c'') counter-face with a slide cam and a keyed grip (no motors)", **base,
                   balance=BL.CounterFace(driver="keyed", R_skid=7e-3 if not slim_ else 4.5e-3), balance_mass=0.7e-3, balance_z=0.076)
    elif key == "d_low_ink":
        d = Design(key=key, title="(d) lower ink force (0.075 N), no balance", **{**base, "F_s": 0.075})
    elif key == "e_steep_tip":
        d = Design(key=key, title="(e) steeper tip (35 deg bend, roll scheduled), short cartridge", **base,
                   bend=35 * D2R, tip_roll="scheduled", balance_mass=0.6e-3, balance_z=0.030)
    elif key == "f_translation":
        d = Design(key=key, title="(f) two-axis flexure translation stage, no balance", **base)
    elif key == "g_coarse_fine":
        d = Design(key=key, title="(g) fine +-0.5 mm counter-face nib + study W's pivot collar", **{**base, "travel": 0.5e-3},
                   balance=BL.CounterFace(driver="imu2", R_skid=7e-3 if not slim_ else 4.5e-3), balance_mass=1.2e-3, balance_z=0.076)
        d.collar = collar_numbers()
    elif key == "h_piezo":
        if slim_:
            ps = A.PiezoStage(plate="PL128", n_p=2, lam=1.33, m_tip=1.2e-3)
        else:
            ps = A.PiezoStage(plate="PL127", n_p=2, lam=1.33, m_tip=1.4e-3)
        d = Design(key=key, title="(h) piezo bender fine stage, no balance", **{**base, "family": "piezo", "travel": 0.4e-3},
                   piezo=ps)
    elif key == "h_piezo_c":
        ps = A.PiezoStage(plate="PL128" if slim_ else "PL127", n_p=2, lam=1.33, m_tip=1.3e-3)
        d = Design(key=key, title="(h') piezo fine stage + counter-face", **{**base, "family": "piezo", "travel": 0.45e-3},
                   piezo=ps, balance=BL.CounterFace(driver="imu2", R_skid=4.5e-3 if slim_ else 7e-3), balance_mass=1.2e-3, balance_z=0.076)
    else:
        raise KeyError(key)
    for k, v in kw.items():
        setattr(d, k, v)
    return d


CANDIDATES = ("a_long_arm", "b_bias", "b_bias_epm", "c_counterface", "c_counterface_cam", "c_counterface_keyed", "d_low_ink",
              "e_steep_tip", "f_translation", "g_coarse_fine", "h_piezo", "h_piezo_c")


def collar_numbers() -> Dict:
    """Study W's pivot collar (wholepen/designs.collar_design, read-only; W's defaults: pivot 60 mm, +-2 mm): its static
    moment and holding power (CALC, study W)."""
    try:
        from wholepen import designs as WD
        r = WD.collar_design(0.060, 2e-3)
        return {"z_p_mm": r["z_p_mm"], "travel_mm": r["travel_mm"], "static_moment_mNm_per_N": r["static_moment_mNm_per_N"],
                "hold_power_W_at_1N": r["hold_power_W"], "Km_out": r["Km_out_Nm_sqrtW"], "Km_label": r["Km_label"],
                "label": "CALC (study W, wholepen/designs.collar_design, read-only)"}
    except Exception as ex:
        return {"error": repr(ex)}


def all_defaults(quick: bool = False) -> Dict:
    out = {}
    for gname, grip in (("pen24", pen24()), ("slim14", slim(14e-3))):
        for key in CANDIDATES:
            d = make(key, grip)
            out[f"{gname}|{key}"] = evaluate(d, detail=not quick)
    return out
