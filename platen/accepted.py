"""Part (b): accepted writing by moving the page under a pen the user holds still (SIMULATION).

PLAN (fixed here before any accepted run):
  References  the independent engineering pass's accepted references, read-only:
                'se'       the 20 exported whole-suffix references (becau -> because) of
                           results/improvement/writing/grounded_accepted/*_accepted_se.npz: UJI session-1 glyphs of 20
                           test writers at 3 mm x-height, 200 ms lower and lift phases, 500 ms pen-up moves between
                           letters (the same files the grounded five-bar replayed)
                'library'  the separate rewrite libary -> library of ai3/run_completion_replay.py, rebuilt here with
                           ai3's own functions (plan_from_acceptance with the grounded export's 100 mm reference
                           envelope and 200 ms lift/lower; letters joined by the grounded export's 500 ms pen-up
                           moves, ai3.export_grounded_completion.join_word): the same 20 writers
  Hand        HW1's hand and ordinary 12 g pen hold the pen still: the imposed hand path is the starting point + a slow
              drift (0.5 mm RMS per axis, 0.3 Hz; ASSUMPTION) + real tremor (study R's library, TUNING patients,
              PD or ET, at the moderate 0.24 mm or severe 1.72 mm class; one recording per writer, seeded).  Nothing
              forces the hand: the page moves.  Writer conventions: 'intended' with no intended motion (the page's drag
              acts on the pen: the main case) and 'hw1' (HW1's ideal drag compensation).
  Platen      the proposed two-layer stage (design.sim_stage('fine_A5_coarse')): the coarse H-bot follows the smooth
              page motion of the word (reference feedforward), the fine stage adds the cancellation of every tip motion
              measured by the camera-class sensor (250 Hz, 6 ms, 15 um), predicted over its lag by the tuned predictor
              ('calm' without tremor, 'tremor' with tremor; both fitted on the tuning split).  Z-drop lift: contact
              follows the plan's lower/ink phases after 40 ms (ASSUMPTION; 200 ms as the five-bar's in part c).
              Supervisor as the five-bar's: refuse (hold the page, drop it) if the platen's own ink estimate is more
              than 0.20 mm off for 10 ms during requested ink.
  Measures    the five-bar's (wholepen/grounded_replay.py): required-ink coverage, RMS error while requested ink
              actually contacts, ink path during pen-up (air) phases, refusals, and its engineering criterion (no
              refusal or stop hit, coverage >= 98 %, RMS <= 0.10 mm, air ink <= 0.02 mm); plus extra ink outside
              requested phases; and the five-bar derivative check's sampled acceleration and jerk (adjacent differences
              at 0.5 ms) of the ink on the page, of the page (stage) and of the pen tip, against 2 m/s2 and 300 m/s3,
              with a 30 Hz low-passed variant as a secondary, labelled measure.
"""
from __future__ import annotations

import dataclasses
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import common as CM

HANDS = {                     # tremor class and kind, drift on/off
    "still": (None, None, False),
    "drift": (None, None, True),
    "mod_PD": ("moderate", "PD", True),
    "mod_ET": ("moderate", "ET", True),
    "sev_PD": ("severe", "PD", True),
    "sev_ET": ("severe", "ET", True),
    "cradle": (None, None, False),          # the pen docked in a stiff holder on the palm rest (the plotter limit)
}
CRADLE_HAND = {"K_grip": 2.0e4, "C_grip": 20.0, "k_arm": 2.0e4, "b_arm": 50.0}     # ASSUMPTION: a stiff holder
WRITERS_CONV = ("intended", "hw1")
# controllers: (drag decoupling on, compliance-model scale).  'naive' follows the measured tip as it is; 'decoupled'
# subtracts the tip deflection the page's own drag causes (measured drag force x the calibrated hand compliance)
# controllers: (drag decoupling + friction feedforward + ink integral on, compliance-model scale).
#   naive     the page follows the camera's tip prediction (page = tip - reference): exact when the tip does not
#             respond to the page's drag
#   ink_loop  the proposed accepted-mode law: the hand-caused tip motion (tip minus the deflection the page's own drag
#             causes: measured drag x the calibrated hand compliance) is cancelled; the expected sliding deflection is
#             fed forward from the reference direction (compliance x mu_k x N); an integral on the measured ink error
#             winds the pen up through stiction
CONTROLLERS = {"naive": (False, 1.0), "ink_loop": (True, 1.0), "ink_loop_model_x0.7": (True, 0.7),
               "ink_loop_model_x1.3": (True, 1.3), "decoupled_only": (True, 1.0)}
