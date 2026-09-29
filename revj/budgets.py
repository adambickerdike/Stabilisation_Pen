r"""Budgets of the integrated Rev J pen: mass, centre of mass and inertia (with and without the end-cap), length, power
and battery life per mode, heat at the grip, cost class.

CALC on the PROPOSED DESIGN of revj.packaging; round-1 SIM results are quoted with their file; every input labelled in
revj/params.py.  Nothing measured.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import ensure_paths
from . import params as PA

ensure_paths()

WIRING = 0.10          # +10 % wiring and adhesive on the base pen's parts (Rev H / study N convention, ASSUMPTION)


# --------------------------------------------------------------------------------------------------- mass properties
def _centre(c: Dict) -> np.ndarray:
    ox, oy = c.get("offset", [0.0, 0.0])
    return np.array([ox, oy, 0.5 * (c["z0"] + c["z1"])])


def _own_inertia(c: Dict, m: float) -> np.ndarray:
    """Inertia of a part about its own centre (g mm^2), principal axes along x, y, z (uniform solid shapes)."""
    L = c["z1"] - c["z0"]
    if c["shape"] == "box":
        sx, sy, sz = c["size"]
        return m / 12.0 * np.array([sy ** 2 + sz ** 2, sx ** 2 + sz ** 2, sx ** 2 + sy ** 2])
    ro = 0.25 * (c.get("d0", 0.0) + c.get("d1", c.get("d0", 0.0)))
    ri = 0.5 * c.get("d_in", 0.0) if c["shape"] == "tube" else 0.0
    Izz = 0.5 * m * (ro ** 2 + ri ** 2)
    Ixx = m / 12.0 * (3 * (ro ** 2 + ri ** 2) + L ** 2)
    return np.array([Ixx, Ixx, Izz])


def mass_properties(comps: List[Dict], wiring: float = WIRING) -> Dict:
    """Total mass (g), centre of mass (mm) and inertia tensor about the centre of mass (g mm^2)."""
    ms, rs, own = [], [], []
    for c in comps:
        m = c.get("mass_g") or 0.0
        if m <= 0:
            continue
        f = 1.0 if c["group"] == "inertial" else (1.0 + wiring)     # study K's end-cap masses carry their own allowances
        ms.append(m * f)
        rs.append(_centre(c))
        own.append(_own_inertia(c, m * f))
    ms = np.array(ms)
    rs = np.array(rs)
    M = float(ms.sum())
    cg = (ms[:, None] * rs).sum(0) / M
    I = np.zeros((3, 3))
    for m, r, io in zip(ms, rs, own):
        d = r - cg
        I += np.diag(io) + m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return {"mass_g": M, "com_mm": cg.tolist(), "inertia_g_mm2": I.tolist()}


def nose_about_pivot(comps: List[Dict], z_p: float) -> Dict:
    """The moving nose's inertia about a transverse axis through the gimbal and its tip-equivalent mass I / z_p^2."""
    I = 0.0
    m_tot = 0.0
    zc = 0.0
    for c in comps:
        if c.get("moves_with") != "nose" or not c.get("mass_g"):
            continue
        m = c["mass_g"] * (1.0 + WIRING)
        r = _centre(c)
        io = _own_inertia(c, m)
        I += io[0] + m * ((r[2] - z_p) ** 2 + r[0] ** 2)
        m_tot += m
        zc += m * r[2]
    return {"mass_g": m_tot, "com_z_mm": zc / m_tot, "I_pivot_g_mm2": I, "m_eff_tip_g": I / z_p ** 2}


