r"""Travel sizing from the tasks (CALC on synthetic writers; every writer is SYNTHETIC, aiguide).

Four tasks set the tip travel the nose needs (radius at the ball, in the page plane):

1. Tremor cancellation.  The tip must undo the hand's tremor at the ink: up to the tremor amplitude at the tip
   (0.3-2 mm peak at the hand, the Rev H grid).  Rev H's sweep (docs/opt_inertial.md 5.3, SIM) found that +-1.5-2 mm
   captures most of the benefit with perfect knowledge of 1-2 mm tremor and an 80 Hz servo; the peak excursion of the
   tremor path is the (upper-bound) requirement computed here (the tremor model's own peaks, with its 30 % amplitude
   modulation and harmonic).
2. Guided letter shaping.  Partial guidance pulls the ink toward a copybook letter; the distance to pull is the
   learner's shape error, 0.1-0.35 x-height in the practice study (handwriting/practice.py error model: warp 0.14
   x-height, baseline 0.12, size 15 %).  The requirement is the 99th percentile of that error on tuning writers.
3. Autowrite.  The nose draws the whole letter while the hand sweeps.  planner.min_reach gives the reach the text
   needs at each x-height and sweep speed; tremor adds its own excursion on top (the page-sensor loop cancels the
   hand's tremor while drawing).
4. Delayed ink.  The ink trails the hand by tau (100-200 ms) so that each stroke can be smoothed with look-ahead:
   the tip must reach from where the hand is to where it was tau ago, |p(t) - p(t - tau)|, on every inked sample.
   Computed on the synthetic writers (their speeds 20-34 mm/s, aiguide) and scaled to the adult speeds of LIT CON-20
   (phrase writing 30.5 mm/s mean on paper, loops 104.6 mm/s).
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np

from . import TUNE_SEEDS, TUNE_WRITERS, ensure_paths
from . import planner as PN

ensure_paths()
from handwriting import writers as W  # noqa: E402
from stabpen import signals as sg  # noqa: E402

TEXT = W.ET_SENTENCE                 # "return library books by friday" (the handwriting/aiprior studies' sentence)
XHEIGHTS_MM = (2.5, 3.0, 3.5, 4.0)
SPEED_FACTORS = (0.6, 1.0, 1.4)
TAUS_S = (0.05, 0.10, 0.15, 0.20)


def written_for(w: int, seed: int, h_mm: float, text: str = TEXT, dt: float = 1e-3):
    wr = W.writer(w, x_height_mm=h_mm)
    return wr.write(text, dt=dt, seed=seed)


# ------------------------------------------------------------------ 1. tremor
def tremor_peaks(amps=(0.3e-3, 1.0e-3, 2.0e-3), f0s=(4.0, 6.0, 8.0, 10.0, 12.0), seeds=TUNE_SEEDS, T=12.0) -> Dict:
    """Peak |tremor| of the project's tremor model (hand side), per amplitude (CALC)."""
    t = np.arange(0.0, T, 1e-3)
    out = {}
    for a in amps:
        pk = []
        for f0 in f0s:
            for s in seeds:
                d = W.tremor_path(t, f0, a, s, 100)
                pk.append(float(np.max(np.hypot(d[:, 0], d[:, 1]))))
        out[f"{a * 1e3:g}"] = {"peak_p50_mm": float(np.median(pk) * 1e3), "peak_max_mm": float(np.max(pk) * 1e3)}
    return out


# ------------------------------------------------------------------ 2. guidance
def guidance_error(writers=TUNE_WRITERS, seeds=TUNE_SEEDS, h_mm: float = 3.0) -> Dict:
    """Distance from the dysgraphia-like learner's letters to the copybook letters (the pull a partial guidance must
    make), 99th percentile over pen-down points (CALC on the practice study's error model, handwriting/writers.py)."""
    from scipy.spatial import cKDTree
    prof = W.dysgraphia_profile()
    d_all = []
    for w in writers:
        for s in seeds:
            plan = W.error_plan(W.PRACTICE_SENTENCE, prof, s)
            wr = W.writer(w, x_height_mm=h_mm)
            learner = wr.write(W.PRACTICE_SENTENCE, dt=1e-3, seed=2000 + w, extra_warp=plan["warp"],
                               size_factors=plan["size"], baseline_offsets=plan["baseline"])
            clean = wr.write(W.PRACTICE_SENTENCE, dt=1e-3, seed=2000 + w)
            for La, Lb in zip(learner.letters, clean.letters):
                A = np.vstack([PN._resample(np.asarray(p), 20e-6) for p in La.polylines])
                B = np.vstack([PN._resample(np.asarray(p), 20e-6) for p in Lb.polylines])
                # anchor at the letter's first point (as the practice study does)
                A = A - A[0] + B[0]
                d, _ = cKDTree(B).query(A)
                d_all.append(d)
    d = np.concatenate(d_all)
    return {"h_mm": h_mm, "p50_mm": float(np.percentile(d, 50) * 1e3), "p95_mm": float(np.percentile(d, 95) * 1e3),
            "p99_mm": float(np.percentile(d, 99) * 1e3), "max_mm": float(d.max() * 1e3)}


