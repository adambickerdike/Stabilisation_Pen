"""Recogniser interface, reference implementations and evaluation metrics.

Implementations
---------------
``NullRecognizer``            records that no recognition was performed.
``GroundTruthRecognizer``     passthrough of the known transcript of a SYNTHETIC
                              session (not a recogniser; CER = 0 by construction).
                              Exercises every downstream component.
``ErrorInjectingRecognizer``  wraps another recogniser and corrupts words to a
                              target character error rate: the CER-band stress
                              test recommended in the OPT research notes (2.4).
``MLKitDigitalInkAdapter``    specification of an adapter to Google ML Kit
                              Digital Ink Recognition (on-device, Android/iOS).
                              Not runnable here; its stroke mapping is.

Every recogniser produces a ``recognition`` derived layer whose spans (line
and word) link to stroke-id ranges of the original layer; the original is
never touched.  See app/README.md for the evaluation protocol (CER/WER,
writer-disjoint splits, dataset licence constraints).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Sequence, runtime_checkable

import numpy as np

from . import __version__
from ._util import file_sha256, ids_from_ranges, ranges_from_ids
from .notes import NoteStore, OriginalLayer


@dataclass
class RecognitionResult:
    spans: List[dict]
    language: Optional[str]
    evidence_status: str
    params: dict = field(default_factory=dict)
    extra_inputs: List[dict] = field(default_factory=list)
    used_segmentation: bool = False


@runtime_checkable
class Recognizer(Protocol):
    recognizer_id: str
    version: str

    def recognize(self, original: OriginalLayer, segmentation: Optional[dict]) -> RecognitionResult:
        """Return line/word text spans linked to stroke-id ranges of ``original``."""


# ------------------------------------------------------------------ metrics
def levenshtein(a: Sequence, b: Sequence) -> int:
    """Edit distance (unit-cost substitution, insertion, deletion)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    """Character error rate = edit distance / reference length."""
    return levenshtein(ref, hyp) / max(len(ref), 1)


def wer(ref: str, hyp: str) -> float:
    r = ref.split()
    return levenshtein(r, hyp.split()) / max(len(r), 1)


def evaluate_lines(ref_lines: Sequence[str], hyp_lines: Sequence[str]) -> dict:
    """Corpus CER/WER over aligned lines (micro-averaged: summed edits / summed length)."""
    n = max(len(ref_lines), len(hyp_lines))
    ref = list(ref_lines) + [""] * (n - len(ref_lines))
    hyp = list(hyp_lines) + [""] * (n - len(hyp_lines))
    ce = sum(levenshtein(r, h) for r, h in zip(ref, hyp))
    cn = sum(len(r) for r in ref)
    we = sum(levenshtein(r.split(), h.split()) for r, h in zip(ref, hyp))
    wn = sum(len(r.split()) for r in ref)
    return {"cer": ce / max(cn, 1), "wer": we / max(wn, 1), "char_edits": ce, "ref_chars": cn,
            "word_edits": we, "ref_words": wn, "n_lines": n}


# ------------------------------------------------------------ implementations
def _bbox(original: OriginalLayer, ranges) -> List[int]:
    return original.bbox_um(ids_from_ranges(ranges))


class NullRecognizer:
    recognizer_id = "penapp.recognize.null"
    version = __version__

    def recognize(self, original: OriginalLayer, segmentation: Optional[dict] = None) -> RecognitionResult:
        return RecognitionResult(spans=[], language=None,
                                 evidence_status="no recognition performed (null recogniser)")


