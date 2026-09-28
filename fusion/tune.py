"""Parameter search for the conventional estimators on the tuning seeds only (SIMULATION).

Seeds: fusion.TUNE_SEEDS (5000-5007), scenarios.handwriting as the test grid (same generator,
disjoint seeds), the full grid 4-12 Hz x 0.1/0.3/0.5 mm and the tremor-free writing of each seed.
Never the test seeds 200-203.

Proxy objective (open loop, fast): for each tremor condition the residual ratio
    RR = sqrt(sum |d - clip(d_hat)|^2 / sum |d|^2)   over in-contact ticks after 0.5 s,
with d the oracle's disturbance (p_H tremor run - p_H clean run), d_hat clipped to the 0.30 mm stage
radius; J = mean RR + 8 mean(HF / |d|) + 2 max(0, FC / FC_max - 1), where HF is the RMS of d_hat above
150 Hz (estimate jitter near the 192 Hz stage resonance dithers the pen's friction in P1 and shifts the
housing path; results/fusion/sensors.json jitter_check quantifies it on tuning seeds),
FC the RMS of d_hat on the tremor-free writing (false correction) and FC_max the frozen Kalman filter's
FC on the same runs (matched distortion, as ml/ tunes its baselines).  Random search, then a local refinement around the best
candidates; the best candidate is then checked in closed loop on tuning seeds 5000-5003
(results/fusion/tuning.json).

Robust variant (`search_robust`): the same search with the aiguide TUNING writers 100-105 (glyph
handwriting, about 3x the tremor-band writing content of the grid's sigma-lognormal writing) added:
J = 0.5 RR_grid + 0.5 RR_aiguide + HF and false-correction hinges on both (30 um on the glyph writing).
"""
from __future__ import annotations

import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import TUNE_SEEDS
from . import data as FD
from . import estimators as ES
from . import harness as H
from . import sensors as S

CLIP = 0.30e-3


# ------------------------------------------------------------------ search spaces
def _lu(rng, lo, hi):
    return float(math.exp(rng.uniform(math.log(lo), math.log(hi))))


ALIAS = {"kfosclp": "kfosc", "akfx": "akf", "akfc": "akf", "wflcx": "wflc"}     # search variants of the same estimator


