"""Stage text (task 4): next-letter and next-word prediction on CC0 text; n-gram vs a small transformer.

Evidence status: CALCULATION on public-domain text (Tatoeba CC0, Common Voice CC0 sentences).  Latency is measured on
this container's CPU (one thread, shared machine) and counted (MAC) for an MCU; nothing ran on a pen or a phone.
Choices (the mixture weight, the transformer checkpoint) use the Tatoeba validation split; the test splits are used
once for the tables.
"""
from __future__ import annotations

import json
import time
from typing import Dict

import numpy as np

from . import BUILD_DIR, ensure_paths
from . import common as C
from . import textpred as TP

ensure_paths()
from aiguide import lm  # noqa: E402
from aiguide.sentences import APP_NOTE_LINES, EXTRA_NOTE_LINES, GUIDE_SENTENCE  # noqa: E402

TF_CFG = {"n_layer": 3, "d_model": 128, "n_head": 4, "ctx": 128}       # 3 x 192 ran at ~4 k tokens/s on one shared thread
                                                                         # (quick run): too few tokens in the time box
TF_CFG_SMALL = {"n_layer": 2, "d_model": 96, "n_head": 4, "ctx": 64}      # the pen-MCU class
MCU_HZ = 128e6


def mcu_latency_ms(macs: int, n_layers: int, int8: bool = True) -> float:
    """CALC (fusion/budget.py convention, ASSUMPTION): int8 CMSIS-NN 0.5 MAC/cycle + 300 cycles per layer call;
    float32 2 cycles per MAC."""
    cyc = macs / 0.5 + 300 * (4 * n_layers + 1) if int8 else macs * 2.0
    return cyc / MCU_HZ * 1e3


