"""Fresh engineering test after causal-servo gain freeze; no learned policy.

Both candidates see the same causal Hall sensors and plant draws, and are
scored against one common, noise-free ideal clean physical reference. This
tests the servo repair; it cannot establish patient benefit or word accuracy.
"""
from __future__ import annotations

import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np

from .rl import RevJTremorEnv
from .rl_integrity_study import ROOT, OUT, dump


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def final_cases():
    return [{"writer": w, "seed": 102000 + wi*29 + fi, "f0": f, "amp": a, "class": label}
            for wi, w in enumerate(range(35001, 35006)) for fi, f in enumerate([5.5, 8., 10.5])
            for a, label in [(0., "clean"), (.3e-3, "mild"), (1.72e-3, "large")]]


def evaluate(case, inner_hz):
    env = RevJTremorEnv(writers=[case["writer"]], episode_s=2.5, settle_s=3.,
                       p_free=1. if case["amp"] == 0 else 0., heel=False, reference_mode="ideal_clean",
                       fixed_params={"inner_hz": inner_hz, "velocity_source": "hall",
                                     "contact_source": "measured", "amp": case["amp"], "f0": case["f0"]})
    env.reset(seed=case["seed"])
    reference_hash = hashlib.sha256(env.ref_ink.tobytes() + env.ref_con.tobytes()).hexdigest()
    start_energy = env.st.servo.copper_energy_J
    starting_temperature = max(c.T for c in env.st.servo.coils)
    rows = []
    done = False
    while not done:
        _, _, term, trunc, metrics = env.step(np.zeros(3))
        rows.append(metrics)
        done = term or trunc
    dt = np.array([r["duration_s"] for r in rows])
    duration = float(dt.sum())
    integral = lambda key: float(np.dot(dt, [r[key] for r in rows]))
    ref_time = integral("reference_fraction")
    return {**case, "inner_hz": inner_hz, "actual_f0_hz": None if env.amp == 0 else env.f0,
            "reference_sha256": reference_hash, "duration_s": duration,
            "reference_ink_s": ref_time,
            "rms_um": float(np.sqrt(integral("error_sq_m2")/max(ref_time, 1e-30)))*1e6,
            "missing_fraction": integral("missing_fraction")/duration,
            "extra_fraction": integral("extra_fraction")/duration,
            "contact_fraction": integral("contact_fraction")/duration,
            "reference_fraction": integral("reference_fraction")/duration,
            "cost": integral("cost")/duration,
            "coil_energy_J": env.st.servo.copper_energy_J-start_energy,
            "coil_power_W": (env.st.servo.copper_energy_J-start_energy)/duration,
            "coil_temperature_start_C": starting_temperature,
            "coil_temperature_max_C": max(starting_temperature, max(r["coil_temperature_C"] for r in rows)),
            "hall_stale_or_warmup_ticks": env.st.servo.hall_stale_ticks}


def cluster_interval(rows, values, seed=514):
    """Exploratory paired bootstrap by synthetic writer, not a population CI."""
    writers = sorted({r["writer"] for r in rows})
    per_writer = [np.mean([v for r, v in zip(rows, values) if r["writer"] == w]) for w in writers]
    rng = np.random.default_rng(seed)
    samples = np.asarray(per_writer)[rng.integers(0, len(writers), (5000, len(writers)))].mean(axis=1)
    return {"mean": float(np.mean(per_writer)), "bootstrap_95pct": np.quantile(samples, [.025, .975]).tolist(),
            "synthetic_writer_clusters": len(writers)}


def summarise(pairs):
    result = {}
    for group in ("clean", "mild", "large", "all"):
        selected = [p for p in pairs if group == "all" or p["case"]["class"] == group]
        b, c = [p["old_causal400"] for p in selected], [p["causal80"] for p in selected]
        result[group] = {
            "n_cases": len(c),
            "old_mean_rms_um": float(np.mean([r["rms_um"] for r in b])),
            "new_mean_rms_um": float(np.mean([r["rms_um"] for r in c])),
            "new_worst_rms_um": max(r["rms_um"] for r in c),
            "paired_rms_ratio": cluster_interval(c, [r["rms_um"]/max(q["rms_um"], 1e-9) for r, q in zip(c, b)]),
            "old_mean_coil_power_W": float(np.mean([r["coil_power_W"] for r in b])),
            "new_mean_coil_power_W": float(np.mean([r["coil_power_W"] for r in c])),
            "new_max_coil_temperature_C": max(r["coil_temperature_max_C"] for r in c),
            "old_mean_missing_fraction": float(np.mean([r["missing_fraction"] for r in b])),
            "new_mean_missing_fraction": float(np.mean([r["missing_fraction"] for r in c])),
            "old_mean_extra_fraction": float(np.mean([r["extra_fraction"] for r in b])),
            "new_mean_extra_fraction": float(np.mean([r["extra_fraction"] for r in c])),
            "new_worse_error_cases": sum(r["rms_um"] > q["rms_um"] for r, q in zip(c, b)),
        }
    return result


