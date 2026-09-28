"""Tests of the aiprior study: causality and gating of the guidance command, the clean copy, the selection rules,
reproduction of the handwriting study's tracker numbers, and the output files (when they exist)."""
from __future__ import annotations

import csv
import json
import math

import numpy as np
import pytest

from aiprior import REPO_ROOT, RESULTS_DIR
from aiprior import cleancopy as CC
from aiprior import guide as GU
from aiprior import tuning as TU

from fusion.sensors import Streams


# ------------------------------------------------------------------ synthetic streams for the guidance command
def _streams(T=3.0, seed=0):
    rng = np.random.default_rng(seed)
    tick_t = np.arange(0, T, 5e-4)
    pos_t = np.arange(0.0003, T, 1e-3)
    # a slow "letter" along x plus an 8 Hz tremor of 1 mm
    pos = np.column_stack([0.004 * pos_t + 1e-3 * np.sin(2 * np.pi * 8 * pos_t),
                           0.5e-3 * np.sin(2 * np.pi * 1.5 * pos_t)]) + rng.standard_normal((len(pos_t), 2)) * 3e-6
    con_t = np.arange(0.0002, T, 1e-3)
    con = ((con_t > 0.2) & (con_t < 2.8)).astype(float)
    st = Streams(tick_t=tick_t, acc_t=np.zeros(1), acc_av=np.zeros(1), acc=np.zeros((1, 2)), pos_t=pos_t, pos_av=pos_t + 2e-3,
                 pos=np.ascontiguousarray(pos), pos_ok=np.ones(len(pos_t)), con_t=con_t, con_av=con_t + 1e-3, con=con)
    # template = the slow part, dense
    u = np.linspace(0, T, 3000)
    tpl = {"xy": np.column_stack([0.004 * u, 0.5e-3 * np.sin(2 * np.pi * 1.5 * u)]), "lid": np.zeros(3000, np.int64),
           "conf": np.ones(3000)}
    dh = 0.5e-3 * np.column_stack([np.sin(2 * np.pi * 8 * tick_t), np.zeros(len(tick_t))])
    amp = np.full(len(tick_t), 500e-6)
    return st, tpl, dh, amp


def test_guidance_is_causal():
    st, tpl, dh, amp = _streams()
    p = {"a_lo": 60e-6, "a_hi": 200e-6, "capture": 2e-3, "drop_d": 1.8e-3}
    q0, _ = GU.command(st, dh, amp, tpl, p, lag_s=3e-3)
    Tcut = 1.5
    st2, _, _, _ = _streams()
    st2.pos[st2.pos_t > Tcut - 2e-3] += 1e-3          # samples acquired after (Tcut - latency) arrive after Tcut
    dh2 = dh.copy(); dh2[st.tick_t > Tcut] += 1e-3
    amp2 = amp.copy(); amp2[st.tick_t > Tcut] = 0.0
    q1, _ = GU.command(st2, dh2, amp2, tpl, p, lag_s=3e-3)
    before = st.tick_t <= Tcut
    assert np.allclose(q0[before], q1[before])
    assert not np.allclose(q0[~before], q1[~before])


def test_guidance_off_without_tremor_and_moves_toward_template():
    st, tpl, dh, amp = _streams()
    q_off, info = GU.command(st, dh, np.zeros_like(amp), tpl, {"a_lo": 60e-6, "a_hi": 200e-6})
    assert np.allclose(q_off, -dh) and info["ticks_on"] == 0
    q_on, info = GU.command(st, dh, amp, tpl, {"a_lo": 60e-6, "a_hi": 200e-6, "g_max": 1.0, "capture": 2e-3, "drop_d": 1.8e-3,
                                              "deadband": 0.0, "tau_b": 10.0})
    assert info["ticks_on"] > 0
    # with full authority the commanded ink (handle + command) lies closer to the template curve than with the tracker
    from scipy.spatial import cKDTree
    tree = cKDTree(tpl["xy"])
    m = (st.tick_t > 0.5) & (st.tick_t < 2.7)
    y = np.column_stack([np.interp(st.tick_t, st.pos_t, st.pos[:, i]) for i in range(2)])
    d_on = tree.query((y + q_on)[m])[0].mean()
    d_off = tree.query((y + q_off)[m])[0].mean()
    assert d_on < 0.7 * d_off


# ------------------------------------------------------------------ clean copy
def _writing(T=12.0, fs=1000.0, seed=1):
    """Broadband writing-like motion: white jerk through a 5 Hz low-pass (a power-law spectrum), about 1 mm RMS,
    plus the advance along the line."""
    from scipy.signal import butter, sosfiltfilt
    rng = np.random.default_rng(seed)
    t = np.arange(0, T, 1 / fs)
    w = sosfiltfilt(butter(2, 5.0, fs=fs, output="sos"), rng.standard_normal((len(t), 2)), axis=0)
    w = np.cumsum(np.cumsum(w, axis=0), axis=0)
    w = w - np.polyval(np.polyfit(t, w, 2)[:, 0], t)[:, None] * 0 - sosfiltfilt(butter(2, 0.3, fs=fs, output="sos"), w, axis=0)
    w *= 1e-3 / np.sqrt(np.mean(np.sum(w ** 2, axis=1)))
    xy = w + np.column_stack([0.004 * t, np.zeros_like(t)])
    down = (np.sin(2 * np.pi * 0.9 * t) > -0.6)
    return t, xy, down


