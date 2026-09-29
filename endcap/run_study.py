#!/usr/bin/env python3
"""Study K (Rev J): the inertial / gyroscopic / pseudo-force end-cap.  Runs every stage and writes results/endcap/.

Stages (each caches results/endcap/_cache/stage_<name>.json; --quick writes to results/endcap/_cache/quick/ and never
touches the final results):
  scaling   closed-form ceilings, receptances of the Rev H hand-pen model, gyroscopic stiffening ratios   (CALC, seconds)
  optimise  CMA-ES design optimisation of every class, Pareto fronts, arrangements, larger budgets     (CALC, ~25 min)
  gradient  autograd (Adam) refinement of the 25 and 45 g optima; fixes the designs used below         (CALC, ~5 min)
  tune      feed-forward gain of the chosen LRM and CMG on TUNING seeds 300-303                         (SIM, ~5 min)
  test      tremor on top of the Rev H nose on TEST seeds 200-203, three grip splits, false correction   (SIM, ~30 min)
  steer     letter-scale steering at 1-5 Hz, single-stroke pulses, hand stiffness, voluntary correction  (SIM, ~3 min)
  gyro      gyroscopic stiffening: passive rotors with and without their mass                          (SIM, ~5 min)
  cue       pseudo-force cue: grip acceleration, ink jitter and drift; literature channel table        (SIM + CALC, ~2 min)
  offshelf  45 g CMG optima with catalogue motors only (no integrated-motor concept)                  (CALC, ~2 min)
  rw        reaction-wheel fronts with the corrected peak-power model (replaces the optimise stage's)    (CALC, ~4 min)
  budgets   larger envelopes redone with a second CMA-ES run and a warm-started Adam run              (CALC, ~8 min)
  report    results/endcap/endcap_study.json, figures (+CSV), evidence rows, layout_parts.json
Run: python3 -m endcap.run_study [--quick] [--stages a,b,...]
Rules (RULES below) were written into this file before the test stage was first run; the test stage records the time.
Evidence status: CALCULATION and SIMULATION on synthetic writing and tremor.  Nothing measured.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from stabpen import provenance  # noqa: E402
from endcap import params as P  # noqa: E402

OUT = os.path.join(ROOT, "results", "endcap")
CACHE = os.path.join(OUT, "_cache")

RULES = {
    "R-T1": "An end-cap device is 'worth fitting for tremor' if, on TEST seeds 200-203 with the causal Rev H tracker cascade, "
            "it adds >= 10 % further reduction of the ink error on top of the nose (mean over 8-12 Hz x 1-2 mm) at r_rot 0.5, "
            ">= 5 % at r_rot 0.3 and 0.7, no split worse on average, and fits 45 g / 0.3 W average.",
    "R-T2": "Among devices passing R-T1, rank by the further reduction at r_rot 0.5; ties (within 2 points) go to the lower "
            "average power, then the lower mass.",
    "R-S1": "'Can write' = >= 2 mm peak tip displacement at 1-3 Hz, repeatable, while writing with the relaxed HAP-26 hand "
            "(most favourable case); 'can nudge' = >= 0.2 mm; below 0.2 mm = a cue at most.",
    "R-G1": "A passive rotor is 'useful' if it lowers the ink error by >= 10 % at 4-12 Hz, 1 mm, r_rot 0.5, compared with the "
            "same mass without spin.",
    "R-C1": "A pseudo-force cue is 'usable while writing' only if its ink side effect is <= 30 um RMS during the cue; "
            "otherwise pen-up or pause only.",
    "R-D1": "Recommended end-cap: the R-T1 device with the best R-T2 rank; if none passes, no inertial end-cap for tremor, "
            "and the end-cap is chosen for its steering / cue value against its mass, power, noise and safety costs.",
    "tuning": "Feed-forward gain chosen on tuning seeds 300-303 (r_rot 0.5, 6-12 Hz, 1-2 mm) from {0.5, 0.75, 1.0}: the largest "
              "mean further reduction at 8-12 Hz; ties within 0.01 go to the lower gain.",
}


def cdir(quick):
    d = os.path.join(CACHE, "quick") if quick else CACHE
    os.makedirs(d, exist_ok=True)
    return d


def save(name, obj, quick):
    provenance.write_json(os.path.join(cdir(quick), f"stage_{name}.json"), obj)


def load(name, quick):
    p = os.path.join(cdir(quick), f"stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:8.1f} s] {msg}", flush=True)


def meta(status, seeds=None, extra=None):
    return provenance.metadata(status, seeds=seeds, extra=dict({"script": "endcap/run_study.py", "doc": "docs/inertial_endcap.md"},
                                                                **(extra or {})))


# ================================================================================================ scaling
def stage_scaling(quick=False):
    import torch
    from endcap import linear_torch as LT
    from endcap import scaling as SCL
    out = {"meta": meta("CALCULATION"), "ceiling": SCL.ceiling_table()}
    rec = []
    for rr in P.SPLITS:
        el = LT.EndcapLinear(rr)
        for f in (0.5, 1, 2, 3, 5, 8, 10, 12):
            with torch.no_grad():
                x0, G = el.responses({}, f, 1e-3, inputs=("tau_t2", "tau_t1", "Fcap_t1", "Fcap_t2"))
            rec.append({"r_rot": rr, "f_Hz": f, "tip_um_per_mNm_t2": float(torch.abs(G[0, 0]).item() * 1e3),
                        "tip_um_per_mNm_t1": float(torch.linalg.norm(torch.abs(G[:, 1])).item() * 1e3),
                        "tip_mm_per_N_cap_t1": float(torch.linalg.norm(torch.abs(G[:, 2])).item() * 1e3),
                        "tip_mm_per_N_cap_t2": float(torch.linalg.norm(torch.abs(G[:, 3])).item() * 1e3),
                        "tip_mm_per_mm_tremor": float(torch.linalg.norm(torch.abs(x0)).item() * 1e3)})
    out["receptance"] = rec
    grips = {}
    for rr in P.SPLITS:
        g = LT.base(rr).grip
        grips[str(rr)] = {"K_rot_Nm_rad": g.K_r, "z_c_mm": g.z_c * 1e3, "kappa_f": g.kappa_f}
    out["grip"] = grips
    # gyroscopic stiffening ratio H w / K_rot (CALC) for pen-scale and literature rotors
    Hs = {"pen end-cap rotor, 45 g class (CALC)": 3.0e-3, "Walker 2018 flywheel 13.4 g, 20 000 rpm (HAP-82)": 1.98e-6 * SCL.rpm2rad(20000),
          "iTorqU 2.0 flywheel 138 g, 6600 rpm (HAP-83)": 2.18e-4 * SCL.rpm2rad(6600)}
    rows = []
    for name, H in Hs.items():
        for rr in P.SPLITS:
            K = grips[str(rr)]["K_rot_Nm_rad"]
            rows.append({"rotor": name, "H_Nms": H, "r_rot": rr, **{f"ratio_{f}Hz": SCL.gyro_stiffening_ratio(H, f, K) for f in (4, 8, 12)}})
    rows.append({"rotor": "hand on the wrist (glove case): K_wrist 1.3 N m/rad (LIT HAP-32), H 0.03 N m s (ASSUMPTION)",
                 "H_Nms": 0.03, "r_rot": None, **{f"ratio_{f}Hz": SCL.gyro_stiffening_ratio(0.03, f, 1.3) for f in (4, 8, 12)}})
    out["gyro_stiffening"] = rows
    # nutation / precession of the pen on its grip with a 3 mN m s rotor: Rev H body + 45 g at the end-cap, inertia about the
    # grip's elastic centre (CALC)
    from sim.handpen.params import pen_with_device
    from opt.inertial import revh as RH
    body = pen_with_device(RH.config_B(RH.RevH()))
    zc = grips["0.5"]["z_c_mm"] * 1e-3
    J_t = body.J_g + body.m * (body.z_g - zc) ** 2 + 0.045 * (P.Z_CAP - zc) ** 2
    out["pen_J_about_grip_kgm2"] = J_t
    out["nutation_precession_Hz"] = {str(rr): SCL.nutation_precession(3.0e-3, J_t, grips[str(rr)]["K_rot_Nm_rad"]) for rr in P.SPLITS}
    out["no_rotor_rot_resonance_Hz"] = {str(rr): math.sqrt(grips[str(rr)]["K_rot_Nm_rad"] / J_t) / (2 * math.pi) for rr in P.SPLITS}
    # single-stroke and static bounds
    out["com_bound_mm"] = {"30 g x +/-4 mm, pen 120 g + hand 210 g": SCL.com_shift_bound(0.030, 4e-3, 0.33) * 1e3,
                           "30 g x +/-4 mm, pen 120 g alone": SCL.com_shift_bound(0.030, 4e-3, 0.12) * 1e3}
    out["cmg_impulse_Nms"] = {"H 2.85 mN m s, one rotor, +/-1.14 rad": float(SCL.cmg_impulse(2.85e-3, 1.14, n=1))}
    out["weight_shift_mNm"] = {"30 g moved 4 mm (tilt plane, 50 deg)": SCL.weight_shift_torque(0.03, 4e-3) * 1e3,
                               "30 g moved 4 mm (sideways)": SCL.weight_shift_torque(0.03, 4e-3, axis="side") * 1e3}
    thrust = SCL.prop_thrust(22e-3, 0.5)
    out["propeller"] = {"thrust_N_per_fan_at_0.5W": thrust, "power_W_for_0.1N": SCL.prop_power_for(0.1, 22e-3),
                        "note": "two opposed 22 mm ducted fans per axis sharing the 1 W peak budget (CALC, momentum theory, FM 0.5, eta 0.6 ASSUMPTION)"}
    out["corners_Hz"] = {"LRM 30 g, 4 mm, 0.5 N: stroke-limited below": SCL.lrm_corner(0.03, 4e-3, 0.5),
                         "CMG rate 30 rad/s, delta 1.14 rad: angle-limited below": SCL.cmg_corner(30.0, 1.14)}
    save("scaling", out, quick)
    return out


# ================================================================================================ optimise
def stage_optimise(quick=False):
    import torch
    from endcap import optimise as OP
    caps = (25e-3, 45e-3) if quick else OP.MASS_CAPS
    evals = 120 if quick else 400
    restarts = 1 if quick else 2
    res = {"meta": meta("CALCULATION"), "caps_g": [c * 1e3 for c in caps], "fronts": {}, "gradient": {}, "arrangements": {},
           "comparators": {}, "budgets": {}, "sensitivity": {}}
    classes = [("LRM2", None), ("CMG", [OP.CMG_ARRS, OP.CMG_MOTORS]), ("RW2", [OP.RW_MOTORS]), ("PG", [OP.PG_MOTORS])]
    for which in ("tremor", "steer", "H"):
        for cls, ch in classes:
            if (cls == "PG") != (which == "H") and not (cls == "PG" and which == "tremor"):
                continue
            key = f"{cls}_{which}"
            res["fronts"][key] = []
            for cap in caps:
                r = OP.cma_opt(cls, cap, which, choices=ch, max_evals=evals, seed=1, restarts=restarts)
                s = OP.summarize(cls, r["x"], r["choice"] if ch else ())
                s.update({"cap_g": cap * 1e3, "objective": which, "cma_evals": r["evals"], "penalty": r["pen"], "cma_f": r["f"],
                          "cma_z": r["z"]})
                res["fronts"][key].append(s)
                log(f"optimise {key} cap {cap * 1e3:.0f} g: f {r['f']:.4f} pen {r['pen']:.3g} choice {r['choice']} mass {s['mass_g']:.1f} g")
    # every CMG arrangement at 45 g (tremor and steer)
    for arr in OP.CMG_ARRS:
        for which in ("tremor", "steer"):
            r = OP.cma_opt("CMG", 45e-3, which, choices=[(arr,), OP.CMG_MOTORS], max_evals=evals, seed=3, restarts=restarts)
            s = OP.summarize("CMG", r["x"], r["choice"])
            s.update({"penalty": r["pen"], "objective": which})
            res["arrangements"][f"{arr}_{which}"] = s
            log(f"  arrangement {arr} {which}: f {r['f']:.4f} pen {r['pen']:.3g} motor {r['choice'][1]}")
    # comparators: the same masses fixed (passive weight), tuned-mass dampers
    res["comparators"]["weight"] = {f"{m * 1e3:.0f}g": OP.passive_weight_ratio(m) for m in (15e-3, 30e-3, 45e-3)}
    res["comparators"]["tmd"] = {f"{ft:.0f}Hz": OP.tmd_ratio(30e-3, ft, 0.1) for ft in (6.0, 8.0, 10.0)}
    # larger budgets: would a bigger envelope change the answer?
    for cap in ((60e-3, 90e-3) if not quick else (60e-3,)):
        for cls, ch in (("LRM2", None), ("CMG", [OP.CMG_ARRS, OP.CMG_MOTORS])):
            for which in ("tremor", "steer"):
                saved = dict(P.ENV)
                P.ENV["p_avg"] = 1.0
                P.ENV["length"] = 60e-3
                try:
                    r = OP.cma_opt(cls, cap, which, choices=ch, max_evals=evals, seed=4, restarts=restarts)
                    s = OP.summarize(cls, r["x"], r["choice"] if ch else ())
                finally:
                    P.ENV.update(saved)
                s.update({"cap_g": cap * 1e3, "p_avg_cap_W": 1.0, "length_mm": 60.0, "penalty": r["pen"]})
                res["budgets"][f"{cls}_{which}_{cap * 1e3:.0f}g"] = s
                log(f"  budget {cls} {which} {cap * 1e3:.0f} g: f {r['f']:.4f} pen {r['pen']:.3g}")
    # stiffer hand (x2) for the 45 g tremor and steer optima
    for key in ("LRM2_tremor", "CMG_tremor", "LRM2_steer", "CMG_steer"):
        s = [x for x in res["fronts"][key] if x["cap_g"] == 45.0][0]
        cls = "LRM2" if key.startswith("LRM2") else "CMG"
        with torch.no_grad():
            d = OP.build(cls, {k: torch.tensor(float(v)) for k, v in s["x"].items()}, tuple(s["choice"]))
            m2 = OP.metrics(d, hard=True, hand_scale=2.0)
        res["sensitivity"][f"{key}_hand_x2"] = {"tremor_mean": float(m2["tremor_mean"]), "steer_3Hz_mm": float(m2["steer_3Hz_mm"]),
                                                "steer_worst_mm": {f"r{rr}_{f:g}Hz": float(v) for (rr, f), v in m2["steer_mm"].items()}}
    save("optimise", res, quick)
    return res


CHOSEN = (("LRM2_tremor", "lrm"), ("CMG_tremor", "cmg"), ("CMG_steer", "cmg_steer"), ("PG_H", "pg"))


def pick_designs(opt):
    """The designs carried into the time domain: at the largest mass cap, the tremor optima of the LRM and the CMG, the
    steering optimum of the CMG and the largest passive rotor; each the better (feasible, lower objective) of the CMA-ES
    optimum and its autograd refinement (stage gradient)."""
    cap = max(opt["caps_g"])
    pick = {}
    for key, name in CHOSEN:
        s = dict([x for x in opt["fronts"][key] if x["cap_g"] == cap][0])
        s["source"] = "CMA-ES"
        g = opt.get("gradient", {}).get(f"{key}_{cap:.0f}g")
        if g and g["pen"] < 1e-3 and (s["penalty"] >= 1e-3 or g["f"] < s["cma_f"] - 1e-6):
            s = dict(g["summary"])
            s.update({"cap_g": cap, "penalty": g["pen"], "objective": key.split("_")[1], "cma_f": g["cma_f"], "grad_f": g["f"],
                      "source": "autograd (Adam) refinement of the CMA-ES optimum"})
        pick[name] = s
    return pick


def chosen_designs(quick=False):
    """The designs fixed after the optimise and gradient stages (stored in the optimise cache as 'chosen')."""
    opt = load("optimise", quick)
    return opt.get("chosen") or pick_designs(opt)


# ================================================================================================ tune (tuning seeds)
def stage_tune(quick=False):
    from endcap import sim as S
    des = chosen_designs(quick)
    seeds = P.SEEDS["tune"][:1] if quick else P.SEEDS["tune"]
    conds = ((10.0, 1e-3), (8.0, 2e-3)) if quick else tuple((f, a) for f in (6.0, 8.0, 10.0, 12.0) for a in (1e-3, 2e-3))
    gains = (0.5, 1.0) if quick else (0.5, 0.75, 1.0)
    out = {"meta": meta("SIMULATION (tuning seeds only)", seeds={"tune": list(seeds)}), "grid": {}, "chosen": {}, "rules": RULES}
    for name in ("lrm", "cmg"):
        s = des[name]
        dev = S.h1_device(s)
        rows = {}
        for g in gains:
            ev = S.TremorEval(dev, 0.5, gain=g, Km=s.get("Km"), J_gimbal=_jg(s))
            rr = []
            for seed in seeds:
                for f0, a in conds:
                    c = ev.case(seed, f0, a)
                    rr.append(c)
            rows[str(g)] = rr
            hi = [1 - c["nose+dev"] / c["nose"] for c in rr if c["f0"] >= 8]
            log(f"tune {name} gain {g}: further reduction at 8-12 Hz {np.mean(hi) * 100:.1f} %")
        out["grid"][name] = rows
        best, bestv = None, -1e9
        for g in gains:
            v = float(np.mean([1 - c["nose+dev"] / c["nose"] for c in rows[str(g)] if c["f0"] >= 8]))
            if v > bestv + 0.01 or best is None:
                best, bestv = g, v
        out["chosen"][name] = {"gain": best, "further_reduction_8_12Hz": bestv}
    save("tune", out, quick)
    return out


def _jg(s):
    """Gimbal inertia (kg m2) per axis for the power estimate: half the rotor polar inertia times rotors per axis (ASSUMPTION)."""
    if s["class"] not in ("SP2", "SP1", "DG1", "DG2", "PL2"):
        return None
    m, D = s["parts_g"]["rotors_g"] * 1e-3, s["x"]["D"]
    n_rot = {"SP2": 4, "SP1": 2, "DG1": 1, "DG2": 2, "PL2": 2}[s["class"]]
    J_one = (m / n_rot) * D * D / 8
    per_axis = {"SP2": 2, "SP1": 2, "DG1": 1, "DG2": 2, "PL2": 2}[s["class"]]
    return P.GIMBAL_DRIVE["J_rotor_frac"] * J_one * per_axis


# ================================================================================================ test (test seeds)
def stage_test(quick=False):
    from endcap import sim as S
    des = chosen_designs(quick)
    tune = load("tune", quick)
    seeds = P.SEEDS["test"][:1] if quick else P.SEEDS["test"]
    f0s = (6.0, 10.0) if quick else (4.0, 6.0, 8.0, 10.0, 12.0)
    amps = (1e-3,) if quick else (0.3e-3, 1e-3, 2e-3)
    splits = (0.5,) if quick else P.SPLITS
    t_start = provenance.metadata("x")["generated_utc"]
    out = {"meta": meta("SIMULATION (test seeds, after the rules and the tuning were fixed)", seeds={"test": list(seeds)}),
           "rules": RULES, "rules_fixed_before_test": True, "tune_generated_utc": tune["meta"]["generated_utc"],
           "test_started_utc": t_start, "rows": {}, "wrist": {}, "distortion": {}, "oracle": {}, "designs": {}}
    devs = {"lrm": S.h1_device(des["lrm"]), "cmg": S.h1_device(des["cmg"]),
            "weight_lrm": S.weight_device(des["lrm"]["mass_g"] * 1e-3), "weight_cmg": S.weight_device(des["cmg"]["mass_g"] * 1e-3)}
    for k, d in devs.items():
        out["designs"][k] = {"label": d.label, "kind": d.kind}
    for name, dev in devs.items():
        rows = []
        g = tune["chosen"].get(name, {}).get("gain", 1.0) if name in ("lrm", "cmg") else 1.0
        s = des.get(name, {})
        for rr in splits:
            ev = S.TremorEval(dev, rr, gain=g, Km=s.get("Km"), J_gimbal=_jg(s) if s else None)
            for seed in seeds:
                for f0 in f0s:
                    for a in amps:
                        rows.append(ev.case(seed, f0, a, active=name in ("lrm", "cmg")))
                if not quick:
                    out["wrist"].setdefault(name, []).append(ev.case(seed, 8.0, 1e-3, kind="wrist", active=name in ("lrm", "cmg")))
            log(f"test {name} r_rot {rr} done ({len(rows)} rows)")
            if name in ("lrm", "cmg") and rr == 0.5:
                dl = [ev.distortion(sd) for sd in seeds]
                gl = [ev.distortion(sd, "glyph") for sd in ((210,) if quick else (210, 211, 212, 213))]
                out["distortion"][name] = {"lognormal_um": dl, "glyph_um": gl}
                if not quick:
                    orc = [ev.case(sd, f0, 1e-3, active=False, oracle=True) for sd in seeds for f0 in (8.0, 10.0, 12.0)]
                    out["oracle"][name] = orc
        out["rows"][name] = rows
    save("test", out, quick)
    return out


# ================================================================================================ steering
def stage_steer(quick=False):
    from endcap import sim as S
    des = chosen_designs(quick)
    out = {"meta": meta("SIMULATION"), "rows": [], "pulses": [], "designs": {}}
    fs = (1.0, 3.0) if quick else (1.0, 2.0, 3.0, 5.0)
    seeds = P.SEEDS["test"][:1] if quick else P.SEEDS["test"]
    for name in ("lrm", "cmg", "cmg_steer"):
        dev = S.h1_device(des[name])
        out["designs"][name] = dev.label
        for rr in ((0.5,) if quick else P.SPLITS):
            for f in fs:
                for axis in ((0,) if quick else (0, 1)):
                    for seed in seeds:
                        r = S.steer_case(dev, rr, f, axis=axis, scenario="write", seed=seed)
                        r.update({"device": name, "seed": seed})
                        out["rows"].append(r)
                    r = S.steer_case(dev, rr, f, axis=axis, scenario="hold")
                    r.update({"device": name, "seed": None})
                    out["rows"].append(r)
        for f in fs:                                             # voluntary correction and a stiffer hand (r_rot 0.5, writing)
            for tag, kw in (("voluntary", dict(voluntary=True)), ("hand_x2", dict(hand_scale=2.0))):
                for seed in seeds:
                    r = S.steer_case(dev, 0.5, f, axis=0, scenario="write", seed=seed, **kw)
                    r.update({"device": name, "seed": seed, "variant": tag})
                    out["rows"].append(r)
        for scen in ("hold", "write"):
            for rr in ((0.5,) if quick else P.SPLITS):
                r = S.pulse_case(dev, rr, scenario=scen, seed=seeds[0])
                r.update({"device": name})
                out["pulses"].append(r)
        log(f"steer {name} done")
    save("steer", out, quick)
    return out


# ================================================================================================ gyroscopic stiffening
def stage_gyro(quick=False):
    from endcap import sim as S
    des = chosen_designs(quick)
    pg = des["pg"]
    seeds = P.SEEDS["test"][:1] if quick else P.SEEDS["test"]
    splits = (0.5,) if quick else P.SPLITS
    f0s = (8.0,) if quick else (4.0, 8.0, 12.0)
    cases = {"pg_design": (pg["H"], pg["mass_g"] * 1e-3), "pg_design_nospin": (0.0, pg["mass_g"] * 1e-3)}
    for k in (1, 3, 10, 30):
        cases[f"massless_H{k}x"] = (k * pg["H"], 0.0)
    out = {"meta": meta("SIMULATION (passive devices: nothing tuned)", seeds={"test": list(seeds)}), "H_design_Nms": pg["H"],
           "mass_g": pg["mass_g"], "rows": {}}
    for name, (H, m) in cases.items():
        rows = []
        dev = S.gyro_device(H, m)
        for rr in splits:
            ev = S.TremorEval(dev, rr)
            for seed in seeds:
                for f0 in f0s:
                    c = ev.case(seed, f0, 1e-3, active=False)
                    c["H"] = H
                    rows.append(c)
                if not quick:
                    c = ev.case(seed, 8.0, 1e-3, kind="wrist", active=False)
                    c["H"] = H
                    rows.append(c)
        out["rows"][name] = rows
        log(f"gyro {name} done")
    save("gyro", out, quick)
    return out


# ================================================================================================ cue
def stage_cue(quick=False):
    from endcap import cue as CU
    from endcap import sim as S
    out = {"meta": meta("SIMULATION + CALCULATION + LITERATURE"), "force_for_levels": CU.force_for_levels(),
           "channels": CU.channel_table(), "writing_share": {}, "sim": []}
    for lat in (0.33, 1.56):
        out["writing_share"][f"{lat:g}s"] = CU.writing_share_slower_than(lat, seeds=P.SEEDS["tune"][:2] if quick else P.SEEDS["tune"])
    grid = [(40.0, 0.5, 0.0, True), (40.0, 0.5, -180.0, True), (40.0, 0.5, 0.0, False), (75.0, 0.5, 0.0, True)]
    if not quick:
        grid += [(40.0, 0.25, 0.0, True), (40.0, 1.0, 0.0, True), (75.0, 1.0, 0.0, True), (75.0, 0.5, -180.0, True)]
    for f, F0, ph, harm in grid:
        for scen in ("write", "hold"):
            for nc in ((False, True) if scen == "write" else (False,)):
                r = S.cue_case(0.5, f, F0, ph, harm, scenario=scen, nose_cancel=nc)
                out["sim"].append(r)
    if not quick:
        for rr in (0.3, 0.7):
            out["sim"].append(S.cue_case(rr, 40.0, 0.5, 0.0, True, scenario="write"))
    log("cue done")
    save("cue", out, quick)
    return out


# ================================================================================================ gradient check (re-run)
def stage_gradient(quick=False):
    """Autograd refinement of the 25 g and 45 g CMA-ES optima (LRM2, CMG; tremor and steer), warm-started from the CMA
    solution plus random starts, keeping the best feasible iterate.  Replaces the 'gradient' block of the optimise stage."""
    from endcap import optimise as OP
    opt = load("optimise", quick)
    out = {}
    for key in ("LRM2_tremor", "CMG_tremor", "LRM2_steer", "CMG_steer"):
        cls = key.split("_")[0]
        which = key.split("_")[1]
        for s in opt["fronts"][key]:
            if s["cap_g"] not in (25.0, 45.0):
                continue
            choice = tuple(s["choice"])
            g = OP.grad_opt(cls, choice, s["cap_g"] * 1e-3, which, starts=2 if quick else 3, iters=60 if quick else 120, seed=2, z0=s["cma_z"])
            out[f"{key}_{s['cap_g']:.0f}g"] = {"x": g["x"], "f": g["f"], "pen": g["pen"], "cma_f": s["cma_f"], "best_start": g["start"],
                                               "best_iter": g["it"], "summary": OP.summarize(cls, g["x"], choice)}
            log(f"  gradient {key} {s['cap_g']:.0f} g: f {g['f']:.4f} (CMA {s['cma_f']:.4f}) pen {g['pen']:.3g} start {g['start']} it {g['it']}")
    opt["gradient"] = out
    opt["chosen"] = pick_designs(opt)
    for name, d in opt["chosen"].items():
        log(f"  chosen {name}: {d['class']} {d.get('choice')} source {d['source']}")
    save("optimise", opt, quick)
    return out


# ================================================================================================ off-the-shelf check (CALC)
def stage_offshelf(quick=False):
    """The 45 g CMG optima again with catalogue motors only (the 'INT' integrated spin motor is a concept, ASSUMPTION), and
    the 45 g passive-gyro momentum optimum likewise.  A sensitivity check on the optimiser's choice; the designs carried
    into the time domain are not changed."""
    from endcap import optimise as OP
    motors = tuple(m for m in OP.CMG_MOTORS if m != "INT")
    evals = 120 if quick else 400
    out = {"meta": meta("CALCULATION"), "motors": list(motors), "designs": {}}
    for which in ("tremor", "steer"):
        r = OP.cma_opt("CMG", 45e-3, which, choices=[OP.CMG_ARRS, motors], max_evals=evals, seed=5, restarts=1 if quick else 2)
        s = OP.summarize("CMG", r["x"], r["choice"])
        s.update({"penalty": r["pen"], "objective": which, "cap_g": 45.0})
        out["designs"][f"CMG_{which}_45g"] = s
        log(f"  off-the-shelf CMG {which}: f {r['f']:.4f} pen {r['pen']:.3g} choice {r['choice']} mass {s['mass_g']:.1f} g")
    save("offshelf", out, quick)
    return out


# ================================================================================================ reaction wheels (re-run)
def stage_rw(quick=False):
    """Reaction-wheel fronts recomputed after a fix of the wheel's peak-power model (the first model counted the spin
    power on top of a full 1 W of copper, so every wheel design was flagged infeasible).  Replaces the RW2 fronts of the
    optimise stage in the report; the wheels are not used downstream."""
    from endcap import optimise as OP
    caps = (25e-3, 45e-3) if quick else OP.MASS_CAPS
    evals = 120 if quick else 400
    out = {"meta": meta("CALCULATION"), "fronts": {}}
    for which in ("tremor", "steer"):
        key = f"RW2_{which}"
        out["fronts"][key] = []
        for cap in caps:
            r = OP.cma_opt("RW2", cap, which, choices=[OP.RW_MOTORS], max_evals=evals, seed=1, restarts=1 if quick else 2)
            s = OP.summarize("RW2", r["x"], r["choice"])
            s.update({"cap_g": cap * 1e3, "objective": which, "cma_evals": r["evals"], "penalty": r["pen"], "cma_f": r["f"], "cma_z": r["z"]})
            out["fronts"][key].append(s)
            log(f"rw {key} cap {cap * 1e3:.0f} g: f {r['f']:.4f} pen {r['pen']:.3g} choice {r['choice']} mass {s['mass_g']:.1f} g")
    save("rw", out, quick)
    return out


# ================================================================================================ larger budgets (re-run)
def stage_budgets(quick=False):
    """Larger envelopes (60 and 90 g, 1 W average, 60 mm long), redone more carefully than in the optimise stage: the best
    of that stage's CMA-ES run, a second CMA-ES run (another seed), and Adam warm-started from the 45 g chosen design
    (which stays feasible in a larger envelope, so a larger budget can never look worse only because a run got stuck).
    Replaces the optimise stage's 'budgets' in the report."""
    from endcap import optimise as OP
    opt = load("optimise", quick)
    chosen = opt.get("chosen") or pick_designs(opt)
    evals = 120 if quick else 400
    out = {"meta": meta("CALCULATION"), "budgets": {}}

    def better(a, b):
        if b is None:
            return a
        if a is None:
            return b
        fa, fb = a["penalty"] >= 1e-3, b["penalty"] >= 1e-3
        if fa != fb:
            return b if fa else a
        return a if a["_f"] <= b["_f"] else b

    for key, s0 in opt["budgets"].items():
        cls, which, capg = key.split("_")
        cap = float(capg.rstrip("g")) * 1e-3
        saved = dict(P.ENV)
        P.ENV["p_avg"] = 1.0
        P.ENV["length"] = 60e-3
        try:
            cand = dict(s0)
            cand["_f"] = s0["tremor_mean"] if which == "tremor" else -s0["steer_3Hz_mm"]
            cand["source"] = "CMA-ES (optimise stage)"
            ch = None if cls == "LRM2" else [OP.CMG_ARRS, OP.CMG_MOTORS]
            r = OP.cma_opt(cls, cap, which, choices=ch, max_evals=evals, seed=14, restarts=1 if quick else 2)
            s1 = OP.summarize(cls, r["x"], r["choice"] if ch else ())
            s1.update({"penalty": r["pen"], "_f": r["f"], "source": "CMA-ES (second run, seed 14)"})
            cand = better(cand, s1)
            base = chosen["lrm" if cls == "LRM2" else ("cmg" if which == "tremor" else "cmg_steer")]
            sp = OP.SPACES[cls]
            z0 = []
            for n_, lo, hi in zip(sp.names, sp.lo, sp.hi):
                u = min(max((base["x"][n_] - lo) / (hi - lo), 1e-4), 1 - 1e-4)
                z0.append(float(np.log(u / (1 - u))))
            g = OP.grad_opt(cls, tuple(base["choice"]), cap, which, starts=1 if quick else 2, iters=60 if quick else 120, seed=7, z0=z0)
            s2 = OP.summarize(cls, g["x"], tuple(base["choice"]))
            s2.update({"penalty": g["pen"], "_f": g["f"], "source": "Adam warm-started from the 45 g design"})
            cand = better(cand, s2)
        finally:
            P.ENV.update(saved)
        cand.update({"cap_g": cap * 1e3, "p_avg_cap_W": 1.0, "length_mm": 60.0})
        cand.pop("_f", None)
        out["budgets"][key] = cand
        log(f"budgets {key}: tremor {cand['tremor_mean']:.4f} steer {cand['steer_3Hz_mm']:.4f} source {cand['source']}")
    save("budgets", out, quick)
    return out


# ================================================================================================ report
def stage_report(quick=False):
    from endcap import report as RP
    RP.build(quick=quick)
    log("report done")


STAGES = {"scaling": stage_scaling, "optimise": stage_optimise, "gradient": stage_gradient, "tune": stage_tune, "test": stage_test, "steer": stage_steer,
          "gyro": stage_gyro, "cue": stage_cue, "offshelf": stage_offshelf, "rw": stage_rw, "budgets": stage_budgets,
          "report": stage_report}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="small grids; outputs under results/endcap/_cache/quick only")
    ap.add_argument("--stages", default=",".join(STAGES), help="comma list of stages")
    a = ap.parse_args(argv)
    for st in a.stages.split(","):
        log(f"stage {st} ...")
        STAGES[st](quick=a.quick)
    return 0


if __name__ == "__main__":
    sys.exit(main())
