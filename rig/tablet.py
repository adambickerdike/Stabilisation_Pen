"""Recording pen and tablet protocol analysis (EXP-T06; supports EXP-H01 and EXP-V03).

The tablet protocol uses rig/tablet/tablet_recorder.html: a self-contained page that logs every
pointer sample the browser receives from a pen tablet (Pointer Events with coalesced events:
position, pressure, tilt, twist, time), with ink on paper clipped to an EMR tablet whose pen
writes real ink (Wacom Intuos Pro Paper Edition with the Finetip gel or Ballpoint pen, MFR
OPT-86). It needs no installation. Position accuracy is the tablet's (+-0.25 mm class for such
digitisers, LIT CON-101 Calcomp 9000 and MFR AMF-98 Wacom sensor boards +-0.4 mm); relative motion
over a tremor cycle is much finer (0.01 mm resolution). The browser's time stamps are the host's
event times, not the tablet's acquisition times (OnHW has the same limitation, review R15):
latency is not measured this way, and sample jitter is reported.

Nib tremor amplitude follows the excess-power method of human_study_plan.md section 3.6:
  Welch displacement PSD (4 s Hann, 50 % overlap) of pen-down segments per axis; S_ref the
  healthy group's median PSD; band = f_pk +- 1.5 Hz, f_pk = argmax S_p/S_ref in 3-12 Hz;
  A_rms = sqrt(int_band max(0, S_p - S_ref) df); A_pp = 2 sqrt(2) A_rms; the major axis uses the
  principal eigenvalue of the band-integrated 2x2 cross-spectral matrix.
The method must recover known injected amplitudes before use (method qualification); rig.selftest
does this on synthetic writing.
"""
from __future__ import annotations

import csv
from typing import Dict

import numpy as np
from scipy import signal as sps


def load_csv(path: str) -> Dict[str, np.ndarray]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(r for r in f if not r.startswith("#")))
    cols = {k: [] for k in rows[0].keys()} if rows else {}
    for r in rows:
        for k, v in r.items():
            cols[k].append(v)
    out = {}
    for k, v in cols.items():
        try:
            out[k] = np.array([float(x) for x in v])
        except ValueError:
            out[k] = np.array(v)
    return out


def fit_affine(px: np.ndarray, mm: np.ndarray) -> Dict:
    """Affine map from screen/tablet pixels to page millimetres using >= 3 tapped fiducials."""
    P = np.column_stack([np.asarray(px, float), np.ones(len(px))])
    X, *_ = np.linalg.lstsq(P, np.asarray(mm, float), rcond=None)
    res = np.asarray(mm, float) - P @ X
    return {"M": X.tolist(), "resid_rms_mm": float(np.sqrt(np.mean(np.sum(res ** 2, axis=1))))}


def to_mm(cal: Dict, px: np.ndarray) -> np.ndarray:
    P = np.column_stack([np.asarray(px, float), np.ones(len(px))])
    return P @ np.asarray(cal["M"])


def sampling_quality(t_s: np.ndarray) -> Dict:
    dt = np.diff(np.asarray(t_s, float))
    dt = dt[dt > 0]
    med = np.median(dt)
    return {"rate_hz": float(1 / med), "jitter_rms_ms": float(np.std(dt) * 1e3),
            "gaps_over_3x": int(np.sum(dt > 3 * med)), "dt_max_ms": float(dt.max() * 1e3)}


def resample(t_s, x, fs):
    t = np.asarray(t_s, float)
    tt = np.arange(t[0], t[-1], 1 / fs)
    return tt, np.column_stack([np.interp(tt, t, np.asarray(x)[:, k]) for k in range(np.asarray(x).shape[1])])


def _runs(mask: np.ndarray):
    m = np.asarray(mask, bool)
    k = 0
    while k < len(m):
        if m[k]:
            j = k
            while j < len(m) and m[j]:
                j += 1
            yield k, j
            k = j
        else:
            k += 1


