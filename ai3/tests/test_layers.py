"""The three outputs stay separate (ai3/layers.py): immutable ink record, audited transcript, accepted-only plan."""
from __future__ import annotations

import numpy as np
import pytest

from ai3 import layers as LY


def _strokes(rec, n=3):
    for k in range(n):
        rec.append([(0.1 * k + 0.01 * i, 1e-3 * k + 1e-4 * i, 0.0) for i in range(5)])


def test_stroke_record_is_append_only_and_tamper_evident():
    rec = LY.StrokeRecord()
    _strokes(rec)
    assert rec.verify() and len(rec) == 3
    ents = rec.entries
    assert isinstance(ents, tuple)                            # callers get a copy
    with pytest.raises(Exception):
        ents[0].points = ()                                   # frozen entries
    # tampering with the stored list is detected
    e = rec._entries[1]
    rec._entries[1] = LY.StrokeEntry(e.index, e.t0, e.points[:-1], e.device_action, e.plan_id, e.digest)
    assert not rec.verify()
    with pytest.raises(LY.LayerError):
        LY.StrokeRecord().append([(0, 0, 0)], device_action="autowritten")   # pen ink must name its accepted plan


def test_transcript_keeps_literal_audits_and_undoes():
    tr = LY.Transcript()
    i = tr.add_word("becuase", [0.9] * 7, [0, 1])
    s = LY.Suggestion(i, "spelling", "checker", "because", 0.8, "likely transposition")
    assert tr.propose(s) is False and tr.text() == "becuase"   # a suggestion changes nothing by itself
    r = tr.accept(s)
    assert tr.text() == "because" and tr.literal() == "becuase" and r.accepted_by == "writer"
    u = tr.undo(r.rev_id)
    assert tr.text() == "becuase" and u.kind == "undo" and len(tr.audit()) == 2


def test_protected_words_and_opt_in_auto_mode():
    tr = LY.Transcript()
    i = tr.add_word("Thrush", [0.9] * 6, [0], protected=True)
    assert tr.propose(LY.Suggestion(i, "spelling", "checker", "thrust", 0.99, "")) is False
    assert tr.text() == "Thrush" and not tr.words[i].flags         # names are never flagged
    auto = LY.Transcript(auto_correct=True, auto_min_p=0.9)
    j = auto.add_word("teh", [0.9] * 3, [0])
    assert auto.propose(LY.Suggestion(j, "spelling", "checker", "the", 0.95, "")) is True
    assert auto.text() == "the" and auto.revisions[-1].accepted_by == "auto_mode"
    assert auto.propose(LY.Suggestion(j, "spelling", "checker", "tea", 0.5, "")) is False   # weak evidence: abstain


def test_writing_plan_needs_writer_acceptance_and_is_fixed():
    tr = LY.Transcript(auto_correct=True)
    i = tr.add_word("becau", [0.9] * 5, [0])
    s = LY.Suggestion(i, "completion", "predictor", "because", 0.7, "completion at a pause")
    letters = [LY.PlanLetter(c, [np.zeros((2, 2))]) for c in "se"]
    tr.propose(s)                                                   # completions are never auto-applied
    assert tr.text() == "becau"
    r = tr.accept(s)
    with pytest.raises(LY.LayerError):
        LY.WritingPlan(r, letters, {"reach": False, "tracking": True})   # gates must pass
    plan = LY.WritingPlan(r, letters, {"reach": True, "tracking": True})
    plan.start_letter(0)
    with pytest.raises(LY.LayerError):
        plan.replace("becalm")                                      # a new prediction cannot redirect the nib
    with pytest.raises(LY.LayerError):
        plan.start_letter(1)                                        # one letter at a time
    plan.replace("because", by_writer=True)                         # the writer can cancel
    assert plan.state == "cancelled" and plan.letters[0].state == "abandoned"
    auto_rev = LY.Revision(9, i, "a", "b", "spelling", "checker", "auto_mode", "", 0.0)
    with pytest.raises(LY.LayerError):
        LY.WritingPlan(auto_rev, letters, {"reach": True})          # automatic changes never become ink
