"""Where is the gap between the best causal estimator and perfect knowledge: prediction or separation?
(SIMULATION, model HW1 with real inputs; the part residuals are CALCULATIONS on the simulated signals.)

Method (fixed in this file before the runs; severe class, 1.72 mm at the tip, PD and ET):
  C0 perfect knowledge   R's oracle: the nose gets -d(t + g), d = the true handle tremor, g = the servo group delay
                         (3.39 ms).  What is left is the mechanism's floor.
  C1 prediction only     the TRUE tremor signal d is known causally, but late: its newest sample at the control tick t
                         is d(t - delta_s), delta_s = the sensor and filter delays of E's budget on the IMU path (anti-
                         aliasing 1.04 ms + FIFO/SPI 0.35 ms + pair averaging 0.13 ms = 1.52 ms); the predictor must
                         give d(t + g): a horizon of 4.9 ms.  Predictors:
                           hold   no prediction (d(t - delta_s)): a pure lag of 4.9 ms
                           AR     the causal linear predictor: d(t + g) = sum_j a_j d(t - delta_s - j Delta), one set of
                                  coefficients for both page axes, ridge least squares on the true tremor of the TUNING
                                  cases (severe and 0.6 mm), cross-fitted by E's folds (the model scoring fold k never
                                  saw fold k's writer or patients); (Delta, order) chosen on the tuning split by the
                                  cross-fitted in-band residual; the model used on the test split is fitted on all
                                  tuning cases.  (With a noise-free input, a Kalman predictor of an AR state-space model
                                  gives the same prediction, so AR stands for "AR or Kalman".)
                         Sensitivity (no reading): delta_s = 0 (the servo lag alone), 3.0 ms (the page sensor path: 2 ms
                         latency + up to 1 ms jitter) and 6.6 ms (a 10 ms horizon).
  C2 sensing, no writing the pen's sensor streams of the TREMOR ALONE: the same case, the same sensor models and noise
                         draws, the note's own contact pattern, but the handle motion is the tremor part only (handle
                         with tremor - handle without, nose held); the writing's pen rotation is removed from the IMU
                         model.  Estimators:
                           FIR    a linear causal filter on the IMU (study E's polyphase FIR at 250 Hz, predicting to
                                  t + g), trained here on the tremor-only streams of the tuning cases (severe and
                                  0.6 mm), cross-fitted by fold; its length and ridge chosen on the tuning split from
                                  FIR_GRID by the cross-fitted in-band residual: what the pen's IMU allows when there is
                                  no writing to reject (sensing: turning acceleration into displacement causally, IMU
                                  noise, bias, drift, anti-aliasing, delays)
                           page   the AR predictor (IMU-path choice of Delta and order, refitted for the page path's
                                  delay of 3 ms) on the page sensor's position of the tremor alone, sample-and-hold of
                                  the valid samples: the ideal page sensor (3 um, 2 ms; a bound) and the DeltaPen-class
                                  one (R's headline sensor)
                           E's families as E froze them: ai2's TCN and the real-data TCN, each raw and with its soft
                                  size gate, and the capture-tuned listening AKF (E's 'ungated_akf'; DeltaPen-class and
                                  ideal page sensor).  They were built to reject writing, so on the tremor alone their
                                  residual still carries that design's caution.
  C3 full                the same estimators on the real streams (tremor + writing): study E's configuration; for the
                         FIR, the filter trained on the tremor alone meets writing it has never seen.
Each estimate is applied as the nose command to the FULL case (tremor + writing), so the tip residual of C1/C2 is what
the prediction or the sensing leaves; C3 - C2 is what separating tremor from writing costs.  Part residuals (CALC): R's
tip-tremor measure applied to the error signals at the action time: e_pred = d(t + g) - d_hat_C1, e_trem = d(t + g) -
d_hat_C2, e_sep = d_hat_C2 - d_hat_C3 (what the writing changes in the estimate), e_full = d(t + g) - d_hat_C3.
Clean writing (tuning notes, E's cached clean cases, E's surrogate of the command path): the change each estimator
makes to the same notes without tremor: the other face of separation.
Words: every full-plant residual is mapped to words of 10 through the frozen E13 tuning curve; on the test split four
configurations are also read directly as a check of the mapping (C1-AR; the linear IMU filter on the tremor alone and
on the full case, where it also moves the writing; the real-data TCN gated on the tremor alone).
Broadband check (CALCULATION on real recorded inputs): R's tremor waveforms keep only f0 +- 2 Hz and 2 f0 +- 2 Hz
(R's ASSUMPTION), which makes them smooth and easy to predict.  The chosen AR predictor is refitted on the tuning ET recordings (Zenodo, hand
acceleration) converted to displacement in the library's bands and in one broad band (f0 - 2 Hz to 20 Hz), cross-fitted
by subject, and its residual at the IMU horizon is compared (as a share of the tremor, then at 1.72 mm).
"""
from __future__ import annotations

import dataclasses
import math
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import common as CM

DELTA_S = {"imu": 1.52e-3, "servo_only": 0.0, "page": 3.0e-3, "h10": 6.6e-3}
HEADLINE = "imu"
DTAU_GRID_MS = (0.5, 1.0, 2.0, 4.0)
ORDER_GRID = (4, 8, 16, 32, 64)
RIDGE = 1e-6
FIT_LEVELS = ("severe", "edge")
FIT_SUBSAMPLE = 4
FAMILIES = {"ai2tcn": ("chosen", None), "net": ("info", "net"), "akf": ("info", "ungated_akf")}
FIR_GRID = [(128, 1e-3), (128, 1e-5), (256, 1e-3), (256, 1e-5)]     # (taps at 250 Hz, ridge); E's was (128, 1e-3)
BROAD_HI_HZ = 20.0


def servo_delay() -> float:
    from realtrack import estimators as E
    return float(E.servo_delay())


# ------------------------------------------------------------------ the causal linear predictor
def lag_matrix(d: np.ndarray, tick_t: np.ndarray, t_rows: np.ndarray, delta_s: float, dtau: float, order: int):
    """(rows, order) per axis: d(t - delta_s - j dtau), j = 0..order-1 (zero before the record starts)."""
    T = t_rows[:, None] - delta_s - np.arange(order)[None, :] * dtau
    return [np.interp(T, tick_t, d[:, a], left=0.0) for a in range(d.shape[1])]


def target_at(d: np.ndarray, tick_t: np.ndarray, t_rows: np.ndarray, lead: float) -> np.ndarray:
    return np.column_stack([np.interp(t_rows + lead, tick_t, d[:, a]) for a in range(d.shape[1])])


