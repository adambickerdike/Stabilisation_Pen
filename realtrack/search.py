"""The families' search boxes and the stage drivers of tune.py's protocol (tuning split only; SIMULATION).

Stage 1: each classical family's raw estimator (no extra authority) on the severe cases, objective T1 (broadband
residual ratio to the nose-held pen).  Boxes (fixed before the runs) span the literature's and the programme's values:
  akf       the AKF of fusion (the Rev H tracker's model) in its 'listening' form: output gates off, tremor process noise
            qt, harmonic ratio, intent jerk qj, accelerometer noise ra, oscillator decay, frequency smoothing tau_w,
            harmonic weight, output low-pass, page sensor used or not, horizon offset
  wflc      fusion's WFLC (LIT ACT-08): weight and frequency steps, band, pre-filter, harmonic, output low-pass, horizon
  bmflc     fusion's BMFLC (LIT ACT-09/10): step, band and spacing, pre-filter, output low-pass, horizon
  bmflc_kf  BMFLC with Kalman weights (LIT ACT-09): process/measurement ratio, band and spacing, pre-filter, rate,
            horizon
  epll      the EPLL / adaptive-oscillator tracker: amplitude, frequency and phase gains, harmonic on/off, pre-filter,
            horizon
Stage 2: the soft authority (tune.auth_search) on the best raw design of each family, amplitude-only and amplitude x
  the detector's continuous line confidence.
"""
from __future__ import annotations

import json
from typing import Dict, List

from . import estimators as E
from . import tune as TU

LISTEN = None


def _listen() -> Dict:
    global LISTEN
    if LISTEN is None:
        LISTEN = E.listening_params()
    return dict(LISTEN)


def akf_design(p: Dict) -> Dict:
    q = _listen()
    q.update({"qt": p["qt"], "qh": p["qt"] * p["qh_ratio"], "qj": p["qj"], "ra": p["ra"], "tau_decay": p["tau_decay"],
              "tau_w": p["tau_w"], "harm": p["harm"], "lp_hz": p["lp_hz"], "use_pos": float(p["use_pos"]),
              "horizon": p["hx"]})
    return {"family": "akf", "params": q}


def flc_design(mode: str):
    def f(p: Dict) -> Dict:
        q = {"mu": p["mu"], "f_lo": p["f_lo"], "f_hi": p["f_hi"], "hp_hz": p["hp_hz"], "lp_hz": p["lp_hz"],
             "out_lp_hz": p["out_lp_hz"], "horizon": p["hx"], "g": 1.0, "w0_hz": 6.0}
        if mode == "wflc":
            q.update({"mu0": p["mu0"], "harm": p["harm"]})
        else:
            q.update({"df": p["df"]})
        return {"family": mode, "params": q}
    return f


def bmflc_kf_design(p: Dict) -> Dict:
    return {"family": "bmflc_kf", "params": {"q": p["q"], "r": 1.0, "p0": 1.0, "df": p["df"], "f_lo": p["f_lo"],
                                              "f_hi": p["f_hi"], "hp_hz": p["hp_hz"], "lp_hz": p["lp_hz"],
                                              "decim": p["decim"], "horizon_extra": p["hx"]}}


def epll_design(p: Dict) -> Dict:
    return {"family": "epll", "params": {"mu_a": p["mu_a"], "mu_w": p["mu_w"], "mu_p": p["mu_p"], "harm": p["harm"],
                                          "hp_hz": p["hp_hz"], "lp_hz": p["lp_hz"], "f_lo": 3.0, "f_hi": 12.0,
                                          "f0": 6.0, "horizon_extra": p["hx"]}}


