r"""Task 6: shared control and arbitration - how much the pen helps, and how it hands control back.

Evidence status: SIMULATION (model HW1; synthetic learners with a passive hand) and design proposals.

The arbitration function of every assistance the pen gives has the same form (Dragan & Srinivasa 2013 policy
blending; Losey et al. 2018):

    u_nose = alpha(t) * u_assist(t)          alpha = alpha_max(mode) x c_conf x c_need x c_agree, slew-limited

  c_conf   confidence that the assistance is right: the tremor-line detector for stabilisation, the known text (1) or
           the predictor's calibrated confidence (rule 5) for guidance, 1 for known text in autowrite
  c_need   assistance as needed (Emken, Wolbrecht): grows with the user's own recent error, decays when the user does
           well (forgetting factor), so help fades with practice
  c_agree  hand-back: falls to 0 when the user persistently disagrees (distance to the assistance target beyond a
           capture radius for longer than a dwell time, T5), or pushes against the nose (force channel)
Invariants: the pen never starts a stroke (no pen-down, no assistance), never scales letters (T8), and its reach is
limited by the nose travel.

This module simulates guided practice (copying a known text) for the dysgraphia-like learners of the handwriting
study with an external guidance law that reproduces HW1's guide mode (nearest point of the matching template stroke
from the page-sensor handle position; capture gate; drop rule) but lets the gain change per letter:
  fixed_partial   gain 0.5 (the handwriting study's partial guidance)
  fixed_full      gain 1.0
  aan             per-letter gain g_{k+1} = clip(f g_k + kappa (e_k - e_tol)_+, 0, g_max): e_k is the RMS distance of
                  the learner's OWN hand path (ink minus the Hall-measured nose deflection, which guidance does not
                  change with a passive hand) of letter k to its target, in x-height units
  aan_fade        the same with a stronger forgetting factor (faster hand-back)
The learner does not learn in this model, so these runs show how much help each policy gives and what it does to the
ink during guidance, not a learning benefit.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np
from numba import njit

from . import ensure_paths

ensure_paths()
from handwriting import metrics as MT  # noqa: E402
from handwriting import params as PR  # noqa: E402
from handwriting import plant as PL  # noqa: E402
from handwriting import practice as PRC  # noqa: E402
from handwriting import tracker as TR  # noqa: E402
from fusion import sensors as S  # noqa: E402

POLICIES = {"none": None, "fixed_partial": {"kind": "fixed", "g": 0.5}, "fixed_full": {"kind": "fixed", "g": 1.0},
            "aan": {"kind": "aan", "f": 0.8, "kappa": 4.0, "e_tol": 0.10, "g_max": 1.0, "g0": 0.5},
            "aan_fade": {"kind": "aan", "f": 0.5, "kappa": 4.0, "e_tol": 0.10, "g_max": 1.0, "g0": 0.5}}


@njit(cache=True)
def _guide(tick_t, pos_t, pos_av, pos, pos_ok, con_av, con, tm, tdown, tss, tse, gain_of_stroke, cap, drop_d, drop_t, out, out_g):
    n = len(tick_t)
    Ts = tick_t[1] - tick_t[0]
    ip = 0; ic = 0
    y0 = 0.0; y1 = 0.0; have = False
    in_con = False; was = False
    cur = -1; prog = 0
    over = 0.0; dropped = 0
    ns = tss.shape[0]
    for k in range(n):
        t = tick_t[k]
        while ip < len(pos_t) and pos_av[ip] <= t:
            if pos_ok[ip] > 0.5:
                y0 = pos[ip, 0]; y1 = pos[ip, 1]; have = True
            ip += 1
        while ic < len(con_av) and con_av[ic] <= t:
            in_con = con[ic] > 0.5
            ic += 1
        c0 = 0.0; c1 = 0.0; g = 0.0
        if in_con and have:
            if not was:
                cur += 1
                dropped = 0; over = 0.0
                if cur < ns:
                    prog = tss[cur]
            if cur < ns:
                lo = tss[cur]; hi = tse[cur]
                j0 = max(lo, prog - 20); j1 = min(hi, prog + 400)
                best = 1e30; bj = prog
                for j in range(j0, j1):
                    if tdown[j] < 0.5:
                        continue
                    dx = tm[j, 0] - y0; dy = tm[j, 1] - y1
                    dd = dx * dx + dy * dy
                    if dd < best:
                        best = dd; bj = j
                prog = bj
                dist = math.sqrt(best)
                if dist > drop_d:
                    over += Ts
                else:
                    over = 0.0
                if over > drop_t:
                    dropped = 1
                gate = 1.0 if dist <= cap else ((1.5 * cap - dist) / (0.5 * cap) if dist < 1.5 * cap else 0.0)
                if dropped == 1:
                    gate = 0.0
                g = gain_of_stroke[cur] * gate
                c0 = g * (tm[prog, 0] - y0); c1 = g * (tm[prog, 1] - y1)
        was = in_con
        out[k, 0] = c0; out[k, 1] = c1
        out_g[k] = g


def streams_for(r: PL.Result, scn: PL.Scenario, pen: PR.Pen, seed: int) -> S.Streams:
    rec = TR.record(r, scn, r.info["tick_decim"])
    cfg = S.config(page="1k", comp="gyro")
    cfg.r_board = pen.r_imu
    return S.make_streams(rec, cfg, seed)


def letter_errors(su: Dict, r_none: PL.Result) -> np.ndarray:
    """Per-letter RMS distance (x-height units) of the learner's own ink (no guidance) to its target letter."""
    rows = MT.letter_rows(su["wr"], r_none, su["rec"], targets=su["targets"], target_polys=[t.strokes for t in su["tl"]])
    h = su["wr"].style.x_height_mm * 1e-3
    return np.array([(rw.get("path_rms_um", 0.0) * 1e-6 / h) if not rw.get("missing") else 0.0 for rw in rows])


