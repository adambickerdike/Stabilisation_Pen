#!/usr/bin/env python3
"""C3 part B: piezo hysteresis for the pencil concept (config/pencil.yaml stage.*).

Truth: Bouc-Wen hysteresis (12-14 % major loop, ASSUMPTION) + 1 %/decade creep + bender
mechanics (k_b = block force / free stroke from pencil.yaml) + Hall sensing on the collar.
Identification: Prandtl-Ishlinskii (NNLS) from one 8 s decaying sine sweep read by the
pen's own Hall sensor. Control at 2 kHz: feedforward (identified linear gain or analytic PI
inverse) against closed-loop position sensing (P+I with a notch at the bender resonance,
40 Hz crossover), and their combination. Reference: 0.2 mm nib sine at 4-12 Hz (two thirds
of stage.travel_nib), without load and with a constant 0.1 N transverse nib load (the
0.15 N nib spring at 50 deg, pencil.yaml nib.spring_force).
Metric: RMS nib tracking error in the 3-15 Hz band (zero-phase band-pass, as M-band) and
in total, relative to the reference RMS. Also: the PI inverse applied to a bender with
-20 % free stroke (the declared tolerance) without re-identification.

Evidence status: SIMULATION + CALCULATION; the hysteresis, creep, mass and flexure numbers
are ASSUMPTIONS (AMF-11 gives no hysteresis figure).
Outputs: results/s2r/c3_piezo.json, fig_c3_piezo.png
Run: python3 -m s2r.run_c3_piezo     (about 2 min, 1 process)
"""
from __future__ import annotations

import argparse
import time
from dataclasses import replace

import numpy as np
from scipy.signal import butter, sosfiltfilt

import s2r  # noqa: F401
from s2r import common, piezo

SCHEMES = ["linear_ff", "pi_ff", "fb", "linear_ff+fb", "pi_ff+fb"]
FREQS = (4.0, 6.0, 8.0, 10.0, 12.0)
AMP = 2e-4


