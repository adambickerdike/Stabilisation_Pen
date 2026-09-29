"""Stage 'predict' (task 3): personalised text prediction on the user's own notes (CALCULATION).

Journals (Project Gutenberg, public domain) play 'the user's own notes': tuning journals choose the settings (rule P1)
and the offer threshold (rule P2); test journals are scored once.  Each journal's first half is the user's history; the
words after it are predicted in order, the model adapting after every word (never looking ahead).
"""
from __future__ import annotations

import math
import time
from typing import Dict, List

import numpy as np

from . import ensure_paths
from . import common as C
from . import data as D
from . import lmx
from . import predict as PR
from .rules import RULES, rules_sha256

ensure_paths()

TUNE_IDS = (1026, 57393)
TEST_IDS = (11579, 2024)
GRID_LC = (0.0, 0.05, 0.1, 0.2, 0.3)
GRID_HL = (500.0, 5000.0, float("inf"))
GRID_LB = (0.0, 0.2, 0.4)
OFFER_TH = (0.3, 0.4, 0.5, 0.6, 0.7)
T_LETTER = 0.45          # s per handwritten letter (CALC from LIT CON-20 speed and UJI letter paths)
T_LETTER_SLOW = 0.9      # a writer with moderate tremor or PD bradykinesia (ASSUMPTION: 50 % of normal speed, LIT PDT-38)
T_AUTOWRITE = 0.32       # s per letter written by the nose (SIM nose_v2: 3.1 letters/s at 3 mm)
T_ACCEPT = 0.6           # s for the acceptance gesture (ASSUMPTION, rule P2)
T_CHECK = 0.25           # s to read an offer (ASSUMPTION, rule P2)


def split_journal(lines: List[str]):
    h = len(lines) // 2
    return lines[:h], lines[h:]


def acc_only(pred, history, test, max_words):
    """Top-1/3 accuracy (next word and completions) without the letters-saved loops (tuning)."""
    prev = None
    for line in history:
        prev = None
        for w in PR.words_of(line):
            pred.observe(prev, w); prev = w
    hits = {(j, k): 0 for j in (0, 1, 2) for k in (1, 3)}
    n = 0
    lat = []
    for line in test:
        prev = None
        for w in PR.words_of(line):
            if n >= max_words:
                break
            for j in (0, 1, 2):
                t0 = time.perf_counter()
                c = pred.candidates(prev, w[:j], k=3)
                if n % 25 == 0:
                    lat.append((time.perf_counter() - t0) * 1e3)
                for k in (1, 3):
                    hits[(j, k)] += int(w in c[:k])
            pred.observe(prev, w); prev = w; n += 1
        if n >= max_words:
            break
    out = {f"after{j}_top{k}": v / max(n, 1) for (j, k), v in hits.items()}
    out["n_words"] = n
    out["latency_ms_p95"] = float(np.percentile(lat, 95)) if lat else float("nan")
    out["score"] = float(np.mean([out["after0_top3"], out["after1_top3"], out["after2_top3"]]))
    return out


