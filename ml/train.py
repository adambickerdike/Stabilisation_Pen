#!/usr/bin/env python3
r"""Train the TCN disturbance predictor (SIMULATION / synthetic data).

Objective (per window k, target d(t_k + h), both in units of S_OUT):
    L = sum_k w_k |y_hat_k - y_k|^2 / sum_k w_k,
    w_k = 1 on tremor ticks (envelope > 0), LAMBDA_NT on no-tremor ticks (target 0),
i.e. MSE on the future disturbance plus a penalty on predictions (false
correction) where no tremor is present.  AdamW, cosine learning rate, fixed
seeds, 2 CPU threads.  Model selection: the epoch with the lowest validation
all-band residual ratio at matched false correction FC <= 25 um (the same
criterion used to tune every baseline).  Training writers only; validation
writers only for selection; test writers never touched here.
Outputs: results/ml/model/<name>.pt (+ .json), results/ml/train_<name>.json.
--no-fest (tcn_s_nofest, the exported model, ICD s5 contract v1.1) keeps the 3-channel
training layout with the f_est channel held at zero (config use_fest false); the pipeline
deploys it as the equivalent 2-channel model (quantize.load_float -> models.drop_fest).
Run: python3 -m ml.train --model tcn_s
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import torch

from . import common as C
from . import baselines as BL
from . import datasets as D
from . import metrics as MT
from . import models as M


def stack_split(recs):
    ch = np.vstack([M.input_channels(r["dp_um"], r["f_est"]) for r in recs]).astype(np.float32)
    y = (np.vstack([r["d_tgt_um"] for r in recs]) / C.S_OUT).astype(np.float32)
    w = np.concatenate([BL.sample_weights(r) for r in recs]).astype(np.float32)
    return ch, y, w


def val_score(model, recs):
    st = MT.stack([MT.rec_stats(r, M.predict(model, r)) for r in recs])
    rr25, g25 = MT.matched_rr_all(st, C.FC_HEADLINE_UM)
    p1 = MT.pooled(st, 1.0)
    return {"rr_all_at_fc25": rr25, "gain_fc25": g25, "rr_all_g1": p1["rr_all"], "fc_g1_um": p1["fc_um"],
            "rr_band_g1": [float(x) for x in p1["rr_band"]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="tcn_s", choices=list(M.CONFIGS))
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--max-minutes", type=float, default=9.0)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--samples-per-epoch", type=int, default=1_500_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--no-fest", action="store_true", help="ablation: f_est channel held at zero")
    ap.add_argument("--tag", default="", help="suffix of the saved model name")
    args = ap.parse_args()
    name = args.model + args.tag
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    t0 = time.time()
    train, val = D.load_split("train"), D.load_split("val")
    ch, y, w = stack_split(train)
    if args.no_fest:
        ch[:, 2] = 0.0
    idx_all = np.flatnonzero(w > 0)
    print(f"train windows {len(idx_all)}, val writers {len(val)}, load {time.time() - t0:.1f} s", flush=True)
    model = M.build(args.model)
    model.use_fest = not args.no_fest
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps_per_epoch = args.samples_per_epoch // args.batch
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=args.epochs * steps_per_epoch,
                                                pct_start=0.1, anneal_strategy="cos")
    log = []
    best = (np.inf, None, -1)
    out_dir = os.path.join(C.RESULTS, "model")
    os.makedirs(out_dir, exist_ok=True)
    for ep in range(args.epochs):
        model.train()
        te = time.time()
        sel = rng.choice(idx_all, size=steps_per_epoch * args.batch, replace=False)
        tot, totw = 0.0, 0.0
        for s in range(steps_per_epoch):
            bi = sel[s * args.batch:(s + 1) * args.batch]
            xb = torch.from_numpy(M.gather_windows(ch, bi))
            yb = torch.from_numpy(y[bi])
            wb = torch.from_numpy(w[bi])
            pred = model(xb)
            loss = (wb * ((pred - yb) ** 2).sum(1)).sum() / wb.sum()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tot += float(loss.detach()) * float(wb.sum())
            totw += float(wb.sum())
        vs = val_score(model, val)
        row = {"epoch": ep + 1, "train_loss": tot / totw, "lr": sched.get_last_lr()[0], "epoch_s": time.time() - te,
               "elapsed_s": time.time() - t0, **vs}
        log.append(row)
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()
                          if k != "rr_band_g1"}), flush=True)
        if vs["rr_all_at_fc25"] < best[0]:
            best = (vs["rr_all_at_fc25"], {k: v.clone() for k, v in model.state_dict().items()}, ep + 1)
        if (time.time() - t0) / 60 > args.max_minutes and ep + 1 < args.epochs:
            print(f"time budget reached after epoch {ep + 1}", flush=True)
            break
    model.load_state_dict(best[1])
    torch.save(model.state_dict(), os.path.join(out_dir, f"{name}.pt"))
    cfg = model.config() | {"name": name, "use_fest": model.use_fest, "macs_window": model.macs(),
                            "n_params": model.n_params(),
                            "best_epoch": best[2], "val_rr_all_at_fc25": best[0],
                            "input": {"IN_CLIP_UM": C.IN_CLIP_UM, "S_IN": C.S_IN, "F_REF_HZ": C.F_REF_HZ,
                                      "F_GAIN": C.F_GAIN, "S_OUT": C.S_OUT, "W": C.W, "fs_hz": C.FS, "horizon_s": C.H_S}}
    with open(os.path.join(out_dir, f"{name}.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    C.write_json(os.path.join(C.RESULTS, f"train_{name}.json"), {
        "meta": C.meta(seeds={"torch": args.seed, "numpy": args.seed},
                       extra={"args": vars(args), "elapsed_s": time.time() - t0, "threads": args.threads}),
        "objective": "weighted MSE on d(t+h)/S_OUT; w = 1 tremor, LAMBDA_NT no-tremor",
        "lambda_nt": C.LAMBDA_NT, "selection": "min validation rr_all at matched FC <= 25 um",
        "config": cfg, "log": log})
    print(f"saved {name}: best epoch {best[2]} val rr_all@FC25 {best[0]:.4f}, "
          f"{time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
