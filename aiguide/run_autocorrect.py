#!/usr/bin/env python3
"""B3 digital autocorrect in the app: WER before and after, over-correction, rare words.

Evidence status: CALCULATION on SYNTHETIC sessions (app/penapp/synth.py glyph
handwriting of known text) with recognition errors injected by
``penapp.recognize.ErrorInjectingRecognizer`` at target CER 2-15 %; the
language model is trained on public-domain text (Tatoeba CC0 training split).
No real ink and no real recogniser are involved.

Text sets
  in_domain   60 held-out Tatoeba test-split sentences (4-9 words)
  notes       the 18 synthetic note lines of aiguide/sentences.py (out of the corpus domain)
  rare        10 synthetic lines with names and rare words (out of the lexicon)
Decision thresholds 0.5-0.97 are swept; the default (0.9) is the app's.
A 'personal dictionary' variant adds the rare lines' names to the lexicon,
as if they came from the user's contacts or earlier accepted notes.

Outputs results/ai/autocorrect.json, fig_autocorrect.png, autocorrect_rerender.svg.
Run: python3 -m aiguide.run_autocorrect  (about 3 min)
"""
from __future__ import annotations

import argparse
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import EVIDENCE_CALC, RESULTS_DIR, corpus, ensure_paths
from .sentences import APP_NOTE_LINES, EXTRA_NOTE_LINES, RARE_LINES
from stabpen import plotstyle, provenance

ensure_paths()
from penapp import autocorrect as AC  # noqa: E402
from penapp import recognize  # noqa: E402
from penapp._util import FixedClock  # noqa: E402
from penapp.cli import import_log_file  # noqa: E402
from penapp.notes import NoteStore  # noqa: E402
from penapp.synth import synth_text_session  # noqa: E402

CERS = (0.02, 0.05, 0.10, 0.15)
SEEDS = (0, 1, 2, 3, 4)
THRESHOLDS = (0.5, 0.7, 0.9, 0.97)
DEFAULT_T = 0.9


def in_domain_lines(n=60, seed=0):
    sp = corpus.make_splits()
    rng = np.random.default_rng(seed)
    pool = []
    for s in sp.test:
        t = " ".join(w for w in (tok.strip(".,:-/") for tok in s.split()) if w and all(c in corpus.LETTERS + "'" for c in w))
        if 4 <= len(t.split()) <= 9 and t.count("'") == 0:
            pool.append(t)
    return [pool[i] for i in rng.choice(len(pool), n, replace=False)]


def build_sessions(sets, workdir):
    """Write each set as synthetic sessions of 6 lines and import them into one note store."""
    store = NoteStore(Path(workdir) / "store", clock=FixedClock("2026-09-27T12:00:00.000Z"))
    notes = defaultdict(list)
    sid = 100
    for name, lines in sets.items():
        for i in range(0, len(lines), 6):
            chunk = lines[i:i + 6]
            ses = synth_text_session(chunk, seed=sid, session_id=sid)
            log = Path(workdir) / f"{name}_{sid}.penlog"
            ses.write(log, truth_path=log.with_suffix(".truth.json"), meta_path=log.with_suffix(".meta.json"))
            info = import_log_file(store, log)
            notes[name].append((info["note_id"], log.with_suffix(".truth.json"), chunk))
            sid += 1
    return store, notes


def decide(corr, threshold):
    """Re-apply the decision rule at another threshold from the stored posteriors."""
    out = []
    for c in corr:
        pre, core, suf = AC._split_token(c.observed.lower())
        best, pbest = c.alternatives[0]
        chosen = core
        if core and core.isalpha() and best != core and pbest >= threshold:
            chosen = best
        out.append(pre + chosen + suf if chosen != core else c.observed)
    return out


