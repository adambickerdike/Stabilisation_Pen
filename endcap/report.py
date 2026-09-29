"""Assemble results/endcap/endcap_study.json, the figures (each with a CSV twin), the evidence rows and layout_parts.json.

Reads the stage caches written by endcap/run_study.py.  With quick=True everything goes to results/endcap/_cache/quick/.
Evidence status: SIMULATION and CALCULATION (labels per section).
"""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List

import numpy as np

from stabpen import provenance
from . import params as P

OUT = os.path.join(P.ROOT, "results", "endcap")


def _load(name, quick):
    d = os.path.join(OUT, "_cache", "quick") if quick else os.path.join(OUT, "_cache")
    p = os.path.join(d, f"stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _mean(v):
    v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(v)) if v else float("nan")


# ================================================================================================ tremor aggregation
BANDS = {"8-12Hz_1-2mm": lambda c: c["f0"] >= 8 and c["amp_mm"] >= 0.99 and c["kind"] == "trans",
         "0.3mm_4-12Hz": lambda c: abs(c["amp_mm"] - 0.3) < 1e-6 and c["kind"] == "trans",
         "4-6Hz_all": lambda c: c["f0"] <= 6 and c["kind"] == "trans",
         "all_trans": lambda c: c["kind"] == "trans"}


def tremor_summary(test):
    out = {}
    for name, rows in test["rows"].items():
        key_dev = "nose+dev" if name in ("lrm", "cmg") else "nose+passive"
        out[name] = {}
        for rr in sorted({c["r_rot"] for c in rows}):
            rs = [c for c in rows if c["r_rot"] == rr]
            o = {}
            for band, fn in BANDS.items():
                b = [c for c in rs if fn(c)]
                if not b:
                    continue
                fr = [1 - c[key_dev] / c["nose"] for c in b]
                seeds = sorted({c["seed"] for c in b})
                per_seed = [float(np.mean([1 - c[key_dev] / c["nose"] for c in b if c["seed"] == s])) for s in seeds]
                o[band] = {"nose": _mean([c["nose"] for c in b]), "nose+device": _mean([c[key_dev] for c in b]),
                           "device_alone": _mean([c.get("dev", c.get("dev_passive")) for c in b]),
                           "passive": _mean([c.get("dev_passive") for c in b]),
                           "nose+passive": _mean([c.get("nose+passive") for c in b]),
                           "further_reduction_mean": float(np.mean(fr)), "further_reduction_seed_min": float(min(per_seed)),
                           "further_reduction_seed_max": float(max(per_seed)), "frac_conditions_worse": float(np.mean([x < 0 for x in fr])),
                           "P_act_W_mean": _mean([c.get("P_act_W") for c in b]), "P_act_W_max": float(np.nanmax([c.get("P_act_W", np.nan) for c in b])) if name in ("lrm", "cmg") else None,
                           "n": len(b)}
            out[name][str(rr)] = o
    return out


def device_use(test):
    """How much of its stroke or gimbal range each active device used in the test runs (SIM), and its actuation power."""
    out = {}
    for n, rows in test["rows"].items():
        if n == "lrm":
            pk = [max(c["stroke_pk_mm"]) for c in rows if c.get("stroke_pk_mm")]
            if pk:
                out[n] = {"stroke_peak_mm_median": float(np.median(pk)), "stroke_peak_mm_p95": float(np.percentile(pk, 95)),
                          "stroke_peak_mm_max": float(np.max(pk))}
        elif n == "cmg":
            pk = [max(c["gimbal_pk_rad"]) for c in rows if c.get("gimbal_pk_rad")]
            if pk:
                out[n] = {"gimbal_peak_rad_median": float(np.median(pk)), "gimbal_peak_rad_p95": float(np.percentile(pk, 95)),
                          "gimbal_peak_rad_max": float(np.max(pk))}
        if n in out:
            P_ = [c["P_act_W"] for c in rows if c.get("P_act_W") is not None]
            out[n].update({"P_act_W_mean": float(np.mean(P_)), "P_act_W_max": float(np.max(P_))})
    return out


def rule_RT1(ts, name, P_avg):
    """R-T1 verdict (see run_study.RULES)."""
    try:
        s5 = ts[name]["0.5"]["8-12Hz_1-2mm"]["further_reduction_mean"]
        s3 = ts[name]["0.3"]["8-12Hz_1-2mm"]["further_reduction_mean"]
        s7 = ts[name]["0.7"]["8-12Hz_1-2mm"]["further_reduction_mean"]
        worse = any(ts[name][k]["all_trans"]["further_reduction_mean"] < 0 for k in ("0.3", "0.5", "0.7"))
    except KeyError:
        return {"pass": None, "note": "incomplete grid (quick run)"}
    ok = s5 >= 0.10 and s3 >= 0.05 and s7 >= 0.05 and not worse and P_avg <= P.ENV["p_avg"]
    return {"pass": bool(ok), "r0.3": s3, "r0.5": s5, "r0.7": s7, "any_split_worse_on_average": bool(worse), "P_avg_W": P_avg}


# ================================================================================================ steering aggregation
def steer_summary(steer):
    out = {}
    for dev in sorted({r["device"] for r in steer["rows"]}):
        rows = [r for r in steer["rows"] if r["device"] == dev]
        o = {}
        for scen in ("write", "hold"):
            for rr in sorted({r["r_rot"] for r in rows}):
                for f in sorted({r["f"] for r in rows}):
                    for ax in (0, 1):
                        b = [r for r in rows if r["scenario"] == scen and r["r_rot"] == rr and r["f"] == f and r["axis"] == ax and not r.get("variant")]
                        if b:
                            o[f"{scen}_r{rr}_{f:g}Hz_ax{ax}"] = {"amp_mm": _mean([r["tip_amp_mm"] for r in b]), "peak_mm": _mean([r["tip_peak_mm"] for r in b]),
                                                                  "command": b[0]["command_amp"]}
        for var in ("voluntary", "hand_x2"):
            for f in sorted({r["f"] for r in rows}):
                b = [r for r in rows if r.get("variant") == var and r["f"] == f]
                if b:
                    o[f"write_{var}_r0.5_{f:g}Hz_ax0"] = {"amp_mm": _mean([r["tip_amp_mm"] for r in b]), "peak_mm": _mean([r["tip_peak_mm"] for r in b])}
        pul = [p for p in steer["pulses"] if p["device"] == dev]
        o["pulses"] = [{k: v for k, v in p.items() if not k.startswith("trace")} for p in pul]
        # rule R-S1: largest peak at 1-3 Hz while writing, relaxed hand, over splits and axes (most favourable)
        pk = [v["peak_mm"] for k, v in o.items() if k.startswith("write_r") and any(k.endswith(f"_{f:g}Hz_ax0") or k.endswith(f"_{f:g}Hz_ax1") for f in (1.0, 2.0, 3.0))]
        best = max(pk) if pk else float("nan")
        verdict = "can write" if best >= P.LETTER_RULE["write_mm"] else ("can nudge" if best >= P.LETTER_RULE["nudge_mm"] else "cue at most")
        o["R-S1"] = {"max_peak_1_3Hz_mm": best, "verdict": verdict}
        out[dev] = o
    return out


