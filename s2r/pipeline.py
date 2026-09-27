"""Calibration pipeline in the protocol order: EXP-B03 -> EXP-B05 -> EXP-B01/B02.

Each experiment gets its own bench session (its own draw of systematic errors: R4,
R5 and R1 are different rigs). EXP-B05 consumes the K_f identified by EXP-B03,
because the FRF mass line needs n K_f. The identification functions see only the
datasets; the truth is used afterwards, by score().

Evidence status: SIMULATION (virtual bench) and CALCULATION (identification).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from . import exp_b01b02, exp_b03, exp_b05, twin
from . import truth as tr

PROTOCOL = {"b03": dict(hold=2.0, n_rep=1, n_avg=16, thermal_s=180.0, back_emf=True),
            "b05": dict(n_chirps=10, T_c=10.0, static_F=0.03),   # PROTOCOL: FRFs averaged over 10 chirps
            "b0102": dict(n_rep=1, reduced=False)}

IDENTIFIED_KEYS = [k for g in tr.IDENTIFIED_GROUPS for k in tr.GROUPS[g]]
DT = 25e-6


def run(truth_vals: Dict, seed: int, noise_scale: float = 1.0, settings=None, keep_datasets=False) -> Dict:
    settings = settings or PROTOCOL
    rng = np.random.default_rng(seed)
    full = twin.nominal_plant()
    full.update(truth_vals)
    ds03 = exp_b03.generate(full, rng, noise_scale=noise_scale, **settings["b03"])
    id03 = exp_b03.identify(ds03, rng)
    kf = id03["estimates"]["actuator.Kf"]
    ds05 = exp_b05.generate(full, rng, noise_scale=noise_scale, seed0=seed % 100000 + 11, **settings["b05"])
    e03 = id03["estimates"]
    id05 = exp_b05.identify(ds05, kf["value"], kf["u"], L_hat=e03["actuator.L"]["value"],
                            R20_hat=e03["actuator.R20"]["value"])
    ds12 = exp_b01b02.generate(full, rng, noise_scale=noise_scale, **settings["b0102"])
    id12 = exp_b01b02.identify(ds12, rng, n_boot=50)
    est = {**id03["estimates"], **id05["estimates"], **id12["estimates"]}
    out = {"estimates": _clean(est), "bench_s": {"B03": id03["bench_s"], "B05": id05["bench_s"],
                                                "B01B02": id12["bench_s"]},
           "diag": {"B05": id05["diag"], "B01B02": id12["diag"],
                    "B03": {"coil_dT_max_K": kf.get("coil_dT_max_K"),
                            "protocol_dT_rule_2K_met": kf.get("protocol_dT_rule_2K_met"),
                            "Kf_force_only": kf.get("force_only"), "Kf_emf_only": kf.get("emf_only")}}}
    if keep_datasets:
        out["datasets"] = {"B03": ds03, "B05": ds05, "B01B02": ds12}
    return out


def _clean(est):
    out = {}
    for k, v in est.items():
        out[k] = {kk: (float(vv) if isinstance(vv, (int, float, np.floating)) else vv) for kk, vv in v.items()}
    return out


def m1_truth_value(key: str, value: float) -> float:
    """The value M1 actually uses (the Hall delay is quantised to the 25 us step)."""
    if key == "sensing.hall_delay":
        return round(value / DT) * DT
    return value


def score(estimates: Dict, truth_vals: Dict) -> Dict:
    rows = {}
    for k, e in estimates.items():
        if k not in truth_vals:
            continue
        tv = m1_truth_value(k, truth_vals[k])
        err = e["value"] - tv
        rows[k] = {"true": tv, "est": e["value"], "rel_err": err / tv if tv else float("nan"),
                   "z": err / e["u"] if e.get("u") else float("nan"),
                   "covered95": bool(abs(err) <= e.get("U95", 0.0)), "U95_rel": e.get("U95", 0.0) / abs(tv),
                   "in_declared_range": bool(tr.in_range(k, truth_vals[k]))}
    return rows


def identified_values(estimates: Dict) -> Dict[str, float]:
    return {k: float(v["value"]) for k, v in estimates.items() if k in IDENTIFIED_KEYS}
