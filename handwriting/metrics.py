"""Metrics of simulated ink (CALCULATIONS on SIMULATION output).

ink error      per letter, nearest-point distance of in-contact ink to the letter's intended (or target) path,
               pooled RMS and p95 (aiguide.metrics.letter_metrics)
recognition    aiguide's template-matching recogniser (26 lower-case glyphs in the writer's style, size-normalised
               DTW), per letter; accuracy against the intended (or target) letters
readability    words read correctly by the app's reader: the recognised letters of each word, then the app's
               lexicon correction (app/penapp/autocorrect.py, threshold 0.9); exact-letter word accuracy also reported
legibility     DTW of the ink letter to the clean letter (aiguide's proxy, um)
tremor band    3-15 Hz part of (ink - intended), time-aligned, in contact
travel         fraction of in-contact time with the tip command at >= 95 % of the usable travel; at the stop; force limit
size           per-letter x-height estimate = ink height / the glyph's height in x-height units
fluency        per stroke: normalised jerk (PDT-17 definition 0.5 * int j^2 dt * D^5 / L^2), speed peaks, mean speed
authorship     device share of ink motion = L(c) / (L(c) + L(h)), where h is the ink the same hand makes without the
               device and c = ink - h (L = pen-down path length); and the largest device displacement
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.signal import butter, savgol_filter, sosfiltfilt

from . import ensure_paths

ensure_paths()
from aiguide.glyphs import GLYPH_SET, bbox  # noqa: E402
from aiguide.metrics import GlyphRecognizer, letter_metrics, pool  # noqa: E402


def recognizer_for(written) -> GlyphRecognizer:
    """The app's recogniser in the writer's style (true width and slant; size is normalised away)."""
    st = written.style
    return GlyphRecognizer(st.x_height_mm * 1e-3, st.width, math.radians(st.slant_deg))


def _k(res, scn):
    return np.clip(np.round(res.t / scn.dt).astype(int), 0, len(scn.t) - 1)


def letter_rows(written, res, rec: GlyphRecognizer, targets: Optional[Sequence[str]] = None,
                target_polys: Optional[Sequence[Sequence[np.ndarray]]] = None, pad: float = 0.01) -> List[Dict]:
    """Per-letter metrics; targets/target_polys override the reference letter (practice: the correct letter)."""
    t = res.t
    ink = res.ink
    con = res.contact
    q = res.xy("qx")
    out = []
    for k, L in enumerate(written.letters):
        m = (t >= L.t0 - pad) & (t <= L.t1 + pad)
        ch = L.char if targets is None else targets[k]
        polys = L.polylines if target_polys is None else target_polys[k]
        lm = letter_metrics(ink[m], con[m], polys, ch, rec, q=q[m])
        lm["glyph_index"] = k
        lm["word_index"] = L.word_index
        lm["written_char"] = L.char
        out.append(lm)
    return out


def summary(rows: List[Dict]) -> Dict:
    s = pool(rows)
    return {k: float(v) for k, v in s.items()}


# ------------------------------------------------------------------ words and the app's lexicon correction
@lru_cache(maxsize=1)
def _corrector():
    from penapp import autocorrect as AC
    model = AC.NgramWordModel.from_corpus()
    return AC.Autocorrector(model, cer=0.10, threshold=0.9)


def words(rows: List[Dict], text: str, corrected: bool = True) -> Dict:
    """Recognised words; exact letter-level word accuracy and the app's corrected word accuracy."""
    target_words = [w for w in text.split(" ") if w]
    n_w = len(target_words)
    rec_words = [""] * n_w
    for r in rows:
        wi = r["word_index"]
        if wi < n_w:
            rec_words[wi] += r.get("recognised_as", "?") if not r.get("missing") else "?"
    exact = [a == b for a, b in zip(rec_words, target_words)]
    out = {"recognised": rec_words, "target": target_words, "word_accuracy_letters": float(np.mean(exact))}
    if corrected:
        try:
            ac = _corrector()
            toks = [w.replace("?", "e") for w in rec_words]
            corr = ac.correct_tokens(toks)
            chosen = [c.chosen.lower() for c in corr]
            out["corrected"] = chosen
            out["word_accuracy_app"] = float(np.mean([a == b for a, b in zip(chosen, target_words)]))
        except Exception as e:                       # the corrector needs the cached corpus model (aiguide/build)
            out["corrector_error"] = repr(e)
    return out