def mass_budget(geo: Dict) -> Dict:
    comps = geo["components"]
    base = [c for c in comps if c["group"] != "inertial"]
    with_ec = [c for c in comps if not c.get("replaced_by_endcap")]
    by_group = {}
    for c in base:
        by_group.setdefault(c["group"], 0.0)
        by_group[c["group"]] += (c.get("mass_g") or 0.0) * (1 + WIRING)
    ec = sum(c.get("mass_g") or 0.0 for c in comps if c["group"] == "inertial")
    b = mass_properties(base)
    w = mass_properties(with_ec)
    handle_base = [c for c in base if c.get("moves_with") != "nose"]
    handle_ec = [c for c in with_ec if c.get("moves_with") not in ("nose", "inertial_mass")]
    nose = nose_about_pivot(comps, geo["pivot_z"])
    # gravity on the nose about the gimbal: the coils hold it (the nose's centre of mass sits ahead of the pivot)
    nd = PA.nose_design()
    arm = (nd["z_a"] - nd["z_p"]) * 1e-3
    d_cg = (geo["pivot_z"] - nose["com_z_mm"]) * 1e-3
    grav = {}
    for th in (35.0, 50.0, 75.0):
        tq = nose["mass_g"] * 1e-3 * 9.81 * math.cos(math.radians(th)) * d_cg
        grav[str(int(th))] = {"torque_mNm": tq * 1e3, "coil_force_N": tq / arm, "hold_power_W": (tq / arm / nd["Km_act"]) ** 2}
    nose["cg_ahead_of_pivot_mm"] = d_cg * 1e3
    nose["gravity_hold"] = grav
    nose["gravity_tip_N_studyN"] = nd["F_grav_tip_N"]
    nose["gravity_note"] = ("CALC: the coils hold the nose's weight about the gimbal (study N's Km at the magnets is an upper "
                            "bound, so the power is a lower bound); study N's duty model already carries this load "
                            "(F_grav_tip); the power budget uses this Rev J value at 50 deg in place of study N's")
    return {"base": b, "with_endcap": w, "by_group_base_g": {k: round(v, 2) for k, v in by_group.items()},
            "endcap_g": ec, "rear_cap_removed_g": sum((c.get("mass_g") or 0) * (1 + WIRING) for c in comps if c.get("replaced_by_endcap")),
            "handle_only_base": mass_properties(handle_base), "handle_only_with_endcap": mass_properties(handle_ec),
            "nose": nose, "limit_g": PA.ENVELOPE["mass_g"].value,
            "references": {"revH_g": 74.95, "revH_com_mm": 92.85, "nose2_pen_g": 83.45, "nose2_com_mm": 102.07,
                           "studyD_added_g": 9.09, "studyK_endcap_g": 43.32,
                           "DEC038_estimate_g": [134, 136],
                           "labels": "CALC (results/revH/layout.json, results/nose2/layout.json, results/drive/layout_parts.json, "
                                     "results/endcap/layout_parts.json, docs/decisions.md DEC-038)"},
            "wiring_allowance": WIRING, "label": "CALC (part masses from volumes and catalogue values; +10 % wiring and "
                                                  "adhesive on the base pen, ASSUMPTION)"}


# --------------------------------------------------------------------------------------------------- nose coil power
def nose_coil_power(tremor_mm: float, extra_travel_factor: float = 1.0, F_grav_tip_N: Optional[float] = None) -> Dict:
    """Copper loss of the C1S nose while writing with the stabiliser on (CALC, study N's duty model): per axis rms force
    sqrt((m_eff a_eff)^2 + (k x)^2 + drag^2 + grav^2), a_eff scaled with the tremor amplitude from study N's SIM
    calibration (10.6 m/s^2 rms at 1 mm, 8 Hz; linear scaling ASSUMPTION), drag = ball friction while inking."""
    nd = PA.nose_design()
    m = nd["m_eff_tip_g"] * 1e-3
    k = nd["k_tip_N_m"]
    a_eff = PA.NOSE["tremor_a_eff"].value * tremor_mm
    x = tremor_mm * 1e-3
    muN = PA.NOSE["mu_ball"].value * PA.NOSE["F_refill_N"].value / math.sin(math.radians(50.0))
    drag2 = PA.NOSE["aw_ink_share"].value * muN ** 2 / 2.0
    g = nd["F_grav_tip_N"] if F_grav_tip_N is None else F_grav_tip_N          # study N's nose, or the Rev J layout's
    F2 = (m * a_eff) ** 2 + (k * x) ** 2 + drag2 + g ** 2
    P = 2.0 * F2 / nd["Km_tip"] ** 2 * extra_travel_factor
    return {"tremor_mm_rms": tremor_mm, "F_rms_per_axis_N": math.sqrt(F2), "P_W": P,
            "share_ball_drag": drag2 / F2, "label": "CALC (study N duty model; a_eff SIM-calibrated at 1 mm, scaled)"}


