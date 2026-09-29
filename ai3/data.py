"""Real public data used by the study: downloads (with provenance) and parsers.

Everything is downloaded into ai3/build/raw/ (git-ignored) through the environment's HTTPS proxy (TLS verified).
Nothing here is redistributed; results carry only statistics and a few short quoted examples.

Datasets (licence as stated by the source when the file was retrieved; 'not stated' where the page states none):
  uji2        UJI Pen Characters v2, UCI ML repository (Prat, Castro, Llorens, Marzal, Vilar), CC BY 4.0.
              60 writers (40 'trn', 20 'tst'), 2 repetitions of 97 characters; x/y points of each stroke, no time.
  chartraj    UCI Character Trajectories (Williams 2008), CC BY 4.0.  One writer, 2858 single-stroke characters,
              pen-tip velocity at 200 Hz (differentiated, smoothed, normalised).
  birkbeck    Mitton's 'birkbeck' file: 36,133 misspellings of 6,136 words from the native-speaker section of the
              Birkbeck spelling error corpus (spelling tests and free writing of schoolchildren, university students
              and adult literacy students; mostly handwritten).  Download page states no licence; the full corpus is
              at the Oxford Text Archive (OTA 0643).
  holbrook    Mitton's tagged Holbrook passages: writing of secondary-school children in their next-to-last school
              year (Holbrook, 'English for the Rejected', CUP 1964), every misspelling tagged with its target.
              Download page states no licence (put into machine-readable form with the permission of the author and
              CUP, per the page).
  aspell, wikipedia   Mitton's reformatted Aspell test list and Wikipedia common-misspellings list (secondary).
  journals    Project Gutenberg public-domain journals and diaries (US public domain; Project Gutenberg licence),
              used as 'the user's own notes' for personalisation: Grossmith 'The Diary of a Nobody' (1026),
              Thoreau 'Journal 01, 1837-1846' (57393) [tuning]; Scott 'Scott's Last Expedition, Volume I' (11579),
              Jerome 'Diary of a Pilgrimage' (2024) [test].
"""
from __future__ import annotations

import html
import re
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import RAW_DIR
from .common import log, sha256_file

MITTON = "https://titan.dcs.bbk.ac.uk/~roger/"
DATASETS: Dict[str, Dict] = {
    "uji2": {"url": "https://archive.ics.uci.edu/static/public/177/uji+pen+characters+version+2.zip",
             "file": "uji2.zip", "sha256": "0881b522911b99d9922820289441b50fd3d307f71cd7f9cc70e86872424a5f90",
             "licence": "CC BY 4.0 (UCI dataset page)", "ledger": "CON-48",
             "citation": "Prat F, Castro MJ, Llorens D, Marzal A, Vilar JM. UJI Pen Characters (Version 2). UCI Machine "
                         "Learning Repository, 2009. doi:10.24432/C5GS5V"},
    "chartraj": {"url": "https://archive.ics.uci.edu/static/public/175/character+trajectories.zip",
                 "file": "chartraj.zip", "sha256": "5d2db017ef0d8cf0e65ed060c9e90399f78eb9f1e3cb63e22ca8c3ef4ba67d52",
                 "licence": "CC BY 4.0 (UCI dataset page)", "ledger": "CON-25",
                 "citation": "Williams BH. Character Trajectories. UCI Machine Learning Repository, 2008. doi:10.24432/C58G7V"},
    "birkbeck": {"url": MITTON + "missp.dat", "file": "mitton_missp.dat", "sha256": None,
                 "licence": "not stated on the download page (corpora of misspellings, R. Mitton, Birkbeck); full corpus at "
                            "the Oxford Text Archive (OTA 0643)",
                 "citation": "Mitton R. Birkbeck spelling error corpus (native-speaker section, amalgamated 'birkbeck' file). "
                             "https://titan.dcs.bbk.ac.uk/~roger/corpora.html"},
    "holbrook": {"url": MITTON + "holbrook-tagged.dat", "file": "mitton_holbrook-tagged.dat", "sha256": None,
                 "licence": "not stated on the download page; passages from Holbrook D. English for the Rejected, CUP 1964, "
                            "machine-readable with the permission of the author and CUP (download page)",
                 "citation": "Holbrook D. English for the Rejected. Cambridge University Press, 1964; tagged by R. Mitton, "
                             "https://titan.dcs.bbk.ac.uk/~roger/corpora.html"},
    "holbrook_missp": {"url": MITTON + "holbrook-missp.dat", "file": "mitton_holbrook-missp.dat", "sha256": None,
                       "licence": "as holbrook", "citation": "as holbrook"},
    "aspell": {"url": MITTON + "aspell.dat", "file": "mitton_aspell.dat", "sha256": None,
               "licence": "not stated on the download page (derived from Atkinson's GNU Aspell test list)",
               "citation": "Mitton R., reformatted from the GNU Aspell test list (Atkinson) as used by Deorowicz & Ciura"},
    "wikipedia": {"url": MITTON + "wikipedia.dat", "file": "mitton_wikipedia.dat", "sha256": None,
                  "licence": "not stated on the download page (derived from Wikipedia's list of common misspellings, "
                             "CC BY-SA)", "citation": "Mitton R., reformatted from Wikipedia:Lists of common misspellings"},
}
GUTENBERG = {
    1026: {"title": "The Diary of a Nobody", "author": "G. and W. Grossmith", "year": 1892, "role": "tune"},
    57393: {"title": "Journal 01, 1837-1846", "author": "H. D. Thoreau", "year": 1906, "role": "tune"},
    11579: {"title": "Scott's Last Expedition, Volume I", "author": "R. F. Scott", "year": 1913, "role": "test"},
    2024: {"title": "Diary of a Pilgrimage", "author": "J. K. Jerome", "year": 1891, "role": "test"},
}
for _gid, _g in GUTENBERG.items():
    DATASETS[f"pg{_gid}"] = {"url": f"https://www.gutenberg.org/cache/epub/{_gid}/pg{_gid}.txt", "file": f"pg{_gid}.txt",
                             "sha256": None, "licence": "Public domain in the USA (Project Gutenberg licence)",
                             "citation": f"{_g['author']}. {_g['title']} ({_g['year']}). Project Gutenberg eBook #{_gid}"}


