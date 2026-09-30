#!/usr/bin/env python3
"""Score a recorded handwriting trace with the same definitions as the simulations (bridge to EXP-HW1..5).

Input: a CSV with columns t_s, x, y, pen_down (0/1) in mm (or --units m), from a digitising tablet, the pen's own
page sensor, or a motion-capture of the tip.  Output (JSON to stdout or --out):
  tremor     narrow spectral peak of the pen-down velocity above the broadband writing spectrum: frequency,
             peak-to-floor ratio and displacement RMS of the excess (tremor_peak); plus the raw 3-15 Hz RMS of the ink
             (includes the writing's own fast strokes: compare only between conditions with the same person and text)
  size       vertical extent of every pen-down stroke along the trace; first-quarter vs last-quarter median and the
             relative change (progressive micrographia estimate; PDT-05 uses > 10 % as the threshold)
  fluency    normalised jerk (PDT-17 definition), speed peaks per stroke, mean speed (metrics.fluency)
  pauses     share of time with the pen up, number of pen-up gaps longer than 150 ms
  target     if --target (CSV x, y in the same frame) is given: RMS nearest-point distance of the ink to the target
Evidence status of any output: MEASUREMENT only if the input is a real recording; the script itself is a CALCULATION.

  python3 -m handwriting.score_recording trace.csv [--units mm] [--target target.csv] [--out result.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

from . import ensure_paths
from . import metrics as MT

ensure_paths()


@dataclass
class Trace:
    t: np.ndarray
    ink: np.ndarray
    contact: np.ndarray


def load(path: str, units: str = "mm", rate: float = 0.0) -> Trace:
    a = np.genfromtxt(path, delimiter=",", names=True)
    t = np.asarray(a["t_s"], float)
    xy = np.column_stack([a["x"], a["y"]]).astype(float) * (1e-3 if units == "mm" else 1.0)
    d = np.asarray(a["pen_down"], float)
    fs = rate if rate > 0 else 1.0 / float(np.median(np.diff(t)))
    tu = np.arange(t[0], t[-1], 1.0 / fs)                          # uniform resampling
    xy_u = np.column_stack([np.interp(tu, t, xy[:, 0]), np.interp(tu, t, xy[:, 1])])
    d_u = np.interp(tu, t, d) > 0.5
    return Trace(tu - tu[0], xy_u, d_u.astype(float))


def tremor_peak(v: np.ndarray, m: np.ndarray, fs: float, band=(3.0, 15.0), half_width: float = 0.75,
                tremor_hz: float = 0.0, detect_ratio: float = 3.0) -> dict:
    """Tremor as a narrow spectral peak above the broadband writing spectrum (pen-down velocity).

    Welch PSD (4 s windows) of the pen-down velocity; the broadband floor is a +-2 Hz running median of the log PSD;
    the peak is the largest PSD/floor ratio in 3-15 Hz; the tremor amplitude is the excess power within +-0.75 Hz
    of the peak, converted to displacement RMS (sqrt(excess)/(2 pi f)).  Writing rhythm (about 4-6 Hz for
    repeated letters such as 'minimum') can mimic a 4-6 Hz tremor peak: use a paired device-off recording of the
    same text, a tracing task, or the IMU at rest to confirm it.  With tremor_hz (for example the IMU posture-test
    peak) the excess is taken at that frequency instead of the largest ratio.
    Synthetic check (tests/test_score.py and CALC notes in docs/handwriting_outcomes.md): a 0.5 mm tremor is found
    with a peak/floor ratio of 6-18 and its RMS reads 75-90 % of the truth (pen lifts spread the line); clean
    synthetic writing gives ratios of 1.6-2.2; the detection limit in free writing is about 0.2-0.3 mm amplitude.
    """
    from scipy.ndimage import median_filter
    vv = np.where(m[:, None], v, 0.0)
    f, p = welch(vv, fs=fs, nperseg=min(len(vv), int(4 * fs)), axis=0)
    p = p.sum(axis=1) / max(float(m.mean()), 1e-9)                 # PSD while the pen is down
    df = float(f[1] - f[0])
    k = max(1, int(round(2.0 / df)))
    floor = np.exp(median_filter(np.log(p + 1e-30), size=2 * k + 1, mode="nearest"))
    sel = (f >= band[0]) & (f <= min(band[1], 0.45 * fs))
    if not sel.any():
        return {}
    ratio = p / floor
    if tremor_hz > 0:
        i = int(np.argmin(np.abs(f - tremor_hz)))
    else:
        i = int(np.flatnonzero(sel)[np.argmax(ratio[sel])])
    fp = float(f[i])
    win = np.abs(f - fp) <= half_width
    excess = float(np.clip(p[win] - floor[win], 0.0, None).sum() * df)
    return {"tremor_peak_hz": fp, "tremor_peak_to_floor": float(ratio[i]),
            "tremor_peak_detected": bool(ratio[i] >= detect_ratio),
            "tremor_amp_rms_um": math.sqrt(excess) / (2 * math.pi * fp) * 1e6,
            "velocity_energy_3_15hz_share": float(p[sel].sum() / max(p.sum(), 1e-30))}


def score(tr: Trace, target: np.ndarray = None, tremor_hz: float = 0.0) -> dict:
    fs = 1.0 / float(tr.t[1] - tr.t[0])
    m = tr.contact > 0.5
    out = {"duration_s": float(tr.t[-1]), "sample_rate_hz": fs, "pen_down_share": float(m.mean())}
    if fs > 30.0:
        band = sosfiltfilt(butter(4, [3.0, min(15.0, 0.45 * fs)], btype="band", fs=fs, output="sos"), tr.ink, axis=0)
        # raw 3-15 Hz content: includes the writing's own fast strokes (about 0.6 mm RMS for clean synthetic writing),
        # so compare it only between conditions of the same person writing the same text
        out["band_3_15hz_rms_um_raw"] = float(np.sqrt(np.mean(np.sum(band[m] ** 2, axis=1))) * 1e6)
        v = np.gradient(tr.ink, 1.0 / fs, axis=0)
        out.update(tremor_peak(v, m, fs, tremor_hz=tremor_hz))
    else:
        out["tremor_note"] = "sample rate too low for 3-15 Hz tremor (need > 30 Hz)"
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    ext = [float(np.ptp(tr.ink[a:b, 1]) * 1e3) for a, b in zip(starts, ends) if b - a > 3]
    if len(ext) >= 8:
        q = max(2, len(ext) // 4)
        s0, s1 = float(np.median(ext[:q])), float(np.median(ext[-q:]))
        out["size"] = {"stroke_extent_first_quarter_mm": s0, "stroke_extent_last_quarter_mm": s1, "change": s1 / s0 - 1.0,
                       "progressive_micrographia_10pct": bool(s1 < 0.9 * s0), "n_strokes": len(ext)}
    gaps = [(a - b) / fs for a, b in zip(starts[1:], ends[:-1])]
    out["pauses"] = {"gaps_over_150ms": int(sum(g > 0.15 for g in gaps)), "median_gap_s": float(np.median(gaps)) if gaps else None}
    sm = min(20.0, 0.4 * fs)                                        # jerk needs the 20 Hz low-pass of metrics.fluency
    out["fluency"] = MT.fluency(tr, smooth_hz=sm)
    out["fluency_smooth_hz"] = sm
    if target is not None:
        from scipy.spatial import cKDTree
        dist, _ = cKDTree(target).query(tr.ink[m])
        out["target_rms_um"] = float(np.sqrt(np.mean(dist ** 2)) * 1e6)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace")
    ap.add_argument("--units", choices=("mm", "m"), default="mm")
    ap.add_argument("--rate", type=float, default=0.0, help="resampling rate (Hz); default: median input rate")
    ap.add_argument("--target", default=None, help="CSV with columns x, y (same units) of the target path")
    ap.add_argument("--tremor-hz", type=float, default=0.0, help="known tremor frequency (IMU posture test); default: search")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    tr = load(a.trace, a.units, a.rate)
    tgt = None
    if a.target:
        g = np.genfromtxt(a.target, delimiter=",", names=True)
        tgt = np.column_stack([g["x"], g["y"]]) * (1e-3 if a.units == "mm" else 1.0)
    res = score(tr, tgt, a.tremor_hz)
    txt = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(txt)
    else:
        sys.stdout.write(txt + "\n")


if __name__ == "__main__":
    main()