HX = ("lin", -0.002, 0.004)
SPACES = {
    "akf": (akf_design, {"qt": ("log", 1e-10, 1e-6), "qh_ratio": ("log", 0.1, 1.0), "qj": ("log", 1e-3, 10.0),
                         "ra": ("log", 0.01, 1.0), "tau_decay": ("log", 0.1, 5.0), "tau_w": ("log", 0.03, 1.0),
                         "harm": ("lin", 0.0, 1.0), "lp_hz": ("log", 20.0, 150.0), "use_pos": ("choice", (0, 1)),
                         "hx": HX}),
    "wflc": (flc_design("wflc"), {"mu": ("log", 1e-4, 0.05), "mu0": ("log", 1e-4, 0.3), "f_lo": ("lin", 2.5, 4.0),
                                  "f_hi": ("lin", 9.0, 14.0), "hp_hz": ("lin", 1.0, 3.0), "lp_hz": ("log", 10.0, 40.0),
                                  "harm": ("lin", 0.0, 1.0), "out_lp_hz": ("log", 20.0, 150.0), "hx": HX}),
    "bmflc": (flc_design("bmflc"), {"mu": ("log", 1e-4, 0.05), "df": ("choice", (0.25, 0.5, 1.0)),
                                    "f_lo": ("lin", 2.5, 4.0), "f_hi": ("lin", 9.0, 14.0), "hp_hz": ("lin", 1.0, 3.0),
                                    "lp_hz": ("log", 10.0, 40.0), "out_lp_hz": ("log", 20.0, 150.0), "hx": HX}),
    "bmflc_kf": (bmflc_kf_design, {"q": ("log", 1e-7, 1e-1), "df": ("choice", (0.25, 0.5, 1.0)),
                                   "f_lo": ("lin", 2.5, 4.0), "f_hi": ("lin", 9.0, 14.0), "hp_hz": ("lin", 1.0, 4.0),
                                   "lp_hz": ("log", 10.0, 40.0), "decim": ("choice", (2, 4)), "hx": HX}),
    "epll": (epll_design, {"mu_a": ("log", 1e-4, 0.1), "mu_w": ("log", 1.0, 1e5), "mu_p": ("log", 0.1, 500.0),
                           "harm": ("choice", (0.0, 1.0)), "hp_hz": ("lin", 1.0, 4.0), "lp_hz": ("log", 10.0, 40.0),
                           "hx": HX}),
}
INIT = {   # the literature's / programme's own settings as starting points (the search also samples the box)
    "akf": [{"qt": 1e-9, "qh_ratio": 0.333, "qj": 0.0275, "ra": 0.075, "tau_decay": 2.0, "tau_w": 0.4, "harm": 0.88,
             "lp_hz": 64.13, "use_pos": 1, "hx": 0.0}],
    "wflc": [{"mu": 0.002, "mu0": 0.02, "f_lo": 3.0, "f_hi": 14.0, "hp_hz": 2.5, "lp_hz": 20.0, "harm": 1.0,
              "out_lp_hz": 60.0, "hx": 0.0015}],
    "bmflc": [{"mu": 0.002, "df": 0.5, "f_lo": 3.0, "f_hi": 14.0, "hp_hz": 2.5, "lp_hz": 20.0, "out_lp_hz": 60.0,
               "hx": 0.0015}],
    "bmflc_kf": [{"q": 1e-3, "df": 0.5, "f_lo": 3.0, "f_hi": 12.0, "hp_hz": 2.0, "lp_hz": 20.0, "decim": 2, "hx": 0.0}],
    "epll": [{"mu_a": 0.01, "mu_w": 2000.0, "mu_p": 30.0, "harm": 1.0, "hp_hz": 2.0, "lp_hz": 20.0, "hx": 0.0}],
}
N_RANDOM = 24
N_LOCAL = 12


def stage1(families=("akf", "wflc", "bmflc", "bmflc_kf", "epll"), log=print) -> Dict[str, Dict]:
    specs = TU.specs_of(("severe",))
    out = {}
    for fam in families:
        tag = f"s1_{fam}"
        prev = TU.load_search(tag)
        if prev is not None:
            out[fam] = prev
            log(f"[stage1] {fam}: cached, best {prev['best']['score']:.3f}")
            continue
        mk, space = SPACES[fam]
        out[fam] = TU.random_search(mk, space, specs, N_RANDOM, N_LOCAL, seed=sum(map(ord, fam)) + 7,
                                    constrained=False, log=log, tag=tag, init=INIT.get(fam))
    return out


def best_design(fam: str) -> Dict:
    s = TU.load_search(f"s1_{fam}")
    mk, _ = SPACES[fam]
    d = mk(s["best"]["params"])
    d["name"] = f"{fam}_s1"
    return d


# ======================================================================================== retuned binary gate (fast)
from typing import Optional  # noqa: E402

import numpy as np  # noqa: E402

DET_CONFIGS = {   # detector windows and bands searched (ai2's own first; fixed before the runs)
    "ai2": {"win": 4.0, "seg": 2.0, "band_lo": 4.5, "band_hi": 13.5},
    "wide": {"win": 4.0, "seg": 2.0, "band_lo": 3.5, "band_hi": 12.0},
    "short": {"win": 2.0, "seg": 1.0, "band_lo": 3.5, "band_hi": 12.0},
}
GATE_SPACE = {"det": ("choice", tuple(DET_CONFIGS)), "r_on": ("log", 1.5, 10.0), "r_off_frac": ("lin", 0.3, 0.9),
              "t_on": ("log", 0.05, 1.0), "t_off": ("log", 0.1, 2.0), "ramp": ("log", 0.05, 0.5),
              "amp_lo": ("log", 0.05e-3, 1.0e-3), "amp_hi_mult": ("log", 1.2, 4.0), "fallback": ("choice", ("revh", "none")),
              "gain": ("lin", 0.6, 1.3)}


