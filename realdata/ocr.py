"""'Words you can read': a handwriting-reading AI stands in for a person reading the ink (CALC on SIM output).

The simulated ink of each line is drawn as black 0.5 mm ballpoint ink on white paper and read by TrOCR (Li et al.
2021, arXiv 2109.10282; the small model fine-tuned on the IAM handwriting database, microsoft/trocr-small-handwritten
on Hugging Face; code MIT licence in microsoft/unilm; the model card states no licence; used locally as a measuring
instrument and never redistributed).  It has never seen these writers.  A word counts as read when the reader's word
equals the intended word (lower case, punctuation removed) after a word-level edit-distance alignment of the line.

Why not the HW1 study's reader: aiguide's recogniser matches the synthetic glyph font; on real writing it misreads
clean letters, and real letters with delayed strokes (t-bars, i-dots) break its per-letter time windows.

Reported with every result: the words read on the TREMOR-FREE ink of the same writing (the reader's own ceiling).
Dependencies (private copies in realdata/build/pydeps, not the system site-packages): transformers 4.46.3,
tokenizers 0.20.3, huggingface_hub 0.26.5, safetensors 0.4.5, sentencepiece 0.2.0, regex, tqdm; torch (system).
"""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import BUILD_DIR

PYDEPS = BUILD_DIR / "pydeps"
HF_HOME = BUILD_DIR / "hf"
MODEL = "microsoft/trocr-small-handwritten"
PX_PER_MM = 10.0            # rendering resolution
INK_MM = 0.5                # ballpoint line width (ASSUMPTION)
MARGIN_MM = 2.0


def _paths():
    os.environ.setdefault("HF_HOME", str(HF_HOME))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if str(PYDEPS) not in sys.path:
        sys.path.append(str(PYDEPS))


def available() -> bool:
    _paths()
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(MODEL, local_files_only=True)
        import transformers  # noqa: F401
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def _model():
    _paths()
    import torch
    torch.set_num_threads(1)
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from huggingface_hub import snapshot_download
    p = snapshot_download(MODEL, local_files_only=True)
    proc = TrOCRProcessor.from_pretrained(p, use_fast=False)
    model = VisionEncoderDecoderModel.from_pretrained(p)
    model.eval()
    return proc, model


# ------------------------------------------------------------------ rendering
def render(strokes: Sequence[np.ndarray], px_per_mm: float = PX_PER_MM, ink_mm: float = INK_MM,
           margin_mm: float = MARGIN_MM):
    """PIL image of polylines (m, page frame y up) as black ink on white."""
    from PIL import Image, ImageDraw
    pts = [np.asarray(s, float) * 1e3 for s in strokes if len(s) >= 2]
    if not pts:
        return Image.new("RGB", (64, 32), "white")
    allp = np.vstack(pts)
    x0, y0 = allp.min(0) - margin_mm
    x1, y1 = allp.max(0) + margin_mm
    W = int(np.ceil((x1 - x0) * px_per_mm)) + 1
    H = int(np.ceil((y1 - y0) * px_per_mm)) + 1
    im = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(im)
    w = max(1, int(round(ink_mm * px_per_mm)))
    for s in pts:
        xy = [((p[0] - x0) * px_per_mm, (y1 - p[1]) * px_per_mm) for p in s]
        dr.line(xy, fill=0, width=w, joint="curve")
        r = w / 2.0
        for (cx, cy) in (xy[0], xy[-1]):
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    return im.convert("RGB")


def ink_lines(res, written, line_of_letter: Sequence[int], decim: int = 4) -> List[List[np.ndarray]]:
    """In-contact ink strokes of a run grouped by the line of each letter (by time: from the first to the last
    sample of the line's letters, delayed strokes included)."""
    t = res.t
    ink = res.ink
    con = res.contact > 0.5
    lines: Dict[int, Tuple[float, float]] = {}
    for Lt, li in zip(written.letters, line_of_letter):
        if not Lt.strokes:
            continue
        a, b = lines.get(li, (np.inf, -np.inf))
        lines[li] = (min(a, Lt.t0), max(b, Lt.t1))
    out = []
    for li in sorted(lines):
        a, b = lines[li]
        m = (t >= a - 0.02) & (t <= b + 0.02) & con
        idx = np.flatnonzero(m)
        if len(idx) < 2:
            out.append([])
            continue
        br = np.flatnonzero(np.diff(idx) > 1) + 1
        out.append([ink[r][::decim] for r in np.split(idx, br) if len(r) >= 2])
    return out


# ------------------------------------------------------------------ reading and scoring
def _norm(w: str) -> str:
    return re.sub(r"[^a-z]", "", w.lower())


def read_images(images) -> List[str]:
    import torch
    proc, model = _model()
    out = []
    with torch.no_grad():
        for im in images:
            pv = proc(images=im, return_tensors="pt").pixel_values
            ids = model.generate(pv, max_new_tokens=32, num_beams=1)
            out.append(proc.batch_decode(ids, skip_special_tokens=True)[0])
    return out


def align_words(target: Sequence[str], read: Sequence[str]) -> List[bool]:
    """Word-level Levenshtein alignment; True where a target word is matched exactly by an aligned read word."""
    a = [_norm(w) for w in target]
    b = [_norm(w) for w in read if _norm(w)]
    n, m = len(a), len(b)
    D = np.zeros((n + 1, m + 1), int)
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (0 if a[i - 1] == b[j - 1] else 1))
    ok = [False] * n
    i, j = n, m
    while i > 0 and j > 0:
        if D[i, j] == D[i - 1, j - 1] + (0 if a[i - 1] == b[j - 1] else 1):
            ok[i - 1] = a[i - 1] == b[j - 1]
            i, j = i - 1, j - 1
        elif D[i, j] == D[i - 1, j] + 1:
            i -= 1
        else:
            j -= 1
    return ok


def words_read(res, written, cache: Optional[Dict] = None) -> Dict:
    """Words read by the AI reader in one run: per line, the rendered ink is read and aligned with the line's words."""
    lines_text = written.real.get("lines") if hasattr(written, "real") else None
    if not lines_text:
        lines_text = [written.text]
    # line index of each letter: by word index, from the per-line word counts
    wl = []
    for li, ln in enumerate(lines_text):
        wl += [li] * len(ln.split())
    lol = [wl[min(Lt.word_index, len(wl) - 1)] for Lt in written.letters]
    strokes = ink_lines(res, written, lol)
    imgs = [render(s) for s in strokes]
    read = read_images(imgs)
    ok, tot = 0, 0
    per = []
    for ln, rd in zip(lines_text, read):
        m = align_words(ln.split(), rd.split())
        ok += sum(m)
        tot += len(m)
        per.append({"target": ln, "read": rd, "ok": [bool(x) for x in m]})
    return {"words_read": ok, "words_total": tot, "share": ok / max(tot, 1), "lines": per}
