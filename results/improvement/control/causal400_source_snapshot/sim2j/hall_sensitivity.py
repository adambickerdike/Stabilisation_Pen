"""Post-hoc servo sensitivity of the frozen RL candidate, without retraining.

The original untouched test has already rejected the learned policy. Reusing
its cases here diagnoses an observation-model assumption; it is not another
independent test and cannot rehabilitate a failed candidate.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from .rl_integrity_study import ROOT, OUT, evaluate_case, compare, dump


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    frozen = json.loads((OUT / "rl_frozen.json").read_text())
    original = json.loads((OUT / "rl_test.json").read_text())
    checkpoint = OUT / "research_checkpoints" / f"seed_{frozen['seed']}.zip"
    model = PPO.load(checkpoint, device="cpu") if frozen["seed"] is not None else None
    protocol = {
        "evidence": "SIM post-hoc sensitivity, reused synthetic test cases; no new independent validation",
        "version": 1, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_sha256": sha(checkpoint) if model else None,
        "original_protocol_sha256": sha(OUT / "rl_protocol.json"),
        "original_test_sha256": sha(OUT / "rl_test.json"),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for prefix in ("sim2", "sim2j")
                          for p in sorted((ROOT / prefix).glob("*.py"))},
        "change": "True derivative feedback replaced by causal Hall velocity: 300Hz LP, actual acquisition "
                  "intervals, declared Hall noise/delay, 1ms maximum age; no controller or policy retuning",
        "metrics": "Each plant is compared with its own matched clean physical reference; this is not "
                   "absolute page-registration accuracy. Power is sampled once per 4ms policy decision.",
        "thermal_note": "2.5s writing after3s rest; reported winding temperature is not barrel temperature",
        "cases": [{k: r[k] for k in ("writer", "seed", "f0", "amp", "class")} for r in original["baseline"]],
        "nominal_frequency_note": "Env retains a10% random redraw; record actual f0 on each case.",
        "adoption": "No; frozen candidate already failed original independent-test benefit requirement",
    }
    protocol_path = OUT / "hall_sensitivity_protocol.json"
    if protocol_path.exists():
        old = json.loads(protocol_path.read_text())
        for key in ("model_sha256", "original_test_sha256", "source_sha256", "cases"):
            if old[key] != protocol[key]:
                raise RuntimeError("Sensitivity inputs changed; create a distinct version instead of overwriting")
        protocol = old
    else:
        dump(protocol_path, protocol)
    start = time.time()
    result = {}
    for name, policy in (("baseline", None), ("selected", model)):
        path = OUT / f"hall_sensitivity_{name}.json"
        rows = json.loads(path.read_text()) if path.exists() else []
        for i, case in enumerate(protocol["cases"]):
            if i < len(rows):
                continue
            row = evaluate_case(case, policy, velocity_source="hall")
            rows.append(row)
            dump(path, rows)
            print(f"causal Hall {name} {i+1}/18 {case['class']}: {row['rms_um']:.1f}um "
                  f"Pcu={row['coil_power_W']:.3f}W T={row['coil_temperature_C']:.2f}C", flush=True)
        result[name] = rows
    result["comparison"] = compare(result["selected"], result["baseline"])
    result["original_optimistic_comparison"] = original["comparison"]
    result["baseline_sensitivity"] = {
        group: {"old_mean_rms_um": float(np.mean([r["rms_um"] for r in original["baseline"] if r["class"] == group])),
                "causal_mean_rms_um": float(np.mean([r["rms_um"] for r in result["baseline"] if r["class"] == group]))}
        for group in ("clean", "mild", "severe")}
    result["max_coil_temperature_C"] = max(r["coil_temperature_C"] for key in ("baseline", "selected") for r in result[key])
    result["wall_this_invocation_s"] = time.time() - start
    result["protocol"] = protocol
    result["conclusion"] = "No RL adoption. This is an observation-model sensitivity, not an independent test."
    dump(OUT / "hall_sensitivity_results.json", result)
    print(json.dumps(result["comparison"], indent=2), flush=True)


if __name__ == "__main__":
    run()
