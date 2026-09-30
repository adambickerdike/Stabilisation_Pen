r"""Budgets of the Rev K pen (CALCULATION on the PROPOSED DESIGN of revk/layout.py; inputs labelled in revk/params.py).

  mass      mass, balance point and inertia (revj/budgets.mass_properties, read-only; +10 % wiring as Rev J), the base pen
            and the heel-module variant; against Rev J.1 (results/revJ1/budgets.json) and study B's Rev K estimate
  power     per REQ-RVJ-I01 mode: the electronics counted from datasheets as Rev J.1 (revj1/power.electronics, read-only)
            with the TMAG5170 in place of the two DRV5055 nose Halls; the PMW3610-class page sensor; the nib's copper loss
            from study B's duty model (bnib/candidates.evaluate) times Rev K's buildable coil and the wire leads; the head's
            positioners, face sensor and pen lifts; the cue LRA; the heel module in the variant; hours on the LIR14500
  heat      the shell's surface over each source in a 30 degC room (Rev J's fin model), at the finger pads and at the web
  cost      the bill of materials at 100 and 1,000 units (MANUFACTURER prices where a distributor page was opened, the rest
            ASSUMPTION ranges), tooling separately
Nothing measured.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from . import ensure_paths
from . import params as PR
from .params import val

ensure_paths()
from revj import budgets as RBU  # noqa: E402  (read-only: mass_properties, WIRING)
from revj1 import power as J1P  # noqa: E402  (read-only: electronics, page_options, cells)

E_USABLE_WH = 2.22           # LIR14500 750 mAh x 3.7 V x 0.8 usable (revj1.power.cells; AMF-80, 80 % ASSUMPTION)


# ------------------------------------------------------------------------------------------------ mass
def mass(lay: Dict) -> Dict:
    base = [c for c in lay["components"]]
    heel = lay["heel_variant"]["components"]
    mb = RBU.mass_properties(base)
    mh = RBU.mass_properties(base + heel)
    groups = {}
    for c in base:
        if c.get("mass_g"):
            groups[c["group"]] = groups.get(c["group"], 0.0) + c["mass_g"] * (1 + RBU.WIRING)
    heel_g = sum((c.get("mass_g") or 0.0) for c in heel) * (1 + RBU.WIRING)
    moving = sum(c["mass_g"] for c in base if c.get("moves_with") == "nib" and c.get("mass_g"))
    head = sum(c["mass_g"] for c in base if c["group"] == "balance" and c.get("mass_g"))
    import json
    from . import REPO_ROOT
    j1 = json.load(open(REPO_ROOT / "results" / "revJ1" / "budgets.json"))["budgets"]["mass"]["base"]
    out = {"base": mb, "with_heel_module": mh, "by_group_base_g": {k: round(v, 3) for k, v in groups.items()},
           "heel_module_g": heel_g, "moving_nib_g": moving, "head_g": head,
           "balance_point_mm": {"base": mb["com_mm"][2], "with_heel": mh["com_mm"][2]},
           "limit_g": val(PR.ENVELOPE["mass_g"]),
           "compare": {"revJ1_base": {"mass_g": j1["mass_g"], "com_z_mm": j1["com_mm"][2],
                                      "I_transverse_g_mm2": j1["inertia_g_mm2"][0][0],
                                      "source": "results/revJ1/budgets.json (CALC)"},
                       "studyB_revK_estimate": {"mass_g": val(PR.B1["mass_studyB_g"]), "com_z_mm": val(PR.B1["com_studyB_mm"]),
                                                "source": "results/bnib/bnib.json recommended (CALC)"}},
           "label": "CALCULATION (layout parts' masses: volumes x handbook densities, datasheet masses, study B's parts; "
                    "+10 % wiring and adhesive, ASSUMPTION as Rev J)"}
    return out


# ------------------------------------------------------------------------------------------------ power
def electronics() -> Dict:
    """Base electronics while writing (W, low / high): Rev J.1's datasheet count with the TMAG5170 (3.4 mA, OPT-44) at a
    0.2-1.0 duty in place of the two DRV5055 nose Halls (CALC)."""
    el = J1P.electronics()
    tm = [val(PR.ELEC["nib_hall_mA"]) * 1e-3 * val(PR.ELEC["hall_supply_V"]) * d for d in val(PR.ELEC["nib_hall_duty"])]
    tot = [el["soc_W"][i] + el["imu_W"] + tm[i] + el["coil_drivers_W"][i] + el["misc_W"][i] for i in (0, 1)]
    return {"soc_W": el["soc_W"], "imu_W": el["imu_W"], "nib_hall_W": tm, "coil_drivers_W": el["coil_drivers_W"],
            "misc_W": el["misc_W"], "total_W": tot, "revJ1_total_W": el["total_W"],
            "label": "CALCULATION (revj1/power.electronics, MANUFACTURER OPT-60 / OPT-37 / AMF-37 with duty ASSUMPTION; "
                     "TMAG5170 MANUFACTURER OPT-44 at a 0.2-1.0 duty, ASSUMPTION)"}


def nib_W(q_rms_mm: float, km: float, coil_pf: float, lead_pf: float, friction_mN: float, Km_tip: float) -> Dict:
    """The nib's copper loss (W): study B's duty model at a correction duty (per axis) and Km scale, times the buildable
    coil's power factor and the wire leads' share, plus the ball guide's rolling friction met while moving (CALC)."""
    from .nib import evaluate
    ev = evaluate(round(q_rms_mm, 4), km)
    P = ev["P_cont_W"] * coil_pf * lead_pf
    P35 = ev["P_cont_worst_W"] * coil_pf * lead_pf
    fr = (friction_mN * 1e-3) ** 2 / (Km_tip * km) ** 2 * (1.0 if q_rms_mm > 0 else 0.0) * lead_pf
    return {"P_W": P + fr, "P_35deg_W": P35 + fr, "friction_W": fr, "studyB_model_W": ev["P_cont_W"]}