# ------------------------------------------------------------------ ink error in the tremor band
def band_error_um(res, scn, band=(3.0, 15.0)) -> float:
    k = _k(res, scn)
    e = res.ink - scn.intended[k]
    fs = 1.0 / float(res.t[1] - res.t[0])
    eb = sosfiltfilt(butter(4, band, btype="band", fs=fs, output="sos"), e, axis=0)
    m = (res.contact > 0.5) & (res.t > 0.5)
    return float(np.sqrt(np.mean(np.sum(eb[m] ** 2, axis=1))) * 1e6)


def aligned_error_um(res, scn) -> float:
    k = _k(res, scn)
    e = res.ink - scn.intended[k]
    m = res.contact > 0.5
    return float(np.sqrt(np.mean(np.sum(e[m] ** 2, axis=1))) * 1e6)


def travel(res, pen) -> Dict:
    m = res.contact > 0.5
    if pen.rigid or not m.any():
        return {"at_travel_limit": 0.0, "on_stop": 0.0, "at_force_limit": 0.0, "q_max_mm": 0.0, "F_rms_N": 0.0}
    qc = np.hypot(res["qcx"], res["qcy"])
    F = np.hypot(res["Fax"], res["Fay"])
    return {"at_travel_limit": float(np.mean(qc[m] >= 0.95 * pen.q_lim)), "on_stop": float(np.mean(res["stop"][m] > 0.5)),
            "at_force_limit": float(np.mean(res["sat"][m] > 0.5)),
            "q_max_mm": float(np.max(np.hypot(res["qx"], res["qy"])) * 1e3),
            "q_rms_mm": float(np.sqrt(np.mean(res["qx"][m] ** 2 + res["qy"][m] ** 2)) * 1e3),
            "F_rms_N": float(np.sqrt(np.mean(F[m] ** 2))), "F_p99_N": float(np.percentile(F[m], 99)),
            "above_continuous": float(np.mean(F[m] > pen.F_cont)) if pen.F_cont > 0 else 0.0}


# ------------------------------------------------------------------ letter size (micrographia)
@lru_cache(maxsize=64)
def glyph_height_units(ch: str) -> float:
    b = bbox(GLYPH_SET[ch])
    return max(b[3] - b[1], 0.3)


def xheight_mm(rows: List[Dict]) -> np.ndarray:
    """Per-letter x-height estimate (mm) from the ink height; nan where missing."""
    out = []
    for r in rows:
        h = r.get("height_um")
        ch = r.get("written_char", r.get("char"))
        out.append(np.nan if (h is None or ch not in GLYPH_SET) else h * 1e-3 / glyph_height_units(ch))
    return np.array(out)


