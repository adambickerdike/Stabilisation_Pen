"""Closed-loop evaluation of external estimators on the pencil model P1 (SIMULATION).

Pattern (per test condition seed x f0 x amplitude):
  1. reference: NEUTRAL on the same handwriting without tremor (harness convention of
     sim/pencil/run_study.py); NEUTRAL with tremor; the oracle (M.housing_disturbance);
  2. sensor streams from the recorded true housing motion of the NEUTRAL tremor run
     (fusion.sensors, own noise draws);
  3. the causal estimator -> d_hat per stage tick -> zero-order hold onto the simulation steps;
  4. Controller(mode="external") with M.with_estimate;
  5. metrics against the reference, plus how far the controlled run's housing path departs from
     the neutral run's (the approximation of step 2); optionally the streams are regenerated from
     the controlled run and the estimate re-injected once (iteration).
Distortion: the same estimator on the tremor-free writing (streams from the reference run),
against the reference.  References also run: the tremor-band oracle (the true disturbance band-passed
3-15 Hz with a zero-phase filter, i.e. NOT causal: the best any tremor-band estimator could do) and,
for the frozen Kalman filter, the internal core mode (kfosc) next to its external port.
All rows are SIMULATION on synthetic signals.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import data as FD
from . import estimators as ES
from . import sensors as S

import sim.pencil  # noqa: F401,E402
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402

F0S = (4.0, 6.0, 8.0, 10.0, 12.0)
AMPS = (0.1e-3, 0.3e-3, 0.5e-3)
BAND = (3.0, 15.0)


# ------------------------------------------------------------------ metrics
def path_distance_um(res, intended: np.ndarray, t_settle: float = 0.5) -> float:
    """Nearest-point distance of in-contact ink to the intended path (timing-free; run_study.path_distance)."""
    from scipy.spatial import cKDTree
    tree = cKDTree(intended[::4])
    m = (res["contact"] > 0) & (res["t"] > t_settle)
    d, _ = tree.query(res.ink()[m])
    return float(np.sqrt(np.mean(d ** 2)) * 1e6)


def run_metrics(res, ref, base: Optional[Dict] = None, neutral=None, intended: Optional[np.ndarray] = None) -> Dict:
    m = E.compare(res, ref)
    out = {k: m[k] for k in ("e_rms_um", "e_band_rms_um", "e_p95_um", "q_sat_frac", "frac_vsat", "frac_stop",
                             "P_rail_classB_mW", "P_rail_recovery_mW", "q_rms_um", "q_peak_um", "housing_dev_rms_um")}
    if base is not None:
        out["ratio"] = m["e_rms_um"] / base["e_rms_um"]
        out["band_ratio"] = m["e_band_rms_um"] / base["e_band_rms_um"]
    if neutral is not None:
        mk, _, n = E._mask(res, neutral)
        dH = res.xy("pHx")[:n] - neutral.xy("pHx")[:n]
        out["housing_vs_neutral_rms_um"] = E.rms2(dH, mk) * 1e6
    if intended is not None:
        out["path_um"] = path_distance_um(res, intended)
        # time-aligned distance of the ink from the intended hand path (static offset removed): not a harness metric,
        # but it shows whether a correction moves the ink toward or away from what the writer intended
        t = res["t"]
        k = np.clip(np.round(t / FD.DT).astype(int), 0, len(intended) - 1)
        mk = (res["contact"] > 0) & (t > 0.5)
        e = res.ink() - intended[k]
        if mk.any():
            e = e - np.median(e[mk], axis=0)
            out["intent_err_um"] = float(np.sqrt(np.mean(np.sum(e[mk] ** 2, axis=1))) * 1e6)
    return out


def signal_metrics(dhat: np.ndarray, tick_t: np.ndarray, rec1: S.Record, rec0: S.Record) -> Dict:
    """Open-loop quality of the estimate against the true disturbance at the ticks (in contact, t > 0.5 s)."""
    d = S.truth_at(tick_t, rec1, rec0)
    con = np.interp(tick_t, rec1.t, rec1.contact) > 0.5
    m = con & (tick_t > 0.5)
    if not m.any():
        return {}
    fs = 1.0 / float(tick_t[1] - tick_t[0])
    sos = butter(4, BAND, btype="band", fs=fs, output="sos")
    db = sosfiltfilt(sos, d, axis=0)
    e = d - dhat
    eb = sosfiltfilt(sos, e, axis=0)

    def r(x):
        return float(np.sqrt(np.mean(np.sum(x[m] ** 2, axis=1))))
    return {"d_rms_um": r(d) * 1e6, "d_band_rms_um": r(db) * 1e6, "dhat_rms_um": r(dhat) * 1e6,
            "residual_ratio": r(e) / max(r(d), 1e-12), "residual_ratio_band": r(eb) / max(r(db), 1e-12)}


def band_oracle_steps(rec1: S.Record, rec0: S.Record, t_sim: np.ndarray) -> np.ndarray:
    """True disturbance band-passed 3-15 Hz, zero-phase (non-causal reference), at the simulation steps."""
    n = min(len(rec1.t), len(rec0.t))
    d = rec1.pH[:n, :2] - rec0.pH[:n, :2]
    sos = butter(4, BAND, btype="band", fs=rec1.fs, output="sos")
    db = sosfiltfilt(sos, d, axis=0)
    return np.ascontiguousarray(np.column_stack([np.interp(t_sim, rec1.t[:n], db[:, 0]),
                                                 np.interp(t_sim, rec1.t[:n], db[:, 1])]))


# ------------------------------------------------------------------ estimator specification
@dataclass
class Spec:
    """One estimator configuration: estimator name, its parameters and its sensor set."""
    label: str
    name: str
    params: Dict = field(default_factory=dict)
    sensors: Dict = field(default_factory=dict)       # kwargs of fusion.sensors.config
    extra: Dict = field(default_factory=dict)         # passed to the estimator (e.g. calibration)

    def sensor_config(self) -> S.SensorConfig:
        return S.config(**self.sensors)


def sensor_seed(seed: int, f0: float, amp: float, tag: int = 0) -> int:
    return 10_000_000 + 1000 * seed + 10 * int(round(f0)) + int(round(amp * 1e4)) + 100_000 * tag


def estimate(spec: Spec, rec: S.Record, sseed: int, extra: Optional[Dict] = None):
    st = S.make_streams(rec, spec.sensor_config(), sseed)
    ex = dict(spec.extra)
    if extra:
        ex.update(extra)
    dh, info = ES.run_estimator(spec.name, st, spec.params, ex)
    return st, dh, info


# ------------------------------------------------------------------ one test condition
def case(seed: int, f0: float, amp: float, specs: Sequence[Spec], duration: float = FD.DURATION,
         with_internal_kfosc: bool = True, with_band_oracle: bool = True, iterate: Sequence[str] = (),
         extra_by_label: Optional[Dict[str, Callable]] = None) -> List[Dict]:
    """All rows for one condition.  extra_by_label[label](seed, f0, amp) -> extra inputs (e.g. personal calibration)."""
    cfg = M.PencilConfig()
    sc0 = FD.test_scenario(seed, duration=duration)
    sc1 = FD.test_scenario(seed, f0, amp, duration)
    ref = FD.run(sc0, seed=seed)
    rn = FD.run(sc1, seed=seed)
    rec0 = S.record_from_result(ref, sc0)
    rec1 = S.record_from_result(rn, sc1)
    base = E.compare(rn, ref)
    rows = []
    key = {"seed": seed, "f0": f0, "amp_mm": amp * 1e3}
    rows.append(dict(key, label="neutral", ratio=1.0, band_ratio=1.0, **run_metrics(rn, ref, intended=sc1.intended)))
    rows.append(dict(key, label="neutral_no_tremor", **{k: v for k, v in run_metrics(ref, ref, intended=sc0.intended).items()
                                                         if k in ("path_um", "intent_err_um", "P_rail_classB_mW", "P_rail_recovery_mW")}))
    ro = FD.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, ref)), M.Controller(mode="oracle"), cfg, seed=seed)
    rows.append(dict(key, label="oracle", **run_metrics(ro, ref, base, rn, sc1.intended)))
    if with_band_oracle:
        rb = FD.run(M.with_estimate(sc1, band_oracle_steps(rec1, rec0, sc1.t)), M.Controller(mode="external"), cfg, seed=seed)
        rows.append(dict(key, label="oracle_band", **run_metrics(rb, ref, base, rn, sc1.intended)))
    if with_internal_kfosc:
        rk = FD.run(sc1, M.kalman_controller(), cfg, seed=seed)
        rows.append(dict(key, label="kfosc_internal", **run_metrics(rk, ref, base, rn, sc1.intended)))
    for spec in specs:
        t0 = time.time()
        ex = extra_by_label[spec.label](seed, f0, amp) if extra_by_label and spec.label in extra_by_label else None
        sseed = sensor_seed(seed, f0, amp)
        st, dh, info = estimate(spec, rec1, sseed, ex)
        t_est = time.time() - t0
        rx = FD.run(M.with_estimate(sc1, S.expand_to_steps(dh, len(sc1.t), rec1.sdec)), M.Controller(mode="external"),
                    cfg, seed=seed)
        row = dict(key, label=spec.label, estimator=spec.name, est_time_s=t_est,
                   **run_metrics(rx, ref, base, rn, sc1.intended), **signal_metrics(dh, st.tick_t, rec1, rec0))
        if "f_est" in info:
            con = np.interp(st.tick_t, rec1.t, rec1.contact) > 0.5
            mm = con & (st.tick_t > 1.0)
            row["f_est_median_hz"] = float(np.median(info["f_est"][mm])) if mm.any() else float("nan")
        if "authority" in info:
            con = np.interp(st.tick_t, rec1.t, rec1.contact) > 0.5
            row["authority_mean"] = float(np.mean(info["authority"][con])) if con.any() else float("nan")
        if spec.label in iterate:
            # re-estimate from the controlled run's own housing motion and re-inject (one fixed-point step)
            rec_x = S.record_from_result(rx, sc1)
            _, dh2, _ = estimate(spec, rec_x, sseed, ex)
            rx2 = FD.run(M.with_estimate(sc1, S.expand_to_steps(dh2, len(sc1.t), rec1.sdec)), M.Controller(mode="external"),
                         cfg, seed=seed)
            m2 = run_metrics(rx2, ref, base, rx)
            row["ratio_iter1"] = m2["ratio"]
            row["housing_iter1_vs_iter0_rms_um"] = m2["housing_vs_neutral_rms_um"]
            row["dhat_change_rms_um"] = float(np.sqrt(np.mean(np.sum((dh2 - dh) ** 2, axis=1))) * 1e6)
        rows.append(row)
    return rows


def distortion(seed: int, specs: Sequence[Spec], duration: float = FD.DURATION,
               extra_by_label: Optional[Dict[str, Callable]] = None) -> List[Dict]:
    """Each estimator on the tremor-free writing, against the reference (false correction)."""
    cfg = M.PencilConfig()
    sc0 = FD.test_scenario(seed, duration=duration)
    ref = FD.run(sc0, seed=seed)
    rec0 = S.record_from_result(ref, sc0)
    rows = []
    rk = FD.run(sc0, M.kalman_controller(), cfg, seed=seed)
    rows.append({"seed": seed, "label": "kfosc_internal", "distortion_um": E.compare(rk, ref)["e_rms_um"]})
    for spec in specs:
        ex = extra_by_label[spec.label](seed, 0.0, 0.0) if extra_by_label and spec.label in extra_by_label else None
        st, dh, info = estimate(spec, rec0, sensor_seed(seed, 0.0, 0.0, 1), ex)
        rx = FD.run(M.with_estimate(sc0, S.expand_to_steps(dh, len(sc0.t), rec0.sdec)), M.Controller(mode="external"),
                    cfg, seed=seed)
        m = E.compare(rx, ref)
        con = np.interp(st.tick_t, rec0.t, rec0.contact) > 0.5
        mm = con & (st.tick_t > 0.5)
        rows.append({"seed": seed, "label": spec.label, "distortion_um": m["e_rms_um"],
                     "false_correction_rms_um": float(np.sqrt(np.mean(np.sum(dh[mm] ** 2, axis=1))) * 1e6),
                     "P_rail_classB_mW": m["P_rail_classB_mW"], "q_sat_frac": m["q_sat_frac"]})
    return rows


# ------------------------------------------------------------------ aggregation
def aggregate(rows: List[Dict], keys=("label", "f0", "amp_mm"), vals=("ratio", "band_ratio", "q_sat_frac",
                                                                       "P_rail_classB_mW", "P_rail_recovery_mW")) -> Dict:
    out: Dict = {}
    for r in rows:
        k = tuple(r.get(x) for x in keys)
        for v in vals:
            if v in r and r[v] is not None and not (isinstance(r[v], float) and math.isnan(r[v])):
                out.setdefault(k, {}).setdefault(v, []).append(float(r[v]))
    return {k: {v: {"mean": float(np.mean(x)), "sd": float(np.std(x)), "n": len(x)} for v, x in d.items()}
            for k, d in out.items()}
