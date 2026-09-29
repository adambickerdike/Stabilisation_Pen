"""A small causal network tremor estimator trained on REAL tuning inputs (SIMULATION; PROPOSED DESIGN).

Training data (tuning split only; built by build_train_set, fixed rule):
  notes     tuning note seeds 10-39 of realdata.library.writing('tuning', seed): 6 notes per tuning writer (writer
            seed % 5), plus the 10 selection notes of cases.py (seeds 0-9) for the folds they do not score
  tremor    per training note, 5 draws: kind PD or ET (alternating), a TUNING-split waveform of the note's fold, a tip
            amplitude log-uniform in 0.05-3.5 mm (the data classes' span), a random start; and the same note without
            tremor (the false-correction examples)
  sensors   the DeltaPen-class page sensor (the headline) and the ideal one, alternating (the net reads only the IMU
            and the contact flag, so the page model matters only through nothing: stated for completeness)
  augment   amplitude is drawn per case (above); the tremor waveform's own wander, intermittency and harmonics are the
            real recording's; IMU noise, bias and pen-rotation draws of fusion.sensors per case
Inputs per step (250 Hz, causal): page-frame acceleration x, y (m/s^2, the mean of the samples available in the step,
  held), the axial contact flag.  Output per step: 8 phases x 2 axes = the handle tremor at the 8 control ticks of the
  next step, each predicted to its tick time + the servo group delay (the delay handling is learned).
Model: causal dilated TCN (Bai et al. 2018, as ai2's), channels 24, kernel 3, dilations 1-64 (receptive field 1.02 s),
  GELU, residual blocks; about 17 k parameters.  Loss: per-case weighted squared error on active steps (weight
  1 / max(A, 0.3 mm)^2 so that small tremor and clean notes count, A = the case's tip amplitude) + LAMBDA x squared
  output on the clean notes.  Adam, 8 s windows, fixed epochs (chosen on fold 0's validation loss before the others).
Cross-fitting: 5 fold models (each without one fold's writer and subjects) score the tuning selection set; one model on
  all tuning data is the design used on the test split.  int8: per-channel symmetric weight quantisation is checked
  against float (the output difference is reported).
"""
from __future__ import annotations

import json
import math
import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import BUILD_DIR
from . import cases as C
from . import learned as LE

TRAIN_DIR = BUILD_DIR / "train"
MODEL_DIR = LE.MODEL_DIR
N_TRAIN_PER_WRITER = 6
TRAIN_SEED0 = 10
DRAWS_PER_NOTE = 5
AMP_RANGE_MM = (0.05, 3.5)
A_FLOOR = 0.3e-3
LAMBDA_CLEAN = 1.0
N_IN = 3
N_OUT = 2 * LE.N_PH
IN_SCALE = np.array([1.0, 1.0, 1.0], np.float32)     # m/s^2, m/s^2, flag
OUT_SCALE = 1e-3                                         # m per unit (mm)


def _torch():
    import torch
    torch.set_num_threads(1)
    return torch


# ------------------------------------------------------------------ data
def features(st) -> (np.ndarray, np.ndarray):
    """X (K, 3) float32 at 250 Hz and the step times."""
    tk, A = LE.acc_grid(st)
    jc = np.searchsorted(st.con_av, tk, side="right") - 1
    con = np.where(jc >= 0, st.con[np.maximum(jc, 0)], 0.0)
    X = np.column_stack([A, con]).astype(np.float32) / IN_SCALE
    return X, tk


def targets(case, tk: np.ndarray) -> np.ndarray:
    """Y (K, 16): per step k and phase p, the truth at t_k + p/2000 + servo delay (units OUT_SCALE)."""
    from .estimators import servo_delay
    gd = servo_delay()
    tick_t = case.tick_t
    d = case.truth
    Y = np.zeros((len(tk), N_OUT), np.float32)
    for p in range(LE.N_PH):
        tt = tk + p / LE.TICK_HZ + gd
        Y[:, 2 * p] = np.interp(tt, tick_t, d[:, 0]) / OUT_SCALE
        Y[:, 2 * p + 1] = np.interp(tt, tick_t, d[:, 1]) / OUT_SCALE
    return Y


def case_arrays(case, sensor: str = "deltapen") -> Dict:
    st = case.streams(sensor)
    X, tk = features(st)
    Y = targets(case, tk) if case.meta.get("tremor") else np.zeros((len(tk), N_OUT), np.float32)
    act = np.interp(tk, case.tick_t, case.arrays["active_ticks"]) > 0.5
    amp = float(case.spec.get("amp_mm", 0.0)) * 1e-3
    w = (1.0 / max(amp, A_FLOOR) ** 2) if amp > 0 else LAMBDA_CLEAN / A_FLOOR ** 2
    return {"X": X, "Y": Y, "m": (act & (tk > 1.0)).astype(np.float32), "w": np.float32(w * OUT_SCALE ** 2),
            "fold": int(case.spec["fold"]), "id": case.spec["id"]}