INK_KI = 25.0                 # 1/s (PROPOSED: below 1 / (4 x the loop delay of about 15-20 ms))
FIRM_HAND = {"K_grip": 1150.0, "k_arm": 2000.0, "b_arm": 20.0}   # ASSUMPTION: a firm grip, the hand anchored on the rest
CONFIGS = {   # name: (writer convention, hand overrides, normal force N, controller)
    "firm_ideal": ("hw1", {}, 1.0, "naive"),                 # the hand cancels the page's drag (HW1's convention)
    "relaxed_naive": ("intended", {}, 1.0, "naive"),         # HW1's relaxed hand, no drag compensation
    "relaxed_ink_loop": ("intended", {}, 1.0, "ink_loop"),
    "proposed": ("intended", FIRM_HAND, 0.5, "ink_loop"),    # palm-rest anchored firm grip, Z force control 0.5 N
    "cradle": ("intended", CRADLE_HAND, 0.5, "naive"),       # the pen docked in a stiff holder (plotter limit)
}
CALM_SERVO_HZ = 15.0          # PROPOSED: the fine follower's bandwidth when the user has no tremor (less camera jitter)
TREMOR_SERVO_HZ = 40.0
CAMERA = {"cam_hz": 250.0, "cam_latency": 6e-3, "noise": 15e-6}
STAGE_VARIANT = "fine_A5_coarse"
PRE_S = 0.6                   # s before the reference starts (the predictor fills its history)
POST_S = 0.3
DT = 2.5e-5                   # HW1's plant step
ACC_LIM = 2.0
JERK_LIM = 300.0
LP_HZ = 30.0


# ------------------------------------------------------------------ references
def _ref_derivs(z) -> tuple:
    """The reference's analytic page-frame velocity and acceleration (ai3's exported channels): v = coarse velocity +
    fine velocity mapped to the page (x / sin 50 deg), a = the absolute nib acceleration on the page."""
    Minv = np.diag([1.0 / np.sin(np.deg2rad(50.0)), 1.0])
    v = np.asarray(z["coarse_velocity_m_s"], float) + np.asarray(z["q_velocity_m_s"], float) @ Minv.T
    a = np.asarray(z["absolute_nib_acceleration_page_m_s2"], float)
    return v, a


def resample(ref: Dict, t_new: np.ndarray):
    """Position (cubic Hermite with the analytic velocity: the reference samples are not uniform in time), velocity
    and acceleration of a reference at the times t_new (held before the start and after the end)."""
    from scipy.interpolate import CubicHermiteSpline
    t = np.asarray(ref["t"], float)
    keep = np.r_[True, np.diff(t) > 1e-9]
    t, xy, v, a = t[keep], np.asarray(ref["xy"])[keep], np.asarray(ref["v"])[keep], np.asarray(ref["a"])[keep]
    tc = np.clip(t_new, t[0], t[-1])
    sp = CubicHermiteSpline(t, xy, v, axis=0)
    inside = ((t_new >= t[0]) & (t_new <= t[-1]))[:, None]
    vv = np.column_stack([np.interp(tc, t, v[:, i]) for i in range(2)]) * inside
    aa = np.column_stack([np.interp(tc, t, a[:, i]) for i in range(2)]) * inside
    return sp(tc), vv, aa


def se_references() -> List[Dict]:
    man = CM.jload(CM.SE_MANIFEST)
    out = []
    for row in man["rows"]:
        if not row.get("word_reference"):
            continue
        z = np.load(CM.REPO_ROOT / row["word_reference"], allow_pickle=True)
        v, a = _ref_derivs(z)
        out.append({"writer": row["writer"], "text": "se", "kind": "completion", "t": z["t"], "xy": z["xy"],
                    "v": v, "a": a, "down": z["down"].astype(bool), "phase": z["phase"].astype(str),
                    "source": row["word_reference"], "sha256": CM.sha256_file(CM.REPO_ROOT / row["word_reference"])})
    return out


def library_references(quick: bool = False, log=CM.log) -> List[Dict]:
    """'libary' -> 'library' (separate rewrite) with ai3's functions and the grounded export's settings (cached)."""
    p = CM.cache_dir(quick, "accepted") / "library_refs.npz"
    if p.exists():
        z = np.load(p, allow_pickle=True)
        return list(z["refs"])
    from ai3 import accepted_completion as A
    from ai3 import coarse_fine as F
    from ai3 import data as D
    from ai3 import layers as L
    from ai3 import online as O
    from ai3 import reachable as R
    from ai3.export_grounded_completion import join_word
    letters, prov = D.load_uji()
    calibration = [l for l in letters if l.rep == 1]
    heights = O.writer_xheights(calibration)
    writers = sorted(w for w in heights if w.startswith("tst"))[:(3 if quick else 20)]
    limits = dataclasses.replace(R.MotionLimits(), radius_m=.100, hard_stop_m=.101, lift_delay_s=.200,
                                 lower_delay_s=.200, position_error_m=0., velocity_error_m_s=0.,
                                 acceleration_error_m_s2=0.)
    refs = []
    for w in writers:
        bank = {l.char: [s / heights[w] for s in l.strokes] for l in calibration if l.writer == w}
        acc = L.Revision(0, 0, "libary", "library", "spelling", "writer", "writer",
                         "ASSUMED explicit acceptance for mechanical replay", 0.)
        try:
            plan, trajs, pre = A.plan_from_acceptance(acc, bank, limits=limits)
        except Exception as e:                      # a missing glyph rejects the whole rewrite (ai3's rule)
            log(f"[accepted] library {w}: rejected ({e})")
            refs.append({"writer": w, "text": "library", "kind": "spelling", "rejected": str(e)})
            continue
        if plan is None:
            refs.append({"writer": w, "text": "library", "kind": "spelling", "rejected": "preflight"})
            continue
        samples = [F.export(tr, F.CoarseStage(), 1.0, None) for tr in trajs]
        pts = np.vstack([s["xy"] for s in samples])
        origin = (pts.min(0) + pts.max(0)) / 2
        word = join_word(samples, origin, limits, trajs[0].model)
        v, a = _ref_derivs(word)
        refs.append({"writer": w, "text": "library", "kind": "spelling", "t": word["t"], "xy": word["xy"],
                     "v": v, "a": a, "down": word["down"].astype(bool), "phase": word["phase"].astype(str),
                     "source": "ai3.accepted_completion.plan_from_acceptance + ai3.export_grounded_completion.join_word "
                               "(UJI session-1 banks, 100 mm reference envelope, 200 ms lift/lower, 500 ms air moves)"})
        log(f"[accepted] library {w}: {word['t'][-1]:.1f} s, {np.ptp(word['xy'][:, 0]) * 1e3:.1f} x "
            f"{np.ptp(word['xy'][:, 1]) * 1e3:.1f} mm")
    np.savez_compressed(p, refs=np.array(refs, dtype=object), allow_pickle=True)
    return refs