def gyro_summary(g):
    out = {}
    for name, rows in g["rows"].items():
        o = {}
        for rr in sorted({c["r_rot"] for c in rows}):
            rs = [c for c in rows if c["r_rot"] == rr]
            o[str(rr)] = {"4-12Hz_1mm_passive": _mean([c["dev_passive"] for c in rs if c["kind"] == "trans"]),
                          "4-12Hz_1mm_nose+passive": _mean([c["nose+passive"] for c in rs if c["kind"] == "trans"]),
                          "nose_alone": _mean([c["nose"] for c in rs if c["kind"] == "trans"]),
                          "wrist_8Hz_passive": _mean([c["dev_passive"] for c in rs if c["kind"] == "wrist"]),
                          "by_f": {f"{f:g}Hz": _mean([c["dev_passive"] for c in rs if c["kind"] == "trans" and c["f0"] == f]) for f in sorted({c["f0"] for c in rs})}}
        out[name] = o
    try:
        a = out["pg_design"]["0.5"]["4-12Hz_1mm_passive"]
        b = out["pg_design_nospin"]["0.5"]["4-12Hz_1mm_passive"]
        out["R-G1"] = {"spin_vs_nospin_reduction": 1 - a / b, "useful": bool(1 - a / b >= 0.10)}
    except KeyError:
        pass
    return out


def cue_summary(cue):
    s = cue["sim"]
    base = [r for r in s if r["scenario"] == "write" and not r["nose_cancel"] and r["harmonic"] and r["F0_N"] == 0.5 and r["r_rot"] == 0.5]
    canc = [r for r in s if r["scenario"] == "write" and r["nose_cancel"] and r["harmonic"] and r["F0_N"] == 0.5]
    jit = max([r["ink_jitter_um"] for r in base], default=float("nan"))
    jit_c = max([r["ink_jitter_um"] for r in canc], default=float("nan"))
    return {"jitter_um_0.5N_write": jit, "jitter_um_0.5N_write_nose_cancel": jit_c,
            "R-C1": {"usable_while_writing": bool(jit <= 30.0), "usable_with_nose_cancel": bool(jit_c <= 30.0)}}


# ================================================================================================ figures
def _fig_setup():
    from stabpen import plotstyle as PS
    PS.apply()
    import matplotlib.pyplot as plt
    return PS, plt


def _plain_log(ax, axis="y"):
    """Plain number tick labels on a log axis (no 10^x notation)."""
    import matplotlib.ticker as mt
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:g}"))
    a.set_minor_formatter(mt.NullFormatter())


def _csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def fig_ceiling(sc, opt, outdir):
    PS, plt = _fig_setup()
    f = np.array([1, 2, 3, 5, 8, 10, 12], float)
    rec = {(r["r_rot"], r["f_Hz"]): r for r in sc["receptance"]}
    ch = opt.get("chosen") or {}
    lrm = ch.get("lrm") or [x for x in opt["fronts"]["LRM2_tremor"] if x["cap_g"] == max(opt["caps_g"])][0]
    cmg = ch.get("cmg") or [x for x in opt["fronts"]["CMG_tremor"] if x["cap_g"] == max(opt["caps_g"])][0]
    m_r, X, F_act = lrm["moving_mass_g"] * 1e-3, lrm["X"], lrm["F_act"]
    w = 2 * np.pi * f
    k_c = m_r * (2 * np.pi * 5.0) ** 2                                   # the design's 5 Hz flexure, damping 0.7
    c_c = 1.4 * np.sqrt(k_c * m_r)
    dyn = np.sqrt((k_c - m_r * w * w) ** 2 + (c_c * w) ** 2)
    F_lrm = np.minimum(0.7 * m_r * w * w * X, F_act * m_r * w * w / dyn)   # net force: stroke- or coil-limited
    kx = {"SP2": 2.0, "SP1": 2.0, "DG1": 1.0, "DG2": 2.0, "PL2": 1.0}[cmg["class"]]
    T_cmg = kx * cmg["H"] * np.minimum(P.GIMBAL_DRIVE["rate_max"], 2 * np.pi * f * cmg["x"]["delta"])
    m2 = P.MOTORS["2214BXT"]
    T_rw = np.full_like(f, m2.rated)
    F_need = np.array([1.0 / (rec[(0.5, fi)]["tip_mm_per_N_cap_t1"]) for fi in f])        # N for 1 mm at the tip
    T_need = np.array([1.0 / (rec[(0.5, fi)]["tip_um_per_mNm_t2"] * 1e-3) * 1e-3 for fi in f])  # N m for 1 mm
    fig, ax = plt.subplots(1, 2, figsize=(10, 5.0))
    mk = dict(marker="o", markersize=6, markeredgecolor=PS.SURFACE, markeredgewidth=1.4)
    ax[0].plot(f, F_lrm * 1e3, color=PS.SERIES[0], label=f"reaction mass {lrm['moving_mass_g']:.0f} g, +/-{X * 1e3:.1f} mm", **mk)
    ax[0].plot(f, F_need * 1e3, color=PS.INK2, linestyle="--", linewidth=1.4, label="needed for 1 mm at the tip (r_rot 0.5)")
    ax[0].set_yscale("log"); _plain_log(ax[0]); ax[0].set_xlabel("frequency (Hz)"); ax[0].set_ylabel("force at the end-cap (mN)")
    ax[0].set_title("Force: a mass gives m w^2 X, so little at 1-3 Hz")
    ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1)
    ax[1].plot(f, T_cmg * 1e3, color=PS.SERIES[1], label=f"CMG {cmg['class']}, H {cmg['H'] * 1e3:.1f} mN m s", **mk)
    ax[1].plot(f, T_rw * 1e3, color=PS.SERIES[2], label="reaction wheel, 2214 BXT rated (28.9 g)", **mk)
    ax[1].plot(f, T_need * 1e3, color=PS.INK2, linestyle="--", linewidth=1.4, label="needed for 1 mm at the tip (r_rot 0.5)")
    ax[1].set_yscale("log"); _plain_log(ax[1]); ax[1].set_xlabel("frequency (Hz)"); ax[1].set_ylabel("torque on the pen (mN m)")
    ax[1].set_title("Torque: a CMG gives H x gimbal rate")
    ax[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1)
    PS.stamp(fig, "CALCULATION", "linear Rev H hand-pen model; 45 g designs from the optimiser")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_ek_ceiling.png")); plt.close(fig)
    _csv(os.path.join(outdir, "fig_ek_ceiling.csv"), ["f_Hz", "LRM_force_mN", "force_for_1mm_mN", "CMG_torque_mNm", "RW_torque_mNm", "torque_for_1mm_mNm"],
         [[fi, a * 1e3, b * 1e3, c * 1e3, d * 1e3, e * 1e3] for fi, a, b, c, d, e in zip(f, F_lrm, F_need, T_cmg, T_rw, T_need)])


