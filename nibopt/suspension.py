r"""The carrier's suspension and guide: wires as coil leads on a preloaded ball thrust guide, a nested parallel-blade
flexure stage, and the screening of flexure alternatives against the counter-face couple (CALCULATION).

Straight C17200 wire leads (study K / the pass): the pass's self-consistent beam-column with an axially compliant
anchor (revk/feasibility.wire_anchor, read-only) gives the nonlinear lateral force F_w(q), the tension it adds and a
conservative Goodman factor; the worst tolerance corner is the pass's (revk/improve.wire_design): diameter +2 %,
length -0.05 mm, modulus +4 %, anchor +20 %, 5 mN assembly tension, Kt 2.5.

Ball thrust guide (study K): 2 x n Si3N4 balls between the carrier flange and two lapped races; the pass's opposed-race
Hertz model (revk/feasibility.thrust_guide, read-only) solves the ball loads under an internal preload per race and the
counter-face couple M = F_n L cos(theta); drag = mu_roll x total normal load (Coulomb, opposing the carrier's motion).
The preload per race is a design variable here: the pass kept study K's 4 N; the minimum that keeps every ball loaded
under the 35 deg couple is about 1.2 x 2 M / (rho n / 2) x n / 2 ... solved numerically.

Nested parallel-blade stage: two one-axis stages in series, each two blades (thickness t, width b, free length L),
fixed-guided; the couple is carried as axial force in the blades (M / spacing), which must stay below half their
fixed-fixed buckling load; lateral stiffness 24 E I / L^3 per stage; an intermediate frame moves with one axis.

Screening of other flexure-guided carriers (screen_topologies): necked struts (rigid middle, short hinges), a planar
high-aspect-ratio flexure stage, pre-tensioned wires; each against the couple, the lateral force at the stop and
Goodman.  Nothing here is a measurement; material data MANUFACTURER, geometry PROPOSED DESIGN, tolerances ASSUMPTION.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Dict

import numpy as np

from . import params as P
from .params import val

import sys
from . import REPO_ROOT
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from revk.feasibility import thrust_guide as _thrust_guide, wire_anchor as _wire_anchor  # noqa: E402 (read-only)

C17 = val(P.MECH["C17200"])
S_F = C17["S_f"] * val(P.MECH["fatigue_knockdown"])


def couple_Nm(theta_deg: float, lever_mm: float = None) -> float:
    """Counter-face couple on the carrier: M = F_n L cos(theta) (study K nib.couple)."""
    L = val(P.LOADS["couple_lever_mm"]) if lever_mm is None else lever_mm
    return val(P.LOADS["F_n_N"]) * L * 1e-3 * math.cos(math.radians(theta_deg))


# ------------------------------------------------------------------------------------------------ wires
@lru_cache(maxsize=4096)
def _wire_table(n_w: int, d_mm: float, L_mm: float, K_a: float, T0: float, stop_mm: float, npts: int = 13):
    q = np.linspace(0.0, stop_mm * 1e-3, npts)
    F = np.array([_wire_anchor(float(x), length=L_mm * 1e-3, diameter=d_mm * 1e-3, n_wires=n_w, anchor_stiffness=K_a,
                               assembly_tension=T0)["lateral_force_N"] for x in q])
    return q, F


def wire_force_law(n_w: int, d_mm: float, L_mm: float, K_a: float, stop_mm: float, T0: float = 0.005):
    """Callable |q| -> radial restoring force (N) of the wire set, the pass's nonlinear model (CALC)."""
    q, F = _wire_table(int(n_w), round(float(d_mm), 5), round(float(L_mm), 4), round(float(K_a), 3), round(float(T0), 5),
                       round(float(stop_mm), 4))

    def f(x):
        x = np.abs(np.asarray(x, float))
        return np.interp(np.minimum(x, q[-1]), q, F) + np.where(x > q[-1], (x - q[-1]) * (F[-1] - F[-2]) / (q[-1] - q[-2]), 0)
    return f


