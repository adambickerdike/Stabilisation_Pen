r"""Choosing the recommended mechanism from the optimisation sweep (CALC; a fixed rule, applied mechanically).

Rule (written when the optimisation log of the gimbal candidates had been seen, before the sweep's results were read in
full and before any autowrite test run; it states the project's preferences and is applied as written).  It was revised
once, after that log: the first version took the smaller handle whenever it was feasible; R2 now lets J choose the
handle, because at the same travel the 24 mm designs have far lower coil loss (more heat margin) for about 3 g more.
The first version's choice is reported beside it ("smallest_handle_first"), as is the choice without R3.
  R1 Travel.  The guaranteed travel (minimum over 35-75 deg tilt and every direction) must hold the autowrite reach of
     the synthetic writers' own letter size, x-height 2.5 mm (their styles span 2.0-3.2 mm, aiguide), for the worst
     TUNING writer at the nominal sweep speed (tasks.autowrite_reach), plus 1.0 mm kept free for tremor (the starting
     value of the reach margin that tuning.py then sets).  Rounded up to the sweep's 1 mm grid.
  R2 Mechanism and handle.  Among the feasible designs at that travel, in either handle (22 mm as Rev H, or 24 mm, the
     Rev J limit where held, docs/revJ_plan.md section 6), the lowest J = P_autowrite + 4 W/kg x added mass (the
     mu_m = 4 runs).  Only candidates whose every stage is sized from geometry are chosen from (C1, C1+, C1S, C2, C4a);
     C3's fine stage uses assumed values (designs._add_fine) and is reported beside them, not chosen (added before
     the final optimisation run, when that model's limits were found).
  R3 Standard parts.  If the best flat-part design (gimbal_radial, gimbal_axial: flat coils and standard magnet blocks,
     as Rev H) is within 25 % of that J, it is chosen instead (easier to make and to inspect).
  R4 If no candidate is feasible at the required travel, the largest feasible travel is taken and the shortfall is
     reported.
Feasible means every penalty of designs._common_out is zero: travel, handle bore, parasitic modes >= 3 x the servo
bandwidth, peak force within the 3.7 V / 1.5 A drive, flexure strain within fatigue and static limits, coil temperature
rise <= 20 K while autowriting with 1 mm rms tremor, actuator within 100 mm of the tip.
"""
from __future__ import annotations

import math
from typing import Dict, List

FLAT = ("gimbal_radial", "gimbal_axial")
SELECTABLE = ("gimbal_radial", "gimbal_axial", "gimbal_sphere", "dual_plane", "xy_wire")
MU_M = 4.0
FLAT_TOL = 0.25
X_GRID_MM = (4.0, 5.0, 6.0, 7.0, 8.0)


def required_travel(reach_rows: List[Dict], h_mm: float = 2.5, reserve_mm: float = 1.0) -> Dict:
    """R1 from tasks.autowrite_reach rows (CALC)."""
    sub = [r["reach_mm"] for r in reach_rows if r["x_height_mm"] == h_mm and r["speed_factor"] == 1.0]
    need = max(sub) + reserve_mm
    grid = [x for x in X_GRID_MM if x >= need - 1e-9]
    return {"x_height_mm": h_mm, "worst_writer_reach_mm": max(sub), "reserve_mm": reserve_mm, "need_mm": need,
            "x_req_mm": grid[0] if grid else X_GRID_MM[-1], "capped": not grid}


def J(row: Dict) -> float:
    return row["P_autowrite_W"] + MU_M * row["mass_added_g"] * 1e-3


def _pick(c: List[Dict], flat_pref: bool = True):
    top = min(c, key=J)
    flat = [r for r in c if r["kind"] in FLAT]
    if flat_pref and top["kind"] not in FLAT and flat:
        fb = min(flat, key=J)
        if J(fb) <= (1.0 + FLAT_TOL) * J(top):
            return fb, f"flat-part design within {FLAT_TOL:.0%} of the lowest J ({J(fb):.4f} vs {J(top):.4f})"
    return top, "lowest J" + ("" if not flat else f" (best flat-part design J {J(min(flat, key=J)):.4f}, "
                                                   f"{J(min(flat, key=J)) / J(top) - 1:+.0%})")


def choose(best: List[Dict], x_req_mm: float, bores=("22", "24"), flat_pref: bool = True, small_handle_first: bool = False) -> Dict:
    """Apply R2-R4 to the sweep's best rows (optimise.sweep()['best'])."""
    def cands(x, bore):
        return [r for r in best if r.get("feasible") and abs(r["x_min_req_mm"] - x) < 1e-6 and r["bore"] == bore
                and abs(r["mu_m"] - MU_M) < 1e-9 and r["kind"] in SELECTABLE]
    log = []
    xs = [x for x in X_GRID_MM if x <= x_req_mm + 1e-9][::-1]
    for x in xs:
        groups = [[b] for b in bores] if small_handle_first else [list(bores)]
        for g in groups:
            c = [r for b in g for r in cands(x, b)]
            log.append({"x_mm": x, "bores": g, "n_feasible": len(c), "kinds": sorted({r["kind"] for r in c})})
            if not c:
                continue
            pick, why = _pick(c, flat_pref)
            per_kind = {}
            for r in c:
                k = (r["kind"], r["bore"])
                if k not in per_kind or J(r) < J(per_kind[k]):
                    per_kind[k] = r
            return {"design": pick, "x_req_mm": x_req_mm, "x_chosen_mm": x, "handle_od": 22.0 if pick["bore"] == "22" else 24.0,
                    "shortfall_mm": max(0.0, x_req_mm - x), "why": why, "J": J(pick),
                    "per_kind": {f"{k[0]}@{k[1]}": {"J": J(v), "P_autowrite_W": v["P_autowrite_W"], "mass_added_g": v["mass_added_g"],
                                                    "Km_tip": v["Km_tip"], "m_eff_tip_g": v["m_eff_tip_g"],
                                                    "dT_coil_K": v.get("dT_coil_K")} for k, v in per_kind.items()},
                    "search_log": log}
    return {"design": None, "x_req_mm": x_req_mm, "search_log": log}


def alternatives(best: List[Dict], x_req_mm: float) -> Dict:
    """The choice under the other rules (reported, not used)."""
    out = {}
    for name, kw in (("smallest_handle_first", {"small_handle_first": True}), ("no_flat_preference", {"flat_pref": False})):
        c = choose(best, x_req_mm, **kw)
        d = c.get("design")
        out[name] = None if d is None else {"kind": d["kind"], "handle_od": c["handle_od"], "x_chosen_mm": c["x_chosen_mm"],
                                            "P_autowrite_W": d["P_autowrite_W"], "mass_added_g": d["mass_added_g"], "J": c["J"],
                                            "dT_coil_K": d.get("dT_coil_K")}
    return out


def best_per_cell(best: List[Dict]) -> List[Dict]:
    """Lowest-J feasible design per (kind, bore, travel, mu_m) over the seeds, plus the cells with none (CALC)."""
    out = {}
    for r in best:
        k = (r["kind"], r["bore"], r["x_min_req_mm"], r["mu_m"])
        cur = out.get(k)
        if r.get("feasible"):
            if cur is None or not cur.get("feasible") or J(r) < J(cur):
                out[k] = r
        elif cur is None:
            out[k] = r
    return [out[k] for k in sorted(out)]


def fmt(x: float, nd: int = 3) -> float:
    return float(round(x, nd)) if isinstance(x, (int, float)) and math.isfinite(x) else x
