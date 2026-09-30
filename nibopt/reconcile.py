r"""Task 1: study K's B1, the pass's re-optimised 1.059 mm and 1.5 mm nibs (24 mm) and its 20 mm / 1.059 mm nib under
one set of assumptions, and every difference between study K's and the pass's numbers, item by item (CALCULATION).

Two waterfalls:
  K -> matched   duty A (study B's typical writing duty) on study K's B1: study K's budget chain (study B's duty model
                 x the buildable coil's 1.80 x the leads' 1.21, + the ball guide's 2.6 mN) first, then one change at a
                 time until the matched model with the brief's force-constant convention;
  pass -> matched  the pass's periodic screen on each of its nibs: its own function on its own stored map first
                 (revk/improve.matched_force_duty, read-only), then this package's screen reproducing it, then one
                 change at a time.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict

import numpy as np

from . import duty as DU
from . import evaluate as E
from . import magnet as M
from . import params as P
from . import pen as PN
from . import suspension as SU
from .design import Design, reconciliation_designs
from .params import val


# ------------------------------------------------------------------------------------------------ study K as published
def k_published() -> Dict:
    b = P.load_json("results/revK/budgets.json")["budgets"]
    k = P.load_json("results/revK/revK.json")
    pt = k["nib"]["power_table"]["rows"]
    rows = b["power"]["rows"]
    return {"duty_A_studyB_mW": {"km1.0": pt["km1_q0.2"]["P_cont_W"] * 1e3, "km0.7": pt["km0.7_q0.2"]["P_cont_W"] * 1e3,
                                 "35deg_km1.0": pt["km1_q0.2"]["P_35deg_W"] * 1e3},
            "factors": b["power"]["factors"],
            "modes_nib_mW": {m: [x * 1e3 for x in rows[m]["nib_W"]] for m in PN.MODES_K},
            "modes_nib35_mW": {m: [x * 1e3 for x in rows[m]["nib_35deg_W"]] for m in PN.MODES_K},
            "modes_hours": {m: rows[m]["hours"] for m in PN.MODES_K},
            "skin_front_pad_C": {m: b["heat"]["rows"][m]["pads_C"][0] for m in PN.MODES_K},
            "skin_max_C": {m: b["heat"]["rows"][m]["max_over_shell_C"] for m in PN.MODES_K},
            "Km_tip": k["nib"]["Km_tip_revK"], "m_move_g": k["nib"]["m_move_g"],
            "source": "results/revK/budgets.json, results/revK/revK.json (CALC, study K)"}


def k_chain_duty(q_mm: float, km: float) -> float:
    """Study K's budget chain re-run today (revk/budgets.nib_W: study B's duty model, which now carries the pass's
    coherent harmonic correction, x 1.80 x 1.21 + the 2.6 mN guide friction) (W)."""
    from revk.budgets import nib_W
    kp = k_published()
    f = kp["factors"]
    r = nib_W(q_mm, km, f["coil_power_factor_vs_studyB"], f["lead_power_factor"], f["ball_guide_friction_mN"],
              kp["Km_tip"]["x"])
    return r["P_W"]


# ------------------------------------------------------------------------------------------------ K -> matched waterfall
def waterfall_K(d: Design = None, fm_fine: Dict = None) -> Dict:
    """Duty A on study K's B1, mean over 35-75 deg: study K's chain to the matched model, one change per step (CALC)."""
    d = d or reconciliation_designs()["K_B1"]
    fm = fm_fine or E.force_map(d, fine=True, n_ang=16)
    base = E.context(d, fm)
    kp = k_published()
    q, f = val(P.DUTIES["A"])["q_rms_mm"], val(P.DUTIES["A"])["f_Hz"]
    steps = []

    def add(name, value_W, what, label="CALCULATION"):
        prev = steps[-1]["P_mW"] if steps else None
        steps.append({"step": len(steps), "name": name, "P_mW": value_W * 1e3,
                      "delta_mW": None if prev is None else value_W * 1e3 - prev, "what": what, "label": label})
    add("K as published", kp["duty_A_studyB_mW"]["km1.0"] * 1e-3 * kp["factors"]["coil_power_factor_vs_studyB"] *
        kp["factors"]["lead_power_factor"] + (kp["factors"]["ball_guide_friction_mN"] * 1e-3) ** 2 /
        kp["Km_tip"]["x"] ** 2 * kp["factors"]["lead_power_factor"],
        "study K's chain at duty A: study B's P_cont 7.56 mW (results/revK/revK.json power_table km1_q0.2) x 1.80 x 1.21 "
        "+ the 2.6 mN guide friction, K_m at the upper bound (study K's low end)")
    add("coherent harmonic load", k_chain_duty(q, 1.0),
        "the same chain re-run with bnib/loads.py as the pass corrected it (spring and inertia keep their phase)")
    # study B's model re-implemented, per axis with study K's two K_m values, roll 0, 20 degC, linear wires, 2.6 mN
    Kx, Ky = kp["Km_tip"]["x"], kp["Km_tip"]["y"]
    A_K = np.diag([1 / Kx ** 2, 1 / Ky ** 2])
    kl = SU.wires(d.n_w, d.d_w_mm, d.L_w_mm, d.K_a, d.stop_mm, d.reach_mm)["k_small_N_m"]
    ctx = replace(base, residual_mode="B", normal="B", rolls=(0.0,), A_fixed=A_K, temp_factor=1.0,
                  fw=lambda x: kl * np.abs(np.asarray(x, float)), fd=lambda th: kp["factors"]["ball_guide_friction_mN"] * 1e-3,
                  weight_trim=True)
    add("study B's loads, per axis", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "study B's loads (bnib/loads.loads_at with the counter-face: F_s along the pen, +1 sigma IMU errors, the weight "
        "trimmed in contact) re-implemented per axis with study K's K_m (0.334 / 0.272) in place of the scalar x 1.80, "
        "roll 0, linear wires, 2.6 mN guide, 20 degC")
    ctx = replace(ctx, rolls=None)
    add("all rolls", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "mean over twelve rolls (study B's fast mode evaluates roll 0 only; with unequal x and y K_m the roll matters)")
    ctx = replace(ctx, residual_mode="K")
    add("study K's residual", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "study K's face-parallelism Monte Carlo (5.7 mN mean, 6.4 mN rms) in place of study B's deterministic +1 sigma "
        "IMU residual (16 mN at 35 deg); weight still trimmed, F_s still along the pen")
    ctx = replace(ctx, normal="K")
    add("ink force N = F_n", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "study K's constant-force float: the ball's normal force is F_n = 0.196 N at every tilt (study B's duty model "
        "used F_s / sin(theta): 0.26 N at 35 deg), so the ball's drag is 28 mN instead of 38 mN at 35 deg")
    ctx = replace(ctx, weight_trim=False)
    add("gravity held in contact", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "study K's head keeps the face parallel to the paper, so the coils hold the 3.44 g moving mass (28 mN at 35 deg) "
        "in contact as well as pen-up; study B's schedule trimmed the face to cancel it in contact and study K's budget "
        "inherited that")
    ctx = replace(ctx, fd=base.fd)
    add("guide preload drag", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "the ball guide's drag from its 4 N internal preload per race (8.1 mN) instead of the couple's ball load alone "
        "(2.6 mN) (the pass's correction)")
    ctx = replace(ctx, fw=base.fw)
    add("nonlinear wires", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "the pass's beam-column wires with study K's 10,000 N/m anchor (at duty A's 0.28 mm radius the force is small)")
    ctx = replace(ctx, A_fixed=None)
    add("map centre", DU.typical(ctx, "centre10", "circle", q, f)["mean"],
        "study K's coil's centre force matrix from this package's map (fine quadrature, raw image method: 0.329 / 0.266 "
        "N/sqrt(W)) in place of study K's values scaled to study B's calibration (0.334 / 0.272)")
    r_t = E._with_temp(d, replace(ctx, temp_factor=1.0), "centre10", "circle", q, f, "steady_1mm")
    add("coil and magnet temperature", r_t["mean"],
        f"copper resistance and Br at the coil temperature of study K's fin model ({r_t['coil_C']:.1f} degC at 35 deg; "
        "study K computed at 20 degC)")
    r_c07 = E._with_temp(d, replace(ctx, temp_factor=1.0), "centre07", "circle", q, f, "steady_1mm")
    add("K_m x 0.7 at the centre", r_c07["mean"], "study K's high-end convention (centre K_m x 0.7)")
    r_w = E._with_temp(d, replace(ctx, temp_factor=1.0), "worst07", "circle", q, f, "steady_1mm")
    add("weakest point x 0.7", r_w["mean"],
        "the brief's convention: the smallest singular value of the force matrix over the usable disk x 0.7 in every "
        "direction")
    k07 = kp["duty_A_studyB_mW"]["km0.7"] * 1e-3 * kp["factors"]["coil_power_factor_vs_studyB"] * \
        kp["factors"]["lead_power_factor"] + (kp["factors"]["ball_guide_friction_mN"] * 1e-3) ** 2 / \
        (0.7 * kp["Km_tip"]["x"]) ** 2 * kp["factors"]["lead_power_factor"]
    return {"duty": "A (study B): 0.2 mm rms per axis at 8 Hz, 70 % contact, writing 30.5 mm/s, mean 35-75 deg",
            "steps": steps, "K_published_high_end_mW": k07 * 1e3, "items_final_mW": {k: v * 1e3 for k, v in
                                                                                       r_w["mean_items_W"].items()},
            "items_centre10_mW": {k: v * 1e3 for k, v in r_t["mean_items_W"].items()},
            "label": "CALCULATION"}


# ------------------------------------------------------------------------------------------------ pass -> matched waterfall
def _pass_inputs(name: str):
    """The pass's stored map, wire inputs and published screen numbers for one of its nibs (read-only)."""
    st = P.load_json("results/improvement/mechanics/mechanics_study.json")
    if name == "K_B1":
        b = st["baseline"]
        return b["map"], b["matched_wire_inputs"], b["radius_mm"], {k: max(r["copper_power_W"] for r in v["rows"])
                                                                      for k, v in b["matched_duty_by_residual"].items()}
    if name == "P_1059_20":
        cp = P.load_json("results/improvement/mechanics/compact_20mm.json")
        return cp["coil"]["map"], cp["wire"], cp["radius_mm"], {k: max(r["copper_power_W"] for r in v["rows"])
                                                                  for k, v in cp["duty_by_residual"].items()}
    target = 1.5 if name == "P_150_24" else 1.058695965882101
    c = min(st["candidates"], key=lambda x: abs(x["radius_mm"] - target))
    return c["coil"]["map"], c["wire"], c["radius_mm"], {k: max(r["copper_power_W"] for r in v["rows"])
                                                         for k, v in c["duty_by_residual"].items()}


