"""Assemble results/sim2/ from the stage caches: JSON (with stabpen provenance), figures with CSV twins, the proposed
evidence rows (23-column ledger header) and a short replay in the viewer's format.  Every number is SIMULATION or
CALCULATION of simulator v2 unless a row says otherwise."""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List

import numpy as np

from stabpen import provenance

from . import ROOT

OUT = os.path.join(ROOT, "results", "sim2")
CACHE = os.path.join(OUT, "_cache")
STATUS = "SIMULATION (simulator v2, MuJoCo 3.6; synthetic writing and tremor; nothing measured)"


def _load(name, quick):
    p = os.path.join(CACHE, "quick" if quick else "", f"stage_{name}.json")
    if not os.path.exists(p) and quick:
        p = os.path.join(CACHE, f"stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k != "meta"}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _write(path, obj, status=STATUS, extra=None):
    obj = dict(obj)
    obj["meta"] = provenance.metadata(status, extra=dict(extra or {}, script="sim2/run_study.py --stages report"))
    provenance.write_json(path, obj)


def _csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([("%.6g" % v) if isinstance(v, float) else v for v in r])


# ============================================================================================ figures
def _fig_h1(h1, out_dir, log):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    PS.apply()
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.2))
    rows_csv = []
    for j, (ctl, tol) in enumerate((("oracle", 0.03), ("akf", 0.05))):
        ax = axs[j]
        lo, hi = 1.0, 0.0
        for k, (sp, res) in enumerate(sorted(h1["splits"].items())):
            x = np.array([r[f"h1_{ctl}"] for r in res["rows"]])
            y = np.array([r[f"s2_{ctl}"] for r in res["rows"]])
            lo, hi = min(lo, x.min(), y.min()), max(hi, x.max(), y.max())
            ax.plot(x, y, label=f"r_rot {sp}", **PS.marker_kw(PS.SERIES[k]))
            for r in res["rows"]:
                rows_csv.append([ctl, float(sp), r["seed"], r["f0"], r["amp_mm"], r["kind"], r[f"h1_{ctl}"], r[f"s2_{ctl}"],
                                 r[f"d_{ctl}"], r["unmod_rel"]])
        g = np.linspace(lo - 0.02, hi + 0.02, 10)
        ax.plot(g, g, color=PS.INK2, linewidth=1.0)
        ax.fill_between(g, g - tol, g + tol, color=PS.GRID, alpha=0.6, linewidth=0, label=f"tolerance +-{tol}")
        ax.set_xlabel(f"H1 ratio ({'perfect knowledge' if ctl == 'oracle' else 'causal AKF'})")
        ax.set_ylabel("sim2 ratio")
        ax.set_title("oracle (perfect knowledge)" if ctl == "oracle" else "causal tracker (Rev H AKF)")
        ax.legend(loc="upper left")
    PS.stamp(fig, "SIMULATION", "sim2 vs H1, test seeds 200-203, ink error ratio")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_sim2_h1check.png"))
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_sim2_h1check.csv"),
         ["controller", "r_rot", "seed", "f0_Hz", "amp_mm", "kind", "h1_ratio", "sim2_ratio", "difference", "unmod_rel_diff"], rows_csv)