def fig_pareto(opt, outdir):
    PS, plt = _fig_setup()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.0))
    rows = []
    for i, (cls, lab) in enumerate((("LRM2", "reaction mass (2 axes)"), ("CMG", "CMG (best arrangement)"), ("RW2", "reaction wheels"), ("PG", "passive gyroscope"))):
        for j, which in enumerate(("tremor", "steer")):
            key = f"{cls}_{which}"
            if key not in opt["fronts"]:
                continue
            fr = [dict(x) for x in opt["fronts"][key]]
            for x in fr:                                   # the better of CMA-ES and its autograd refinement (25 and 45 g)
                g = opt.get("gradient", {}).get(f"{key}_{x['cap_g']:.0f}g")
                if g and g["pen"] < 1e-3 and (x["penalty"] >= 1e-3 or g["f"] < x["cma_f"] - 1e-9):
                    x.update({k: g["summary"][k] for k in ("tremor_mean", "steer_3Hz_mm", "mass_g", "P_avg_W", "choice")})
                    x["penalty"] = g["pen"]
            caps = [x["cap_g"] for x in fr]
            ok = [x["penalty"] < 1e-3 for x in fr]
            y = [x["tremor_mean"] if which == "tremor" else x["steer_3Hz_mm"] for x in fr]
            yy = [v if o else np.nan for v, o in zip(y, ok)]
            ax[j].plot(caps, yy, color=PS.SERIES[i], label=lab if any(ok) else f"{lab} (no feasible design)", marker="o", markersize=7,
                       markeredgecolor=PS.SURFACE, markeredgewidth=1.6)
            for c, v, o, x in zip(caps, y, ok, fr):
                rows.append([cls, which, c, v, int(o), x["mass_g"], x["P_avg_W"], "/".join(x["choice"])])
    ax[0].axhline(1.0, color=PS.BASELINE, linewidth=1)
    ax[0].set_xlabel("end-cap mass cap (g)"); ax[0].set_ylabel("tremor left at the handle tip (bound)"); ax[0].set_title("Tremor, 4-12 Hz, 1 mm (lower is better)")
    ax[1].set_xlabel("end-cap mass cap (g)"); ax[1].set_ylabel("tip shift, weakest direction (mm)"); ax[1].set_title("Steering at 3 Hz (higher is better)")
    ax[0].legend(); ax[1].legend()
    PS.stamp(fig, "CALCULATION", "CMA-ES + autograd optima; linear bounds (optimistic); infeasible points omitted")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "fig_ek_pareto.png")); plt.close(fig)
    _csv(os.path.join(outdir, "fig_ek_pareto.csv"), ["class", "objective", "cap_g", "value", "feasible", "mass_g", "P_avg_W", "choice"], rows)


def fig_tremor(ts, outdir):
    PS, plt = _fig_setup()
    names = [n for n in ("lrm", "cmg", "weight_lrm", "weight_cmg") if n in ts]
    labels = {"lrm": "reaction mass (active)", "cmg": "CMG (active)", "weight_lrm": "same mass as the reaction mass, fixed",
              "weight_cmg": "same mass as the CMG, fixed"}
    splits = sorted({k for n in names for k in ts[n]})
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.0))
    rows = []
    w = 0.8 / max(1, len(names))
    for i, n in enumerate(names):
        vals = [ts[n][s]["8-12Hz_1-2mm"]["further_reduction_mean"] * 100 if "8-12Hz_1-2mm" in ts[n][s] else np.nan for s in splits]
        x = np.arange(len(splits)) + (i - (len(names) - 1) / 2) * w
        ax[0].bar(x, vals, width=w * 0.9, color=PS.SERIES[i], label=labels[n])
        for s, v in zip(splits, vals):
            rows.append([n, s, "8-12Hz_1-2mm", v])
        vals2 = [ts[n][s]["4-6Hz_all"]["further_reduction_mean"] * 100 if "4-6Hz_all" in ts[n][s] else np.nan for s in splits]
        ax[1].bar(x, vals2, width=w * 0.9, color=PS.SERIES[i], label=labels[n])
        for s, v in zip(splits, vals2):
            rows.append([n, s, "4-6Hz_all", v])
    for a, t in zip(ax, ("8-12 Hz, 1-2 mm", "4-6 Hz, 0.3-2 mm")):
        a.axhline(0, color=PS.BASELINE, linewidth=1)
        a.set_xticks(range(len(splits))); a.set_xticklabels([f"r_rot {s}" for s in splits])
        a.set_ylabel("further reduction on top of the nose (%)"); a.set_title(t)
    ax[0].axhline(10, color=PS.MUTED, linewidth=0.8, linestyle="--", label="rule R-T1 line, 10 % (r_rot 0.5)")
    h_, l_ = ax[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.03))
    PS.stamp(fig, "SIMULATION", "H1, causal Rev H tracker, test seeds 200-203")
    fig.tight_layout(rect=(0, 0.13, 1, 1)); fig.savefig(os.path.join(outdir, "fig_ek_tremor.png")); plt.close(fig)
    _csv(os.path.join(outdir, "fig_ek_tremor.csv"), ["device", "r_rot", "band", "further_reduction_pct"], rows)


def fig_steer(ss, steer, outdir):
    PS, plt = _fig_setup()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.0))
    rows = []
    fs = sorted({r["f"] for r in steer["rows"]})
    k = 0
    for dev, lab in (("lrm", "reaction mass"), ("cmg", "CMG (tremor design)"), ("cmg_steer", "CMG (steering design)")):
        if dev not in ss:
            continue
        for scen, ls in (("write", "-"), ("hold", "--")):
            y = [ss[dev].get(f"{scen}_r0.5_{f:g}Hz_ax0", {}).get("peak_mm", np.nan) for f in fs]
            if scen == "write":
                ax[0].plot(fs, y, color=PS.SERIES[k], label=f"{lab}, writing", marker="o", markersize=7, markeredgecolor=PS.SURFACE, markeredgewidth=1.6)
            else:
                ax[0].plot(fs, y, color=PS.SERIES[k], label=f"{lab}, pen held still", alpha=0.55)
            for f, v in zip(fs, y):
                rows.append([dev, scen, 0.5, f, v])
        k += 1
    ax[0].axhline(P.LETTER_RULE["write_mm"], color=PS.MUTED, linewidth=0.8)
    ax[0].axhline(P.LETTER_RULE["nudge_mm"], color=PS.BASELINE, linewidth=0.8)
    ax[0].text(fs[0], P.LETTER_RULE["write_mm"] * 1.05, "'can write' line, 2 mm", fontsize=7.5, color=PS.INK2)
    ax[0].text(fs[0], P.LETTER_RULE["nudge_mm"] * 1.05, "'can nudge' line, 0.2 mm", fontsize=7.5, color=PS.INK2)
    ax[0].set_yscale("log"); _plain_log(ax[0]); ax[0].set_xlabel("frequency of the push (Hz)"); ax[0].set_ylabel("tip shift, peak (mm)")
    ax[0].set_title("Can inertia write? (r_rot 0.5, relaxed hand)"); ax[0].legend(fontsize=7)
    pul = [p for p in steer["pulses"] if p["device"] == "cmg" and p["r_rot"] == 0.5 and p["scenario"] == "write"]
    if pul:
        p = pul[0]
        ax[1].plot(np.array(p["trace_t"]) - p["trace_t"][0] - 0.2, p["trace_mm"], color=PS.SERIES[1], label="CMG 150 ms pulse, 550 ms reset")
        for t, v in zip(p["trace_t"], p["trace_mm"]):
            rows.append(["cmg_pulse", "write", 0.5, t, v])
    ax[1].set_xlabel("time from pulse start (s)"); ax[1].set_ylabel("tip shift (mm)"); ax[1].set_title("One stroke-long torque pulse")
    ax[1].legend()
    PS.stamp(fig, "SIMULATION", "H1 with paper friction; device at 90 % of its limit")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "fig_ek_steer.png")); plt.close(fig)
    _csv(os.path.join(outdir, "fig_ek_steer.csv"), ["device", "scenario", "r_rot", "f_Hz_or_t_s", "tip_peak_mm"], rows)


