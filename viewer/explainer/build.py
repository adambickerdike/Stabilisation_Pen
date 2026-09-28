#!/usr/bin/env python3
"""Assemble the Rev H explainer page: viewer/explainer/index.html and viewer/explainer/data/*.json.

Every input has a final file and a provisional fallback.  The final file wins as soon as it exists:

  data/layout.json   <- results/revH/layout.json           else results/revH/layout_provisional.json
  data/board.json    <- results/board/layout.json          else PROVISIONAL_BOARD below (proposed design, assumed sizes)
  data/samples.json  <- results/handwriting/samples.json   else panels built from earlier simulations of the pencil
                                                             design (results/fusion/viz_fusion.json,
                                                             results/ai/viz_guided.json) plus an illustration of
                                                             shrinking letters (not a result)
  data/outcomes.json <- results/handwriting/outcomes.json (optional: averages per pen, fast and slow shakes)
  data/tip.json      <- results/revH/tip_params.json      else tip_params_provisional.json (optional: headline numbers
                                                             of the Rev H tip study; the page hides them when absent)
  data/manifest.json    which source each file came from (the page shows it)

The page itself is viewer/explainer/template.html; build.py fills its <!--BUILD:...--> placeholders (component table,
data status, provenance) so the tables read without any script.  The 3-D views and the handwriting panels load the
JSON files with fetch() at run time.

Handwriting samples are normalised to one schema (see README.md, "Data files").  A final file in another shape is
read through a list of accepted key names; if nothing usable is found, the provisional panels are used and the build
prints a warning.

Run:  python3 viewer/explainer/build.py
"""
from __future__ import annotations

import datetime as _dt
import html
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(HERE, "data")

LAYOUT_FINAL = "results/revH/layout.json"
LAYOUT_PROV = "results/revH/layout_provisional.json"
BOARD_FINAL = "results/board/layout.json"
SAMPLES_FINAL = "results/handwriting/samples.json"
FUSION = "results/fusion/viz_fusion.json"
GUIDED = "results/ai/viz_guided.json"
GUIDANCE = "results/ai/guidance.json"
TIP_FINAL = "results/revH/tip_params.json"
TIP_PROV = "results/revH/tip_params_provisional.json"
BOARD_PARAMS = ("results/board/board_params.json", "results/board/board_params_provisional.json")

PROVISIONAL_LABEL = "earlier pencil design (±0.3 mm), simulation; the new pen's results are being computed"

WARNINGS: list[str] = []


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print("WARNING:", msg, file=sys.stderr)


def rel(p: str) -> str:
    return os.path.join(ROOT, p)


def load(p: str):
    with open(rel(p), encoding="utf-8") as f:
        return json.load(f)


def exists(p: str) -> bool:
    return os.path.exists(rel(p))


def git_revision() -> str:
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                             timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True,
                               text=True, timeout=20).stdout.strip()
        return rev + ("-dirty" if dirty else "") if rev else "unknown"
    except Exception:  # noqa: BLE001  (git missing is not an error for the page)
        return "unknown"