def sample(name: str, rng) -> Dict:
    if name == "akfx":                      # AKF with the cross-track-only output option
        p = sample("akf", rng)
        p["xtrack"] = float(rng.random() < 0.5)
        p["v_xt"] = _lu(rng, 1e-3, 20e-3)
        return p
    if name == "akfc":                      # AKF with the slow-motion amplitude reference cap (and the cross-track option)
        p = sample("akfx", rng)
        p["cap_k"] = float(rng.uniform(0.8, 3.0))
        p["v_slow"] = _lu(rng, 1e-3, 20e-3)
        p["tau_ref"] = _lu(rng, 0.2, 2.0)
        return p
    if name == "wflcx":
        return sample("wflc", rng)
    if name == "akf":
        harm = float(rng.random() < 0.5)
        p = {"qj": _lu(rng, 1e-3, 1e2), "qt": _lu(rng, 1e-10, 1e-6), "qb": _lu(rng, 1e-9, 1e-3),
             "ra": _lu(rng, 1e-5, 1e-1), "rp": _lu(rng, 1e-12, 1e-9), "tau_decay": _lu(rng, 0.1, 3.0),
             "tau_w": _lu(rng, 0.05, 1.0), "wmin_hz": float(rng.uniform(2.5, 5.0)), "horizon": float(rng.uniform(0.0, 3e-3)),
             "g": float(rng.uniform(0.6, 1.2)), "tau_amp": _lu(rng, 0.05, 0.5), "harm": harm, "lp_hz": _lu(rng, 25.0, 150.0)}
        p["qh"] = p["qt"] * 10 ** rng.uniform(-3, 0)
        if rng.random() < 0.5:
            p["f_gate"] = float(rng.uniform(3.5, 9.0)); p["f_gate_w"] = float(rng.uniform(1.0, 3.0))
        if rng.random() < 0.6:
            p["a_lo"] = float(rng.uniform(0.0, 80e-6)); p["a_hi"] = p["a_lo"] + float(rng.uniform(10e-6, 150e-6))
        return p
    if name in ("kfosc", "kfosclp"):
        p = {"qj": _lu(rng, 1e-3, 1e2), "qt": _lu(rng, 1e-10, 1e-6), "r": _lu(rng, 1e-12, 1e-9),
             "tau_decay": _lu(rng, 0.1, 3.0), "tau_w": _lu(rng, 0.05, 1.0), "horizon": float(rng.uniform(0.0, 3e-3)),
             "g": float(rng.uniform(0.6, 1.2)), "nis_hi": float(rng.uniform(2.0, 50.0))}
        p["f_gate"] = float(rng.uniform(3.5, 9.0)) if rng.random() < 0.6 else 0.0
        p["f_gate_w"] = float(rng.uniform(1.0, 3.0))
        p["lp_hz"] = _lu(rng, 20.0, 150.0) if name == "kfosclp" else 0.0
        return p
    if name == "bmflc":
        p = {"mu": _lu(rng, 1e-4, 0.05), "f_lo": float(rng.uniform(3.0, 6.0)), "f_hi": float(rng.uniform(12.0, 16.0)),
             "df": float(rng.choice([0.25, 0.5, 1.0])), "hp_hz": _lu(rng, 1.0, 6.0), "lp_hz": _lu(rng, 15.0, 45.0),
             "horizon": float(rng.uniform(0.0, 3e-3)), "g": float(rng.uniform(0.4, 1.2)), "tau_amp": _lu(rng, 0.05, 0.5),
             "out_lp_hz": _lu(rng, 25.0, 150.0)}
        if rng.random() < 0.6:
            p["a_lo"] = float(rng.uniform(0.0, 80e-6)); p["a_hi"] = p["a_lo"] + float(rng.uniform(10e-6, 150e-6))
        return p
    if name == "wflc":
        p = {"mu": _lu(rng, 2e-4, 0.02), "mu0": _lu(rng, 2e-3, 0.1), "hp_hz": _lu(rng, 1.0, 6.0), "lp_hz": _lu(rng, 15.0, 45.0),
             "harm": float(rng.random() < 0.5), "horizon": float(rng.uniform(0.0, 3e-3)), "g": float(rng.uniform(0.4, 1.2)),
             "tau_amp": _lu(rng, 0.05, 0.5), "w0_hz": 7.0, "out_lp_hz": _lu(rng, 25.0, 150.0)}
        if rng.random() < 0.6:
            p["a_lo"] = float(rng.uniform(0.0, 80e-6)); p["a_hi"] = p["a_lo"] + float(rng.uniform(10e-6, 150e-6))
        if rng.random() < 0.4:
            p["f_gate"] = float(rng.uniform(3.5, 9.0)); p["f_gate_w"] = float(rng.uniform(1.0, 3.0))
        return p
    raise KeyError(name)


LOG_KEYS = {"qj", "qt", "qh", "qb", "ra", "rp", "r", "tau_decay", "tau_w", "mu", "mu0", "hp_hz", "lp_hz", "tau_amp", "nis_hi",
            "out_lp_hz", "sigma_t", "q_tb", "tb0", "v_xt", "v_slow", "tau_ref"}


