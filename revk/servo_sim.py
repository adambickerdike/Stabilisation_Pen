"""SIMULATION check of the servo bandwidth that DEC-050's 2.5 x rule allows (study B's sim2 set-up, read-only, on the
TUNING writers only; nothing here touches the test writers).

Study B's frozen controller ran the nib's position loop at 80 Hz with a 100 Hz inner loop (bnib/sim.py config, rules.json
servo_fi 100).  Rev K's lowest structural mode (ball stuck, worst case over tilt, refill stiffness and pre-sliding) allows
about 46 Hz under the 2.5 x rule (revk/nib.modes_grid).  This runs study B's B1 pen in sim2 with Rev K's nib constants
(Km 0.334 N/sqrt(W) x layer, k 1.56 N/m of the C17200 wires) at three controller settings:
  A  80 Hz position loop, 100 Hz inner loop (study B's frozen setting)
  B  40 Hz position loop, 100 Hz inner loop
  C  40 Hz position loop, 46 Hz inner loop (both loops inside the 2.5 x rule)
on tuning writers 100-101, seed 300, the tuning cells (ET 8 Hz 1 mm, PD 5 Hz 1 mm) and tremor-free writing.
The sim2 model has no structural modes of the carrier: it measures what the lower bandwidth costs in tracking, not the
stability margin (that is the CALC of nib.modes_grid).  Caches and rows in revk/build/ (study B's build folder is never
written).  Run: python3 -m revk.servo_sim --variant A|B|C  then  python3 -m revk.servo_sim --collect
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace

from . import BUILD, RESULTS, ensure_paths, write_json

ensure_paths()

VARIANTS = {"A": (80.0, 100.0), "B": (40.0, 100.0), "C": (40.0, 46.0)}
WRITERS = (100, 101)
SEED = 300
REVK_KM = 0.3335
REVK_K = 1.5617


def run_variant(v: str, log=print) -> dict:
    import bnib.sim as S
    servo, inner = VARIANTS[v]
    S.SETUPS = BUILD / "servo_setups"                      # never study B's build folder
    orig = S.config

    def cfg(sd, theta_deg=50.0, dt=S.DT):
        c = orig(sd, theta_deg, dt)
        return replace(c, nose=replace(c.nose, servo_hz=servo, inner_hz=inner))
    S.config = cfg
    designs = S.apply_rules(S.sim_designs(), S.frozen_rules())
    b1 = designs["B1"]
    ev = dict(b1.ev)
    ev["Km_tip"] = REVK_KM
    ev["k_tip_N_m"] = REVK_K
    b1 = replace(b1, ev=ev, servo_fi=inner)
    pens = S.Pens({"B1": b1})
    rows = S.Rows(path=BUILD / f"servo_rows_{v}.json")
    tag = f"revk_servo|{v}"
    out = {"variant": v, "servo_hz": servo, "inner_hz": inner, "cells": [], "clean": []}
    t0 = time.time()
    for w in WRITERS:
        su = S.Setup(w, pens, "B1", log=log)
        S.run_clean(su, rows, tag, SEED, log=log)
        ck = f"{tag}|B1|clean|{w}|{SEED}|deltapen|nose"
        out["clean"].append({"writer": w, "moved_um": rows.rows[ck]["moved_vs_clean_um"], "P_nib_W": rows.rows[ck]["P_nib_W"]})
        for kind, f0, amp in S.TUNE_CELLS:
            S.run_cell(su, rows, tag, kind, f0, amp, SEED, log=log)
            kn = f"{tag}|B1|{kind}|{f0:g}|{amp * 1e3:g}|{w}|{SEED}|deltapen|nose"
            k0 = f"{tag}|B1|{kind}|{f0:g}|{amp * 1e3:g}|{w}|{SEED}|deltapen|none"
            out["cells"].append({"writer": w, "cell": f"{kind} {f0:g} Hz {amp * 1e3:g} mm",
                                 "ink_err_none_um": rows.rows[k0]["ink_err_um"], "ink_err_nib_um": rows.rows[kn]["ink_err_um"],
                                 "P_nib_W": rows.rows[kn]["P_nib_W"]})
        rows.save()
    out["runtime_s"] = time.time() - t0
    json.dump(out, open(BUILD / f"servo_result_{v}.json", "w"), indent=1, default=float)
    return out


def collect() -> str:
    res = {}
    for v in VARIANTS:
        p = BUILD / f"servo_result_{v}.json"
        if p.exists():
            res[v] = json.load(open(p))
    summ = {}
    for v, r in res.items():
        import numpy as np
        ratio = [c["ink_err_nib_um"] / c["ink_err_none_um"] for c in r["cells"]]
        summ[v] = {"servo_hz": r["servo_hz"], "inner_hz": r["inner_hz"],
                   "ink_err_nib_um_mean": float(np.mean([c["ink_err_nib_um"] for c in r["cells"]])),
                   "ink_err_none_um_mean": float(np.mean([c["ink_err_none_um"] for c in r["cells"]])),
                   "ratio_mean": float(np.mean(ratio)), "moved_um_mean": float(np.mean([c["moved_um"] for c in r["clean"]])),
                   "P_nib_mW_mean": float(np.mean([c["P_nib_W"] for c in r["cells"]]) * 1e3), "runtime_s": r["runtime_s"]}
    out = {"variants": res, "summary": summ,
           "setup": {"writers": list(WRITERS), "seed": SEED, "cells": "bnib.sim.TUNE_CELLS + tremor-free writing",
                     "nib": {"Km_tip": REVK_KM, "k_tip_N_m": REVK_K}, "note": __doc__},
           "label": "SIMULATION (sim2 via bnib/sim.py, tuning writers only; synthetic tremor; no carrier structural modes "
                    "in the model)"}
    return write_json(RESULTS / "servo_bandwidth_sim.json", out, "SIMULATION (tuning writers 100-101, seed 300)",
                      extra={"command": "python3 -m revk.servo_sim --variant A|B|C; --collect"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS))
    ap.add_argument("--collect", action="store_true")
    a = ap.parse_args(argv)
    if a.variant:
        r = run_variant(a.variant)
        print(json.dumps({k: v for k, v in r.items() if k != "cells"}, default=float))
    if a.collect:
        print(collect())
    return 0


if __name__ == "__main__":
    sys.exit(main())
