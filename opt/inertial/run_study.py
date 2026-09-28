#!/usr/bin/env python3
"""Rev H active-nose pen with inertial options: the whole study.

Stages (each writes its section into results/opt/_cache/inertial_stage_<name>.json; `report` assembles
results/opt/inertial_opt.json, the figures and the replay):
  nose_adjoint   adjoint (autograd) design of the nose actuator: power-mass front                 (CALC, seconds)
  tracker        Rev H tracker setting by ParEGO on training seeds (opt/inertial/tracker_tune)    (SIM, ~5 min)
  grid           Rev H B and A on the TEST seeds 200-203: oracle and causal (shipped and Rev H tracker settings),
                 0.1-2 mm, 4-12 Hz, wrist tremor, grip splits 0.3/0.5/0.7, false correction, power (SIM, ~10 min)
  sweep          travel and servo-bandwidth sensitivity on training seeds                         (SIM, ~3 min)
  addon          rear-cap reaction mass / CMG / weight on top of the nose, training then test      (SIM, ~15 min)
  neural         BPTT-trained neural reaction-mass controller (differentiable linear model), checked in H1
  tiers          T0-T2 linear-model summary                                                       (CALC)
  report         JSON, figures (+CSV twins), viz, layout, tip parameters, evidence rows
Run: python3 -m opt.inertial.run_study [--quick] [--stages a,b,...]
Seed plan: tuning/training seeds 300-323 (lognormal) and glyph seeds 330-337; test seeds 200-203 (lognormal) and glyph test
seeds 210-213 used only by `grid`, `addon --test` and the final tables.  Evidence status: SIMULATION and CALCULATION.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import sim.handpen  # noqa: E402,F401
from opt.inertial import revh as RH  # noqa: E402
from opt.inertial import scen as SC  # noqa: E402
from stabpen import provenance  # noqa: E402

CACHE = os.path.join(ROOT, "results", "opt", "_cache")
OUT = os.path.join(ROOT, "results", "opt")
REVH_TRACKER = os.path.join(OUT, "inertial_tracker_revh.json")


def save_stage(name, obj):
    os.makedirs(CACHE, exist_ok=True)
    provenance.write_json(os.path.join(CACHE, f"inertial_stage_{name}.json"), obj)


def load_stage(name):
    p = os.path.join(CACHE, f"inertial_stage_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def revh_tracker_params():
    if os.path.exists(REVH_TRACKER):
        return json.load(open(REVH_TRACKER))["params"]
    return None


# ================================================================================= stages
def stage_nose_adjoint(quick=False):
    from opt.inertial import adjoint as AJ
    res = [AJ.nose_optimise(mu_mass=mu, n_start=2 if quick else 4, iters=200 if quick else 400) for mu in (0.5, 2.0, 5.0, 10.0, 20.0)]
    out = {"front": res, "grad_check": AJ.nose_grad_check(), "chosen_mu": 5.0,
           "label": "CALCULATION (differentiable actuator model; inputs ASSUMPTION; gradients by autograd, checked by central differences)"}
    save_stage("nose_adjoint", out)
    return out


def stage_tracker(quick=False):
    from opt.inertial import tracker_tune as TT
    rows = TT.search(n_init=6 if quick else 14, n_iter=6 if quick else 36, quick=quick,
                     log=TT.LOG.replace(".jsonl", "_quick.jsonl") if quick else TT.LOG)
    best = TT.select(rows)
    x0 = [r for r in rows if r["tag"] == "x0"][0]
    if best is not None and not quick:
        from opt.inertial import tracker as TK
        p = dict(TK.ship_params()); p.update(best["x"])
        provenance.write_json(REVH_TRACKER, {"meta": provenance.metadata(
            "SIMULATION (model H1 Rev H-B, training seeds only)", seeds={"train": [300, 301], "glyph_train": [330, 331]},
            extra={"script": "opt/inertial/tracker_tune.py", "rule": TT.__doc__.split("Selection rule")[1].strip()}),
            "label": "revh", "params": p, "changed": best["x"], "training": best["res"], "ship_on_training": x0["res"],
            "at_bounds": [k for k, v in best["x"].items() if np.isclose(v, TT.SPACE.lo[TT.SPACE.names.index(k)]) or
                          np.isclose(v, TT.SPACE.hi[TT.SPACE.names.index(k)])]})
    out = {"n_evals": len(rows), "selected": best, "ship_on_training": x0["res"],
           "front": [{"x": r["x"], "f": r["f"]} for r in rows]}
    save_stage("tracker", out)
    return out


def _grid_B(ev_by_split, seeds, f0s, amps, wrist, controllers, log=None):
    rows = []
    for r_rot, ev in ev_by_split.items():
        for seed in seeds:
            for f0 in f0s:
                for amp in amps:
                    r = ev.case(seed, f0, amp, "trans", controllers=controllers)
                    r["r_rot"] = r_rot
                    rows.append(r)
            for f0, amp in wrist:
                r = ev.case(seed, f0, amp, "wrist", controllers=controllers)
                r["r_rot"] = r_rot
                rows.append(r)
            if log:
                log(f"  B r_rot {r_rot} seed {seed} done ({len(rows)} rows)")
    return rows


def stage_grid(quick=False, seeds=None):
    """Test grid (first use of the test seeds): Rev H-B nose with the oracle, the shipped AKF and the Rev H AKF setting."""
    from opt.inertial.evaluate import RevHEval
    seeds = seeds or (SC.SEEDS["test"][:1] if quick else SC.SEEDS["test"])
    f0s = (6.0, 10.0) if quick else (4.0, 6.0, 8.0, 10.0, 12.0)
    amps = (0.3e-3, 2.0e-3) if quick else (0.1e-3, 0.3e-3, 1.0e-3, 2.0e-3)
    wrist = ((8.0, 0.3e-3),) if quick else ((4.0, 0.3e-3), (8.0, 0.3e-3), (12.0, 0.3e-3), (8.0, 1.0e-3))
    splits = (0.5,) if quick else (0.3, 0.5, 0.7)
    d = RH.RevH()
    prm_revh = revh_tracker_params()
    t0 = time.time()
    out = {"design": RH.describe(d), "seeds": list(seeds), "rows": {}, "distortion": {}}

    def log(msg):
        print(f"[{time.time() - t0:7.1f} s] {msg}", flush=True)

    for tag, prm in (("ship", None), ("revh", prm_revh)):
        if tag == "revh" and prm is None:
            continue
        evs = {rr: RevHEval(d, r_rot=rr, akf_params=prm) for rr in splits}
        ctrls = ("oracle", "akf") if tag == "ship" else ("akf",)
        out["rows"][tag] = _grid_B(evs, seeds, f0s, amps, wrist, ctrls, log)
        dist = []
        for rr, ev in evs.items():
            if rr != 0.5:
                continue
            for s in seeds:
                dist.append(ev.distortion(s, "lognormal"))
            for s in (SC.SEEDS["glyph_test"][:1] if quick else SC.SEEDS["glyph_test"]):
                dist.append(ev.distortion(s, "glyph"))
        out["distortion"][tag] = dist
        log(f"tracker {tag} done")
    out["A"] = grid_A(seeds, f0s, amps=(0.3e-3, 1.0e-3, 2.0e-3) if not quick else (0.3e-3,), log=log)
    save_stage("grid" + ("_quick" if quick else ""), out)
    return out


def grid_A(seeds, f0s, amps, log=None):
    """Architecture A (rigid nose carrying the load) with the oracle (true handle disturbance, 2 passes) and the shipped AKF."""
    from sim.handpen import evaluate as HE
    from sim.handpen import model as HM
    from opt.inertial import control as CL
    from opt.inertial import tracker as TK
    dA = RH.RevH(arch="A")
    ms = RH.masses(dA)
    m_act = ms["nose_inertia_about_pivot_g_mm2"] * 1e-9 / (dA.z_a - dA.z_p) ** 2
    blocks, gains = CL.tip_servo_A(dA.lever, 50.0, m_act, f_bw=dA.servo_hz)
    ctl = CL.ctl_spec(blocks, Ts=2e-4, imu=dict(pos_nd=0.2e-6, lat_ticks=1), ulim=[0, 0, 0, dA.F_peak_act, dA.F_peak_act, 0, 0])
    cfg = RH.config_A(dA).replace(ctl=ctl)

    def run(sc, est):
        n = len(sc.t)
        u = np.zeros((n, 7))
        if est is not None:
            u[:, 3:5] = est
        return HM.run(sc, cfg, uff=u, rec_hz=TK.REC_HZ)

    rows = []
    for seed in seeds:
        sc0 = SC.get(seed)
        ref = run(sc0, None)
        for f0 in f0s:
            for amp in amps:
                sc = SC.get(seed, SC.tremor(f0, amp))
                n = len(sc.t)
                un = run(sc, None)
                mu = HE.compare(un, ref)
                k = min(len(un["t"]), len(ref["t"]))
                d1 = np.column_stack([un["sx"][:k] - ref["sx"][:k], un["sy"][:k] - ref["sy"][:k]])
                o1 = run(sc, HM.uff_at_sim_rate(d1, un["t"][:k], n))
                d2 = d1 + np.column_stack([o1["sx"][:k] - un["sx"][:k], o1["sy"][:k] - un["sy"][:k]])
                o2 = run(sc, HM.uff_at_sim_rate(d2, un["t"][:k], n))
                mo = min(HE.compare(o1, ref)["e_rms_um"], HE.compare(o2, ref)["e_rms_um"])
                dh, info, _ = TK.estimate(un, sc, seed=seed + 7000, body="sleeve")
                ca = run(sc, TK.to_steps(dh, n))
                mc = HE.compare(ca, ref)
                sel = (ca["t"] > 0.5) & (ca["contact"] > 0)
                Fa = np.column_stack([ca["pf1"] - cfg.sleeve.preload[0], ca["pf2"]])[sel]
                rows.append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "unmod_e_rms_um": mu["e_rms_um"],
                             "oracle": {"ratio": mo / mu["e_rms_um"]},
                             "akf": {"ratio": mc["e_rms_um"] / mu["e_rms_um"], "band_ratio": mc["e_band_rms_um"] / mu["e_band_rms_um"],
                                     "F_act_rms_N": np.sqrt(np.mean(Fa ** 2, axis=0)).tolist(),
                                     "P_cu_W": float(np.sum(np.mean(Fa ** 2, axis=0)) / dA.Km_act ** 2),
                                     "P_cu_no_bias_W": float(np.sum(np.mean(np.column_stack([ca["pf1"], ca["pf2"]])[sel] ** 2, axis=0)) / dA.Km_act ** 2),
                                     "N_std_N": float(np.std((ca["Ns"] + ca["Nn"])[sel]))}})
        if log:
            log(f"  A seed {seed} done")
    return {"design": RH.describe(dA), "servo": gains, "rows": rows}


def stage_addon(quick=False, seeds=None):
    """Rear-cap reaction mass (and the passive weight) on top of the Rev H nose, TEST seeds, all three grip splits."""
    from opt.inertial import addon_eval as AE
    seeds = seeds or (SC.SEEDS["test"][:1] if quick else SC.SEEDS["test"])
    f0s = (6.0, 10.0) if quick else (4.0, 6.0, 8.0, 10.0, 12.0)
    amps = (0.3e-3, 1.0e-3) if quick else (0.3e-3, 1.0e-3, 2.0e-3)
    splits = (0.5,) if quick else (0.3, 0.5, 0.7)
    prm = revh_tracker_params()
    t0 = time.time()
    rows, dist = [], []
    for rr in splits:
        ev = AE.AddonEval(r_rot=rr, akf_params=prm, afc_mu=0.005)
        for seed in seeds:
            for f0 in f0s:
                for amp in amps:
                    rows.append(ev.case(seed, f0, amp))
            for f0, amp in ((8.0, 0.3e-3), (8.0, 1.0e-3)):
                rows.append(ev.case(seed, f0, amp, kind="wrist", controllers=("ff", "ff_cal", "afc")))
            print(f"[{time.time() - t0:7.1f} s] addon r_rot {rr} seed {seed} ({len(rows)} rows)", flush=True)
        if rr == 0.5:
            for s_ in seeds:
                for c in ("ff", "afc"):
                    dist.append({"seed": s_, "writer": "lognormal", "ctrl": c, "distortion_um": ev.distortion(s_, c)})
            for s_ in (SC.SEEDS["glyph_test"][:1] if quick else SC.SEEDS["glyph_test"]):
                for c in ("ff", "afc"):
                    dist.append({"seed": s_, "writer": "glyph", "ctrl": c, "distortion_um": ev.distortion(s_, c, "glyph")})
    rm = AE.default_rm()
    out = {"rm": {"label": rm.label, "m_g": rm.m * 1e3, "added_fixed_g": rm.added_fixed * 1e3, "stroke_mm": rm.stroke[0] * 1e3,
                  "F_max_N": rm.F_max[0], "Km": rm.Km, "f_centring_Hz": 5.0, "z_mm": rm.z * 1e3},
           "rows": rows, "distortion": dist, "seeds": list(seeds)}
    save_stage("addon" + ("_quick" if quick else ""), out)
    return out


def stage_sweep(quick=False):
    """Travel and servo-bandwidth sensitivity of the Rev H-B nose on TRAINING seeds (oracle and Rev H tracker)."""
    from dataclasses import replace as _rep
    from sim.handpen import evaluate as HE
    from sim.handpen import model as HM
    from opt.inertial import tracker as TK
    seeds = (300,) if quick else (300, 301, 302, 303)
    conds = ((10.0, 2.0e-3),) if quick else ((6.0, 1.0e-3), (10.0, 1.0e-3), (12.0, 1.0e-3), (6.0, 2.0e-3), (10.0, 2.0e-3), (12.0, 2.0e-3))
    travels = (1.5e-3, 3.0e-3) if quick else (1.0e-3, 1.5e-3, 2.0e-3, 3.0e-3, 4.0e-3)
    servos = (80.0,) if quick else (30.0, 80.0, 150.0)
    prm = revh_tracker_params()
    d0 = RH.RevH()
    base_cfg = RH.config_B(d0)
    cache = {}
    rows = []
    t0 = time.time()
    for seed in seeds:
        sc0 = SC.get(seed)
        ref = HM.run(sc0, base_cfg, rec_hz=TK.REC_HZ)
        for f0, amp in conds:
            sc = SC.get(seed, SC.tremor(f0, amp))
            n = len(sc.t)
            un = HM.run(sc, base_cfg, rec_hz=TK.REC_HZ)
            mu = HE.compare(un, ref)
            dh, info, _ = TK.estimate(un, sc, seed=seed + 7000, body="pen", params=prm)
            est = TK.to_steps(dh, n)
            clean = HM.clean_at_sim_rate(ref, n)
            for X in travels:
                for fs in servos:
                    d = _rep(d0, travel=X, servo_hz=fs)
                    cfg = RH.config_B(d)
                    ro = HE.compare(HM.run(sc, cfg.replace(stage=True), clean=clean, rec_hz=TK.REC_HZ), ref)
                    ra = HE.compare(HM.run(sc, cfg.replace(stage=True, stage_src=1), clean=est, rec_hz=TK.REC_HZ), ref)
                    rows.append({"seed": seed, "f0": f0, "amp_mm": amp * 1e3, "travel_mm": X * 1e3, "servo_hz": fs,
                                 "oracle": ro["e_rms_um"] / mu["e_rms_um"], "oracle_sat": ro["q_sat_frac"],
                                 "akf": ra["e_rms_um"] / mu["e_rms_um"], "akf_sat": ra["q_sat_frac"]})
        print(f"[{time.time() - t0:6.1f} s] sweep seed {seed}", flush=True)
    out = {"rows": rows, "seeds": list(seeds), "label": "SIM (model H1, training seeds, r_rot 0.5, Rev H tracker setting)"}
    save_stage("sweep" + ("_quick" if quick else ""), out)
    return out


def stage_tiers(quick=False):
    """T0-T2 (secondary slim variants): frictionless linear-model bounds of the best cap reaction mass per tier at 0.3 mm,
    4-12 Hz and the three grip splits (CALC).  T0 time-domain values are in results/pencil/inertial.json (study I1)."""
    import math as _m
    from sim.handpen import devices as DV
    from sim.handpen import params as HP
    from opt.inertial.linear_ext import LinearExt, ls_bound, tremor_direction
    tiers = {  # moving mass (WHA d x L), lateral stroke, position, what it displaces (CALC / ASSUMPTION packaging)
        "T0": {"d": 4.5e-3, "L": 18e-3, "stroke": 1.0e-3, "z": 0.151, "note": "5.15 g slug in the 7.9 mm bore, half the cell (study I1)"},
        "T1": {"d": 6.0e-3, "L": 20e-3, "stroke": 1.4e-3, "z": 0.150, "note": "Ø11 x 166 mm: 10.2 g slug, bore 10.4 mm"},
        "T2c": {"d": 9.0e-3, "L": 17e-3, "stroke": 2.0e-3, "z": 0.145, "note": "cap bulb Ø16: 19.5 g slug"},
    }
    out = {}
    for tk, t in tiers.items():
        m = DV.cylinder_mass(t["d"], t["L"])
        k_c = m * (2 * _m.pi * 5.0) ** 2
        dev = HP.Device(kind="rm", m=m, z=t["z"], stroke=(t["stroke"], t["stroke"], 0.0), F_max=(0.5, 0.5, 0.0), k_c=k_c,
                        c_c=2 * 0.7 * _m.sqrt(k_c * m), added_fixed=1.5e-3, removed_cell_frac=0.5 if tk == "T0" else 0.0)
        row = {"moving_mass_g": m * 1e3, "stroke_mm": t["stroke"] * 1e3, "mass_x_stroke_g_mm": m * t["stroke"] * 1e6, "note": t["note"]}
        for rr in (0.3, 0.5, 0.7):
            b0 = HP.Config(r_rot=rr)
            lm0 = LinearExt(b0)
            lm = LinearExt(b0.replace(device=dev))
            vals = {}
            for f in (4.0, 6.0, 8.0, 10.0, 12.0):
                w = 2 * np.pi * f
                umaj, umin = tremor_direction(0.6)
                x0 = lm0.solve(w, lm0.exc_translation(umaj, w) * 3e-4 + lm0.exc_translation(umin, w) * (-0.4j * 3e-4))[0:2]
                x1 = lm.solve(w, lm.exc_translation(umaj, w) * 3e-4 + lm.exc_translation(umin, w) * (-0.4j * 3e-4))[0:2]
                gains, lims = [], []
                for i, nm in enumerate(("F_t1", "F_t2")):
                    X = lm.solve(w, lm.input_vector(nm).astype(complex))
                    gains.append(X[0:2])
                    lims.append(min(0.5, t["stroke"] / max(abs(X[lm.ir + i]), 1e-12)))
                res, u = ls_bound(x1, gains, lims)
                vals[f"{f:g}Hz"] = float(np.linalg.norm(res) / np.linalg.norm(np.abs(x0)))
            row[f"r_rot_{rr}"] = vals
        out[tk] = row
    out["label"] = ("CALC: frictionless linear model, single frequency, optimally phased input limited by force (0.5 N) and stroke; "
                    "optimistic (the time-domain oracle realised a quarter to a half of these gains in study I1)")
    save_stage("tiers", out)
    return out


def stage_neural(quick=False):
    """BPTT-trained neural controller of the rear-cap reaction mass (task 4d): trained on the differentiable linear model with
    tracker outputs from H1 runs on TRAINING seeds 300-311, checked in H1 on validation seeds 316-319, then evaluated once on
    the TEST seeds at the three grip splits against the feed-forward controller (SIM)."""
    import torch
    from opt.inertial import addon_eval as AE
    from opt.inertial import control as CL
    from opt.inertial import neural as NN
    torch.manual_seed(0)
    prm = revh_tracker_params()
    t0 = time.time()
    log = lambda s: print(f"[{time.time() - t0:7.1f} s] {s}", flush=True)  # noqa: E731
    seeds = (300, 301) if quick else tuple(range(300, 312))
    pol, hist, info = NN.train(seeds=seeds, val_seeds=(316,) if quick else (316, 317), akf_params=prm, iters=4 if quick else 60,
                               win=1.0, batch=6 if quick else 12, log=log)
    blocks, cost = NN.export(pol)
    rm = AE.default_rm()
    spec = CL.ctl_spec([(blocks["A"], blocks["B"], blocks["C"], blocks["D"])], Ts=NN.TS, imu=dict(seed=5, lat_ticks=3),
                       ulim=[rm.F_max[0], rm.F_max[1], 0, 0, 0, 0, 0], nn=blocks["nn"])
    conds = ((10.0, 1.0e-3),) if quick else ((6.0, 1.0e-3), (8.0, 0.3e-3), (8.0, 1.0e-3), (10.0, 1.0e-3), (10.0, 2.0e-3),
                                             (12.0, 1.0e-3))
    val_rows, test_rows = [], []
    ev = AE.AddonEval(r_rot=0.5, akf_params=prm, nn_spec=spec)
    for seed in ((316,) if quick else (316, 317, 318, 319)):
        for f0, amp in conds:
            val_rows.append(ev.case(seed, f0, amp, controllers=("ff", "nn"), with_nose=False))
    log(f"validation done ({len(val_rows)} rows)")
    for rr in ((0.5,) if quick else (0.3, 0.5, 0.7)):
        ev = AE.AddonEval(r_rot=rr, akf_params=prm, nn_spec=spec)
        for seed in (SC.SEEDS["test"][:1] if quick else SC.SEEDS["test"]):
            for f0, amp in conds:
                test_rows.append(ev.case(seed, f0, amp, controllers=("ff", "nn")))
        log(f"test r_rot {rr} done ({len(test_rows)} rows)")
    ev = AE.AddonEval(r_rot=0.5, akf_params=prm, nn_spec=spec)
    dist = [{"seed": s_, "writer": w_, "ctrl": "nn", "distortion_um": ev.distortion(s_, "nn", w_)}
            for s_, w_ in ([(200, "lognormal")] if quick else [(s, "lognormal") for s in SC.SEEDS["test"]] +
                           [(s, "glyph") for s in SC.SEEDS["glyph_test"]])]
    W = {k: np.asarray(v).tolist() for k, v in blocks["nn"].items()}
    out = {"history": hist, "train": {**info, "seeds": list(seeds), "iters": len(hist), "window_s": 1.0},
           "cost": {**cost, "rate_Hz": 1.0 / NN.TS, "tanh_per_tick": NN.H,
                    "mcu_load_pct_nrf54l15": 100 * (cost["macs_per_tick"] * 2 + NN.H * 20) / NN.TS / 128e6,
                    "note": "2 cycles per MAC and 20 cycles per tanh (table) on the 128 MHz Cortex-M33 (ASSUMPTION)"},
           "weights": W, "lti": {k: np.asarray(blocks[k]).tolist() for k in ("A", "B")},
           "val_rows": val_rows, "test_rows": test_rows, "distortion": dist,
           "label": "SIM: policy trained by BPTT on the linear model (CALC), evaluated in the nonlinear model H1"}
    save_stage("neural" + ("_quick" if quick else ""), out)
    return out


STAGES = ("nose_adjoint", "tracker", "grid", "sweep", "addon", "neural", "tiers", "report")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--stages", default=",".join(STAGES))
    a = ap.parse_args()
    for st in a.stages.split(","):
        t0 = time.time()
        fn = globals().get("stage_" + st)
        if fn is None:
            from opt.inertial import report as RP
            fn = getattr(RP, "stage_" + st)
        print(f"== stage {st}", flush=True)
        fn(quick=a.quick)
        print(f"== stage {st} done in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