def wires(n_w: int, d_mm: float, L_mm: float, K_a: float, stop_mm: float, travel_mm: float, T0: float = 0.005) -> Dict:
    """Wire leads: force at the usable radius and the stop, small-motion stiffness, worst-corner Goodman, buckling,
    resistance (CALC)."""
    tc = val(P.MECH["tol_corner"])
    E = C17["E"]
    stop = stop_mm * 1e-3
    nom = _wire_anchor(stop, length=L_mm * 1e-3, diameter=d_mm * 1e-3, n_wires=n_w, anchor_stiffness=K_a,
                       assembly_tension=T0, kt=1.8)
    worst = _wire_anchor(stop, length=L_mm * 1e-3 + tc["L_mm"] * 1e-3, diameter=d_mm * 1e-3 * tc["d"], young=E * tc["E"],
                         n_wires=n_w, anchor_stiffness=K_a * tc["anchor"], assembly_tension=tc["assembly_N"],
                         kt=val(P.MECH["Kt_worst"]))
    at_u = _wire_anchor(travel_mm * 1e-3, length=L_mm * 1e-3, diameter=d_mm * 1e-3, n_wires=n_w, anchor_stiffness=K_a,
                        assembly_tension=T0)
    I = math.pi * (d_mm * 1e-3) ** 4 / 64
    A = math.pi * (d_mm * 1e-3) ** 2 / 4
    k0 = n_w * 12 * E * I / (L_mm * 1e-3) ** 3
    rho = val(P.ELEC["rho_C17200_ohm_m"])
    R_w = rho * L_mm * 1e-3 / A
    return {"n_w": n_w, "d_mm": d_mm, "L_mm": L_mm, "anchor_N_m": K_a, "assembly_N": T0,
            "F_usable_mN": at_u["lateral_force_N"] * 1e3, "F_stop_mN": nom["lateral_force_N"] * 1e3,
            "F_stop_linear_mN": nom["linear_lateral_force_N"] * 1e3, "tension_stop_N": nom["tension_total_N"],
            "k_small_N_m": k0, "goodman_worst_corner": worst["goodman_sf_conservative"],
            "goodman_nominal_Kt1.8": nom["goodman_sf_conservative"], "bend_stress_worst_MPa": worst["bend_stress_MPa"],
            "P_buckle_each_ff_N": 4 * math.pi ** 2 * E * I / (L_mm * 1e-3) ** 2,
            "R_wire_ohm": R_w, "k_axial_N_m": n_w * E * A / (L_mm * 1e-3),
            "k_tilt_Nm_rad_wires": 0.5 * n_w * E * A / (L_mm * 1e-3) * (4e-3) ** 2,
            "mass_g": n_w * C17["rho"] * A * L_mm * 1e-3 * 1e3,
            "label": "CALCULATION (revk/feasibility.wire_anchor, read-only; the pass's worst corner; C17200 AMF-19)"}


def wire_joule_rise(I_rms_wire: float, L_mm: float, d_mm: float) -> float:
    """Mid-wire rise above equal-temperature clamps, no convection, with resistivity feedback (the pass's screen)."""
    rho = val(P.ELEC["rho_C17200_ohm_m"])
    k = val(P.ELEC["k_C17200_W_mK"])
    A = math.pi * (d_mm * 1e-3) ** 2 / 4
    dT0 = I_rms_wire ** 2 * rho * (L_mm * 1e-3) ** 2 / (8 * k * A * A)
    den = 1 - val(P.ELEC["Cu_alpha_per_K"]) * dT0
    return dT0 / den if den > 0 else float("inf")


