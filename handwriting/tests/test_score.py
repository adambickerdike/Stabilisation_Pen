"""The recording scorer (bridge to the EXP-HW protocols) on synthetic traces with known tremor and size trend."""
from __future__ import annotations

import math

import numpy as np

from handwriting import score_recording as SR
from handwriting import writers as W


def _trace(size_factors=None, f0=0.0, amp=0.0, text="minimum minimum"):
    wr = W.writer(1).write(text, dt=1e-3, seed=1, size_factors=size_factors)
    t = np.arange(len(wr.intended.xy)) * 1e-3
    xy = wr.intended.xy.copy()
    if amp:
        xy[:, 0] += amp * np.sin(2 * math.pi * f0 * t)
        xy[:, 1] += 0.5 * amp * np.sin(2 * math.pi * f0 * t + 1.0)
    return t, xy, wr.intended.pen_down.astype(float), wr


def _csv(path, t, xy, down):
    with open(path, "w") as f:
        f.write("t_s,x,y,pen_down\n")
        for a, (x, y), d in zip(t, xy * 1e3, down):
            f.write(f"{a:.4f},{x:.4f},{y:.4f},{int(d)}\n")


def test_tremor_frequency_and_band(tmp_path):
    t, xy, d, _ = _trace(text=W.ET_SENTENCE)                               # not a periodic text: see tremor_peak
    _csv(tmp_path / "clean.csv", t[::10], xy[::10], d[::10])              # 100 Hz, like a tablet
    t, xy, d, _ = _trace(f0=8.0, amp=0.5e-3, text=W.ET_SENTENCE)
    _csv(tmp_path / "trem.csv", t[::10], xy[::10], d[::10])
    clean = SR.score(SR.load(str(tmp_path / "clean.csv")))
    trem = SR.score(SR.load(str(tmp_path / "trem.csv")))
    assert abs(trem["tremor_peak_hz"] - 8.0) < 0.5 and trem["tremor_peak_detected"]
    assert 0.6 * 395 < trem["tremor_amp_rms_um"] < 1.1 * 395             # 0.5 mm x and 0.25 mm y sine: 395 um RMS
    assert not clean["tremor_peak_detected"]
    known = SR.score(SR.load(str(tmp_path / "trem.csv")), tremor_hz=8.0)
    assert abs(known["tremor_amp_rms_um"] - trem["tremor_amp_rms_um"]) < 1.0
    assert trem["fluency"] and clean["fluency"]


def test_size_trend_flags_progressive_micrographia(tmp_path):
    n = len("minimum minimum".replace(" ", ""))
    t, xy, d, wr = _trace(size_factors=list(np.linspace(1.0, 0.6, n)))
    _csv(tmp_path / "pd.csv", t[::5], xy[::5], d[::5])
    s = SR.score(SR.load(str(tmp_path / "pd.csv")))
    assert s["size"]["progressive_micrographia_10pct"] and s["size"]["change"] < -0.15
    t, xy, d, _ = _trace()
    _csv(tmp_path / "flat.csv", t[::5], xy[::5], d[::5])
    s0 = SR.score(SR.load(str(tmp_path / "flat.csv")))
    assert not s0["size"]["progressive_micrographia_10pct"]
