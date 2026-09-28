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
  data/replay.json   <- results/opt/viz_inertial_opt_1mm.json + viz_inertial_opt.json (optional: the mechanism study's
                                                             replay that drives scenes a and b; + band averages from
                                                             results/opt/inertial_opt.json).  Without it, scenes a and b
                                                             use the handwriting panels, else an illustration
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
BOARD_STUDY = "results/board/board.json"      # the full board study (tracing simulation, hand model); optional

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
    # the board study placed the pen's magnet in a keel under the FIXED front sleeve (it moves with the handle, not
    # the nose); the same place is assumed here until the study's files exist
    pen_magnet = {"d": 6.35, "h": 3.17, "moves_with": "handle", "label": "Magnet in a keel under the fixed sleeve",
                  "pen_frame_mm": {"along_axis_from_ball": 13.5, "off_axis_toward_paper": 10.2},
                  "function": "A small magnet under the sleeve that the board's magnet pulls on, so the board moves the whole pen."}
    if bp:
        pm = bp.get("pen_magnet") or {}
        if isinstance(pm.get("pen_frame_mm"), dict):
            pen_magnet.update({k: pm[k] for k in ("d", "h", "pen_frame_mm", "location") if k in pm})
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


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _study_tracing(study, mode, nose="locked", hand="relaxed"):
    """Ink error (RMS, mm) of one tracing run of the board study (results/board/board.json simulation.tracing)."""
    for r in ((study or {}).get("simulation") or {}).get("tracing") or []:
        if r.get("mode") == mode and r.get("nose") == nose and r.get("hand") == hand:
            return _num(r.get("ink_rms_mm"))
    return None


def _study_deflection(study, case):
    """Hand movement (mm) under a steady 0.1 N pull (results/board/board.json hand.deflection_per_0p1N)."""
    for r in ((study or {}).get("hand") or {}).get("deflection_per_0p1N") or []:
        if r.get("case") == case:
            return _num(r.get("deflection_mm_at_0Hz"))
    return None


def _param(study, group, key):
    v = (((study or {}).get("params") or {}).get(group) or {}).get(key)
    return _num(v.get("value")) if isinstance(v, dict) else _num(v)


def board_numbers(bp, study=None) -> list:
    """Plain-language numbers of the board study for scene (e), each with its evidence label.

    bp    = results/board/board_params.json (headline parameters)
    study = results/board/board.json (the full study: tracing simulation, hand model, control settings); optional.
    Labels follow the study: the 0.4 N cap and the give-way rule are settings (ASSUMPTION / PROPOSED DESIGN), the
    hand movement per 0.1 N is CALCULATION (HAP-26 hand model), the tracing errors are SIMULATION."""
    if not bp and not study:
        return []
    bp = bp or {}
    out = []

    def add(label, text, evidence):
        out.append({"label": label, "value": None, "unit": "", "text": text, "evidence": evidence})

    pm = bp.get("pen_magnet") or {}
    at = pm.get("board_frame_at_50deg_mm") or {}
    d, behind, high = _num(pm.get("d")), _num(at.get("behind_ball_along_azimuth")), _num(at.get("height_above_paper"))
    if "sleeve" in str(pm.get("location", "")) and d and behind and high:
        add("What the board pulls", f"a {d:g} mm magnet in a small keel under the fixed sleeve, about {behind:g} mm "
            f"behind the ball and {high:g} mm above the paper, so it moves the whole pen, not the nose", "PROPOSED DESIGN")
    cap = bp.get("software_force_cap_N")
    cap = _num(cap.get("value")) if isinstance(cap, dict) else _num(cap)
    if cap is None:
        cap = _param(study, "control", "force_cap_N")
    if cap:
        add("Pull limit", f"{cap:g} N, about the weight of {10 * round(cap / 9.81 * 100):g} g (a safety setting)",
            "ASSUMPTION")
    mf = bp.get("max_lateral_force_N") or {}
    iso = _num(mf.get("at_design_gap_isotropic", mf.get("A4_design_gap_2p7mm")))
    if iso:
        add("Strongest pull the magnets could give", f"{iso:.1f} N; the limit keeps it gentle", "CALCULATION")
    rel, res = _study_deflection(study, "relaxed"), _study_deflection(study, "lightly_resisting")
    if rel:
        t = f"about {rel:.2f} mm for every 0.1 N of steady pull"
        if cap:
            t += f", so about {rel * cap / 0.1:.0f} mm at the limit"
        if res:
            t += f"; {res:.2f} mm per 0.1 N if you resist a little"
        add("How far a relaxed hand moves", t, "CALCULATION")
    off, full = _study_tracing(study, "off"), _study_tracing(study, "full")
    if off is None or full is None:
        sh = (bp.get("sim_headlines") or {}).get("tracing_full_vs_off_ink_rms_mm")
        # board/run_study.py writes [board off, full guidance] (relaxed hand, nose locked)
        if isinstance(sh, list) and len(sh) == 2 and all(_num(x) is not None for x in sh):
            off, full = sh
    if off is not None and full is not None:
        add("Tracing a letter, ink off the letter (relaxed writer)", f"board off {off:.2f} mm, full guidance {full:.2f} mm",
            "SIMULATION")
    both, nose_only = _study_tracing(study, "full", "assist"), _study_tracing(study, "off", "assist")
    if both is not None:
        add("With the nose also correcting the ink", f"{both:.3f} mm" + (f" (the nose alone: {nose_only:.2f} mm)"
                                                                        if nose_only is not None else ""), "SIMULATION")
    oe, ot = _param(study, "control", "override_error_mm"), _param(study, "control", "override_time_s")
    if oe and ot:
        add("If you push against it", f"the pull fades away when the pen stays more than {oe:g} mm off the letter "
            f"for {ot:g} s, and comes back slowly", "ASSUMPTION")
    return out