def fig_gyro(gs, g, outdir):
    PS, plt = _fig_setup()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.0))
    rows = []
    H0 = g["H_design_Nms"]
    splits = sorted({c["r_rot"] for c in g["rows"]["pg_design"]})
    for i, rr in enumerate(splits):
        xs, ys = [], []
        for k in (1, 3, 10, 30):
            key = f"massless_H{k}x"
            if key in gs:
                xs.append(k * H0 * 1e3); ys.append(gs[key][str(rr)]["4-12Hz_1mm_passive"])
        ax[0].plot(xs, ys, color=PS.SERIES[i], label=f"r_rot {rr}", marker="o", markersize=7, markeredgecolor=PS.SURFACE, markeredgewidth=1.6)
        for x, y in zip(xs, ys):
            rows.append(["massless", rr, x, y])
    ax[0].axhline(1.0, color=PS.BASELINE, linewidth=1)
    ax[0].axvline(H0 * 1e3, color=PS.MUTED, linewidth=0.8, linestyle="--")
    ax[0].set_xscale("log"); _plain_log(ax[0], "x")
    ax[0].set_xlabel(f"rotor angular momentum H (mN m s); dashed: largest rotor in 45 g ({H0 * 1e3:.1f})")
    ax[0].set_ylabel("ink error with / without the rotor, 4-12 Hz, 1 mm"); ax[0].set_title("Spin alone (rotor mass left out)")
    ax[0].legend()
    w = 0.38
    v_ns = [gs["pg_design_nospin"][str(rr)]["4-12Hz_1mm_passive"] for rr in splits]
    v_s = [gs["pg_design"][str(rr)]["4-12Hz_1mm_passive"] for rr in splits]
    x = np.arange(len(splits))
    ax[1].bar(x - w / 2, v_ns, width=w * 0.95, color=PS.SERIES[3], label=f"same {g['mass_g']:.0f} g, not spinning")
    ax[1].bar(x + w / 2, v_s, width=w * 0.95, color=PS.SERIES[0], label=f"spinning (H {H0 * 1e3:.1f} mN m s)")
    for rr, a_, b_ in zip(splits, v_ns, v_s):
        rows.append(["design_not_spinning", rr, 0.0, a_]); rows.append(["design_spinning", rr, H0 * 1e3, b_])
    ax[1].axhline(1.0, color=PS.BASELINE, linewidth=1)
    ax[1].set_xticks(x); ax[1].set_xticklabels([f"r_rot {rr}" for rr in splits])
    ax[1].set_ylabel("ink error with / without the end-cap"); ax[1].set_title("The 45 g passive gyroscope: spin vs its own weight")
    ax[1].set_ylim(0, 1.3)
    ax[1].legend(loc="upper center", ncol=2)
    PS.stamp(fig, "SIMULATION", "H1, passive rotor along the pen axis, no nose, test seeds 200-203")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "fig_ek_gyro.png")); plt.close(fig)
    _csv(os.path.join(outdir, "fig_ek_gyro.csv"), ["case", "r_rot", "H_mNms", "ratio"], rows)


def fig_cue(cue, outdir):
    PS, plt = _fig_setup()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.0))
    rows = []
    for i, f in enumerate((40.0, 75.0)):
        b = [r for r in cue["force_for_levels"] if r["f_Hz"] == f]
        rr = [r["r_rot"] for r in b]
        v = [min(r["grip_acc_per_N_t1"], r["grip_acc_per_N_t2"]) for r in b]
        ax[0].plot(rr, v, color=PS.SERIES[i], label=f"{f:.0f} Hz", marker="o", markersize=7, markeredgecolor=PS.SURFACE, markeredgewidth=1.6)
        for a_, b_ in zip(rr, v):
            rows.append(["acc_per_N", f, a_, b_])
    ax[0].set_xlabel("grip split r_rot"); ax[0].set_ylabel("finger-pad acceleration per 1 N (m/s2)")
    ax[0].set_title("A force at the end-cap, felt at the fingers"); ax[0].legend()
    sims = [r for r in cue["sim"] if r["scenario"] == "write" and r["harmonic"] and r["r_rot"] == 0.5 and r["phase_deg"] == 0.0]
    for i, nc in enumerate((False, True)):
        b = sorted([r for r in sims if r["nose_cancel"] == nc and r["f_cue"] == 40.0], key=lambda r: r["F0_N"])
        if b:
            ax[1].plot([r["F0_N"] for r in b], [r["ink_jitter_um"] for r in b], color=PS.SERIES[i], marker="o", markersize=7,
                       markeredgecolor=PS.SURFACE, markeredgewidth=1.6, label="nose cancels the cue" if nc else "no cancellation")
            for r in b:
                rows.append(["jitter_40Hz", nc, r["F0_N"], r["ink_jitter_um"]])
    ax[1].axhline(30.0, color=PS.MUTED, linewidth=0.8, linestyle="--", label="rule R-C1 limit while writing, 30 um")
    ax[1].set_xlabel("cue force amplitude (N)"); ax[1].set_ylabel("ink jitter during the cue (um RMS)"); ax[1].set_title("The cue shakes the ink (40 Hz)")
    ax[1].legend()
    PS.stamp(fig, "SIMULATION + CALCULATION", "linear model and H1; a pseudo-force is a percept, not a force")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "fig_ek_cue.png")); plt.close(fig)
    _csv(os.path.join(outdir, "fig_ek_cue.csv"), ["quantity", "f_Hz_or_cancel", "x", "y"], rows)


def what_it_would_take(sc, target_mm=2.0, fs=(1.0, 2.0, 3.0), r_rot=0.5):
    """CALC from the linear receptances (relaxed HAP-26 hand, no paper friction: optimistic): the force, torque, mass x stroke,
    rotor momentum and rotor energy that a 'writing' end-cap would need to move the tip target_mm at f."""
    from . import scaling as SCL
    rec = {(r["r_rot"], r["f_Hz"]): r for r in sc["receptance"]}
    rows = []
    for f in fs:
        rr = rec[(r_rot, f)]
        F = target_mm / rr["tip_mm_per_N_cap_t1"]                       # N at the end-cap
        T = target_mm / (rr["tip_um_per_mNm_t2"] * 1e-3) * 1e-3        # N m
        w = 2 * math.pi * f
        mX = F / (0.7 * w * w)                                          # kg m (eta 0.7)
        H = T / min(P.GIMBAL_DRIVE["rate_max"], w * 1.0)                # single rotor, delta 1 rad
        n = 40000.0
        J = H / SCL.rpm2rad(n)
        D = 24e-3
        m_rot = 8 * J / (D * D)                                         # disc of 24 mm at 40 000 rpm
        rows.append({"f_Hz": f, "target_mm": target_mm, "force_at_endcap_N": F, "mass_x_stroke_g_mm": mX * 1e6,
                     "stroke_mm_for_30g": mX / 0.030 * 1e3, "torque_mNm": T * 1e3, "H_mNms_single_rotor_delta_1rad": H * 1e3,
                     "rotor_24mm_40krpm_mass_g": m_rot * 1e3, "rotor_energy_J": 0.5 * J * SCL.rpm2rad(n) ** 2,
                     "propeller_W_steady_22mm": SCL.prop_power_for(F, 22e-3)})
    return {"label": "CALCULATION (linear model, relaxed hand, frictionless paper: an optimistic lower bound on what writing would need; "
                     "see 'h1_vs_linear' for how much less H1 with paper friction gave per unit push)", "rows": rows}