# ------------------------------------------------------------------------------------------------ ball guide
def unloading_preload(circle_r_mm: float, n_balls: int = 6, ball_d_mm: float = 0.8, theta_deg: float = 35.0,
                      lever_mm: float = None) -> float:
    """Smallest internal preload per race (N) at which the opposed-race Hertz solver (revk/feasibility.thrust_guide)
    still keeps every ball loaded under the counter-face couple at theta (bisection, 0.1 % in the load)."""
    M = couple_Nm(theta_deg, lever_mm)
    if M <= 0:
        return 0.0

    def loaded(P0: float) -> bool:
        g = _guide(round(M, 12), round(P0, 6), n_balls, round(ball_d_mm * 0.5e-3, 9), round(circle_r_mm * 1e-3, 9),
                   val(P.MECH["mu_roll"]))
        return g["unloaded_contacts"] == 0
    lo, hi = 1e-3, 1.0
    while not loaded(hi):
        lo, hi = hi, hi * 2
        if hi > 1e3:
            return float("inf")
    while hi - lo > 1e-3 * hi:
        mid = 0.5 * (lo + hi)
        if loaded(mid):
            hi = mid
        else:
            lo = mid
    return hi


def min_preload(circle_r_mm: float, n_balls: int = 6, theta_deg: float = 35.0, lever_mm: float = None,
                ball_d_mm: float = 0.8) -> float:
    """The preload floor (N per race): the solver's unloading preload at 35 deg x the margin (1.2: it also covers the
    ink force's +20 % tolerance, REQ-BNIB-008), so no ball unloads in writing (PROPOSED DESIGN rule, CALC)."""
    return unloading_preload(circle_r_mm, n_balls, ball_d_mm, theta_deg, lever_mm) * val(P.MECH["preload_min_margin"])


@lru_cache(maxsize=4096)
def _guide(M: float, preload: float, n: int, ball_r: float, circle_r: float, mu: float):
    return _thrust_guide([M, 0.0], preload_per_race=preload, balls_per_race=n, ball_radius=ball_r, circle_radius=circle_r,
                         rolling_coefficient=mu)


def ball_guide(circle_r_mm: float, preload_N: float, ball_d_mm: float = 0.8, n_balls: int = 6,
               mu_roll: float = None, lever_mm: float = None) -> Dict:
    """Guide loads at 35 / 50 / 60 / 75 deg and with no couple (pen up), Hertz at the sustained load and at the race
    springs' release (static), drag, tilt stiffness (CALC; revk/feasibility.thrust_guide read-only)."""
    mu = val(P.MECH["mu_roll"]) if mu_roll is None else mu_roll
    rows = {}
    for th in (35.0, 50.0, 60.0, 75.0, None):
        M = 0.0 if th is None else couple_Nm(th, lever_mm)
        g = _guide(round(M, 12), round(preload_N, 6), n_balls, round(ball_d_mm * 0.5e-3, 9), round(circle_r_mm * 1e-3, 9),
                   mu)
        rows["penup" if th is None else f"{th:g}"] = {"couple_mNm": M * 1e3, "total_normal_N": g["total_normal_load_N"],
                                                     "drag_mN": g["rolling_force_N"] * 1e3, "max_hertz_GPa": g["max_hertz_GPa"],
                                                     "min_tilt_stiffness_Nm_rad": g["min_tilt_stiffness_Nm_rad"],
                                                     "tilt_urad": float(np.hypot(*g["tilt_rad"])) * 1e6,
                                                     "unloaded_contacts": g["unloaded_contacts"]}
    # static: a drop lifts a race off its spring seat; the balls then carry at most the spring's release load shared by
    # half the balls (study K's convention: preload / 3 for six balls)
    R = ball_d_mm * 0.5e-3
    Estar = 1.0 / ((1 - 0.27 ** 2) / 310e9 + (1 - 0.3 ** 2) / 200e9)
    F_rel = preload_N / max(n_balls / 2, 1)
    a = (3 * F_rel * R / (4 * Estar)) ** (1 / 3)
    p_rel = 3 * F_rel / (2 * math.pi * a * a) / 1e9
    return {"circle_r_mm": circle_r_mm, "preload_per_race_N": preload_N, "ball_d_mm": ball_d_mm, "n_balls": n_balls,
            "mu_roll": mu, "rows": rows, "drag_35_mN": rows["35"]["drag_mN"],
            "drag_mean_mN": float(np.mean([rows[k]["drag_mN"] for k in ("35", "50", "60", "75")])),
            "hertz_run_GPa": max(rows[k]["max_hertz_GPa"] for k in ("35", "50", "60", "75", "penup")),
            "hertz_static_GPa": p_rel, "tilt_stiffness_min_Nm_rad": min(r["min_tilt_stiffness_Nm_rad"] for r in rows.values()),
            "unloading_preload_N": unloading_preload(circle_r_mm, n_balls, ball_d_mm, lever_mm=lever_mm),
            "min_preload_all_balls_loaded_N": min_preload(circle_r_mm, n_balls, lever_mm=lever_mm, ball_d_mm=ball_d_mm),
            "lever_mm": lever_mm,
            "mass_balls_g": 2 * n_balls * 3200 * 4 / 3 * math.pi * R ** 3 * 1e3,
            "label": "CALCULATION (revk/feasibility.thrust_guide: opposed Hertz races, rigid supports; mu_roll ASSUMPTION)"}


