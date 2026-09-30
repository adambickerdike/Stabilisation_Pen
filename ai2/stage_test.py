"""Stage test: tasks 1 (delayed ink), 2 (causal separation) and 3 (RL policies) on the TEST grid, used once for the
final tables: aiguide test writers 0-5 x seeds 200-203 x 6/8/10 Hz x 0.3/1/2 mm (216 scenarios) + each writer's
tremor-free writing.

Evidence status: SIMULATION (model HW1 via aiprior conventions).  Every setting was fixed on tuning data before this
stage ran (stages d01, d2b, learn, rl, cl).  Variants that the rules did not adopt are shown for information and
marked.  All commands are causal at the control tick (estimator outputs every tick; DL.OUT_EVERY = 1).
"""
from __future__ import annotations

import copy
import time
from typing import Dict, List, Optional

import numpy as np

from . import AMPS, F0S, TEST_SEEDS, TEST_WRITERS, ensure_paths
from . import candidates as CA
from . import common as C
from . import delayed as DL
from . import stage_learn_data as SLD
from . import tuning as TU

ensure_paths()
from aiprior import core as CO  # noqa: E402
from aiprior import study as SD  # noqa: E402
from handwriting import metrics as MT  # noqa: E402

VIZ = {"writer": 0, "seed": 200, "cases": [(6.0, 1.0e-3), (8.0, 2.0e-3), (10.0, 1.0e-3)]}
VIZ_VARIANTS = ("none", "tracker", "gated", "delayed_3mm", "delayed_6mm", "lag_100_6mm", "limit_100_6mm", "clean_copy",
                "oracle", "oracle_delayed_100_6mm", "learned_tcn", "learned_hybrid", "rl_arbiter")


def settings(quick: bool) -> Dict:
    """The settings fixed on tuning data (d01, d2b), with the adoption status."""
    d01 = C.load("d01", quick) or C.load("d01", False)
    d2b = C.load("d2b", quick) or C.load("d2b", False)
    if d01 is None or d2b is None:
        raise FileNotFoundError("ai2 frozen tuning caches d01/d2b are absent from this checkout; "
                                "rebuild the tuning stages before loading their estimators")
    sel = d2b["selection"]
    tab = sel["table"]
    cands = {TU.key(c): c for c in d2b["candidates"]}

    def cand_of(name):
        k = name.rsplit("_nose", 1)[0]
        return cands[k], int(name.rsplit("_nose", 1)[1])
    out = {"tremor": d01["chosen_tremor"], "det": d01["chosen_det"], "adopted": {}, "info_only": {}}
    causal = sel["causal_gated"]
    c, _ = cand_of(causal)
    out["gated"] = {"amp_lo": c.get("amp_lo", 0.0), "amp_hi": c.get("amp_hi", 0.0), "name": causal}
    out["adopted"]["gated"] = bool(sel.get("causal_passes"))
    for travel in (3, 6):
        ch = sel["chosen"].get(f"nose{travel}")
        if ch is None:                   # none passed: show the best by the objective, for information
            pool = [k for k in tab if k.endswith(f"nose{travel}") and "lam_max0_" not in k]
            ch = min(pool, key=lambda k: tab[k]["J_ink_1_2mm_um"])
            out["adopted"][f"delayed_{travel}mm"] = False
        else:
            out["adopted"][f"delayed_{travel}mm"] = "lam_max0_" not in ch
        c, _ = cand_of(ch)
        out[f"delayed_{travel}mm"] = dict(c, name=ch)
    conf = d2b.get("confirmation_seed_301") or {}
    out["confirmation_seed_301"] = {k: {kk: v.get(kk) for kk in ("R1", "R2", "R3", "R4", "passes", "J_ink_1_2mm_um")}
                                    for k, v in (conf.get("table") or {}).items()}
    # a setting is adopted only if it also passes the rules on the confirmation seed (301)
    for name in ("gated", "delayed_3mm", "delayed_6mm"):
        nm = out[name]["name"]
        c = out["confirmation_seed_301"].get(nm)
        out.setdefault("confirmed", {})[name] = bool(c and c.get("passes"))
        out["adopted"][name] = bool(out["adopted"].get(name)) and out["confirmed"][name]
    cl = C.load("cl", quick) or C.load("cl", False)
    learn = C.load("learn", quick) or C.load("learn", False)
    out["learned_best"] = (learn or {}).get("best_learned")
    out["cl_adopted"] = cl.get("adopted") if cl else None
    out["cl_passing"] = cl.get("passing") if cl else []
    return out


