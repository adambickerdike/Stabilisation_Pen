#!/usr/bin/env python3
"""Contact-feedforward options under tremor (sim model M1, v0.3 Monte Carlo worst cases).

Evidence status: SIMULATION.  Companion to sim/diag_ff_chatter.py.  Compares,
on the six v0.3 Monte Carlo samples that bounced with 9 Hz / 0.3 mm tremor
and on the tuning seeds: the filtered measured-force contact feedforward
(2nd-order 60, 10, 5 Hz), no contact feedforward, and no feedforward with a
doubled integral corner.  Result used for DEC-011 (feedforward disabled).
Outputs results/sim/ff_options.json.  Run: python3 sim/diag_ff_options.py
"""
import json
import os
import sys

import numpy as np
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import bench, evaluate, harness, model, scenarios  # noqa: E402
from stabpen import provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

WORST = {
 "mc125": {
  "theta": 39.419,
  "N0": 0.67823,
  "seed": 205,
  "ov": {
   "hand.grip_stiffness": 348.174,
   "hand.grip_damping": 3.94386,
   "hand.mass": 0.240339,
   "hand.arm_stiffness": 425.874,
   "hand.arm_damping": 6.60825,
   "hand.normal_stiffness": 2860.22,
   "writing.mu_eff": 0.0816332,
   "writing.paper_stiffness": 17657.1,
   "stage.axial_k": 4933.48,
   "stage.k_tip": 58.9249,
   "actuator.Kf": 0.929626,
   "actuator.R20": 9.53324,
   "sensing.opt_delay": 0.00440109,
   "sensing.opt_noise": 1.20886e-06,
   "sensing.imu_delay": 0.000872181,
   "sensing.hall_noise_tip": 2.15459e-06
  }
 },
 "mc22": {
  "theta": 38.662,
  "N0": 0.65388,
  "seed": 210,
  "ov": {
   "hand.grip_stiffness": 720.249,
   "hand.grip_damping": 0.471785,
   "hand.mass": 0.468541,
   "hand.arm_stiffness": 225.247,
   "hand.arm_damping": 7.17301,
   "hand.normal_stiffness": 2527.02,
   "writing.mu_eff": 0.0965391,
   "writing.paper_stiffness": 180323.0,
   "stage.axial_k": 2802.54,
   "stage.k_tip": 368.36,
   "actuator.Kf": 0.869153,
   "actuator.R20": 14.4144,
   "sensing.opt_delay": 0.00381137,
   "sensing.opt_noise": 4.40232e-06,
   "sensing.imu_delay": 0.00191596,
   "sensing.hall_noise_tip": 8.13978e-07
  }
 },
 "mc32": {
  "theta": 36.298,
  "N0": 0.41327,
  "seed": 208,
  "ov": {
   "hand.grip_stiffness": 625.745,
   "hand.grip_damping": 1.54495,
   "hand.mass": 0.32743,
   "hand.arm_stiffness": 99.4592,
   "hand.arm_damping": 25.1306,
   "hand.normal_stiffness": 2204.34,
   "writing.mu_eff": 0.0843071,
   "writing.paper_stiffness": 120528.0,
   "stage.axial_k": 7754.18,
   "stage.k_tip": 584.997,
   "actuator.Kf": 1.06716,
   "actuator.R20": 13.3279,
   "sensing.opt_delay": 0.00371362,
   "sensing.opt_noise": 3.71662e-06,
   "sensing.imu_delay": 0.00191912,
   "sensing.hall_noise_tip": 1.21614e-06
  }
 },
 "mc123": {
  "theta": 37.534,
  "N0": 0.49268,
  "seed": 203,
  "ov": {
   "hand.grip_stiffness": 297.12,
   "hand.grip_damping": 2.4162,
   "hand.mass": 0.149793,
   "hand.arm_stiffness": 90.6972,
   "hand.arm_damping": 9.72464,
   "hand.normal_stiffness": 2434.57,
   "writing.mu_eff": 0.313176,
   "writing.paper_stiffness": 148473.0,
   "stage.axial_k": 9597.47,
   "stage.k_tip": 178.179,
   "actuator.Kf": 0.835168,
   "actuator.R20": 12.3503,
   "sensing.opt_delay": 0.00378509,
   "sensing.opt_noise": 3.03534e-06,
   "sensing.imu_delay": 0.000899332,
   "sensing.hall_noise_tip": 5.30769e-07
  }
 },
 "mc116": {
  "theta": 35.906,
  "N0": 0.60395,
  "seed": 208,
  "ov": {
   "hand.grip_stiffness": 687.628,
   "hand.grip_damping": 2.85159,
   "hand.mass": 0.243865,
   "hand.arm_stiffness": 116.753,
   "hand.arm_damping": 12.9365,
   "hand.normal_stiffness": 2149.59,
   "writing.mu_eff": 0.0821142,
   "writing.paper_stiffness": 125695.0,
   "stage.axial_k": 5150.02,
   "stage.k_tip": 56.0594,
   "actuator.Kf": 1.14749,
   "actuator.R20": 13.5325,
   "sensing.opt_delay": 0.00150501,
   "sensing.opt_noise": 3.35095e-06,
   "sensing.imu_delay": 0.00147191,
   "sensing.hall_noise_tip": 6.49541e-07
  }
 },
 "mc14": {
  "theta": 38.102,
  "N0": 0.39877,
  "seed": 202,
  "ov": {
   "hand.grip_stiffness": 318.168,
   "hand.grip_damping": 0.589466,
   "hand.mass": 0.111582,
   "hand.arm_stiffness": 167.321,
   "hand.arm_damping": 4.35868,
   "hand.normal_stiffness": 1535.72,
   "writing.mu_eff": 0.223716,
   "writing.paper_stiffness": 98383.3,
   "stage.axial_k": 740.47,
   "stage.k_tip": 69.6184,
   "actuator.Kf": 0.778411,
   "actuator.R20": 8.6501,
   "sensing.opt_delay": 0.00462557,
   "sensing.opt_noise": 1.85885e-06,
   "sensing.imu_delay": 0.000820898,
   "sensing.hall_noise_tip": 2.04134e-06
  }
 }
}
sel = json.load(open(os.path.join(ROOT, "results", "sim", "estimator_selection.json")))["results"]
KB = sel["kfosc"]["selected"]["params"]; KA = sel["kfosc"]["selected_assertive"]["params"]
OPTS = {"ff_2nd60": {"ff_contact": 1.0, "ff_contact_fc": 60.0}, "ff_off": {"ff_contact": 0.0},
        "ff_2nd10": {"ff_contact": 1.0, "ff_contact_fc": 10.0}, "ff_2nd5": {"ff_contact": 1.0, "ff_contact_fc": 5.0},
        "ff_off_ki04": {"ff_contact": 0.0, "ki_ratio": 0.4}}


