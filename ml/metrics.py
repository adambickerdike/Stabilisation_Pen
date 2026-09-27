r"""Metrics for the causal disturbance predictor (definitions used everywhere).

Scored ticks: t_k >= WARMUP_S and pen down at the target time t_k + h
(correction acts only in contact).
Residual ratio per band b (pooled over the writers of a set):
    RR_b(g) = sqrt( sum |d - g d_hat|^2 / sum |d|^2 )   over tremor ticks (envelope > 0)
    of band b, d = true disturbance at t_k + h, g = output gain.  RR = 1: no benefit.
False correction:  FC(g) = g * RMS(|d_hat|) over no-tremor ticks (envelope = 0), um.
Both only need the per-writer sums S_dd, S_dy, S_yy (per band) and S_nt, n_nt,
so gain sweeps and writer bootstraps are exact and cheap.
Matched false correction: for a target F, the gain is chosen on the VALIDATION
writers as g = min(g_opt, F / FC_val(1), G_MAX), g_opt = S_dy / S_yy (pooled over
all bands), i.e. the best all-band residual subject to FC_val <= F; it is then
frozen and applied to the test writers.
Evidence status: SIMULATION / synthetic data.
"""
from __future__ import annotations

import numpy as np

from . import common as C

NB = len(C.BANDS)


def score_mask(rec):
    return (rec["t"] >= C.WARMUP_S) & rec["pen_tgt"]


def rec_stats(rec, dhat):
    m = score_mask(rec)
    d = np.asarray(rec["d_tgt_um"], np.float64)
    y = np.asarray(dhat, np.float64)
    env = rec["env_tgt"]
    tr = m & (env > 0)
    nt = m & (env == 0)
    b = C.band_index(rec["f0_tgt"])
    out = {k: np.zeros(NB) for k in ("Sdd", "Sdy", "Syy", "n")}
    for i in range(NB):
        mm = tr & (b == i)
        if mm.any():
            dd, yy = d[mm], y[mm]
            out["Sdd"][i] = np.sum(dd * dd)
            out["Sdy"][i] = np.sum(dd * yy)
            out["Syy"][i] = np.sum(yy * yy)
            out["n"][i] = mm.sum()
    out["Snt"] = float(np.sum(y[nt] ** 2))
    out["nnt"] = float(nt.sum())
    out["finite"] = bool(np.all(np.isfinite(y[m])))
    return out


def stack(stats_list):
    return {k: np.array([s[k] for s in stats_list]) for k in ("Sdd", "Sdy", "Syy", "n", "Snt", "nnt")}


def _rr(Sdd, Sdy, Syy, g):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.sqrt(np.maximum(Sdd - 2 * g * Sdy + g * g * Syy, 0.0) / Sdd)


def pooled(st, g=1.0, idx=None):
    """Pooled metrics of a stacked stats dict (optionally a writer subset)."""
    sel = slice(None) if idx is None else idx
    Sdd, Sdy, Syy, n = (st[k][sel].sum(0) for k in ("Sdd", "Sdy", "Syy", "n"))
    Snt, nnt = st["Snt"][sel].sum(), st["nnt"][sel].sum()
    fc = g * np.sqrt(Snt / nnt) if nnt > 0 else float("nan")
    return {"rr_band": _rr(Sdd, Sdy, Syy, g), "rr_all": float(_rr(Sdd.sum(), Sdy.sum(), Syy.sum(), g)),
            "fc_um": float(fc), "n_band": n, "n_nt": float(nnt),
            "d_rms_band_um": np.sqrt(np.where(n > 0, Sdd / np.maximum(n, 1), np.nan))}


def select_gain(st, fc_target):
    Sdy, Syy = st["Sdy"].sum(), st["Syy"].sum()
    g_opt = float(np.clip(Sdy / Syy, 0.0, C.G_MAX)) if Syy > 0 else 0.0
    nnt = st["nnt"].sum()
    fc1 = float(np.sqrt(st["Snt"].sum() / nnt)) if nnt > 0 else 0.0
    g_fc = fc_target / fc1 if fc1 > 0 else np.inf
    return float(min(g_opt, g_fc, C.G_MAX)), {"g_opt": g_opt, "fc_at_unit_gain_um": fc1}


def matched_rr_all(st, fc_target):
    """Selection criterion (validation): all-band RR at the gain chosen for fc_target."""
    g, _ = select_gain(st, fc_target)
    return pooled(st, g)["rr_all"], g


def sweep(st, gains=None):
    gains = np.linspace(0.0, C.G_MAX, 81) if gains is None else np.asarray(gains)
    rows = [pooled(st, g) for g in gains]
    return {"gain": gains.tolist(), "fc_um": [r["fc_um"] for r in rows], "rr_all": [r["rr_all"] for r in rows],
            "rr_band": [[float(x) for x in r["rr_band"]] for r in rows]}


def _counts(nw, B, seed):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nw, size=(B, nw))
    cnt = np.zeros((B, nw))
    np.add.at(cnt, (np.repeat(np.arange(B), nw), idx.ravel()), 1.0)
    return cnt


def bootstrap(st_by_method, gains, B=2000, seed=12345, paired=None):
    """Writer bootstrap (resample writers with replacement, recompute pooled metrics
    with the frozen gains).  Returns per-method 95 % percentile CIs of RR per band,
    all-band RR and FC, plus paired differences RR[a] - RR[b] for (a, b) in paired.
    The gain-selection uncertainty (validation) is not included."""
    names = list(st_by_method)
    nw = st_by_method[names[0]]["Sdd"].shape[0]
    cnt = _counts(nw, B, seed)
    draws = {}
    for m in names:
        st, g = st_by_method[m], gains[m]
        Sdd, Sdy, Syy = cnt @ st["Sdd"], cnt @ st["Sdy"], cnt @ st["Syy"]
        rr_b = _rr(Sdd, Sdy, Syy, g)
        rr_a = _rr(Sdd.sum(1), Sdy.sum(1), Syy.sum(1), g)
        nnt = cnt @ st["nnt"]
        with np.errstate(invalid="ignore", divide="ignore"):
            fc = g * np.sqrt((cnt @ st["Snt"]) / nnt)
        draws[m] = (rr_b, rr_a, fc)

    def ci(x):
        x = x[np.isfinite(x)]
        return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))] if len(x) else [float("nan")] * 2

    out = {}
    for m in names:
        rr_b, rr_a, fc = draws[m]
        out[m] = {"rr_band_ci95": [ci(rr_b[:, i]) for i in range(NB)], "rr_all_ci95": ci(rr_a), "fc_ci95": ci(fc)}
    diffs = {}
    for a, b in (paired or []):
        da = draws[a][0] - draws[b][0]
        dall = draws[a][1] - draws[b][1]
        diffs[f"{a}-{b}"] = {"band_mean": [float(np.nanmean(da[:, i])) for i in range(NB)],
                             "band_ci95": [ci(da[:, i]) for i in range(NB)],
                             "band_p_a_better": [float(np.mean(da[:, i][np.isfinite(da[:, i])] < 0))
                                                 if np.isfinite(da[:, i]).any() else float("nan") for i in range(NB)],
                             "all_mean": float(np.nanmean(dall)), "all_ci95": ci(dall)}
    return out, diffs