# ------------------------------------------------------------------ predictors (tuning split)
def stage_for(hand_key: str):
    """The two-layer stage; the fine follower at 15 Hz for a calm hand, 40 Hz with tremor (PROPOSED)."""
    from . import design as D
    st = D.sim_stage(STAGE_VARIANT)
    calm = HANDS[hand_key][0] is None
    st.servo_hz = CALM_SERVO_HZ if calm else TREMOR_SERVO_HZ
    return st


def predictors(quick: bool) -> Dict[str, Dict]:
    """'tremor': tremor + drift training (40 Hz stage horizon); 'calm': drift only (15 Hz stage horizon).  Both fitted
    on the tuning split (predictor.py)."""
    from . import predictor as PRD
    out = {}
    for name, hk in (("tremor", "sev_PD"), ("calm", "still")):
        g = stage_for(hk).group_delay()
        base = f"{CAMERA['cam_hz']:g}Hz_{CAMERA['cam_latency'] * 1e3:g}ms_{CAMERA['noise'] * 1e6:g}um_g{g * 1e3:.2f}"

        def sig(name=name):
            ss = PRD.training_signals(quick)
            if name == "calm":
                for x in ss:
                    x["e"] = np.zeros_like(x["e"])  # drift only (the fit adds the drift variant)
            return ss
        out[name] = PRD.load_or_fit(f"acc_{name}_" + base, sig, quick=quick, cam_hz=CAMERA["cam_hz"],
                                    cam_latency=CAMERA["cam_latency"], noise=CAMERA["noise"], g=g, with_drift=True)
    return out


# ------------------------------------------------------------------ one accepted run
def hand_path(t: np.ndarray, hand_key: str, seed_key: str):
    """Imposed hand path (m): start point (0, 0) + drift + tremor, and its tremor part."""
    from realdata import library as RL
    cls, kind, use_drift = HANDS[hand_key]
    p = np.zeros((len(t), 2))
    trem = np.zeros((len(t), 2))
    meta = {"hand": hand_key}
    if use_drift:
        from . import predictor as PRD
        p += PRD.drift(t, CM.h("acc-drift", seed_key))
    if cls is not None:
        amp = RL.classes(False)[cls]["representative_mm"]
        dr = RL.tremor(cls, seed=CM.h("acc-trem", seed_key, kind) % 100000, kind=kind, split="tuning", t=t, amp_mm=amp)
        trem = np.asarray(dr.d, float)
        p += trem
        meta.update({"tremor": {k: dr.meta[k] for k in ("rid", "amp_mm", "f0", "subject", "source", "kind")}})
    return p, trem, meta


def friction_feedforward(v_ref: np.ndarray, contact_phase: np.ndarray, G0: float, mu_k: float, N: float,
                         v_min: float = 1e-3) -> np.ndarray:
    """The pen's expected sliding deflection, fed forward into the page command (PROPOSED): -G0 mu_k N v_hat, v_hat the
    reference's ink direction; within each contact segment the first direction is held back to the touchdown (the pen
    is wound up before the stroke) and the last one forward to the lift; zero in the air."""
    n = len(v_ref)
    sp = np.linalg.norm(v_ref, axis=1)
    out = np.zeros((n, 2))
    seg = np.flatnonzero(np.diff(np.r_[0, contact_phase.astype(int), 0]) != 0).reshape(-1, 2)
    for a, b in seg:
        vv = v_ref[a:b]
        mv = sp[a:b] > v_min
        if not mv.any():
            continue
        u = np.zeros_like(vv)
        u[mv] = vv[mv] / sp[a:b][mv, None]
        idx = np.where(mv, np.arange(len(vv)), -1)
        idx = np.maximum.accumulate(idx)
        first = int(np.argmax(mv))
        idx[idx < 0] = first
        out[a:b] = -G0 * mu_k * N * u[idx]
    return out


