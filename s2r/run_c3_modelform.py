#!/usr/bin/env python3
"""C3: model-form gap. Structurally different truths, identified with M1's structure.

1. Stage (EXP-B05 test build) with physics M1 lacks, each at three excitation levels
   (tip 10 / 30 / 100 um), 3 estimation chirps + 1 held-out chirp per level:
     control (M1 structure), flexure mode at 220 Hz (tip mass 10 %), extra loop delay
     150 us + 20 us release jitter, pivot Coulomb friction 0.3 mN, backlash +-2 um.
   Diagnostics: FRF misfit bands, output-error whiteness on the held-out chirp (after an
   output-error refinement on the estimation chirps), parameter drift across levels, loop
   delay against the design value.
2. Friction memory: generalised Maxwell-slip truth on the EXP-B01/B02 tribometer, identified
   with single-state LuGre (control: LuGre truth). Diagnostics: drift of the pre-sliding
   length across sweep amplitudes, held-out reciprocation R^2 and residual excess.
3. Hand resting on paper: M1 truth with the palm stuck to the paper, linearised as extra
   arm stiffness and damping (ASSUMPTION +500 N/m, +10 N s/m); the twin keeps the EXP-B06
   (free-hand) values. Outcome gap on the B09 cells and a band-resolved neutral-error misfit.

Evidence status: SIMULATION + CALCULATION. The truths are constructed; the point is which
diagnostic catches which missing physics, not the size of any real effect.
Outputs: results/s2r/c3_modelform.json, fig_c3_frf_misfit.png, fig_c3_friction_memory.png
Run: python3 -m s2r.run_c3_modelform [--quick]     (about 6 min, 1-2 processes)
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np

import s2r  # noqa: F401
from s2r import common, exp_b01b02, fastharness, ident, modelform, twin
from s2r import stage_model as sm
from sim.pensim import evaluate, harness, model, scenarios
from stabpen import signals as sg

CASES = {"control (M1 structure)": sm.Extras(),
         "flexure mode 220 Hz": sm.Extras(f2_hz=220.0, zeta2=0.02, mass_ratio2=0.1),
         "extra delay 150 us + 20 us jitter": sm.Extras(tau_extra=150e-6, jitter_rms=20e-6),
         "pivot Coulomb friction 0.3 mN": sm.Extras(coulomb_N=3e-4),
         "backlash +-2 um": sm.Extras(backlash_m=2e-6)}
PALM = {"hand.arm_stiffness": 500.0, "hand.arm_damping": 10.0}     # ASSUMPTION palm stuck to the paper


def stage_part(quick):
    plant = twin.nominal_plant()
    out = {}
    levels = (10e-6, 100e-6) if quick else (10e-6, 30e-6, 100e-6)
    for i, (name, ex) in enumerate(CASES.items()):
        rng = np.random.default_rng(300 + i)
        c = modelform.run_stage_case(plant, ex, rng, levels=levels, n_chirps=2 if quick else 3)
        c["verdict"] = modelform.verdicts(c)
        c["extras"] = vars(ex)
        if name.startswith("flexure"):
            # the analyst's next step after a flagged 160-240 Hz band: refit below it
            rng = np.random.default_rng(399)
            c2 = modelform.run_stage_case(plant, ex, rng, levels=levels, n_chirps=2 if quick else 3,
                                          fit_band=(2.0, 120.0))
            c2["verdict"] = modelform.verdicts(c2)
            c["refit_2_120Hz"] = c2
        out[name] = c
        print(name, c["verdict"], flush=True)
    return out, plant


def friction_part(quick):
    nominal = twin.nominal_plant()
    out = {}
    for label, cls in (("control (LuGre truth)", exp_b01b02.Contact), ("friction memory (Maxwell-slip truth)",
                                                                         exp_b01b02.ContactMS)):
        rng = np.random.default_rng(77)
        c = exp_b01b02.Contact.from_truth(nominal)
        if cls is exp_b01b02.ContactMS:
            c = exp_b01b02.ContactMS(**vars(c))
        session = exp_b01b02.draw_rig_session(rng)
        ds = {"_hidden": {}, "indent": exp_b01b02.ds_indentation(c, rng, session),
              "sliding": exp_b01b02.ds_sliding(c, rng, session, Ns=(1.0,) if quick else (0.2, 0.5, 1.0, 2.0, 4.0)),
              "steps": exp_b01b02.ds_steps(c, rng, session, Ns=(1.0,), thetas=(50.0,), dirs_deg=(0, 180)),
              "sweeps": exp_b01b02.ds_sweeps(c, rng, session, amps=(5e-6, 20e-6, 50e-6, 200e-6, 1e-3)),
              "recip": exp_b01b02.ds_recip(c, rng, session, n_rec=12 if quick else 32)}
        r = exp_b01b02.identify(ds, rng, n_boot=20)
        # drift of the pre-sliding length with sweep amplitude
        per_amp = {}
        for rec in ds["sweeps"]["records"]:
            xs = [x[0] for x in exp_b01b02.reversal_fit(rec, rec["theta"])]
            if xs:
                per_amp[f"{rec['A'] * 1e6:.0f}um"] = {"x_pre_um": float(np.median(xs)) * 1e6,
                                                     "u_um": float(np.std(xs) / math.sqrt(len(xs))) * 1e6 + 0.01,
                                                     "n": len(xs)}
        vals = np.array([v["x_pre_um"] for v in per_amp.values()])
        us = np.array([v["u_um"] for v in per_amp.values()])
        drift = ident.drift_test(vals, us) if len(vals) > 1 else None
        # held-out reciprocation residual: small-amplitude records (tremor scale) separately
        small, large = [], []
        for rec in ds["recip"]["records"]:
            r2v, fp = exp_b01b02.predict_recip(rec, r["contact_model"], rec["theta"])
            f_h, _, _ = exp_b01b02.to_page(rec, rec["theta"])
            m = rec["t"] > 0.3
            nr = float(np.sqrt(np.mean((f_h[m] - fp[m]) ** 2)) / (r["contact_model"].mu_k * rec["N_set"]))
            (small if rec["A"] <= 5e-5 else large).append(nr)
        out[label] = {"estimates": r["estimates"], "diag": r["diag"], "x_pre_by_sweep_amplitude": per_amp,
                      "x_pre_drift": drift,
                      "recip_nrmse_small_amp_median": float(np.median(small)) if small else None,
                      "recip_nrmse_large_amp_median": float(np.median(large)) if large else None,
                      "truth": vars(c)}
        # reversal curve for the figure: 200 um sweep
        rec = [x for x in ds["sweeps"]["records"] if abs(x["A"] - 200e-6) < 1e-9][0]
        f_h, _, N = exp_b01b02.to_page(rec, rec["theta"])
        out[label]["_curve"] = {"x_um": (rec["x_cap"][::20] * 1e6).tolist(),
                                "f_over_N": (np.interp(rec["t_cap"][::20], rec["t"], f_h / np.maximum(N, 1e-6))).tolist()}
        print(label, "x_pre by amplitude", {k: round(v["x_pre_um"], 2) for k, v in per_amp.items()},
              "drift p", None if drift is None else round(drift["p"], 4), "R2", round(r["diag"]["recip_R2_pooled"], 4),
              flush=True)
    return out


def neutral_band_error(ov, seeds, f0, bands=((1, 3), (3, 6), (6, 10), (10, 15), (15, 30))):
    rows = []
    for s in seeds:
        sc0 = fastharness.scenario(s)
        sc1 = fastharness.scenario(s, f0=f0, amp=3e-4)
        rs = model.run(sc0, model.Controller(mode="neutral"), overrides=ov, seed=s)
        rn = model.run(sc1, model.Controller(mode="neutral"), overrides=ov, seed=s)
        msk, fs = evaluate._mask(rn, rs, 0.5, 0.03)
        n = min(len(rn["t"]), len(rs["t"]))
        e = rn.xy("tipx")[:n] - rs.xy("tipx")[:n]
        rows.append([evaluate.rms2(evaluate.band(e, fs, lo, hi), msk[:n]) * 1e6 for lo, hi in bands])
    return {f"{lo}-{hi}Hz": float(v) for (lo, hi), v in zip(bands, np.mean(rows, axis=0))}


def hand_part(quick, workers):
    seeds = harness.TEST_SEEDS[:2] if quick else harness.TEST_SEEDS
    nominal = twin.nominal_plant()
    truth = dict(nominal)
    truth["hand.arm_stiffness"] = nominal["hand.arm_stiffness"] + PALM["hand.arm_stiffness"]
    truth["hand.arm_damping"] = nominal["hand.arm_damping"] + PALM["hand.arm_damping"]
    tw = twin.evaluate_plant(nominal, seeds=seeds, workers=workers, device=False)
    tr_ = twin.evaluate_plant(truth, seeds=seeds, workers=workers, device=False)
    keys = [k for k in tw if not k.startswith("_")]
    bands = {}
    for f0 in (6.0, 9.0):
        bt = neutral_band_error(twin.shim(truth)[0], seeds[:4], f0)
        bw = neutral_band_error(twin.shim(nominal)[0], seeds[:4], f0)
        bands[f"{f0:g}Hz"] = {"truth_um": bt, "twin_um": bw, "ratio_truth_over_twin": {k: bt[k] / bw[k] for k in bt}}
    return {"palm_assumption": PALM, "twin": {k: tw[k] for k in keys}, "truth": {k: tr_[k] for k in keys},
            "gap": {k: tw[k] - tr_[k] for k in keys}, "neutral_error_bands": bands, "seeds": list(seeds)}


def plot(stage, fric):
    from stabpen import plotstyle
    fig, axs = common.figure(1, 3, figsize=(14.0, 4.0))
    ax = axs[0]
    for j, name in enumerate(["control (M1 structure)", "flexure mode 220 Hz", "pivot Coulomb friction 0.3 mN",
                              "backlash +-2 um"]):
        lv = stage[name]["levels"][len(stage[name]["levels"]) // 2]
        xs = [0.5 * (b["band_hz"][0] + b["band_hz"][1]) for b in lv["band_misfit"]]
        ys = [max(b["chi2_per_dof"], 1e-2) for b in lv["band_misfit"]]
        ax.plot(xs, ys, "-o", ms=4, color=plotstyle.SERIES[j], label=name)
    ax.axhline(4.0, color=plotstyle.MUTED, lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("band centre (Hz)")
    ax.set_ylabel("normalised FRF misfit (1 = noise level)")
    ax.set_title("FRF misfit bands (30 um level)", loc="left", fontsize=10)
    ax.legend(fontsize=7)
    ax = axs[1]
    for j, name in enumerate(CASES):
        lv = stage[name]["levels"]
        ax.plot([x["q_target_um"] for x in lv], [x["zeta"] / lv[-1]["zeta"] for x in lv], "-o", ms=4,
                color=plotstyle.SERIES[j], label=name)
    ax.set_xscale("log")
    ax.set_xlabel("excitation level (um at the tip)")
    ax.set_ylabel("identified zeta / zeta at 100 um")
    ax.set_title("Parameter drift across excitation levels", loc="left", fontsize=10)
    ax.set_ylim(0.9, 1.6)
    ax = axs[2]
    for j, (label, v) in enumerate(fric.items()):
        c = v["_curve"]
        ax.plot(c["x_um"], c["f_over_N"], lw=1.0, color=plotstyle.SERIES[j], label=label)
    ax.set_xlabel("platen displacement (um)")
    ax.set_ylabel("friction / N")
    ax.set_title("Pre-sliding loops, 200 um sweep", loc="left", fontsize=10)
    ax.legend(fontsize=7)
    common.save_figure(fig, "fig_c3_model_form", "simulation",
                       "constructed truths identified with M1 structure; diagnostics only, no physical effect sizes claimed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    stage, plant = stage_part(a.quick)
    fric = friction_part(a.quick)
    hand = hand_part(a.quick, a.workers)
    plot(stage, fric)
    for v in fric.values():
        v.pop("_curve", None)
    payload = {"stage": stage, "friction_memory": fric, "hand_on_paper": hand, "elapsed_s": time.time() - t0,
               "thresholds_proposed": {"frf_band_chi2": 4.0, "oe_excess_over_sensor_noise": 1.3,
                                       "ljung_box_p": 0.01, "drift_p": 0.01, "loop_delay_tol_us": 25.0}}
    path = common.write_result("c3_modelform", payload, "SIMULATION (constructed structural truths) + CALCULATION",
                               seeds={"stage": [300 + i for i in range(len(CASES))], "friction": 77,
                                      "hand": list(harness.TEST_SEEDS)})
    print(path, f"{time.time() - t0:.0f} s")
    print("hand gap", {k: round(v, 3) for k, v in hand["gap"].items()})


if __name__ == "__main__":
    main()
