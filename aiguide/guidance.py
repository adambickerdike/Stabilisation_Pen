"""Closed-loop guided writing with the unmodified M1 simulator (sim/pensim).

``model.run(scn, Controller(mode="guided"), tmpl=...)`` is called exactly as
sim/guided_eval.py does; nothing in sim/ is changed.

Configurations
  revA         Controller defaults (q_lim 0.55 mm), N0 = 1.0 N
  pencil_like  Controller(q_lim = 0.30 mm), overrides stage.travel_tip_mech = 0.40 mm,
               N0 = 0.15 N; and stage.axial_preload = 0.05 N, because M1 declares
               contact when the axial force exceeds F_pre + 20 mN: with the Rev A
               preload of 0.25 N a 0.15 N nib force never registers contact and the
               guided mode never engages (checked).  The pencil concept's piezo stage
               and skid (config/pencil.yaml) are NOT modelled: this is the Rev A
               voice-coil lever with pencil-like limits and force.

Confidence scaling (ICD s5 rule 5, c = min(1, c_hat / c_full), zero below c_min)
  The guided core uses a binary confidence (inside 2 q_lim of the template or
  not).  Per-letter authority is emulated by segment-wise runs: the sentence is
  simulated once per authority level present (levels quantised to 0, 0.25, 0.5,
  0.75, 1 through Controller.g_assist) and the outputs are spliced letter by
  letter at the midpoints of the pen-up gaps.  At a pen lift the core sets the
  target authority to zero and the stage returns toward neutral, so the state at
  a splice point is nearly run-independent; the discontinuity of the housing
  and ink positions at every splice point is measured and reported.

Pen anchoring
  Each AI letter template is translated so that its first point is the housing
  position at the letter's first touchdown, taken from the neutral run of the
  same scenario (same tremor, same sensor-noise seed).  This emulates a pen-side
  rule ("anchor the segment at the first contact after its validity start")
  that the firmware does not have yet (proposed in docs/ai_guidance.md).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import REPO_ROOT, use_private_numba_cache

use_private_numba_cache()
from sim.pensim import model, scenarios  # noqa: E402
from stabpen import signals as sg  # noqa: E402

from .metrics import GlyphRecognizer, letter_metrics, pool, travel_limit  # noqa: E402
from .template import LetterTemplate, TemplateTrack, anchor_to, build_track, letter_template  # noqa: E402

CONFIGS = {
    "revA": {"ctrl": {"q_lim": 0.55e-3}, "overrides": {}, "N0": 1.0,
             "label": "Rev A defaults (q_lim 0.55 mm, N0 1.0 N)"},
    "pencil_like": {"ctrl": {"q_lim": 0.30e-3},
                    "overrides": {"stage.travel_tip_mech": 0.40e-3, "stage.axial_preload": 0.05}, "N0": 0.15,
                    "label": "pencil-like limits on the Rev A plant (q_lim 0.30 mm, stop 0.40 mm, N0 0.15 N, F_pre 0.05 N)"},
    "pencil_0.3N": {"ctrl": {"q_lim": 0.30e-3},
                    "overrides": {"stage.travel_tip_mech": 0.40e-3, "stage.axial_preload": 0.05}, "N0": 0.30,
                    "label": "supplementary: pencil-like limits at N0 0.3 N, where M1 contact is stable (one contact per stroke)"},
}
THETA_DEG = 50.0
LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
C_FULL = 0.8
C_MIN = 0.5            # B1.1 authority table (held-out text, depth 2): precision when guided ~0.8; per-user value: EXP-A02
SIM_DT = 25e-6


def kalman_params() -> Dict:
    p = REPO_ROOT / "results" / "sim" / "estimator_selection.json"
    return json.loads(p.read_text())["results"]["kfosc"]["selected_assertive"]["params"]


def nib_offset(cfg: Dict, theta_deg: float = THETA_DEG) -> np.ndarray:
    """Static ink offset from the housing datum: axial slide s0 at the nominal force, projected on the page.

    C = p_H + s a (+ stage terms) with s0 = clip((N0 sin(theta) - F_pre) / k_ax, 0, s_max); the page
    projection of a is cos(theta) along the azimuth (phi = 0: +x).  A constant offset of all writing
    does not affect legibility and the guided core cannot remove it (it servoes the housing datum), so
    path distances are measured to the ideal-pen ink path = intended + this offset.
    """
    from stabpen import params as sp_params
    p = sp_params.load()
    ov = cfg["overrides"]
    th = math.radians(theta_deg)
    F_pre = ov.get("stage.axial_preload", p["stage.axial_preload"])
    kax = ov.get("stage.axial_k", p["stage.axial_k"])
    smax = ov.get("stage.axial_travel", p["stage.axial_travel"])
    s0 = min(max(0.0, (cfg["N0"] * math.sin(th) - F_pre) / kax), smax)
    return np.array([s0 * math.cos(th), 0.0])


def authority(conf: float, c_full: float = C_FULL, c_min: float = C_MIN) -> float:
    return 0.0 if conf < c_min else min(1.0, conf / c_full)


def quantise(c: float) -> float:
    return float(min(LEVELS, key=lambda v: abs(v - c)))


def make_scenario(written, tremor: Optional[sg.TremorSpec], N0: float, seed: int, theta_deg: float = 50.0):
    it = written.intended
    d = np.zeros_like(it.xy) if tremor is None else sg.tremor(it.t, tremor, np.random.default_rng(seed))
    return scenarios._assemble(it, d, N0, theta_deg, meta={"kind": "aiguide_sentence", "text": written.text,
                                                            "seed": seed, "tremor": None if tremor is None else vars(tremor)})


def run(scn, cfg: Dict, mode: str, *, tmpl: Optional[np.ndarray] = None, g: float = 1.0, seed: int = 1,
        extra: Optional[Dict] = None):
    kw = dict(cfg["ctrl"])
    kw.update(extra or {})
    ctrl = model.Controller(mode=mode, g_assist=g, **kw)
    return model.run(scn, ctrl, overrides=cfg["overrides"], seed=seed, tmpl=tmpl)


def arrays(r) -> Dict[str, np.ndarray]:
    return {"t": r["t"].copy(), "tip": r.xy("tipx").copy(), "pH": np.column_stack([r["pHx"], r["pHy"], r["pHz"]]),
            "q": r.xy("q1").copy(), "qr": r.xy("qr1").copy(), "contact": r["contact"].copy(),
            "g": r["conf"].copy(), "stop": r["stop"].copy()}


def letter_windows(written, t_end: float) -> List[Tuple[float, float]]:
    """Splice windows: each letter from the midpoint of the preceding pen-up gap to the next midpoint."""
    Ls = written.letters
    b = [0.0] + [0.5 * (a.t1 + c.t0) for a, c in zip(Ls[:-1], Ls[1:])] + [t_end + 1.0]
    return list(zip(b[:-1], b[1:]))


def splice(runs: Dict[float, Dict[str, np.ndarray]], levels: Sequence[float], windows) -> Tuple[Dict, Dict]:
    """Letter-wise splice of runs made at different authority levels."""
    base = next(iter(runs.values()))
    t = base["t"]
    out = {k: v.copy() for k, v in base.items()}
    jumps_pH, jumps_tip = [], []
    prev = None
    for lev, (a, b) in zip(levels, windows):
        m = (t >= a) & (t < b)
        src = runs[lev]
        for k in out:
            if k != "t":
                out[k][m] = src[k][m]
        if prev is not None and prev != lev:
            i = int(np.searchsorted(t, a))
            if 0 < i < len(t):
                jumps_pH.append(float(np.hypot(*(runs[prev]["pH"][i, :2] - src["pH"][i, :2]))))
                jumps_tip.append(float(np.hypot(*(runs[prev]["tip"][i] - src["tip"][i]))))
        prev = lev
    info = {"n_splices": len(jumps_pH), "max_housing_jump_um": float(max(jumps_pH, default=0.0) * 1e6),
            "max_ink_jump_um": float(max(jumps_tip, default=0.0) * 1e6)}
    return out, info


def touchdowns(written, neutral: Dict[str, np.ndarray]) -> List[Optional[np.ndarray]]:
    """Housing position at each letter's first contact in the neutral run."""
    t, c = neutral["t"], neutral["contact"] > 0
    out = []
    for L in written.letters:
        m = np.flatnonzero((t >= L.t0 - 0.01) & (t <= L.t1) & c)
        out.append(neutral["pH"][m[0], :2].copy() if len(m) else None)
    return out