def h1_vs_linear(sc, steer, fs=(1.0, 2.0, 3.0, 5.0), r_rot=0.5, lrm=None):
    """SIM vs CALC: tip amplitude in H1 while writing (paper friction, test seeds) against the linear model's prediction
    for the same command (relaxed hand, no friction), per device and frequency (axis 0, r_rot 0.5).  For the reaction mass
    the command is the coil force; the net force on the pen is the slug's inertial force, cmd m w^2 / |k - m w^2 + j c w|
    (5 Hz flexure, damping 0.7), which is what the linear end-cap receptance is applied to."""
    rec = {(r["r_rot"], r["f_Hz"]): r for r in sc["receptance"]}
    out = []
    for dev in sorted({r["device"] for r in steer["rows"]}):
        for f in fs:
            b = [r for r in steer["rows"] if r["device"] == dev and r["f"] == f and r["r_rot"] == r_rot and r["axis"] == 0
                 and r["scenario"] == "write" and not r.get("variant")]
            if not b or (r_rot, f) not in rec:
                continue
            cmd = b[0]["command_amp"]
            if dev == "lrm":
                m = (lrm or {}).get("moving_mass_g", 30.0) * 1e-3
                w = 2 * math.pi * f
                k = m * (2 * math.pi * 5.0) ** 2
                c = 1.4 * math.sqrt(k * m)
                net = cmd * m * w * w / math.sqrt((k - m * w * w) ** 2 + (c * w) ** 2)
                lin = net * rec[(r_rot, f)]["tip_mm_per_N_cap_t1"]
            else:
                lin = cmd * rec[(r_rot, f)]["tip_um_per_mNm_t2"]
            h1 = _mean([r["tip_amp_mm"] for r in b])
            out.append({"device": dev, "f_Hz": f, "command": cmd, "linear_amp_mm": lin, "h1_write_amp_mm": h1,
                        "h1_write_peak_mm": _mean([r["tip_peak_mm"] for r in b]), "linear_over_h1": lin / h1 if h1 > 0 else float("nan")})
    return out


def single_axis_lrm(s):
    """CALC: the chosen reaction-mass design driven along one axis only (the other coil pair off), against both axes, on
    the linear tremor bound (4-12 Hz, 1 mm, mean of 3 splits).  Tremor is elliptical (ellipticity 0.4 in the model), so one
    axis leaves the other untouched."""
    import torch
    from . import optimise as OP
    out = {}
    with torch.no_grad():
        d = OP.build("LRM2", {k: torch.tensor(float(v)) for k, v in s["x"].items()}, ())
        base = float(OP.metrics(d, hard=True)["tremor_mean"])
        out["both_axes"] = base
        orig = OP.limits
        for ax, name in ((1, "t1_only"), (0, "t2_only")):
            OP.limits = (lambda dd, f, _o=orig, _ax=ax: _o(dd, f) * torch.tensor([1.0 if i != _ax else 0.0 for i in range(2)], dtype=torch.float64))
            try:
                out[name] = float(OP.metrics(d, hard=True)["tremor_mean"])
            finally:
                OP.limits = orig
    return {"label": "CALCULATION (linear bound, 4-12 Hz, 1 mm, mean over r_rot 0.3/0.5/0.7; 1 = no change)", **out}


def side_effects(des):
    """CALC on the optimised designs: (1) the gyroscopic twist a rotor end-cap puts into the hand when the writer turns the pen
    (tau = H_net x Omega; a counter-rotating pair has H_net = 0), (2) the reaction mass reused as the pseudo-force vibrator
    (stroke and coil power for a given cue force), (3) the variable-speed (VSCMG) term J dOmega/dt, capped by the spin motor."""
    out = {"label": "CALCULATION (endcap/design.py values; spin-motor torques MFR AMF-120/121/51 or ASSUMPTION for 'INT')"}
    turn = {}
    for n, s in des.items():
        if s["class"] == "LRM2":
            continue
        Hn = s.get("H_net", s.get("H", 0.0)) if s["class"] != "PG" else s.get("H", 0.0)
        turn[n] = {"H_net_mNms": Hn * 1e3, **{f"twist_mNm_at_{w:g}rad_s": Hn * w * 1e3 for w in (2.0, 5.0, 10.0)}}
    out["twist_when_turning_the_pen"] = turn
    if "lrm" in des:
        s = des["lrm"]
        m_r, Km, X = s["moving_mass_g"] * 1e-3, s["Km"], s["X"]
        rows = []
        for f in (40.0, 75.0):
            for F in (0.25, 0.5, 1.0):
                w = 2 * math.pi * f
                rows.append({"f_Hz": f, "F_N": F, "slug_stroke_mm": F / (m_r * w * w) * 1e3, "coil_W": (F / Km) ** 2,
                             "fits_stroke": bool(F / (m_r * w * w) < X), "within_1W_peak": bool((F / Km) ** 2 <= P.ENV["p_peak"])})
        out["reaction_mass_as_cue_vibrator"] = rows
    vs = {}
    for n, s in des.items():
        if s["class"] in ("LRM2", "PG"):
            continue
        mot = P.MOTORS[s["choice"][1]]
        vs[n] = {"spin_motor": mot.name, "rated_or_stall_torque_mNm": float(getattr(mot, "rated", 0.0) or 0.0) * 1e3,
                 "note": "a variable-speed CMG adds tau = J dOmega/dt, at most the spin motor's torque; compare with the gimbal term"}
    out["vscmg_extra_torque"] = vs
    return out


# ================================================================================================ build
def _design_brief(s):
    keep = ("class", "choice", "x", "mass_g", "moving_mass_g", "P_spin_W", "P_avg_W", "P_peak_W", "tremor_mean", "steer_3Hz_mm", "H", "X", "Km",
            "F_act", "L_ax", "H_net", "extras", "parts_g", "battery_h_14500", "battery_h_10440", "violation")
    return {k: s[k] for k in keep if k in s}


def _impl_scaling(sc, c3):
    r3 = [r for r in sc["receptance"] if r["r_rot"] == 0.5 and r["f_Hz"] == 3][0]
    F2 = 2.0 / r3["tip_mm_per_N_cap_t1"]
    T2 = 2000.0 / r3["tip_um_per_mNm_t2"]
    return (f"Moving the ink 2 mm at 3 Hz needs about {F2:.2f} N at the end-cap or {T2:.0f} mN m (r_rot 0.5, relaxed hand, no paper friction); "
            f"a 30 g x +/-3.5 mm mass gives {c3['LRM_30g_3.5mm_N'] * 1e3:.0f} mN and a CMG pair {c3['CMG_pair_H1.2e-3_mNm']:.0f} mN m. "
            "A mass's force falls as f^2; a CMG's torque falls as f below its angle-limited corner.")