def board_physics(bp, study) -> dict:
    """The few numbers scene (e) needs to draw the pull (the page falls back to the study's published values):
    cap     pull limit, N (software cap, ASSUMPTION)
    mmPerN  how far a relaxed hand moves per newton of steady pull (HAP-26 hand model, CALCULATION)
    lead    small pull along the letter in full guidance, N (ASSUMPTION)
    slope   pull per mm of head offset at the 0.4 N setting, N/mm (CALCULATION)
    keep    share of the hand's drift left with full guidance (SIMULATION: full / off, nose held still)
    fix     share of the remaining error the nose removes (SIMULATION: 1 - (full, nose assisting) / (full, nose still))"""
    bp = bp or {}
    out = {}
    cap = bp.get("software_force_cap_N")
    cap = _num(cap.get("value")) if isinstance(cap, dict) else _num(cap)
    cap = cap or _param(study, "control", "force_cap_N")
    if cap:
        out["cap"] = cap
    rel = _study_deflection(study, "relaxed")
    if rel:
        out["mmPerN"] = round(rel / 0.1, 3)
    lead = _param(study, "control", "lead_force_N")
    if lead:
        out["lead"] = lead
    slope = _num((bp.get("offset_to_force_slope_N_per_mm") or {}).get("at_0.4N_capability"))
    if slope:
        out["slope"] = round(slope, 4)
    off, full, both = _study_tracing(study, "off"), _study_tracing(study, "full"), _study_tracing(study, "full", "assist")
    if off and full:
        out["keep"] = round(full / off, 3)
    if full and both is not None:
        out["fix"] = round(1 - both / full, 3)
    return out


