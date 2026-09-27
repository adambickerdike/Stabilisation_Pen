#!/usr/bin/env python3
"""Post-process the ngspice drive-stage transient (drive_stage.cir).

Run:  ngspice -b drive_stage.cir && python3 plot_drive_stage.py
Writes results/electronics/spice_drive_stage.json, fig_spice_drive_stage.png and
a decimated CSV (the full ngspice output, ~10 MB, is not tracked).
Evidence status: SIMULATION of a proposed circuit with idealised switches.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from stabpen import plotstyle, provenance  # noqa: E402

OUT = os.path.join(ROOT, "results", "electronics")


def main():
    d = np.genfromtxt(os.path.join(HERE, "drive_stage_out.csv"), names=True)
    t = d["time"]
    meas = {}
    for line in open(os.path.join(HERE, "drive_stage_meas.txt")):
        if "=" in line:
            k, v = line.split("=")
            meas[k.strip()] = float(v.split()[0])
    T = 1 / 40e3
    ss = (t > 0.8e-3) & (t < 1.0e-3)
    # centre-of-on-time samples (what the SAADC sees) vs true average
    centres = np.arange(0.8e-3 + T / 2, 1.0e-3, T)
    i_c = np.interp(centres, t, d["i_coil"])
    v_c = np.interp(centres, t, d["visns"] if "visns" in d.dtype.names else d["v_isns_"]) if False else None
    names = d.dtype.names
    col = {n: n for n in names}
    isns = d[[n for n in names if n.startswith("visns") and "raw" not in n][0]]
    ocn = d[[n for n in names if n.startswith("voc_n")][0]]
    en = d[[n for n in names if n.startswith("ven")][0]]
    v_c = np.interp(centres, t, isns)
    summary = {
        "i_coil_avg_A": meas["i_avg"], "ripple_pp_mA": (meas["i_max"] - meas["i_min"]) * 1e3,
        "centre_sample_current_A": float(np.mean(i_c)),
        "centre_sample_error_mA": float((np.mean(i_c) - meas["i_avg"]) * 1e3),
        "isns_centre_mean_V": float(np.mean(v_c)), "isns_implied_A": float(np.mean(v_c) - 1.25),
        "fault_detect_us": (meas["t_trip"] - 1.2e-3) * 1e6, "fault_vmot_off_us": (meas["t_off"] - 1.2e-3) * 1e6,
        "fault_peak_shunt_A": meas["i_peak_fault"], "battery_current_avg_A": meas["ibat_avg"],
        "notes": "ideal switches (Ron 0.21 ohm each), no driver OCP modelled; DRV8212P internal OCP (VERIFY) would clamp the fault peak earlier",
    }
    meta = provenance.metadata("simulation (ngspice 42, idealised device models)")
    provenance.write_json(os.path.join(OUT, "spice_drive_stage.json"), {"meta": meta, "summary": summary, "ngspice_meas": meas})
    # decimated export (steady-state window at full rate, rest thinned)
    keep = ((t > 0.9e-3) & (t < 0.95e-3)) | ((t > 1.19e-3) & (t < 1.3e-3)) | (np.arange(len(t)) % 50 == 0)
    np.savetxt(os.path.join(OUT, "spice_drive_stage_decimated.csv"), np.column_stack([d[n][keep] for n in names]),
               delimiter=",", header=",".join(names), comments="", fmt="%.6e")
    plotstyle.apply()
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13.0, 3.6))
    w = (t > 0.9e-3) & (t < 0.9e-3 + 3 * T)
    axs[0].plot((t[w] - 0.9e-3) * 1e6, d["i_coil"][w] * 1e3, color=plotstyle.SERIES[0], label="coil current")
    cw = centres[(centres > 0.9e-3) & (centres < 0.9e-3 + 3 * T)]
    axs[0].plot((cw - 0.9e-3) * 1e6, np.interp(cw, t, d["i_coil"]) * 1e3, **plotstyle.marker_kw(plotstyle.SERIES[1]))
    axs[0].axhline(meas["i_avg"] * 1e3, color=plotstyle.MUTED, lw=1.0)
    axs[0].set_xlabel("Time (us)"); axs[0].set_ylabel("Coil current (mA)")
    axs[0].set_title("Steady state, 40 kHz, duty 0.72", loc="left", fontsize=10)
    axs[0].text(2, meas["i_avg"] * 1e3 + 4, "average", color=plotstyle.INK2, fontsize=8)
    axs[0].text(2, meas["i_min"] * 1e3 - 2, "dots: centre-of-period ADC samples", color=plotstyle.INK2, fontsize=8)
    f = (t > 1.19e-3) & (t < 1.26e-3)
    axs[1].plot((t[f] - 1.2e-3) * 1e6, d["i_shunt"][f], color=plotstyle.SERIES[0])
    axs[1].set_xlabel("Time from coil short (us)"); axs[1].set_ylabel("Bridge (shunt) current (A)")
    axs[1].set_title("Coil short at t = 0", loc="left", fontsize=10)
    axs[2].plot((t[f] - 1.2e-3) * 1e6, isns[f], color=plotstyle.SERIES[0], label="ISNS (SAADC pin)")
    axs[2].plot((t[f] - 1.2e-3) * 1e6, ocn[f] * 3.0, color=plotstyle.SERIES[1], label="OC_N (scaled to 3 V)")
    axs[2].plot((t[f] - 1.2e-3) * 1e6, en[f] * 3.0, color=plotstyle.SERIES[2], label="ACT_EN (scaled to 3 V)")
    axs[2].axhline(2.048, color=plotstyle.MUTED, lw=1.0)
    axs[2].set_xlabel("Time from coil short (us)"); axs[2].set_ylabel("Voltage (V)")
    axs[2].set_title(f"Trip {summary['fault_detect_us']:.1f} us, VMOT off {summary['fault_vmot_off_us']:.1f} us", loc="left", fontsize=10)
    axs[2].legend(fontsize=7.5, loc="center right")
    plotstyle.stamp(fig, "simulation", "ngspice, idealised switches and behavioural INA241/LMV331/latch; proposed circuit")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_spice_drive_stage.png"))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