# ------------------------------------------------------------------ fluency (PDT-17 measures)
def fluency(res, min_len_s: float = 0.05, smooth_hz: float = 20.0) -> Dict:
    """Normalised jerk and speed peaks per pen-down stroke of the ink (low-pass smoothed at smooth_hz)."""
    t = res.t
    fs = 1.0 / float(t[1] - t[0])
    xy = sosfiltfilt(butter(2, smooth_hz, fs=fs, output="sos"), res.ink, axis=0)
    v = np.gradient(xy, 1.0 / fs, axis=0)
    a = np.gradient(v, 1.0 / fs, axis=0)
    j = np.gradient(a, 1.0 / fs, axis=0)
    sp = np.hypot(v[:, 0], v[:, 1])
    c = res.contact > 0.5
    d = np.diff(np.r_[0, c.astype(np.int8), 0])
    nj, peaks, speeds, durs = [], [], [], []
    for a0, b0 in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        # skip the first/last 10 ms of each contact (touchdown and lift)
        a1 = a0 + int(0.01 * fs); b1 = b0 - int(0.01 * fs)
        if b1 - a1 < int(min_len_s * fs):
            continue
        seg = slice(a1, b1)
        D = (b1 - a1) / fs
        L = float(np.sum(np.hypot(*np.diff(xy[seg], axis=0).T)))
        if L < 1e-5:
            continue
        J = 0.5 * float(np.sum(np.sum(j[seg] ** 2, axis=1)) / fs)
        nj.append(math.sqrt(J * D ** 5 / L ** 2))
        s = sp[seg]
        pk = int(np.sum((s[1:-1] > s[:-2]) & (s[1:-1] >= s[2:]) & (s[1:-1] > 0.1 * s.max())))
        peaks.append(pk)
        speeds.append(L / D)
        durs.append(D)
    if not nj:
        return {}
    return {"norm_jerk_median": float(np.median(nj)), "speed_peaks_per_stroke": float(np.mean(peaks)),
            "mean_speed_mm_s": float(np.mean(speeds) * 1e3), "stroke_duration_s": float(np.median(durs)),
            "peak_speed_mm_s": float(np.percentile(sp[c], 99) * 1e3), "n_strokes": len(nj)}


# ------------------------------------------------------------------ authorship
def authorship(res, res_hand_only) -> Dict:
    """Device share of the ink motion against the counterfactual ink of the same hand without the device."""
    n = min(len(res.t), len(res_hand_only.t))
    m = (res.contact[:n] > 0.5) & (res_hand_only.contact[:n] > 0.5)
    h = res_hand_only.ink[:n]
    c = res.ink[:n] - h
    dm = m[1:] & m[:-1]
    Lh = float(np.sum(np.hypot(*np.diff(h, axis=0).T)[dm]))
    Lc = float(np.sum(np.hypot(*np.diff(c, axis=0).T)[dm]))
    disp = np.hypot(c[:, 0], c[:, 1])[m]
    return {"device_share": Lc / max(Lc + Lh, 1e-12), "device_path_mm": Lc * 1e3, "hand_path_mm": Lh * 1e3,
            "device_disp_rms_mm": float(np.sqrt(np.mean(disp ** 2)) * 1e3) if disp.size else 0.0,
            "device_disp_max_mm": float(disp.max() * 1e3) if disp.size else 0.0}


def decimate_path(res, scn=None, hz: float = 60.0, key: str = "ink") -> np.ndarray:
    """[[x_mm, y_mm, pen_down], ...] at <= hz (pen-down state from the recorded contact)."""
    t = res.t
    step = max(1, int(round((1.0 / hz) / float(t[1] - t[0]))))
    xy = res.ink if key == "ink" else res.handle
    idx = np.arange(0, len(t), step)
    c = res.contact
    # keep transitions so strokes start and end at the right places
    tr = np.flatnonzero(np.diff(c) != 0)
    idx = np.unique(np.r_[idx, tr, np.minimum(tr + 1, len(t) - 1)])
    return np.column_stack([xy[idx, 0] * 1e3, xy[idx, 1] * 1e3, (c[idx] > 0.5).astype(float)])


def intended_path(scn, hz: float = 60.0) -> np.ndarray:
    t = scn.t
    step = max(1, int(round((1.0 / hz) / scn.dt)))
    c = scn.down
    idx = np.arange(0, len(t), step)
    tr = np.flatnonzero(np.diff(c) != 0)
    idx = np.unique(np.r_[idx, tr, np.minimum(tr + 1, len(t) - 1)])
    return np.column_stack([scn.intended[idx, 0] * 1e3, scn.intended[idx, 1] * 1e3, (c[idx] > 0.5).astype(float)])