def run_one(ref: Dict, hand_key: str, config: str, preds: Dict[str, Dict], stage=None, ctl_over: Optional[Dict] = None,
            paper=None, seed_key: str = "", keep: bool = False, controller: Optional[str] = None,
            hand_extra: Optional[Dict] = None) -> Dict:
    """Execute one accepted reference by moving the page; returns the five-bar's metrics and the derivative check."""
    from handwriting import params as PR
    from . import plant as PP
    writer_conv, hand_over, N, ctl_name = CONFIGS[config]
    ctl_name = controller or ctl_name
    stage = stage or stage_for(hand_key)
    g = stage.group_delay()
    tr, phase = np.asarray(ref["t"], float), np.asarray(ref["phase"]).astype(str)
    dur = float(tr[-1]) + PRE_S + POST_S
    t = np.arange(0.0, dur, DT)
    Ts = 5e-4
    n_ticks = int(np.ceil(len(t) / 20)) + 1
    tick_t = np.arange(n_ticks) * Ts
    # the reference on the plant clock (shifted by the pre-roll), held before and after
    r_abs, v_ref, a_ref = resample(ref, tick_t - PRE_S)
    r_tick = r_abs - np.asarray(ref["xy"])[0]
    idx = np.clip(np.searchsorted(tr, tick_t - PRE_S, side="right") - 1, 0, len(tr) - 1)
    ph_tick = phase[idx]
    inside = (tick_t >= PRE_S) & (tick_t <= PRE_S + float(tr[-1]))
    req = np.where(inside, ph_tick == "ink", False)
    lift_cmd = np.where(inside, np.isin(ph_tick, ["lower", "ink"]), False).astype(float)
    contact_phase = np.where(inside, np.isin(ph_tick, ["lower", "ink", "lift"]), False)
    # page motion that writes the word under a still pen: offset = -(r - r0); the coarse stage follows it with the
    # reference's analytic velocity and acceleration as feedforward
    off, offv, offa = -r_tick, -v_ref, -a_ref
    # hand (HW1) and pen
    hand = PR.Hand.from_config(**hand_over, **(hand_extra or {}))
    writing = PR.Writing(N=N)
    pref, trem, meta = hand_path(t, hand_key, seed_key or ref["writer"] + ref["text"])
    vref = np.gradient(pref, DT, axis=0)
    cls = HANDS[hand_key][0]
    pk = "tremor" if cls is not None else "calm"
    drag_on, scale = CONTROLLERS[ctl_name]
    b, a = PP.hand_compliance(hand, CM.PEN_MASS_HW1, Ts=Ts, scale=scale)
    G0 = float(b.sum() / a.sum())
    loop = ctl_name.startswith("ink_loop")
    uff = friction_feedforward(v_ref, contact_phase, G0, writing.mu_ball, writing.N) if loop else None
    ctl = PP.Control(mode=1, cam_hz=CAMERA["cam_hz"], cam_latency=CAMERA["cam_latency"], cam_noise=CAMERA["noise"],
                     ar_coef=np.asarray(preds[pk]["coef"]), horizon=g, lift_mode=1, drag=drag_on, drag_b=b, drag_a=a,
                     ink_ki=INK_KI if loop else 0.0)
    for k, v in (ctl_over or {}).items():
        setattr(ctl, k, v)
    tip0 = pref[0]
    ref_ink = np.column_stack([r_tick + tip0, req.astype(float)])
    pr = PP.run(pref, vref, np.ones(len(t)), DT, hand=hand, writing=writing, pen_mass=CM.PEN_MASS_HW1,
                stage=stage, paper=paper, ctl=ctl, writer=writer_conv, trem=trem,
                tgt_tick=np.tile(tip0, (n_ticks, 1)), off_tick=off, offv_tick=offv, offa_tick=offa,
                cref_tick=off, cvel_tick=offv, cacc_tick=offa, lift_cmd=lift_cmd, ref_ink=ref_ink, uff_tick=uff,
                seed=CM.h("acc-run", seed_key or ref["writer"], ref["text"], hand_key, config, ctl_name) % (2 ** 31),
                rec_hz=2000.0)
    m = metrics(pr, r_tick + tip0, req, ph_tick, tick_t)
    m.update({"writer": ref["writer"], "text": ref["text"], "hand": hand_key, "config": config,
              "writer_convention": writer_conv, "controller": ctl_name, "normal_force_N": N, "predictor": pk,
              "fine_servo_hz": stage.servo_hz, "hand_meta": meta, "hand_compliance_mm_per_N": G0 * 1e3 / scale,
              "duration_s": float(tr[-1]), "stage_group_delay_s": g})
    if keep:
        m["_trace"] = {"t": pr.t, "ink": pr.ink, "page": pr.page, "tip": pr.tip, "contact": pr.contact,
                       "ref": np.column_stack([np.interp(pr.t, tick_t, r_tick[:, i] + tip0[i]) for i in range(2)]),
                       "req": np.interp(pr.t, tick_t, req.astype(float)) > 0.5}
    return m


def _derivs(x: np.ndarray, dt: float):
    v = np.diff(x, axis=0) / dt
    a = np.diff(v, axis=0) / dt
    j = np.diff(a, axis=0) / dt
    return np.linalg.norm(v, axis=1), np.linalg.norm(a, axis=1), np.linalg.norm(j, axis=1)