def _impl_optimise(opt, l45, c45):
    cap = max(opt["caps_g"])
    def at(key):
        v = [x for x in opt["fronts"].get(key, []) if x["cap_g"] == cap]
        return v[0] if v else None
    rw, pg = at("RW2_tremor"), at("PG_tremor")
    better = "CMG" if c45["tremor_mean"] < l45["tremor_mean"] else "reaction mass"
    txt = f"At {cap:.0f} g the {better} has the lower linear tremor bound (the device cancelling within its limits with exact knowledge of the tremor: optimistic)."
    if rw:
        txt += f" Reaction wheels: bound {rw['tremor_mean']:.2f} ({'feasible' if rw['penalty'] < 1e-3 else 'infeasible'})."
    if pg:
        txt += f" Passive rotor: bound {pg['tremor_mean']:.2f} (1 = no change)."
    return txt


def _impl_steer(ss):
    rows = {d: v["R-S1"] for d, v in ss.items() if "R-S1" in v}
    if not rows:
        return ""
    best = max(rows, key=lambda d: rows[d]["max_peak_1_3Hz_mm"] if rows[d]["max_peak_1_3Hz_mm"] == rows[d]["max_peak_1_3Hz_mm"] else -1)
    can = [d for d, v in rows.items() if v["verdict"] == "can write"]
    txt = ("No end-cap device can write (rule R-S1: 2 mm at 1-3 Hz). " if not can else f"Can write by rule R-S1: {', '.join(can)}. ")
    return txt + f"Largest tip shift at 1-3 Hz: {rows[best]['max_peak_1_3Hz_mm']:.2f} mm ({best}, verdict '{rows[best]['verdict']}')."


def _gyro_finding(g):
    """Plain sentence for rule R-G1 (spin against the same mass not spinning)."""
    red = g.get("spin_vs_nospin_reduction", float("nan"))
    if red != red:
        return "Rule R-G1 not evaluated."
    how = "lowered" if red >= 0 else "raised"
    return (f"Spin {how} the ink error by {abs(red) * 100:.1f} % against the same mass not spinning (4-12 Hz, 1 mm, r_rot 0.5); "
            f"rule R-G1 (>= 10 % lower) {'passed' if g.get('useful') else 'failed'}.")


def _impl_recommend(ts, rec):
    """What the recommendation means, with the fixed-weight comparator (computed from the test summary)."""
    ch = rec.get("choice")
    txt = rec.get("text", "")
    try:
        wk = "weight_" + ch
        dev = [ts[ch][r]["8-12Hz_1-2mm"]["further_reduction_mean"] * 100 for r in ("0.3", "0.5", "0.7")]
        wt = [ts[wk][r]["8-12Hz_1-2mm"]["further_reduction_mean"] * 100 for r in ("0.3", "0.5", "0.7")]
    except (KeyError, TypeError):
        return txt
    gain = [a - b for a, b in zip(dev, wt)]
    name = {"lrm": "reaction-mass", "cmg": "CMG"}.get(ch, ch)
    return (f"Carry the {name} end-cap into Rev J as a tremor steadier on top of the nose, not as a writing device. The same mass fixed "
            f"gives {wt[0]:.0f}/{wt[1]:.0f}/{wt[2]:.0f} % at r_rot 0.3/0.5/0.7, so the motion adds {gain[0]:+.0f}/{gain[1]:+.0f}/{gain[2]:+.0f} "
            f"points: measure the grip split before building (EXP-K08).")


