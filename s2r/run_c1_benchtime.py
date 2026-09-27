#!/usr/bin/env python3
"""C1 part B: recovery error against instrument noise and test duration ("how much bench time").

For each experiment the virtual bench is run at several durations (hold times,
repeats, averages, chirp count and length, grid size) and instrument noise
levels (x1 = the protocol/assumed instrument class, x4, x16 worse), on fresh hidden
plants drawn inside the declared ranges, each with its own session systematics.
A second series at noise x1 turns the session systematics off (ideal calibration)
to show which floor more bench time cannot remove.

Bench time = recorded time plus per-record overheads (repositioning, zeroing,
cooling, settling) that are ASSUMPTIONS stated in each generator.
Evidence status: SIMULATION (virtual bench) + CALCULATION (identification).
Outputs: results/s2r/c1_bench_time.json, fig_c1_bench_time.png
Run: python3 -m s2r.run_c1_benchtime [--quick] [--only B05|B01B02|B03] [--replot]
     (about 10 min for all three on 2 single-threaded processes: B05 1 min, B01/B02 8 min, B03 1 min;
     run_all.sh calls it once per experiment and the parts merge into one JSON)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import s2r  # noqa: F401
from s2r import common, exp_b01b02, exp_b03, exp_b05, pipeline, twin
from s2r import instruments as ins
from s2r import truth as tr

B03_LEVELS = [("0.2 s holds, 4 step averages, 45 s thermal, no back-EMF",
               dict(hold=0.2, n_rep=1, n_avg=4, thermal_s=45.0, back_emf=False)),
              ("0.5 s holds, 16 averages, 90 s thermal, back-EMF",
               dict(hold=0.5, n_rep=1, n_avg=16, thermal_s=90.0, back_emf=True)),
              ("protocol: 2 s holds, 16 averages, 180 s thermal, back-EMF",
               dict(hold=2.0, n_rep=1, n_avg=16, thermal_s=180.0, back_emf=True)),
              ("2 s holds x3, 64 averages, 360 s thermal, back-EMF",
               dict(hold=2.0, n_rep=3, n_avg=64, thermal_s=360.0, back_emf=True))]
B05_LEVELS = [("2 chirps x 3 s", dict(n_chirps=2, T_c=3.0)), ("2 chirps x 10 s", dict(n_chirps=2, T_c=10.0)),
              ("4 chirps x 10 s", dict(n_chirps=4, T_c=10.0)),
              ("protocol: 10 chirps x 10 s", dict(n_chirps=10, T_c=10.0))]
B12_LEVELS = [("reduced grid x1 (1 N, 50 deg, +-t1)", dict(n_rep=1, reduced=True)),
              ("reduced grid x3", dict(n_rep=3, reduced=True)),
              ("protocol grid x1 (3 N x 2 angles x 4 directions)", dict(n_rep=1, reduced=False)),
              ("reduced grid x1, quarter-decade speeds (proposed)",
               dict(n_rep=1, reduced=True, speeds=exp_b01b02.QUARTER_SPEEDS))]
KEYS = {"B03": tr.GROUPS["B03_actuator"], "B05": tr.GROUPS["B05_stage"], "B01B02": tr.GROUPS["B01B02_contact"]}
# which dataset's bench time governs each parameter (for the per-parameter answer)
AC_BANDS = {  # relative half-width of the acceptance band the identified value is judged against (TUR >= 4)
    "actuator.Kf": ("AC-B03-01 +-10 %", 0.10), "actuator.R20": ("AC-B03-05 +-5 %", 0.05),
    "actuator.Rth_coil_amb": ("AC-B03-08 +-15 %", 0.15), "stage.k_tip": ("AC-B05-03 +-15 %", 0.15),
    "stage.m_eq": ("AC-B05-02 <= 12 g vs 13.7 g expected", (13.7 - 12.0) / 13.7),
    "stage.axial_k": ("AC-B05-08 1-5 kN/m vs 2 kN/m", 0.5),
    "writing.mu_eff": ("AC-B01-04 0.09-0.40 vs 0.15", 0.4), "writing.mu_static_ratio": ("AC-B01-05 1.0-2.0 vs 1.3", 0.23),
    "writing.stribeck_speed": ("AC-B02-02 0.5-10 mm/s vs 2 mm/s", 0.75),
    "writing.paper_stiffness": ("AC-B01-08 1e4-2e5 N/m vs 5e4", 0.8)}


def _trial(args):
    exp, li, kw, noise, syst, seed = args
    rng = np.random.default_rng(seed)
    full = twin.nominal_plant()
    group = {"B03": "B03_actuator", "B05": "B05_stage", "B01B02": "B01B02_contact"}[exp]
    t = tr.draw(rng, "inside", groups=[group])
    full.update(t["values"])
    t0 = time.time()
    if exp == "B03":
        ses = ins.draw_session(rng, systematic_scale=syst)
        ds = exp_b03.generate(full, rng, session=ses, noise_scale=noise, **kw)
        r = exp_b03.identify(ds, rng)
        per = {"actuator.Kf": ds["force"]["bench_s"] + ds.get("emf", {}).get("bench_s", 0.0),
               "actuator.R20": ds["r20"]["bench_s"], "actuator.L": ds["step"]["bench_s"] + ds["r20"]["bench_s"],
               "actuator.Rth_coil_amb": ds["thermal"]["bench_s"], "actuator.Cth_coil": ds["thermal"]["bench_s"]}
    elif exp == "B05":
        ses0 = ins.draw_session(rng)
        ds3 = exp_b03.generate(full, rng, session=ses0)
        kf = exp_b03.identify(ds3, rng)["estimates"]["actuator.Kf"]
        ses = ins.draw_session(rng, systematic_scale=syst)
        ds = exp_b05.generate(full, rng, session=ses, noise_scale=noise, seed0=seed % 10000 + 3, **kw)
        e3 = exp_b03.identify(ds3, rng)["estimates"]
        r = exp_b05.identify(ds, kf["value"], kf["u"], L_hat=e3["actuator.L"]["value"],
                             R20_hat=e3["actuator.R20"]["value"])
        chirp = (kw["n_chirps"] + 1) * (kw["T_c"] + exp_b05.TAIL + 5.0) + 600.0
        per = {k: chirp for k in KEYS["B05"]}
        per["stage.k_tip"] = chirp + ds["static"]["bench_s"]
        per["stage.axial_k"] = per["stage.axial_preload"] = ds["axial"]["bench_s"]
    else:
        ses = exp_b01b02.draw_rig_session(rng, systematic_scale=syst)
        ds = exp_b01b02.generate(full, rng, session=ses, noise_scale=noise, **kw)
        r = exp_b01b02.identify(ds, rng, n_boot=30)
        st = ds["steps"]["bench_s"]
        per = {"writing.mu_eff": st + ds["sliding"]["bench_s"], "writing.mu_static_ratio": st,
               "writing.stribeck_speed": st, "writing.paper_stiffness": ds["indent"]["bench_s"],
               "friction.x_presliding": ds["sweeps"]["bench_s"]}
    sc = pipeline.score(r["estimates"], full)
    return {"exp": exp, "level": li, "noise": noise, "syst": syst, "bench_s": r["bench_s"], "per_param_s": per,
            "score": {k: sc[k] for k in KEYS[exp] if k in sc}, "elapsed_s": time.time() - t0}


def _time_to(times, p95s, target):
    """Smallest bench time at which the p95 |error| is <= target (log-linear interpolation)."""
    order = np.argsort(times)
    t, e = np.asarray(times)[order], np.asarray(p95s)[order]
    if e[0] <= target:
        return float(t[0])
    for i in range(1, len(t)):
        if e[i] <= target:
            a = (math.log(target) - math.log(e[i - 1])) / (math.log(e[i]) - math.log(e[i - 1]))
            return float(math.exp(math.log(t[i - 1]) + a * (math.log(t[i]) - math.log(t[i - 1]))))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--replot", action="store_true", help="redraw the figure from the saved JSON")
    ap.add_argument("--only", default="", help="comma list of B03,B05,B01B02: run only these experiments (same "
                    "seeds as the full run) and merge them into an existing c1_bench_time.json, so each part "
                    "stays under the 25 min budget")
    a = ap.parse_args()
    if a.replot:
        plot(json.load(open(os.path.join(s2r.RESULTS, "c1_bench_time.json")))["table"])
        return
    sel = set(x.strip() for x in a.only.split(",") if x.strip()) or {"B03", "B05", "B01B02"}
    assert sel <= {"B03", "B05", "B01B02"}, sel
    nt = {"B03": 3 if a.quick else 24, "B05": 1 if a.quick else 6, "B01B02": 1 if a.quick else 5}
    noises = {"B03": (1.0, 4.0, 16.0), "B05": (1.0, 4.0), "B01B02": (1.0, 4.0)}
    levels = {"B03": B03_LEVELS, "B05": B05_LEVELS, "B01B02": B12_LEVELS}
    jobs = []
    seed = 5000
    for exp in ("B05", "B01B02", "B03"):
        for li, (_, kw) in enumerate(levels[exp]):
            combos = [(n, 1.0) for n in noises[exp]] + [(1.0, 0.0)]
            for noise, syst in combos:
                for _ in range(nt[exp]):
                    seed += 1
                    jobs.append((exp, li, kw, noise, syst, seed))
    jobs = [j for j in jobs if j[0] in sel]          # seeds are assigned before filtering: parts reproduce the full run
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(_trial, jobs, chunksize=1))
    elapsed = {"+".join(sorted(sel)): time.time() - t0}
    table = []
    for exp in ("B03", "B05", "B01B02"):
        if exp not in sel:
            continue
        for li, (label, kw) in enumerate(levels[exp]):
            combos = sorted({(r["noise"], r["syst"]) for r in rows if r["exp"] == exp and r["level"] == li})
            for noise, syst in combos:
                sub = [r for r in rows if r["exp"] == exp and r["level"] == li and r["noise"] == noise
                       and r["syst"] == syst]
                ent = {"exp": exp, "level": li, "label": label, "noise_scale": noise, "systematics": syst,
                       "bench_s_median": float(np.median([r["bench_s"] for r in sub])), "n": len(sub),
                       "trial_wall_s_median": float(np.median([r["elapsed_s"] for r in sub])), "params": {}}
                for k in KEYS[exp]:
                    e = np.array([r["score"][k]["rel_err"] for r in sub if k in r["score"]])
                    u = np.array([r["score"][k]["U95_rel"] for r in sub if k in r["score"]])
                    c = np.array([r["score"][k]["covered95"] for r in sub if k in r["score"]])
                    ent["params"][k] = {"rms": float(np.sqrt(np.mean(e ** 2))), "p95": float(np.percentile(np.abs(e), 95)),
                                        "U95_median": float(np.median(u)), "coverage95": float(np.mean(c)),
                                        "bench_s_param": float(np.median([r["per_param_s"][k] for r in sub]))}
                table.append(ent)
    out_path = os.path.join(s2r.RESULTS, "c1_bench_time.json")
    if a.only and os.path.exists(out_path):
        old = json.load(open(out_path))
        table = [e for e in old["table"] if e["exp"] not in sel] + table
        elapsed = {**old.get("elapsed_s_by_part", {}), **elapsed}
    # time to accuracy at protocol instruments (noise 1, systematics on)
    tta = {}
    for exp in ("B03", "B05", "B01B02"):
        if not any(e["exp"] == exp for e in table):
            continue
        ents = sorted([e for e in table if e["exp"] == exp and e["noise_scale"] == 1.0 and e["systematics"] == 1.0],
                      key=lambda e: e["bench_s_median"])
        for k in KEYS[exp]:
            ts = [e["params"][k]["bench_s_param"] for e in ents]
            ps = [max(e["params"][k]["p95"], 1e-6) for e in ents]
            floor = [e for e in table if e["exp"] == exp and e["noise_scale"] == 1.0 and e["systematics"] == 0.0]
            tta[k] = {"p95_by_level": ps, "bench_s_by_level": ts,
                      "p95_no_systematics_by_level": [e["params"][k]["p95"] for e in sorted(
                          floor, key=lambda e: e["bench_s_median"])],
                      **{f"time_to_{int(100 * g)}pct_s" if g >= 0.01 else f"time_to_{g * 100:.1f}pct_s":
                         _time_to(ts, ps, g) for g in (0.005, 0.01, 0.02, 0.05)}}
            if k in AC_BANDS:
                lab, hw = AC_BANDS[k]
                prot = [e for e in ents if e["label"].startswith("protocol")]
                if prot:
                    u = prot[0]["params"][k]["U95_median"]
                    tta[k]["TUR_protocol"] = {"criterion": lab, "band_rel": hw, "U95_rel": u,
                                              "TUR": hw / u if u > 0 else None}
    payload = {"levels": {"B03": [l for l, _ in B03_LEVELS], "B05": [l for l, _ in B05_LEVELS],
                          "B01B02": [l for l, _ in B12_LEVELS]},
               "table": table, "time_to_accuracy": tta, "elapsed_s": time.time() - t0,
               "elapsed_s_by_part": elapsed,
               "notes": ["noise_scale multiplies the random noise of every instrument channel",
                         "systematics 0 removes session gain, offset, angle and sync errors (ideal calibration)",
                         "bench time includes ASSUMED per-record overheads (see generators)"]}
    path = common.write_result("c1_bench_time", payload,
                               "SIMULATION (virtual bench) + CALCULATION (identification); bench times include ASSUMED overheads",
                               seeds={"first": 5001, "n_jobs": len(jobs)})
    plot(table)
    print(path, f"{time.time() - t0:.0f} s")
    for k, v in tta.items():
        print(f"{k:28s} p95 by level {[round(100 * x, 2) for x in v['p95_by_level']]} % ; no-syst "
              f"{[round(100 * x, 2) for x in v['p95_no_systematics_by_level']]} ; t(1%) {v.get('time_to_1pct_s')}")


SHORT = {"B03": ["0.2 s holds,\nno back-EMF", "0.5 s holds,\n+ back-EMF", "protocol\n(2 s holds)", "2 s holds x3,\n64 averages"],
         "B05": ["2 x 3 s", "2 x 10 s", "4 x 10 s", "protocol\n10 x 10 s"],
         "B01B02": ["reduced\ngrid", "reduced\ngrid x3", "protocol\ngrid", "reduced +\n1/4-decade"]}


def plot(table):
    from stabpen import plotstyle
    show = {"B03": ["actuator.Kf", "actuator.L", "actuator.Rth_coil_amb"],
            "B05": ["stage.m_eq", "stage.k_tip", "stage.zeta_open", "sensing.hall_delay"],
            "B01B02": ["writing.mu_eff", "writing.stribeck_speed", "friction.x_presliding"]}
    fig, axs = common.figure(1, 3, figsize=(14.0, 4.4))
    for ax, (exp, keys) in zip(axs, show.items()):
        levels = sorted({e["level"] for e in table if e["exp"] == exp})
        for j, k in enumerate(keys):
            for style, (noise, syst) in (("-", (1.0, 1.0)), ("--", (4.0, 1.0)), (":", (1.0, 0.0))):
                ents = {e["level"]: e for e in table if e["exp"] == exp and e["noise_scale"] == noise
                        and e["systematics"] == syst}
                if not ents:
                    continue
                x = [li for li in levels if li in ents]
                y = [100 * max(ents[li]["params"][k]["p95"], 1e-4) for li in x]
                ax.plot(x, y, style, color=plotstyle.SERIES[j], lw=1.6,
                        label=f"{k.split('.', 1)[1]}" if style == "-" else None)
                ax.plot(x, y, "o", color=plotstyle.SERIES[j], ms=3.5)
        prot = {e["level"]: e["bench_s_median"] / 60 for e in table if e["exp"] == exp and e["noise_scale"] == 1.0
                and e["systematics"] == 1.0}
        ax.set_xticks(levels, [f"{SHORT[exp][li]}\n{prot.get(li, float('nan')):.0f} min" for li in levels], fontsize=7.5)
        ax.set_yscale("log")
        ax.set_xlabel("test level and bench time for the experiment")
        ax.set_title({"B03": "EXP-B03 actuator coupon (24 per level)", "B05": "EXP-B05 stage FRF + statics (6 per level)",
                      "B01B02": "EXP-B01/B02 contact and friction (5 per level)"}[exp], loc="left", fontsize=9.5)
        ax.legend(fontsize=7.5)
    axs[0].set_ylabel("95th percentile |identification error| (%)")
    common.save_figure(fig, "fig_c1_bench_time", "simulation",
                       "solid: protocol instruments; dashed: noise x4; dotted: systematics removed (ideal calibration)")


if __name__ == "__main__":
    main()
