#!/usr/bin/env python3
r"""Build, cache and check the synthetic datasets (SIMULATION / synthetic data).

Splits (one 60 s recording per synthetic writer; writer ids disjoint):
  train              240 writers, nominal tremor f0 in [4, 12] Hz except [7, 8) Hz
  val                 40 writers, same distribution (early stopping, gains, baseline tuning)
  test                80 writers, same distribution (touched once, by ml/evaluate.py)
  test_freq_holdout   30 writers, f0 in [7, 8) Hz only (never seen in training)
  test_features       canonical stabpen.signals.feature_course (corners, dots, 4 Hz hatching,
                      fast stroke, circle, spiral) at 3 scales x 3 speeds x 2 sensor draws,
                      no tremor: intended-feature distortion ("false correction") test
  realism_sim         coupled hand-pen-paper simulator (sim/pensim, powered-neutral pen) on
                      12 seeds x (no tremor + tremor at 4.5, 6, 9, 11 Hz, 0.3 mm): housing
                      trajectories and housing-level disturbance (tremor run - clean run)
About 15 % of writers in train/val/test never have tremor; the others alternate tremor-on
(4-12 s) and tremor-off (2-9 s) segments.
Seeds: numpy SeedSequence(MASTER_SEED, spawn_key=(split_code, writer_index)); spawn keys are
recorded per writer.  Cached arrays go to ml/runs/data/ (git-ignored, reproducible);
the manifest and leakage checks go to results/ml/dataset_manifest.json.
Run: python3 -m ml.datasets [--quick]
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from . import common as C
from . import synth
from . import baselines as BL

MASTER_SEED = 20260927
DURATION_S = 60.0
SPLITS = {
    "train": {"code": 1, "n": 240, "prefix": "W0", "f0_rule": "main", "p_no_tremor": 0.15},
    "val": {"code": 2, "n": 40, "prefix": "W3", "f0_rule": "main", "p_no_tremor": 0.15},
    "test": {"code": 3, "n": 80, "prefix": "W4", "f0_rule": "main", "p_no_tremor": 0.15},
    "test_freq_holdout": {"code": 4, "n": 30, "prefix": "W5", "f0_rule": "holdout", "p_no_tremor": 0.0},
    "stress_tremor": {"code": 7, "n": 30, "prefix": "W7", "f0_rule": "main", "p_no_tremor": 0.0,
                      "regime": "stress_tremor"},
    "stress_writing": {"code": 8, "n": 30, "prefix": "W8", "f0_rule": "main", "p_no_tremor": 0.15,
                       "regime": "stress_writing"},
}
FEATURE_SCALES = (0.6, 1.0, 1.5)
FEATURE_SPEEDS = (0.8, 1.0, 1.25)
FEATURE_SENSOR_DRAWS = 2
REALISM_SEEDS = tuple(range(300, 312))       # disjoint from sim harness tuning (100-105) and test (200-211)
REALISM_F0 = (4.5, 6.0, 9.0, 11.0)
REALISM_AMP = 3e-4
REALISM_DURATION = 10.0
DATA_CACHE = os.path.join(C.RUNS, "data")
ARRAY_KEYS = ("t", "dp_um", "f_est", "d_tgt_um", "env_tgt", "pen_tgt", "f0_tgt", "finst_tgt",
              "oracle_hold_um", "oracle_phase_um")


def writer_seed(split, i):
    return np.random.SeedSequence(MASTER_SEED, spawn_key=(SPLITS[split]["code"], i))


def kf_feature_params():
    """Frozen controller KF used to produce the f_est input channel (snapshotted in the
    manifest so later steps never re-read results/sim, which other jobs rewrite)."""
    man = os.path.join(C.RESULTS, "dataset_manifest.json")
    if os.path.exists(man):
        m = json.load(open(man))
        if "kf_frozen_250Hz" in m:
            return m["kf_frozen_250Hz"], m["kf_frozen_source"]
    return BL.frozen_kf_params()


def build_writer(split, i, kf_feat):
    cfg = SPLITS[split]
    ss = writer_seed(split, i)
    s_prof, s_rec = ss.spawn(2)
    prof = synth.draw_writer(np.random.default_rng(s_prof), f"{cfg['prefix']}{i:03d}", split,
                             cfg["f0_rule"], cfg["p_no_tremor"], cfg.get("regime", "main"))
    prof.seed = {"entropy": MASTER_SEED, "spawn_key": [cfg["code"], i]}
    rec = synth.make_recording(prof, DURATION_S, s_rec, kf_feat, cfg["f0_rule"])
    rec["meta"]["record_id"] = f"{split}/{prof.writer_id}"
    return rec


def _build_writer_star(args):
    return build_writer(*args)


def build_feature_course(kf_feat):
    recs = []
    k = 0
    for sc in FEATURE_SCALES:
        for sp in FEATURE_SPEEDS:
            for j in range(FEATURE_SENSOR_DRAWS):
                ss = np.random.SeedSequence(MASTER_SEED, spawn_key=(5, k))
                rng = np.random.default_rng(ss)
                sensor = synth.SensorSpec(delay_s=float(rng.uniform(0.002, 0.003)),
                                          noise_um=float(rng.uniform(2.5, 3.5)), scale_err=float(rng.uniform(-0.01, 0.01)))
                rec = synth.feature_course_record(sc, sp, sensor, rng, kf_feat)
                rec["meta"]["record_id"] = f"test_features/FC{k:02d}"
                rec["meta"]["writer"] = {"writer_id": f"FC{k:02d}", "split": "test_features"}
                rec["meta"]["seed"] = {"entropy": MASTER_SEED, "spawn_key": [5, k]}
                recs.append(rec)
                k += 1
    return recs


def build_realism(kf_feat):
    """Housing trajectories from the coupled simulator (neutral pen, stage held at zero)."""
    from sim.pensim import model, scenarios
    from stabpen import signals as sg
    recs = []
    k = 0
    for seed in REALISM_SEEDS:
        sc0 = scenarios.handwriting(seed=seed, duration=REALISM_DURATION, tremor=None)
        r0 = model.run(sc0, model.Controller(mode="neutral"), seed=seed)
        t = r0["t"]
        p0 = r0.xy("pHx").copy()
        cases = [(None, r0)]
        for f0 in REALISM_F0:
            sc1 = scenarios.handwriting(seed=seed, duration=REALISM_DURATION,
                                        tremor=sg.TremorSpec(f0=f0, amp_pk=REALISM_AMP))
            cases.append((f0, model.run(sc1, model.Controller(mode="neutral"), seed=seed)))
        for f0, r in cases:
            ss = np.random.SeedSequence(MASTER_SEED, spawn_key=(6, k))
            rng = np.random.default_rng(ss)
            sensor = synth.SensorSpec(delay_s=float(rng.uniform(0.002, 0.003)),
                                      noise_um=float(rng.uniform(2.5, 3.5)), scale_err=float(rng.uniform(-0.01, 0.01)))
            n = min(len(t), len(r["t"]))
            ph = r.xy("pHx")[:n]
            d = ph - p0[:n] if f0 is not None else np.zeros((n, 2))
            env = np.clip(t[:n] / 0.3, 0, 1) if f0 is not None else np.zeros(n)
            st = {"env": env, "f0": np.full(n, f0 or 0.0), "f": np.full(n, f0 or 0.0)}
            rec = synth.sample_record(t[:n], ph, d, r["contact"][:n] > 0, st, sensor, rng, kf_feat, None)
            rid = f"SIM{seed}" + ("" if f0 is None else f"-f{f0:g}")
            rec["meta"] = {"record_id": f"realism_sim/{rid}",
                           "writer": {"writer_id": f"SIM{seed}", "split": "realism_sim"},
                           "sim": {"seed": seed, "f0": f0, "amp_pk": REALISM_AMP if f0 else 0.0,
                                   "duration_s": REALISM_DURATION, "model_version": r.info.get("model_version"),
                                   "params_version": r.info.get("params_version"),
                                   "params_digest": r.info.get("params_digest"), "controller": "neutral"},
                           "sensor": vars(sensor), "seed": {"entropy": MASTER_SEED, "spawn_key": [6, k]},
                           "content_hash": synth.content_hash(sc0.intended)}
            recs.append(rec)
            k += 1
    return recs


# ------------------------------------------------------------------ cache I/O
def save_split(name, recs):
    os.makedirs(DATA_CACHE, exist_ok=True)
    lens = np.array([len(r["t"]) for r in recs])
    arrs = {k: np.concatenate([r[k] for r in recs]) for k in ARRAY_KEYS}
    np.savez(os.path.join(DATA_CACHE, f"{name}.npz"), offsets=np.concatenate([[0], np.cumsum(lens)]), **arrs)
    with open(os.path.join(DATA_CACHE, f"{name}.meta.json"), "w") as f:
        json.dump([r["meta"] for r in recs], f, default=str)


def load_split(name):
    z = np.load(os.path.join(DATA_CACHE, f"{name}.npz"))
    metas = json.load(open(os.path.join(DATA_CACHE, f"{name}.meta.json")))
    off = z["offsets"]
    arrs = {k: z[k] for k in ARRAY_KEYS}
    recs = []
    for i, m in enumerate(metas):
        a, b = off[i], off[i + 1]
        r = {k: v[a:b] for k, v in arrs.items()}
        r["meta"] = m
        recs.append(r)
    return recs


def exists(name):
    return os.path.exists(os.path.join(DATA_CACHE, f"{name}.npz"))


# ------------------------------------------------------------------ leakage checks + manifest
def leakage_checks(all_splits):
    chk = {}
    ids = {s: {r["meta"]["writer"]["writer_id"] for r in recs} for s, recs in all_splits.items()}
    names = list(ids)
    inter = {f"{a}&{b}": sorted(ids[a] & ids[b]) for i, a in enumerate(names) for b in names[i + 1:]}
    chk["writer_ids_disjoint"] = all(len(v) == 0 for v in inter.values())
    keys = {}
    dup_keys = []
    for s, recs in all_splits.items():
        for r in recs:
            k = tuple(r["meta"]["seed"]["spawn_key"])
            if k in keys:
                dup_keys.append([s, keys[k], list(k)])
            keys[k] = s
    chk["seed_spawn_keys_unique"] = len(dup_keys) == 0
    hashes = {}
    dup_h = []
    for s, recs in all_splits.items():
        for r in recs:
            h = r["meta"].get("content_hash")
            if s == "realism_sim":        # 5 runs per simulator seed share one intended path
                h = f"{h}-{r['meta']['sim']['seed']}"
                if r["meta"]["sim"]["f0"] is not None:
                    continue
            if h in hashes and hashes[h] != s:
                dup_h.append([s, hashes[h]])
            hashes.setdefault(h, s)
    chk["intended_paths_unique_across_splits"] = len(dup_h) == 0
    lo, hi = C.HOLDOUT_BAND
    viol = []
    for s in ("train", "val", "test"):
        for r in all_splits.get(s, []):
            for seg in r["meta"]["segments"]:
                if lo <= seg["spec"]["f0"] < hi:
                    viol.append([s, r["meta"]["record_id"], seg["spec"]["f0"]])
    chk["no_holdout_f0_in_train_val_test"] = len(viol) == 0
    hold_ok = all(lo <= seg["spec"]["f0"] < hi for r in all_splits.get("test_freq_holdout", [])
                  for seg in r["meta"]["segments"])
    chk["holdout_f0_all_in_band"] = bool(hold_ok)
    tr = all_splits.get("train", [])
    fin = np.concatenate([r["finst_tgt"][r["env_tgt"] > 0] for r in tr]) if tr else np.zeros(0)
    chk["train_fraction_instantaneous_f_in_holdout_band"] = float(np.mean((fin >= lo) & (fin < hi))) if len(fin) else 0.0
    chk["feature_course_only_in_test_features"] = all(
        "course" not in r["meta"] for s, recs in all_splits.items() if s != "test_features" for r in recs)
    from sim.pensim import harness
    chk["realism_seeds_disjoint_from_sim_tuning_and_test"] = (
        not set(REALISM_SEEDS) & set(harness.TUNING_SEEDS) and not set(REALISM_SEEDS) & set(harness.TEST_SEEDS))
    chk["input_normalisation_fixed_a_priori"] = True   # IN_CLIP_UM, S_IN, S_OUT, F_REF, F_GAIN are constants
    chk["target_after_window"] = "target d(t_k + h) lies strictly after the newest input sample (t_k - delay); " \
                                 "verified by ml/tests (output invariant to later inputs)"
    chk["all_pass"] = all(v for k, v in chk.items() if isinstance(v, bool))
    chk["detail"] = {"writer_id_intersections": inter, "duplicate_spawn_keys": dup_keys,
                     "duplicate_content_hashes": dup_h, "holdout_violations": viol}
    return chk


def split_summary(recs):
    n = sum(len(r["t"]) for r in recs)
    env = np.concatenate([r["env_tgt"] for r in recs])
    pen = np.concatenate([r["pen_tgt"] for r in recs])
    f0s = [seg["spec"]["f0"] for r in recs for seg in r["meta"].get("segments", [])]
    amps = [seg["spec"]["amp_pk"] for r in recs for seg in r["meta"].get("segments", [])]
    out = {"n_records": len(recs), "n_ticks": int(n), "hours": n * C.TS / 3600, "frac_tremor_ticks": float(np.mean(env > 0)),
           "frac_pen_down": float(np.mean(pen)), "n_tremor_segments": len(f0s)}
    if f0s:
        bi = C.band_index(np.array(f0s))
        out["segments_per_band"] = {C.BAND_NAMES[i]: int(np.sum(bi == i)) for i in range(len(C.BANDS))}
        out["amp_pk_mm_quantiles"] = [float(np.percentile(np.array(amps) * 1e3, q)) for q in (0, 25, 50, 75, 100)]
    spec = [r["meta"].get("intended_spectrum") for r in recs if r["meta"].get("intended_spectrum")]
    if spec:
        for k in ("v_4_7Hz", "v_8_12Hz", "speed_mean_down_mm_s"):
            v = np.array([s[k] for s in spec], float)
            out[f"intended_{k}_median_iqr"] = [float(np.nanmedian(v)), float(np.nanpercentile(v, 25)),
                                               float(np.nanpercentile(v, 75))]
    return out


# ------------------------------------------------------------------ schema examples
def example_samples(all_splits, kf_src):
    """A few windows serialised per data/schema/ml_sample.schema.json."""
    out = []
    picks = [("train", 0), ("train", 3), ("val", 0), ("test", 1), ("test_freq_holdout", 0), ("test_features", 0),
             ("realism_sim", 1)]
    for s, i in picks:
        if s not in all_splits or i >= len(all_splits[s]):
            continue
        r = all_splits[s][i]
        env = r["env_tgt"]
        cand = np.flatnonzero((env > 0.99) & r["pen_tgt"] & (r["t"] > 2.0))
        if len(cand) == 0:
            cand = np.flatnonzero(r["pen_tgt"] & (r["t"] > 2.0))
        k = int(cand[len(cand) // 2])
        m = r["meta"]
        seg = None
        for sg_ in m.get("segments", []):
            if sg_["t0"] <= r["t"][k] + C.H_S < sg_["t1"]:
                seg = sg_
        wr = m.get("writer", {})
        out.append({
            "format_version": 1, "evidence_status": C.EVIDENCE,
            "sample_id": f"{m['record_id']}#{k}", "writer_id": wr.get("writer_id"), "split": s,
            "recording_id": m["record_id"], "tick_index": k, "t_s": float(r["t"][k]), "fs_hz": C.FS,
            "window": {"length": C.W, "dp_um": np.round(r["dp_um"][k - C.W + 1:k + 1].astype(float), 4).tolist(),
                       "f_est_hz": float(r["f_est"][k])},
            "horizon_s": C.H_S,
            "target": {"d_um": np.round(r["d_tgt_um"][k].astype(float), 4).tolist(), "t_target_s": float(r["t"][k] + C.H_S)},
            "labels": {"tremor_present": bool(env[k] > 0), "tremor_envelope": float(env[k]), "pen_down": bool(r["pen_tgt"][k]),
                       "f0_nominal_hz": float(r["f0_tgt"][k]) if env[k] > 0 else None,
                       "band": C.BAND_NAMES[int(C.band_index(r["f0_tgt"][k]))] if env[k] > 0 else None},
            "tremor": None if seg is None else {"segment_t0_s": seg["t0"], "segment_t1_s": seg["t1"], **seg["spec"]},
            "writer": {k2: v for k2, v in wr.items() if k2 not in ("tremor", "sensor", "seed")},
            "sensor": wr.get("sensor") or m.get("sensor"),
            "seed": m["seed"],
            "generator": {"name": synth.GEN_VERSION, "f_est_source": "ml/baselines.py kf_run (port of sim/pensim/core.py)",
                          "kf_params_source": kf_src.get("file")},
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="few writers per split (smoke test)")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--no-realism", action="store_true")
    ap.add_argument("--only", nargs="*", default=None, help="build only these splits; load the others from cache "
                    "and reuse the KF snapshot of the existing manifest")
    args = ap.parse_args()
    t0 = time.time()
    man_path = os.path.join(C.RESULTS, "dataset_manifest.json")
    if args.only and os.path.exists(man_path):
        old = json.load(open(man_path))
        kf_frozen, kf_src = old["kf_frozen_250Hz"], old["kf_frozen_source"]
    else:
        kf_frozen, kf_src = BL.frozen_kf_params()
    kf_feat = BL.feature_kf_params(kf_frozen)
    BL.kf_run(np.zeros((8, 2)), **kf_feat)          # compile numba once before forking workers
    BL.bmflc_run(np.zeros((8, 2)))
    all_splits = {}
    want = lambda nm: args.only is None or nm in args.only  # noqa: E731
    for s, cfg in SPLITS.items():
        if not want(s):
            if exists(s):
                all_splits[s] = load_split(s)
            continue
        n = 4 if args.quick else cfg["n"]
        jobs = [(s, i, kf_feat) for i in range(n)]
        if args.workers > 1:
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(args.workers) as ex:
                recs = list(ex.map(_build_writer_star, jobs, chunksize=4))
        else:
            recs = [build_writer(*j) for j in jobs]
        save_split(s, recs)
        all_splits[s] = recs
        print(f"{s}: {len(recs)} writers, {time.time() - t0:.1f} s", flush=True)
    if want("test_features"):
        recs = build_feature_course(kf_feat)
        save_split("test_features", recs)
        all_splits["test_features"] = recs
        print(f"test_features: {len(recs)} runs, {time.time() - t0:.1f} s", flush=True)
    elif exists("test_features"):
        all_splits["test_features"] = load_split("test_features")
    realism_status = "built"
    if not want("realism_sim"):
        if exists("realism_sim"):
            all_splits["realism_sim"] = load_split("realism_sim")
            realism_status = json.load(open(man_path)).get("realism_status", "built") if os.path.exists(man_path) else "built"
    elif not args.no_realism:
        try:
            recs = build_realism(kf_feat)
            save_split("realism_sim", recs)
            all_splits["realism_sim"] = recs
        except Exception as e:  # the simulator is owned and edited by others; never block on it
            realism_status = f"FAILED: {type(e).__name__}: {e}"
        print(f"realism_sim: {realism_status}, {time.time() - t0:.1f} s", flush=True)
    chk = leakage_checks(all_splits)
    print("leakage checks all_pass =", chk["all_pass"], flush=True)
    man = {
        "meta": C.meta(seeds={"master": MASTER_SEED, "spawn_key": "(split_code, writer_index)",
                              "split_codes": {s: c["code"] for s, c in SPLITS.items()} |
                              {"test_features": 5, "realism_sim": 6}},
                       extra={"elapsed_s": time.time() - t0, "quick": args.quick, "generator": synth.GEN_VERSION}),
        "contract": {"fs_hz": C.FS, "window": C.W, "horizon_s": C.H_S, "time_stamp": "arrival; physical horizon = h + delay",
                     "inputs": "dp_um (x,y) increments, f_est_hz", "output": "d_hat_um (x,y) at t_k + h"},
        "kf_frozen_250Hz": kf_frozen, "kf_frozen_source": kf_src, "kf_feature_params": kf_feat,
        "splits": {s: split_summary(r) | {"writer_ids": [x["meta"]["writer"]["writer_id"] for x in r]}
                   for s, r in all_splits.items()},
        "realism_status": realism_status,
        "leakage_checks": chk,
        "cache": C.rpath(DATA_CACHE),
    }
    C.write_json(os.path.join(C.RESULTS, "dataset_manifest.json"), man)
    ex = example_samples(all_splits, kf_src)
    os.makedirs(os.path.join(C.DATA_DIR, "samples"), exist_ok=True)
    with open(os.path.join(C.DATA_DIR, "samples", "ml_samples_example.json"), "w") as f:
        json.dump({"evidence_status": C.EVIDENCE, "schema": "data/schema/ml_sample.schema.json", "samples": ex}, f, indent=1)
    print(f"done in {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
