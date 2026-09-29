"""Physical completion of an ACCEPTED word, planned jointly with the hand's advance (review section 10; rule C1).
SIMULATION of kinematics only: the nib stage is assumed to track its command within the 0.5 mm reserve.

The writer has written the start of a word, the app offered completions at a pause, and the writer ACCEPTED one
(layers.WritingPlan: created only from an acceptance, fixed for its strokes).  The rest of the word is a path r(s) in
the writer's own letters (UJI test writers' real letters, session 1 = the calibration, at a 3 mm x-height, joined
with pen-up moves), placed after the letters already written.  The hand (barrel) moves as b(t); the nib offset is
q(t) = r(s(t)) - b(t) and must stay within the usable reach R_u = R - 0.5 mm.

Planner (rule C1): the nib moves only forward along r, at <= 30 mm/s and <= 2 m/s^2; it slows or waits when the next
point is out of reach; with 'letter admission' it starts a letter only when the whole letter is predicted to stay
in reach (from the hand's current velocity), so a hand-back never leaves half a letter; it lifts when the hand has
not advanced for 0.5 s and hands back after 2 s without progress, or when the hand has run past the next point by
more than R_u.

Hand behaviours (ASSUMPTIONS): 'steady' (the hand advances as fast as the writer's own writing would move it:
horizontal extent / own writing time at 30 mm/s path speed), 'slow' (x0.5), 'fast' (x1.8, the hand runs ahead),
'pause' (steady, then stops for 3 s after 40 % of the path), 'still' (the hand does not move: the review's point that
a small stage cannot draw a word around a stationary grip).
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np

from . import common as C
from . import data as D
from . import online as O

XH_M = O.XH_MM * 1e-3
V_MAX = 0.030              # m/s, nib path speed limit (LIT CON-20 median pen-down speed; rule C1)
A_MAX = 2.0                # m/s^2
RESERVE = 0.5e-3           # m, kept for tremor and tracking
DT = 0.002
BEHAVIOURS = ("steady", "slow", "fast", "pause", "still")
RADII_MM = (1.0, 2.0, 3.0, 4.0, 6.0)
POLICIES = ("pointwise", "letter_admission")


def word_path(letters: Sequence[List[np.ndarray]], gap_xh: float = 0.25, x_start: float = 0.0):
    """Join letters (strokes in x-height units) into one path in metres: points, pen flags (1 = down), letter ids."""
    pts, pen, lid = [], [], []
    cur = x_start
    for k, st in enumerate(letters):
        allp = np.vstack(st)
        x0 = float(allp[:, 0].min()); w = float(allp[:, 0].max()) - x0
        yb = float(np.percentile(allp[:, 1], 5))
        for s in st:
            s = (np.asarray(s, float) - np.array([x0, yb])) * XH_M + np.array([cur * XH_M, 0.0])
            if pts:                                   # pen-up move to the stroke start
                a, b = pts[-1][-1], s[0]
                n = max(2, int(np.hypot(*(b - a)) / 0.1e-3))
                pts.append(np.linspace(a, b, n)[1:-1] if n > 2 else np.zeros((0, 2)))
                pen.append(np.zeros(max(n - 2, 0))); lid.append(np.full(max(n - 2, 0), k))
            d = np.hypot(*np.diff(s, axis=0).T)
            L = float(d.sum())
            n = max(2, int(L / 0.05e-3) + 1)
            u = np.linspace(0, 1, n)
            cs = np.r_[0.0, np.cumsum(d)] / max(L, 1e-12)
            r = np.column_stack([np.interp(u, cs, s[:, 0]), np.interp(u, cs, s[:, 1])])
            pts.append(r); pen.append(np.ones(n)); lid.append(np.full(n, k))
        cur += w + gap_xh
    P = np.vstack([p for p in pts if len(p)])
    pen = np.concatenate(pen); lid = np.concatenate(lid)
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    return P, pen, lid, s


def hand_track(P: np.ndarray, s: np.ndarray, behaviour: str, T: float, rng) -> Tuple[np.ndarray, float]:
    """b(t) on a DT grid for T seconds; returns (B, v_h).  The hand starts where the stage is centred on the path's
    first point, and advances horizontally."""
    own_time = s[-1] / V_MAX
    v_h = (P[:, 0].max() - P[0, 0]) / max(own_time, 1e-6)
    n = int(T / DT) + 1
    t = np.arange(n) * DT
    k = {"steady": 1.0, "slow": 0.5, "fast": 1.8, "pause": 1.0, "still": 0.0}[behaviour]
    v = np.full(n, k * v_h)
    if behaviour == "pause":
        t_stop = 0.4 * own_time
        v[(t >= t_stop) & (t < t_stop + 3.0)] = 0.0
    v *= 1 + 0.15 * np.sin(2 * np.pi * 1.3 * t + rng.uniform(0, 6.3))          # uneven advance (ASSUMPTION)
    x = P[0, 0] + np.cumsum(v) * DT
    y = np.full(n, P[:, 1].mean()) + 0.2e-3 * np.sin(2 * np.pi * 0.7 * t + rng.uniform(0, 6.3))
    return np.column_stack([x, y]), v_h


def _letter_end(lid: np.ndarray) -> Dict[int, int]:
    ends = {}
    for i, L in enumerate(lid):
        ends[int(L)] = i
    return ends


def simulate(P, pen, lid, s, B, R_mm: float, policy: str) -> Dict:
    """One accepted completion.  The pen-down nib point must be within R_u of the hand; if it falls out of reach
    mid-letter the pen is forced to lift (an ink gap: a defect).  'pointwise' starts a letter as soon as its first
    point is in reach; 'letter_admission' only when the whole letter is predicted to stay in reach (hand velocity
    averaged over 0.3 s), otherwise it waits pen-up, or hands back at once if the hand is ahead (waiting cannot help)."""
    Ru = R_mm * 1e-3 - RESERVE
    n_t = len(B)
    ends = _letter_end(lid)
    si, sv, s_pos = 0, 0.0, 0.0
    started, finished = set(), set()
    defects = lifts = 0
    stall = 0.0
    lifted_now = False
    q_max = 0.0
    state = "writing"
    hvx = np.zeros(n_t)
    k_t = 0
    for k_t in range(1, n_t):
        t = k_t * DT
        b = B[k_t]
        hv = (B[k_t] - B[k_t - 1]) / DT
        hvx[k_t] = hv[0]
        hvs = np.array([hvx[max(1, k_t - 150):k_t + 1].mean(), 0.0])
        L = int(lid[si])
        if L not in started:
            if P[si, 0] < b[0] - Ru:
                state = "handed_back_ran_ahead"
                break
            if policy == "letter_admission":
                idx = np.arange(si, ends[L] + 1)
                ts = (s[idx] - s[si]) / V_MAX
                pred = b[None, :] + ts[:, None] * hvs[None, :]
                d = np.hypot(*(P[idx] - pred).T)
                ok = bool(np.all(d[pen[idx] > 0.5] <= Ru))
                if not ok:
                    behind = np.any((P[idx, 0] - pred[:, 0] < -Ru) & (pen[idx] > 0.5))
                    stall += DT
                    if behind and hvs[0] > 0.2e-3:
                        state = "handed_back_ran_ahead"
                        break
                    if stall > 2.0:
                        state = "handed_back_no_progress"
                        break
                    continue
            elif np.hypot(*(P[si] - b)) > Ru:
                stall += DT
                if stall > 2.0:
                    state = "handed_back_no_progress"
                    break
                continue
            started.add(L)
            stall = 0.0
        # advance: the largest speed whose next point stays in reach of the hand one step ahead
        v_hi = min(V_MAX, sv + A_MAX * DT)
        moved = False
        for v in (v_hi, 0.75 * v_hi, 0.5 * v_hi, 0.25 * v_hi):
            sp = min(s_pos + v * DT, s[-1])
            j = min(max(int(np.searchsorted(s, sp, side="right")) - 1, si), len(s) - 1)
            if pen[j] < 0.5 or np.hypot(*(P[j] - (b + hv * DT))) <= Ru:
                sv, si, s_pos, moved = v, j, sp, True
                break
        if not moved:
            sv = 0.0
            stall += DT
            if pen[si] > 0.5 and np.hypot(*(P[si] - b)) > Ru and not lifted_now:
                defects += 1                          # the hand moved the reach away from a pen-down point
                lifted_now = True
                lifts += 1
            elif stall > 0.5 and not lifted_now:
                lifted_now = True
                lifts += 1
                if pen[si] > 0.5 and si != ends[L]:
                    defects += 1                      # a stall lift inside a letter leaves a gap
            if stall > 2.0:
                state = "handed_back_no_progress"
                break
            continue
        stall = 0.0
        lifted_now = False
        if pen[si] > 0.5:
            q_max = max(q_max, float(np.hypot(*(P[si] - b))))
        for Lq in list(started - finished):
            if si >= ends[Lq]:
                finished.add(Lq)
        if s_pos >= s[-1] - 1e-12:
            si = len(s) - 1
            state = "done"
            finished |= started
            break
    partial = len(started - finished)
    return {"state": state, "time_s": k_t * DT, "own_time_s": s[-1] / V_MAX, "share_written": s[si] / max(s[-1], 1e-12),
            "q_max_mm": q_max * 1e3, "lifts": lifts, "defects": defects, "letters": int(len(np.unique(lid))),
            "letters_done": len(finished), "partial_letters": partial}


def completions(n: int, seed: int, sentences: Sequence[str]) -> List[Tuple[str, int]]:
    """(word, letters already written): words of >= 5 letters from held-out sentences, accepted after 40-60 %."""
    rng = np.random.default_rng(seed)
    words = []
    for i in rng.permutation(len(sentences)):
        for w in sentences[i].lower().split():
            w = "".join(c for c in w if c in O.LETTERS)
            if len(w) >= 5:
                words.append(w)
        if len(words) >= 4 * n:
            break
    out = []
    for w in words[:n]:
        k = int(round(len(w) * rng.uniform(0.4, 0.6)))
        out.append((w, max(2, min(k, len(w) - 1))))
    return out


def run(quick: bool) -> Dict:
    from aiguide import corpus as ACO
    t0 = time.time()
    letters, _ = D.load_uji()
    xh = O.writer_xheights(letters)
    bank = {}
    for L in letters:
        if O.split_of(L.writer) == "test" and int(L.rep) == 1:
            bank[(L.writer, L.char)] = [np.asarray(s, float) / xh[L.writer] for s in L.strokes]
    writers = sorted({w for w, _ in bank})[: 4 if quick else 20]
    comps = completions(20 if quick else 100, seed=51, sentences=list(ACO.make_splits().test))
    rng = np.random.default_rng(52)
    rows = []
    for ci, (word, k) in enumerate(comps):
        w = writers[ci % len(writers)]
        rest = word[k:]
        lets = [bank.get((w, c)) for c in rest]
        if any(x is None for x in lets):
            continue
        P, pen, lid, s = word_path(lets)
        for beh in BEHAVIOURS:
            B, v_h = hand_track(P, s, beh, T=s[-1] / V_MAX * 4 + 6.0, rng=rng)
            for R in RADII_MM:
                for pol in POLICIES:
                    r = simulate(P, pen, lid, s, B, R, pol)
                    r.update({"word": word, "written": k, "rest": rest, "writer": w, "behaviour": beh, "R_mm": R,
                              "policy": pol, "path_mm": s[-1] * 1e3,
                              "extent_mm": float(P[:, 0].max() - P[:, 0].min()) * 1e3, "v_hand_mm_s": v_h * 1e3})
                    rows.append(r)
    table = {}
    for beh in BEHAVIOURS:
        for R in RADII_MM:
            for pol in POLICIES:
                sel = [r for r in rows if r["behaviour"] == beh and r["R_mm"] == R and r["policy"] == pol]
                if not sel:
                    continue
                done = [r for r in sel if r["state"] == "done"]
                table[f"{beh}|{R:g}|{pol}"] = {
                    "n": len(sel), "completed_share": len(done) / len(sel),
                    "handed_back_share": float(np.mean([r["state"].startswith("handed_back") for r in sel])),
                    "partial_letters_per_100": 100.0 * sum(r["partial_letters"] for r in sel) / len(sel),
                    "time_ratio_median_done": float(np.median([r["time_s"] / r["own_time_s"] for r in done])) if done else float("nan"),
                    "q_max_mm_p95": float(np.percentile([r["q_max_mm"] for r in sel], 95)),
                    "lifts_per_completion": float(np.mean([r["lifts"] for r in sel])),
                    "ink_gaps_per_100": 100.0 * sum(r["defects"] for r in sel) / len(sel),
                    "letters_written_share": sum(r["letters_done"] for r in sel) / max(sum(r["letters"] for r in sel), 1),
                    "share_written_mean": float(np.mean([r["share_written"] for r in sel]))}
    ext = [r["extent_mm"] for r in rows if r["behaviour"] == "steady" and r["R_mm"] == 6.0 and r["policy"] == POLICIES[0]]
    out = {"rules": "C1_complete", "v_max_mm_s": V_MAX * 1e3, "a_max": A_MAX, "reserve_mm": RESERVE * 1e3,
           "completions": len(ext), "extent_mm_median": float(np.median(ext)) if ext else float("nan"),
           "extent_mm_p90": float(np.percentile(ext, 90)) if ext else float("nan"),
           "v_hand_mm_s_median": float(np.median([r["v_hand_mm_s"] for r in rows])) if rows else float("nan"),
           "table": table, "rows": rows[:2000], "minutes": (time.time() - t0) / 60}
    C.save("plan", out, quick)
    C.log(f"[plan] {len(ext)} completions; steady hand, R 3 mm, letter admission: "
          f"{table.get('steady|3|letter_admission', {}).get('completed_share', float('nan')):.2f} completed; "
          f"still hand, R 6 mm: {table.get('still|6|letter_admission', {}).get('completed_share', float('nan')):.2f}")
    return out