def hyst_gate(t_up, ratio, amp, p: Dict, every: float = 0.05) -> np.ndarray:
    """ai2.smoothers.detector's hysteresis gate (same statements) x the amplitude gate on the line amplitude, per
    detector update."""
    r_on = p["r_on"]
    r_off = p["r_on"] * p["r_off_frac"]
    n_on = max(1, int(round(p["t_on"] / every))); n_off = max(1, int(round(p["t_off"] / every)))
    stt = False; c_on = 0; c_off = 0
    a = min(1.0, every / max(p["ramp"], 1e-9))
    gv = 0.0
    g = np.zeros(len(ratio))
    for i, x in enumerate(ratio):
        if not stt:
            c_on = c_on + 1 if x > r_on else 0
            if c_on >= n_on:
                stt = True; c_off = 0
        else:
            c_off = c_off + 1 if x < r_off else 0
            if c_off >= n_off:
                stt = False; c_on = 0
        gv = min(1.0, gv + a) if stt else max(0.0, gv - a)
        g[i] = gv
    lo = p["amp_lo"]; hi = p["amp_lo"] * p["amp_hi_mult"]
    return g * np.clip((amp - lo) / (hi - lo), 0.0, 1.0)


def gate_search(D_design: Dict, n_random: int = 60, n_local: int = 30, seed: int = 23, tag: str = "gate",
                log=print) -> Dict:
    """Search the binary (hysteresis) gate on cached per-case detector outputs; command = g D + (1 - g) fb, fb the
    Rev H tracker as built (R's gated tracker) or nothing."""
    from . import cases as C
    from . import evaluate as EV
    from . import servo as SV
    from ai2 import smoothers as SM
    import time
    import json
    rng = np.random.default_rng(seed)
    pp = SV.pen_params()
    t0 = time.time()
    data = []
    for s in C.tuning_specs():
        case = C.load_case(s)
        st = case.streams("deltapen")
        D, _ = E.raw_estimate(D_design["family"], st, D_design.get("params"), horizon=D_design.get("horizon"),
                              case=case, sensor="deltapen")
        dets = {}
        for k, dc in DET_CONFIGS.items():
            dp = dict(SM.DET_DEFAULTS); dp.update(dc)
            det = SM.detector(st, dp)
            dets[k] = (det["t"], det["ratio"], det["amp"])
        data.append((s, D, case.dh_revh("deltapen"), dets, TU._light(case)))
        del case, st
    log(f"[gate] {tag}: detectors and estimates on {len(data)} cases in {time.time() - t0:.0f} s")
    hist = []

    def run(plist):
        for p in plist:
            rows = []
            for s, D, fb, dets, lc in data:
                t_up, ratio, amp = dets[p["det"]]
                gu = hyst_gate(t_up, ratio, amp, p)
                tick_t = lc.tick_t
                k = np.searchsorted(t_up, tick_t, side="right") - 1
                g = np.where(k >= 0, gu[np.clip(k, 0, len(gu) - 1)], 0.0)[:, None]
                d = p["gain"] * g * D + ((1.0 - g) * fb if p["fallback"] == "revh" else 0.0)
                m = SV.fast_measures(lc, -d, pp)
                m.update({"design": "x", "case": s["id"], "level": s["level"], "kind": s.get("kind"),
                          "gate_open": float(np.mean(g[lc.arrays["down_ticks"] > 0.5] > 0.5))})
                rows.append(m)
            sm = EV.summarize(rows)["x"]
            hist.append({"params": dict(p), "summary": sm, "score": TU.score(sm, True)})

    init = [{"det": "ai2", "r_on": 5.0, "r_off_frac": 0.5, "t_on": 0.5, "t_off": 1.0, "ramp": 0.2, "amp_lo": 0.15e-3,
             "amp_hi_mult": 0.35 / 0.15, "fallback": "revh", "gain": 1.0},
            {"det": "ai2", "r_on": 8.0, "r_off_frac": 0.5, "t_on": 0.5, "t_off": 1.0, "ramp": 0.2, "amp_lo": 0.15e-3,
             "amp_hi_mult": 0.35 / 0.15, "fallback": "none", "gain": 1.0}]
    run(init + [TU.sample(GATE_SPACE, rng) for _ in range(n_random)])
    for rnd in range(2):
        best = sorted(hist, key=lambda h: h["score"])[:3]
        run([TU.perturb(b["params"], GATE_SPACE, rng, 0.3 if rnd == 0 else 0.15) for b in best
             for _ in range(max(1, n_local // 3))])
    best = min(hist, key=lambda h: h["score"])
    log(f"[gate] {tag}: {len(hist)} gates in {time.time() - t0:.0f} s; best {best['score']:.3f} " +
        json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in best['summary'].items()
                    if k in ('severe_bb', 'severe_ratio', 'edge_bb', 'moderate_rheld', 'mild_rheld', 'clean_um_mean',
                             'clean_um_max', 'gate_open_severe', 'gate_open_clean')}))
    out = {"tag": tag, "D_design": D_design, "best": best, "history": hist, "init_scores": [h["score"] for h in hist[:2]],
           "elapsed_s": time.time() - t0}
    TU.TUNE_DIR.mkdir(parents=True, exist_ok=True)
    (TU.TUNE_DIR / f"gate_{tag}.json").write_text(json.dumps(out, default=float))
    return out
