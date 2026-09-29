"""Stage synth (task 5): handwriting synthesis in the writer's style.

Evidence status: CALCULATION / SIMULATION.
  A  sigma-lognormal extraction and synthesis on the synthetic test writers 0-5 (aiguide): k = 1 or 3 reference
     instances per letter; legibility by the app's recogniser; style similarity by writer identification among the six
     writers (size-normalised DTW to each writer's held-out instances).  Baselines: the font in the writer's global
     style, and a copy of one reference instance.
  B  sigma-lognormal extraction on real pen-tip velocity (UCI Character Trajectories, one writer, CC BY 4.0).
  C  a learned few-shot generator on real handwriting shapes (UCI UJI Pen Characters v2, 60 writers, CC BY 4.0;
     no time stamps, so shapes only): a conditional decoder trained on the 40 'trn' writers, conditioned on a style
     vector from the writer's OTHER letters; tested on the 20 'tst' writers: legibility by a classifier trained on
     trn writers' real letters, and style by a same-writer preference test.
"""
from __future__ import annotations

import math
import time
import zipfile
from typing import Dict, List, Tuple

import numpy as np

from . import BUILD_DIR, TEST_WRITERS, ensure_paths
from . import common as C
from . import synth as SY

ensure_paths()
from aiguide.glyphs import GLYPH_SET, LETTERS  # noqa: E402
from aiguide.metrics import GlyphRecognizer, dtw, normalise, shape_points  # noqa: E402
from handwriting import writers as W  # noqa: E402

CORP = BUILD_DIR / "corpora"
EXAMPLE_LETTERS = "aegks"
UJI_URL = "https://archive.ics.uci.edu/static/public/177/uji+pen+characters+version+2.zip"
CT_URL = "https://archive.ics.uci.edu/static/public/175/character+trajectories.zip"


# ------------------------------------------------------------------ A: synthetic writers
def letter_instances(w: int, ch: str, seeds) -> List[Tuple[np.ndarray, List[np.ndarray]]]:
    """The writer writing one letter (instance seeds): (t at 200 Hz, list of pen-down strokes (m))."""
    out = []
    wtr = W.writer(w)
    for s in seeds:
        wr = wtr.write(ch, dt=1.0 / SY.FS, seed=s)
        it = wr.intended
        d = np.diff(np.r_[0, it.pen_down.astype(np.int8), 0])
        strokes = [(it.t[a:b], it.xy[a:b]) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= 4]
        out.append(strokes)
    return out


def synth_letter(refs, rng, k: int) -> List[np.ndarray]:
    """Sigma-lognormal synthesis from the first k reference instances (per stroke).  The prototype is the medoid of the
    k instances (size-normalised DTW; with k = 1 the instance itself); a new instance perturbs its lognormal parameters
    by the default intra-writer spread (component matching across instances is not reliable, so the spread is not
    estimated from k samples).  The synthetic stroke spans the prototype stroke's own time span."""
    cand = refs[:k]
    if k > 1:
        shapes = [_norm_shape([xy for _, xy in inst]) for inst in cand]
        cost = [sum(dtw(shapes[i], shapes[j]) for j in range(len(cand)) if j != i) for i in range(len(cand))]
        j = int(np.argmin(cost))
    else:
        j = 0
    proto = cand[j]
    out, snr = [], []
    for t, xy in proto:
        f = SY.extract(t, xy)
        snr.append(f["snr_db"])
        P = SY.perturb(f["P"], rng) if len(f["P"]) else f["P"]
        out.append(SY.trajectory(t, P, f["start"]) if len(P) else xy)
    return out, float(np.nanmean(snr)) if snr else float("nan")


def _norm_shape(strokes) -> np.ndarray:
    return normalise(shape_points([np.asarray(s) for s in strokes]))