def modes(nibsum: Dict, hd: Dict, heel: bool = False) -> Dict:
    """Mean power per mode (W, low / high) and hours on the LIR14500 (CALC)."""
    el = electronics()["total_W"]
    page = J1P.page_options()["PMW3610_class"]
    face = list(val(PR.HEAD["face_sensor_W"]))
    pos = hd["positioner_power"]["W"]
    coil_pf = nibsum["Km_tip_revK"]["power_factor_vs_studyB"]
    lead_pf = nibsum["leads"]["options"]["revK_C17200_0.100"]["power_factor"]
    fr = nibsum["couple"]["worst"]["ball_guide_friction_mN"]
    Km = nibsum["Km_tip_revK"]["x"]
    km_lo, km_hi = 1.0, val(PR.B1["Km_scale_range"])[0]
    clip = val(PR.MODES["clip_rms_mm"])

    def nib(q, extra=1.0):
        lo = nib_W(q, km_lo, coil_pf, lead_pf, fr, Km)
        hi = nib_W(q, km_hi, coil_pf, lead_pf, fr, Km)
        return [lo["P_W"], hi["P_W"] * extra], [lo["P_35deg_W"], hi["P_35deg_W"] * extra]
    wpm = val(PR.MODES["words_per_min"])
    lifts = [wpm * x / 100.0 / 60.0 for x in val(PR.MODES["spelling_lifts_per_100_words"])]
    ticks = [wpm * x / 100.0 / 60.0 for x in val(PR.MODES["spelling_ticks_per_100_words"])]
    E_lift = hd["lift"]["energy_per_lift_J"]
    tick_mJ = val(PR.ELEC["lra_tick_mJ"])
    spell = [lifts[0] * E_lift[0] + ticks[0] * tick_mJ[0] * 1e-3, lifts[1] * E_lift[1] + ticks[1] * tick_mJ[1] * 1e-3]
    guide_ticks = [0.5 * tick_mJ[0] * 1e-3, 1.0 * tick_mJ[1] * 1e-3]           # 0.5-1 cue per second while guiding (ASSUMPTION)
    heel_sleep = [0.0, 0.002] if heel else [0.0, 0.0]
    q1 = min(1.0 / math.sqrt(2.0), clip)
    spec = {
        "steady_0mm": {"q": 0.0, "extra": 1.0, "add": [0.0, 0.0], "note": "writing with no tremor: holding and the balance residual"},
        "steady_1mm": {"q": q1, "extra": 1.0, "add": [0.0, 0.0], "note": f"1 mm rms at the tip (0.71 mm per axis) corrected"},
        "steady_2mm": {"q": clip, "extra": 1.3, "add": [0.0, 0.0],
                       "note": "2 mm rms: the +-1.06 mm nib clips (0.75 mm rms per axis); high end x1.3 for the servo "
                               "pushing into the soft stops (ASSUMPTION)"},
        "guide": {"q": val(PR.MODES["guide_q_rms_mm"]), "extra": 1.0, "add": guide_ticks,
                  "note": "guidance nudges within the nib's reach (0.3 mm rms) and 0.5-1 LRA cue per second"},
        "spelling_cue": {"q": 0.0, "extra": 1.0, "add": spell,
                         "note": f"steady writing + pen lifts {val(PR.MODES['spelling_lifts_per_100_words'])} and ticks "
                                 f"{val(PR.MODES['spelling_ticks_per_100_words'])} per 100 words at {wpm:g} words/min "
                                 f"(SIM study S rates; {E_lift[0]:.2f}-{E_lift[1]:.2f} J per lift, CALC)"},
    }
    if heel:
        lead = val(PR.MODES["lead_heel_W"])
        drv = val(PR.MODES["heel_drivers_W"])
        spec["lead_through"] = {"q": val(PR.MODES["guide_q_rms_mm"]), "extra": 1.0, "add": [lead + drv[0], lead + drv[1]],
                                "note": "heel module driving (study D SIM 84 mW / 0.9 mesh) + drivers 10-20 mW"}
        st = val(PR.MODES["heel_steer_W"])
        spec["guide"]["add"] = [spec["guide"]["add"][0] + st[0] + drv[0], spec["guide"]["add"][1] + st[1] + drv[1]]
        spec["guide"]["note"] += "; heel steered (study D 1-6 mW + drivers)"
    rows = {}
    for k, s in spec.items():
        pn, p35 = nib(s["q"], s["extra"])
        hs = heel_sleep if k not in ("lead_through", "guide") or not heel else [0.0, 0.0]
        lo = el[0] + page[0] + face[0] + pos[0] + pn[0] + s["add"][0] + hs[0]
        hi = el[1] + page[1] + face[1] + pos[1] + pn[1] + s["add"][1] + hs[1]
        rows[k] = {"q_rms_mm": s["q"], "nib_W": pn, "nib_35deg_W": p35, "electronics_W": list(el), "page_W": list(page),
                   "face_sensor_W": face, "positioners_W": list(pos), "mode_extra_W": list(s["add"]), "heel_sleep_W": hs,
                   "total_W": [lo, hi], "hours": [E_USABLE_WH / hi, E_USABLE_WH / lo], "note": s["note"]}
    # awake but not writing, and on the desk
    elh = electronics()
    hover_lo = elh["soc_W"][0] * 0.3 + elh["imu_W"] + page[0] * 0.5 + elh["misc_W"][0]
    hover_hi = elh["soc_W"][1] * 0.5 + elh["imu_W"] + page[1] + elh["misc_W"][1] + face[1] * 0.5 + 0.002
    rows["hover_awake"] = {"total_W": [hover_lo, hover_hi], "hours": [E_USABLE_WH / hover_hi, E_USABLE_WH / hover_lo],
                           "note": "held, not writing: SoC at 30-50 % of its writing duty, IMU and page sensor on, nib Hall "
                                   "and coil drivers off (the carrier rests on its soft stops), face sensor at half duty "
                                   "(ASSUMPTION)"}
    sl = val(PR.ELEC["idle_sleep_W"])
    rows["standby_desk"] = {"total_W": list(sl), "hours": [E_USABLE_WH / sl[1], E_USABLE_WH / sl[0]],
                            "days": [E_USABLE_WH / sl[1] / 24, E_USABLE_WH / sl[0] / 24],
                            "note": "on the desk (IMU wake-up, SoC idle, BLE advertising slowly): the cell's own "
                                    "self-discharge (a few % per month, ASSUMPTION) matters as much"}
    tg = val(PR.MODES["targets_h"])
    vs = {"steady_0mm": tg["steady"], "steady_1mm": tg["steady"], "guide": tg["guide"]}
    if heel:
        vs["lead_through"] = tg["lead"]
    checks = {k: {"target_h": t, "hours_low": rows[k]["hours"][0], "passes": rows[k]["hours"][0] >= t} for k, t in vs.items()}
    return {"rows": rows, "E_usable_Wh": E_USABLE_WH, "vs_REQ_RVJ_I01": checks,
            "factors": {"coil_power_factor_vs_studyB": coil_pf, "lead_power_factor": lead_pf, "Km_scale": [km_lo, km_hi],
                        "ball_guide_friction_mN": fr},
            "label": "CALCULATION (datasheet electronics MANUFACTURER with duty ASSUMPTION; nib: study B's duty model x Rev K's "
                     "coil and leads; positioners MANUFACTURER AMF-15 with rates ASSUMPTION; SIM rates from study S)"}


