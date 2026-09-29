"""Task 4: next-letter and next-word prediction for templates, autowrite and the app (CALCULATION on public text).

Corpora (all public-domain dedications; snapshots in ai2/build/corpora, digests recorded):
  * Tatoeba English, CC0 subset (the snapshot in aiguide/data, split exactly as aiguide does: its test and
    validation splits are the headline test and validation sets here);
  * Mozilla Common Voice English sentence text, server/data/en/sentence-collector.txt and wiki.en.txt.  The Common
    Voice README states that the sentence text in /server/data comes from the Sentence Collector or the Wikipedia
    extractor and is released under CC0 (europarl files are not used).  Split 90/5/5 by a hash of the sentence.

Models:
  NG0   aiguide's calibrated Tatoeba n-gram predictor (character 7-gram KN + word bigram KN), as used so far;
  NG1   the same model family trained on Tatoeba train + Common Voice train (a larger corpus);
  TF    a small character transformer (causal, context 128) trained on the same text, CPU only;
  MIX   TF mixed with NG1 (weight chosen on Tatoeba validation).
Every model is scored on the same positions: the glyph one and two ahead (spaces are gaps, as aiguide), the next word
before its first letter, word completion after 1-3 letters, bits per character; latency and memory are measured here
(this container's CPU, one thread) and counted (MAC) for a pen-class MCU and a phone.
"""
from __future__ import annotations

import bz2
import hashlib
import json
import math
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import BUILD_DIR, ensure_paths

ensure_paths()
from aiguide import corpus as ACO  # noqa: E402
from aiguide import lm  # noqa: E402

CORPUS_DIR = BUILD_DIR / "corpora"
CV_BASE = "https://raw.githubusercontent.com/common-voice/common-voice/main/server/data/en/"
CV_FILES = {"sentence-collector.txt": CV_BASE + "sentence-collector.txt", "wiki.en.txt": CV_BASE + "wiki.en.txt"}
CV_LICENCE = ("CC0 1.0 (Common Voice README, 'Licensing and content source': 'The majority of our sentence text in "
              "/server/data comes directly from user submissions in our Sentence Collector or they are scraped from "
              "Wikipedia using our extractor tool, and are released under a CC0 public domain Creative Commons "
              "license'; europarl-* files excluded)")
V = lm.V
SYM = lm.SYM
ALPH = lm.LM_ALPHABET
SPACE_ID, EOS_ID = lm.SPACE_ID, lm.EOS_ID


