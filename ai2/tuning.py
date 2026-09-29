"""Every design choice of task 1 (delayed ink) and of the causal gated tracker, on TUNING data only, with the rules
written here before any test run (tuning writers 100-103, seed 300; seed 301 confirms the choice).

Stage D0  the tremor smoother (open loop): the RTS model settings.  Metric: the time-aligned tremor residual (true
          disturbance minus estimate at the smoothed time, pen-down samples) averaged over 1-2 mm at 6-10 Hz and the
          lags 0, 25 and 50 ms.  Rule D0: the candidate with the lowest metric.  The windowed zero-phase smoother
          (the app's clean copy on a sliding window) is scored on the same data for information.
Stage D1  the tremor-line detector's gate (hysteresis on the running peak-to-floor ratio).  Rule D1: among the
          candidates whose gate never opens on any tuning writer's tremor-free writing, the one with the largest open
          fraction at 1-2 mm (mean over 6-10 Hz); ties go to the higher r_on.
Stage D2  the lag policy per nose travel (closed loop, model HW1).  Rules (against the Rev H tracker on the same data):
            R1  tremor-free writing: false correction <= the Rev H tracker's + 2 um (the gate must keep the pen the
                Rev H pen when there is no tremor line);
            R2  0.3 mm tremor: ink error <= 1.02 x the Rev H tracker's at each frequency (mean over writers);
            R3  letters read >= the Rev H tracker's - 0.01 at each frequency and amplitude (mean over writers);
            R4  coverage of the intended path (ink within 0.3 mm) >= the Rev H tracker's - 0.01 at each condition
                (the delay must not lose ink at stroke ends);
          choice: the lowest mean ink error at 1-2 mm (6-10 Hz) among the settings that pass R1-R4.  The causal gated
          tracker (lag 0) is a candidate like the others.
"""
from __future__ import annotations

import copy
import time
from itertools import product
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import F0S, AMPS, TUNE_SEEDS, TUNE_WRITERS, ensure_paths
from . import common as C
from . import delayed as DL
from . import smoothers as SM

ensure_paths()
from aiprior import core as CO  # noqa: E402
from aiprior import study as SD  # noqa: E402
from handwriting import params as PR  # noqa: E402

D0_LAGS = (0.0, 0.025, 0.05, 0.1)


def d0_candidates() -> List[Dict]:
    out = []
    for tau, qt in product((0.5, 1.0, 2.0), (1e-9, 3e-9)):
        out.append({"tau_decay": tau, "qt": qt, "qh": qt / 3.0, "tau_w": 0.4})
    out.append({"tau_decay": 0.21, "qt": 1e-8, "qh": 3e-9, "tau_w": 0.124})       # the first exploration setting
    return out


def d1_candidates() -> List[Dict]:
    return [{"r_on": 5.0, "r_off": 2.5, "t_on": 0.5, "t_off": 1.0}, {"r_on": 4.5, "r_off": 2.5, "t_on": 1.0, "t_off": 1.0},
            {"r_on": 4.0, "r_off": 2.5, "t_on": 1.0, "t_off": 1.0}, {"r_on": 5.5, "r_off": 3.0, "t_on": 0.5, "t_off": 1.0},
            {"r_on": 4.5, "r_off": 3.0, "t_on": 0.5, "t_off": 0.5}]


def d2b_candidates() -> List[Dict]:
    """Stage D2b (added after D2 found no setting passing R3/R4 at 10 Hz 0.3 mm, where the gate opens on a small line
    and the listening estimate distorts letters): an amplitude gate on the detector's line amplitude, crossed with the
    lag settings.  Same rules R1-R4."""
    out = []
    for (alo, ahi) in ((0.0, 0.0), (0.15e-3, 0.35e-3), (0.25e-3, 0.45e-3), (0.35e-3, 0.6e-3)):
        for lam in (0.0, 0.025, 0.05):
            out.append({"lam_max": lam, "alpha": 1.0, "beta": 6.0, "amp_lo": alo, "amp_hi": ahi})
    return out


