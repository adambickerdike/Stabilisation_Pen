"""EXP-E13: how much tremor may be left at the tip for words to be readable (SIMULATION, model HW1, real inputs).

PLAN (fixed in this file before any case was read):
  Tuning split (every choice is made here): study E's selection set (realtrack.cases): notes 0-9 of R's tuning split
  (5 tuning writers x 2 notes, tuning texts), PD and ET recordings of tuning patients of the note's fold, at the severe
  representative (1.72 mm at the tip, DEC-055's condition) and the moderate representative (0.24 mm); the 10 notes
  without tremor (the ceiling).  The Rev J nose (+-6 mm, results/nose2) is driven by R's perfect-knowledge command made
  imperfect in three ways (residual.py):
    (a) amplitude  remaining share rho = 1 - k in REMAIN (rho = 0 is perfect knowledge, rho = 1 the nose held)
    (b) lag        the perfect estimate delayed by tau in DELAY_MS: 5.2 ms = the whole IMU-to-tip chain of study E's
                   delay budget without prediction (it leaves 19 % at 6 Hz, CALC); 13.4 ms = the end of E's horizon
                   sweep (servo delay + 10 ms); 25 ms = far into the unreadable range
    (c) noise      perfect cancellation + band-limited noise (f0 +- 2 Hz) of power amplitude sigma in NOISE_MM
  Severe cases: the ordinary pen + every variant (14 runs); moderate cases: the ordinary pen + perfect knowledge.
  Every run is read by R's reader (TrOCR base, literal) and measured with R's tip-tremor measure.
  Curve: curve.py (w(r) log-logistic; per-case points; writer bootstrap).  Frozen on the tuning split: the fit, r_plus2
  (w = ordinary pen + 2 words, DEC-055) and r_80 (80 % of the tremor-free words), and the test levels below.
  Test split (confirmation, run once after the freeze): R's 9 test notes, R's severe PD and ET cases (R's seeds), six
  variants aimed at the frozen thresholds: (a) at r_80, midway, r_plus2 and 1.3 x r_plus2 (rho = target / the case's
  nose-held tip tremor), (b) the delay whose steady-sine residual at the case's f0 equals r_plus2, (c) sigma = r_plus2.
  R's cached readings of the same cases (ordinary pen, perfect knowledge at severe and moderate, clean notes) are merged.
  Reported: words of 10 against the tip tremor for PD and ET, severe and moderate; the test fit and its thresholds;
  the tuning curve's prediction error on the test points; the words gain at the level aimed at r_plus2.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import common as CM
from . import curve as CV
from . import residual as RS

REMAIN = (0.0, 0.10, 0.18, 0.27, 0.38, 0.55, 1.0)
DELAY_MS = (5.2, 13.4, 25.0)
NOISE_MM = (0.2, 0.4, 0.8)
QUICK_REMAIN = (0.0, 0.27)
QUICK_DELAY_MS = ()
QUICK_NOISE_MM = ()
N_TUNE_NOTES = 10
TEST_FALLBACK = {"r_80_mm": 0.30, "r_plus2_mm": 0.60}      # used only if the tuning fit gives no threshold (quick runs)
ORACLE_KEY = RS.variant_key("a", 0.0)
HELD_KEY = RS.variant_key("a", 1.0)


def plan(quick: bool) -> Dict:
    return {"tuning": {"notes": [0] if quick else list(range(N_TUNE_NOTES)), "kinds": ["PD"] if quick else list(CM.KINDS),
                       "classes": ["severe"] if quick else ["severe", "moderate"],
                       "severe": {"remain": list(QUICK_REMAIN if quick else REMAIN),
                                  "delay_ms": list(QUICK_DELAY_MS if quick else DELAY_MS),
                                  "noise_mm": list(QUICK_NOISE_MM if quick else NOISE_MM)},
                       "moderate": {"remain": [0.0], "delay_ms": [], "noise_mm": []},
                       "reference": "the ordinary pen on the same case; the same notes without tremor (ordinary pen)"},
            "test": {"notes": [0] if quick else list(range(9)), "kinds": ["PD"] if quick else list(CM.KINDS),
                     "classes": ["severe"],
                     "variants": ["E13a_r80", "E13a_mid", "E13a_r2", "E13a_r2x1.3", "E13b_r2", "E13c_r2"]
                     if not quick else ["E13a_r2"]},
            "curve_model": CV.__doc__.split("Read off")[0].strip()}


def _variants(tc, cls: str, P: Dict, seed_key: str):
    """(key, command or None for the nose held, parameters) for one case."""
    lv = P["tuning"][cls]
    for rho in lv["remain"]:
        yield RS.variant_key("a", rho), (None if rho >= 1.0 else RS.scaled(tc.q_oracle, rho)), {"type": "a", "remain": rho}
    for tau in lv["delay_ms"]:
        yield RS.variant_key("b", tau), RS.delayed(tc.q_oracle, tc.tick_t, tau * 1e-3), {"type": "b", "delay_ms": tau}
    for sg in lv["noise_mm"]:
        seed = CM.h(seed_key, "noise", f"{sg:.3f}")
        yield (RS.variant_key("c", sg), RS.noisy(tc.q_oracle, tc.Ts, tc.f0, sg * 1e-3, seed),
               {"type": "c", "noise_mm": sg, "seed": seed})


# ------------------------------------------------------------------ tuning job (one note)
def tune_note(i: int, quick: bool = False) -> Dict:
    from handwriting import plant as PL
    from realdata import hw1 as H
    P = plan(quick)
    out_dir = CM.cache_dir(quick) / "e13"
    t0 = time.time()
    note = None
    done = []
    p = out_dir / f"tune_n{i}_clean.json"
    if not p.exists():
        note = note or CM.tuning_note(i)
        scn_n = note.scenario("none", None)
        rn = PL.run(scn_n, note.pens["none"], note.hand)
        m = CM.measures(note.written, rn, scn_n, note.pens["none"], 0.0, read=True)
        CM.jdump(p, {"set": "clean_real", "split": "tuning", "writer": note.written.real["writer"], "note": i,
                     "devices": {"none": m}})
        CM.log(f"[e13] tune n{i} clean: {m['words_read']}/{m['words_total']}")
    done.append(p.name)
    for cls in P["tuning"]["classes"]:
        for kind in P["tuning"]["kinds"]:
            p = out_dir / f"tune_n{i}_{kind}_{cls}.json"
            if p.exists():
                done.append(p.name)
                continue
            t1 = time.time()
            note = note or CM.tuning_note(i)
            spec = CM.tuning_spec(i, kind, cls)
            tc = CM.TuneCase(note, spec)
            dev = {}
            rn, scn_n = tc.ordinary()
            dev["none"] = CM.measures(tc.written, rn, scn_n, note.pens["none"], tc.f0, read=True)
            held_tt = H.tip_tremor_mm(tc.neutral, tc.scn, tc.f0)
            for key, q, prm in _variants(tc, cls, P, spec["id"]):
                r = tc.run(q)
                m = CM.measures(tc.written, r, tc.scn, tc.pen, tc.f0, read=True)
                m["param"] = prm
                dev[key] = m
            res = {"set": "real", "split": "tuning", "writer": note.written.real["writer"], "note": i, "kind": kind,
                   "class": cls, "case_id": spec["id"], "tremor": tc.tremor_meta(), "held_tip_tremor_mm": held_tt,
                   "devices": dev, "_elapsed_s": time.time() - t1}
            CM.jdump(p, res)
            CM.log(f"[e13] tune n{i} {kind} {cls}: none {dev['none']['words_read']}/{dev['none']['words_total']} "
                   f"{dev['none']['tip_tremor_mm']:.2f} mm; " + ", ".join(
                       f"{k} {v['words_read']} {v['tip_tremor_mm']:.2f}" for k, v in dev.items() if k != "none")
                   + f" ({time.time() - t1:.0f} s)")
            done.append(p.name)
    return {"job": f"e13_tune_n{i}", "files": done, "elapsed_s": time.time() - t0}


# ------------------------------------------------------------------ loading and points
def load_cases(quick: bool, split: str) -> Tuple[List[Dict], List[Dict]]:
    """(tremor cases, clean cases) in R's format."""
    d = CM.cache_dir(quick) / "e13"
    pre = "tune" if split == "tuning" else "test"
    real, clean = [], []
    for p in sorted(d.glob(f"{pre}_*.json")):
        c = CM.jload(p)
        if c is None:
            continue
        (clean if c["set"] == "clean_real" else real).append(c)
    return real, clean