# ------------------------------------------------------------------ corpora
def download(name: str, url: str) -> Dict:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    p = CORPUS_DIR / name
    if not p.exists():
        tmp = p.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:     # TLS verified (proxy CA)
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        tmp.replace(p)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {"file": name, "url": url, "bytes": p.stat().st_size, "sha256": h.hexdigest(), "licence": CV_LICENCE,
            "retrieved_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(p.stat().st_mtime))}


def _bucket(s: str) -> int:
    return int(hashlib.sha256(f"cv:{s}".encode()).hexdigest()[:8], 16) % 100


def cv_splits(max_wiki: int = 400_000, seed: int = 0) -> Tuple[Dict[str, List[str]], Dict]:
    """Common Voice sentences, normalised to the glyph alphabet, deduplicated, split 90/5/5 by hash.  The wiki file
    is subsampled to max_wiki sentences (deterministic hash order) to keep the n-gram and training time bounded."""
    prov = [download(n, u) for n, u in CV_FILES.items()]
    out = {"train": [], "val": [], "test": []}
    seen = set()
    n_raw = 0
    for n in CV_FILES:
        lines = (CORPUS_DIR / n).read_text(encoding="utf-8", errors="ignore").splitlines()
        n_raw += len(lines)
        norm = []
        for ln in lines:
            s = ACO.normalize(ln)
            if len(s) >= 8 and s not in seen:
                seen.add(s)
                norm.append(s)
        if n.startswith("wiki") and len(norm) > max_wiki:
            norm = sorted(norm, key=lambda s: hashlib.sha256(s.encode()).hexdigest())[:max_wiki]
        for s in norm:
            b = _bucket(s)
            out["test" if b < 5 else "val" if b < 10 else "train"].append(s)
    info = {"files": prov, "n_raw_lines": n_raw, "max_wiki": max_wiki,
            **{f"n_{k}": len(v) for k, v in out.items()}, **{f"chars_{k}": sum(len(s) + 1 for s in v) for k, v in out.items()},
            "split_rule": "sha256('cv:<normalised sentence>') mod 100: <5 test, <10 val, else train"}
    return out, info


def tatoeba_splits():
    return ACO.make_splits()


# ------------------------------------------------------------------ n-gram (aiguide's model family)
def build_ngram(train: List[str], val: List[str], order: int = 7):
    """aiguide.lm.build_predictor on a custom split (lambda and temperatures fitted on `val`)."""
    sp = ACO.Splits(train, val, [], {"note": "ai2 larger-corpus split"})
    return lm.build_predictor(sp, order=order)


# ------------------------------------------------------------------ character transformer
def _torch():
    import torch
    return torch


def make_transformer(n_layer: int = 3, d_model: int = 192, n_head: int = 4, ctx: int = 128, dropout: float = 0.0):
    torch = _torch()
    nn = torch.nn

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            self.ln1 = nn.LayerNorm(d_model)
            self.att = nn.MultiheadAttention(d_model, n_head, dropout=dropout, batch_first=True)
            self.ln2 = nn.LayerNorm(d_model)
            self.mlp = nn.Sequential(nn.Linear(d_model, 4 * d_model), nn.GELU(), nn.Linear(4 * d_model, d_model))

        def forward(self, x, mask):
            h = self.ln1(x)
            a, _ = self.att(h, h, h, attn_mask=mask, need_weights=False)
            x = x + a
            return x + self.mlp(self.ln2(x))

    class CharTF(nn.Module):
        def __init__(self):
            super().__init__()
            self.ctx = ctx
            self.emb = nn.Embedding(V, d_model)
            self.pos = nn.Embedding(ctx, d_model)
            self.blocks = nn.ModuleList([Block() for _ in range(n_layer)])
            self.ln = nn.LayerNorm(d_model)
            self.head = nn.Linear(d_model, V)
            self.cfg = {"n_layer": n_layer, "d_model": d_model, "n_head": n_head, "ctx": ctx}

        def forward(self, idx):
            T = idx.shape[1]
            mask = torch.triu(torch.full((T, T), float("-inf")), diagonal=1)
            x = self.emb(idx) + self.pos(torch.arange(T))[None]
            for b in self.blocks:
                x = b(x, mask)
            return self.head(self.ln(x))

    return CharTF()


def n_params(model) -> int:
    return int(sum(p.numel() for p in model.parameters()))


def macs_per_char(cfg: Dict, ctx_used: int = 64) -> int:
    """Multiply-accumulates for one new character with a key/value cache (CALC): per layer 4 d^2 (q,k,v,o) + 8 d^2
    (MLP) + 2 d ctx_used (attention scores and values); head V d."""
    d, L = cfg["d_model"], cfg["n_layer"]
    return int(L * (12 * d * d + 2 * d * ctx_used) + V * d)


def encode_stream(sentences: Sequence[str]) -> np.ndarray:
    return lm.encode(lm.EOS.join(sentences) + lm.EOS)


def train_transformer(train_ids: np.ndarray, val_ids: np.ndarray, cfg: Dict, minutes: float = 45.0, batch: int = 48,
                      lr: float = 2e-3, seed: int = 0, threads: int = 1, log: Callable = print) -> Tuple[object, Dict]:
    torch = _torch()
    torch.manual_seed(seed)
    torch.set_num_threads(threads)
    model = make_transformer(**cfg)
    ctx = model.ctx
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01, betas=(0.9, 0.98))
    rng = np.random.default_rng(seed)
    tr = torch.from_numpy(train_ids.astype(np.int64))
    va = torch.from_numpy(val_ids.astype(np.int64))
    t_end = time.time() + minutes * 60.0
    hist = []
    step = 0
    best = (float("inf"), None)
    t0 = time.time()
    tokens = 0

    def val_bpc(n_batches=8):
        model.eval()
        g = np.random.default_rng(123)
        tot, n = 0.0, 0
        with torch.no_grad():
            for _ in range(n_batches):
                ix = g.integers(0, len(va) - ctx - 1, size=32)
                x = torch.stack([va[i:i + ctx] for i in ix]); y = torch.stack([va[i + 1:i + ctx + 1] for i in ix])
                lo = model(x)
                l = torch.nn.functional.cross_entropy(lo.reshape(-1, V), y.reshape(-1), reduction="sum")
                tot += float(l); n += y.numel()
        model.train()
        return tot / n / math.log(2)
    est_steps = None
    while time.time() < t_end:
        # cosine schedule on wall-clock progress (training is time-boxed)
        frac = (time.time() - t0) / (t_end - t0)
        for gp in opt.param_groups:
            gp["lr"] = lr * min(1.0, (step + 1) / 200) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(frac, 1.0))))
        ix = rng.integers(0, len(tr) - ctx - 1, size=batch)
        x = torch.stack([tr[i:i + ctx] for i in ix]); y = torch.stack([tr[i + 1:i + ctx + 1] for i in ix])
        lo = model(x)
        loss = torch.nn.functional.cross_entropy(lo.reshape(-1, V), y.reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        tokens += batch * ctx
        if step % 200 == 0:
            vb = val_bpc()
            hist.append({"step": step, "tokens": tokens, "train_bpc": float(loss) / math.log(2), "val_bpc": vb,
                         "minutes": (time.time() - t0) / 60.0})
            log(f"  [tf] step {step} tokens {tokens / 1e6:.1f}M train {float(loss) / math.log(2):.3f} val {vb:.3f} bpc")
            if vb < best[0]:
                best = (vb, {k: v.detach().clone() for k, v in model.state_dict().items()})
    if best[1] is not None:
        model.load_state_dict(best[1])
    model.eval()
    info = {"cfg": cfg, "steps": step, "tokens": tokens, "minutes": (time.time() - t0) / 60.0, "threads": threads,
            "history": hist, "best_val_bpc_sampled": best[0], "n_params": n_params(model), "batch": batch, "lr": lr}
    return model, info


class TFPredictor:
    """Next-character distributions from the transformer, with the TextPredictor interface used for evaluation
    (raw_dist, glyph_ahead, next_words, complete_word); `mix` = (NG predictor, weight of TF)."""

    def __init__(self, model, mix: Optional[Tuple[object, float]] = None, T: float = 1.0):
        self.model = model
        self.ctx = model.ctx
        self.mix = mix
        self.T = T
        self._cache: Dict[str, np.ndarray] = {}

    def _tf_dist_batch(self, texts: Sequence[str]) -> np.ndarray:
        torch = _torch()
        out = np.zeros((len(texts), V))
        todo = [i for i, t in enumerate(texts) if t[-self.ctx:] not in self._cache]
        if todo:
            ctxs = [lm.EOS + texts[i] if not texts[i].startswith(lm.EOS) else texts[i] for i in todo]
            ids = [lm.encode(c[-self.ctx:]) for c in ctxs]
            L = max(len(a) for a in ids)
            # left-pad with EOS (the model saw EOS-separated sentences)
            X = np.full((len(ids), L), EOS_ID, np.int64)
            for r, a in enumerate(ids):
                X[r, L - len(a):] = a
            with torch.no_grad():
                lo = self.model(torch.from_numpy(X))[:, -1, :]
                p = torch.softmax(lo, dim=-1).numpy()
            for r, i in enumerate(todo):
                self._cache[texts[i][-self.ctx:]] = p[r]
        for i, t in enumerate(texts):
            out[i] = self._cache[t[-self.ctx:]]
        if len(self._cache) > 200_000:
            self._cache.clear()
        return out

    def raw_dist(self, text: str) -> np.ndarray:
        p = self._tf_dist_batch([text])[0]
        if self.mix is not None:
            ng, w = self.mix
            p = w * p + (1 - w) * ng.raw_dist(text)
        return p / p.sum()

    def raw_dist_batch(self, texts: Sequence[str]) -> np.ndarray:
        P = self._tf_dist_batch(texts)
        if self.mix is not None:
            ng, w = self.mix
            P = w * P + (1 - w) * np.stack([ng.raw_dist(t) for t in texts])
        return P / P.sum(axis=1, keepdims=True)

    def dist(self, text: str) -> np.ndarray:
        return lm._temper(self.raw_dist(text), self.T)


# ------------------------------------------------------------------ generic evaluation (any predictor with raw_dist)
def glyph_ahead(pred, text: str, d: int, beam: int = 10) -> np.ndarray:
    """The d-th next glyph (spaces are gaps), marginalised over a beam of character paths (aiguide's definition,
    uncalibrated).  Uses raw_dist_batch when the predictor has it (one batched call per depth step)."""
    out = np.zeros(V)
    paths = [(text, 1.0, 0)]
    batch = getattr(pred, "raw_dist_batch", None)
    for _ in range(2 * d + 1):
        P = batch([t for t, _, _ in paths]) if batch else np.stack([pred.raw_dist(t) for t, _, _ in paths])
        nxt = []
        for (t, w, g), p in zip(paths, P):
            if g == d - 1:
                q = p.copy(); q[SPACE_ID] = 0.0; q[EOS_ID] = 0.0
                out += w * q
                if p[SPACE_ID] > 1e-9 and not t.endswith(" "):
                    nxt.append((t + " ", w * p[SPACE_ID], g))
            else:
                for i in np.argsort(-p)[:beam]:
                    if i == EOS_ID or (i == SPACE_ID and t.endswith(" ")):
                        continue
                    nxt.append((t + ALPH[i], w * p[i], g + (i != SPACE_ID)))
        if not nxt:
            break
        nxt.sort(key=lambda z: -z[1])
        paths = nxt[:beam]
    s = out.sum()
    return out / s if s > 0 else np.full(V, 1.0 / V)


def next_words_beam(pred, text: str, k: int = 5, beam: int = 12, max_len: int = 14) -> List[Tuple[str, float]]:
    """Top-k next words from a character model by beam search to the next word boundary."""
    base = text if (not text or text.endswith(" ")) else text + " "
    beams = [("", 1.0)]
    done: Dict[str, float] = {}
    batch = getattr(pred, "raw_dist_batch", None)
    for _ in range(max_len):
        P = batch([base + s for s, _ in beams]) if batch else np.stack([pred.raw_dist(base + s) for s, _ in beams])
        nxt = []
        for (s, w), p in zip(beams, P):
            for i in np.argsort(-p)[:beam]:
                c = ALPH[i]
                if c in (" ", lm.EOS) or c in ".,:":
                    if s:
                        done[s] = done.get(s, 0.0) + w * p[i]
                else:
                    nxt.append((s + c, w * p[i]))
        if not nxt:
            break
        nxt.sort(key=lambda z: -z[1])
        beams = nxt[:beam]
        if len(done) >= k and min(sorted(done.values(), reverse=True)[:k]) > beams[0][1]:
            break
    items = sorted(done.items(), key=lambda z: -z[1])[:k]
    return items


def word_positions(sentences: Sequence[str], rng: np.random.Generator, n: int) -> List[Tuple[str, str]]:
    """(context ending in a space, next word) pairs; the context is the sentence so far."""
    out = []
    for s in sentences:
        ws = s.split(" ")
        for i in range(1, len(ws)):
            w = ws[i].strip(".,:-/")
            if w and w.replace("'", "").isalpha():
                out.append((" ".join(ws[:i]) + " ", w))
    if n and len(out) > n:
        idx = rng.choice(len(out), size=n, replace=False)
        out = [out[i] for i in idx]
    return out


def evaluate(pred, sentences: Sequence[str], n_glyph: Optional[int] = 2000, n_word: Optional[int] = 800, seed: int = 0,
             word_fn: Optional[Callable] = None) -> Dict:
    """Top-k accuracies: glyph 1 and 2 ahead, next word before its first letter.  n = None: every position;
    n_word = 0: no word evaluation."""
    rng = np.random.default_rng(seed)
    res = {}
    for d in (1, 2):
        pos = lm.glyph_positions(list(sentences), d)
        sel = np.arange(len(pos)) if n_glyph is None else rng.choice(len(pos), size=min(n_glyph, len(pos)), replace=False)
        t0 = time.time()
        P = np.stack([glyph_ahead(pred, pos[i][0], d) for i in sel])
        dt = (time.time() - t0) / len(sel)
        y = np.array([SYM[pos[i][1]] for i in sel])
        order = np.argsort(-P, axis=1)
        res[f"glyph_d{d}"] = {"n": int(len(sel)), "top1": float((order[:, 0] == y).mean()),
                              "top3": float((order[:, :3] == y[:, None]).any(1).mean()),
                              "top5": float((order[:, :5] == y[:, None]).any(1).mean()),
                              "nll_bits": float(-np.mean(np.log2(np.maximum(P[np.arange(len(y)), y], 1e-12)))),
                              "latency_ms": dt * 1e3}
    if n_word == 0:
        return res
    wp = word_positions(sentences, rng, n_word or 0)
    t0 = time.time()
    hits = {1: 0, 3: 0, 5: 0}
    for ctx, w in wp:
        cands = [c for c, _ in (word_fn(ctx) if word_fn else next_words_beam(pred, ctx, k=5))]
        for kk in hits:
            hits[kk] += int(w in cands[:kk])
    res["next_word"] = {"n": len(wp), **{f"top{kk}": v / max(len(wp), 1) for kk, v in hits.items()},
                        "latency_ms": (time.time() - t0) / max(len(wp), 1) * 1e3}
    return res


def char_bpc(pred, sentences: Sequence[str], n: int = 3000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    pos = lm.positions(list(sentences))
    sel = rng.choice(len(pos), size=min(n, len(pos)), replace=False)
    ctxs = [pos[i][0] for i in sel]
    y = np.array([SYM[pos[i][1]] for i in sel])
    batch = getattr(pred, "raw_dist_batch", None)
    if batch:
        P = np.concatenate([batch(ctxs[i:i + 256]) for i in range(0, len(ctxs), 256)])
    else:
        P = np.stack([pred.raw_dist(c) for c in ctxs])
    return float(-np.mean(np.log2(np.maximum(P[np.arange(len(y)), y], 1e-12))))
