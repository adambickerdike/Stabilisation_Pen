r"""Figures (each with a CSV twin), samples.json (handwriting schema) and a short viewer replay for the Rev J
closed-loop study (SIMULATION; every figure is stamped with its evidence status)."""
from __future__ import annotations

import csv
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np

from . import RESULTS, ROOT, TEST_SEEDS, TEST_WRITERS, VERSION

STATUS = "SIMULATION (sim2) - ranks concepts (COU-1) until EXP-V01/V02/V04 calibrate and EXP-V05 validates"


def _load(name: str) -> Optional[Dict]:
    p = os.path.join(RESULTS, f"{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _csv(path: str, header: List[str], rows: List[list]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([("%.6g" % v) if isinstance(v, float) else v for v in r])


def _save(fig, name: str, header, rows, log=print):
    from stabpen import plotstyle as PS
    PS.stamp(fig, "SIMULATION", "sim2j/report.py")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, f"{name}.png"))
    import matplotlib.pyplot as plt
    plt.close(fig)
    _csv(os.path.join(RESULTS, f"{name}.csv"), header, rows)
    log(f"[report] {name}.png + .csv")


CTL_LABEL = {"none": "Ordinary pen (Rev J off)", "nose": "Rev J nose (chosen tracker)", "nose_guarded": "Nose, guarded tracker",
             "nose_gl": "Nose, ai2 gated listening", "nose_glg": "Nose, gated listening + guarded fallback",
             "nose_noguard": "Nose, Rev H tracker as built", "nose_wheel": "Rev J nose + heel wheel",
             "nose_wheel_ec": "Nose + wheel + end-cap", "oracle": "Perfect tremor knowledge (limit)", "rl": "Nose + RL arbiter"}


# ------------------------------------------------------------------------------------------------ figures
def fig_et(log=print) -> None:
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    et = _load("et")
    if not et:
        return
    PS.apply()
    cells = et["by_cell"]
    rl = _load("et_rl")
    if rl:
        cells = dict(cells, **{k: v for k, v in rl["by_cell"].items() if k.endswith("|rl")})
    ctls = [c for c in ("none", "nose", "nose_wheel", "oracle")          # the rest are in the tables (clarity)
            if any(k.endswith("|" + c) for k in cells)]
    f0s = sorted({float(k.split("|")[0]) for k in cells})
    fig, axs = plt.subplots(2, len(f0s), figsize=(4.0 * len(f0s), 6.4), sharey="row")
    rows = []
    for j, f0 in enumerate(f0s):
        for i, key in enumerate(("ink_err_um", "letters_read")):
            ax = axs[i, j]
            for ci, c in enumerate(ctls):
                pts = sorted((float(k.split("|")[1]), v) for k, v in cells.items()
                             if float(k.split("|")[0]) == f0 and k.split("|")[2] == c and key in v)
                if not pts:
                    continue
                x = [p[0] for p in pts]
                y = [p[1][key] * (100.0 if key == "letters_read" else 1.0) for p in pts]
                ax.plot(x, y, color=PS.SERIES[ci % 8], label=CTL_LABEL.get(c, c))
                ax.plot(x, y, **PS.marker_kw(PS.SERIES[ci % 8]))
                for p in pts:
                    rows.append([f0, p[0], c, key, p[1][key], p[1].get(key + "_sd"), p[1]["n"]])
            ax.set_xlabel("hand tremor (mm, peak)")
            ax.set_title(f"{f0:g} Hz tremor" + (": wobble left in the ink" if i == 0 else ": letters the app reads"))
            ax.set_ylabel("distance from own tremor-free letters (um rms)" if i == 0 else "letters read (%)")
    axs[0, 0].legend(fontsize=7)
    _save(fig, "fig_et", ["f0_Hz", "amp_mm", "controller", "metric", "mean", "sd", "n"], rows, log)


