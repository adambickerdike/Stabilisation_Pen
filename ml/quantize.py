#!/usr/bin/env python3
r"""int8 post-training quantisation of the TCN and its bit-exact integer reference.

Scheme (docs/icd.md s5; TFLite / CMSIS-NN conventions):
  * input tensor: int8 symmetric, zero point 0, scale IN_CLIP_UM/127 um per LSB for dp
    (f_est channel: 0.063 Hz per LSB), q = clamp(floor(x * inv_scale + 0.5), -127, 127)
    evaluated in float32 (the C code does the same with -ffp-contract=off);
  * weights: int8 symmetric per tensor (zero point 0), scale max|W|/127;
  * bias: int32, scale s_in * s_w;
  * activations after ReLU: int8 asymmetric, zero point -128, scale a_max/255 with a_max
    from a calibration set of training windows (max or a high percentile, chosen on val);
    ReLU is the clamp at the zero point (act_min = -128);
  * requantisation: acc * M with M = s_in s_w / s_out as a Q31 multiplier and shift,
    rounded exactly like CMSIS-NN arm_nn_requantize (doubling high multiply with
    rounding, then rounding divide by a power of two);
  * output layer: int32 accumulator requantised to int16 in 0.1 um (the research-log unit
    of dhat, docs/icd.md s4.2), clamp +-32767.
`run_int8` is the integer reference that ml/export/tcn_int8.c must match bit-exactly.
Outputs: results/ml/model/<name>_int8.npz, results/ml/quantization.json.
Run: python3 -m ml.quantize --model tcn_s
Evidence status: SIMULATION / synthetic data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import torch

from . import common as C
from . import datasets as D
from . import metrics as MT
from . import models as M
from . import train as T

IN_SCALE_UM = C.IN_CLIP_UM / 127.0                       # um per LSB (dp channels)
IN_INV_SCALE = np.float32(127.0 / C.IN_CLIP_UM)          # float32 constant shared with C
F_INV_SCALE = np.float32(C.F_GAIN * 127.0 / C.IN_CLIP_UM)  # LSB per Hz for the f_est channel (15.875)
F_REF = np.float32(C.F_REF_HZ)
OUT_LSB_UM = 0.1


def quantize_multiplier(m):
    """TFLite QuantizeMultiplier: m = q * 2**shift, q in [2**30, 2**31) (Q31)."""
    if m == 0.0:
        return 0, 0
    mant, shift = np.frexp(m)
    q = int(round(mant * (1 << 31)))
    if q == (1 << 31):
        q //= 2
        shift += 1
    if shift < -31:
        return 0, 0
    return int(q), int(shift)


def _dhm(a, b):
    """arm_nn_doubling_high_mult_no_sat on int64 arrays."""
    return (a * np.int64(b) + (np.int64(1) << np.int64(30))) >> np.int64(31)


def _div_pow2(x, e):
    """arm_nn_divide_by_power_of_two (round half away from zero)."""
    if e == 0:
        return x
    mask = np.int64((1 << e) - 1)
    rem = x & mask
    res = x >> np.int64(e)
    thr = (mask >> np.int64(1)) + (res < 0).astype(np.int64)
    return res + (rem > thr).astype(np.int64)


def requantize(acc, mult, shift):
    left, right = max(shift, 0), max(-shift, 0)
    v = acc * np.int64(1 << left)
    if np.any(np.abs(v) >= (1 << 31)):
        raise OverflowError("requantize input exceeds int32 (CMSIS-NN would overflow)")
    return _div_pow2(_dhm(v, mult), right)


# ------------------------------------------------------------------ input quantisation (float32, as in C)
def quantize_inputs(dp_um, f_est):
    """Per-tick int8 channels (n, 3) exactly as tcn_quantize_input() in C."""
    dp = np.asarray(dp_um, np.float32)
    q = np.empty((len(dp), 3), np.int8)
    v = np.floor(dp * IN_INV_SCALE + np.float32(0.5))
    q[:, :2] = np.clip(v, -127, 127).astype(np.int8)
    f = np.asarray(f_est, np.float32)
    vf = np.floor((f - F_REF) * F_INV_SCALE + np.float32(0.5))
    q[:, 2] = np.clip(vf, -127, 127).astype(np.int8)
    return q


def int_windows(qch):
    """(K, 64, 3) int8 windows of a recording (zero padded before tick 63, f broadcast)."""
    pad = np.zeros((C.W - 1, 3), np.int8)
    chp = np.vstack([pad, qch])
    idx = np.arange(len(qch)) + (C.W - 1)
    off = np.arange(-(C.W - 1), 1)
    win = chp[idx[:, None] + off[None, :]]
    win[:, :, 2] = chp[idx, 2][:, None]
    return win


# ------------------------------------------------------------------ quantised model
def build_qmodel(model, calib_x, calib="max", pct=99.99):
    """calib_x: (N, 64, 3) float windows from training writers."""
    with torch.no_grad():
        _, acts = model(torch.from_numpy(calib_x), return_acts=True)
    acts = [a.numpy() for a in acts]          # [input, level1..6, head, out]
    s_in0 = (C.IN_CLIP_UM / C.S_IN) / 127.0   # model units per LSB of the input tensor
    lins = list(model.levels) + [model.head]
    layers = []
    s_prev, zp_prev = s_in0, 0
    for i, lin in enumerate(lins):
        Wf = lin.weight.detach().numpy().astype(np.float64)
        bf = lin.bias.detach().numpy().astype(np.float64)
        s_w = float(np.max(np.abs(Wf)) / 127.0)
        wq = np.clip(np.round(Wf / s_w), -127, 127).astype(np.int8)
        a = acts[i + 1]
        amax = float(np.max(a)) if calib == "max" else float(np.percentile(a, pct))
        amax = max(amax, 1e-6)
        s_out = amax / 255.0
        bq = np.round(bf / (s_prev * s_w)).astype(np.int64)
        mult, shift = quantize_multiplier(s_prev * s_w / s_out)
        layers.append({"w": wq, "b": bq.astype(np.int32), "in_offset": -zp_prev, "out_zp": -128, "mult": mult,
                       "shift": shift, "act_min": -128, "act_max": 127, "s_w": s_w, "s_in": s_prev, "s_out": s_out,
                       "a_max": amax, "c_in": int(Wf.shape[1]), "c_out": int(Wf.shape[0])})
        s_prev, zp_prev = s_out, -128
    Wf = model.out.weight.detach().numpy().astype(np.float64)
    bf = model.out.bias.detach().numpy().astype(np.float64)
    s_w = float(np.max(np.abs(Wf)) / 127.0)
    wq = np.clip(np.round(Wf / s_w), -127, 127).astype(np.int8)
    bq = np.round(bf / (s_prev * s_w)).astype(np.int64)
    m_out = s_prev * s_w * C.S_OUT / OUT_LSB_UM      # acc -> 0.1 um
    mult, shift = quantize_multiplier(m_out)
    out = {"w": wq, "b": bq.astype(np.int32), "in_offset": -zp_prev, "mult": mult, "shift": shift, "s_w": s_w,
           "s_in": s_prev, "out_lsb_um": OUT_LSB_UM, "c_in": int(Wf.shape[1]), "c_out": 2}
    qm = {"layers": layers, "out": out, "in_scale_um": IN_SCALE_UM, "in_inv_scale": float(IN_INV_SCALE),
          "f_inv_scale": float(F_INV_SCALE), "f_ref_hz": float(F_REF), "calib": calib, "pct": pct,
          "arch": model.config()}
    qm["hash"] = model_hash(qm)
    return qm


def model_hash(qm):
    h = hashlib.sha256()
    for L in qm["layers"] + [qm["out"]]:
        for k in ("w", "b"):
            h.update(np.ascontiguousarray(L[k]).tobytes())
        h.update(np.array([L["mult"], L["shift"], L["in_offset"]], np.int64).tobytes())
    return h.hexdigest()


def run_int8(qm, xq, stats=None):
    """Integer reference.  xq: (N, 64, 3) int8.  Returns (N, 2) int16 in 0.1 um."""
    h = xq.astype(np.int64)
    for i, L in enumerate(qm["layers"]):
        if i < 6:
            n, Lp, c = h.shape
            h = h.reshape(n, Lp // 2, 2 * c)
        else:
            h = h.reshape(h.shape[0], -1)
        acc = (h + L["in_offset"]) @ L["w"].astype(np.int64).T + L["b"].astype(np.int64)
        v = requantize(acc, L["mult"], L["shift"]) + L["out_zp"]
        if stats is not None:
            stats.setdefault(i, [0, 0])
            stats[i][0] += int(np.sum(v > L["act_max"]))
            stats[i][1] += v.size
        h = np.clip(v, L["act_min"], L["act_max"])
    O = qm["out"]
    acc = (h + O["in_offset"]) @ O["w"].astype(np.int64).T + O["b"].astype(np.int64)
    v = requantize(acc, O["mult"], O["shift"])
    if stats is not None:
        stats.setdefault("out", [0, 0])
        stats["out"][0] += int(np.sum(np.abs(v) > 32767))
        stats["out"][1] += v.size
    return np.clip(v, -32767, 32767).astype(np.int16)


def predict_int8(qm, rec, batch=65536, stats=None):
    X = int_windows(quantize_inputs(rec["dp_um"], rec["f_est"]))
    out = np.empty((len(X), 2), np.float64)
    for a in range(0, len(X), batch):
        out[a:a + batch] = run_int8(qm, X[a:a + batch], stats) * OUT_LSB_UM
    return out


def save_qmodel(qm, path):
    arrs = {}
    for i, L in enumerate(qm["layers"]):
        arrs[f"w{i}"], arrs[f"b{i}"] = L["w"], L["b"]
    arrs["w_out"], arrs["b_out"] = qm["out"]["w"], qm["out"]["b"]
    meta = {"layers": [{k: v for k, v in L.items() if k not in ("w", "b")} for L in qm["layers"]],
            "out": {k: v for k, v in qm["out"].items() if k not in ("w", "b")},
            **{k: qm[k] for k in ("in_scale_um", "in_inv_scale", "f_inv_scale", "f_ref_hz", "calib", "pct", "arch", "hash")}}
    np.savez(path, meta=json.dumps(meta), **arrs)


def load_qmodel(path):
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    layers = []
    for i, L in enumerate(meta["layers"]):
        layers.append(dict(L, w=z[f"w{i}"], b=z[f"b{i}"]))
    qm = {k: v for k, v in meta.items() if k not in ("layers", "out")}
    qm["layers"] = layers
    qm["out"] = dict(meta["out"], w=z["w_out"], b=z["b_out"])
    return qm


def load_float(name):
    cfg = json.load(open(os.path.join(C.RESULTS, "model", f"{name}.json")))
    model = M.TCNTree(channels=tuple(cfg["channels"]), head=cfg["head"])
    model.load_state_dict(torch.load(os.path.join(C.RESULTS, "model", f"{name}.pt")))
    model.use_fest = bool(cfg.get("use_fest", True))
    model.eval()
    return model, cfg


def compare(model, qm, recs):
    """Float vs int8 on a split: RMS prediction difference on scored ticks and metric stats."""
    sf, sq, dif, n = [], [], 0.0, 0
    sat = {}
    for r in recs:
        pf = M.predict(model, r)
        pq = predict_int8(qm, r, stats=sat)
        m = MT.score_mask(r)
        dif += float(np.sum((pf[m] - pq[m]) ** 2))
        n += int(m.sum())
        sf.append(MT.rec_stats(r, pf))
        sq.append(MT.rec_stats(r, pq))
    return MT.stack(sf), MT.stack(sq), float(np.sqrt(dif / max(n, 1))), sat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="tcn_s")
    ap.add_argument("--n-calib", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    torch.set_num_threads(2)
    t0 = time.time()
    model, cfg = load_float(args.model)
    train, val = D.load_split("train"), D.load_split("val")
    ch, _, w = T.stack_split(train)
    rng = np.random.default_rng(args.seed)
    ci = rng.choice(np.flatnonzero(w > 0), size=args.n_calib, replace=False)
    calib_x = M.gather_windows(ch, ci)
    cands = {}
    for calib, pct in (("max", None), ("pct", 99.99), ("pct", 99.9)):
        qm = build_qmodel(model, calib_x, calib, pct if pct else 100.0)
        _, sq, d_rms, _ = compare(model, qm, val)
        crit, g = MT.matched_rr_all(sq, C.FC_HEADLINE_UM)
        cands[f"{calib}{'' if pct is None else pct}"] = (crit, qm, d_rms)
        print(f"calib {calib} {pct}: val crit {crit:.4f} (g {g:.3f}), float-int8 rms diff {d_rms:.2f} um", flush=True)
    best_key = min(cands, key=lambda k: cands[k][0])
    qm = cands[best_key][1]
    save_qmodel(qm, os.path.join(C.RESULTS, "model", f"{args.model}_int8.npz"))
    res = {"model": args.model, "calibration": {"n_windows": args.n_calib, "source": "training writers", "seed": args.seed,
                                                "candidates_val_criterion": {k: v[0] for k, v in cands.items()},
                                                "candidates_val_rms_diff_um": {k: v[2] for k, v in cands.items()},
                                                "selected": best_key},
           "hash_sha256": qm["hash"], "hash_low32": int(qm["hash"][-8:], 16),
           "scheme": "int8 symmetric per-tensor weights, int8 asymmetric activations (zp -128 after ReLU), int32 bias, "
                     "CMSIS-NN requantisation, int16 output in 0.1 um",
           "layers": [{k: v for k, v in L.items() if k not in ("w", "b")} for L in qm["layers"]],
           "out_layer": {k: v for k, v in qm["out"].items() if k not in ("w", "b")}, "splits": {}}
    for split in ("val", "test", "test_freq_holdout", "test_features", "realism_sim"):
        if not D.exists(split):
            continue
        recs = val if split == "val" else D.load_split(split)
        sf, sq, d_rms, sat = compare(model, qm, recs)
        row = {"rms_float_minus_int8_um": d_rms,
               "saturation_fraction": {str(k): v[0] / max(v[1], 1) for k, v in sat.items()}}
        for tag, st in (("float", sf), ("int8", sq)):
            p1 = MT.pooled(st, 1.0)
            row[tag] = {"rr_band_g1": [float(x) for x in p1["rr_band"]], "rr_all_g1": p1["rr_all"], "fc_g1_um": p1["fc_um"]}
        res["splits"][split] = row
        print(f"{split}: rms diff {d_rms:.2f} um; rr_all float {row['float']['rr_all_g1']:.4f} "
              f"int8 {row['int8']['rr_all_g1']:.4f}; fc float {row['float']['fc_g1_um']:.2f} int8 {row['int8']['fc_g1_um']:.2f}",
              flush=True)
    res["meta"] = C.meta(seeds={"calibration": args.seed}, extra={"elapsed_s": time.time() - t0})
    C.write_json(os.path.join(C.RESULTS, "quantization.json"), res)
    print(f"done {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
