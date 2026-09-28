"""Every variant on one (writer, f0, amplitude, seed) scenario, and the tremor-free check, with the metrics.

Variants (all SIMULATION on HW1; the same hand, writing, tremor and sensor noise for every variant):
  none            ordinary 12 g pen
  revH_off        Rev H, nose held (the hand-only counterfactual for the device share)
  tracker         Rev H + the tracker as in results/handwriting (AKF re-tuned for Rev H by opt/inertial)
  tracker_rt      Rev H + the same filter with its tremor-state noise, damping and gain re-tuned here for severe
                  tremor on tuning data (no AI; the base the AI variants sit on, so the AI's own effect is isolated)
  prior_<case>    A(i): the AI template as a prior inside tracker_rt (fusion.context), case = ai_correct |
                  ai_predicted | wrong_full | oracle (known text: the upper bound of any template)
  guide_<case>    A(ii): tracker_rt + partial guidance toward the template (guide.py)
  tracker_sev     information only: the T0 candidate with the lowest severe-tremor ink error on tuning data, which the
                  T0 rules rejected (false correction and 0.3 mm degradation); shows what a severe-tremor mode would
                  give and cost
  oracle          perfect knowledge of the tremor (the mechanism's limit)
  clean_<src>     B: the app's non-causal clean copy of the recorded tip path of <src> (tracker, tracker_rt,
                  revH_off), Wiener smoother; clean_bs_<src>: zero-phase band-stop

Metrics: ink error (RMS nearest-point distance of in-contact ink to the intended letters), letters read (aiguide
recogniser), words read by the app (lexicon correction), wrong letters introduced ("flips": letters newly read as the
wrongly predicted letter against the tracker underneath), letters broken / fixed against that tracker, device share of
the ink motion (against the nose-held run) and AI share (against the tracker underneath), travel use, and on
tremor-free writing the false correction (RMS ink displacement against the nose-held run).
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths
from . import cleancopy as CC
from . import core as CO
from . import guide as GU

ensure_paths()
from fusion import context as CX  # noqa: E402
from fusion import estimators as ES  # noqa: E402
from handwriting import metrics as MT  # noqa: E402
from handwriting.plant import RIDX, Result  # noqa: E402

CASES = ("ai_correct", "ai_predicted", "wrong_full", "oracle")
PRIOR_DEFAULTS = {"tpl_mode": 1.0, "sigma_t": 150e-6, "gate": 0.0, "drop_um": 1200.0, "drop_s": 0.06, "tb0": 500e-6,
                  "t_rate": 500.0, "q_tb": (30e-6) ** 2, "tb_letter": -1.0, "c_min": CO.C_MIN, "xtrack": 0.0}


# ------------------------------------------------------------------ metrics
def letters_of(sc: CO.Scenario, res: Result) -> List[Dict]:
    return MT.letter_rows(sc.wr.written, res, sc.wr.rec)


def metrics(sc: CO.Scenario, res: Result, rows: Optional[List[Dict]] = None, travel: bool = True) -> Dict:
    rows = rows if rows is not None else letters_of(sc, res)
    s = MT.summary(rows)
    wd = MT.words(rows, sc.wr.su.text)
    out = {"ink_err_um": s.get("path_rms_um"), "ink_p95_um": s.get("path_p95_um"), "recognition": s.get("recognition_accuracy"),
           "word_acc_app": wd.get("word_accuracy_app"), "word_acc_letters": wd["word_accuracy_letters"],
           "recognised_words": " ".join(wd["recognised"]), "app_words": " ".join(wd.get("corrected", []))}
    if travel:
        out.update({k: v for k, v in MT.travel(res, sc.pen).items() if k in ("at_travel_limit", "q_rms_mm", "q_max_mm", "F_rms_N")})
    return out


def read_as(rows: List[Dict]) -> List[Optional[str]]:
    return [None if r.get("missing") else r.get("recognised_as") for r in rows]


def compare_letters(sc: CO.Scenario, rows: List[Dict], base_rows: List[Dict]) -> Dict:
    """Wrong letters introduced and letters broken / fixed against the tracker underneath."""
    preds = sc.wr.preds
    ra, rb = read_as(rows), read_as(base_rows)
    chars = [L.char for L in sc.wr.written.letters]
    flips = sum(1 for k, p in enumerate(preds) if ra[k] == p["wrong"] and rb[k] != p["wrong"])
    flips_back = sum(1 for k, p in enumerate(preds) if rb[k] == p["wrong"] and ra[k] != p["wrong"])
    mispred = sum(1 for k, p in enumerate(preds) if p["top1"] != chars[k] and ra[k] == p["top1"] and rb[k] != p["top1"])
    broken = sum(1 for k in range(len(chars)) if rb[k] == chars[k] and ra[k] != chars[k])
    fixed = sum(1 for k in range(len(chars)) if rb[k] != chars[k] and ra[k] == chars[k])
    return {"flips": flips, "flips_removed": flips_back, "mispred_flips": mispred, "broken": broken, "fixed": fixed,
            "read_as_wrong": sum(1 for k, p in enumerate(preds) if ra[k] == p["wrong"]), "n_letters": len(chars)}


def with_ink(res: Result, t_track: np.ndarray, xy: np.ndarray) -> Result:
    """A copy of a run whose ink is replaced by a (cleaned) track; the nose channels are zeroed (digital copy)."""
    rec = res.rec.copy()
    rec[:, RIDX["tipx"]] = np.interp(res.t, t_track, xy[:, 0])
    rec[:, RIDX["tipy"]] = np.interp(res.t, t_track, xy[:, 1])
    for k in ("qx", "qy", "qcx", "qcy"):
        rec[:, RIDX[k]] = 0.0
    return Result(rec, dict(res.info))


def clean_copy(sc: CO.Scenario, res: Result, method: str = "wiener", seed: int = 0, **kw):
    t, xy, down = CO.recorded_track(res, "ink", np.random.default_rng(seed))
    cl, info = CC.clean_track(t, xy, down, method, **kw)
    return with_ink(res, t, cl), info


# ------------------------------------------------------------------ estimators on the scenario's streams
def base_estimate(sc: CO.Scenario, base: Optional[Dict]):
    """The re-tuned tracker (no template); None: the Rev H tracker (identical to sc.dh)."""
    if base is None:
        return sc.dh, sc.info
    p = CO.tracker_params(sc.pen, sc.wr.trk)
    p.update(base)
    return ES.akf(sc.streams, p)


def prior_estimate(sc: CO.Scenario, base: Optional[Dict], prior: Dict, tpl_arr: Dict):
    p = CO.tracker_params(sc.pen, sc.wr.trk)
    if base:
        p.update(base)
    q = dict(PRIOR_DEFAULTS)
    q.update(prior or {})
    p.update(q)
    return CX.estimate(sc.streams, p, {"template": tpl_arr})


def guide_command(sc: CO.Scenario, dh: np.ndarray, info: Dict, gparams: Dict, tpl_arr: Dict, base: Optional[Dict]):
    p = CO.tracker_params(sc.pen, sc.wr.trk)
    if base:
        p.update(base)
    lag = float(p["horizon"]) + (np.sqrt(2.0) / (2 * np.pi * p["lp_hz"]) if p.get("lp_hz", 0) > 0 else 0.0)
    return GU.command(sc.streams, dh, info["amp"], tpl_arr, gparams, lag_s=lag)


# ------------------------------------------------------------------ one scenario
def evaluate(sc: CO.Scenario, cfg: Dict, variants: Sequence[str], keep: bool = False, est0=None, tpls=None) -> Dict:
    """cfg: {"base": {...} or None, "prior": {...}, "guide": {...}}.  variants: names from the module docstring."""
    t0 = time.time()
    out: Dict[str, Dict] = {}
    runs: Dict[str, Result] = {}
    need_tpl = any(v.startswith(("prior_", "guide_")) for v in variants)
    if need_tpl and tpls is None:
        est0 = est0 or CO.calibrate_style(sc.wr, sc.f0 or 8.0, sc.amp, sc.seed)
        tpls = CO.templates(sc, est0)
    rows_cache: Dict[str, List[Dict]] = {}

    def add(name, res, travel=True, base_name=None):
        runs[name] = res
        rows = letters_of(sc, res)
        rows_cache[name] = rows
        m = metrics(sc, res, rows, travel=travel)
        if name not in ("none", "revH_off") and not name.startswith("clean"):
            m["device_share"] = MT.authorship(res, sc.neutral)["device_share"]
        if base_name is not None and base_name in runs:
            m.update(compare_letters(sc, rows, rows_cache[base_name]))
            a = MT.authorship(res, runs[base_name])
            m["ai_share"] = a["device_share"]
            m["ai_disp_max_mm"] = a["device_disp_max_mm"]
        out[name] = m

    if "none" in variants:
        add("none", CO.run_none(sc), travel=False)
    add("revH_off", sc.neutral)
    base = cfg.get("base")
    if "tracker" in variants or any(v.endswith("_tracker") for v in variants) or (need_tpl and base is None):
        add("tracker", CO.run_cmd(sc, -sc.dh))
        out["tracker"]["f_est_median_hz"] = float(np.median(sc.info["f_est"]))
    base = cfg.get("base")
    dh_b, info_b = base_estimate(sc, base)
    base_name = "tracker_rt" if base is not None else "tracker"
    if base is not None and (base_name in variants or need_tpl or any(v.endswith("_tracker_rt") for v in variants)):
        add("tracker_rt", CO.run_cmd(sc, -dh_b))
    if "tracker_sev" in variants and cfg.get("sev"):
        dh_s, _ = base_estimate(sc, cfg["sev"])
        add("tracker_sev", CO.run_cmd(sc, -dh_s))
    if "oracle" in variants:
        add("oracle", CO.run_cmd(sc, CO.oracle_cmd(sc)))
    extra = {}
    for v in variants:
        if v.startswith("prior_"):
            case = v[len("prior_"):]
            ta = CO.template_arrays(tpls[case], CO.template_conf(case, sc.wr.preds))
            dh_p, ip = prior_estimate(sc, base, cfg.get("prior", {}), ta)
            add(v, CO.run_cmd(sc, -dh_p), base_name=base_name)
            out[v].update({"template_updates": ip["template_updates"], "template_gated": ip["template_gated"],
                           "template_dropped_letters": ip["template_dropped_letters"]})
        elif v.startswith("guide_"):
            case = v[len("guide_"):]
            ta = CO.template_arrays(tpls[case], CO.template_conf(case, sc.wr.preds))
            q, ig = guide_command(sc, dh_b, info_b, cfg.get("guide", {}), ta, base)
            add(v, CO.run_cmd(sc, q), base_name=base_name)
            out[v].update({"guide_ticks_on": ig["ticks_on"], "guide_letters_dropped": ig["letters_dropped"],
                           "guide_mean_g": ig["mean_g_in_use"]})
    for v in variants:
        if v.startswith("clean_"):
            bs = v.startswith("clean_bs_")
            src = v[len("clean_bs_"):] if bs else v[len("clean_"):]
            if src not in runs:
                continue
            res_c, inf = clean_copy(sc, runs[src], "bandstop" if bs else "wiener",
                                    seed=1000 + sc.wr.w + int(sc.seed) + int(10 * sc.f0) + int(1e4 * sc.amp))
            add(v, res_c, travel=False)
            out[v].update({"f_hat_hz": inf.get("f_hat"), "peak_ratio": inf.get("peak_ratio"), "applied": inf.get("applied", True)})
    if "none" in out:
        for k, m in out.items():
            if m.get("ink_err_um") is not None:
                m["ink_err_ratio"] = m["ink_err_um"] / max(out["none"]["ink_err_um"], 1e-9)
    res = {"writer": sc.wr.w, "f0": sc.f0, "amp_mm": sc.amp * 1e3, "seed": sc.seed, "variants": out,
           "tracker_amp_median_um": float(np.median(info_b["amp"]) * 1e6), "elapsed_s": time.time() - t0}
    if tpls is not None:
        res["template_error"] = {c: CO.template_error_um(sc, tpls[c]) for c in ("ai_correct", "ai_predicted", "wrong_full")}
    if keep:
        res["_runs"] = runs
    return res


def tremor_free(wr: CO.Writer, cfg: Dict, variants: Sequence[str]) -> Dict:
    """False correction: each variant on the same writing without tremor (templates built from that run)."""
    sc = CO.make_clean_scenario(wr)
    est0 = CO.calibrate_style(wr, 8.0, 0.0, 0)
    tpls = CO.templates(sc, est0) if any(v.startswith(("prior_", "guide_")) for v in variants) else None
    ev = evaluate(sc, cfg, [v for v in variants if not v.startswith("clean_") and v not in ("none", "oracle")] +
                  [v for v in variants if v.startswith("clean_")], keep=True, est0=est0, tpls=tpls)
    runs = ev.pop("_runs")
    rc = sc.neutral
    c = rc.contact > 0.5
    for k, r in runs.items():
        n = min(len(r.t), len(rc.t))
        m = c[:n] & (r.contact[:n] > 0.5)
        ev["variants"][k]["false_correction_um"] = float(np.sqrt(np.mean(np.sum((r.ink[:n] - rc.ink[:n])[m] ** 2, axis=1))) * 1e6)
    return ev