def _lp(x: np.ndarray, fs: float, fc: float = LP_HZ) -> np.ndarray:
    from scipy.signal import butter, sosfiltfilt
    return sosfiltfilt(butter(4, fc, fs=fs, output="sos"), x, axis=0)


def metrics(pr, ref_xy: np.ndarray, req_tick: np.ndarray, ph_tick: np.ndarray, tick_t: np.ndarray) -> Dict:
    """The five-bar's measures on the platen run (recorded at 2 kHz = the 0.5 ms step of the five-bar's check)."""
    t = pr.t
    dt = float(t[1] - t[0])
    k = np.clip(np.round(t / 5e-4).astype(int), 0, len(tick_t) - 1)
    req = req_tick[k]
    ph = ph_tick[k]
    ref = ref_xy[k]
    ink = pr.ink
    con = pr.contact > 0.5
    err = np.linalg.norm(ink - ref, axis=1)
    air = np.isin(ph, ["air", "transfer"])
    step = np.r_[0.0, np.linalg.norm(np.diff(ink, axis=0), axis=1)]
    refused = bool(np.any(pr["abort"] > 0.5))
    t_ref = float(t[np.argmax(pr["abort"] > 0.5)]) if refused else None
    both = con & req
    out = {"ink_coverage_fraction": float(np.sum(both) / max(np.sum(req), 1)),
           "actual_requested_ink_rms_error_mm": float(np.sqrt(np.mean(err[both] ** 2)) * 1e3) if both.any() else None,
           "actual_requested_ink_max_error_mm": float(np.max(err[both]) * 1e3) if both.any() else None,
           "air_phase_ink_path_mm": float(np.sum(step[air & con]) * 1e3),
           "extra_ink_path_mm": float(np.sum(step[con & ~req]) * 1e3),
           "extra_ink_samples_share": float(np.mean(con & ~req)),
           "extra_ink_spread_mm": float(np.max(err[con & ~req]) * 1e3) if (con & ~req).any() else 0.0,
           "refused": refused, "refusal_time_s": t_ref,
           "fine_stop_hits": int(np.sum(np.diff(np.r_[0, (pr["stop"] > 0.5).astype(int)]) == 1)),
           "fine_travel_max_mm": float(np.max(np.hypot(pr["fx"], pr["fy"])) * 1e3),
           "coarse_travel_max_mm": float(np.max(np.hypot(pr["cx"], pr["cy"])) * 1e3),
           "fine_force_max_N": float(np.max(np.hypot(pr["Ffx"], pr["Ffy"]))),
           "coarse_force_max_N": float(np.max(np.hypot(pr["Fcx"], pr["Fcy"]))),
           "ball_drag_max_N": float(np.max(np.hypot(pr["Fbx"], pr["Fby"])))}
    out["engineering_complete"] = bool((not refused) and out["fine_stop_hits"] == 0 and
                                       out["ink_coverage_fraction"] >= 0.98 and
                                       out["actual_requested_ink_rms_error_mm"] is not None and
                                       out["actual_requested_ink_rms_error_mm"] <= 0.10 and
                                       out["air_phase_ink_path_mm"] <= 0.02)
    # derivative check (the five-bar's convention: adjacent differences at the stored 0.5 ms step)
    fs = 1.0 / dt
    der = {}
    for name, x in (("ink_on_page", ink), ("page", pr.page), ("tip", pr.tip)):
        v, a, j = _derivs(x, dt)
        va, aa, ja = _derivs(_lp(x, fs), dt)
        m_ink = both[3:] if name == "ink_on_page" else np.ones(len(j), bool)
        der[name] = {"max_speed_mm_s": float(v.max() * 1e3), "max_acc_m_s2": float(a.max()),
                     "max_jerk_m_s3": float(j.max()),
                     "max_acc_requested_ink_m_s2": float(a[2:][m_ink[:len(a) - 2]].max()) if m_ink.any() else None,
                     "max_jerk_requested_ink_m_s3": float(j[m_ink].max()) if m_ink.any() else None,
                     "passes_both": bool(a.max() <= ACC_LIM and j.max() <= JERK_LIM),
                     "lp30_max_acc_m_s2": float(aa.max()), "lp30_max_jerk_m_s3": float(ja.max()),
                     "lp30_passes_both": bool(aa.max() <= ACC_LIM and ja.max() <= JERK_LIM)}
    out["derivatives"] = der
    return out


