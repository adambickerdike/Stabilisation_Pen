"""Evaluate designs on cached cases: fast surrogate measures (tuning searches) and the full HW1 closed loop (finalists).

A design is a dict {'name', 'family', 'params', 'auth'} (estimators.estimate).  Batches are evaluated case by case (each
cached case is loaded once for all designs of the batch).  Every number is SIM (model HW1 with real inputs; surrogate
= the HW1 command path without the nose's reaction on the handle, see servo.py).
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import cases as C
from . import estimators as E
from . import servo as SV


def oracle_cmd(case) -> np.ndarray:
    """Perfect knowledge: -d(t + servo group delay) from the stored truth (handwriting.tracker.oracle_command)."""
    tick_t = case.tick_t
    d = case.truth
    gd = float(case.meta["servo_group_delay_s"])
    return -np.column_stack([np.interp(tick_t + gd, tick_t, d[:, 0]), np.interp(tick_t + gd, tick_t, d[:, 1])])


def command(design: Dict, case, sensor: str = "deltapen"):
    fam = design["family"]
    if fam == "oracle":
        return oracle_cmd(case), {}
    if fam == "none_cmd":
        return np.zeros((len(case.tick_t), 2)), {}
    if fam == "revh_cached":
        return -case.dh_revh(sensor), {}
    st = case.streams(sensor)
    d, info = E.estimate(design, st, case=case, sensor=sensor, horizon=design.get("horizon"))
    return -d, info


def est_error(case, qcmd) -> Dict:
    """Estimation diagnostics in contact: RMS of (truth at the action time + command), the regression gain and lag."""
    A = case.arrays
    gd = float(case.meta["servo_group_delay_s"])
    tick_t = case.tick_t
    d = case.truth
    tgt = np.column_stack([np.interp(tick_t + gd, tick_t, d[:, 0]), np.interp(tick_t + gd, tick_t, d[:, 1])])
    act = A["down_ticks"] > 0.5
    est = -qcmd
    e = (tgt - est)[act]
    return {"est_rms_um": float(np.sqrt(np.mean(np.sum(e ** 2, 1))) * 1e6),
            "truth_rms_um": float(np.sqrt(np.mean(np.sum(tgt[act] ** 2, 1))) * 1e6),
            "out_rms_um": float(np.sqrt(np.mean(np.sum(est[act] ** 2, 1))) * 1e6)}


def eval_batch(designs: Sequence[Dict], specs: Sequence[Dict], sensor: str = "deltapen", log=print,
               diag: bool = False) -> List[Dict]:
    """Surrogate measures of every design on every case: rows {'design', 'case', 'level', 'kind', ...}."""
    rows = []
    pp = SV.pen_params()
    t0 = time.time()
    for s in specs:
        case = C.load_case(s)
        for dz in designs:
            t1 = time.time()
            q, info = command(dz, case, sensor)
            m = SV.fast_measures(case, q, pp)
            m.update({"design": dz["name"], "case": s["id"], "level": s["level"], "kind": s.get("kind"),
                      "note": s["note"], "fold": s["fold"], "sensor": sensor, "t_est_s": time.time() - t1})
            if diag and s.get("kind"):
                m.update(est_error(case, q))
            if isinstance(info, dict):
                for k in ("gate_open", "g_mean", "guard_events"):
                    if k in info:
                        m[k] = info[k]
                if "auth_g" in info:
                    con = case.arrays["down_ticks"] > 0.5
                    m["auth_mean"] = float(np.mean(info["auth_g"][con]))
                if "det_gate" in info:
                    m["gate_open"] = float(np.mean(np.asarray(info["det_gate"]) > 0.5))
            rows.append(m)
        del case
    log(f"[eval] {len(designs)} designs x {len(specs)} cases in {time.time() - t0:.0f} s")
    return rows


def summarize(rows: List[Dict]) -> Dict[str, Dict]:
    """Per design: mean tip-tremor ratio per level (all kinds, and PD / ET), clean-writing change (mean, max)."""
    out: Dict[str, Dict] = {}
    for r in rows:
        d = out.setdefault(r["design"], {"_n": 0})
        d["_n"] += 1
        if r["level"] == "clean":
            d.setdefault("clean_um", []).append(r["clean_change_um"])
        else:
            d.setdefault(f"{r['level']}_ratio", []).append(r["ratio"])
            d.setdefault(f"{r['level']}_{r['kind']}_ratio", []).append(r["ratio"])
            d.setdefault(f"{r['level']}_mm", []).append(r["tip_tremor_mm"])
            d.setdefault(f"{r['level']}_bb", []).append(r["bb_ratio_held"])
            d.setdefault(f"{r['level']}_rheld", []).append(r["ratio_held"])
        for k in ("gate_open", "auth_mean"):
            if k in r and r["level"] in ("severe", "clean"):
                d.setdefault(f"{k}_{r['level']}", []).append(r[k])
    for name, d in out.items():
        for k in list(d.keys()):
            if isinstance(d[k], list):
                v = np.array(d[k], float)
                if k == "clean_um":
                    d["clean_um_mean"] = float(np.nanmean(v))
                    d["clean_um_max"] = float(np.nanmax(v))
                    del d[k]
                else:
                    d[k] = float(np.nanmean(v))
    return out


def table(summary: Dict[str, Dict], keys=("severe_ratio", "severe_bb", "edge_ratio", "edge_bb", "moderate_rheld",
                                          "mild_rheld", "clean_um_mean", "clean_um_max", "severe_PD_ratio",
                                          "severe_ET_ratio", "gate_open_severe", "auth_mean_severe",
                                          "auth_mean_clean")) -> str:
    lines = ["design".ljust(34) + " ".join(k[:13].rjust(13) for k in keys)]
    for name, d in summary.items():
        lines.append(name[:34].ljust(34) + " ".join(
            (f"{d[k]:13.3f}" if isinstance(d.get(k), float) else " " * 12 + "-") for k in keys))
    return "\n".join(lines)
