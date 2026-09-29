"""Build the prototype page ai3/demo/index.html from ai3/demo/template.html and the study's own models and results.

    python3 -m ai3.demo.build [--quick]

Everything the page needs is inlined (no network): the task-1 recogniser's weights (the chosen causal GRU, trained on
UJI Pen Characters v2, CC BY 4.0), a 20 000-word lexicon counted from the same CC0 sentences as NG1x (Tatoeba train +
Common Voice), the spelling-error channel of task 2 (aggregate edit costs estimated from the Birkbeck corpus; the
corpus itself is not included), one UJI training writer's letters (for 'show me' and the writing plan until the user
has written a letter), an example phrase written with a UJI test writer's real letters, and the tuned settings from
results (rules O2, O4, S2, S3, W2, W3, P2, S4).  Also writes ai3/demo/fixtures.json for the smoke test: 26 real test
letters with the Python model's posteriors, and stroke sets for words.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from ai3 import common as C  # noqa: E402
from ai3 import data as D  # noqa: E402
from ai3 import online as O  # noqa: E402
from ai3 import spell as SP  # noqa: E402

N_LEX = 20000
EXAMPLE = ["we", "went", "to", "the", "libary"]
FIX_WORDS = ["becau", "libary", "because"]


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode()


def model_blob(quick: bool):
    import torch
    from ai3.stage_online import load_model
    m, js = load_model(quick)
    sd = {k: v.detach().numpy() for k, v in m.state_dict().items()}
    return m, js, {"hidden": js["cfg"]["hidden"], "layers": js["cfg"]["layers"], "variant": js.get("variant"),
                   "tensors": {k: {"shape": list(v.shape), "b64": _b64(v)} for k, v in sd.items()}}


def lexicon():
    """Word counts over the NG1x training sentences (Tatoeba train + Common Voice train, CC0), a-z words only."""
    from aiguide import corpus as ACO
    from ai3 import lmx
    tat = ACO.make_splits()
    cv, _ = lmx.cv_splits(max_wiki=200_000)
    from aiguide.sentences import APP_NOTE_LINES, EXTRA_NOTE_LINES, GUIDE_SENTENCE
    held = set(ACO.normalize(x) for x in list(tat.val) + list(tat.test) + APP_NOTE_LINES + EXTRA_NOTE_LINES + [GUIDE_SENTENCE])
    cnt = Counter()
    for s in list(tat.train) + [x for x in cv["train"] if x not in held]:
        for w in s.split():
            if re.fullmatch(r"[a-z]{1,20}", w):
                cnt[w] += 1
    top = [w for w, _ in cnt.most_common(N_LEX)]
    top.sort()
    return top, [int(cnt[w]) for w in top], sum(cnt.values())


def channel_blob():
    from ai3.stage_spell import pair_split
    pairs, _ = D.load_pairs("birkbeck")
    ch = SP.Channel.from_pairs([(w, s) for w, s in pairs if pair_split(w) == "train"])
    idx = [SP.A2I[c] for c in O.LETTERS]
    rules = []
    for be, lst in ch.rules.items():
        if not re.fullmatch(r"[a-z]{1,3}", be):
            continue
        for al, cost, st, en in lst:
            if re.fullmatch(r"[a-z]{1,3}", al):
                rules.append([be, al, round(float(cost), 3), int(st), int(en)])
    return {"sub": np.round(ch.sub[np.ix_(idx, idx)], 3).tolist(),
            "del": np.round(ch.dele[idx], 3).tolist(),
            "ins": np.round(ch.ins[np.ix_(idx + [SP.BOS], idx)], 3).tolist(),     # row 26 = at the word start
            "match": np.round(ch.match_cost[idx], 4).tolist(),
            "rules": rules, "pairs_used": ch.info["pairs_used"]}


def char_bigram(words, counts):
    """P(next letter | previous letter) over the lexicon, frequency-weighted, with start (26) and end (26) symbols."""
    M = np.full((27, 27), 0.5)
    for w, c in zip(words, counts):
        prev = 26
        for ch in w:
            M[prev, O.L2I[ch]] += c
            prev = O.L2I[ch]
        M[prev, 26] += c
    return np.round(np.log(M / M.sum(1, keepdims=True)), 4).tolist()


def letters_xh(quick: bool):
    letters, _ = D.load_uji()
    xh = O.writer_xheights(letters)
    return letters, xh


def _strokes_rounded(st, n_max=48):
    out = []
    for s in st:
        s = np.asarray(s, float)
        if len(s) > n_max:
            s = O._resample(s, max(np.hypot(*np.diff(s, axis=0).T).sum() / (n_max - 1), 1e-6))
        out.append(np.round(s, 3).tolist())
    return out


def settings(quick: bool):
    S = {"tau_commit": 0.9, "cal_a": 0.5, "cal_tau": 0.05, "alpha": 0.063, "p_oov": 0.03, "theta": 0.9,
         "theta_w": 0.99, "lam_r": 1.0, "T": 1.0, "theta_c": 0.9, "p_s": 0.3, "T_s": 1.0, "p_offer": 0.3,
         "cue_default": "pause_offer", "reach_mm": 6.0, "reserve_mm": 0.5, "xh_mm": 3.0, "v_max_mm_s": 30.0,
         "from_results": []}
    on = C.load("online", quick) or {}
    if on.get("O2"):
        S["tau_commit"] = on["O2"].get("tau", S["tau_commit"]); S["from_results"].append("O2")
    cal = C.load("online_cal", quick) or {}
    if cal.get("O4"):
        S["cal_a"], S["cal_tau"] = cal["O4"]["a"], cal["O4"]["tau"]; S["from_results"].append("O4")
    sp = C.load("spell_NG1x", quick) or {}
    if sp.get("S2"):
        S["alpha"], S["p_oov"], S["theta"] = sp["alpha"], sp["S2"]["p_oov"], sp["S2"]["theta"]
        S["theta_w"] = sp.get("S3", {}).get("theta_w", S["theta_w"]); S["from_results"] += ["S2", "S3"]
    wd = C.load("words", quick) or {}
    blk = (wd.get("spelling") or {}).get("independent")
    if blk:
        S["lam_r"], S["T"], S["theta_c"] = blk["W2"]["lambda_r"], blk["W2"]["T"], blk["W2"]["theta_c"]
        S["p_s"], S["T_s"] = blk["W3"]["p_s"], blk["W3"]["T_s"]; S["from_results"] += ["W2", "W3"]
    pr = C.load("predict", quick) or {}
    if pr.get("P2", {}).get("p_offer") is not None:
        S["p_offer"] = pr["P2"]["p_offer"]; S["from_results"].append("P2")
    cu = C.load("cues", quick) or {}
    if cu.get("S4", {}).get("recommended"):
        S["cue_recommended_by_S4"] = cu["S4"]["recommended"]; S["from_results"].append("S4")
    return S


def facts(quick: bool):
    """Headline numbers for the page's 'what the study found' box (with evidence labels)."""
    F = []
    on = C.load("online", quick) or {}
    cal = C.load("online_cal", quick) or {}
    t = on.get("test", {}).get("clean", {})
    if t.get("top1"):
        F.append({"k": "Letters read at the end of the letter (new writers)", "v": f"{100 * t['top1'][-1]:.0f} %",
                  "label": "SIM on real UJI letters"})
    c = cal.get("test", {}).get("clean", {})
    if c.get("top1"):
        F.append({"k": "... after one calibration sample per letter (other session)", "v": f"{100 * c['top1'][-1]:.0f} %",
                  "label": "SIM on real UJI letters"})
    wd = C.load("words", quick) or {}
    tw = (wd.get("test_words") or {}).get("normal") or {}
    b = (wd.get("W1") or {}).get("beta_w")
    for key, name in (("independent|beta=0", "new writer, no language model"),
                      (f"independent|beta={b:g}" if b is not None else "", "new writer, with language model"),
                      (f"calibrated|beta={b:g}" if b is not None else "", "calibrated, with language model")):
        if key in tw:
            F.append({"k": f"Words read wrong ({name})", "v": f"{100 * tw[key]['wer']:.0f} %",
                      "label": "SIM, real letters, assumed spacing"})
    sp = C.load("spell_NG1x", quick) or {}
    s = (sp.get("test") or {}).get("score")
    if s:
        F.append({"k": "Misspellings caught (children's real errors)", "v": f"{100 * s['detection_rate']:.0f} %",
                  "label": f"CALC, {s['fa_per_100_correct']:.1f} false alarms per 100 correct words"})
    return F


