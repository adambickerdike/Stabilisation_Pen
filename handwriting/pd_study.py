"""Task 3: Parkinson's micrographia, before and after (SIMULATION, model HW1; writer response = ASSUMPTION ranges).

Writers: aiguide test writers 0-5 (style) made PD-like (ASSUMPTION): start x-height 5.0 mm (PDT-06), slower
(x 0.5-0.7), progressive size loss of 20-30 % over the pangram (PDT-05: -23 %), small tremor 4-6 Hz, 0.05-0.25 mm
at the hand (PDT-07: rest tremor diminishes during writing).  Seeds 200-203 draw the ranges and the tremor.

Interventions
  pen_none        ordinary pen, no help
  revH_off        Rev H with every function off (the 75 g pen)
  cue             Rev H's vibration cue 'write bigger' when a letter is > 10 % below the writer's start size; the
                  writer's response (recovery 50-100 % of the deficit, movement time x 1.10-1.20 for 3 letters) is an
                  ASSUMPTION range built on PDT-19 (verbal/visual cues: size up mainly through longer movement time)
  lines           >= 1 cm target lines (paper; PDT-18, PDT-33): the size loss kept at 30-70 %, size jitter at 70 %
  size_assist_G   the nose amplifies the writer's strokes: q = (G - 1) (p_hat - LP_tau(p_hat)), G = 1.2 / 1.35 / 1.5
                  (both axes), within +-3 mm; a novel, untested function
  size_assist_y   vertical-only gain 1.35
  size_adapt_y    adaptive vertical gain (up to 1.5) that restores the writer's start letter size: the app measures
                  each finished letter's size on the unassisted hand path (ink minus nose offset; +-3 % ASSUMPTION)
                  and, 0.2 s later, sets G = start size / median of the last 3 letters; a design variant, untested
  cue_size        cue plus size assist 1.35
Metrics: per-letter x-height (start = first 5 letters, end = last 5), recognition, words read by the app, fluency
(normalised jerk, speed peaks per stroke, speed; PDT-17), the tremor in the ink (3-15 Hz, from paired runs with and
without tremor), writing time, and letter crowding (share of neighbouring letters within a word whose inks come within
0.15 mm).  The size-assist anchor time constant tau_sa is chosen on tuning writers (tuning.size_tau; run_study passes it).
"""
from __future__ import annotations

import math
import time
from typing import Dict, List

import numpy as np

from . import ensure_paths
from . import metrics as MT
from . import params as PR
from . import plant as PL
from . import writers as W

ensure_paths()

CONDITIONS = ["pen_none", "revH_off", "cue", "lines", "size_assist_1.2", "size_assist_1.35", "size_assist_1.5",
              "size_assist_y1.35", "size_adapt_y1.5", "cue_size_1.35"]
LABELS = {"pen_none": "No device (ordinary pen)", "revH_off": "Rev H, functions off", "cue": "Vibration cue 'write bigger'",
          "lines": "Lines >= 1 cm", "size_assist_1.2": "Size assist x1.2", "size_assist_1.35": "Size assist x1.35",
          "size_assist_1.5": "Size assist x1.5", "size_assist_y1.35": "Size assist x1.35, vertical only",
          "size_adapt_y1.5": "Adaptive size assist, vertical (restores the start size, up to x1.5)",
          "cue_size_1.35": "Cue + size assist x1.35"}
TAU_SA_CANDIDATES = (0.2, 0.4, 0.8)
TAU_SA_DEFAULT = 0.4
VIZ = {"writer": 0, "seed": 200}


def pd_written(w: int, seed: int, mode: str, text: str = W.PD_SENTENCE):
    prof = W.pd_profile(1000 * w + seed)
    base = W.writer(w)
    st = base.style
    wtr = W.writer(w, x_height_mm=prof.h0_mm, speed_mm_s=st.speed_mm_s * prof.speed_factor,
                   air_speed_mm_s=st.air_speed_mm_s * prof.speed_factor,
                   scale_jitter=st.scale_jitter * (prof.lines_jitter if mode == "lines" else 1.0))
    n = sum(1 for c in text if c != " ")
    sched_mode = "cue" if mode.startswith("cue") else ("lines" if mode == "lines" else "none")
    s, tempo, cues = W.pd_schedule(n, prof, sched_mode, np.random.default_rng(5_000 + 1000 * w + seed))
    wr = wtr.write(text, dt=W.SIM_DT, seed=4000 + w, size_factors=s, tempo_factors=tempo)
    return wr, prof, {"size_factors": s.tolist(), "tempo": tempo.tolist(), "cues": cues}