def normal_eq(d: np.ndarray, tick_t: np.ndarray, delta_s: float, dtau: float, order: int, lead: float,
              t_min: float = 1.0, sub: int = FIT_SUBSAMPLE) -> Tuple[np.ndarray, np.ndarray]:
    """Normal-equation blocks (X'X, X'y) of one case, both axes stacked (isotropic coefficients)."""
    rows = np.flatnonzero((tick_t > t_min) & (tick_t < tick_t[-1] - lead - 1e-3))[::sub]
    tr = tick_t[rows]
    X = lag_matrix(d, tick_t, tr, delta_s, dtau, order)
    Y = target_at(d, tick_t, tr, lead)
    A = sum(x.T @ x for x in X)
    b = sum(X[a].T @ Y[:, a] for a in range(len(X)))
    return A, b


def solve(A: np.ndarray, b: np.ndarray, ridge: float = RIDGE) -> np.ndarray:
    n = A.shape[0]
    lam = ridge * float(np.trace(A)) / n
    return np.linalg.solve(A + lam * np.eye(n), b)


def ar_apply(coef: np.ndarray, d: np.ndarray, tick_t: np.ndarray, delta_s: float, dtau: float) -> np.ndarray:
    """The predicted d(t + g) at every tick from d(t - delta_s - j dtau) (causal: only samples at or before
    t - delta_s are used)."""
    X = lag_matrix(d, tick_t, tick_t, delta_s, dtau, len(coef))
    return np.column_stack([x @ coef for x in X])


def hold_apply(d: np.ndarray, tick_t: np.ndarray, delta_s: float) -> np.ndarray:
    """No prediction: the newest available sample d(t - delta_s)."""
    return np.column_stack([np.interp(tick_t - delta_s, tick_t, d[:, a], left=0.0) for a in range(d.shape[1])])


def fit_predictors(log=CM.log, quick: bool = False) -> Dict:
    """Cross-fitted choice of (Delta, order) on E's cached tuning cases, then the per-fold and all-tuning coefficients
    at every horizon of DELTA_S.  CALC on SIM signals (the true handle tremor of the tuning cases)."""
    from realtrack import cases as C
    lead = servo_delay()
    specs = [s for s in C.tuning_specs() if s.get("kind") and s["level"] in FIT_LEVELS]
    if quick:
        specs = [s for s in specs if s["note"] in (0, 1, 2)]
    data = []
    for s in specs:
        c = C.load_case(s)
        data.append({"id": s["id"], "fold": int(s["fold"]), "level": s["level"], "tick_t": c.tick_t,
                     "d": np.asarray(c.truth), "t1k": c.arrays["t1k"], "c1k": c.arrays["contact1k"],
                     "f0": float(c.meta["tremor"]["f0"])})
    folds = sorted({x["fold"] for x in data})
    out = {"lead_s": lead, "delta_s": DELTA_S, "grid": {"dtau_ms": list(DTAU_GRID_MS), "order": list(ORDER_GRID)},
           "fit_levels": list(FIT_LEVELS), "ridge": RIDGE, "n_cases": len(data), "scores": {}}
    ds = DELTA_S[HEADLINE]
    best = None
    t0 = time.time()
    for dtau_ms in ((1.0,) if quick else DTAU_GRID_MS):
        for order in ((32, 64) if quick else ORDER_GRID):
            dtau = dtau_ms * 1e-3
            blocks = [normal_eq(x["d"], x["tick_t"], ds, dtau, order, lead) for x in data]
            errs = []
            for k in folds:
                A = sum(b[0] for b, x in zip(blocks, data) if x["fold"] != k)
                bb = sum(b[1] for b, x in zip(blocks, data) if x["fold"] != k)
                coef = solve(A, bb)
                for x in data:
                    if x["fold"] != k or x["level"] != "severe":
                        continue
                    dh = ar_apply(coef, x["d"], x["tick_t"], ds, dtau)
                    e = target_at(x["d"], x["tick_t"], x["tick_t"], lead) - dh
                    errs.append(CM.signal_residual_mm(e, x["tick_t"], x["t1k"], x["c1k"], x["f0"]))
            sc = float(np.nanmean(errs)) if errs else float("nan")
            out["scores"][f"{dtau_ms:g}ms_x{order}"] = sc
            if np.isfinite(sc) and (best is None or sc < best[0] - 1e-6):
                best = (sc, dtau_ms, order)
    out["choice"] = {"dtau_ms": best[1], "order": best[2], "cv_residual_mm": best[0],
                     "rule": "the lowest cross-fitted in-band residual (R's measure on d(t + g) - prediction) over the "
                             "severe tuning cases at the IMU-path horizon; ties: the first in grid order"}
    # hold baseline on the same cases
    hold = []
    for x in data:
        if x["level"] != "severe":
            continue
        e = target_at(x["d"], x["tick_t"], x["tick_t"], lead) - hold_apply(x["d"], x["tick_t"], ds)
        hold.append(CM.signal_residual_mm(e, x["tick_t"], x["t1k"], x["c1k"], x["f0"]))
    out["hold_cv_residual_mm"] = float(np.nanmean(hold)) if hold else float("nan")
    dtau = best[1] * 1e-3
    order = best[2]
    coefs = {}
    for name, dsv in DELTA_S.items():
        blocks = [normal_eq(x["d"], x["tick_t"], dsv, dtau, order, lead) for x in data]
        per_fold = {}
        for k in folds:
            A = sum(b[0] for b, x in zip(blocks, data) if x["fold"] != k)
            bb = sum(b[1] for b, x in zip(blocks, data) if x["fold"] != k)
            per_fold[str(k)] = solve(A, bb).tolist()
        coefs[name] = {"delta_s": dsv, "horizon_s": dsv + lead, "per_fold": per_fold,
                       "all": solve(sum(b[0] for b in blocks), sum(b[1] for b in blocks)).tolist()}
    out["coef"] = coefs
    out["elapsed_s"] = time.time() - t0
    log(f"[gap] AR predictor: Delta {best[1]} ms x {order} (cv residual {best[0] * 1e3:.1f} um; hold "
        f"{out['hold_cv_residual_mm'] * 1e3:.1f} um) in {out['elapsed_s']:.0f} s")
    out["imu_fir"] = fit_imu_fir(quick, log)
    out["broadband"] = broadband_check(out, quick, log)
    return out


# ------------------------------------------------------------------ the linear estimator on the tremor-only IMU streams
class TremCase:
    """What realtrack.learned.fir_stats needs, for the tremor-only streams of one tuning case."""

    def __init__(self, st, truth: np.ndarray, active: np.ndarray, meta: Dict):
        self._st = st
        self.tick_t = st.tick_t
        self.truth = truth
        self.arrays = {"active_ticks": active}
        self.meta = meta

    def streams(self, sensor: str = "ideal"):
        return self._st