def waterfall_pass(name: str, d: Design, fm97: Dict, residual_N: float = 0.02) -> Dict:
    from revk.improve import matched_force_duty
    mp, wire, radius, published = _pass_inputs(name)
    steps = []

    def add(nm, value_W, what):
        prev = steps[-1]["P_W"] if steps else None
        steps.append({"step": len(steps), "name": nm, "P_W": value_W, "delta_W": None if prev is None else value_W - prev,
                      "what": what, "label": "CALCULATION"})
    add("the pass as published", published[f"{residual_N:g}"],
        f"results/improvement/mechanics: worst cycle-mean copper loss, {residual_N * 1e3:.0f} mN constant residual along "
        "the motion, field x 0.7 on the map, coil and leads at +90 K")
    rep = matched_force_duty({"map": mp}, wire, radius, residual_N=residual_N)
    add("the pass's function re-run", max(r["copper_power_W"] for r in rep["rows"]),
        "revk/improve.matched_force_duty on the pass's stored map (read-only): reproduces it")
    ctx = E.context(d, fm97)
    m_pass = rep["moving_mass_kg"]
    hot = 1 + val(P.ELEC["Cu_alpha_per_K"]) * 90.0
    fw_pass = SU.wire_force_law(wire.get("n_wires", 4), wire["diameter_mm"], wire["length_mm"],
                                wire.get("anchor_stiffness_N_m", 100.0), radius + 0.2 + 0.3,
                                wire.get("assembly_tension_max_N", 0.005))
    sc = DU.screen(ctx, "map07", loads="pass", residual_N=residual_N, hot_factor=hot, mass_kg=m_pass, fw=fw_pass,
                   n_phase=512)
    add("this package, the pass's loads", sc["P_worst_W"],
        "nibopt's screen with the pass's loads, mass and hot factor on nibopt's own 97-point map: the models agree")
    sc = DU.screen(ctx, "map07", loads="pass", residual_N=residual_N, hot_factor=hot, fw=fw_pass, n_phase=512)
    add("moving mass", sc["P_worst_W"], f"this package's moving-mass model {ctx.m * 1e3:.2f} g (study K's layout "
        f"conventions) in place of the pass's {m_pass * 1e3:.2f} g")
    # matched loads, one at a time, still at +90 K and the map convention
    kr = DU.k_residual()
    th = 35.0

    def matched_screen(c2, fd_on: bool, drag_var: bool, conv: str = "map07", hot_f=hot):
        c3 = replace(c2, fd=c2.fd if fd_on else (lambda t: 0.0))
        return DU.screen(c3, conv, loads="matched", hot_factor=hot_f, n_phase=512, drag_var=drag_var)["P_worst_W"]
    add("gravity + residual + drag offset", matched_screen(ctx, False, False),
        f"the constant load: gravity on {ctx.m * 1e3:.2f} g at 35 deg and the worst roll ({ctx.m * P.G0 * math.cos(math.radians(th)) * 1e3:.1f} mN) "
        f"+ study K's residual p95 ({kr['p95_N'] * 1e3:.1f} mN) aligned with it + the drag's mean offset, in place of "
        f"{residual_N * 1e3:.0f} mN along the motion")
    add("writing-drag fluctuation", matched_screen(ctx, False, True),
        "the ball's drag as the writing direction turns (28 mN magnitude at N = F_n) with the refill-slide and face "
        "friction (study B's friction share), continuous contact")
    add("guide drag", matched_screen(ctx, True, True),
        f"the ball guide's Coulomb drag at its 4 N preload ({ctx.fd(35.0) * 1e3:.1f} mN), opposing every stroke")
    sc_t, tf, sk = E.screen_with_temp(d, ctx, "map07")
    add("coil at the fin model's temperature", sc_t["P_worst_W"],
        f"coil and magnets at the temperature study K's fin model gives for this screen sustained at 35 deg "
        f"({sk['coil_C']:.0f} degC: x {tf:.3f}) instead of +90 K copper (x {hot:.3f}) with 20 degC magnets")
    sc_w, tf_w, sk_w = E.screen_with_temp(d, ctx, "worst07")
    add("weakest point x 0.7", sc_w["P_worst_W"],
        "the brief's convention: the smallest singular value over the disk x 0.7 in every direction, in place of the "
        "map's own matrix x 0.7 at each position")
    return {"design": name, "residual_N": residual_N, "steps": steps, "label": "CALCULATION"}


