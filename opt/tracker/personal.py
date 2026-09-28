r"""Adjoint personalisation: per-writer AKF parameters by gradient descent on the 20 s calibration recording.

Inputs are exactly those of fusion.personal (never the test recording, never the simulator's truth): the
calibration task (spiral, circle, lines; the writer's tremor is an independent realisation, seed + 40000), the
pen's sensor streams of it, and the phone's label: the page-sensor path matched to the known shapes, cross-track
component band-passed 3-15 Hz per stroke (fusion.personal.page_label).  fusion.personal chooses among 12 AKF
variants by the fit
    s = sqrt( sum_use (band_at_page(d_hat) - label)^2 / sum_use label^2 )
where band_at_page interpolates the estimate at the page-sample times, projects it on the same normals and
band-passes it per stroke like the label.  Here the same fit is minimised over a subset of the AKF parameters by
Adam through the AKF adjoint (opt.tracker.adjoint) and an exact PyTorch version of band_at_page (scipy's
sosfiltfilt rebuilt from its own impulse and initial-condition responses, so it is the same linear operator),
starting from the 12-candidate choice, with a quadratic prior pulling the log-parameters back to that start:
    L = s^2 + rho * sum_k (theta_k - theta_k,start)^2  [+ lambda_fc,p * FC / 100 um]
The optional last term is the false correction of the writer's candidate set on tremor-free writing of OTHER
writers (fusion training specs): the calibration task always contains tremor, so without it nothing tells the fit
to stay quiet on writing (the first version, without it, gained in the tremor band and nearly tripled distortion).
The prior weight and lambda_fc,p are chosen on tuning seeds 5000-5003 (their calibration recordings and their 0.3 mm
grid conditions), never on the test seeds.
"""
from __future__ import annotations

import math
import time
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import torch
from scipy.signal import sosfilt, sosfilt_zi

from . import CALIB_SEED_OFFSET
from . import adjoint as AD
from . import data as DA
from . import schedule as SCH
from . import torch_akf as TA
from . import train_akf as TR

from fusion import personal as PS  # noqa: E402
from fusion import sensors as S  # noqa: E402

SK_1K = {"page": "1k", "comp": "gyro"}
PERSONAL_KEYS = ("qt", "tau_decay", "w0_hz", "tau_w", "wmin_hz", "wmax_hz", "a_c", "a_w", "horizon", "g", "lp_hz",
                 "cap_k")


# ------------------------------------------------------------------ exact sosfiltfilt as a torch operator
class SosFiltFilt:
    """scipy.signal.sosfiltfilt(sos, x, padtype='odd', padlen=p) for 1-D x, as linear torch operations:
    sosfilt with zi = sosfilt_zi(sos) * v[0] equals conv(h, v) + v[0] g_zi (h: zero-state impulse response,
    g_zi: free response from the state zi), both computed by scipy itself up to n_max samples."""

    def __init__(self, sos, n_max: int):
        imp = np.zeros(n_max); imp[0] = 1.0
        self.h = torch.as_tensor(sosfilt(sos, imp), dtype=TA.DT)
        zi = sosfilt_zi(sos)
        self.gz = torch.as_tensor(sosfilt(sos, np.zeros(n_max), zi=zi)[0], dtype=TA.DT)
        self.n_max = n_max

    def _sf(self, v):
        m = v.shape[-1]
        return TA._fft_causal_conv(v, self.h[:m].expand_as(v)) + v[..., :1] * self.gz[:m]

    def __call__(self, x, padlen: int):
        n = x.shape[-1]
        if padlen > 0:
            left = 2 * x[..., :1] - torch.flip(x[..., 1:padlen + 1], [-1])          # x[padlen:0:-1]
            right = 2 * x[..., -1:] - torch.flip(x[..., n - padlen - 1:n - 1], [-1])  # x[-2:-padlen-2:-1]
            ext = torch.cat([left, x, right], -1)
        else:
            ext = x
        if ext.shape[-1] > self.n_max:
            raise ValueError("segment longer than the precomputed responses")
        y = self._sf(ext)
        y = self._sf(y.flip(-1)).flip(-1)
        return y[..., padlen:padlen + n] if padlen > 0 else y