def compare_power(pw: Dict) -> Dict:
    import json
    from . import REPO_ROOT
    j1 = json.load(open(REPO_ROOT / "results" / "revJ1" / "budgets.json"))["budgets"]["power"]["x1_PMW3610_class"]
    return {"revJ1": {"steady_no_tremor_h": j1["hours"]["LIR14500"]["steady_no_tremor"]["h"],
                      "steady_1mm_h": j1["hours"]["LIR14500"]["steady_1mm"]["h"], "guide_h": j1["hours"]["LIR14500"]["guide"]["h"],
                      "lead_h": j1["hours"]["LIR14500"]["lead"]["h"],
                      "status": "suspended (DEC-046: the static side load was left out; with it about 1 h)",
                      "source": "results/revJ1/budgets.json (CALC)"},
            "studyB": {"battery_h_CALC": val(PR.B1["battery_h_studyB"]), "battery_h_SIM": val(PR.B1["battery_h_sim"]),
                       "basis": "electronics 47 mW mid + nib 7.6 / 0.85 + 2 mW positioners (study B)",
                       "source": "results/bnib/bnib.json; docs/balanced_nib.md"},
            "revK_steady_1mm_h": pw["rows"]["steady_1mm"]["hours"],
            "why_different_from_studyB": "Rev K counts the TMAG5170 at up to full duty, a face-position sensor (4-8 mW, "
                                         "Rev J value), the buildable coil (x%.2f copper loss) and the wire leads (x%.2f)" %
                                         (pw["factors"]["coil_power_factor_vs_studyB"], pw["factors"]["lead_power_factor"])}


