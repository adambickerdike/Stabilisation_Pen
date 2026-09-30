"""Public-domain text corpus for the text predictor and the autocorrect model.

Source: Tatoeba English sentences released under CC0 1.0 (public-domain
dedication).  The per-language CC0 export is small (1.3 MB compressed,
41.5 k sentences, 3.3 M characters).  A snapshot is kept in aiguide/data/ so
that tests and results never need the network; ``ensure_corpus(download=True)``
re-fetches it (TLS verified through the environment's proxy CA bundle) only if
the snapshot is missing.

Domain caveat: Tatoeba sentences are conversational and example-sentence
English (with a strong "Tom" bias and some opinionated quotations), not
personal notes.  Results on it are a proxy for the user's own text.

Normalisation maps text onto the single-line glyph font of app/penapp/synth.py
(a-z, 0-9, . , : - / ') plus space; '\\n' marks a sentence end for the
character model.
"""
from __future__ import annotations

import bz2
import hashlib
import json
import re
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from . import DATA_DIR

CORPUS_FILE = DATA_DIR / "tatoeba_eng_sentences_CC0.tsv.bz2"
SOURCE = {
    "name": "Tatoeba English sentences, CC0 subset (per-language export eng_sentences_CC0.tsv.bz2)",
    "url": "https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences_CC0.tsv.bz2",
    "downloads_page": "https://tatoeba.org/en/downloads",
    "licence": "CC0 1.0 Universal (public-domain dedication)",
    "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "licence_evidence": ("tatoeba.org/en/downloads, 'Sentences (CC0)': 'Contains all the sentences available "
                         "under CC0.' (checked 2026-09-27); the rest of Tatoeba is CC BY 2.0 FR and is NOT used"),
    "retrieved_utc": "2026-09-27T20:52Z",
    "sha256": "88741ad33d7e71adca99de65b10f592584b6d85f073b8f8c454bc3ae9dab4c2a",
    "bytes": 1288578,
    "format": "TSV: sentence id, lang, text, date last modified",
}

# glyph alphabet of app/penapp/synth.py (single-line font) + space; '\n' = sentence end
LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT = ".,:-/'"
ALPHABET = LETTERS + DIGITS + PUNCT + " "
EOS = "\n"
LM_ALPHABET = ALPHABET + EOS

_MAP = {"?": ".", "!": ".", ";": ",", "—": "-", "–": "-", "’": "'", "‘": "'",
        "`": "'", "_": " ", "&": " and ", "+": " plus ", "%": " percent ", "@": " at "}
_WS = re.compile(r"\s+")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_corpus(download: bool = True) -> Path:
    """Path of the corpus snapshot; download it if missing (and allowed)."""
    if CORPUS_FILE.exists():
        return CORPUS_FILE
    if not download:
        raise FileNotFoundError(f"{CORPUS_FILE} missing and download disabled")
    CORPUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CORPUS_FILE.with_suffix(".part")
    with urllib.request.urlopen(SOURCE["url"], timeout=60) as r, open(tmp, "wb") as f:   # TLS verified
        f.write(r.read())
    tmp.replace(CORPUS_FILE)
    return CORPUS_FILE


def provenance(path=None) -> dict:
    """Source, licence and the digest of the snapshot actually used."""
    path = Path(path or CORPUS_FILE)
    sha = sha256_file(path)
    out = dict(SOURCE)
    out["file"] = str(path.relative_to(DATA_DIR.parent.parent)) if path.is_relative_to(DATA_DIR.parent.parent) else str(path)
    out["sha256_used"] = sha
    out["snapshot_matches_recorded_sha256"] = sha == SOURCE["sha256"]
    return out


def normalize(text: str) -> str:
    """Lower-case ASCII over ALPHABET; unknown symbols become spaces; spaces collapsed."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    out = []
    for c in t.lower():
        c = _MAP.get(c, c)
        if len(c) > 1:
            out.append(c)
        elif c in ALPHABET:
            out.append(c)
        else:
            out.append(" ")
    s = _WS.sub(" ", "".join(out)).strip()
    # punctuation hugs the previous word ("word ." -> "word.")
    s = re.sub(r" ([.,:])", r"\1", s)
    return s


def load_sentences(path=None) -> List[Tuple[int, str]]:
    """(sentence id, raw text) for every English sentence of the snapshot."""
    path = Path(path or ensure_corpus())
    out = []
    with bz2.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3 or parts[1] != "eng":
                continue
            out.append((int(parts[0]), parts[2]))
    return out


def _bucket(sid: int) -> int:
    return int(hashlib.sha256(f"tatoeba:{sid}".encode()).hexdigest()[:8], 16) % 100


@dataclass
class Splits:
    train: List[str]
    val: List[str]
    test: List[str]
    info: Dict

    def text(self, name: str) -> str:
        """Split as one character stream, sentences separated by EOS."""
        return EOS.join(getattr(self, name)) + EOS


def make_splits(sentences: Sequence[Tuple[int, str]] = None, *, val_pct: int = 10, test_pct: int = 10,
                min_chars: int = 2) -> Splits:
    """Deterministic 80/10/10 split by hashed sentence id, after normalisation.

    Exact duplicates (after normalisation) are kept once, in the split of their
    lowest id, so no held-out sentence also occurs in training.
    """
    sentences = sentences if sentences is not None else load_sentences()
    seen = {}
    for sid, raw in sorted(sentences):
        s = normalize(raw)
        if len(s) < min_chars or s in seen:
            continue
        seen[s] = sid
    tr, va, te = [], [], []
    for s, sid in seen.items():
        b = _bucket(sid)
        (te if b < test_pct else va if b < test_pct + val_pct else tr).append(s)
    info = {"n_raw": len(sentences), "n_unique_normalized": len(seen), "n_train": len(tr), "n_val": len(va),
            "n_test": len(te), "chars_train": sum(len(s) + 1 for s in tr), "chars_val": sum(len(s) + 1 for s in va),
            "chars_test": sum(len(s) + 1 for s in te),
            "split_rule": "sha256('tatoeba:<id>') mod 100: <10 test, <20 val, else train; duplicates dropped"}
    return Splits(tr, va, te, info)


def words_of(sentence: str) -> List[str]:
    """Whitespace tokens with surrounding punctuation stripped (apostrophes kept)."""
    out = []
    for tok in sentence.split():
        w = tok.strip(".,:-/")
        if w:
            out.append(w)
    return out


def save_json(path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1))