# --------------------------------------------------------------------------------------------------- power per mode
def power_modes(travel_factor: float, F_grav_tip_N: Optional[float] = None) -> Dict:
    """Mean electrical power per mode (W), low and high ends, and hours on the LIR14500 (2.22 Wh usable)."""
    base = PA.POWER["base_W"].value + PA.POWER["nose_drivers_hall_W"].value            # 0.077 W, Rev H ASSUMPTION
    i_lo, i_hi = PA.POWER["page_sensor_mA"].value
    v_lo, v_hi = PA.POWER["page_sensor_V"].value
    page = (i_lo * 1e-3 * v_lo / 0.9, i_hi * 1e-3 * v_hi)                             # 1.9 V buck (90 %, ASSUMPTION) .. linear
    drv = PA.HEEL["P_drivers_W"].value                                                  # 10-20 mW
    sl_lo, sl_hi = PA.POWER["slide_sensor_W"].value                                    # refill-slide Hall (front stop)
    page = (page[0] + sl_lo, page[1] + sl_hi)                                          # carried with the page sensor (sensing)
    brake = 0.006 * 2.0                                                                 # 6 mJ per pen lift x 2 lifts/s (ASSUMPTION)
    lift_aw = PA.NOSE["pen_lift_W"].value
    lead = PA.HEEL["P_lead_W"].value / PA.HEEL["mesh_eff"].value                       # the Rev J idler mesh (one more 0.9)
    coil = {t: nose_coil_power(t, travel_factor, F_grav_tip_N)["P_W"] for t in (0.0, 0.3, 1.0, 2.0)}
    E = PA.POWER["cell_mAh"].value * 1e-3 * PA.POWER["cell_V"].value * PA.POWER["usable_frac"].value
    modes = {
        "steady_no_tremor": {"what": "stabiliser on, writing without tremor (ball drag only); wheel free-following",
                             "nose": (coil[0.0], coil[0.0]), "heel": (0.001 + drv[0], 0.001 + drv[1]), "lift": (brake, brake)},
        "steady_0.3mm": {"what": "stabiliser on, 0.3 mm rms tremor", "nose": (coil[0.3], coil[0.3]),
                         "heel": (0.001 + drv[0], 0.001 + drv[1]), "lift": (brake, brake)},
        "steady_1mm": {"what": "stabiliser on, 1 mm rms tremor at 8 Hz (study N's design duty)", "nose": (coil[1.0], coil[1.0]),
                       "heel": (0.001 + drv[0], 0.001 + drv[1]), "lift": (brake, brake)},
        "guide": {"what": "tracing / loops / known text: wheel steered (study D 1-6 mW), nose partial guidance (0.3 mm duty as a "
                          "proxy, ASSUMPTION)", "nose": (coil[0.3], coil[0.3]),
                  "heel": (PA.HEEL["P_steer_only_W"].value + drv[0], PA.HEEL["P_guide_W"].value + drv[1]), "lift": (brake, brake)},
        "lead": {"what": "lead-through: the heel drive leads a relaxed hand (study D SIM 84 mW / 0.9 = 93 mW), the nose adds detail (study N "
                         "autowrite without tremor, 0.089 W, as a proxy)", "nose": (0.089, 0.089),
                 "heel": (lead + drv[0], lead + drv[1]), "lift": (brake, brake)},
        "autowrite_no_tremor": {"what": "the nose writes a known text (study N SIM 0.089 W), pen lift 0.071 W",
                                "nose": (0.089, 0.089), "heel": (0.001 + drv[0], 0.001 + drv[1]), "lift": (lift_aw, lift_aw)},
        "autowrite_1mm": {"what": "autowrite with 1 mm tremor (study N SIM 0.166 W)", "nose": (0.166, 0.166),
                          "heel": (0.001 + drv[0], 0.001 + drv[1]), "lift": (lift_aw, lift_aw)},
        "autowrite_2mm": {"what": "autowrite with 2 mm tremor (study N SIM 0.376 W; short texts only)", "nose": (0.376, 0.376),
                          "heel": (0.001 + drv[0], 0.001 + drv[1]), "lift": (lift_aw, lift_aw)},
    }
    ec_lo, ec_hi = PA.ENDCAP["P_sim_W"].value, PA.ENDCAP["P_design_W"].value
    out = {}
    for k, m in modes.items():
        lo = base + page[0] + m["nose"][0] + m["heel"][0] + m["lift"][0]
        hi = base + page[1] + m["nose"][1] + m["heel"][1] + m["lift"][1]
        out[k] = {"what": m["what"], "nose_coil_W": m["nose"][0], "heel_W": list(m["heel"]), "pen_lift_W": m["lift"][0],
                  "electronics_W": base, "page_sensor_W": list(page), "total_W": [lo, hi], "hours": [E / hi, E / lo],
                  "total_with_endcap_W": [lo + ec_lo, hi + ec_hi], "hours_with_endcap": [E / (hi + ec_hi), E / (lo + ec_lo)]}
    return {"modes": out, "energy_Wh": E, "coil_by_tremor_W": coil, "travel_factor": travel_factor,
            "F_grav_tip_N": F_grav_tip_N if F_grav_tip_N is not None else PA.nose_design()["F_grav_tip_N"],
            "endcap_W": [ec_lo, ec_hi], "target_h": PA.ENVELOPE["battery_h"].value,
            "labels": {"electronics": "ASSUMPTION 0.077 W (Rev H: 0.065 MCU/radio + 0.012 drivers and Hall)",
                       "page_sensor": "MFR AMF-109 16.3-21.6 mA at 1.9 V (90 % buck) .. 3.7 V (linear); plus the refill-slide "
                                      "Hall 4-8 mW (ASSUMPTION, duty-cycled TMAG5273 class)",
                       "heel": "SIM study D (1, 6, 84 mW; lead divided by 0.9 for the Rev J idler mesh, CALC) + ASSUMPTION "
                               "drivers 10-20 mW",
                       "pen_lift": "CALC study N 0.071 W in autowrite; ASSUMPTION 6 mJ x 2 lifts/s brake-only otherwise",
                       "nose": "CALC (duty model) or SIM study N (autowrite rows)",
                       "endcap": "SIM study K 0.029 W (test runs) .. CALC 0.145 W (design model)",
                       "cell": "MFR AMF-80 750 mAh x 3.7 V x 0.8 usable (ASSUMPTION)"}}


