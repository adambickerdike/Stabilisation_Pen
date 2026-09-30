"""Calibrate a causal servo from linear uncertainty bounds, then inspect physics.

The gain choice is made by the saved linear rule before nonlinear bench runs.
No word-writing test cases or learned policies enter this calibration.
"""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from .servo_design import pole_summary
from . import sim as S
from sim2j import revj as RJ
from sim.pensim import scenarios as SCN

OUT = Path(__file__).resolve().parents[1] / "results/improvement/control"


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def run():
    cfg = RJ.config(heel=False)
    pm = RJ.build(cfg)
    physical = dict(inertia=pm.info["nose_I_pivot"], spring=cfg.nose.k_r,
                    damping=pm.info["nose_c_flex"], resistance=cfg.nose.R, inductance=cfg.nose.L_ind)
    protocol = {"evidence": "CALC and SIM, proposed RevJ plant; no hardware or RevK validation",
                "linear_model": "Exact ZOH mechanics and coil, discrete PI-D and delayed Hall samples; no contact",
                "candidates_hz": [60, 80, 100, 125, 150, 200, 400],
                "delay_ticks": [1, 2, 3, 4], "inertia_ratio": [.7, 1., 1.3], "torque_ratio": [.7, 1., 1.3],
                "hall_cutoff_hz": 300., "sample_hz": 10000., "radius_max": .998,
                "rule": "Highest candidate bandwidth with all uncertainty-grid pole radii<=0.998; freeze before bench",
                "uncertainty_note": "Declared engineering stress bounds, not measured uncertainty or a continuous robust proof",
                "physical": physical,
                "bench_cases": [{"seed": seed, "frequency_hz": f, "amplitude_m": a}
                                for seed in [117, 211, 419] for f, a in [(0., 0.), (6., .0005), (10., .0015)]],
                "bench_duration_s": 1.2, "bench_scoring_start_s": .4,
                "source_sha256": {str(p): hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest()
                                  for p in ["servo_design.py", "servo_design_study.py", "sim.py", "params.py"]}}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "servo_design_protocol.json"
    if path.exists():
        if json.loads(path.read_text()) != protocol:
            raise RuntimeError("Calibration protocol changed; do not overwrite it")
    else:
        dump(path, protocol)
    linear = []
    for f in protocol["candidates_hz"]:
        for delay in protocol["delay_ticks"]:
            for ir in protocol["inertia_ratio"]:
                for tr in protocol["torque_ratio"]:
                    kwargs = dict(inner_hz=f, delay_ticks=delay, inertia_ratio=ir, torque_ratio=tr)
                    linear.append({**kwargs, **pole_summary(**physical, **kwargs)})
    worst = {f: max(r["spectral_radius"] for r in linear if r["inner_hz"] == f) for f in protocol["candidates_hz"]}
    chosen = max(f for f, radius in worst.items() if radius <= protocol["radius_max"])
    selection = {"selected_inner_hz": chosen, "worst_radius_by_hz": worst, "linear_grid": linear}
    dump(OUT / "servo_design_frozen.json", selection)
    print("Frozen linear selection", chosen, "Hz", worst, flush=True)
    modes = [("legacy_true", 400.), ("hall", 400.), ("hall", float(chosen))]
    rows = []
    for mode, f in modes:
        for case in protocol["bench_cases"]:
            cc = cfg.replace(nose=replace(cfg.nose, inner_hz=f, velocity_source=mode))
            pm = RJ.build(cc)
            sc = SCN.static_hold(duration=protocol["bench_duration_s"], theta_deg=cc.geom.theta_deg, N0=cc.N0)
            # A smooth start avoids testing an unintended infinite command step.
            def policy(t, pm, servo):
                ramp = min(max((t-.2)/.2, 0), 1)
                q = case["amplitude_m"] * np.sin(2*np.pi*case["frequency_hz"]*t) * ramp
                return [q, 0.]
            result = S.run(pm, sc, S.RunOptions(policy=policy, seed=case["seed"]))
            mask = result["t"] >= protocol["bench_scoring_start_s"]
            error = result.xy("q1")[mask] - result.xy("qd1")[mask]
            rows.append({"velocity_source": mode, "inner_hz": f, **case,
                         "follower_error_rms_um": float(np.sqrt(np.mean(np.sum(error**2, axis=1))))*1e6,
                         "contact_fraction": float(np.mean(result["contact"][mask])),
                         "coil_power_W": float(np.mean(result["Pcu"][mask])),
                         "coil_temperature_C": float(np.max(result["Tcoil"])),
                         "travel_rms_mm": float(np.sqrt(np.mean(np.sum(result.xy("q1")[mask]**2, axis=1))))*1e3})
            print(mode, f, case, rows[-1], flush=True)
            dump(OUT / "servo_design_bench_rows.json", rows)
    summaries = []
    for mode, f in modes:
        selected = [r for r in rows if r["velocity_source"] == mode and r["inner_hz"] == f]
        summaries.append({"velocity_source": mode, "inner_hz": f,
                          "mean_follower_error_rms_um": float(np.mean([r["follower_error_rms_um"] for r in selected])),
                          "min_contact_fraction": min(r["contact_fraction"] for r in selected),
                          "mean_coil_power_W": float(np.mean([r["coil_power_W"] for r in selected])),
                          "max_coil_temperature_C": max(r["coil_temperature_C"] for r in selected)})
    dump(OUT / "servo_design_results.json", {"protocol": protocol, "selection": selection,
                                             "bench": rows, "summary": summaries})
    print(json.dumps(summaries, indent=2), flush=True)


if __name__ == "__main__":
    run()