# ------------------------------------------------------------------------------------------------ the matched table
def matched_table(designs: Dict[str, Design] = None, fine: bool = True) -> Dict:
    designs = designs or reconciliation_designs()
    rows = {}
    for name, d in designs.items():
        fm = E.force_map(d, fine=fine, n_ang=16 if fine else 8)
        ev = E.evaluate(d, fine=fine, full=True, fm=fm)
        rows[name] = ev
    return rows


def run(quick: bool = False) -> Dict:
    ds = reconciliation_designs()
    maps97 = {k: E.force_map(d, fine=not quick, n_ang=48 if not quick else 8) for k, d in ds.items()}
    table = {}
    for k, d in ds.items():
        table[k] = E.evaluate(d, fine=not quick, full=True, fm=maps97[k])
    wk = waterfall_K(ds["K_B1"], maps97["K_B1"])
    wp = {k: waterfall_pass(k, d, maps97[k]) for k, d in ds.items()}
    wp40 = {k: waterfall_pass(k, d, maps97[k], residual_N=0.04) for k, d in ds.items() if k in ("P_150_24",)}
    return {"designs": {k: d.summary() for k, d in ds.items()}, "table": table, "waterfall_K": wk,
            "waterfall_pass": wp, "waterfall_pass_40mN": wp40, "K_published": k_published(),
            "K_residual": DU.k_residual(), "screen_topologies": SU.screen_topologies(1.7),
            "label": "CALCULATION (matched reconciliation; nothing measured)"}