def example_and_fixtures(letters, xh, m):
    """The example phrase (UJI test writer, session 1) and fixtures (session 2 letters with Python posteriors)."""
    test_w = sorted({L.writer for L in letters if O.split_of(L.writer) == "test"})
    by = {(L.writer, L.rep, L.char): L for L in letters}
    full = [w for w in test_w if all((w, 1, c) in by and (w, 2, c) in by for c in O.LETTERS)]
    need = sorted(set("".join(EXAMPLE)))

    def n_read(w):                                   # the example shows the interface: a writer whose letters it reads
        F = [O.encode([np.asarray(s) / xh[w] for s in by[(w, 1, c)].strokes], 1.0)[0] for c in need]
        return sum(int(O.LETTERS[int(np.argmax(p[-1]))] == c) for p, c in zip(O.posteriors(m, F), need))
    w = max(full, key=lambda q: (n_read(q), -full.index(q)))
    ex = [{"word": word, "letters": [{"char": c, "strokes": _strokes_rounded([np.asarray(s) / xh[w] for s in by[(w, 1, c)].strokes], 64)}
                                     for c in word]} for word in EXAMPLE]
    fx = []
    for c in O.LETTERS:
        st = [np.asarray(s) / xh[w] for s in by[(w, 2, c)].strokes]
        F, _ = O.encode(st, 1.0)
        p = O.posteriors(m, [F])[0][-1]
        fx.append({"char": c, "strokes": [np.asarray(s).round(4).tolist() for s in st], "p": np.round(p, 5).tolist(),
                   "top1": O.LETTERS[int(np.argmax(p))]})
    words = {word: [{"char": c, "strokes": [np.asarray(s).round(4).tolist() for s in
                                            [np.asarray(q) / xh[w] for q in by[(w, 1, c)].strokes]]} for c in word]
             for word in FIX_WORDS}
    return w, ex, {"writer": w, "letters": fx, "words": words}