# ------------------------------------------------------------------------------------------------ heat
def fin_R(L_mm: float, D_mm: float = 24.0) -> float:
    h = val(PR.THERMAL["h_W_m2K"])
    k = val(PR.THERMAL["k_shell_W_mK"])
    t = 1.0
    P = math.pi * D_mm * 1e-3
    Ac = math.pi / 4 * ((D_mm * 1e-3) ** 2 - ((D_mm - 2 * t) * 1e-3) ** 2)
    return 1.0 / (h * P * L_mm * 1e-3 + 2.0 * math.sqrt(h * P * k * Ac))


def fin_lambda_mm(D_mm: float = 24.0) -> float:
    h = val(PR.THERMAL["h_W_m2K"])
    k = val(PR.THERMAL["k_shell_W_mK"])
    P = math.pi * D_mm * 1e-3
    Ac = math.pi / 4 * ((D_mm * 1e-3) ** 2 - ((D_mm - 2.0) * 1e-3) ** 2)
    return math.sqrt(k * Ac / (h * P)) * 1e3


def surface_rise(z_mm: float, sources: List[Dict]) -> float:
    """Shell-surface rise (K) at z from sources {z0, z1, P}: each source's patch at P x R_fin(L), decaying with the fin's
    length constant beyond its ends (1-D PEEK shell, no hand contact: conservative) (CALC)."""
    lam = fin_lambda_mm()
    dT = 0.0
    for s in sources:
        R = fin_R(s["z1"] - s["z0"])
        d = 0.0 if s["z0"] <= z_mm <= s["z1"] else min(abs(z_mm - s["z0"]), abs(z_mm - s["z1"]))
        dT += s["P"] * R * math.exp(-d / lam)
    return dT