# ------------------------------------------------------------------------------------------------ nested blade stage
def blade_stage(t_um: float, b_mm: float, L_mm: float, spacing_mm: float, stop_mm: float, E: float = None,
                Kt: float = 1.3) -> Dict:
    """Two nested one-axis parallel-blade stages (two blades each, fixed-guided, C17200 unless E given) (CALC)."""
    E = C17["E"] if E is None else E
    t, b, L = t_um * 1e-6, b_mm * 1e-3, L_mm * 1e-3
    I = b * t ** 3 / 12
    k_stage = 2 * 12 * E * I / L ** 3
    P_ff = 4 * math.pi ** 2 * E * I / L ** 2
    F_couple = couple_Nm(35.0) / (spacing_mm * 1e-3)
    sig = 3 * E * t * stop_mm * 1e-3 / L ** 2 * Kt
    gm = 1.0 / (sig / S_F + F_couple / (b * t) / C17["S_u"])
    return {"k_per_axis_N_m": k_stage, "F_stop_mN": k_stage * stop_mm * 1e-3 * 1e3, "blade_buckling_ff_N": P_ff,
            "couple_axial_N": F_couple, "buckling_margin": P_ff / F_couple, "goodman": gm,
            "length_mm": 2 * L_mm + 3.0, "label": "CALCULATION (fixed-guided blades; C17200 AMF-19; Kt 1.3 etched fillet ASSUMPTION)"}