# ------------------------------------------------------------------ the batch
def plan(quick: bool) -> Dict:
    hands = ["still", "sev_PD"] if quick else [h for h in HANDS if h != "cradle"]
    conds = [(c, h) for c in (["firm_ideal", "proposed"] if quick else
                              ["firm_ideal", "relaxed_naive", "relaxed_ink_loop", "proposed"]) for h in hands]
    conds.append(("cradle", "cradle"))
    return {"texts": ["se"] if quick else ["se", "library"], "conditions": conds,
            "n_writers": 2 if quick else 20, "stage": STAGE_VARIANT, "camera": CAMERA, "pre_s": PRE_S,
            "lift_s": 0.040, "supervisor": {"abort_err_mm": 0.20, "abort_t_s": 0.010}, "ink_ki": INK_KI,
            "calm_servo_hz": CALM_SERVO_HZ, "tremor_servo_hz": TREMOR_SERVO_HZ,
            "configs": {k: {"writer_convention": v[0], "hand": v[1], "normal_force_N": v[2], "controller": v[3]}
                        for k, v in CONFIGS.items()},
            "criteria": {"coverage": 0.98, "rms_mm": 0.10, "air_ink_mm": 0.02, "acc_m_s2": ACC_LIM,
                         "jerk_m_s3": JERK_LIM}}


def references(quick: bool) -> Dict[str, List[Dict]]:
    P = plan(quick)
    refs = {"se": se_references()[:P["n_writers"]]}
    if "library" in P["texts"]:
        refs["library"] = [r for r in library_references(quick) if "t" in r][:P["n_writers"]]
    return refs


def run_batch(quick: bool = False, log=CM.log) -> List[str]:
    P = plan(quick)
    d = CM.cache_dir(quick, "accepted")
    preds = predictors(quick)
    refs = references(quick)
    done = []
    for text in P["texts"]:
        for cfg, hk in P["conditions"]:
            p = d / f"{text}_{cfg}_{hk}.json"
            if p.exists():
                done.append(p.name)
                continue
            t0 = time.time()
            rows = [run_one(ref, hk, cfg, preds) for ref in refs[text]]
            CM.jdump(p, {"text": text, "config": cfg, "hand": hk, "rows": rows, "_elapsed_s": time.time() - t0})
            s = summarize(rows)
            log(f"[accepted] {text} {cfg} {hk}: complete {s['engineering_complete']}/{s['n']}, refused {s['refused']}, "
                f"coverage {s['median_coverage']:.3f}, RMS {s['median_rms_mm']:.3f} mm, ink acc/jerk pass "
                f"{s['ink_passes_both']}/{s['n']} (30 Hz: {s['ink_lp30_passes_both']}) ({time.time() - t0:.0f} s)")
            done.append(p.name)
    return done


SENS = {   # accepted-mode sensitivity (text 'se', the proposed configuration unless stated); name: (config, overrides)
    "lift_200ms": ("proposed", {"ctl": {"lift_up": 0.200, "lift_down": 0.200}}),
    "camera_noise_30um": ("proposed", {"ctl": {"cam_noise": 30e-6}}),
    "camera_latency_12ms": ("proposed", {"ctl": {"cam_latency": 12e-3}}),
    "model_x0.7": ("proposed", {"controller": "ink_loop_model_x0.7"}),
    "model_x1.3": ("proposed", {"controller": "ink_loop_model_x1.3"}),
    "decoupled_only": ("proposed", {"controller": "decoupled_only"}),
    "proposed_naive": ("proposed", {"controller": "naive"}),
    "firm_N1.0": ("proposed", {"N": 1.0}),
    "medium_grip_N0.5": ("proposed", {"hand": {"K_grip": 575.0, "k_arm": 1000.0, "b_arm": 15.0}}),
    "relaxed_N0.5": ("proposed", {"hand": {"K_grip": 575.0, "k_arm": 170.0, "b_arm": 11.0}}),
    "relaxed_N0.3": ("proposed", {"hand": {"K_grip": 575.0, "k_arm": 170.0, "b_arm": 11.0}, "N": 0.3}),
    "slip_hand_on_paper": ("proposed", {"paper": {"rigid": False, "N_hold": 7.5, "N_hand": 2.0}}),
}
SENS_HANDS = ("still", "mod_PD", "sev_ET")


def run_sensitivity(quick: bool = False, log=CM.log) -> List[str]:
    from . import plant as PP
    d = CM.cache_dir(quick, "accepted_sens")
    preds = predictors(quick)
    refs = references(quick)["se"]
    names = list(SENS)[:2] if quick else list(SENS)
    hands = SENS_HANDS[:1] if quick else SENS_HANDS
    done = []
    for name in names:
        cfg, ov = SENS[name]
        for hk in hands:
            p = d / f"se_{name}_{hk}.json"
            if p.exists():
                done.append(p.name)
                continue
            t0 = time.time()
            saved = CONFIGS[cfg]
            try:
                if "N" in ov or "hand" in ov:
                    wc, hov, N, ctl_name = saved
                    CONFIGS[cfg] = (wc, ov.get("hand", hov), ov.get("N", N), ctl_name)
                paper = PP.Paper(**ov["paper"]) if "paper" in ov else None
                rows = [run_one(ref, hk, cfg, preds, ctl_over=ov.get("ctl"), paper=paper,
                                controller=ov.get("controller")) for ref in refs]
            finally:
                CONFIGS[cfg] = saved
            CM.jdump(p, {"text": "se", "variant": name, "config": cfg, "overrides": ov, "hand": hk, "rows": rows,
                         "_elapsed_s": time.time() - t0})
            s = summarize(rows)
            log(f"[accepted-sens] {name} {hk}: complete {s['engineering_complete']}/{s['n']}, refused {s['refused']}, "
                f"RMS {s['median_rms_mm']:.3f} mm ({time.time() - t0:.0f} s)")
            done.append(p.name)
    return done


