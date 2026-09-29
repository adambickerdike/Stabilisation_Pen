"""Validation of the writing inputs against the literature: real writing next to the old synthetic writers and sim2j's
refitted writers, all measured by ONE function (sim2j.writers.kinematics, itself sim2/validate.py's method: 1 kHz,
20 Hz zero-phase low-pass, mean pen-down speed, Welch velocity spectrum of the pen-down samples, stroke durations
between speed minima, power-law exponent from log angular speed against log curvature).  CALC on DATA and SIM.

Sets
  real_brush     BRUSH notes (all writers of both splits: a description of the inputs, not an evaluation), pen-down
                 timing as released, pen-up moves added (writinglib); speed in mm/s depends on the DERIVED size; its
                 8-12 Hz share (a timing artefact) is why it is not a tracker input
  real_unipen    UNIPEN hpb2 notes (the HW1 writing input): ballpoint on paper, 14 writers, documented physical units,
                 recorded hover paths between strokes; unipen_survey measures every category-8 setup for the rule
  real_chartraj  UCI Character Trajectories letters (one writer), composed into the test sentence
  syn_v1         aiguide writers 0-5 (the writers of every earlier HW1 result)
  syn_v2         sim2j's refitted writers 0-5 (read-only; results/sim2j/writer_fit.json)
Literature (ledger ids): CON-20 phrase speed on paper 30.46 +- 7.90 mm/s; CON-24 strokes 90-150 ms, spectrum flat to
5 Hz; CON-25 cumulative velocity energy 3.1 / 4.9 / 5.9 / 9.3 Hz (50/90/95/99 %), 8-12 Hz share 1.3-1.7 %;
CON-27 exponent 2/3.
"""
from __future__ import annotations

import glob
import json
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


SURVEY_JSON = None      # set below (CACHE_DIR / unipen_survey.json)
SURVEY_RULE = {"share_8_12_max": 0.025, "share_above_12_max": 0.03, "speed_mm_s": (15.0, 60.0), "pps_min": 100.0,
               "res_min_per_mm": 15.0, "writers_min": 10, "surface": "paper"}


def _survey_path():
    from . import CACHE_DIR
    return CACHE_DIR / "unipen_survey.json"


