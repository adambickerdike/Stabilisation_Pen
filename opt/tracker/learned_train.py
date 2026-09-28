"""Training of the learned trackers (opt.tracker.learned), SIMULATION.

Data: opt.tracker.data items (training pairs of fusion.learned._spec(i, "train"), randomised sensor rotation);
validation: the fusion validation pairs and tuning seeds 5004-5007.  Never the test seeds or aiguide test writers.
Full 5 s recordings (the recurrent state starts from zero at pen pick-up, as deployed), batches of 32 recordings,
AdamW with a one-cycle learning rate, gradient clipping; the epoch with the lowest validation objective is kept.
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional

import numpy as np
import torch

from . import MODEL_DIR
from . import data as DA
from . import learned as LN
from . import losses as LS
from . import torch_akf as TA

from fusion import learned as FL  # noqa: E402

F32 = torch.float32


@dataclass
class LCfg:
    kind: str = "gru"                 # "gru" | "hybrid"
    hidden: int = 48
    lam_fc: float = 0.2
    mu_hf: float = 0.02
    w_glyph_fc: float = 3.0
    lp_hz: float = 60.0               # gru: output low-pass (the hybrid uses its AKF's)
    epochs: int = 14
    batch: int = 32
    lr: float = 3e-3
    seed: int = 7
    max_minutes: float = 60.0


def arrays(items: List[Dict], akf_params: Optional[Dict] = None, chunk: int = 64) -> Dict[str, np.ndarray]:
    """Compact training arrays: inputs at 1 kHz, band truth and mask at the ticks, flags; the AKF's pre-low-pass
    estimate for the hybrid."""
    K = max(len(it["st"].tick_t) for it in items)
    items = [DA.pad_item(it, K) for it in items]
    K1 = int(math.ceil(K / 2))
    n = len(items)
    X7 = np.zeros((n, K1, FL.N_IN), np.float32)
    for b, it in enumerate(items):
        x, _ = FL.features(it["st"], LN.NET_HZ)
        X7[b, :min(K1, len(x))] = x[:K1]
    d = torch.as_tensor(np.stack([it["d"] for it in items]), dtype=TA.DT)
    db = LS.zero_phase(d, "band", 2000.0).numpy()
    out = {"X7": X7, "d": d.numpy(), "db": db, "m": np.stack([it["m"] for it in items]).astype(np.float32),
           "clean": np.array([it["clean"] for it in items]), "glyph": np.array([it["glyph"] for it in items]),
           "K": K, "K1": K1}
    if akf_params is not None:
        from . import adjoint as AD
        F = np.zeros((n, K1, LN.N_IN_GATE), np.float32)
        U = np.zeros((n, K, 2))
        static = TA.static_of(akf_params)
        for s in range(0, n, chunk):
            rs = DA.build_set(items[s:s + chunk])
            with torch.no_grad():
                prm = TA.expand(TA.numba_to_values(akf_params), rs.B)
                XO, W = AD.CoreFn.apply(AD.core_params(prm, static["harm"]), rs.pk, static["harm"])
                _, parts = TA.output_stage(XO, W, rs.ev, prm, static, None, return_parts=True)
            u = (parts["authority"][..., None] * parts["d_pred"]).numpy()
            for j in range(rs.B):
                b = s + j
                ap = {"u": u[j], "authority": parts["authority"][j].numpy(), "f_est": parts["f_est"][j].numpy(),
                      "amp_f": parts["amp_f"][j].numpy(), "v": XO[j, :, :, 0].numpy()}
                F[b] = LN.akf_features(items[b]["st"], ap, K1)
                U[b] = u[j]
        out["F16"] = F
        out["U"] = U
    return out


def _loss(dh, A, idx, cfg: LCfg, kind: str):
    """dh (b, K, 2) float64 at the ticks."""
    m = torch.as_tensor(A["m"][idx], dtype=TA.DT)
    clean = torch.as_tensor(A["clean"][idx])
    glyph = torch.as_tensor(A["glyph"][idx])
    db = torch.as_tensor(A["db"][idx], dtype=TA.DT)
    if kind == "gru":
        mm = m[..., None]
        n = m.sum(1).clamp(min=1.0)
        e = ((dh - db) ** 2 * mm).sum((1, 2))
        den = (db ** 2 * mm).sum((1, 2)).clamp(min=1e-30)
        rr = torch.sqrt(e / den + 1e-30)                                      # full-band error against the band truth
        fc = torch.sqrt((dh ** 2 * mm).sum((1, 2)) / n + 1e-30) * 1e6
        hp = LS.causal_hp150(LS.clip(dh), 2000.0)
        hf = torch.sqrt((hp ** 2 * mm).sum((1, 2)) / n + 1e-30) * 1e6
        t = {"rr": torch.where(clean, torch.full_like(rr, float("nan")), rr), "fc": fc, "hf": hf, "num": e, "den": den}
    else:
        d = torch.as_tensor(A["d"][idx], dtype=TA.DT)
        t = LS.terms(dh, d, db, m, clean, 2000.0)
    J, info = LS.objective(t, clean, glyph, LS.LossCfg(lam_fc=cfg.lam_fc, mu_hf=cfg.mu_hf, w_glyph_fc=cfg.w_glyph_fc))
    info.update(LS.summary(t, clean, glyph))
    return J, info


def _forward(model, A, idx, cfg: LCfg, kind: str, lp_hz: float):
    K = A["K"]
    if kind == "gru":
        x = torch.from_numpy(A["X7"][idx])
        y, _ = model(x)
        return LN.zoh_lp(y.double() * LN.OUT_S, K, lp_hz)
    x = torch.from_numpy(A["F16"][idx])
    gam, _ = model(x)
    g2 = gam.double().repeat_interleave(2, dim=1)[:, :K]
    if g2.shape[1] < K:
        g2 = torch.cat([g2, g2[:, -1:].expand(g2.shape[0], K - g2.shape[1], 1)], 1)
    return LN.zoh_lp_ticks(torch.as_tensor(A["U"][idx]) * g2, lp_hz)


def evaluate(model, A, cfg: LCfg, kind: str, lp_hz: float, batch: int = 64) -> Dict:
    model.eval()
    parts = []
    with torch.no_grad():
        dh = torch.cat([_forward(model, A, np.arange(s, min(len(A["m"]), s + batch)), cfg, kind, lp_hz)
                        for s in range(0, len(A["m"]), batch)], 0)
        J, info = _loss(dh, A, np.arange(len(A["m"])), cfg, kind)
    model.train()
    return info


def train(tr: Dict, vals: Dict[str, Dict], cfg: LCfg, name: str, akf_params: Optional[Dict] = None, log: Callable = print,
          threads: int = 2) -> Dict:
    torch.set_num_threads(threads)
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    kind = cfg.kind
    n_in = FL.N_IN if kind == "gru" else LN.N_IN_GATE
    n_out = 2 if kind == "gru" else 1
    model = LN.GRUTracker(n_in, cfg.hidden, n_out, gate=kind == "hybrid")
    lp_hz = cfg.lp_hz if kind == "gru" else float(TA.complete(akf_params)["lp_hz"])
    n = len(tr["m"])
    steps_per_epoch = max(1, n // cfg.batch)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=cfg.lr, total_steps=cfg.epochs * steps_per_epoch, pct_start=0.15)
    t0 = time.time()
    hist = []
    best = None
    v0 = {k: evaluate(model, A, cfg, kind, lp_hz) for k, A in vals.items()}
    log(f"[{name}] start val " + " | ".join(f"{k}: J {v['J']:.3f} rr {v['rr_band']:.3f} fc {v['fc_w_um']:.1f}" for k, v in v0.items()))
    stop = False
    for ep in range(cfg.epochs):
        perm = rng.permutation(n)
        tl = []
        for s in range(steps_per_epoch):
            idx = np.sort(perm[s * cfg.batch:(s + 1) * cfg.batch])
            dh = _forward(model, tr, idx, cfg, kind, lp_hz)
            J, info = _loss(dh, tr, idx, cfg, kind)
            opt.zero_grad()
            J.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            if sched.last_epoch < sched.total_steps - 1:
                sched.step()
            tl.append(info["J"])
            if (time.time() - t0) / 60.0 > cfg.max_minutes:
                stop = True
                break
        v = {k: evaluate(model, A, cfg, kind, lp_hz) for k, A in vals.items()}
        score = float(np.mean([x["J"] for x in v.values()]))
        hist.append({"epoch": ep, "train_J": float(np.mean(tl)), "val": v, "score": score, "elapsed_s": time.time() - t0})
        log(f"[{name}] epoch {ep}: train J {np.mean(tl):.4f} | " + " | ".join(
            f"{k}: J {x['J']:.3f} rr {x['rr_band']:.3f} fc {x['fc_w_um']:.1f} hf {x['hf_um']:.2f}" for k, x in v.items())
            + f" ({time.time() - t0:.0f} s)")
        if best is None or score < best[0]:
            best = (score, {k: t.detach().clone() for k, t in model.state_dict().items()}, ep)
        if stop:
            break
    model.load_state_dict(best[1])
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, name + ".pt"))
    meta = {"name": name, "kind": kind, "n_in": n_in, "hidden": cfg.hidden, "n_out": n_out, "out_scale": LN.OUT_S,
            "lp_hz": lp_hz, "net_hz": LN.NET_HZ, "cfg": asdict(cfg), "best_epoch": best[2], "history": hist,
            "start_val": v0, "macs_per_step": LN.macs_per_step(n_in, cfg.hidden, n_out),
            "params": LN.n_params(n_in, cfg.hidden, n_out), "train_recordings": int(n), "total_s": time.time() - t0,
            "akf_params": akf_params}
    with open(os.path.join(MODEL_DIR, name + ".json"), "w") as f:
        json.dump(meta, f, indent=1, default=float)
    LN._MODELS.pop(name, None)
    return meta


# ------------------------------------------------------------------ compact data for the GRU (all 400 training pairs)
def _gru_job(args):
    i, kind = args
    items = DA._pair_job((i, kind))
    A = arrays(items)
    return {k: (v.astype(np.float32) if isinstance(v, np.ndarray) and v.dtype == np.float64 else v) for k, v in A.items()}


def gru_data(idx, kind: str = "train", tag: str = "", workers: int = 1) -> Dict[str, np.ndarray]:
    """Inputs, band truth, mask and flags of the pairs `idx` (both runs of each pair), cached as npz."""
    from . import CACHE
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"gru_{kind}_{tag or len(idx)}.npz")
    if os.path.exists(p):
        z = np.load(p)
        out = {k: z[k] for k in z.files}
        out["K"] = int(out["K"]); out["K1"] = int(out["K1"])
        return out
    jobs = [(i, kind) for i in idx]
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as ex:
            parts = list(ex.map(_gru_job, jobs))
    else:
        parts = [_gru_job(j) for j in jobs]
    out = {}
    for k in ("X7", "d", "db", "m", "clean", "glyph"):
        out[k] = np.concatenate([q[k] for q in parts], 0)
    out["K"] = parts[0]["K"]; out["K1"] = parts[0]["K1"]
    np.savez(p + ".tmp.npz", **out)
    os.replace(p + ".tmp.npz", p)
    return out
