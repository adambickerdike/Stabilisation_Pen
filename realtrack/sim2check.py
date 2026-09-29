"""One confirmation of the frozen design in the physics simulator sim2 (sim2j's ET grid; SIMULATION, synthetic inputs).

What: sim2j's test writer 0 (v2 synthetic writer, 'return library', Rev J pen with the heel wheel retracted, H1 hand),
seed 200, ET tremor from the project's model (stabpen TremorSpec) at 4 / 8 / 12 Hz x 0.3 / 1 / 2 mm, and the same
writing without tremor.  The device-off run records the pen's own sensor samples (sim2j firmware, record_streams); the
frozen design runs once over them (causal, the same code as in HW1; the IMU's group delay set to sim2's online IMU,
0.25 ms, as sim2j's firmware does for its trackers) and is replayed as the nose command in a second run with the same
seed (sim2j/learned_replay.py's method: valid because the nose's action does not change the handle's motion in sim2,
within 1 %, docs/revJ_simulation.md).  The device-off, G4 ('nose') and perfect-knowledge rows are sim2j's own cached
test rows for the same writer, seed and cells (sim2j/build/et_rows.json, read-only); the device-off run is repeated
here and must match sim2j's row (determinism check).
Nothing is written to sim2j/: the writer's adapted hand path is read from sim2j's cache if it exists, otherwise it is
recomputed into realtrack/build/sim2_setups; the run's working directory is realtrack/build (MuJoCo's log file).
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Dict, List, Optional

import numpy as np

from . import BUILD_DIR, REPO_ROOT, RESULTS_DIR
from . import estimators as E

OUT = BUILD_DIR / "sim2"
CELLS = [(f, a) for a in (0.3e-3, 1.0e-3, 2.0e-3) for f in (4.0, 8.0, 12.0)]
SIM2_ACC_GD = 0.25e-3


def _setup(w: int, log=print):
    from sim2j import et as ET
    pens = ET.PenModels()
    orig = ET.WriterSetup._cache_path

    def cache_path(self, n_adapt):
        p = orig(self, n_adapt)
        if p and os.path.exists(p):
            return p
        d = BUILD_DIR / "sim2_setups"
        d.mkdir(parents=True, exist_ok=True)
        return str(d / os.path.basename(p)) if p else None
    ET.WriterSetup._cache_path = cache_path
    try:
        su = ET.WriterSetup(w, pens, log=log)
    finally:
        ET.WriterSetup._cache_path = orig
    return su


def table_for(design: Dict, st, gd: float, n_ticks: int, Ts: float = 0.5e-3) -> np.ndarray:
    """dtab[k] = the design's estimate of the handle tremor at tau_k, from its tick output at tau_k - gd (which it
    predicted to that tick + gd): the firmware's 'oracle' slot reads dtab at t + gd, so the tick at t uses the output
    computed at t (causal)."""
    old = E.ACC_GD
    E.ACC_GD = SIM2_ACC_GD
    try:
        dz = dict(design)
        if dz["family"] in ("akf", "gatefast", "revh"):
            p = dict(dz.get("params") or {})
            if dz["family"] == "akf":
                p["acc_gd"] = SIM2_ACC_GD
            dz["params"] = p
        d, _ = E.estimate(dz, st, case=None, sensor="deltapen", horizon=gd)
    finally:
        E.ACC_GD = old
    k0 = int(round(gd / Ts))
    out = np.zeros((n_ticks, 2))
    n = min(len(d), n_ticks - k0)
    out[k0:k0 + n] = d[:n]
    return out


def run(log=print, quick: bool = False, writers=(0,), seed: int = 200) -> Dict:
    from . import test as T
    fr = T.load_frozen()
    design = fr["chosen"]
    OUT.mkdir(parents=True, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(BUILD_DIR)
    try:
        from dataclasses import replace
        from sim2j import et as ET
        from sim2j import learned_replay as LR
        from sim2j import stepper as ST
        rows_ref = json.load(open(REPO_ROOT / "sim2j" / "build" / "et_rows.json"))
        out = {"rows": [], "design": design, "cells": [[f, a] for f, a in CELLS]}
        for w in writers:
            su = None
            cells = CELLS[:2] if quick else CELLS
            for f0, amp in [(0.0, 0.0)] + cells:
                key = f"w{w}_s{seed}_{f0:g}_{amp * 1e3:g}"
                p = OUT / f"{key}.json"
                if p.exists():
                    out["rows"].append(json.loads(p.read_text()))
                    continue
                su = su or _setup(w, log)
                t0 = time.time()
                nz = su.pm.cfg.nose
                gd = 2 * nz.servo_zeta / (2 * math.pi * nz.servo_hz) + 0.25e-3
                if amp > 0:
                    rn = ET.run_case(su, "none", f0, amp, seed, keep=True, record=True)
                    r_none = rn.pop("_r")
                else:
                    r_none = su.clean_ref(seed)
                    rn = {"ink_err_um": None}
                st = LR.streams_of(r_none)
                dtab = table_for(design, st, gd, int(r_none.info["n_ticks"]) + 10)
                case = su.case
                tr = case.tremor(f0, amp, seed) if amp > 0 else None
                scn = case.scenario(tremor=tr)
                fw = replace(ET.controller("oracle", seed=seed * 7 + su.w))
                r = ST.run(su.pm, scn, fw, {"oracle_d": dtab}, mu=ET.mu_for(su.w, seed, f0, amp), seed=seed)
                m = su.metrics(r, ref_none=r_none if amp > 0 else None, clean_ref=su.clean_ref(seed) if amp <= 0 else None)
                ref = {c: rows_ref.get(f"clean|{w}|{seed}|{c}" if amp <= 0 else f"{f0:g}|{amp * 1e3:g}|{w}|{seed}|{c}")
                       for c in ("none", "nose", "oracle", "tcn")}
                row = {"w": w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3, "new": m, "none_rerun": rn,
                       "sim2j_rows": ref, "wall_s": time.time() - t0}
                p.write_text(json.dumps(row, default=float))
                out["rows"].append(row)
                log(f"[sim2] {key}: new ink {m.get('ink_err_um', float('nan')):.0f} um "
                    f"(ratio {m.get('ratio', float('nan'))}), moved {m.get('moved_vs_clean_um')}; {time.time() - t0:.0f} s")
        return out
    finally:
        os.chdir(cwd)
