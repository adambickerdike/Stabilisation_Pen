r"""Overlap checks against round 1 (SIMULATION vs SIMULATION): the same tasks in sim2 (MuJoCo, 3-D, the Rev J pen) and
in the round-1 models (HW1: 2-D page-plane nose model; HW1-D: HW1 + a heel element), on the same writers and seeds.

  autowrite  nose2's autowrite of "return library books by friday" at 2.5 mm x-height (aiguide v1 writers, as
             nose2), C1S nose with the pen lift, test writers 0-5, seed 200, no tremor and 1 mm at 8 Hz; nose2's
             per-case results (results/nose2/nose2.json and its cache when present) as the comparator
  tracing    the drive study's task (a) with dysgraphia-like learners (aiguide v1 writers, as study D), steered wheel
             steer-only and wheel + nose, test writers 0-5, seed 200; results/drive/tasks.json as the comparator
Differences are explained by what each model has (HW1 is 2-D: no tilt, no refill spring geometry, no rotation in the
grip; sim2 is 3-D with the H1 contact law and the Rev J mass properties).
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, List

import numpy as np

from . import ROOT
from . import revj as RJ
from . import stepper as ST
from . import tasks as TK
from .firmware import FWConfig


def autowrite_case(w: int, seed: int, f0: float, amp: float, pm, version: str = "v1", h_mm: float = 2.5,
                   lift: bool = True) -> Dict:
    ac = TK.AutowriteCase(w, h_mm=h_mm, version=version)
    if not ac.ok:
        return {"w": w, "seed": seed, "plan_ok": False}
    scn = ac.scenario(f0, amp, seed)
    fw = FWConfig(nose="autowrite", pen_lift="plan" if lift else "none", seed=seed, reach=6.0e-3)
    t0 = time.time()
    r = ST.run(pm, scn, fw, ac.task(), seed=seed)
    m = ac.metrics(r)
    m.update({"w": w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "plan_ok": True, "version": version,
              "wall_s": time.time() - t0, "lift": lift, "h_mm": h_mm})
    return m, r, ac


def nose2_reference() -> Dict:
    d = json.load(open(os.path.join(ROOT, "results", "nose2", "nose2.json")))
    return {"table": d["autowrite"]["table"], "by_frequency": d["autowrite"]["by_frequency_revJ_2p5"],
            "settings": d["autowrite"]["settings"]}


def drive_reference() -> Dict:
    p = os.path.join(ROOT, "results", "drive", "tasks.json")
    return json.load(open(p)) if os.path.exists(p) else {}