def fig_writers(log=print) -> None:
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    wr = _load("writers")
    if not wr:
        return
    PS.apply()
    fig, ax = plt.subplots(1, 1, figsize=(6.6, 4.0))
    rows = []
    for i, (name, k) in enumerate(wr["kinematics"].items()):
        f = np.asarray(k["spectrum_Hz"])
        p = np.asarray(k["spectrum_rel"])
        ax.semilogy(f, p, color=PS.SERIES[i], label=f"{name} (8-12 Hz share {100 * k['spectrum']['share_8_12']:.1f} %)")
        for fi, pi in zip(f, p):
            rows.append([name, float(fi), float(pi)])
    ax.axvspan(8, 12, color=PS.GRID, alpha=0.6, label="8-12 Hz (LIT CON-25: 1.3-1.7 % of the energy)")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("pen-down velocity PSD (relative)")
    ax.set_title("Writer models: velocity spectrum of the intended writing")
    ax.legend(fontsize=7)
    _save(fig, "fig_writers", ["population", "f_Hz", "psd_rel"], rows, log)


def fig_guided(log=print) -> None:
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    g = _load("guided")
    if not g:
        return
    PS.apply()
    fig, axs = plt.subplots(1, 3, figsize=(13.0, 4.0))
    rows = []
    for ax, (task, metric, lab) in zip(axs, (("tracing", "letters_read", "letters read as the target (%)"),
                                             ("lead", "letters_read", "letters read as the target (%)"),
                                             ("loops", "loop_height_ratio", "loop height / target"))):
        d = g.get(task) or {}
        names = list(d.keys())
        vals = [d[n].get(metric, float("nan")) * (100.0 if metric == "letters_read" else 1.0) for n in names]
        ax.bar(np.arange(len(names)), vals, color=[PS.SERIES[i % 8] for i in range(len(names))])
        ax.set_xticks(np.arange(len(names)))
        ax.set_xticklabels([n.replace("|", "\n") for n in names], fontsize=7, rotation=0)
        ax.set_ylabel(lab)
        ax.set_title({"tracing": "Dysgraphia tracing", "lead": "Dyslexia lead-through ('dug a deep')",
                      "loops": "PD 'write big' loops"}[task])
        for n, v in zip(names, vals):
            rows.append([task, n, metric, v, d[n].get("n")])
    _save(fig, "fig_guided", ["task", "controller", "metric", "mean", "n"], rows, log)


def fig_autowrite(log=print) -> None:
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    a = _load("autowrite")
    if not a:
        return
    PS.apply()
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.0))
    rows = []
    aw = a.get("autowrite", {})
    pts = sorted(((float(k.split("|")[1]), float(k.split("|")[0]), v) for k, v in aw.items()))
    for f0 in sorted({p[1] for p in pts}):
        x = [p[0] for p in pts if p[1] == f0]
        for ax, key, sc in ((axs[0], "letters_read", 100.0), (axs[1], "ink_err_um", 1.0)):
            y = [p[2].get(key, float("nan")) * sc for p in pts if p[1] == f0]
            ax.plot(x, y, marker="o", label=f"autowrite, {f0:g} Hz")
        for p in pts:
            if p[1] == f0:
                rows.append(["autowrite", f0, p[0], "letters_read", p[2].get("letters_read")])
                rows.append(["autowrite", f0, p[0], "ink_err_um", p[2].get("ink_err_um")])
    sev = a.get("severe", {})
    for ci, c in enumerate(("none", "nose", "nose_wheel", "oracle")):
        for f0 in (5.0, 8.0):
            pp = sorted((float(k.split("|")[1]), v) for k, v in sev.items()
                        if k.split("|")[2] == c and float(k.split("|")[0]) == f0)
            if not pp:
                continue
            axs[0].plot([p[0] for p in pp], [p[1].get("letters_read", float("nan")) * 100 for p in pp],
                        linestyle="--", marker="s", label=f"writing: {CTL_LABEL.get(c, c)}, {f0:g} Hz")
            for p in pp:
                rows.append([c, f0, p[0], "letters_read", p[1].get("letters_read")])
                rows.append([c, f0, p[0], "ink_err_um", p[1].get("ink_err_um")])
    axs[0].set_xlabel("tremor amplitude (mm, peak)")
    axs[0].set_ylabel("letters read by the app (%)")
    axs[0].set_title("Autowrite of a known text vs writing through the tremor")
    axs[0].legend(fontsize=6)
    axs[1].set_xlabel("tremor amplitude (mm, peak)")
    axs[1].set_ylabel("ink error to the planned letters (um)")
    axs[1].set_title("Autowrite ink error")
    axs[1].legend(fontsize=7)
    _save(fig, "fig_autowrite", ["controller", "f0_Hz", "amp_mm", "metric", "mean"], rows, log)