def run(quick: bool, workers: int):
    import torch
    torch.set_num_threads(1)
    t_all = time.time()
    tat = TP.tatoeba_splits()
    cv, cv_info = TP.cv_splits(max_wiki=20_000 if quick else 200_000)
    C.log(f"[text] tatoeba train {len(tat.train)} val {len(tat.val)} test {len(tat.test)}; cv {cv_info['n_train']}/{cv_info['n_val']}/{cv_info['n_test']}")
    out = {"corpora": {"tatoeba": tat.info, "common_voice": cv_info}, "models": {}, "eval": {}}
    # --- models
    t0 = time.time()
    ng0 = lm.cached_predictor()
    out["models"]["NG0"] = {"what": "aiguide Tatoeba n-gram (char 7-gram KN + word bigram KN), as used so far",
                            "n_params": int(ng0.char.n_params()), "vocab": len(ng0.word.vocab)}
    # no test leakage: drop from the Common Voice training text every sentence that is in a Tatoeba validation or test
    # split or among the evaluated app note lines and the study sentence; drop from the Common Voice test split every
    # sentence in the Tatoeba training split (NG0 was trained on it)
    from aiguide import corpus as ACO
    notes0 = APP_NOTE_LINES + EXTRA_NOTE_LINES + [GUIDE_SENTENCE]
    held = set(ACO.normalize(x) for x in list(tat.val) + list(tat.test) + notes0)
    cv_train = [x for x in cv["train"] if x not in held]
    tat_train = set(ACO.normalize(x) for x in tat.train)
    cv["test"] = [x for x in cv["test"] if x not in tat_train]
    out["corpora"]["leakage_filter"] = {"cv_train_removed": len(cv["train"]) - len(cv_train), "cv_test_kept": len(cv["test"]),
                                        "rule": "CV train minus (Tatoeba val/test, app note lines, study sentence); CV test minus Tatoeba train"}
    C.log(f"[text] leakage filter: {out['corpora']['leakage_filter']}")
    train_sents = list(tat.train) + cv_train
    t0 = time.time()
    ng1 = TP.build_ngram(train_sents, tat.val)
    out["models"]["NG1"] = {"what": "the same n-gram family on Tatoeba + Common Voice training text",
                            "n_params": int(ng1.char.n_params()), "vocab": len(ng1.word.vocab),
                            "train_chars": int(sum(len(s) + 1 for s in train_sents)), "build_s": time.time() - t0,
                            "lambda": ng1.lam, "T": ng1.T}
    C.log(f"[text] NG1 built in {time.time() - t0:.0f} s ({ng1.char.n_params()} n-grams, {len(ng1.word.vocab)} words)")
    # --- transformer (time-boxed, one thread)
    rng = np.random.default_rng(0)
    tr_ids = TP.encode_stream(list(rng.permutation(np.array(train_sents, dtype=object))))
    va_ids = TP.encode_stream(tat.val)
    models = {}
    for name, cfg, minutes in (("TF", TF_CFG, 3.0 if quick else 30.0), ("TF_small", TF_CFG_SMALL, 1.5 if quick else 10.0)):
        m, info = TP.train_transformer(tr_ids, va_ids, cfg, minutes=minutes, log=C.log)
        torch.save(m.state_dict(), BUILD_DIR / f"{name.lower()}.pt")
        info["macs_per_char"] = TP.macs_per_char(cfg)
        info["mcu_ms_per_char_int8"] = mcu_latency_ms(info["macs_per_char"], cfg["n_layer"])
        info["weights_kB_int8"] = info["n_params"] / 1024.0
        info["weights_kB_float32"] = 4 * info["n_params"] / 1024.0
        out["models"][name] = info
        models[name] = m
        C.log(f"[text] {name}: {info['n_params']} parameters, {info['tokens'] / 1e6:.1f} M tokens in {info['minutes']:.0f} min, "
              f"best val {info['best_val_bpc_sampled']:.3f} bpc")
    tf = TP.TFPredictor(models["TF"])
    tfs = TP.TFPredictor(models["TF_small"])
    # --- mixture weight on Tatoeba validation (glyph two ahead, NLL)
    best = None
    for w in (0.3, 0.5, 0.7):
        mix = TP.TFPredictor(models["TF"], mix=(ng1, w))
        r = TP.evaluate(mix, tat.val, n_glyph=200 if quick else 400, n_word=0, seed=11)
        nll = r["glyph_d2"]["nll_bits"]
        C.log(f"[text] mixture weight {w}: glyph-2 NLL {nll:.3f} bits, top-1 {r['glyph_d2']['top1']:.3f}")
        if best is None or nll < best[1]:
            best = (w, nll)
    out["mixture_weight"] = best[0]
    mix = TP.TFPredictor(models["TF"], mix=(ng1, best[0]))
    preds = {"NG0": ng0, "NG1": ng1, "TF": tf, "TF_small": tfs, "MIX": mix}
    word_fns = {"NG0": lambda c: ng0.next_words(c, k=5), "NG1": lambda c: ng1.next_words(c, k=5)}
    # --- test sets (used once)
    notes = APP_NOTE_LINES + EXTRA_NOTE_LINES
    # evaluation sizes bounded for compute (the transformer's glyph-two-ahead query costs ~0.1-0.2 s on one shared
    # CPU thread); the same positions for every model (same seed)
    sets = {"tatoeba_test": (tat.test, 300 if quick else 1500, 60 if quick else 300),
            "common_voice_test": (cv["test"], 150 if quick else 800, 40 if quick else 200),
            "note_lines": (notes, None, None), "study_sentence": ([GUIDE_SENTENCE], None, None)}
    for name, pred in preds.items():
        out["eval"][name] = {}
        for sname, (sents, ng, nw) in sets.items():
            t0 = time.time()
            if name == "TF_small" and nw is not None:
                nw = 0                                   # the MCU-class model is scored on letters only
            r = TP.evaluate(pred, sents, n_glyph=ng, n_word=nw, seed=5, word_fn=word_fns.get(name))
            r["bpc"] = TP.char_bpc(pred, sents, n=1000) if ng else None
            r["seconds"] = time.time() - t0
            out["eval"][name][sname] = r
            C.log(f"[text] {name} {sname}: glyph-2 top1 {r['glyph_d2']['top1']:.3f} top3 {r['glyph_d2']['top3']:.3f} "
                  f"next-word top1 {r['next_word']['top1']:.3f} top3 {r['next_word']['top3']:.3f} ({r['seconds']:.0f} s)")
    out["minutes_total"] = (time.time() - t_all) / 60.0
    C.save("text", out, quick)
    return out