def active_ticks(tc, n: int) -> np.ndarray:
    """E's 'active' ticks (in contact, or within 2 mm of the page: the plant's authority gating) at n stream ticks."""
    scn = tc.scn
    lift = np.asarray(scn.meta.get("lift"))
    kt = np.clip(np.arange(n) * int(tc.neutral.info["tick_decim"]), 0, len(scn.t) - 1)
    return (((scn.down > 0.5) | (lift < 2.0e-3))[kt]).astype(np.float64)


def fit_imu_fir(quick: bool, log=CM.log) -> Dict:
    """E's polyphase FIR (realtrack.learned) trained on the TREMOR-ONLY IMU streams of the tuning cases (severe and
    0.6 mm), per held-out fold and on all folds; (taps, ridge) chosen from FIR_GRID by the cross-fitted in-band residual
    on the severe tuning cases (CALC on SIM)."""
    from realtrack import cases as C
    from realtrack import learned as LE
    t0 = time.time()
    lead = servo_delay()
    specs = [s for s in C.tuning_specs() if s.get("kind") and s["level"] in FIT_LEVELS]
    grid = [(256, 1e-5)] if quick else FIR_GRID
    if quick:
        specs = [s for s in specs if s["note"] in (0, 1)]
    by_note: Dict[int, List[Dict]] = {}
    for s in specs:
        by_note.setdefault(s["note"], []).append(s)
    Ls = sorted({L for L, _ in grid})
    stats: Dict[int, List] = {L: [] for L in Ls}
    evalset = []
    for i, ss in sorted(by_note.items()):
        note = CM.tuning_note(i)
        for s in ss:
            tc = CM.TuneCase(note, s)
            st = tremor_only_streams(tc.neutral, tc.scn, tc.clean, tc.scn_clean, tc.pen, note.trk, tc.s_seed, None)
            truth = C.truth_at_ticks(tc.neutral, tc.clean, st.tick_t)
            cl = TremCase(st, truth, active_ticks(tc, len(st.tick_t)), {"tremor": tc.tremor_meta()})
            for L in Ls:
                stats[L].append((int(s["fold"]), LE.fir_stats(cl, L, lead, "ideal", 0.0, 0.0)))
            if s["level"] == "severe":
                g1k = CM.grid_1k(tc.neutral, tc.scn)
                evalset.append({"fold": int(s["fold"]), "st": st, "truth": truth, "f0": tc.f0, **g1k})
        del note
    folds = sorted({f for f, _ in stats[Ls[0]]})
    scores = {}
    for L, ridge in grid:
        errs = []
        for k in folds:
            H = LE.fir_solve([x for f, x in stats[L] if f != k], L, ridge)
            for x in evalset:
                if x["fold"] != k:
                    continue
                dh = LE.fir_apply(x["st"], H, 0.0)
                tt = x["st"].tick_t
                e = target_at(x["truth"], tt, tt, lead) - dh
                errs.append(CM.signal_residual_mm(e, tt, x["t1k"], x["contact1k"], x["f0"]))
        scores[f"L{L}_r{ridge:g}"] = float(np.mean(errs))
    bestk = min(scores, key=scores.get)
    L, ridge = next((L, r) for L, r in grid if f"L{L}_r{r:g}" == bestk)
    H_all = LE.fir_solve([x for _, x in stats[L]], L, ridge)
    H_fold = {str(k): LE.fir_solve([x for f, x in stats[L] if f != k], L, ridge).tolist() for k in folds}
    out = {"L": L, "fs_in": LE.FS_IN, "lead_s": lead, "ridge": ridge, "n_cases": len(specs), "scores_mm": scores,
           "rule": "the lowest cross-fitted in-band residual (R's measure on d(t + g) - estimate) over the severe tuning "
                   "cases; grid FIR_GRID",
           "H_all": H_all.tolist(), "H_fold": H_fold, "elapsed_s": time.time() - t0,
           "trained_on": "tremor-only IMU streams of E's tuning cases (severe and 0.6 mm), no clean-writing penalty"}
    log(f"[gap] IMU FIR on the tremor alone: {len(specs)} cases; scores " +
        ", ".join(f"{k} {v * 1e3:.0f} um" for k, v in scores.items()) + f"; chosen {bestk} in {out['elapsed_s']:.0f} s")
    return out


def fir_estimate(ar: Dict, st, fold_key: Optional[str]) -> np.ndarray:
    from realtrack import learned as LE
    f = ar["imu_fir"]
    H = np.asarray(f["H_fold"][fold_key] if fold_key is not None else f["H_all"])
    return LE.fir_apply(st, H, 0.0)