def train_specs() -> List[Dict]:
    """The training cases' specs (fixed rule, module docstring)."""
    from realdata import library as RL
    rng = np.random.default_rng(20260929)
    out = []
    for i in range(TRAIN_SEED0, TRAIN_SEED0 + C.N_FOLDS * N_TRAIN_PER_WRITER):
        fold = i % C.N_FOLDS
        out.append({"id": f"train_n{i}_clean", "split": "tuning", "note": i, "fold": fold, "kind": None,
                    "level": "clean", "amp_mm": 0.0})
        for j in range(DRAWS_PER_NOTE):
            kind = "PD" if (i + j) % 2 == 0 else "ET"
            rids = C.fold_rids(kind, fold)
            amp = float(math.exp(rng.uniform(math.log(AMP_RANGE_MM[0]), math.log(AMP_RANGE_MM[1]))))
            out.append({"id": f"train_n{i}_d{j}", "split": "tuning", "note": i, "fold": fold, "kind": kind,
                        "level": "severe" if amp > 0.507 else ("moderate" if amp > 0.165 else "mild"),
                        "amp_mm": amp, "rid": rids[int(rng.integers(len(rids)))], "tseed": 50_000 + 100 * i + j})
    return out


def build_train_set(log=print) -> List[str]:
    """Build (or resume) the training cases (cases.build_case, stored as compact per-case training arrays)."""
    TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    specs = train_specs()
    by_note: Dict[int, List[Dict]] = {}
    for s in specs:
        by_note.setdefault(s["note"], []).append(s)
    ids = []
    for i, ss in sorted(by_note.items()):
        todo = [s for s in ss if not (TRAIN_DIR / f"{s['id']}.npz").exists()]
        if todo:
            t0 = time.time()
            note = C.tuning_note(i)
            for j, s in enumerate(todo):
                c = C.build_case(note, s)
                arr = case_arrays(c, "deltapen" if j % 2 == 0 else "ideal")
                np.savez_compressed(TRAIN_DIR / f"{s['id']}.npz", X=arr["X"], Y=arr["Y"], m=arr["m"],
                                    w=np.array([arr["w"]], np.float32), fold=np.array([arr["fold"]]))
                del c
            log(f"[train-data] note {i} ({note.written.real.get('writer')}): {len(todo)} cases in {time.time() - t0:.0f} s")
            del note
        ids += [s["id"] for s in ss]
    return ids


def selection_arrays(log=print) -> List[Dict]:
    """The selection set's cases as training arrays too (used only by the folds they do not score)."""
    out = []
    p = TRAIN_DIR / "selection"
    p.mkdir(parents=True, exist_ok=True)
    for s in C.tuning_specs():
        f = p / f"{s['id']}.npz"
        if not f.exists():
            c = C.load_case(s)
            arr = case_arrays(c, "deltapen")
            np.savez_compressed(f, X=arr["X"], Y=arr["Y"], m=arr["m"], w=np.array([arr["w"]], np.float32),
                                fold=np.array([arr["fold"]]))
        out.append(str(f))
    return out


def load_arrays(paths: Sequence[str]) -> List[Dict]:
    out = []
    for f in paths:
        with np.load(f) as z:
            out.append({"X": z["X"], "Y": z["Y"], "m": z["m"], "w": float(z["w"][0]), "fold": int(z["fold"][0])})
    return out


def all_train_paths() -> List[str]:
    return sorted(str(p) for p in TRAIN_DIR.glob("train_*.npz")) + sorted(
        str(p) for p in (TRAIN_DIR / "selection").glob("*.npz"))


