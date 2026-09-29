"""Stage 'online' (task 1): train and evaluate the online letter recogniser on real handwriting (CALCULATION).

Resumable: sigma-lognormal fits are cached in chunks (ai3/build/cache/sl_fits*.pkl); each variant's training writes a
checkpoint every 2 minutes (ai3/build/models/online_<variant>.pt) and a finished-record json; a restart continues.
"""
from __future__ import annotations

import json
import math
import pickle
import re
import time
from typing import Dict, List

import numpy as np

from . import BUILD_DIR, ensure_paths
from . import common as C
from . import data as D
from . import online as O
from .rules import RULES, rules_sha256

ensure_paths()

VARIANTS = {
    "base": {"name": "base", "affine": True, "jitter": True, "tremor": False, "sl": False},
    "tremor": {"name": "tremor", "affine": True, "jitter": True, "tremor": True, "p_tremor": 0.5, "tremor_max": 0.4,
               "sl": False},
    "full": {"name": "full", "affine": True, "jitter": True, "tremor": True, "p_tremor": 0.5, "tremor_max": 0.4,
             "sl": True, "sl_scales": (0.3, 0.6)},
}
TREMOR_EVAL_XH = (0.1, 0.33)          # 0.3 mm and 1 mm peak at a 3 mm x-height


def model_dir() -> "Path":
    d = BUILD_DIR / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sl_fits(items: List[Dict], dt: float, quick: bool) -> Dict[str, "O.SLFit"]:
    p = C.cache_dir(quick) / "sl_fits.pkl"
    fits = pickle.loads(p.read_bytes()) if p.exists() else {}
    todo = [it for it in items if it["key"] not in fits]
    if todo:
        C.log(f"[online] sigma-lognormal fits: {len(fits)} cached, {len(todo)} to do")
    t0 = time.time()
    for k, it in enumerate(todo):
        fits[it["key"]] = O.sl_fit_letter(it["strokes"], dt)
        if (k + 1) % 100 == 0 or k + 1 == len(todo):
            tmp = p.with_suffix(".tmp"); tmp.write_bytes(pickle.dumps(fits)); tmp.replace(p)
            C.log(f"[online]   {k + 1}/{len(todo)} fits ({time.time() - t0:.0f} s)")
    return fits


def tremor_items(items: List[Dict], amp_xh: float, dt: float, seed: int) -> List[Dict]:
    out = []
    for it in items:
        rng = np.random.default_rng(C.stable_hash(f"{seed}:{it['key']}", 1 << 30))
        s = O.add_tremor(it["strokes"], rng, 1.0, dt, (amp_xh, amp_xh))
        out.append(dict(it, strokes=s))
    return out


STEPS = 5470                          # training batches per variant (48 letters each): the base variant's count
                                      # under the first (time-boxed) run; every variant gets the same number


def train_variant(name: str, train, val, dt: float, minutes: float, quick: bool):
    import torch
    tag = f"online_{name}{'_quick' if quick else ''}"
    pt, js, ck = model_dir() / f"{tag}.pt", model_dir() / f"{tag}.json", model_dir() / f"{tag}.ckpt"
    steps = 250 if quick else STEPS
    if pt.exists() and js.exists():
        info = json.loads(js.read_text())
        if info.get("steps", 0) >= steps or (quick and abs(info.get("minutes_budget", -1) - minutes) < 1e-9):
            m = O.make_model(info["cfg"].get("hidden", 96), info["cfg"].get("layers", 2))
            m.load_state_dict(torch.load(pt)); m.eval()
            C.log(f"[online] {name}: reusing the trained model ({info['steps']} steps)")
            return m, info
    m, info = O.train(train, val, VARIANTS[name], minutes, dt, seed=11, ckpt=ck, max_steps=steps)
    info["minutes_budget"] = minutes
    info["step_budget"] = steps
    torch.save(m.state_dict(), pt)
    js.write_text(json.dumps(info, default=C.jdefault))
    return m, info


# ------------------------------------------------------------------ language context
def lm_letter_prior(pred, text: str) -> np.ndarray:
    """Next-letter distribution over a-z from the text predictor (aiguide NG0; glyph one ahead), renormalised."""
    from aiguide import lm
    p = pred.glyph_ahead(text, 1)
    q = np.array([p[lm.SYM[c]] for c in O.LETTERS])
    return q / max(q.sum(), 1e-12)