def fig_power(log=print) -> None:
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    p = _load("power")
    if not p:
        return
    PS.apply()
    fig, ax = plt.subplots(1, 1, figsize=(6.4, 4.0))
    rows = []
    calc = p["calc"]
    for i, (Fc, kms) in enumerate(sorted({(r["F_c_N"], r["km_scale"]) for r in calc})):
        rr = sorted([r for r in calc if r["F_c_N"] == Fc and r["km_scale"] == kms], key=lambda r: r["theta_deg"])
        ax.plot([r["theta_deg"] for r in rr], [r["P_static_W"] for r in rr], color=PS.SERIES[i],
                label=f"CALC, side load only: spring {Fc:g} N, Km x{kms:g}")
        for r in rr:
            rows.append(["calc", r["theta_deg"], Fc, kms, r["P_static_W"]])
    first = True
    sims = sorted([(k, v) for k, v in (p.get("sim") or {}).items() if k.endswith("|clean_none")],
                  key=lambda kv: kv[1]["P_nose_W"])
    for j, (k, v) in enumerate(sims):
        Fc, kms, case = k.split("|")
        if True:
            ax.plot([50.0], [v["P_nose_W"]], label="SIM: whole nose power, tremor-free writing (writer 0)" if first else None,
                    **PS.marker_kw(PS.SERIES[4]))
            ax.annotate(f"{float(Fc):g} N, Km x{float(kms):g}", (50.0, v["P_nose_W"]), xytext=(6, 6 if j % 2 == 0 else -6),
                        textcoords="offset points", fontsize=7, color=PS.INK2, va="center")
            first = False
            rows.append(["sim_nose_held_tremor_free", 50.0, float(Fc), float(kms), v["P_nose_W"]])
    ax.axhspan(0.064, 0.376, color=PS.GRID, alpha=0.8, label="the integrated budget's nose power, 0.06-0.38 W (results/revJ)")
    ax.set_xlabel("pen tilt (deg)")
    ax.set_ylabel("nose coil power (W)")
    ax.set_title("Holding the refill spring's side load at the ball costs the C1S nose watts")
    ax.legend(fontsize=7)
    _save(fig, "fig_power", ["kind", "theta_deg", "F_c_N", "km_scale", "P_W"], rows, log)


# ------------------------------------------------------------------------------------------------ samples / replay
def _path50(t, xy, down, hz: float = 50.0, t0: float = 0.0):
    tt = np.arange(t0, t[-1], 1.0 / hz)
    x = np.interp(tt, t, xy[:, 0]) * 1e3
    y = np.interp(tt, t, xy[:, 1]) * 1e3
    d = np.interp(tt, t, down.astype(float)) > 0.5
    return [[round(float(a), 2), round(float(b), 2), int(c)] for a, b, c in zip(x, y, d)]


