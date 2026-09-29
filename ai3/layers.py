"""The three separate outputs of the language layer (PROPOSED DESIGN, as an executable specification).

Adopted from the independent review of 2026-09-29, section 10 (docs/reviews/): the pen and the app keep three outputs
apart, and nothing in the language layer can blur them.

1 StrokeRecord   what was actually put on paper.  Append-only: pen-down samples with time, and what the device did
                 on each stroke (nothing / nudged / withheld ink / wrote an accepted completion).  Every entry is
                 hash-chained to the one before, so any later edit is detectable (verify()).  Permanent ink cannot
                 be corrected by moving the nib, so nothing here is ever rewritten.
2 Transcript     what the app reads, and what the writer decides it should say.  Per word: the literal reading (the
                 recogniser's letters and confidences, never changed) and the current text.  Every change is a
                 Revision (who, what, why, when) and can be undone.  Suggestions are proposals until the writer
                 accepts one; automatic correction exists only as a mode the writer switches on, and is still
                 logged and reversible.
3 WritingPlan    ink the pen will write for the writer.  It can only be created from an acceptance in the
                 transcript (a completion or correction the writer chose to have written).  Once created it is fixed
                 for its stroke sequence: a new prediction cannot change it; only a writer action cancels it; a letter
                 that has started is finished or abandoned, never re-routed.  It passes reach and tracking gates
                 (complete_plan.py) before any command reaches the nib.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

DEVICE_ACTIONS = ("none", "nudged", "withheld", "autowritten")


class LayerError(RuntimeError):
    """An operation that would break the separation of the three outputs."""


# ============================================================================================ 1 stroke record
@dataclass(frozen=True)
class StrokeEntry:
    index: int
    t0: float
    points: Tuple[Tuple[float, float, float], ...]      # (t [s], x [m], y [m]) of the pen-down samples
    device_action: str
    plan_id: Optional[int]
    digest: str


class StrokeRecord:
    """Append-only, hash-chained record of the ink on paper."""

    def __init__(self):
        self._entries: List[StrokeEntry] = []

    @staticmethod
    def _hash(prev: str, pts, action: str, plan_id) -> str:
        h = hashlib.sha256(prev.encode())
        h.update(np.asarray(pts, np.float64).tobytes())
        h.update(f"{action}|{plan_id}".encode())
        return h.hexdigest()

    def append(self, points: Sequence[Sequence[float]], device_action: str = "none",
               plan_id: Optional[int] = None) -> StrokeEntry:
        if device_action not in DEVICE_ACTIONS:
            raise LayerError(f"unknown device action {device_action!r}")
        if device_action == "autowritten" and plan_id is None:
            raise LayerError("ink written by the pen must name the accepted writing plan it came from")
        pts = tuple((float(t), float(x), float(y)) for t, x, y in points)
        prev = self._entries[-1].digest if self._entries else "genesis"
        e = StrokeEntry(len(self._entries), pts[0][0] if pts else 0.0, pts, device_action, plan_id,
                        self._hash(prev, pts, device_action, plan_id))
        self._entries.append(e)
        return e

    @property
    def entries(self) -> Tuple[StrokeEntry, ...]:
        return tuple(self._entries)                 # a copy: callers cannot insert or delete

    def verify(self) -> bool:
        prev = "genesis"
        for e in self._entries:
            if self._hash(prev, e.points, e.device_action, e.plan_id) != e.digest:
                return False
            prev = e.digest
        return True

    def __len__(self):
        return len(self._entries)


# ============================================================================================ 2 transcript
@dataclass(frozen=True)
class Revision:
    rev_id: int
    word_index: int
    before: str
    after: str
    kind: str              # 'recognition' | 'spelling' | 'completion' | 'writer_edit' | 'undo'
    source: str            # 'recogniser' | 'checker' | 'predictor' | 'writer'
    accepted_by: str       # 'writer' | 'auto_mode'
    reason: str
    t: float


@dataclass
class Word:
    literal: str                                       # the recogniser's reading, never changed
    letter_conf: Tuple[float, ...]
    strokes: Tuple[int, ...]                           # stroke-record indices of this word's ink
    text: str = ""
    flags: List[Dict] = field(default_factory=list)    # suggestions shown (proposals, not changes)
    protected: bool = False                            # a name, number or word the writer marked as intended


@dataclass(frozen=True)
class Suggestion:
    word_index: int
    kind: str              # 'recognition' | 'spelling' | 'completion'
    source: str
    text: str
    p: float               # calibrated probability that this is what the writer means
    reason: str


class Transcript:
    """The revisable digital text with an audit trail."""

    KINDS = ("recognition", "spelling", "completion", "writer_edit", "undo")

    def __init__(self, auto_correct: bool = False, auto_min_p: float = 0.9):
        self.words: List[Word] = []
        self.revisions: List[Revision] = []
        self.auto_correct = auto_correct           # the writer's opt-in digital auto-correction mode
        self.auto_min_p = auto_min_p

    def add_word(self, literal: str, letter_conf: Sequence[float], strokes: Sequence[int],
                 protected: bool = False) -> int:
        self.words.append(Word(literal, tuple(float(c) for c in letter_conf), tuple(strokes), literal,
                               protected=protected))
        return len(self.words) - 1

    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    def literal(self) -> str:
        return " ".join(w.literal for w in self.words)

    def propose(self, s: Suggestion) -> bool:
        """Show a suggestion (no change).  Returns True if the auto mode applied it (logged, reversible)."""
        w = self.words[s.word_index]
        if w.protected and s.kind == "spelling":
            return False                              # names, numbers and marked words are never flagged
        w.flags.append({"kind": s.kind, "text": s.text, "p": s.p, "reason": s.reason})
        if self.auto_correct and s.kind in ("spelling", "recognition") and s.p >= self.auto_min_p:
            self._apply(s.word_index, s.text, s.kind, s.source, "auto_mode", s.reason)
            return True
        return False

    def accept(self, s: Suggestion) -> Revision:
        """The writer accepts a suggestion (an explicit action)."""
        return self._apply(s.word_index, s.text, s.kind, s.source, "writer", s.reason)

    def edit(self, word_index: int, text: str, reason: str = "writer edit") -> Revision:
        return self._apply(word_index, text, "writer_edit", "writer", "writer", reason)

    def protect(self, word_index: int) -> None:
        self.words[word_index].protected = True

    def undo(self, rev_id: int) -> Revision:
        r = self.revisions[rev_id]
        if self.words[r.word_index].text != r.after:
            raise LayerError("a later revision changed this word; undo that one first")
        return self._apply(r.word_index, r.before, "undo", "writer", "writer", f"undo of revision {rev_id}")

    def _apply(self, i: int, text: str, kind: str, source: str, by: str, reason: str) -> Revision:
        if kind not in self.KINDS:
            raise LayerError(f"unknown revision kind {kind!r}")
        w = self.words[i]
        r = Revision(len(self.revisions), i, w.text, text, kind, source, by, reason, time.time())
        w.text = text
        self.revisions.append(r)
        return r

    def audit(self) -> List[Dict]:
        return [r.__dict__.copy() for r in self.revisions]


# ============================================================================================ 3 writing plan
@dataclass
class PlanLetter:
    char: str
    strokes: List[np.ndarray]           # the letter's path (m), in page coordinates, pen-down strokes
    state: str = "queued"               # queued | writing | done | abandoned


class WritingPlan:
    """Ink the pen may write: only for text the writer accepted, fixed once created."""

    _next_id = 0
    STATES = ("planned", "writing", "done", "handed_back", "cancelled")

    def __init__(self, acceptance: Revision, letters: List[PlanLetter], gates: Dict[str, bool]):
        if acceptance.accepted_by != "writer" or acceptance.kind not in ("completion", "spelling", "writer_edit"):
            raise LayerError("a writing plan needs text the writer accepted explicitly (not an automatic change)")
        if not all(gates.values()):
            failed = [k for k, v in gates.items() if not v]
            raise LayerError(f"writing plan refused: gates not passed {failed}")
        WritingPlan._next_id += 1
        self.plan_id = WritingPlan._next_id
        self.acceptance = acceptance
        self._letters = letters
        self.text = "".join(L.char for L in letters)
        self.state = "planned"
        self.log: List[Tuple[float, str]] = []

    @property
    def letters(self) -> Tuple[PlanLetter, ...]:
        return tuple(self._letters)

    def start_letter(self, k: int) -> None:
        if self.state not in ("planned", "writing"):
            raise LayerError(f"plan is {self.state}")
        if any(L.state == "writing" for L in self._letters):
            raise LayerError("one letter at a time")
        self._letters[k].state = "writing"
        self.state = "writing"

    def finish_letter(self, k: int) -> None:
        self._letters[k].state = "done"
        if all(L.state in ("done", "abandoned") for L in self._letters):
            self.state = "done"

    def replace(self, new_text: str, by_writer: bool = False) -> None:
        """A new prediction cannot change an accepted plan; only the writer can (by cancelling and accepting anew)."""
        if not by_writer:
            raise LayerError("an accepted writing plan is fixed; a new prediction cannot redirect the nib")
        self.cancel("writer replaced the plan")

    def cancel(self, reason: str) -> None:
        for L in self._letters:
            if L.state == "writing":
                L.state = "abandoned"              # the pen lifts; the started letter is not re-routed
        self.state = "cancelled"
        self.log.append((time.time(), reason))

    def hand_back(self, reason: str) -> None:
        for L in self._letters:
            if L.state == "writing":
                L.state = "abandoned"
        self.state = "handed_back"
        self.log.append((time.time(), reason))


def as_json(record: StrokeRecord, tr: Transcript, plans: Sequence[WritingPlan]) -> str:
    """The three outputs side by side, as the app would export them."""
    return json.dumps({
        "stroke_record": [{"index": e.index, "t0": e.t0, "n": len(e.points), "device_action": e.device_action,
                           "plan_id": e.plan_id, "digest": e.digest[:16]} for e in record.entries],
        "stroke_record_verified": record.verify(),
        "transcript": {"literal": tr.literal(), "text": tr.text(), "audit": tr.audit()},
        "writing_plans": [{"plan_id": p.plan_id, "text": p.text, "state": p.state,
                           "accepted_revision": p.acceptance.rev_id} for p in plans]}, default=str)