def headline(sc, opt, tune, test, steer, gyro, cue, ts, ss, gs, cs, rec):
    """Plain summaries used by the evidence rows and the doc (numbers only from the stage caches)."""
    h = {}
    if sc:
        c3 = [r for r in sc["ceiling"] if r["f_Hz"] == 3][0]
        h["scaling"] = {"setup": "closed-form limits of a 30 g x +/-3.5 mm reaction mass, a CMG pair with H 1.2 mN m s, reaction wheels (MFR motors), a propeller, "
                                 "a passive rotor; Rev H linear hand-pen receptances at r_rot 0.3/0.5/0.7",
                        "findings": f"At 3 Hz: reaction mass {c3['LRM_30g_3.5mm_N'] * 1e3:.0f} mN; CMG pair {c3['CMG_pair_H1.2e-3_mNm']:.0f} mN m; wheel (2214 BXT rated) "
                                    f"{c3['RW_2214BXT_rated_mNm']:.1f} mN m. Propeller: {sc['propeller']['thrust_N_per_fan_at_0.5W'] * 1e3:.0f} mN per 22 mm fan at 0.5 W. "
                                    f"Passive rotor 3 mN m s: gyroscopic stiffening H w / K_rot = {[r for r in sc['gyro_stiffening'] if r['r_rot'] == 0.5][0]['ratio_8Hz'] * 100:.0f} % at 8 Hz (r_rot 0.5).",
                        "units": "N, N m; single-frequency amplitudes", "implication": _impl_scaling(sc, c3)}
    if opt:
        ch = opt.get("chosen") or {}
        l45 = ch.get("lrm") or [x for x in opt["fronts"]["LRM2_tremor"] if x["cap_g"] == max(opt["caps_g"])][0]
        c45 = ch.get("cmg") or [x for x in opt["fronts"]["CMG_tremor"] if x["cap_g"] == max(opt["caps_g"])][0]
        h["optimise"] = {"setup": "CMA-ES (derivative-free, discrete motor and arrangement choices) and autograd (Adam through a differentiable linear model) "
                                  "for 4 device classes and mass caps 15-45 g; 26 x 45 mm, 1 W peak, 0.3 W average",
                         "findings": f"45 g tremor optima (linear bound, 4-12 Hz, 1 mm, mean of 3 splits): reaction mass {l45['tremor_mean']:.2f} "
                                     f"({l45['moving_mass_g']:.0f} g moving, +/-{l45['X'] * 1e3:.1f} mm, {l45['P_avg_W']:.2f} W); CMG {c45['class']} {c45['tremor_mean']:.2f} "
                                     f"(H {c45['H'] * 1e3:.2f} mN m s at {c45['x']['n']:.0f} rpm, {c45['P_avg_W']:.2f} W, stored {c45['extras']['E_J']:.1f} J); "
                                     f"steering at 3 Hz: reaction mass {l45['steer_3Hz_mm']:.3f} mm, CMG {c45['steer_3Hz_mm']:.2f} mm (weakest direction).",
                         "units": "ratio of handle-tip tremor with/without; mm", "implication": _impl_optimise(opt, l45, c45)}
    if ts:
        def fr(n, r):
            try:
                return ts[n][r]["8-12Hz_1-2mm"]["further_reduction_mean"] * 100
            except KeyError:
                return float("nan")
        h["tremor"] = {"setup": "H1; Rev H nose with the causal Rev H tracker; device feed-forward from the tracker; test seeds 200-203; 4-12 Hz x 0.3/1/2 mm; r_rot 0.3/0.5/0.7",
                       "comparator": "nose alone; the same mass fixed in the end-cap",
                       "findings": "Further reduction on top of the nose, 8-12 Hz, 1-2 mm (r_rot 0.3/0.5/0.7): reaction mass "
                                   f"{fr('lrm', '0.3'):.0f}/{fr('lrm', '0.5'):.0f}/{fr('lrm', '0.7'):.0f} %; CMG {fr('cmg', '0.3'):.0f}/{fr('cmg', '0.5'):.0f}/{fr('cmg', '0.7'):.0f} %; "
                                   f"fixed mass (LRM) {fr('weight_lrm', '0.3'):.0f}/{fr('weight_lrm', '0.5'):.0f}/{fr('weight_lrm', '0.7'):.0f} %; "
                                   f"fixed mass (CMG) {fr('weight_cmg', '0.3'):.0f}/{fr('weight_cmg', '0.5'):.0f}/{fr('weight_cmg', '0.7'):.0f} %.",
                       "units": "relative change of the RMS ink error", "implication": rec.get("text", "")}
    if ss:
        def pk(d, f):
            return ss.get(d, {}).get(f"write_r0.5_{f:g}Hz_ax0", {}).get("peak_mm", float("nan"))
        h["steer"] = {"setup": "open-loop sinusoids at 90 % of each device's limit, 1-5 Hz, while writing and while holding still; single 150 ms pulses; "
                               "r_rot 0.3/0.5/0.7; relaxed HAP-26 hand, x2 stiffer hand, writer's visual correction",
                      "findings": f"Peak tip shift while writing, r_rot 0.5, at 1/3/5 Hz: reaction mass {pk('lrm', 1):.3f}/{pk('lrm', 3):.3f}/{pk('lrm', 5):.2f} mm; "
                                  f"CMG {pk('cmg', 1):.2f}/{pk('cmg', 3):.2f}/{pk('cmg', 5):.2f} mm. Verdicts (rule R-S1): reaction mass '{ss.get('lrm', {}).get('R-S1', {}).get('verdict')}', "
                                  f"CMG '{ss.get('cmg', {}).get('R-S1', {}).get('verdict')}'.",
                      "units": "mm at the ink", "implication": _impl_steer(ss)}
    if gs:
        g = gs.get("R-G1", {})
        h["gyro"] = {"setup": "passive rotor along the pen axis: the largest that fits 45 g, with and without spin, and massless rotors 1-30x its momentum",
                     "findings": _gyro_finding(g), "units": "ink error ratio",
                     "implication": ("Gyroscopic stiffening is not useful at pen scale (rule R-G1 failed)" if not g.get("useful")
                                     else "Gyroscopic stiffening passed rule R-G1 at pen scale")}
    if cs:
        h["cue"] = {"setup": "asymmetric 40/75 Hz force at the end-cap (5 g vibrator) in H1 while writing; literature channel table",
                    "findings": f"Ink jitter at 0.5 N: {cs['jitter_um_0.5N_write']:.0f} um RMS, {cs['jitter_um_0.5N_write_nose_cancel']:.0f} um with the nose cancelling it; "
                                f"rule R-C1 (<= 30 um while writing) {'passed' if cs['R-C1']['usable_while_writing'] else 'failed'}.", "units": "um RMS",
                    "implication": ("A 0.5 N cue is usable while writing (rule R-C1)" if cs["R-C1"]["usable_while_writing"] else
                                    ("A 0.5 N cue is usable while writing only with the nose cancelling it (rule R-C1)" if cs["R-C1"]["usable_with_nose_cancel"]
                                     else "A 0.5 N cue shakes the ink beyond 30 um RMS even with the nose cancelling it: cue only in pauses or pen-up (rule R-C1)"))}
    h["recommendation"] = {"setup": "rule R-D1 applied to the test results", "findings": rec.get("text", ""),
                           "units": "relative change of the RMS ink error (8-12 Hz, 1-2 mm, test seeds); W",
                           "implication": _impl_recommend(ts, rec)}
    extra = {"scaling": ("Sets what any end-cap device can do at writing (1-5 Hz) and tremor (4-12 Hz) frequencies",
                         "Closed-form single-frequency limits; linear model with the relaxed HAP-26 hand and no paper friction"),
             "optimise": ("Chooses the end-cap design in each device class and the arrangement of the CMG",
                          "Linear bounds with ideal knowledge of the tremor; part masses partly ASSUMPTION; the integrated hub motor is a concept"),
             "tremor": ("Decides whether an end-cap is worth fitting for tremor (rule R-T1)",
                        "Synthetic writers and tremor, 4 test seeds; grip split unmeasured (0.3/0.5/0.7 swept); relaxed HAP-26 hand"),
             "steer": ("Answers whether inertia can write or steer letters (rule R-S1)",
                       "Open-loop pushes at the device limit; relaxed hand (x2 stiffer tried); simple visual-correction model"),
             "gyro": ("Decides whether a passive gyroscope is worth fitting (rule R-G1)",
                      "Passive rotor along the pen axis only; linear grip; synthetic tremor"),
             "cue": ("Decides when pseudo-force cues may be used while writing (rule R-C1)",
                     "Perception is not modelled, only side effects; one vibrator model; literature from healthy adults except one preprint"),
             "recommendation": ("Which end-cap to carry into the Rev J architecture", "Rests on the simulations above; nothing measured")}
    for k, (rel, lim) in extra.items():
        if k in h:
            h[k].setdefault("relevance", rel)
            h[k].setdefault("limitations", lim)
    return h


def recommend(ts, des, ss, cs):
    """Rule R-D1 (see run_study.RULES)."""
    verdicts = {}
    for n in ("lrm", "cmg"):
        if n in (ts or {}) and n in des:
            verdicts[n] = rule_RT1(ts, n, des[n]["P_avg_W"])
    passing = [n for n, v in verdicts.items() if v.get("pass")]
    ranking = None
    if passing:
        # R-T2 as written: rank by the further reduction at r_rot 0.5; devices within 2 points of the best are tied and the
        # tie goes to the lower average power, then the lower mass.  (A first version rounded the reductions into 2-point
        # bins, which is not the rule's "within 2 points"; corrected before the report was written - see the doc.)
        best_r = max(verdicts[n]["r0.5"] for n in passing)
        tied = [n for n in passing if best_r - verdicts[n]["r0.5"] <= 0.02 + 1e-12]
        best = sorted(tied, key=lambda n: (des[n]["P_avg_W"], des[n]["mass_g"]))[0]
        ranking = {"by_r0.5": {n: verdicts[n]["r0.5"] for n in passing}, "tied_within_2_points": tied,
                   "tie_break": "lower average power, then lower mass" if len(tied) > 1 else None,
                   "P_avg_W": {n: des[n]["P_avg_W"] for n in tied}}
        names = {"lrm": "reaction-mass", "cmg": "CMG"}
        text = (f"Fit the {names[best]} end-cap for tremor (rule R-T1 passed: "
                f"{verdicts[best]['r0.3'] * 100:.0f}/{verdicts[best]['r0.5'] * 100:.0f}/{verdicts[best]['r0.7'] * 100:.0f} % at r_rot 0.3/0.5/0.7")
        if len(tied) > 1:
            others = [n for n in tied if n != best]
            o_names = ", ".join(names[n] for n in others)
            o_red = ", ".join("%.1f %%" % (verdicts[n]["r0.5"] * 100) for n in others)
            o_pow = ", ".join("%.3f W" % des[n]["P_avg_W"] for n in others)
            text += ("; rule R-T2: the %s end-cap was within 2 points at r_rot 0.5 (%s against %.1f %%), so the tie went to the lower "
                     "average power (%.3f W against %s)" % (o_names, o_red, verdicts[best]["r0.5"] * 100, des[best]["P_avg_W"], o_pow))
        text += ")."
        choice = best
    else:
        choice = None
        text = "No end-cap device passes rule R-T1; no inertial end-cap is justified for tremor."
    return {"verdicts": verdicts, "choice": choice, "text": text, "ranking": ranking}


