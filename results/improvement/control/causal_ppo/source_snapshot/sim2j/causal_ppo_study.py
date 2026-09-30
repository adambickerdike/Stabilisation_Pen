"""Fresh, larger PPO screen on the repaired causal plant; frozen before training.

Three final checkpoints, separate synthetic train/tune/test writers, matched
sensor draws and common ideal clean references. Every failed seed is retained.
Clean protection uses actual policy-induced trajectory change relative to the
same causal controller, alongside common-target error and ink constraints.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from .rl import RevJTremorEnv
from .rl_integrity_study import ROOT, dump

OUT = ROOT / "results/improvement/control/causal_ppo"
STEPS = 65536
SEEDS = [0, 1, 2]
RULE = {
    "clean_delta_mean_um_max": 25., "clean_delta_worst_um_max": 50.,
    "clean_error_mean_increase_um_max": 5., "clean_error_worst_increase_um_max": 10.,
    "mild_ratio_max": 1.02, "large_ratio_max": .98, "large_worst_ratio_max": 1.05,
    "large_cluster_ratio_95_upper_max": 1.,
    "missing_increase_max": .005, "extra_increase_max": .005,
    "power_ratio_max": 1.05, "temperature_increase_C_max": 2.,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(split):
    writers = range(42001, 42004) if split == "tune" else range(43001, 43006)
    frequencies = [5.5, 9.5] if split == "tune" else [5., 8., 11.]
    seed0 = 212000 if split == "tune" else 223000
    return [{"writer": w, "seed": seed0 + wi*29 + fi, "f0": f, "amp": amp, "class": label}
            for wi, w in enumerate(writers) for fi, f in enumerate(frequencies)
            for amp, label in [(0., "clean"), (.3e-3, "mild"), (1.72e-3, "large")]]


def train_seed(seed):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    checkpoint = OUT / "checkpoints" / f"seed_{seed}.zip"
    record_path = OUT / f"training_seed_{seed}.json"
    if checkpoint.exists() and record_path.exists():
        old = json.loads(record_path.read_text())
        if old["model_sha256"] != sha(checkpoint):
            raise RuntimeError("Saved training checkpoint changed")
        return old
    env = RevJTremorEnv(seed=140000 + seed, writers=range(40000, 40800), episode_s=2.5,
                       settle_s=3., p_free=.5, heel=False, reference_mode="ideal_clean",
                       fixed_params={"inner_hz": 80., "velocity_source": "hall", "contact_source": "measured"})
    if torch.get_default_dtype() != torch.float32:
        raise RuntimeError("Unrelated import changed torch's default dtype")
    model = PPO("MlpPolicy", env, n_steps=1024, batch_size=256, n_epochs=5, learning_rate=3e-4,
                gamma=.98, gae_lambda=.95, clip_range=.2, ent_coef=0.,
                policy_kwargs={"net_arch": [64, 64], "activation_fn": torch.nn.Tanh, "log_std_init": -2.},
                seed=seed, device="cpu", verbose=0)
    print(f"Training causal seed{seed}: requested {STEPS} transitions", flush=True)
    start = time.time()
    model.learn(total_timesteps=STEPS)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    model.save(checkpoint)
    record = {"seed": seed, "requested_steps": STEPS, "actual_steps": int(model.num_timesteps),
              "wall_seconds": time.time()-start, "episode_metrics": env.ep_log, "env_stats": env.stats,
              "model_sha256": sha(checkpoint), "torch_default_dtype": str(torch.get_default_dtype())}
    dump(record_path, record)
    print(f"Finished seed{seed}: {model.num_timesteps} transitions in {record['wall_seconds']:.1f}s", flush=True)
    return record


def evaluate_job(job):
    case, name, checkpoint = job
    key = f"{case['writer']}_{case['seed']}_{case['class']}"
    path = OUT / "cases" / name / f"{key}.json"
    model_hash = sha(Path(checkpoint)) if checkpoint is not None else None
    if path.exists():
        row = json.loads(path.read_text())
        if row["model_sha256"] != model_hash:
            raise RuntimeError("Cached case belongs to another policy")
        if sha(OUT / row["trace_path"]) != row["trace_sha256"]:
            raise RuntimeError("Trajectory trace changed")
        return row
    model = None
    if checkpoint is not None:
        import torch
        from stable_baselines3 import PPO
        torch.set_num_threads(1)
        model = PPO.load(checkpoint, device="cpu")
    env = RevJTremorEnv(writers=[case["writer"]], episode_s=2.5, settle_s=3.,
                       p_free=1. if case["amp"] == 0 else 0., heel=False, reference_mode="ideal_clean",
                       fixed_params={"inner_hz": 80., "velocity_source": "hall", "contact_source": "measured",
                                     "f0": case["f0"], "amp": case["amp"]})
    env.reset(seed=case["seed"])
    # Enable ordinary read-only simulator recording for the scored writing
    # interval. Its 4kHz trace measures policy displacement independent of reward.
    env.st.rec = np.zeros((env.st.nrec, len(env.st.names)))
    start_energy = env.st.servo.copper_energy_J
    rows = []
    done = False
    obs = env._obs()
    while not done:
        action = np.zeros(3) if model is None else model.predict(obs, deterministic=True)[0]
        obs, _, term, trunc, metrics = env.step(action)
        rows.append(metrics)
        done = term or trunc
    dt = np.asarray([r["duration_s"] for r in rows])
    duration = float(dt.sum())
    integral = lambda k: float(np.dot(dt, [r[k] for r in rows]))
    reference_time = integral("reference_fraction")
    recorded = env.st.result()
    t = recorded["t"]
    ids = np.clip(np.searchsorted(env.ref_t, t, side="right")-1, 0, len(env.ref_t)-1)
    trace = OUT / "traces" / name / f"{key}.npz"
    trace.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(trace, t=t, xy=recorded.ink(), required=env.ref_con[ids] > .5,
                        contact=recorded["contact"] > .5)
    row = {**case, "policy": name, "model_sha256": model_hash,
           "actual_f0_hz": None if env.amp == 0 else env.f0, "duration_s": duration,
           "rms_um": float(np.sqrt(integral("error_sq_m2")/max(reference_time, 1e-30)))*1e6,
           "cost": integral("cost")/duration,
           "missing_fraction": integral("missing_fraction")/duration,
           "extra_fraction": integral("extra_fraction")/duration,
           "coil_power_W": (env.st.servo.copper_energy_J-start_energy)/duration,
           "coil_temperature_C": max(r["coil_temperature_C"] for r in rows),
           "reference_sha256": hashlib.sha256(env.ref_ink.tobytes()+env.ref_con.tobytes()).hexdigest(),
           "trace_path": str(trace.relative_to(OUT)), "trace_sha256": sha(trace)}
    dump(path, row)
    return row


def evaluate(split, name, seed=None):
    checkpoint = str(OUT / "checkpoints" / f"seed_{seed}.zip") if seed is not None else None
    jobs = [(c, name, checkpoint) for c in cases(split)]
    rows = []
    with ProcessPoolExecutor(max_workers=2) as pool:
        for i, row in enumerate(pool.map(evaluate_job, jobs)):
            rows.append(row)
            print(f"{split} {name} {i+1}/{len(jobs)} {row['class']}: {row['rms_um']:.1f}um", flush=True)
    return rows


def clean_displacement(row, baseline):
    a, b = np.load(OUT / row["trace_path"]), np.load(OUT / baseline["trace_path"])
    np.testing.assert_array_equal(a["t"], b["t"])
    np.testing.assert_array_equal(a["required"], b["required"])
    delta = a["xy"][a["required"]] - b["xy"][b["required"]]
    return float(np.sqrt(np.mean(np.sum(delta**2, axis=1))))*1e6


def compare(rows, baseline):
    for r, b in zip(rows, baseline):
        assert (r["writer"], r["seed"], r["class"], r["reference_sha256"]) == (
            b["writer"], b["seed"], b["class"], b["reference_sha256"])
    clean_pairs = [(r, b) for r, b in zip(rows, baseline) if r["class"] == "clean"]
    delta = [clean_displacement(r, b) for r, b in clean_pairs]
    clean_error_delta = [r["rms_um"]-b["rms_um"] for r, b in clean_pairs]
    ratios = lambda g: [r["rms_um"]/max(b["rms_um"], 1e-9) for r, b in zip(rows, baseline) if r["class"] == g]
    large_rows = [r for r in rows if r["class"] == "large"]
    large_ratios = ratios("large")
    writers = sorted({r["writer"] for r in large_rows})
    writer_ratios = [np.mean([v for r, v in zip(large_rows, large_ratios) if r["writer"] == w]) for w in writers]
    rng = np.random.default_rng(993)
    resamples = np.asarray(writer_ratios)[rng.integers(0, len(writers), (5000, len(writers)))].mean(axis=1)
    out = {"clean_delta_mean_um": float(np.mean(delta)), "clean_delta_worst_um": max(delta),
           "clean_error_mean_increase_um": float(np.mean(clean_error_delta)),
           "clean_error_worst_increase_um": max(clean_error_delta),
           "mild_ratio": float(np.mean(ratios("mild"))), "large_ratio": float(np.mean(large_ratios)),
           "large_worst_ratio": max(large_ratios), "large_cluster_ratio_95_upper": float(np.quantile(resamples, .975)),
           "missing_increase": max(r["missing_fraction"]-b["missing_fraction"] for r, b in zip(rows, baseline)),
           "extra_increase": max(r["extra_fraction"]-b["extra_fraction"] for r, b in zip(rows, baseline)),
           "power_ratio": max(r["coil_power_W"]/max(b["coil_power_W"], 1e-9) for r, b in zip(rows, baseline)),
           "temperature_increase_C": max(r["coil_temperature_C"]-b["coil_temperature_C"] for r, b in zip(rows, baseline)),
           "clean_displacement_by_case_um": delta,
           "large_ratio_by_writer": dict(zip(map(str, writers), map(float, writer_ratios)))}
    out["failed_rules"] = [k for k, v in RULE.items() if out[k.removesuffix("_max")] > v]
    out["passes"] = not out["failed_rules"]
    return out


def run():
    import gymnasium, mujoco, scipy, stable_baselines3, torch
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [p for prefix in ("sim2", "sim2j", "handwriting", "aiguide")
             for p in sorted((ROOT / prefix).glob("*.py"))]
    paths += [ROOT / "app/penapp/synth.py", ROOT / "sim/pensim/scenarios.py"]
    protocol = {"version": 1, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "evidence": "SIMULATION with synthetic writers; no hardware or clinical outcomes",
                "seeds": SEEDS, "requested_steps_per_seed": STEPS, "train_writers": [40000, 40799],
                "tune_cases": cases("tune"), "test_cases": cases("test"), "rules": RULE,
                "plant": "RevJ no heel; causalHall300Hz, inner80Hz, measured delayedcontact; fixedbeforethisexperiment",
                "reference": "Common noiseless ideal-clean physical reference; privileged only in scoring",
                "training": {"p_free": .5, "episode_s": 2.5, "settle_s": 3., "n_steps": 1024, "batch_size": 256,
                             "n_epochs": 5, "learning_rate": .0003, "gamma": .98, "gae_lambda": .95,
                             "clip_range": .2, "ent_coef": 0., "log_std_init": -2., "MLP": [64, 64]},
                "reward": "Contact-complete reference tracking /0.3mm, missing/extra ink9, actioncost0.005; 2kHz scoring",
                "selection": "Final checkpoint perseedonly; eligible lowest tuning large ratio; freeze then test only selectedcandidate",
                "no_eligible_candidate": "Retainzero residual and do not consume the fresh test set",
                "clean_gate": "Actual4kHz policy-minus-baseline path RMS on reference-requiredink; separate common-target-error constraints",
                "statistics": "Paired cases and5000 synthetic-writer-cluster resamples, descriptive uncertainty under this generator",
                "workers": {"training": 3, "evaluation": 2},
                "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in paths},
                "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "runtime": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__,
                            "torch": torch.__version__, "mujoco": mujoco.__version__, "gymnasium": gymnasium.__version__,
                            "scipy": scipy.__version__, "stable_baselines3": stable_baselines3.__version__}}
    pp = OUT / "protocol.json"
    if pp.exists():
        old = json.loads(pp.read_text())
        for k in ("seeds", "requested_steps_per_seed", "rules", "source_sha256", "tune_cases", "test_cases"):
            if old[k] != protocol[k]:
                raise RuntimeError("Frozen causal PPO inputs changed; create a new version")
        protocol = old
    else:
        dump(pp, protocol)
    start = time.time()
    with ProcessPoolExecutor(max_workers=3) as pool:
        training = list(pool.map(train_seed, SEEDS))
    base = evaluate("tune", "zero")
    candidates = []
    for seed in SEEDS:
        rows = evaluate("tune", f"seed_{seed}", seed)
        comparison = compare(rows, base)
        dump(OUT / f"tuning_seed_{seed}.json", {"seed": seed, "rows": rows, "comparison": comparison})
        candidates.append({"seed": seed, **comparison})
    eligible = [c for c in candidates if c["passes"]]
    selected = min(eligible, key=lambda c: c["large_ratio"])["seed"] if eligible else None
    frozen = {"seed": selected, "candidates": candidates, "protocol_sha256": sha(pp),
              "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    fp = OUT / "selection_frozen.json"
    if fp.exists():
        assert json.loads(fp.read_text())["seed"] == selected
    else:
        dump(fp, frozen)
    test = None
    if selected is not None:
        test_base = evaluate("test", "zero")
        test_rows = evaluate("test", f"seed_{selected}", selected)
        test = {"baseline": test_base, "selected": test_rows, "comparison": compare(test_rows, test_base)}
        dump(OUT / "test.json", test)
    adopted = bool(test and test["comparison"]["passes"])
    result = {"protocol": protocol, "training": [{k: v for k, v in r.items() if k != "episode_metrics"} for r in training],
              "selection": frozen, "test": test, "actual_total_transitions": sum(r["actual_steps"] for r in training),
              "adopted_for_further_simulation": adopted, "hardware_or_firmware_deployment": False,
              "wall_seconds": time.time()-start,
              "conclusion": "Candidate passes this synthetic screen only" if adopted else
                            "Retainzero residual: no learnedcandidate passed all tuning and independent-test gates"}
    dump(OUT / "results.json", result)
    print(json.dumps({"selected_seed": selected, "adopted_for_further_simulation": adopted,
                      "tuning": candidates}, indent=2), flush=True)


if __name__ == "__main__":
    run()
