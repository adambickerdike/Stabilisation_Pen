r"""The random search's own objectives, re-optimised by the adjoint (SIMULATION).

fusion.tune found the two published AKF sets by random search + local refinement of open-loop proxies on the
tuning data.  Here the same proxies are written in PyTorch on exactly the same streams (sensor-noise tags 7/8 of
fusion.harness.sensor_seed for seeds 5000-5007, fusion.tune.aiguide_items for writers 100-105) and minimised by
Adam through the AKF adjoint, starting from the random search's winner:
  grid     J = mean RR + 8 mean(HF / RMS d) + 2 max(0, FC / 14 um - 1)                          (fusion.tune.proxy)
  robust   J = 0.5 RR_grid + 0.5 RR_aiguide + 8 HF_grid + 2 max(0, FC_grid / 14 um - 1)
               + 2 max(0, FC_aiguide / 30 um - 1)                                           (fusion.tune.proxy_robust)
with RR = sqrt(sum |d - clip(d_hat)|^2 / sum |d|^2) over the in-contact ticks after 0.5 s (all frequencies, d the
oracle's disturbance), HF the RMS above 150 Hz, FC the RMS of d_hat on the tremor-free writing.  Same objective,
same data: any improvement is the optimiser's.  The objective value of the numba AKF from fusion.tune.proxy /
proxy_robust is reproduced first (check).
"""
from __future__ import annotations

import math
import time
from typing import Callable, Dict, List

import numpy as np
import torch

from . import data as DA
from . import losses as LS
from . import torch_akf as TA
from . import train_akf as TR
from . import adjoint as AD

from fusion import data as FD  # noqa: E402
from fusion import harness as H  # noqa: E402
from fusion import sensors as S  # noqa: E402
from fusion import TUNE_SEEDS  # noqa: E402

FC_MAX = 14e-6
FC_AI_MAX = 30e-6


def _grid_job(args):
    s, f0, a = args
    r1, r0 = FD.test_pair_records(s, f0, a)
    cfg = S.config(page="1k", comp="gyro")
    st1 = S.make_streams(r1, cfg, H.sensor_seed(s, f0, a, 7))
    m = (np.interp(st1.tick_t, r1.t, r1.contact) > 0.5) & (st1.tick_t > 0.5)
    out = [DA._item(st1, S.truth_at(st1.tick_t, r1, r0), m, False, False, {"set": "fusion_tune", "seed": s, "f0": f0,
                                                                             "amp_mm": a * 1e3, "clean": False})]
    if f0 == 4.0 and abs(a - 0.1e-3) < 1e-12:            # fusion.tune.load: the clean run of (s, F0S[0], AMPS[0])
        st0 = S.make_streams(r0, cfg, H.sensor_seed(s, 0.0, 0.0, 8))
        m0 = (np.interp(st0.tick_t, r0.t, r0.contact) > 0.5) & (st0.tick_t > 0.5)
        out.append(DA._item(st0, np.zeros((len(st0.tick_t), 2)), m0, True, False,
                            {"set": "fusion_tune", "seed": s, "f0": 0.0, "amp_mm": 0.0, "clean": True}))
    return out


def fusion_tune_items(workers: int = 2) -> List[Dict]:
    jobs = [(s, f0, a) for s in TUNE_SEEDS for f0 in H.F0S for a in H.AMPS]
    return DA._cached("fusion_tune_grid", lambda: DA._map(_grid_job, jobs, workers))


def _terms(rs: DA.RecSet, dh: torch.Tensor) -> Dict[str, torch.Tensor]:
    m = rs.m[..., None]
    n = rs.m.sum(1).clamp(min=1.0)
    e = rs.d - LS.clip(dh)
    den = (rs.d ** 2 * m).sum((1, 2)).clamp(min=1e-30)
    rr = torch.sqrt((e ** 2 * m).sum((1, 2)) / den + 1e-30)
    dn = torch.sqrt(den / n)
    hp = LS.causal_hp150(dh, 2000.0)
    hf = torch.sqrt((hp ** 2 * m).sum((1, 2)) / n + 1e-30)
    fc = torch.sqrt((dh ** 2 * m).sum((1, 2)) / n + 1e-30)
    return {"rr": rr, "hf_rel": hf / dn, "fc": fc}


