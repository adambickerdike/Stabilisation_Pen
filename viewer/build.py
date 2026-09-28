#!/usr/bin/env python3
"""Assemble the 3D replay page (viewer/index.html + viewer/data/*.json).

Inputs (all generated elsewhere in the repository):
  results/cad/pencil_revP{L,Q}_viewer.json and _summary.json  (mechanics/cad/pencil_revP.py)
  results/pencil/viz_trace.json                               (sim/pencil, pencil model)
  results/ai/viz_guided.json                                  (aiguide, M1 guided mode)
  results/pencil/inertial_viz.json                            (sim/handpen, hand-pen model H1: cap devices)
  results/fusion/viz_fusion.json                              (fusion/viz.py, pencil model P1: accelerometer tracker)
  results/opt/viz_touchdown.json                              (opt/touchdown, pencil model P1: touchdown feed-forward)
  results/pencil/*.json, results/ai/*.json, results/s2r/*.json (numbers for the tables, via viewer/sections.py)
The page itself is viewer/template.html; the tables are rendered into it here so
they are readable without running any script.
Run: python3 viewer/build.py [--variant L|Q] [--trace PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
VIEW = os.path.join(ROOT, "viewer")
DATA = os.path.join(VIEW, "data")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


NOTES = {
    "neutral": "Stage held at centre. The ink carries the hand's tremor; this is the pencil with its correction switched off.",
    "oracle": "The stage is told the true tremor. This is what the mechanism can physically do with perfect knowledge of intent; "
              "at 0.3 mm tremor it spends about a third of the time at its travel limit.",
    "kalman": "The pen estimates the tremor from its own sensors. At 6 Hz it cannot separate tremor from writing, so it corrects "
              "almost nothing (it helps from about 8 Hz). Separating intent is the open problem.",
    "guided": "The nib is pulled toward a template of the stroke. Judged by distance to the path: the error chart shows the nearest-point distance.",
}


STAB_NOTES = {
    "unmodified": "No correction. The pen tilts in the grip and slides on its skid; the ink carries the hand's tremor minus what "
                  "the skid friction absorbs. The rings show where the fingers and the thumb-index web hold the pen.",
    "reaction_mass": "A 5.15 g tungsten slug in the cap, pushed sideways and along the pen by coils, with perfect knowledge of the "
                     "tremor. It is the best moving weight that fits the 20 g target, and it takes half the cell.",
    "stage": "The piezo nib stage alone, with perfect knowledge of the tremor. The same result as the pencil group, "
             "in the model that lets the pen tilt in the grip.",
    "stage+reaction_mass": "Nib stage plus the tungsten slug: the slug shaves the tremor peaks the stage cannot reach.",
    "cmg": "Two pairs of spinning tungsten rotors (60 000 rpm, spin slowed for display) on motorised gimbals that tip them to make "
           "torque. The strongest inertial option studied, but about 25 g and 0.34 W, with no room left for the cell; the full "
           "unit needs about 20 mm more length than the pen has.",
    "stage+cmg": "Nib stage plus the gyroscope pairs: the best physics studied, and impossible packaging.",
}


def stab_trace(path):
    """results/pencil/inertial_viz.json (model H1, m, window t0-t1) -> the viewer schema (mm, t from 0, key 'neutral'
    for the uncorrected case). housing = ball centre fixed to the barrel; nib = ball centre with the stage correction;
    intended = the same pen's tremor-free ink (the ratio reference)."""
    vz = load(path)
    r_b = 0.35e-3
    t0 = vz["t"][0]
    rnd = lambda v: float(f"{v:.5g}")          # noqa: E731
    cases = []
    for c in vz["cases"]:
        down = c["pen_down"]
        housing = [[rnd(x * 1e3), rnd(y * 1e3), rnd((z + r_b) * 1e3)] for x, y, z in c["nib"]]
        nib = [[rnd(ix * 1e3), rnd(iy * 1e3), rnd(r_b * 1e3 if d else h[2])] for (ix, iy), d, h in zip(c["ink"], down, housing)]
        dev = c.get("device") or {}
        out = {"key": "neutral" if c["key"] == "unmodified" else c["key"], "label": c["label"], "t": [rnd(t - t0) for t in vz["t"]],
               "housing": housing, "nib": nib, "intended": [[rnd(x * 1e3), rnd(y * 1e3)] for x, y in c["ref_ink"]],
               "contact": down, "tilt": c["tilt_rad"], "metric": "time",
               "q": [[rnd(a * 1e3), rnd(b * 1e3)] for a, b in dev["stage_q_m"]] if "stage_q_m" in dev else [[0.0, 0.0]] * len(down),
               "metrics": {"ink_err_rms_um": c["metrics"]["ink_err_rms_um"], "ratio_vs_neutral": c["metrics"]["ratio_vs_unmodified"],
                           "q_sat_frac": c["metrics"]["q_sat_frac"] if c["key"].startswith("stage") else None},
               "note": STAB_NOTES.get(c["key"], c.get("description", ""))}
        if dev.get("type") == "reaction_mass":
            out["device"] = {"type": "reaction_mass", "r": [[rnd(v * 1e3) for v in row] for row in dev["r_pen_frame_m"]], "force": dev["force_N"]}
        elif dev.get("type") == "cmg":
            out["device"] = {"type": "cmg", "gimbal": dev["gimbal_rad"], "torque": dev["torque_Nm"], "rpm": dev.get("rotor_rpm")}
        cases.append(out)
    meta = dict(vz["meta"])
    meta["case_group"] = "Weights and gyroscopes in the cap: 8 Hz, 0.3 mm tremor (hand-pen model H1, perfect knowledge)"
    return {"meta": meta, "units": {"length": "mm", "time": "s", "angle": "rad"}, "theta_deg": 50.0, "cases": cases}


