"""AI + physical help on the aiguide writers: the AI-context estimator in closed loop on P1 (SIMULATION).

Set-up (as aiguide/run_guidance.py, configuration "pencil_P1"): synthetic glyph writers write "return
library books by friday" after a pangram calibration; tremor 0.3 mm at 4, 6, 8, 10 Hz; P1 with
Controller(q_lim 0.30 mm), user force 1.0 N; seeds tremor 3000 + 10 w + f0, sensor noise 11 + w,
calibration 1000 + w, sentence 2000 + w (as aiguide).  Test writers 0-5 (aiguide's); the context
estimator's template parameters are tuned on writers 100-105 only.
Templates (aiguide.run_guidance.build_templates): oracle (the true intended letters), AI-correct
(correct letters in the estimated style from the writer's own exemplars, anchored at the neutral
run's touchdown), AI-predicted (top-1 at glyph depth 2 with its calibrated confidence; below 0.5 no
template), wrong letter (the most likely wrong letter, gated by its confidence, and at full confidence
as the worst case).
Cases: neutral; disturbance oracle; frozen Kalman (core); the old template pull (guided mode) with the
oracle, AI-correct, AI-predicted (per-letter authority by aiguide's splice emulation) and wrong-letter
templates; and, through Controller(mode="external"), the AKF without template, the learned GRU without
template and the context estimator with each template.
Metrics: aiguide.metrics (path distance to the intended letters, DTW legibility proxy, template-matching
recognition), on all ink and on the writing only (touchdown/lift tails excluded), the harness ink ratio
against the same writing without tremor, time at the stage's soft limit, and wrong-letter flips.
"""
from __future__ import annotations

import copy
import math
import time
from typing import Dict, List, Optional

import numpy as np
from scipy.spatial import cKDTree

from . import sensors as S
from . import context as CX
from . import estimators as ES

import aiguide  # noqa: F401  (paths, private numba cache only if unset)
from aiguide import guidance as G  # noqa: E402
from aiguide import lm  # noqa: E402
from aiguide import run_guidance as RG  # noqa: E402
from aiguide.metrics import GlyphRecognizer  # noqa: E402
from aiguide.sentences import GUIDE_SENTENCE  # noqa: E402
from aiguide.template import LetterTemplate  # noqa: E402
from aiguide.writer import SyntheticWriter, sample_style  # noqa: E402
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from stabpen import signals as sg  # noqa: E402

AMP = 3e-4
F0S = (4.0, 6.0, 8.0, 10.0)
TEST_WRITERS = (0, 1, 2, 3, 4, 5)
CFG = G.CONFIGS["pencil_P1"]
Q_LIM = CFG["ctrl"]["q_lim"]
REC_HZ = 4000.0
C_FULL = G.C_FULL
C_MIN = G.C_MIN


def prun(scn, mode: str, seed: int, tmpl=None, g: float = 1.0, extra: Optional[Dict] = None):
    kw = dict(CFG["ctrl"])
    kw.update(extra or {})
    ctrl = M.Controller(mode=mode, g_assist=g, **kw)
    return M.run(scn, ctrl, M.PencilConfig(**CFG.get("pencil", {})), seed=seed, tmpl=tmpl, rec_hz=REC_HZ)


