"""Spot check of task 4b with study R's word reader (lead's note, 2026-09-29): the saved sample words of the shape-assist
test (the same words without and with the assist, and the writer's own clean letters) read by TrOCR, the literal
"words you can read" judge that study R chose on its tuning notes (realdata.ocr.reader_choice: TrOCR base, greedy, no
lexicon; MIT code licence, model card without a licence, used locally as a measuring instrument; ledger EML-80).

Why task 4b's main numbers use another reader: the assist's tuning rule (A1) counts letters it makes unreadable, which
needs a per-letter reader; TrOCR reads whole words and its decoder carries a language prior that can complete a damaged
word.  This check makes the two studies' numbers comparable on the words the report shows.  CALC on SIM output; post hoc.
"""
from __future__ import annotations

import time
from typing import Dict

import numpy as np

from . import common as C


def run(quick: bool) -> Dict:
    t0 = time.time()
    sh = C.load("shape", quick)
    if sh is None or not sh.get("samples"):
        raise RuntimeError("the shape stage (with samples) must run first")
    from realdata import ocr as OC
    choice = OC.reader_choice(log=C.log)
    samples = sh["samples"][: 24 if quick else 60]
    rows = []
    imgs, keys = [], []
    for i, smp in enumerate(samples):
        for panel in ("intended", "none", "assist"):
            strokes = [np.asarray(s, float) * 1e-3 for let in smp[panel] for s in let if len(s) >= 2]
            imgs.append(OC.render(strokes)); keys.append((i, panel))
    read = OC.read_images(imgs)
    by = {}
    for (i, panel), txt in zip(keys, read):
        by.setdefault(i, {})[panel] = txt
    for i, smp in enumerate(samples):
        w = smp["word"]
        r = {p: OC._norm(by[i].get(p, "")) for p in ("intended", "none", "assist")}
        rows.append({"word": w, "cond": smp["cond"], "writer": smp["writer"], **{f"read_{p}": r[p] for p in r},
                     **{f"ok_{p}": r[p] == w for p in r},
                     **{f"cer_{p}": OC.cer(w, r[p]) for p in r}})
    agg = {}
    for cond in sorted({r["cond"] for r in rows}):
        sel = [r for r in rows if r["cond"] == cond]
        agg[cond] = {"words": len(sel), **{f"read_{p}": float(np.mean([r[f"ok_{p}"] for r in sel])) for p in ("intended", "none", "assist")},
                     **{f"cer_{p}": float(np.mean([r[f"cer_{p}"] for r in sel])) for p in ("intended", "none", "assist")}}
    out = {"reader": choice.get("chosen"), "reader_reliable": choice.get("reliable"), "rows": rows, "aggregate": agg,
           "all": {f"read_{p}": float(np.mean([r[f"ok_{p}"] for r in rows])) for p in ("intended", "none", "assist")},
           "minutes": (time.time() - t0) / 60}
    C.save("ocr", out, quick)
    C.log(f"[ocr] {len(rows)} sample words read by {out['reader']}: intended {out['all']['read_intended']:.2f}, "
          f"none {out['all']['read_none']:.2f}, assist {out['all']['read_assist']:.2f}")
    return out
