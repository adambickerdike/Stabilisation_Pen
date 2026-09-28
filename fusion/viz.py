"""3-D replay traces of the accelerometer tremor tracker on the pencil model P1 (viewer/, case group "fusion").

One test condition (seed 200, 10 Hz, 0.3 mm, the harness convention of sim/pencil/run_study.py) with:
  neutral      stage held at centre
  oracle       perfect disturbance knowledge (core mode 4)
  kalman       the frozen Kalman oscillator in the core (mode 3)
  akf_robust   the acceleration-domain Kalman filter, robust set, gyroscope-compensated 6-axis IMU,
               1 kHz page sensor (fusion/estimators.py via Controller(mode="external"))
  akf_personal the same filter with the set chosen by the 20 s calibration of this writer (fusion/personal.py)
Output: results/fusion/viz_fusion.json in the format of results/pencil/viz_trace.json (mm, 100 Hz).
Evidence status: SIMULATION (synthetic handwriting and tremor; nothing measured).
Run: python3 -m fusion.viz [--f0 10] [--seed 200]
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from fusion import data as FD
from fusion import harness as H
from fusion import sensors as S
from fusion import run_study as RS
from sim.pencil import evaluate as E
from sim.pencil import model as M
from stabpen import provenance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "fusion", "viz_fusion.json")

LABELS = {"neutral": "No correction (stage held at centre)",
          "oracle": "Physical limit (perfect disturbance knowledge)",
          "kalman": "Old tremor estimator (Kalman on position, frozen)",
          "akf_robust": "Accelerometer tracker (Kalman on the IMU, robust set)",
          "akf_personal": "Accelerometer tracker, tuned by a 20 s calibration"}
NOTES = {"neutral": "Stage held at centre: the ink carries the hand's tremor.",
         "oracle": "The stage is told the true disturbance. This is what the mechanism can do with perfect knowledge.",
         "kalman": "The previous estimator: a Kalman filter on the page-sensor position, with frozen parameters.",
         "akf_robust": "Reads the 6-axis IMU directly at about 2 kHz, corrects the lever arm with the gyroscope, and removes only a "
                       "steady oscillation it is sure of. Built never to move tremor-free writing much, so it gives up part of the benefit.",
         "akf_personal": "The same tracker with its frequency window and gates set from 20 s of drawing known shapes "
                         "(spiral, circle, lines) by this writer."}


def traces(seed: int = 200, f0: float = 10.0, amp: float = 0.3e-3):
    T = RS.tuned()
    pop = RS.population(T)
    cfg = M.PencilConfig()
    sc0 = FD.test_scenario(seed, duration=FD.DURATION)
    sc1 = FD.test_scenario(seed, f0, amp, FD.DURATION)
    ref = FD.run(sc0, seed=seed)
    rn = FD.run(sc1, seed=seed)
    rec1 = S.record_from_result(rn, sc1)
    runs = {"neutral": rn,
            "oracle": FD.run(M.with_disturbance(sc1, M.housing_disturbance(sc1, ref)), M.Controller(mode="oracle"), cfg, seed=seed),
            "kalman": FD.run(sc1, M.kalman_controller(), cfg, seed=seed)}
    from fusion import personal as PS
    pers = PS.personalise(seed, f0, amp, pop, RS.SK_1K)
    for key, params in (("akf_robust", pop), ("akf_personal", pers["params"])):
        spec = H.Spec(key, "akf", params, RS.SK_1K)
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
        cases.append({"key": key, "label": LABELS[key], "note": NOTES[key], "t": [sig(v) for v in r["t"][:n][sl]],
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
                               seeds={"handwriting": seed, "tremor": seed + 1000, "sensors": H.sensor_seed(seed, f0, amp),
                                      "calibration": seed + 40000},
                               extra={"model_version": M.MODEL_VERSION,
                                      "scenario": f"fusion.data.test_scenario({seed}, {f0}, {amp}) = sim.pensim.scenarios.handwriting(seed={seed}, duration=5.0, TremorSpec(f0={f0}, amp_pk={amp}), N0=1.0)",
                                      "sensors": "LSM6DSV16X-class 6-axis IMU, gyroscope-compensated, pen rotation rho 0.5 (ASSUMPTION); page sensor 1 kHz / 2 ms",
                                      "personal_calibration": {"estimate": {k: v for k, v in (pers.get("calibration") or {}).items()
                                                                            if isinstance(v, (int, float, str))},
                                                               "calib_band_rr": pers.get("calib_band_rr"),
                                                               "n_candidates": pers.get("n_candidates")},
                                      "case_group": f"Accelerometer tremor tracker: handwriting with {f0:g} Hz, {amp * 1e3:g} mm tremor (pencil model P1)",
                                      "decimation": "4 kHz record decimated to 100 Hz"})
    return {"meta": meta, "units": {"length": "mm", "time": "s", "force": "N"}, "frame": "page frame (stabpen/frames.py)",
            "theta_deg": 50.0, "phi_deg": 0.0, "cases": cases}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=200)
    ap.add_argument("--f0", type=float, default=10.0)
    ap.add_argument("--amp", type=float, default=0.3e-3)
    a = ap.parse_args()
    vz = traces(a.seed, a.f0, a.amp)
    provenance.write_json(OUT, vz)
    for c in vz["cases"]:
        print(c["key"], c["metrics"])


if __name__ == "__main__":
    main()