def run_case(p, pim, g_lin, rng, f, load=0.0, T=3.0):
    p2 = replace(p, load_nib=load)
    t = np.arange(int(T / piezo.DT)) * piezo.DT
    r = AMP * np.sin(2 * np.pi * f * t)
    sos = butter(4, [3.0, 15.0], btype="band", fs=1 / piezo.DT, output="sos")
    sel = t > 1.0
    out = {}
    for sch in SCHEMES:
        y, u = piezo.track(p2, t, r, sch, pim, rng, lin_gain=g_lin)
        e = y[:, 3] - r
        eb = sosfiltfilt(sos, e)
        rr = float(np.sqrt(np.mean(r[sel] ** 2)))
        out[sch] = {"band_rms_um": float(np.sqrt(np.mean(eb[sel] ** 2)) * 1e6),
                    "band_rel": float(np.sqrt(np.mean(eb[sel] ** 2)) / rr),
                    "total_rms_um": float(np.sqrt(np.mean(e[sel] ** 2)) * 1e6),
                    "mean_um": float(np.mean(e[sel]) * 1e6), "u_peak_V": float(np.max(np.abs(u)))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(42)
    p = piezo.PiezoPlant()
    width = piezo.hysteresis_width(p)
    idr = piezo.identify(p, rng)
    pim, g_lin = idr["model"], idr["linear_gain"]
    # model-form floor: the same fit without sensor noise
    p0 = replace(p, hall_noise=0.0)
    id0 = piezo.identify(p0, np.random.default_rng(0))
    ops = {}
    for n in (4, 8, 16):
        ops[n] = piezo.identify(p, np.random.default_rng(1), n_ops=n)["resid_rms_pi_um"]
    freqs = (4.0, 12.0) if a.quick else FREQS
    res = {"no_load": {}, "load_0.1N": {}, "stroke_-20pct_no_reident": {}}
    for f in freqs:
        res["no_load"][f"{f:g}Hz"] = run_case(p, pim, g_lin, rng, f)
        res["load_0.1N"][f"{f:g}Hz"] = run_case(p, pim, g_lin, rng, f, load=0.1)
        pw = replace(p, free_stroke=0.8 * p.free_stroke)
        res["stroke_-20pct_no_reident"][f"{f:g}Hz"] = run_case(pw, pim, g_lin, rng, f)
        print(f, {k: round(v["band_rel"] * 100, 2) for k, v in res["no_load"][f"{f:g}Hz"].items()}, flush=True)
    payload = {
        "plant": {"free_stroke_m": p.free_stroke, "block_force_N": p.block_force, "k_b_N_per_m": p.k_b,
                  "lever": p.lever, "resonance_hz": piezo.resonance_hz(p), "nib_gain_datasheet_um_per_V": p.nib_gain() * 1e6,
                  "bouc_wen": {"alpha": p.alpha, "beta": p.beta, "gamma": p.gamma},
                  "major_loop_width_rel": width, "creep_per_decade": p.creep_gain,
                  "status": {"free_stroke, block_force, lever, bender_voltage": "config/pencil.yaml (sourced/calculated/assumed as stated there)",
                             "hysteresis, creep, collar mass, flexure, damping, amplifier": "ASSUMPTION",
                             "hall noise, delay": "config/parameters.yaml sensing.hall_*"}},
        "identification": {"record_s": idr["record_s"], "stroke_um": idr["stroke_um"],
                           "resid_rms_pi_um": idr["resid_rms_pi_um"], "resid_rms_linear_um": idr["resid_rms_linear_um"],
                           "resid_rms_pi_noise_free_um": id0["resid_rms_pi_um"],
                           "resid_rms_by_n_ops_um": ops, "linear_gain_um_per_V": g_lin * 1e6,
                           "pi_w0": pim.w0, "pi_thresholds_V": pim.r.tolist(), "pi_weights": pim.w.tolist()},
        "tracking": res, "reference": {"amp_m": AMP, "freqs_hz": list(freqs), "metric": "3-15 Hz band RMS / reference RMS"},
        "elapsed_s": time.time() - t0}
    path = common.write_result("c3_piezo", payload, "SIMULATION + CALCULATION (pencil piezo stage; hysteresis values ASSUMED)",
                               seeds={"rng": 42})
    plot(p, pim, res, freqs)
    print(path, f"{time.time() - t0:.0f} s")


def plot(p, pim, res, freqs):
    from stabpen import plotstyle
    fig, axs = common.figure(1, 3, figsize=(14.0, 4.0))
    t, u = piezo.decaying_sweep(4.0)
    y = piezo.simulate_open(p, u)[:, 3]
    ax = axs[0]
    ax.plot(u[::20], y[::20] * 1e6, color=plotstyle.SERIES[0], lw=1.0, label="truth (Bouc-Wen + creep)")
    ax.plot(u[::20], pim(u)[::20] * 1e6, color=plotstyle.SERIES[1], lw=1.0, ls="--", label="identified PI")
    ax.set_xlabel("drive voltage about mid (V)")
    ax.set_ylabel("nib displacement (um)")
    ax.set_title("Decaying sweep: nested loops", loc="left", fontsize=10)
    ax.legend(fontsize=7.5)
    for ax, case in zip(axs[1:], ("no_load", "load_0.1N")):
        for j, sch in enumerate(SCHEMES):
            ys = [100 * res[case][f"{f:g}Hz"][sch]["band_rel"] for f in freqs]
            ax.plot(freqs, ys, "-o", ms=4, color=plotstyle.SERIES[j], label=sch)
        ax.set_yscale("log")
        ax.set_xlabel("reference frequency (Hz)")
        ax.set_ylabel("3-15 Hz tracking error / reference RMS (%)")
        ax.set_title({"no_load": "Free nib", "load_0.1N": "0.1 N transverse nib load"}[case], loc="left", fontsize=10)
    axs[1].legend(fontsize=7)
    common.save_figure(fig, "fig_c3_piezo", "simulation",
                       "pencil piezo stage; hysteresis 12-14 % and creep 1 %/decade are ASSUMPTIONS; 0.2 mm nib sine")


if __name__ == "__main__":
    main()
