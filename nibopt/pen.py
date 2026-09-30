r"""The pen around the nib: study K's fin model of the skin, study K's battery budget structure, the loaded structural
modes (study B's beam model), the counter-face head and front-end fit, and the fit checks (CALCULATION).

Skin (study K, revk/budgets.heat): the 1 mm PEEK shell is a fin; each source warms the shell over it by
P R_fin(L) and the rise decays as exp(-d / lambda) beyond its ends,
    R_fin(L) = 1 / (h pi D L + 2 sqrt(h pi D k A_c)),  lambda = sqrt(k A_c / (h pi D)),  A_c = pi/4 (D^2 - (D - 2t)^2);
generalised here to the body diameter D (study K's code fixes D = 24 mm).  Sources at study K's high end: the coils
(the actuator's length), the board, the page sensor, the head's motors; the coil adds P R_int (15 K/W).
Battery (study K, revk/budgets.modes): 2.22 Wh usable; electronics, page sensor, face sensor, positioners and the mode's
extras are study K's numbers (results/revK/budgets.json); the nib's copper loss is replaced by the matched model.
Modes (study K, revk/nib.modes_grid, with bnib/flexure.loaded_modes read-only): refill as a planar beam in two guide
stations, the carrier on the wires' lateral stiffness and the guide's tilt stiffness, the ball free and stuck
(pre-sliding 5 / 10 / 20 um), refill EI 0.09-0.385 N m^2, 35 / 50 / 75 deg; servo bandwidth <= lowest / 2.5.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Dict, List

import numpy as np

from . import BUILD, REPO_ROOT
from . import params as P
from .params import val

import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ------------------------------------------------------------------------------------------------ study K's numbers
@lru_cache(maxsize=1)
def k_budget_rows() -> Dict:
    return P.load_json("results/revK/budgets.json")["budgets"]["power"]["rows"]


@lru_cache(maxsize=1)
def k_layout() -> Dict:
    lay = P.load_json("results/revK/layout.json")
    return {c["id"]: c for c in lay["components"]}


# ------------------------------------------------------------------------------------------------ fin model
def fin_R(L_mm: float, D_mm: float) -> float:
    h = val(P.THERMAL["h_W_m2K"])
    k = val(P.THERMAL["k_shell_W_mK"])
    t = val(P.THERMAL["wall_mm"])
    Pp = math.pi * D_mm * 1e-3
    Ac = math.pi / 4 * ((D_mm * 1e-3) ** 2 - ((D_mm - 2 * t) * 1e-3) ** 2)
    return 1.0 / (h * Pp * L_mm * 1e-3 + 2.0 * math.sqrt(h * Pp * k * Ac))


def fin_lambda_mm(D_mm: float) -> float:
    h = val(P.THERMAL["h_W_m2K"])
    k = val(P.THERMAL["k_shell_W_mK"])
    t = val(P.THERMAL["wall_mm"])
    Pp = math.pi * D_mm * 1e-3
    Ac = math.pi / 4 * ((D_mm * 1e-3) ** 2 - ((D_mm - 2 * t) * 1e-3) ** 2)
    return math.sqrt(k * Ac / (h * Pp)) * 1e3


def surface_rise(z_mm, sources: List[Dict], D_mm: float):
    """Shell-surface rise (K) at z (scalar or array) from the sources (study K's revk/budgets.surface_rise, with D)."""
    lam = fin_lambda_mm(D_mm)
    z = np.asarray(z_mm, float)
    dT = np.zeros_like(z)
    for s in sources:
        R = fin_R(s["z1"] - s["z0"], D_mm)
        d = np.where((z >= s["z0"]) & (z <= s["z1"]), 0.0, np.minimum(np.abs(z - s["z0"]), np.abs(z - s["z1"])))
        dT = dT + s["P"] * R * np.exp(-d / lam)
    return float(dT) if dT.ndim == 0 else dT


def heat_sources(design, P_nib_35_W: float, mode: str = "steady_1mm", end: int = 1) -> List[Dict]:
    """Study K's four sources at the high end (end = 1) with the design's actuator and shifted rear parts."""
    c = k_layout()
    rows = k_budget_rows()
    r = rows[mode] if mode in rows else rows["steady_1mm"]
    z0 = val(P.PEN["actuator_z0_mm"])
    z1 = z0 + design.stack_mm()
    shift = design.rear_shift_mm()
    shift_head = design.holder_extension_mm() + (22.8 * 0.4 if design.board_narrow else 0.0)
    board_len = 22.8 * (1.4 if (design.board_narrow and design.race_topology != "pads") else 1.0)
    return [{"name": "coils", "z0": z0, "z1": z1, "P": P_nib_35_W},
            ({"name": "board", "z0": c["main_board"]["z0"] + shift, "z1": c["main_board"]["z0"] + shift + board_len,
              "P": r["electronics_W"][end]} if design.race_topology != "pads" else
             {"name": "board", "z0": c["head_roll_motor"]["z1"] + shift_head + 0.5,
              "z1": c["head_roll_motor"]["z1"] + shift_head + 0.5 + board_len, "P": r["electronics_W"][end]}),
            {"name": "page sensor", "z0": c["page_sensor"]["z0"], "z1": c["page_sensor"]["z1"], "P": r["page_W"][end]},
            {"name": "head motors and face sensor", "z0": c["head_tilt_motor"]["z0"] + shift_head,
             "z1": c["head_roll_motor"]["z1"] + shift_head,
             "P": r["positioners_W"][end] + r["face_sensor_W"][end] + r["mode_extra_W"][end]}]


def skin(design, P_nib_35_W: float, mode: str = "steady_1mm") -> Dict:
    D = design.od_mm
    src = heat_sources(design, P_nib_35_W, mode)
    room = val(P.THERMAL["room_C"])
    pads = (26.0, 32.0, 38.0)                      # study K's hand model (revk/params ENVELOPE finger_pads_z_mm)
    L = design.length_mm()
    zs = np.arange(5.0, L, 0.5)
    shell = room + surface_rise(zs, src, D)
    coil_mid = 0.5 * (src[0]["z0"] + src[0]["z1"])
    T_coil = room + surface_rise(coil_mid, src, D) + P_nib_35_W * val(P.THERMAL["R_int_K_W"])
    return {"pads_C": [room + surface_rise(z, src, D) for z in pads], "web_C": room + surface_rise(92.0, src, D),
            "max_shell_C": float(max(shell)), "coil_C": T_coil, "sources_W": {s["name"]: s["P"] for s in src},
            "D_mm": D, "fin_lambda_mm": fin_lambda_mm(D),
            "label": "CALCULATION (study K's fin model generalised to the body diameter; h ASSUMPTION, k MFR AMF-24)"}


def temp_factor(T_cu: float, T_mag: float) -> float:
    """Copper resistance and reversible Br loss relative to 20 degC; temperatures clamped at 200 degC (far beyond
    every limit: such a design fails the skin, coil and magnet constraints anyway, and the linear Br law would
    otherwise turn over)."""
    a = val(P.ELEC["Cu_alpha_per_K"])
    b = val(P.KM["Br_tempco_per_K"])
    T_cu = min(max(T_cu, -20.0), 200.0)
    T_mag = min(max(T_mag, -20.0), 200.0)
    return (1 + a * (T_cu - 20.0)) / (1 + b * (T_mag - 20.0)) ** 2


# ------------------------------------------------------------------------------------------------ battery (study K)
MODES_K = ("steady_0mm", "steady_1mm", "steady_2mm", "guide", "spelling_cue")


def battery(nib_W: Dict[str, float], end: int) -> Dict:
    """Hours on 2.22 Wh per mode with study K's non-nib powers at end 0 (low) or 1 (high) (CALC)."""
    rows = k_budget_rows()
    out = {}
    for mode, Pn in nib_W.items():
        r = rows[mode] if mode in rows else rows["steady_1mm"]
        tot = r["electronics_W"][end] + r["page_W"][end] + r["face_sensor_W"][end] + r["positioners_W"][end] + \
            r["mode_extra_W"][end] + Pn
        out[mode] = {"nib_W": Pn, "total_W": tot, "hours": 2.22 / tot}
    return out


# ------------------------------------------------------------------------------------------------ loaded modes
def p_ahead(theta_deg: float, R_s: float, r_b: float = 0.35) -> float:
    th = math.radians(theta_deg)
    return (R_s * math.cos(th) - r_b) / math.sin(th)


def modes(design, k_lat: float, k_tilt: float, R_s_mm: float = 6.0, quick: bool = False) -> Dict:
    """Study K's loaded-mode grid for this carrier (bnib/flexure.loaded_modes, read-only) (CALC)."""
    from bnib import flexure as FX
    mp = design.moving_parts_g()
    m_car = sum(v for k, v in mp.items() if k not in ("refill", "refill_holder")) * 1e-3
    zf = design.flange_z()
    zb = (10.0, 0.5 * (zf[0] + zf[1]))              # study K: front guide station + 1 mm, the flange's middle
    zc0 = val(P.PEN["actuator_z0_mm"]) + design.plate_t_mm() + design.mag.t_m * 1e3 + design.mag.c0 * 1e3
    zpos = {"carrier_tube": 0.5 * (9.0 + zf[1] + 0.5), "guide_stations": 0.5 * (10.0 + zf[0]),
            "coils": zc0 + design.mag.t_cu * 0.5e3, "flange": 0.5 * (zf[0] + zf[1]), "position_magnet": zf[1] + 0.5,
            "wires_third": zf[1] + design.L_w_mm / 3, "flange_inserts": 0.5 * (zf[0] + zf[1]),
            "holder_extension": 67.8 + design.holder_extension_mm() / 2}
    z_car = sum(mp[k] * zpos[k] for k in zpos) / sum(mp[k] for k in zpos)
    J_car = 3e-8 + 0.65e-3 * 0.028 ** 2 / 12.0
    F_n = val(P.LOADS["F_n_N"])
    mu_s = 0.15 * 1.3
    mpl = (0.84e-3 + 0.08e-3) / 0.0695
    rows = []
    for EI in ((0.09, 0.385) if not quick else (0.09,)):
        beam = FX.RefillBeam(L=0.0695, EI=EI, m_per_len=mpl, n_el=20)
        for th in ((35.0, 50.0, 75.0) if not quick else (35.0,)):
            ds = (p_ahead(th, R_s_mm) - p_ahead(50.0, R_s_mm)) * 1e-3
            args = (beam, m_car, J_car, z_car * 1e-3 + ds, zb[0] * 1e-3 + ds, zb[1] * 1e-3 + ds, k_lat, k_tilt, 0.0, F_n)
            free = FX.loaded_modes(*args, 0.0)["f_Hz"]
            for xp in ((5.0, 10.0, 20.0) if not quick else (20.0,)):
                stuck = FX.loaded_modes(*args, mu_s * F_n / (xp * 1e-6))["f_Hz"]
                rows.append({"EI": EI, "theta": th, "x_pre_um": xp, "free_1": free[1], "stuck_0": stuck[0],
                             "bw_Hz": min(free[1], stuck[0]) / val(P.MECH["mode_ratio"])})
    worst = min(rows, key=lambda r: r["bw_Hz"])
    nom = [r for r in rows if r["EI"] == 0.385 and r["x_pre_um"] == 10.0] or rows
    return {"servo_bw_max_worst_Hz": worst["bw_Hz"], "lowest_stuck_worst_Hz": min(r["stuck_0"] for r in rows),
            "first_free_nominal_Hz": min(r["free_1"] for r in nom), "lowest_stuck_nominal_Hz": min(r["stuck_0"] for r in nom),
            "m_carrier_g": m_car * 1e3, "k_lat_N_m": k_lat, "k_tilt_Nm_rad": k_tilt, "n_cases": len(rows),
            "passes": worst["bw_Hz"] >= val(P.MECH["servo_bw_min_Hz"]),
            "label": "CALCULATION (bnib/flexure.loaded_modes read-only; pre-sliding and refill EI ASSUMPTION)"}


# ------------------------------------------------------------------------------------------------ head and front end
@lru_cache(maxsize=1)
def head_table() -> Dict:
    """For usable radii 1.0-2.0 mm: the smallest skid ring that passes study K's front-end rules and the counter-face
    head's smallest swept radius among layouts that keep the follower's spare travel (revk/frontend.front_close,
    revk/counterface.sweep, read-only; cached in nibopt/build/) (CALC)."""
    cache = BUILD / "head_table.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except Exception:
            pass
    from revk import counterface, frontend
    rows = []
    for r in (1.0, 1.0587, 1.25, 1.5, 1.75, 2.0):
        stop = r + 0.2
        fr = frontend.front_close(quick=True, travel=r, stop=stop)
        hs = counterface.sweep(fr["R_s_mm"], quick=False, stop_mm=stop)
        spare = [x for x in hs["rows"] if x["keeps_spare_travel"]]
        smin = min(x["swept_r_max_mm"] for x in spare) if spare else float("inf")
        rows.append({"reach_mm": r, "stop_mm": stop, "R_s_mm": fr["R_s_mm"], "head_swept_min_mm": smin,
                     "od_min_head_mm": 2 * (smin + 0.3 + val(P.THERMAL["wall_mm"])), "n_layouts": len(hs["rows"]),
                     "n_spare": len(spare)})
    out = {"rows": rows, "label": "CALCULATION (revk/frontend, revk/counterface read-only; head bore rule 0.3 mm)"}
    BUILD.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=1))
    return out


