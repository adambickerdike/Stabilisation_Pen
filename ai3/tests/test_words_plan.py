"""Word recognition helpers, the recognition-aware spelling score, calibration, and the completion planner."""
from __future__ import annotations

import numpy as np

from ai3 import complete_plan as CP
from ai3 import stage_words as SW


def test_segment_rule_joins_dots_and_overlaps():
    stem = np.array([[0.0, 0.0], [0.0, 1.0]])
    dot = np.array([[0.35, 1.5], [0.37, 1.52]])             # an i-dot set off to the right
    nxt = np.array([[1.0, 0.0], [1.6, 1.0]])
    assert SW.segment([stem, dot, nxt]) == [[0, 1], [2]]
    far = np.array([[0.5, 0.0], [0.9, 1.0]])                  # a long stroke 0.5 x-height away is a new letter
    assert SW.segment([stem, far]) == [[0], [1]]


def test_edit_distance_and_nbest():
    assert SW.edit_distance("libary", "library") == 1 and SW.edit_distance("", "ab") == 2
    P = [np.eye(26)[0] * 0.7 + 0.3 / 26, np.eye(26)[1] * 0.5 + np.eye(26)[3] * 0.4 + 0.1 / 26]
    nb = SW.nbest(P, 3)
    assert nb[0][0] == "ab" and nb[1][0] == "ad" and nb[0][1] > nb[1][1]


def test_combine_separates_recognition_from_spelling():
    # reading 'teh' (likely) vs 'the' (a bit less likely by the strokes, but a common word): the score picks 'the'
    tok = {"capital": False, "reads": [
        {"x": "teh", "lp": -1.0, "err": 1e-6, "cor": 0.0, "oov": 1e-9, "tot": 1e-6 + 1e-9, "sug": [("the", 0.99)]},
        {"x": "the", "lp": -2.0, "err": 1e-7, "cor": 1e-3, "oov": 1e-9, "tot": 1e-3 + 1e-7 + 1e-9, "sug": []}]}
    c = SW.combine(tok, 1.0)
    assert c["best_read"] == "the" and c["p_err"] < 0.01    # a misreading, not a misspelling
    tok["capital"] = True
    assert SW.combine(tok, 1.0)["p_err"] <= 1e-8            # names are never flagged


def test_temperature_scaling_reduces_calibration_error():
    rng = np.random.default_rng(0)
    z = rng.normal(0, 2, 4000)
    y = (rng.random(4000) < 1 / (1 + np.exp(-z))).astype(int)
    over = 1 / (1 + np.exp(-3 * z))                          # overconfident scores
    T = SW.fit_temperature(over, y)
    assert 2.4 < T < 3.6
    assert SW.ece(SW.apply_T(over, T), y)["ece"] < SW.ece(over, y)["ece"]


def test_planner_respects_reach_and_hands_back():
    lets = [[np.array([[0.0, 0.0], [0.0, 1.0], [0.5, 1.0], [0.5, 0.0]])] for _ in range(3)]
    P, pen, lid, s = CP.word_path(lets)
    rng = np.random.default_rng(1)
    B, _ = CP.hand_track(P, s, "steady", 6.0, rng)
    r = CP.simulate(P, pen, lid, s, B, 6.0, "letter_admission")
    assert r["state"] == "done" and r["q_max_mm"] <= 6.0 - 0.5 + 1e-6 and r["partial_letters"] == 0
    Bs, _ = CP.hand_track(P, s, "still", 6.0, rng)
    r2 = CP.simulate(P, pen, lid, s, Bs, 1.0, "letter_admission")
    assert r2["state"].startswith("handed_back") and r2["partial_letters"] == 0