# ------------------------------------------------------------------ broadband tremor: does the band limit flatter prediction?
def broadband_check(ar: Dict, quick: bool, log=CM.log) -> Dict:
    """The chosen AR structure refitted on the tuning ET recordings made displacement (a) in the library's bands and
    (b) in one broad band; subject-wise cross-fitting (5 groups); residual at each horizon as a share of the tremor's
    power amplitude (f0 +- 2 Hz), and the broadband RMS share.  CALCULATION on real recorded inputs (hand
    acceleration, Zenodo ET)."""
    from realdata import dsp as D
    from realdata import loaders as L
    from realdata import tremorlib as TL
    t0 = time.time()
    lib = TL.load(False)
    rows = {r["rid"]: r for r in lib["rows"] if r["source"] == "zenodo_et" and r["split"] == "tuning"
            and r.get("generator")}
    recs = [r for r in L.zenodo_et_records() if r.rid in rows]
    if quick:
        recs = recs[:4]
    fs = float(recs[0].fs) if recs else 1000.0
    lead = servo_delay()
    ch = ar["choice"]
    dtau, order = ch["dtau_ms"] * 1e-3, int(ch["order"])
    sigs = []
    for r in recs:
        f0 = float(rows[r.rid]["f0"])
        x = r.x[:, 0] if r.x.ndim > 1 else r.x
        narrow = sum(D.acc_to_disp(x, fs, lo, hi) for lo, hi in D.tremor_bands(f0))
        broad = D.acc_to_disp(x, fs, max(1.5, f0 - 2.0), BROAD_HI_HZ)
        trim = int(1.0 * fs)
        for name, s in (("narrow", narrow), ("broad", broad)):
            s = np.asarray(s, float)[trim:len(s) - trim]
            s = s / max(D.power_amplitude(s[:, None], fs, f0), 1e-30)
            sigs.append({"rid": r.rid, "subject": r.subject, "f0": f0, "band": name, "s": s})
    subjects = sorted({x["subject"] for x in sigs})
    group = {s: k % 5 for k, s in enumerate(subjects)}
    out = {"n_records": len(recs), "n_subjects": len(subjects), "fs": fs, "broad_band_hz": [None, BROAD_HI_HZ],
           "structure": {"dtau_ms": ch["dtau_ms"], "order": order}, "by_horizon": {}}
    for hname, ds in DELTA_S.items():
        res = {}
        for band in ("narrow", "broad"):
            S = [x for x in sigs if x["band"] == band]
            blocks = []
            for x in S:
                t = np.arange(len(x["s"])) / fs
                blocks.append(normal_eq(x["s"][:, None], t, ds, dtau, order, lead, t_min=0.5, sub=2))
            inb, rms = [], []
            for g in sorted(set(group.values())):
                tr = [b for b, x in zip(blocks, S) if group[x["subject"]] != g]
                if not tr:
                    continue
                coef = solve(sum(b[0] for b in tr), sum(b[1] for b in tr))
                for x in S:
                    if group[x["subject"]] != g:
                        continue
                    t = np.arange(len(x["s"])) / fs
                    d = x["s"][:, None]
                    e = (target_at(d, t, t, lead) - ar_apply(coef, d, t, ds, dtau))[int(0.5 * fs):-int(0.1 * fs)]
                    inb.append(D.power_amplitude(e, fs, x["f0"]))
                    rms.append(float(np.sqrt(np.mean(e ** 2)) / np.sqrt(np.mean(d[int(0.5 * fs):-int(0.1 * fs)] ** 2))))
            hold_inb = []
            for x in S:
                t = np.arange(len(x["s"])) / fs
                d = x["s"][:, None]
                e = (target_at(d, t, t, lead) - hold_apply(d, t, ds))[int(0.5 * fs):-int(0.1 * fs)]
                hold_inb.append(D.power_amplitude(e, fs, x["f0"]))
            res[band] = {"ar_inband_share_mean": float(np.mean(inb)), "ar_inband_share_max": float(np.max(inb)),
                         "ar_rms_share_mean": float(np.mean(rms)), "hold_inband_share_mean": float(np.mean(hold_inb)),
                         "ar_at_1p72mm_mm": float(np.mean(inb) * 1.72), "n": len(inb)}
        out["by_horizon"][hname] = {"horizon_ms": (ds + lead) * 1e3, **res}
    out["elapsed_s"] = time.time() - t0
    b = out["by_horizon"][HEADLINE]
    log(f"[gap] broadband check (ET tuning recordings): AR residual share narrow {b['narrow']['ar_inband_share_mean']:.4f}, "
        f"broad {b['broad']['ar_inband_share_mean']:.4f} (in band); rms broad {b['broad']['ar_rms_share_mean']:.3f} "
        f"in {out['elapsed_s']:.0f} s")
    return out


# ------------------------------------------------------------------ the tremor-only sensor streams
def tremor_only_record(res_n, scn_n, res_c, scn_c, tick_decim: int):
    """fusion Record of the tremor part of the handle motion: pH, aH (x, y) = with tremor - without (nose held), the
    note's own contact and lift, no writing in the pen-rotation model (intended = 0), the same hand tremor."""
    from handwriting import tracker as TR
    rn = TR.record(res_n, scn_n, tick_decim)
    rc = TR.record(res_c, scn_c, tick_decim)
    n = min(len(rn.t), len(rc.t))
    pH = rn.pH[:n].copy()
    pH[:, :2] = rn.pH[:n, :2] - rc.pH[:n, :2]
    aH = rn.aH[:n].copy()
    aH[:, :2] = rn.aH[:n, :2] - rc.aH[:n, :2]
    return dataclasses.replace(rn, t=rn.t[:n].copy(), pH=pH, aH=aH, s=rn.s[:n].copy(), contact=rn.contact[:n].copy(),
                               hand_tremor=rn.hand_tremor[:n].copy(), intended=np.zeros((n, 2)))


def tremor_only_streams(res_n, scn_n, res_c, scn_c, pen, trk: Dict, s_seed: int, page_model=None):
    """The pen's sensor streams of the tremor alone (same sensor models and seeds as the full case's streams)."""
    from fusion import sensors as S
    from handwriting import tracker as TR
    from realdata import sensors as RS
    rec = tremor_only_record(res_n, scn_n, res_c, scn_c, res_n.info["tick_decim"])
    st = S.make_streams(rec, TR.sensor_config(pen, trk["sensors"]), s_seed)
    if page_model is None:
        return st
    return RS.degrade_page(st, page_model, s_seed + 17)


def page_known(st, t_query: np.ndarray) -> np.ndarray:
    """The page sensor's position as known causally: at time tau, the newest VALID sample acquired at or before tau
    (sample and hold; gaps while the pen is lifted keep the last value).  Used with delta_s >= the stream's latency, so
    every sample used is available at the tick."""
    ok = np.asarray(st.pos_ok) > 0.5
    ta = np.asarray(st.pos_t)[ok]
    P = np.asarray(st.pos)[ok]
    if len(ta) == 0:
        return np.zeros((len(t_query), 2))
    j = np.searchsorted(ta, t_query, side="right") - 1
    out = P[np.clip(j, 0, len(P) - 1)].copy()
    out[j < 0] = 0.0
    return out


# ------------------------------------------------------------------ one case, every configuration
def designs() -> Dict[str, Dict]:
    fr = CM.frozen_e()
    out = {}
    for fam, (where, key) in FAMILIES.items():
        d = fr["chosen"] if where == "chosen" else fr["info"][key]
        out[fam] = d
    return out


def _raw(d: Dict) -> Dict:
    return {k: v for k, v in d.items() if k != "auth"}


def fit_len(x: np.ndarray, n: int) -> np.ndarray:
    """A per-tick array cut or extended (last value held) to n ticks (the streams have one tick fewer than the plant)."""
    x = np.asarray(x, float)
    if len(x) >= n:
        return x[:n]
    return np.vstack([x, np.repeat(x[-1:], n - len(x), axis=0)])