def mtime_utc(p: str) -> str:
    return _dt.datetime.fromtimestamp(os.path.getmtime(rel(p)), _dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def r3(v: float) -> float:
    return float(f"{v:.3f}")


# ---------------------------------------------------------------------------------------------------------------- pen
REQUIRED_SHAPES = {"cylinder", "cone", "tube", "box"}


def check_layout(lay: dict) -> list[str]:
    """Problems that would stop the page drawing the pen (empty list = usable)."""
    probs = []
    comps = lay.get("components")
    if not isinstance(comps, list) or not comps:
        return ["no 'components' list"]
    for c in comps:
        if not isinstance(c, dict) or "z0" not in c or "z1" not in c:
            probs.append(f"component {c.get('id', '?') if isinstance(c, dict) else c!r} has no z0/z1")
        elif c.get("shape") not in REQUIRED_SHAPES:
            probs.append(f"component {c.get('id')} has unknown shape {c.get('shape')!r} (drawn as a cylinder)")
    return probs


def build_layout():
    src, status = (LAYOUT_FINAL, "final") if exists(LAYOUT_FINAL) else (LAYOUT_PROV, "provisional")
    lay = load(src)
    probs = check_layout(lay)
    fatal = [p for p in probs if "no 'components'" in p or "no z0/z1" in p]
    if fatal and src == LAYOUT_FINAL:
        warn(f"{LAYOUT_FINAL} is not usable ({'; '.join(fatal)}); using {LAYOUT_PROV}")
        src, status, lay = LAYOUT_PROV, "provisional", load(LAYOUT_PROV)
    for p in probs:
        if p not in fatal:
            warn(f"{src}: {p}")
    return lay, {"file": "layout.json", "source": src, "status": status, "modified": mtime_utc(src),
                 "evidence": (lay.get("meta") or {}).get("evidence_status", "")}


# -------------------------------------------------------------------------------------------------------------- board
def board_params():
    for p in BOARD_PARAMS:
        if exists(p):
            try:
                return load(p), p
            except (OSError, ValueError):
                pass
    return None, None


def provisional_board() -> dict:
    """A desk guidance board to draw until results/board/layout.json exists.  PROPOSED DESIGN, every size ASSUMED.

    Frame: desk, x to the right, y away from the writer, z up; z = 0 is the top of the paper; the centre of the
    writing area is at x = y = 0.  Parts listed under 'moves' follow the carriage: 'xy' the carriage itself,
    'y' the gantry bridge that carries it.  When the board study's parameter file exists (results/board/
    board_params*.json) its pull, pen-magnet and head-magnet values are used (CALCULATION / ASSUMPTION as labelled
    there); otherwise the pull is the published magnetic-stylus device (HAP-15), not a calculation for this board."""
    bp, bp_src = board_params()
    comps = [
        {"id": "base", "label": "Board case", "shape": "box", "center": [0, 0, -14.0], "size": [300, 220, 20],
         "moves": "none", "role": "case", "function": "A flat case that sits on the desk under the paper."},
        {"id": "top", "label": "Writing surface", "shape": "box", "center": [0, 0, -1.5], "size": [300, 220, 3],
         "moves": "none", "role": "surface",
         "function": "A thin non-magnetic plate: the paper lies on it and the magnet moves just under it."},
        {"id": "rail_left", "label": "Rail (y)", "shape": "cylinder", "axis": "y", "center": [-120, 0, -9.5], "d": 6,
         "length": 190, "moves": "none", "role": "mechanism", "function": "Guide rail for the gantry bridge."},
        {"id": "rail_right", "label": "Rail (y)", "shape": "cylinder", "axis": "y", "center": [120, 0, -9.5], "d": 6,
         "length": 190, "moves": "none", "role": "mechanism", "function": "Guide rail for the gantry bridge."},
        {"id": "gantry", "label": "Gantry bridge (x)", "shape": "box", "center": [0, 0, -9.0], "size": [250, 12, 6],
         "moves": "y", "role": "mechanism", "function": "Bridge that slides along the rails and carries the magnet carriage."},
        {"id": "carriage", "label": "Carriage", "shape": "box", "center": [0, 0, -8.0], "size": [30, 26, 5],
         "moves": "xy", "role": "mechanism", "function": "Runs along the bridge, so the magnet can reach any point under the page."},
        {"id": "magnet", "label": "Magnet head", "shape": "cylinder", "axis": "z", "center": [0, 0, -9.0], "d": 12,
         "length": 12, "moves": "xy", "role": "magnet",
         "function": "Pulls the magnet in the pen through the paper and the glass; a spring lift sets how hard it pulls."},
        {"id": "motor_x", "label": "Motor (x)", "shape": "box", "center": [110, 0, -9.0], "size": [20, 20, 12],
         "moves": "y", "role": "drive", "function": "Moves the carriage left and right."},
        {"id": "motor_y", "label": "Motor (y)", "shape": "box", "center": [-135, -95, -13.0], "size": [20, 20, 12],
         "moves": "none", "role": "drive", "function": "Moves the bridge toward and away from the writer."},
        {"id": "board_pcb", "label": "Board electronics", "shape": "box", "center": [100, -95, -17.0],
         "size": [60, 20, 3], "moves": "none", "role": "electronics",
         "function": "Motor drivers, magnet driver and Bluetooth link to the pen and the app."},
    ]
    numbers = [
        {"label": "Pull on the pen (published magnetic stylus, 3.5 mm from the magnet)", "value": 0.43, "unit": "N",
         "evidence": "LITERATURE HAP-15"},
        {"label": "Shape error when copying letters: lower with the magnetic pull than without", "value": None,
         "unit": "", "evidence": "LITERATURE HAP-15"},
    ]
    pen_magnet = {"z0": 5.0, "z1": 8.0, "d": 5.0, "d_in": 2.5, "moves_with": "nose", "label": "Magnet ring in the pen's nose",
                  "function": "A small magnet near the tip that the board's magnet pulls on."}
    if bp:
        lo = bp.get("leading_option", {})
        pm = lo.get("pen_magnet", {})
        zc = pm.get("centre_along_axis_from_ball_mm")
        if isinstance(zc, (int, float)):
            pen_magnet.update({"z0": zc - 1.5, "z1": zc + 1.5, "d": 5.0, "d_in": 2.5})
        mf = (bp.get("max_lateral_force_N") or {})
        cap = (bp.get("software_force_cap_N") or {})
        nums = []
        if isinstance(mf.get("A4_design_gap_2p7mm"), (int, float)):
            nums.append({"label": "Largest sideways pull on the pen (A4 board)", "value": mf["A4_design_gap_2p7mm"], "unit": "N",
                         "evidence": "CALCULATION"})
        if isinstance(cap.get("value"), (int, float)):
            nums.append({"label": "Software limit on the pull", "value": cap["value"], "unit": "N", "evidence": "ASSUMPTION"})
        nums.append({"label": "A published magnetic stylus: copying error lower with the pull", "value": None, "unit": "",
                     "evidence": "LITERATURE HAP-15"})
        numbers = nums
    return {
        "meta": {"evidence_status": "PROPOSED DESIGN (provisional board defined in viewer/explainer/build.py; every "
                                    "dimension is an ASSUMPTION until results/board/layout.json exists)"
                                    + (f"; pull and magnets from {bp_src}" if bp_src else ""),
                 "provisional": True},
        "units": "mm",
        "frame": "desk: x right, y away from the writer, z up; z = 0 is the paper surface; writing area centred at x = y = 0",
        "paper": {"size": [210, 148]},
        "work_area": [200, 140],
        "pen_magnet": pen_magnet,
        "components": comps,
        "numbers": numbers,
    }


def board_numbers(bp) -> list:
    """Plain-language headline numbers of the board study (results/board/board_params*.json), each with its label."""
    if not bp:
        return []
    out = []
    mf = bp.get("max_lateral_force_N") or {}
    iso = mf.get("at_design_gap_isotropic", mf.get("A4_design_gap_2p7mm"))
    if isinstance(iso, (int, float)):
        out.append({"label": "Largest pull on the pen, magnet fully raised", "value": round(iso, 2), "unit": "N",
                    "evidence": "CALCULATION"})
    cap = bp.get("software_force_cap_N")
    cap = cap.get("value") if isinstance(cap, dict) else cap
    if isinstance(cap, (int, float)):
        out.append({"label": "Pull limit chosen for safety", "value": cap, "unit": "N", "evidence": "ASSUMPTION"})
    bw = (bp.get("force_bandwidth_Hz") or {}).get("value")
    if isinstance(bw, (int, float)):
        out.append({"label": "How quickly the pull can change", "value": round(bw), "unit": "times a second",
                    "evidence": "CALCULATION"})
    sh = (bp.get("sim_headlines") or {}).get("tracing_full_vs_off_ink_rms_mm")
    if isinstance(sh, list) and len(sh) == 2 and all(isinstance(x, (int, float)) for x in sh):
        # board/run_study.py writes [board off, full guidance] (relaxed hand, nose locked)
        out.append({"label": "Tracing a letter, ink off the letter: board off, then full guidance", "value": None,
                    "text": f"{sh[0]:.2f} mm, then {sh[1]:.2f} mm", "unit": "", "evidence": "SIMULATION"})
    pm = bp.get("pen_magnet") or (bp.get("leading_option") or {}).get("pen_magnet") or {}
    if "sleeve" in str(pm.get("location", "")):
        out.append({"label": "The board pulls a small magnet under the fixed sleeve, so it steers the whole pen", "value": None,
                    "unit": "", "evidence": "PROPOSED DESIGN"})
    return out


def build_board():
    if exists(BOARD_FINAL):
        b = load(BOARD_FINAL)
        if isinstance(b, dict) and isinstance(b.get("components"), list) and b["components"]:
            b.setdefault("meta", {}).setdefault("provisional", False)
            bp, bp_src = board_params()
            nums = board_numbers(bp)
            if nums:
                b["explainer_numbers"] = nums          # added by the explainer build; the layout itself is unchanged
                b["explainer_numbers_source"] = bp_src
            return b, {"file": "board.json", "source": BOARD_FINAL + (f" (+ numbers from {bp_src})" if nums else ""),
                       "status": "final", "modified": mtime_utc(BOARD_FINAL), "evidence": b["meta"].get("evidence_status", "")}
        warn(f"{BOARD_FINAL} has no 'components' list the page can draw; using the provisional board")
    b = provisional_board()
    return b, {"file": "board.json", "source": "viewer/explainer/build.py (provisional board)", "status": "provisional",
               "modified": "", "evidence": b["meta"]["evidence_status"]}


# -------------------------------------------------------------------------------------------------- handwriting data
def runs(flags):
    out, s, n = [], 0, len(flags)
    while s < n:
        while s < n and not flags[s]:
            s += 1
        e = s
        while e < n and flags[e]:
            e += 1
        if e - s > 1:
            out.append((s, e))
        s = e
    return out


def strokes_from(points, flags, stride=1):
    """Pen-down runs of a point list -> list of strokes [[x, y], ...] in mm (3 decimals)."""
    out = []
    for s, e in runs(flags):
        idx = list(range(s, e, stride))
        if idx[-1] != e - 1:
            idx.append(e - 1)
        out.append([[r3(points[i][0]), r3(points[i][1])] for i in idx])
    return out


def metric(name, value, unit, evidence, nd=2, note=""):
    return {"name": name, "value": None if value is None else float(f"{value:.{nd}f}"), "unit": unit,
            "evidence": evidence, "note": note}


def panel_tremor_fusion():
    """Tremor group: results/fusion/viz_fusion.json (pencil model P1, 10 Hz, 0.3 mm)."""
    f = load(FUSION)
    by = {c["key"]: c for c in f["cases"]}
    if "neutral" not in by:
        return None
    base = by["neutral"]
    down = base["contact"]
    variants = []
    ref = base["metrics"]["ink_err_rms_um"]
    spec = [("neutral", "before", "Pen off (no correction)"),
            ("oracle", "after", "Correction with perfect knowledge of the shake (best possible)"),
            ("akf_personal", "after", "Correction by the motion-sensor tracker, tuned to this writer"),
            ("akf_robust", "after", "Correction by the motion-sensor tracker, untuned")]
    for key, role, label in spec:
        c = by.get(key)
        if not c:
            continue
        m = c["metrics"]
        mets = [metric("Average distance of the ink from the intended line", m["ink_err_rms_um"] / 1000, "mm",
                       "SIMULATION", 2)]
        if role == "after":
            mets.append(metric("Less wobble than pen off", 100 * (1 - m["ink_err_rms_um"] / ref), "%", "SIMULATION", 0))
        variants.append({"key": key, "role": role, "label": label,
                         "ink": strokes_from([p[:2] for p in c["nib"]], c["contact"]), "metrics": mets})
    return {
        "id": "tremor_fusion", "condition": "tremor", "evidence": "SIMULATION",
        "title": "Handwriting with a fast shake",
        "subtitle": "10 Hz shake of 0.3 mm, 5 s of simulated writing (earlier pencil design, ±0.3 mm nib stage)",
        "source": FUSION, "provisional": True, "ruling_mm": 8,
        "intended": strokes_from(base["intended"], down),
        "variants": variants,
        "note": "The best-possible line needs a perfect tracker. The realistic trackers are what the pen can do today in "
                "simulation: at 0.3 mm the pencil's small stage limits both.",
    }


def panel_guided():
    """Guided group: results/ai/viz_guided.json (sentence, pencil model P1, 6 Hz 0.3 mm)."""
    g = load(GUIDED)
    by = {c["key"]: c for c in g["cases"]}
    if "neutral" not in by:
        return None
    base = by["neutral"]
    down = [int(a and b) for a, b in zip(base["contact"], base.get("skid_contact", base["contact"]))]
    ref = base["metrics_writing_only"]["path_rms_um"]
    spec = [("neutral", "before", "No guidance"),
            ("oracle", "after", "Guided toward the true letter shapes (best case)"),
            ("ai_predicted", "after", "Guided toward the letters the AI predicts (realistic)")]
    variants = []
    for key, role, label in spec:
        c = by.get(key)
        if not c:
            continue
        m = c["metrics_writing_only"]
        flags = [int(a and b) for a, b in zip(c["contact"], c.get("skid_contact", c["contact"]))]
        mets = [metric("Average distance of the ink from the letter shapes", m["path_rms_um"] / 1000, "mm",
                       "SIMULATION", 2)]
        if role == "after":
            mets.append(metric("Closer to the letter shapes than without guidance", 100 * (1 - m["path_rms_um"] / ref),
                               "%", "SIMULATION", 0))
        mets.append(metric("Letters the app recognises", 100 * m["recognition_accuracy"], "%", "SIMULATION", 0))
        variants.append({"key": key, "role": role, "label": label, "ink": strokes_from(c["ink"], flags),
                         "metrics": mets})
    sentence = (g.get("meta") or {}).get("sentence", "")
    return {
        "id": "guided_sentence", "condition": "guided", "evidence": "SIMULATION",
        "title": f"Guidance toward the letter shapes: “{sentence}”" if sentence else "Guidance toward the letter shapes",
        "subtitle": "The nib is nudged toward a template of each letter while a 6 Hz, 0.3 mm shake is present "
                    "(earlier pencil design, ±0.3 mm nib stage)",
        "source": GUIDED, "provisional": True, "ruling_mm": 8,
        "intended": strokes_from(base["intended"], down),
        "variants": variants,
        "note": "With only ±0.3 mm to work with, guidance helps a little when the pen knows the letter, and not at all "
                "when it has to guess. The new pen moves ten times further.",
    }


def loops_line(n_loops: int, size_fn, u=4.0, slant=0.32, pitch=0.95, x0=0.0, samples=48):
    """Cursive 'lelele…' loops (tall l, short e) as one pen-down stroke; size_fn(i) scales loop i.
    Each loop: x = x0 + w*s - r*sin(2*pi*s), y = h*(1 - cos(2*pi*s))/2, s in [0, 1]; then slanted."""
    pts, x = [], x0
    for i in range(n_loops):
        k = size_fn(i)
        tall = i % 2 == 0
        h = (2.1 if tall else 1.0) * u * k
        w = pitch * u * k
        r = (0.30 if tall else 0.36) * u * k
        for j in range(samples + 1):
            if i and j == 0:
                continue
            s = j / samples
            px = x + w * s - r * math.sin(2 * math.pi * s)
            py = h * (1 - math.cos(2 * math.pi * s)) / 2
            pts.append([r3(px + slant * py), r3(py)])
        x += w
    return [pts]


def panel_micrographia_illustration():
    """Parkinson's group until the new pen's results exist: an ILLUSTRATION, not a simulation or measurement.
    Shrink along the line follows the size of effect reported in PDT-05 (stroke length about 23 % shorter at the end);
    the cue and the recovery are drawn to show the idea only."""
    n = 16

    def shrink(i):
        return 1.0 - 0.27 * i / (n - 1)

    def cued(i):
        # shrinks like the uncued line until the size drops below 85 %, then the buzz; recovers over two loops
        s = shrink(i)
        i_cue = next(k for k in range(n) if shrink(k) < 0.85)
        if i < i_cue:
            return s
        return min(1.0, 0.85 + 0.08 * (i - i_cue + 1)) * (1 - 0.03 * (i - i_cue) / n)

    i_cue = next(k for k in range(n) if shrink(k) < 0.85)
    before = loops_line(n, shrink)
    after = loops_line(n, cued)
    intended = loops_line(n, lambda i: 1.0)
    cue_x = after[0][i_cue * 48][0]
    return {
        "id": "micrographia_illustration", "condition": "parkinsons", "evidence": "ILLUSTRATION",
        "title": "Letters that shrink along the line",
        "subtitle": "Drawn to show the idea; not a simulation. The size loss follows published measurements; the "
                    "effect of this pen's buzz has not been tested.",
        "source": "viewer/explainer/build.py (illustration)", "provisional": True, "ruling_mm": 10,
        "intended": intended,
        "variants": [
            {"key": "no_cue", "role": "before", "label": "No cue: the letters get smaller",
             "ink": before,
             "metrics": [metric("Stroke length at the end of a writing task, people with shrinking writing", 14.61, "mm",
                                "LITERATURE PDT-05", 1, "down from 18.97 mm at the start, about 23 % smaller")]},
            {"key": "buzz_cue", "role": "after", "label": "With a buzz when the letters shrink",
             "ink": after, "cue_x": [r3(cue_x)],
             "metrics": [metric("Writing size with visual or spoken 'write big' cues", None, "", "LITERATURE PDT-19",
                                note="size moved back toward normal; the effect of a buzz from the pen is not known yet")]},
        ],
        "note": "Lines about 1 cm apart help; narrower lines made writing smaller (PDT-18).",
    }


def provisional_samples():
    panels = []
    for fn in (panel_tremor_fusion, panel_micrographia_illustration, panel_guided):
        try:
            p = fn()
        except (OSError, KeyError, ValueError, StopIteration) as ex:
            warn(f"provisional panel {fn.__name__} skipped: {ex}")
            p = None
        if p:
            panels.append(p)
    return {"meta": {"provisional": True, "label": PROVISIONAL_LABEL,
                     "evidence_status": "SIMULATION of the earlier pencil design (tremor, guidance) and an ILLUSTRATION "
                                        "(shrinking letters); nothing measured",
                     "sources": [FUSION, GUIDED]},
            "units": "mm", "panels": panels}


# ---- normalising a final samples file ------------------------------------------------------------------------------
PANEL_LIST_KEYS = ("panels", "samples", "cases", "items")
INTENDED_KEYS = ("intended", "target", "reference", "ref", "template", "intent")
INK_KEYS = ("ink", "nib", "path", "trace", "strokes", "points", "tip")
BEFORE_KEYS = ("before", "off", "baseline", "neutral", "uncorrected", "pen_off", "without")
AFTER_KEYS = ("after", "on", "corrected", "stabilised", "stabilized", "assisted", "pen_on", "with")
DOWN_KEYS = ("pen_down", "contact", "down")
TIME_KEYS = ("t", "time", "time_s")
HAND_KEYS = ("hand", "housing", "handle", "hand_path")
NOSE_KEYS = ("nose", "nose_offset", "tip_offset", "q")


def _first(d: dict, keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _is_pt(p):
    return isinstance(p, (list, tuple)) and len(p) >= 2 and all(isinstance(v, (int, float)) for v in p[:2])


def to_strokes(v, down=None):
    """Accept: list of strokes; flat point list (+ optional pen-down flags); points with None separators;
    {'x': [...], 'y': [...]} (optionally with pen_down); {'strokes': ...}.  Returns list of strokes or None."""
    if v is None:
        return None
    if isinstance(v, dict):
        if "x" in v and "y" in v:
            pts = [[a, b] if a is not None and b is not None else None for a, b in zip(v["x"], v["y"])]
            return to_strokes(pts, _first(v, DOWN_KEYS) or down)
        inner = _first(v, ("strokes",) + INK_KEYS)
        return to_strokes(inner, _first(v, DOWN_KEYS) or down) if inner is not None else None
    if not isinstance(v, list) or not v:
        return None
    if all(isinstance(s, list) and s and _is_pt(s[0]) for s in v if s is not None) and not _is_pt(v[0]):
        out = [[[r3(p[0]), r3(p[1])] for p in s if _is_pt(p)] for s in v if s]
        return [s for s in out if len(s) >= 2] or None
    if _is_pt(v[0]) or v[0] is None:
        if down is None and all(_is_pt(p) and len(p) >= 3 and p[2] in (0, 1, True, False) for p in v):
            down = [p[2] for p in v]                       # [[x, y, pen_down], ...]
        if down is not None and len(down) == len(v):
            pts = [p if _is_pt(p) else [math.nan, math.nan] for p in v]
            flags = [bool(d) and _is_pt(p) for d, p in zip(down, v)]
            return strokes_from(pts, flags) or None
        out, cur = [], []
        for p in v:
            if _is_pt(p) and not any(isinstance(q, float) and math.isnan(q) for q in p[:2]):
                cur.append([r3(p[0]), r3(p[1])])
            elif cur:
                out.append(cur)
                cur = []
        if cur:
            out.append(cur)
        return [s for s in out if len(s) >= 2] or None
    return None


def to_metrics(m, default_evidence):
    if m is None:
        return []
    out = []
    if isinstance(m, dict):
        m = [{"name": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in m.items()]
    if not isinstance(m, list):
        return []
    for x in m:
        if not isinstance(x, dict):
            continue
        name = x.get("name") or x.get("label") or x.get("metric")
        if not name:
            continue
        val = x.get("value")
        out.append({"name": str(name).replace("_", " "),
                    "value": val if isinstance(val, (int, float)) or val is None else None,
                    "text": val if isinstance(val, str) else None,
                    "unit": x.get("unit", ""), "evidence": x.get("evidence") or default_evidence,
                    "note": x.get("note", "")})
    return out


def _series(d):
    """Optional time series kept for the animated scenes: t, hand path, nose offset, pen-down flags."""
    out = {}
    for name, keys in (("t", TIME_KEYS), ("hand", HAND_KEYS), ("nose", NOSE_KEYS), ("pen_down", DOWN_KEYS)):
        v = _first(d, keys)
        if isinstance(v, list) and v:
            out[name] = v
    ink = _first(d, INK_KEYS)
    if isinstance(ink, list) and ink and _is_pt(ink[0]):
        out["ink_points"] = [[r3(p[0]), r3(p[1])] if _is_pt(p) else None for p in ink]
    return out


def normalise_variant(key, d, role, default_evidence):
    if isinstance(d, list):
        d = {"ink": d}
    if not isinstance(d, dict):
        return None
    down = _first(d, DOWN_KEYS)
    ink = to_strokes(_first(d, INK_KEYS), down)
    if not ink:
        return None
    v = {"key": str(d.get("key", key)), "role": d.get("role", role), "label": d.get("label") or d.get("name") or
         str(key).replace("_", " ").capitalize(), "ink": ink,
         "metrics": to_metrics(d.get("metrics"), d.get("evidence") or default_evidence)}
    ser = _series(d)
    if ser:
        v["series"] = ser
    for k in ("cue_x", "cue_t", "note"):
        if k in d:
            v[k] = d[k]
    return v


def normalise_panel(p, i):
    if not isinstance(p, dict):
        return None
    cond = p.get("condition") or p.get("group") or p.get("problem") or p.get("category") or "other"
    ev = p.get("evidence") or p.get("evidence_status") or "SIMULATION"
    variants = []
    if isinstance(p.get("variants"), list):
        for j, d in enumerate(p["variants"]):
            v = normalise_variant((d or {}).get("key", f"v{j}") if isinstance(d, dict) else f"v{j}", d,
                                  (d or {}).get("role", "after" if j else "before") if isinstance(d, dict) else "after", ev)
            if v:
                variants.append(v)
    elif isinstance(p.get("variants"), dict):
        for j, (k, d) in enumerate(p["variants"].items()):
            role = "before" if k in BEFORE_KEYS else "after"
            v = normalise_variant(k, d, role, ev)
            if v:
                variants.append(v)
    else:
        for keys, role in ((BEFORE_KEYS, "before"), (AFTER_KEYS, "after")):
            for k in keys:
                if k in p:
                    v = normalise_variant(k, p[k], role, ev)
                    if v:
                        variants.append(v)
    if not variants:
        return None
    intended = to_strokes(_first(p, INTENDED_KEYS), _first(p, DOWN_KEYS))
    out = {"id": str(p.get("id") or p.get("key") or f"panel{i}"), "condition": str(cond).lower(), "evidence": ev,
           "title": p.get("title") or p.get("label") or str(cond).replace("_", " ").capitalize(),
           "subtitle": p.get("subtitle") or p.get("description") or "", "source": p.get("source", SAMPLES_FINAL),
           "provisional": False, "ruling_mm": p.get("ruling_mm", 8), "intended": intended or [],
           "variants": variants, "note": p.get("note", "")}
    ser = _series(p)
    if ser:
        out["series"] = ser
    for k in ("units", "tremor", "scale_note", "metrics"):
        if k in p and k not in out:
            out[k] = p[k] if k != "metrics" else to_metrics(p[k], ev)
    return out


DEVICE_ORDER = ["none", "ordinary", "weighted", "pencil_off", "pencil_akf", "pencil_oracle", "revH_off", "revH_akf",
                "revH_akf_revh", "revH_board", "revH_oracle"]
DEVICE_LABEL = {"none": "Ordinary pen", "ordinary": "Ordinary pen", "weighted": "Weighted pen (60 g heavier)",
                "pencil_akf": "Earlier slim design (tip moves ±0.3 mm), with tracker",
                "pencil_oracle": "Earlier slim design, if it knew the shake exactly",
                "revH_off": "New pen, stabiliser switched off",
                "revH_akf": "New pen, tracker as first tuned (for the slim design)",
                "revH_akf_revh": "New pen, tracker tuned for it (today's best)",
                "revH_oracle": "New pen, if it knew the shake exactly (the limit)"}
KEY_DEVICES = {"none", "ordinary", "revH_akf_revh", "revH_oracle"}


def _device_role(dev: str) -> str:
    d = dev.lower()
    if d in ("none", "ordinary", "off", "baseline"):
        return "before"
    if d.startswith("revh") and not d.endswith("_off"):
        return "limit" if "oracle" in d else "after"
    return "other"


def _plain_scenario(title: str) -> str:
    t = title.split(" - ", 1)[1] if " - " in title else title
    m = re.search(r"tremor\s+([\d.]+)\s*mm\s+at\s+([\d.]+)\s*Hz", t, re.I)
    if m:
        return f"A shake of {m.group(1)} mm, {m.group(2)} times a second"
    return t[:1].upper() + t[1:]


def hw1_metrics(m: dict, ref: dict | None, ev: str) -> list:
    out = []
    if isinstance(m.get("ink_err_um"), (int, float)):
        out.append(metric("Ink off the letters, on average", m["ink_err_um"] / 1000, "mm", ev, 2))
        if ref and isinstance(ref.get("ink_err_um"), (int, float)) and ref is not m and ref["ink_err_um"] > 0:
            ch = 100 * (m["ink_err_um"] / ref["ink_err_um"] - 1)
            out.append({"name": "Compared with the ordinary pen", "value": None, "text": f"{abs(ch):.0f} % " + ("less" if ch < 0 else "more"),
                        "unit": "", "evidence": ev, "note": ""})
    if isinstance(m.get("word_acc_app"), (int, float)):
        out.append(metric("Words right after the app's spelling check", 100 * m["word_acc_app"], "%", ev, 0))
    if isinstance(m.get("at_travel_limit"), (int, float)) and m["at_travel_limit"] > 0.01:
        out.append(metric("Time with the tip at its limit", 100 * m["at_travel_limit"], "%", ev, 0))
    if m.get("app_words"):
        out.append({"name": "The app read", "value": None, "text": f"“{m['app_words']}”", "unit": "", "evidence": ev, "note": ""})
    return out


def normalise_hw1(raw: dict):
    """results/handwriting/samples.json of the handwriting study (schema 'panels[{id, title, condition, device,
    caption, evidence, intended [[x, y, pen_down]], ink [[...]], metrics}]'): one panel per device run.  Panels that
    share a condition and a scenario (the id without its device) become one panel with one variant per device."""
    meta = dict(raw.get("meta", {}))
    rate = 50.0
    mm = re.search(r"at\s+([\d.]+)\s*Hz", str(meta.get("schema", "")))
    if mm:
        rate = float(mm.group(1))
    groups: dict = {}
    for p in raw["panels"]:
        dev = str(p.get("device", "none"))
        pid = str(p.get("id", ""))
        scen = re.sub(r"_+", "_", pid.replace(dev, "")).strip("_") or pid
        groups.setdefault((str(p.get("condition", "other")), scen), []).append(p)
    panels = []
    for (cond, scen), ps in groups.items():
        ps.sort(key=lambda q: DEVICE_ORDER.index(q.get("device")) if q.get("device") in DEVICE_ORDER else 99)
        ref = next((q["metrics"] for q in ps if _device_role(str(q.get("device", ""))) == "before"), None)
        first = ps[0]
        ev_raw = str(first.get("evidence", "SIM"))
        ev = "SIMULATION" if ev_raw.upper().startswith("SIM") else ev_raw
        prate = rate * (30 / 50 if "pd" in cond.lower() and "PD 30" in str(meta.get("schema", "")) else 1)
        variants = []
        for q in ps:
            dev = str(q.get("device", "none"))
            ink = to_strokes(q.get("ink"))
            if not ink:
                continue
            label = DEVICE_LABEL.get(dev) or (q.get("title", dev).split(" - ")[0])
            variants.append({"key": dev, "role": _device_role(dev), "label": label, "key_device": dev in KEY_DEVICES,
                             "ink": ink, "points": [[r3(a[0]), r3(a[1]), int(a[2]) if len(a) > 2 else 1] for a in q["ink"] if _is_pt(a)],
                             "metrics": hw1_metrics(q.get("metrics") or {}, ref, ev)})
        if not variants:
            continue
        cap = re.sub(r"\s*\(seed \d+\)", "", str(first.get("caption", "")))
        panels.append({"id": f"{cond}_{scen}", "condition": cond, "evidence": ev, "title": _plain_scenario(str(first.get("title", scen))),
                       "subtitle": cap, "source": SAMPLES_FINAL, "provisional": False, "ruling_mm": 8, "rate_hz": prate,
                       "intended": to_strokes(first.get("intended")) or [],
                       "intended_points": [[r3(a[0]), r3(a[1]), int(a[2]) if len(a) > 2 else 1] for a in first.get("intended", []) if _is_pt(a)],
                       "variants": variants, "note": ""})
    if not panels:
        return None
    meta["provisional"] = False
    meta["label"] = "simulation of the new pen and of other pens on the same simulated hand and tremor (model HW1); nothing measured"
    return {"meta": meta, "units": "mm", "panels": panels}


def normalise_samples(raw):
    if isinstance(raw, dict) and isinstance(raw.get("panels"), list) and raw["panels"] and all(
            isinstance(p, dict) and "device" in p and "ink" in p and "variants" not in p for p in raw["panels"]):
        return normalise_hw1(raw)
    panels_raw = None
    if isinstance(raw, list):
        panels_raw = raw
    elif isinstance(raw, dict):
        panels_raw = _first(raw, PANEL_LIST_KEYS)
        if isinstance(panels_raw, dict):
            panels_raw = [dict(v, condition=v.get("condition", k)) if isinstance(v, dict) else v
                          for k, v in panels_raw.items()]
    if not isinstance(panels_raw, list):
        return None
    panels = [q for q in (normalise_panel(p, i) for i, p in enumerate(panels_raw)) if q]
    if not panels:
        return None
    meta = dict(raw.get("meta", {})) if isinstance(raw, dict) else {}
    meta["provisional"] = False
    meta.setdefault("label", meta.get("evidence_status", "simulation of the new pen (Rev H)"))
    return {"meta": meta, "units": "mm", "panels": panels}


def cond_key(c) -> str:
    """Condition name -> page group (tremor, parkinsons, guided, board, spelling), by its words."""
    toks = set(re.split(r"[^a-z]+", str(c).lower()))
    for key, words in (("tremor", {"tremor", "et", "shake", "shaky", "essential"}),
                       ("parkinsons", {"pd", "parkinson", "parkinsons", "micrographia"}),
                       ("board", {"board"}),
                       ("guided", {"guided", "practice", "dysgraphia", "guidance"}),
                       ("spelling", {"spelling", "dyslexia"})):
        if toks & words:
            return key
    return str(c).lower()


def build_samples():
    if exists(SAMPLES_FINAL):
        try:
            s = normalise_samples(load(SAMPLES_FINAL))
        except (OSError, ValueError, KeyError, TypeError) as ex:
            s = None
            warn(f"{SAMPLES_FINAL} could not be read ({ex})")
        if s:
            covered = {cond_key(p["condition"]) for p in s["panels"]}
            kept = []
            for p in provisional_samples()["panels"]:      # conditions the study has not covered yet stay visible
                if cond_key(p["condition"]) not in covered:
                    s["panels"].append(p)
                    kept.append(p["id"])
            s["meta"]["provisional_panels"] = kept
            return s, {"file": "samples.json", "source": SAMPLES_FINAL + (f" + provisional panels for the conditions not yet in it ({', '.join(kept)})" if kept else ""),
                       "status": "final", "modified": mtime_utc(SAMPLES_FINAL), "evidence": s["meta"].get("evidence_status", ""),
                       "panels": len(s["panels"])}
        warn(f"{SAMPLES_FINAL} exists but no panel could be read from it; using the provisional panels")
    s = provisional_samples()
    return s, {"file": "samples.json", "source": " + ".join(p for p in (FUSION, GUIDED) if exists(p)) +
               " + illustration (build.py)", "status": "provisional", "modified": "",
               "evidence": s["meta"]["evidence_status"], "panels": len(s["panels"])}


# ------------------------------------------------------------------------------------------------------------ tables
GROUP_NAMES = {"moving_nose": "Moving nose", "refill": "Ink refill", "grip": "Finger sleeve", "structure": "Handle shell",
               "skid": "Skid ring",
               "mechanism": "Pivot", "actuator": "Coils and magnets", "sensor": "Sensors", "electronics": "Electronics",
               "power": "Battery", "haptic": "Vibration motor", "inertial": "Inertial module"}


def e(x) -> str:
    return html.escape(str(x), quote=True)


def dims(c: dict) -> str:
    if c.get("shape") == "box" and c.get("size"):
        s = c["size"]
        return f"{s[0]:g} × {s[1]:g} × {s[2]:g} mm"
    d0, d1 = c.get("d0"), c.get("d1")
    length = c["z1"] - c["z0"]
    if d0 is None:
        return f"{length:g} mm long"
    d = f"Ø{d0:g}" if d1 in (None, d0) else f"Ø{d0:g}–{d1:g}"
    return f"{d} × {length:g} mm"


def component_rows(lay: dict) -> str:
    rows = []
    comps = sorted(lay.get("components", []), key=lambda c: (c.get("z0", 0), c.get("z1", 0)))
    for c in comps:
        g = "skid" if "skid" in str(c.get("id", "")).lower() else c.get("group", "other")
        pills = []
        if c.get("moves_with") == "nose":
            pills.append('<span class="pill move">moves with the nose</span>')
        if c.get("optional"):
            pills.append('<span class="pill opt">optional</span>')
        ledger = e(c["ledger"]) if c.get("ledger") else '<span class="muted">—</span>'
        rows.append(
            f'<tr data-part="{e(c.get("id", ""))}"><td><span class="sw g-{e(g)}" aria-hidden="true"></span>'
            f'<b>{e(c.get("label", c.get("id", "")))}</b><span class="where">{e(GROUP_NAMES.get(g, g))} · '
            f'z {c["z0"]:g}–{c["z1"]:g} mm · {e(dims(c))}</span>{"".join(pills)}</td>'
            f'<td>{e(c.get("function", ""))}</td><td>{e(c.get("part", ""))}</td><td class="mono">{ledger}</td></tr>')
    return "\n".join(rows)


def status_html(manifest: dict) -> str:
    names = {"layout.json": "Pen layout", "board.json": "Guidance board", "samples.json": "Handwriting results",
             "tip.json": "Tip study headline numbers", "outcomes.json": "Handwriting study averages"}
    items = []
    for m in manifest["files"]:
        st = m["status"]
        cls = "final" if st == "final" else "prov"
        word = "final" if st == "final" else "provisional"
        items.append(f'<li><span class="st {cls}">{word}</span> {e(names.get(m["file"], m["file"]))}: '
                     f'<code>{e(m["source"])}</code></li>')
    return "<ul class=\"status\">" + "".join(items) + "</ul>"


def provenance_html(manifest: dict, lay: dict) -> str:
    meta = lay.get("meta") or {}
    bits = [f"Built {e(manifest['built_utc'])} from git {e(manifest['git_revision'])}"]
    if meta.get("parameters_version"):
        bits.append(f"parameters v{e(meta['parameters_version'])}")
    if meta.get("generated_utc"):
        bits.append(f"layout generated {e(meta['generated_utc'])}")
    return " · ".join(bits)


# ------------------------------------------------------------------------------------------- handwriting outcomes
OUTCOMES = "results/handwriting/outcomes.json"


def build_outcomes():
    """Headline averages of the handwriting study (results/handwriting/outcomes.json), slimmed for the page:
    ink error and words read by the app for each pen, for fast (8-10 Hz) and slow (4-6 Hz) shakes of 1-2 mm."""
    if not exists(OUTCOMES):
        return None, None
    try:
        o = load(OUTCOMES)
        et = o.get("et") or {}
        h = et.get("headlines") or {}
        bands = {}
        for key, title in (("high_f_1_2mm", "Fast shake: 8 to 10 times a second, 1 to 2 mm"),
                           ("low_f_1_2mm", "Slow shake: 4 to 6 times a second, 1 to 2 mm")):
            if isinstance(h.get(key), dict):
                bands[key] = {"title": title, "devices": {d: {"ink_mm": r3(v.get("ink", float("nan")) / 1000),
                                                               "words": v.get("words"), "letters": v.get("letters")}
                                                          for d, v in h[key].items() if isinstance(v, dict)}}
        if not bands:
            return None, None
        meta = dict(o.get("meta", {}))
        agg = et.get("aggregate") or {}
        out = {"meta": {k: meta.get(k) for k in ("evidence_status", "generated_utc", "git_revision", "script", "quick")},
               "writers": agg.get("writers"), "n_scenarios": agg.get("n_scenarios"), "bands": bands,
               "device_labels": DEVICE_LABEL, "text": (o.get("text") or {}).get("et", {}),
               "by_frequency_text": h.get("by_frequency_text", [])}
        return out, {"file": "outcomes.json", "source": OUTCOMES, "status": "final", "modified": mtime_utc(OUTCOMES),
                     "evidence": meta.get("evidence_status", "")}
    except (OSError, ValueError, TypeError, AttributeError) as ex:
        warn(f"{OUTCOMES} could not be summarised ({ex})")
        return None, None


# ---------------------------------------------------------------------------------------------------- tip study file
def build_tip():
    """Optional headline numbers of the Rev H tip study (results/revH/tip_params*.json), copied as they are."""
    for src, status in ((TIP_FINAL, "final"), (TIP_PROV, "provisional")):
        if exists(src):
            try:
                t = load(src)
            except (OSError, ValueError) as ex:
                warn(f"{src} could not be read ({ex})")
                continue
            return t, {"file": "tip.json", "source": src, "status": status, "modified": mtime_utc(src),
                       "evidence": (t.get("meta") or {}).get("evidence_status", "")}
    return None, None


# -------------------------------------------------------------------------------------------------------------- main
def dump(obj, name):
    p = os.path.join(DATA, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
    return os.path.getsize(p)


def main():
    os.makedirs(DATA, exist_ok=True)
    lay, m_lay = build_layout()
    board, m_board = build_board()
    samples, m_samp = build_samples()
    tip, m_tip = build_tip()
    outc, m_out = build_outcomes()
    files = [m_lay, m_board, m_samp] + ([m_out] if m_out else []) + ([m_tip] if m_tip else [])
    manifest = {"built_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "git_revision": git_revision(), "files": files, "warnings": WARNINGS,
                "provisional_label": PROVISIONAL_LABEL}
    sizes = {"layout.json": dump(lay, "layout.json"), "board.json": dump(board, "board.json"),
             "samples.json": dump(samples, "samples.json")}
    for obj, name in ((tip, "tip.json"), (outc, "outcomes.json")):
        path = os.path.join(DATA, name)
        if obj is not None:
            sizes[name] = dump(obj, name)
        elif os.path.exists(path):
            os.remove(path)
    sizes["manifest.json"] = dump(manifest, "manifest.json")
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        page = f.read()
    fills = {"<!--BUILD:COMPONENT_ROWS-->": component_rows(lay), "<!--BUILD:DATA_STATUS-->": status_html(manifest),
             "<!--BUILD:PROVENANCE-->": provenance_html(manifest, lay)}
    for k, v in fills.items():
        if k not in page:
            warn(f"template.html has no {k} placeholder")
        page = page.replace(k, v)
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(out, ROOT)} ({len(page.encode('utf-8'))} bytes)")
    for m in manifest["files"]:
        print(f"  {m['file']:<13} {m['status']:<11} <- {m['source']}")
    print("  data sizes:", ", ".join(f"{k} {v / 1024:.0f} kB" for k, v in sizes.items()))
    if WARNINGS:
        print(f"  {len(WARNINGS)} warning(s); see above")


if __name__ == "__main__":
    main()
