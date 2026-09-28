"""Heavy optimisation steps of the hardware study, each cached in results/opt/_cache/<step>.json.

Steps
-----
enumerate   exhaustive enumeration of the mechanical discrete choices (topology x ceramic x stack x leaf material
            x clamp electrodes), each solved by multi-start augmented-Lagrangian Adam + L-BFGS-B polish, with the
            reference power options (LT8365 charge-recovery driver, 2 x DRV5055 Hall)
drivers     driver x Hall-sensor enumeration for the best mechanical combinations (re-optimised: the drive range
            and the battery-life constraint depend on them)
cmaes       derivative-free CMA-ES global check of the best combination
pareto      epsilon-constraint Pareto front: maximise the worst-case stroke subject to mean assist power <= P_max
            and mass <= M_max, over a grid
fc_sweep    best stroke against the nib spring force F_c (0.08-0.30 N), at mu 0.15 and mu 0.35
Evidence status: CALCULATION.
"""
from __future__ import annotations

import itertools
import json
import os
import time

import numpy as np
import torch

from . import OUT
from . import model as MD
from . import optimise as O

CACHE = os.path.join(OUT, "_cache")
FC_DEFAULT = 0.15
FIXED_EXTRA: dict = {}     # variables held fixed in every step after the recommendation (e.g. the skid ring)
BASE_POWER = dict(driver="recovery_lt8365", hall="drv5055a4_x2")


def _save(name, obj):
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, name + ".json"), "w") as f:
        json.dump(obj, f, default=_default)


