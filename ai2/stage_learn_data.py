"""Stage learn_data: domain-randomised training samples (writers >= 1000) and the tuning set (writers 100-103, seed 300,
the D0 conditions) with sensor features, targets and the model-based estimates (RTS, Rev H tracker, detector).

Evidence status: SIMULATION.  Output: ai2/build/learn_data/*.npz (regenerable, git-ignored).
"""
from __future__ import annotations

import json

import numpy as np

from . import TUNE_SEEDS, TUNE_WRITERS, ensure_paths
from . import common as C
from . import data as DA

ensure_paths()

N_TRAIN = 320
N_TRAIN_QUICK = 12


def model_params(quick: bool):
    """The model-based stack fixed on tuning data: D0 tremor smoother, D1 gate, D2b amplitude gate."""
    from . import delayed as DL
    from . import tuning as TU
    d01 = C.load("d01", quick) or C.load("d01", False)
    if d01 is None:
        raise FileNotFoundError("ai2 frozen tuning cache d01 is missing; rebuild it before loading model parameters")
    tp = dict(DL.TREMOR_DEFAULTS); tp.update(d01["chosen_tremor"])
    dp = dict(DL.DET_DEFAULTS); dp.update(d01["chosen_det"] or {})
    out = {"tremor": tp, "det": dp, "amp_gate": (0.0, 0.0)}
    d2b = C.load("d2b", quick) or C.load("d2b", False)
    if d2b:
        ck = d2b["selection"]["causal_gated"].rsplit("_nose", 1)[0]
        c = next(c for c in d2b["candidates"] if TU.key(c) == ck)
        out["amp_gate"] = (c.get("amp_lo", 0.0), c.get("amp_hi", 0.0))
    return out


def _train_job(job):
    DA.set_quick(job.get("quick", False))
    return DA.save_sample(job["i"], "train", job["mp"])


def tuning_arrays(w: int, mp, seed: int = TUNE_SEEDS[0]):
    from aiprior import core as CO
    from fusion import learned as FL
    from handwriting import params as PR
    from . import tuning as TU
    wr = CO.Writer(w)
    clean = wr.su.clean["revH"]
    out = []
    for f0, amp in TU.conditions():
        sc = TU.scenario(wr, f0, amp, seed)
        X, tk = FL.features(sc.streams, DA.NET_HZ)
        delta = PR.servo_group_delay(sc.pen)
        Y, con = DA.targets_for(sc.neutral, clean, tk, delta)
        mb = DA.model_based(sc.streams, sc.pen, tk, mp["tremor"], mp["det"])
        out.append({"X": X.astype(np.float32), "Y": Y.astype(np.float32), "mask": (con & (tk > 1.0)).astype(np.float32),
                    "spec": {"writer": w, "f0": f0, "amp": amp, "seed": seed}, **mb})
    return out


def _tune_job(job):
    DA.set_quick(job.get("quick", False))
    arrs = tuning_arrays(job["w"], job["mp"])
    p = DA.DATA_DIR / f"tune_w{job['w']}.npz"
    DA.DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, **{f"{k}_{i}": (np.array(json.dumps(v)) if k == "spec" else v) for i, a in enumerate(arrs) for k, v in a.items()},
                        n=np.array(len(arrs)))
    return str(p)


def load_tuning(writers=TUNE_WRITERS):
    out = []
    for w in writers:
        p = DA.DATA_DIR / f"tune_w{w}.npz"
        if not p.exists():
            continue
        z = np.load(p)
        for i in range(int(z["n"])):
            d = {}
            for k in ("X", "Y", "mask") + DA.MB_KEYS:
                d[k] = z[f"{k}_{i}"]
            d["spec"] = json.loads(str(z[f"spec_{i}"]))
            out.append(d)
    return out


def run(quick: bool, workers: int):
    DA.set_quick(quick)
    mp = model_params(quick)
    n = N_TRAIN_QUICK if quick else N_TRAIN
    C.log(f"[learn_data] {n} training samples")
    C.jmap(_train_job, [{"i": i, "mp": mp, "quick": quick} for i in range(n)], workers)
    writers = TUNE_WRITERS[:1] if quick else TUNE_WRITERS
    C.log(f"[learn_data] tuning arrays for writers {writers}")
    C.jmap(_tune_job, [{"w": w, "mp": mp, "quick": quick} for w in writers], workers)
    C.save("learn_data", {"n_train": n, "tuning_writers": list(writers), "model_params": mp}, quick)
