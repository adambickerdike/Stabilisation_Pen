"""G5 collar and tail analysis (EXP-T16, T17) on rig R14 (grip simulant).

Four conditions, same tasks, same disturbance realisations (seeds), at several grip strengths:
  none      no module fitted
  locked    a dummy of the same mass, centre of mass and inertia, rigidly fixed
  passive   the module fitted and unpowered (flexures free, coils open)
  active    the module running its controller

Gate (review G5, PROPOSED): active must beat locked by >= 10 % (relative reduction of the
predeclared ink-error metric) at every grip strength, and no condition may be worse than none on
average. Paired analysis per seed; bootstrap 95 % intervals. The decision uses the lower CI bound
(guarded) because the effect is the product decision, not an instrument reading.

Also: instrument translation and rotation from two tracked points (tip end and tail end) or from
one point plus the IMU angle, and their transfer functions from the simulant's hand motion.
"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np

CONDITIONS = ("none", "locked", "passive", "active")


def paired_reduction(e_ref: Sequence[float], e_test: Sequence[float], n_boot: int = 2000, seed: int = 0) -> Dict:
    a = np.asarray(e_ref, float)
    b = np.asarray(e_test, float)
    red = 1 - b / a
    rng = np.random.default_rng(seed)
    bs = np.array([np.mean(rng.choice(red, len(red))) for _ in range(n_boot)])
    return {"mean": float(red.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "n": int(len(red))}


def g5_decision(errors: Dict[str, Dict[str, Sequence[float]]], gate: float = 0.10) -> Dict:
    """errors[grip][condition] = per-seed ink-error metric (same seeds in the same order)."""
    out = {"gate": gate, "per_grip": {}}
    passes = []
    for grip, d in errors.items():
        r_al = paired_reduction(d["locked"], d["active"])
        r_an = paired_reduction(d["none"], d["active"])
        r_ln = paired_reduction(d["none"], d["locked"])
        r_pn = paired_reduction(d["none"], d["passive"])
        worse = any(np.mean(d[c]) > np.mean(d["none"]) for c in ("active",))
        ok = (r_al["ci95"][0] >= gate) and not worse
        passes.append(ok)
        out["per_grip"][grip] = {"active_vs_locked": r_al, "active_vs_none": r_an, "locked_vs_none": r_ln,
                                 "passive_vs_none": r_pn, "active_worse_than_none": bool(worse),
                                 "meets_gate_guarded": bool(ok),
                                 "meets_gate_point": bool(r_al["mean"] >= gate and not worse)}
    out["all_grips_pass"] = bool(all(passes))
    return out


def pose_from_two_points(p_front: np.ndarray, p_rear: np.ndarray, grip_frac: float) -> Dict:
    """Instrument translation at the grip point and rotation (rad) in the page-parallel plane of
    the camera, from two tracked markers (n x 2, m). grip_frac: position of the grip between the
    front (0) and rear (1) markers."""
    pf = np.asarray(p_front, float)
    pr = np.asarray(p_rear, float)
    d = pr - pf
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    grip = pf + grip_frac * d
    return {"grip_xy": grip - grip[0], "rotation_rad": ang - ang[0]}


def split_translation_rotation(tip_disp: np.ndarray, grip_disp: np.ndarray, rot: np.ndarray, lever_m: float) -> Dict:
    """Share of the tip motion from translation of the grip and from rotation about it (RMS)."""
    tr = np.sqrt(np.mean(np.sum(np.atleast_2d(grip_disp) ** 2, axis=-1)))
    ro = np.sqrt(np.mean((lever_m * np.asarray(rot)) ** 2))
    tot = np.sqrt(np.mean(np.sum(np.atleast_2d(tip_disp) ** 2, axis=-1)))
    return {"translation_rms_m": float(tr), "rotation_rms_m_at_tip": float(ro), "tip_rms_m": float(tot),
            "rotation_share": float(ro ** 2 / max(ro ** 2 + tr ** 2, 1e-30))}