def build(quick=False):
    outdir = os.path.join(OUT, "_cache", "quick") if quick else OUT
    os.makedirs(outdir, exist_ok=True)
    sc, opt, tune, test, steer, gyro, cue = (_load(n, quick) for n in ("scaling", "optimise", "tune", "test", "steer", "gyro", "cue"))
    offs = _load("offshelf", quick)
    rw = _load("rw", quick)
    bud = _load("budgets", quick)
    compact = _load("compact", quick)
    if opt and rw:
        opt = dict(opt)
        opt["fronts"] = dict(opt["fronts"])
        opt["fronts"].update(rw["fronts"])            # corrected reaction-wheel fronts (see run_study.stage_rw)
    if opt and bud:
        opt = dict(opt)
        opt["budgets"] = bud["budgets"]               # larger envelopes redone (see run_study.stage_budgets)
    res = {"meta": provenance.metadata("CALCULATION + SIMULATION (model H1 and a linear hand-pen model; synthetic writing and tremor)",
                                       seeds={"tune": list(P.SEEDS["tune"]), "test": list(P.SEEDS["test"])},
                                       extra={"script": "endcap/run_study.py", "doc": "docs/inertial_endcap.md", "quick": quick}),
           "labels": P.labels_table(), "envelope": P.ENV}
    if test:
        res["rules"] = test["rules"]
        res["rules_fixed_before_test"] = {"tune_generated_utc": test.get("tune_generated_utc"), "test_started_utc": test.get("test_started_utc")}
    des = {}
    if opt:
        if opt.get("chosen"):
            des = opt["chosen"]
        else:
            cap = max(opt["caps_g"])
            for key, n in (("LRM2_tremor", "lrm"), ("CMG_tremor", "cmg"), ("CMG_steer", "cmg_steer"), ("PG_H", "pg")):
                des[n] = [x for x in opt["fronts"][key] if x["cap_g"] == cap][0]
        res["designs"] = {n: _design_brief(s) | {"source": s.get("source", "CMA-ES")} for n, s in des.items()}
        res["optimise"] = {"fronts": {k: [_design_brief(x) | {"cap_g": x["cap_g"], "feasible": x["penalty"] < 1e-3} for x in v] for k, v in opt["fronts"].items()},
                           "gradient_vs_cma": {k: {"gradient_f": v["f"], "cma_f": v["cma_f"], "gradient_penalty": v["pen"]} for k, v in opt["gradient"].items()},
                           "arrangements_45g": {k: _design_brief(v) | {"feasible": v["penalty"] < 1e-3} for k, v in opt["arrangements"].items()},
                           "comparators": opt["comparators"],
                           "larger_budgets": {k: _design_brief(v) | {"feasible": v["penalty"] < 1e-3, "source": v.get("source", "CMA-ES")}
                                              for k, v in opt["budgets"].items()},
                           "stiffer_hand": opt["sensitivity"],
                           "catalogue_motors_only_45g": ({k: _design_brief(v) | {"feasible": v["penalty"] < 1e-3} for k, v in offs["designs"].items()}
                                                         if offs else None),
                           "method": "CMA-ES (own implementation, endcap/cmaes.py) over continuous sizes plus discrete choices; Adam through the differentiable linear "
                                     "model (endcap/linear_torch.py) warm-started from the CMA-ES optimum; both on the same penalised objective"}
    if des:
        res["side_effects"] = side_effects(des)
        if "lrm" in des:
            try:
                res["side_effects"]["single_axis_reaction_mass"] = single_axis_lrm(des["lrm"])
            except Exception as e:                       # a check, not a result the report depends on
                res["side_effects"]["single_axis_reaction_mass"] = {"error": str(e)}
    if sc:
        res["scaling"] = sc
        res["what_it_would_take"] = what_it_would_take(sc)
        if steer:
            res["what_it_would_take"]["h1_vs_linear"] = h1_vs_linear(sc, steer, lrm=des.get("lrm"))
    ts = tremor_summary(test) if test else None
    ss = steer_summary(steer) if steer else None
    gs = gyro_summary(gyro) if gyro else None
    cs = cue_summary(cue) if cue else None
    rec = recommend(ts, des, ss, cs) if ts else {"text": "", "verdicts": {}}
    if tune:
        res["tuning"] = {"chosen": tune["chosen"], "seeds": list(P.SEEDS["tune"])}
    if ts:
        res["tremor"] = {"summary": ts, "distortion": test["distortion"], "designs": test["designs"],
                         "oracle": {n: {"dev_oracle_mean_8_12Hz_1mm_r0.5": _mean([c.get("dev_oracle") for c in v]),
                                        "dev_passive_mean": _mean([c.get("dev_passive") for c in v])} for n, v in test.get("oracle", {}).items()},
                         "wrist": {n: {"nose": _mean([c["nose"] for c in v]), "nose+device": _mean([c.get("nose+dev", c.get("nose+passive")) for c in v])}
                                   for n, v in test.get("wrist", {}).items()},
                         "device_use": device_use(test)}
    if ss:
        res["steering"] = ss
    if gs:
        res["gyroscopic_stiffening"] = gs
    if cue:
        from . import cue as CU
        res["cue"] = {"summary": cs, "force_for_levels": cue["force_for_levels"], "writing_share": cue["writing_share"],
                      "channels": CU.channel_table(cmg=des.get("cmg")), "sim": cue["sim"]}
    res["recommendation"] = rec
    if compact:
        res["compact_packaging"] = {"label": "SIMULATION (test seeds, r_rot 0.5, 8-12 Hz x 1-2 mm; a sensitivity check run after the test, "
                                             "not used to choose anything)", "gain": compact["gain"],
                                    "by_z_mm": {z: {k: v for k, v in b.items() if k != "rows"} for z, b in compact["z_mm"].items()}}
    res["headline"] = headline(sc, opt, tune, test, steer, gyro, cue, ts, ss, gs, cs, rec)
    # figures
    figs = []
    try:
        if sc and opt:
            fig_ceiling(sc, opt, outdir); figs.append("fig_ek_ceiling.png")
        if opt:
            fig_pareto(opt, outdir); figs.append("fig_ek_pareto.png")
        if ts:
            fig_tremor(ts, outdir); figs.append("fig_ek_tremor.png")
        if ss:
            fig_steer(ss, steer, outdir); figs.append("fig_ek_steer.png")
        if gs:
            fig_gyro(gs, gyro, outdir); figs.append("fig_ek_gyro.png")
        if cue:
            fig_cue(cue, outdir); figs.append("fig_ek_cue.png")
    finally:
        res["figures"] = figs
    provenance.write_json(os.path.join(outdir, "endcap_study.json"), res)
    from . import evidence as EV
    EV.write(os.path.join(outdir, "evidence_rows.csv"), res)
    from . import layout as LY
    if des:
        LY.write(os.path.join(outdir, "layout_parts.json"), res)
    return res
