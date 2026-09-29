"""Language models reused from the earlier studies (read-only code), rebuilt or loaded into ai3/build.

NG0   aiguide's calibrated Tatoeba CC0 predictor (character 7-gram KN + word bigram KN), loaded from aiguide/build
      (read-only; aiguide rebuilds it into its own build folder only if it is missing).
NG1x  the ai2 'NG1' recipe rebuilt here: the same model family on Tatoeba train + Common Voice CC0 sentence text
      (sentence-collector.txt + 200 000 hashed wiki.en.txt sentences, split 90/5/5 by sha256 as ai2 did, with ai2's
      leakage filter).  ai2 did not store NG1, so it is rebuilt (CALC) and cached in ai3/build/cache.
"""
from __future__ import annotations

import hashlib
import pickle
import shutil
import time
from pathlib import Path
from typing import Dict, List, Tuple

from . import RAW_DIR, REPO_ROOT, ensure_paths
from .common import cache_dir, log, sha256_file

ensure_paths()

CV_BASE = "https://raw.githubusercontent.com/common-voice/common-voice/main/server/data/en/"
CV_FILES = ("sentence-collector.txt", "wiki.en.txt")
CV_LICENCE = ("CC0 1.0 (Common Voice README: sentence text in /server/data from the Sentence Collector or the Wikipedia "
              "extractor is released under CC0; ledger EML-65)")


def ng0():
    from aiguide import lm
    return lm.cached_predictor()


def cv_file(name: str) -> Tuple[Path, Dict]:
    """A Common Voice text file in ai3/build/raw: copied from ai2's local snapshot if present (same bytes), else
    downloaded."""
    import urllib.request
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    p = RAW_DIR / name
    src = "download"
    if not p.exists():
        loc = REPO_ROOT / "ai2" / "build" / "corpora" / name
        if loc.exists():
            shutil.copyfile(loc, p)
            src = f"copy of {loc.relative_to(REPO_ROOT)}"
        else:
            tmp = p.with_suffix(".part")
            with urllib.request.urlopen(CV_BASE + name, timeout=600) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            tmp.replace(p)
    return p, {"file": name, "url": CV_BASE + name, "source": src, "sha256": sha256_file(p), "bytes": p.stat().st_size,
               "licence": CV_LICENCE}


def _bucket(s: str) -> int:
    return int(hashlib.sha256(f"cv:{s}".encode()).hexdigest()[:8], 16) % 100


def cv_splits(max_wiki: int = 200_000):
    """ai2.textpred.cv_splits, with the files read from ai3/build/raw (identical rule)."""
    from aiguide import corpus as ACO
    prov = []
    out = {"train": [], "val": [], "test": []}
    seen = set()
    for n in CV_FILES:
        p, pv = cv_file(n)
        prov.append(pv)
        norm = []
        for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = ACO.normalize(ln)
            if len(s) >= 8 and s not in seen:
                seen.add(s)
                norm.append(s)
        if n.startswith("wiki") and len(norm) > max_wiki:
            norm = sorted(norm, key=lambda s: hashlib.sha256(s.encode()).hexdigest())[:max_wiki]
        for s in norm:
            b = _bucket(s)
            out["test" if b < 5 else "val" if b < 10 else "train"].append(s)
    return out, {"files": prov, "max_wiki": max_wiki, **{f"n_{k}": len(v) for k, v in out.items()}}


def ng1x(quick: bool = False):
    """Build (or load) NG1x.  Returns (predictor, info)."""
    from aiguide import corpus as ACO, lm
    from aiguide.sentences import APP_NOTE_LINES, EXTRA_NOTE_LINES, GUIDE_SENTENCE
    tag = "ng1x_quick" if quick else "ng1x"
    p = cache_dir(quick) / f"{tag}.pkl"
    if p.exists():
        with open(p, "rb") as f:
            obj = pickle.load(f)
        return obj["pred"], obj["info"]
    t0 = time.time()
    tat = ACO.make_splits()
    cv, info = cv_splits(max_wiki=20_000 if quick else 200_000)
    notes0 = APP_NOTE_LINES + EXTRA_NOTE_LINES + [GUIDE_SENTENCE]
    held = set(ACO.normalize(x) for x in list(tat.val) + list(tat.test) + notes0)
    cv_train = [x for x in cv["train"] if x not in held]
    train = list(tat.train) + cv_train
    log(f"[lm] building NG1x on {len(train)} sentences ...")
    pred = lm.build_predictor(ACO.Splits(train, tat.val, [], {"note": "ai3 NG1x (ai2 NG1 recipe)"}), order=7)
    pred.word._cache.clear()
    info.update({"n_train_sentences": len(train), "cv_train_removed": len(cv["train"]) - len(cv_train),
                 "build_s": time.time() - t0, "lambda": pred.lam, "T": pred.T, "vocab": len(pred.word.vocab),
                 "char_ngrams": int(pred.char.n_params())})
    with open(p, "wb") as f:
        pickle.dump({"pred": pred, "info": info}, f, protocol=pickle.HIGHEST_PROTOCOL)
    log(f"[lm] NG1x built in {info['build_s']:.0f} s: {info['vocab']} words, {info['char_ngrams']} n-grams")
    return pred, info


def cv_test_sentences(quick: bool = False) -> List[str]:
    cv, _ = cv_splits(max_wiki=20_000 if quick else 200_000)
    return cv["test"]
