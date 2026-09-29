r"""Recorded Parkinson's data used for the tremor targets (task 1) and as a recorded tremor waveform (REAL DATA, CALC).

Data (read-only; not in the repository; paths from wholepen.SCRATCH or the environment variable WHOLEPEN_DATA):
  UCI 'Parkinson Disease Spiral Drawings Using Digitized Graphics Tablet' (LIT PDT-30, CC BY 4.0): 25 PD and 15
      control files in the public archive (the page lists 62 PD), static and dynamic spiral tests, pen x/y on a Wacom
      Cintiq 12WX at 7-9 ms steps.  ASSUMPTION: x/y are screen pixels of 0.204 mm (MFR AMF-180, the display's pixel
      pitch; spirals then span about 70 mm).
  NewHandPD signals (LIT PDT-67; lead's copy PatientSignal.zip, this study's download HealthySignal.zip): a BiSP
      smart pen at 1 kHz, 6 channels: 1 microphone, 2 finger grip, 3 axial refill pressure, 4-6 tilt and acceleration
      in x, y, z (uncalibrated volts; channel order LIT PDT-67); 31 patient and 35 healthy subject folders; tasks:
      4 spirals, 4 meanders, circles, diadochokinesis.  Some patient folders repeat a person (same ID; one pair of
      byte-identical files): persons are counted once.
      ASSUMPTION (calibration): the slowly varying part of channels 4-6 during the diadochokinesis tasks spans at most
      2 g (the pen turned through +-90 degrees), so each subject's sensitivity is at least range / 2 g; acceleration
      amplitudes are therefore upper bounds, and displacement = acceleration / (2 pi f)^2 at the pen's sensor, not at
      the tip.
Analyses:
  uci()        per file: tremor-band (3-12 Hz) displacement of the pen tip, peak frequency, spectral peak ratio
  newhandpd()  per person: the most prominent narrow spectral line at 3.5-12 Hz of the pen's acceleration during
               spirals, meanders and the paper circle (line power / median power 1-3 Hz either side); a person 'shows a
               tremor line while drawing' when the prominence exceeds the healthy group's 95th percentile
  pd_waveform  the recorded tremor of the patient with the most prominent line (a 2-D displacement-shaped waveform
               normalised to unit mean envelope), used as the 'PD recorded' simulator input
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import re
import zipfile
from typing import Dict, List, Optional

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt, welch

from . import BUILD, SCRATCH

G0 = 9.80665
PX_MM = 0.204            # MFR AMF-180 (Cintiq 12WX pixel pitch); ASSUMPTION that UCI x/y are pixels


def _nh_dir() -> str:
    d = os.path.join(BUILD, "newhandpd")
    if not os.path.isdir(os.path.join(d, "patients")):
        os.makedirs(d, exist_ok=True)
        for zname, sub in (("PatientSignal.zip", "patients"), ("HealthySignal.zip", "healthy")):
            zp = os.path.join(SCRATCH, zname)
            if not os.path.exists(zp):
                raise FileNotFoundError(zp)
            with zipfile.ZipFile(zp) as z:
                os.makedirs(os.path.join(d, sub), exist_ok=True)
                for nm in z.namelist():
                    if nm.endswith(".txt") and "__MACOSX" not in nm:
                        open(os.path.join(d, sub, os.path.basename(nm)), "wb").write(z.read(nm))
    return d


def _uci_dir() -> str:
    d = os.path.join(BUILD, "uci395")
    if not os.path.isdir(os.path.join(d, "hw_dataset")):
        os.makedirs(d, exist_ok=True)
        zp = os.path.join(SCRATCH, "W", "uci", "uci395.zip")
        if not os.path.exists(zp):
            raise FileNotFoundError(zp)
        with zipfile.ZipFile(zp) as z:
            z.extractall(d)
    return d


def load_nh(path: str):
    meta, rows = {}, []
    for line in open(path, errors="ignore"):
        if line.startswith("#"):
            m = re.match(r"#<(\w+)>(.*)</\w+>", line.strip())
            if m:
                meta[m.group(1)] = m.group(2)
            continue
        p = line.split()
        if len(p) == 6:
            rows.append([float(v) for v in p])
    return meta, np.array(rows)


# ------------------------------------------------------------------------------------------------ UCI
def uci() -> Dict:
    d = os.path.join(_uci_dir(), "hw_dataset")
    out = {}
    for grp in ("parkinson", "control"):
        rows = []
        for f in sorted(glob.glob(os.path.join(d, grp, "*.txt"))):
            a = np.loadtxt(f, delimiter=";")
            for tid in (0, 1):
                s = a[a[:, 6] == tid]
                if len(s) < 200:
                    continue
                t = (s[:, 5] - s[0, 5]) / 1000.0
                ok = np.r_[True, np.diff(t) > 0]
                s, t = s[ok], t[ok]
                fs = 100.0
                tu = np.arange(t[0], t[-1], 1 / fs)
                x = np.interp(tu, t, s[:, 0]) * PX_MM
                y = np.interp(tu, t, s[:, 1]) * PX_MM
                sos = butter(4, [3.0, 12.0], btype="band", fs=fs, output="sos")
                xb, yb = sosfiltfilt(sos, x), sosfiltfilt(sos, y)
                f_, Px = welch(xb, fs, nperseg=min(512, len(xb)))
                _, Py = welch(yb, fs, nperseg=min(512, len(xb)))
                P = Px + Py
                band = (f_ >= 3) & (f_ <= 12)
                ev = np.linalg.eigvalsh(np.cov(np.vstack([xb, yb])))
                rows.append({"file": os.path.basename(f), "test": tid, "dur_s": float(t[-1]), "f_peak": float(f_[band][np.argmax(P[band])]),
                             "peak_ratio": float(P[band].max() / np.median(P[band])), "amp_pk_mm": float(np.sqrt(2 * ev[-1]))})
        A = np.array([r["amp_pk_mm"] for r in rows])
        out[grp] = {"n_files": len({r["file"] for r in rows}), "n_tests": len(rows),
                    "amp_pk_mm_median": float(np.median(A)), "amp_pk_mm_p90": float(np.percentile(A, 90)),
                    "amp_pk_mm_max": float(A.max()), "f_peak_median": float(np.median([r["f_peak"] for r in rows])),
                    "rows": rows}
    thr = np.percentile([r["peak_ratio"] for r in out["control"]["rows"]], 95)
    pd_rows = out["parkinson"]["rows"]
    files = sorted({r["file"] for r in pd_rows})
    shown = [f for f in files if max(r["peak_ratio"] for r in pd_rows if r["file"] == f) > thr]
    out["line_threshold_control_p95"] = float(thr)
    out["pd_files_above"] = shown
    out["pd_share_above"] = len(shown) / max(len(files), 1)
    out["label"] = ("REAL DATA (LIT PDT-30), CALC: tremor-band displacement at the pen tip on the tablet; pixel pitch "
                    "0.204 mm ASSUMPTION (MFR AMF-180); the 3-12 Hz band also holds the drawing's own fast content, so "
                    "controls set the floor")
    return out


# ------------------------------------------------------------------------------------------------ NewHandPD
def _persons(grp_dir: str) -> Dict[str, List[str]]:
    """subject folder ids per person id (the same person may appear under several subject numbers)."""
    subj = sorted(set(re.findall(r"-([PH]\d+)\.txt", " ".join(glob.glob(os.path.join(grp_dir, "*.txt"))))),
                  key=lambda s: int(s[1:]))
    per = {}
    for s in subj:
        f = glob.glob(os.path.join(grp_dir, f"sigSp1-{s}.txt")) or glob.glob(os.path.join(grp_dir, f"*-{s}.txt"))
        meta, _ = load_nh(f[0])
        per.setdefault(meta.get("Person_ID_Number", s), []).append(s)
    return per


def _sensitivity(grp_dir: str, s: str) -> float:
    rng = 0.0
    for task in ("sigDiaA", "sigDiaB"):
        fl = glob.glob(os.path.join(grp_dir, f"{task}-{s}.txt"))
        if not fl:
            continue
        _, a = load_nh(fl[0])
        if len(a) < 2000:
            continue
        lp = sosfiltfilt(butter(2, 2.0, fs=1000.0, output="sos"), a[:, 3:6], axis=0)
        rng = max(rng, float((lp.max(0) - lp.min(0)).max()))
    return rng / 2.0 if rng > 0 else float("nan")


def _best_line(grp_dir: str, s: str) -> Dict:
    best = None
    for task in ("sigSp1", "sigSp2", "sigSp3", "sigSp4", "sigMea1", "sigMea2", "sigMea3", "sigMea4", "circA"):
        fl = glob.glob(os.path.join(grp_dir, f"{task}-{s}.txt"))
        if not fl:
            continue
        meta, a = load_nh(fl[0])
        if len(a) < 4000:
            continue
        acc = a[:, 3:6] - a[:, 3:6].mean(0)
        acc = sosfiltfilt(butter(2, 1.0, btype="high", fs=1000.0, output="sos"), acc, axis=0)
        f_, P = welch(acc, 1000.0, nperseg=2048, noverlap=1536, axis=0)
        Pt = P.sum(1)
        for k in np.flatnonzero((f_ >= 3.5) & (f_ <= 12.0)):
            nb = (np.abs(f_ - f_[k]) <= 3.0) & (np.abs(f_ - f_[k]) >= 1.0)
            prom = float(Pt[k] / np.median(Pt[nb]))
            if best is None or prom > best["prominence"]:
                best = {"task": task, "f_Hz": float(f_[k]), "prominence": prom, "age": meta.get("Age")}
    return best


def newhandpd() -> Dict:
    root = _nh_dir()
    out = {}
    for grp, sub in (("patients", "patients"), ("healthy", "healthy")):
        gd = os.path.join(root, sub)
        per = _persons(gd)
        rows = []
        for pid, subs in per.items():
            lines = [(_best_line(gd, s), s) for s in subs]
            lines = [(b, s) for b, s in lines if b is not None]
            if not lines:
                continue
            b, s = max(lines, key=lambda x: x[0]["prominence"])
            S = _sensitivity(gd, s)
            b = dict(b, subject=s, n_folders=len(subs), S_V_per_g=S)
            if np.isfinite(S) and S > 0:
                _, a = load_nh(os.path.join(gd, f"{b['task']}-{s}.txt"))
                f0 = b["f_Hz"]
                nb = sosfiltfilt(butter(2, [max(f0 - 0.6, 1.0), f0 + 0.6], btype="band", fs=1000.0, output="sos"),
                                 a[:, 3:6], axis=0)
                ev = np.linalg.eigvalsh(np.cov(nb.T))
                a_pk = math.sqrt(2 * ev[-1]) / S * G0
                env = np.abs(hilbert(nb, axis=0)).max(1) / S * G0 / (2 * math.pi * f0) ** 2 * 1e3
                b.update(acc_pk_m_s2=a_pk, disp_pk_mm_at_sensor=a_pk / (2 * math.pi * f0) ** 2 * 1e3,
                         disp_env_p90_mm=float(np.percentile(env, 90)), disp_env_max_mm=float(env.max()))
            rows.append(b)
        out[grp] = {"n_persons": len(rows), "n_folders": sum(len(v) for v in per.values()), "rows": rows}
    thr = float(np.percentile([r["prominence"] for r in out["healthy"]["rows"]], 95))
    above = [r for r in out["patients"]["rows"] if r["prominence"] > thr]
    out["threshold_healthy_p95"] = thr
    out["patients_above"] = len(above)
    out["patients_share_above"] = len(above) / max(out["patients"]["n_persons"], 1)
    out["healthy_share_above"] = float(np.mean([r["prominence"] > thr for r in out["healthy"]["rows"]]))
    out["above_rows"] = above
    out["ages_median"] = {g: float(np.median([float(r["age"]) for r in out[g]["rows"] if r.get("age")])) for g in ("patients", "healthy")}
    out["label"] = ("REAL DATA (LIT PDT-67), CALC; displacement at the pen's sensor from acceleration / (2 pi f)^2 with a "
                    "gravity self-calibration (ASSUMPTION, an upper bound on acceleration); the healthy group is younger")
    return out


def pd_waveform() -> Dict:
    """The recorded tremor of the patient with the most prominent line (cached in wholepen/build)."""
    cache = os.path.join(BUILD, "pd_waveform.npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return {"xy": z["xy"], "fs": float(z["fs"]), "f0": float(z["f0"]), "meta": json.loads(str(z["meta"]))}
    nh = newhandpd()
    best = max(nh["above_rows"], key=lambda r: r["prominence"])
    gd = os.path.join(_nh_dir(), "patients")
    _, a = load_nh(os.path.join(gd, f"{best['task']}-{best['subject']}.txt"))
    f0 = best["f_Hz"]
    nb = sosfiltfilt(butter(2, [f0 - 1.0, f0 + 1.0], btype="band", fs=1000.0, output="sos"), a[:, 3:6], axis=0)
    C = np.cov(nb.T)
    w, V = np.linalg.eigh(C)
    xy = nb @ V[:, [2, 1]]                  # major and second axes
    xy = -xy                                # displacement ~ -acceleration / w^2 for a narrow band (shape only)
    env = np.abs(hilbert(xy[:, 0]))
    xy = xy / float(np.mean(env))
    meta = {"subject": best["subject"], "task": best["task"], "f0_Hz": f0, "prominence": best["prominence"],
            "label": "REAL DATA (NewHandPD, LIT PDT-67): band-passed pen acceleration, shape and envelope only"}
    os.makedirs(BUILD, exist_ok=True)
    np.savez(cache, xy=xy, fs=1000.0, f0=f0, meta=json.dumps(meta))
    return {"xy": xy, "fs": 1000.0, "f0": f0, "meta": meta}
