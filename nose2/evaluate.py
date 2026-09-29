r"""The autowrite test grid (SIMULATION, HW1 via autowrite.py) on TEST writers 0-5 and TEST seeds 200-203 only, with the
settings frozen by tuning.py, plus the size and speed limits (CALC, planner) and sensitivities.

Grid: designs x x-height x {no tremor; 0.3, 1, 2 mm at 4, 8, 12 Hz} x 6 writers x 4 seeds.
Metrics per case (autowrite.metrics): ink error to the target letters, letters and words read by the app's recogniser
and reader (and the same recogniser on the clean target: the ceiling), letters per second, coil power, force, travel
use, handle deviation.
"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import Callable, Dict, List, Optional

import numpy as np

from . import TEST_SEEDS, TEST_WRITERS
from . import autowrite as AW
from . import planner as PN
from .tuning import sensor_seed

CONDS = [(8.0, 0.0)] + [(f, a) for a in (0.3e-3, 1.0e-3, 2.0e-3) for f in (4.0, 8.0, 12.0)]


def grid(designs: Dict[str, AW.NoseDesign], st: AW.AWSettings, sizes: Dict[str, List[float]], writers=TEST_WRITERS,
         seeds=TEST_SEEDS, conds=CONDS, progress: Optional[Callable] = None) -> List[Dict]:
    rows = []
    for key, d in designs.items():
        for h in sizes.get(key, [2.5]):
            for w in writers:
                for s in seeds:
                    for f0, amp in conds:
                        c = AW.build(w, s, h, f0, amp, d, st)
                        if not c.plan.ok:
                            r = {"plan_ok": False, "design": key, "w": w, "seed": s, "h_mm": h, "f0": f0, "amp_mm": amp * 1e3}
                        else:
                            r = AW.run(c, sensor_seed(w, s, f0, amp))
                            r["design"] = key
                        rows.append(r)
                        if progress:
                            progress(key, h, w, s, f0, amp, r.get("ink_err_um"), r.get("letters_read"))
    return rows


def summarise(rows: List[Dict]) -> List[Dict]:
    """Means per design, x-height and condition (CALC on SIM rows)."""
    out = []
    keys = sorted({(r["design"], r["h_mm"], r["amp_mm"], r["f0"] if r["amp_mm"] > 0 else 0.0) for r in rows})
    for d, h, a, f in keys:
        sub = [r for r in rows if r["design"] == d and r["h_mm"] == h and r["amp_mm"] == a and (a == 0 or r["f0"] == f)]
        ok = [r for r in sub if r.get("plan_ok")]
        row = {"design": d, "h_mm": h, "amp_mm": a, "f0": f, "n": len(sub), "plan_fail": len(sub) - len(ok)}
        for k in ("ink_err_um", "ink_p95_um", "letters_read", "target_letters_read", "words_read_app", "target_words_read_app",
                  "letters_per_s", "P_coil_W", "F_rms_N", "F_p99_N", "at_travel_limit", "at_force_limit", "q_max_mm",
                  "handle_dev_rms_um", "v_h_mm_s"):
            vals = [r[k] for r in ok if r.get(k) is not None and r[k] == r[k]]
            row[k] = float(np.mean(vals)) if vals else None
        vals = [r["q_max_mm"] for r in ok if r.get("q_max_mm") is not None]
        row["q_max_max_mm"] = float(np.max(vals)) if vals else None
        out.append(row)
    return out


def size_speed_limits(reach_mm: Dict[str, float], writers=TEST_WRITERS, seed: int = TEST_SEEDS[0],
                      h_grid=(1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0), speed_grid=(0.6, 0.8, 1.0, 1.25, 1.5, 2.0),
                      pp: Optional[PN.PlanParams] = None) -> Dict:
    """Largest x-height the plan fits (all writers, nominal speed) and the fastest sweep at 2.5 mm, per reach (CALC)."""
    from .tasks import written_for
    pp = pp or PN.PlanParams()
    out = {}
    for key, R in reach_mm.items():
        hmax = 0.0
        for h in h_grid:
            ok = True
            for w in writers:
                tp = PN.target_from_written(written_for(w, seed, h))
                if not PN.plan(tp, PN.line_speed(tp, pp), R * 1e-3, pp).ok:
                    ok = False
                    break
            if ok:
                hmax = h
        vmax, lps = 0.0, 0.0
        for f in speed_grid:
            ok, rates = True, []
            for w in writers:
                tp = PN.target_from_written(written_for(w, seed, 2.5))
                p = PN.plan(tp, PN.line_speed(tp, pp) * f, R * 1e-3, pp)
                if not p.ok:
                    ok = False
                    break
                rates.append(len(tp.letters) / max(p.meta["t_end_s"] - p.meta["t_start_s"], 1e-6))
            if ok:
                vmax, lps = f, float(np.mean(rates))
        out[key] = {"reach_mm": R, "largest_x_height_mm": hmax, "fastest_speed_factor_at_2.5mm": vmax,
                    "letters_per_s_at_fastest": lps, "label": "CALC (planner feasibility on test writers, seed 200)"}
    return out


def sensitivity(design: AW.NoseDesign, st: AW.AWSettings, writers=TEST_WRITERS, seed: int = TEST_SEEDS[0],
                conds=((8.0, 0.0), (4.0, 1.0e-3), (8.0, 1.0e-3)), h: float = 2.5) -> List[Dict]:
    """One factor at a time (SIM, test writers, seed 200; reported, not used for any choice)."""
    from handwriting import params as PR
    from fusion import sensors as S
    variants = {
        "nominal": {},
        "page sensor 120 Hz, 10 ms (fusion page_120)": {"page": "120"},
        "hand compensates the drags (writer_comp drag)": {"writer_comp": "drag"},
        "servo 40 Hz": {"design": replace(design, servo_hz=40.0)},
        "gel ink, mu 0.095 (LIT CON-13)": {"mu_ball": 0.095},
        "refill force 0.3 N": {"design": replace(design, F_c=0.30)},
        "axial switching delay 20 ms": {"design": replace(design, axial_delay=20e-3)},
        "no axial DOF (ball down for the whole line)": {"design": replace(design, axial=False)},
        "uneven sweep: speed +-30 % at 0.5 Hz": {"speed_mod": (0.3, 0.5)},
        "hand drifts +-1 mm across the line at 0.2 Hz": {"drift": (1.0e-3, 0.2)},
    }
    rows = []
    for name, v in variants.items():
        d = v.get("design", design)
        for w in writers:
            for f0, amp in conds:
                c = AW.build(w, seed, h, f0, amp, d, st, speed_mod=v.get("speed_mod", (0.0, 0.5)), drift=v.get("drift", (0.0, 0.2)))
                if not c.plan.ok:
                    rows.append({"variant": name, "plan_ok": False, "w": w, "f0": f0, "amp_mm": amp * 1e3})
                    continue
                hand = AW.hand_default(v.get("writer_comp", "none"))
                writing = PR.Writing(mu_skid=1e-6 if v.get("writer_comp", "none") == "none" else 0.12,
                                     mu_ball=v.get("mu_ball", 0.15))
                m = AW.run(c, sensor_seed(w, seed, f0, amp), hand=hand, writing=writing, page=v.get("page", "1k"))
                m["variant"] = name
                rows.append(m)
    return rows