def run_case(tc, spec_like: Dict, fold_key: Optional[str], ar: Dict, read_keys: Sequence[str] = (),
             quick: bool = False) -> Dict:
    """Every configuration of one severe case (tc: common.TuneCase or common.TestCase with DeltaPen-class streams)."""
    from realdata import hw1 as H
    from realdata import sensors as RSN
    from realtrack import estimators as E
    lead = servo_delay()
    tick_t = tc.tick_t
    n = tc.n_ticks
    from realtrack import cases as C
    d_true = C.truth_at_ticks(tc.neutral, tc.clean, tick_t)
    tgt = target_at(d_true, tick_t, tick_t, lead)
    g1k = CM.grid_1k(tc.neutral, tc.scn)
    f0 = tc.f0
    cmds: Dict[str, np.ndarray] = {}
    ests: Dict[str, np.ndarray] = {}
    info: Dict[str, Dict] = {}
    cmds["oracle"] = tc.q_oracle
    # C1: prediction only
    ds = DELTA_S[HEADLINE]
    ests["pred_hold"] = hold_apply(d_true, tick_t, ds)
    ch = ar["choice"]
    for name, cf in ar["coef"].items():
        coef = np.asarray(cf["per_fold"][fold_key] if fold_key is not None else cf["all"])
        ests[f"pred_ar_{name}"] = ar_apply(coef, d_true, tick_t, cf["delta_s"], ch["dtau_ms"] * 1e-3)
    # C2 / C3: study E's families on the tremor-only and on the full streams
    dz = designs()
    trk = tc.note.trk if hasattr(tc, "note") else tc.wr.trk
    st_full = tc.streams_d if getattr(tc, "streams_d", None) is not None else tc.make_streams()
    st_trem = tremor_only_streams(tc.neutral, tc.scn, tc.clean, tc.scn_clean, tc.pen, trk, tc.s_seed, H.page_model())
    st_trem_i = tremor_only_streams(tc.neutral, tc.scn, tc.clean, tc.scn_clean, tc.pen, trk, tc.s_seed, None)
    cl = CM.CaseLike(spec_like)
    Ts = float(tick_t[1] - tick_t[0])
    for fam, d in dz.items():
        for tag, st in (("full", st_full), ("trem", st_trem)):
            raw, inf = E.estimate(_raw(d), st, case=cl, sensor="deltapen")
            raw = fit_len(raw, n)
            ests[f"{fam}_{tag}_raw"] = raw
            if d.get("auth"):
                gd, g, A = E.authority(raw, Ts, d["auth"])
                ests[f"{fam}_{tag}_gated"] = gd
                con = np.interp(tick_t, tc.neutral.t, tc.neutral.contact) > 0.5
                info[f"{fam}_{tag}_gated"] = {"auth_mean_contact": float(np.mean(g[con])) if con.any() else float("nan")}
        if fam == "akf":
            raw, _ = E.estimate(_raw(d), st_trem_i, case=cl, sensor="ideal")
            ests[f"{fam}_trem_raw_idealpage"] = fit_len(raw, n)
    # the AR predictor on the page sensor's position of the tremor alone (ideal and DeltaPen-class)
    cfp = ar["coef"]["page"]
    coef_p = np.asarray(cfp["per_fold"][fold_key] if fold_key is not None else cfp["all"])
    for tag, st in (("ideal", st_trem_i), ("deltapen", st_trem)):
        pk = page_known(st, tick_t)
        ests[f"page_ar_trem_{tag}"] = ar_apply(coef_p, pk, tick_t, cfp["delta_s"], ch["dtau_ms"] * 1e-3)
    # the linear filter on the IMU trained on the tremor alone (it reads the IMU only: the page sensor does not matter)
    if ar.get("imu_fir"):
        ests["fir_trem_raw"] = fit_len(fir_estimate(ar, st_trem_i, fold_key), n)
        ests["fir_full_raw"] = fit_len(fir_estimate(ar, st_full, fold_key), n)
    out = {"configs": {}, "parts": {}, "f0": f0}
    for k, dh in ests.items():
        cmds[k] = -dh
    for k, q in cmds.items():
        r = tc.run(q)
        read = k in read_keys
        m = CM.measures(tc.written, r, tc.scn, tc.pen, f0, read=read) if read else \
            {"tip_tremor_mm": H.tip_tremor_mm(r, tc.scn, f0), "bb_um": CM.broadband_um(r, tc.scn)}
        if k in ests:
            m["signal_residual_mm"] = CM.signal_residual_mm(tgt - ests[k], tick_t, g1k["t1k"], g1k["contact1k"], f0)
        m.update(info.get(k, {}))
        out["configs"][k] = m
    out["configs"]["held"] = {"tip_tremor_mm": H.tip_tremor_mm(tc.neutral, tc.scn, f0),
                              "bb_um": CM.broadband_um(tc.neutral, tc.scn)}
    for fam in list(dz) + ["fir"]:
        for gate in ("raw", "gated"):
            a, b = f"{fam}_trem_{gate}", f"{fam}_full_{gate}"
            if a in ests and b in ests:
                out["parts"][f"{fam}_{gate}_sep"] = CM.signal_residual_mm(ests[a] - ests[b], tick_t, g1k["t1k"],
                                                                           g1k["contact1k"], f0)
    return out


# ------------------------------------------------------------------ jobs
def tune_note(i: int, ar: Dict, quick: bool = False) -> Dict:
    """Every severe tuning case of note i (no reading)."""
    out_dir = CM.cache_dir(quick) / "gap"
    t0 = time.time()
    note = None
    done = []
    for kind in (("PD",) if quick else CM.KINDS):
        p = out_dir / f"tune_n{i}_{kind}_severe.json"
        if p.exists():
            done.append(p.name)
            continue
        t1 = time.time()
        note = note or CM.tuning_note(i)
        spec = CM.tuning_spec(i, kind, "severe")
        tc = CM.TuneCase(note, spec, streams=True)
        res = run_case(tc, spec, str(spec["fold"]), ar, quick=quick)
        res.update({"split": "tuning", "writer": note.written.real["writer"], "note": i, "kind": kind,
                    "class": "severe", "case_id": spec["id"], "tremor": tc.tremor_meta(), "_elapsed_s": time.time() - t1})
        res["streams_repro_vs_E"] = streams_repro(tc, spec)
        CM.jdump(p, res)
        CM.log(f"[gap] tune n{i} {kind}: " + ", ".join(f"{k} {v['tip_tremor_mm']:.2f}" for k, v in res["configs"].items())
               + f" ({time.time() - t1:.0f} s)")
        done.append(p.name)
    p = out_dir / f"tune_n{i}_clean.json"
    if not p.exists():
        CM.jdump(p, clean_note(i, ar))
    done.append(p.name)
    return {"job": f"gap_tune_n{i}", "files": done, "elapsed_s": time.time() - t0}