# ------------------------------------------------------------------ 3. autowrite
def autowrite_reach(writers=TUNE_WRITERS, seeds=TUNE_SEEDS[:1], xh=XHEIGHTS_MM, speeds=SPEED_FACTORS,
                    pp: PN.PlanParams = None) -> List[Dict]:
    """Smallest reach the planner needs, per writer, x-height and sweep speed (CALC)."""
    pp = pp or PN.PlanParams()
    rows = []
    for w in writers:
        for s in seeds:
            for h in xh:
                wr = written_for(w, s, h)
                tp = PN.target_from_written(wr)
                v0 = PN.line_speed(tp, pp)
                for f in speeds:
                    r = PN.min_reach(tp, v0 * f, pp)
                    n_let = len(tp.letters)
                    rows.append({"writer": w, "seed": s, "x_height_mm": h, "speed_factor": f, "v_h_mm_s": v0 * f * 1e3,
                                 "reach_mm": r["reach_mm"], "exc_rms_mm": r.get("exc_rms_mm"),
                                 "letters_per_s": n_let / r["t_end_s"] if r.get("t_end_s") else None,
                                 "path_down_mm": tp.length_down * 1e3, "path_up_mm": tp.length_up * 1e3})
    return rows


# ------------------------------------------------------------------ 4. delayed ink
def delayed_ink(writers=TUNE_WRITERS, seeds=TUNE_SEEDS[:2], taus=TAUS_S, h_mm: float = 3.0) -> Dict:
    """Reach for ink that trails the hand by tau: |p(t) - p(t - tau)| on inked samples (CALC), on the synthetic
    writers' own speeds and rescaled to an adult phrase-writing speed of 30.5 mm/s (LIT CON-20)."""
    res = {}
    for tau in taus:
        e_all, e_scaled, cut = [], [], []
        for w in writers:
            for s in seeds:
                wr = written_for(w, s, h_mm)
                it = wr.intended
                dt = float(it.t[1] - it.t[0])
                k = int(round(tau / dt))
                p = it.xy
                dn = np.asarray(it.pen_down, bool)
                ink = dn[:-k] if k > 0 else dn
                e = np.hypot(*(p[k:] - p[:-k]).T)[ink]
                e_all.append(e)
                v = np.hypot(*np.gradient(p, dt, axis=0).T)[dn]
                scale = 30.5e-3 / max(float(np.mean(v)), 1e-9)
                # the same path at the adult mean speed: the delay covers scale x more path
                ks = int(round(tau * scale / dt))
                if ks > 0 and ks < len(p):
                    e_scaled.append(np.hypot(*(p[ks:] - p[:-ks]).T)[dn[:-ks]])
                # share of inked samples whose stroke ends (pen lifts) before the delayed ink finishes it
                up_ahead = np.zeros(len(dn), bool)
                up_ahead[:-k] = ~dn[k:]
                cut.append(float(np.mean(up_ahead[dn])))
        e = np.concatenate(e_all)
        es = np.concatenate(e_scaled) if e_scaled else e
        res[f"{tau * 1e3:.0f}ms"] = {
            "synthetic_p50_mm": float(np.percentile(e, 50) * 1e3), "synthetic_p95_mm": float(np.percentile(e, 95) * 1e3),
            "synthetic_p99_mm": float(np.percentile(e, 99) * 1e3), "synthetic_max_mm": float(e.max() * 1e3),
            "adult_speed_p95_mm": float(np.percentile(es, 95) * 1e3), "adult_speed_p99_mm": float(np.percentile(es, 99) * 1e3),
            "adult_speed_max_mm": float(es.max() * 1e3),
            "inked_share_lifted_before_finish": float(np.mean(cut)),
            "straight_line_bound_mm": {"30.5 mm/s (CON-20 phrase)": 30.5 * tau, "104.6 mm/s (CON-20 loops)": 104.6 * tau}}
    return res