def load_version():
    from stabpen import params as sp_params
    return sp_params.load(os.path.join(ROOT, "config", "pencil.yaml")).version()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="L", choices=("L", "Q"))
    ap.add_argument("--trace", default=os.path.join(ROOT, "results", "pencil", "viz_trace.json"))
    ap.add_argument("--guided", default=os.path.join(ROOT, "results", "ai", "viz_guided.json"))
    ap.add_argument("--inertial", default=os.path.join(ROOT, "results", "pencil", "inertial_viz.json"))
    ap.add_argument("--fusion", default=os.path.join(ROOT, "results", "fusion", "viz_fusion.json"))
    ap.add_argument("--touchdown", default=os.path.join(ROOT, "results", "opt", "viz_touchdown.json"))
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    cad = os.path.join(ROOT, "results", "cad", f"pencil_revP{a.variant}")
    geom = load(cad + "_viewer.json")
    summ = load(cad + "_summary.json")["summary"]
    P = summ["parameters_mm"]
    geom.update({"mass_total_g": summ["mass_total_g"], "z_skid": P["z_skid"], "skid_contact_r": P["skid_r"],
                 "stage_label": {"L": "piezo L pair", "Q": "piezo quad"}[a.variant], "variant": a.variant,
                 "pencil_params": load_version(),
                 "ball_r": next((q["ball_r"] for q in geom["primitives"] if q["type"] == "refill"), 0.35)})
    with open(os.path.join(DATA, "geometry.json"), "w") as f:
        json.dump(geom, f, separators=(",", ":"))
    trace = load(a.trace)
    for c in trace["cases"]:
        c.setdefault("note", NOTES.get(c["key"], ""))
        if c["key"] == "guided":
            c["metric"] = "path"      # guided mode is judged by distance to the path, not time-aligned
    with open(os.path.join(DATA, "viz_trace.json"), "w") as f:
        json.dump(trace, f, separators=(",", ":"))
    g_out = os.path.join(DATA, "viz_guided.json")
    if os.path.exists(a.guided):
        shutil.copyfile(a.guided, g_out)
    elif os.path.exists(g_out):
        os.remove(g_out)
    for src, name in ((a.touchdown, "viz_touchdown.json"),):
        out_p = os.path.join(DATA, name)
        if os.path.exists(src):
            with open(out_p, "w") as f:
                json.dump(load(src), f, separators=(",", ":"))
        elif os.path.exists(out_p):
            os.remove(out_p)
    f_out = os.path.join(DATA, "viz_fusion.json")
    if os.path.exists(a.fusion):
        with open(f_out, "w") as f:
            json.dump(load(a.fusion), f, separators=(",", ":"))
    elif os.path.exists(f_out):
        os.remove(f_out)
    s_out = os.path.join(DATA, "viz_inertial.json")
    if os.path.exists(a.inertial):
        with open(s_out, "w") as f:
            json.dump(stab_trace(a.inertial), f, separators=(",", ":"))
    elif os.path.exists(s_out):
        os.remove(s_out)
    fig_dir = os.path.join(VIEW, "figures")
    try:
        from viewer import sections_extra as SX
        figs = SX.gallery_files(ROOT)
    except ImportError:
        figs = []
    if os.path.isdir(fig_dir):
        shutil.rmtree(fig_dir)
    if figs:
        os.makedirs(fig_dir)
        for name, src in figs:
            shutil.copyfile(src, os.path.join(fig_dir, name))
    html = open(os.path.join(VIEW, "template.html"), encoding="utf-8").read()
    try:
        from viewer import sections
        body = sections.render(ROOT, variant=a.variant)
    except ImportError:
        body = ""
    html = html.replace("<!--SECTIONS-->", body)
    with open(os.path.join(VIEW, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    sizes = {n: os.path.getsize(os.path.join(DATA, n)) for n in sorted(os.listdir(DATA))}
    print("wrote viewer/index.html", len(html), "bytes; data", sizes)


if __name__ == "__main__":
    main()