def heat(lay: Dict, pw: Dict) -> Dict:
    c = {x["id"]: x for x in lay["components"]}
    room = val(PR.THERMAL["room_C"])
    web = val(PR.ENVELOPE["web_z_mm"])
    pads = val(PR.ENVELOPE["finger_pads_z_mm"])
    rows = {}
    for k, r in pw["rows"].items():
        if "nib_W" not in r:
            continue
        hi = 1
        src = [{"name": "coils (through the bonded stator)", "z0": c["back_plate"]["z0"], "z1": c["keeper"]["z1"],
                "P": r["nib_35deg_W"][hi]},
               {"name": "board", "z0": c["main_board"]["z0"], "z1": c["main_board"]["z1"],
                "P": r["electronics_W"][hi] - r["electronics_W"][hi] * 0.0},
               {"name": "page sensor", "z0": c["page_sensor"]["z0"], "z1": c["page_sensor"]["z1"], "P": r["page_W"][hi]},
               {"name": "head motors and face sensor", "z0": c["head_tilt_motor"]["z0"], "z1": c["head_roll_motor"]["z1"],
                "P": r["positioners_W"][hi] + r["face_sensor_W"][hi] + r["mode_extra_W"][hi]}]
        if k == "lead_through":
            src.append({"name": "heel motors", "z0": 104.0, "z1": 124.0, "P": r["mode_extra_W"][hi]})
        rows[k] = {"web_C": room + surface_rise(web, src), "pads_C": [room + surface_rise(z, src) for z in pads],
                   "basis": "35 deg nib power at the high end (Km 0.7 x, high electronics): the worst steady case",
                   "max_over_shell_C": room + max(surface_rise(z, src) for z in np.arange(5.0, lay["length"], 0.5)),
                   "coil_C": room + surface_rise(0.5 * (src[0]["z0"] + src[0]["z1"]), src)
                   + src[0]["P"] * val(PR.THERMAL["R_int_coil_K_W"]), "sources_W": {s["name"]: s["P"] for s in src}}
    worst = max(rows.values(), key=lambda r: r["max_over_shell_C"])
    return {"room_C": room, "rows": rows, "worst_shell_C": worst["max_over_shell_C"], "fin_length_constant_mm": fin_lambda_mm(),
            "limits": {"held_max_C": val(PR.THERMAL["skin_limit_C"]), "design_target_C": val(PR.THERMAL["skin_target_C"])},
            "passes_41C": worst["max_over_shell_C"] <= val(PR.THERMAL["skin_target_C"]),
            "compare": {"revJ1_web_1mm_C": 35.9, "revJ1_source": "DEC-045 (CALC; suspended by DEC-046)",
                        "studyB_skin_C": val(PR.B1["T_skin_studyB_C"])},
            "pen_lift_motor_rise_K": 0.3 / (0.16 * 0.5),
            "label": "CALCULATION (1-D fin model of the PEEK shell, h 10 W/m2K ASSUMPTION, k MANUFACTURER AMF-24; high-end "
                     "powers; no hand contact counted: conservative)"}


# ------------------------------------------------------------------------------------------------ cost
def cost(heel: bool = False) -> Dict:
    rows = []
    tot = {"100": [0.0, 0.0], "1000": [0.0, 0.0]}
    items = list(PR.COST) + (list(PR.HEEL_COST) if heel else [])
    for name, qty, c100, c1000, lab, src in items:
        r = {"item": name, "qty": qty, "unit_100_usd": list(c100), "unit_1000_usd": list(c1000),
             "line_100_usd": [qty * c100[0], qty * c100[1]], "line_1000_usd": [qty * c1000[0], qty * c1000[1]],
             "label": lab, "source": src}
        rows.append(r)
        for i in (0, 1):
            tot["100"][i] += r["line_100_usd"][i]
            tot["1000"][i] += r["line_1000_usd"][i]
    mfr_share = {q: sum(r[f"line_{q}_usd"][0] for r in rows if r["label"] == PR.MFR) / tot[q][0] for q in ("100", "1000")}
    nre = val(PR.NRE)
    nre_tot = [nre["moulds_and_fixtures_usd"][0] + nre["coil_tooling_usd"][0], nre["moulds_and_fixtures_usd"][1]
               + nre["coil_tooling_usd"][1]]
    big = sorted(rows, key=lambda r: -r["line_1000_usd"][1])[:5]
    return {"rows": rows, "unit_cost_usd": tot, "catalogue_share_of_low": mfr_share, "nre_usd": nre_tot,
            "nre_per_unit_at_1000_usd": [nre_tot[0] / 1000, nre_tot[1] / 1000],
            "largest_at_1000": [r["item"] for r in big],
            "compare": {"revJ1": "cost classes only (no prices seen): heel drive and spherical actuator 'high' "
                                 "(revj/budgets.COST)",
                        "studyB": "a 16-line bill of materials without prices (results/bnib/bnib.json bom)"},
            "label": "MANUFACTURER prices for five catalogue ICs (distributor pages opened 2026-09-30, AMF-250..254 proposed); "
                     "every other line ASSUMPTION (a request for quotation pins it)"}


def summary(lay: Dict, nibsum: Dict, hd: Dict) -> Dict:
    ms = mass(lay)
    pw = modes(nibsum, hd, heel=False)
    pw_h = modes(nibsum, hd, heel=True)
    ht = heat(lay, pw)
    ht_h = heat(lay, pw_h)
    return {"mass": ms, "electronics": electronics(), "power": pw, "power_heel_variant": pw_h,
            "power_compare": compare_power(pw), "heat": ht, "heat_heel_variant": ht_h,
            "cost": cost(False), "cost_heel_variant": cost(True),
            "length_mm": lay["length"], "length_compare": {"revJ1_base_mm": 143.9, "studyB_mm": val(PR.B1["length_studyB_mm"]),
                                                            "limit_mm": val(PR.ENVELOPE["length_mm"])}}