def summarize(rows: List[Dict]) -> Dict:
    rms = [r["actual_requested_ink_rms_error_mm"] for r in rows if r["actual_requested_ink_rms_error_mm"] is not None]
    der = lambda name, key: [r["derivatives"][name][key] for r in rows]      # noqa: E731
    return {"n": len(rows), "engineering_complete": int(sum(r["engineering_complete"] for r in rows)),
            "refused": int(sum(r["refused"] for r in rows)),
            "median_coverage": float(np.median([r["ink_coverage_fraction"] for r in rows])),
            "median_rms_mm": float(np.median(rms)) if rms else float("nan"),
            "max_rms_mm": float(np.max(rms)) if rms else float("nan"),
            "median_air_ink_mm": float(np.median([r["air_phase_ink_path_mm"] for r in rows])),
            "median_extra_ink_mm": float(np.median([r["extra_ink_path_mm"] for r in rows])),
            "median_extra_ink_spread_mm": float(np.median([r.get("extra_ink_spread_mm", 0.0) for r in rows])),
            "max_extra_ink_spread_mm": float(np.max([r.get("extra_ink_spread_mm", 0.0) for r in rows])),
            "fine_stop_words": int(sum(r["fine_stop_hits"] > 0 for r in rows)),
            "ink_passes_both": int(sum(der("ink_on_page", "passes_both"))),
            "ink_lp30_passes_both": int(sum(der("ink_on_page", "lp30_passes_both"))),
            "page_passes_both": int(sum(der("page", "passes_both"))),
            "page_lp30_passes_both": int(sum(der("page", "lp30_passes_both"))),
            "ink_max_acc_m_s2": float(np.max(der("ink_on_page", "max_acc_m_s2"))),
            "ink_max_jerk_m_s3": float(np.max(der("ink_on_page", "max_jerk_m_s3"))),
            "ink_median_peak_acc_m_s2": float(np.median(der("ink_on_page", "max_acc_m_s2"))),
            "ink_median_peak_jerk_m_s3": float(np.median(der("ink_on_page", "max_jerk_m_s3"))),
            "ink_lp30_max_acc_m_s2": float(np.max(der("ink_on_page", "lp30_max_acc_m_s2"))),
            "ink_lp30_max_jerk_m_s3": float(np.max(der("ink_on_page", "lp30_max_jerk_m_s3"))),
            "page_max_acc_m_s2": float(np.max(der("page", "max_acc_m_s2"))),
            "page_max_jerk_m_s3": float(np.max(der("page", "max_jerk_m_s3"))),
            "page_lp30_max_acc_m_s2": float(np.max(der("page", "lp30_max_acc_m_s2"))),
            "page_lp30_max_jerk_m_s3": float(np.max(der("page", "lp30_max_jerk_m_s3"))),
            "tip_max_speed_mm_s": float(np.max(der("tip", "max_speed_mm_s"))),
            "fine_force_max_N": float(np.max([r["fine_force_max_N"] for r in rows])),
            "coarse_force_max_N": float(np.max([r["coarse_force_max_N"] for r in rows])),
            "fine_travel_max_mm": float(np.max([r["fine_travel_max_mm"] for r in rows])),
            "coarse_travel_max_mm": float(np.max([r["coarse_travel_max_mm"] for r in rows])),
            "ball_drag_max_N": float(np.max([r["ball_drag_max_N"] for r in rows]))}


def aggregate(quick: bool) -> Dict:
    P = plan(quick)
    d = CM.cache_dir(quick, "accepted")
    out = {"label": "SIMULATION (HW1 hand and pen + the platen stage) of the independent pass's accepted references; "
                    "UJI glyphs already used in development (not a blind test); real tremor of TUNING patients",
           "plan": P, "summary": {}, "sensitivity": {}}
    for text in P["texts"]:
        for cfg, hk in P["conditions"]:
            c = CM.jload(d / f"{text}_{cfg}_{hk}.json")
            if c:
                out["summary"][f"{text}|{cfg}|{hk}"] = summarize(c["rows"])
    ds = CM.cache_dir(quick, "accepted_sens")
    for p in sorted(ds.glob("se_*.json")):
        c = CM.jload(p)
        out["sensitivity"][f"{c['variant']}|{c['hand']}"] = summarize(c["rows"])
    out["refusal_context"] = refusal_context(quick)
    ext = {}
    for text, rr in references(quick).items():
        if not rr:
            continue
        xy = [np.asarray(r["xy"], float) for r in rr]
        ext[text] = {"n": len(rr), "max_width_mm": float(max(np.ptp(a[:, 0]) for a in xy) * 1e3),
                     "max_height_mm": float(max(np.ptp(a[:, 1]) for a in xy) * 1e3),
                     "median_width_mm": float(np.median([np.ptp(a[:, 0]) for a in xy]) * 1e3),
                     "max_duration_s": float(max(float(np.asarray(r["t"])[-1]) for r in rr)),
                     "median_duration_s": float(np.median([float(np.asarray(r["t"])[-1]) for r in rr]))}
    out["reference_extent"] = ext
    if "library" in P["texts"]:
        out["library_rejected"] = [{"writer": r["writer"], "reason": r["rejected"]}
                                   for r in library_references(quick)[:P["n_writers"]] if "t" not in r]
        out["library_rejected_text"] = ", ".join(f"{r['writer']} ({r['reason']})" for r in out["library_rejected"]) \
            or "none"
    return out