def samples(log=print, w: int = 0) -> Dict:
    """Before/after strips of the Rev J pen (handwriting samples.json schema) for writer 0, first test seed: ET at 8 Hz
    x 1 mm and 2 mm (device off, the chosen tracker, + heel wheel, perfect knowledge), severe tremor 3 mm (device off
    vs autowrite of the same text at 2.5 mm)."""
    from stabpen import provenance as PV
    from . import et as ET
    from . import revj as RJ
    from . import stepper as ST
    from . import tasks as TK
    from .firmware import FWConfig
    from .run_study import et_seeds
    seed = et_seeds(w)[0]
    pens = ET.PenModels()
    su = ET.WriterSetup(w, pens, log=log)
    it = su.case.written.intended
    t0 = float(su.case.written.letters[0].t0) - 0.02          # after the 4 s rest (its ink is not part of the writing)
    intended = _path50(it.t, it.xy, it.pen_down, t0=t0)
    panels = []

    def panel(pid, title, cond, device, caption, r, m):
        ink = _path50(r["t"], r.ink(), r["contact"] > 0.5, t0=t0)
        keep = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()
                if k in ("ink_err_um", "letters_read", "words_app", "recognised", "P_total_W", "device_share",
                         "felt_rms_N", "ratio")}
        panels.append({"id": pid, "title": title, "condition": cond, "device": device, "caption": caption,
                       "evidence": "SIM", "intended": intended, "ink": ink, "metrics": keep})
    for amp in (1.0e-3, 2.0e-3):
        rn = ET.run_case(su, "none", 8.0, amp, seed, keep=True)
        r_none = rn.pop("_r")
        cap = (f"Writer {w} (v2), 'return library', hand tremor {amp * 1e3:g} mm peak at 8 Hz (seed {seed}), H1 hand, "
               f"Rev J pen (the lead's parameters). The same hand and tremor in every panel. Ink error = distance of the "
               f"ink to the writer's clean-ink letters.")
        panel(f"revj_none_8Hz_{amp * 1e3:g}mm", f"Device off - tremor {amp * 1e3:g} mm at 8 Hz", "et_tremor", "none",
              cap, r_none, rn)
        for c in ("nose", "nose_wheel", "oracle"):
            m = ET.run_case(su, c, 8.0, amp, seed, ref_none=r_none, keep=True)
            r = m.pop("_r")
            m["ratio"] = m["ink_err_um"] / rn["ink_err_um"]
            panel(f"revj_{c}_8Hz_{amp * 1e3:g}mm", f"{CTL_LABEL.get(c, c)} - tremor {amp * 1e3:g} mm at 8 Hz",
                  "et_tremor", c, cap, r, m)
            log(f"[samples] {c} {amp * 1e3:g} mm: {m['ink_err_um']:.0f} um")
    # severe tremor: device off vs autowrite (the same text, 2.5 mm letters)
    rn = ET.run_case(su, "none", 5.0, 3.0e-3, seed, keep=True)
    r_none = rn.pop("_r")
    panel("revj_none_5Hz_3mm", "Device off - severe tremor 3 mm at 5 Hz", "severe", "none",
          f"Writer {w}, 'return library', 3 mm peak at 5 Hz (seed {seed}).", r_none, rn)
    ac = TK.AutowriteCase(w, h_mm=2.5, version="v2", text=ET.ET_TEXT)
    if ac.ok:
        pm = RJ.build(RJ.config(heel=True, dt=50e-6))
        r = ST.run(pm, ac.scenario(5.0, 3.0e-3, seed), FWConfig(nose="autowrite", pen_lift="plan", seed=seed,
                                                                 reach=pm.cfg.geom.travel), ac.task(), seed=seed)
        m = ac.metrics(r)
        itp = ac.written.intended
        ink = _path50(r["t"], r.ink(), r["contact"] > 0.5)
        panels.append({"id": "revj_autowrite_5Hz_3mm", "title": "Autowrite (known text) - severe tremor 3 mm at 5 Hz",
                       "condition": "severe", "device": "autowrite",
                       "caption": "The hand sweeps the pen along the line; the nose writes the known text at 2.5 mm and "
                                  "lifts the ball between strokes (nose2 planner). Ink error = distance to the planned "
                                  "letters.", "evidence": "SIM",
                       "intended": [[round(a * 1e3, 2), round(b * 1e3, 2), int(c)] for (a, b), c in
                                    zip(itp.xy[::20], itp.pen_down[::20])],
                       "ink": ink, "metrics": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()
                                               if k in ("ink_err_um", "letters_read", "words_app", "recognised",
                                                        "letters_per_s", "P_total_W")}})
    meta = PV.metadata(STATUS, seeds={"writers": [w], "seeds": [seed]},
                       extra={"script": "sim2j/report.py", "version": VERSION,
                              "schema": "panels[{id, title, condition, device, caption, evidence, intended [[x_mm, y_mm, "
                                        "pen_down]], ink [[...]], metrics}]; paths at 50 Hz, 0.01 mm",
                              "units": "mm; page frame, x along the line, y up; pen_down 0/1",
                              "pen_source": RJ.lead()["meta"] if RJ.lead_available() else "round1"})
    out = {"meta": meta, "panels": panels}
    PV.write_json(os.path.join(RESULTS, "samples.json"), out)
    log(f"[report] samples.json: {len(panels)} panels")
    fig_samples(out, log)
    fig_handwriting(out, log)
    return out