def crowding(rows: List[Dict], written, res, touch: float = 0.15e-3) -> Dict:
    """Closest approach of neighbouring letters' ink within a word; 'touching' when closer than 0.15 mm."""
    from scipy.spatial import cKDTree
    t = res.t
    pts = []
    for L in written.letters:
        m = (t >= L.t0 - 0.01) & (t <= L.t1 + 0.01) & (res.contact > 0.5)
        pts.append((res.ink[m][::4], L.word_index) if m.sum() >= 2 else None)
    dmins = []
    for a, b in zip(pts[:-1], pts[1:]):
        if a is None or b is None or a[1] != b[1] or len(a[0]) == 0 or len(b[0]) == 0:
            continue
        d, _ = cKDTree(a[0]).query(b[0])
        dmins.append(float(d.min()))
    if not dmins:
        return {"touching_frac": float("nan"), "gap_median_mm": float("nan")}
    dmins = np.array(dmins)
    return {"touching_frac": float(np.mean(dmins < touch)), "gap_median_mm": float(np.median(dmins) * 1e3)}


def tremor_in_ink(r, r0, band=(3.0, 15.0)) -> float:
    """3-15 Hz RMS of (ink with tremor - ink of the same condition without tremor), in contact (um)."""
    from scipy.signal import butter, sosfiltfilt
    n = min(len(r.t), len(r0.t))
    e = r.ink[:n] - r0.ink[:n]
    fs = 1.0 / float(r.t[1] - r.t[0])
    eb = sosfiltfilt(butter(4, band, btype="band", fs=fs, output="sos"), e, axis=0)
    m = r.contact[:n] > 0.5
    return float(np.sqrt(np.mean(np.sum(eb[m] ** 2, axis=1))) * 1e6)


def adaptive_gain_track(wr, n_ticks: int, Ts: float, rng: np.random.Generator, g_max: float = 1.5, n_ref: int = 3,
                        n_win: int = 3, meas_noise: float = 0.03, latency: float = 0.2) -> np.ndarray:
    """Causal per-letter gain schedule: after letter j ends (+ app latency), G = clip(h_ref / median(last n_win), 1, g_max)."""
    sizes = np.array([L.size for L in wr.letters]) * (1.0 + meas_noise * rng.standard_normal(len(wr.letters)))
    h_ref = float(np.median(sizes[:n_ref]))
    g = np.ones(n_ticks)
    for j, L in enumerate(wr.letters):
        if j < n_ref - 1:
            continue
        val = float(np.clip(h_ref / np.median(sizes[max(0, j - n_win + 1):j + 1]), 1.0, g_max))
        k0 = int(round((L.t1 + latency) / Ts))
        if k0 < n_ticks:
            g[k0:] = val
    return g


def run_condition(w: int, seed: int, cond: str, hand: PR.Hand, tau_sa: float = TAU_SA_DEFAULT, keep: bool = False) -> Dict:
    wr, prof, sched = pd_written(w, seed, cond)
    pen = PR.ordinary_pen() if cond == "pen_none" else PR.rev_h()
    scn0 = PL.scenario_from_written(wr, None, meta={"writer": w})
    hp = PL.adapted_path(scn0.intended, scn0.dt, pen, hand)
    rs = 10_000 * w + seed
    d = W.tremor_path(scn0.t, prof.tremor_hz, prof.tremor_amp, seed, w)
    scn = PL.with_hand_path(scn0, hp, d)
    G = (1.0, 1.0)
    if "size" in cond:
        g = float(cond.split("_")[-1].lstrip("y"))
        G = (1.0, g) if "_y" in cond else (g, g)
    track = None
    if "adapt" in cond:
        Ts = 1.0 / pen.tick_hz
        track = adaptive_gain_track(wr, int(len(scn0.t) * scn0.dt / Ts) + 2, Ts, np.random.default_rng(77_000 + rs), g_max=G[1])
    ctl = PL.Controls(size_gain=G, tau_sa=tau_sa, size_gain_track=track)
    r = PL.run(scn, pen, hand, ctl=ctl, seed=rs)
    r0 = PL.run(PL.with_hand_path(scn0, hp, None), pen, hand, ctl=ctl, seed=rs)   # same condition without tremor
    rec = MT.recognizer_for(wr)
    rows = MT.letter_rows(wr, r, rec)
    s = MT.summary(rows)
    wd = MT.words(rows, W.PD_SENTENCE)
    xh = MT.xheight_mm(rows)
    xh_int = np.array([L.size * 1e3 for L in wr.letters])
    flu = MT.fluency(r)
    out = {"writer": w, "seed": seed, "cond": cond, "size_gain": list(G),
           "xh_start_mm": float(np.nanmean(xh[:5])), "xh_end_mm": float(np.nanmean(xh[-5:])),
           "xh_mean_mm": float(np.nanmean(xh)), "xh_intended_start_mm": float(np.mean(xh_int[:5])),
           "xh_intended_end_mm": float(np.mean(xh_int[-5:])), "recognition": s.get("recognition_accuracy"),
           "dtw_um": s.get("dtw_mean_um"), "word_acc_app": wd.get("word_accuracy_app"),
           "word_acc_letters": wd["word_accuracy_letters"], "recognised": " ".join(wd["recognised"]),
           "band_err_um": MT.band_error_um(r, scn), "tremor_in_ink_um": tremor_in_ink(r, r0),
           "tremor_at_hand_um": float(np.sqrt(np.mean(np.sum(d[scn.down > 0.5] ** 2, axis=1))) * 1e6),
           "writing_time_s": float(wr.letters[-1].t1 - wr.letters[0].t0),
           "n_cues": len(sched["cues"]), "profile": {k: float(v) for k, v in vars(prof).items()}}
    out["xh_drift"] = out["xh_end_mm"] / max(out["xh_start_mm"], 1e-9)
    out["xh_end_vs_writer_start"] = out["xh_end_mm"] / prof.h0_mm
    out.update(flu)
    out.update(crowding(rows, wr, r))
    out.update(MT.travel(r, pen))
    out["xh_per_letter_mm"] = [None if not np.isfinite(v) else float(v) for v in xh]
    if keep:
        out["_paths"] = {"ink": MT.decimate_path(r, hz=250.0).tolist(), "intended": MT.intended_path(scn0, hz=250.0).tolist(),
                         "cues_t": [float(wr.letters[i].t0) for i in sched["cues"] if i < len(wr.letters)],
                         "cue_letters": sched["cues"]}
    return out