def _load(name):
    p = os.path.join(CACHE, name + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


def _nm(step: str, best: dict) -> str:
    """Cache name of a study around one design: the step plus the design's combination key (and its candidate
    tag when two candidates share a combination)."""
    return f"{step}__{best.get('cache_tag') or best['key']}"


def _default(o):
    if isinstance(o, torch.Tensor):
        return o.detach().tolist()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return str(o)


def opts_from(d: dict) -> MD.Options:
    keep = {k: v for k, v in d.items() if k in MD.Options.__dataclass_fields__ and k != "extra"}
    return MD.Options(**keep)


def summarise(prob: O.Problem, u, lam=None):
    """Design and its key metrics (plain floats) for caching and reporting."""
    x, out, G, f = O.design_of(prob, u)
    F = lambda v: float(v.reshape(-1)[0]) if isinstance(v, torch.Tensor) else float(v)   # noqa: E731
    st = out["stage"]
    row = {"x": x, "u": list(map(float, u)), "f": F(f), "viol": float(O.violation(G[None])[0]),
           "q_wc_um": F(out["q_wc"]) * 1e6, "q_nom_um": F(out["q_nom"]) * 1e6, "q_lim_um": F(out["q_lim"]) * 1e6,
           "usable_wc_um": F(out["usable_wc"]) * 1e6, "q_wc_mu035_um": F(out["q_wc_mu035"]) * 1e6,
           "q_35_nomtol_um": F(out["q_35_nomtol"]) * 1e6, "q_nom_tol_um": F(out["q_nom_tol"]) * 1e6,
           "F_b_nib_N": F(st["F_b_nib"]), "F_b_nib_tol_N": F(out["stage_wc"]["F_b_nib"]), "k_tot_nib": F(st["k_tot"]),
           "free_stroke_nib_um": F(st["delta_f_nib"]) * 1e6, "lever": F(st["n"]), "f1_Hz": F(st["f1"]),
           "m_eq_nib_g": F(st["m_eq_nib"]) * 1e3, "C_axis_uF": F(st["C_axis"]) * 1e6,
           "mass_g": F(out["mass"]["total_g"]), "mass_with_margin_g": F(out["mass"]["with_margin_g"]),
           "plates_g": F(out["mass"]["plates_g"]), "sig_stop_MPa": F(out["sig_stop"]) / 1e6,
           "sig_allow_MPa": F(out["sig_allow"]) / 1e6, "sig0_MPa": F(out["sig0"]) / 1e6,
           "P_fail_stop": F(out["P_fail_stop"]), "leaf_sf": F(out["leaf_sf"]), "leaf_stress_MPa": F(out["leaf_stress"]) / 1e6,
           "protrusion_travel_mm": F(out["geo"]["protrusion_travel"]) * 1e3, "u_tip_um": F(out["geo"]["u_tip"]) * 1e6,
           "g": {k: F(v) for k, v in out["g"].items()}}
    if "sig_drop_2ms" in out:
        row["sig_drop_2ms_MPa"] = F(out["sig_drop_2ms"]) / 1e6
        row["P_fail_drop_2ms"] = F(out["P_fail_drop_2ms"])
    if "P_total_mean" in out:
        row.update({"P_total_mean_mW": F(out["P_total_mean"]) * 1e3, "P_total_worst_mW": F(out["P_total_worst"]) * 1e3,
                    "P_rail_grid_mean_mW": F(out["P_rail_grid_mean"]) * 1e3,
                    "life_assist_h": F(out["life_assist_h"]), "life_assist_mean_h": F(out["life_assist_mean_h"]),
                    "life_recording_h": F(out["life_recording_h"]), "sigma_nib_um": F(out["noise"]["sigma_nib"]) * 1e6,
                    "servo_rho": F(out["noise"]["rho"]),
                    "power_cases_mW": {c: {k: F(v) * 1e3 for k, v in d.items()} for c, d in out["power"].items()}})
    if lam is not None:
        row["active"] = O.active_constraints(prob, G, lam)
    return row


FEAS_TOL = 2e-3          # max normalised violation accepted as feasible (0.2 um on lengths, 0.2 % otherwise)


def solve_combo(opts: MD.Options, fixed=None, n_starts=12, iters=900, polish=3, seed=0, eps=None, extra_start=None,
                warm=None):
    """Multi-start AL-Adam (Sobol starts + the current design + warm starts from other optima) and an L-BFGS-B
    polish of the best `polish` candidates."""
    prob = O.Problem(opts, fixed=fixed, eps=eps)
    t0 = time.time()
    inc = prob.u_of(extra_start, 0.0) if extra_start is not None else prob.u_of(MD.CURRENT, 0.0)
    U0 = O.sobol_starts(n_starts, prob.n, seed=seed, include=inc)
    if warm:
        W = torch.stack([prob.u_of(w, 0.0) for w in warm])
        U0 = torch.cat([W, U0], 0)
    U, f, G, lam = O.adam_al(prob, U0, iters=iters)
    v = O.violation(torch.nan_to_num(G, nan=-10.0))
    score = torch.where(v < FEAS_TOL, f, f - 1e3 * v)
    order = torch.argsort(score, descending=True)
    results = []
    for j in order[:polish].tolist():
        u, lamj, hist = O.lbfgs_al(prob, U[j].numpy(), lam0=lam[j])
        with torch.no_grad():
            fj, Gj = prob.eval(torch.tensor(u[None], dtype=torch.float64))
        vj = float(O.violation(torch.nan_to_num(Gj, nan=-10.0))[0])
        results.append({"u": u, "f": float(fj[0]), "viol": vj, "lam": lamj})
    feas = [r for r in results if r["viol"] < FEAS_TOL]
    best = max(feas, key=lambda r: r["f"]) if feas else min(results, key=lambda r: r["viol"])
    row = summarise(prob, best["u"], best["lam"])
    row.update({"options": {k: v for k, v in vars(opts).items() if k != "extra"}, "key": opts.key(),
                "feasible": best["viol"] < FEAS_TOL, "adam_feasible_fraction": float((v < FEAS_TOL).float().mean()),
                "polished_f": [r["f"] for r in results], "polished_viol": [r["viol"] for r in results],
                "n_starts_total": int(U0.shape[0]), "elapsed_s": time.time() - t0, "fixed": fixed or {}, "eps": eps or {}})
    return row


def _warm_from(rows, k=4):
    feas = sorted([r for r in rows if r.get("feasible")], key=lambda r: -r["usable_wc_um"])
    return [r["x"] for r in feas[:k]]


# ------------------------------------------------------------------------------------------------------------
def step_enumerate(force=False, n_starts=8, iters=900):
    cached = None if force else _load("enumerate")
    rows = cached["rows"] if cached else []
    done = {r["key"] for r in rows}
    # the clamp-electrode choice changes only the capacitance (power), not the stroke optimum: it is enumerated
    # with the driver and Hall sensor in step_drivers
    combos = list(itertools.product(("Q", "L", "Q2L"), ("PIC252", "PIC251"), (1, 2), ("C17200", "Ti6Al4V")))
    t0 = time.time()
    for topo, cer, stk, lm in combos:
        opts = MD.Options(topology=topo, ceramic=cer, stack=stk, leaf_mat=lm, **BASE_POWER)
        if opts.key() in done:
            continue
        r = solve_combo(opts, fixed={"Fc": FC_DEFAULT}, n_starts=n_starts, iters=iters, warm=_warm_from(rows))
        rows.append(r)
        print(f"{opts.key():60s} feasible {r['feasible']} usable_wc {r['usable_wc_um']:.0f} um  q_nom {r['q_nom_um']:.0f}  "
              f"mass {r['mass_with_margin_g']:.1f} g  P {r.get('P_total_mean_mW', float('nan')):.0f} mW  "
              f"life {r.get('life_assist_h', float('nan')):.2f} h  ({r['elapsed_s']:.0f} s)", flush=True)
        _save("enumerate", {"rows": rows, "elapsed_s": time.time() - t0})
    return rows


def best_rows(rows, k=3):
    feas = [r for r in rows if r["feasible"]]
    return sorted(feas, key=lambda r: -r["usable_wc_um"])[:k]


def step_drivers(enum_rows, force=False, top=1):
    cached = None if force else _load("drivers")
    rows = cached["rows"] if cached else []
    done = {r["key"] for r in rows}
    t0 = time.time()
    for base in best_rows(enum_rows, top):
        for drv, hall, ce in itertools.product(("drv2700", "recovery_lt8330", "recovery_lt8365", "capdrive_bos1931"),
                                               ("tmag5170_a2", "drv5055a4_x2"), (True, False)):
            if True:
                o = dict(base["options"], driver=drv, hall=hall, clamp_electroded=ce)
                opts = opts_from(o)
                if opts.key() in done:
                    continue
                r = solve_combo(opts, fixed={"Fc": FC_DEFAULT}, n_starts=4, iters=500, polish=2, extra_start=base["x"],
                                warm=[base["x"]])
                r["base_key"] = base["key"]
                rows.append(r)
                print(f"{opts.key():70s} feasible {r['feasible']} usable_wc {r['usable_wc_um']:.0f} um "
                      f"P {r.get('P_total_mean_mW', float('nan')):.0f} mW life {r.get('life_assist_h', float('nan')):.2f} h",
                      flush=True)
                _save("drivers", {"rows": rows, "elapsed_s": time.time() - t0})
    return rows


def step_cmaes(best, force=False, seeds=(0, 1, 2)):
    cached = None if force else _load(_nm("cmaes", best))
    if cached:
        return cached
    opts = opts_from(best["options"])
    prob = O.Problem(opts, fixed={"Fc": FC_DEFAULT, **FIXED_EXTRA})
    runs = []
    for s in seeds:
        t0 = time.time()
        r = O.cmaes(prob, u0=None, sigma0=0.3, gens=400, seed=s)
        # polish the CMA-ES point with the gradient method to see which basin it found
        u, lam, hist = O.lbfgs_al(prob, r["u"])
        with torch.no_grad():
            fp, Gp = prob.eval(torch.tensor(u[None], dtype=torch.float64))
        runs.append({"seed": s, "cmaes_f": r["f"], "cmaes_viol": r["viol"], "cmaes_usable_um": r["f"] * 100.0,
                     "generations": r["generations"], "popsize": r["popsize"],
                     "polished_usable_um": float(fp[0]) * 100.0,
                     "polished_viol": float(O.violation(Gp)[0]), "elapsed_s": time.time() - t0})
        print("cmaes", runs[-1], flush=True)
    out = {"key": best["key"], "gradient_optimum_usable_um": best["usable_wc_um"], "runs": runs}
    _save(_nm("cmaes", best), out)
    return out


def step_pareto(best, force=False, P_grid=None, M_grid=None):
    cached = None if force else _load(_nm("pareto", best))
    if cached and cached.get("complete"):
        return cached
    opts = opts_from(best["options"])
    P0 = best["P_total_mean_mW"] * 1e-3
    M0 = best["mass_with_margin_g"]
    P_grid = P_grid or [P0 * f for f in (0.90, 0.94, 0.97, 1.0, 1.06)]
    M_grid = M_grid or [M0 * f for f in (0.88, 0.93, 0.97, 1.05)]
    pts = list(cached["points"]) if cached else []           # resume a partial run
    done = {(round(p["P_max_mW"], 6), round(p["M_max_g"], 6)) for p in pts}
    t0 = time.time()
    for Pm in P_grid:
        for Mm in M_grid:
            if (round(Pm * 1e3, 6), round(Mm, 6)) in done:
                continue
            r = solve_combo(opts, fixed={"Fc": FC_DEFAULT, **FIXED_EXTRA}, n_starts=4, iters=500, polish=1,
                            eps={"P_max": Pm, "M_max": Mm}, extra_start=best["x"], warm=[best["x"]])
            r["P_max_mW"], r["M_max_g"] = Pm * 1e3, Mm
            pts.append(r)
            print(f"pareto P<= {Pm * 1e3:.1f} mW M<= {Mm:.2f} g: feasible {r['feasible']} usable {r['usable_wc_um']:.0f} um",
                  flush=True)
            _save(_nm("pareto", best), {"points": pts, "key": best["key"], "elapsed_s": time.time() - t0, "complete": False})
    out = {"points": pts, "key": best["key"], "elapsed_s": time.time() - t0, "complete": True}
    _save(_nm("pareto", best), out)
    return out


def step_fc_sweep(best, force=False, fcs=(0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30)):
    cached = None if force else _load(_nm("fc_sweep", best))
    if cached and cached.get("complete"):
        return cached
    rows = list(cached["rows"]) if cached else []            # resume a partial run
    done = {(round(r["mu_wc"], 6), round(r["Fc"], 6)) for r in rows}
    for mu in (0.15, 0.35):
        for fc in fcs:
            if (round(mu, 6), round(fc, 6)) in done:
                continue
            o = dict(best["options"], mu_wc=mu)
            r = solve_combo(opts_from(o), fixed={"Fc": fc, **FIXED_EXTRA}, n_starts=4, iters=600, polish=2, extra_start=best["x"],
                            warm=[best["x"]])
            r["Fc"], r["mu_wc"] = fc, mu
            rows.append(r)
            print(f"Fc {fc:.2f} mu {mu:.2f}: feasible {r['feasible']} usable_wc {r['usable_wc_um']:.0f} um "
                  f"q_wc {r['q_wc_um']:.0f}", flush=True)
            _save(_nm("fc_sweep", best), {"rows": rows, "complete": False})
    out = {"rows": rows, "complete": True}
    _save(_nm("fc_sweep", best), out)
    return out


def step_stop_sweep(best, force=False, qlims=(0.30e-3, 0.35e-3, 0.40e-3, 0.45e-3, 0.50e-3)):
    """Worst-case usable stroke against the nominal soft limit (stop travel - 0.10 mm): robustness vs authority.
    The skid ring is free here (up to 2.0 mm): the refill cone needs a larger skid aperture for longer stops."""
    cached = None if force else _load(_nm("stop_sweep", best))
    if cached and cached.get("complete"):
        return cached
    rows = list(cached["rows"]) if cached else []
    done = {round(r["q_lim_min_um"], 3) for r in rows}
    fixed = {"Fc": FC_DEFAULT, **{k: v for k, v in FIXED_EXTRA.items() if k != "r_ring"}}
    for ql in qlims:
        if round(ql * 1e6, 3) in done:
            continue
        o = dict(best["options"], q_lim_min=ql)
        r = solve_combo(opts_from(o), fixed=fixed, n_starts=8, iters=800, polish=2, extra_start=best["x"],
                        warm=[dict(best["x"], q_stop=ql + 0.1e-3, r_ring=2.0e-3)])
        r["q_lim_min_um"] = ql * 1e6
        rows.append(r)
        print(f"soft limit >= {ql * 1e6:.0f} um: feasible {r['feasible']} usable_wc {r['usable_wc_um']:.0f} q_nom "
              f"{r['q_nom_um']:.0f} q_lim {r['q_lim_um']:.0f} skid ring {r['x']['r_ring'] * 1e3:.2f} mm", flush=True)
        _save(_nm("stop_sweep", best), {"rows": rows, "complete": False})
    out = {"rows": rows, "complete": True}
    _save(_nm("stop_sweep", best), out)
    return out


def step_firmware_clamp(best, force=False, fracs=(1.0, 0.5, 0.25)):
    """Price of the stop-stress constraint: re-optimise with a firmware drive clamp while pinned at a stop."""
    cached = None if force else _load(_nm("firmware_clamp", best))
    if cached and cached.get("complete"):
        return cached
    rows = list(cached["rows"]) if cached else []
    done = {round(r["stop_drive_frac"], 6) for r in rows}
    for fr in fracs:
        if round(fr, 6) in done:
            continue
        o = dict(best["options"], stop_drive_frac=fr)
        r = solve_combo(opts_from(o), fixed={"Fc": FC_DEFAULT, **FIXED_EXTRA}, n_starts=8, iters=800, polish=2,
                        extra_start=best["x"])
        r["stop_drive_frac"] = fr
        rows.append(r)
        print(f"stop drive fraction {fr}: usable_wc {r['usable_wc_um']:.0f}", flush=True)
        _save(_nm("firmware_clamp", best), {"rows": rows, "complete": False})
    out = {"rows": rows, "complete": True}
    _save(_nm("firmware_clamp", best), out)
    return out


def step_hall_rear(best, force=False):
    """Price of the nose Hall sensor: the same combination with the sensor behind the collar (leaf zone)."""
    cached = None if force else _load(_nm("hall_rear", best))
    if cached:
        return cached
    o = dict(best["options"], hall_location="rear")
    r = solve_combo(opts_from(o), fixed={"Fc": FC_DEFAULT, **FIXED_EXTRA}, n_starts=8, iters=900, polish=2,
                    extra_start=best["x"])
    print(f"Hall behind the collar: usable_wc {r['usable_wc_um']:.0f} um (nose: {best['usable_wc_um']:.0f})", flush=True)
    out = {"row": r, "nose_usable_wc_um": best["usable_wc_um"]}
    _save(_nm("hall_rear", best), out)
    return out


def step_refine(rows, force=False, top=6, n_starts=16, iters=1000):
    """Refinement: (1) the best combinations with more starts and warm starts from every good optimum; (2) any
    combination below 70 % of a sibling (same layout and stack; other leaf material or other ceramic), re-solved
    from the sibling's optimum, so an unlucky start does not decide a comparison. The better of the screening and
    refined solutions is kept."""
    cached = None if force else _load("refine")
    out = cached["rows"] if cached else []
    done = {r["key"] for r in out}
    best = sorted([r for r in rows if r.get("feasible")], key=lambda r: -r["usable_wc_um"])[:top]
    warm = _warm_from(rows, k=8)
    todo = [(r0, warm + [r0["x"]], "top") for r0 in best]
    for r0 in rows:
        if r0 in best:
            continue
        o0 = r0["options"]
        sibs = []
        for fld, a, b in (("leaf_mat", "C17200", "Ti6Al4V"), ("ceramic", "PIC252", "PIC251")):
            other = b if o0[fld] == a else a
            sibs += [r for r in rows if r["options"]["topology"] == o0["topology"] and r["options"][fld] == other
                     and all(r["options"][k] == o0[k] for k in ("stack", "ceramic", "leaf_mat") if k != fld)]
        sibs = [r for r in sibs if r.get("feasible") and r0["usable_wc_um"] < 0.7 * r["usable_wc_um"]]
        if sibs:
            todo.append((r0, [r["x"] for r in sibs] + warm[:4], "sibling"))
    for r0, wm, why in todo:
        if r0["key"] in done:
            continue
        r = solve_combo(opts_from(r0["options"]), fixed={"Fc": FC_DEFAULT}, n_starts=n_starts, iters=iters, polish=3,
                        seed=1, warm=wm)
        if r0.get("feasible") and (not r["feasible"] or r["usable_wc_um"] < r0["usable_wc_um"]):
            r = dict(r0)                                  # keep the better of the two solves
        r["screening_usable_wc_um"] = r0["usable_wc_um"]
        r["refine_reason"] = why
        out.append(r)
        done.add(r["key"])
        print(f"refine ({why}) {r['key']:60s} {r0['usable_wc_um']:.0f} -> {r['usable_wc_um']:.0f} um "
              f"(feasible {r['feasible']})", flush=True)
        _save("refine", {"rows": out})
    return out


def step_ring_fixed(best, force=False, r_ring=1.4e-3):
    """Price of keeping the P0.1.2 skid ring (1.4 mm): a larger ring widens the nose for the collar and Hall sensor
    but lengthens the nib's axial travel, which the touchdown/lift behaviour (EXP-Q08) depends on."""
    cached = None if force else _load("ring_fixed")
    if cached:
        return cached
    r = solve_combo(opts_from(best["options"]), fixed={"Fc": FC_DEFAULT, "r_ring": r_ring}, n_starts=8, iters=900,
                    polish=3, extra_start=dict(best["x"], r_ring=r_ring), warm=[dict(best["x"], r_ring=r_ring)])
    print(f"skid ring fixed at {r_ring * 1e3:.1f} mm: usable_wc {r['usable_wc_um']:.0f} um (free ring: "
          f"{best['usable_wc_um']:.0f})", flush=True)
    out = {"row": r, "free_ring_usable_wc_um": best["usable_wc_um"], "r_ring_m": r_ring}
    _save("ring_fixed", out)
    return out


def step_leaf_gauge(best, force=False, gauges=(38.1e-6, 50.8e-6)):
    """Leaf thickness snapped to inch strip gauges (0.0015", 0.002"), the other variables re-optimised: the price of
    ordering standard strip instead of a strip rolled to the optimum thickness."""
    cached = None if force else _load(_nm("leaf_gauge", best))
    if cached and cached.get("complete"):
        return cached
    rows = list(cached["rows"]) if cached else []
    done = {round(r["leaf_t_um"], 3) for r in rows}
    for tl in gauges:
        if round(tl * 1e6, 3) in done:
            continue
        x0 = dict(best["x"], leaf_t=tl)
        r = solve_combo(opts_from(best["options"]), fixed={"Fc": FC_DEFAULT, "leaf_t": tl, **FIXED_EXTRA}, n_starts=8,
                        iters=800, polish=2, extra_start=x0, warm=[x0])
        r["leaf_t_um"] = tl * 1e6
        rows.append(r)
        print(f"leaf gauge {tl * 1e6:.1f} um: feasible {r['feasible']} usable_wc {r['usable_wc_um']:.0f} um "
              f"(optimum {best['x']['leaf_t'] * 1e6:.1f} um: {best['usable_wc_um']:.0f})", flush=True)
        _save(_nm("leaf_gauge", best), {"rows": rows, "complete": False})
    out = {"rows": rows, "complete": True}
    _save(_nm("leaf_gauge", best), out)
    return out


def leaf_tolerance(best, fracs=(-0.10, -0.05, 0.05, 0.10)):
    """The recommended design with its leaf thickness off by +/-5 and 10 % (nothing re-optimised): cross ratio,
    buckling safety factor, leaf stress and worst-case stroke."""
    opts = opts_from(best["options"])
    F = lambda v: float(v.reshape(-1)[0])   # noqa: E731
    rows = []
    for fr in (0.0,) + tuple(fracs):
        x = dict(best["x"], leaf_t=best["x"]["leaf_t"] * (1.0 + fr))
        out = MD.evaluate(MD.design_batch([x]), opts, with_power=False, with_drop=False)
        st, lf = out["stage"], MD.leaf(MD.design_batch([x]), opts)
        rows.append({"leaf_t_frac": fr, "leaf_t_um": x["leaf_t"] * 1e6,
                     "cross_ratio": F(lf["k_cross"] * st["ppa"] / st["k_col"]), "buckling_sf": F(out["leaf_sf"]),
                     "leaf_stress_MPa": F(out["leaf_stress"]) / 1e6, "q_wc_um": F(out["q_wc"]) * 1e6,
                     "q_nom_um": F(out["q_nom"]) * 1e6, "f1_Hz": F(st["f1"])})
    return {"rows": rows, "rules": "cross ratio <= 0.05, buckling SF >= 2", "label": "CALCULATION"}


def repair_monotone(name, best, rows_key, looser, solve, force=False, tol_um=1.0):
    """Re-solve sweep points that a looser point beats (or that failed) from the optimum of every tighter-or-equal
    point: a point whose constraints are looser than another's can never be worse. `looser(a, b)` is True when a's
    constraints are at least as loose as b's; `solve(row, warm)` re-solves row's problem from the warm starts."""
    data = _load(_nm(name, best))
    if data is None or (data.get("repaired") and not force):
        return data
    rows = data[rows_key]
    changed = 0
    for i, ri in enumerate(rows):
        tighter = [rj for j, rj in enumerate(rows) if j != i and rj.get("feasible") and looser(ri, rj)]
        best_t = max([rj["usable_wc_um"] for rj in tighter], default=None)
        if best_t is None:
            continue
        if not ri.get("feasible") or best_t > ri["usable_wc_um"] + tol_um:
            r = solve(ri, [rj["x"] for rj in sorted(tighter, key=lambda r: -r["usable_wc_um"])[:4]])
            if r["feasible"] and (not ri.get("feasible") or r["usable_wc_um"] > ri["usable_wc_um"]):
                for k in [k for k in ri if k not in r]:
                    r[k] = ri[k]
                r["repaired_from_um"] = ri["usable_wc_um"] if ri.get("feasible") else None
                rows[i] = r
                changed += 1
                print(f"{name}: point {i} repaired {ri['usable_wc_um']:.0f} -> {r['usable_wc_um']:.0f} um", flush=True)
    data[rows_key] = rows
    data["repaired"] = True
    data["repaired_points"] = changed
    _save(_nm(name, best), data)
    return data


def repair_pareto(best, force=False):
    opts = opts_from(best["options"])

    def looser(a, b):
        return a["P_max_mW"] >= b["P_max_mW"] - 1e-9 and a["M_max_g"] >= b["M_max_g"] - 1e-9

    def solve(row, warm):
        r = solve_combo(opts, fixed={"Fc": FC_DEFAULT, **FIXED_EXTRA}, n_starts=4, iters=500, polish=2,
                        eps={"P_max": row["P_max_mW"] * 1e-3, "M_max": row["M_max_g"]}, extra_start=warm[0], warm=warm)
        r["P_max_mW"], r["M_max_g"] = row["P_max_mW"], row["M_max_g"]
        return r
    return repair_monotone("pareto", best, "points", looser, solve, force=force)


def repair_fc_sweep(best, force=False):
    def looser(a, b):          # a lower nib force (same friction) is a looser problem
        return abs(a["mu_wc"] - b["mu_wc"]) < 1e-9 and a["Fc"] <= b["Fc"] + 1e-12

    def solve(row, warm):
        o = dict(best["options"], mu_wc=row["mu_wc"])
        ws = [dict(wx, Fc=row["Fc"]) for wx in warm]
        r = solve_combo(opts_from(o), fixed={"Fc": row["Fc"], **FIXED_EXTRA}, n_starts=4, iters=600, polish=2,
                        extra_start=ws[0], warm=ws)
        r["Fc"], r["mu_wc"] = row["Fc"], row["mu_wc"]
        return r
    return repair_monotone("fc_sweep", best, "rows", looser, solve, force=force)