def _metrics(sc, res, pen):
    m = SD.metrics(sc, res, travel=False)
    m["coverage"] = DL.coverage(sc, res)
    if not pen.rigid:
        m.update({k: v for k, v in MT.travel(res, pen).items() if k in ("at_travel_limit", "q_max_mm", "q_rms_mm")})
    return m


def scenario_job(sc: CO.Scenario, S: Dict, keep: bool = False, cands: Optional[Dict] = None, mp: Optional[Dict] = None,
                 ctx=None) -> Dict:
    DL.OUT_EVERY = 1
    pens = {3: DL.pen_travel(3.0), 6: DL.pen_travel(6.0)}
    out, runs = {}, {}
    base = DL.DelayCfg(tremor=S["tremor"], det=S["det"] or {})
    base.amp_lo, base.amp_hi = S["gated"]["amp_lo"], S["gated"]["amp_hi"]
    est = DL.estimates(sc, base, lags=CA.LAGS_CL)
    obs = DL.observables(sc, est)
    tick_t = sc.streams.tick_t
    clean_run = sc.amp == 0
    # baselines
    if not clean_run:
        r = CO.run_none(sc); runs["none"] = r
        out["none"] = SD.metrics(sc, r, travel=False); out["none"]["coverage"] = DL.coverage(sc, r)
    r = sc.neutral; runs["revH_off"] = r
    out["revH_off"] = SD.metrics(sc, r, travel=False); out["revH_off"]["coverage"] = DL.coverage(sc, r)
    r = CO.run_cmd(sc, -sc.dh); runs["tracker"] = r
    out["tracker"] = _metrics(sc, r, sc.pen)
    if not clean_run:
        r = CO.run_cmd(sc, CO.oracle_cmd(sc)); runs["oracle"] = r
        out["oracle"] = _metrics(sc, r, sc.pen)
        rc, inf = SD.clean_copy(sc, runs["tracker"], "wiener", seed=1000 + sc.wr.w + int(sc.seed) + int(10 * sc.f0) + int(1e4 * sc.amp))
        runs["clean_copy"] = rc
        out["clean_copy"] = SD.metrics(sc, rc, travel=False); out["clean_copy"]["coverage"] = DL.coverage(sc, rc)
    # task 2: the gated listening tracker (lag 0)
    variants = [("gated", 3, dict(lam_max=0.0, alpha=1.0, beta=6.0), "catchup", False)]
    for travel in (3, 6):
        c = S[f"delayed_{travel}mm"]
        variants.append((f"delayed_{travel}mm", travel, dict(lam_max=c["lam_max"], alpha=c["alpha"], beta=c["beta"]), "catchup", False))
    # the lag curve: 25 ms = delayed_3mm and 50 ms = delayed_6mm when those are the chosen settings (same policy
    # parameters; at 25 ms the travel needed is far inside +-3 mm), so only the lags not already run are added
    have = {round(S[f"delayed_{tr}mm"]["lam_max"], 3) for tr in (3, 6)}
    for lam in (0.025, 0.05, 0.1):
        if round(lam, 3) not in have or lam == 0.1:
            variants.append((f"lag_{int(lam * 1e3)}_6mm", 6, dict(lam_max=lam, alpha=1.0, beta=6.0), "catchup", False))
    variants.append(("limit_100_6mm", 6, dict(lam_max=0.1, alpha=1.0, beta=1.0), "limit", False))
    if not clean_run:
        variants.append(("oracle_delayed_100_6mm", 6, dict(lam_max=0.1, alpha=1.0, beta=6.0), "catchup", True))
    est_or = None
    for name, travel, kw, pol, orc in variants:
        cfg = copy.copy(base)
        cfg.policy = pol
        for k, v in kw.items():
            setattr(cfg, k, v)
        if orc:
            if est_or is None:
                e1 = DL.estimates(sc, DL.DelayCfg(estimator="oracle"), lags=CA.LAGS_CL, det=est["det"],
                                  handle_out=est["handle_out"])
                est_or = DL.oracle_handle(sc, e1)
            e = est_or
            ob = DL.observables(sc, e)
        else:
            e, ob = est, obs
        lam = DL.lag_schedule(ob, cfg, sc.Ts)
        q = DL.command(e, lam, tick_t)
        r = DL.run(sc, q, pens[travel])
        if pol == "limit":
            r = DL.shifted(r, cfg.lam_max)
        runs[name] = r
        m = DL.evaluate_run(sc, r, pens[travel], q, lam, ob)
        if clean_run and pol != "limit":
            m["false_correction_um"] = DL.ink_timeline_error(sc, r, lam, sc.neutral)
        out[name] = m
    # tasks 2 and 3: learned estimators and RL policies (lag 0, Rev H nose)
    if cands is not None:
        X, tk, mb = CA.arrays(sc, mp)
        lam0 = np.zeros(len(tick_t))
        kept: Dict = {}
        for name, q in CA.commands(sc, est, mp, cands, X, tk, mb, ctx, keep_est=kept).items():
            if name == "gated":
                continue
            r = DL.run(sc, q, pens[3])
            runs[name] = r
            m = DL.evaluate_run(sc, r, pens[3], q, lam0, obs)
            if clean_run:
                m["false_correction_um"] = DL.ink_timeline_error(sc, r, lam0, sc.neutral)
            out[name] = m
        # task 1 with a learned fixed-lag estimator: the best open-loop learned model at the lags chosen for the
        # model-based smoother (same catch-up policy; the network's own output, no detector gate)
        best = S.get("learned_best")
        if best in kept:
            e = kept[best]
            ob = DL.observables(sc, e)
            for travel in (3, 6):
                c = S[f"delayed_{travel}mm"]
                cfg = copy.copy(base)
                cfg.policy, cfg.lam_max, cfg.alpha, cfg.beta = "catchup", c["lam_max"], c["alpha"], c["beta"]
                lam = DL.lag_schedule(ob, cfg, sc.Ts)
                q = DL.command(e, lam, tick_t)
                r = DL.run(sc, q, pens[travel])
                name = f"learned_delayed_{travel}mm"
                runs[name] = r
                m = DL.evaluate_run(sc, r, pens[travel], q, lam, ob)
                if clean_run:
                    m["false_correction_um"] = DL.ink_timeline_error(sc, r, lam, sc.neutral)
                out[name] = m
    if clean_run:
        out["tracker"]["false_correction_um"] = DL.ink_timeline_error(sc, runs["tracker"], np.zeros(len(tick_t)), sc.neutral)
    res = {"writer": sc.wr.w, "f0": sc.f0, "amp_mm": sc.amp * 1e3, "seed": sc.seed, "variants": out,
           "gate_open_frac": float(np.mean(est["g"] > 0.5))}
    if keep:
        res["_runs"] = runs
    return res


