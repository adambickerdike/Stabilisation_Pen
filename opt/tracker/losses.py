r"""Intent-aligned loss of the tremor tracker (SIMULATION tooling).

For every recording (5 s P1 run pair, sensor streams from fusion.sensors):
  tremor-band residual  RR_band = || BP(d - clip(d_hat)) ||_m / || BP(d) ||_m          (tremor recordings)
      d: the true housing disturbance at the ticks (p_H with tremor - p_H of the same writing without tremor,
      fusion.sensors.truth_at), BP: 4th-order Butterworth band-pass 3-15 Hz applied forwards and backwards
      (zero phase, as the harness's sosfiltfilt; here by FFT after an odd extension of 0.5 s), clip: the estimate
      limited to the 0.30 mm correction radius (fusion.tune.CLIP), m: nib in contact and t > 0.5 s.
      This is fusion.harness.signal_metrics' residual_ratio_band (up to the edge handling of the filter).
  false correction      FC = RMS_m(d_hat) in um                                          (tremor-free recordings)
      weighted w_glyph : 1 between the sharp glyph writers and the sigma-lognormal writers.
  jitter                HF = RMS_m(HP_150(clip(d_hat))) in um, causal 4th-order Butterworth high-pass from rest (as
      fusion.tune._hf_rms; all recordings): estimate content near the 192 Hz stage resonance
      (docs/sensor_fusion_ai.md s3.3).  (A zero-phase version on the zero-padded record was tried first: the jump at
      the end of each record leaked into it and made it ~10x too large.)
  J = RR_band,agg + lambda_fc mean_w(FC) / FC_REF + mu_hf mean(HF),
      RR_band,agg = sqrt(sum_rec ||BP(d - clip(d_hat))||^2 / sum_rec ||BP(d)||^2) over the tremor recordings
      (energy-weighted: the training tremor is log-uniform 0.05-0.6 mm, and with the mean of per-recording ratios the
      many small tremors, where no tracker can help much, made the "benefit" term mostly a false-correction term:
      the optimum was conservative for every lambda_fc, see opt/tracker/build/logs/sweep_A_per_recording_ratio.log;
      rr_mode="mean" keeps that variant)
with FC_REF = 100 um and mu_hf per um (defaults: 0.02 / um, the fusion.tune weighting of 8 x HF / RMS(d) for
RMS(d) ~ 400 um).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import torch
from scipy.signal import butter, sosfreqz

DT = torch.float64
CLIP = 0.30e-3
FC_REF_UM = 100.0
BAND = (3.0, 15.0)

_H: Dict = {}


PAD = 1000          # odd-extension padding of the zero-phase band-pass (0.5 s at 2 kHz), as filtfilt's padtype="odd"


def _nfft(K: int) -> int:
    from scipy.fft import next_fast_len
    return int(next_fast_len(2 * K, real=True))


def _resp(kind: str, n: int, fs: float) -> torch.Tensor:
    """Frequency response at the rfft bins of length n: "band" |H|^2 (forward-backward, zero phase) of the 4th-order
    Butterworth 3-15 Hz band-pass; "hp150" the complex response of the causal 4th-order Butterworth 150 Hz
    high-pass (with n >= 2K the product is a linear, causal convolution: exactly sosfilt from rest, as
    fusion.tune._hf_rms)."""
    key = (kind, n, fs)
    if key not in _H:
        f = np.fft.rfftfreq(n, 1.0 / fs)
        if kind == "band":
            sos = butter(4, BAND, btype="band", fs=fs, output="sos")
            _H[key] = torch.as_tensor(np.abs(sosfreqz(sos, worN=f, fs=fs)[1]) ** 2, dtype=DT)
        elif kind == "hp150":
            sos = butter(4, 150.0, btype="high", fs=fs, output="sos")
            _H[key] = torch.as_tensor(sosfreqz(sos, worN=f, fs=fs)[1], dtype=torch.complex128)
        else:
            raise KeyError(kind)
    return _H[key]


def odd_ext(x: torch.Tensor, L: int) -> torch.Tensor:
    """Odd extension by L samples at both ends along dim 1 (scipy.signal's padtype="odd")."""
    K = x.shape[1]
    L = min(L, K - 1)
    left = 2 * x[:, :1] - torch.flip(x[:, 1:L + 1], [1])
    right = 2 * x[:, -1:] - torch.flip(x[:, K - L - 1:K - 1], [1])
    return torch.cat([left, x, right], 1), L


def zero_phase(x: torch.Tensor, kind: str, fs: float) -> torch.Tensor:
    """x (B, K, C) -> zero-phase 3-15 Hz band-pass along K (odd extension, FFT, |H|^2)."""
    if kind != "band":
        raise KeyError(kind)
    K = x.shape[1]
    xe, L = odd_ext(x, PAD)
    n = _nfft(xe.shape[1])
    X = torch.fft.rfft(xe, n=n, dim=1)
    return torch.fft.irfft(X * _resp("band", n, fs)[None, :, None], n=n, dim=1)[:, L:L + K]


def causal_hp150(x: torch.Tensor, fs: float) -> torch.Tensor:
    """x (B, K, C) -> causal 4th-order Butterworth 150 Hz high-pass from rest (as scipy sosfilt)."""
    K = x.shape[1]
    n = _nfft(K)
    X = torch.fft.rfft(x, n=n, dim=1)
    return torch.fft.irfft(X * _resp("hp150", n, fs)[None, :, None], n=n, dim=1)[:, :K]


def clip(dh: torch.Tensor, lim: float = CLIP) -> torch.Tensor:
    r = torch.sqrt((dh ** 2).sum(-1, keepdim=True) + 1e-30)
    return dh * torch.clamp(lim / r, max=1.0)


@dataclass
class LossCfg:
    lam_fc: float = 0.2
    mu_hf: float = 0.02              # per um of RMS above 150 Hz
    w_glyph_fc: float = 3.0          # weight of glyph writers in the false-correction mean (sigma-lognormal: 1)
    w_glyph_rr: float = 1.0
    fs: float = 2000.0
    rr_mode: str = "aggregate"       # "aggregate" (energy-weighted over recordings) or "mean" (mean of per-recording ratios)


def terms(dh: torch.Tensor, d: torch.Tensor, db: torch.Tensor, m: torch.Tensor, clean: torch.Tensor, fs: float = 2000.0):
    """Per-recording terms.  dh, d, db (B, K, 2) (db = BP(d) precomputed); m (B, K) float; clean (B,) bool."""
    mm = m[..., None]
    n = m.sum(1).clamp(min=1.0)
    dc = clip(dh)
    e = db - zero_phase(dc, "band", fs)
    num = (e ** 2 * mm).sum((1, 2))
    den = (db ** 2 * mm).sum((1, 2)).clamp(min=1e-30)
    rr = torch.sqrt(num / den + 1e-30)
    fc = torch.sqrt((dh ** 2 * mm).sum((1, 2)) / n + 1e-30) * 1e6
    hp = causal_hp150(dc, fs)
    hf = torch.sqrt((hp ** 2 * mm).sum((1, 2)) / n + 1e-30) * 1e6
    return {"rr": torch.where(clean, torch.full_like(rr, float("nan")), rr), "fc": fc, "hf": hf, "num": num, "den": den}


def objective(t: Dict[str, torch.Tensor], clean: torch.Tensor, glyph: torch.Tensor, cfg: LossCfg):
    tr = ~clean
    wr = torch.where(glyph[tr], torch.full_like(t["fc"][tr], cfg.w_glyph_rr), torch.ones_like(t["fc"][tr]))
    if cfg.rr_mode == "aggregate" and "num" in t:
        # residual energy over band energy summed over the recordings: large tremors, where the benefit is, dominate;
        # harm on small tremor and tremor-free writing is the false-correction term's job
        rr = torch.sqrt((t["num"][tr] * wr).sum() / (t["den"][tr] * wr).sum().clamp(min=1e-30))
    else:
        rr = (t["rr"][tr] * wr).sum() / wr.sum()
    J = rr
    fcm = torch.zeros((), dtype=DT)
    if bool(clean.any()):
        wf = torch.where(glyph[clean], torch.full_like(t["fc"][clean], cfg.w_glyph_fc), torch.ones_like(t["fc"][clean]))
        fcm = (t["fc"][clean] * wf).sum() / wf.sum()
        J = J + cfg.lam_fc * fcm / FC_REF_UM
    hfm = t["hf"].mean()
    J = J + cfg.mu_hf * hfm
    return J, {"J": float(J.detach()), "rr_band": float(rr.detach()), "fc_w_um": float(fcm.detach()),
               "hf_um": float(hfm.detach())}


def summary(t: Dict[str, torch.Tensor], clean: torch.Tensor, glyph: torch.Tensor) -> Dict[str, float]:
    """Plain means by writer type (for reports)."""
    out = {}
    c = clean.numpy(); g = glyph.numpy()
    rr = t["rr"].detach().numpy(); fc = t["fc"].detach().numpy(); hf = t["hf"].detach().numpy()
    for lab, sel in (("all", np.ones_like(c)), ("lognormal", ~g), ("glyph", g)):
        tr = sel & ~c
        cl = sel & c
        if tr.any():
            out[f"rr_band_{lab}"] = float(np.mean(rr[tr]))
            out[f"hf_um_{lab}"] = float(np.mean(hf[tr]))
        if cl.any():
            out[f"fc_um_{lab}"] = float(np.mean(fc[cl]))
    return out