def d2_candidates() -> List[Dict]:
    out = [{"lam_max": 0.0, "alpha": 0.5, "beta": 3.0}]
    for lam, a, b in product((0.025, 0.05, 0.075), (0.5, 1.0), (3.0, 6.0)):
        out.append({"lam_max": lam, "alpha": a, "beta": b})
    return out


def key(c: Dict) -> str:
    return "_".join(f"{k}{v:g}" if isinstance(v, (int, float)) else f"{k}{v}" for k, v in sorted(c.items()))


def conditions(clean: bool = True):
    out = [(f, a) for f in F0S for a in AMPS]
    return out + ([(0.0, 0.0)] if clean else [])


def scenario(wr, f0, amp, seed):
    return CO.make_scenario(wr, f0, amp, seed) if amp > 0 else CO.make_clean_scenario(wr)


# ------------------------------------------------------------------ open-loop residual
def residual_um(sc: CO.Scenario, t_out: np.ndarray, D: np.ndarray, lags: Sequence[float], t_min: float = 1.0) -> List[float]:
    """Time-aligned tremor residual |d(s) - D(s)| over pen-down samples, s = t + delta - lag, per lag (um RMS)."""
    clean = sc.wr.su.clean["revH"]
    n = min(len(sc.neutral.t), len(clean.t))
    tr = sc.neutral.t[:n]
    d = sc.neutral.handle[:n] - clean.handle[:n]
    con = (sc.neutral.contact[:n] > 0.5).astype(float)
    delta = PR.servo_group_delay(sc.pen)
    out = []
    for i, lag in enumerate(lags):
        s = t_out + delta - lag
        m = (s > t_min) & (s < tr[-1])
        dd = np.column_stack([np.interp(s[m], tr, d[:, 0]), np.interp(s[m], tr, d[:, 1])])
        c = np.interp(s[m], tr, con) > 0.5
        e = dd - D[m, i]
        out.append(float(np.sqrt(np.mean(np.sum(e[c] ** 2, axis=1))) * 1e6) if c.any() else float("nan"))
    return out


# ------------------------------------------------------------------ stage D0 + D1 (one job per writer)
def d01_job(job: Dict) -> Dict:
    wr = CO.Writer(job["writer"])
    seed = job["seed"]
    rows = []
    for f0, amp in conditions():
        sc = scenario(wr, f0, amp, seed)
        delta = PR.servo_group_delay(sc.pen)
        r = {"writer": wr.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "rts": {}, "det": {}}
        for c in job["d0"]:
            p = dict(DL.TREMOR_DEFAULTS); p.update(c)
            out = SM.rts_fixed_lag(sc.streams, p, D0_LAGS, delta, out_every=8)
            r["rts"][key(c)] = residual_um(sc, out["t"], out["tremor"], D0_LAGS)
        det0 = SM.detector(sc.streams, dict(DL.DET_DEFAULTS, every=0.05))
        dopen = dict(det0); dopen["gate"] = np.ones_like(det0["gate"])
        w = SM.window_smoother(sc.streams, dopen, D0_LAGS, delta, out_every=8)
        r["window"] = residual_um(sc, w["t"], w["tremor"], D0_LAGS)
        r["ratio"] = det0["ratio"].tolist()
        r["det_t"] = det0["t"].tolist()
        rows.append(r)
    return {"writer": wr.w, "rows": rows}


def hysteresis(ratio: np.ndarray, every: float, r_on, r_off, t_on, t_off) -> np.ndarray:
    n_on = max(1, int(round(t_on / every))); n_off = max(1, int(round(t_off / every)))
    stt = False; c_on = 0; c_off = 0
    out = np.zeros(len(ratio))
    for i, x in enumerate(ratio):
        if not stt:
            c_on = c_on + 1 if x > r_on else 0
            if c_on >= n_on:
                stt = True; c_off = 0
        else:
            c_off = c_off + 1 if x < r_off else 0
            if c_off >= n_off:
                stt = False; c_on = 0
        out[i] = stt
    return out


