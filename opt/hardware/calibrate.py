"""P1 runs of the current stage (Q26) that calibrate and check the drive-power model of opt/hardware/model.py.

For Hall noise 0, 0.3 and 1 um at the nib and the harness grid (4-12 Hz x 0.1/0.3/0.5 mm, neutral and oracle,
seeds 200-201, 5 s), record the rail powers (sim/pencil/power.py conventions) and the per-axis stage motion.
The model takes from these runs only (a) the stage velocity the oracle needs per grid case (design-independent
to first order: the stage cancels the housing tremor) and (b) the writing-induced drive power at zero noise;
the Hall-noise power and the tremor power of any other design are computed, and the noise levels 0.3 and 1 um
are held out to check the model.  Evidence status: SIMULATION (model P1, synthetic signals).
Run: python3 -m opt.hardware.calibrate      (about 2-3 min, one process)
Output: results/opt/p1_power_calibration.json
"""
from __future__ import annotations

import argparse
import os
import time

from . import OUT
from . import p1_harness as H
from sim.pencil import design as D  # noqa: E402
from stabpen import provenance  # noqa: E402

CAL_FILE = os.path.join(OUT, "p1_power_calibration.json")
NOISES = (0.0, 0.3e-6, 1.0e-6)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[200, 201])
    a = ap.parse_args(argv)
    t0 = time.time()
    H.warm()
    runs = {}
    for hn in NOISES:
        rows, el = H.run_grid("Q26", seeds=tuple(a.seeds), modes=("oracle",), cfg_kw={"overrides": {"hall_noise": hn}})
        runs[f"{hn:g}"] = {"rows": rows, "summary": H.summarise(rows, keys=(
            "ratio", "q_sat_frac", "P_rail_classB_mW", "P_rail_recovery_mW", "e_rms_um", "q1_rms_um", "q2_rms_um",
            "q1dot_rms_mm_s", "q2dot_rms_mm_s", "V1_mean", "V2_mean", "V1dot_rms_V_s", "V2dot_rms_V_s")), "elapsed_s": el}
        print(f"hall {hn:g}: {el:.0f} s", flush=True)
    meta = provenance.metadata("simulation (pencil model P1, synthetic handwriting and tremor; nothing measured)",
                               seeds={"test": list(a.seeds)}, p=D.Params().pencil,
                               extra={"script": "opt/hardware/calibrate.py", "stage": "Q26", "duration_s": H.DUR,
                                      "hall_noise_levels_m": list(NOISES), "elapsed_s": round(time.time() - t0, 1)})
    provenance.write_json(CAL_FILE, {"meta": meta, "runs": runs})
    print("wrote", CAL_FILE, round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
