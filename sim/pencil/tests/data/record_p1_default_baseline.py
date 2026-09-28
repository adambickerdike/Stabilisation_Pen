"""Recorder of the pre-change P1 baseline used by sim/pencil/tests/test_default_regression.py.

The fixture p1_default_baseline.{npz,json} was produced by this script at git 410a173, BEFORE the
touchdown feed-forward was added to the simulator core.  It documents how the fixture was made; do not
re-run it with newer code to refresh the fixture (that would defeat the bit-identity check).
Usage (historical): python3 record_p1_default_baseline.py <output path without extension>"""
import hashlib, json, sys, subprocess
sys.path.insert(0, __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', '..', '..', '..')))
import numpy as np
import sim.pencil
from sim.pensim import scenarios
from sim.pencil import model as M
from sim.pencil.layout import NAMES, REC
from stabpen import signals as sg

def cases():
    tr = sg.TremorSpec(f0=6.0, amp_pk=3e-4)
    out = []
    sc0 = scenarios.handwriting(seed=200, duration=2.0)
    out.append(("neutral_tiltrange_s200", sc0, M.Controller(mode="neutral"), M.PencilConfig(), 201))
    out.append(("neutral_adaptive030_s200", sc0, M.Controller(mode="neutral"), M.PencilConfig(overrides={"s_min": -0.3e-3, "s_init": -0.3e-3}), 201))
    out.append(("locked_s200", sc0, M.Controller(mode="neutral"), M.PencilConfig(locked=True), 201))
    s0 = scenarios.handwriting(seed=201, duration=2.0)
    s1 = scenarios.handwriting(seed=201, duration=2.0, tremor=tr)
    ref = M.run(s0, M.Controller(mode="neutral"), M.PencilConfig(), seed=202)
    d = M.housing_disturbance(s1, ref)
    out.append(("oracle_6Hz_s201", M.with_disturbance(s1, d), M.Controller(mode="oracle"), M.PencilConfig(), 202))
    out.append(("kalman_6Hz_s201", s1, M.kalman_controller(), M.PencilConfig(), 202))
    out.append(("external_6Hz_s201", M.with_estimate(s1, 0.5 * np.asarray(s1.dtrue)), M.Controller(mode="external"), M.PencilConfig(), 203))
    out.append(("guided_6Hz_s201", s1, M.Controller(mode="guided"), M.PencilConfig(), 204))
    s35 = scenarios.handwriting(seed=202, duration=2.0, theta_deg=35.0)
    out.append(("neutral_theta35_s202", s35, M.Controller(mode="neutral"), M.PencilConfig(), 205))
    s75 = scenarios.handwriting(seed=203, duration=2.0, theta_deg=75.0, tremor=tr)
    s75c = scenarios.handwriting(seed=203, duration=2.0, theta_deg=75.0)
    ref75 = M.run(s75c, M.Controller(mode="neutral"), M.PencilConfig(), seed=206)
    out.append(("oracle_theta75_s203", M.with_disturbance(s75, M.housing_disturbance(s75, ref75)), M.Controller(mode="oracle"), M.PencilConfig(), 206))
    return out

def main(path):
    rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    arrays = {}
    meta = {"git_revision": rev, "names": list(NAMES), "rec": list(REC), "cases": {}}
    for key, scn, ctrl, cfg, seed in cases():
        r = M.run(scn, ctrl, cfg, seed=seed)
        rec = np.ascontiguousarray(r.rec)
        h = hashlib.sha256(rec.tobytes()).hexdigest()
        arrays[key + "__P"] = r.P.copy()
        arrays[key + "__ink"] = r.ink()[::20].copy()
        meta["cases"][key] = {"sha256_rec": h, "seed": seed, "nrec": int(rec.shape[0])}
        print(key, h[:16], rec.shape)
    np.savez_compressed(path + ".npz", **arrays)
    json.dump(meta, open(path + ".json", "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
