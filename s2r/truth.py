"""Hidden "true" plants for twin experiments.

A truth is a set of M1 plant parameters drawn inside the declared ranges of
config/parameters.yaml (with the declared distribution) or deliberately outside
them. The identification code never receives a truth: it receives only the
recorded datasets. Truth values are revealed to the scoring code after
identification, and each batch is committed with a SHA-256 digest before the
identification runs (results/s2r/*: ``truth_commitment``).

Parameters are grouped by the experiment that measures them. The hand and
sensor groups are part of the truth but are NOT identified by the experiments
built here (EXP-B06, EXP-S01 and EXP-B04 measure them), so they give the
residual gap a calibrated twin keeps until those experiments run.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Dict, List, Optional

import numpy as np

from stabpen import params as sp_params

GROUPS: Dict[str, List[str]] = {
    "B03_actuator": ["actuator.Kf", "actuator.R20", "actuator.L", "actuator.Rth_coil_amb", "actuator.Cth_coil"],
    "B05_stage": ["stage.k_tip", "stage.zeta_open", "stage.m_eq", "sensing.hall_delay", "stage.axial_k",
                  "stage.axial_preload"],
    "B01B02_contact": ["writing.mu_eff", "writing.mu_static_ratio", "writing.stribeck_speed",
                       "writing.paper_stiffness", "friction.x_presliding"],
    "B06_hand": ["hand.grip_stiffness", "hand.grip_damping", "hand.mass", "hand.arm_stiffness", "hand.arm_damping",
                 "hand.normal_stiffness"],
    "S01B04_sensors": ["sensing.opt_noise", "sensing.opt_delay", "sensing.hall_noise_tip", "sensing.imu_delay"],
}
IDENTIFIED_GROUPS = ("B03_actuator", "B05_stage", "B01B02_contact")
NOT_IDENTIFIED_GROUPS = ("B06_hand", "S01B04_sensors")

# Keys the YAML does not declare (M1 hard-codes a default in model.build_params).
EXTRA = {
    "friction.x_presliding": {"value": 1.0e-5, "min": 3.0e-6, "max": 3.0e-5, "dist": "loguniform",
                              "status": "ASSUMPTION", "note": "model.py default 1e-5 m; range chosen here"},
}
# Physical limits for out-of-range draws.
LIMITS = {"stage.zeta_open": (0.003, 0.5), "writing.mu_static_ratio": (1.0, 3.0), "writing.mu_eff": (0.02, 0.6),
          "sensing.hall_delay": (2.5e-5, 6e-4), "stage.axial_preload": (0.05, 0.8)}


def leaf(p: sp_params.Params, key: str) -> Dict:
    if key in EXTRA:
        return EXTRA[key]
    return p.leaf(key)


def nominal(keys=None, p: Optional[sp_params.Params] = None) -> Dict[str, float]:
    p = p or sp_params.load()
    keys = keys or [k for g in GROUPS.values() for k in g]
    return {k: float(leaf(p, k)["value"]) for k in keys}


def _draw_inside(lf, rng):
    lo, hi, dist = float(lf["min"]), float(lf["max"]), lf.get("dist", "uniform")
    if dist == "loguniform":
        return float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
    if dist == "fixed" or lo == hi:
        return float(lf["value"])
    return float(rng.uniform(lo, hi))


def _draw_outside(key, lf, rng, reach=(0.15, 0.5)):
    lo, hi, dist = float(lf["min"]), float(lf["max"]), lf.get("dist", "uniform")
    u = rng.uniform(*reach)
    up = rng.random() < 0.5
    if dist == "loguniform":
        v = hi * (hi / lo) ** u if up else lo / (hi / lo) ** u
    elif up:
        v = hi + u * (hi - lo)
    else:
        # below the range: log extension, so positive quantities stay positive
        v = lo * (lo / hi) ** u if lo > 0 else lo - u * (hi - lo)
    a, b = LIMITS.get(key, (1e-12, np.inf))
    return float(np.clip(v, a, b))


def draw(rng: np.random.Generator, kind: str = "inside", groups=None, frac_outside: float = 0.4,
         p: Optional[sp_params.Params] = None) -> Dict:
    """One hidden plant. kind: 'inside' (declared ranges and distributions) or 'outside'
    (a random fraction of the keys pushed 15-50 % of the range beyond a bound)."""
    p = p or sp_params.load()
    groups = groups or list(GROUPS)
    keys = [k for g in groups for k in GROUPS[g]]
    vals, outside = {}, []
    for k in keys:
        lf = leaf(p, k)
        if kind == "outside" and rng.random() < frac_outside:
            vals[k] = _draw_outside(k, lf, rng)
            outside.append(k)
        else:
            vals[k] = _draw_inside(lf, rng)
    return {"kind": kind, "values": vals, "outside": outside}


def batch(seed: int, n_inside: int, n_outside: int, groups=None) -> List[Dict]:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_inside + n_outside):
        t = draw(rng, "inside" if i < n_inside else "outside", groups)
        t["id"] = f"T{i:02d}"
        out.append(t)
    return out


def commitment(truths) -> str:
    blob = json.dumps(truths, sort_keys=True, default=float).encode()
    return hashlib.sha256(blob).hexdigest()


def in_range(key: str, value: float, p: Optional[sp_params.Params] = None) -> bool:
    p = p or sp_params.load()
    lf = leaf(p, key)
    return float(lf["min"]) <= value <= float(lf["max"])