# ------------------------------------------------------------------ model
def make_tcn(ch: int = 24, k: int = 3, dil=(1, 2, 4, 8, 16, 32, 64)):
    torch = _torch()
    nn = torch.nn

    class CausalConv(nn.Module):
        def __init__(self, cin, cout, k, d):
            super().__init__()
            self.pad = (k - 1) * d
            self.conv = nn.Conv1d(cin, cout, k, dilation=d)

        def forward(self, x):
            return self.conv(nn.functional.pad(x, (self.pad, 0)))

    class Block(nn.Module):
        def __init__(self, d):
            super().__init__()
            self.c1 = CausalConv(ch, ch, k, d)
            self.c2 = nn.Conv1d(ch, ch, 1)

        def forward(self, x):
            return x + self.c2(nn.functional.gelu(self.c1(x)))

    class TCN(nn.Module):
        def __init__(self):
            super().__init__()
            self.inp = nn.Conv1d(N_IN, ch, 1)
            self.blocks = nn.ModuleList([Block(d) for d in dil])
            self.head = nn.Conv1d(ch, N_OUT, 1)
            nn.init.normal_(self.head.weight, std=0.01)
            nn.init.zeros_(self.head.bias)
            self.cfg = {"ch": ch, "k": k, "dil": list(dil), "n_in": N_IN, "n_out": N_OUT}
            self.rf = 1 + sum((k - 1) * d for d in dil)

        def forward(self, x):                        # (B, T, n_in) -> (B, T, n_out)
            h = self.inp(x.transpose(1, 2))
            for b in self.blocks:
                h = b(h)
            return self.head(h).transpose(1, 2)

    return TCN()


def n_params(model) -> int:
    return int(sum(p.numel() for p in model.parameters()))


def macs_per_step(cfg: Dict) -> int:
    ch, k = cfg["ch"], cfg["k"]
    return int(cfg["n_in"] * ch + len(cfg["dil"]) * (k * ch * ch + ch * ch) + ch * cfg["n_out"])


def train(data: List[Dict], epochs: int, seed: int = 0, win_s: float = 8.0, batch: int = 16, lr: float = 2e-3,
          val: Optional[List[Dict]] = None, log=print, cfg: Optional[Dict] = None) -> Dict:
    torch = _torch()
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = make_tcn(**(cfg or {}))
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    W = int(win_s * LE.FS_IN)
    rf = model.rf
    lens = np.array([len(d["X"]) for d in data])
    steps_per_epoch = int(max(1, lens.sum() // (W * batch)))
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs * steps_per_epoch)
    hist = []
    t0 = time.time()
    p_case = lens / lens.sum()
    for ep in range(epochs):
        model.train()
        tot = 0.0
        for it in range(steps_per_epoch):
            xs, ys, ms = [], [], []
            for b in range(batch):
                ci = int(rng.choice(len(data), p=p_case))
                d = data[ci]
                n = len(d["X"])
                s0 = int(rng.integers(0, max(1, n - W - rf)))
                s1 = min(n, s0 + W + rf)
                x = np.zeros((W + rf, N_IN), np.float32); y = np.zeros((W + rf, N_OUT), np.float32)
                m = np.zeros(W + rf, np.float32)
                x[:s1 - s0] = d["X"][s0:s1]; y[:s1 - s0] = d["Y"][s0:s1]; m[:s1 - s0] = d["m"][s0:s1] * d["w"]
                m[:rf] = 0.0                                   # the receptive field warms up
                xs.append(x); ys.append(y); ms.append(m)
            X = torch.from_numpy(np.stack(xs)); Y = torch.from_numpy(np.stack(ys)); M = torch.from_numpy(np.stack(ms))
            out = model(X)
            loss = ((out - Y) ** 2).mean(dim=2).mul(M).sum() / M.gt(0).sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tot += float(loss)
        h = {"epoch": ep, "train_loss": tot / steps_per_epoch, "t_s": time.time() - t0}
        if val:
            h["val_loss"] = evaluate_loss(model, val)
        hist.append(h)
        log(f"[net] epoch {ep}: train {h['train_loss']:.4f}" + (f", val {h['val_loss']:.4f}" if val else "")
            + f" ({h['t_s']:.0f} s)")
    return {"model": model, "history": hist, "params": n_params(model), "cfg": model.cfg}


def evaluate_loss(model, data: List[Dict]) -> float:
    torch = _torch()
    model.eval()
    num = den = 0.0
    with torch.no_grad():
        for d in data:
            out = model(torch.from_numpy(d["X"][None]))[0].numpy()
            m = d["m"] * d["w"]
            num += float(np.sum(((out - d["Y"]) ** 2).mean(axis=1) * m))
            den += float(np.sum(d["m"] > 0))
    return num / max(den, 1.0)


def save(model, tag: str, info: Dict) -> None:
    torch = _torch()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), MODEL_DIR / f"net_{tag}.pt")
    (MODEL_DIR / f"net_{tag}.json").write_text(json.dumps({k: v for k, v in info.items() if k != "model"}, default=float))


_M: Dict = {}


def load(tag: str):
    if tag not in _M:
        torch = _torch()
        info = json.loads((MODEL_DIR / f"net_{tag}.json").read_text())
        m = make_tcn(**{k: info["cfg"][k] for k in ("ch", "k", "dil")})
        m.load_state_dict(torch.load(MODEL_DIR / f"net_{tag}.pt"))
        m.eval()
        _M[tag] = (m, info)
    return _M[tag]


