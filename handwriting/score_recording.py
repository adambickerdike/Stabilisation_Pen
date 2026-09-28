#!/usr/bin/env python3
"""Score a recorded handwriting trace with the same definitions as the simulations (bridge to EXP-HW1..5).

Input: a CSV with columns t_s, x, y, pen_down (0/1) in mm (or --units m), from a digitising tablet, the pen's own
page sensor, or a motion-capture of the tip.  Output (JSON to stdout or --out):
  tremor     3-15 Hz RMS of the pen-down trace after removing its 0-3 Hz part (um), the dominant 3-15 Hz frequency
             of the pen velocity, and the share of velocity energy in 3-15 Hz
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


def score(tr: Trace, target: np.ndarray = None) -> dict:
    fs = 1.0 / float(tr.t[1] - tr.t[0])
    m = tr.contact > 0.5
    out = {"duration_s": float(tr.t[-1]), "sample_rate_hz": fs, "pen_down_share": float(m.mean())}
    if fs > 30.0:
        hp = tr.ink - sosfiltfilt(butter(4, 3.0, fs=fs, output="sos"), tr.ink, axis=0)
        band = sosfiltfilt(butter(4, [3.0, min(15.0, 0.45 * fs)], btype="band", fs=fs, output="sos"), tr.ink, axis=0)
        out["tremor_band_rms_um"] = float(np.sqrt(np.mean(np.sum(band[m] ** 2, axis=1))) * 1e6)
        out["above_3hz_rms_um"] = float(np.sqrt(np.mean(np.sum(hp[m] ** 2, axis=1))) * 1e6)
        v = np.gradient(tr.ink, 1.0 / fs, axis=0)
        f, p = welch(np.where(m[:, None], v, 0.0), fs=fs, nperseg=min(len(v), int(4 * fs)), axis=0)
        p = p.sum(axis=1)
        sel = (f >= 3.0) & (f <= 15.0)
        out["tremor_peak_hz"] = float(f[sel][np.argmax(p[sel])]) if sel.any() else None
        out["velocity_energy_3_15hz_share"] = float(p[sel].sum() / max(p.sum(), 1e-30))
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
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    tr = load(a.trace, a.units, a.rate)
    tgt = None
    if a.target:
        g = np.genfromtxt(a.target, delimiter=",", names=True)
        tgt = np.column_stack([g["x"], g["y"]]) * (1e-3 if a.units == "mm" else 1.0)
    res = score(tr, tgt)
    txt = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(txt)
    else:
        sys.stdout.write(txt + "\n")


if __name__ == "__main__":
    main()