def hand_path_strokes(written, neutral: Dict[str, np.ndarray], rate: float = 200.0):
    """Per letter: the unassisted hand path the app would learn from (housing position in contact, 200 Hz)."""
    t, c = neutral["t"], neutral["contact"] > 0
    dec = max(1, int(round((1.0 / rate) / (t[1] - t[0]))))
    out = []
    for L in written.letters:
        m = (t >= L.t0 - 0.01) & (t <= L.t1)
        idx = np.flatnonzero(m)
        cc = c[idx]
        d = np.diff(np.r_[0, cc.astype(np.int8), 0])
        strokes, times = [], []
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            j = idx[a:b][::dec]
            if len(j) >= 3:
                strokes.append(neutral["pH"][j, :2].copy())
                times.append(t[j].copy())
        out.append((strokes, times))
    return out


def track_from_letters(letters: Sequence[LetterTemplate], est) -> TemplateTrack:
    return build_track(letters, speed=est.speed, air_speed=est.air_speed, dt=5e-4)


def case_metrics(written, arr: Dict[str, np.ndarray], recognizer: GlyphRecognizer, q_lim: float,
                 neutral: Optional[Dict[str, np.ndarray]] = None, letter_idx: Optional[Sequence[int]] = None,
                 offset=(0.0, 0.0)) -> Dict:
    t = arr["t"]
    per = []
    off = np.asarray(offset, float)
    idxs = range(len(written.letters)) if letter_idx is None else letter_idx
    for k in idxs:
        L = written.letters[k]
        m = (t >= L.t0 - 0.01) & (t <= L.t1 + 0.01)
        lm = letter_metrics(arr["tip"][m], arr["contact"][m], [p + off for p in L.polylines], L.char, recognizer,
                            q=arr["q"][m])
        lm["glyph_index"] = k
        if neutral is not None:
            cm = (arr["contact"][m] > 0) & (neutral["contact"][m] > 0)
            if cm.any():
                dev = np.hypot(*(arr["tip"][m][cm] - neutral["tip"][m][cm]).T)
                lm["max_imposed_um"] = float(dev.max() * 1e6)
        per.append(lm)
    summ = pool(per)
    summ.update(travel_limit(arr["qr"], arr["stop"], arr["contact"], q_lim))
    c = arr["contact"] > 0
    summ["mean_authority_in_contact"] = float(arr["g"][c].mean()) if c.any() else 0.0
    d = np.diff(np.r_[0, c.astype(np.int8), 0])
    summ["contact_runs"] = int(np.sum(d == 1))
    summ["intended_strokes"] = int(sum(len(L.strokes) for L in written.letters))
    stg = [L["max_stage_um"] for L in per if "max_stage_um" in L]
    if stg:
        summ["max_stage_um"] = float(max(stg))
    imp = [L["max_imposed_um"] for L in per if "max_imposed_um" in L]
    if imp:
        summ["max_imposed_um"] = float(max(imp))
        summ["median_letter_max_imposed_um"] = float(np.median(imp))
    return {"summary": summ, "letters": [{k: v for k, v in L.items() if k != "d"} for L in per]}