def test_tremor_peak_and_wiener_clean():
    t, w, down = _writing()
    trem = np.column_stack([1e-3 * np.sin(2 * np.pi * 6.0 * t), 0.4e-3 * np.sin(2 * np.pi * 6.0 * t + 1.0)])
    pk = CC.tremor_peak(t, w + trem)
    assert abs(pk["f_hat"] - 6.0) < 0.3 and pk["peak_ratio"] > 10
    cl, info = CC.wiener_clean(t, w + trem, down)
    e_raw = np.sqrt(np.mean(np.sum(trem ** 2, axis=1)))
    e_cl = np.sqrt(np.mean(np.sum((cl - w)[1000:-1000] ** 2, axis=1)))
    assert info["applied"] and e_cl < 0.2 * e_raw
    cl2, _ = CC.bandstop_clean(t, w + trem, down)
    assert np.sqrt(np.mean(np.sum((cl2 - w)[1000:-1000] ** 2, axis=1))) < 0.3 * e_raw


def test_wiener_leaves_clean_writing_alone():
    t, w, down = _writing()
    cl, info = CC.wiener_clean(t, w, down)
    assert not info["applied"] and np.sqrt(np.mean(np.sum((cl - w) ** 2, axis=1))) < 1e-9


# ------------------------------------------------------------------ selection rules
def _ai_outs(flips, gain_ink, letters_delta=0.0):
    rows = []
    for f0 in (6.0, 8.0, 10.0):
        for amp in (0.3, 1.0, 2.0):
            base = {"ink_err_um": 500.0 if amp > 0.5 else 150.0, "recognition": 0.8, "word_acc_app": 0.6}
            c = {}
            for i, (fl, g) in enumerate(zip(flips, gain_ink)):
                e = base["ink_err_um"] * (1 - g) if amp > 0.5 else base["ink_err_um"]
                c[str(i)] = {case: {"ink_err_um": e, "recognition": 0.8 + letters_delta, "word_acc_app": 0.6, "flips": fl if case == "wrong_full" else 0,
                                    "ai_share": 0.1, "device_share": 0.3} for case in ("ai_correct", "ai_predicted", "wrong_full")}
            rows.append({"writer": 100, "seed": 300, "f0": f0, "amp_mm": amp, "base": base, "c": c})
    return [{"writer": 100, "rows": rows, "tremor_free": None}]


def test_select_ai_rules():
    cands = [{"g_max": 1.0}, {"g_max": 0.5}, {"g_max": 0.2}]
    s = TU.select_ai(_ai_outs([1, 0, 0], [0.30, 0.10, 0.01]), "T2", cands)
    assert s["table"]["0"]["passes"] is False            # a flip is never allowed
    assert s["best_passing"] == "1" and s["adopted"]
    s = TU.select_ai(_ai_outs([0], [0.01]), "T2", cands[:1])
    assert s["best_passing"] == "0" and not s["adopted"]  # below the 3 % adoption threshold
    s = TU.select_ai(_ai_outs([0], [0.2], letters_delta=-0.05), "T2", cands[:1])
    assert s["best_passing"] is None                     # guidance may not lower letters read


# ------------------------------------------------------------------ reproduction of the handwriting study (slow-ish)
def test_tracker_reproduces_handwriting_study():
    from aiprior import core as CO
    from aiprior import study as SD
    wr = CO.Writer(0)
    sc = CO.make_scenario(wr, 10.0, 1.0e-3, 200)
    ev = SD.evaluate(sc, {"base": None}, ["tracker", "oracle"])
    # results/handwriting (writer 0, seed 200, 10 Hz, 1 mm): Rev H + re-tuned tracker 327.2 um, perfect knowledge 24.9 um
    assert abs(ev["variants"]["tracker"]["ink_err_um"] - 327.2) < 1.0
    assert abs(ev["variants"]["oracle"]["ink_err_um"] - 24.9) < 1.0
    # the template-prior filter without a template is the same tracker
    from fusion import context as CX
    d0, _ = CX.estimate(sc.streams, CO.tracker_params(sc.pen, wr.trk), {"template": None})
    assert np.sqrt(np.mean(np.sum((d0 - sc.dh) ** 2, axis=1))) < 2e-6


# ------------------------------------------------------------------ outputs (skipped until the study has run)
def _need(p):
    if not p.exists():
        pytest.skip(f"{p} not built yet (python3 -m aiprior.run_study)")


def test_outputs_schema():
    j = RESULTS_DIR / "aiprior.json"
    _need(j)
    d = json.loads(j.read_text())
    for k in ("evidence_status", "git_revision", "parameters_sha256_16", "seeds", "command"):
        assert k in d["meta"]
    assert d["meta"]["seeds"]["test_writers"] == [0, 1, 2, 3, 4, 5]
    s = json.loads((RESULTS_DIR / "samples.json").read_text())
    assert s["panels"] and all(set(p) >= {"id", "title", "condition", "device", "caption", "evidence", "intended", "ink", "metrics"}
                               for p in s["panels"])
    with open(REPO_ROOT / "docs" / "evidence.csv", newline="", encoding="utf-8") as f:
        hdr = next(csv.reader(f))
    with open(RESULTS_DIR / "evidence_rows.csv", newline="", encoding="utf-8") as f:
        rd = list(csv.reader(f))
    assert rd[0] == hdr and len(hdr) == 23
    ids = [r[0] for r in rd[1:]]
    assert all(i in {f"ACT-{n}" for n in range(76, 81)} | {f"EML-{n}" for n in range(40, 44)} for i in ids)
    for png in RESULTS_DIR.glob("fig_*.png"):
        assert png.with_suffix(".csv").exists()
