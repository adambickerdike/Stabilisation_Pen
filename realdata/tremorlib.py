"""The tremor library: every recording's tremor parameters, the severity classes and the tremor-only waveforms.

What each source contributes (details in docs/real_data.md):
  uci_spiral  PD and control pen-tip DISPLACEMENT while drawing (the only calibrated tip data): the severity
              classes in mm at the tip and the PD waveforms of the generator (2-D, real)
  zenodo_et   ET hand acceleration (a.u.), rest and posture: the ET waveforms of the generator (1-axis, real; made
              2-D by a documented construction; amplitude set by the class)
  newhandpd   PD and healthy pen ACCELERATION (derived gravity calibration): acceleration spectra
  pads        ET, PD and healthy WRIST acceleration (g) in rest, postural and kinetic tasks: rest/action behaviour,
              wrist amplitude (a lower bound of the tip's; statistics only)

Rules, fixed before any simulation used the library (the simulation outcomes never feed back into them):
  * roles (assign_roles): subjects are split into 'tuning' and 'test' FIRST; thresholds and class boundaries are
    fitted on the tuning subjects only and checked on the test subjects; HW1 uses test subjects only;
  * detection: a recording has a tremor line when its line ratio (dsp.tremor_params) is at least the 95th percentile
    of the TUNING control recordings of the same source (and condition, for PADS); Zenodo ET has no controls and
    uses the UCI control threshold (both are unit-free spectral contrasts; ASSUMPTION);
  * tip amplitude of a UCI recording = the background-corrected major-axis peak amplitude ('amp_excess');
  * a subject's tip amplitude = the median over its recordings with a line; severity classes over the detected
    TUNING PD subjects' tip amplitudes: mild = below their median, moderate = median to 90th percentile, severe = the
    top 10 % ('severe' means rare and large); 'none' = no line;
  * split: subjects of each source are sorted by a detection-free amplitude and assigned alternately (seeded coin per
    pair) to 'tuning' and 'test', so both splits span the severities; controls likewise; a subject's every recording
    (all tasks and sessions) is in one split;
  * a recording's waveform enters the generator when it has a line, its background share in f0 +- 1.5 Hz is at most
    0.35, it lasts at least 6 s (UCI) or 20 s (Zenodo, posture condition only: the action-tremor proxy), and its
    unit-power waveform (f0 +- 2 Hz and 2 f0 +- 2 Hz; dsp.power_amplitude) has a major-axis 99.9th percentile <= 4
    (a tremor line, not splices, clipping or pen-landing transients).
Waveforms are extracted with ZERO-PHASE filters (dsp.bandpass, dsp.acc_to_disp): simulation inputs only.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import CACHE_DIR
from . import dsp as D
from . import loaders as L

VERSION = "tremorlib-1"
WAVE_FS = 1000.0
BG_MAX = 0.35
MIN_S = {"uci_spiral": 6.0, "zenodo_et": 20.0}
PLAN_CLASSES_MM = {"mild": (0.3, 1.0), "moderate": (2.0, 4.0), "severe": (5.0, 10.0)}   # docs/round4_plan.md s6 (ASSUMPTION)
LIB_JSON = CACHE_DIR / "tremorlib.json"
WAVE_NPZ = CACHE_DIR / "tremor_waveforms.npz"


def _params_row(r: L.TremorRec) -> Dict:
    p = D.tremor_params(r.x, r.fs)
    row = {"rid": r.rid, "source": r.source, "subject": r.subject, "group": r.group, "task": r.task,
           "condition": r.condition, "quantity": r.quantity, "units": r.units, "fs": r.fs,
           "duration_s": round(r.duration, 3), "calib": r.calib}
    row.update({k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in p.items() if not k.startswith("_")})
    row["meta"] = {k: v for k, v in r.meta.items() if k not in ("gyro",) and not isinstance(v, np.ndarray)}
    if r.quantity == "displacement":
        row["amp_tip_mm"] = row["amp_excess"] * 1e3 if r.source == "uci_spiral" else None
    elif r.units == "m/s2":
        lo, hi = D.tremor_band_for(p["f0"])
        dp = D.tremor_params(D.acc_to_disp(r.x, r.fs, lo, hi), r.fs)
        key = "amp_wrist_mm" if r.source == "pads" else "amp_sensor_mm"
        row[key] = dp["amp_excess"] * 1e3
        row["disp_ellipticity"] = dp["ellipticity"]
        if r.source == "pads":
            g = r.meta.get("gyro")
            if g is not None:
                pg = D.tremor_params(g, r.fs)
                row["gyro_line_ratio"] = pg["line_ratio"]
                row["gyro_amp_deg"] = math.degrees(pg["amp_excess"]) / (2 * math.pi * max(pg["f0"], 0.5))
    return row


def _dedupe(recs: List[L.TremorRec]) -> Tuple[List[L.TremorRec], List[Dict]]:
    seen, keep, dups = {}, [], []
    for r in recs:
        h = hashlib.sha1(np.round(np.asarray(r.x) * 1e9).astype(np.int64).tobytes()).hexdigest()
        if h in seen:
            dups.append({"rid": r.rid, "same_as": seen[h]})
            continue
        seen[h] = r.rid
        keep.append(r)
    return keep, dups


def _split_subjects(amp_by_subject: Dict[str, float], seed: int) -> Dict[str, str]:
    """Sorted by amplitude, assigned alternately in pairs with a seeded coin: both splits span the severities."""
    subs = sorted(amp_by_subject, key=lambda s: (-amp_by_subject[s], s))
    rng = random.Random(seed)
    out = {}
    for i in range(0, len(subs), 2):
        pair = subs[i:i + 2]
        first = "tuning" if rng.random() < 0.5 else "test"
        other = "test" if first == "tuning" else "tuning"
        out[pair[0]] = first
        if len(pair) > 1:
            out[pair[1]] = other
    return out


def _waveform(r: L.TremorRec, row: Dict) -> np.ndarray:
    """Tremor-only waveform at WAVE_FS: the recording band-passed to f0 +- 2 Hz and 2 f0 +- 2 Hz (dsp.tremor_bands;
    acceleration converted to displacement band by band), normalised to unit power amplitude (dsp.power_amplitude:
    sqrt(2) x RMS of the major axis at f0 +- 2 Hz).  ZERO-PHASE extraction: simulation inputs only."""
    parts = []
    for lo, hi in D.tremor_bands(row["f0"]):
        if r.quantity == "displacement":
            parts.append(D.bandpass(r.x, r.fs, lo, hi))
        else:
            a = D.acc_to_disp(r.x, r.fs, lo, hi)
            parts.append(a[:, None] if a.ndim == 1 else a)
    w = np.sum(parts, axis=0)
    trim = int(0.5 * r.fs)
    w = w[trim:len(w) - trim]
    if r.fs != WAVE_FS:
        t = np.arange(len(w)) / r.fs
        _, w = D.uniform(t, w, WAVE_FS)
    return (w / max(D.power_amplitude(w, WAVE_FS, row["f0"]), 1e-30)).astype(np.float32)


def waveform_quality(w: np.ndarray, f0: float) -> Dict:
    """Checks of a unit-power-amplitude waveform: the 99.9th percentile of the major axis (a steady sinusoid gives
    1.0; real amplitude modulation 1.5-3; splices, clipping and pen-landing transients give much more) and the
    intermittency (median Hilbert envelope / power amplitude: 1 for steady tremor, small when it comes and goes)."""
    X = np.asarray(w, float)
    if X.shape[1] > 1:
        _, _, Y = D.principal_axes(X - X.mean(0))
        m = Y[:, 0]
    else:
        m = X[:, 0]
    es = D.envelope_stats(D.bandpass(m, WAVE_FS, max(1.0, f0 - 2.0), f0 + 2.0), WAVE_FS)
    return {"major_p999": float(np.percentile(np.abs(m), 99.9)), "intermittency": es["amp_median"],
            "env_cv": es["env_cv"]}


P999_MAX = 4.0


def assign_roles(rows: List[Dict], sources: Sequence[str], log=print) -> Tuple[Dict, Dict]:
    """The four data roles, in this order (review 2026-09-29 s11):
      split       subject level, per source and group, BEFORE anything is fitted (every recording, window and
                  session of a person goes to one split); stratified by a detection-free amplitude
      calibration unit conversions from device documents or calibration recordings only (calib.py; no split used)
      fitting     detection thresholds from the TUNING controls; severity class boundaries from the TUNING PD subjects
      validation  the class boundaries checked on the TEST subjects (share per class; reported, never refitted)
      final test  HW1 uses TEST-split waveforms and writers only
    Returns (thresholds, classes); sets x['split'], x['threshold'], x['detected'], x['class'] in place."""
    # ---------------------------------------------------------------- split (subject level, detection-free)
    split: Dict[Tuple[str, str], str] = {}
    for src in sources:
        amp = {}
        for x in rows:
            if x["source"] != src:
                continue
            a_ = x.get("amp_tip_mm") or x.get("amp_wrist_mm") or x.get("amp_sensor_mm") or x.get("line_ratio") or 0.0
            key = f"{x['group']}:{x['subject']}"
            amp[key] = max(amp.get(key, 0.0), float(a_) if np.isfinite(a_) else 0.0)
        for grp in {k.split(":")[0] for k in amp}:
            sub = {k: v for k, v in amp.items() if k.startswith(grp + ":")}
            seed = int(hashlib.sha1(f"{src}/{grp}".encode()).hexdigest()[:8], 16)
            for k, v in _split_subjects(sub, seed).items():
                split[(src, k.split(":", 1)[1])] = v
    for x in rows:
        x["split"] = split.get((x["source"], x["subject"]), "test")
    # ---------------------------------------------------------------- fitting: thresholds from TUNING controls
    thr: Dict[str, float] = {}
    for src in sources:
        ctl = [x for x in rows if x["source"] == src and x["group"] == "control" and x["split"] == "tuning"]
        if src == "pads":
            for cond in ("rest", "postural", "kinetic"):
                v = [x["line_ratio"] for x in ctl if x["condition"] == cond]
                if v:
                    thr[f"pads/{cond}"] = float(np.percentile(v, 95))
        elif ctl:
            thr[src] = float(np.percentile([x["line_ratio"] for x in ctl], 95))
    if "zenodo_et" in sources:
        thr["zenodo_et"] = thr.get("uci_spiral", 5.0)
    for x in rows:
        key = f"pads/{x['condition']}" if x["source"] == "pads" else x["source"]
        x["threshold"] = thr.get(key)
        x["detected"] = bool(x["threshold"] is not None and x["line_ratio"] >= x["threshold"] and 3.0 <= x["f0"] <= 12.0)
    thr["_fitted_on"] = "tuning-split controls (95th percentile of the line ratio)"
    # ---------------------------------------------------------------- fitting: classes from TUNING PD subjects
    pd_sub: Dict[str, List[float]] = {}
    for x in rows:
        if x["source"] == "uci_spiral" and x["group"] == "PD" and x["detected"]:
            pd_sub.setdefault(x["subject"], []).append(x["amp_tip_mm"])
    sub_amp = {s_: float(np.median(v)) for s_, v in pd_sub.items()}
    sub_split = {x["subject"]: x["split"] for x in rows if x["source"] == "uci_spiral" and x["group"] == "PD"}
    classes: Dict = {}
    fit = np.array(sorted(v for s_, v in sub_amp.items() if sub_split.get(s_) == "tuning"))
    if len(fit) >= 4:
        a = fit
        q50, q90 = np.percentile(a, [50, 90])
        ctl_amp = [x["amp_excess"] * 1e3 for x in rows if x["source"] == "uci_spiral" and x["group"] == "control"
                   and x["split"] == "tuning"]
        classes = {
            "none": {"range_mm": [0.0, float(a.min())], "representative_mm": float(np.median(ctl_amp)) if ctl_amp else 0.03,
                     "definition": "no tremor line above the tuning controls' 95th percentile; representative = median "
                                   "background-corrected amplitude of the tuning control recordings (sensor and pixel "
                                   "noise included)"},
            "mild": {"range_mm": [float(a.min()), float(q50)], "n_subjects": int(np.sum(a < q50)),
                     "definition": "below the median of the tuning PD subjects with a tremor line"},
            "moderate": {"range_mm": [float(q50), float(q90)], "n_subjects": int(np.sum((a >= q50) & (a < q90))),
                         "definition": "median to 90th percentile"},
            "severe": {"range_mm": [float(q90), float(a.max())], "n_subjects": int(np.sum(a >= q90)),
                       "definition": "the top 10 % (upper end = the largest tuning subject; larger test subjects exist)"},
        }
        for k in ("mild", "moderate", "severe"):
            lo_, hi_ = classes[k]["range_mm"]
            sel = a[(a >= lo_) & (a <= hi_)]
            classes[k]["representative_mm"] = float(np.median(sel)) if len(sel) else float(np.sqrt(lo_ * hi_))
            classes[k]["definition"] += (" of the peak (major semi-axis) tremor amplitude at the pen tip of PD subjects "
                                         "with a tremor line while drawing spirals on a tablet (DATA uci_spiral; one "
                                         "value per subject = median over its recordings with a line; boundaries "
                                         "fitted on the tuning subjects only)")
        classes["_n_pd_subjects_with_line"] = int(len(sub_amp))
        classes["_n_fit_subjects"] = int(len(a))
        classes["_n_pd_subjects"] = int(len({x["subject"] for x in rows if x["source"] == "uci_spiral" and x["group"] == "PD"}))
        classes["_quantiles_mm"] = {"p10": float(np.percentile(a, 10)), "p25": float(np.percentile(a, 25)),
                                    "p50": float(q50), "p75": float(np.percentile(a, 75)), "p90": float(q90),
                                    "max": float(a.max())}
        classes["_subject_amplitudes_mm"] = sorted(float(v) for v in a)
        classes["_plan_assumption_mm"] = PLAN_CLASSES_MM
        classes["_fitted_on"] = "tuning-split PD subjects of uci_spiral"
        # validation on held-out subjects: the boundaries are not refitted
        tst = np.array(sorted(v for s_, v in sub_amp.items() if sub_split.get(s_) == "test"))
        if len(tst):
            classes["_validation_test_subjects"] = {
                "n": int(len(tst)),
                "share_mild": float(np.mean(tst < q50)), "share_moderate": float(np.mean((tst >= q50) & (tst < q90))),
                "share_severe": float(np.mean(tst >= q90)),
                "p50_mm": float(np.percentile(tst, 50)), "p90_mm": float(np.percentile(tst, 90)),
                "expected_shares": {"mild": 0.5, "moderate": 0.4, "severe": 0.1}}
        allv = np.array(sorted(sub_amp.values()))
        classes["_all_subjects_descriptive"] = {"n": int(len(allv)), "p50_mm": float(np.percentile(allv, 50)),
                                                "p90_mm": float(np.percentile(allv, 90)), "max_mm": float(allv.max())}
    for x in rows:
        if x["source"] == "uci_spiral" and x["group"] == "PD":
            s_amp = sub_amp.get(x["subject"])
            x["subject_amp_tip_mm"] = s_amp
            x["class"] = _class_of(s_amp, classes) if (s_amp is not None and classes) else "none"
    return thr, classes


def refresh_roles(quick: bool = False, log=print) -> Dict:
    """Re-apply the roles (split, thresholds, classes) to the cached per-recording parameters, then re-extract the
    generator waveforms (UCI and Zenodo are re-read).  The per-recording parameters are unchanged."""
    tag = "_quick" if quick else ""
    p = CACHE_DIR / f"tremorlib{tag}.json"
    lib = json.loads(p.read_text())
    sources = sorted({x["source"] for x in lib["rows"]})
    thr, classes = assign_roles(lib["rows"], sources, log)
    lib["thresholds"], lib["classes"] = thr, classes
    lib["rules"] = __doc__.split("Rules, fixed")[1].split("Waveforms are")[0].strip()
    p.write_text(json.dumps(lib, default=_jd))
    _LIB.pop(tag, None)
    return refresh_generator(quick, log)


def refresh_generator(quick: bool = False, log=print) -> Dict:
    """Recompute only the generator waveforms and their eligibility on the cached library (the UCI and Zenodo
    recordings are re-read; parameters, thresholds, classes and splits are unchanged)."""
    tag = "_quick" if quick else ""
    lib = json.loads((CACHE_DIR / f"tremorlib{tag}.json").read_text())
    rows = {x["rid"]: x for x in lib["rows"]}
    waves = {}
    recs = L.uci_spiral_records() + L.zenodo_et_records()
    for r in recs:
        x = rows.get(r.rid)
        if x is None:
            continue
        src = r.source
        ok = (x["detected"] and x["background_share"] <= BG_MAX and x["duration_s"] >= MIN_S[src]
              and (src != "zenodo_et" or x["condition"] == "postural") and x["group"] in ("PD", "ET"))
        x.pop("waveform_quality", None)
        if ok:
            w = _waveform(r, x)
            q = waveform_quality(w, x["f0"])
            x["waveform_quality"] = q
            ok = q["major_p999"] <= P999_MAX
            if ok:
                waves[r.rid] = w
        x["generator"] = bool(ok)
    e2 = [x for x in lib["rows"] if x["source"] == "uci_spiral" and x.get("generator")]
    if e2:
        lib["shape_2d"] = {"ellipticity_median": float(np.median([x["ellipticity"] for x in e2])),
                           "ellipticity_iqr": [float(np.percentile([x["ellipticity"] for x in e2], 25)),
                                               float(np.percentile([x["ellipticity"] for x in e2], 75))],
                           "n": len(e2), "label": "DATA uci_spiral (PD, tip, 2-D), recordings in the generator"}
    lib["generator_rule"] = (f"line detected, background share <= {BG_MAX}, duration >= {MIN_S}, Zenodo posture only, "
                             f"unit-power waveform 99.9th percentile <= {P999_MAX}")
    (CACHE_DIR / f"tremorlib{tag}.json").write_text(json.dumps(lib, default=_jd))
    np.savez_compressed(CACHE_DIR / f"tremor_waveforms{tag}.npz", **{k.replace("/", "|"): v for k, v in waves.items()})
    _LIB.pop(tag, None)
    _WAV.pop(tag, None)
    n = {s: sum(1 for x in lib["rows"] if x.get("generator") and x["source"] == s) for s in ("uci_spiral", "zenodo_et")}
    log(f"[tremorlib] generator waveforms: {n}")
    return lib


def build(quick: bool = False, log=print, sources: Sequence[str] = ("uci_spiral", "zenodo_et", "newhandpd", "pads")) -> Dict:
    t0 = time.time()
    rows: List[Dict] = []
    dups_all: List[Dict] = []
    waves: Dict[str, np.ndarray] = {}
    recs_by_source: Dict[str, List[L.TremorRec]] = {}
    extra: Dict = {}
    if "uci_spiral" in sources:
        recs, dups = _dedupe(L.uci_spiral_records())
        recs_by_source["uci_spiral"] = recs
        dups_all += dups
    if "zenodo_et" in sources:
        recs_by_source["zenodo_et"] = L.zenodo_et_records()
    if "newhandpd" in sources:
        cal = L.newhandpd_gravity(max_files=60 if quick else 400)
        extra["newhandpd_calibration"] = cal
        tasks = ("spiral", "meander", "circle")
        recs = L.newhandpd_records(cal, tasks=tasks)
        if quick:
            recs = recs[::6]
        recs, dups = _dedupe(recs)
        dups_all += dups
        recs_by_source["newhandpd"] = recs
    if "pads" in sources:
        recs = L.pads_records()
        if quick:
            recs = recs[::10]
        recs_by_source["pads"] = recs
    for src, recs in recs_by_source.items():
        log(f"[tremorlib] {src}: {len(recs)} recordings")
        for r in recs:
            rows.append(_params_row(r))
    thr, classes = assign_roles(rows, list(recs_by_source))
    # ---------------------------------------------------------------- generator waveforms
    for src in ("uci_spiral", "zenodo_et"):
        for r in recs_by_source.get(src, []):
            x = next(z for z in rows if z["rid"] == r.rid)
            ok = (x["detected"] and x["background_share"] <= BG_MAX and x["duration_s"] >= MIN_S[src]
                  and (src != "zenodo_et" or x["condition"] == "postural") and x["group"] in ("PD", "ET"))
            if ok:
                w = _waveform(r, x)
                q = waveform_quality(w, x["f0"])
                x["waveform_quality"] = q
                ok = q["major_p999"] <= P999_MAX
                if ok:
                    waves[r.rid] = w
            x["generator"] = bool(ok)
    # ellipticity and orientation of real 2-D tip tremor (for the ET construction)
    e2 = [x for x in rows if x["source"] == "uci_spiral" and x.get("generator")]
    shape = {"ellipticity_median": float(np.median([x["ellipticity"] for x in e2])) if e2 else 0.4,
             "ellipticity_iqr": [float(np.percentile([x["ellipticity"] for x in e2], 25)),
                                 float(np.percentile([x["ellipticity"] for x in e2], 75))] if e2 else [0.3, 0.5],
             "n": len(e2), "label": "DATA uci_spiral (PD, tip, 2-D), recordings in the generator"}
    lib = {"version": VERSION, "rows": rows, "thresholds": thr, "classes": classes, "duplicates": dups_all,
           "shape_2d": shape, "extra": extra, "elapsed_s": time.time() - t0, "quick": quick,
           "rules": __doc__.split("Rules, fixed")[1].split("Waveforms are")[0].strip()}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tag = "_quick" if quick else ""
    (CACHE_DIR / f"tremorlib{tag}.json").write_text(json.dumps(lib, default=_jd))
    np.savez_compressed(CACHE_DIR / f"tremor_waveforms{tag}.npz", **{k.replace("/", "|"): v for k, v in waves.items()})
    log(f"[tremorlib] {len(rows)} rows, {len(waves)} generator waveforms, {len(dups_all)} duplicates removed, "
        f"{time.time() - t0:.0f} s")
    return lib


def _class_of(a_mm: float, classes: Dict) -> str:
    for k in ("mild", "moderate", "severe"):
        lo, hi = classes[k]["range_mm"]
        if lo <= a_mm <= hi + 1e-12:
            return k
    return "severe" if a_mm > classes["severe"]["range_mm"][0] else "none"


def _jd(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


_LIB: Dict[str, Dict] = {}
_WAV: Dict[str, Dict[str, np.ndarray]] = {}


def load(quick: bool = False) -> Dict:
    tag = "_quick" if quick else ""
    if tag not in _LIB:
        p = CACHE_DIR / f"tremorlib{tag}.json"
        if not p.exists():
            if quick and (CACHE_DIR / "tremorlib.json").exists():
                return load(False)
            raise FileNotFoundError(f"{p}: run python3 -m realdata.run --stages tremor")
        _LIB[tag] = json.loads(p.read_text())
    return _LIB[tag]


def waveforms(quick: bool = False) -> Dict[str, np.ndarray]:
    tag = "_quick" if quick else ""
    if tag not in _WAV:
        p = CACHE_DIR / f"tremor_waveforms{tag}.npz"
        if not p.exists() and quick:
            return waveforms(False)
        z = np.load(p)
        _WAV[tag] = {k.replace("|", "/"): z[k] for k in z.files}
    return _WAV[tag]


def summary(lib: Dict) -> Dict:
    """Per source and group: counts, detection share and parameter medians (the committed statistics)."""
    out = {}
    rows = lib["rows"]
    for src in sorted({x["source"] for x in rows}):
        for grp in sorted({x["group"] for x in rows if x["source"] == src}):
            for cond in sorted({x["condition"] for x in rows if x["source"] == src and x["group"] == grp}):
                sel = [x for x in rows if x["source"] == src and x["group"] == grp and x["condition"] == cond]
                det = [x for x in sel if x["detected"]]
                e = {"n_recordings": len(sel), "n_subjects": len({x["subject"] for x in sel}),
                     "detected_share": len(det) / max(len(sel), 1)}
                for k in ("f0", "env_cv", "f_sd", "harmonic_excess", "ellipticity", "line_ratio", "amp_tip_mm",
                          "amp_sensor_mm", "amp_wrist_mm"):
                    v = [x[k] for x in det if x.get(k) is not None and np.isfinite(x[k])]
                    if v:
                        e[k] = {"median": float(np.median(v)), "p25": float(np.percentile(v, 25)),
                                "p75": float(np.percentile(v, 75)), "n": len(v)}
                out[f"{src}/{grp}/{cond}"] = e
    return out
