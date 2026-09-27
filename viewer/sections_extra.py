"""AI-guidance and sim-to-real tables for viewer/index.html (rendered at build time).

Reads results/ai/*.json (aiguide, app/penapp/autocorrect.py) and results/s2r/*.json
(s2r).  Missing inputs skip the section.
"""
from __future__ import annotations

from viewer.sections import _e, _load, _section, _table, _tags

SET_LABEL = {"in_domain": "Held-out sentences", "notes": "Note-like lines", "rare": "Lines with names and rare words"}


def _pct(x, nd=0):
    return f"{100 * x:.{nd}f} %"


def autocorrect(root):
    a = _load(root, "results/ai/autocorrect.json")
    if not a:
        return ""
    thr = str(a["setup"]["default_threshold"])
    rows = []
    for sname, lab in SET_LABEL.items():
        v = a["by_set"].get(sname)
        if not v:
            continue
        for mode in ("lexicon", "personal"):
            if mode not in v or (mode == "personal" and sname != "rare"):
                continue
            cells = []
            for c, x in v[mode].items():
                t = x["thresholds"][thr]
                cells.append(f"{_pct(t['wer_before'])} → <b>{_pct(t['wer_after'])}</b>")
            over = max(x["thresholds"][thr]["over_correction_rate"] for x in v[mode].values())
            rows.append([lab + (" + personal dictionary" if mode == "personal" else "")] + cells + [f"≤ {_pct(over, 1)}"])
    cers = [f"CER {100 * x['achieved_cer']:.1f} %" for x in a["by_set"]["in_domain"]["lexicon"].values()]
    demo = ", ".join(f"<code>{_e(c['from'])}</code> → <code>{_e(c['to'])}</code> ({c['posterior']:.2f})" for c in a["demo"]["changes"])
    lede = ("The app corrects the recognised text with a language model and stores the result as a derived layer that cites the "
            "strokes; the ink itself is never changed. Recognition errors are injected at the character error rates shown "
            f"(synthetic sessions, CC0 text). A word is changed only if the corrector is at least {float(thr):.0%} sure. "
            f"Example changes on a shopping-list note, with the corrector's confidence: {demo}.")
    return _section("Digital autocorrect in the app", _tags("CALC"), lede,
                    _table(["Text"] + [f"Word errors, {c}" for c in cers] + ["Correct words changed"], rows, (1, 2, 3, 4, 5)),
                    "results/ai/autocorrect.json (app/penapp/autocorrect.py; docs/ai_guidance.md §6)")


CONFIG_LABEL = {"pencil_P1": "Pencil model P1", "revA": "Rev A limits (M1)", "pencil_like": "Pencil limits (M1)",
                "pencil_0.3N": "Pencil limits, 0.3 N (M1)"}
CONDITIONS = [("neutral", "No guidance"), ("oracle", "Oracle template (the true intended path)"),
              ("ai_correct", "AI template, letter predicted correctly"), ("ai_predicted", "AI prediction, confidence-gated"),
              ("wrong_letter_full", "Wrong letter at full authority")]


def guidance(root):
    g = _load(root, "results/ai/guidance.json")
    if not g or "summary" not in g:
        return ""
    cfgs = [c for c in CONFIG_LABEL if c in g["summary"]]
    rows = []
    for key, lab in CONDITIONS:
        cells = []
        for c in cfgs:
            v = g["summary"][c].get(key, {}).get("path_rms_um", {}).get("mean")
            cells.append("—" if v is None else f"{v:.0f} µm")
        rows.append([lab] + cells)
    be = g.get("breakeven", {}).get("by_config", {})
    lede = ("Path distance from the ink to the intended letters (RMS over synthetic writers and tremor frequencies). "
            "The app predicts letters two ahead, draws them in the writer's estimated style and the pen is pulled toward that "
            "template within its travel. A correctly predicted letter in the writer's style is still about 300 µm from what "
            "they meant, which is where guidance stops paying off; wrong predictions stay bounded by the travel.")
    return _section("Physical guidance toward AI-predicted letters", _tags("SIM"), lede,
                    _table(["Condition"] + [CONFIG_LABEL[c] for c in cfgs], rows, tuple(range(1, len(cfgs) + 1))),
                    "results/ai/guidance.json (aiguide/guidance.py; docs/ai_guidance.md §4)")


def ai(root):
    return guidance(root) + autocorrect(root)


def s2r(root):
    return ""