def setup(wseed: int, f0: float, amp: float = AMP) -> Dict:
    """Writer, scenario (with and without tremor), recogniser, static offset, predictions and templates."""
    pred = lm.cached_predictor()
    st_ = sample_style(np.random.default_rng(wseed))
    wtr = SyntheticWriter(st_, seed=wseed)
    est0 = RG.calibrate(wtr, wseed, amp, f0)
    wr = wtr.write(GUIDE_SENTENCE, dt=G.SIM_DT, seed=2000 + wseed)
    e0 = est0.estimate()
    rec = GlyphRecognizer(e0.h, e0.width, e0.slant)
    scn = G.make_scenario(wr, sg.TremorSpec(f0=f0, amp_pk=amp), CFG["N0"], seed=3000 + 10 * wseed + int(f0))
    scn0 = G.make_scenario(wr, None, CFG["N0"], seed=0)
    S_ = 11 + wseed
    clean = prun(scn0, "neutral", S_)
    neutral = prun(scn, "neutral", S_)
    off = G.static_offset_from_run(G.arrays(clean))
    preds = RG.predictions(pred, GUIDE_SENTENCE, RG.DEPTH)
    ww = RG.word_prediction(pred, GUIDE_SENTENCE, RG.WRONG_WORD_INDEX)
    conds, tracks, _ = RG.build_templates(wr, est0, G.arrays(neutral), preds, wrong_word=ww)
    oracle_letters = [LetterTemplate(L.char, [p + off for p in L.polylines], 1.0, "oracle", k) for k, L in enumerate(wr.letters)]
    return {"wseed": wseed, "f0": f0, "wr": wr, "scn": scn, "scn0": scn0, "S": S_, "clean": clean, "neutral": neutral,
            "off": off, "rec": rec, "preds": preds, "conds": conds, "tracks": tracks, "oracle_letters": oracle_letters,
            "est0": est0}


def gated_conf(c: float) -> float:
    """ICD s5 rule 5 applied to the estimator: 0 below c_min, else min(1, c / c_full)."""
    return 0.0 if c < C_MIN else min(1.0, c / C_FULL)


def context_templates(su: Dict) -> Dict[str, Dict]:
    preds = su["preds"]
    n = len(su["wr"].letters)
    return {
        "oracle": CX.template_arrays(su["oracle_letters"], [1.0] * n),
        "ai_correct": CX.template_arrays(su["conds"]["ai_correct"], [1.0] * n),
        "ai_predicted": CX.template_arrays(su["conds"]["ai_predicted"], [gated_conf(p["conf"]) for p in preds]),
        "wrong_letter_gated": CX.template_arrays(su["conds"]["wrong_letter"], [gated_conf(p["wrong_conf"]) for p in preds]),
        "wrong_letter_full": CX.template_arrays(su["conds"]["wrong_letter"], [1.0] * n),
    }


# ------------------------------------------------------------------ template error (hypothesis test)
def _dense(strokes, step=5e-6):
    out = []
    for s in strokes:
        s = np.asarray(s, float)
        seg = np.hypot(*np.diff(s, axis=0).T)
        L = np.r_[0.0, np.cumsum(seg)]
        if L[-1] <= 0:
            out.append(s[:1]); continue
        u = np.linspace(0, L[-1], max(2, int(L[-1] / step) + 1))
        out.append(np.column_stack([np.interp(u, L, s[:, 0]), np.interp(u, L, s[:, 1])]))
    return np.vstack(out)


