"""A writer-adapted letter reader: the app's reader for real handwriting (CALC).

The HW1 study reads ink with aiguide's recogniser, which compares each letter with 26 glyphs of the synthetic font
drawn in the writer's slant and width.  Real writers do not write that font, so on real handwriting it misreads clean
letters.  This reader instead compares each ink letter with the SAME writer's own clean letters taken from OTHER
recordings of that writer (never the recording being read): size-normalised shapes (aiguide.metrics.normalise and
shape_points, 64 points), dynamic time warping (aiguide.metrics.dtw), nearest instance per letter.  It has the
interface of aiguide.metrics.GlyphRecognizer (classify(strokes) -> (letter, {letter: distance})), so the handwriting
package's metrics (letters read, words read with the app's lexicon correction) run unchanged.

Its skill on clean writing is measured on tuning writers and reported (a reader that cannot read clean writing would
make every pen look bad).  It stands for 'a reader who knows this person's handwriting', not for a stranger.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import ensure_paths

ensure_paths()
from aiguide.metrics import dtw, normalise, shape_points  # noqa: E402


class WriterReader:
    """Nearest-instance DTW reader over a writer's own letters."""

    def __init__(self, instances: Dict[str, List[Sequence[np.ndarray]]], max_per_letter: int = 8, n_pts: int = 64):
        self.refs: Dict[str, List[np.ndarray]] = {}
        self.n_pts = n_pts
        for ch, lst in instances.items():
            keep = [normalise(shape_points([np.asarray(s, float) for s in strokes if len(s)], n_pts))
                    for strokes in lst[:max_per_letter] if any(len(s) >= 2 for s in strokes)]
            if keep:
                self.refs[ch] = keep
        self.letters = "".join(sorted(self.refs))

    def classify(self, strokes: Sequence[np.ndarray]) -> Tuple[str, Dict[str, float]]:
        q = normalise(shape_points([np.asarray(s, float) for s in strokes if len(s)], self.n_pts))
        d = {c: min(dtw(q, r) for r in refs) for c, refs in self.refs.items()}
        return min(d, key=d.get), d

    def covers(self, text: str) -> bool:
        return all(c in self.refs for c in text if c != " ")


def accuracy_on(reader: WriterReader, letters: Sequence[Tuple[str, Sequence[np.ndarray]]]) -> float:
    """Share of (char, strokes) pairs read as their char."""
    ok = [reader.classify(s)[0] == c for c, s in letters if c in reader.refs]
    return float(np.mean(ok)) if ok else float("nan")