def _fig_convergence(cv, out_dir):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    PS.apply()
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.0))
    rows = []
    for k, key in enumerate(("h1_contact", "native_contact")):
        if key not in cv:
            continue
        rr = cv[key]["rows"]
        dts = [r["dt_us"] for r in rr]
        axs[0].plot(dts[1:], [max(r["ink_path_diff_um"], 1e-6) for r in rr[1:]], label=key.replace("_", " "),
                    color=PS.SERIES[k], marker="o")
        axs[1].plot(dts, [r["oracle_ratio"] for r in rr], label=key.replace("_", " "), color=PS.SERIES[k], marker="o")
        for r in rr:
            rows.append([key, r["integrator"], r["dt_us"], r["unmod_e_rms_um"], r["oracle_ratio"], r["ink_path_diff_um"],
                         r.get("observed_order")])
    for r in cv.get("integrators", []):
        for x in r["rows"]:
            rows.append(["h1_contact", x["integrator"], x["dt_us"], x["unmod_e_rms_um"], x["oracle_ratio"], None, None])
    axs[0].set_xscale("log")
    axs[0].set_yscale("log")
    axs[0].set_xlabel("time step (us)")
    axs[0].set_ylabel("ink path difference vs finest step (um rms)")
    axs[0].legend()
    axs[1].set_xscale("log")
    axs[1].set_xlabel("time step (us)")
    axs[1].set_ylabel("oracle ink error ratio")
    PS.stamp(fig, "SIMULATION", "seed 300, 8 Hz 1 mm, Rev H-B")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_sim2_convergence.png"))
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_sim2_convergence.csv"),
         ["contact", "integrator", "dt_us", "unmod_e_rms_um", "oracle_ratio", "ink_path_diff_vs_finest_um", "observed_order"], rows)


def _fig_myo(myo, out_dir):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    from . import myo as MY
    PS.apply()
    fig, axs = plt.subplots(1, 3, figsize=(12, 4.0), sharey=True)
    rows = []
    for i, ax_n in enumerate("xyz"):
        ax = axs[i]
        for k, r in enumerate(myo["rows"]):
            f = np.array(r["freqs_Hz"])
            C = np.array(r["dynamic_fit"][ax_n]["compliance_mag_m_per_N"])
            m = f >= 0.5
            ax.plot(f[m], 1.0 / C[m], label=f"MyoArm c {r['cocontraction']:.2f}", color=PS.SEQ_BLUE[min(k + 1, 6)])
            for ff, cc in zip(f[m], C[m]):
                rows.append([ax_n, "MyoArm", r["cocontraction"], ff, 1.0 / cc])
        f = np.array(myo["rows"][0]["freqs_Hz"])
        f = f[f >= 0.5]
        hp = MY.HAP26[MY.AXIS_MAP[ax_n]]
        zh = 1.0 / np.abs(MY.two_mass_compliance(f, **hp))
        z1 = 1.0 / np.abs(MY.two_mass_compliance(f, **MY.H1_TIP))
        ax.plot(f, zh, color=PS.SERIES[1], label=f"HAP-26 {MY.AXIS_MAP[ax_n]} (nominal)")
        ax.plot(f, z1, color=PS.SERIES[2], linestyle="--", label="H1 tip")
        for ff, a, b in zip(f, zh, z1):
            rows.append([ax_n, "HAP-26", None, ff, a])
            rows.append([ax_n, "H1", None, ff, b])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("frequency (Hz)")
        ax.set_title(f"MyoArm {ax_n} (HAP-26 {MY.AXIS_MAP[ax_n]})")
    axs[0].set_ylabel("|Z| at the pen point (N/m)")
    axs[2].legend(fontsize=7)
    PS.stamp(fig, "SIMULATION", "MyoSuite MyoArm, Hill-type muscles, linearised; HAP-26 = LIT")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_sim2_myo.png"))
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_sim2_myo.csv"), ["axis", "model", "cocontraction", "f_Hz", "Z_abs_N_per_m"], rows)


def _fig_arm(arm, out_dir):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    PS.apply()
    cal = arm["calibration"]
    f = np.array(cal["freqs"])
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    rows = []
    for i, d in enumerate("xyz"):
        ax = axs[i]
        a = np.array(cal["H_arm"][d])
        h = np.array(cal["H_h1"][d])
        ax.plot(f, 1.0 / a, color=PS.SERIES[0], marker="o", label="arm (fitted)")
        ax.plot(f, 1.0 / h, color=PS.SERIES[1], linestyle="--", label="H1 hand + grip")
        for ff, x, y in zip(f, a, h):
            rows.append([d, ff, 1.0 / x, 1.0 / y])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"pen tip, page {d}")
        ax.set_xlabel("frequency (Hz)")
    axs[0].set_ylabel("|Z| at the pen tip (N/m), pen lifted")
    axs[0].legend()
    PS.stamp(fig, "SIMULATION", f"arm joint impedance fitted to H1 (rms rel. error {cal['rms_rel_error']:.2f})")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_sim2_arm.png"))
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_sim2_arm.csv"), ["axis", "f_Hz", "Z_arm_N_per_m", "Z_h1_N_per_m"], rows)