def evaluate(store, notes, model, cer, seed, lex):
    """Word-level outcomes for every threshold (posteriors computed once per line)."""
    rows = defaultdict(lambda: defaultdict(float))
    ac = AC.Autocorrector(model, cer=cer, threshold=0.0)
    achieved = []
    for nid, truth_path, lines in notes:
        base = recognize.GroundTruthRecognizer.from_file(truth_path)
        inj = recognize.ErrorInjectingRecognizer(base, cer, seed=seed)
        res = inj.recognize(store.original_for_note(nid), None)
        achieved.append(res.params["achieved_cer_vs_base"])
        words = defaultdict(list)
        for s in res.spans:
            if s["level"] == "word":
                words[s["parent"]].append(s["text"])
        for li, ref in enumerate(lines):
            hyp = words.get(f"l{li}", [])
            refw = ref.lower().split()
            if len(hyp) != len(refw):
                continue
            corr = ac.correct_tokens(hyp)
            for T in THRESHOLDS:
                out = decide(corr, T)
                r = rows[T]
                r["ref_words"] += len(refw)
                r["edits_before"] += recognize.levenshtein(refw, hyp)
                r["edits_after"] += recognize.levenshtein(refw, out)
                r["ref_chars"] += len(ref)
                r["char_edits_before"] += recognize.levenshtein(ref.lower(), " ".join(hyp))
                r["char_edits_after"] += recognize.levenshtein(ref.lower(), " ".join(out))
                for rw, h, o in zip(refw, hyp, out):
                    ok_b, ok_a = h == rw, o == rw
                    core = rw.strip(".,:-/")
                    rare = not lex(core)
                    r["correct_before"] += ok_b
                    r["wrong_before"] += not ok_b
                    r["fixed"] += (not ok_b) and ok_a
                    r["broken"] += ok_b and not ok_a
                    r["changed"] += h != o
                    r["changed_still_wrong"] += (h != o) and (not ok_b) and (not ok_a)
                    if rare:
                        r["rare_words"] += 1
                        r["rare_correct_before"] += ok_b
                        r["rare_broken"] += ok_b and not ok_a
                        r["rare_wrong_before"] += not ok_b
                        r["rare_fixed"] += (not ok_b) and ok_a
    out = {}
    for T, r in rows.items():
        out[str(T)] = {"wer_before": r["edits_before"] / max(r["ref_words"], 1),
                       "wer_after": r["edits_after"] / max(r["ref_words"], 1),
                       "cer_before": r["char_edits_before"] / max(r["ref_chars"], 1),
                       "cer_after": r["char_edits_after"] / max(r["ref_chars"], 1),
                       "fix_rate": r["fixed"] / max(r["wrong_before"], 1),
                       "over_correction_rate": r["broken"] / max(r["correct_before"], 1),
                       "changed": int(r["changed"]), "fixed": int(r["fixed"]), "broken": int(r["broken"]),
                       "changed_still_wrong": int(r["changed_still_wrong"]), "words": int(r["ref_words"]),
                       "rare_words": int(r["rare_words"]),
                       "rare_preserved_rate": 1 - r["rare_broken"] / max(r["rare_correct_before"], 1),
                       "rare_fix_rate": r["rare_fixed"] / max(r["rare_wrong_before"], 1)}
    return out, float(np.mean(achieved))


def mean_dicts(ds):
    keys = ds[0].keys()
    return {k: (float(np.mean([d[k] for d in ds])) if isinstance(ds[0][k], float) else int(np.sum([d[k] for d in ds])))
            for k in keys}