def requirement_table(tr: Dict, gd: Dict, aw: List[Dict], di: Dict) -> List[Dict]:
    """Travel each task needs (radius at the ball, mm; CALC)."""
    rows = []
    for a, v in tr.items():
        rows.append({"task": f"tremor cancellation, {a} mm at the hand", "travel_mm": v["peak_max_mm"],
                     "basis": "peak of the tremor model (30 % AM, 15 % harmonic), 4-12 Hz, tuning seeds"})
    rows.append({"task": f"guided shaping, dysgraphia-like learner, {gd['h_mm']:g} mm letters", "travel_mm": gd["p99_mm"],
                 "basis": "p99 distance of the learner's letters to the copybook letters"})
    for h in sorted({r["x_height_mm"] for r in aw}):
        sub = [r["reach_mm"] for r in aw if r["x_height_mm"] == h and r["speed_factor"] == 1.0]
        if sub:
            rows.append({"task": f"autowrite, {h:g} mm x-height, no tremor", "travel_mm": float(np.max(sub)),
                         "basis": "planner minimum reach, worst tuning writer, nominal sweep speed"})
    for k, v in di.items():
        rows.append({"task": f"delayed ink {k}", "travel_mm": v["synthetic_p99_mm"],
                     "basis": "p99 of |p(t) - p(t - tau)| on inked samples, synthetic writers (20-34 mm/s)"})
        rows.append({"task": f"delayed ink {k} at adult phrase speed", "travel_mm": v["adult_speed_p99_mm"],
                     "basis": "the same paths rescaled to 30.5 mm/s mean (LIT CON-20)"})
    return rows


def autowrite_kinematics(writers=TUNE_WRITERS, seed: int = TUNE_SEEDS[0], h_mm: float = 3.0, pp: PN.PlanParams = None,
                         speed_factor: float = 1.0) -> Dict:
    """Nose kinematics while autowriting (the planned excursion q = drawn point - hand), per axis: rms and p99.9 of the
    displacement and the acceleration, and the inking share (CALC on the smoothed plans of tuning writers)."""
    pp = pp or PN.PlanParams()
    qs, acc, ink, lifts = [], [], [], []
    for w in writers:
        wr = written_for(w, seed, h_mm)
        tp = PN.target_from_written(wr)
        v = PN.line_speed(tp, pp) * speed_factor
        r = PN.min_reach(tp, v, pp)
        p = PN.plan(tp, v, r["reach_mm"] * 1e-3 + 0.2e-3, pp)
        q = p.xy - p.hand
        m = (p.t >= p.meta["t_start_s"]) & (p.t <= p.meta["t_end_s"])
        a = np.gradient(np.gradient(p.xy, pp.dt, axis=0), pp.dt, axis=0)       # the hand sweeps steadily: a_q = a_xy
        qs.append(q[m]); acc.append(a[m]); ink.append(p.down[m])
        dm = p.down[m].astype(int)
        lifts.append(float(np.sum(np.diff(dm) == -1)) / max(float(p.meta["t_end_s"] - p.meta["t_start_s"]), 1e-9))
    q = np.vstack(qs); a = np.vstack(acc); d = np.concatenate(ink)
    return {"h_mm": h_mm, "q_rms_axis_mm": float(np.max(np.sqrt(np.mean(q ** 2, axis=0))) * 1e3),
            "q_p999_mm": float(np.percentile(np.hypot(*q.T), 99.9) * 1e3),
            "a_rms_axis_m_s2": float(np.max(np.sqrt(np.mean(a ** 2, axis=0)))),
            "a_p999_m_s2": float(np.percentile(np.hypot(*a.T), 99.9)), "ink_share": float(np.mean(d)),
            "pen_lifts_per_s": float(np.mean(lifts)), "pen_lifts_per_s_max": float(np.max(lifts)),
            "label": "CALC on smoothed plans (planner.PlanParams: 45 mm/s drawing, 90 mm/s pen-up, 6 Hz smoothing), tuning writers"}