# ------------------------------------------------------------------------------------------------ strut FE (screen)
def strut_fe(L: float, l_h: float, d_h: float, P_ax: float = 0.0, d_mid: float = 0.5e-3, E: float = None, n_h: int = 8,
             n_m: int = 8) -> Dict:
    """A necked strut: hinge (d_h, l_h) - stiff middle (d_mid) - hinge, fixed at the anchor, fixed-guided at the carrier,
    axial force P_ax (tension +).  Lateral stiffness, hinge bending stress per metre of lateral travel (CALC)."""
    E = C17["E"] if E is None else E
    segs = [(l_h, d_h, n_h), (L - 2 * l_h, d_mid, n_m), (l_h, d_h, n_h)]
    nodes = [0.0]
    props = []
    for (ls, ds, ns) in segs:
        for _ in range(ns):
            nodes.append(nodes[-1] + ls / ns)
            props.append((ls / ns, math.pi * ds ** 4 / 64))
    nd = 2 * len(nodes)
    K = np.zeros((nd, nd))
    for e, (le, I) in enumerate(props):
        EI = E * I
        ke = EI / le ** 3 * np.array([[12, 6 * le, -12, 6 * le], [6 * le, 4 * le ** 2, -6 * le, 2 * le ** 2],
                                      [-12, -6 * le, 12, -6 * le], [6 * le, 2 * le ** 2, -6 * le, 4 * le ** 2]])
        kg = P_ax / (30 * le) * np.array([[36, 3 * le, -36, 3 * le], [3 * le, 4 * le ** 2, -3 * le, -le ** 2],
                                          [-36, -3 * le, 36, -3 * le], [3 * le, -le ** 2, -3 * le, 4 * le ** 2]])
        i = 2 * e
        K[i:i + 4, i:i + 4] += ke + kg
    fixed = [0, 1, nd - 2, nd - 1]
    free = [i for i in range(nd) if i not in fixed]
    u = np.zeros(nd)
    u[nd - 2] = 1.0                               # unit lateral displacement at the carrier, rotation held
    uf = np.linalg.solve(K[np.ix_(free, free)], -K[np.ix_(free, [nd - 2])] @ np.array([1.0]))
    u[free] = uf
    f = K @ u
    k_lat = f[nd - 2]
    # element end moments -> max bending stress in the hinges per metre of travel
    smax = 0.0
    for e, (le, I) in enumerate(props):
        i = 2 * e
        EI = E * I
        ke = EI / le ** 3 * np.array([[12, 6 * le, -12, 6 * le], [6 * le, 4 * le ** 2, -6 * le, 2 * le ** 2],
                                      [-12, -6 * le, 12, -6 * le], [6 * le, 2 * le ** 2, -6 * le, 4 * le ** 2]])
        fe = ke @ u[i:i + 4]
        d = (64 * I / math.pi) ** 0.25
        smax = max(smax, abs(fe[1]) * d / 2 / I, abs(fe[3]) * d / 2 / I)
    return {"k_lat_N_m": float(k_lat), "stress_per_m_Pa": float(smax), "P_cr_hinge_sway_N": math.pi ** 2 * E *
            math.pi * d_h ** 4 / 64 / l_h ** 2}