def run(quick: bool) -> Dict:
    t_all = time.time()
    journals = {}
    prov = {}
    for gid in TUNE_IDS + TEST_IDS:
        lines, pv = D.load_journal(gid)
        journals[gid] = lines
        prov[gid] = pv
    bases = {"NG0": lmx.ng0()}
    ng1, ng1_info = lmx.ng1x(quick)
    bases["NG1x"] = ng1
    out = {"journals": prov, "ng1x": ng1_info, "rules_sha256": rules_sha256(),
           "rules": {k: RULES[k] for k in ("P1_personal", "P2_offer")}}
    n_tune = 300 if quick else 1500
    n_test = 500 if quick else 3000
    # ---- rule P1 on the tuning journals
    grid = []
    for bname in bases:
        for lc in GRID_LC:
            for hl in (GRID_HL if lc > 0 else (float("inf"),)):
                for lb in GRID_LB:
                    grid.append((bname, lc, hl, lb))
    if quick:
        grid = [g for g in grid if g[1] in (0.0, 0.1) and g[3] in (0.0, 0.2) and g[2] in (5000.0, float("inf"))]
    tab = []
    for bname, lc, hl, lb in grid:
        rs = []
        for gid in TUNE_IDS:
            hist, test = split_journal(journals[gid])
            p = PR.Predictor(bases[bname], lc=lc, lb=lb, half_life=hl)
            rs.append(acc_only(p, hist, test, n_tune))
        row = {"base": bname, "lc": lc, "half_life": hl, "lb": lb, "score": float(np.mean([r["score"] for r in rs])),
               "latency_ms_p95": float(max(r["latency_ms_p95"] for r in rs)), "per_journal": rs}
        tab.append(row)
        C.log(f"[predict] P1 {bname} lc={lc} hl={hl} lb={lb}: score {row['score']:.4f} ({row['latency_ms_p95']:.1f} ms p95)")
    ok = [r for r in tab if r["latency_ms_p95"] <= 20.0]
    best = max(ok or tab, key=lambda r: r["score"])
    out["P1"] = {"table": tab, "chosen": {k: best[k] for k in ("base", "lc", "half_life", "lb", "score")}}
    C.log(f"[predict] rule P1 -> {out['P1']['chosen']}")
    base_same = max([r for r in tab if r["lc"] == 0 and r["lb"] == 0], key=lambda r: r["score"])
    # ---- rule P2: offer threshold on the tuning journals (chosen settings)
    offers_tune = {}
    for gid in TUNE_IDS:
        hist, test = split_journal(journals[gid])
        p = PR.Predictor(bases[best["base"]], lc=best["lc"], lb=best["lb"], half_life=best["half_life"])
        r = PR.evaluate_stream(p, hist, test, 200 if quick else 800, offer_thresholds=OFFER_TH)
        offers_tune[gid] = r["offers"]
    p2 = {}
    for th in OFFER_TH:
        agg = {k: sum(offers_tune[g][f"{th:g}"][k] for g in TUNE_IDS) for k in ("saved_letters", "offers", "accepted", "total")}
        p2[f"{th:g}"] = {"counts": agg, **PR.time_saved(agg, T_LETTER, T_AUTOWRITE, T_ACCEPT, T_CHECK)}
    th_best = max(OFFER_TH, key=lambda th: p2[f"{th:g}"]["seconds_saved_per_100_letters"])
    out["P2"] = {"table": p2, "p_offer": th_best}
    C.log(f"[predict] rule P2 -> p_offer {th_best}: {p2[f'{th_best:g}']}")
    # ---- TEST journals (rules fixed above)
    res = {}
    configs = {"NG0 (as used so far)": ("NG0", 0.0, float("inf"), 0.0),
               "NG1x (larger corpus)": ("NG1x", 0.0, float("inf"), 0.0),
               "personalised (chosen)": (best["base"], best["lc"], best["half_life"], best["lb"])}
    for gid in TEST_IDS:
        hist, test = split_journal(journals[gid])
        res[str(gid)] = {}
        for name, (bn, lc, hl, lb) in configs.items():
            p = PR.Predictor(bases[bn], lc=lc, lb=lb, half_life=hl)
            r = PR.evaluate_stream(p, hist, test, n_test, offer_thresholds=(th_best,))
            o = r["offers"][f"{th_best:g}"]
            r["time_autowrite_normal"] = PR.time_saved(o, T_LETTER, T_AUTOWRITE, T_ACCEPT, T_CHECK)
            r["time_autowrite_slow_writer"] = PR.time_saved(o, T_LETTER_SLOW, T_AUTOWRITE, T_ACCEPT, T_CHECK)
            res[str(gid)][name] = r
            C.log(f"[predict] test {gid} {name}: next-word top3 {r['after0_top3']:.3f}, after 1 letter {r['after1_top3']:.3f}, "
                  f"letters saved top3 {r['letters_saved_top3']:.3f}, {r['latency_ms_p95']:.1f} ms p95")
        # learning curve: how much history the personalisation needs
        curve = {}
        for nh in ((0, 1000) if quick else (0, 1000, 5000, 20000)):
            hw, k = [], 0
            for line in hist[::-1]:
                if k >= nh:
                    break
                hw.insert(0, line); k += len(PR.words_of(line))
            bn, lc, hl, lb = configs["personalised (chosen)"]
            p = PR.Predictor(bases[bn], lc=lc, lb=lb, half_life=hl)
            curve[str(nh)] = acc_only(p, hw, test, n_test // 2)
        res[str(gid)]["history_curve"] = curve
    # the app's note lines (synthetic, short; the ai2 comparison set) with the chosen settings, no history
    from aiguide.sentences import APP_NOTE_LINES, EXTRA_NOTE_LINES
    from aiguide import corpus as ACO
    notes = [ACO.normalize(x) for x in APP_NOTE_LINES + EXTRA_NOTE_LINES]
    res["note_lines"] = {}
    for name, (bn, lc, hl, lb) in configs.items():
        p = PR.Predictor(bases[bn], lc=lc, lb=lb, half_life=hl)
        res["note_lines"][name] = acc_only(p, [], notes, 10_000)
    out["test"] = res
    out["times"] = {"t_letter": T_LETTER, "t_letter_slow": T_LETTER_SLOW, "t_autowrite": T_AUTOWRITE, "t_accept": T_ACCEPT,
                    "t_check": T_CHECK}
    out["minutes"] = (time.time() - t_all) / 60
    C.save("predict", out, quick)
    return out
