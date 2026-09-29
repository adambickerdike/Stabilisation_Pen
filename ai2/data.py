"""Domain-randomised training data for the learned estimators (task 2) and for the RL environment (task 3).

Evidence status: SIMULATION (model HW1, synthetic writers and tremor; nothing here is a person).

One sample = one synthetic writer (aiguide style generator, writer id >= 1000, never 0-5 or 100-103) writing a random
3-5 word phrase (Tatoeba CC0 training split, letters only; never the study sentence), with Rev H held (the neutral
run the pen's sensors see) and the same writing without tremor (the target's reference), the fusion sensor streams
with their own noise draws, and per 2 ms step: the 7 causal sensor features of fusion.learned (accelerometer 2,
page-sensor increment 2, new-sample flag, page valid, axial contact), the true tremor disturbance of the handle at
t + delta - lag for the lags of LAGS, and a pen-down mask.

Randomised (ASSUMPTION ranges around the project's nominal values):
  tremor      25 % tremor-free; else f0 4-12 Hz, 0.1-2.5 mm peak (log-uniform), harmonic 0-0.3, ellipticity 0.2-0.8,
              axis 0-180 deg, frequency wander 0.1-0.5 Hz RMS, amplitude modulation 0.1-0.5
  hand        grip stiffness 300-1000 N/m (HAP-26 95 % ranges 228-651 and 679-1043), grip damping 0.8-2.0 N s/m,
              hand mass 0.17-0.26 kg, arm stiffness 120-250 N/m, arm damping 7-16 N s/m
  sensors     pen rotation rho_t, rho_w 0-1, phase -90..90 deg; noise, bias and clock draws of fusion.sensors
  writer      the aiguide style generator (size, slant, width, spacing, speed 20-34 mm/s, allographs)
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR, TRAIN_WRITER0, ensure_paths

ensure_paths()
from fusion import learned as FL  # noqa: E402
from fusion import sensors as S  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting import tracker as TR  # noqa: E402
from handwriting import writers as W  # noqa: E402
from stabpen import signals as sg  # noqa: E402

NET_HZ = 500.0
LAGS = (0.0, 0.025, 0.05, 0.1)
DATA_DIR = BUILD_DIR / "learn_data"
STUDY_TEXT = W.ET_SENTENCE


_POOL: List[str] = []


def phrases(n: int, seed: int = 0) -> List[str]:
    """Random 3-5 word phrases of letters from the Tatoeba CC0 training split (never the study sentence)."""
    from aiguide import corpus as ACO
    if not _POOL:
        _POOL.extend(s for s in ACO.make_splits().train if 12 <= len(s) <= 80)
    rng = np.random.default_rng(seed)
    out = []
    pool = _POOL
    while len(out) < n:
        s = pool[int(rng.integers(len(pool)))]
        ws = [w.strip(".,:-/'") for w in s.split()]
        if not all(w.isalpha() and w.isascii() for w in ws):
            continue
        k = int(rng.integers(3, 6))
        if len(ws) < k:
            continue
        i = int(rng.integers(0, len(ws) - k + 1))
        ph = " ".join(ws[i:i + k])
        if ph != STUDY_TEXT and 10 <= len(ph) <= 40:
            out.append(ph)
    return out


def draw(i: int, kind: str = "train") -> Dict:
    """The randomised specification of sample i (deterministic)."""
    base = {"train": 5000, "val": 9000}[kind]
    rng = np.random.default_rng(base * 1000 + i)
    tremor = rng.random() >= 0.25
    spec = {"i": i, "kind": kind, "writer": TRAIN_WRITER0 + (i if kind == "train" else 5000 + i),
            "text_seed": base + i, "tremor": bool(tremor),
            "f0": float(rng.uniform(4.0, 12.0)), "amp": float(math.exp(rng.uniform(math.log(0.1e-3), math.log(2.5e-3)))),
            "harmonic": float(rng.uniform(0.0, 0.3)), "ellipticity": float(rng.uniform(0.2, 0.8)),
            "orientation": float(rng.uniform(0.0, math.pi)), "f_jitter": float(rng.uniform(0.1, 0.5)),
            "am_depth": float(rng.uniform(0.1, 0.5)),
            "K_grip": float(rng.uniform(300.0, 1000.0)), "C_grip": float(rng.uniform(0.8, 2.0)),
            "M_hand": float(rng.uniform(0.17, 0.26)), "k_arm": float(rng.uniform(120.0, 250.0)),
            "b_arm": float(rng.uniform(7.0, 16.0)), "rho_t": float(rng.uniform(0.0, 1.0)), "rho_w": float(rng.uniform(0.0, 1.0)),
            "psi_t": float(rng.uniform(-math.pi / 2, math.pi / 2)), "sensor_seed": int(70_000_000 + base * 100 + i),
            "tremor_seed": int(80_000_000 + base * 100 + i)}
    if not tremor:
        spec["amp"] = 0.0
    return spec


def build_runs(spec: Dict, text: Optional[str] = None):
    """(scenario, pen, hand, neutral run, clean run, streams) for one randomised sample."""
    pen = PR.rev_h()
    hand = replace(PR.Hand.from_config(), K_grip=spec["K_grip"], C_grip=spec["C_grip"], M_hand=spec["M_hand"],
                   k_arm=spec["k_arm"], b_arm=spec["b_arm"])
    txt = text or phrases(1, seed=spec["text_seed"])[0]
    written = W.writer(spec["writer"]).write(txt, dt=W.SIM_DT, seed=3000 + spec["writer"])
    scn0 = PL.scenario_from_written(written, None, meta={"writer": spec["writer"]})
    hp = PL.adapted_path(scn0.intended, scn0.dt, pen, hand)
    clean = PL.run(PL.with_hand_path(scn0, hp), pen, hand, ctl=PL.Controls())
    d = None
    if spec["amp"] > 0:
        ts = sg.TremorSpec(f0=spec["f0"], amp_pk=spec["amp"], harmonic=spec["harmonic"], ellipticity=spec["ellipticity"],
                           orientation=spec["orientation"], f_jitter=spec["f_jitter"], am_depth=spec["am_depth"])
        d = sg.tremor(scn0.t, ts, np.random.default_rng(spec["tremor_seed"]))
    scn = PL.with_hand_path(scn0, hp, d)
    neutral = clean if d is None else PL.run(scn, pen, hand, ctl=PL.Controls())
    cfg = S.config(page="1k", comp="gyro", rho_t=spec["rho_t"], rho_w=spec["rho_w"], psi_t=spec["psi_t"])
    cfg.r_board = pen.r_imu
    st = S.make_streams(TR.record(neutral, scn, neutral.info["tick_decim"]), cfg, spec["sensor_seed"])
    return scn, pen, hand, neutral, clean, st, written, txt


def targets_for(neutral, clean, tk: np.ndarray, delta: float, lags: Sequence[float] = LAGS):
    """True handle disturbance d = handle(tremor) - handle(clean) at tk + delta - lag (m), and the pen-down mask."""
    n = min(len(neutral.t), len(clean.t))
    tr = neutral.t[:n]
    d = neutral.handle[:n] - clean.handle[:n]
    Y = np.zeros((len(tk), len(lags), 2))
    for i, lag in enumerate(lags):
        s = tk + delta - lag
        Y[:, i, 0] = np.interp(s, tr, d[:, 0]); Y[:, i, 1] = np.interp(s, tr, d[:, 1])
    con = np.interp(tk + delta, tr, neutral.contact[:n]) > 0.5
    return Y, con


def model_based(st, pen, tk: np.ndarray, tremor_params: Dict, det_params: Dict, lags: Sequence[float] = LAGS) -> Dict:
    """The model-based estimates on the same streams, at the network steps: the fixed-lag RTS tremor estimate at
    `lags` (ungated), the Rev H tracker's causal output (the fallback), and the detector's ratio, amplitude,
    frequency and hysteresis gate (zero-order hold)."""
    from fusion import estimators as ES
    from . import smoothers as SM
    delta = PR.servo_group_delay(pen)
    tp = dict(tremor_params)
    rts = SM.rts_fixed_lag(st, tp, lags, delta, out_every=int(round(pen.tick_hz / NET_HZ)))
    n = min(len(tk), len(rts["t"]))
    D = np.zeros((len(tk), len(lags), 2)); D[:n] = rts["tremor"][:n]
    trk = PR.akf_revh()
    p = dict(trk["params"]); p["horizon"] = float(p.get("horizon", 0.0)) + delta
    dh, _ = ES.akf(st, p)
    dh_k = np.column_stack([np.interp(tk, st.tick_t, dh[:, 0]), np.interp(tk, st.tick_t, dh[:, 1])])
    det = SM.detector(st, det_params)
    kk = np.searchsorted(det["t"], tk, side="right") - 1
    ok = kk >= 0
    kk = np.clip(kk, 0, max(len(det["t"]) - 1, 0))
    g = lambda a: np.where(ok, np.asarray(a)[kk], 0.0) if len(det["t"]) else np.zeros(len(tk))  # noqa: E731
    return {"D": D.astype(np.float32), "dh": dh_k.astype(np.float32), "ratio": g(det["ratio"]).astype(np.float32),
            "amp": g(det["amp"]).astype(np.float32), "f_hat": g(det["f_hat"]).astype(np.float32),
            "gate": g(det["gate"]).astype(np.float32)}


def sample(spec: Dict, model_params: Optional[Dict] = None) -> Dict:
    scn, pen, hand, neutral, clean, st, written, txt = build_runs(spec)
    X, tk = FL.features(st, NET_HZ)
    delta = PR.servo_group_delay(pen)
    Y, con = targets_for(neutral, clean, tk, delta)
    out = {"X": X.astype(np.float32), "Y": Y.astype(np.float32), "mask": (con & (tk > 0.3)).astype(np.float32),
           "tk": tk, "spec": spec, "text": txt}
    if model_params is not None:
        out.update(model_based(st, pen, tk, model_params["tremor"], model_params["det"]))
    return out


MB_KEYS = ("D", "dh", "ratio", "amp", "f_hat", "gate")


def save_sample(i: int, kind: str = "train", model_params: Optional[Dict] = None) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = DATA_DIR / f"{kind}_{i:04d}.npz"
    if not p.exists():
        s = sample(draw(i, kind), model_params)
        np.savez_compressed(p, X=s["X"], Y=s["Y"], mask=s["mask"], tk=s["tk"],
                            spec=np.array(json.dumps(s["spec"])), text=np.array(s["text"]),
                            **{k: s[k] for k in MB_KEYS if k in s})
    return str(p)


def load_set(kind: str, n: int):
    out = []
    for i in range(n):
        p = DATA_DIR / f"{kind}_{i:04d}.npz"
        if p.exists():
            z = np.load(p)
            d = {"X": z["X"], "Y": z["Y"], "mask": z["mask"], "spec": json.loads(str(z["spec"]))}
            for k in MB_KEYS:
                if k in z:
                    d[k] = z[k]
            out.append(d)
    return out