def fig_samples(s: Dict, log=print) -> None:
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    PS.apply()
    P = s["panels"]
    fig, axs = plt.subplots(len(P), 1, figsize=(10.0, 1.25 * len(P)))
    rows = []
    for ax, p in zip(np.atleast_1d(axs), P):
        for key, col, lw in (("intended", PS.GRID, 3.0), ("ink", PS.INK, 1.0)):
            a = np.asarray(p[key], float)
            if len(a) == 0:
                continue
            seg = np.split(np.arange(len(a)), np.flatnonzero(np.diff(a[:, 2]) != 0) + 1)
            for sg in seg:
                if a[sg[0], 2] > 0.5 and len(sg) > 1:
                    ax.plot(a[sg, 0], a[sg, 1], color=col, linewidth=lw)
        ax.set_aspect("equal")
        ax.set_axis_off()
        mt = p["metrics"]
        ax.set_title(f"{p['title']}: ink {mt.get('ink_err_um', float('nan')):.0f} um, letters "
                     f"{100 * (mt.get('letters_read') or 0):.0f} %, read '{mt.get('recognised', '')}'", fontsize=8,
                     loc="left")
        rows.append([p["id"], p["device"], mt.get("ink_err_um"), mt.get("letters_read"), mt.get("words_app"),
                     mt.get("recognised")])
    _save(fig, "fig_before_after", ["panel", "device", "ink_err_um", "letters_read", "words_app", "recognised"], rows, log)


def fig_handwriting(s: Optional[Dict] = None, log=print) -> None:
    """Before/after as handwriting: the ink only, at true scale, blue-black ball-pen line on 8 mm ruled paper (SIM)."""
    import matplotlib.pyplot as plt
    from stabpen import plotstyle as PS
    s = s or (json.load(open(os.path.join(RESULTS, "samples.json"))) if os.path.exists(os.path.join(RESULTS, "samples.json")) else None)
    if not s:
        return
    want = [("revj_none_8Hz_1mm", "Ordinary pen, tremor 1 mm"), ("revj_nose_8Hz_1mm", "Rev J, tremor 1 mm"),
            ("revj_none_8Hz_2mm", "Ordinary pen, tremor 2 mm"), ("revj_nose_8Hz_2mm", "Rev J, tremor 2 mm"),
            ("revj_none_5Hz_3mm", "Ordinary pen, severe tremor 3 mm"),
            ("revj_autowrite_5Hz_3mm", "Rev J writes it (autowrite), severe tremor 3 mm")]
    P = {p["id"]: p for p in s["panels"]}
    rows_ = [(P[i], lab) for i, lab in want if i in P]
    if not rows_:
        return
    PS.apply()
    ink = "#1f2a44"
    fig, axs = plt.subplots(len(rows_), 1, figsize=(8.0, 1.35 * len(rows_)))
    csv_rows = []
    for ax, (p, lab) in zip(np.atleast_1d(axs), rows_):
        a = np.asarray(p["ink"], float)
        if len(a) == 0:
            continue
        a[:, 0] -= np.nanmin(a[:, 0])
        base = np.nanpercentile(a[a[:, 2] > 0.5, 1], 5) if np.any(a[:, 2] > 0.5) else 0.0
        a[:, 1] -= base
        for y in (0.0, 8.0):                                   # 8 mm ruled lines (the handwriting study's figures)
            ax.axhline(y - 1.0, color="#b9cbe0", linewidth=0.8)
        seg = np.split(np.arange(len(a)), np.flatnonzero(np.diff(a[:, 2]) != 0) + 1)
        for sg in seg:
            if a[sg[0], 2] > 0.5 and len(sg) > 1:
                ax.plot(a[sg, 0], a[sg, 1], color=ink, linewidth=1.3, solid_capstyle="round", solid_joinstyle="round")
        ax.set_aspect("equal")
        ax.set_xlim(-2, max(70.0, float(np.nanmax(a[:, 0])) + 2))
        ax.set_ylim(-4, 10)
        ax.set_axis_off()
        mt = p["metrics"]
        ax.text(-2, 9.2, f"{lab}: the app reads '{mt.get('recognised', '')}'", fontsize=8, color=PS.INK2, va="bottom")
        csv_rows.append([p["id"], lab, mt.get("recognised"), mt.get("letters_read"), mt.get("words_app"), mt.get("ink_err_um")])
    _save(fig, "fig_handwriting", ["panel", "label", "app_reads", "letters_read", "words_app", "ink_err_um"], csv_rows, log)