def evaluate_pair(case):
    pair = {"case": case, "old_causal400": evaluate(case, 400.), "causal80": evaluate(case, 80.)}
    if pair["old_causal400"]["reference_sha256"] != pair["causal80"]["reference_sha256"]:
        raise AssertionError("The candidates do not share the same reference")
    return pair


def run():
    frozen = json.loads((OUT / "servo_design_frozen.json").read_text())
    assert frozen["selected_inner_hz"] == 80
    protocol = {"evidence": "SIM, fresh synthetic engineering cases; no patient, handwriting-reader or RevK validation",
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "version": 2,
                "freeze_sha256": sha(OUT / "servo_design_frozen.json"),
                "selection": "80Hz frozen from independent linear uncertainty grid before engineering bench and final cases",
                "candidates": {"old_causal400": 400., "causal80": 80.}, "cases": final_cases(),
                "reference": "Same ideal clean physical trajectory for both candidates; noiseless Hall, true velocity400Hz only in reference",
                "observations": "Both candidates causal Hall300Hz derivative filter, declared noise and latency, 1ms freshness; delayed measured refill contact gates servo bias/authority",
                "aborted_previous_run": "aborted_hall_only_final: stopped after11pairs because true contact remained in servo gating; no gain retuning; all final writerIDs and seeds changed",
                "policy": "Zero residual; existing guarded tracker identical for both; no PPO or tuning on these cases",
                "power": "Copper energy accumulated at10kHz servo/thermal ticks, divided by scored duration",
                "limits": "Short notes, starts nominal ambient then3s rest; coil temperature is not grip surface temperature",
                "uncertainty": "5000 paired resamples by5synthetic writer clusters, descriptive only; shared glyph family",
                "rejection_reporting": "Report every case, including worse tracking, extra or missing ink and high temperature; no case exclusion",
                "parallel_workers": 2,
                "source_sha256": {str(p.relative_to(ROOT)): sha(p) for prefix in ("sim2", "sim2j")
                                  for p in sorted((ROOT / prefix).glob("*.py"))},
                "runtime": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__}}
    path = OUT / "causal_controller_protocol.json"
    if path.exists():
        old = json.loads(path.read_text())
        for key in ("freeze_sha256", "source_sha256", "cases", "candidates"):
            if old[key] != protocol[key]:
                raise RuntimeError("Frozen final inputs changed; use a new version instead of overwriting")
        protocol = old
    else:
        dump(path, protocol)  # no final scenario has run before this write
    pairpath = OUT / "causal_controller_pairs.json"
    pairs = json.loads(pairpath.read_text()) if pairpath.exists() else []
    started = time.time()
    from concurrent.futures import ProcessPoolExecutor
    start_index = len(pairs)
    with ProcessPoolExecutor(max_workers=protocol["parallel_workers"]) as pool:
        for i, pair in enumerate(pool.map(evaluate_pair, protocol["cases"][start_index:]), start=start_index):
            case = pair["case"]
            pairs.append(pair)
            dump(pairpath, pairs)
            print(f"{i+1}/45 {case['class']} writer{case['writer']} f{case['f0']}: "
                  f"{pair['old_causal400']['rms_um']:.1f}->{pair['causal80']['rms_um']:.1f}um, "
                  f"{pair['old_causal400']['coil_power_W']:.2f}->{pair['causal80']['coil_power_W']:.2f}W", flush=True)
    result = {"protocol": protocol, "pairs": pairs, "summary": summarise(pairs),
              "wall_this_invocation_seconds": time.time()-started,
              "conclusion": "Servo repair evaluated under shared causal sensing. This does not establish usable handwriting, word correction, long-duration thermal safety, or clinical benefit."}
    dump(OUT / "causal_controller_results.json", result)
    print(json.dumps(result["summary"], indent=2), flush=True)


if __name__ == "__main__":
    run()