class GroundTruthRecognizer:
    """Known-transcript passthrough for synthetic sessions (NOT a recogniser).

    ``truth`` = {"lines": [{"text", "words": [{"text", "stroke_ranges"}]}]} as
    written by ``penapp.synth``.  Word links come from the generator; boxes are
    computed from the stored original.  Strokes lost to log corruption are
    dropped from the links and reported in ``params``.
    """
    recognizer_id = "penapp.recognize.groundtruth"
    version = __version__

    def __init__(self, truth: dict, *, truth_sha256: Optional[str] = None, truth_name: str = ""):
        self.truth = truth
        self.truth_sha256 = truth_sha256
        self.truth_name = truth_name

    @classmethod
    def from_file(cls, path) -> "GroundTruthRecognizer":
        with open(path, encoding="utf-8") as f:
            truth = json.load(f)
        return cls(truth, truth_sha256=file_sha256(path), truth_name=Path(path).name)

    def recognize(self, original: OriginalLayer, segmentation: Optional[dict] = None) -> RecognitionResult:
        present = original.stroke_ids
        spans: List[dict] = []
        dropped = []
        for li, line in enumerate(self.truth["lines"]):
            words = []
            for wi, w in enumerate(line["words"]):
                ids = [i for i in ids_from_ranges(w["stroke_ranges"]) if i in present]
                if not ids:
                    dropped.append(w["text"])
                    continue
                r = ranges_from_ids(ids)
                words.append({"span_id": f"l{li}.w{wi}", "level": "word", "parent": f"l{li}",
                              "text": w["text"], "stroke_ranges": r, "bbox_um": _bbox(original, r),
                              "confidence": None})
            if not words:
                continue
            lr = ranges_from_ids(i for w in words for i in ids_from_ranges(w["stroke_ranges"]))
            spans.append({"span_id": f"l{li}", "level": "line", "text": " ".join(w["text"] for w in words),
                          "stroke_ranges": lr, "bbox_um": _bbox(original, lr), "confidence": None})
            spans.extend(words)
        params = {"truth_file": self.truth_name, "dropped_words": dropped}
        extra = ([{"type": "external_file", "sha256": self.truth_sha256, "role": "synthetic ground-truth transcript",
                   "name": self.truth_name}] if self.truth_sha256 else [])
        return RecognitionResult(spans=spans, language=self.truth.get("language", "en"),
                                 evidence_status=("GROUND-TRUTH PASSTHROUGH of a synthetic transcript; "
                                                  "not recogniser output, CER = 0 by construction"),
                                 params=params, extra_inputs=extra)


class ErrorInjectingRecognizer:
    """Corrupt a base recogniser's words to a target CER (seeded, deterministic).

    Each character of each word is independently substituted (p = 0.6 cer),
    deleted (p = 0.2 cer) or followed by an inserted character (p = 0.2 cer),
    so the expected edit count per word character is ``cer``.  Spaces are never
    corrupted and a substitution can redraw the same letter, so the line-level
    CER is somewhat lower; the achieved CER against the base output is
    measured and reported in ``params`` (use it, not the target, in analyses).
    """
    recognizer_id = "penapp.recognize.inject_errors"
    version = __version__

    def __init__(self, base: Recognizer, cer: float, seed: int = 0,
                 alphabet: str = "abcdefghijklmnopqrstuvwxyz"):
        if not 0.0 <= cer <= 1.0:
            raise ValueError("cer must be in [0, 1]")
        self.base = base
        self.cer = float(cer)
        self.seed = int(seed)
        self.alphabet = alphabet

    def _corrupt(self, word: str, rng: np.random.Generator) -> str:
        out = []
        for ch in word:
            u = rng.random()
            if u < 0.6 * self.cer:
                out.append(self.alphabet[rng.integers(len(self.alphabet))])
            elif u < 0.8 * self.cer:
                continue
            elif u < self.cer:
                out.append(ch)
                out.append(self.alphabet[rng.integers(len(self.alphabet))])
            else:
                out.append(ch)
        return "".join(out) or word[:1]

    def recognize(self, original: OriginalLayer, segmentation: Optional[dict] = None) -> RecognitionResult:
        base = self.base.recognize(original, segmentation)
        rng = np.random.default_rng(self.seed)
        spans = [dict(s) for s in base.spans]
        for s in spans:
            if s["level"] == "word":
                s["text"] = self._corrupt(s["text"], rng)
                s["confidence"] = None
        by_parent: Dict[str, List[dict]] = {}
        for s in spans:
            if s["level"] == "word" and s.get("parent"):
                by_parent.setdefault(s["parent"], []).append(s)
        ref_lines, hyp_lines = [], []
        for s, b in zip(spans, base.spans):
            if s["level"] == "line":
                s["text"] = " ".join(w["text"] for w in by_parent.get(s["span_id"], []))
                ref_lines.append(b["text"])
                hyp_lines.append(s["text"])
        ev = evaluate_lines(ref_lines, hyp_lines)
        params = {"base": f"{self.base.recognizer_id}@{self.base.version}", "target_cer": self.cer,
                  "seed": self.seed, "achieved_cer_vs_base": round(ev["cer"], 4),
                  "achieved_wer_vs_base": round(ev["wer"], 4), **{f"base_{k}": v for k, v in base.params.items()}}
        return RecognitionResult(spans=spans, language=base.language,
                                 evidence_status=f"SYNTHETIC ERROR INJECTION (target CER {self.cer}) over: "
                                                 + base.evidence_status,
                                 params=params, extra_inputs=base.extra_inputs,
                                 used_segmentation=base.used_segmentation)