def figure(res, path):
    import matplotlib.pyplot as plt
    plotstyle.apply()
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    T = str(DEFAULT_T)
    for i, name in enumerate(("in_domain", "notes", "rare")):
        c = plotstyle.SERIES[i]
        d = res["by_set"][name]["lexicon"]
        cer = [d[str(x)]["achieved_cer"] for x in CERS]
        axes[0].plot(cer, [d[str(x)]["thresholds"][T]["wer_before"] for x in CERS], color=c, lw=1.2, ls="--")
        axes[0].plot(cer, [d[str(x)]["thresholds"][T]["wer_after"] for x in CERS], color=c, label=f"{name}: after")
        axes[0].plot(cer, [d[str(x)]["thresholds"][T]["wer_after"] for x in CERS], **plotstyle.marker_kw(c))
        th = [float(t) for t in THRESHOLDS]
        axes[1].plot(th, [d["0.1"]["thresholds"][str(t)]["over_correction_rate"] for t in THRESHOLDS], color=c, label=name)
        axes[1].plot(th, [d["0.1"]["thresholds"][str(t)]["over_correction_rate"] for t in THRESHOLDS], **plotstyle.marker_kw(c))
        axes[2].plot(th, [d["0.1"]["thresholds"][str(t)]["fix_rate"] for t in THRESHOLDS], color=c, label=name)
        axes[2].plot(th, [d["0.1"]["thresholds"][str(t)]["fix_rate"] for t in THRESHOLDS], **plotstyle.marker_kw(c))
    dp = res["by_set"]["rare"]["personal"]
    axes[1].plot([float(t) for t in THRESHOLDS], [dp["0.1"]["thresholds"][str(t)]["over_correction_rate"] for t in THRESHOLDS],
                 color=plotstyle.SERIES[3], ls=":", label="rare + personal dictionary")
    axes[0].set_xlabel("achieved CER of the injected errors")
    axes[0].set_ylabel("WER")
    axes[0].set_title(f"WER before (dashed) and after autocorrect (threshold {DEFAULT_T})", fontsize=9)
    axes[1].set_xlabel("decision threshold (posterior)")
    axes[1].set_title("Over-correction: correct words changed (CER 10 %)", fontsize=9)
    axes[2].set_xlabel("decision threshold (posterior)")
    axes[2].set_title("Fix rate: wrong words made right (CER 10 %)", fontsize=9)
    axes[0].legend(fontsize=7.5)
    axes[1].legend(fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    plotstyle.stamp(fig, "CALCULATION", "synthetic sessions, injected errors; LM on Tatoeba CC0")
    fig.savefig(path)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-in-domain", type=int, default=60)
    args = ap.parse_args(argv)
    t0 = time.time()
    sets = {"in_domain": in_domain_lines(args.n_in_domain), "notes": APP_NOTE_LINES + EXTRA_NOTE_LINES, "rare": RARE_LINES}
    model = AC.NgramWordModel.from_corpus()
    rare_words = sorted({w for l in RARE_LINES for w in l.split() if not model.known(w)})
    with tempfile.TemporaryDirectory() as td:
        store, notes = build_sessions(sets, td)
        res = {"sets": {k: {"n_lines": len(v), "n_words": sum(len(l.split()) for l in v)} for k, v in sets.items()},
               "rare_out_of_lexicon_words": rare_words, "by_set": {}}
        for variant in ("lexicon", "personal"):
            m = model if variant == "lexicon" else AC.NgramWordModel(model.word, model.char, personal=set(rare_words),
                                                                     source=model.source)
            lex = model.known
            for name, nl in notes.items():
                if variant == "personal" and name == "in_domain":
                    continue
                block = {}
                for cer in CERS:
                    per_seed, ach = [], []
                    for seed in SEEDS:
                        r, a = evaluate(store, nl, m, cer, seed, lex)
                        per_seed.append(r)
                        ach.append(a)
                    block[str(cer)] = {"achieved_cer": float(np.mean(ach)),
                                       "thresholds": {t: mean_dicts([ps[t] for ps in per_seed]) for t in per_seed[0]}}
                res["by_set"].setdefault(name, {})[variant] = block
                print(variant, name, {c: round(b["thresholds"][str(DEFAULT_T)]["wer_after"], 3) for c, b in block.items()},
                      f"{time.time() - t0:.0f}s", flush=True)
        # demonstration: layer + re-render on one note (temporary store; results/app is not touched)
        nid, truth, lines = notes["notes"][0]
        base = recognize.GroundTruthRecognizer.from_file(truth)
        recognize.run_recognizer(store, nid, recognize.ErrorInjectingRecognizer(base, 0.10, seed=4))
        demo = AC.autocorrect_note(store, nid, AC.Autocorrector(model, cer=0.10, threshold=DEFAULT_T))
        rr = AC.rerender_words(store, nid, demo)
        AC.rerender_svg(store, nid, rr, RESULTS_DIR / "autocorrect_rerender.svg")
        lay = demo.layer
        res["demo"] = {"lines": lines, "changes": demo.changes, "layer_id": lay["layer_id"], "created_by": lay["created_by"],
                       "inputs": lay["inputs"], "effective_text_recognizer": store.effective_text(nid)["recognizer"],
                       "store_verify_ok": store.verify()["ok"], "rerender_style": rr.get("style"),
                       "rerendered_words": [w["text"] for w in rr.get("words", [])]}
    res["setup"] = {"cer_targets": CERS, "seeds": SEEDS, "thresholds": THRESHOLDS, "default_threshold": DEFAULT_T,
                    "channel": "cer assumed = target CER", "lexicon_min_count": model.min_count, "p_oov": model.p_oov}
    res["meta"] = provenance.metadata(EVIDENCE_CALC + "; synthetic sessions with injected recognition errors",
                                      seeds={"injection": list(SEEDS), "in_domain_sample": 0, "sessions": "100.."},
                                      extra={"corpus_url": corpus.SOURCE["url"], "corpus_licence": corpus.SOURCE["licence"]})
    res["runtime_s"] = round(time.time() - t0, 1)
    provenance.write_json(str(RESULTS_DIR / "autocorrect.json"), res)
    figure(res, RESULTS_DIR / "fig_autocorrect.png")
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