def _fig_validate(va, out_dir):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    PS.apply()
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.0))
    rows = []
    for k, key in enumerate(("writer_lognormal", "writer_glyph")):
        w = va.get(key) or {}
        if "spectrum_Hz" not in w:
            continue
        f = np.array(w["spectrum_Hz"])
        p = np.array(w["spectrum_rel"])
        axs[0].plot(f, p, color=PS.SERIES[k], label=key.replace("writer_", "") + " writer (sim2 input)")
        for ff, pp in zip(f, p):
            rows.append(["velocity_spectrum", key, ff, pp])
    # CON-25 (UCI Character Trajectories): cumulative velocity energy 50 % by 3.1 Hz, 90 % by 4.9 Hz, 95 % by 5.9 Hz
    for q, fq in ((0.5, 3.1), (0.9, 4.9), (0.95, 5.9), (0.99, 9.3)):
        axs[0].axvline(fq, color=PS.MUTED, linewidth=0.8)
        axs[0].text(fq, 1.02, f"{int(q * 100)}%", fontsize=7, color=PS.INK2, ha="center")
    axs[0].set_xlabel("frequency (Hz)")
    axs[0].set_ylabel("velocity PSD (relative)")
    axs[0].set_title("writing velocity spectrum (lines: CON-25 cumulative energy)")
    axs[0].set_xlim(0, 15)
    axs[0].legend()
    wr = va.get("wrist_resonance")
    if wr:
        f = np.array(wr["freqs_Hz"])
        for k, lbl in enumerate(("nominal", "loaded")):
            c = np.array(wr[lbl]["curve_mm_per_Nm"])
            fn = wr[lbl].get("f_n_wrist_Hz")
            axs[1].plot(f, c, color=PS.SERIES[k], label=f"{lbl} (+{wr[lbl]['extra_mass_kg'] * 1e3:.0f} g): tip peak {wr[lbl]['peak_Hz']:.1f} Hz"
                        + (f", wrist f_n {fn:.1f} Hz" if fn else ""))
            for ff, cc in zip(f, c):
                rows.append(["wrist_resonance", lbl, ff, cc])
        axs[1].set_xlabel("frequency (Hz)")
        axs[1].set_ylabel("pen-tip motion per wrist torque (mm per N m)")
        axs[1].set_title("hand-wrist mechanical resonance (arm model)")
        axs[1].legend()
    PS.stamp(fig, "SIMULATION", "sim2 writers and arm model; CON-25 = LIT")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_sim2_validation.png"))
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_sim2_validation.csv"), ["panel", "series", "f_Hz", "value"], rows)


