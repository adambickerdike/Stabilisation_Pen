"""Ink metrics of touchdown and lift against a rigid pen on the same writing (SIMULATION post-processing).

extra ink   pencil ink more than `tol` from anything the rigid pen drew (diag_touchdown_tails.ink_vs_rigid)
missing ink rigid-pen ink more than `tol` from anything the pencil drew
The diagnostic of sim/pencil/diag_touchdown_tails.py (REQ-PNC-006 status) uses 5 s runs and divides by the
rigid pen's pen-down count (its touchdown bounces are counted as pen-downs).  Here the runs are 5.2 s and the
ink is compared up to T_end = 5.0 s with the other pen's ink allowed until T_end + pad, so a touchdown that the
run's end cuts (the pencil lands a few ms before the rigid pen) is not counted as extra ink.

Decomposition: ink within +-win of a contact transition of either pen is "transition" ink (the touchdown and lift
tails REQ-PNC-006 is about); the rest is "in-stroke" ink, where the pencil's letters sit about 0.14 mm RMS from
the rigid pen's because the skid drags the housing differently (device distortion; docs/pencil_concept.md s10).
With a 0.2 mm tolerance that in-stroke part reacts strongly to 5-10 um changes of the housing path, so it is
reported, and guarded by the robust in-stroke nearest-point RMS, but not optimised.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

TOL = 0.2e-3


def _ink(res):
    C = np.column_stack([res["Cx"], res["Cy"]])
    n = res["contact"] > 0
    step = np.r_[0.0, np.linalg.norm(np.diff(C, axis=0), axis=1)]
    return C, n, step


def transitions(res, t0=0.05):
    """Contact on/off times after t0 (the first 50 ms hold the hand model's start-up transient)."""
    c = res["contact"] > 0
    t = res["t"]
    e = np.flatnonzero(np.diff(c.astype(int)) != 0) + 1
    return t[e][t[e] > t0]


def pen_downs(res, t_end=None, merge=0.0):
    """Touchdown count; merge > 0 merges touchdowns that follow a lift shorter than `merge` s (bounces)."""
    c = res["contact"] > 0
    t = res["t"]
    on = np.flatnonzero(np.diff(c.astype(int)) == 1) + 1
    off = np.flatnonzero(np.diff(c.astype(int)) == -1) + 1
    if t_end is not None:
        on = on[t[on] <= t_end]
    if merge <= 0 or len(on) == 0:
        return int(len(on))
    n = 1
    for a in on[1:]:
        prev_off = off[off < a]
        if len(prev_off) == 0 or t[a] - t[prev_off[-1]] >= merge:
            n += 1
    return n


def ink_vs_rigid(r, rigid, tol=TOL, T_end=5.0, pad=0.2, win=0.03, tol2=0.1e-3):
    """Extra and missing ink of run r against the rigid run (mm), with the transition / in-stroke split."""
    n0 = min(len(r["t"]), len(rigid["t"]))
    t = r["t"][:n0]
    C, n, st = (a[:n0] for a in _ink(r))
    Cr, nr, sr = (a[:n0] for a in _ink(rigid))
    A = n & (t <= T_end)
    Ar = nr & (t <= T_end + pad)
    B = n & (t <= T_end + pad)
    Br = nr & (t <= T_end)
    out = {"pen_downs_rigid": pen_downs(rigid, T_end), "words_rigid": pen_downs(rigid, T_end, merge=0.03),
           "pen_downs": pen_downs(r, T_end), "transitions": int(len(transitions(r)[transitions(r) <= T_end]))}
    if not A.any() or not Ar.any():
        return dict(out, extra_mm=0.0, extra_tr_mm=0.0, extra_in_mm=0.0, missing_mm=0.0, missing_tr_mm=0.0,
                    extra_tr_tight_mm=0.0, rms_nn_instroke_um=float("nan"), ink_mm=0.0, tail_noskid_mm=0.0)
    d_ex = np.full(n0, np.inf)
    d_ex[A] = cKDTree(Cr[Ar]).query(C[A])[0]
    d_ms = np.full(n0, np.inf)
    d_ms[Br] = cKDTree(C[B]).query(Cr[Br])[0]
    tr = np.sort(np.r_[transitions(r, 0.0), transitions(rigid, 0.0)])
    if len(tr):
        idx = np.clip(np.searchsorted(tr, t), 1, len(tr) - 1)
        near = np.minimum(np.abs(t - tr[idx - 1]), np.abs(t - tr[idx])) < win
        if len(tr) == 1:
            near = np.abs(t - tr[0]) < win
    else:
        near = np.zeros(n0, bool)
    ex = A & (d_ex > tol)
    ms = Br & (d_ms > tol)
    ex2 = A & (d_ex > tol2)
    sk = r["skid_contact"][:n0] > 0
    inst = A & ~near
    out.update({
        "ink_mm": float(st[A].sum() * 1e3),
        "extra_mm": float(st[ex].sum() * 1e3),
        "extra_tr_mm": float(st[ex & near].sum() * 1e3),
        "extra_in_mm": float(st[ex & ~near].sum() * 1e3),
        "extra_tr_tight_mm": float(st[ex2 & near].sum() * 1e3),
        "missing_mm": float(sr[ms].sum() * 1e3),
        "missing_tr_mm": float(sr[ms & near].sum() * 1e3),
        "tail_noskid_mm": float(st[A & ~sk].sum() * 1e3),
        "rms_nn_instroke_um": float(np.sqrt(np.mean(d_ex[inst] ** 2)) * 1e6) if inst.any() else float("nan"),
    })
    return out


def diag_metric(r5, rigid5, tol=TOL):
    """Exactly the published diagnostic (sim/pencil/diag_touchdown_tails.py) on 5 s runs: extra and missing ink (mm)
    and the rigid pen's pen-down count used to normalise it."""
    from sim.pencil.diag_touchdown_tails import ink_vs_rigid as diag_ivr
    ex, ms = diag_ivr(r5, rigid5, tol)
    return {"extra_mm": ex, "missing_mm": ms, "pen_downs_rigid": pen_downs(rigid5)}


PER_PD = ("extra_mm", "extra_tr_mm", "extra_in_mm", "extra_tr_tight_mm", "missing_mm", "missing_tr_mm", "tail_noskid_mm")


def per_stroke(rows, norm="pen_downs_rigid"):
    """Sum over seeds, divided by the summed rigid pen-downs (the diagnostic's normalisation) or words."""
    den = max(sum(r[norm] for r in rows), 1)
    out = {k: float(sum(r[k] for r in rows) / den) for k in PER_PD if all(k in r for r in rows)}
    rms = [r["rms_nn_instroke_um"] for r in rows if np.isfinite(r.get("rms_nn_instroke_um", np.nan))]
    out["rms_nn_instroke_um"] = float(np.mean(rms)) if rms else float("nan")
    out["transitions_per_pd"] = float(sum(r["transitions"] for r in rows) / den)
    out["pen_downs_rigid"] = int(sum(r["pen_downs_rigid"] for r in rows))
    out["words_rigid"] = int(sum(r["words_rigid"] for r in rows))
    return out


def contact_events(r, t0=0.05, t_end=5.0, short=0.03):
    """Touchdowns after t0 and the short contact gaps (a lift shorter than `short` s before a touchdown: bounces and
    re-contacts), with each gap's duration and the ball's peak height above the page during it."""
    c = r["contact"] > 0
    t = r["t"]
    on = np.flatnonzero(np.diff(c.astype(int)) == 1) + 1
    off = np.flatnonzero(np.diff(c.astype(int)) == -1) + 1
    on = on[(t[on] > t0) & (t[on] <= t_end)]
    rb = r.info["static"]["r_b"]
    gaps = []
    for a in on:
        po = off[off < a]
        if len(po) and t[po[-1]] > t0 and t[a] - t[po[-1]] < short:
            gaps.append({"t_s": float(t[a]), "gap_ms": float((t[a] - t[po[-1]]) * 1e3),
                         "peak_height_um": float(np.max(r["Cz"][po[-1]:a] - rb) * 1e6)})
    return {"touchdowns": int(len(on)), "short_gaps": gaps}


def travel_stats(r, qlim=None):
    """Stage use in contact: peak feed-forward command, fraction of contact time with the command at >= 95 % of the
    travel limit, the drive voltage saturated or the stage on its stop (as sim/pencil/evaluate.py q_sat_frac)."""
    from sim.pencil.layout import IDX
    qlim = float(r.P[IDX["q_lim"]]) if qlim is None else qlim
    c = r["contact"] > 0
    qr = r.xy("qr1")
    lim = (np.linalg.norm(qr, axis=1) > 0.95 * qlim) | (r["vsat"] > 0) | (r["stop"] > 0)
    qff = np.hypot(r["qff1"], r["qff2"])
    return {"qff_peak_mm": float(qff.max() * 1e3), "qff_peak_contact_mm": float(qff[c].max() * 1e3) if c.any() else 0.0,
            "limit_frac_contact": float(np.mean(lim[c])) if c.any() else 0.0,
            "vsat_frac_contact": float(np.mean(r["vsat"][c] > 0)) if c.any() else 0.0}