def clean_note(i: int, ar: Dict) -> Dict:
    """The clean-writing change of every estimator on tuning note i without tremor (E's cached clean case, E's
    surrogate of the Rev J command path: SIMULATION)."""
    from realtrack import cases as C
    from realtrack import estimators as E
    from realtrack import servo as SV
    spec = CM.tuning_spec(i, None, "clean")
    case = C.load_case(spec)
    st_d, st_i = case.streams("deltapen"), case.streams("ideal")
    n = len(case.tick_t)
    Ts = float(case.tick_t[1] - case.tick_t[0])
    pp = SV.pen_params()
    out = {"split": "tuning", "note": i, "writer": case.meta.get("writer"), "case_id": spec["id"], "clean_change_um": {}}
    for fam, d in designs().items():
        raw, _ = E.estimate(_raw(d), st_d, case=case, sensor="deltapen")
        raw = fit_len(raw, n)
        out["clean_change_um"][f"{fam}_full_raw"] = SV.fast_measures(case, -raw, pp)["clean_change_um"]
        if d.get("auth"):
            gd, _, _ = E.authority(raw, Ts, d["auth"])
            out["clean_change_um"][f"{fam}_full_gated"] = SV.fast_measures(case, -gd, pp)["clean_change_um"]
    if ar.get("imu_fir"):
        dh = fit_len(fir_estimate(ar, st_i, str(spec["fold"])), n)
        out["clean_change_um"]["fir_full_raw"] = SV.fast_measures(case, -dh, pp)["clean_change_um"]
    out["label"] = "SIMULATION (E's surrogate of the Rev J command path on E's cached clean tuning case)"
    return out


def streams_repro(tc, spec: Dict) -> Dict:
    """The rebuilt DeltaPen-class streams against E's cached case (the same seeds must give the same samples)."""
    from realtrack import cases as C
    try:
        c = C.load_case(spec)
    except Exception as e:
        return {"error": repr(e)}
    st = tc.streams_d
    return {"acc_max_abs_diff": float(np.max(np.abs(np.asarray(st.acc) - c.arrays["i_acc"]))),
            "pos_max_abs_diff": float(np.max(np.abs(np.asarray(st.pos) - c.arrays["d_pos"]))),
            "truth_max_abs_diff": float(np.max(np.abs(
                C.truth_at_ticks(tc.neutral, tc.clean, st.tick_t) - np.asarray(c.truth))))}


TEST_READ = ("pred_ar_imu", "fir_trem_raw", "fir_full_raw", "net_trem_gated")


def test_note(wr, i: int, ar: Dict, quick: bool = False) -> List[str]:
    out_dir = CM.cache_dir(quick) / "gap"
    done = []
    for kind in (("PD",) if quick else CM.KINDS):
        p = out_dir / f"test_w{i}_{kind}_severe.json"
        if p.exists():
            done.append(p.name)
            continue
        t1 = time.time()
        tc = CM.TestCase(wr, i, kind, "severe")
        res = run_case(tc, {"split": "test"}, None, ar, read_keys=() if quick else TEST_READ, quick=quick)
        res.update({"split": "test", "writer": wr.written.real["writer"], "note": i, "kind": kind, "class": "severe",
                    "tremor": tc.tremor_meta(), "_elapsed_s": time.time() - t1})
        e = tc.e_cached() or {}
        res["repro_vs_E"] = {k: {"mine": res["configs"].get(m, {}).get("tip_tremor_mm"),
                                 "E": (e.get("devices", {}).get(k) or {}).get("tip_tremor_mm")}
                             for k, m in (("revJ_new|deltapen", "ai2tcn_full_gated"),
                                          ("revJ_info_net|deltapen", "net_full_gated"),
                                          ("revJ_info_ungated_akf|deltapen", "akf_full_raw"))}
        CM.jdump(p, res)
        CM.log(f"[gap] test w{i} {kind}: " + ", ".join(f"{k} {v['tip_tremor_mm']:.2f}" for k, v in res["configs"].items())
               + f" ({time.time() - t1:.0f} s)")
        done.append(p.name)
    return done


# ------------------------------------------------------------------ aggregation
CHAINS = {
    "fir_raw": ("a linear filter on the IMU trained on the tremor alone (no writing seen in training)", "fir_trem_raw",
                "fir_full_raw"),
    "ai2tcn_gated": ("E's frozen design: ai2's TCN + soft size gate", "ai2tcn_trem_gated", "ai2tcn_full_gated"),
    "net_gated": ("the real-data TCN + soft size gate (E, information)", "net_trem_gated", "net_full_gated"),
    "ai2tcn_raw": ("ai2's TCN, no gate", "ai2tcn_trem_raw", "ai2tcn_full_raw"),
    "net_raw": ("the real-data TCN, no gate", "net_trem_raw", "net_full_raw"),
    "akf_raw": ("the listening AKF tuned for capture, no gate (E's 'ungated_akf')", "akf_trem_raw", "akf_full_raw"),
}


def load(quick: bool, split: str) -> List[Dict]:
    d = CM.cache_dir(quick) / "gap"
    pre = "tune" if split == "tuning" else "test"
    return [c for c in (CM.jload(p) for p in sorted(d.glob(f"{pre}_*.json"))) if c]