def part_a(quick: bool) -> Dict:
    writers = TEST_WRITERS[:2] if quick else TEST_WRITERS
    letters = LETTERS[:6] if quick else LETTERS
    rng = np.random.default_rng(5)
    held = {}
    recs = {}
    for w in writers:
        st = W.writer(w).style
        recs[w] = GlyphRecognizer(st.x_height_mm * 1e-3, st.width, math.radians(st.slant_deg))
        for ch in letters:
            held[(w, ch)] = [[xy for _, xy in inst] for inst in letter_instances(w, ch, (11, 12, 13))]
    methods = ("font", "copy", "sl_k1", "sl_k3")
    res = {m: {"legible": [], "writer_id": [], "d_own": [], "d_other": []} for m in methods}
    examples: Dict[str, Dict] = {}
    snrs = []
    for w in writers:
        st = W.writer(w).style
        h = st.x_height_mm * 1e-3
        shear = math.tan(math.radians(st.slant_deg))
        for ch in letters:
            refs = letter_instances(w, ch, (1, 2, 3))
            gens = {}
            gens["font"] = [np.column_stack([h * (st.width * g[:, 0] + g[:, 1] * shear), h * g[:, 1]]) for g in GLYPH_SET[ch]]
            gens["copy"] = [xy for _, xy in refs[0]]
            gens["sl_k1"], s1 = synth_letter(refs, rng, 1)
            gens["sl_k3"], s3 = synth_letter(refs, rng, 3)
            snrs.append(s3)
            if w == writers[0] and ch in EXAMPLE_LETTERS:
                examples.setdefault(ch, {"held": [[np.round(xy * 1e3, 3).tolist() for xy in held[(w, ch)][0]]]})
                for m, strokes in gens.items():
                    examples[ch][m] = [np.round(np.asarray(xy) * 1e3, 3).tolist() for xy in strokes]
            for m, strokes in gens.items():
                pred, _ = recs[w].classify(strokes)
                res[m]["legible"].append(pred == ch)
                q = _norm_shape(strokes)
                dist = {ww: float(np.mean([dtw(q, _norm_shape(inst)) for inst in held[(ww, ch)]])) for ww in writers}
                res[m]["writer_id"].append(min(dist, key=dist.get) == w)
                res[m]["d_own"].append(dist[w]); res[m]["d_other"].append(float(np.mean([v for k2, v in dist.items() if k2 != w])))
    out = {m: {"legibility": float(np.mean(v["legible"])), "writer_id_acc": float(np.mean(v["writer_id"])),
               "dtw_own": float(np.mean(v["d_own"])), "dtw_other": float(np.mean(v["d_other"])), "n": len(v["legible"])}
           for m, v in res.items()}
    out["extraction_snr_db"] = {"median": float(np.nanmedian(snrs)), "p10": float(np.nanpercentile(snrs, 10)),
                                "p90": float(np.nanpercentile(snrs, 90))}
    out["chance_writer_id"] = 1.0 / len(writers)
    out["examples_writer"] = writers[0]
    out["examples_mm"] = examples
    return out


# ------------------------------------------------------------------ B: Character Trajectories (real velocity)
def part_b(quick: bool) -> Dict:
    from scipy.io import loadmat
    p = CORP / "chartraj" / "mixoutALL_shifted.mat"
    if not p.exists():
        z = CORP / "chartraj.zip"
        zipfile.ZipFile(z).extractall(CORP / "chartraj")
    m = loadmat(p, squeeze_me=True, struct_as_record=False)
    mix = m["mixout"]
    labels = np.asarray(m["consts"].charlabels).astype(int)
    key = list(m["consts"].key)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(mix), size=40 if quick else 240, replace=False)
    snr, ncomp, per = [], [], {}
    for i in idx:
        v = np.asarray(mix[i], float)[:2].T              # velocity x, y (normalised units per sample)
        t = np.arange(len(v)) / SY.FS
        xy = np.cumsum(v, axis=0) / SY.FS
        r = SY.extract(t, xy)
        snr.append(r["snr_db"]); ncomp.append(len(r["P"]))
        per.setdefault(str(key[labels[i] - 1]), []).append(r["snr_db"])
    return {"n": len(idx), "snr_db_median": float(np.nanmedian(snr)), "snr_db_p10": float(np.nanpercentile(snr, 10)),
            "snr_db_p90": float(np.nanpercentile(snr, 90)), "components_median": float(np.median(ncomp)),
            "by_char_median_snr_db": {k: float(np.nanmedian(v)) for k, v in per.items()},
            "source": {"url": CT_URL, "licence": "CC BY 4.0", "writers": 1}}


# ------------------------------------------------------------------ C: UJI learned few-shot generator
N_PTS = 48


