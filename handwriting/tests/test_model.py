"""Fast checks of model HW1 and the study helpers (SIMULATION verification, not validation)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from handwriting import metrics as MT
from handwriting import params as PR
from handwriting import plant as PL
from handwriting import tracker as TR
from handwriting import writers as W

HAND = PR.Hand.from_config()


@pytest.fixture(scope="module")
def word():
    wr = W.writer(100).write("ab", dt=W.SIM_DT, seed=2100)
    return wr, PL.scenario_from_written(wr, None)


def test_scheduled_writer_reproduces_aiguide():
    from aiguide.writer import SyntheticWriter, sample_style
    a = SyntheticWriter(sample_style(np.random.default_rng(3)), seed=3).write("dog", dt=1e-3, seed=7)
    b = W.writer(3).write("dog", dt=1e-3, seed=7)
    assert np.array_equal(a.intended.xy, b.intended.xy)
    assert [L.char for L in a.letters] == [L.char for L in b.letters]


def test_reversal_and_size_schedule():
    plan = W.error_plan("bdpq", W.ErrorProfile("t", p_reversal=1.0), 1)
    assert plan["override"] == {0: "d", 1: "b", 2: "q", 3: "p"}
    wr = W.writer(1).write("oo", dt=1e-3, seed=1, size_factors=[1.0, 0.5])
    assert wr.letters[1].size < 0.7 * wr.letters[0].size


def test_pd_schedule_cue_and_lines():
    prof = W.PDProfile(decrement=0.3, cue_recovery=1.0)
    rng = np.random.default_rng(0)
    s_none, _, c_none = W.pd_schedule(30, prof, "none", rng)
    s_cue, tempo, c_cue = W.pd_schedule(30, prof, "cue", np.random.default_rng(0))
    s_lines, _, _ = W.pd_schedule(30, prof, "lines", rng)
    assert not c_none and c_cue
    assert s_cue[-1] > s_none[-1] and s_lines[-1] > s_none[-1]
    assert tempo.max() > 1.0


def test_adapted_writer_reproduces_letters(word):
    wr, s0 = word
    for pen in (PR.ordinary_pen(), PR.rev_h()):
        hp = PL.adapted_path(s0.intended, s0.dt, pen, HAND)
        r = PL.run(PL.with_hand_path(s0, hp), pen, HAND)
        assert MT.aligned_error_um(r, s0) < 10.0, pen.key


def test_tremor_transmission_matches_linear_model():
    dt, f, A = 25e-6, 8.0, 1e-3
    t = np.arange(0.0, 3.0, dt)
    w = 2 * math.pi * f
    d = np.column_stack([A * np.sin(w * t), np.zeros_like(t)])
    scn = PL.Scenario(t=t, pref=np.ascontiguousarray(d), vref=np.ascontiguousarray(np.gradient(d, dt, axis=0)),
                      down=np.zeros(len(t)), intended=np.zeros_like(d), tremor=d, dt=dt, meta={"lift": np.full(len(t), 1.5e-3)})
    for pen in (PR.ordinary_pen(), PR.weighted_pen()):
        r = PL.run(scn, pen, HAND)
        m = r.t > 2.0
        X = np.column_stack([np.sin(w * r.t[m]), np.cos(w * r.t[m])])
        coef, *_ = np.linalg.lstsq(X, r.handle[m, 0], rcond=None)
        amp = math.hypot(*coef)
        G = complex(HAND.K_grip, w * HAND.C_grip)
        H = complex(HAND.k_arm - HAND.M_hand * w ** 2, w * HAND.b_arm)
        ratio = abs(H / (H - pen.mass * w ** 2 * (H / G + 1)))
        assert abs(amp / A - ratio) < 0.02 * ratio, (pen.key, amp / A, ratio)


def test_oracle_cancels_with_rev_h_and_saturates_pencil(word):
    wr, s0 = word
    d = W.tremor_path(s0.t, 8.0, 1.0e-3, 300, 100)
    out = {}
    for pen in (PR.rev_h(), PR.pencil_p0()):
        hp = PL.adapted_path(s0.intended, s0.dt, pen, HAND)
        rc = PL.run(PL.with_hand_path(s0, hp), pen, HAND)
        sc = PL.with_hand_path(s0, hp, d)
        rn = PL.run(sc, pen, HAND)
        qo = TR.oracle_command(rn, rc, pen, rn.info["n_ticks"], rn.info["Ts"])
        ro = PL.run(sc, pen, HAND, ctl=PL.Controls(qext=qo))
        out[pen.key] = (MT.aligned_error_um(ro, sc) / MT.aligned_error_um(rn, sc), MT.travel(ro, pen)["at_travel_limit"])
    assert out["revH"][0] < 0.15
    assert out["pencil"][0] > 0.5 and out["pencil"][1] > 0.3


def test_force_limit_and_stop(word):
    wr, s0 = word
    pen = PR.rev_h()
    pen.F_peak = 0.005
    nt = int(len(s0.t) * s0.dt * pen.tick_hz) + 2
    q = np.zeros((nt, 2))
    q[nt // 3:, 0] = 5e-3                                   # beyond the travel: soft limit, stop and force limit engage
    r = PL.run(s0, pen, HAND, ctl=PL.Controls(qext=q))
    assert r["sat"].max() > 0.5
    assert np.hypot(r["qx"], r["qy"]).max() < pen.q_stop + 0.2e-3


def test_guidance_authorship(word):
    from aiguide.template import LetterTemplate, build_track
    wr, s_raw = word
    pen = PR.rev_h()
    s0 = PL.with_hand_path(s_raw, PL.adapted_path(s_raw.intended, s_raw.dt, pen, HAND))
    r0 = PL.run(s0, pen, HAND)
    for shift, lo, hi in ((0.0, 0.0, 0.10), (0.8e-3, 0.10, 0.9)):
        letters = [LetterTemplate(L.char, [p + np.array([shift, 0.0]) for p in L.polylines], 1.0, "t", k) for k, L in enumerate(wr.letters)]
        trk = build_track(letters, speed=wr.style.speed_mm_s * 1e-3, air_speed=wr.style.air_speed_mm_s * 1e-3, dt=5e-4)
        r = PL.run(s0, pen, HAND, ctl=PL.Controls(tmpl=trk.xy, tmpl_down=trk.pen_down.astype(float), g_guide=1.0, stroke_match=True))
        a = MT.authorship(r, r0)
        assert lo <= a["device_share"] <= hi, (shift, a)


def test_stroke_ranges():
    a, b = PL.stroke_ranges(np.array([0, 1, 1, 0, 0, 1, 0, 1, 1, 1]))
    assert a.tolist() == [1, 5, 7] and b.tolist() == [3, 6, 10]


def test_rev_h_parameters_are_labelled():
    p = PR.rev_h()
    assert 0 < p.q_lim < p.q_stop and p.F_peak > 0 and p.servo_hz > 0
    assert p.sources, "every Rev H value needs a source label"
    assert PR.servo_group_delay(p) > p.latency


def test_board_law_band_cap_handle_and_yield(word):
    """The board study's law: nothing inside the partial band, capped force on the handle (not the nose), and the
    supervisor yields to a writer who keeps writing elsewhere."""
    from aiguide.template import LetterTemplate, build_track
    wr, s_raw = word
    pen = PR.rev_h()
    brd = PR.board()
    s0 = PL.with_hand_path(s_raw, PL.adapted_path(s_raw.intended, s_raw.dt, pen, HAND))
    r0 = PL.run(s0, pen, HAND)

    def run(shift, mode):
        letters = [LetterTemplate(L.char, [p + np.array([shift, 0.0]) for p in L.polylines], 1.0, "t", k) for k, L in enumerate(wr.letters)]
        trk = build_track(letters, speed=wr.style.speed_mm_s * 1e-3, air_speed=wr.style.air_speed_mm_s * 1e-3, dt=5e-4)
        ctl = PL.Controls(board=brd, board_mode=mode, board_tmpl=trk.xy, board_tmpl_down=trk.pen_down.astype(float), stroke_match=True)
        r = PL.run(s0, pen, HAND, ctl=ctl)
        F = np.hypot(r["FBx"], r["FBy"])
        return r, F
    r, F = run(0.5e-3, "partial")
    assert F.max() < 0.02                                    # inside the 1 mm band (sensing noise can cross it briefly)
    r, F = run(0.5e-3, "full")
    assert 0.05 < F.max() <= brd.F_cap + 1e-9
    assert np.hypot(r["qx"], r["qy"]).max() < 0.05e-3      # the nose is not loaded: the magnet is on the handle
    c = (r.contact > 0.5) & (r0.contact > 0.5)
    assert np.mean(r.ink[c, 0] - r0.ink[c, 0]) > 0.05e-3    # the ink moves toward the shifted template
    r, F = run(10e-3, "full")
    c = np.flatnonzero(r.contact > 0.5)
    late = c[c > c[0] + int(0.8 * (c[-1] - c[0]))]
    assert F[late].mean() < 0.2 * brd.F_cap                  # yielded to a writer 10 mm away