def _fig_contact(ct, out_dir):
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    PS.apply()
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    rows = []
    names = [r["name"] for r in ct["native_block"]]
    creep = [r["creep"]["v_creep_m_s"] * 1e6 for r in ct["native_block"]]
    glide = [r["gliding"]["mean_gap_um"] for r in ct["native_block"]]
    x = np.arange(len(names))
    axs[0].bar(x - 0.2, creep, width=0.4, color=PS.SERIES[0], label="creep in stick at 0.5 mu N (um/s)")
    axs[0].bar(x + 0.2, glide, width=0.4, color=PS.SERIES[1], label="gliding gap at 20 mm/s (um)")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(names, fontsize=7)
    axs[0].set_yscale("log")
    axs[0].legend(fontsize=7)
    axs[0].set_title("MuJoCo soft contact artefacts (20 g block)")
    for n_, c_, g_ in zip(names, creep, glide):
        rows.append(["native_block", n_, "creep_um_s", c_])
        rows.append(["native_block", n_, "gliding_gap_um", g_])
    ps = ct.get("pen_sliding", [])
    lab = [f"{r['solref'][0] * 1e3:g} ms/{r['impratio']:g}{'/ns' if r.get('noslip_iterations', 0) else ''} {tuple(r['dir'])}" for r in ps]
    cv = [r["Ns_cv"] for r in ps]
    axs[1].bar(np.arange(len(ps)), cv, color=PS.SERIES[2])
    axs[1].set_xticks(np.arange(len(ps)))
    axs[1].set_xticklabels(lab, rotation=60, fontsize=6)
    axs[1].set_ylabel("skid normal force std/mean")
    axs[1].set_title("pen sliding at 20 mm/s: chatter index")
    for l_, r in zip(lab, ps):
        rows.append(["pen_sliding", l_, "Ns_cv", r["Ns_cv"]])
        rows.append(["pen_sliding", l_, "mu_apparent", r["mu_apparent"]])
    PS.stamp(fig, "SIMULATION", "verify.py")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_sim2_contact.png"))
    plt.close(fig)
    _csv(os.path.join(out_dir, "fig_sim2_contact.csv"), ["test", "setting", "quantity", "value"], rows)


# ============================================================================================ replay
def replay(out_dir, seed=300, f0=8.0, amp=1.0e-3, window=(1.0, 3.5), rate=200.0, log=print):
    """Short replay (viewer format, as results/opt/viz_inertial_opt.json): unmodified, oracle and causal Rev H nose in
    sim2 with the H1 hand, training seed 300."""
    from sim.handpen import evaluate as HE
    from . import builder as B, h1compare as HC, params as P, sensors as SN, sim as S
    cfg = P.Config(hand=P.HandH1(r_rot=0.5, lock_roll=True))
    pm = B.build(cfg)
    sc, sc0 = HC.scenario(seed, f0, amp)
    ref = S.run(pm, sc0)
    un = S.run(pm, sc)
    n_ticks = int(math.ceil(len(sc.t) / 20))
    orc = S.run(pm, sc, S.RunOptions(source="oracle", clean=S.clean_ticks(ref, n_ticks)))
    dh, info, _ = SN.akf_estimate(un, seed + 7000, cfg.geom.z_imu, SN.revh_params(), n_ticks=n_ticks)
    cau = S.run(pm, sc, S.RunOptions(source="external", dhat=dh))
    tt = np.arange(window[0], window[1], 1.0 / rate)
    it = lambda r, ch: np.interp(tt, r["t"], r[ch])
    mu = HE.compare(un, ref)
    ref_nib = np.column_stack([it(ref, "ballx"), it(ref, "bally"), it(ref, "ballz")])
    cases = []
    for key, lbl, desc, r in (("unmodified", "Rev H, no correction", "Rev H pen in sim2 (MuJoCo), nose held centred.", un),
                              ("oracle", "Rev H, perfect knowledge", "The nose cancels the true tremor deviation of the handle tip.", orc),
                              ("causal", "Rev H, causal tracker", "The Rev H AKF estimates the tremor from the pen's IMU and page sensor.", cau)):
        m = HE.compare(r, ref)
        nib = np.column_stack([it(r, "ballx"), it(r, "bally"), it(r, "ballz")])
        axis = np.column_stack([it(r, "ax"), it(r, "ay"), it(r, "az")])
        cases.append({"key": key, "label": lbl, "description": desc, "nib": np.round(nib, 7).tolist(),
                      "axis": np.round(axis, 5).tolist(),
                      "tilt_rad": np.round(np.column_stack([it(r, "b1"), it(r, "b2")]), 7).tolist(),
                      "grip": np.round(np.column_stack([it(r, "handx"), it(r, "handy"), it(r, "handz")]), 7).tolist(),
                      "ref_nib": np.round(ref_nib, 7).tolist(), "ref_ink": np.round(ref_nib[:, :2], 7).tolist(),
                      "ink": np.round(nib[:, :2], 7).tolist(), "pen_down": (it(r, "contact") > 0.5).astype(int).tolist(),
                      "device": {"type": "active_nose"},
                      "metrics": {"ink_err_rms_um": round(m["e_rms_um"], 2), "band_rms_um": round(m["e_band_rms_um"], 2),
                                  "ratio_vs_unmodified": round(m["e_rms_um"] / mu["e_rms_um"], 4), "q_sat_frac": round(m["q_sat_frac"], 4)}})
    intended = np.column_stack([np.interp(tt, sc.t, sc.intended[:, 0]), np.interp(tt, sc.t, sc.intended[:, 1])])
    obj = {"units": {"length": "m", "time": "s", "angle": "rad", "force": "N", "torque": "N m"},
           "t": np.round(tt, 4).tolist(), "intended": np.round(intended, 7).tolist(), "cases": cases}
    _write(os.path.join(out_dir, "viz_sim2.json"), obj, extra={"seeds": {"handwriting": seed, "tracker_noise": seed + 7000},
                                                            "scenario": f"opt.inertial.scen.get({seed}, tremor({f0}, {amp}))",
                                                            "model_version": "sim2-0.1 (H1 hand, H1 contact law, ring skid)",
                                                            "window_s": list(window), "rate_Hz": rate})
    log(f"  replay: " + ", ".join(f"{c['key']} {c['metrics']['ink_err_rms_um']:.0f} um ({c['metrics']['ratio_vs_unmodified']:.3f})" for c in cases))