def objective(kind: str, sets: Dict[str, DA.RecSet], vals: Dict, static: Dict, beta=None, grad: bool = False):
    ctx = torch.enable_grad() if grad else torch.no_grad()
    with ctx:
        g = sets["grid"]
        tg = _terms(g, AD.forward(g.pk, g.ev, vals, static, gate_beta=beta))
        tr = ~g.clean
        rr_g = tg["rr"][tr].mean()
        hf_g = tg["hf_rel"][tr].mean()
        fc_g = tg["fc"][g.clean].mean()
        info = {"rr_grid": float(rr_g), "hf_rel_grid": float(hf_g), "fc_grid_um": float(fc_g) * 1e6}
        if kind == "grid":
            J = rr_g + 8.0 * hf_g + 2.0 * torch.clamp(fc_g / FC_MAX - 1.0, min=0.0)
        else:
            a = sets["ai"]
            ta = _terms(a, AD.forward(a.pk, a.ev, vals, static, gate_beta=beta))
            rr_a = ta["rr"][~a.clean].mean()
            fc_a = ta["fc"][a.clean].mean()
            J = (0.5 * rr_g + 0.5 * rr_a + 8.0 * hf_g + 2.0 * torch.clamp(fc_a / FC_AI_MAX - 1.0, min=0.0)
                 + 2.0 * torch.clamp(fc_g / FC_MAX - 1.0, min=0.0))
            info.update({"rr_ai": float(rr_a), "fc_ai_um": float(fc_a) * 1e6})
        info["J"] = float(J)
    return J, info


def reference_value(kind: str, params: Dict) -> Dict:
    """fusion.tune's own value of the objective (numba AKF, its own code path)."""
    from fusion import tune as TU
    if kind == "grid":
        r = TU.proxy("akf", params, {"page": "1k", "comp": "gyro"}, FC_MAX)
        return {"J": r["J"], "rr_grid": r["rr_mean"], "fc_grid_um": r["fc_um"], "hf_rel_grid": r["hf_rel_mean"]}
    ai = TU.aiguide_items({"page": "1k", "comp": "gyro"})
    for it in ai:
        it.pop("templates", None)
    r = TU.proxy_robust("akf", params, {"page": "1k", "comp": "gyro"}, ai, FC_MAX)
    return {"J": r["J"], "rr_grid": r["rr_mean"], "rr_ai": r["rr_ai_mean"], "fc_ai_um": r["fc_ai_um"],
            "fc_grid_um": r["fc_um"], "hf_rel_grid": r["hf_rel_mean"]}


def run(kind: str, start_params: Dict, iters: int = 40, lr: float = 0.03, leak0: float = 0.1, log: Callable = print,
        workers: int = 2) -> Dict:
    torch.set_num_threads(1)
    AD.set_threads(2)
    sets = {"grid": DA.build_set(fusion_tune_items(workers))}
    if kind == "robust":
        sets["ai"] = DA.build_set(DA.tune_ai_items())
    static = TA.static_of(start_params)
    t0 = time.time()
    ref = reference_value(kind, start_params)
    J0, info0 = objective(kind, sets, TA.numba_to_values(start_params), static)
    log(f"[replicate {kind}] fusion.tune value J {ref['J']:.5f}; torch value J {info0['J']:.5f} ({time.time() - t0:.0f} s)")
    cfg = TR.TrainCfg(iters=iters, lr=lr, leak0=leak0, harm=static["harm"])
    theta = TR.project(TA.to_theta(TA.trainable_start(start_params)).clone()).requires_grad_(True)
    optim = torch.optim.Adam([theta], lr=lr)
    hist = []
    best = None
    for it in range(iters + 1):
        with torch.no_grad():
            vh = {k: float(v) for k, v in TA.from_theta(theta.detach()).items()}
        _, info_h = objective(kind, sets, vh, static)                        # exact gates: the deployed filter
        if best is None or info_h["J"] < best["info"]["J"]:
            best = {"iter": it, "info": info_h, "vals": vh}
        hist.append({"iter": it, **info_h})
        log(f"[replicate {kind}] it {it}: J {info_h['J']:.5f} " + " ".join(f"{k} {v:.4g}" for k, v in info_h.items() if k != "J")
            + f" ({time.time() - t0:.0f} s)")
        if it == iters:
            break
        J, _ = objective(kind, sets, TA.from_theta(theta), static, beta=TR.beta_at(it, cfg), grad=True)
        optim.zero_grad()
        J.backward()
        g = theta.grad
        g[~torch.isfinite(g)] = 0.0
        gn = float(g.norm())
        if gn > cfg.grad_clip:
            g.mul_(cfg.grad_clip / gn)
        optim.step()
        TR.project(theta)
    p_best = TA.to_numba(best["vals"], static)
    ref_best = reference_value(kind, p_best)
    log(f"[replicate {kind}] best iter {best['iter']}: torch J {best['info']['J']:.5f}; fusion.tune value of the result "
        f"{ref_best['J']:.5f} (start {ref['J']:.5f}) ({time.time() - t0:.0f} s)")
    return {"kind": kind, "start_reference": ref, "start_torch": info0, "best": best, "params": p_best,
            "result_reference": ref_best, "history": hist, "elapsed_s": time.time() - t0,
            "objective": __doc__.split("with RR")[0].strip()}
