"""Post-hoc numerical sensitivity for the frozen80Hz causal controller.

Cases deliberately include the first clean case, worst tracking and worst
thermal case in the completed45-case study. This is a numerical diagnostic,
not additional unseen performance validation. A common12.5us ideal reference
and identical physical/sensor draws isolate step-size effects.
"""
import hashlib
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
import numpy as np
from sim2j.rl import RevJTremorEnv
from sim2.reward import InkReference

def run_case(case, dt, reference=None):
    env = RevJTremorEnv(writers=[case["writer"]], episode_s=2.5, settle_s=3., dt=dt,
                       p_free=1. if case["amp"] == 0 else 0., heel=False, reference_mode="ideal_clean",
                       fixed_params={"inner_hz": 80., "velocity_source": "hall", "contact_source": "measured",
                                     "f0": case["f0"], "amp": case["amp"]})
    env.reset(seed=case["seed"])
    own_reference = (env.ref_t.copy(), env.ref_ink.copy(), env.ref_con.copy())
    reference = own_reference if reference is None else reference
    env.reference = InkReference(*reference)
    env.st.rec = np.zeros((env.st.nrec, len(env.st.names)))
    energy0 = env.st.servo.copper_energy_J
    rows = []
    done = False
    while not done:
        _, _, term, trunc, info = env.step(np.zeros(3))
        rows.append(info)
        done = term or trunc
    weights = np.array([r["duration_s"] for r in rows])
    total = lambda key: float(np.dot(weights, [r[key] for r in rows]))
    result = env.st.result()
    summary = {"dt_us": dt*1e6, "rms_um": float(np.sqrt(total("error_sq_m2")/total("reference_fraction")))*1e6,
               "missing_fraction": total("missing_fraction")/weights.sum(),
               "extra_fraction": total("extra_fraction")/weights.sum(),
               "coil_power_W": (env.st.servo.copper_energy_J-energy0)/weights.sum(),
               "coil_temperature_C": max(r["coil_temperature_C"] for r in rows)}
    return summary, result["t"], result.ink(), reference


def main():
    old = json.loads((HERE / "causal_controller_results.json").read_text())
    chosen = [old["pairs"][0]["case"], max(old["pairs"], key=lambda p:p["causal80"]["rms_um"])["case"],
              max(old["pairs"], key=lambda p:p["causal80"]["coil_temperature_max_C"])["case"]]
    protocol = {"evidence": "Post-hoc numerical sensitivity, not unseen validation", "cases": chosen,
                "steps_us": [12.5, 25., 50.], "reference": "Same12.5us ideal clean target for all steps in each case",
                "controller": "Frozen80Hz causalHall and measuredcontact; no tuning",
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE / "timestep_protocol.json").write_text(json.dumps(protocol, indent=2)+"\n")
    summaries = []
    for case in chosen:
        fine, t_fine, xy_fine, reference = run_case(case, 12.5e-6)
        ids = np.clip(np.searchsorted(reference[0], t_fine, side="right")-1, 0, len(reference[0])-1)
        required = reference[2][ids] > .5
        fine["trajectory_difference_from12p5us_um"] = 0.
        rows = [fine]
        for dt in [25e-6, 50e-6]:
            result, t, xy, _ = run_case(case, dt, reference)
            interp = np.column_stack([np.interp(t_fine, t, xy[:,i]) for i in range(2)])
            result["trajectory_difference_from12p5us_um"] = float(np.sqrt(np.mean(np.sum((interp[required]-xy_fine[required])**2,axis=1))))*1e6
            rows.append(result)
        summaries.append({"case": case, "results": rows})
        print(case, rows, flush=True)
        (HERE / "timestep_sensitivity.json").write_text(json.dumps({"protocol":protocol,"cases":summaries},indent=2)+"\n")


if __name__ == "__main__":
    main()