def unipen_survey(max_per_setup: int = 40, log=print, refresh: bool = False, words_only: bool = True) -> Dict:
    """Every UNIPEN category-8 recording setup (contributor + its documentation file: one device, surface, rate and
    resolution) measured with the one kinematics function, and the selection rule applied to it.  The rule is about
    the recordings only (clean digitiser, adult speed, rate, resolution, number of writers, writing on paper); it was
    fixed before any HW1 run on UNIPEN notes.  Up to max_per_setup text lines per setup, reservoir-sampled with a
    fixed seed across all of its files.  words_only: only lines of lower-case words (the material the notes use;
    digits, symbols and names have shorter strokes and more high-frequency content)."""
    path = _survey_path()
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    rng = np.random.default_rng(20260929)
    res_by, seen, writers, meta = {}, {}, {}, {}
    for r in L.unipen_segments(("8",), level="TEXT", min_down_s=1.0):
        if words_only and not WL._is_words(r.text.strip()):
            continue
        key = r.meta["setup"]
        seen[key] = seen.get(key, 0) + 1
        writers.setdefault(key, set()).add(r.writer)
        meta[key] = {"pps": r.fs, "res_x_per_mm": r.meta.get("res_x_per_mm"), "device": r.meta.get("device", ""),
                     "pen": r.meta.get("pen", ""), "surface": r.meta.get("surface", "")}
        lst = res_by.setdefault(key, [])
        if len(lst) < max_per_setup:
            lst.append(r)
        else:
            j = int(rng.integers(0, seen[key]))
            if j < max_per_setup:
                lst[j] = r
    rows = []
    for key in sorted(res_by):
        items = []
        for r in res_by[key]:
            strokes = []
            for sidx in np.unique(r.stroke[r.stroke >= 0]):
                sel = np.flatnonzero(r.stroke == sidx)
                if len(sel) >= 4:
                    strokes.append(WL.Stroke(t=np.arange(len(sel)) / r.fs, xy=r.xy[sel], char=-np.ones(len(sel), int)))
            if len(strokes) < 3:
                continue
            try:
                nt = WL.assemble(strokes, "x", dt=1e-3, height_m=5e-3, writer=r.writer, source="unipen")
            except Exception:
                continue
            items.append(_item(nt))
        m = meta[key]
        row = {"setup": key, "segments": seen[key], "writers": len(writers[key]), "measured_lines": len(items), **m}
        if items:
            try:
                k = _kin(items)
                sp = k["spectrum"]
                row.update({"speed_mm_s": k["speed_mm_s"]["mean"], "stroke_ms": k["stroke_ms"]["median"],
                            "f50": sp["f50"], "f90": sp["f90"], "share_8_12": sp["share_8_12"],
                            "share_above_12": sp["share_above_12"], "beta": k["beta"]["mean"]})
            except Exception as e:
                row["error"] = repr(e)
        R = SURVEY_RULE
        checks = {
            "clean_8_12": row.get("share_8_12", 1.0) <= R["share_8_12_max"],
            "clean_above_12": row.get("share_above_12", 1.0) <= R["share_above_12_max"],
            "adult_speed": R["speed_mm_s"][0] <= row.get("speed_mm_s", 0.0) <= R["speed_mm_s"][1],
            "rate": (m["pps"] or 0) >= R["pps_min"] and (m["pps"] or 0) <= 250.0,
            "resolution": (m["res_x_per_mm"] or 0) >= R["res_min_per_mm"],
            "writers": len(writers[key]) >= R["writers_min"],
            "paper": R["surface"] in (m["surface"] or "").lower()}
        row["checks"] = checks
        row["selected"] = all(checks.values())
        rows.append(row)
        log(f"[survey] {key:12s} lines {seen[key]:5d} writers {len(writers[key]):4d} "
            f"speed {row.get('speed_mm_s', float('nan')):6.1f} 8-12 {100 * row.get('share_8_12', float('nan')):5.1f}% "
            f">12 {100 * row.get('share_above_12', float('nan')):5.1f}% {'SELECTED' if row['selected'] else ''} | "
            f"{m['device'][:28]} | {m['surface'][:40]}")
    out = {"rule": SURVEY_RULE, "rows": rows, "selected": [r["setup"] for r in rows if r["selected"]],
           "words_only": words_only,
           "method": "sim2j.writers.kinematics on up to %d %s per setup (reservoir sample, seed 20260929)"
                     % (max_per_setup, "lines of lower-case words" if words_only else "text lines")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, default=float))
    return out


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
    k["label"] = ("DATA brush (pen-down timing as released; size DERIVED from LIT PDT-06; pen-up moves ASSUMPTION): "
                  "REJECTED as tracker input for its 8-12 Hz content (a timing artefact)")
    out["sets"]["real_brush"] = k
    log(f"[kin] brush: {len(items)} notes, speed {k['speed_mm_s']['mean']:.1f} mm/s")
    try:
        idx = WL.unipen_index()
        ws = sorted(idx["writers"])
        items_u = []
        for w in ws[: (4 if quick else len(ws))]:
            n = WL.unipen_note(w, seed=0, n_words=10, dt=1e-3, index=idx)
            if n is not None:
                items_u.append(_item(n))
        if items_u:
            ku = _kin(items_u)
            ku["label"] = ("DATA UNIPEN hpb2 notes (the HW1 writing input: ballpoint on paper, 14 writers of both splits, "
                           "documented physical units; line changes added)")
            out["sets"]["real_unipen"] = ku
            log(f"[kin] unipen hpb2: {len(items_u)} notes, speed {ku['speed_mm_s']['mean']:.1f} mm/s")
    except Exception as e:
        out["sets"]["real_unipen"] = {"error": repr(e)}
    try:
        out["unipen_survey"] = unipen_survey(log=log)
    except Exception as e:
        out["unipen_survey"] = {"error": repr(e)}
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
