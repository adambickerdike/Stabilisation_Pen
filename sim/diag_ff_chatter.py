#!/usr/bin/env python3
"""Diagnosis of contact chatter found by the Monte Carlo sweep (model M1).

Finding (simulation): with the contact-load feedforward computed from the raw
axial-force signal (1 kHz, 1 ms delay), 3 of 160 Monte Carlo cases (v0.3
parameters, commit bbcf1c7) produced no evaluable ink because the powered pen
bounced on the paper (>1000 contact transitions in 3 s, 1.5-2 ms contact
segments).  Rigid and unpowered pens with the same parameters did not bounce.

Mechanism: the feedforward cancels the transverse component of the paper
reaction, N cos(theta).  Because N follows the stage position through the
transverse-normal coupling (a stage move q along t1 indents the paper by
q cos(theta)), the feedforward acts on the stage as a stiffness
-cos^2(theta) K_n H(s), where K_n is the paper in series with the axial path
and H the force-sensing dynamics.  The physical reaction supplies
+cos^2(theta) K_n instantly.  With H a delay tau, the net force has a
quadrature part equal to a NEGATIVE damper c = -cos^2(theta) K_n sin(w tau)/w
at the stage-against-paper mode (~150-250 Hz), which exceeds the servo's
derivative damping when K_n is large (stiff paper, stiff axial path).

Resolution (DEC-011).  Filtering the feedforward force removes the bounce in
these no-tremor cases (second-order 30-60 Hz is best), but the v0.3 Monte
Carlo re-run with tremor still produced bounce in 6/160 samples (low
altitude, stiff hand and axial path) that disappears only when the
measured-force contact feedforward is removed.  Removing it raised the
neutral servo error from 20 to 29 um RMS and the device distortion from 51
to 59 um on the tuning seeds, left the Kalman results unchanged and slightly
improved the oracle bound.  The feedforward is therefore disabled by default
(Controller.ff_contact = 0); the filtered path remains for bench work.
This script documents the no-tremor part of the diagnosis; the with-tremor
comparison is recorded in results/sim/ff_options.json (sim/diag_ff_options.py).

Outputs results/sim/ff_chatter.json and fig_ff_chatter.png.  Evidence status:
SIMULATION.  Run: python3 sim/diag_ff_chatter.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim.pensim import model, scenarios  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "sim")
# Parameter sets of the three Monte Carlo samples that returned no evaluable
# ink (indices 14, 32, 140 of the v0.3 run) plus an envelope corner.
CASES = {
    "mc32": dict(theta=36.30, N0=0.413, seed=208, ov={
        "hand.grip_stiffness": 625.7, "hand.grip_damping": 1.545, "hand.mass": 0.3274, "hand.arm_stiffness": 99.46,
        "hand.arm_damping": 25.13, "hand.normal_stiffness": 2204.3, "writing.mu_eff": 0.0843,
        "writing.paper_stiffness": 1.205e5, "stage.axial_k": 7754.0, "stage.k_tip": 585.0, "actuator.Kf": 1.067,
        "actuator.R20": 13.33, "sensing.opt_delay": 3.71e-3, "sensing.opt_noise": 4e-6, "sensing.imu_delay": 1.92e-3,
        "sensing.hall_noise_tip": 1.0e-6}),
    "mc140": dict(theta=39.51, N0=0.210, seed=208, ov={
        "hand.grip_stiffness": 341.7, "hand.grip_damping": 2.084, "hand.mass": 0.354, "hand.arm_stiffness": 155.9,
        "hand.arm_damping": 27.06, "hand.normal_stiffness": 1105.5, "writing.mu_eff": 0.277,
        "writing.paper_stiffness": 8.43e4, "stage.axial_k": 8433.0, "stage.k_tip": 238.2, "actuator.Kf": 1.248,
        "actuator.R20": 8.47, "sensing.opt_delay": 4.57e-3, "sensing.opt_noise": 7.5e-6, "sensing.imu_delay": 1.37e-3,
        "sensing.hall_noise_tip": 8.1e-7}),
    "corner_50deg_0p2N": dict(theta=50.0, N0=0.2, seed=200, ov={
        "writing.paper_stiffness": 2.0e5, "stage.axial_k": 1.0e4, "hand.normal_stiffness": 3000.0,
        "stage.k_tip": 50.0, "writing.mu_eff": 0.05}),
    "nominal": dict(theta=50.0, N0=1.0, seed=200, ov={}),
}
FCS = (0.0, 60.0, 30.0, 15.0, 10.0, 5.0)          # first-order corners
FCS2 = (30.0, 40.0, 60.0)                           # second-order Butterworth corners


def transitions(r):
    c = (r["contact"] > 0).astype(int)
    return int(np.sum(np.diff(c) != 0))


def main():
    out = {}
    for name, c in CASES.items():
        sc = scenarios.handwriting(seed=c["seed"], duration=3.0, theta_deg=c["theta"], N0=c["N0"])
        row = {"rigid": transitions(model.run(sc, model.Controller(mode="rigid"), overrides=c["ov"], seed=c["seed"])),
               "unpowered": transitions(model.run(sc, model.Controller(mode="unpowered"), overrides=c["ov"], seed=c["seed"]))}
        for fc in FCS:
            r = model.run(sc, model.Controller(mode="neutral", ff_contact=1.0, ff_contact_fc=fc, ff_contact_order=1), overrides=c["ov"], seed=c["seed"])
            row[f"neutral_fc{fc:g}"] = transitions(r)
        for fc in FCS2:
            r = model.run(sc, model.Controller(mode="neutral", ff_contact=1.0, ff_contact_fc=fc, ff_contact_order=2), overrides=c["ov"], seed=c["seed"])
            row[f"neutral_2nd{fc:g}"] = transitions(r)
        row["neutral_no_ff"] = transitions(model.run(sc, model.Controller(mode="neutral", ff_contact=0.0),
                                                     overrides=c["ov"], seed=c["seed"]))
        out[name] = row
        print(name, row, flush=True)
    # analytic negative-damping estimate at the stage-against-paper mode for mc32
    p = CASES["mc32"]
    th = math.radians(p["theta"])
    kp, kax = p["ov"]["writing.paper_stiffness"], p["ov"]["stage.axial_k"]
    Kn = 1.0 / (1.0 / kp + math.sin(th) ** 2 / kax)
    Kc = math.cos(th) ** 2 * Kn
    m_eq, wc = 0.0103, 2 * math.pi * 60.0
    Kservo = m_eq * wc ** 2
    w = math.sqrt((Kservo + Kc) / m_eq)
    tau = 1.0e-3 + 0.5e-3
    est = {"K_n_N_per_m": Kn, "K_c_cos2_N_per_m": Kc, "mode_Hz": w / (2 * math.pi),
           "servo_damping_Ns_per_m": 2 * 0.7 * m_eq * wc,
           "ff_negative_damping_Ns_per_m": Kc * math.sin(w * tau) / w, "assumed_force_delay_s": tau}
    meta = provenance.metadata("simulation + analytic estimate", seeds={c: CASES[c]["seed"] for c in CASES})
    provenance.write_json(os.path.join(OUT, "ff_chatter.json"), {"meta": meta, "transitions_in_3s": out, "estimate_mc32": est})
    print(json.dumps(est, indent=1))
    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    labels = ["none" if fc == 0 else f"1st {fc:g}" for fc in FCS] + [f"2nd {fc:g}" for fc in FCS2]
    xs = np.arange(len(labels))
    for j, name in enumerate(CASES):
        ys = [max(out[name][f"neutral_fc{fc:g}"], 1) for fc in FCS] + [max(out[name][f"neutral_2nd{fc:g}"], 1) for fc in FCS2]
        ax.plot(xs, ys, color=plotstyle.SERIES[j], label=name)
        ax.plot(xs, ys, **plotstyle.marker_kw(plotstyle.SERIES[j]))
    ax.set_yscale("log")
    ax.set_xticks(xs, labels, fontsize=8)
    ax.set_xlabel("Filter on the contact-feedforward force (order, corner Hz)")
    ax.set_ylabel("Contact transitions in 3 s")
    ax.set_title("Nib bounce vs feedforward filtering (powered neutral pen)", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    plotstyle.stamp(fig, "simulation", "rigid-pen reference: 4-10 transitions in 3 s (pen lifts)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_ff_chatter.png"))


if __name__ == "__main__":
    main()