def select_d0(outs: List[Dict], cands: List[Dict]) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    table = {}
    for c in cands:
        k = key(c)
        big = [np.mean(r["rts"][k][:3]) for r in rows if r["amp_mm"] >= 1.0]
        small = [np.mean(r["rts"][k][:3]) for r in rows if 0 < r["amp_mm"] < 0.5]
        clean = [np.mean(r["rts"][k][:3]) for r in rows if r["amp_mm"] == 0]
        table[k] = {"J_1_2mm_um": float(np.mean(big)), "at_0p3mm_um": float(np.mean(small)),
                    "tremor_free_leak_um": float(np.mean(clean)),
                    "by_lag_1_2mm_um": [float(np.mean([r["rts"][k][i] for r in rows if r["amp_mm"] >= 1.0])) for i in range(len(D0_LAGS))]}
    win = {"by_lag_1_2mm_um": [float(np.mean([r["window"][i] for r in rows if r["amp_mm"] >= 1.0])) for i in range(len(D0_LAGS))],
           "tremor_free_leak_um": float(np.mean([np.mean(r["window"][:3]) for r in rows if r["amp_mm"] == 0]))}
    best = min(table, key=lambda k: table[k]["J_1_2mm_um"])
    return {"rule": "D0: lowest mean residual over 1-2 mm, 6-10 Hz, lags 0/25/50 ms", "table": table, "chosen_key": best,
            "window_smoother": win, "lags_s": list(D0_LAGS)}


def select_d1(outs: List[Dict], cands: List[Dict], every: float = 0.05, t_min: float = 0.0) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    table = {}
    for c in cands:
        k = key(c)
        opens = {}
        for r in rows:
            g = hysteresis(np.asarray(r["ratio"]), every, **c)
            opens.setdefault((r["f0"], r["amp_mm"]), []).append(float(g.mean()) if len(g) else 0.0)
        clean_open = max(opens.get((0.0, 0.0), [0.0]))
        big = float(np.mean([np.mean(v) for (f, a), v in opens.items() if a >= 1.0]))
        small = {f"{f:g}Hz": float(np.mean(v)) for (f, a), v in opens.items() if 0 < a < 0.5}
        table[k] = {"clean_max_open": clean_open, "open_1_2mm": big, "open_0p3mm": small, "passes": clean_open == 0.0,
                    **c}
    ok = [k for k in table if table[k]["passes"]]
    best = max(ok, key=lambda k: (table[k]["open_1_2mm"], table[k]["r_on"])) if ok else None
    return {"rule": "D1: gate never open on tuning tremor-free writing; then the largest open fraction at 1-2 mm",
            "table": table, "chosen_key": best, "chosen": next((c for c in cands if key(c) == best), None)}