def points(real: List[Dict], clean: List[Dict], kinds=("PD", "ET"), classes=("severe", "moderate"),
           types: Optional[Tuple[str, ...]] = None, metric: str = "tip_tremor_mm") -> Dict[str, List[Tuple[float, float]]]:
    """{writer: [(residual, words of 10)]} over every read run of the selected cases (+ clean notes at r = 0).
    types: keep only E13 variants of these residual types (a, b, c) plus the anchors (ordinary pen, perfect knowledge,
    nose held, clean notes).  metric: 'tip_tremor_mm' (R's in-band measure, mm) or 'bb_um' (E's broadband residual,
    0.5-20 Hz RMS, reported in mm): the second is a check that counts error outside f0 +- 2 Hz."""
    out: Dict[str, List[Tuple[float, float]]] = {}
    anchors = {"none", "revJ_oracle", ORACLE_KEY, HELD_KEY}
    for c in real:
        if c["kind"] not in kinds or c["class"] not in classes:
            continue
        for k, v in c["devices"].items():
            if not isinstance(v, dict) or v.get("words_total") in (None, 0):
                continue
            if types is not None and k not in anchors:
                ty = (v.get("param") or {}).get("type")
                if ty not in types:
                    continue
            r = v.get(metric)
            if r is None or not np.isfinite(float(r)):
                continue
            r = float(r) * (1e-3 if metric == "bb_um" else 1.0)
            out.setdefault(c["writer"], []).append((r, CM.of10(v)))
    for c in clean:
        v = c["devices"].get("none")
        if v and v.get("words_total"):
            out.setdefault(c["writer"], []).append((0.0, CM.of10(v)))
    return out