def screen_topologies(stop_mm: float = 1.7) -> Dict:
    """Why the carrier keeps a rolling guide: each flexure alternative against the 35 deg couple (CALC)."""
    M = couple_Nm(35.0)
    rows = []
    # (1) study K's four 0.10 mm C17200 wires alone (no guide): compression vs fixed-fixed buckling
    E = C17["E"]
    d, L = 0.10e-3, 26.8e-3
    I = math.pi * d ** 4 / 64
    Fw = M / (2 * math.sqrt(2) * 5.5e-3)
    rows.append({"topology": "wires alone (study B / K's four 0.10 mm C17200 wires on a 5.5 mm circle)",
                 "carries_couple": False, "reason": f"{Fw:.2f} N of compression per wire against {4 * math.pi ** 2 * E * I / L ** 2 * 1e3:.1f} mN "
                 "fixed-fixed buckling (study K N14)", "F_stop_mN": None, "drag_mN": 0.0})
    # (2) pre-tensioned wires: tension >= the couple's axial force; string stiffness n T / L
    for rho_mm, L_mm in ((5.5, 34.0), (9.0, 40.0)):
        T = M / (2 * rho_mm * 1e-3) * 1.2
        k = 4 * 1.2 * T / (L_mm * 1e-3) + 4 * 12 * E * I / (L_mm * 1e-3) ** 3
        rows.append({"topology": f"four wires pre-tensioned to {T:.2f} N each (circle {rho_mm} mm, {L_mm} mm long)",
                     "carries_couple": True, "k_N_m": k, "F_stop_mN": k * stop_mm, "drag_mN": 0.0,
                     "reason": "tension stiffening n T / L: the spring force at the stop exceeds the moving mass's weight"})
    # (3) necked struts: the hinge must be short to carry ~1 N of compression, and a short hinge bends hard
    best = None
    for n_s, rho_mm in ((4, 5.0), (6, 5.0)):
        F_c = 2 * M / (n_s * rho_mm * 1e-3)
        for L_mm in (30.0, 45.0):
            for d_h in (0.10e-3, 0.12e-3, 0.15e-3):
                for l_h in (1.0e-3, 1.5e-3, 2.0e-3, 3.0e-3, 5.0e-3):
                    fe = strut_fe(L_mm * 1e-3, l_h, d_h)
                    marg = fe["P_cr_hinge_sway_N"] / F_c
                    sig = fe["stress_per_m_Pa"] * stop_mm * 1e-3 * 1.8
                    gm = 1.0 / (sig / S_F + F_c / (math.pi * d_h ** 2 / 4) / C17["S_u"])
                    r = {"n": n_s, "L_mm": L_mm, "d_h_mm": d_h * 1e3, "l_h_mm": l_h * 1e3, "buckling_margin": marg,
                         "goodman_Kt1.8": gm, "k_N_m": n_s * fe["k_lat_N_m"]}
                    if marg >= 2.0 and (best is None or gm > best["goodman_Kt1.8"]):
                        best = r
    rows.append({"topology": "necked struts (stiff middle, short C17200 hinges) in place of wires and balls",
                 "carries_couple": True, "best_with_buckling_margin_2": best, "F_stop_mN": best["k_N_m"] * stop_mm if best else None,
                 "drag_mN": 0.0, "reason": "a hinge short enough to carry the couple's compression twice over bends to "
                 f"Goodman {best['goodman_Kt1.8']:.2f} at the stop (target 1.5)" if best else "no geometry"})
    # (4) planar high-aspect flexure stage at two stations: tilt carried by out-of-plane stiffness
    k_lat_budget = 5.0
    aspect = 15.0
    k_ax = k_lat_budget * aspect ** 2
    k_tilt = k_ax * (8e-3) ** 2 + k_lat_budget * (20e-3) ** 2 / 2
    rows.append({"topology": "two planar flexure stages (beams 15 x taller than wide, 5 N/m lateral each, 20 mm apart)",
                 "carries_couple": False, "k_tilt_Nm_rad": k_tilt, "tilt_mrad": M / k_tilt * 1e3, "drag_mN": 0.0,
                 "reason": f"tilt {M / k_tilt * 1e3:.0f} mrad under the couple ({M / k_tilt * 36:.1f} mm at the ball): the "
                           "out-of-plane to in-plane stiffness ratio of a planar beam is only (height / width)^2"})
    # (5) nested parallel blades, best of a small grid meeting buckling margin 2 and Goodman 1.5
    bb = None
    for t in (40, 50, 60, 80):
        for b in (6.0, 8.0, 10.0):
            for Lb in (15.0, 20.0, 25.0, 30.0):
                r = blade_stage(t, b, Lb, 16.0, stop_mm)
                if r["buckling_margin"] >= 2 and r["goodman"] >= 1.5 and (bb is None or r["F_stop_mN"] < bb["F_stop_mN"]):
                    bb = dict(r, t_um=t, b_mm=b, L_mm=Lb)
    rows.append({"topology": "nested parallel-blade XY stage (two blades per axis, 16 mm apart)", "carries_couple": True,
                 "best": bb, "F_stop_mN": bb["F_stop_mN"] if bb else None, "drag_mN": 0.0,
                 "reason": "carries the couple, but its lateral spring force at the stop is several times the wires' and "
                           "it needs two stages in series (about 35-60 mm)"})
    # (6) ball guide
    for pre in (4.0, 1.0):
        g = ball_guide(8.3, pre)
        rows.append({"topology": f"ball thrust guide, 2 x 6 Si3N4 0.8 mm on 16.6 mm, {pre:g} N preload per race + wires",
                     "carries_couple": True, "drag_mN": g["drag_35_mN"], "hertz_run_GPa": g["hertz_run_GPa"],
                     "F_stop_mN": None, "reason": "rolling drag mu_roll x total normal load, Coulomb"})
    return {"stop_mm": stop_mm, "couple_35_mNm": M * 1e3, "rows": rows,
            "label": "CALCULATION (beam models; C17200 AMF-19; tolerances and Kt ASSUMPTION)"}
