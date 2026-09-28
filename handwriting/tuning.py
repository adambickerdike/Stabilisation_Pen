"""Design choices checked on TUNING data only (aiguide writers >= 100, seeds >= 300) (SIMULATION, model HW1).

Each check states its rule before its result; the test writers 0-5 and seeds 200-203 are never used here.
  akf_horizon     add the tip servo's group delay to the AKF prediction horizon? (rule: keep if it does not raise the
                  mean ink error at 8-10 Hz, 1 mm, for both tip modules)
  gating          tip authority on while hovering (<= 2 mm) or only in contact (P1 convention)? (rule: the lower
                  oracle ink error; the tracker case is reported)
  stroke_match    guidance search restricted to the matching template stroke vs the nearest-point search of the M1/P1
                  guided core (rule: lower target error without lower letter recognition, averaged over both learners)
  board_damping   D of the board law at K = 400 N/m, among 0, 2, 4, 8 N s/m (rule: highest mean letter recognition)
  size_tau        size-assist anchor time constant among 0.2, 0.4, 0.8 s (rule: highest recognition at x1.35; ties to
                  the longer constant); the default 0.4 s was set before this check
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from . import ensure_paths
from . import metrics as MT
from . import params as PR
from . import plant as PL
from . import tracker as TR
from . import writers as W

ensure_paths()


def _err(r, scn):
    return MT.aligned_error_um(r, scn)


def akf_horizon_and_gating(writers=(100, 101), seed=300) -> Dict:
    hand = PR.Hand.from_config()
    trk = PR.akf_ship()
    rows = []
    for w in writers:
        wr = W.writer(w).write(W.ET_SENTENCE, dt=W.SIM_DT, seed=2000 + w)
        s0 = PL.scenario_from_written(wr, None)
        for pen in (PR.pencil_p0(), PR.rev_h()):
            hp = PL.adapted_path(s0.intended, s0.dt, pen, hand)
            rc = PL.run(PL.with_hand_path(s0, hp), pen, hand)
            for f0 in (8.0, 10.0):
                d = W.tremor_path(s0.t, f0, 1.0e-3, seed, w)
                sc = PL.with_hand_path(s0, hp, d)
                rn = PL.run(sc, pen, hand)
                Ts, nt = rn.info["Ts"], rn.info["n_ticks"]
                qo = TR.oracle_command(rn, rc, pen, nt, Ts)
                row = {"writer": w, "pen": pen.key, "f0": f0, "neutral_um": _err(rn, sc),
                       "oracle_hover_um": _err(PL.run(sc, pen, hand, ctl=PL.Controls(qext=qo)), sc),
                       "oracle_contact_um": _err(PL.run(sc, pen, hand, ctl=PL.Controls(qext=qo, gating="contact")), sc)}
                for hc in (True, False):
                    dh, _ = TR.akf_estimate(rn, sc, pen, trk, 3_000_000 + 100 * w + int(f0), horizon_comp=hc)
                    row["akf_h%d_hover_um" % hc] = _err(PL.run(sc, pen, hand, ctl=PL.Controls(qext=-dh)), sc)
                    if hc:
                        row["akf_h1_contact_um"] = _err(PL.run(sc, pen, hand, ctl=PL.Controls(qext=-dh, gating="contact")), sc)
                rows.append(row)
    def mean(k, pen=None):
        return float(np.mean([r[k] for r in rows if pen is None or r["pen"] == pen]))
    keep_h = all(mean("akf_h1_hover_um", p) <= mean("akf_h0_hover_um", p) * 1.005 for p in ("pencil", "revH"))
    return {"rows": rows, "horizon_comp_chosen": keep_h,
            "gating_chosen": "hover" if mean("oracle_hover_um") < mean("oracle_contact_um") else "contact",
            "means": {k: mean(k) for k in rows[0] if k.endswith("_um")}}


def guidance_checks(writers=(100, 101, 102), seeds=(300, 301)) -> Dict:
    from . import practice as PRC
    hand = PR.Hand.from_config()
    pen = PR.rev_h()
    out = {}
    for prof in ("dysgraphia", "dyslexia"):
        for w in writers:
            for seed in seeds:
                su = PRC.setup(w, seed, prof, hand, pen)
                trk = su["track"]
                rn = PL.run(su["scn"], pen, hand, seed=su["seed"])
                for sm in (False, True):
                    for g in (0.5, 1.0):
                        ctl = PL.Controls(tmpl=trk.xy, tmpl_down=trk.pen_down.astype(float), g_guide=g, stroke_match=sm)
                        ev = PRC.evaluate(su, PL.run(su["scn"], pen, hand, ctl=ctl, seed=su["seed"]), rn)
                        out.setdefault(f"nose_g{g:g}_{'stroke' if sm else 'nearest'}", []).append((ev["target_err_um"], ev["letters_read_ok"]))
                for D in (0.0, 2.0, 4.0, 8.0):
                    b = PR.board()
                    b.K, b.D = 400.0, D
                    ctl = PL.Controls(board=b, board_tmpl=trk.xy, board_tmpl_down=trk.pen_down.astype(float), stroke_match=True)
                    ev = PRC.evaluate(su, PL.run(su["scn"], pen, hand, ctl=ctl, seed=su["seed"]), rn)
                    out.setdefault(f"board_K400_D{D:g}", []).append((ev["target_err_um"], ev["letters_read_ok"]))
    summ = {k: {"target_err_um": float(np.mean([v[0] for v in vals])), "letters_read_ok": float(np.mean([v[1] for v in vals]))}
            for k, vals in out.items()}
    sm_better = all(summ[f"nose_g{g:g}_stroke"]["target_err_um"] < summ[f"nose_g{g:g}_nearest"]["target_err_um"] and
                    summ[f"nose_g{g:g}_stroke"]["letters_read_ok"] >= summ[f"nose_g{g:g}_nearest"]["letters_read_ok"] - 0.01
                    for g in (0.5, 1.0))
    bestD = max((0.0, 2.0, 4.0, 8.0), key=lambda D: summ[f"board_K400_D{D:g}"]["letters_read_ok"])
    return {"summary": summ, "stroke_match_chosen": sm_better, "board_D_chosen": bestD}


def size_tau(writers=(100, 101, 102), seeds=(300,)) -> Dict:
    from . import pd_study as PD
    hand = PR.Hand.from_config()
    res = {}
    for tau in (0.2, 0.4, 0.8):
        rows = [PD.run_condition(w, s, "size_assist_1.35", hand, tau_sa=tau) for w in writers for s in seeds]
        res[str(tau)] = {"recognition": float(np.mean([r["recognition"] for r in rows])),
                         "xh_mean_mm": float(np.mean([r["xh_mean_mm"] for r in rows])),
                         "norm_jerk": float(np.mean([r["norm_jerk_median"] for r in rows]))}
    best = max(res, key=lambda k: (round(res[k]["recognition"], 3), float(k)))
    return {"candidates": res, "chosen": float(best)}


def run(quick: bool = False) -> Dict:
    if quick:
        return {"akf_horizon_and_gating": akf_horizon_and_gating(writers=(100,)),
                "guidance": guidance_checks(writers=(100,), seeds=(300,)), "size_tau": size_tau(writers=(100,)),
                "rules": __doc__}
    return {"akf_horizon_and_gating": akf_horizon_and_gating(), "guidance": guidance_checks(), "size_tau": size_tau(),
            "rules": __doc__}