def replay(log=print, w: int = 0, rate: float = 200.0, window=(4.0, 7.0)) -> None:
    """A short replay in sim2's viewer format (results/sim2/viz_sim2.json): writer 0, 8 Hz x 1 mm, device off, the
    chosen tracker, + heel wheel, perfect knowledge."""
    from stabpen import provenance as PV
    from . import et as ET
    from .run_study import et_seeds
    seed = et_seeds(w)[0]
    su = ET.WriterSetup(w, ET.PenModels(), log=log)
    rn = ET.run_case(su, "none", 8.0, 1.0e-3, seed, keep=True)
    r_none = rn.pop("_r")
    ref = su.clean_ref(seed)
    tt = np.arange(window[0], window[1], 1.0 / rate)
    it = lambda r, ch: np.interp(tt, r["t"], r[ch])
    ref_nib = np.column_stack([it(ref, "ballx"), it(ref, "bally"), it(ref, "ballz")])
    cases = []
    runs = [("none", "Rev J, device off", "The Rev J pen in sim2, nose held centred, wheel retracted.", r_none, rn)]
    for c, lbl, desc in (("nose", "Rev J nose, chosen tracker", "The nose cancels the tracker's tremor estimate."),
                         ("nose_wheel", "Rev J nose + heel wheel", "The heel wheel damps and constrains; the nose cancels the rest."),
                         ("oracle", "Rev J nose, perfect knowledge", "The nose cancels the true tremor deviation (limit).")):
        m = ET.run_case(su, c, 8.0, 1.0e-3, seed, ref_none=r_none, keep=True)
        runs.append((c, lbl, desc, m.pop("_r"), m))
    for key, lbl, desc, r, m in runs:
        nib = np.column_stack([it(r, "ballx"), it(r, "bally"), it(r, "ballz")])
        cases.append({"key": key, "label": lbl, "description": desc, "nib": np.round(nib, 7).tolist(),
                      "axis": np.round(np.column_stack([it(r, "ax"), it(r, "ay"), it(r, "az")]), 5).tolist(),
                      "tilt_rad": np.round(np.column_stack([it(r, "b1"), it(r, "b2")]), 7).tolist(),
                      "grip": np.round(np.column_stack([it(r, "handx"), it(r, "handy"), it(r, "handz")]), 7).tolist(),
                      "ref_nib": np.round(ref_nib, 7).tolist(), "ref_ink": np.round(ref_nib[:, :2], 7).tolist(),
                      "ink": np.round(nib[:, :2], 7).tolist(), "pen_down": (it(r, "contact") > 0.5).astype(int).tolist(),
                      "device": {"type": "revJ_" + key},
                      "metrics": {"ink_err_rms_um": round(float(m["ink_err_um"]), 2),
                                  "ratio_vs_unmodified": round(float(m["ink_err_um"] / rn["ink_err_um"]), 4),
                                  "letters_read": m.get("letters_read"), "words_app": m.get("words_app")}})
    sc = su.case
    intended = np.column_stack([np.interp(tt, sc.t, sc.intended[:, 0]), np.interp(tt, sc.t, sc.intended[:, 1])])
    obj = {"units": {"length": "m", "time": "s", "angle": "rad", "force": "N", "torque": "N m"},
           "t": np.round(tt, 4).tolist(), "intended": np.round(intended, 7).tolist(), "cases": cases,
           "meta": PV.metadata(STATUS, seeds={"writer": w, "seed": seed},
                               extra={"script": "sim2j/report.py", "scenario": f"writer {w} v2, 'return library', 8 Hz x 1 mm",
                                      "model_version": f"{VERSION} (sim2 H1 hand, H1 contact law, Rev J pen)",
                                      "window_s": list(window), "rate_Hz": rate})}
    PV.write_json(os.path.join(RESULTS, "viz_sim2j.json"), obj)
    log("[report] viz_sim2j.json: " + ", ".join(f"{c['key']} {c['metrics']['ink_err_rms_um']:.0f} um" for c in cases))


