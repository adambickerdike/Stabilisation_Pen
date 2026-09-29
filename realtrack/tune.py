"""The tuning protocol: rules written here BEFORE any search ran; searches on the tuning split only; the freeze.

RULES (fixed 2026-09-29 before the searches; SIMULATION on the tuning selection set of cases.py, DeltaPen-class page
sensor, the fast surrogate of servo.py; finalists re-run in the full HW1 plant):
  T1  primary objective (lower is better): J = the mean over the SEVERE cases (1.72 mm at the tip, PD and ET, 10
      tuning notes) of the broadband residual ratio: RMS of ink - intended in contact, 0.5-20 Hz, divided by the same
      for the pen with the nose held.  It counts the tremor left in every band and anything the correction adds, so
      in-band gains cannot be bought with out-of-band damage.  R's tip-tremor ratio (f0 +- 2 Hz, to the ordinary pen)
      is reported next to it.
  T2  clean writing: the mean clean-writing change over the 10 tuning notes <= 20 um (a 5 um margin under DEC-055's
      25 um) and every note <= 60 um.
  T3  no harm at small tremor: at the mild (0.098 mm) and moderate (0.24 mm) levels the tip-tremor ratio to the
      nose-held pen <= 1.02 (the tracker must not add tremor; the heavier Rev J pen's own effect is reported apart).
  T4  0.6 mm level: the broadband ratio to the held pen <= 1.00 (no harm inside the severe class's lower part).
  Search: per family, stage 1 tunes the raw estimator (no extra authority) on the severe and 0.6 mm cases for T1;
      stage 2 tunes the soft authority (a_lo, a_hi, tau_amp, tau_up, tau_down, gain) on all cases for T1 under
      T2-T4; families with their own gates (G4, gated) are tuned on all cases directly.  Random search in a fixed box
      (seeded), then two rounds of local perturbation around the best, a fixed number of evaluations per family.
  Choice: among the finalists (the best design of each family that passes T2-T4 in the full-plant re-run), the lowest
      J; if two are within 0.02, the one with the lower MCU cost.  Learned models are scored cross-fitted (fold k's
      cases by a model trained without fold k's writer and patients).  If nothing passes T2-T4, the design with the
      smallest clean-writing change that passes T3 is reported, and DEC-055 is not claimed.
  Freeze: the chosen design, its parameters, the models' checksums and the time are written to
      results/realtrack/frozen.json before test.py runs; test.py refuses to run without it.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, RESULTS_DIR
from . import cases as C
from . import estimators as E
from . import evaluate as EV
from . import servo as SV

TUNE_DIR = BUILD_DIR / "tune"
CLEAN_MEAN_UM = 20.0
CLEAN_MAX_UM = 60.0
SMALL_MAX = 1.02
EDGE_MAX = 1.00


def specs_of(levels: Sequence[str]) -> List[Dict]:
    return [s for s in C.tuning_specs() if s["level"] in levels]


def passes(sm: Dict) -> Dict:
    r = {"T2": sm.get("clean_um_mean", np.inf) <= CLEAN_MEAN_UM and sm.get("clean_um_max", np.inf) <= CLEAN_MAX_UM,
         "T3": sm.get("mild_rheld", np.inf) <= SMALL_MAX and sm.get("moderate_rheld", np.inf) <= SMALL_MAX,
         "T4": sm.get("edge_bb", np.inf) <= EDGE_MAX}
    r["all"] = all(r.values())
    return r


def score(sm: Dict, constrained: bool = True) -> float:
    """T1 with the constraints as penalties (search only; the choice uses passes())."""
    J = sm.get("severe_bb", np.inf)
    if not constrained:
        return J
    pen = 0.0
    pen += max(0.0, sm.get("clean_um_mean", 0.0) - CLEAN_MEAN_UM) / 10.0
    pen += max(0.0, sm.get("clean_um_max", 0.0) - CLEAN_MAX_UM) / 30.0
    pen += max(0.0, sm.get("mild_rheld", 1.0) - SMALL_MAX) * 5.0 + max(0.0, sm.get("moderate_rheld", 1.0) - SMALL_MAX) * 5.0
    pen += max(0.0, sm.get("edge_bb", 1.0) - EDGE_MAX) * 2.0
    return J + pen


# ------------------------------------------------------------------ search spaces
def _lu(rng, lo, hi):
    return float(math.exp(rng.uniform(math.log(lo), math.log(hi))))


def sample(space: Dict, rng) -> Dict:
    out = {}
    for k, v in space.items():
        kind = v[0]
        if kind == "log":
            out[k] = _lu(rng, v[1], v[2])
        elif kind == "lin":
            out[k] = float(rng.uniform(v[1], v[2]))
        elif kind == "int":
            out[k] = int(rng.integers(v[1], v[2] + 1))
        elif kind == "choice":
            out[k] = v[1][int(rng.integers(len(v[1])))]
        else:
            out[k] = v[1]
    return out


def perturb(p: Dict, space: Dict, rng, scale: float = 0.3) -> Dict:
    out = dict(p)
    for k, v in space.items():
        if rng.random() > 0.5:
            continue
        kind = v[0]
        if kind == "log":
            out[k] = float(min(v[2], max(v[1], p[k] * math.exp(rng.normal(0, scale)))))
        elif kind == "lin":
            out[k] = float(min(v[2], max(v[1], p[k] + rng.normal(0, scale) * (v[2] - v[1]) / 3)))
        elif kind == "int":
            out[k] = int(min(v[2], max(v[1], p[k] + int(round(rng.normal(0, 1))))))
        elif kind == "choice":
            out[k] = v[1][int(rng.integers(len(v[1])))] if rng.random() < scale else p[k]
    return out


def random_search(make_design: Callable[[Dict], Dict], space: Dict, specs: Sequence[Dict], n_random: int,
                  n_local: int, seed: int, constrained: bool, log=print, tag: str = "",
                  init: Optional[List[Dict]] = None) -> Dict:
    """Random search then local perturbation; each batch evaluated case by case (every case loaded once per batch)."""
    rng = np.random.default_rng(seed)
    hist = []
    TUNE_DIR.mkdir(parents=True, exist_ok=True)

    def run(params_list):
        ds = []
        for i, p in enumerate(params_list):
            d = make_design(p)
            d["name"] = f"{tag}#{len(hist) + i}"
            d["_p"] = p
            ds.append(d)
        rows = EV.eval_batch(ds, specs, "deltapen", log=lambda *a: None)
        sm = EV.summarize(rows)
        for d in ds:
            s = sm[d["name"]]
            hist.append({"params": d["_p"], "summary": s, "score": score(s, constrained), "name": d["name"]})
        return hist[-len(ds):]

    t0 = time.time()
    first = list(init or []) + [sample(space, rng) for _ in range(n_random)]
    run(first)
    for rnd in range(2):
        best = sorted(hist, key=lambda h: h["score"])[:3]
        cand = []
        for b in best:
            for _ in range(max(1, n_local // 3)):
                cand.append(perturb(b["params"], space, rng, 0.3 if rnd == 0 else 0.15))
        run(cand)
    best = min(hist, key=lambda h: h["score"])
    log(f"[tune] {tag}: {len(hist)} evaluations in {time.time() - t0:.0f} s; best score {best['score']:.3f} "
        f"{json.dumps({k: round(v, 5) if isinstance(v, float) else v for k, v in best['params'].items()})}")
    out = {"tag": tag, "best": best, "history": hist, "space": {k: list(map(str, v)) for k, v in space.items()},
           "seed": seed, "elapsed_s": time.time() - t0}
    (TUNE_DIR / f"{tag}.json").write_text(json.dumps(out, default=float))
    return out


def load_search(tag: str) -> Optional[Dict]:
    p = TUNE_DIR / f"{tag}.json"
    return json.loads(p.read_text()) if p.exists() else None


# ------------------------------------------------------------------ stage 2: the soft authority on cached raw estimates
AUTH_SPACE = {"a_lo": ("log", 0.2e-3, 2.0e-3), "a_hi": ("log", 0.4e-3, 4.0e-3), "tau_amp": ("log", 0.05, 1.5),
              "tau_up": ("log", 0.01, 0.5), "tau_down": ("log", 0.02, 2.0), "gain": ("lin", 0.6, 1.3)}


def auth_search(design: Dict, n_random: int = 60, n_local: int = 30, seed: int = 11, log=print, tag: str = "",
                conf_fn: Optional[Callable] = None, conf_space: Optional[Dict] = None) -> Dict:
    """Stage 2: the raw estimate of `design` on every tuning case once (kept in memory), then the soft authority's
    parameters by random search + local perturbation under T2-T4 (score with penalties)."""
    specs = C.tuning_specs()
    rng = np.random.default_rng(seed)
    raw = []
    t0 = time.time()
    pp = SV.pen_params()
    for s in specs:
        case = C.load_case(s)
        st = case.streams("deltapen")
        d, info = E.raw_estimate(design["family"], st, design.get("params"), horizon=design.get("horizon"),
                                 case=case, sensor="deltapen")
        conf = conf_fn(case, st) if conf_fn else None
        raw.append((s, d.astype(np.float64), conf, _light(case)))
        del case, st
    log(f"[auth] {tag}: raw estimates on {len(specs)} cases in {time.time() - t0:.0f} s")
    hist = []

    def run(plist):
        for p in plist:
            if p["a_hi"] <= p["a_lo"]:
                p["a_hi"] = p["a_lo"] * 1.5
            if "r_hi" in p and p["r_hi"] <= p["r_lo"]:
                p["r_hi"] = p["r_lo"] * 1.5
            rows = []
            for s, d, conf, lc in raw:
                Ts = float(lc.meta["Ts"])
                c = None if conf is None else E.conf_from_ratio(conf, p["r_lo"], p["r_hi"])
                dh, g, A = E.authority(d, Ts, p, c)
                m = SV.fast_measures(lc, -dh, pp)
                m.update({"design": "x", "case": s["id"], "level": s["level"], "kind": s.get("kind"),
                          "auth_mean": float(np.mean(g[lc.arrays["down_ticks"] > 0.5]))})
                rows.append(m)
            sm = EV.summarize(rows)["x"]
            hist.append({"params": dict(p), "summary": sm, "score": score(sm, True)})

    space = dict(AUTH_SPACE)
    space.update(conf_space or {})
    raw_p = {"a_lo": 0.0, "a_hi": 0.0, "tau_amp": 0.3, "tau_up": 0.005, "tau_down": 0.005, "gain": 1.0}
    if conf_space:
        raw_p.update({"r_lo": 0.0, "r_hi": 1e-9})
    run([raw_p] + [sample(space, rng) for _ in range(n_random)])        # history[0] = the estimator without a gate
    for rnd in range(2):
        best = sorted(hist, key=lambda h: h["score"])[:3]
        run([perturb(b["params"], space, rng, 0.3 if rnd == 0 else 0.15) for b in best
             for _ in range(max(1, n_local // 3))])
    best = min(hist, key=lambda h: h["score"])
    log(f"[auth] {tag}: {len(hist)} authority settings in {time.time() - t0:.0f} s; best score {best['score']:.3f}; "
        + json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in best['summary'].items()
                      if k in ('severe_bb', 'severe_ratio', 'edge_bb', 'moderate_rheld', 'mild_rheld', 'clean_um_mean',
                               'clean_um_max')}))
    out = {"tag": tag, "design": design, "best": best, "history": hist, "elapsed_s": time.time() - t0}
    TUNE_DIR.mkdir(parents=True, exist_ok=True)
    (TUNE_DIR / f"auth_{tag}.json").write_text(json.dumps(out, default=float))
    return out


class _LightCase:
    def __init__(self, spec, meta, arrays):
        self.spec, self.meta, self.arrays = spec, meta, arrays

    @property
    def tick_t(self):
        return self.arrays["i_tick_t"]


def _light(case):
    keep = ("t1k", "handle1k", "intended1k", "contact1k", "active_ticks", "down_ticks", "i_tick_t")
    return _LightCase(case.spec, case.meta, {k: case.arrays[k] for k in keep})