def fetch(name: str, retries: int = 3) -> Tuple[Path, Dict]:
    """Download a dataset file into ai3/build/raw (if missing) and return its path and provenance."""
    d = DATASETS[name]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    p = RAW_DIR / d["file"]
    if not p.exists():
        last = None
        for k in range(retries):
            try:
                tmp = p.with_suffix(p.suffix + ".part")
                req = urllib.request.Request(d["url"], headers={"User-Agent": "stabpen-ai3/0.1 (research)"})
                with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:   # TLS verified (proxy CA)
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        f.write(b)
                tmp.replace(p)
                break
            except Exception as e:                  # network hiccup: retry, then give up with the reason
                last = e
                log(f"[data] download {name} failed ({e!r}); retry {k + 1}/{retries}")
                time.sleep(5 * (k + 1))
        if not p.exists():
            raise RuntimeError(f"could not download {name} from {d['url']}: {last!r}")
    digest = sha256_file(p)
    if d.get("sha256") and digest != d["sha256"]:
        raise RuntimeError(f"{name}: sha256 {digest} differs from the recorded {d['sha256']}")
    prov = {"name": name, "url": d["url"], "file": d["file"], "bytes": p.stat().st_size, "sha256": digest,
            "licence": d["licence"], "citation": d["citation"],
            "retrieved_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(p.stat().st_mtime))}
    return p, prov


# ============================================================================================ UJI Pen Characters v2
@dataclass
class Letter:
    char: str
    writer: str                 # e.g. 'trn_UJI_W03'
    rep: int                    # 1 or 2
    strokes: List[np.ndarray]   # pen-down strokes, (n, 2) in mm, y up, consecutive duplicate points removed
    site: str                   # 'UJI' or 'UPV'
    raw_counts: List[int] = field(default_factory=list)   # points per stroke before de-duplication


def load_uji(letters: str = "abcdefghijklmnopqrstuvwxyz") -> Tuple[List[Letter], Dict]:
    """Lower-case letters of UJI v2, in mm (UJI 100 units/mm, UPV 152 units/mm, as the dataset notes), y up."""
    z, prov = fetch("uji2")
    txt = RAW_DIR / "uji2" / "ujipenchars2.txt"
    if not txt.exists():
        zipfile.ZipFile(z).extractall(RAW_DIR / "uji2")
    lines = txt.read_text(encoding="utf-8", errors="replace").splitlines()
    out: List[Letter] = []
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("WORD"):
            parts = ln.split()
            ch, sid = parts[1], parts[2]
            writer, rep = sid.rsplit("-", 1)
            ns = int(lines[i + 1].split()[1])
            site = "UPV" if "_UPV_" in writer else "UJI"
            scale = 1.0 / (152.0 if site == "UPV" else 100.0)
            strokes, counts = [], []
            for s in range(ns):
                toks = lines[i + 2 + s].split("#")[1].split()
                a = np.array(toks, float).reshape(-1, 2) * np.array([scale, -scale])
                counts.append(len(a))
                keep = np.r_[True, np.any(np.abs(np.diff(a, axis=0)) > 0, axis=1)]
                strokes.append(a[keep])
            if ch in letters:
                out.append(Letter(ch, writer, int(rep), strokes, site, counts))
            i += 2 + ns
        else:
            i += 1
    prov["n_letters_used"] = len(out)
    prov["writers"] = len({L.writer for L in out})
    return out, prov


# ============================================================================================ Character Trajectories
CT_FS = 200.0


def load_chartraj() -> Tuple[List[Dict], Dict]:
    """One writer's single-stroke letters: positions integrated from the 200 Hz pen-tip velocity (normalised units,
    y up as recorded), time stamps and pen force."""
    from scipy.io import loadmat
    z, prov = fetch("chartraj")
    p = RAW_DIR / "chartraj" / "mixoutALL_shifted.mat"
    if not p.exists():
        zipfile.ZipFile(z).extractall(RAW_DIR / "chartraj")
    m = loadmat(p, squeeze_me=True, struct_as_record=False)
    mix = m["mixout"]
    labels = np.asarray(m["consts"].charlabels).astype(int)
    key = [str(k) for k in m["consts"].key]
    out = []
    for i in range(len(mix)):
        a = np.asarray(mix[i], float)
        v = a[:2].T
        xy = np.cumsum(v, axis=0) / CT_FS
        out.append({"char": key[labels[i] - 1], "t": np.arange(len(v)) / CT_FS, "xy": xy, "force": a[2], "index": i})
    prov["n"] = len(out)
    prov["classes"] = sorted({o["char"] for o in out})
    return out, prov


# ============================================================================================ misspelling corpora
def load_pairs(name: str) -> Tuple[List[Tuple[str, str]], Dict]:
    """(target, misspelling) pairs from a Mitton-format file ('$target' lines followed by misspellings; underscores
    stand for spaces; holbrook-missp lines carry a count, kept as repeated pairs)."""
    p, prov = fetch(name)
    pairs = []
    target = None
    for ln in p.read_text(encoding="latin-1").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("$"):
            target = ln[1:]
            continue
        if target is None or target == "?":
            continue
        parts = ln.split()
        mis = parts[0]
        cnt = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        for _ in range(cnt):
            pairs.append((target.replace("_", " "), mis.replace("_", " ")))
    prov["n_pairs"] = len(pairs)
    prov["n_targets"] = len({t for t, _ in pairs})
    return pairs, prov


@dataclass
class Token:
    written: str                # what the child wrote (may contain spaces: a split word)
    target: Optional[str]       # the intended word(s) if this is a tagged error, else None (a correct word)


@dataclass
class Passage:
    child: str
    page: int
    tokens: List[Token]


_ERR = re.compile(r"<ERR targ=(.*?)>\s*(.*?)\s*</ERR>", flags=re.S)


def _split_plain(s: str) -> List[str]:
    return [w for w in re.split(r"\s+", s) if w]


def load_holbrook() -> Tuple[List[Passage], Dict]:
    """The tagged Holbrook passages, one Passage per child section, as a token stream with the tagged errors."""
    p, prov = fetch("holbrook")
    text = p.read_text(encoding="latin-1")
    heads = list(re.finditer(r"^\s*\d+\.\s*\n([A-Z' ]+?)\s+page\s+(\d+)\s*$", text, flags=re.M))
    out: List[Passage] = []
    for k, h in enumerate(heads):
        body = text[h.end(): heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        toks: List[Token] = []
        pos = 0
        for m in _ERR.finditer(body):
            for w in _split_plain(body[pos:m.start()]):
                toks.append(Token(w, None))
            tgt = m.group(1).strip()
            toks.append(Token(m.group(2).strip(), None if tgt == "?" else tgt))
            if tgt == "?":
                toks[-1] = Token(m.group(2).strip(), "?")
            pos = m.end()
        for w in _split_plain(body[pos:]):
            toks.append(Token(w, None))
        out.append(Passage(h.group(1).strip().title(), int(h.group(2)), toks))
    prov["n_children"] = len(out)
    prov["n_tokens"] = sum(len(p.tokens) for p in out)
    prov["n_tagged"] = sum(1 for p in out for t in p.tokens if t.target is not None)
    return out, prov


# ============================================================================================ journals (Gutenberg)
def load_journal(gid: int) -> Tuple[List[str], Dict]:
    """A Project Gutenberg journal as a list of normalised lines (sentences), boilerplate removed."""
    from aiguide import corpus as ACO
    p, prov = fetch(f"pg{gid}")
    t = p.read_text(encoding="utf-8", errors="replace")
    a = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", t)
    b = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", t)
    body = t[a.end() if a else 0: b.start() if b else len(t)]
    body = re.sub(r"\[Illustration[^\]]*\]", " ", body)
    body = re.sub(r"\[\d+\]|\{\d+\}", " ", body)              # footnote marks
    paras = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\n\s*\n", body)]
    lines: List[str] = []
    for para in paras:
        if len(para) < 20 or para.isupper():
            continue
        for s in re.split(r"(?<=[.!?;])\s+", para):
            n = ACO.normalize(s)
            n = re.sub(r"\s+", " ", n).strip()
            if len(n) >= 8 and sum(c.isalpha() for c in n) >= 0.6 * len(n):
                lines.append(n)
    prov.update(GUTENBERG[gid])
    prov["n_lines"] = len(lines)
    prov["n_words"] = sum(len(l.split()) for l in lines)
    return lines, prov


def html_text(p: Path) -> str:
    t = p.read_text(encoding="utf-8", errors="ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