def gain_schedule(pol: Dict, e: np.ndarray) -> np.ndarray:
    """Per-letter gains (causal: letter k's gain uses letters < k)."""
    n = len(e)
    if pol["kind"] == "fixed":
        return np.full(n, pol["g"])
    g = np.zeros(n)
    gk = pol["g0"]
    for k in range(n):
        g[k] = gk
        gk = float(np.clip(pol["f"] * gk + pol["kappa"] * max(e[k] - pol["e_tol"], 0.0), 0.0, pol["g_max"]))
    return g


def stroke_gains(su: Dict, g_letter: np.ndarray) -> np.ndarray:
    """Gain per template stroke (the template track's pen-down runs follow the letters' strokes in order)."""
    out = []
    for k, t in enumerate(su["tl"]):
        out.extend([g_letter[k]] * len(t.strokes))
    return np.asarray(out, float)


def run_policy(su: Dict, pol: Optional[Dict], hand: PR.Hand, pen: PR.Pen, r_none: PL.Result, st: S.Streams,
               e: np.ndarray, cap: float = 2.0e-3, drop_d: float = 2.5e-3, drop_t: float = 0.06):
    if pol is None:
        return r_none, np.zeros(len(su["tl"]))
    g_letter = gain_schedule(pol, e)
    trk = su["track"]
    tss, tse = PL.stroke_ranges(trk.pen_down.astype(float))
    gs = stroke_gains(su, g_letter)
    if len(gs) < len(tss):
        gs = np.r_[gs, np.full(len(tss) - len(gs), gs[-1] if len(gs) else 0.0)]
    n = len(st.tick_t)
    q = np.zeros((n, 2)); gg = np.zeros(n)
    _guide(st.tick_t, st.pos_t, st.pos_av, np.ascontiguousarray(st.pos), st.pos_ok, st.con_av, st.con,
           np.ascontiguousarray(trk.xy, dtype=np.float64), trk.pen_down.astype(np.float64), tss, tse,
           np.ascontiguousarray(gs[:len(tss)]), cap, drop_d, drop_t, q, gg)
    r = PL.run(su["scn"], pen, hand, ctl=PL.Controls(qext=q), seed=su["seed"])
    return r, g_letter


def evaluate_policy(su: Dict, r: PL.Result, r_none: PL.Result, g_letter: np.ndarray) -> Dict:
    ev = PRC.evaluate(su, r, r_none)
    ev.pop("_rows", None)
    ev["gain_mean"] = float(np.mean(g_letter)) if len(g_letter) else 0.0
    kinds = su["plan"]["kind"]
    bad = [g for g, k in zip(g_letter, kinds) if k != "ok"]
    good = [g for g, k in zip(g_letter, kinds) if k == "ok"]
    ev["gain_on_malformed"] = float(np.mean(bad)) if bad else None
    ev["gain_on_wellformed"] = float(np.mean(good)) if good else None
    return ev


def job(j: Dict) -> Dict:
    hand = PR.Hand.from_config()
    pen = PR.rev_h()
    rows = []
    for seed in j["seeds"]:
        su = PRC.setup(j["writer"], seed, "dysgraphia", hand, pen)
        r_none = PRC.run_condition(su, "none", hand, pen, None)
        st = streams_for(r_none, su["scn"], pen, 90_000 + 100 * j["writer"] + seed)
        e = letter_errors(su, r_none)
        res = {}
        for name, pol in POLICIES.items():
            r, g = run_policy(su, pol, hand, pen, r_none, st, e)
            res[name] = evaluate_policy(su, r, r_none, g)
        # the plant's own guide mode at 0.5 (the handwriting study's partial guidance) as a check of the external law
        r_chk = PRC.run_condition(su, "nose_partial", hand, pen, None)
        res["check_plant_partial"] = evaluate_policy(su, r_chk, r_none, np.full(len(su["tl"]), 0.5))
        rows.append({"writer": j["writer"], "seed": seed, "res": res, "letter_err_xh": e.tolist(), "kinds": su["plan"]["kind"]})
    return {"writer": j["writer"], "rows": rows}