def predict(model, X: np.ndarray) -> np.ndarray:
    torch = _torch()
    with torch.no_grad():
        return model(torch.from_numpy(X[None].astype(np.float32)))[0].numpy()


def estimate(st, tag: str, fold, case=None) -> np.ndarray:
    """Per tick: the output of the tick's phase at the newest completed step (causal), in m."""
    key = tag if fold is None else f"{tag}_f{fold}"
    model, info = load(key)
    X, tk = features(st)
    Yh = predict(model, X) * OUT_SCALE
    k, p = LE.tick_index(st.tick_t)
    kk = np.clip(k, 0, len(tk) - 1)
    out = np.zeros((len(st.tick_t), 2))
    out[:, 0] = Yh[kk, 2 * p]
    out[:, 1] = Yh[kk, 2 * p + 1]
    return out


# ------------------------------------------------------------------ the cross-fitting driver (fixed rule)
MAX_EPOCHS_F0 = 14


def cross_fit(log=print, tag: str = "net_main", cfg: Optional[Dict] = None, max_epochs: int = MAX_EPOCHS_F0) -> Dict:
    """Fold 0 first, with fold 0's data as validation, for up to max_epochs; the epoch count with the lowest fold-0
    validation loss is then used for folds 1-4 and for the model on all folds (rule fixed before training)."""
    paths = all_train_paths()
    data = load_arrays(paths)
    info = {"n_cases": len(data), "rule": cross_fit.__doc__, "cfg": cfg}
    t0 = time.time()
    tr0 = [d for d in data if d["fold"] != 0]
    va0 = [d for d in data if d["fold"] == 0]
    r0 = train(tr0, max_epochs, seed=0, val=va0, log=log, cfg=cfg)
    vl = [h["val_loss"] for h in r0["history"]]
    n_ep = int(np.argmin(vl)) + 1
    info["fold0_val_loss"] = vl
    info["epochs"] = n_ep
    log(f"[net] {tag}: fold-0 validation chooses {n_ep} epochs ({time.time() - t0:.0f} s)")
    if n_ep == max_epochs:
        m0 = r0
    else:
        m0 = train(tr0, n_ep, seed=0, log=log, cfg=cfg)
    save(m0["model"], f"{tag}_f0", {"cfg": m0["cfg"], "params": m0["params"], "history": m0["history"], "fold": 0})
    for f in range(1, C.N_FOLDS):
        tr = [d for d in data if d["fold"] != f]
        m = train(tr, n_ep, seed=f, log=log, cfg=cfg)
        save(m["model"], f"{tag}_f{f}", {"cfg": m["cfg"], "params": m["params"], "history": m["history"], "fold": f})
    m = train(data, n_ep, seed=99, log=log, cfg=cfg)
    save(m["model"], tag, {"cfg": m["cfg"], "params": m["params"], "history": m["history"], "fold": None})
    info.update({"params": m["params"], "cfg": m["cfg"], "macs_per_step": macs_per_step(m["cfg"]),
                 "elapsed_s": time.time() - t0})
    (MODEL_DIR / f"{tag}_crossfit.json").write_text(json.dumps(info, default=float))
    log(f"[net] {tag}: 6 models in {time.time() - t0:.0f} s; {m['params']} parameters")
    return info


def int8_check(tag: str, data: List[Dict]) -> Dict:
    """Per-channel symmetric int8 quantisation of the weights (activations float): the output difference against the
    float model on the given arrays (RMS, um) and the float output's RMS."""
    torch = _torch()
    model, info = load(tag)
    import copy
    q = copy.deepcopy(model)
    with torch.no_grad():
        for name, p in q.named_parameters():
            if p.dim() >= 2:
                s = p.abs().amax(dim=tuple(range(1, p.dim())), keepdim=True).clamp(min=1e-12) / 127.0
                p.copy_(torch.round(p / s).clamp(-127, 127) * s)
    num = den = 0.0
    for d in data:
        a = predict(model, d["X"]); b = predict(q, d["X"])
        num += float(np.sum((a - b) ** 2)); den += float(np.sum(a ** 2))
    n = sum(len(d["X"]) * N_OUT for d in data)
    return {"rms_diff_um": math.sqrt(num / n) * OUT_SCALE * 1e6, "rms_out_um": math.sqrt(den / n) * OUT_SCALE * 1e6,
            "label": "CALC: weights per-channel int8, activations float (CMSIS-NN would also quantise activations)"}