def ord_severe(real: List[Dict], kinds=("PD", "ET")) -> Dict[str, float]:
    sel = [c for c in real if c["class"] == "severe" and c["kind"] in kinds]
    return CM.per_writer(sel, "none", "", fn=CM.of10)


def clean_words(clean: List[Dict]) -> Dict[str, float]:
    return CM.per_writer(clean, "none", "", fn=CM.of10)


def level_table(real: List[Dict], clean: List[Dict], kinds, cls: str) -> List[Dict]:
    """Model-free: per device (variant), the mean over writers of words of 10 and of the tip tremor (95 % intervals),
    the words gain over the ordinary pen (paired per writer)."""
    sel = [c for c in real if c["kind"] in kinds and c["class"] == cls]
    if not sel:
        return []
    devs = []
    for c in sel:
        for k, v in c["devices"].items():
            if isinstance(v, dict) and k not in devs and v.get("tip_tremor_mm") is not None:
                devs.append(k)
    rows = []
    for k in devs:
        wv = CM.boot(CM.per_writer(sel, k, "", fn=CM.of10))
        tt = CM.boot(CM.per_writer(sel, k, "tip_tremor_mm"))
        gain = CM.boot(CM.per_writer(sel, k, "", ref="none", fn=lambda d, r: CM.of10(d) - CM.of10(r) if r else float("nan"))) \
            if k != "none" else None
        prm = next(((c["devices"][k].get("param") or {}) for c in sel if k in c["devices"]), {})
        rows.append({"device": k, "param": prm, "words_of_10": wv, "tip_tremor_mm": tt, "gain_vs_ordinary": gain,
                     "cer": CM.boot(CM.per_writer(sel, k, "cer")), "bb_um": CM.boot(CM.per_writer(sel, k, "bb_um")),
                     "n_cases": sum(1 for c in sel if k in c["devices"])})
    rows.sort(key=lambda r: (r["device"] != "none", r["tip_tremor_mm"]["mean"]))
    cw = CM.boot(clean_words(clean)) if clean else None
    return [{"clean_words_of_10": cw}] + rows