def run_all(log=print, with_runs: bool = True) -> None:
    os.makedirs(RESULTS, exist_ok=True)
    try:                                              # the ET stage's rows + its second-seed pass, when present
        from . import BUILD
        if os.path.exists(os.path.join(BUILD, "et2_rows.json")):
            from .run_study import merge_et
            merge_et()
            log("[report] et.json merged with the second-seed pass")
    except Exception as e:
        log(f"[report] merge failed: {e!r}")
    for f in (fig_et, fig_writers, fig_guided, fig_autowrite, fig_power):
        try:
            f(log)
        except Exception as e:                      # a missing stage must not stop the others
            log(f"[report] {f.__name__} failed: {e!r}")
    if with_runs:
        samples(log)
        replay(log)


# ------------------------------------------------------------------------------------------------ tables for the doc
def _f(v, nd=0, pct=False):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return f"{100 * v:.{nd}f} %" if pct else f"{v:.{nd}f}"


def md_et() -> str:
    et = _load("et")
    if not et:
        return ""
    rl = _load("et_rl")
    cells = dict(et["by_cell"])
    if rl:
        cells.update({k: v for k, v in rl["by_cell"].items() if k.endswith("|rl") or k.endswith("|none")
                      and k.replace("|none", "|rl") in rl["by_cell"] and False})
        cells.update({k: v for k, v in rl["by_cell"].items() if k.endswith("|rl")})
    ctls = [c for c in ("none", "nose", "nose_gl", "nose_wheel", "nose_wheel_ec", "tcn", "rl", "oracle")
            if any(k.endswith("|" + c) for k in cells)]
    out = ["| Tremor | " + " | ".join(CTL_LABEL.get(c, c) for c in ctls) + " |",
           "|---|" + "---|" * len(ctls)]
    for f0 in sorted({float(k.split("|")[0]) for k in cells}):
        for amp in sorted({float(k.split("|")[1]) for k in cells}):
            row = []
            for c in ctls:
                v = cells.get(f"{f0:g}|{amp:g}|{c}")
                if not v:
                    row.append("–")
                elif c == "none":
                    row.append(f"{v['ink_err_um']:.0f} µm, {100 * v['letters_read']:.0f} %")
                else:
                    row.append(f"{v.get('ratio', float('nan')):.2f}, {100 * v['letters_read']:.0f} %")
            out.append(f"| {f0:g} Hz, {amp:g} mm | " + " | ".join(row) + " |")
    return "\n".join(out)


def print_all() -> None:
    for name in ("rules", "writers", "writer_cmp", "verify", "et", "et_rl", "guided", "autowrite", "dr", "arm", "dt_check",
                 "power", "rl_select", "rl_test"):
        d = _load(name)
        if d is None:
            print(f"## {name}: (missing)")
            continue
        d = {k: v for k, v in d.items() if k not in ("stabpen.provenance", "meta", "rows", "draws")}
        print(f"## {name}")
        print(json.dumps(d, indent=1, default=str)[:6000])
    print(md_et())