def power_options(pw: Dict, length_base_mm: float, length_endcap_mm: float) -> Dict:
    """What reaching the 8 h target would take (CALC on the ASSUMPTION inputs of power_modes).

    (1) The usable energy each mode needs for 8 h, against the 2.22 Wh cell.
    (2) Power-gating the page sensor in the steady modes (tremor stabilisation does not use the page position;
        the refill-slide Hall stays on).
    (3) The cell length that would give 8 h (ASSUMPTION: usable energy proportional to the cell's length less 3 mm
        of caps and tabs, same chemistry and diameter), and the pen length that follows.
    """
    E = pw["energy_Wh"]
    target = pw["target_h"]
    ec_lo, ec_hi = pw["endcap_W"]
    sl_lo, sl_hi = PA.POWER["slide_sensor_W"].value
    L_cell = PA.POWER["cell_l_mm"].value
    caps = 3.0
    out, gated = {}, {}
    for k, m in pw["modes"].items():
        lo, hi = m["total_W"]
        need = target * hi
        L_need = caps + (L_cell - caps) * need / E
        out[k] = {"Wh_needed_for_8h_worst": need, "vs_cell": need / E,
                  "cell_length_for_8h_mm": max(L_cell, L_need),
                  "pen_length_base_mm": length_base_mm + max(0.0, L_need - L_cell),
                  "pen_length_with_endcap_mm": length_endcap_mm + max(0.0, L_need - L_cell),
                  "Wh_needed_for_8h_with_endcap_worst": target * (hi + ec_hi)}
        if k.startswith("steady"):
            p_lo = m["page_sensor_W"][0] - sl_lo
            p_hi = m["page_sensor_W"][1] - sl_hi
            lo2, hi2 = lo - p_lo, hi - p_hi
            gated[k] = {"total_W": [lo2, hi2], "hours": [E / hi2, E / lo2],
                        "hours_with_endcap": [E / (hi2 + ec_hi), E / (lo2 + ec_lo)]}
    return {"energy_needed": out, "page_sensor_gated_in_steady_modes": gated,
            "label": "CALC (power_modes rows); cell scaling ASSUMPTION (energy proportional to length less 3 mm); "
                     "gating ASSUMPTION (the sensor is off, not in a rest mode, while only the tremor is corrected)"}


