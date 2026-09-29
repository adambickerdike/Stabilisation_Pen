"""Fast checks of study S's building blocks (no network, no trained model needed; well under a minute)."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pytest

import ai3
from ai3 import cues as CU
from ai3 import online as O
from ai3 import predict as PR
from ai3 import shape as SH
from ai3 import spell as SP
from ai3.rules import RULES, rules_sha256

REPO = Path(ai3.__file__).resolve().parent.parent


# ------------------------------------------------------------------ spelling
def test_alignment_and_first_deviation():
    ops = SP.align("sister", "siter")
    assert sum(1 for o in ops if o[0] != "M") == 1
    assert SP.first_deviation("sister", "siter") == 3
    assert SP.first_deviation("goes", "go") == 3           # a proper prefix: the error shows at the word end
    assert SP.first_deviation("because", "becuase") == 4
    assert [o[0] for o in SP.align("the", "teh")].count("T") == 1


class _FakeWordLM:
    def __init__(self, vocab, probs):
        self.vocab = list(vocab)
        self.index = {w: i for i, w in enumerate(self.vocab)}
        self.p = np.asarray(probs, float) / np.sum(probs)

    def dist(self, prev):
        return self.p.copy()

    def prob(self, w, prev):
        i = self.index.get(w)
        return float(self.p[i]) if i is not None else 0.0


class _FakeCharLM:
    def dist(self, text):
        from aiguide import lm
        return np.full(lm.V, 1.0 / lm.V)


def _checker():
    pairs = [("sister", "siter"), ("because", "becuase"), ("watch", "wach"), ("because", "becos"), ("friend", "freind"),
             ("sister", "sistor"), ("watch", "woch"), ("club", "clob"), ("there", "thier"), ("which", "wich")] * 3
    ch = SP.Channel.from_pairs(pairs, min_rule=1)
    vocab = ["sister", "sit", "site", "because", "watch", "wash", "club", "friend", "the", "there", "which", "my"]
    wl = _FakeWordLM(vocab, [5, 3, 2, 8, 4, 2, 2, 3, 20, 6, 5, 9])
    trie = SP.Trie(vocab)
    lex_ids = np.array([wl.index.get(w, -1) for w in trie.words])
    return SP.Checker(trie, ch, wl, _FakeCharLM(), lex_ids, alpha=0.12, p_oov=0.01), ch


def test_checker_flags_nonword_and_passes_correct_word():
    ck, ch = _checker()
    st = ck.start("my", "my ")
    pd = [ck.push(st, c)["p_dev"] for c in "wach"]
    assert pd[2] > 0.9                                     # 'wac' is not the start of any word
    e = ck.end(st)
    assert e["p_err"] > 0.9 and e["suggestions"][0][0] == "watch"
    st = ck.start("my", "my ")
    pd = [ck.push(st, c)["p_dev"] for c in "sister"]
    assert max(pd) < 0.5 and ck.end(st)["p_err"] < 0.5
    assert ch.word_cost("sister", "siter") < ch.word_cost("sister", "club")


def test_trie_prefix_ranges():
    t = SP.Trie(["a", "ab", "abc", "b", "ba"])
    lo, hi = t.prefix_range("ab")
    assert t.words[lo:hi] == ["ab", "abc"]
    assert t.node_of("zz") == -1


# ------------------------------------------------------------------ online recogniser
def test_encode_features_and_causality():
    import torch
    s1 = np.column_stack([np.linspace(0, 1, 20), np.sin(np.linspace(0, 3, 20))])
    s2 = np.column_stack([np.linspace(1, 1.2, 5), np.linspace(1, 0, 5)])
    F, fr = O.encode([s1, s2], 1.0)
    assert F.shape[1] == O.N_FEAT and np.all(np.diff(fr) >= -1e-12) and fr[-1] == pytest.approx(1.0)
    assert (F[:, 4] == 0).sum() == 1                        # one pen-up jump
    m = O.make_model(16, 1)
    m.eval()
    with torch.no_grad():
        a, _ = m(torch.from_numpy(F[None]))
        G = F.copy(); G[-5:] += 3.0                         # change the future
        b, _ = m(torch.from_numpy(G[None]))
    assert torch.allclose(a[0, :-5], b[0, :-5])             # the past output does not depend on the future


def test_tremor_augmentation_amplitude():
    rng = np.random.default_rng(0)
    s = [np.zeros((400, 2))]
    out = O.add_tremor(s, rng, 1.0, 0.008, (0.3, 0.3))
    r = np.hypot(out[0][:, 0], out[0][:, 1])
    assert 0.25 < r.max() < 0.4


def test_calibration_fusion_prefers_matching_template():
    t = np.linspace(0, 2 * math.pi, 40)
    circ = np.column_stack([np.cos(t) - 1, np.sin(t)])
    line = np.column_stack([np.zeros(40), np.linspace(0, 2, 40)])
    Fc, _ = O.encode([circ], 1.0); Fl, _ = O.encode([line], 1.0)
    sc = O.calib_logscores(Fc[:20], {0: Fc, 1: Fl}, 0.1)
    assert sc[0] > sc[1]
    q = O.fuse(np.full(26, 1 / 26), sc, 0.5)
    assert np.argmax(q) == 0 and q.sum() == pytest.approx(1.0)


# ------------------------------------------------------------------ shape assist
def test_open_end_dtw_moves_forward():
    B = np.column_stack([np.linspace(0, 1, 50), np.zeros(50)])
    A = B[:20] + np.array([0.0, 0.01])
    jb, match = SH.open_end_dtw(A, B)
    assert 17 <= jb <= 22 and np.all(np.diff(match) >= 0)


def test_command_dead_band_and_limit():
    dev = np.full((400, 2), np.nan)
    dev[100:300] = [30e-6, 0.0]                              # below a 0.1 x-height dead band (300 um)
    q = SH.command(dev, 0.75, 0.3e-3, 0.3e-3, 2000.0)
    assert np.abs(q).max() == 0.0
    dev[100:300] = [5e-3, 0.0]                               # a large deviation is limited to q_max
    q = SH.command(dev, 0.75, 0.3e-3, 0.3e-3, 2000.0)
    assert np.abs(q).max() <= 0.3e-3 + 1e-12 and np.abs(q[:100]).max() == 0.0


def test_render_centred():
    img = SH.render([np.column_stack([np.zeros(10), np.linspace(0, 1, 10)])])
    ys, xs = np.nonzero(img > 0.2)
    assert abs(xs.mean() - SH.IMG / 2) < 2.0 and abs(ys.mean() - SH.IMG / 2) < 2.0


# ------------------------------------------------------------------ cues
def _records():
    err = {"kind": "error", "target": "watch", "tokens": [{"written": "wach", "p_dev": [0.0, 0.0, 0.99, 1.0],
                                                          "p_next": [0.01, 0.01, 0.0, 0.0], "p_err_end": 1.0,
                                                          "suggestions": ["watch"], "complete_top": [[], [], ["watch"], ["watch"]]}]}
    cor = {"kind": "correct", "target": "my", "tokens": [{"written": "my", "p_dev": [0.0, 0.0], "p_next": [0.0, 0.0],
                                                         "p_err_end": 0.0, "suggestions": [], "complete_top": [[], []]}]}
    return [[err, cor] * 20]


def test_cues_invariants():
    rec = _records()
    commit = {"p_before_end": 0.6, "frac_median": 0.7}
    for c in CU.CUES:
        r = CU.simulate(rec, c, 0.9, 0.98, 0.05, CU.Response(), commit, 0.9, n_rep=3)
        if c != "show_me":
            assert r["letters_drawn_by_pen_per_100_words"] == 0.0
        assert r["false_interventions_per_100_correct"] == 0.0
    r = CU.simulate(rec, "none", 0.9, 0.98, 0.05, CU.Response(), commit, 0.9, n_rep=3)
    assert r["fixed_on_paper_per_10_errors"] == 0.0
    r = CU.simulate(rec, "tick_after", 0.9, 0.98, 0.05, CU.Response(), commit, 0.9, n_rep=5)
    assert r["caught_per_10_errors"] == pytest.approx(10.0)


# ------------------------------------------------------------------ prediction
def test_personal_cache_learns_user_words():
    class _W:
        vocab = ["</s>", "the", "a", "pony"]
        index = {w: i for i, w in enumerate(vocab)}
        def dist(self, prev):
            return np.array([0.1, 0.6, 0.29, 0.01])
        def prob(self, w, prev):
            return float(self.dist(prev)[self.index[w]]) if w in self.index else 0.0
        def prefix_range(self, p):
            return np.array([i for i, w in enumerate(self.vocab) if w.startswith(p) and i > 0], int)
    class _B:
        word = _W()
    p = PR.Predictor(_B(), lc=0.3, lb=0.0, half_life=float("inf"))
    assert "oates" not in p.candidates(None, "", 3)
    for _ in range(5):
        p.observe(None, "oates")
    assert p.candidates(None, "o", 3)[0] == "oates"         # the user's own word (not in the base vocabulary)


# ------------------------------------------------------------------ bookkeeping
def test_rules_hash_and_evidence_header():
    assert len(rules_sha256()) == 16 and "S2_detect" in RULES
    hdr = next(csv.reader(open(REPO / "docs" / "evidence.csv", encoding="utf-8")))
    assert len(hdr) == 23
    from ai3 import evidence as EV
    assert EV.HEADER == hdr
    for row in EV.rows():
        assert len(row) == 23 and row[0].split("-")[0] in ("EML", "PDT", "CON", "HAP")