def build_board():
    if exists(BOARD_FINAL):
        b = load(BOARD_FINAL)
        if isinstance(b, dict) and isinstance(b.get("components"), list) and b["components"]:
            b.setdefault("meta", {}).setdefault("provisional", False)
            bp, bp_src = board_params()
            study = None
            if exists(BOARD_STUDY):
                try:
                    study = load(BOARD_STUDY)
                except (OSError, ValueError) as e:
                    warn(f"{BOARD_STUDY} could not be read ({e}); scene (e) shows the headline numbers only")
            nums = board_numbers(bp, study)
            srcs = ", ".join(s for s in (bp_src, BOARD_STUDY if study else None) if s)
            if nums:
                b["explainer_numbers"] = nums          # added by the explainer build; the layout itself is unchanged
                b["explainer_numbers_source"] = srcs
            phys = board_physics(bp, study)
            if phys:
                b["explainer_physics"] = phys          # sizes scene (e)'s illustration like the study's tracing run
            return b, {"file": "board.json", "source": BOARD_FINAL + (f" (+ numbers from {srcs})" if nums else ""),
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
            ch = 100 * (m["ink_err_rms_um"] / ref - 1)
            mets.append({"name": "Compared with pen off", "value": None, "text": f"{abs(ch):.0f} % " + ("less wobble" if ch < 0 else "more wobble"),
                         "unit": "", "evidence": "SIMULATION", "note": ""})
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
            ch = 100 * (m["path_rms_um"] / ref - 1)
            mets.append({"name": "Compared with no guidance", "value": None, "text": f"{abs(ch):.0f} % " + ("closer" if ch < 0 else "farther"),
                         "unit": "", "evidence": "SIMULATION", "note": ""})
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


def _txt(name, text, ev, note=""):
    return {"name": name, "value": None, "text": text, "unit": "", "evidence": ev, "note": note}


def _change(v, ref, closer=False):
    """'x % less' / 'x % more' (or 'closer' / 'farther') of v against ref."""
    ch = 100 * (v / ref - 1)
    if abs(ch) < 0.5:
        return "about the same"
    return f"{abs(ch):.0f} % " + (("closer" if ch < 0 else "farther") if closer else ("less" if ch < 0 else "more"))


def hw1_metrics(m: dict, ref: dict | None, ev: str) -> list:
    """Tremor runs: ink error, change against the ordinary pen, words after the app, time at the travel limit."""
    out = []
    if _num(m.get("ink_err_um")) is not None:
        out.append(metric("Ink off the letters, on average", m["ink_err_um"] / 1000, "mm", ev, 2))
        if ref and ref is not m and (_num(ref.get("ink_err_um")) or 0) > 0:
            out.append(_txt("Compared with the ordinary pen", _change(m["ink_err_um"], ref["ink_err_um"]), ev))
    if _num(m.get("word_acc_app")) is not None:
        out.append(metric("Words right after the app's spelling check", 100 * m["word_acc_app"], "%", ev, 0))
    if (_num(m.get("at_travel_limit")) or 0) > 0.01:
        out.append(metric("Time with the tip at its limit", 100 * m["at_travel_limit"], "%", ev, 0))
    if m.get("app_words"):
        out.append(_txt("The app read", f"“{m['app_words']}”", ev))
    return out


def pd_metrics(m: dict, ref: dict | None, ev: str) -> list:
    """Parkinson's-like runs: letter height first -> last, size kept, words, buzzes, time, crowding, shake in the ink."""
    out = []
    xs, xe = _num(m.get("xh_start_mm")), _num(m.get("xh_end_mm"))
    if xs and xe:
        out.append(_txt("Letter height, first letters → last letters", f"{xs:.1f} → {xe:.1f} mm", ev))
        out.append(metric("Size kept at the end of the line", 100 * xe / xs, "%", ev, 0))
    if _num(m.get("word_acc_app")) is not None:
        out.append(metric("Words right after the app's spelling check", 100 * m["word_acc_app"], "%", ev, 0))
    if (_num(m.get("n_cues")) or 0) > 0:
        out.append(metric("Buzzes", m["n_cues"], "", ev, 0))
    wt = _num(m.get("writing_time_s"))
    if wt:
        rt = _num((ref or {}).get("writing_time_s"))
        out.append(_txt("Writing time", f"{wt:.0f} s" + (f" ({_change(wt, rt)} than the ordinary pen)" if rt and ref is not m and abs(wt / rt - 1) >= 0.005 else ""), ev))
    if _num(m.get("touching_frac")) is not None:
        out.append(metric("Letters touching their neighbours", 100 * m["touching_frac"], "%", ev, 0))
    if _num(m.get("tremor_in_ink_um")) is not None:
        out.append(metric("Shake left in the ink", m["tremor_in_ink_um"] / 1000, "mm", ev, 2))
    return out


def practice_metrics(m: dict, ref: dict | None, ev: str) -> list:
    """Guided practice runs: distance to the copybook letters, change against no guidance, letters and words read,
    the share of the ink's movement made by the device, what the app read."""
    out = []
    te = _num(m.get("target_err_um"))
    if te is not None:
        out.append(metric("Ink off the copybook letters, on average", te / 1000, "mm", ev, 2))
        rt = _num((ref or {}).get("target_err_um"))
        if rt and ref is not m:
            out.append(_txt("Compared with no guidance", _change(te, rt, closer=True), ev))
    if _num(m.get("letters_read_ok")) is not None:
        out.append(metric("Letters the app reads correctly", 100 * m["letters_read_ok"], "%", ev, 0))
    if _num(m.get("words_app")) is not None:
        out.append(metric("Words right after the app's spelling check", 100 * m["words_app"], "%", ev, 0))
    if (_num(m.get("device_share")) or 0) > 0.005:
        out.append(metric("Share of the ink's movement made by the pen or the board", 100 * m["device_share"], "%", ev, 0))
    if m.get("recognised"):
        out.append(_txt("The app read", f"“{m['recognised']}”", ev))
    return out


def spelling_metrics(m: dict, ref: dict | None, ev: str) -> list:
    out = []
    if m.get("recognised"):
        out.append(_txt("The app read", f"“{m['recognised']}”", ev))
    fw = m.get("flagged_words")
    if isinstance(fw, list):
        out.append(_txt("Words the app flags (it knows the sentence)", ", ".join(fw) if fw else "none", ev))
    if m.get("corrected_copy"):
        out.append(_txt("Corrected copy the app keeps next to your ink", f"“{m['corrected_copy']}”", ev))
    if m.get("free_writing_correction"):
        out.append(_txt("In free writing (the app does not know the sentence) its correction gives",
                        f"“{m['free_writing_correction']}”", ev))
    return out


PD_LABEL = {"pen_none": "Ordinary pen", "none": "Ordinary pen", "revH_off": "New pen, all help switched off",
            "cue": "Buzz when the letters shrink (“write bigger”)", "lines": "Paper with lines 1 cm apart",
            "size_assist_1.2": "Nose makes the ink 1.2 times larger", "size_assist_1.35": "Nose makes the ink 1.35 times larger",
            "size_assist_1.5": "Nose makes the ink 1.5 times larger", "size_assist_y1.35": "Nose makes the ink 1.35 times taller only",
            "size_adapt_y1.5": "Nose brings the letter height back (adaptive, up to 1.5 times)",
            "cue_size_1.35": "Buzz, and the nose makes the ink 1.35 times larger"}
PD_ORDER = ["pen_none", "none", "cue", "lines", "size_adapt_y1.5", "revH_off", "size_assist_1.2", "size_assist_1.35",
            "size_assist_1.5", "size_assist_y1.35", "cue_size_1.35"]
PD_KEY = {"pen_none", "none", "cue", "lines", "size_adapt_y1.5"}
PR_LABEL = {"none": "No guidance", "cue": "Buzz on a wrong letter (the ink is not changed)",
            "nose_partial": "Nose guidance, gentle (half strength)", "nose_full": "Nose guidance, full strength",
            "nose_nogate": "Nose guidance with no limits (the pen would write for you)",
            "board_partial": "Guidance board, gentle", "board_full": "Guidance board, full strength"}
PR_ORDER = ["none", "cue", "nose_partial", "nose_full", "board_partial", "board_full", "nose_nogate"]
PR_KEY = {"dysgraphia": {"none", "nose_partial", "nose_full", "board_full"},
          "dyslexia": {"none", "cue", "nose_full", "board_full"}}


def _cond_kind(cond: str) -> str:
    c = cond.lower()
    return ("parkinsons" if ("pd" in re.split(r"[^a-z]+", c) or "micrographia" in c or "parkinson" in c) else
            "guided" if ("practice" in c or "guided" in c) else "spelling" if "spelling" in c else "tremor")


def _pts3(a):
    return [[r3(q[0]), r3(q[1]), int(q[2]) if len(q) > 2 else 1] for q in a if _is_pt(q)]


def normalise_hw1(raw: dict):
    """results/handwriting/samples.json of the handwriting study (schema 'panels[{id, title, condition, device,
    caption, evidence, intended [[x, y, pen_down]], ink [[...]], metrics}]'): one panel per device run.  Runs that
    share a condition and a scenario (the id without its device) become one panel with one variant per device.
    Tremor, Parkinson's-like writing, guided practice and spelling each get their own labels and plain metrics."""
    meta = dict(raw.get("meta", {}))
    schema = str(meta.get("schema", ""))
    mm = re.search(r"at\s+([\d.]+)\s*Hz", schema)
    rate = float(mm.group(1)) if mm else 50.0
    mpd = re.search(r"PD\s+([\d.]+)\s*Hz", schema)
    rate_pd = float(mpd.group(1)) if mpd else rate
    groups: dict = {}
    for p in raw["panels"]:
        dev = str(p.get("device", "none"))
        pid = str(p.get("id", ""))
        scen = pid
        for tok in (dev, dev.replace(".", "p")):
            if tok and tok in scen:
                scen = scen.replace(tok, "")
                break
        scen = re.sub(r"_+", "_", scen).strip("_") or pid
        groups.setdefault((str(p.get("condition", "other")), scen), []).append(p)
    panels = []
    for (cond, scen), ps in groups.items():
        kind = _cond_kind(cond)
        learner = "dyslexia" if "dyslexia" in scen else "dysgraphia"
        order = PD_ORDER if kind == "parkinsons" else PR_ORDER if kind == "guided" else DEVICE_ORDER
        ps.sort(key=lambda q: order.index(q.get("device")) if q.get("device") in order else 99)
        first = ps[0]
        ev_raw = str(first.get("evidence", "SIM"))
        ev = "SIMULATION (model HW1)" if ev_raw.upper().startswith("SIM") else ev_raw
        refp = next((q for q in ps if str(q.get("device")) in ("none", "pen_none", "ordinary")), None)
        ref = (refp or {}).get("metrics")
        variants = []
        for q in ps:
            dev = str(q.get("device", "none"))
            ink = to_strokes(q.get("ink"))
            if not ink:
                continue
            m = q.get("metrics") or {}
            if kind == "parkinsons":
                role = "before" if dev in ("pen_none", "none") else "after" if dev in PD_KEY else "other"
                label, key_dev, mets = PD_LABEL.get(dev, q.get("title", dev)), dev in PD_KEY, pd_metrics(m, ref, ev)
            elif kind == "guided":
                role = "before" if dev == "none" else "other" if dev == "nose_nogate" else "after"
                label = PR_LABEL.get(dev) or str(q.get("title", dev)).split(": ", 1)[-1]
                key_dev, mets = dev in PR_KEY[learner], practice_metrics(m, ref, ev)
            elif kind == "spelling":
                role, label, key_dev, mets = "after", "The app's spelling help", True, spelling_metrics(m, ref, ev)
            else:
                role = _device_role(dev)
                label = DEVICE_LABEL.get(dev) or str(q.get("title", dev)).split(" - ")[0]
                key_dev, mets = dev in KEY_DEVICES, hw1_metrics(m, ref, ev)
            v = {"key": dev, "role": role, "label": label, "key_device": key_dev, "ink": ink, "metrics": mets}
            if kind == "tremor":          # kept for the animated scenes (a, b) when the mechanism replay is absent
                v["points"] = _pts3(q["ink"])
            if kind == "parkinsons" and q.get("intended") and q.get("intended") != first.get("intended"):
                v["intended"] = to_strokes(q["intended"]) or []      # the buzz and the lines change the writer's own plan
            variants.append(v)
        if not variants:
            continue
        cap = re.sub(r"\s*\(seed \d+\)", "", str(first.get("caption", "")))
        note = ""
        if kind == "parkinsons":
            title = "Letters that shrink along the line"
            cap = ("One simulated writer with Parkinson's-like writing copies a pangram: the letters start about 5 mm high "
                   "and shrink along the line. Faint line: the writer's own plan, which shrinks. The buzz and the lines "
                   "change the plan; the nose's size assist moves the ink.")
            note = ("How writers respond to the buzz and to the lines is an assumption from small studies (PDT-19, PDT-18). "
                    "The nose's size assist is new and untested; it can hide the shrinking from the writer.")
        elif kind == "guided":
            title = ("Copying a sentence: a learner who reverses b/d and p/q" if learner == "dyslexia" else
                     "Copying a sentence: a learner with poorly formed letters")
            cap = "One simulated learner copies “a big dog dug a deep pit by the pond”. Faint line: the copybook letters."
            note = ("No kind of guidance turned a reversed or wrong letter into the right one: for dyslexia the help is in "
                    "the app, which flags the words." if learner == "dyslexia" else
                    "Closer to the copybook is not always easier to read. Whether practice with guidance improves writing "
                    "without it still has to be tested.")
        elif kind == "spelling":
            title = "Spelling help: the ink is never changed"
        else:
            title = _plain_scenario(str(first.get("title", scen)))
        panel = {"id": f"{cond}_{scen}", "condition": cond, "evidence": ev, "title": title, "subtitle": cap,
                 "source": SAMPLES_FINAL, "provisional": False, "ruling_mm": 10 if kind == "parkinsons" else 8,
                 "rate_hz": rate_pd if kind == "parkinsons" else rate, "intended": to_strokes(first.get("intended")) or [],
                 "variants": variants, "note": note}
        if kind == "tremor":
            panel["intended_points"] = _pts3(first.get("intended", []))
        panels.append(panel)
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
               "power": "Battery", "haptic": "Vibration motor", "inertial": "Inertial module", "magnet": "Board magnet"}


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
            pills.append('<span class="pill opt">optional, in the first prototype</span>' if g == "inertial" else
                         '<span class="pill opt">optional, for the guidance board</span>' if (g == "magnet" or "board" in str(c.get("id", "")))
                         else '<span class="pill opt">optional</span>')
        ledger = e(c["ledger"]) if c.get("ledger") else '<span class="muted">—</span>'
        rows.append(
            f'<tr data-part="{e(c.get("id", ""))}"><td><span class="sw g-{e(g)}" aria-hidden="true"></span>'
            f'<b>{e(c.get("label", c.get("id", "")))}</b><span class="where">{e(GROUP_NAMES.get(g, g))} · '
            f'z {c["z0"]:g}–{c["z1"]:g} mm · {e(dims(c))}</span>{"".join(pills)}</td>'
            f'<td>{e(c.get("function", ""))}</td><td>{e(c.get("part", ""))}</td><td class="mono">{ledger}</td></tr>')
    return "\n".join(rows)


