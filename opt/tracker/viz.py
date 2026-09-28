"""3-D replay traces of the trackers of this study on the pencil model P1 (viewer/ format, SIMULATION).

One test condition (seed 200, 10 Hz, 0.3 mm, harness convention) with the cases
  neutral        stage held at centre
  oracle         perfect disturbance knowledge (core mode 4)
  oracle_band    perfect knowledge of the 3-15 Hz part only (zero phase, not causal): the limit of a tremor tracker
  akf_prev_best  the previous best tremor-band tracker on the test grid (the AKF tuned on the grid's writing)
  akf_robust     the previous recommendation (robust AKF)
  <best>         the tracker this study recommends
Output: results/opt/viz_tracker.json in the schema of results/fusion/viz_fusion.json (fusion/viz.py: mm, 100 Hz,
the same per-case channels and metrics), so viewer/build.py can take it as another case group.
"""
from __future__ import annotations

import os
from typing import Dict, List, Tuple

import numpy as np

from fusion import data as FD
from fusion import harness as H
from fusion import sensors as S
from sim.pencil import evaluate as E
from sim.pencil import model as M
from stabpen import provenance

from . import RESULTS
from . import evaluate as EV

OUT = os.path.join(RESULTS, "viz_tracker.json")


def traces(best: Tuple[str, str, Dict, str, str], prev: Dict[str, Dict], seed: int = 200, f0: float = 10.0,
           amp: float = 0.3e-3) -> Dict:
    """best: (key, estimator name, params, label, note); prev: {"akf_prev_best": params, "akf_robust": params}."""
    EV.register()
    cfg = M.PencilConfig()
    sc0 = FD.test_scenario(seed, duration=FD.DURATION)
    sc1 = FD.test_scenario(seed, f0, amp, FD.DURATION)
    ref = FD.run(sc0, seed=seed)
    rn = FD.run(sc1, seed=seed)
    rec0 = S.record_from_result(ref, sc0)
    rec1 = S.record_from_result(rn, sc1)
    runs = {"neutral": rn,
            "oracle": FD.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, ref)), M.Controller(mode="oracle"), cfg, seed=seed),
            "oracle_band": FD.run(M.with_estimate(sc1, H.band_oracle_steps(rec1, rec0, sc1.t)), M.Controller(mode="external"),
                                  cfg, seed=seed)}
    labels = {"neutral": "No correction (stage held at centre)",
              "oracle": "Physical limit (perfect disturbance knowledge)",
              "oracle_band": "Tremor-band limit (perfect 3-15 Hz knowledge, not causal)",
              "akf_prev_best": "Previous best tremor tracker (AKF tuned on the grid's writing)",
              "akf_robust": "Previous recommendation (robust AKF)"}
    notes = {"neutral": "Stage held at centre: the ink carries the hand's tremor.",
             "oracle": "The stage is told the true disturbance, including the slow friction drift the tremor causes in this model.",
             "oracle_band": "The stage is told only the tremor-band (3-15 Hz) part of the disturbance: the best a tremor tracker can do.",
             "akf_prev_best": "Accelerometer Kalman filter with random-search settings tuned on smooth synthetic writing; it also "
                              "moves sharper writers' tremor-free ink by about 150 um.",
             "akf_robust": "The same filter with settings that barely touch tremor-free writing; it gives up most of the benefit."}
    specs = [("akf_prev_best", "akf", prev["akf_prev_best"]), ("akf_robust", "akf", prev["akf_robust"]),
             (best[0], best[1], best[2])]
    labels[best[0]] = best[3]
    notes[best[0]] = best[4]
    for key, name, params in specs:
        spec = H.Spec(key, name, params, {"page": "1k", "comp": "gyro"})
        _, dh, _ = H.estimate(spec, rec1, H.sensor_seed(seed, f0, amp))
        runs[key] = FD.run(M.with_estimate(sc1, S.expand_to_steps(dh, len(sc1.t), rec1.sdec)), M.Controller(mode="external"),
                           cfg, seed=seed)
    base = E.compare(rn, ref)
    rb = ref.info["static"]["r_b"]
    dec = int(round(0.01 / (ref["t"][1] - ref["t"][0])))
    sl = slice(0, None, dec)

    def sig(x):
        return float(f"{x:.4g}")

    def arr(a, scale=1.0):
        return [[sig(v * scale) for v in row] for row in np.asarray(a)[sl]]

    cases = []
    for key, r in runs.items():
        m = E.compare(r, ref)
        n = min(len(r["t"]), len(ref["t"]))
        cases.append({"key": key, "label": labels[key], "note": notes[key], "t": [sig(v) for v in r["t"][:n][sl]],
                      "housing": arr(np.column_stack([r.xy("pHx")[:n], r["pHz"][:n] - rb]), 1e3),
                      "nib": arr(np.column_stack([r.ink()[:n], r["Cz"][:n] - rb]), 1e3),
                      "intended": arr(ref.ink()[:n], 1e3),
                      "contact": [int(v > 0) for v in r["contact"][:n][sl]],
                      "q": arr(r.xy("q1")[:n], 1e3), "F_nib": arr(np.column_stack([r.xy("fnx")[:n], r["Nn"][:n]])),
                      "F_skid": arr(np.column_stack([r.xy("fsx")[:n], r["Ns"][:n]])), "F_act": arr(r.xy("Fa1")[:n]),
                      "V": arr(r.xy("V1")[:n]),
                      "metrics": {"ink_err_rms_um": sig(m["e_rms_um"]), "ratio_vs_neutral": sig(m["e_rms_um"] / base["e_rms_um"]),
                                  "band_ratio_vs_neutral": sig(m["e_band_rms_um"] / base["e_band_rms_um"]),
                                  "q_sat_frac": sig(m["q_sat_frac"]), "P_drive_mW": sig(float(np.mean(r["PrailB"])) * 1e3)}})
    meta = provenance.metadata("simulation (pencil model P1, synthetic handwriting and tremor; sensor models; nothing measured)",
                               seeds={"handwriting": seed, "tremor": seed + 1000, "sensors": H.sensor_seed(seed, f0, amp)},
                               extra={"model_version": M.MODEL_VERSION,
                                      "scenario": f"fusion.data.test_scenario({seed}, {f0}, {amp}) = sim.pensim.scenarios.handwriting(seed={seed}, duration=5.0, TremorSpec(f0={f0}, amp_pk={amp}), N0=1.0)",
                                      "sensors": "LSM6DSV16X-class 6-axis IMU, gyroscope-compensated, pen rotation rho 0.5 (ASSUMPTION); page sensor 1 kHz / 2 ms",
                                      "case_group": f"Tremor tracker tuned by backpropagation: handwriting with {f0:g} Hz, {amp * 1e3:g} mm tremor (pencil model P1)",
                                      "decimation": "4 kHz record decimated to 100 Hz", "script": "opt/tracker/viz.py"})
    return {"meta": meta, "units": {"length": "mm", "time": "s", "force": "N"}, "frame": "page frame (stabpen/frames.py)",
            "theta_deg": 50.0, "phi_deg": 0.0, "cases": cases}


def write(vz: Dict, path: str = OUT) -> str:
    provenance.write_json(path, vz)
    return path
