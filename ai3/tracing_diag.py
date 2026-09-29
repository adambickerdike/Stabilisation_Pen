"""Task 4a: why close tracing (steered heel wheel + nose) brings the ink to 76 um of the target letters while the letters
read fall from 92 % to 79 % (SIMULATION, model HW1-D of drive/, used read-only; the drive study's test writers 0-5,
seeds 200-203, its frozen gains results/drive/rules.json).

Per letter, on the same runs the drive study scored:
  read_ok      the app's recogniser (aiguide GlyphRecognizer in the writer's style) reads the target letter
  d_ink        RMS distance of the letter's ink to the target letter (one-sided, ink -> target; the drive study's
               'target error')
  covered      share of the target letter's path that has ink within 0.3 mm (target -> ink)
  missing      share of the target letter's path with NO ink within 1.0 mm (a part left undrawn)
  backtrack    share of the ink's path whose nearest-point position along the target runs backwards (bunching, retracing)
Counterfactual readings of the guided ink (the same recogniser):
  projected    the ink replaced by its nearest point on the target (keeps which parts are drawn and in which order)
  covered_only the drawn parts of the target, in the target's own order (removes bunching and wiggles)
  filled       the ink plus the missing target parts (drawn after the ink)
  target       the target letter itself (the recogniser's ceiling)
The app's recogniser compares letters as paths in writing order (DTW over the strokes joined in the order they were
written, pen-up jumps included), so ink that retraces, bunches or is drawn in another order can be misread although it
looks right.  A second, order-free reader (StaticReader: the pen-down ink as a picture of occupied cells, matched to the
same 26 glyphs in the writer's style by the symmetric chamfer distance) separates that from a real loss of legibility:
  read_static_ok, cf_filled_static_ok, cf_target_static_ok
Neither reader is a person; where both call a letter misread it is taken as a real loss of legibility (CALC on SIM).
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Sequence

import numpy as np
from scipy.spatial import cKDTree

from . import ensure_paths
from .common import log

ensure_paths()

CONDS = ["none", "nose_partial", "wheel_path", "nose_nogate", "wheel_path+nose"]
LABELS = {"none": "no guidance", "nose_partial": "nose, partial (0.5)", "wheel_path": "heel wheel steers (no nose)",
          "nose_nogate": "nose, full, no gate", "wheel_path+nose": "heel wheel + nose (close tracing)"}


class StaticReader:
    """Order-free reader: the letter as a static picture.  The pen-down ink (no pen-up jumps, no writing order, no
    dwell) becomes a set of occupied cells (0.02 x-height); it is matched to the 26 lower-case glyphs in the writer's
    style (the app recogniser's glyphs, x-height, width and slant, as learnt at calibration) by the symmetric chamfer
    distance (mean nearest-point distance ink -> glyph and glyph -> ink), after aligning the centroids, a scale in
    0.8-1.25 and two translation refinements (ICP).  The 6 glyphs closest at scale 1 are refined."""

    def __init__(self, h: float, width: float, slant: float, cell_rel: float = 0.02,
                 scales=(0.8, 0.9, 1.0, 1.12, 1.25), icp: int = 2, n_refine: int = 6):
        from aiguide.glyphs import GLYPH_SET, LETTERS
        self.cell = cell_rel * h
        self.scales, self.icp, self.n_refine = scales, icp, n_refine
        self.refs = {}
        for c in LETTERS:
            strokes = [np.column_stack([h * width * s[:, 0] + h * math.tan(slant) * s[:, 1], h * s[:, 1]])
                       for s in GLYPH_SET[c]]
            P = self.cloud(strokes)
            self.refs[c] = (P, cKDTree(P))

    def cloud(self, strokes: Sequence[np.ndarray]) -> np.ndarray:
        from aiguide.glyphs import resample, arclength
        pts = []
        for s in strokes:
            s = np.asarray(s, float)
            if len(s) < 2:
                continue
            L = arclength(s)[-1]
            pts.append(resample(s, max(2, int(L / (0.5 * self.cell)) + 1)) if L > 0 else s[:1])
        if not pts:
            return np.zeros((1, 2))
        P = np.unique(np.round(np.vstack(pts) / self.cell).astype(np.int64), axis=0).astype(float) * self.cell
        return P - P.mean(axis=0)

    def _fit(self, q: np.ndarray, P: np.ndarray, tP) -> float:
        best = np.inf
        for sc in self.scales:
            Q = q / sc
            t = np.zeros(2)
            for it in range(self.icp + 1):
                Qt = Q + t
                d1, j1 = tP.query(Qt)
                d2, j2 = cKDTree(Qt).query(P)
                if it < self.icp:
                    t = t + 0.5 * ((P[j1] - Qt).mean(0) + (P - Qt[j2]).mean(0))
            best = min(best, 0.5 * (float(d1.mean()) + float(d2.mean())) * math.sqrt(sc))
        return best

    def classify(self, strokes: Sequence[np.ndarray]):
        q = self.cloud(strokes)
        tq = cKDTree(q)
        coarse = {c: 0.5 * (float(np.mean(tP.query(q)[0])) + float(np.mean(tq.query(P)[0])))
                  for c, (P, tP) in self.refs.items()}
        cand = sorted(coarse, key=coarse.get)[: self.n_refine]
        d = {c: self._fit(q, *self.refs[c]) for c in cand}
        return min(d, key=d.get), d


def static_reader_for(written) -> StaticReader:
    st = written.style
    return StaticReader(st.x_height_mm * 1e-3, st.width, math.radians(st.slant_deg))


def _dense(strokes: Sequence[np.ndarray], step: float = 25e-6):
    from aiguide.glyphs import resample, arclength
    pts, sid, u = [], [], []
    tot = 0.0
    for k, s in enumerate(strokes):
        s = np.asarray(s, float)
        L = arclength(s)[-1] if len(s) > 1 else 0.0
        n = max(2, int(L / step) + 1)
        r = resample(s, n) if L > 0 else np.repeat(s[:1], 2, axis=0)
        pts.append(r); sid.append(np.full(len(r), k))
        u.append(tot + np.linspace(0.0, L, len(r)))
        tot += L
    return np.vstack(pts), np.concatenate(sid), np.concatenate(u), tot


def letter_diag(ink: np.ndarray, contact: np.ndarray, target_strokes: Sequence[np.ndarray], rec, char: str,
                srec: "StaticReader" = None) -> Dict:
    from aiguide.metrics import split_strokes
    m = contact > 0.5
    out = {"char": char}
    if m.sum() < 4:
        out["missing_letter"] = True
        return out
    T, sid, u, Ltot = _dense(target_strokes)
    tree_t = cKDTree(T)
    d, j = tree_t.query(ink[m])
    out["d_ink_um"] = float(np.sqrt(np.mean(d ** 2)) * 1e6)
    tree_i = cKDTree(ink[m])
    dt_, _ = tree_i.query(T)
    out["covered"] = float(np.mean(dt_ < 0.3e-3))
    out["missing"] = float(np.mean(dt_ > 1.0e-3))
    strokes = split_strokes(ink, m)
    strokes = [s[::10] if len(s) > 20 else s for s in strokes]
    # backtracking along the target (nearest-point arclength position of consecutive ink samples)
    back = 0.0; tot = 0.0
    for s in split_strokes(ink, m):
        if len(s) < 3:
            continue
        _, jj = tree_t.query(s)
        du = np.diff(u[jj])
        seg = np.hypot(*np.diff(s, axis=0).T)
        same = np.diff(sid[jj]) == 0
        back += float(np.sum(seg[(du < 0) & same])); tot += float(np.sum(seg))
    out["backtrack"] = back / max(tot, 1e-12)
    out["ink_len_ratio"] = tot / max(Ltot, 1e-12)
    pred, _ = rec.classify(strokes)
    out["read_as"] = pred
    out["read_ok"] = pred == char
    # counterfactuals
    proj = [T[tree_t.query(s)[1]] for s in split_strokes(ink, m) if len(s) >= 2]
    proj = [p[::10] if len(p) > 20 else p for p in proj]
    out["cf_projected_ok"] = rec.classify(proj)[0] == char if proj else False
    cov = dt_ < 0.3e-3
    runs = []
    for k in np.unique(sid):
        mk = (sid == k)
        idx = np.flatnonzero(mk & cov)
        if len(idx) < 2:
            continue
        br = np.flatnonzero(np.diff(idx) > 1)
        for a, b in zip(np.r_[0, br + 1], np.r_[br, len(idx) - 1]):
            if b - a >= 1:
                runs.append(T[idx[a]:idx[b] + 1][::4])
    out["cf_covered_only_ok"] = rec.classify(runs)[0] == char if runs else False
    miss = dt_ > 0.3e-3
    fill = list(strokes)
    for k in np.unique(sid):
        idx = np.flatnonzero((sid == k) & miss)
        if len(idx) < 2:
            continue
        br = np.flatnonzero(np.diff(idx) > 1)
        for a, b in zip(np.r_[0, br + 1], np.r_[br, len(idx) - 1]):
            if b - a >= 1:
                fill.append(T[idx[a]:idx[b] + 1][::4])
    out["cf_filled_ok"] = rec.classify(fill)[0] == char
    out["cf_target_ok"] = rec.classify([np.asarray(s) for s in target_strokes])[0] == char
    if srec is not None:
        full = split_strokes(ink, m)
        out["read_static_as"] = srec.classify(full)[0]
        out["read_static_ok"] = out["read_static_as"] == char
        out["cf_filled_static_ok"] = (out["read_static_ok"] if len(fill) == len(strokes)
                                      else srec.classify(full + fill[len(strokes):])[0] == char)
    return out


def run_case(w: int, seed: int, profile: str, conds=CONDS, keep: bool = False) -> Dict:
    from drive import scenarios as S, tune as TU
    from drive.run_study import case_mu
    rules = TU.load_rules()
    case = S.practice_case(w, seed, profile)
    su = case["su"]
    mu = case_mu(1000 * w + seed)
    ev0, r0 = S.run_practice(case, "none", TU.gains_for(rules, "none"), mu)
    srec = static_reader_for(su["wr"])
    tgt_static = [srec.classify([np.asarray(s) for s in su["tl"][k].strokes])[0] == su["targets"][k]
                  for k in range(len(su["wr"].letters))]
    res = {"writer": w, "seed": seed, "profile": profile, "conds": {}, "kinds": su["plan"]["kind"]}
    runs = {"none": r0}
    for cond in conds:
        if cond == "none":
            ev, r = ev0, r0
        else:
            ev, r = S.run_practice(case, cond, TU.gains_for(rules, cond), mu, ref=r0)
            runs[cond] = r
        rows = []
        for k, L in enumerate(su["wr"].letters):
            msk = (r.t >= L.t0 - 0.01) & (r.t <= L.t1 + 0.01)
            rows.append(letter_diag(r.ink[msk], r.contact[msk], su["tl"][k].strokes, su["rec"], su["targets"][k], srec))
            if not rows[-1].get("missing_letter"):
                rows[-1]["cf_target_static_ok"] = bool(tgt_static[k])
        res["conds"][cond] = {"target_err_um": ev["target_err_um"], "letters_read_ok": ev["letters_read_ok"],
                              "coverage": ev["coverage"], "recognised": ev["recognised"], "letters": rows}
    if keep:
        res["_runs"] = runs
        res["_su"] = su
    return res


def aggregate(cases: List[Dict], conds=CONDS) -> Dict:
    out = {}
    for prof in sorted({c["profile"] for c in cases}):
        sel = [c for c in cases if c["profile"] == prof]
        out[prof] = {}
        for cond in conds:
            rows = [L for c in sel for L in c["conds"][cond]["letters"] if not L.get("missing_letter")]
            ok = [L for L in rows if L["read_ok"]]
            bad = [L for L in rows if not L["read_ok"]]
            cell = {"letters": len(rows), "read": len(ok) / max(len(rows), 1),
                    "target_err_um_published": float(np.mean([c["conds"][cond]["target_err_um"] for c in sel])),
                    "letters_read_published": float(np.mean([c["conds"][cond]["letters_read_ok"] for c in sel])),
                    "d_ink_um_mean": float(np.mean([L["d_ink_um"] for L in rows])),
                    "covered_mean": float(np.mean([L["covered"] for L in rows])),
                    "missing_mean": float(np.mean([L["missing"] for L in rows])),
                    "backtrack_mean": float(np.mean([L["backtrack"] for L in rows])),
                    "ink_len_ratio_mean": float(np.mean([L["ink_len_ratio"] for L in rows])),
                    "misread_missing_mean": float(np.mean([L["missing"] for L in bad])) if bad else float("nan"),
                    "read_missing_mean": float(np.mean([L["missing"] for L in ok])) if ok else float("nan"),
                    "misread_with_missing_part_share": float(np.mean([L["missing"] > 0.15 for L in bad])) if bad else float("nan"),
                    "misread_d_ink_um": float(np.mean([L["d_ink_um"] for L in bad])) if bad else float("nan"),
                    "cf_projected": float(np.mean([L["cf_projected_ok"] for L in rows])),
                    "cf_covered_only": float(np.mean([L["cf_covered_only_ok"] for L in rows])),
                    "cf_filled": float(np.mean([L["cf_filled_ok"] for L in rows])),
                    "cf_target": float(np.mean([L["cf_target_ok"] for L in rows]))}
            if rows and "read_static_ok" in rows[0]:
                cell["read_static"] = float(np.mean([L["read_static_ok"] for L in rows]))
                cell["cf_filled_static"] = float(np.mean([L["cf_filled_static_ok"] for L in rows]))
                cell["cf_target_static"] = float(np.mean([L["cf_target_static_ok"] for L in rows]))
                news = []
                for c in sel:
                    a = c["conds"]["none"]["letters"]; b = c["conds"][cond]["letters"]
                    for La, Lb in zip(a, b):
                        if La.get("read_static_ok") and not Lb.get("missing_letter") and not Lb.get("read_static_ok"):
                            news.append(Lb)
                cell["newly_misread_static"] = len(news)
                if news:
                    cell["newly_misread_static_missing_mean"] = float(np.mean([L["missing"] for L in news]))
                    cell["newly_misread_static_filled_recovers"] = float(np.mean([L["cf_filled_static_ok"] for L in news]))
                # both readers agree the letter got worse (read unguided, misread guided, by both)
                both = 0
                for c in sel:
                    a = c["conds"]["none"]["letters"]; b = c["conds"][cond]["letters"]
                    for La, Lb in zip(a, b):
                        if (La.get("read_ok") and La.get("read_static_ok") and not Lb.get("missing_letter")
                                and not Lb.get("read_ok") and not Lb.get("read_static_ok")):
                            both += 1
                cell["newly_misread_both_readers"] = both
            # letters read unguided but misread under this condition: what happened to them
            newly = []
            for c in sel:
                a = c["conds"]["none"]["letters"]; b = c["conds"][cond]["letters"]
                for La, Lb in zip(a, b):
                    if La.get("read_ok") and not Lb.get("missing_letter") and not Lb.get("read_ok"):
                        newly.append(Lb)
            cell["newly_misread"] = len(newly)
            if newly:
                cell["newly_misread_missing_mean"] = float(np.mean([L["missing"] for L in newly]))
                cell["newly_misread_with_missing_part_share"] = float(np.mean([L["missing"] > 0.15 for L in newly]))
                cell["newly_misread_filled_recovers"] = float(np.mean([L["cf_filled_ok"] for L in newly]))
                cell["newly_misread_projected_recovers"] = float(np.mean([L["cf_projected_ok"] for L in newly]))
                cell["newly_misread_covered_only_recovers"] = float(np.mean([L["cf_covered_only_ok"] for L in newly]))
            out[prof][cond] = cell
    return out


def run(quick: bool, writers=(0, 1, 2, 3, 4, 5), seeds=(200, 201, 202, 203), profiles=("dysgraphia", "dyslexia")) -> Dict:
    t0 = time.time()
    if quick:
        writers, seeds, profiles = writers[:2], seeds[:1], profiles[:1]
    cases = []
    for prof in profiles:
        for w in writers:
            for s in seeds:
                cases.append(run_case(w, s, prof))
        log(f"[trace] {prof}: {len(writers) * len(seeds)} cases [{time.time() - t0:.0f} s]")
    agg = aggregate(cases)
    return {"cases": cases, "aggregate": agg, "writers": list(writers), "seeds": list(seeds), "profiles": list(profiles),
            "minutes": (time.time() - t0) / 60}
