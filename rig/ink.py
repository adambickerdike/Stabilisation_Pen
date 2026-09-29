"""G1 ink analysis (EXP-T02): continuity of a scanned line against the force that wrote it,
and the minimum reliable ink force.

Definitions (bench_protocols.md AC-B01-07, EXP-Q02):
  * gap fraction = unfilled length / line length along the centreline, sampled every 20 um;
  * a force level writes "continuously" if the gap fraction is <= 1 %;
  * the minimum ink force is the lowest force with gap fraction <= 1 %, found here two ways:
    (a) windows along a force-ramp line (first window, going down in force, whose gap fraction
        exceeds 1 %), and (b) a logistic fit of gap presence per 0.5 mm segment against force,
        with a bootstrap over lines for the 95 % interval.

The scan must be registered to the page (fiducials) so that the line's written start and end
points are known in scan pixels; the force along the line comes from the R9 record through the
encoder distance s. The image analysis works on 8- or 16-bit grayscale arrays (ink dark).
"""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np
from scipy import ndimage, optimize


def line_samples(img: np.ndarray, p0, p1, px_um: float, step_um: float = 20.0, half_width_um: float = 400.0,
                 n_across: int = 41) -> Dict:
    """Sample a straight line from p0 to p1 (pixel coordinates (row, col)) every step_um, and
    across it over +-half_width_um. Returns s (um along the line) and the across-profile matrix."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    L_px = np.linalg.norm(p1 - p0)
    u = (p1 - p0) / L_px
    nrm = np.array([-u[1], u[0]])
    n_along = int(L_px * px_um / step_um) + 1
    s_px = np.linspace(0, L_px, n_along)
    a_px = np.linspace(-half_width_um / px_um, half_width_um / px_um, n_across)
    rr = p0[0] + s_px[:, None] * u[0] + a_px[None, :] * nrm[0]
    cc = p0[1] + s_px[:, None] * u[1] + a_px[None, :] * nrm[1]
    prof = ndimage.map_coordinates(np.asarray(img, float), [rr.ravel(), cc.ravel()], order=1, mode="nearest")
    return {"s_um": s_px * px_um, "across_um": a_px * px_um, "profile": prof.reshape(n_along, n_across)}


def ink_presence(profile: np.ndarray, background: float = None, frac: float = 0.35) -> Dict:
    """Ink present at a station if the darkest pixel across the line is darker than the paper
    background by more than `frac` of the line's typical contrast. Background and contrast are
    estimated from the profile itself (robust percentiles), so the rule adapts to paper and ink."""
    dark = profile.min(axis=1)
    bg = np.median(profile[:, [0, -1]]) if background is None else background
    typical = np.percentile(dark, 10)
    contrast = bg - typical
    thr = bg - frac * contrast
    present = dark < thr
    # width at half contrast (um) where ink is present, for line-width reporting
    return {"present": present, "dark": dark, "background": float(bg), "threshold": float(thr),
            "contrast": float(contrast)}


def gap_fraction(present: np.ndarray) -> float:
    return float(1.0 - np.mean(present))


def windows(s_um: np.ndarray, present: np.ndarray, force: np.ndarray, win_um: float = 5000.0,
            hop_um: float = 1000.0) -> Dict:
    """Sliding windows along the line: gap fraction and mean force per window."""
    starts = np.arange(s_um[0], s_um[-1] - win_um + 1e-9, hop_um)
    g, F, c = [], [], []
    for a in starts:
        m = (s_um >= a) & (s_um < a + win_um)
        g.append(1 - present[m].mean())
        F.append(force[m].mean())
        c.append(a + win_um / 2)
    return {"centre_um": np.array(c), "gap_fraction": np.array(g), "force": np.array(F)}


def threshold_from_windows(win: Dict, limit: float = 0.01) -> float:
    """Force of the continuity limit: going from high to low force, the first window whose gap
    fraction exceeds `limit`, interpolated with the previous window. NaN if never exceeded."""
    order = np.argsort(-win["force"])
    F = win["force"][order]
    g = win["gap_fraction"][order]
    for k in range(1, len(F)):
        if g[k] > limit >= g[k - 1]:
            return float(F[k - 1] + (limit - g[k - 1]) * (F[k] - F[k - 1]) / (g[k] - g[k - 1]))
    if g[0] > limit:
        return float(F[0])
    return float("nan")


def segment_gaps(s_um: np.ndarray, present: np.ndarray, force: np.ndarray, seg_um: float = 500.0):
    """Split the line into segments; a segment 'has a gap' if any station in it lacks ink."""
    edges = np.arange(s_um[0], s_um[-1] + seg_um, seg_um)
    idx = np.digitize(s_um, edges) - 1
    yes, F = [], []
    for k in range(len(edges) - 1):
        m = idx == k
        if m.sum() < 3:
            continue
        yes.append(float((~present[m]).any()))
        F.append(float(force[m].mean()))
    return np.array(F), np.array(yes)


def logistic_fit(F: np.ndarray, gap: np.ndarray) -> Dict:
    """P(gap in a segment) = 1 / (1 + exp((F - F50) / s)): maximum likelihood."""
    F = np.asarray(F, float)
    y = np.asarray(gap, float)

    def nll(p):
        F50, log_s = p
        z = np.clip((F - F50) / np.exp(log_s), -50, 50)
        pg = 1.0 / (1.0 + np.exp(z))
        pg = np.clip(pg, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(pg) + (1 - y) * np.log(1 - pg))

    F50_0 = F[np.argmin(np.abs(y - 0.5))] if np.any(y > 0) and np.any(y < 1) else np.median(F)
    r = optimize.minimize(nll, [F50_0, np.log(max(0.1 * np.std(F), 1e-3))], method="Nelder-Mead",
                          options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 2000})
    return {"F50": float(r.x[0]), "scale": float(np.exp(r.x[1])), "success": bool(r.success)}


def force_at_segment_gap_prob(fit: Dict, p: float) -> float:
    """Force at which a segment has a gap with probability p."""
    return fit["F50"] + fit["scale"] * np.log((1 - p) / p)


def analyse_line(img, p0, p1, px_um, force_of_s, step_um=20.0, win_um=5000.0, limit=0.01) -> Dict:
    """Full analysis of one scanned line. force_of_s: callable s_um -> force (N) from the R9 record."""
    ls = line_samples(img, p0, p1, px_um, step_um)
    pres = ink_presence(ls["profile"])
    F = np.asarray(force_of_s(ls["s_um"]), float)
    w = windows(ls["s_um"], pres["present"], F, win_um=win_um)
    Fseg, gseg = segment_gaps(ls["s_um"], pres["present"], F)
    return {"gap_fraction_total": gap_fraction(pres["present"]), "F_threshold_windows": threshold_from_windows(w, limit),
            "windows": w, "segments": (Fseg, gseg), "presence": pres, "s_um": ls["s_um"], "force": F}


def minimum_ink_force(lines: Sequence[Dict], limit: float = 0.01, seg_prob: float = 0.05, n_boot: int = 200,
                      seed: int = 0) -> Dict:
    """Combine repeat lines of one (refill, paper, tilt, speed) cell. Returns the window threshold
    (median over lines, bootstrap 95 % CI) and the logistic segment model pooled over lines."""
    thr = np.array([l["F_threshold_windows"] for l in lines], float)
    thr = thr[np.isfinite(thr)]
    rng = np.random.default_rng(seed)
    boots = [np.median(rng.choice(thr, len(thr))) for _ in range(n_boot)] if len(thr) else [np.nan]
    Fs = np.concatenate([l["segments"][0] for l in lines])
    gs = np.concatenate([l["segments"][1] for l in lines])
    fit = logistic_fit(Fs, gs)
    return {"F_min_windows_median": float(np.median(thr)) if len(thr) else float("nan"),
            "F_min_windows_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "n_lines": len(lines), "logistic": fit,
            "F_at_segment_gap_prob": float(force_at_segment_gap_prob(fit, seg_prob)), "segment_gap_prob": seg_prob}