def load_uji() -> Dict[Tuple[str, str], List[List[np.ndarray]]]:
    p = CORP / "uji2" / "ujipenchars2.txt"
    if not p.exists():
        zipfile.ZipFile(CORP / "uji2.zip").extractall(CORP / "uji2")
    data: Dict[Tuple[str, str], List[List[np.ndarray]]] = {}
    lines = p.read_text(encoding="latin-1").splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("WORD"):
            parts = ln.split()
            ch, wid = parts[1], parts[2]
            writer = wid.rsplit("-", 1)[0]
            ns = int(lines[i + 1].split()[1])
            strokes = []
            for s in range(ns):
                toks = lines[i + 2 + s].split("#")[1].split()
                a = np.array(toks, float).reshape(-1, 2) * np.array([1.0, -1.0])   # y up
                strokes.append(a * 1e-5)                                        # 100 units/mm -> m
            data.setdefault((writer, ch), []).append(strokes)
            i += 2 + ns
        else:
            i += 1
    return data


def encode_char(strokes: List[np.ndarray]) -> np.ndarray:
    """(N_PTS, 3): points along the pen path (strokes joined, pen-up jumps included) resampled by arc length,
    centred and scaled to unit RMS radius; third column = 1 on pen-down segments."""
    P, pen = [], []
    for s in strokes:
        if len(s) == 0:
            continue
        P.append(np.asarray(s, float)); pen.append(np.ones(len(s)))
    X = np.vstack(P); D = np.concatenate(pen)
    # mark the first point of each stroke after the first as the end of a pen-up jump
    starts = np.cumsum([0] + [len(s) for s in P[:-1]])
    D[starts[1:]] = 0.0
    seg = np.r_[0.0, np.cumsum(np.hypot(*np.diff(X, axis=0).T))]
    if seg[-1] <= 0:
        return np.zeros((N_PTS, 3))
    u = np.linspace(0, seg[-1], N_PTS)
    x = np.interp(u, seg, X[:, 0]); y = np.interp(u, seg, X[:, 1])
    d = np.interp(u, seg, D) > 0.5
    Y = np.column_stack([x, y]); Y -= Y.mean(0)
    Y /= max(np.sqrt(np.mean(np.sum(Y ** 2, 1))), 1e-12)
    return np.column_stack([Y, d.astype(float)])


