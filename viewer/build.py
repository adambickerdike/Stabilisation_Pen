#!/usr/bin/env python3
"""Assemble the 3D replay page (viewer/index.html + viewer/data/*.json).

Inputs (all generated elsewhere in the repository):
  results/cad/pencil_revP{L,Q}_viewer.json and _summary.json  (mechanics/cad/pencil_revP.py)
  results/pencil/viz_trace.json                               (sim/pencil, pencil model)
  results/ai/viz_guided.json                                  (aiguide, M1 guided mode)
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


def load_version():
    from stabpen import params as sp_params
    return sp_params.load(os.path.join(ROOT, "config", "pencil.yaml")).version()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="L", choices=("L", "Q"))
    ap.add_argument("--trace", default=os.path.join(ROOT, "results", "pencil", "viz_trace.json"))
    ap.add_argument("--guided", default=os.path.join(ROOT, "results", "ai", "viz_guided.json"))
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    cad = os.path.join(ROOT, "results", "cad", f"pencil_revP{a.variant}")
    geom = load(cad + "_viewer.json")
    summ = load(cad + "_summary.json")["summary"]
    P = summ["parameters_mm"]
    geom.update({"mass_total_g": summ["mass_total_g"], "z_skid": P["z_skid"], "skid_contact_r": P["skid_r"],
                 "stage_label": {"L": "piezo L pair", "Q": "piezo quad"}[a.variant], "variant": a.variant,
                 "pencil_params": load_version()})
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