class Calib:
    """One calibration recording with its label (fusion.personal), as data for the torch fit."""

    def __init__(self, seed: int, f0: float, amp: float, sensor_kw: Dict = SK_1K):
        r1, _ = PS.calibration_records(seed, f0, amp, clean=False)
        self.st = S.make_streams(r1, S.config(**sensor_kw), seed + CALIB_SEED_OFFSET + 1)
        it = PS.calibration_path(dt=1e-3)
        self.pl = PS.page_label(self.st, it.xy[it.pen_down])
        self.est = PS.tremor_from_calibration(self.pl)
        self.seed, self.f0, self.amp = seed, f0, amp
        st, pl = self.st, self.pl
        # linear interpolation of the tick-rate estimate at the page times (np.interp semantics inside the range)
        tt = st.tick_t
        tq = np.clip(st.pos_t, tt[0], tt[-1])
        i = np.clip(np.searchsorted(tt, tq, side="right") - 1, 0, len(tt) - 2)
        f = (tq - tt[i]) / (tt[i + 1] - tt[i])
        self.i0 = torch.as_tensor(i, dtype=torch.long)
        self.fr = torch.as_tensor(f, dtype=TA.DT)
        self.nrm = torch.as_tensor(pl["normal"], dtype=TA.DT)
        self.segs = [(int(a), int(b)) for a, b in pl["segments"]]
        self.use = torch.as_tensor(pl["use"])
        lab = np.where(pl["use"], pl["label"], 0.0)
        self.lab = torch.as_tensor(lab, dtype=TA.DT)
        self.den = float(np.sum(lab[pl["use"]] ** 2))
        self.sff = SosFiltFilt(pl["sos"], max(b - a for a, b in self.segs) + 2 * 40)

    def band_at_page(self, dh: torch.Tensor) -> torch.Tensor:
        """fusion.personal.band_at_page for a (K, 2) torch estimate (differentiable)."""
        x = dh[self.i0] * (1.0 - self.fr)[:, None] + dh[self.i0 + 1] * self.fr[:, None]
        xn = (x * self.nrm).sum(1)
        out = torch.zeros_like(xn)
        parts, idx = [], []
        for a, b in self.segs:
            seg = xn[a:b] - xn[a:b].mean()
            parts.append(self.sff(seg, min(3 * 13, b - a - 1)))
            idx.append(torch.arange(a, b))
        return out.index_put((torch.cat(idx),), torch.cat(parts))

    def fit(self, dh: torch.Tensor) -> torch.Tensor:
        e = (self.band_at_page(dh) - self.lab) * self.use
        return torch.sqrt((e ** 2).sum() / self.den)


def fit_numpy(c: Calib, dh: np.ndarray) -> float:
    """fusion.personal's own score of an estimate (numpy, scipy): the reference for the torch operator."""
    m = c.pl["use"]
    e = PS.band_at_page(dh, c.st, c.pl)[m] - c.pl["label"][m]
    return float(np.sqrt(np.sum(e ** 2) / max(np.sum(c.pl["label"][m] ** 2), 1e-30)))


