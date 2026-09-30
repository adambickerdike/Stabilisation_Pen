"""Fresh synthetic, physically closed-loop PPO audit with a frozen selection rule.

python -m sim2j.rl_integrity_study --steps 16384 --seeds 0 1 2
Outputs are NEW under results/improvement/control; historical studies are intact.
No patient/legibility claim. Zero action is the identical plant's guarded model
controller. Three independent training seeds are retained, including failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np

from .rl import RevJTremorEnv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/improvement/control"
BUILD = ROOT / "sim2j/build/rl_integrity"
RULE = {
    "clean_mean_um_max": 25.0,
    "clean_worst_um_max": 50.0,
    "mild_ratio_max": 1.02,
    "severe_ratio_max": 0.98,
    "missing_ink_increase_max": 0.005,
    "extra_ink_increase_max": 0.005,
    "coil_power_ratio_max": 1.05,
}


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def code_hashes():
    paths = ["sim2j/rl_integrity_study.py", "sim2j/rl.py", "sim2/reward.py", "sim2j/sensing.py",
             "sim2j/firmware.py", "sim2j/stepper.py", "sim2/sim.py", "sim2/plugins.py"]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def cases(split):
    # New writer IDs/seeds, outside every legacy train/tune/test set. Distinct
    # scenarios are an engineering stress sample, not independent clinical data.
    writers = [31001, 31002] if split == "tune" else [32001, 32002, 32003]
    first_seed = 81000 if split == "tune" else 82000
    return [{"writer": w, "seed": first_seed + wi * 19 + fi,
             "f0": f, "amp": amp, "class": label}
            for wi, w in enumerate(writers) for fi, f in enumerate([5.0, 9.0])
            for amp, label in [(0.0, "clean"), (0.3e-3, "mild"), (1.72e-3, "severe")]]


def evaluate_case(case, model=None, velocity_source="legacy_true", inner_hz=400.0):
    env = RevJTremorEnv(writers=[case["writer"]], episode_s=2.5, settle_s=3.0,
                       p_free=1.0 if case["amp"] == 0 else 0.0, heel=False,
                       reference_mode="matched_clean", respect_fixed_frequency=False,
                       fixed_params={"amp": case["amp"], "f0": case["f0"], "velocity_source": velocity_source,
                                     "inner_hz": inner_hz, "contact_source": "legacy_force"})
    obs, info = env.reset(seed=case["seed"])
    rows = []
    done = False
    while not done:
        action = np.zeros(3) if model is None else model.predict(obs, deterministic=True)[0]
        obs, reward, term, trunc, metrics = env.step(action)
        rows.append(metrics)
        done = term or trunc
    dt = np.array([r["duration_s"] for r in rows])
    duration = float(dt.sum())
    total = lambda key: float(np.dot(dt, [r[key] for r in rows]))
    ref_time = total("reference_fraction")
    return {**case, "actual_f0_hz": None if env.amp == 0 else env.f0,
            "velocity_source": velocity_source, "hall_stale_or_warmup_ticks": env.st.servo.hall_stale_ticks,
            "duration_s": duration, "reference_ink_s": ref_time,
            "rms_um": float(np.sqrt(total("error_sq_m2") / max(ref_time, 1e-30))) * 1e6,
            "cost": total("cost") / duration,
            "missing_fraction": total("missing_fraction") / duration,
            "extra_fraction": total("extra_fraction") / duration,
            "coil_power_W": total("coil_power_W") / duration,
            "coil_temperature_C": max(r["coil_temperature_C"] for r in rows)}


def evaluate(split, model=None, name="zero"):
    result = []
    for i, c in enumerate(cases(split)):
        row = evaluate_case(c, model)
        result.append(row)
        print(f"{split} {name} {i + 1}/{len(cases(split))} {c['class']}: {row['rms_um']:.1f} um", flush=True)
    return result


def compare(rows, baseline):
    clean = [r for r in rows if r["class"] == "clean"]
    ratio = lambda group: float(np.mean([r["rms_um"] / max(b["rms_um"], 1e-6)
                                        for r, b in zip(rows, baseline) if r["class"] == group]))
    out = {"clean_mean_um": float(np.mean([r["rms_um"] for r in clean])),
           "clean_worst_um": max(r["rms_um"] for r in clean),
           "mild_ratio": ratio("mild"), "severe_ratio": ratio("severe"),
           "missing_ink_increase": max(r["missing_fraction"] - b["missing_fraction"] for r, b in zip(rows, baseline)),
           "extra_ink_increase": max(r["extra_fraction"] - b["extra_fraction"] for r, b in zip(rows, baseline)),
           "coil_power_ratio": max(r["coil_power_W"] / max(b["coil_power_W"], 1e-9) for r, b in zip(rows, baseline))}
    out["passes"] = all(out[k.removesuffix("_max")] <= v for k, v in RULE.items())
    return out


def run(steps, seeds):
    import gymnasium
    import mujoco
    import scipy
    import stable_baselines3
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    plan = {"evidence": "SIM: fresh synthetic writers and tremor; no hardware or clinical evidence",
            "protocol_version": 2, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "requested_steps_per_seed": steps, "seeds": seeds, "train_writers": [20000, 20399],
            "tune_cases": cases("tune"), "test_cases": cases("test"), "rule": RULE,
            "selection": "Eligible final policy with lowest tuning severe RMS ratio; otherwise zero residual. "
                         "Evaluate selected policy on test only after freeze; retain every seed's tuning failure.",
            "p_free": 0.5, "plant": "Rev J no heel, legacy true-velocity optimistic servo, matched DR; not Rev K",
            "reward": "reference-tick contact-complete tracking, scale0.3mm, missing/extra9; action cost0.005",
            "budget": "Three final checkpoints only; no test-driven hyperparameter search",
            "hashes": code_hashes(),
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                        "numpy": np.__version__, "torch": torch.__version__, "scipy": scipy.__version__,
                        "gymnasium": gymnasium.__version__, "mujoco": mujoco.__version__,
                        "stable_baselines3": stable_baselines3.__version__}}
    path = OUT / "rl_protocol.json"
    if path.exists():
        previous = json.loads(path.read_text())
        for key in ("requested_steps_per_seed", "seeds", "rule", "hashes"):
            if previous[key] != plan[key]:
                raise RuntimeError("protocol exists with different inputs; choose a new study directory")
        plan = previous
    else:
        dump(path, plan)  # written before training or evaluation
    policies = []
    all_start = time.time()
    for seed in seeds:
        checkpoint = BUILD / f"seed_{seed}.zip"
        compute_path = OUT / f"training_seed_{seed}.json"
        if checkpoint.exists() and compute_path.exists():
            model = PPO.load(checkpoint, device="cpu")
            record = json.loads(compute_path.read_text())
        else:
            env = RevJTremorEnv(seed=seed + 70000, writers=range(20000, 20400), episode_s=2.5,
                               settle_s=3.0, p_free=0.5, heel=False, reference_mode="matched_clean",
                               fixed_params={"velocity_source": "legacy_true", "inner_hz": 400.0,
                                             "contact_source": "legacy_force"})
            model = PPO("MlpPolicy", env, n_steps=1024, batch_size=256, n_epochs=5, learning_rate=3e-4,
                        gamma=0.98, gae_lambda=0.95, clip_range=0.2, ent_coef=0.0,
                        policy_kwargs={"net_arch": [64, 64], "activation_fn": torch.nn.Tanh,
                                       "log_std_init": -2.0}, seed=seed, device="cpu", verbose=0)
            start = time.time()
            print(f"training seed {seed}, requested steps {steps}", flush=True)
            model.learn(total_timesteps=steps)
            model.save(checkpoint)
            record = {"seed": seed, "actual_steps": int(model.num_timesteps), "requested_steps": steps,
                      "wall_seconds": time.time() - start, "episodes": env.stats["episodes"],
                      "episode_metrics": env.ep_log,
                      "model_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest()}
            dump(compute_path, record)
        policies.append((seed, model, record))
    baseline_path = OUT / "rl_tune_zero.json"
    if baseline_path.exists():
        base = json.loads(baseline_path.read_text())
    else:
        base = evaluate("tune")
        dump(baseline_path, base)
    candidates = []
    for seed, model, record in policies:
        tune_path = OUT / f"rl_tune_seed_{seed}.json"
        if tune_path.exists():
            rows = json.loads(tune_path.read_text())["rows"]
        else:
            rows = evaluate("tune", model, f"PPO seed{seed}")
        summary = compare(rows, base)
        dump(tune_path, {"rows": rows, "comparison": summary, "seed": seed})
        candidates.append({"seed": seed, **summary})
    eligible = [c for c in candidates if c["passes"]]
    chosen = min(eligible, key=lambda c: c["severe_ratio"])["seed"] if eligible else None
    frozen = {"seed": chosen, "selected": "zero residual (G4)" if chosen is None else "PPO",
              "candidates": candidates, "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "protocol_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    freeze_path = OUT / "rl_frozen.json"
    if freeze_path.exists():
        assert json.loads(freeze_path.read_text())["seed"] == chosen
    else:
        dump(freeze_path, frozen)
    test_path = OUT / "rl_test.json"
    if test_path.exists():
        test = json.loads(test_path.read_text())
    else:
        base_test = evaluate("test")
        model = next((m for s, m, _ in policies if s == chosen), None)
        selected = base_test if model is None else evaluate("test", model, f"selected seed{chosen}")
        test = {"baseline": base_test, "selected": selected, "comparison": compare(selected, base_test),
                "selected_policy": frozen["selected"], "selected_seed": chosen}
        dump(test_path, test)
    result = {"protocol": plan, "training": [{k: v for k, v in rec.items() if k != "episode_metrics"}
                                             for _, _, rec in policies],
              "selection": frozen, "test": test, "wall_this_invocation_seconds": time.time() - all_start,
              "conclusion": "No learned policy adopted: tuning or independent test failed" if chosen is None or not test["comparison"]["passes"] else
                            "Selected learned policy is synthetic evidence only; hardware and human validation pending"}
    dump(OUT / "rl_integrity_results.json", result)
    print(json.dumps({"selected": frozen["selected"], "candidates": candidates}, indent=2), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=16384)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    p.add_argument("--out", type=Path, help="New study directory; existing frozen outputs are never overwritten")
    args = p.parse_args()
    if args.out is not None:
        OUT = args.out.resolve()
        BUILD = OUT / "research_checkpoints"
    run(args.steps, args.seeds)