def cross_spectra(xy: np.ndarray, fs: float, pen_down: np.ndarray, win_s: float = 4.0) -> Dict:
    """Welch auto- and cross-spectra over pen-down runs at least one window long
    (Hann, 50 % overlap), averaged with the number of windows as weight."""
    n = int(round(win_s * fs))
    Sxx = Syy = Sxy = 0.0
    nw = 0
    f = None
    for a, b in _runs(pen_down):
        if b - a < n:
            continue
        seg = xy[a:b] - xy[a:b].mean(axis=0)
        f, pxx = sps.welch(seg[:, 0], fs=fs, window="hann", nperseg=n, noverlap=n // 2, detrend="linear")
        _, pyy = sps.welch(seg[:, 1], fs=fs, window="hann", nperseg=n, noverlap=n // 2, detrend="linear")
        _, pxy = sps.csd(seg[:, 0], seg[:, 1], fs=fs, window="hann", nperseg=n, noverlap=n // 2, detrend="linear")
        w = 1 + (b - a - n) // (n // 2)
        Sxx, Syy, Sxy, nw = Sxx + w * pxx, Syy + w * pyy, Sxy + w * pxy, nw + w
    if nw == 0:
        raise ValueError(f"no pen-down run of at least {win_s} s")
    return {"f": f, "Sxx": Sxx / nw, "Syy": Syy / nw, "Sxy": Sxy / nw, "n_windows": nw}


def excess_power(xy_mm: np.ndarray, fs: float, pen_down: np.ndarray, S_ref: Dict = None, band=(3.0, 12.0),
                 half_bw: float = 1.5, win_s: float = 4.0) -> Dict:
    """Excess-power tremor amplitude (human_study_plan.md section 3.6). S_ref: dict with f, Sxx, Syy
    (the healthy reference, already scaled to the participant's letter height); None uses zero."""
    cs = cross_spectra(np.asarray(xy_mm, float), fs, pen_down, win_s)
    f = cs["f"]
    if S_ref is None:
        rx = ry = np.zeros_like(f)
    else:
        rx = np.interp(f, S_ref["f"], S_ref["Sxx"])
        ry = np.interp(f, S_ref["f"], S_ref["Syy"])
    m = (f >= band[0]) & (f <= band[1])
    ratio = (cs["Sxx"] + cs["Syy"]) / np.maximum(rx + ry, 1e-12 * np.max(cs["Sxx"] + cs["Syy"]))
    fpk = float(f[m][np.argmax(ratio[m])])
    mb = (f >= fpk - half_bw) & (f <= fpk + half_bw)
    df = f[1] - f[0]
    ex = np.maximum(0, cs["Sxx"] - rx)[mb].sum() * df
    ey = np.maximum(0, cs["Syy"] - ry)[mb].sum() * df
    # major axis: principal eigenvalue of the band-integrated excess cross-spectral matrix
    Cxx = ex
    Cyy = ey
    Cxy = np.real(cs["Sxy"][mb]).sum() * df
    lam = 0.5 * (Cxx + Cyy) + np.sqrt(0.25 * (Cxx - Cyy) ** 2 + Cxy ** 2)
    out = {"f_peak_hz": fpk, "n_windows": cs["n_windows"]}
    for name, v in (("x", ex), ("y", ey), ("major", lam)):
        a = float(np.sqrt(max(v, 0.0)))
        out[f"A_rms_{name}_mm"] = a
        out[f"A_pp_{name}_mm"] = float(2 * np.sqrt(2) * a)
    return out


def pressure_to_newton(p: np.ndarray, cal_levels: np.ndarray, cal_newton: np.ndarray) -> np.ndarray:
    """Monotone interpolation of the tablet's reported pressure (0-1) to newtons from a dead-weight
    calibration of the pen on the tablet (or against the R9 plate)."""
    order = np.argsort(cal_levels)
    return np.interp(np.asarray(p, float), np.asarray(cal_levels)[order], np.asarray(cal_newton)[order])


# ------------------------------------------------------------------------------------------ recorder files
def load_recording(path: str) -> Dict:
    """Read a CSV written by rig/tablet/tablet_recorder.html (format rig-tablet-1): metadata ('# key=value'),
    pen samples, and the four fiducial taps. Positions are mapped to page millimetres with the affine fit of
    the tapped fiducials (fit_affine) when all four are present; otherwise they stay in CSS pixels."""
    meta = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") and "=" in line:
                k, v = line[1:].strip().split("=", 1)
                meta[k.strip()] = v.strip()
    cols = load_csv(path)
    pen = np.asarray(cols.get("pointer_type", np.array([])) == "pen") if "pointer_type" in cols else None
    keep = pen if pen is not None and pen.any() else np.ones(len(cols["t_ms"]), bool)
    t = cols["t_ms"][keep] / 1e3
    order = np.argsort(t, kind="stable")
    px = np.column_stack([cols["x_px"][keep], cols["y_px"][keep]])[order]
    out = {"meta": meta, "t_s": t[order], "px": px, "pen_down": cols["pen_down"][keep][order] > 0.5,
           "pressure": cols["pressure"][keep][order], "stroke": cols["stroke"][keep][order].astype(int),
           "coalesced": cols["coalesced"][keep][order] > 0.5}
    for k in ("tilt_x_deg", "tilt_y_deg", "twist_deg"):
        if k in cols:
            out[k] = cols[k][keep][order]

    def pairs(s):
        pts = [p.split() for p in s.split(";") if p.strip()]
        return np.array([[float(a), float(b)] for a, b in pts]) if pts else np.zeros((0, 2))

    fmm, fpx = pairs(meta.get("fiducials_mm", "")), pairs(meta.get("fiducials_px", ""))
    out["fiducials_mm"], out["fiducials_px"] = fmm, fpx
    if len(fmm) >= 3 and len(fpx) == len(fmm):
        cal = fit_affine(fpx, fmm)
        out["cal"] = cal
        out["xy_mm"] = to_mm(cal, px)
        out["units"] = "mm"
    else:
        out["xy_mm"] = px.astype(float)
        out["units"] = "px"
    return out


def analyse_recording(rec: Dict, fs: float = 200.0, S_ref: Dict = None, win_s: float = 4.0) -> Dict:
    """Sampling quality, then the excess-power tremor estimate on pen-down runs of >= win_s seconds
    (human_study_plan.md section 3.6). Raises ValueError when no run is long enough (sentence copying:
    see the open issue on a pooled-run variant in docs/measurement_rig.md)."""
    t = rec["t_s"]
    u, idx = np.unique(t, return_index=True)            # drop duplicate time stamps (coalesced copies)
    xy = rec["xy_mm"][idx]
    down = rec["pen_down"][idx]
    q = sampling_quality(u)
    tt, xyr = resample(u, xy, fs)
    k = np.clip(np.searchsorted(u, tt), 0, len(u) - 1)
    down_r = down[k]
    out = {"sampling": q, "units": rec.get("units", "?"), "duration_s": float(u[-1] - u[0]),
           "pen_down_s": float(down_r.sum() / fs)}
    if "cal" in rec:
        out["fiducial_fit_rms_mm"] = rec["cal"]["resid_rms_mm"]
    out["tremor"] = excess_power(xyr, fs, down_r, S_ref=S_ref, win_s=win_s)
    return out


def write_recording_csv(path: str, t_s, px, pen_down, pressure=None, fiducials_mm=None, fiducials_px=None, meta=None):
    """Write a file in the recorder's format (used by the tests and to convert other tablet logs)."""
    cols = ["t_ms", "type", "pointer_id", "pointer_type", "x_px", "y_px", "screen_x", "screen_y", "pressure",
            "tilt_x_deg", "tilt_y_deg", "twist_deg", "altitude_rad", "azimuth_rad", "width_px", "height_px",
            "buttons", "coalesced", "stroke", "pen_down"]
    t_s, px, pen_down = np.asarray(t_s, float), np.asarray(px, float), np.asarray(pen_down, bool)
    pressure = np.where(pen_down, 0.5, 0.0) if pressure is None else np.asarray(pressure, float)
    stroke = np.cumsum(np.concatenate([[pen_down[0]], pen_down[1:] & ~pen_down[:-1]])).astype(int)
    m = {"format": "rig-tablet-1", "participant": "SYNTH", "session": "1", "task": "el-loops"}
    m.update(meta or {})
    if fiducials_mm is not None:
        m["fiducials_mm"] = ";".join(f"{a} {b}" for a, b in fiducials_mm)
        m["fiducials_px"] = ";".join(f"{a} {b}" for a, b in fiducials_px)
    with open(path, "w", encoding="utf-8", newline="") as f:
        for k, v in m.items():
            f.write(f"# {k}={v}\n")
        f.write(",".join(cols) + "\n")
        for i in range(len(t_s)):
            typ = "move"
            row = [f"{t_s[i] * 1e3:.3f}", typ, "1", "pen", f"{px[i, 0]:.4f}", f"{px[i, 1]:.4f}", "", "",
                   f"{pressure[i]:.5f}", "20", "-10", "0", "", "", "1", "1", "1" if pen_down[i] else "0", "0",
                   str(stroke[i]), "1" if pen_down[i] else "0"]
            f.write(",".join(row) + "\n")