# ------------------------------------------------------------------ fits
def fits(real: List[Dict], clean: List[Dict], n_boot: int = CV.N_BOOT) -> Dict:
    out = {"pooled": CV.fit_with_ci(points(real, clean), ord_severe(real), clean_words(clean), n_boot=n_boot)}
    for kind in ("PD", "ET"):
        if any(c["kind"] == kind for c in real):
            out[f"kind_{kind}"] = CV.fit_with_ci(points(real, clean, kinds=(kind,)), ord_severe(real, (kind,)),
                                                 clean_words(clean), n_boot=n_boot // 4)
    for ty in ("a", "b", "c"):
        pts = points(real, clean, types=(ty,))
        if sum(len(v) for v in pts.values()) >= 8:
            out[f"type_{ty}"] = CV.fit_with_ci(pts, ord_severe(real), clean_words(clean), n_boot=n_boot // 4)
    out["severe_only"] = CV.fit_with_ci(points(real, clean, classes=("severe",)), ord_severe(real), clean_words(clean),
                                        n_boot=n_boot // 4)
    # the same with E's broadband residual (0.5-20 Hz RMS, mm) as the x-axis: does counting out-of-band error make the
    # three kinds of residual agree?  (a check, not the target's definition)
    out["pooled_broadband"] = CV.fit_with_ci(points(real, clean, metric="bb_um"), ord_severe(real), clean_words(clean),
                                             n_boot=n_boot // 4)
    for ty in ("a", "b", "c"):
        pts = points(real, clean, types=(ty,), metric="bb_um")
        if sum(len(v) for v in pts.values()) >= 8:
            out[f"type_{ty}_broadband"] = CV.fit_with_ci(pts, ord_severe(real), clean_words(clean), n_boot=n_boot // 4)
    return out


def model_free(real: List[Dict], clean: List[Dict]) -> Dict:
    """Check of the curve model: the type (a) sweep at the severe class (PD and ET pooled) as per-level means over
    writers (residual, words), with the ordinary pen's mean; the residuals at which the piecewise-linear line through
    them crosses the ordinary pen + 2 words and 80 % of the clean words (CALC; no model)."""
    sev = [c for c in real if c["class"] == "severe"]
    keys = sorted({k for c in sev for k, v in c["devices"].items()
                   if isinstance(v, dict) and (v.get("param") or {}).get("type") == "a"})
    pts = []
    for k in keys:
        r = CM.mean_finite(CM.per_writer(sev, k, "tip_tremor_mm").values())
        w = CM.mean_finite(CM.per_writer(sev, k, "", fn=CM.of10).values())
        pts.append((r, w))
    pts.sort()
    w_ord = CM.mean_finite(ord_severe(real).values())
    w_cl = CM.mean_finite(clean_words(clean).values())

    def cross(target):
        for (r0, w0), (r1, w1) in zip(pts[:-1], pts[1:]):
            if (w0 - target) * (w1 - target) <= 0 and w0 != w1:
                return r0 + (target - w0) * (r1 - r0) / (w1 - w0)
        return float("nan")
    return {"levels": [{"r_mm": a, "words": b} for a, b in pts], "w_ord_severe": w_ord, "w_clean": w_cl,
            "r_plus2_mm": cross(w_ord + 2.0), "r_80_mm": cross(0.8 * w_cl), "r_within1_mm": cross(w_cl - 1.0),
            "rule": "first crossing, going up in residual, of the line through the per-level means"}


def freeze_levels(tune_fit: Dict) -> Dict:
    """The test levels aimed at the frozen tuning thresholds (fallback values if a threshold is missing)."""
    r80 = tune_fit.get("r_80_mm")
    r2 = tune_fit.get("r_plus2_mm")
    fb = []
    if r80 is None or not np.isfinite(r80):
        r80 = TEST_FALLBACK["r_80_mm"]
        fb.append("r_80")
    if r2 is None or not np.isfinite(r2):
        r2 = TEST_FALLBACK["r_plus2_mm"]
        fb.append("r_plus2")
    return {"targets_mm": {"E13a_r80": r80, "E13a_mid": 0.5 * (r80 + r2), "E13a_r2": r2, "E13a_r2x1.3": 1.3 * r2,
                           "E13b_r2": r2, "E13c_r2": r2},
            "rule": "(a): rho = target / the case's nose-held tip tremor (clipped to 0.02-1); (b): tau such that "
                    "2 sin(pi f0 tau) x the nose-held tip tremor = target; (c): sigma = target",
            "fallback_used": fb}


# ------------------------------------------------------------------ test job part (one note; after the freeze)
def test_note(wr, i: int, frozen: Dict, quick: bool = False) -> List[str]:
    from realdata import hw1 as H
    P = plan(quick)
    out_dir = CM.cache_dir(quick) / "e13"
    tg = frozen["e13"]["test_levels"]["targets_mm"]
    done = []
    for kind in P["test"]["kinds"]:
        p = out_dir / f"test_w{i}_{kind}_severe.json"
        if p.exists():
            done.append(p.name)
            continue
        t1 = time.time()
        tc = CM.TestCase(wr, i, kind, "severe")
        held = H.tip_tremor_mm(tc.neutral, tc.scn, tc.f0)
        dev = {}
        # reproduction check (no reading): R's perfect-knowledge run of this case
        r_or = tc.run(tc.q_oracle)
        dev["_oracle_tip_tremor_mm"] = H.tip_tremor_mm(r_or, tc.scn, tc.f0)
        for key in P["test"]["variants"]:
            target = float(tg[key])
            if key.startswith("E13a"):
                rho = float(np.clip(target / held, 0.02, 1.0))
                q, prm = RS.scaled(tc.q_oracle, rho), {"type": "a", "remain": rho}
            elif key.startswith("E13b"):
                tau = RS.delay_for_fraction(tc.f0, target / held)
                q, prm = RS.delayed(tc.q_oracle, tc.tick_t, tau), {"type": "b", "delay_ms": tau * 1e3}
            else:
                seed = CM.h(tc.key, "noise", key)
                q, prm = RS.noisy(tc.q_oracle, tc.Ts, tc.f0, target * 1e-3, seed), {"type": "c", "noise_mm": target,
                                                                                   "seed": seed}
            prm["target_mm"] = target
            r = tc.run(q)
            m = CM.measures(tc.written, r, tc.scn, tc.pen, tc.f0, read=True)
            m["param"] = prm
            dev[key] = m
        res = {"set": "real", "split": "test", "writer": wr.written.real["writer"], "note": i, "kind": kind,
               "class": "severe", "tremor": tc.tremor_meta(), "held_tip_tremor_mm": held, "devices": dev,
               "_elapsed_s": time.time() - t1}
        CM.jdump(p, res)
        CM.log(f"[e13] test w{i} {kind}: " + ", ".join(f"{k} {v['words_read']} {v['tip_tremor_mm']:.2f}"
                                                        for k, v in dev.items() if isinstance(v, dict))
               + f" ({time.time() - t1:.0f} s)")
        done.append(p.name)
    return done


def test_cases_merged(quick: bool) -> Tuple[List[Dict], List[Dict]]:
    """The test variants merged with R's cached cases (R's ordinary pen and perfect knowledge at severe and moderate,
    R's clean notes), in R's format.  R's pens keep R's keys ('none', 'revJ_oracle')."""
    P = plan(quick)
    mine, _ = load_cases(quick, "test")
    by = {(c["note"], c["kind"]): c for c in mine}
    real, clean = [], []
    for i in P["test"]["notes"]:
        for kind in P["test"]["kinds"]:
            for cls in ("severe", "moderate"):
                r = CM.jload(CM.R_CACHE / f"real_w{i}_{kind}_{cls}.json")
                if r is None:
                    continue
                keep = {k: v for k, v in r["devices"].items() if k in ("none", "revJ_oracle")}
                c = {"set": "real", "split": "test", "writer": r["writer"], "note": i, "kind": kind, "class": cls,
                     "tremor": r["tremor"], "devices": keep}
                if cls == "severe" and (i, kind) in by:
                    c["devices"].update({k: v for k, v in by[(i, kind)]["devices"].items() if isinstance(v, dict)})
                    c["held_tip_tremor_mm"] = by[(i, kind)].get("held_tip_tremor_mm")
                    c["_oracle_repro"] = {"mine": by[(i, kind)]["devices"].get("_oracle_tip_tremor_mm"),
                                          "R": r["devices"]["revJ_oracle"]["tip_tremor_mm"]}
                real.append(c)
        cr = CM.jload(CM.R_CACHE / f"clean_real_w{i}.json")
        if cr:
            clean.append({"set": "clean_real", "split": "test", "writer": cr["writer"], "note": i,
                          "devices": {"none": cr["devices"]["none"]}})
    return real, clean


# ------------------------------------------------------------------ aggregation
def aggregate(quick: bool, frozen: Optional[Dict] = None, n_boot: int = CV.N_BOOT) -> Dict:
    P = plan(quick)
    out = {"plan": P, "label": "SIMULATION (model HW1) with real recorded inputs; words read by R's AI reader (TrOCR "
                               "base, literal); the curve and thresholds are CALCULATIONS on those simulated points"}
    real, clean = load_cases(quick, "tuning")
    tun = {"n_cases": len(real), "n_clean": len(clean), "tables": {}}
    for kinds, kn in ((("PD", "ET"), "all"), (("PD",), "PD"), (("ET",), "ET")):
        for cls in ("severe", "moderate"):
            t = level_table(real, clean, kinds, cls)
            if t:
                tun["tables"][f"{kn}/{cls}"] = t
    if real:
        tun["fits"] = fits(real, clean, n_boot=n_boot)
        tun["model_free_type_a"] = model_free(real, clean)
        tun["cards"] = cards(real, clean)
        tun["repro_held_vs_E"] = held_repro(real, quick)
    out["tuning"] = tun
    if frozen and frozen.get("e13"):
        out["frozen"] = frozen["e13"]
        treal, tclean = test_cases_merged(quick)
        have = [c for c in treal if any(k.startswith("E13") for k in c["devices"])]
        te = {"n_cases_with_variants": len(have), "tables": {}}
        for kinds, kn in ((("PD", "ET"), "all"), (("PD",), "PD"), (("ET",), "ET")):
            for cls in ("severe", "moderate"):
                t = level_table(treal, tclean, kinds, cls)
                if t:
                    te["tables"][f"{kn}/{cls}"] = t
        if have:
            te["fits"] = {"pooled": CV.fit_with_ci(points(treal, tclean), ord_severe(treal), clean_words(tclean),
                                                   n_boot=n_boot)}
            for kd in ("PD", "ET"):
                te["fits"][f"kind_{kd}"] = CV.fit_with_ci(points(treal, tclean, kinds=(kd,)), ord_severe(treal, (kd,)),
                                                          clean_words(tclean), n_boot=n_boot // 4)
            te["model_free_type_a"] = model_free(treal, tclean)
            te["prediction_check"] = prediction_check(frozen["e13"]["fit"]["p"], treal)
            te["oracle_repro"] = [c.get("_oracle_repro") for c in treal if c.get("_oracle_repro")]
            te["cards"] = cards(treal, tclean)
            te["gain_at_r_plus2"] = gain_at(treal, "E13a_r2")
        out["test"] = te
    return out


def cards(real: List[Dict], clean: List[Dict]) -> Dict:
    """R's results cards (words of 10, tip tremor, clean-writing change) per kind and class over every device."""
    out = {}
    devs = sorted({k for c in real for k, v in c["devices"].items() if isinstance(v, dict)})
    for kind in ("PD", "ET", "all"):
        for cls in ("severe", "moderate"):
            sel = [c for c in real if (kind == "all" or c["kind"] == kind) and c["class"] == cls]
            if sel:
                cd = CM.card(sel, devs, clean)
                cd["_n_cases"] = len(sel)
                cd["_n_writers"] = len({c["writer"] for c in sel})
                out[f"{kind}/{cls}"] = cd
    return out


def gain_at(real: List[Dict], key: str) -> Dict:
    sel = [c for c in real if c["class"] == "severe" and key in c["devices"]]
    if not sel:
        return {}
    g = CM.boot(CM.per_writer(sel, key, "", ref="none", fn=lambda d, r: CM.of10(d) - CM.of10(r) if r else float("nan")))
    return {"device": key, "gain": g, "tip_tremor_mm": CM.boot(CM.per_writer(sel, key, "tip_tremor_mm")),
            "words_of_10": CM.boot(CM.per_writer(sel, key, "", fn=CM.of10)),
            "meets_dec055_words_line": bool(g["mean"] >= 2.0 and g["lo"] > 0.0)}


def prediction_check(p_tune, real: List[Dict]) -> Dict:
    """The frozen tuning curve's words at each test run's measured residual, against the words read (per case and as
    means over writers)."""
    rows = []
    for c in real:
        for k, v in c["devices"].items():
            if not isinstance(v, dict) or not v.get("words_total") or v.get("tip_tremor_mm") is None:
                continue
            pred = float(CV.model(float(v["tip_tremor_mm"]), p_tune))
            rows.append({"writer": c["writer"], "kind": c["kind"], "class": c["class"], "device": k,
                         "r_mm": float(v["tip_tremor_mm"]), "words": CM.of10(v), "predicted": pred})
    if not rows:
        return {}
    err = np.array([r["words"] - r["predicted"] for r in rows])
    by_dev = {}
    for k in sorted({r["device"] for r in rows}):
        rr = [r for r in rows if r["device"] == k]
        by_dev[k] = {"n": len(rr), "words_mean": float(np.mean([r["words"] for r in rr])),
                     "predicted_mean": float(np.mean([r["predicted"] for r in rr])),
                     "r_mm_mean": float(np.mean([r["r_mm"] for r in rr]))}
    return {"n_runs": len(rows), "mean_error_words": float(err.mean()), "mae_words": float(np.abs(err).mean()),
            "by_device": by_dev}


def held_repro(real: List[Dict], quick: bool) -> Dict:
    """The rebuilt nose-held tip tremor of every tuning case against study E's cached value (same scenario)."""
    from realtrack import cases as C
    diffs = []
    for c in real:
        try:
            e = C.load_case(c["case_id"]).meta["ref"]["held_tip_tremor_mm"]
        except Exception:
            continue
        diffs.append(abs(float(c["held_tip_tremor_mm"]) - float(e)))
    return {"n": len(diffs), "max_abs_diff_mm": float(max(diffs)) if diffs else float("nan"),
            "rule": "the tuning cases are rebuilt with E's code and seeds; the nose-held run must match E's cache"}
