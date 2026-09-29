"""Validation of the writing inputs against the literature: real writing next to the old synthetic writers and sim2j's
refitted writers, all measured by ONE function (sim2j.writers.kinematics, itself sim2/validate.py's method: 1 kHz,
20 Hz zero-phase low-pass, mean pen-down speed, Welch velocity spectrum of the pen-down samples, stroke durations
between speed minima, power-law exponent from log angular speed against log curvature).  CALC on DATA and SIM.

Sets
  real_brush     BRUSH notes (all writers of both splits: a description of the inputs, not an evaluation), pen-down
                 timing real, pen-up moves added (writinglib); speed in mm/s depends on the DERIVED size, so it is also
                 given in letter heights per second (scale-free)
  real_unipen    UNIPEN text lines (category 8) from contributors with >= 100 samples/s and >= 10 points/mm, pen-down
                 strokes in physical units (documented per data set), joined like the BRUSH notes
  real_chartraj  UCI Character Trajectories letters (one writer), composed into the test sentence
  syn_v1         aiguide writers 0-5 (the writers of every earlier HW1 result)
  syn_v2         sim2j's refitted writers 0-5 (read-only; results/sim2j/writer_fit.json)
Literature (ledger ids): CON-20 phrase speed on paper 30.46 +- 7.90 mm/s; CON-24 strokes 90-150 ms, spectrum flat to
5 Hz; CON-25 cumulative velocity energy 3.1 / 4.9 / 5.9 / 9.3 Hz (50/90/95/99 %), 8-12 Hz share 1.3-1.7 %;
CON-27 exponent 2/3.
"""
from __future__ import annotations

import glob
import os
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths
from . import loaders as L
from . import writinglib as WL

ensure_paths()

LIT = {"speed_mm_s": {"value": 30.46, "sd_between": 7.90, "ledger": "CON-20", "what": "adults, phrase on paper"},
       "stroke_ms": {"lo": 90.0, "hi": 150.0, "ledger": "CON-24 (CON-25 median 135 ms)"},
       "cum_Hz": {"f50": 3.1, "f90": 4.9, "f95": 5.9, "f99": 9.3, "ledger": "CON-25"},
       "share_8_12": {"lo": 0.013, "hi": 0.017, "ledger": "CON-25"},
       "beta": {"value": 2.0 / 3.0, "ledger": "CON-27"}}
UNIPEN_MIN_PPS = 100.0
UNIPEN_MIN_RES = 10.0


def _kin(items):
    from sim2j import writers as SJ          # read-only: the one measurement function of the project
    return SJ.kinematics(items)


def _item(w):
    it = w.intended
    return (it.t, it.xy, it.pen_down)


def brush_items(max_writers: Optional[int] = None, dt: float = 1e-3) -> List:
    stats = WL.brush_writer_stats()
    ws = sorted([w for w, s in stats["writers"].items() if len(s["lowercase_recordings"]) >= 2], key=int)
    if max_writers:
        ws = ws[:max_writers]
    items, heights = [], []
    for w in ws:
        n = WL.brush_note(w, seed=0, n_words=10, dt=dt, stats=stats, with_reader=False)
        if n is None:
            continue
        items.append(_item(n))
        heights.append(n.real["letter_height_mm"])
    return items, heights


def unipen_items(max_lines: Optional[int] = None, dt: float = 1e-3) -> List:
    items, devices = [], {}
    n = 0
    for r in L.unipen_segments(("8",), level="TEXT", min_down_s=1.5):
        f = r.fs
        if not (UNIPEN_MIN_PPS <= f <= 250.0) or (r.meta.get("res_x_per_mm") or 0.0) < UNIPEN_MIN_RES:
            continue
        strokes = []
        for s in np.unique(r.stroke[r.stroke >= 0]):
            sel = np.flatnonzero(r.stroke == s)
            if len(sel) < 4:
                continue
            strokes.append(WL.Stroke(t=np.arange(len(sel)) / f, xy=r.xy[sel], char=-np.ones(len(sel), int)))
        if len(strokes) < 3:
            continue
        try:
            nt = WL.assemble(strokes, "x", dt=dt, height_m=5e-3, writer=r.writer, source="unipen")
        except Exception:
            continue
        items.append(_item(nt))
        devices[r.meta["contributor"]] = devices.get(r.meta["contributor"], 0) + 1
        n += 1
        if max_lines and n >= max_lines:
            break
    return items, devices


def synthetic_items(version: str, writers: Sequence[int] = (0, 1, 2, 3, 4, 5), dt: float = 1e-3) -> List:
    from handwriting import writers as HW
    out = []
    for w in writers:
        if version == "v1":
            wr = HW.writer(w).write(HW.ET_SENTENCE, dt=dt, seed=2000 + w)
        else:
            from sim2j import writers as SJ
            wr = SJ.writer(w, "v2").write(HW.ET_SENTENCE, dt=dt, seed=2000 + w)
        out.append(_item(wr))
    return out


def validate(quick: bool = False, log=print) -> Dict:
    out = {"literature": LIT, "sets": {}}
    items, heights = brush_items(max_writers=8 if quick else None)
    k = _kin(items)
    k["letter_height_mm_mean"] = float(np.mean(heights))
    k["speed_letter_heights_per_s"] = k["speed_mm_s"]["mean"] / float(np.mean(heights))
    k["label"] = "DATA brush (pen-down timing real; size DERIVED from LIT PDT-06; pen-up moves ASSUMPTION)"
    out["sets"]["real_brush"] = k
    log(f"[kin] brush: {len(items)} notes, speed {k['speed_mm_s']['mean']:.1f} mm/s")
    try:
        items_u, dev = unipen_items(max_lines=40 if quick else 400)
        if items_u:
            ku = _kin(items_u)
            ku["contributors"] = dev
            ku["label"] = "DATA unipen category 8 text lines (physical units as documented by each contributor)"
            out["sets"]["real_unipen"] = ku
            log(f"[kin] unipen: {len(items_u)} lines, speed {ku['speed_mm_s']['mean']:.1f} mm/s")
    except Exception as e:
        out["sets"]["real_unipen"] = {"error": repr(e)}
    ct = WL.ct_note(dt=1e-3, split="test")
    kc = _kin([_item(ct)])
    kc["label"] = "DATA chartraj (one writer; letters resized to 5.0 mm letter height, placement ASSUMPTION)"
    out["sets"]["real_chartraj"] = kc
    out["sets"]["syn_v1"] = dict(_kin(synthetic_items("v1")), label="SIM aiguide writers 0-5 (v1)")
    try:
        out["sets"]["syn_v2"] = dict(_kin(synthetic_items("v2")), label="SIM sim2j refitted writers 0-5 (v2, read-only)")
    except Exception as e:
        out["sets"]["syn_v2"] = {"error": repr(e)}
    return out


def table(val: Dict) -> List[Dict]:
    """Rows of the validation table (one per set)."""
    rows = []
    for key, k in val["sets"].items():
        if "error" in k:
            continue
        s = k["spectrum"]
        rows.append({"set": key, "speed_mm_s": k["speed_mm_s"]["mean"], "stroke_ms": k["stroke_ms"]["median"],
                     "f50": s["f50"], "f90": s["f90"], "f95": s["f95"], "f99": s["f99"], "share_8_12": s["share_8_12"],
                     "beta": k["beta"]["mean"], "n": k["n_paths"], "label": k.get("label", "")})
    return rows