def inertial_note_html() -> str:
    """One line under the technology table: what the mechanism study found for weights and the rear module."""
    if not exists(INERTIAL_OPT):
        return ""
    try:
        ch = (load(INERTIAL_OPT).get("choice") or {}).get("inertial_module") or {}
        gains = [v.get("mean") for v in (ch.get("gain_band_8_12Hz_1_2mm") or {}).values() if _num((v or {}).get("mean")) is not None]
        worse = [v.get("frac_conditions_worse") for k, v in (ch.get("passive_weight_gain") or {}).items()
                 if k in ("0.5", "0.7") and _num((v or {}).get("frac_conditions_worse")) is not None]
        added = _num(ch.get("added_mass_g"))
    except (OSError, ValueError, AttributeError, TypeError):
        return ""
    if not gains:
        return ""
    t = (f"Weights: the mechanism study's rear module{f' ({added:.0f} g added)' if added else ''}, a tungsten slug moved by "
         f"coils, cuts the ink error left by the nose by a further {100 * min(gains):.0f}–{100 * max(gains):.0f} % for fast shakes of 1–2 mm. "
         "It is fitted in the first prototype; a measurement of how people grip the pen decides the product.")
    if worse:
        t += (f" A fixed extra weight made {100 * min(worse):.0f}–{100 * max(worse):.0f} % of those cases worse than the nose "
              "alone.")
    return (f'    <p class="note">{html.escape(t)} <span class="tag sim"><i></i>Simulation · model H1</span> '
            '<span class="tag prop"><i></i>Proposed design</span></p>')


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
        # Parkinson's-like writing and guided practice: averages over the study's runs (24 per kind of help)
        pdc = ((o.get("pd") or {}).get("aggregate") or {}).get("by_condition") or {}
        keep_pd = ("xh_start_mm", "xh_end_mm", "word_acc_app", "writing_time_s", "touching_frac", "tremor_in_ink_um",
                   "norm_jerk_median", "n_cues", "n")
        if pdc:
            out["pd"] = {"by_help": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk in keep_pd}
                                     for k, v in pdc.items() if isinstance(v, dict)},
                         "labels": PD_LABEL, "text": (o.get("text") or {}).get("pd", {})}
        pra = (o.get("practice") or {}).get("aggregate") or {}
        keep_pr = ("target_err_um", "letters_read_ok", "words_app", "device_share", "error_letters_read_as_target", "n")
        prac = {}
        for learner in ("dysgraphia", "dyslexia"):
            d = pra.get(learner)
            if isinstance(d, dict):
                prac[learner] = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk in keep_pr}
                                 for k, v in d.items() if isinstance(v, dict) and v}
        if prac:
            out["practice"] = {"by_help": prac, "labels": PR_LABEL, "spelling_flagged_share": pra.get("spelling_flagged_share"),
                               "text": (o.get("text") or {}).get("practice", {})}
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