def writer_job(job: Dict) -> Dict:
    t0 = time.time()
    hand = PR.Hand.from_config()
    rows, viz = [], {}
    for seed in job["seeds"]:
        for cond in job.get("conds", CONDITIONS):
            keep = job.get("viz") and seed == VIZ["seed"]
            r = run_condition(job["writer"], seed, cond, hand, tau_sa=job.get("tau_sa", TAU_SA_DEFAULT), keep=keep)
            if keep:
                viz[cond] = r.pop("_paths")
            rows.append(r)
    return {"writer": job["writer"], "rows": rows, "viz": viz, "elapsed_s": time.time() - t0}


def tune_tau(writers=(100, 101, 102, 103, 104, 105), seeds=(300, 301)) -> Dict:
    """Pre-declared rule on tuning writers/seeds only: the anchor time constant with the highest mean recognition at
    G = 1.35 (both axes); ties broken toward the longer constant (less phase distortion)."""
    hand = PR.Hand.from_config()
    res = {}
    for tau in TAU_SA_CANDIDATES:
        acc = [run_condition(w, s, "size_assist_1.35", hand, tau_sa=tau)["recognition"] for w in writers for s in seeds]
        res[tau] = float(np.mean(acc))
    best = max(TAU_SA_CANDIDATES, key=lambda t: (round(res[t], 3), t))
    return {"candidates": {str(k): v for k, v in res.items()}, "chosen": best, "rule": tune_tau.__doc__,
            "writers": list(writers), "seeds": list(seeds)}


def aggregate(outs: List[Dict]) -> Dict:
    rows = [r for o in outs for r in o["rows"]]
    keys = ["xh_start_mm", "xh_end_mm", "xh_drift", "xh_end_vs_writer_start", "xh_mean_mm", "recognition", "dtw_um",
            "word_acc_app", "band_err_um", "norm_jerk_median", "speed_peaks_per_stroke", "mean_speed_mm_s",
            "peak_speed_mm_s", "writing_time_s", "n_cues", "touching_frac", "gap_median_mm", "at_travel_limit", "q_rms_mm",
            "tremor_in_ink_um", "tremor_at_hand_um"]
    by = {}
    for c in CONDITIONS:
        sel = [r for r in rows if r["cond"] == c]
        if not sel:
            continue
        by[c] = {k: float(np.nanmean([r[k] for r in sel if r.get(k) is not None])) for k in keys if any(r.get(k) is not None for r in sel)}
        by[c].update({k + "_sd": float(np.nanstd([r[k] for r in sel if r.get(k) is not None])) for k in ("xh_end_mm", "recognition", "norm_jerk_median") if any(r.get(k) is not None for r in sel)})
        by[c]["n"] = len(sel)
        prof = np.array([r["xh_per_letter_mm"] for r in sel], dtype=float)
        by[c]["xh_profile_mm"] = np.nanmean(prof, axis=0).tolist()
    return {"by_condition": by, "n_rows": len(rows)}