# --------------------------------------------------------------------------------------------------- heat
def fin_resistance(L_src_mm: float, D_mm: float = 24.0) -> float:
    """Shell-surface temperature rise per watt (K/W) over a heat source of axial length L inside a PEEK shell: the source
    patch plus two semi-infinite fins (CALC; h and k labelled in params.THERMAL)."""
    h = PA.THERMAL["h_W_m2K"].value
    k = PA.THERMAL["k_shell_W_mK"].value
    t = PA.THERMAL["shell_wall_mm"].value
    P = math.pi * D_mm * 1e-3
    Ac = math.pi / 4 * ((D_mm * 1e-3) ** 2 - ((D_mm - 2 * t) * 1e-3) ** 2)
    return 1.0 / (h * P * L_src_mm * 1e-3 + 2.0 * math.sqrt(h * P * k * Ac))


def spreader_resistance(L_mm: float, t_mm: float, D_mm: float = 24.0) -> float:
    """Surface rise per watt (K/W) with a thin aluminium sleeve of length L inside the shell over the source: the sleeve is
    nearly isothermal over its length (fin parameter m L << 1), PEEK fins beyond its ends (CALC)."""
    h = PA.THERMAL["h_W_m2K"].value
    k = PA.THERMAL["k_shell_W_mK"].value
    tw = PA.THERMAL["shell_wall_mm"].value
    P = math.pi * D_mm * 1e-3
    Ac = math.pi / 4 * ((D_mm * 1e-3) ** 2 - ((D_mm - 2 * tw) * 1e-3) ** 2)
    kal = PA.THERMAL["k_al_W_mK"].value
    Aal = math.pi * (D_mm - 2 * tw) * 1e-3 * t_mm * 1e-3
    m = math.sqrt(h * P / (kal * Aal))
    eff = math.tanh(m * L_mm * 1e-3 / 2) / (m * L_mm * 1e-3 / 2)          # fin efficiency of the sleeve (heated at the middle)
    return 1.0 / (h * P * L_mm * 1e-3 * eff + 2.0 * math.sqrt(h * P * k * Ac))