# ------------------------------------------------------------------------------------------- mechanism replay (a, b)
REPLAYS = ("results/opt/viz_inertial_opt_1mm.json", "results/opt/viz_inertial_opt.json")
INERTIAL_OPT = "results/opt/inertial_opt.json"
REPLAY_CASES = {  # replay case key -> (role in the scenes, plain label)
    "unmodified": ("off", "New pen, nose held still"),
    "nose_oracle": ("best", "New pen, if it knew the shake exactly"),
    "nose": ("today", "New pen, today's tracker"),
    "nose+reaction_mass": ("module", "New pen, today's tracker + rear module"),
}


def _mm2(p):
    return [round(p[0] * 1000, 3), round(p[1] * 1000, 3)]


def replay_headline():
    """Band averages of the mechanism study (results/opt/inertial_opt.json), 8-12 Hz tremor of 1-2 mm at the hand,
    over the three grip assumptions (r_rot 0.3 / 0.5 / 0.7): ink error ratio against the nose held still."""
    if not exists(INERTIAL_OPT):
        return None
    try:
        o = load(INERTIAL_OPT)
        band = (o.get("rev_h_B") or {}).get("band_8_12Hz_1_2mm") or {}
        causal = [band[k]["causal"] for k in ("revh_r0.3", "revh_r0.5", "revh_r0.7") if k in band]
        oracle = [band[k]["oracle"] for k in ("revh_r0.3", "revh_r0.5", "revh_r0.7") if k in band]
        split = ((o.get("inertial_module") or {}).get("by_split") or {})
        module = [split[k]["band_8_12Hz_1_2mm"]["nose+ff"] for k in ("0.3", "0.5", "0.7")
                  if k in split and "nose+ff" in (split[k].get("band_8_12Hz_1_2mm") or {})]
        rng = lambda a: [round(min(a), 2), round(max(a), 2)] if a else None
        return {"causal": rng(causal), "oracle": rng(oracle), "module": rng(module),
                "label": (o.get("rev_h_B") or {}).get("label", "SIM (model H1)"), "source": INERTIAL_OPT,
                "doc": "docs/opt_inertial.md"}
    except (OSError, ValueError, KeyError, TypeError) as ex:
        warn(f"{INERTIAL_OPT} could not be summarised ({ex})")
        return None


