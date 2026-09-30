r"""Evaluate one nib design under the matched assumptions (CALCULATION): magnetics, suspension and guide, the duties with
the thermal loop, battery hours per mode, skin, structural modes, electrical headroom and fit.

Thermal loop: the coil's copper resistance and the magnets' Br follow the coil temperature that study K's fin model
gives for the duty's copper loss at 35 deg (the worst sustained tilt), two passes; study K computed at 20 degC and the
pass at +90 K.  The magnets are taken at the coil's temperature (an upper bound on their warming).
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, Optional

import numpy as np

from . import duty as DU
from . import magnet as M
from . import pen as PN
from . import params as P
from . import suspension as SU
from .design import Design
from .params import val

CONVS = ("worst07", "centre10", "centre07")


def force_map(d: Design, fine: bool = False, n_ang: int = 8) -> Dict:
    quad = val(P.KM["quad_fine"]) if fine else val(P.KM["quad_fast"])
    n_img = 3 if fine else val(P.KM["n_img_fast"])
    pos = M.disk_positions(d.reach_mm * 1e-3, n_ang)
    fm = M.force_map(d.mag, d.coil, pos, quad=quad, n_img=n_img)
    return fm


def lead_factor(d: Design) -> float:
    rw = SU.wires(d.n_w, d.d_w_mm, d.L_w_mm, d.K_a, d.stop_mm, d.reach_mm, d.T0)["R_wire_ohm"]
    R_lead = 2 * rw / d.parallel
    return (d.R_coil + R_lead) / d.R_coil, R_lead


def context(d: Design, fm: Dict) -> DU.Ctx:
    fw = SU.wire_force_law(d.n_w, d.d_w_mm, d.L_w_mm, d.K_a, d.stop_mm + 0.3, d.T0)
    g = SU.ball_guide(d.guide_circle_mm, d.preload_N, d.ball_d_mm, d.n_balls, lever_mm=d.couple_lever_mm())
    drag = {float(k): v["drag_mN"] * 1e-3 for k, v in g["rows"].items() if k != "penup"}
    th_k = sorted(drag)

    def fd(theta_deg):
        return float(np.interp(theta_deg, th_k, [drag[t] for t in th_k]))
    lf, _ = lead_factor(d)
    return DU.Ctx(m=d.m_move_g() * 1e-3, fw=fw, fd=fd, K0=fm["K"][0].copy(), sv_min=float(fm["sv_min"].min()),
                  map_pos=fm["positions_m"], map_K=fm["K"], reach_m=d.reach_mm * 1e-3, lead_factor=lf,
                  weight_trim=d.weight_trim, fd_penup=g["rows"]["penup"]["drag_mN"] * 1e-3)


def _with_temp(d: Design, ctx: DU.Ctx, conv: str, kind: str, q: float, f: float, mode: str) -> Dict:
    """Two passes of the thermal loop; returns the duty at the consistent coil temperature and the skin (CALC)."""
    tf = 1.0
    for _ in range(2):
        c2 = replace(ctx, temp_factor=tf)
        p35 = DU.typical(c2, conv, kind, q, f, thetas=(35.0,))["mean"]
        sk = PN.skin(d, p35, mode)
        tf = PN.temp_factor(sk["coil_C"], sk["coil_C"])
    c2 = replace(ctx, temp_factor=tf)
    res = DU.typical(c2, conv, kind, q, f)
    p35 = DU.typical(c2, conv, kind, q, f, thetas=(35.0,))["mean"]
    sk = PN.skin(d, p35, mode)
    res.update({"P35_W": p35, "temp_factor": tf, "coil_C": sk["coil_C"], "skin": sk})
    return res


def screen_with_temp(d: Design, ctx: DU.Ctx, conv: str, passes: int = 3):
    """The matched screen at the coil temperature it would reach if sustained at 35 deg (fin model), three passes."""
    tf = 1.0
    sk = None
    for _ in range(passes):
        Pw = DU.screen(replace(ctx, temp_factor=tf), conv)["P_worst_W"]
        sk = PN.skin(d, Pw, "steady_2mm")
        tf = PN.temp_factor(sk["coil_C"], sk["coil_C"])
    return DU.screen(replace(ctx, temp_factor=tf), conv), tf, sk


def evaluate(d: Design, fine: bool = False, full: bool = True, fm: Optional[Dict] = None) -> Dict:
    fm = force_map(d, fine=fine, n_ang=16 if fine else 8) if fm is None else fm
    ctx = context(d, fm)
    wires = SU.wires(d.n_w, d.d_w_mm, d.L_w_mm, d.K_a, d.stop_mm, d.reach_mm, d.T0)
    guide = SU.ball_guide(d.guide_circle_mm, d.preload_N, d.ball_d_mm, d.n_balls, lever_mm=d.couple_lever_mm())
    lf, R_lead = lead_factor(d)
    out = {"design": d.summary(),
           "magnetics": {**M.summary(fm), "sv_min_workspace_x0.7": 0.7 * float(fm["sv_min"].min()),
                         "n_positions": len(fm["positions_m"]), "quadrature": "fine" if fine else "fast"},
           "wires": wires, "guide": {k: v for k, v in guide.items() if k != "rows"}, "guide_rows": guide["rows"],
           "leads": {"R_lead_ohm": R_lead, "factor": lf}}
    # duty A (typical writing) and the severe-tremor duty, three conventions, thermal loop
    dA, sev = {}, {}
    for conv in (CONVS if full else ("worst07",)):
        qa = val(P.DUTIES["A"])
        dA[conv] = _with_temp(d, ctx, conv, "circle", qa["q_rms_mm"], qa["f_Hz"], "steady_1mm")
        sev[conv] = _with_temp(d, ctx, conv, "severe", 0.0, 6.0, "steady_2mm")
    mo = DU.severe_motion(round(d.reach_mm, 4))
    out["dutyA"] = dA
    out["severe"] = sev
    out["severe_motion"] = {"q_rms_2d_mm": mo["q_rms_2d_mm"], "at_limit": mo["at_limit"],
                            "F_a_r2_tip_mm": DU.f_reach_interp("a_r2_tip_mm", d.reach_mm),
                            "F_oracle_tip_mm": DU.f_reach_interp("oracle_tip_mm", d.reach_mm),
                            "F_a_r2_at_limit": DU.f_reach_interp("a_r2_at_limit", d.reach_mm)}
    # the screen: matched loads, at the coil temperature it would reach if sustained (fin model)
    scr = {}
    for conv in (("worst07", "map07", "centre10") if full else ("worst07",)):
        r, tf_s, sk_s = screen_with_temp(d, ctx, conv)
        scr[conv] = r["P_worst_W"]
        scr[conv + "_at"] = r["at"]
        scr[conv + "_temp_factor"] = tf_s
        scr[conv + "_coil_C"] = sk_s["coil_C"]
        scr[conv + "_skin_max_C"] = sk_s["max_shell_C"]
    out["screen"] = scr
    # battery per mode (study K's structure), three ends
    if full:
        modes = {"steady_0mm": ("circle", 0.0), "steady_1mm": ("circle", 0.7071), "steady_2mm": ("circle", 1.4142),
                 "guide": ("circle", 0.30), "spelling_cue": ("circle", 0.0)}
        bat = {}
        nibw = {}
        for conv in CONVS:
            nibw[conv] = {}
            for mode, (kind, q) in modes.items():
                r = _with_temp(d, ctx, conv, kind, q, 8.0, mode if mode != "spelling_cue" else "spelling_cue")
                nibw[conv][mode] = {"mean_W": r["mean"], "P35_W": r["P35_W"], "skin_max_C": r["skin"]["max_shell_C"],
                                    "front_pad_C": r["skin"]["pads_C"][0], "coil_C": r["coil_C"]}
            nibw[conv]["severe"] = {"mean_W": sev[conv]["mean"], "P35_W": sev[conv]["P35_W"],
                                    "skin_max_C": sev[conv]["skin"]["max_shell_C"],
                                    "front_pad_C": sev[conv]["skin"]["pads_C"][0], "coil_C": sev[conv]["coil_C"]}
        bat["conservative"] = PN.battery({k: v["mean_W"] for k, v in nibw["worst07"].items()}, 1)
        bat["worst07_low_electronics"] = PN.battery({k: v["mean_W"] for k, v in nibw["worst07"].items()}, 0)
        bat["optimistic"] = PN.battery({k: v["mean_W"] for k, v in nibw["centre10"].items()}, 0)
        out["nib_by_mode"] = nibw
        out["battery"] = bat
    # electrical headroom at the peak force (the travel-under-load rule), the conservative force constant
    pk = DU.peak_force(ctx)
    Kmin_A = 0.7 * ctx.sv_min * math.sqrt(d.R_coil) / math.sqrt(sev["worst07"]["temp_factor"])
    I_pk = pk["total_N"] / Kmin_A
    a = val(P.ELEC["Cu_alpha_per_K"])
    T = sev["worst07"]["coil_C"]
    R_hot = (d.R_coil + R_lead) * (1 + a * (T - 20))
    v_pk = d.reach_mm * 1e-3 * 2 * math.pi * 12.0
    K_emf = float(np.linalg.svd(fm["K"][0], compute_uv=False)[0]) * math.sqrt(d.R_coil)   # upper bound, V s/m
    V_pk = I_pk * (R_hot + val(P.ELEC["R_drv_ohm"])) + K_emf * v_pk
    out["electrical"] = {"F_peak_N": pk["total_N"], "F_peak_parts_N": pk, "I_peak_A": I_pk, "V_peak_V": V_pk,
                         "R_hot_loop_ohm": R_hot, "back_emf_V": K_emf * v_pk, "ok": bool(V_pk <= val(P.ELEC["V_low_V"]))}
    # lead heating at the severe duty's rms current (per wire)
    I_rms = math.sqrt(sev["worst07"]["mean"] / (d.R_coil * lf) / 2)
    out["lead_heating"] = {"I_rms_coil_A": I_rms, "rise_K": SU.wire_joule_rise(I_rms / d.parallel, d.L_w_mm, d.d_w_mm)}
    # modes
    k_tilt = guide["tilt_stiffness_min_Nm_rad"] + wires["k_tilt_Nm_rad_wires"]
    hf = PN.head_fit(d.reach_mm, d.od_mm)
    out["modes"] = PN.modes(d, wires["k_small_N_m"], k_tilt, R_s_mm=hf["R_s_mm"], quick=not full)
    out["fit"] = PN.fit_checks(d)
    out["constraints"] = constraints(out)
    return out


def constraints(ev: Dict) -> Dict:
    """Margins (>= 0 passes) of the brief's constraints (CALC)."""
    fit = ev["fit"]
    sev = ev["severe"]["worst07"]
    c = {
        "goodman": ev["wires"]["goodman_worst_corner"] - val(P.MECH["goodman_min"]),
        "hertz_run": val(P.MECH["hertz_run_GPa"]) - ev["guide"]["hertz_run_GPa"],
        "hertz_static": val(P.MECH["hertz_static_GPa"]) - ev["guide"]["hertz_static_GPa"],
        "preload": ev["guide"]["preload_per_race_N"] - ev["guide"]["min_preload_all_balls_loaded_N"],
        "modes": ev["modes"]["servo_bw_max_worst_Hz"] - val(P.MECH["servo_bw_min_Hz"]),
        "coil_p99": fit["coil_clearance_p99_mm"] - val(P.MECH["clearance_p99_min_mm"]),
        "skin": val(P.THERMAL["skin_target_C"]) - sev["skin"]["max_shell_C"],
        "coil_inner": fit["coil_inner_edge_mm"] - 1.7,
        "magnets": (ev["design"]["bore_mm"] - 0.2) - fit["magnet_r_out_mm"],
        "wires_min": fit["wire_circle_mm"] - fit["wire_circle_min_mm"],
        "wires_max": fit["wire_circle_max_mm"] - fit["wire_circle_mm"] - (0.0 if fit["pad_gap_ok"] else 1.0),
        "head": fit["head"]["margin_mm"],
        "board": 1.0 if fit["board_ok"] else -1.0,
        "length": val(P.PEN["length_limit_mm"]) - fit["length_mm"],
        "voltage": val(P.ELEC["V_low_V"]) - ev["electrical"]["V_peak_V"],
        "lead_heat": val(P.ELEC["wire_rise_limit_K"]) - ev["lead_heating"]["rise_K"],
        "magnet_T": val(P.KM["grades"])[ev["design"]["grade"]]["T_max_C"] - sev["coil_C"],
    }
    c["feasible"] = all(v >= -1e-9 for v in c.values())
    return c