def writer_job(job: Dict) -> Dict:
    t0 = time.time()
    S = job["S"]
    mp = job["mp"]
    cands = CA.load(job["quick"])
    wr = CO.Writer(job["writer"])
    rows, viz = [], {}
    for seed in job["seeds"]:
        for f0 in job["f0s"]:
            for amp in job["amps"]:
                sc = CO.make_scenario(wr, f0, amp, seed)
                keep = wr.w == VIZ["writer"] and seed == VIZ["seed"] and (f0, amp) in VIZ["cases"]
                ctx = CA.calibration(wr, f0, amp, seed, mp["det"]) if "ctx" in cands["learned"] else None
                ev = scenario_job(sc, S, keep=keep, cands=cands, mp=mp, ctx=ctx)
                ev["ctx"] = ctx
                C.log(f"[test] writer {wr.w} seed {seed} {f0:g} Hz {amp * 1e3:g} mm: " + ", ".join(
                    f"{k} {v['ink_err_um']:.0f}" for k, v in ev["variants"].items() if k in ("tracker", "gated", "delayed_3mm", "delayed_6mm", "learned_hybrid", "rl_arbiter")))
                if keep:
                    runs = ev.pop("_runs")
                    viz[f"{f0:g}Hz_{amp * 1e3:g}mm"] = {k: MT.decimate_path(r, hz=50.0).tolist() for k, r in runs.items()
                                                       if k in VIZ_VARIANTS or k.startswith("delayed")}
                rows.append(ev)
    sc0 = CO.make_clean_scenario(wr)
    ctx0 = CA.calibration(wr, 0.0, 0.0, job["seeds"][0], mp["det"]) if "ctx" in cands["learned"] else None
    free = scenario_job(sc0, S, cands=cands, mp=mp, ctx=ctx0)
    free["ctx"] = ctx0
    out = {"writer": wr.w, "rows": rows, "tremor_free": free, "elapsed_s": time.time() - t0}
    if viz:
        viz["intended"] = MT.intended_path(wr.scn0, hz=50.0).tolist()
        viz["x_height_mm"] = wr.written.style.x_height_mm
        out["viz"] = viz
    return out