def perturb(p: Dict, rng, scale: float = 0.3) -> Dict:
    q = dict(p)
    keys = [k for k in p if k not in ("harm", "w0_hz", "df", "xtrack")]
    for k in rng.choice(keys, size=max(1, len(keys) // 3), replace=False):
        v = q[k]
        if k in LOG_KEYS and v > 0:
            q[k] = float(v * math.exp(rng.normal(0.0, scale * 2.0)))
        elif k in ("horizon",):
            q[k] = float(np.clip(v + rng.normal(0.0, scale * 1e-3), 0.0, 4e-3))
        elif k in ("a_lo", "a_hi"):
            q[k] = float(max(0.0, v + rng.normal(0.0, scale * 30e-6)))
        else:
            q[k] = float(v * (1.0 + rng.normal(0.0, scale * 0.5)))
    if "a_lo" in q and "a_hi" in q and q["a_hi"] <= q["a_lo"]:
        q["a_hi"] = q["a_lo"] + 10e-6
    return q


# ------------------------------------------------------------------ data
def conditions(seeds: Sequence[int] = TUNE_SEEDS) -> List[Tuple[int, float, float]]:
    return [(s, f0, a) for s in seeds for f0 in H.F0S for a in H.AMPS]


def _prep(c):
    FD.test_pair_records(*c)
    return c


def prepare(seeds: Sequence[int] = TUNE_SEEDS, workers: int = 2):
    conds = conditions(seeds)
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            list(ex.map(_prep, conds))
    else:
        for c in conds:
            _prep(c)
    return conds


_DATA: Dict = {}


def load(sensor_kw: Dict, seeds: Sequence[int] = TUNE_SEEDS):
    """Streams of every tuning condition and of each seed's clean run (kept in the process)."""
    key = (json.dumps(sensor_kw, sort_keys=True), tuple(seeds))
    if key in _DATA:
        return _DATA[key]
    cfg = S.config(**sensor_kw)
    items, clean = [], []
    for (s, f0, a) in conditions(seeds):
        r1, r0 = FD.test_pair_records(s, f0, a)
        st = S.make_streams(r1, cfg, H.sensor_seed(s, f0, a, 7))
        d = S.truth_at(st.tick_t, r1, r0)
        con = np.interp(st.tick_t, r1.t, r1.contact) > 0.5
        m = con & (st.tick_t > 0.5)
        items.append({"cond": (s, f0, a), "st": st, "d": d, "m": m})
    for s in seeds:
        r1, r0 = FD.test_pair_records(s, H.F0S[0], H.AMPS[0])
        st = S.make_streams(r0, cfg, H.sensor_seed(s, 0.0, 0.0, 8))
        con = np.interp(st.tick_t, r0.t, r0.contact) > 0.5
        clean.append({"seed": s, "st": st, "m": con & (st.tick_t > 0.5)})
    _DATA[key] = (items, clean)
    return _DATA[key]


def _clip(dh, lim=CLIP):
    r = np.linalg.norm(dh, axis=1)
    f = np.minimum(1.0, lim / np.maximum(r, 1e-12))
    return dh * f[:, None]


_HP = {}


def _hf_rms(dh, m, fs=2000.0, fc=150.0):
    if fc not in _HP:
        from scipy.signal import butter
        _HP[fc] = butter(4, fc, btype="high", fs=fs, output="sos")
    from scipy.signal import sosfilt
    h = sosfilt(_HP[fc], dh, axis=0)
    return float(np.sqrt(np.mean(np.sum(h[m] ** 2, axis=1))))


def proxy(name: str, params: Dict, sensor_kw: Dict, fc_max: Optional[float] = None, seeds=TUNE_SEEDS,
          lam_hf: float = 8.0) -> Dict:
    name = ALIAS.get(name, name)                        # the same estimator, searched with an extra option
    items, clean = load(sensor_kw, seeds)
    rr, hf = [], []
    for it in items:
        dh, _ = ES.run_estimator(name, it["st"], params)
        m = it["m"]
        e = it["d"][m] - _clip(dh[m])
        dn = max(float(np.sqrt(np.mean(np.sum(it["d"][m] ** 2, axis=1)))), 1e-12)
        rr.append(math.sqrt(np.sum(e ** 2) / max(np.sum(it["d"][m] ** 2), 1e-30)))
        hf.append(_hf_rms(dh, m) / dn)
    fc = []
    for c in clean:
        dh, _ = ES.run_estimator(name, c["st"], params)
        fc.append(float(np.sqrt(np.mean(np.sum(dh[c["m"]] ** 2, axis=1)))))
    rr = np.array(rr)
    fcm = float(np.mean(fc))
    J = float(np.mean(rr)) + lam_hf * float(np.mean(hf))
    if not np.isfinite(J):
        J = 10.0
    if fc_max is not None:
        J += 2.0 * max(0.0, fcm / fc_max - 1.0)
    by = {}
    for it, r in zip(items, rr):
        s, f0, a = it["cond"]
        by.setdefault(f"{f0:g}Hz_{a * 1e3:g}mm", []).append(float(r))
    return {"J": J, "rr_mean": float(np.mean(rr)), "hf_rel_mean": float(np.mean(hf)), "fc_um": fcm * 1e6,
            "rr_by_cond": {k: float(np.mean(v)) for k, v in by.items()}}


_W: Dict = {}


def _init_worker(name, sensor_kw, fc_max, seeds):
    _W.update(name=name, sensor_kw=sensor_kw, fc_max=fc_max, seeds=seeds)
    load(sensor_kw, seeds)


def _eval(p):
    try:
        r = proxy(_W["name"], p, _W["sensor_kw"], _W["fc_max"], _W["seeds"])
    except Exception as exc:  # pragma: no cover (a failing candidate is scored out)
        r = {"J": 10.0, "error": repr(exc)}
    r["params"] = p
    return r


def search(name: str, sensor_kw: Dict, n_random: int = 160, n_local: int = 80, workers: int = 2, seed: int = 11,
           fc_max: Optional[float] = None, seeds=TUNE_SEEDS, start: Optional[List[Dict]] = None, log=print) -> Dict:
    rng = np.random.default_rng(seed)
    cands = list(start or []) + [sample(name, rng) for _ in range(n_random)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(name, sensor_kw, fc_max, seeds)) as ex:
        res = list(ex.map(_eval, cands))
        res.sort(key=lambda r: r["J"])
        log(f"[tune {name} {sensor_kw}] random {len(cands)}: best J {res[0]['J']:.4f} rr {res[0].get('rr_mean')} "
            f"fc {res[0].get('fc_um')} ({time.time() - t0:.0f} s)")
        rounds = 4
        per = max(1, n_local // rounds)
        for rd in range(rounds):
            elite = res[:5]
            local = [perturb(elite[i % len(elite)]["params"], rng, scale=0.3 / (1 + rd)) for i in range(per)]
            res = sorted(res + list(ex.map(_eval, local)), key=lambda r: r["J"])
            log(f"[tune {name}] local round {rd + 1}: best J {res[0]['J']:.4f} rr {res[0].get('rr_mean')} fc {res[0].get('fc_um')} "
                f"({time.time() - t0:.0f} s)")
    return {"best": res[0], "top": res[:8], "n_evaluated": len(res), "elapsed_s": time.time() - t0,
            "objective": "mean residual ratio (open loop, clipped at 0.30 mm) + 8 mean(RMS above 150 Hz / RMS d) + 2 max(0, FC/FC_max - 1)",
            "fc_max_um": None if fc_max is None else fc_max * 1e6}


# ------------------------------------------------------------------ closed-loop check on the tuning seeds
def _closed(args):
    specs, c = args
    rows = H.case(*c, specs, with_internal_kfosc=False, with_band_oracle=False)
    return [r for r in rows if r["label"] in {sp.label for sp in specs}]


def _closed_dist(args):
    specs, s = args
    return [r for r in H.distortion(s, specs) if r["label"] in {sp.label for sp in specs}]


def closed_loop_check(specs: Sequence[H.Spec], seeds=TUNE_SEEDS[:4], workers: int = 2, f0s=H.F0S, amps=H.AMPS) -> Dict:
    """Closed-loop mean ratio (harness convention) and distortion of each spec on tuning seeds."""
    conds = [(s, f0, a) for s in seeds for f0 in f0s for a in amps]
    specs = list(specs)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = [r for rr in ex.map(_closed, [(specs, c) for c in conds]) for r in rr]
        dist = [r for rr in ex.map(_closed_dist, [(specs, s) for s in seeds]) for r in rr]
    out = {}
    for spec in specs:
        R = [r for r in rows if r["label"] == spec.label]
        D = [d for d in dist if d["label"] == spec.label]
        out[spec.label] = {"ratio_mean": float(np.mean([r["ratio"] for r in R])),
                           "band_ratio_mean": float(np.mean([r["band_ratio"] for r in R])),
                           "distortion_um": float(np.mean([d["distortion_um"] for d in D])),
                           "q_sat_mean": float(np.mean([r["q_sat_frac"] for r in R])),
                           "ratio_by_cond": {f"{f0:g}Hz_{a * 1e3:g}mm": float(np.mean([r["ratio"] for r in R if r["f0"] == f0 and abs(r["amp_mm"] - a * 1e3) < 1e-9]))
                                             for f0 in f0s for a in amps}}
    return out


# ------------------------------------------------------------------ robust tuning: grid tuning seeds + aiguide tuning writers
AI_TUNE = ((100, 5.0), (101, 7.0), (102, 9.0), (103, 6.0), (104, 8.0), (105, 4.5))


def aiguide_items(sensor_kw: Dict, jobs=AI_TUNE) -> List[Dict]:
    """Tremor run (streams, truth) and tremor-free run (streams) of aiguide TUNING writers (100-105, never 0-5), 0.3 mm."""
    from . import aieval as AE
    cfg = S.config(**sensor_kw)
    out = []
    for w, f0 in jobs:
        su = AE.setup(w, f0)
        r1 = S.record_from_result(su["neutral"], su["scn"])
        r0 = S.record_from_result(su["clean"], su["scn0"])
        st = S.make_streams(r1, cfg, 800_000 + 1000 * w + int(f0))
        st0 = S.make_streams(r0, cfg, 810_000 + 1000 * w + int(f0))
        d = S.truth_at(st.tick_t, r1, r0)
        m = (np.interp(st.tick_t, r1.t, r1.contact) > 0.5) & (st.tick_t > 0.5)
        m0 = (np.interp(st0.tick_t, r0.t, r0.contact) > 0.5) & (st0.tick_t > 0.5)
        out.append({"writer": w, "f0": f0, "st": st, "d": d, "m": m, "st0": st0, "m0": m0,
                    "templates": AE.context_templates(su)})
    return out


FC_AI_MAX = 30e-6      # ASSUMPTION: distortion allowed on tremor-free glyph writing (about 1 % of a 2-3 mm x-height)


def proxy_robust(name: str, params: Dict, sensor_kw: Dict, ai: List[Dict], fc_max: Optional[float] = None,
                 seeds=TUNE_SEEDS, lam_hf: float = 8.0, fc_ai_max: float = FC_AI_MAX) -> Dict:
    """J = 0.5 RR_grid + 0.5 RR_aiguide + 8 HF + 2 max(0, FC_grid / FC_max - 1) + 2 max(0, FC_aiguide / FC_ai_max - 1)."""
    g = proxy(name, params, sensor_kw, fc_max, seeds, lam_hf)
    nm = ALIAS.get(name, name)
    rr, fcr, fca = [], [], []
    for it in ai:
        dh, _ = ES.run_estimator(nm, it["st"], params)
        m = it["m"]
        dn = float(np.sqrt(np.mean(np.sum(it["d"][m] ** 2, axis=1))))
        rr.append(math.sqrt(np.sum((it["d"][m] - _clip(dh[m])) ** 2) / max(np.sum(it["d"][m] ** 2), 1e-30)))
        dh0, _ = ES.run_estimator(nm, it["st0"], params)
        fc_ = float(np.sqrt(np.mean(np.sum(dh0[it["m0"]] ** 2, axis=1))))
        fca.append(fc_)
        fcr.append(fc_ / max(dn, 1e-12))
    fc_ai = float(np.mean(fca))
    J = 0.5 * g["rr_mean"] + 0.5 * float(np.mean(rr)) + lam_hf * g["hf_rel_mean"] + 2.0 * max(0.0, fc_ai / fc_ai_max - 1.0)
    if fc_max is not None:
        J += 2.0 * max(0.0, g["fc_um"] * 1e-6 / fc_max - 1.0)
    if not np.isfinite(J):
        J = 10.0
    return dict(g, J=J, J_grid=g["J"], rr_ai_mean=float(np.mean(rr)), fc_ai_rel_mean=float(np.mean(fcr)), fc_ai_um=fc_ai * 1e6,
                rr_ai=[float(x) for x in rr])


def _init_worker_robust(name, sensor_kw, fc_max, seeds, ai):
    _W.update(name=name, sensor_kw=sensor_kw, fc_max=fc_max, seeds=seeds, ai=ai)
    load(sensor_kw, seeds)


def _eval_robust(p):
    try:
        r = proxy_robust(_W["name"], p, _W["sensor_kw"], _W["ai"], _W["fc_max"], _W["seeds"])
    except Exception as exc:  # pragma: no cover
        r = {"J": 10.0, "error": repr(exc)}
    r["params"] = p
    return r


def search_robust(name: str, sensor_kw: Dict, n_random: int = 160, n_local: int = 80, workers: int = 2, seed: int = 31,
                  fc_max: Optional[float] = None, start: Optional[List[Dict]] = None, log=print) -> Dict:
    """As `search`, with the robust objective (grid tuning seeds + aiguide tuning writers)."""
    rng = np.random.default_rng(seed)
    ai = aiguide_items(sensor_kw)
    for it in ai:
        it.pop("templates", None)
    cands = list(start or []) + [sample(name, rng) for _ in range(n_random)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker_robust,
                             initargs=(name, sensor_kw, fc_max, TUNE_SEEDS, ai)) as ex:
        res = sorted(ex.map(_eval_robust, cands), key=lambda r: r["J"])
        log(f"[robust {name} {sensor_kw}] random {len(cands)}: best J {res[0]['J']:.4f} rr_grid {res[0].get('rr_mean')} "
            f"rr_ai {res[0].get('rr_ai_mean')} fc_ai_um {res[0].get('fc_ai_um')} fc_grid_um {res[0].get('fc_um')} ({time.time() - t0:.0f} s)")
        rounds = 4
        per = max(1, n_local // rounds)
        for rd in range(rounds):
            elite = res[:5]
            local = [perturb(elite[i % len(elite)]["params"], rng, scale=0.3 / (1 + rd)) for i in range(per)]
            res = sorted(res + list(ex.map(_eval_robust, local)), key=lambda r: r["J"])
            log(f"[robust {name}] local round {rd + 1}: best J {res[0]['J']:.4f} rr_grid {res[0].get('rr_mean')} "
                f"rr_ai {res[0].get('rr_ai_mean')} fc_ai_um {res[0].get('fc_ai_um')} fc_grid_um {res[0].get('fc_um')} ({time.time() - t0:.0f} s)")
    return {"best": res[0], "top": res[:8], "n_evaluated": len(res), "elapsed_s": time.time() - t0,
            "objective": "0.5 RR_grid + 0.5 RR_aiguide + 8 HF/RMS(d) + 2 max(0, FC_grid/FC_max - 1) + 2 max(0, FC_aiguide/30 um - 1); "
                         "grid tuning seeds 5000-5007 (15 conditions each), aiguide tuning writers 100-105 at 4.5-9 Hz, 0.3 mm",
            "aiguide_tuning": [list(x) for x in AI_TUNE], "fc_max_um": None if fc_max is None else fc_max * 1e6}
