"""Rev H tracker setting: ParEGO over the AKF's gate, cap and output parameters for the large-travel nose.

Why: the shipped set (results/opt/tracker_models/akf_ship.json) was selected on the pencil (P1, 0.1-0.5 mm tremor, 0.3 mm
travel).  Rev H has 3 mm of travel and is meant for 0.3-2 mm tremor.  The Kalman noise parameters (qj, qt, qh, qb, ra, rp)
stay at the shipped values; only the decision layer is searched: output gain g, frequency gate (f_gate, f_gate_w),
amplitude gates (a_lo, a_hi), amplitude cap (cap_k, v_slow), 2nd harmonic weight (harm), output low-pass (lp_hz),
frequency window top (wmax_hz).
Objectives (training seeds only, SEEDS['train'] and SEEDS['glyph_train']): mean 3-15 Hz ink-error ratio over 4-12 Hz x
0.3/1/2 mm on two lognormal seeds; false correction = mean closed-loop distortion of tremor-free writing (two lognormal +
two glyph seeds).  Selection rule, fixed before any test run: lowest mean band ratio among points with lognormal
distortion <= 15 um and glyph distortion <= 30 um (the tracker study's rule: 14 / 30 um), on the training data.
Evidence status: SIMULATION.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fusion import estimators as ES  # noqa: E402
from opt.touchdown import bo as BO  # noqa: E402
from sim.handpen import evaluate as HE  # noqa: E402
from sim.handpen import model as HM  # noqa: E402
from opt.inertial import revh as RH  # noqa: E402
from opt.inertial import scen as SC  # noqa: E402
from opt.inertial import tracker as TK  # noqa: E402

OUT = os.path.join(ROOT, "results", "opt", "_cache")
LOG = os.path.join(OUT, "inertial_tracker_parego.jsonl")
SPACE = BO.Space({"g": (0.8, 3.0), "f_gate": (3.0, 7.0), "f_gate_w": (0.5, 4.0), "a_lo": (5e-6, 1.5e-4), "a_hi": (5e-5, 8e-4),
                  "cap_k": (0.0, 6.0), "v_slow": (0.004, 0.06), "harm": (0.0, 1.0), "lp_hz": (20.0, 75.0), "wmax_hz": (12.0, 16.0)},
                 log=("a_lo", "a_hi", "v_slow"))
F0S = (4.0, 6.0, 8.0, 10.0, 12.0)
AMPS = (0.3e-3, 1.0e-3, 2.0e-3)


class Tuner:
    def __init__(self, seeds=(300, 301), glyph_seeds=(330, 331), quick=False):
        self.d = RH.RevH()
        self.cfg = RH.config_B(self.d)
        self.seeds = seeds[:1] if quick else seeds
        self.glyph = glyph_seeds[:1] if quick else glyph_seeds
        self.f0s = (6.0, 10.0) if quick else F0S
        self.amps = (0.3e-3, 2.0e-3) if quick else AMPS
        self.cache = {}

    def _pair(self, seed, f0, amp, writer="lognormal"):
        k = (seed, f0, amp, writer)
        if k not in self.cache:
            tr = SC.tremor(f0, amp) if amp > 0 else None
            sc = SC.get(seed, tr, writer)
            sc0 = SC.get(seed, None, writer)
            ref = HM.run(sc0, self.cfg, rec_hz=TK.REC_HZ)
            un = ref if amp == 0 else HM.run(sc, self.cfg, rec_hz=TK.REC_HZ)
            st = TK.make_streams(un, sc, seed=seed + 7000, body="pen")
            self.cache[k] = (sc, ref, un, HE.compare(un, ref) if amp > 0 else None, st)
        return self.cache[k]

    def run_one(self, prm, seed, f0, amp, writer="lognormal"):
        sc, ref, un, mu, st = self._pair(seed, f0, amp, writer)
        p = dict(TK.ship_params()); p.update(prm)
        dh, info = ES.akf(st, p)
        n = len(sc.t)
        r = HM.run(sc, self.cfg.replace(stage=True, stage_src=1), clean=TK.to_steps(dh, n), rec_hz=TK.REC_HZ)
        if amp == 0:
            return HE.distortion(r, ref)["detrended_rms_um"]
        m = HE.compare(r, ref)
        return m["e_band_rms_um"] / mu["e_band_rms_um"], m["e_rms_um"] / mu["e_rms_um"]

    def evaluate(self, x):
        t0 = time.time()
        br, ar = [], []
        for s in self.seeds:
            for f0 in self.f0s:
                for amp in self.amps:
                    b, a = self.run_one(x, s, f0, amp)
                    br.append(b); ar.append(a)
        dl = [self.run_one(x, s, 0.0, 0.0) for s in self.seeds]
        dg = [self.run_one(x, s, 0.0, 0.0, "glyph") for s in self.glyph]
        return {"band_ratio": float(np.mean(br)), "ratio": float(np.mean(ar)), "dist_lognormal_um": float(np.mean(dl)),
                "dist_glyph_um": float(np.mean(dg)), "false_corr_um": float(np.mean(dl + dg)),
                "band_by_cond": [float(v) for v in br], "t_eval_s": time.time() - t0}


def ship_x():
    p = TK.ship_params()
    return {k: float(np.clip(p.get(k, ES.AKF_DEFAULTS[k]), lo, hi)) for k, lo, hi in zip(SPACE.names, SPACE.lo, SPACE.hi)}


def search(n_init=14, n_iter=36, quick=False, seed=0, log=LOG):
    os.makedirs(os.path.dirname(log), exist_ok=True)
    tu = Tuner(quick=quick)
    rows = BO.parego(SPACE, tu.evaluate, ["band_ratio", "false_corr_um"], n_init=n_init, n_iter=n_iter, log_path=log, seed=seed,
                     x0=[ship_x()])
    return rows


def select(rows, max_log=15.0, max_glyph=30.0):
    ok = [r for r in rows if r["res"]["dist_lognormal_um"] <= max_log and r["res"]["dist_glyph_um"] <= max_glyph]
    if not ok:
        return None
    return min(ok, key=lambda r: r["res"]["band_ratio"])


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    rows = search(n_init=6 if quick else 14, n_iter=6 if quick else 36, quick=quick,
                  log=LOG.replace(".jsonl", "_quick.jsonl") if quick else LOG)
    best = select(rows)
    print("selected", json.dumps(best["x"] if best else None), json.dumps(best["res"] if best else None)[:400])
