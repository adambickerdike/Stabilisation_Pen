"""EXP-E11: does calibrating the authority gate on the user's own clean writing keep every writer under 50 um?
(REQ-CTRL-016; SIMULATION, model HW1 with real inputs.)  INFORMATION ONLY on the test split: study E has already seen it.

The designs (study E's frozen files, read-only):
  D1  ai2's causal TCN + its soft size gate: E's frozen choice (retired as a nib driver by DEC-061; a test object here)
  D2  the TCN trained on real tuning data ('net') + its soft size gate (E's information row)
  D3  the listening AKF + soft confidence gate (E's information row; tip tremor and clean writing only, not read)
The gate (realtrack.estimators.authority): A(t) = sqrt(2 LP_tau_amp(|d_raw|^2)) of the raw estimate; the nose gets
g(t) x gain x d_raw, g = clip((A - a_lo) / (a_hi - a_lo), 0, 1) with attack and release times (D3: times a line
confidence).  Calibration changes a_lo and a_hi only; tau_amp, the times, the gain and D3's confidence stay frozen.

CALIBRATION RULE (grid fixed here before any run):
  For the scored note of a writer, the calibration note is ANOTHER note of the same writer: the first note with seed
  i + K k (K = the number of writers of the split, k = 1, 2, ...) that shares no recorded line with the scored note.  The
  design's raw estimate runs on the calibration note written WITHOUT tremor (Rev J nose held, the DeltaPen-class page
  sensor, its own sensor seed); Q_p = the p-quantile of A over its pen-down ticks after the first second.
    a_lo,w = kappa x Q_p                         ('per_user': the threshold follows the writer, up or down), or
    a_lo,w = max(a_lo,frozen, kappa x Q_p)       ('raise_only': it may only rise above the frozen threshold);
    a_hi,w = a_lo,w x (a_hi / a_lo)_frozen       (the ramp keeps its relative width).
  Grid: p in {0.99, 0.999, 1.0 (the maximum)} x kappa in {1.0, 1.25, 1.5, 2.0} x the two modes: 24 rules per design.
CHOICE on the tuning split (E's selection set, surrogate of the Rev J command path, DeltaPen-class sensor; the learned
  model of each tuning note is its cross-fitted fold model, which never saw that writer): every tuning note calibrated
  on its writer's other note.  A rule passes if the clean-writing change is <= 40 um on EVERY tuning note (DEC-055's
  50 um per writer, with a 10 um margin) and <= 20 um on average (E's T2), with E's T3 (the mild and moderate tip
  tremor <= 1.02 x the nose-held pen's) and T4 (0.6 mm: broadband <= the held pen's).  Among passing rules the lowest
  severe broadband residual (E's T1) wins; within 0.01 of it the most conservative (higher p, then higher kappa, then
  raise_only).  If none passes, the rule with the smallest worst-note change is reported and flagged.
TEST (once, after the freeze): R's 9 test notes; each writer calibrated on a different note of the same writer; the
  calibrated gates scored in the full HW1 plant on R's cases: the clean note (clean-writing change, words), the severe PD
  and ET cases (words read for D1 and D2, tip tremor), the moderate and mild cases (tip tremor: no-harm check).
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import common as CM

DESIGNS = {"D1": ("chosen", None, "ai2's TCN + soft size gate (E's frozen choice)"),
           "D2": ("info", "net", "TCN trained on real data + soft size gate (E, information)"),
           "D3": ("info", "listen_conf", "listening AKF + soft confidence gate (E, information)")}
READ_DESIGNS = ("D1", "D2")
P_Q = (0.99, 0.999, 1.0)
KAPPA = (1.0, 1.25, 1.5, 2.0)
MODES = ("per_user", "raise_only")
CLEAN_NOTE_MAX_UM = 40.0
CLEAN_MEAN_UM = 20.0
T_SETTLE_S = 1.0
QUICK_RULES = [(1.0, 1.25, "raise_only"), (1.0, 1.25, "per_user")]


def design(name: str) -> Dict:
    fr = CM.frozen_e()
    where, key, _ = DESIGNS[name]
    return fr["chosen"] if where == "chosen" else fr["info"][key]


def rules(quick: bool = False) -> List[Tuple[float, float, str]]:
    if quick:
        return list(QUICK_RULES)
    return [(p, k, m) for p in P_Q for k in KAPPA for m in MODES]


def rule_key(p: float, kappa: float, mode: str) -> str:
    return f"q{p:g}_k{kappa:g}_{mode}"


def raw_estimate(dz: Dict, st, case_like) -> np.ndarray:
    from realtrack import estimators as E
    d, _ = E.estimate({k: v for k, v in dz.items() if k != "auth"}, st, case=case_like, sensor="deltapen")
    return d


def gate(raw: np.ndarray, st, auth: Dict):
    """The frozen authority law with the given parameters (+ D3's line confidence) on a raw estimate."""
    from realtrack import estimators as E
    Ts = float(st.tick_t[1] - st.tick_t[0])
    conf = None
    if "r_lo" in auth:
        conf = E.conf_from_ratio(E._ratio_cached(st), auth["r_lo"], auth["r_hi"])
    return E.authority(raw, Ts, auth, conf)


def calib_stats(raw: np.ndarray, st, auth: Dict, down: np.ndarray) -> Dict:
    """Quantiles of the gate's amplitude signal A over pen-down ticks after the first second (clean calibration note)."""
    from realtrack import estimators as E
    Ts = float(st.tick_t[1] - st.tick_t[0])
    _, _, A = E.authority(raw, Ts, dict(auth, a_lo=0.0, a_hi=0.0), None)      # A does not depend on a_lo, a_hi, conf
    t = st.tick_t[:len(A)]
    m = (np.asarray(down[:len(A)]) > 0.5) & (t > T_SETTLE_S)
    a = A[m] if m.any() else A
    return {"q": {f"{p:g}": float(np.quantile(a, p)) for p in P_Q}, "max": float(a.max()), "mean": float(a.mean()),
            "n_ticks": int(len(a))}


def calibrated(auth: Dict, stats: Dict, p: float, kappa: float, mode: str) -> Dict:
    lo_f, hi_f = float(auth["a_lo"]), float(auth["a_hi"])
    lo = kappa * float(stats["q"][f"{p:g}"])
    if mode == "raise_only":
        lo = max(lo_f, lo)
    ratio = hi_f / lo_f if lo_f > 0 else 2.0
    return dict(auth, a_lo=lo, a_hi=lo * ratio)


# ------------------------------------------------------------------ calibration notes
def calibration_note(split: str, i: int, K: int, scored_recordings: Sequence[str], max_k: int = 30):
    """Disjoint note of the same writer; a seed stride never establishes writer identity."""
    from realdata import library as RL
    if K < 1 or max_k < 2:
        raise ValueError("Calibration requires a positive seed stride and at least one alternative note")
    writer = RL.writing(split, seed=i).real["writer"]
    rec0 = set(scored_recordings)
    for k in range(1, max_k):
        s = i + K * k
        w = RL.writing(split, seed=s, writer=writer)
        if w.real["writer"] != writer:
            raise ValueError("Calibration data returned a different writer")
        if rec0.isdisjoint(w.real["recordings"]):
            return s, w
    raise RuntimeError(f"no disjoint calibration note for {split} note {i}")


def clean_streams(written, key: str):
    """The Rev J pen on a note without tremor (nose held): its DeltaPen-class sensor streams and pen-down ticks."""
    from aiprior import core as CO
    from realdata import hw1 as H
    from realdata import sensors as RSN
    from realtrack import cases as C
    note = C.Note(written)
    pen = note.pens["revJ"]
    scn = note.scenario("revJ", None)
    res = note.clean["revJ"]
    s_seed = C._h(key, "revJ") % (2 ** 31)
    st = CO.streams_for(res, scn, pen, note.trk, s_seed)
    std = RSN.degrade_page(st, H.page_model(), s_seed + 17)
    kt = np.clip(np.arange(len(std.tick_t)) * res.info["tick_decim"], 0, len(scn.t) - 1)
    down = (scn.down[kt] > 0.5).astype(float)
    return std, down


# ------------------------------------------------------------------ the tuning choice (one job, surrogate)
def tune(quick: bool = False, log=CM.log) -> Dict:
    from realtrack import cases as C
    from realtrack import evaluate as EV
    from realtrack import servo as SV
    from realtrack import tune as TU
    from realdata import library as RL
    out_p = CM.cache_dir(quick) / "e11" / "tune.json"
    if out_p.exists():
        return CM.jload(out_p)
    t0 = time.time()
    notes = [0, 5] if quick else list(range(10))
    specs = [s for s in C.tuning_specs() if s["note"] in notes]
    dz = {k: design(k) for k in DESIGNS}
    pp = SV.pen_params()
    # pass 1: calibration notes and their statistics
    calib = {}
    for i in notes:
        base = RL.writing("tuning", seed=i)
        s, w = calibration_note("tuning", i, 5, base.real["recordings"])
        st, down = clean_streams(w, f"calib_tune_n{i}_s{s}")
        spec_like = {"split": "tuning", "fold": i % 5}
        cl = CM.CaseLike(spec_like)
        calib[i] = {"seed": s, "recordings": w.real["recordings"], "stats": {}}
        for k, d in dz.items():
            raw = raw_estimate(d, st, cl)
            calib[i]["stats"][k] = calib_stats(raw, st, d["auth"], down)
        log(f"[e11] tuning note {i}: calibration note seed {s}: " + ", ".join(
            f"{k} max {v['max'] * 1e3:.2f} mm" for k, v in calib[i]["stats"].items()))
    # pass 2: every case of every note, every rule (+ the frozen gate)
    rows: Dict[str, Dict[str, List[Dict]]] = {k: {} for k in dz}
    for s in specs:
        case = C.load_case(s)
        st = case.streams("deltapen")
        for k, d in dz.items():
            raw = raw_estimate(d, st, case)
            variants = {"frozen": d["auth"]}
            for (p, kappa, mode) in rules(quick):
                variants[rule_key(p, kappa, mode)] = calibrated(d["auth"], calib[s["note"]]["stats"][k], p, kappa, mode)
            for vk, au in variants.items():
                dh, g, A = gate(raw, st, au)
                m = SV.fast_measures(case, -dh, pp)
                m.update({"design": vk, "case": s["id"], "level": s["level"], "kind": s.get("kind"),
                          "note": s["note"], "fold": s["fold"], "sensor": "deltapen"})
                con = case.arrays["down_ticks"][:len(g)] > 0.5
                m["auth_mean"] = float(np.mean(g[con])) if con.any() else float("nan")
                rows[k].setdefault(vk, []).append(m)
        del case
    out = {"notes": notes, "calibration": calib, "designs": {}, "rules": [rule_key(*r) for r in rules(quick)],
           "elapsed_s": None}
    for k in dz:
        summ = {}
        for vk, rr in rows[k].items():
            sm = EV.summarize(rr)[vk]
            clean = {r["note"]: r["clean_change_um"] for r in rr if r["level"] == "clean"}
            sm["clean_um_by_note"] = clean
            sm["clean_um_note_max"] = float(max(clean.values())) if clean else float("nan")
            ps = TU.passes(sm)
            ps["note_max_40"] = bool(sm["clean_um_note_max"] <= CLEAN_NOTE_MAX_UM)
            ps["mean_20"] = bool(sm.get("clean_um_mean", np.inf) <= CLEAN_MEAN_UM)
            ps["all_e11"] = bool(ps["note_max_40"] and ps["mean_20"] and ps["T3"] and ps["T4"])
            summ[vk] = {"summary": sm, "passes": ps}
        out["designs"][k] = {"label": DESIGNS[k][2], "frozen_auth": dz[k]["auth"], "variants": summ,
                             "choice": choose(summ, quick)}
        ch = out["designs"][k]["choice"]
        log(f"[e11] {k}: chosen {ch['rule']} (passes {ch['passes']}): severe x{ch['severe_ratio']:.3f}, "
            f"clean mean {ch['clean_um_mean']:.1f} um, worst note {ch['clean_um_note_max']:.1f} um")
    out["elapsed_s"] = time.time() - t0
    CM.jdump(out_p, out)
    return out


def _conservative_order(rk: str) -> Tuple:
    p = float(rk.split("_")[0][1:])
    kappa = float(rk.split("_")[1][1:])
    mode = rk.split("_", 2)[2]
    return (-p, -kappa, 0 if mode == "raise_only" else 1)


def choose(summ: Dict[str, Dict], quick: bool = False) -> Dict:
    cands = {k: v for k, v in summ.items() if k != "frozen"}
    ok = {k: v for k, v in cands.items() if v["passes"]["all_e11"]}
    if ok:
        J = {k: v["summary"]["severe_bb"] for k, v in ok.items()}
        jmin = min(J.values())
        near = [k for k, j in J.items() if j <= jmin + 0.01]
        best = sorted(near, key=_conservative_order)[0]
        passed = True
    else:
        best = min(cands, key=lambda k: cands[k]["summary"]["clean_um_note_max"])
        passed = False
    s = cands[best]["summary"]
    p, kappa, mode = best.split("_", 2)
    return {"rule": best, "p": float(p[1:]), "kappa": float(kappa[1:]), "mode": mode, "passes": passed,
            "severe_ratio": s["severe_ratio"], "severe_bb": s["severe_bb"], "clean_um_mean": s["clean_um_mean"],
            "clean_um_note_max": s["clean_um_note_max"], "moderate_rheld": s["moderate_rheld"],
            "mild_rheld": s["mild_rheld"],
            "frozen_gate_on_tuning": {k: summ["frozen"]["summary"].get(k) for k in
                                      ("severe_ratio", "severe_bb", "clean_um_mean", "clean_um_note_max",
                                       "moderate_rheld", "mild_rheld")}}


# ------------------------------------------------------------------ the test part (one writer)
READ_PLAN = {"clean": {"D1|cal", "D2|cal"}, "severe": {"D1|cal", "D2|cal", "D2|frozen"}, "moderate": set(), "mild": set()}


def test_note(wr, i: int, frozen: Dict, quick: bool = False) -> List[str]:
    from realdata import hw1 as H
    from realdata import library as RL
    p_out = CM.cache_dir(quick) / "e11" / f"test_w{i}.json"
    if p_out.exists():
        return [p_out.name]
    t0 = time.time()
    fe = frozen["e11"]
    dz = {k: design(k) for k in DESIGNS}
    s, w = calibration_note("test", i, 9, wr.written.real["recordings"])
    st_c, down_c = clean_streams(w, f"calib_test_w{i}_s{s}")
    cl = CM.CaseLike({"split": "test"})
    cal = {"seed": s, "recordings": w.real["recordings"], "writer": w.real["writer"], "stats": {}, "gates": {}}
    for k, d in dz.items():
        raw = raw_estimate(d, st_c, cl)
        cal["stats"][k] = calib_stats(raw, st_c, d["auth"], down_c)
        ch = fe["choice"][k]
        cal["gates"][k] = calibrated(d["auth"], cal["stats"][k], ch["p"], ch["kappa"], ch["mode"])
    cases = [("clean", None, None)] + [(cls, kind, cls) for cls in ("severe", "moderate", "mild")
                                       for kind in (("PD",) if quick else CM.KINDS)]
    if quick:
        cases = cases[:2]
    res = {"writer": wr.written.real["writer"], "note": i, "calibration": cal, "cases": {}}
    for tag, kind, cls in cases:
        tc = CM.TestCase(wr, i, kind, cls)
        clc = CM.CaseLike({"split": "test"}, dh=tc.dh_revh)
        st = tc.streams_d
        dev = {}
        for k, d in dz.items():
            raw = raw_estimate(d, st, clc)
            for gk, au in (("frozen", d["auth"]), ("cal", cal["gates"][k])):
                dh, g, A = gate(raw, st, au)
                r = tc.run(-dh)
                key = f"{k}|{gk}"
                read = (key in READ_PLAN[tag]) and not quick
                m = CM.measures(tc.written, r, tc.scn, tc.pen, tc.f0, read=read)
                con = np.interp(st.tick_t, r.t, r.contact) > 0.5
                m["auth_mean"] = float(np.mean(g[con[:len(g)]])) if con.any() else float("nan")
                if kind is None:
                    m["false_correction_um"] = CM.false_correction_um(tc.sJ, r)
                dev[key] = m
        if kind is not None:
            dev["held"] = {"tip_tremor_mm": H.tip_tremor_mm(tc.neutral, tc.scn, tc.f0)}
        e = tc.e_cached() or {}
        rep = {}
        for k, ek in (("D1", "revJ_new|deltapen"), ("D2", "revJ_info_net|deltapen"),
                      ("D3", "revJ_info_listen_conf|deltapen")):
            ed = (e.get("devices") or {}).get(ek) or {}
            rep[k] = {"tip_tremor_mm": [dev[f"{k}|frozen"].get("tip_tremor_mm"), ed.get("tip_tremor_mm")],
                      "false_correction_um": [dev[f"{k}|frozen"].get("false_correction_um"),
                                              ed.get("false_correction_um")]}
        res["cases"][tc.r_name()] = {"kind": kind, "class": cls, "devices": dev, "repro_frozen_vs_E": rep}
        CM.log(f"[e11] test w{i} {tag} {kind or ''}: " + ", ".join(
            f"{k} {v.get('tip_tremor_mm', float('nan')):.2f}mm" + (f" {v['false_correction_um']:.1f}um"
                                                                  if 'false_correction_um' in v else "")
            + (f" w{v['words_read']}" if 'words_read' in v else "") for k, v in dev.items()))
    res["_elapsed_s"] = time.time() - t0
    CM.jdump(p_out, res)
    return [p_out.name]


# ------------------------------------------------------------------ aggregation
def aggregate(quick: bool, frozen: Optional[Dict]) -> Dict:
    out = {"designs": {k: v[2] for k, v in DESIGNS.items()},
           "label": "INFORMATION ONLY (feasibility): SIMULATION (model HW1) with real recorded inputs on R's test split, "
                    "which study E has already seen; the real answer needs EXP-R01 shadow-mode recordings of people"}
    tp = CM.cache_dir(quick) / "e11" / "tune.json"
    tu = CM.jload(tp)
    if tu:
        out["tuning"] = {"calibration": tu["calibration"], "choice": {k: v["choice"] for k, v in tu["designs"].items()},
                         "table": {k: {vk: {"severe_ratio": vv["summary"]["severe_ratio"],
                                            "severe_bb": vv["summary"]["severe_bb"],
                                            "clean_um_mean": vv["summary"]["clean_um_mean"],
                                            "clean_um_note_max": vv["summary"]["clean_um_note_max"],
                                            "moderate_rheld": vv["summary"]["moderate_rheld"],
                                            "mild_rheld": vv["summary"]["mild_rheld"], "passes": vv["passes"]["all_e11"]}
                                       for vk, vv in v["variants"].items()} for k, v in tu["designs"].items()},
                         "elapsed_s": tu.get("elapsed_s")}
    files = sorted((CM.cache_dir(quick) / "e11").glob("test_w*.json"))
    tests = [CM.jload(p) for p in files]
    tests = [t for t in tests if t]
    if not tests:
        return out
    # R-format cases: R's ordinary pen and clean readings merged with the E11 devices
    real, clean = [], []
    for t in tests:
        for name, c in t["cases"].items():
            r = CM.jload(CM.R_CACHE / f"{name}.json") or {}
            e = CM.jload(CM.E_TEST_CACHE / f"{name}.json") or {}
            dev = {k: v for k, v in (r.get("devices") or {}).items() if k in ("none", "revJ_oracle")}
            ed = (e.get("devices") or {}).get("revJ_new|deltapen")
            if ed:
                dev["D1|frozen_E"] = ed                       # E's reading of the frozen design (same case)
            dev.update(c["devices"])
            if c["kind"] is None:
                clean.append({"set": "clean_real", "writer": t["writer"], "note": t["note"], "devices": dev})
            else:
                real.append({"set": "real", "writer": t["writer"], "note": t["note"], "kind": c["kind"],
                             "class": c["class"], "tremor": r.get("tremor"), "devices": dev})
    per_writer = []
    for t in tests:
        row = {"note": t["note"], "writer": t["writer"].split("/")[-1], "calibration_seed": t["calibration"]["seed"]}
        cn = f"clean_real_w{t['note']}"
        c = t["cases"].get(cn, {}).get("devices", {})
        for k in DESIGNS:
            row[f"{k}_frozen_um"] = c.get(f"{k}|frozen", {}).get("false_correction_um")
            row[f"{k}_cal_um"] = c.get(f"{k}|cal", {}).get("false_correction_um")
            row[f"{k}_a_lo_mm"] = t["calibration"]["gates"][k]["a_lo"] * 1e3
            row[f"{k}_calib_max_mm"] = t["calibration"]["stats"][k]["max"] * 1e3
        per_writer.append(row)
    out["test"] = {"per_writer": per_writer, "n_writers": len(tests)}
    summ = {}
    for k in DESIGNS:
        for gk in ("frozen", "cal"):
            key = f"{k}|{gk}"
            pw = CM.per_writer(clean, key, "false_correction_um")
            vals = [v for v in pw.values() if np.isfinite(v)]
            s = {"clean_um": CM.boot(pw), "clean_um_worst_writer": max(vals) if vals else float("nan"),
                 "worst_writer": max(pw, key=pw.get).split("/")[-1] if pw else None,
                 "writers_over_50um": int(sum(v > 50.0 for v in vals))}
            sev = [c for c in real if c["class"] == "severe"]
            s["severe_tip_tremor_mm"] = CM.boot(CM.per_writer(sev, key, "tip_tremor_mm"))
            s["severe_ratio_to_ordinary"] = CM.boot(CM.per_writer(
                sev, key, "", ref="none", fn=lambda d, r: float(d["tip_tremor_mm"]) / float(r["tip_tremor_mm"])
                if r and r.get("tip_tremor_mm") else float("nan")))
            wkey = key if not (k == "D1" and gk == "frozen") else "D1|frozen_E"
            if any(c["devices"].get(wkey, {}).get("words_total") for c in sev):
                s["severe_words_of_10"] = CM.boot(CM.per_writer(sev, wkey, "", fn=CM.of10))
                s["severe_words_gain"] = CM.boot(CM.per_writer(
                    sev, wkey, "", ref="none", fn=lambda d, r: CM.of10(d) - CM.of10(r) if r else float("nan")))
            if any(c["devices"].get(key, {}).get("words_total") for c in clean):
                s["clean_words_of_10"] = CM.boot(CM.per_writer(clean, key, "", fn=CM.of10))
            for cls in ("moderate", "mild"):
                sel = [c for c in real if c["class"] == cls]
                rh = CM.per_writer(sel, key, "", ref="held", fn=lambda d, r: float(d["tip_tremor_mm"]) / float(
                    r["tip_tremor_mm"]) if r and r.get("tip_tremor_mm") else float("nan"))
                vals = [v for v in rh.values() if np.isfinite(v)]
                s[f"{cls}_ratio_to_held"] = CM.boot(rh)
                s[f"{cls}_ratio_to_held_worst_writer"] = max(vals) if vals else float("nan")
            s["dec055"] = dec055(s)
            summ[key] = s
    out["test"]["summary"] = summ
    out["test"]["repro_frozen_vs_E"] = [c["repro_frozen_vs_E"] for t in tests for c in t["cases"].values()]
    out["test"]["cards"] = {"severe": CM.card([c for c in real if c["class"] == "severe"],
                                              sorted({k for c in real for k in c["devices"]}), clean)}
    return out


def dec055(s: Dict) -> Dict:
    g = s.get("severe_words_gain") or {}
    fc = s.get("clean_um") or {}
    worst = s.get("clean_um_worst_writer", float("nan"))
    ok_w = bool(g and g.get("mean", -np.inf) >= 2.0 and g.get("lo", -np.inf) > 0.0)
    ok_m = bool(fc.get("mean", np.inf) <= 25.0)
    ok_x = bool(np.isfinite(worst) and worst <= 50.0)
    return {"words_line": ok_w if g else None, "clean_mean_line": ok_m, "clean_worst_line": ok_x,
            "passes": bool(ok_w and ok_m and ok_x) if g else None}