def aggregate(quick: bool, p_curve: Optional[Sequence[float]], ar: Optional[Dict],
              p_curve_test: Optional[Sequence[float]] = None) -> Dict:
    from . import curve as CV
    out = {"method": __doc__.split("Method")[1].strip() if "Method" in __doc__ else "", "predictor": _ar_summary(ar)}
    sc = {k: CM.jload(CM.cache_dir(quick) / "gap" / f"sensing_{k}.json") for k in ("imu", "page")}
    out["sensing_check"] = {k: v for k, v in sc.items() if v}
    for split in ("tuning", "test"):
        cases = [c for c in load(quick, split) if "configs" in c]
        cleans = [c for c in load(quick, split) if "clean_change_um" in c]
        if not cases:
            continue
        keys = sorted({k for c in cases for k in c["configs"]})
        tab = {}
        for k in keys:
            pw = {}
            for c in cases:
                v = c["configs"].get(k)
                if v is not None and v.get("tip_tremor_mm") is not None:
                    pw.setdefault(c["writer"], []).append(float(v["tip_tremor_mm"]))
            row = {"tip_tremor_mm": CM.boot({w: float(np.mean(v)) for w, v in pw.items()})}
            sr = {}
            for c in cases:
                v = c["configs"].get(k, {})
                if v.get("signal_residual_mm") is not None:
                    sr.setdefault(c["writer"], []).append(float(v["signal_residual_mm"]))
            if sr:
                row["signal_residual_mm"] = CM.boot({w: float(np.mean(v)) for w, v in sr.items()})
            if p_curve is not None and np.all(np.isfinite(p_curve)):
                ww = {}
                for c in cases:
                    v = c["configs"].get(k)
                    if v is not None and v.get("tip_tremor_mm") is not None:
                        ww.setdefault(c["writer"], []).append(float(CV.model(float(v["tip_tremor_mm"]), p_curve)))
                row["words_via_curve"] = CM.boot({w: float(np.mean(v)) for w, v in ww.items()})
            if split == "test" and p_curve_test is not None and np.all(np.isfinite(p_curve_test)):
                ww = {}
                for c in cases:
                    v = c["configs"].get(k)
                    if v is not None and v.get("tip_tremor_mm") is not None:
                        ww.setdefault(c["writer"], []).append(float(CV.model(float(v["tip_tremor_mm"]), p_curve_test)))
                row["words_via_test_curve"] = CM.boot({w: float(np.mean(v)) for w, v in ww.items()})
            rd = {}
            for c in cases:
                v = c["configs"].get(k, {})
                if v.get("words_total"):
                    rd.setdefault(c["writer"], []).append(CM.of10(v))
            if rd:
                row["words_read"] = CM.boot({w: float(np.mean(v)) for w, v in rd.items()})
            tab[k] = row
        parts = {}
        for k in sorted({k for c in cases for k in c.get("parts", {})}):
            pw = {}
            for c in cases:
                if k in c.get("parts", {}):
                    pw.setdefault(c["writer"], []).append(float(c["parts"][k]))
            parts[k] = CM.boot({w: float(np.mean(v)) for w, v in pw.items()})
        chains = {}
        for name, (label, trem, full) in CHAINS.items():
            if trem not in tab or full not in tab:
                continue
            ch = {"label": label, "steps": []}
            for step, key in (("perfect knowledge (C0)", "oracle"), ("prediction only, AR, IMU horizon (C1)",
                                                                      "pred_ar_imu"),
                              ("sensing + prediction, tremor alone (C2)", trem), ("full: tremor + writing (C3)", full)):
                if key in tab:
                    ch["steps"].append({"step": step, "config": key, **{kk: tab[key].get(kk) for kk in
                                                                         ("tip_tremor_mm", "words_via_curve",
                                                                          "words_via_test_curve", "signal_residual_mm",
                                                                          "words_read")}})
            fam, gate = name.rsplit("_", 1)
            ch["separation_part_mm"] = parts.get(f"{fam}_{gate}_sep")
            if cleans:
                pw = {}
                for c in cleans:
                    v = c["clean_change_um"].get(full)
                    if v is not None:
                        pw.setdefault(c["writer"], []).append(float(v))
                if pw:
                    b = CM.boot({w: float(np.mean(v)) for w, v in pw.items()})
                    b["worst_note"] = float(max(max(v) for v in pw.values()))
                    ch["clean_change_um"] = b
            chains[name] = ch
        out[split] = {"n_cases": len(cases), "n_writers": len({c["writer"] for c in cases}), "configs": tab,
                      "parts": parts, "chains": chains,
                      "repro": [c.get("repro_vs_E") or c.get("streams_repro_vs_E") for c in cases]}
    return out


def _ar_summary(ar: Optional[Dict]) -> Dict:
    if not ar:
        return {}
    out = {k: ar[k] for k in ("lead_s", "delta_s", "grid", "fit_levels", "ridge", "n_cases", "scores", "choice",
                              "hold_cv_residual_mm", "elapsed_s", "broadband") if k in ar}
    if ar.get("imu_fir"):
        out["imu_fir"] = {k: v for k, v in ar["imu_fir"].items() if k not in ("H_all", "H_fold")}
    return out


def test_clean(wr, i: int, ar: Dict, quick: bool = False) -> List[str]:
    """The clean-writing change of every full estimator on R's clean test note i (full HW1 plant, ai2's false-correction
    measure, DeltaPen-class streams with R's seeds): the other face of separation on the test split."""
    from realtrack import estimators as E
    p = CM.cache_dir(quick) / "gap" / f"test_w{i}_clean.json"
    if p.exists():
        return [p.name]
    t0 = time.time()
    tc = CM.TestCase(wr, i, None, None)
    st = tc.streams_d
    n = tc.n_ticks
    Ts = float(tc.tick_t[1] - tc.tick_t[0])
    cl = CM.CaseLike({"split": "test"}, dh=tc.dh_revh)
    ests = {}
    for fam, d in designs().items():
        raw, _ = E.estimate(_raw(d), st, case=cl, sensor="deltapen")
        raw = fit_len(raw, n)
        ests[f"{fam}_full_raw"] = raw
        if d.get("auth"):
            ests[f"{fam}_full_gated"], _, _ = E.authority(raw, Ts, d["auth"])
    if ar.get("imu_fir"):
        # the FIR reads the IMU only (the DeltaPen-class streams carry the same IMU samples as the ideal ones)
        ests["fir_full_raw"] = fit_len(fir_estimate(ar, st, None), n)
    out = {"split": "test", "note": i, "writer": wr.written.real["writer"], "clean_change_um": {},
           "label": "SIMULATION (full HW1 plant; ai2's false-correction measure against the nose-held run)"}
    for k, dh in ests.items():
        r = tc.run(-dh)
        out["clean_change_um"][k] = CM.false_correction_um(tc.sJ, r)
    out["_elapsed_s"] = time.time() - t0
    CM.jdump(p, out)
    CM.log(f"[gap] test w{i} clean: " + ", ".join(f"{k} {v:.1f} um" for k, v in out["clean_change_um"].items()))
    return [p.name]


# ------------------------------------------------------------------ sensing check (extras stage; tuning split only)
PAGE_HP_HZ = 1.5          # causal 2nd-order Butterworth high-pass of the page position (below the lowest tremor band)


def normal_eq_xy(x: np.ndarray, d: np.ndarray, tick_t: np.ndarray, delta_s: float, dtau: float, order: int,
                 lead: float, t_min: float = 1.0, sub: int = FIT_SUBSAMPLE) -> Tuple[np.ndarray, np.ndarray]:
    """As normal_eq, with a separate input signal x (the lags) and target signal d (at t + lead)."""
    rows = np.flatnonzero((tick_t > t_min) & (tick_t < tick_t[-1] - lead - 1e-3))[::sub]
    tr = tick_t[rows]
    X = lag_matrix(x, tick_t, tr, delta_s, dtau, order)
    Y = target_at(d, tick_t, tr, lead)
    return sum(a.T @ a for a in X), sum(X[k].T @ Y[:, k] for k in range(len(X)))


def causal_highpass(x: np.ndarray, fs: float, fc: float = PAGE_HP_HZ) -> np.ndarray:
    from scipy.signal import butter, lfilter
    b, a = butter(2, fc, btype="high", fs=fs)
    return lfilter(b, a, x, axis=0)