def run_recognizer(store: NoteStore, note_id: str, recognizer: Recognizer) -> dict:
    """Run ``recognizer`` on a stored note and append a recognition layer."""
    note = store.get_note(note_id)
    orig = store.get_original(note["original_sha256"])
    segs = store.list_layers(note_id=note_id, kind="segmentation")
    seg = segs[-1] if segs else None
    res = recognizer.recognize(orig, seg)
    used = sorted({i for s in res.spans for i in ids_from_ranges(s["stroke_ranges"])})
    inputs = [{"type": "original", "sha256": orig.sha256, **({"stroke_ranges": ranges_from_ids(used)} if used else {})}]
    if seg is not None and res.used_segmentation:
        inputs.append({"type": "layer", "layer_id": seg["layer_id"]})
    inputs.extend(res.extra_inputs)
    return store.add_layer(kind="recognition", note_ids=[note_id],
                           created_by=f"{recognizer.recognizer_id}@{recognizer.version}", inputs=inputs,
                           payload={"language": res.language, "evidence_status": res.evidence_status,
                                    "spans": res.spans},
                           params=res.params)


# --------------------------------------------------- on-device adapter (spec)
class MLKitDigitalInkAdapter:
    """SPECIFICATION of an adapter to Google ML Kit Digital Ink Recognition.

    Not runnable in this repository (the SDK is an Android/iOS library); the
    data mapping ``to_ink`` is implemented and tested so a mobile client can
    reproduce it exactly.

    Mapping (ML Kit API names as documented by Google, research ledger OPT-20)
      * Recognise per segmentation *line* span (fallback: per word span).  One
        ``Ink`` per span, built with ``Ink.builder()``; one ``Ink.Stroke`` per
        logged stroke id in the span, points in writing order.
      * Point = ``Ink.Point.create(x, y, t)``: x, y floats in millimetres of the
        page frame with **y negated** (ML Kit uses screen coordinates, y down);
        t = session ``start_unix_ms`` + ``t_ms`` (epoch milliseconds).
      * ``RecognitionContext``: ``WritingArea(width_mm, height_mm)`` of the span
        box; ``preContext`` = last 20 characters of the preceding effective text.
      * Model: ``DigitalInkRecognitionModelIdentifier.fromLanguageTag("en-US")``,
        downloaded once through ``RemoteModelManager`` (about 20 MB per
        language); recognition then runs on-device and offline.
      * Result: ``RecognitionResult.getCandidates()``; take candidate 0.  ML Kit
        returns text (and optionally a score that is not a calibrated
        probability) without per-character stroke alignment, so the whole
        span's stroke ranges are linked to the text.  Word spans are produced
        only when the number of recognised words equals the number of
        segmentation word spans on the line (left-to-right alignment);
        otherwise the layer holds line spans only.
      * Provenance: ``created_by = "mlkit.digitalink@<sdk version>"``;
        ``params = {"model": <language tag>, "model_version": ..., "context": ...}``.
    Privacy and licence
      * Google publishes no accuracy figures for ML Kit Digital Ink; our CER/WER
        must be measured with the protocol in app/README.md before any claim.
      * ML Kit sends performance metrics to Google; the app must disclose this
        and obtain the user's consent before enabling the adapter.  Use falls
        under the Google APIs Terms of Service.
    """
    recognizer_id = "mlkit.digitalink"
    version = "spec"

    def __init__(self, language_tag: str = "en-US", *, user_consented_to_vendor_metrics: bool = False):
        self.language_tag = language_tag
        self.consented = user_consented_to_vendor_metrics

    @staticmethod
    def to_ink(original: OriginalLayer, stroke_ids: Sequence[int], start_unix_ms: int) -> dict:
        """Stroke samples -> ML Kit Ink structure (x, y in mm with y down; t in epoch ms)."""
        s = original.samples
        want = set(int(i) for i in stroke_ids)
        strokes = []
        for sid, a, b in original.stroke_runs:
            if sid not in want:
                continue
            strokes.append({"stroke_id": int(sid), "points": [
                {"x": float(s["x_um"][k]) / 1000.0, "y": -float(s["y_um"][k]) / 1000.0,
                 "t": int(start_unix_ms) + int(s["t_ms"][k])} for k in range(a, b)]})
        return {"strokes": strokes}

    @staticmethod
    def writing_area(bbox_um: Sequence[float]) -> dict:
        return {"width": (bbox_um[2] - bbox_um[0]) / 1000.0, "height": (bbox_um[3] - bbox_um[1]) / 1000.0}

    def recognize(self, original: OriginalLayer, segmentation: Optional[dict] = None) -> RecognitionResult:
        if not self.consented:
            raise PermissionError("ML Kit sends usage metrics to Google: obtain explicit user consent first")
        raise NotImplementedError("ML Kit Digital Ink runs only inside an Android/iOS client; "
                                  "this class documents the adapter contract")