def trans(r):
    c = (r["contact"] > 0).astype(int)
    return int(np.sum(np.diff(c) != 0))


def worst(args):
    name, cn = args
    c = WORST[cn]
    sc = scenarios.handwriting(seed=c["seed"], duration=5.0, tremor=sg.TremorSpec(f0=9.0, amp_pk=3e-4), theta_deg=c["theta"], N0=c["N0"])
    return name, cn, trans(model.run(sc, model.Controller(mode="neutral", **OPTS[name]), overrides=c["ov"], seed=c["seed"]))


def perf(args):
    name, seed = args
    kw = OPTS[name]
    sc0 = scenarios.handwriting(seed=seed, duration=6.0)
    sc1 = scenarios.handwriting(seed=seed, duration=6.0, tremor=sg.TremorSpec(f0=9.0, amp_pk=3e-4))
    rs = model.run(sc0, model.Controller(mode="neutral", **kw), seed=seed)
    rr = model.run(sc0, model.Controller(mode="rigid"), seed=seed)
    dd = bench.device_distortion(rs, rr)["detrended_rms_um"]
    q = rs.xy("q1"); qr = rs.xy("qr1"); con = rs["contact"] > 0
    se = float(np.sqrt(np.mean(np.sum((q - qr)[con] ** 2, axis=1))) * 1e6)
    dist, rn = bench.housing_disturbance(sc1, rs, seed=seed)
    base = evaluate.compare(rn, rs)["e_rms_um"]
    ro = evaluate.compare(model.run(bench.with_disturbance(sc1, dist), model.Controller(mode="oracle", **kw), seed=seed), rs)["e_rms_um"] / base
    out = {"servo_err_um": se, "device_distortion_um": dd, "oracle_ratio_9Hz": ro}
    for tag, kp in (("kf_bal", KB), ("kf_asr", KA)):
        rc = model.run(sc0, model.Controller(mode="kfosc", **kw, **kp), seed=seed)
        out[f"{tag}_distortion_um"] = evaluate.compare(rc, rs)["e_rms_um"]
        r1 = model.run(sc1, model.Controller(mode="kfosc", **kw, **kp), seed=seed)
        out[f"{tag}_ratio_9Hz"] = evaluate.compare(r1, rs)["e_rms_um"] / base
    return name, seed, out

def main():
    with ProcessPoolExecutor(3) as ex:
        W = {}
        for name, cn, n in ex.map(worst, [(o, c) for o in OPTS for c in WORST]):
            W.setdefault(name, {})[cn] = n
        agg = {}
        for name, seed, out in ex.map(perf, [(o, s) for o in OPTS for s in harness.TUNING_SEEDS]):
            agg.setdefault(name, []).append(out)
    perf_mean = {o: {k: float(np.mean([r[k] for r in rows])) for k in rows[0]} for o, rows in agg.items()}
    meta = provenance.metadata("simulation", seeds={"tuning": list(harness.TUNING_SEEDS)})
    provenance.write_json(os.path.join(ROOT, "results", "sim", "ff_options.json"),
                          {"meta": meta, "worst_case_transitions_in_5s": W, "tuning_seed_means": perf_mean,
                           "rigid_pen_transitions_in_5s_reference": "4-18 (pen lifts only)"})
    for o in OPTS:
        print(o, W[o], {k: round(v, 3) for k, v in perf_mean[o].items()})


if __name__ == "__main__":
    main()