def _sensing_streams(kind: str, tc, note, variants):
    import dataclasses as dc
    from fusion import sensors as S
    from handwriting import tracker as TR
    from realdata import hw1 as H
    from realdata import sensors as RSN
    rec = tremor_only_record(tc.neutral, tc.scn, tc.clean, tc.scn_clean, tc.neutral.info["tick_decim"])
    cfg = TR.sensor_config(tc.pen, note.trk["sensors"])
    if kind == "imu":
        cfg_p = dc.replace(cfg, comp="ideal", acc=dc.replace(cfg.acc, nd=0.0, bias_sd=0.0, drift_sd=0.0, scale_sd=0.0,
                                                             misalign_sd=0.0))
        return {"pen": S.make_streams(rec, cfg, tc.s_seed), "perfect": S.make_streams(rec, cfg_p, tc.s_seed)}
    st_i = S.make_streams(rec, cfg, tc.s_seed)
    return {"ideal": st_i, "deltapen": RSN.degrade_page(st_i, H.page_model(), tc.s_seed + 17)}


def sensing_check(kind: str, quick: bool = False, log=CM.log) -> Dict:
    """What the pen's sensors allow when the tremor is alone (CALC on SIM streams, tuning split, cross-fitted by fold).
    kind 'imu':  the IMU filter (the chosen FIR) with the pen's IMU against a perfect accelerometer (no noise, bias,
                 drift, scale error or misalignment, and no pen rotation), same records and seeds
    kind 'page': a linear predictor on the page sensor's position, causally high-passed at PAGE_HP_HZ (the relative
                 DeltaPen-class sensor accumulates error), lags as the AR choice at the page path's delay (3 ms),
                 target the true tremor at t + g, fitted per fold; ideal and DeltaPen-class page sensors.
    Pass 1 collects the fit statistics note by note; pass 2 rebuilds each severe case, applies the model of its held-out
    fold and runs the full case in the plant (tip tremor, R's measure).  Memory: one note at a time."""
    from realdata import hw1 as H
    from realtrack import cases as C
    from realtrack import learned as LE
    from . import stages as SG
    t0 = time.time()
    ar = SG.load_predictor(quick)
    lead = servo_delay()
    fi = ar["imu_fir"]
    L, ridge = int(fi["L"]), float(fi["ridge"])
    dtau, order = ar["choice"]["dtau_ms"] * 1e-3, int(ar["choice"]["order"])
    ds_page = DELTA_S["page"]
    specs = [s for s in C.tuning_specs() if s.get("kind") and s["level"] in FIT_LEVELS]
    if quick:
        specs = [s for s in specs if s["note"] in (0, 1, 2)]
    by_note: Dict[int, List[Dict]] = {}
    for s in specs:
        by_note.setdefault(s["note"], []).append(s)
    variants = ("pen", "perfect") if kind == "imu" else ("ideal", "deltapen")

    def inputs(v, st):
        return st if kind == "imu" else causal_highpass(page_known(st, st.tick_t), 1.0 / float(st.tick_t[1] - st.tick_t[0]))
    stats: Dict[str, List] = {v: [] for v in variants}
    for i, ss in sorted(by_note.items()):                         # pass 1: the fit statistics
        note = CM.tuning_note(i)
        for s in ss:
            tc = CM.TuneCase(note, s)
            sts = _sensing_streams(kind, tc, note, variants)
            truth = C.truth_at_ticks(tc.neutral, tc.clean, sts[variants[0]].tick_t)
            act = active_ticks(tc, len(truth))
            for v in variants:
                st = sts[v]
                if kind == "imu":
                    stats[v].append((int(s["fold"]), LE.fir_stats(TremCase(st, truth, act, {"tremor": 1}), L, lead,
                                                                   "ideal", 0.0, 0.0)))
                else:
                    stats[v].append((int(s["fold"]), normal_eq_xy(inputs(v, st), truth, st.tick_t, ds_page, dtau, order,
                                                                  lead)))
            del tc, sts
        del note
    folds = sorted({f for f, _ in stats[variants[0]]})
    models = {}
    for v in variants:
        for k in folds:
            tr = [x for f, x in stats[v] if f != k]
            models[(v, k)] = LE.fir_solve(tr, L, ridge) if kind == "imu" else solve(sum(x[0] for x in tr),
                                                                                  sum(x[1] for x in tr))
    res = {v: {"sig": [], "tip": []} for v in variants}
    for i, ss in sorted(by_note.items()):                         # pass 2: score the severe cases, held-out fold
        sev = [s for s in ss if s["level"] == "severe"]
        if not sev:
            continue
        note = CM.tuning_note(i)
        for s in sev:
            tc = CM.TuneCase(note, s)
            sts = _sensing_streams(kind, tc, note, variants)
            k = int(s["fold"])
            g1k = CM.grid_1k(tc.neutral, tc.scn)
            for v in variants:
                st = sts[v]
                tt = st.tick_t
                truth = C.truth_at_ticks(tc.neutral, tc.clean, tt)
                dh = LE.fir_apply(st, models[(v, k)], 0.0) if kind == "imu" else \
                    ar_apply(models[(v, k)], inputs(v, st), tt, ds_page, dtau)
                err = target_at(truth, tt, tt, lead) - dh
                res[v]["sig"].append(CM.signal_residual_mm(err, tt, g1k["t1k"], g1k["contact1k"], tc.f0))
                r = tc.run(-fit_len(dh, tc.n_ticks))
                res[v]["tip"].append(H.tip_tremor_mm(r, tc.scn, tc.f0))
                del r
            del tc, sts
        del note
    out = {"kind": kind, "variants": {}, "n_cases": len(specs),
           "label": "CALC on SIM streams of the tremor alone (tuning split, cross-fitted by fold); tip = SIM (full plant)"}
    for v in variants:
        out["variants"][v] = {"signal_residual_mm": float(np.mean(res[v]["sig"])), "tip_tremor_mm": float(np.mean(res[v]["tip"])),
                              "n": len(res[v]["sig"]), "per_case_signal_mm": [float(x) for x in res[v]["sig"]],
                              "per_case_tip_mm": [float(x) for x in res[v]["tip"]]}
    out["elapsed_s"] = time.time() - t0
    log(f"[gap] sensing check ({kind}): " + ", ".join(
        f"{v} signal {x['signal_residual_mm']:.3f} mm, tip {x['tip_tremor_mm']:.3f} mm" for v, x in out["variants"].items())
        + f" in {out['elapsed_s']:.0f} s")
    return out