def part_c(quick: bool) -> Dict:
    import torch
    torch.set_num_threads(1)
    torch.manual_seed(0)
    data = load_uji()
    letters = "abcdefghijklmnopqrstuvwxyz"
    writers = sorted({w for (w, c) in data})
    trn = [w for w in writers if w.startswith("trn")]
    tst = [w for w in writers if w.startswith("tst")]
    enc = {(w, c): [encode_char(s) for s in data[(w, c)]] for (w, c) in data if c in letters}
    L = {c: i for i, c in enumerate(letters)}

    def samples(ws):
        out = []
        for w in ws:
            for c in letters:
                for e in enc.get((w, c), []):
                    out.append((w, c, e))
        return out
    tr = samples(trn); te = samples(tst)
    nn = torch.nn
    # classifier (legibility judge) on real trn letters
    clf = nn.Sequential(nn.Linear(N_PTS * 3, 128), nn.ReLU(), nn.Linear(128, 26))
    Xc = torch.tensor(np.stack([e.ravel() for _, _, e in tr]), dtype=torch.float32)
    yc = torch.tensor([L[c] for _, c, _ in tr])
    opt = torch.optim.Adam(clf.parameters(), 1e-3)
    for ep in range(60 if not quick else 10):
        perm = torch.randperm(len(Xc))
        for b in range(0, len(Xc), 128):
            ii = perm[b:b + 128]
            loss = nn.functional.cross_entropy(clf(Xc[ii]), yc[ii])
            opt.zero_grad(); loss.backward(); opt.step()
    Xt = torch.tensor(np.stack([e.ravel() for _, _, e in te]), dtype=torch.float32)
    yt = np.array([L[c] for _, c, _ in te])
    real_acc = float((clf(Xt).argmax(1).numpy() == yt).mean())
    # style encoder + conditional decoder (few-shot): style = mean embedding of K other letters of the writer
    K, ZS = 5, 16
    enc_net = nn.Sequential(nn.Linear(N_PTS * 3 + 26, 128), nn.ReLU(), nn.Linear(128, ZS))
    dec = nn.Sequential(nn.Linear(26 + ZS + 8, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, N_PTS * 3))
    params = list(enc_net.parameters()) + list(dec.parameters())
    opt = torch.optim.Adam(params, 1e-3)
    by_w = {}
    for w, c, e in tr:
        by_w.setdefault(w, []).append((c, e))
    rng = np.random.default_rng(1)

    def style(w_items, exclude):
        pool = [(c, e) for c, e in w_items if c != exclude]
        pick = [pool[i] for i in rng.choice(len(pool), size=min(K, len(pool)), replace=False)]
        x = torch.tensor(np.stack([np.r_[e.ravel(), np.eye(26)[L[c]]] for c, e in pick]), dtype=torch.float32)
        return enc_net(x).mean(0)
    steps = 300 if quick else 4000
    t0 = time.time()
    for step in range(steps):
        batch = [tr[i] for i in rng.integers(0, len(tr), size=64)]
        S = torch.stack([style(by_w[w], c) for w, c, _ in batch])
        Y = torch.tensor(np.stack([e for _, _, e in batch]), dtype=torch.float32)
        oh = torch.tensor(np.stack([np.eye(26)[L[c]] for _, c, _ in batch]), dtype=torch.float32)
        z = torch.randn(len(batch), 8) * 0.3
        out = dec(torch.cat([oh, S, z], 1)).view(-1, N_PTS, 3)
        loss = ((out[..., :2] - Y[..., :2]) ** 2).mean() + 0.1 * nn.functional.binary_cross_entropy_with_logits(out[..., 2], Y[..., 2])
        opt.zero_grad(); loss.backward(); opt.step()
    train_min = (time.time() - t0) / 60.0
    # test on tst writers: generate each letter from the writer's other letters
    by_wt = {}
    for w, c, e in te:
        by_wt.setdefault(w, []).append((c, e))
    gen_ok, pref, pref_mean, pref_near = [], [], [], []
    means = {c: np.mean([e for w, cc, e in tr if cc == c], axis=0) for c in letters}
    with torch.no_grad():
        for w in tst:
            items = by_wt[w]
            for c in letters:
                own = [e for cc, e in items if cc == c]
                others = [e for ww in tst if ww != w for cc, e in by_wt[ww] if cc == c]
                if not own or not others:
                    continue
                S = style(items, c)
                g = dec(torch.cat([torch.tensor(np.eye(26)[L[c]], dtype=torch.float32), S, torch.zeros(8)])).view(N_PTS, 3).numpy()
                g[:, 2] = (g[:, 2] > 0).astype(float)
                gen_ok.append(int(clf(torch.tensor(g.ravel(), dtype=torch.float32)[None]).argmax(1).item() == L[c]))
                d_own = min(dtw(g[:, :2], o[:, :2]) for o in own)
                j = rng.integers(len(others))
                d_oth = dtw(g[:, :2], others[j][:, :2])
                pref.append(d_own < d_oth)
                m = means[c]
                pref_mean.append(min(dtw(m[:, :2], o[:, :2]) for o in own) < dtw(m[:, :2], others[j][:, :2]))
    return {"writers_train": len(trn), "writers_test": len(tst), "n_train_samples": len(tr), "n_test_samples": len(te),
            "classifier_acc_real_test_letters": real_acc, "generated_legibility": float(np.mean(gen_ok)),
            "same_writer_preference_generated": float(np.mean(pref)), "same_writer_preference_class_mean": float(np.mean(pref_mean)),
            "chance": 0.5, "train_minutes": train_min, "K_reference_letters": K,
            "source": {"url": UJI_URL, "licence": "CC BY 4.0", "writers": 60, "timestamps": False}}


def run(quick: bool, workers: int):
    t0 = time.time()
    out = {"A_synthetic_writers": part_a(quick)}
    C.log(f"[synth] A: {out['A_synthetic_writers']}")
    out["B_character_trajectories"] = part_b(quick)
    C.log(f"[synth] B: SNR median {out['B_character_trajectories']['snr_db_median']:.1f} dB")
    out["C_uji_generator"] = part_c(quick)
    C.log(f"[synth] C: {out['C_uji_generator']}")
    out["minutes"] = (time.time() - t0) / 60.0
    C.save("synth", out, quick)
    return out