def refusal_context(quick: bool) -> Dict:
    """Where the refusals happen: the reference phase at the refusal, the time since that phase began and the phase's
    length (CALC on the SIM rows): refusals in short strokes (< 200 ms: dots and hooks) against long ones."""
    P = plan(quick)
    refs = references(quick)
    d = CM.cache_dir(quick, "accepted")
    out = {}
    for text in P["texts"]:
        byw = {r["writer"]: r for r in refs.get(text, [])}
        for cfg, hk in P["conditions"]:
            c = CM.jload(d / f"{text}_{cfg}_{hk}.json")
            if not c:
                continue
            ev = []
            for r in c["rows"]:
                if not r["refused"] or r["writer"] not in byw:
                    continue
                ref = byw[r["writer"]]
                t, ph = np.asarray(ref["t"], float), np.asarray(ref["phase"]).astype(str)
                tr = float(r["refusal_time_s"]) - PRE_S
                i = int(np.clip(np.searchsorted(t, tr, side="right") - 1, 0, len(t) - 1))
                j, k = i, i
                while j > 0 and ph[j - 1] == ph[i]:
                    j -= 1
                while k < len(ph) - 1 and ph[k + 1] == ph[i]:
                    k += 1
                ev.append({"writer": r["writer"], "phase": str(ph[i]), "ms_into_phase": (tr - t[j]) * 1e3,
                           "phase_ms": (t[k] - t[j]) * 1e3})
            if ev:
                short = [e for e in ev if e["phase"] == "ink" and e["phase_ms"] < 200.0]
                out[f"{text}|{cfg}|{hk}"] = {"refusals": len(ev), "in_short_strokes": len(short),
                                             "median_ms_into_phase": float(np.median([e["ms_into_phase"] for e in ev])),
                                             "events": ev}
    return out


def fivebar_lp30() -> Optional[Dict]:
    """The five-bar's own stored traces (read-only: the 20 unloaded feedforward words) through this study's derivative
    check: sampled at its 0.5 ms step (reproducing the published check) and after the same 30 Hz low-pass as the
    platen's secondary measure, so that both devices are compared on one definition."""
    folder = CM.GROUNDED_BATCH.parent / "grounded_words"
    files = sorted(folder.glob("*_0N_m_ff.npz"))
    if not files:
        return None
    rows = []
    for f in files:
        with np.load(f) as z:
            t, xy = np.asarray(z["t"], float), np.asarray(z["actual_xy"], float)
        dt = float(t[1] - t[0])
        _, a, j = _derivs(xy, dt)
        _, al, jl = _derivs(_lp(xy, 1.0 / dt), dt)
        rows.append({"file": f.name, "max_acc_m_s2": float(a.max()), "max_jerk_m_s3": float(j.max()),
                     "lp30_max_acc_m_s2": float(al.max()), "lp30_max_jerk_m_s3": float(jl.max()),
                     "passes_both": bool(a.max() <= ACC_LIM and j.max() <= JERK_LIM),
                     "lp30_passes_both": bool(al.max() <= ACC_LIM and jl.max() <= JERK_LIM)})
    return {"label": "CALC on the five-bar's stored SIMULATION traces (tip on the page, actual_xy)", "n": len(rows),
            "max_acc_m_s2": max(r["max_acc_m_s2"] for r in rows), "max_jerk_m_s3": max(r["max_jerk_m_s3"] for r in rows),
            "lp30_max_acc_m_s2": max(r["lp30_max_acc_m_s2"] for r in rows),
            "lp30_max_jerk_m_s3": max(r["lp30_max_jerk_m_s3"] for r in rows),
            "passes_both": int(sum(r["passes_both"] for r in rows)),
            "lp30_passes_both": int(sum(r["lp30_passes_both"] for r in rows)), "rows": rows}


def fivebar() -> Dict:
    """The grounded five-bar's published results (read-only), for the comparison table."""
    b = CM.jload(CM.GROUNDED_BATCH) or {}
    dv = CM.jload(CM.GROUNDED_DERIV) or {}
    return {"summary": b.get("summary"), "criterion": b.get("declared_engineering_criterion"),
            "derivative_check": {k: dv.get(k) for k in list(dv.keys())[:12]} if dv else None,
            "derivative_check_same_definition": fivebar_lp30(),
            "source": [str(CM.GROUNDED_BATCH.relative_to(CM.REPO_ROOT)), str(CM.GROUNDED_DERIV.relative_to(CM.REPO_ROOT))],
            "sha256": {"grounded_batch": CM.sha256_file(CM.GROUNDED_BATCH),
                       "grounded_derivative_check": CM.sha256_file(CM.GROUNDED_DERIV)}}