def run(quick: bool, workers: int):
    S = settings(quick)
    C.log(f"[test] settings: {S}")
    writers = TEST_WRITERS[:2] if quick else TEST_WRITERS
    seeds = TEST_SEEDS[:1] if quick else TEST_SEEDS
    amps = AMPS
    mp = SLD.model_params(quick)
    jobs = [{"writer": w, "seeds": list(seeds), "f0s": list(F0S), "amps": list(amps), "S": S, "mp": mp, "quick": quick}
            for w in writers]
    outs = C.jmap(writer_job, jobs, workers)
    cands = CA.load(quick)
    out = {"outs": outs, "settings": S, "writers": list(writers), "seeds": list(seeds), "model_params": mp,
           "candidates": {"learned": sorted(cands["learned"]), **cands["info"]}}
    C.save("test", out, quick)
    return out


def viz_extra(quick: bool, keys=("learned_tcn", "learned_hybrid", "rl_arbiter")) -> Dict:
    """Re-run the three strip cases (writer 0, seed 200) and keep the ink of variants that the first test run did not
    keep for the figures (same settings and models; deterministic, so the metrics equal the test grid's rows)."""
    S = settings(quick)
    mp = SLD.model_params(quick)
    cands = CA.load(quick)
    wr = CO.Writer(VIZ["writer"])
    out = {}
    for f0, amp in VIZ["cases"]:
        sc = CO.make_scenario(wr, f0, amp, VIZ["seed"])
        ctx = CA.calibration(wr, f0, amp, VIZ["seed"], mp["det"]) if "ctx" in cands["learned"] else None
        ev = scenario_job(sc, S, keep=True, cands=cands, mp=mp, ctx=ctx)
        runs = ev.pop("_runs")
        out[f"{f0:g}Hz_{amp * 1e3:g}mm"] = {"paths": {k: MT.decimate_path(runs[k], hz=50.0).tolist() for k in keys if k in runs},
                                            "metrics": {k: ev["variants"][k] for k in keys if k in ev["variants"]}}
    return out