def template_error_signal(su: Dict, cond: str, rate: float = 1000.0) -> Dict:
    """Cross-track template error along the intended pen-down trajectory, e(t) = intended(t) - nearest template
    point of the same letter, at `rate`; plus per-letter offset and affine decompositions."""
    wr = su["wr"]
    it = wr.intended
    dec = max(1, int(round(1.0 / (rate * (it.t[1] - it.t[0])))))
    letters = su["oracle_letters"] if cond == "oracle" else su["conds"][cond]
    off = su["off"]
    segs, stats = [], {"total": [], "after_offset": [], "after_affine": []}
    for k, L in enumerate(wr.letters):
        T = _dense(letters[k].strokes)
        tree = cKDTree(T)
        for (a, b) in L.strokes:
            idx = np.arange(a, b, dec)
            idx = idx[it.pen_down[idx]]
            if len(idx) < 8:
                continue
            P = it.xy[idx] + off
            _, j = tree.query(P)
            e = P - T[j]
            segs.append(e)
        # per-letter decomposition on the letter's pen-down points
        idx = np.concatenate([np.arange(a, b, dec) for (a, b) in L.strokes])
        idx = idx[it.pen_down[idx]]
        if len(idx) < 8:
            continue
        P = it.xy[idx] + off
        d, j = tree.query(P)
        stats["total"].append(np.sum((P - T[j]) ** 2, axis=1))
        o = np.mean(P - T[j], axis=0)
        d2, j2 = tree.query(P - o)
        stats["after_offset"].append(np.sum((P - o - T[j2]) ** 2, axis=1))
        # best affine map of the template onto the intended points (3 ICP iterations)
        A = np.eye(2); c = o.copy()
        for _ in range(3):
            Tq = T @ A.T + c
            _, jq = cKDTree(Tq).query(P)
            X = np.column_stack([T[jq], np.ones(len(jq))])
            sol = np.linalg.lstsq(X, P, rcond=None)[0]
            A, c = sol[:2].T, sol[2]
        Tq = T @ A.T + c
        dq, _ = cKDTree(Tq).query(P)
        stats["after_affine"].append(dq ** 2)
    out = {k: float(np.sqrt(np.mean(np.concatenate(v))) * 1e6) for k, v in stats.items() if v}
    # temporal spectrum: per stroke segment, remove the segment mean (the bias state), then the fraction in 3-15 Hz
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [3.0, 15.0], btype="band", fs=rate, output="sos")
    sos_lo = butter(4, 3.0, fs=rate, output="sos")
    tot = band = lo = n = 0.0
    psd_acc = None
    for e in segs:
        e0 = e - e.mean(axis=0)
        pad = min(len(e0) - 1, 64)
        ep = np.vstack([e0[pad:0:-1], e0, e0[-2:-pad - 2:-1]]) if pad > 1 else e0
        eb = sosfiltfilt(sos, ep, axis=0)[pad:pad + len(e0)] if len(ep) > 27 else np.zeros_like(e0)
        el = sosfiltfilt(sos_lo, ep, axis=0)[pad:pad + len(e0)] if len(ep) > 27 else e0
        tot += float(np.sum(e ** 2)); band += float(np.sum(eb ** 2)); lo += float(np.sum(el ** 2)); n += len(e)
    out.update({"segment_mean_removed_rms_um": float(np.sqrt(sum(np.sum((e - e.mean(0)) ** 2) for e in segs) / n) * 1e6),
                "band_3_15Hz_rms_um": float(np.sqrt(band / n) * 1e6), "below_3Hz_rms_um": float(np.sqrt(lo / n) * 1e6),
                "total_rms_um_time_weighted": float(np.sqrt(tot / n) * 1e6), "n_samples": int(n)})
    return out


def template_spectrum(su: Dict, cond: str, rate: float = 1000.0, nfft: int = 256):
    """Welch-like PSD of the cross-track template error over stroke segments (segment mean removed), um^2/Hz."""
    from scipy.signal import welch
    wr = su["wr"]
    it = wr.intended
    dec = max(1, int(round(1.0 / (rate * (it.t[1] - it.t[0])))))
    letters = su["oracle_letters"] if cond == "oracle" else su["conds"][cond]
    acc = None; cnt = 0
    for k, L in enumerate(wr.letters):
        tree = cKDTree(_dense(letters[k].strokes))
        for (a, b) in L.strokes:
            idx = np.arange(a, b, dec)
            idx = idx[it.pen_down[idx]]
            if len(idx) < 32:
                continue
            P = it.xy[idx] + su["off"]
            _, j = tree.query(P)
            e = (P - tree.data[j]) * 1e6
            e = e - e.mean(0)
            f, pxx = welch(e, fs=rate, nperseg=min(nfft, len(e)), nfft=nfft, axis=0, detrend=False)
            p = pxx.sum(axis=1) * len(e)
            acc = p if acc is None else acc + p
            cnt += len(e)
    return f, acc / max(cnt, 1)


# ------------------------------------------------------------------ closed loop
def _metrics(su: Dict, res, neutral_arr=None) -> Dict:
    arr = G.arrays(res)
    wr, rec, off = su["wr"], su["rec"], su["off"]
    cm = G.case_metrics(wr, arr, rec, Q_LIM, neutral=neutral_arr, offset=off)
    cmw = G.case_metrics(wr, G.writing_only(arr), rec, Q_LIM,
                         neutral=G.writing_only(neutral_arr) if neutral_arr is not None else None, offset=off)
    base = E.compare(su["neutral"], su["clean"])
    m = E.compare(res, su["clean"])
    s = cm["summary"]
    out = {k: s.get(k) for k in ("path_rms_um", "path_p95_um", "dtw_mean_um", "recognition_accuracy", "at_soft_limit",
                                 "on_stop", "max_imposed_um", "at_voltage_limit")}
    out.update({"wo_" + k: cmw["summary"].get(k) for k in ("path_rms_um", "dtw_mean_um", "recognition_accuracy")})
    out.update({"ratio": m["e_rms_um"] / base["e_rms_um"], "band_ratio": m["e_band_rms_um"] / base["e_band_rms_um"],
                "P_rail_classB_mW": m["P_rail_classB_mW"], "q_sat_frac": m["q_sat_frac"]})
    out["_letters"] = cm["letters"]
    out["_letters_wo"] = cmw["letters"]
    return out