def heat(geo: Dict, pw: Dict) -> Dict:
    """Coil rise and surface temperatures where the hand touches (CALC; no credit for the hand's cooling: conservative)."""
    amb, amb_hot = PA.THERMAL["ambient_C"].value, PA.THERMAL["ambient_hot_C"].value
    R_int = PA.THERMAL["R_int_K_W"].value
    c = {x["id"]: x for x in geo["components"]}
    plate_L = c["coil_plate"]["z1"] - c["coil_plate"]["z0"]
    R_plate = fin_resistance(plate_L)
    R_board = fin_resistance(c["main_board"]["z1"] - c["main_board"]["z0"])
    R_motor = fin_resistance(20.0)
    R_page = fin_resistance(5.0)
    R_ec = fin_resistance(20.0, 26.0)
    sp = PA.THERMAL["spreader"].value
    R_spr = spreader_resistance(sp["L_mm"], sp["t_mm"])
    rows = {}
    for k, m in pw["modes"].items():
        Pc = m["nose_coil_W"]
        rise_coil_100 = Pc * PA.NOSE["coil_R_th_K_W"].value
        shell = Pc * R_plate
        motors = (m["heel_W"][1] - PA.HEEL["P_drivers_W"].value[1])            # copper + mechanical at the motors (upper)
        rows[k] = {"coil_W": Pc, "coil_rise_K_100KW": rise_coil_100, "coil_rise_K_fin": Pc * (R_plate + R_int),
                   "web_surface_C": amb + shell, "web_surface_C_hot_room": amb_hot + shell,
                   "board_surface_C": amb + (PA.POWER["base_W"].value + 0.02) * R_board,
                   "motor_surface_C": amb + max(motors, 0.0) * R_motor,
                   "page_sensor_surface_C": amb + m["page_sensor_W"][1] * R_page,
                   "passes_20K": rise_coil_100 <= PA.ENVELOPE["coil_rise_K"].value,
                   "passes_41C_at_23C": amb + shell <= PA.ENVELOPE["grip_max_C"].value,
                   "with_spreader": {"web_surface_C": amb + Pc * R_spr, "web_surface_C_hot_room": amb_hot + Pc * R_spr,
                                     "coil_rise_K": Pc * (R_spr + R_int)}}
    ecP = pw["endcap_W"]
    return {"R_shell_over_coil_plate_K_W": R_plate, "R_with_spreader_K_W": R_spr, "spreader": sp,
            "spreader_mass_g": math.pi * (24.0 - 2.0) * sp["t_mm"] * sp["L_mm"] * PA.RHO["Al"].value * 1e-3,
            "R_shell_over_board_K_W": R_board, "R_over_motors_K_W": R_motor,
            "R_over_page_sensor_K_W": R_page, "R_over_endcap_K_W": R_ec, "rows": rows,
            "endcap_surface_C": [amb + ecP[0] * R_ec, amb + ecP[1] * R_ec],
            "where": "the coil plate (z 88.8-92.2) lies under the thumb-index web (z about 92): the web touches the shell "
                     "right over the coils; the fingertips (z 26-38) are 50 mm from them",
            "coil_power_allowed_for_41C_W": (PA.ENVELOPE["grip_max_C"].value - amb) / R_plate,
            "coil_power_allowed_for_20K_W": PA.ENVELOPE["coil_rise_K"].value / PA.NOSE["coil_R_th_K_W"].value,
            "label": "CALC (fin model of the PEEK shell, h 10 W/m2K and R_int ASSUMPTION; no hand contact counted)"}


# --------------------------------------------------------------------------------------------------- cost class
COST = [
    {"module": "base pen (shell, sleeve, ring, cell, board, IMU, LRA)", "class": "medium",
     "why": "catalogue electronics (nRF54L15, DRV8214, LSM6DSV16X, LIR14500) and moulded PEEK/TPE parts"},
    {"module": "C1S nose (gimbal, spherical-gap actuator, carrier)", "class": "high",
     "why": "custom spherical Hiperco cap and plate, curved N52 segments, bonded coils on a formed plate, laser-cut 50 um flexures"},
    {"module": "pen lift and ink-force drum", "class": "high",
     "why": "custom spiral spring (38 um strip), electro-permanent brake and bistable latch at watch scale, tendon loop"},
    {"module": "heel drive (wheel, pod, shafts, two motors, gears)", "class": "high",
     "why": "two precision 6 mm brushless motors (Faulhaber 0620 B), module-0.1 gears, jewel bearings, a sealed sprung pod"},
    {"module": "page sensor (folded optics)", "class": "high (development)",
     "why": "chip-on-board optical-flow die with custom lens and mirror; not a catalogue module in this size"},
    {"module": "reaction-mass end-cap (detachable)", "class": "medium-high",
     "why": "tungsten heavy-alloy slug (non-magnetic grade), arc coils, nested spiral flexures, own driver board"},
]


def summary(geo: Dict, travel_factor: float) -> Dict:
    mb = mass_budget(geo)
    F_g = mb["nose"]["gravity_hold"]["50"]["torque_mNm"] / geo["pivot_z"]      # mN m / mm = N at the tip (Rev J nose)
    pw = power_modes(travel_factor, F_g)
    ht = heat(geo, pw)
    L = {"base_mm": geo["length"], "with_endcap_mm": geo["length_with_endcap"], "limit_mm": PA.ENVELOPE["length_mm"].value,
         "references": {"revH_mm": 170.0, "nose2_mm": 175.0, "studyK_revH_with_endcap_mm": 175.0},
         "label": "CALC (layout)"}
    opts = power_options(pw, geo["length"], geo["length_with_endcap"])
    return {"mass": mb, "length": L, "power": pw, "power_options": opts, "heat": ht, "cost": COST,
            "cost_note": "classes only: no prices were seen on a page (as Rev H); the heel drive and the spherical actuator "
                         "dominate"}