def templates(letters, xh):
    """One UJI training writer's letters (session 1), for 'show me' and writing plans."""
    tr = sorted({L.writer for L in letters if O.split_of(L.writer) == "train"})
    by = {(L.writer, L.rep, L.char): L for L in letters}
    w = next(w for w in tr if all((w, 1, c) in by for c in O.LETTERS))
    return w, {c: _strokes_rounded([np.asarray(s) / xh[w] for s in by[(w, 1, c)].strokes]) for c in O.LETTERS}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    m, js, model = model_blob(a.quick)
    words, counts, total = lexicon()
    letters, xh = letters_xh(a.quick)
    ex_writer, example, fixtures = example_and_fixtures(letters, xh, m)
    t_writer, tpl = templates(letters, xh)
    data = {"model": model, "lexicon": {"words": "\n".join(words), "counts": counts, "total_tokens": total},
            "channel": channel_blob(), "char_bigram": char_bigram(words, counts), "templates": tpl,
            "example": example, "settings": settings(a.quick), "facts": facts(a.quick),
            "provenance": {"uji_template_writer": t_writer, "uji_example_writer": ex_writer,
                           "built_quick": a.quick}}
    tpl_html = (HERE / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = tpl_html.replace("/*__DATA__*/null", blob)
    if html == tpl_html:
        raise SystemExit("template placeholder /*__DATA__*/null not found")
    out = HERE / ("index_quick.html" if a.quick else "index.html")
    out.write_text(html, encoding="utf-8")
    (HERE / ("fixtures_quick.json" if a.quick else "fixtures.json")).write_text(json.dumps(fixtures))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB); settings from {data['settings']['from_results']}")


if __name__ == "__main__":
    main()