def build_replay():
    """Scenes (a) and (b) replay the mechanism study (results/opt/viz_inertial_opt*.json): per case the handle's tip
    ('nib', where the hand puts the tip), the ink, the pen axis, pen up/down and the rear module's slug, in mm and
    rad, at the file's rate.  The tremor-free ink of the same pen ('ref_ink') is the letter the writer meant."""
    scen = []
    for src in REPLAYS:
        if not exists(src):
            continue
        try:
            v = load(src)
            meta = v.get("meta") or {}
            m = re.search(r"f0=([\d.]+).*?amp_pk=([\d.eE-]+)", str(meta.get("scenario", "")))
            f0, amp = (float(m.group(1)), float(m.group(2)) * 1000) if m else (None, None)
            t = v.get("t") or []
            t0 = t[0] if t else 0.0
            cases = {}
            for c in v.get("cases") or []:
                key = c.get("key")
                if key not in REPLAY_CASES:
                    continue
                role, label = REPLAY_CASES[key]
                dev = c.get("device") or {}
                rm = dev.get("r_pen_frame_m")
                met = c.get("metrics") or {}
                cases[role] = {
                    "key": key, "label": label, "study_label": c.get("label", ""), "description": c.get("description", ""),
                    "nib": [_mm2(p) for p in c["nib"]], "lift": [round(max(0.0, p[2]) * 1000, 3) for p in c["nib"]],
                    "ink": [_mm2(p) for p in c["ink"]], "ref": [_mm2(p) for p in c["ref_ink"]],
                    "axis": [[round(a, 5) for a in p[:3]] for p in c["axis"]],
                    "down": [1 if d else 0 for d in c["pen_down"]],
                    "rm": [[round(q[0] * 1000, 3), round(q[1] * 1000, 3)] for q in rm] if isinstance(rm, list) else None,
                    "ink_err_mm": round(met["ink_err_rms_um"] / 1000, 3) if _num(met.get("ink_err_rms_um")) is not None else None,
                    "ratio": round(met["ratio_vs_unmodified"], 3) if _num(met.get("ratio_vs_unmodified")) is not None else None}
            if "off" not in cases or len(cases) < 2:
                warn(f"{src}: the replay cases were not found; scenes (a) and (b) keep the other data")
                continue
            scen.append({"id": os.path.splitext(os.path.basename(src))[0], "source": src, "f0_hz": f0, "amp_mm": amp,
                         "title": (f"A shake of {amp:g} mm, {f0:g} times a second" if f0 else "Tremor"),
                         "rate_hz": meta.get("rate_Hz", 200.0), "t0": t0, "n": len(t),
                         "theta_deg": (meta.get("geometry_mm") or {}).get("theta_deg", 50.0), "cases": cases})
        except (OSError, ValueError, KeyError, TypeError, IndexError) as ex:
            warn(f"{src} could not be read ({ex})")
    if not scen:
        return None, None
    scen.sort(key=lambda s: -(s["amp_mm"] or 0))            # the 1 mm shake first
    first = load(scen[0]["source"]).get("meta", {})
    out = {"meta": {"evidence_status": first.get("evidence_status", "SIMULATION (model H1)"),
                    "generated_utc": first.get("generated_utc"), "git_revision": first.get("git_revision"),
                    "model_version": first.get("model_version"), "doc": "docs/opt_inertial.md",
                    "units": "mm, rad; page frame x along the line, y up the page; axis = unit vector of the pen axis"},
           "headline": replay_headline(), "scenarios": scen}
    return out, {"file": "replay.json", "source": " + ".join(s["source"] for s in scen) +
                 (f" (+ averages from {INERTIAL_OPT})" if out["headline"] else ""), "status": "final",
                 "modified": mtime_utc(scen[0]["source"]), "evidence": out["meta"]["evidence_status"]}


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
    replay, m_rep = build_replay()
    files = [m_lay, m_board, m_samp] + ([m_rep] if m_rep else []) + ([m_out] if m_out else []) + ([m_tip] if m_tip else [])
    manifest = {"built_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "git_revision": git_revision(), "files": files, "warnings": WARNINGS,
                "provisional_label": PROVISIONAL_LABEL}
    sizes = {"layout.json": dump(lay, "layout.json"), "board.json": dump(board, "board.json"),
             "samples.json": dump(samples, "samples.json")}
    for obj, name in ((tip, "tip.json"), (outc, "outcomes.json"), (replay, "replay.json")):
        path = os.path.join(DATA, name)
        if obj is not None:
            sizes[name] = dump(obj, name)
        elif os.path.exists(path):
            os.remove(path)
    sizes["manifest.json"] = dump(manifest, "manifest.json")
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        page = f.read()
    fills = {"<!--BUILD:COMPONENT_ROWS-->": component_rows(lay), "<!--BUILD:DATA_STATUS-->": status_html(manifest),
             "<!--BUILD:PROVENANCE-->": provenance_html(manifest, lay), "<!--BUILD:INERTIAL_NOTE-->": inertial_note_html()}
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