# ------------------------------------------------------------------ the fit
def refine(calibs: Sequence[Calib], starts: Sequence[Dict], rho: float = 0.02, iters: int = 40, lr: float = 0.05,
           keys: Sequence[str] = PERSONAL_KEYS, log: Callable = print, tag: str = "", fc_items: Optional[List[Dict]] = None,
           lam_fc: float = 0.0, fc_chunk: int = 10) -> List[Dict]:
    """Per-calibration parameters by Adam on the calibration fit (all calibrations in one batch, each with its own
    theta).  starts: numba parameter dicts (the 12-candidate choice per calibration).  With fc_items and lam_fc > 0,
    every writer's set also runs on those tremor-free recordings (fc_chunk writers at a time, to bound memory) and
    lam_fc * mean RMS estimate / 100 um is added to its loss.  Returns per calibration the refined numba dict, the
    fit before/after and the history."""
    G = len(calibs)
    static = TA.static_of(starts[0])
    if any(TA.static_of(s)["harm"] != static["harm"] for s in starts):
        raise ValueError("mixed harmonic structure")
    sch = [SCH.build(c.st) for c in calibs]
    K = max(s.K for s in sch)
    if any(s.K != K for s in sch):
        raise ValueError("calibration recordings of different length")
    ev = DA.light_events(sch)
    pk = AD.Packed(sch)
    full = [TA.trainable_start(s) for s in starts]
    th0 = torch.stack([TA.to_theta(v) for v in full])                          # (G, 23)
    TR.project(th0)
    sel = torch.tensor([TA.TRAIN_KEYS.index(k) for k in keys])
    z = th0[:, sel].clone().requires_grad_(True)
    opt = torch.optim.Adam([z], lr=lr)
    use_fc = bool(fc_items) and lam_fc > 0
    fc_sets = {}
    if use_fc:
        nfc = len(fc_items)

        def fc_set(n):
            # the same tremor-free recordings once per writer of a chunk of n writers
            if n not in fc_sets:
                fc_sets[n] = DA.build_set([it for _ in range(n) for it in fc_items])
            return fc_sets[n]
    hist = []
    t0 = time.time()
    best = [None] * G
    for it in range(iters + 1):
        need_grad = it < iters
        opt.zero_grad()
        with torch.set_grad_enabled(need_grad):
            th = th0.clone()
            th[:, sel] = z
            vals = TA.from_theta(th)
            dh = AD.forward(pk, ev, vals, static, gate_beta=None)
            fits = torch.stack([c.fit(dh[g]) for g, c in enumerate(calibs)])
            prior = ((z - th0[:, sel]) ** 2).sum(1)
            L0 = fits ** 2 + rho * prior
        if need_grad:
            L0.sum().backward()
        L = L0.detach().clone()
        fc_g = None
        if use_fc:
            fc_g = torch.zeros(G, dtype=TA.DT)
            for c0 in range(0, G, fc_chunk):
                gs = torch.arange(c0, min(G, c0 + fc_chunk))
                n = len(gs)
                fcs = fc_set(n)
                with torch.set_grad_enabled(need_grad):
                    thc = th0[gs].clone()
                    thc[:, sel] = z[gs]
                    vc = TA.from_theta(thc)
                    vfc = {k: v.repeat_interleave(nfc) for k, v in vc.items()}
                    dfc = AD.forward(fcs.pk, fcs.ev, vfc, static, gate_beta=None)
                    mm = fcs.m[..., None]
                    fc_rec = torch.sqrt((dfc ** 2 * mm).sum((1, 2)) / fcs.m.sum(1).clamp(min=1.0) + 1e-30) * 1e6
                    fcc = fc_rec.view(n, nfc).mean(1)
                    term = lam_fc * fcc / 100.0
                if need_grad:
                    term.sum().backward()
                fc_g[gs] = fcc.detach()
            L = L + lam_fc * fc_g / 100.0
        fv = fits.detach().numpy()
        for g in range(G):
            if best[g] is None or L[g].item() < best[g]["L"]:
                best[g] = {"L": float(L[g].item()), "fit": float(fv[g]), "iter": it, "theta": th[g].detach().clone(),
                           "fc_um": None if fc_g is None else float(fc_g[g])}
        hist.append({"iter": it, "fit_mean": float(fv.mean()), "L_mean": float(L.mean()),
                     **({"fc_um_mean": float(fc_g.mean())} if fc_g is not None else {})})
        if it % 10 == 0:
            log(f"[personal{tag}] it {it}: fit mean {fv.mean():.4f} (min {fv.min():.3f}, max {fv.max():.3f}) "
                f"prior {float(prior.detach().mean()):.3f}" + (f" FC {float(fc_g.mean()):.1f} um" if fc_g is not None else "")
                + f" ({time.time() - t0:.0f} s)")
        if not need_grad:
            break
        with torch.no_grad():
            z.grad[~torch.isfinite(z.grad)] = 0.0
        opt.step()
        with torch.no_grad():
            th = th0.clone(); th[:, sel] = z
            TR.project(th)
            z.copy_(th[:, sel])
    out = []
    for g in range(G):
        vals = {k: float(v) for k, v in TA.from_theta(best[g]["theta"]).items()}
        p = TA.to_numba(vals, static)
        out.append({"params": p, "fit_start": float(hist[0]["fit_mean"]) if G == 1 else None,
                    "fit_best": best[g]["fit"], "best_iter": best[g]["iter"], "fc_um_best": best[g]["fc_um"]})
    return out, hist