def head_fit(reach_mm: float, od_mm: float) -> Dict:
    t = head_table()["rows"]
    rs = [r["reach_mm"] for r in t]
    od_min = float(np.interp(reach_mm, rs, [r["od_min_head_mm"] for r in t]))
    R_s = float(np.interp(reach_mm, rs, [r["R_s_mm"] for r in t]))
    return {"od_min_head_mm": od_min, "margin_mm": (od_mm - od_min) / 2, "R_s_mm": R_s, "fits": od_mm >= od_min - 1e-9}


# ------------------------------------------------------------------------------------------------ fit checks
def fit_checks(design, sv_ok: bool = True) -> Dict:
    stop = design.stop_mm
    bore = design.bore_mm
    cr = design.coil.outer_radius * 1e3
    clr = bore - stop - cr
    p99 = clr - val(P.MECH["coil_p99_loss_mm"])
    mag_r = design.mag.r_out * 1e3
    rr = val(P.MECH["refill_r_mm"])
    w_min = rr + stop + 0.3 + 0.3
    Rf = design.flange_radius_mm
    race_w = stop + design.ball_d_mm + 0.4
    race_in = design.guide_circle_mm - race_w / 2
    if design.race_topology == "ring":
        w_max = race_in - stop - design.d_w_mm / 2 - 0.3
        gap_ok = True
    else:
        w_max = min(design.flange_radius_mm - 0.1, bore - stop - design.d_w_mm / 2 - 0.3)
        # the wires swing between the rear race's pads: the gap between pad discs (radius stop/2 + ball/2 + 0.2) on the
        # ball circle must pass a wire's +-stop swing with 0.3 mm each side
        pad_r = stop / 2 + design.ball_d_mm / 2 + 0.2
        gap = 2 * design.guide_circle_mm * math.sin(math.pi / design.n_balls) - 2 * pad_r
        gap_ok = gap >= 2 * stop + design.d_w_mm + 0.6
    board_half = 5.0 if design.board_narrow else 7.0
    board_x = design.wire_circle_mm + stop + 1.6
    hf = head_fit(design.reach_mm, design.od_mm)
    checks = {
        "coil_clearance_stop_mm": clr, "coil_clearance_p99_mm": p99, "coil_p99_ok": p99 >= val(P.MECH["clearance_p99_min_mm"]),
        "coil_inner_edge_mm": design.coil.inner_edge * 1e3, "coil_inner_ok": design.coil.inner_edge * 1e3 >= 1.7 - 1e-9,
        "magnet_r_out_mm": mag_r, "magnets_ok": mag_r <= bore - 0.2 + 1e-9,
        "flange_r_mm": Rf, "flange_ok": Rf <= bore - stop - 0.3 + 1e-6,
        "ball_circle_r_mm": design.guide_circle_mm, "ball_on_flange_ok": design.guide_circle_mm + design.ball_d_mm / 2 +
        stop / 2 <= Rf + 1e-6,
        "wire_circle_mm": design.wire_circle_mm, "wire_circle_min_mm": w_min, "wire_circle_max_mm": w_max,
        "wires_ok": (w_min - 1e-6 <= design.wire_circle_mm <= w_max + 1e-6) and gap_ok, "rear_race": design.race_topology,
        "pad_gap_ok": gap_ok,
        "board_ok": design.race_topology == "pads" or bore ** 2 >= board_half ** 2 + board_x ** 2,
        "board": ("14 mm, moved behind the head" if design.race_topology == "pads" else
                  "10 mm (repackaged)" if design.board_narrow else "14 mm (study K)"),
        "head": hf, "head_ok": hf["fits"], "length_mm": design.length_mm(),
        "length_ok": design.length_mm() <= val(P.PEN["length_limit_mm"]),
    }
    checks["all_ok"] = all(v for k, v in checks.items() if k.endswith("_ok"))
    return checks