def _flips(su: Dict, res_letters: List[Dict], neutral_letters: List[Dict], key: str = "wrong") -> Dict:
    preds = su["preds"]
    n_new = sum(1 for k, L in enumerate(res_letters) if L.get("recognised_as") == preds[k][key]
                and neutral_letters[k].get("recognised_as") != preds[k][key])
    return {"newly_read_as_wrong_letter": int(n_new), "n": len(res_letters)}


# ------------------------------------------------------------------ tuning of the template parameters (writers 100-105 only)
def tune_setup(job) -> Dict:
    """Streams, truth and templates of one tuning scenario (no closed loop)."""
    su = setup(job["writer"], job["f0"])
    rec1 = S.record_from_result(su["neutral"], su["scn"])
    rec0 = S.record_from_result(su["clean"], su["scn0"])
    st = S.make_streams(rec1, S.config(**job["sensors"]), 700_000 + 1000 * job["writer"] + int(job["f0"]))
    d = S.truth_at(st.tick_t, rec1, rec0)
    con = np.interp(st.tick_t, rec1.t, rec1.contact) > 0.5
    return {"st": st, "d": d, "m": con & (st.tick_t > 0.5), "tpl": context_templates(su), "writer": job["writer"], "f0": job["f0"]}


def tune_score(items: List[Dict], base: Dict, cand: Dict) -> Dict:
    """Open-loop band residual ratio with the AI templates, and the wrong-template penalty."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [3.0, 15.0], btype="band", fs=2000.0, output="sos")
    p = dict(base)
    p.update(cand)
    res = {"none": [], "ai_correct": [], "ai_predicted": [], "wrong_letter_full": []}
    for it in items:
        db = sosfiltfilt(sos, it["d"], axis=0)
        for key in res:
            tpl = None if key == "none" else it["tpl"][key]
            dh, _ = CX.estimate(it["st"], p, {"template": tpl})
            e = sosfiltfilt(sos, dh, axis=0) - db
            m = it["m"]
            res[key].append(float(np.sqrt(np.sum(e[m] ** 2) / max(np.sum(db[m] ** 2), 1e-30))))
    r = {k: float(np.mean(v)) for k, v in res.items()}
    r["J"] = 0.5 * (r["ai_correct"] + r["ai_predicted"]) + 0.5 * max(0.0, r["wrong_letter_full"] - r["none"])
    return r


def tune_candidates():
    """Template-noise, bias-drift and gate settings; with the AKF's frequency gate kept or switched off (the template is
    meant to disambiguate writing from tremor exactly where the gate would otherwise block correction)."""
    out = []
    for sig in (30e-6, 60e-6, 120e-6):
        for qtb in ((30e-6) ** 2, (100e-6) ** 2):
            for gate in (3.0, 5.0):
                for fg in (None, 0.0):
                    c = {"sigma_t": sig, "q_tb": qtb, "gate": gate, "t_rate": 250.0}
                    if fg is not None:
                        c["f_gate"] = fg
                    out.append(c)
    return out


def tune_score_chunk(args):
    items, base, cands = args
    return [tune_score(items, base, c) for c in cands]


def scenario(job: Dict) -> Dict:
    """All cases of one (writer, f0) scenario.  job: {"writer", "f0", "specs": {label: (name, params, sensor_kw)}}"""
    t0 = time.time()
    su = setup(job["writer"], job["f0"])
    scn, S_ = su["scn"], su["S"]
    neutral = su["neutral"]
    na = G.arrays(neutral)
    rows = {}
    rows["neutral"] = _metrics(su, neutral)
    rows["neutral_no_tremor"] = _metrics(su, su["clean"])
    rows["oracle_disturbance"] = _metrics(su, prun(M.with_disturbance(scn, M.housing_disturbance(scn, su["clean"])), "oracle", S_), na)
    rows["kfosc_internal"] = _metrics(su, M.run(scn, M.kalman_controller(q_lim=Q_LIM), M.PencilConfig(), seed=S_, rec_hz=REC_HZ), na)
    # the old template pull (guided core), as aiguide
    tr = su["tracks"]
    rows["pull_oracle"] = _metrics(su, prun(scn, "guided", S_), na)
    rows["pull_ai_correct"] = _metrics(su, prun(scn, "guided", S_, tmpl=tr["ai_correct"].xy), na)
    rows["pull_wrong_letter_full"] = _metrics(su, prun(scn, "guided", S_, tmpl=tr["wrong_letter"].xy), na)
    windows = G.letter_windows(su["wr"], float(na["t"][-1]))
    for name, trk, key in (("pull_ai_predicted", "ai_predicted", "conf"), ("pull_wrong_letter_gated", "wrong_letter", "wrong_conf")):
        levels = [G.quantise(G.authority(p[key])) for p in su["preds"]]
        runs = {}
        for lev in sorted(set(levels)):
            runs[lev] = na if lev == 0.0 else G.arrays(prun(scn, "guided", S_, tmpl=tr[trk].xy, g=lev))
        arr, info = G.splice(runs, levels, windows)
        cm = G.case_metrics(su["wr"], arr, su["rec"], Q_LIM, neutral=na, offset=su["off"])
        cmw = G.case_metrics(su["wr"], G.writing_only(arr), su["rec"], Q_LIM, neutral=G.writing_only(na), offset=su["off"])
        s = cm["summary"]
        rows[name] = {k: s.get(k) for k in ("path_rms_um", "path_p95_um", "dtw_mean_um", "recognition_accuracy", "at_soft_limit",
                                            "on_stop", "max_imposed_um")}
        rows[name].update({"wo_" + k: cmw["summary"].get(k) for k in ("path_rms_um", "dtw_mean_um", "recognition_accuracy")})
        rows[name]["splice_max_housing_jump_um"] = info["max_housing_jump_um"]
        rows[name]["_letters"] = cm["letters"]
        rows[name]["_letters_wo"] = cmw["letters"]
    # external estimators: sensor streams from the neutral tremor run
    rec1 = S.record_from_result(neutral, scn)
    tpls = context_templates(su)
    for label, (name, params, skw, tpl_key) in job["specs"].items():
        st = S.make_streams(rec1, S.config(**skw), 500_000 + 1000 * job["writer"] + int(job["f0"]))
        extra = {"template": tpls[tpl_key]} if tpl_key else None
        dh, info = ES.run_estimator(name, st, params, extra)
        res = M.run(M.with_estimate(scn, S.expand_to_steps(dh, len(scn.t), rec1.sdec)),
                    M.Controller(mode="external", **CFG["ctrl"]), M.PencilConfig(), seed=S_, rec_hz=REC_HZ)
        r = _metrics(su, res, na)
        for k in ("template_updates", "template_gated", "template_dropped_letters"):
            if k in info:
                r[k] = info[k]
        rows[label] = r
    # wrong-letter flips against the neutral run
    nl, nlw = rows["neutral"]["_letters"], rows["neutral"]["_letters_wo"]
    for lab in list(rows):
        if "wrong_letter" in lab:
            rows[lab]["flips"] = _flips(su, rows[lab]["_letters"], nl)
            rows[lab]["flips_wo"] = _flips(su, rows[lab]["_letters_wo"], nlw)
    for lab in rows:
        rows[lab].pop("_letters", None)
        rows[lab].pop("_letters_wo", None)
    te = {c: template_error_signal(su, c) for c in ("oracle", "ai_correct", "ai_predicted", "wrong_letter")}
    return {"writer": job["writer"], "f0": job["f0"], "rows": rows, "template_error": te,
            "prediction_accuracy": float(np.mean([p["correct"] for p in su["preds"]])),
            "elapsed_s": time.time() - t0}