# ------------------------------------------------------------------------------------------------ plain-words table
def plain_table() -> str:
    """One understandable number per condition, ordinary pen -> Rev J (SIM means over the test writers)."""
    import numpy as np
    from . import BUILD

    def rows(n):
        p = os.path.join(BUILD, f"{n}_rows.json")
        return list(json.load(open(p)).values()) if os.path.exists(p) else []
    et = [r for r in rows("et") + rows("et2") if r.get("kind") == "tremor"]
    out = ["| Who | What Rev J does | Measure | Ordinary pen | Rev J |", "|---|---|---|---|---|"]

    def m(rs, key, sc=1.0):
        v = [r[key] * sc for r in rs if r.get(key) is not None]
        return float(np.mean(v)) if v else float("nan")
    for amp, lab in ((1.0, "moderate (1 mm)"), (2.0, "strong (2 mm)")):
        sel = lambda c: [r for r in et if r["ctl"] == c and abs(r["amp_mm"] - amp) < 1e-6 and r["f0"] >= 8]
        if sel("none") and sel("nose"):
            out.append(f"| Essential tremor, {lab}, 8–12 Hz | the nose cancels the tremor it detects | tremor left in "
                       f"the writing (mm, rms) | {m(sel('none'), 'ink_err_um', 1e-3):.2f} | "
                       f"{m(sel('nose'), 'ink_err_um', 1e-3):.2f} (nose); {m(sel('nose_wheel'), 'ink_err_um', 1e-3):.2f} "
                       f"(nose + wheel); limit {m(sel('oracle'), 'ink_err_um', 1e-3):.2f} |")
    sel4 = lambda c: [r for r in et if r["ctl"] == c and r["f0"] < 5 and r["amp_mm"] > 1.5]
    if sel4("none"):
        out.append(f"| Essential tremor at 4 Hz, 2 mm | the detector does not see 4 Hz; the heel wheel damps | tremor left "
                   f"(mm) | {m(sel4('none'), 'ink_err_um', 1e-3):.2f} | {m(sel4('nose'), 'ink_err_um', 1e-3):.2f} (nose); "
                   f"{m(sel4('nose_wheel'), 'ink_err_um', 1e-3):.2f} (nose + wheel) |")
    aw = [r for r in rows("autowrite") if r.get("task") == "autowrite" and r.get("plan_ok")]
    sev = [r for r in rows("autowrite") if r.get("task") == "severe"]
    if aw and sev:
        a3 = [r for r in aw if r["amp_mm"] == 3.0]
        s3 = [r for r in sev if r["ctl"] == "none" and r["amp_mm"] == 3.0]
        out.append(f"| Severe tremor (3 mm) | the pen writes a known text itself (autowrite) while the hand sweeps | "
                   f"letters the app reads | {m(s3, 'letters_read', 100):.0f} % | {m(a3, 'letters_read', 100):.0f} % |")
    g = rows("guided")
    lo = [r for r in g if r.get("task") == "loops"]
    if lo:
        out.append(f"| Parkinson's, small writing (loops shrink) | the wheel and nose hold the loops to the 10 mm template | "
                   f"loop height, % of target | {m([r for r in lo if r['ctl'] == 'none'], 'loop_height_ratio', 100):.0f} % | "
                   f"{m([r for r in lo if r['ctl'] == 'wheel_nose'], 'loop_height_ratio', 100):.0f} % |")
    tr = [r for r in g if r.get("task") == "tracing"]
    if tr:
        out.append(f"| Dysgraphia (malformed letters) | the nose pulls the ink onto the copybook letter; the wheel steers | "
                   f"distance from the copybook letters (mm) | {m([r for r in tr if r['ctl'] == 'none'], 'target_err_um', 1e-3):.2f} | "
                   f"{m([r for r in tr if r['ctl'] == 'wheel_nose'], 'target_err_um', 1e-3):.2f} |")
    ld = [r for r in g if r.get("task") == "lead"]
    if ld:
        out.append(f"| Dyslexia, led through 'dug a deep' (hand relaxed) | the wheel drives the pen along the right letters | "
                   f"letters read as the right letter | {m([r for r in ld if r['ctl'] == 'writer_alone'], 'letters_read', 100):.0f} % "
                   f"(writing alone) | {m([r for r in ld if r['ctl'] == 'lead_nose'], 'letters_read', 100):.0f} % |")
    a0 = [r for r in aw if r["amp_mm"] == 0.0]
    if a0:
        out.append(f"| Dyslexia or anyone: known text | autowrite | words right, out of 5 | – | "
                   f"{m(a0, 'words_app', 5):.1f} |")
    cl = [r for r in rows("et") if r.get("kind") == "clean"]
    if cl:
        out.append(f"| Anyone, no tremor | nothing should change | how far the pen moves normal writing (mm) | 0 | "
                   f"{m([r for r in cl if r['ctl'] == 'nose'], 'moved_vs_clean_um', 1e-3):.2f} (nose); "
                   f"{m([r for r in cl if r['ctl'] == 'nose_wheel'], 'moved_vs_clean_um', 1e-3):.2f} (with the wheel on) |")
    return "\n".join(out)