# ------------------------------------------------------------------ stage D2 (closed loop)
def d2_job(job: Dict) -> Dict:
    wr = CO.Writer(job["writer"])
    seed = job["seed"]
    base = DL.DelayCfg(tremor=job["tremor"], det=job["det"])
    pens = {3: DL.pen_travel(3.0), 6: DL.pen_travel(6.0)}
    rows = []
    for f0, amp in job.get("conds") or conditions():
        sc = scenario(wr, f0, amp, seed)
        ests = {}
        r = {"writer": wr.w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "v": {}}
        rt = CO.run_cmd(sc, -sc.dh)
        m = SD.metrics(sc, rt, travel=False)
        m["coverage"] = DL.coverage(sc, rt)
        if amp == 0:
            m["false_correction_um"] = DL.ink_timeline_error(sc, rt, np.zeros(sc.n_ticks), sc.neutral)
        r["v"]["tracker"] = m
        det = None
        handle_out = None
        for c in job["cands"]:
            ak = (c.get("amp_lo", 0.0), c.get("amp_hi", 0.0))
            if ak not in ests:
                cfg0 = copy.copy(base)
                cfg0.amp_lo, cfg0.amp_hi = ak
                if det is None:
                    e0 = DL.estimates(sc, cfg0)
                    det, handle_out = e0["det"], e0["handle_out"]
                e = DL.regate(e0, cfg0)
                ests[ak] = (e, DL.observables(sc, e))
            est, obs = ests[ak]
            for travel in (3, 6):
                if c["lam_max"] == 0 and travel == 6:
                    continue
                cfg = copy.copy(base)
                cfg.lam_max, cfg.alpha, cfg.beta = c["lam_max"], c["alpha"], c["beta"]
                cfg.amp_lo, cfg.amp_hi = ak
                lam = DL.lag_schedule(obs, cfg, sc.Ts)
                q = DL.command(est, lam, sc.streams.tick_t)
                res = DL.run(sc, q, pens[travel])
                mm = DL.evaluate_run(sc, res, pens[travel], q, lam, obs)
                if amp == 0:
                    mm["false_correction_um"] = DL.ink_timeline_error(sc, res, lam, sc.neutral)
                r["v"][f"{key(c)}_nose{travel}"] = mm
        rows.append(r)
    return {"writer": wr.w, "rows": rows}


def select_d2(outs: List[Dict], cands: List[Dict]) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    names = sorted({k for r in rows for k in r["v"] if k != "tracker"})

    def mean(name, field, cond):
        v = [r["v"][name][field] for r in rows if cond(r) and name in r["v"] and r["v"][name].get(field) is not None]
        return float(np.mean(v)) if v else float("nan")
    table = {}
    for nm in names:
        fc = mean(nm, "false_correction_um", lambda r: r["amp_mm"] == 0)
        fc0 = mean("tracker", "false_correction_um", lambda r: r["amp_mm"] == 0)
        r1 = fc <= fc0 + 2.0
        r2 = all(mean(nm, "ink_err_um", lambda r, f=f: r["f0"] == f and 0 < r["amp_mm"] < 0.5)
                 <= 1.02 * mean("tracker", "ink_err_um", lambda r, f=f: r["f0"] == f and 0 < r["amp_mm"] < 0.5) for f in F0S)
        r3 = all(mean(nm, "recognition", lambda r, f=f, a=a: r["f0"] == f and abs(r["amp_mm"] - a * 1e3) < 1e-6)
                 >= mean("tracker", "recognition", lambda r, f=f, a=a: r["f0"] == f and abs(r["amp_mm"] - a * 1e3) < 1e-6) - 0.01
                 for f in F0S for a in AMPS)
        r4 = all(mean(nm, "coverage", lambda r, f=f, a=a: r["f0"] == f and abs(r["amp_mm"] - a * 1e3) < 1e-6)
                 >= mean("tracker", "coverage", lambda r, f=f, a=a: r["f0"] == f and abs(r["amp_mm"] - a * 1e3) < 1e-6) - 0.01
                 for f in F0S for a in AMPS)
        J = mean(nm, "ink_err_um", lambda r: r["amp_mm"] >= 1.0)
        table[nm] = {"J_ink_1_2mm_um": J, "tracker_J_ink_1_2mm_um": mean("tracker", "ink_err_um", lambda r: r["amp_mm"] >= 1.0),
                     "fc_um": fc, "tracker_fc_um": fc0, "R1": bool(r1), "R2": bool(r2), "R3": bool(r3), "R4": bool(r4),
                     "passes": bool(r1 and r2 and r3 and r4),
                     "ink_0p3mm_um": mean(nm, "ink_err_um", lambda r: 0 < r["amp_mm"] < 0.5),
                     "letters_1_2mm": mean(nm, "recognition", lambda r: r["amp_mm"] >= 1.0),
                     "words_1_2mm": mean(nm, "word_acc_app", lambda r: r["amp_mm"] >= 1.0),
                     "coverage_1_2mm": mean(nm, "coverage", lambda r: r["amp_mm"] >= 1.0),
                     "lag_mean_ms": mean(nm, "lag_mean_ms", lambda r: r["amp_mm"] >= 1.0),
                     "q_p95_mm": mean(nm, "q_p95_mm", lambda r: r["amp_mm"] >= 1.0)}
    chosen = {}
    for travel in (3, 6):
        ok = [k for k in table if table[k]["passes"] and (k.endswith(f"nose{travel}") or (k.endswith("nose3") and "lam_max0_" in k))]
        chosen[f"nose{travel}"] = min(ok, key=lambda k: table[k]["J_ink_1_2mm_um"]) if ok else None
    ok0 = [k for k in table if "lam_max0_" in k]
    ok0p = [k for k in ok0 if table[k]["passes"]]
    causal = min(ok0p, key=lambda k: table[k]["J_ink_1_2mm_um"]) if ok0p else (ok0[0] if ok0 else None)
    return {"rule": "D2: R1-R4 against the Rev H tracker; lowest mean ink error at 1-2 mm", "table": table,
            "chosen": chosen, "causal_gated": causal, "causal_passes": bool(ok0p)}


