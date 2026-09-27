#!/usr/bin/env python3
"""Pencil simulation study (task A2): coupled time-domain model P1 on synthetic handwriting.

Protocol (harness conventions of sim/pensim/harness.py and bench.py):
  * reference ink = the same pencil in NEUTRAL mode (stage servoed at centre) on the same
    handwriting WITHOUT tremor; errors are time-aligned ink differences (sim/pencil/evaluate.py);
  * ratio = e_rms(controller, tremor) / e_rms(neutral, tremor), both against that reference;
  * distortion = the controller on the tremor-free handwriting against the reference;
  * device distortion = locked conventional pen vs the neutral pencil (mean offset removed);
  * the oracle receives the clean housing path (neutral, no tremor) as its disturbance reference;
  * the Kalman uses the parameters frozen on M1's tuning seeds (results/sim/estimator_selection.json);
    test seeds 200-203 only.
Studies: controller grid (4-12 Hz x 0.1/0.3/0.5 mm x 4 seeds), passive skid effect (skid on,
frictionless skid, conventional locked pen), design sensitivity (L vs Q, tolerance, spring force,
tilt, hysteresis, sensor noise, 55 V rail), cross-check against model M1, 3-D replay trace, drive
power and battery life.
Evidence status: SIMULATION on synthetic signals.  Nothing here is a measurement.
Outputs: results/pencil/sim_metrics.json, viz_trace.json, fig_sim_*.png
Run: python3 -m sim.pencil.run_study          (about 2-4 min on 2 processes)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import sim.pencil  # noqa: E402,F401  (sets NUMBA_CACHE_DIR before numba loads)
from sim.pencil import design as D  # noqa: E402
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from sim.pencil import power as PW  # noqa: E402
from sim.pensim import scenarios  # noqa: E402
from stabpen import plotstyle, provenance  # noqa: E402
from stabpen import signals as sg  # noqa: E402

OUT = os.path.join(ROOT, "results", "pencil")
SEEDS = (200, 201, 202, 203)
F0S = (4.0, 6.0, 8.0, 10.0, 12.0)
AMPS = (0.1e-3, 0.3e-3, 0.5e-3)
DUR = 6.0
CTRL = ("oracle", "kfosc", "guided")


def _ctrl(name):
    return M.kalman_controller() if name == "kfosc" else M.Controller(mode=name)


def device_distortion(ref_same, ref_rigid):
    n = min(len(ref_same["t"]), len(ref_rigid["t"]))
    m = (ref_same["contact"][:n] > 0) & (ref_rigid["contact"][:n] > 0) & (ref_same["t"][:n] > 0.5)
    e = ref_same.ink()[:n] - ref_rigid.ink()[:n]
    off = e[m].mean(axis=0)
    ed = e[m] - off
    return {"mean_offset_um": (off * 1e6).tolist(), "detrended_rms_um": float(np.sqrt(np.mean(np.sum(ed ** 2, axis=1))) * 1e6)}


def path_distance(res, template):
    from scipy.spatial import cKDTree
    tree = cKDTree(template)
    m = (res["contact"] > 0) & (res["t"] > 0.5)
    d, _ = tree.query(res.ink()[m])
    return float(np.sqrt(np.mean(d ** 2)) * 1e6)


def run_mode(sc1, mode, cfg, seed, ref, d_clean):
    if mode == "oracle":
        return M.run(M.with_disturbance(sc1, d_clean), M.Controller(mode="oracle"), cfg, seed=seed)
    return M.run(sc1, _ctrl(mode), cfg, seed=seed)


# ------------------------------------------------------------------ controller grid (one seed)
def grid_seed(seed):
    cfg = M.PencilConfig()
    sc0 = scenarios.handwriting(seed=seed, duration=DUR)
    ref = M.run(sc0, M.Controller(mode="neutral"), cfg, seed=seed)
    rig = M.run(sc0, M.Controller(mode="locked"), M.PencilConfig(locked=True, skid=False), seed=seed)
    rsk = M.run(sc0, M.Controller(mode="neutral"), M.PencilConfig(stage_locked=True), seed=seed)
    out = {"seed": seed, "device_distortion_rigid_vs_neutral": device_distortion(ref, rig),
           "device_distortion_skid_locked_vs_rigid": device_distortion(rsk, rig),
           "device_distortion_neutral_vs_skid_locked": device_distortion(ref, rsk), "rows": [],
           "distortion_um": {m: E.compare(M.run(sc0, _ctrl(m), cfg, seed=seed), ref)["e_rms_um"] for m in ("kfosc", "guided")}}
    for f0 in F0S:
        for amp in AMPS:
            sc1 = scenarios.handwriting(seed=seed, duration=DUR, tremor=sg.TremorSpec(f0=f0, amp_pk=amp))
            d_clean = M.housing_disturbance(sc1, ref)
            rn = M.run(sc1, M.Controller(mode="neutral"), cfg, seed=seed)
            base = E.compare(rn, ref)
            base["path_um"] = path_distance(rn, sc1.intended)
            out["rows"].append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "mode": "neutral", "ratio": 1.0, **base})
            for mode in CTRL:
                r = run_mode(sc1, mode, cfg, seed, ref, d_clean)
                m = E.compare(r, ref)
                m["ratio"] = m["e_rms_um"] / base["e_rms_um"]
                if mode == "guided":
                    m["path_um"] = path_distance(r, sc1.intended)
                    m["path_ratio"] = m["path_um"] / base["path_um"]
                out["rows"].append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "mode": mode, **m})
    return out


# ------------------------------------------------------------------ passive skid effect (one seed)
PASSIVE = {"skid_on": dict(), "skid_frictionless": dict(mu_skid=0.0), "conventional_locked": dict(locked=True, skid=False)}


def passive_seed(seed):
    rows = []
    sc0 = scenarios.handwriting(seed=seed, duration=DUR)
    refs = {}
    for name, kw in PASSIVE.items():
        cfg = M.PencilConfig(**kw)
        mode = "locked" if kw.get("locked") else "neutral"
        refs[name] = (cfg, mode, M.run(sc0, M.Controller(mode=mode), cfg, seed=seed))
    for f0 in F0S:
        sc1 = scenarios.handwriting(seed=seed, duration=DUR, tremor=sg.TremorSpec(f0=f0, amp_pk=0.3e-3))
        d_rms = float(np.sqrt(np.mean(np.sum(sc1.dtrue[int(0.5 / (sc1.t[1] - sc1.t[0])):] ** 2, axis=1))) * 1e6)
        for name, (cfg, mode, ref) in refs.items():
            r = M.run(sc1, M.Controller(mode=mode), cfg, seed=seed)
            m = E.compare(r, ref)
            rows.append({"seed": seed, "f0": f0, "config": name, "hand_tremor_rms_um": d_rms,
                         "housing_band_rms_um": m["housing_band_rms_um"], "e_rms_um": m["e_rms_um"],
                         "e_band_rms_um": m["e_band_rms_um"], "N_skid_mean": m["N_skid_mean"], "N_nib_mean": m["N_nib_mean"]})
    return rows


# ------------------------------------------------------------------ design sensitivity (one seed)
def variants():
    th35 = dict(theta_deg=35.0)
    return {
        "Q26_nominal": (dict(), {}),
        "L35": (dict(stage_key="L35"), {}),
        "Q26_minus20pct": (dict(tol=-0.2), {}),
        "Q26_Fc_0.08": (dict(F_c_ref=0.08), {}),
        "Q26_Fc_0.30": (dict(F_c_ref=0.30), {}),
        "Q26_theta35": (dict(), th35),
        "Q26_theta75": (dict(), dict(theta_deg=75.0)),
        "Q26_no_hysteresis": (dict(hysteresis=False), {}),
        "Q26_hall_0.3um": (dict(overrides={"hall_noise": 0.3e-6}), {}),
        "Q26_hall_0": (dict(overrides={"hall_noise": 0.0}), {}),
        "Q26_rail_55V": (dict(V_rail=55.0), {}),
        "Q26_mu_nib_0.35": (dict(mu_nib=0.35), {}),
        "L35_minus20pct": (dict(stage_key="L35", tol=-0.2), {}),
        "L35_theta35": (dict(stage_key="L35"), th35),
        "Q26_theta35_minus20pct": (dict(tol=-0.2), th35),
    }


def sens_seed(seed):
    rows = []
    for name, (ckw, skw) in variants().items():
        cfg = M.PencilConfig(**ckw)
        sc0 = scenarios.handwriting(seed=seed, duration=DUR, **skw)
        ref = M.run(sc0, M.Controller(mode="neutral"), cfg, seed=seed)
        for f0 in (6.0, 10.0):
            sc1 = scenarios.handwriting(seed=seed, duration=DUR, tremor=sg.TremorSpec(f0=f0, amp_pk=0.3e-3), **skw)
            d_clean = M.housing_disturbance(sc1, ref)
            base = E.compare(M.run(sc1, M.Controller(mode="neutral"), cfg, seed=seed), ref)
            row = {"seed": seed, "variant": name, "f0": f0, "neutral_e_rms_um": base["e_rms_um"],
                   "neutral_P_rail_classB_mW": base["P_rail_classB_mW"], "neutral_P_rail_recovery_mW": base["P_rail_recovery_mW"],
                   "neutral_q_sat_frac": base["q_sat_frac"], "N_nib_std": base["N_nib_std"]}
            for mode in ("oracle", "kfosc"):
                m = E.compare(run_mode(sc1, mode, cfg, seed, ref, d_clean), ref)
                row.update({f"{mode}_ratio": m["e_rms_um"] / base["e_rms_um"], f"{mode}_q_sat_frac": m["q_sat_frac"],
                            f"{mode}_frac_vsat": m["frac_vsat"], f"{mode}_P_rail_classB_mW": m["P_rail_classB_mW"],
                            f"{mode}_P_rail_recovery_mW": m["P_rail_recovery_mW"]})
            rows.append(row)
    return rows


# ------------------------------------------------------------------ guided mode on the feature course
def guided_features(seed):
    """As sim/guided_eval.py: path distance from each in-contact ink sample to the template
    (intended path), per feature, neutral vs guided, 6 Hz / 0.3 mm tremor."""
    from scipy.spatial import cKDTree
    cfg = M.PencilConfig()
    sc = scenarios.features(tremor=sg.TremorSpec(f0=6.0, amp_pk=3e-4), seed=seed)
    tree = cKDTree(sc.intended)
    out = {}
    for name in ("neutral", "guided"):
        r = M.run(sc, M.Controller(mode=name), cfg, seed=seed + 1)
        t = r["t"]
        ink = r.ink()
        con = r["contact"] > 0
        for feat, t0, t1, _m in sc.meta.get("features", []) or []:
            m = (t >= t0) & (t <= t1) & con
            if m.sum() < 10:
                continue
            d, _ = tree.query(ink[m])
            out.setdefault((name, feat), []).append(d)
    return out


# ------------------------------------------------------------------ cross-check against model M1
def m1_crosscheck():
    from sim.pensim import model as m1
    tr = sg.TremorSpec(f0=6.0, amp_pk=0.3e-3)
    out = {}
    for label, trem in (("tremor_6Hz_0.3mm", tr), ("no_tremor", None)):
        sc = scenarios.handwriting(seed=5, duration=4.0, tremor=trem)
        a = m1.run(sc, m1.Controller(mode="rigid"), seed=5)
        b = M.run(sc, M.Controller(mode="locked"), M.PencilConfig(locked=True, skid=False, m1_match=True), seed=5)
        n = min(len(a["t"]), len(b["t"]))
        ink_a = a.xy("tipx")[:n]
        ink_b = b.ink()[:n]
        both = (a["contact"][:n] > 0) & (b["contact"][:n] > 0)
        out[label] = {"ink_rms_difference_um": float(np.sqrt(np.mean(np.sum((ink_a - ink_b) ** 2, axis=1))) * 1e6),
                      "ink_max_difference_um": float(np.max(np.linalg.norm(ink_a - ink_b, axis=1)) * 1e6),
                      "housing_rms_difference_um": float(np.sqrt(np.mean(np.sum((a.xy("pHx")[:n] - b.xy("pHx")[:n]) ** 2, axis=1))) * 1e6),
                      "N_mean_M1": float(a["N"][:n][both].mean()), "N_mean_P1": float(b["Nn"][:n][both].mean()),
                      "contact_agreement": float(np.mean((a["contact"][:n] > 0) == (b["contact"][:n] > 0)))}
        out[label]["_runs"] = (a, b)
    # neutral ink error with the stage locked: e_rms of tremor vs clean, each model against itself
    a1, b1 = out["tremor_6Hz_0.3mm"].pop("_runs")
    a0, b0 = out["no_tremor"].pop("_runs")
    from sim.pensim import evaluate as ev1
    out["locked_ink_error_um"] = {"M1": ev1.compare(a1, a0)["e_rms_um"], "P1": E.compare(b1, b0)["e_rms_um"]}
    out["note"] = ("same handwriting and tremor; M1 'rigid' mode vs the pencil model with stage and axial slide locked, "
                   "skid off, M1's housing mass and paper contact: the physics coincide, so the traces must agree")
    return out


# ------------------------------------------------------------------ servo loop check (analytic)
def servo_check():
    cfg = M.PencilConfig()
    st = D.stage(cfg.stage_key)
    m, k = st.m_eq_nib, st.k_b_nib + st.k_par_nib
    c = 2 * cfg.zeta_stage * math.sqrt(k * m)
    fs = cfg.servo_hz
    Ts = 1 / fs
    Kd = max(2 * cfg.servo_zeta * math.sqrt(k * m) - c, 0.0)
    Ki = k * 2 * math.pi * cfg.servo_bw
    out = {}
    for zo in (0.02, 0.05, 0.1):
        cz = 2 * zo * math.sqrt(k * m)
        w = 2 * np.pi * np.logspace(0, math.log10(fs / 2 * 0.999), 6000)
        s = 1j * w
        z = np.exp(s * Ts)
        G = 1 / (m * s ** 2 + cz * s + k) * (1 - np.exp(-s * Ts)) / (s * Ts) / (1 + s / (2 * np.pi * cfg.drv_bw)) * np.exp(-s * 1e-4)
        ad = 1 - math.exp(-2 * math.pi * cfg.d_filt_hz * Ts)
        Dz = (1 - 1 / z) / Ts * ad / (1 - (1 - ad) / z)
        L = (Ki * Ts / (1 - 1 / z) + Kd * Dz) * G
        mag, ph = np.abs(L), np.unwrap(np.angle(L))
        idx = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
        p180 = np.where(np.diff(np.sign(ph + np.pi)) != 0)[0]
        S = 1 / (1 + L)
        i8 = int(np.argmin(abs(w / 2 / np.pi - 8)))
        out[f"zeta_open_{zo}"] = {"crossovers_Hz": [float(w[i] / 2 / np.pi) for i in idx],
                                  "phase_margins_deg": [float(180 + math.degrees(ph[i])) for i in idx],
                                  "gain_margin_dB": [float(-20 * math.log10(mag[i])) for i in p180][:2],
                                  "S_at_8Hz": float(abs(S[i8])), "peak_S": float(np.max(abs(S)))}
    return {"servo_rate_Hz": fs, "Ki": Ki, "Kd": Kd, "d_filter_Hz": cfg.d_filt_hz, "integral_corner_Hz": cfg.servo_bw,
            "feedforward": "k_tot q_ref + m_eq q_ref'' + static normal-load bias (contact-gated, constant, not measured-force)",
            "margins": out, "label": "CALCULATION (discrete loop: ZOH, 0.1 ms Hall delay, 2 kHz driver pole)"}


# ------------------------------------------------------------------ viz trace
def viz(seed=200, f0=6.0, amp=0.3e-3, dur=5.0):
    cfg = M.PencilConfig()
    sc0 = scenarios.handwriting(seed=seed, duration=dur)
    sc1 = scenarios.handwriting(seed=seed, duration=dur, tremor=sg.TremorSpec(f0=f0, amp_pk=amp))
    ref = M.run(sc0, M.Controller(mode="neutral"), cfg, seed=seed)
    d_clean = M.housing_disturbance(sc1, ref)
    runs = {"neutral": M.run(sc1, M.Controller(mode="neutral"), cfg, seed=seed),
            "oracle": M.run(M.with_disturbance(sc1, d_clean), M.Controller(mode="oracle"), cfg, seed=seed),
            "kalman": M.run(sc1, M.kalman_controller(), cfg, seed=seed),
            "guided": M.run(sc1, M.Controller(mode="guided"), cfg, seed=seed)}
    labels = {"neutral": "No correction (stage held at centre)", "oracle": "Physical limit (perfect disturbance knowledge)",
              "kalman": "Tremor estimator (Kalman, frozen M1 set)", "guided": "Guided by template"}
    base = E.compare(runs["neutral"], ref)
    rb = ref.info["static"]["r_b"]
    dec = int(round(0.01 / (ref["t"][1] - ref["t"][0])))
    sl = slice(0, None, dec)

    def sig(x):
        return float(f"{x:.4g}")

    def arr(a, scale=1.0):
        return [[sig(v * scale) for v in row] for row in np.asarray(a)[sl]]

    cases = []
    extra_power = {}
    for key, r in runs.items():
        m = E.compare(r, ref)
        n = min(len(r["t"]), len(ref["t"]))
        hous = np.column_stack([r.xy("pHx")[:n], r["pHz"][:n] - rb])
        nib = np.column_stack([r.ink()[:n], r["Cz"][:n] - rb])
        Fn = np.column_stack([r.xy("fnx")[:n], r["Nn"][:n]])
        Fs = np.column_stack([r.xy("fsx")[:n], r["Ns"][:n]])
        P_mW = float(np.mean(r["PrailB"])) * 1e3
        P_batt_mW = PW.battery_power("drv2700", P_mW * 1e-3) * 1e3
        cases.append({"key": key, "label": labels[key], "t": [sig(v) for v in r["t"][:n][sl]],
                      "housing": arr(hous, 1e3), "nib": arr(nib, 1e3), "intended": arr(ref.ink()[:n], 1e3),
                      "contact": [int(v > 0) for v in r["contact"][:n][sl]],
                      "q": arr(r.xy("q1")[:n], 1e3), "F_nib": arr(Fn), "F_skid": arr(Fs), "F_act": arr(r.xy("Fa1")[:n]),
                      "V": arr(r.xy("V1")[:n]),
                      "metrics": {"ink_err_rms_um": sig(m["e_rms_um"]), "ratio_vs_neutral": sig(m["e_rms_um"] / base["e_rms_um"]),
                                  "q_sat_frac": sig(m["q_sat_frac"]), "P_drive_mW": sig(P_mW)}})
        extra_power[key] = {"P_drive_rail_classB_mW": sig(P_mW), "P_drive_rail_recovery_mW": sig(float(np.mean(r["PrailR"])) * 1e3),
                            "P_battery_2xDRV2700_mW": sig(P_batt_mW)}
    meta = provenance.metadata("simulation (pencil model P1, synthetic handwriting and tremor)", seeds={"handwriting": seed, "tremor": seed + 1000},
                               p=D.Params().pencil,
                               extra={"model_version": M.MODEL_VERSION, "scenario": f"sim.pensim.scenarios.handwriting(seed={seed}, duration={dur}, TremorSpec(f0={f0}, amp_pk={amp}))",
                                      "theta_deg": 50.0, "N_user_N": 1.0, "stage": "Q26 (2.6 mm quad)",
                                      "decimation": "2 kHz record decimated to 100 Hz",
                                      "drive_power_per_case": extra_power,
                                      "definitions": {
                                          "housing": "housing reference point at the nominal nib position: nominal ball-contact point fixed to the barrel (ball centre at zero stage deflection and nominal protrusion, minus r_b in z); nib minus housing = stage and axial displacement",
                                          "nib": "ball contact point (ball centre minus r_b in z; z < 0 is paper indentation, z > 0 lifted)",
                                          "intended": "reference ink: the same pencil in NEUTRAL mode on the same handwriting without tremor (harness convention; not scenario.intended)",
                                          "q": "stage deflection at the nib in housing axes x_H (tilt plane), y_H (sideways), mm",
                                          "F_nib": "paper on nib, page frame (fx, fy friction; fz normal), N",
                                          "F_skid": "paper on skid ring, page frame, N",
                                          "F_act": "net bender force referred to the nib, k_b (delta_free(V) - q), housing axes x_H, y_H, N",
                                          "V": "centre-electrode drive voltage of each axis (0-60 V; 30 V = neutral)",
                                          "P_drive_mW": "mean power drawn from the piezo drive rail, both axes, class-B / switch-to-rail stage (DRV2700 class; add its 72 mW quiescent and divide by the 0.75 boost efficiency for battery power); the charge-recovery value is P_drive_rail_recovery_mW; includes the drive activity caused by 1 um Hall noise"}})
    return {"meta": meta, "units": {"length": "mm", "time": "s", "force": "N"},
            "frame": "paper: x,y on the page, z up; pen tilt theta_deg about the pen's azimuth phi_deg",
            "theta_deg": 50, "phi_deg": 0, "cases": cases}, runs, ref


# ------------------------------------------------------------------ aggregation helpers
def agg(rows, keys, val):
    out = {}
    for r in rows:
        k = tuple(r[x] for x in keys)
        out.setdefault(k, []).append(r[val])
    return {k: (float(np.mean(v)), float(np.std(v)), len(v)) for k, v in out.items()}


def battery_table(grid_rows, p_el):
    """Battery life per mode from simulated rail powers (mean over seeds, 0.3 mm tremor)."""
    def mean_P(mode, f0, key):
        v = [r[key] for r in grid_rows if r["mode"] == mode and r["f0"] == f0 and abs(r["amp_mm"] - 0.3) < 1e-9]
        return float(np.mean(v)) * 1e-3
    cases = {"stage held (neutral), 6 Hz": ("neutral", 6.0), "tremor assist, full correction (oracle), 6 Hz": ("oracle", 6.0),
             "tremor assist, full correction (oracle), 10 Hz": ("oracle", 10.0), "tremor assist, Kalman, 10 Hz": ("kfosc", 10.0),
             "guided assist, 6 Hz tremor": ("guided", 6.0)}
    out = {"recording_only": {dk: {"P_W": p_el + PW.battery_power(dk, 0.0, active=False),
                                   "life_h": PW.battery_life_h(p_el + PW.battery_power(dk, 0.0, active=False))} for dk in ("drv2700", "recovery")}}
    for label, (mode, f0) in cases.items():
        pb = mean_P(mode, f0, "P_rail_classB_mW")
        pr = mean_P(mode, f0, "P_rail_recovery_mW")
        row = {}
        for dk, prail in (("drv2700", pb), ("recovery", pr)):
            P = p_el + PW.battery_power(dk, prail)
            row[dk] = {"P_rail_mW": prail * 1e3, "P_total_W": P, "energy_per_hour_mWh": P * 1e3, "life_h": PW.battery_life_h(P)}
        out[label] = row
    return out


# ------------------------------------------------------------------ figures
def figures(grid_rows, passive_rows, runs, ref):
    plotstyle.apply()
    import matplotlib.pyplot as plt
    S = plotstyle.SERIES
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.4), sharey=True)
    for ax, amp in zip(axs, (0.1, 0.3, 0.5)):
        for i, mode in enumerate(CTRL):
            a = agg([r for r in grid_rows if r["mode"] == mode and abs(r["amp_mm"] - amp) < 1e-9], ("f0",), "ratio")
            f = sorted(k[0] for k in a)
            y = [a[(x,)][0] for x in f]
            lbl = {"oracle": "oracle (physical bound)", "kfosc": "Kalman (frozen M1 set)", "guided": "guided (template)"}[mode]
            ax.plot(f, y, color=S[i], label=lbl, **plotstyle.marker_kw(S[i]) | {"linestyle": "-"})
        ax.axhline(1.0, color=plotstyle.MUTED, lw=1.0)
        ax.set_title(f"tremor {amp:.1f} mm peak", loc="left", fontsize=9)
        ax.set_xlabel("Tremor frequency (Hz)")
    axs[0].set_ylabel("Ink error / neutral pencil")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=8)
    fig.suptitle("Pencil (2.6 mm quad, skid, 0.30 mm usable stroke): ink error ratio, mean of 4 test seeds", x=0.01, ha="left", fontsize=9.5)
    plotstyle.stamp(fig, "simulation", "model P1, synthetic handwriting and tremor; not measured")
    fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(os.path.join(OUT, "fig_sim_ratio_vs_frequency.png")); plt.close(fig)
    # passive skid
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    for i, (name, lbl) in enumerate((("conventional_locked", "conventional pen (nib carries 1 N, μ 0.15)"),
                                     ("skid_on", "pencil, skid μ 0.12, stage held"), ("skid_frictionless", "pencil, frictionless skid"))):
        a = agg([r for r in passive_rows if r["config"] == name], ("f0",), "housing_band_rms_um")
        f = sorted(k[0] for k in a)
        ax.plot(f, [a[(x,)][0] for x in f], color=S[i], label=lbl, **plotstyle.marker_kw(S[i]) | {"linestyle": "-"})
    ax.set_xlabel("Tremor frequency (Hz), 0.3 mm peak at the hand")
    ax.set_ylabel("Housing tremor at the nib, 3-15 Hz RMS (µm)")
    ax.set_title("Passive effect of nose friction on housing tremor", loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5)
    plotstyle.stamp(fig, "simulation", "model P1, 4 test seeds; friction coefficients assumed (EXP-Q01)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_sim_skid_passive.png")); plt.close(fig)
    # example trace
    fig, axs = plt.subplots(2, 1, figsize=(7.2, 5.0), sharex=True)
    t = ref["t"]
    w = (t > 2.0) & (t < 3.5)
    refi = ref.ink()
    for i, key in enumerate(("neutral", "oracle")):
        r = runs[key]
        n = min(len(r["t"]), len(t))
        e = (r.ink()[:n] - refi[:n]) * 1e6
        ww = w[:n] & (r["contact"][:n] > 0) & (ref["contact"][:n] > 0)
        ee = np.where(ww, np.linalg.norm(e, axis=1), np.nan)
        axs[0].plot(t[:n][w[:n]], ee[w[:n]], color=S[i], lw=1.4, label={"neutral": "stage held", "oracle": "oracle correction"}[key])
    axs[0].set_ylabel("Ink error vs reference (µm)")
    axs[0].legend(fontsize=7.5, loc="upper right")
    r = runs["oracle"]
    n = min(len(r["t"]), len(t))
    axs[1].plot(t[:n][w[:n]], r["q1"][:n][w[:n]] * 1e3, color=S[0], lw=1.4, label="q1 (tilt plane)")
    axs[1].plot(t[:n][w[:n]], r["q2"][:n][w[:n]] * 1e3, color=S[1], lw=1.4, label="q2 (sideways)")
    axs[1].axhline(0.30, color=plotstyle.MUTED, lw=1.0); axs[1].axhline(-0.30, color=plotstyle.MUTED, lw=1.0)
    axs[1].set_ylabel("Stage deflection at nib (mm)")
    axs[1].set_xlabel("Time (s)")
    axs[1].legend(fontsize=7.5, loc="upper right")
    axs[0].set_title("Seed 200, 6 Hz / 0.3 mm tremor, 50°, 1 N: ink error and the oracle's stage motion", loc="left", fontsize=9.5)
    plotstyle.stamp(fig, "simulation", "model P1; not measured")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_sim_trace.png")); plt.close(fig)


def _r4(x):
    if isinstance(x, float):
        return float(f"{x:.4g}") if math.isfinite(x) and x != 0.0 else x
    if isinstance(x, dict):
        return {str(k): _r4(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r4(v) for v in x]
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--quick", action="store_true", help="2 seeds, fewer frequencies (smoke run)")
    a = ap.parse_args()
    global SEEDS, F0S
    if a.quick:
        SEEDS, F0S = (200, 201), (6.0, 10.0)
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    # warm the numba cache in this process first
    M.run(scenarios.handwriting(seed=1, duration=0.3), M.Controller(mode="neutral"))
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        grids = list(ex.map(grid_seed, SEEDS))
        passive = [r for rows in ex.map(passive_seed, SEEDS) for r in rows]
        sens = [r for rows in ex.map(sens_seed, SEEDS[:2]) for r in rows]
        gfeat = list(ex.map(guided_features, (0, 1, 2, 3)))
    grid_rows = [r for g in grids for r in g["rows"]]
    t_grid = time.time() - t0
    xc = m1_crosscheck()
    vz, runs, ref = viz()
    provenance.write_json(os.path.join(OUT, "viz_trace.json"), vz)
    figures(grid_rows, passive, runs, ref)
    P = D.Params()
    # summaries
    summ = {}
    for mode in ("neutral",) + CTRL:
        for key in ("ratio", "e_rms_um", "q_sat_frac", "P_rail_classB_mW", "P_rail_recovery_mW", "e_band_rms_um"):
            a_ = agg([r for r in grid_rows if r["mode"] == mode], ("f0", "amp_mm"), key)
            summ.setdefault(mode, {})[key] = {f"{f:g}Hz_{amp:g}mm": {"mean": v[0], "sd": v[1], "n": v[2]} for (f, amp), v in sorted(a_.items())}
    g_path = agg([r for r in grid_rows if r["mode"] == "guided"], ("f0", "amp_mm"), "path_ratio")
    summ["guided"]["path_distance_ratio_vs_neutral"] = {f"{f:g}Hz_{amp:g}mm": {"mean": v[0], "sd": v[1], "n": v[2]} for (f, amp), v in sorted(g_path.items())}
    pas = {}
    for name in PASSIVE:
        for key in ("housing_band_rms_um", "e_rms_um", "e_band_rms_um"):
            a_ = agg([r for r in passive if r["config"] == name], ("f0",), key)
            pas.setdefault(name, {})[key] = {f"{f:g}Hz": {"mean": v[0], "sd": v[1]} for (f,), v in sorted(a_.items())}
    for key in ("housing_band_rms_um", "e_rms_um", "e_band_rms_um"):
        for name in ("skid_on", "skid_frictionless"):
            ratios = {}
            for f in F0S:
                num = np.mean([r[key] for r in passive if r["config"] == name and r["f0"] == f])
                den = np.mean([r[key] for r in passive if r["config"] == "conventional_locked" and r["f0"] == f])
                ratios[f"{f:g}Hz"] = float(num / den)
            pas.setdefault("ratios_vs_conventional", {})[f"{name}_{key}"] = ratios
    sens_s = {}
    for r in sens:
        d = sens_s.setdefault(r["variant"], {}).setdefault(f"{r['f0']:g}Hz", {})
        for k, v in r.items():
            if k in ("seed", "variant", "f0"):
                continue
            d.setdefault(k, []).append(v)
    sens_s = {v: {f: {k: float(np.mean(x)) for k, x in d.items()} for f, d in fd.items()} for v, fd in sens_s.items()}
    p_el = P["electronics.p_active"]
    batt = battery_table(grid_rows, p_el)
    for var in ("Q26_hall_0.3um", "Q26_hall_0"):
        for f in ("6Hz", "10Hz"):
            for mode in ("neutral", "oracle"):
                v = sens_s.get(var, {}).get(f, {})
                if not v:
                    continue
                pb, pr = v[f"{mode}_P_rail_classB_mW"] * 1e-3, v[f"{mode}_P_rail_recovery_mW"] * 1e-3
                row = {}
                for dk, prail in (("drv2700", pb), ("recovery", pr)):
                    Pt = p_el + PW.battery_power(dk, prail)
                    row[dk] = {"P_rail_mW": prail * 1e3, "P_total_W": Pt, "energy_per_hour_mWh": Pt * 1e3, "life_h": PW.battery_life_h(Pt)}
                batt[f"{mode} {f}, {var.split('_', 1)[1].replace('hall_', 'Hall noise ').replace('um', ' um')}"] = row
    gf = {}
    for d in gfeat:
        for k, v in d.items():
            gf.setdefault(k, []).extend(v)
    guided_feat = {}
    for (name, feat), ds in gf.items():
        dd = np.concatenate(ds) * 1e6
        guided_feat.setdefault(feat, {})[name] = {"rms_um": float(np.sqrt(np.mean(dd ** 2))), "p95_um": float(np.percentile(dd, 95))}
    meta = provenance.metadata("simulation (pencil model P1, synthetic handwriting and tremor; nothing measured)",
                               seeds={"test": list(SEEDS), "sensitivity": list(SEEDS[:2]), "crosscheck": 5, "viz": 200}, p=P.pencil,
                               extra={"model_version": M.MODEL_VERSION, "parameters_base_version": P.base.version(),
                                      "dt_s": 25e-6, "record_Hz": 2000, "duration_s": DUR, "workers": a.workers,
                                      "elapsed_s": round(time.time() - t0, 1), "grid_elapsed_s": round(t_grid, 1),
                                      "kalman_frozen_params": M.frozen_kf(), "script": "sim/pencil/run_study.py"})
    out = {"meta": meta,
           "protocol": {"reference": "same pencil, NEUTRAL, same handwriting without tremor (harness convention)",
                        "ratio": "e_rms(controller, tremor) / e_rms(neutral, tremor), both against the reference",
                        "distortion": "controller on the tremor-free handwriting against the reference",
                        "oracle": "disturbance = housing position minus its clean (neutral, no tremor) path",
                        "q_sat_frac": "fraction of evaluated contact time with the command at >= 95 % of the 0.30 mm soft limit, the drive voltage saturated, or the stage on its stop",
                        "P_rail": "mean rail power over the run (both axes): class-B/switch-to-rail and charge-recovery conventions (sim/pencil/power.py)",
                        "integration": "symplectic Euler, dt 25 us (highest modes: nib-paper contact 1.2 kHz, stage 192 Hz; omega*dt <= 0.19); servo 10 kHz, estimator 2 kHz"},
           "grid_summary": summ,
           "distortion_um": {m: float(np.mean([g["distortion_um"][m] for g in grids])) for m in ("kfosc", "guided")},
           "device_distortion_rigid_vs_neutral_um": float(np.mean([g["device_distortion_rigid_vs_neutral"]["detrended_rms_um"] for g in grids])),
           "device_distortion_decomposition_um": {k: float(np.mean([g[k]["detrended_rms_um"] for g in grids])) for k in
                                                  ("device_distortion_skid_locked_vs_rigid", "device_distortion_neutral_vs_skid_locked")},
           "guided_feature_course_path_distance": guided_feat,
           "skid_passive": pas, "sensitivity": sens_s, "servo_check": servo_check(), "m1_crosscheck": xc,
           "battery": {"table": batt, "p_electronics_W": p_el, "capacity_mAh": P["battery.capacity_mAh"],
                       "note": "rail powers from the simulation (1 um Hall noise at 10 kSPS included); DRV2700 quiescent 72 mW, recovery stage 1 mW"},
           "grid_rows": grid_rows}
    provenance.write_json(os.path.join(OUT, "sim_metrics.json"), _r4(out))
    # console
    for mode in CTRL:
        print(mode, {k: round(v["mean"], 3) for k, v in summ[mode]["ratio"].items()})
    print("q_sat oracle", {k: round(v["mean"], 3) for k, v in summ["oracle"]["q_sat_frac"].items()})
    print("distortion", out["distortion_um"], "device", out["device_distortion_rigid_vs_neutral_um"])
    print("passive ratios", pas["ratios_vs_conventional"])
    print("m1 crosscheck", xc)
    print("battery", {k: {dk: round(v["life_h"], 2) for dk, v in row.items()} for k, row in batt.items()})
    print("device decomposition", out["device_distortion_decomposition_um"])
    print("guided features", {k: {n: round(v['rms_um']) for n, v in d.items()} for k, d in guided_feat.items()})
    print("viz metrics", [(c["key"], c["metrics"]) for c in vz["cases"]])
    print("elapsed", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
