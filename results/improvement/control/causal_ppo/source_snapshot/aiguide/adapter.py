"""Text-predictor interface: the local n-gram model and a larger-model adapter specification.

Every predictor the template pipeline or the autocorrect uses must provide
``glyph_ahead(text, d)`` - the distribution of the d-th next written glyph
(spaces are gaps, not glyphs) - with a *calibrated* top-1 probability, because
that probability sets the stage authority (ICD s5 rule 5: c = min(1, c_hat /
c_full)).  The local n-gram model (``aiguide.lm.TextPredictor``) is the
reference implementation and runs everywhere offline.

``LLMPredictorSpec`` specifies, and does not implement, an adapter to a
larger language model, on the phone or in the cloud.  No API key is available
here and nothing in this package opens a network connection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, Sequence, Tuple, runtime_checkable

import numpy as np


@runtime_checkable
class TextPredictorProtocol(Protocol):
    model_id: str
    is_local: bool

    def glyph_ahead(self, text: str, d: int = 1) -> np.ndarray:
        """Calibrated distribution over ``aiguide.corpus.LM_ALPHABET`` of the d-th next glyph."""

    def next_words(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        """Top-k next words before any of their letters is written."""

    def complete_word(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        """Top-k completions of the partial word at the end of ``text``."""


class NgramAdapter:
    """The local reference predictor behind the protocol (character KN + word KN, Tatoeba CC0)."""
    model_id = "aiguide.ngram-kn7"
    is_local = True

    def __init__(self, pred=None):
        from .lm import cached_predictor
        self.pred = pred or cached_predictor()

    def glyph_ahead(self, text: str, d: int = 1) -> np.ndarray:
        return self.pred.glyph_ahead(text, d)

    def next_words(self, text: str, k: int = 3):
        return self.pred.next_words(text, k)

    def complete_word(self, text: str, k: int = 3):
        return self.pred.complete_word(text, k)


@dataclass(frozen=True)
class LatencyBudget:
    """End-to-end budget for a letter template (s).  Values are allocations, not measurements."""
    template_lead: float = 0.30          # config/pencil.yaml ai.template_lead
    ble_uplink: float = 0.030            # stroke samples batched per connection event (7.5-15 ms interval + batching)
    recognition: float = 0.060           # on-phone letter/word recogniser (unmeasured; EXP-C01 must measure it)
    prediction: float = 0.050            # predictor call, p95 (the n-gram model: a few ms)
    synthesis: float = 0.010             # style-conditioned template
    ble_downlink: float = 0.030          # one to two connection events
    pen: float = 0.002                   # parse, anchor, resample to the stage rate

    def total(self) -> float:
        return self.ble_uplink + self.recognition + self.prediction + self.synthesis + self.ble_downlink + self.pen

    def margin(self) -> float:
        return self.template_lead - self.total()


@dataclass
class LLMPredictorSpec:
    """SPECIFICATION of an adapter to a larger language model.  Not runnable here.

    Mapping from a token-level model to the glyph distribution
      * Condition on the recognised text so far (the note line, plus up to the
        last N characters of earlier lines as context).  Never send ink, timing,
        force or tremor data: text only (app/README.md, privacy).
      * Next-character distribution: sum the probabilities of all vocabulary
        tokens whose decoded string starts with the partial word + c, for every
        glyph c ("token healing": back off to the last complete word boundary
        so a partial word is not forced into one token).  Needs top-k logprobs
        (k >= 50) from the model; an API that returns only sampled text cannot
        supply a calibrated confidence and must not drive the stage.
      * Glyph depth d: beam over the first d-1 characters exactly as
        ``aiguide.lm.TextPredictor.glyph_ahead`` does, skipping spaces.
      * Calibration: temperature per depth fitted on held-out text *of the
        user's own notes* (the Tatoeba-calibrated n-gram is over-confident on
        note text: ECE 0.15 on the synthetic note lines, results/ai/text_predictor.json).
      * Mixing: p = w * p_LLM + (1 - w) * p_ngram, w chosen on validation, so the
        lexicon and the user's personal dictionary still act.
    Latency (see ``LatencyBudget``)
      * on-phone model: the depth-2 glyph distribution must return within
        50 ms p95 to leave margin in the 0.3 s template lead; a model that cannot
        is used only for word-level prediction (depth >= 3) and for autocorrect;
      * cloud model: network round trips of hundreds of ms leave no margin at
        letter level; cloud use is for autocorrect and next-word suggestions
        only, after explicit consent (``penapp.grounded.CloudConsent``), with a
        timeout that falls back to the local n-gram model.
    Safety
      * The adapter's confidence goes through the same rule 5 as the n-gram's;
        a timeout, an error, or a missing calibration gives c_hat = 0 (no template).
    """
    model_id: str = "llm-spec"
    locality: str = "on_phone"            # on_phone | cloud
    is_local: bool = True
    min_logprobs_top_k: int = 50
    p95_latency_budget_s: float = 0.050
    requires_consent: bool = False
    notes: Dict = field(default_factory=dict)

    def glyph_ahead(self, text: str, d: int = 1) -> np.ndarray:
        raise NotImplementedError("specification only: no large model is available in this repository")

    def next_words(self, text: str, k: int = 3):
        raise NotImplementedError("specification only")

    def complete_word(self, text: str, k: int = 3):
        raise NotImplementedError("specification only")


CLOUD_LLM_SPEC = LLMPredictorSpec(model_id="cloud-llm-spec", locality="cloud", is_local=False,
                                  p95_latency_budget_s=0.600, requires_consent=True,
                                  notes={"use": "autocorrect and next-word suggestions only; never letter templates"})
PHONE_LLM_SPEC = LLMPredictorSpec(model_id="phone-llm-spec", locality="on_phone", is_local=True,
                                  p95_latency_budget_s=0.050,
                                  notes={"use": "letter templates only if the p95 latency and calibration are met"})


def time_predictor(pred, contexts: Sequence[str], d: int = 2) -> Dict[str, float]:
    """Wall-clock time per glyph_ahead call of the local model (this machine; CALCULATION)."""
    import time
    ts = []
    for c in contexts:
        t0 = time.perf_counter()
        pred.glyph_ahead(c, d)
        ts.append(time.perf_counter() - t0)
    a = np.array(ts)
    return {"n": len(a), "median_ms": float(np.median(a) * 1e3), "p95_ms": float(np.percentile(a, 95) * 1e3)}
