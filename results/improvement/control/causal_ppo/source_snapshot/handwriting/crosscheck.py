"""Cross-check of HW1's pencil module against the project's pencil model P1 (sim/pencil, unmodified) (SIMULATION).

Same writers, writing and tremor realisations.  P1 is run as fusion/harness.py does: neutral, the disturbance oracle
(mode "oracle" with the clean neutral housing path) and the shipped AKF through Controller(mode="external").
HW1 is run with P1's conventions (open-loop hand: writer_comp "none"; contact-gated authority; no writer adaptation).
Compared: the 3-15 Hz ink error against the same pen's tremor-free ink, as a ratio to the pen's neutral run
(sim/pencil/evaluate.compare definition), and the ink error against the intended letters.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import ensure_paths
from . import params as PR
from . import plant as PL
from . import tracker as TR
from . import writers as W

ensure_paths()
from fusion import estimators as ES  # noqa: E402
from fusion import sensors as S  # noqa: E402
from sim.pencil import evaluate as E  # noqa: E402
from sim.pencil import model as M  # noqa: E402
from sim.pensim import scenarios as SC  # noqa: E402

Q_LIM = 0.30e-3


def _band_ratio_hw1(r, r_clean, r_neutral) -> float:
    def band_err(x):
        n = min(len(x.t), len(r_clean.t))
        e = x.ink[:n] - r_clean.ink[:n]
        fs = 1.0 / float(x.t[1] - x.t[0])
        eb = sosfiltfilt(butter(4, (3.0, 15.0), btype="band", fs=fs, output="sos"), e, axis=0)
        m = (x.contact[:n] > 0.5) & (x.t[:n] > 0.5)
        return float(np.sqrt(np.mean(np.sum(eb[m] ** 2, axis=1))))
    return band_err(r) / max(band_err(r_neutral), 1e-12)


def scenario(w: int, seed: int, f0: float, amp: float, tracker: Dict) -> Dict:
    wr = W.writer(w).write(W.ET_SENTENCE, dt=W.SIM_DT, seed=2000 + w)
    it = wr.intended
    d = W.tremor_path(it.t, f0, amp, seed, w)
    out = {"writer": w, "seed": seed, "f0": f0, "amp_mm": amp * 1e3}
    # ---- P1
    scn1 = SC._assemble(it, d, 1.0, 50.0, meta={"kind": "handwriting_crosscheck"})
    scn0 = SC._assemble(it, np.zeros_like(d), 1.0, 50.0, meta={"kind": "handwriting_crosscheck"})
    S_ = 11 + w
    clean = M.run(scn0, M.Controller(mode="neutral", q_lim=Q_LIM), M.PencilConfig(), seed=S_, rec_hz=4000.0)
    neut = M.run(scn1, M.Controller(mode="neutral", q_lim=Q_LIM), M.PencilConfig(), seed=S_, rec_hz=4000.0)
    orc = M.run(M.with_disturbance(scn1, M.housing_disturbance(scn1, clean)), M.Controller(mode="oracle", q_lim=Q_LIM),
                M.PencilConfig(), seed=S_, rec_hz=4000.0)
    rec1 = S.record_from_result(neut, scn1)
    st = S.make_streams(rec1, S.config(**tracker["sensors"]), 90_000_000 + 1000 * w + 10 * int(f0) + int(amp * 1e4))
    dh, _ = ES.run_estimator("akf", st, tracker["params"])
    akf = M.run(M.with_estimate(scn1, S.expand_to_steps(dh, len(scn1.t), rec1.sdec)),
                M.Controller(mode="external", q_lim=Q_LIM), M.PencilConfig(), seed=S_, rec_hz=4000.0)
    base = E.compare(neut, clean)
    out["P1"] = {"oracle_band_ratio": E.compare(orc, clean)["e_band_rms_um"] / base["e_band_rms_um"],
                 "akf_band_ratio": E.compare(akf, clean)["e_band_rms_um"] / base["e_band_rms_um"],
                 "neutral_band_um": base["e_band_rms_um"]}
    # ---- HW1 pencil module with P1 conventions
    hand = PR.Hand.from_config(writer_comp="none")
    pen = PR.pencil_p0()
    s0 = PL.scenario_from_written(wr, None)
    s1 = PL.scenario_from_written(wr, d)
    ck = {"gating": "contact"}
    rc = PL.run(s0, pen, hand, ctl=PL.Controls(**ck))
    rn = PL.run(s1, pen, hand, ctl=PL.Controls(**ck))
    Ts, nt = rn.info["Ts"], rn.info["n_ticks"]
    ro = PL.run(s1, pen, hand, ctl=PL.Controls(qext=TR.oracle_command(rn, rc, pen, nt, Ts), **ck))
    dh2, _ = TR.akf_estimate(rn, s1, pen, tracker, 91_000_000 + 1000 * w + 10 * int(f0) + int(amp * 1e4))
    ra = PL.run(s1, pen, hand, ctl=PL.Controls(qext=-dh2, **ck))
    out["HW1"] = {"oracle_band_ratio": _band_ratio_hw1(ro, rc, rn), "akf_band_ratio": _band_ratio_hw1(ra, rc, rn)}
    # HW1 nominal conventions (adapted writer, drag compensated, hover gating) for the same pen
    hand_n = PR.Hand.from_config()
    hp = PL.adapted_path(s0.intended, s0.dt, pen, hand_n)
    rc2 = PL.run(PL.with_hand_path(s0, hp), pen, hand_n)
    rn2 = PL.run(PL.with_hand_path(s0, hp, d), pen, hand_n)
    ro2 = PL.run(PL.with_hand_path(s0, hp, d), pen, hand_n, ctl=PL.Controls(qext=TR.oracle_command(rn2, rc2, pen, nt, Ts)))
    dh3, _ = TR.akf_estimate(rn2, PL.with_hand_path(s0, hp, d), pen, tracker, 92_000_000 + 1000 * w + 10 * int(f0))
    ra2 = PL.run(PL.with_hand_path(s0, hp, d), pen, hand_n, ctl=PL.Controls(qext=-dh3))
    out["HW1_nominal"] = {"oracle_band_ratio": _band_ratio_hw1(ro2, rc2, rn2), "akf_band_ratio": _band_ratio_hw1(ra2, rc2, rn2)}
    return out


def run(writers=(0, 1, 2, 3, 4, 5), seeds=(200,), f0s=(6.0, 10.0), amps=(0.3e-3, 1.0e-3)) -> Dict:
    trk = PR.akf_ship()
    rows = [scenario(w, s, f0, a, trk) for w in writers for s in seeds for f0 in f0s for a in amps]
    agg = {}
    for f0 in f0s:
        for a in amps:
            sel = [r for r in rows if r["f0"] == f0 and r["amp_mm"] == a * 1e3]
            agg[f"{f0:g}Hz_{a * 1e3:g}mm"] = {m: {k: float(np.mean([r[m][k] for r in sel])) for k in ("oracle_band_ratio", "akf_band_ratio")}
                                            for m in ("P1", "HW1", "HW1_nominal")}
    return {"rows": rows, "summary": agg,
            "note": "band ratio = 3-15 Hz ink error against the same pen's tremor-free ink, relative to its neutral run"}