# ------------------------------------------------------------------ sensor ablation of the listening smoother (information)
def sensor_ablation_job(job: Dict) -> Dict:
    """Open-loop residual of the chosen fixed-lag RTS smoother (D0) with both sensors, the page sensor only and the IMU
    only, on one tuning writer (seed 300).  Information for the multi-sensor question; no choice depends on it."""
    wr = CO.Writer(job["writer"])
    rows = []
    for f0, amp in conditions():
        sc = scenario(wr, f0, amp, TUNE_SEEDS[0])
        delta = PR.servo_group_delay(sc.pen)
        r = {"writer": wr.w, "f0": f0, "amp_mm": amp * 1e3, "res": {}}
        for name, ua, up in (("imu+page", 1.0, 1.0), ("page_only", 0.0, 1.0), ("imu_only", 1.0, 0.0)):
            p = dict(DL.TREMOR_DEFAULTS); p.update(job["tremor"]); p.update({"use_acc": ua, "use_pos": up})
            out = SM.rts_fixed_lag(sc.streams, p, D0_LAGS, delta, out_every=8)
            r["res"][name] = residual_um(sc, out["t"], out["tremor"], D0_LAGS)
        rows.append(r)
    return {"writer": wr.w, "rows": rows}


def sensor_ablation(quick: bool, workers: int = 1) -> Dict:
    d01 = C.load("d01", quick) or C.load("d01", False)
    writers = TUNE_WRITERS[:1] if quick else TUNE_WRITERS
    outs = C.jmap(sensor_ablation_job, [{"writer": w, "tremor": d01["chosen_tremor"]} for w in writers], workers)
    rows = [r for o in outs for r in o["rows"]]
    summ = {}
    for name in ("imu+page", "page_only", "imu_only"):
        big = [r["res"][name] for r in rows if r["amp_mm"] >= 1.0]
        summ[name] = {"res_1_2mm_by_lag_um": [float(np.nanmean([b[i] for b in big])) for i in range(len(D0_LAGS))],
                      "res_0p3mm_um": float(np.nanmean([np.nanmean(r["res"][name][:3]) for r in rows if 0 < r["amp_mm"] < 0.5])),
                      "tremor_free_leak_um": float(np.nanmean([r["res"][name][0] for r in rows if r["amp_mm"] == 0]))}
    return {"lags_s": list(D0_LAGS), "summary": summ, "rows": rows, "writers": list(writers),
            "note": "ungated listening smoother, open loop, tuning seed 300; tremor-free 'leak' = its output there"}