def clean_sentence(s: str) -> str:
    s = re.sub(r"[^a-z ]", "", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def context_sequences(letters, xh, split: str, sentences: List[str], n_letters: int, seed: int) -> List[Dict]:
    """Each writer of the split 'writes' sentences letter by letter with their own real letter samples."""
    byw: Dict[str, Dict[str, List]] = {}
    for L in letters:
        if O.split_of(L.writer) == split:
            byw.setdefault(L.writer, {}).setdefault(L.char, []).append(L)
    rng = np.random.default_rng(seed)
    out = []
    sents = [clean_sentence(s) for s in sentences]
    sents = [s for s in sents if len(s) >= 12]
    for w in sorted(byw):
        count = 0
        while count < n_letters:
            s = sents[int(rng.integers(len(sents)))]
            seq = []
            for i, ch in enumerate(s):
                if ch == " ":
                    continue
                Ls = byw[w].get(ch)
                if not Ls:
                    continue
                L = Ls[int(rng.integers(len(Ls)))]
                seq.append({"char": ch, "context": s[:i], "strokes": [np.asarray(x) / xh[w] for x in L.strokes],
                            "label": O.L2I[ch], "key": f"{w}-{L.rep}-{ch}"})
            out.append({"writer": w, "sentence": s, "letters": seq})
            count += len(seq)
    return out


def eval_context(model, seqs: List[Dict], pred, betas, fracs=(0.3, 0.5, 0.7, 1.0)) -> Dict:
    """Letter accuracy at fractions of each letter, with the language prior computed from the RECOGNISED previous
    letters (the true word boundaries are known: pen lifts)."""
    allP = {}
    flat = [(si, li, L) for si, sq in enumerate(seqs) for li, L in enumerate(sq["letters"])]
    enc = [O.encode(L["strokes"], 1.0) for _, _, L in flat]
    P = O.posteriors(model, [e[0] for e in enc])
    for (si, li, _), p, e in zip(flat, P, enc):
        allP[(si, li)] = (p, e[1])
    res = {}
    for beta in betas:
        hits = {f: 0 for f in fracs}
        n = 0
        cache: Dict[str, np.ndarray] = {}
        for si, sq in enumerate(seqs):
            rec = ""
            for li, L in enumerate(sq["letters"]):
                # the recognised context: previous recognised letters with the true spaces
                ctx = L["context"]
                # map context characters onto recognised ones (same length, spaces kept)
                rc, k = [], 0
                for ch in ctx:
                    if ch == " ":
                        rc.append(" ")
                    else:
                        rc.append(rec[k] if k < len(rec) else ch); k += 1
                rctx = "".join(rc)
                if beta > 0:
                    if rctx not in cache:
                        cache[rctx] = lm_letter_prior(pred, rctx)
                    prior = cache[rctx]
                else:
                    prior = None
                p, fr = allP[(si, li)]
                for f in fracs:
                    v = O.at_fraction(p, fr, f)
                    if prior is not None:
                        v = v * np.power(np.maximum(prior, 1e-6), beta); v = v / v.sum()
                    hits[f] += int(np.argmax(v) == L["label"])
                vfin = p[-1]
                if prior is not None:
                    vfin = vfin * np.power(np.maximum(prior, 1e-6), beta); vfin = vfin / vfin.sum()
                rec += O.LETTERS[int(np.argmax(vfin))]
                n += 1
        res[f"{beta:g}"] = {"n": n, **{f"top1_{f:g}": hits[f] / max(n, 1) for f in fracs}}
    return res


# ------------------------------------------------------------------ Character Trajectories (cross-dataset)
def ct_items() -> List[Dict]:
    ct, prov = D.load_chartraj()
    hs = [float(np.ptp(o["xy"][:, 1])) for o in ct if o["char"] in O.XH_LETTERS]
    xh = float(np.median(hs))
    items = []
    for o in ct:
        if o["char"] not in O.L2I:
            continue
        xy = o["xy"] - o["xy"][0]
        items.append({"strokes": [xy / xh], "label": O.L2I[o["char"]], "key": f"ct-{o['index']}", "writer": "ct",
                      "t": o["t"]})
    return items, prov, xh


def confusion(model, items: List[Dict]) -> np.ndarray:
    seqs = [O.encode(it["strokes"], 1.0)[0] for it in items]
    P = O.posteriors(model, seqs)
    M = np.zeros((26, 26), int)
    for p, it in zip(P, items):
        M[it["label"], int(np.argmax(p[-1]))] += 1
    return M


# ------------------------------------------------------------------ the stage
def run(quick: bool, minutes: float = None) -> Dict:
    t_all = time.time()
    minutes = minutes or (0.4 if quick else 9.0)
    letters, prov = D.load_uji()
    xh = O.writer_xheights(letters)
    dt = O.sample_dt(letters, xh)
    train = O.build_items(letters, xh, "train")
    tune = O.build_items(letters, xh, "tune")
    test = O.build_items(letters, xh, "test")
    if quick:
        train = train[::6]; tune = tune[::3]; test = test[::8]
    C.log(f"[online] UJI: train {len(train)} tune {len(tune)} test {len(test)} letters; dt {dt * 1e3:.2f} ms/point")
    fits = sl_fits(train, dt, quick)
    for it in train:
        it["sl"] = fits.get(it["key"])
    n_fit = sum(1 for it in train if it["sl"] is not None)
    out = {"data": prov, "dt_ms": dt * 1e3, "n": {"train": len(train), "tune": len(tune), "test": len(test)},
           "writers": {s: sorted({it["writer"] for it in its}) for s, its in (("train", train), ("tune", tune), ("test", test))},
           "sl_fits": {"n_ok": n_fit, "n": len(train),
                       "snr_db_median": float(np.median([f.snr for f in fits.values() if f is not None])) if n_fit else None},
           "rules_sha256": rules_sha256(), "rules": {k: RULES[k] for k in ("O1_variant", "O2_commit", "O3_beta")}}
    # ---- train the three variants (tuning writers only for monitoring and the choice)
    models, infos = {}, {}
    for name in VARIANTS:
        models[name], infos[name] = train_variant(name, train, tune, dt, minutes, quick)
    out["training"] = infos
    # ---- rule O1 on tuning writers
    tune_trem = tremor_items(tune, 0.33, dt, seed=301)
    sel = {}
    for name, m in models.items():
        a = O.evaluate_fracs(m, tune)
        b = O.evaluate_fracs(m, tune_trem)
        k = [i for i, f in enumerate(a["fractions"]) if f >= 0.3 - 1e-9]
        sel[name] = {"clean": a, "tremor_0.33xh": b,
                     "score": float(0.5 * (np.mean([a["top1"][i] for i in k]) + np.mean([b["top1"][i] for i in k])))}
        C.log(f"[online] tuning {name}: score {sel[name]['score']:.4f} (full letter clean {a['top1'][-1]:.3f}, "
              f"tremor {b['top1'][-1]:.3f})")
    order = ["base", "tremor", "full"]                         # simplest first (tie rule)
    best = max(sel[n]["score"] for n in order)
    chosen = next(n for n in order if sel[n]["score"] >= best - 0.005)
    out["O1"] = {"tuning": sel, "chosen": chosen}
    model = models[chosen]
    C.log(f"[online] rule O1 -> {chosen}")
    # ---- rule O2: commit threshold on clean tuning letters
    seqs = [O.encode(it["strokes"], 1.0) for it in tune]
    Pt = O.posteriors(model, [s[0] for s in seqs])
    taus = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
    o2 = {f"{t:g}": O.commit_stats(Pt, [s[1] for s in seqs], [it["label"] for it in tune], t) for t in taus}
    ok = [t for t in taus if o2[f"{t:g}"]["commit_accuracy"] >= 0.97]
    tau = min(ok) if ok else max(taus)
    out["O2"] = {"tuning": o2, "tau": tau, "met": bool(ok)}
    C.log(f"[online] rule O2 -> tau {tau} ({o2[f'{tau:g}']})")
    # ---- rule O3: language weight on tuning writers' letters in Tatoeba validation sentences
    from aiguide import corpus as ACO, lm
    pred = lm.cached_predictor()
    spl = ACO.make_splits()
    ctx_tune = context_sequences(letters, xh, "tune", spl.val, 60 if quick else 250, seed=7)
    betas = (0.0, 0.25, 0.5, 0.75, 1.0)
    o3 = eval_context(model, ctx_tune, pred, betas)
    base_full = o3["0"]["top1_1"]
    okb = [b for b in betas if o3[f"{b:g}"]["top1_1"] >= base_full - 0.005]
    beta = max(okb, key=lambda b: (o3[f"{b:g}"]["top1_0.5"], -b))
    out["O3"] = {"tuning": o3, "beta": beta}
    C.log(f"[online] rule O3 -> beta {beta}: {o3[f'{beta:g}']}")
    # ---- TEST (rules fixed above)
    res = {"chosen": chosen, "tau": tau, "beta": beta}
    res["clean"] = O.evaluate_fracs(model, test)
    for a in TREMOR_EVAL_XH:
        res[f"tremor_{a:g}xh"] = O.evaluate_fracs(model, tremor_items(test, a, dt, seed=401))
    seqs = [O.encode(it["strokes"], 1.0) for it in test]
    Pz = O.posteriors(model, [s[0] for s in seqs])
    res["commit"] = O.commit_stats(Pz, [s[1] for s in seqs], [it["label"] for it in test], tau)
    res["points_per_letter_median"] = float(np.median([len(s[0]) for s in seqs]))
    ctx_test = context_sequences(letters, xh, "test", spl.test, 60 if quick else 300, seed=9)
    res["context"] = eval_context(model, ctx_test, pred, (0.0, beta))
    M = confusion(model, test)
    res["confusion_full_letter"] = M.tolist()
    ci, ctp, ct_xh = ct_items()
    if quick:
        ci = ci[::10]
    res["chartraj"] = O.evaluate_fracs(model, ci)
    res["chartraj"]["classes"] = sorted({O.LETTERS[it["label"]] for it in ci})
    # for information: every variant on the test writers (the choice was made on tuning writers)
    res["variants_for_information"] = {n: {"clean": O.evaluate_fracs(m, test)["top1"],
                                           "tremor_0.33xh": O.evaluate_fracs(m, tremor_items(test, 0.33, dt, 401))["top1"]}
                                       for n, m in models.items()}
    lat = O.latency_ms(model)
    npar = O.n_params(model)
    res["cost"] = {"n_params": npar, "kB_float32": 4 * npar / 1024, "kB_int8": npar / 1024,
                   "macs_per_point": O.macs_per_point(model.cfg), "ms_per_point_this_cpu": lat["ms_per_point"],
                   "letter_ms_this_cpu": lat["ms_per_point"] * res["points_per_letter_median"],
                   "mcu_ms_per_point_int8": (O.macs_per_point(model.cfg) / 0.5 + 300 * 7) / 128e6 * 1e3}
    # time to write the median letter at 30 mm/s and a 3 mm x-height (ASSUMPTION timing)
    res["letter_time_s_median"] = float(np.median([sum(len(s) for s in it["strokes"]) * dt for it in test]))
    out["test"] = res
    out["chartraj_data"] = ctp
    out["minutes_total"] = (time.time() - t_all) / 60
    C.save("online", out, quick)
    import torch
    torch.save(model.state_dict(), model_dir() / f"online_chosen{'_quick' if quick else ''}.pt")
    (model_dir() / f"online_chosen{'_quick' if quick else ''}.json").write_text(json.dumps({"cfg": model.cfg, "variant": chosen,
                                                                                         "tau": tau, "beta": beta}))
    C.log(f"[online] test: clean full-letter top-1 {res['clean']['top1'][-1]:.3f}, half {res['clean']['top1'][4]:.3f}; "
          f"CT {res['chartraj']['top1'][-1]:.3f}; {out['minutes_total']:.1f} min")
    return out


def load_model(quick: bool = False):
    import torch
    js = json.loads((model_dir() / f"online_chosen{'_quick' if quick else ''}.json").read_text())
    m = O.make_model(js["cfg"]["hidden"], js["cfg"]["layers"])
    m.load_state_dict(torch.load(model_dir() / f"online_chosen{'_quick' if quick else ''}.pt"))
    m.eval()
    return m, js


# ------------------------------------------------------------------ writer calibration (rule O4)
def _calib_sets(letters, xh, split):
    """For every writer of the split: the encoded letters of each repetition, as calibration sets."""
    sets: Dict[str, Dict[int, Dict[int, np.ndarray]]] = {}
    for L in letters:
        if O.split_of(L.writer) != split:
            continue
        F, _ = O.encode([np.asarray(s) / xh[L.writer] for s in L.strokes], 1.0)
        sets.setdefault(L.writer, {}).setdefault(L.rep, {})[O.L2I[L.char]] = F
    return sets


def _eval_cal(model, items, sets, a, tau, fracs=O.FRACTIONS):
    seqs = [O.encode(it["strokes"], 1.0) for it in items]
    P = O.posteriors(model, [s[0] for s in seqs])
    top1 = np.zeros(len(fracs)); n = 0
    M = np.zeros((26, 26), int)
    fused_final = []
    for it, (F, fr), p in zip(items, seqs, P):
        w, rep = it["writer"], int(it["key"].split("-")[-2])
        cal = sets[w].get(3 - rep, {})
        for i, f in enumerate(fracs):
            k = int(np.searchsorted(fr, f + 1e-9, side="right")) - 1
            k = max(k, 1)
            q = O.fuse(p[k], O.calib_logscores(F[:k + 1], cal, tau), a)
            top1[i] += int(np.argmax(q) == it["label"])
        q = O.fuse(p[-1], O.calib_logscores(F, cal, tau), a)
        fused_final.append(q)
        M[it["label"], int(np.argmax(q))] += 1
        n += 1
    return {"fractions": list(fracs), "top1": (top1 / max(n, 1)).tolist(), "n": n}, M, fused_final


def run_calibrated(quick: bool) -> Dict:
    t0 = time.time()
    model, js = load_model(quick)
    letters, _ = D.load_uji()
    xh = O.writer_xheights(letters)
    dt = O.sample_dt(letters, xh)
    tune = O.build_items(letters, xh, "tune")
    test = O.build_items(letters, xh, "test")
    if quick:
        tune = tune[::3]; test = test[::8]
    s_tune = _calib_sets(letters, xh, "tune")
    s_test = _calib_sets(letters, xh, "test")
    grid = [(a, tau) for a in (0.3, 0.5, 0.7) for tau in (0.05, 0.1, 0.2)]
    tab = {}
    for a, tau in grid:
        r, _, _ = _eval_cal(model, tune, s_tune, a, tau)
        k = [i for i, f in enumerate(r["fractions"]) if f >= 0.3 - 1e-9]
        tab[f"{a:g},{tau:g}"] = {"top1": r["top1"], "score": float(np.mean([r["top1"][i] for i in k]))}
    best = max(tab, key=lambda k: tab[k]["score"])
    a, tau = (float(x) for x in best.split(","))
    C.log(f"[online] rule O4 -> a {a}, tau {tau} (score {tab[best]['score']:.3f})")
    res_clean, M, fused = _eval_cal(model, test, s_test, a, tau)
    res_trem, _, _ = _eval_cal(model, tremor_items(test, 0.33, dt, seed=401), s_test, a, tau)
    # commit statistics with the fused posterior (full evaluation at every point is costly: every 3rd point)
    fr_list, P_list, y = [], [], []
    seqs = [O.encode(it["strokes"], 1.0) for it in test]
    Pg = O.posteriors(model, [s[0] for s in seqs])
    for it, (F, fr), p in zip(test, seqs, Pg):
        w, rep = it["writer"], int(it["key"].split("-")[-2])
        cal = s_test[w].get(3 - rep, {})
        idx = list(range(1, len(F), 3)) + [len(F) - 1]
        Q = np.stack([O.fuse(p[k], O.calib_logscores(F[:k + 1], cal, tau), a) for k in idx])
        P_list.append(Q); fr_list.append(fr[idx]); y.append(it["label"])
    commit = O.commit_stats(P_list, fr_list, y, js["tau"])
    out = {"O4": {"table": tab, "a": a, "tau": tau}, "test": {"clean": res_clean, "tremor_0.33xh": res_trem,
                                                            "commit": commit, "confusion_full_letter": M.tolist()},
           "minutes": (time.time() - t0) / 60}
    C.save("online_cal", out, quick)
    C.log(f"[online] calibrated test: full letter {res_clean['top1'][-1]:.3f}, half {res_clean['top1'][4]:.3f}, "
          f"commit {commit}")
    return out