# ============================================================================================ build
def build(quick=False, log=print):
    out_dir = os.path.join(OUT, "_quick_report") if quick else OUT
    os.makedirs(out_dir, exist_ok=True)
    st = {n: _load(n, quick) for n in ("h1check", "diagnose", "streams", "attrib", "contact", "convergence", "energy", "gyro",
                                       "sensors", "native", "frontstop", "arm", "myo", "validate", "env", "plugins")}
    if st["env"]:
        from . import env as E            # the DR table as it stands in env.py (it may have changed after the env stage)
        st["env"]["dr"] = {k: {"low": v[0], "high": v[1], "scale": v[2], "source": v[3]} for k, v in E.DR.items()}
    avail = [k for k, v in st.items() if v is not None]
    log(f"  report: stages available {avail}")
    # ---- verification.json
    ver = {k: _strip(st[k]) for k in ("h1check", "diagnose", "streams", "attrib", "contact", "convergence", "energy", "gyro",
                                      "sensors", "native", "frontstop") if st[k]}
    _write(os.path.join(out_dir, "verification.json"), ver)
    if st["myo"]:
        _write(os.path.join(out_dir, "myo_impedance.json"), _strip(st["myo"]))
    val = {k: _strip(st[k]) for k in ("validate", "arm") if st[k]}
    if val:
        _write(os.path.join(out_dir, "validation.json"), val)
    if st["env"]:
        _write(os.path.join(out_dir, "env_benchmark.json"), _strip(st["env"]))
    if st["plugins"]:
        _write(os.path.join(out_dir, "plugins.json"), _strip(st["plugins"]))
    # ---- figures
    figs = []
    for name, fn, key in (("h1check", _fig_h1, "h1check"), ("convergence", _fig_convergence, "convergence"),
                          ("myo", _fig_myo, "myo"), ("arm", _fig_arm, "arm"), ("validation", _fig_validate, "validate"),
                          ("contact", _fig_contact, "contact")):
        if st[key]:
            try:
                if fn is _fig_h1:
                    fn(st[key], out_dir, log)
                else:
                    fn(st[key], out_dir)
                figs.append(name)
            except Exception as e:                      # a figure must not stop the report
                log(f"  figure {name} failed: {e!r}")
    # ---- evidence rows
    from . import evidence as EV
    rows = EV.rows(st)
    with open(os.path.join(out_dir, "evidence_rows.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EV.HEADER)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"  evidence rows: {len(rows)}")
    # ---- replay
    if not quick:
        try:
            replay(out_dir, log=log)
        except Exception as e:
            log(f"  replay failed: {e!r}")
    # ---- master summary
    summ = summary(st)
    summ["figures"] = [f"fig_sim2_{n}.png" for n in figs]
    summ["files"] = sorted(os.listdir(out_dir))
    _write(os.path.join(out_dir, "sim2.json"), summ)
    log(f"  report written to {out_dir}")


def summary(st: Dict) -> Dict:
    """Headline numbers per stage (each labelled in docs/sim_v2.md)."""
    s = {"simulator": "sim2-0.1", "label": STATUS}
    if st["h1check"]:
        s["h1check"] = {sp: _strip(res["summary"]) for sp, res in st["h1check"]["splits"].items()}
        s["h1check"]["tolerance"] = st["h1check"]["splits"]["0.5"]["tolerance"]
    if st["diagnose"]:
        s["diagnose"] = _strip(st["diagnose"])
    if st.get("streams"):
        s["streams"] = _strip(st["streams"])
    if st.get("attrib"):
        s["attrib"] = _strip(st["attrib"])
    if st["convergence"]:
        s["convergence"] = {k: [{kk: r.get(kk) for kk in ("dt_us", "integrator", "unmod_e_rms_um", "oracle_ratio", "ink_path_diff_um",
                                                          "observed_order", "wall_s")} for r in v["rows"]]
                            for k, v in st["convergence"].items() if isinstance(v, dict) and "rows" in v}
        if "integrators" in st["convergence"]:
            s["convergence"]["integrators"] = [r["rows"][0] for r in st["convergence"]["integrators"]]
    if st["energy"]:
        s["energy"] = [{k: r[k] for k in ("case", "integrator", "residual_rel", "dE_J", "E0_J")} for r in st["energy"]["rows"]]
    if st["gyro"]:
        s["gyro"] = {"max_rel_error": st["gyro"]["max_rel_error"]}
    if st["sensors"]:
        s["sensors"] = _strip(st["sensors"])
    if st["native"]:
        s["native"] = st["native"]["rows"]
    if st.get("frontstop"):
        s["frontstop"] = st["frontstop"]["rows"]
    if st["myo"]:
        s["myo"] = {"table": st["myo"].get("table"), "unstable": [(r["cocontraction"], r["n_unstable"], r["max_growth_per_s"])
                                                                  for r in st["myo"]["rows"]],
                    "two_mass_fits": [{"c": r["cocontraction"], **{ax: r["dynamic_fit"][ax]["two_mass_fit"] for ax in "xyz"}}
                                      for r in st["myo"]["rows"]]}
    if st["arm"]:
        a = st["arm"]
        s["arm"] = {"calibration": {k: a["calibration"][k] for k in ("arm", "multipliers", "rms_rel_error")},
                    "writer_tracking": a["writer_tracking"], "arm_vs_h1": a["arm_vs_h1"],
                    "tremor_calibration": a["tremor_calibration"]}
    if st["validate"]:
        v = st["validate"]
        s["validate"] = {k: ({kk: vv for kk, vv in v[k].items() if kk not in ("spectrum_Hz", "spectrum_rel")}
                             if isinstance(v.get(k), dict) else v.get(k)) for k in ("writer_lognormal", "writer_glyph")}
        s["validate"]["tremor_spectra"] = v.get("tremor_spectra")
        wr = v.get("wrist_resonance") or {}
        s["validate"]["wrist_resonance"] = {k: {kk: vv for kk, vv in wr[k].items() if kk != "curve_mm_per_Nm"}
                                            for k in ("nominal", "loaded") if k in wr}
    if st["env"]:
        s["env"] = {"speed": st["env"]["speed"], "rollouts": st["env"]["rollouts"], "plugin_env": st["env"].get("plugin_env")}
    if st["plugins"]:
        s["plugins"] = _strip(st["plugins"])
    return s
