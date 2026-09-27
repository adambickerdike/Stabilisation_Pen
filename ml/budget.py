#!/usr/bin/env python3
r"""Compute / memory / time / energy budget of the TCN predictor against docs/icd.md s5
(<= 35 k MAC per inference, <= 32 kB flash weights, <= 8 kB activation RAM, <= 1 ms at 128 MHz).

Numbers are ANALYTICAL CALCULATIONS (MACs, bytes) plus, where available, the executed-
instruction count of the plain-C kernel on an emulated Cortex-M33 (QEMU, not cycle
accurate) and the ARM object sizes from ml/export_c.py.  Nothing is measured on nRF5340
hardware.  Assumptions (stated in the output):
  * plain C (ml/export/tcn_int8.c, gcc -O2): cycles = QEMU instruction count x CPI,
    CPI 1.0 / 1.3 / 1.6 (Cortex-M33: single-cycle ALU/MLA, 1-2 cycle loads, 2-3 cycle taken
    branches; weights and code small enough for the 8 kB flash cache after the first call);
  * CMSIS-NN int8 (arm_fully_connected_s8, SMLAD path): 0.5 MAC/cycle central, 0.15
    pessimistic (EML-23 / EML-24), plus ~300 cycles per kernel call (8 calls);
  * energy: 183 pJ/cycle at 128 MHz, 155 pJ/cycle at 64 MHz (EML-02: CoreMark current of the
    whole SoC, typical, 3 V) - an order-of-magnitude figure, not an NN-kernel measurement.
Run: python3 -m ml.budget --model tcn_s --alt tcn_m
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from . import common as C
from . import models as M

PJ_PER_CYCLE = {128e6: 183e-12, 64e6: 155e-12}
CPI = (1.0, 1.3, 1.6)
CMSIS_MAC_PER_CYCLE = {"central": 0.5, "pessimistic": 0.15}
CMSIS_CALL_OVERHEAD = 300


def arch_budget(name):
    cfg = json.load(open(os.path.join(C.RESULTS, "model", f"{name}.json")))
    m = M.TCNTree(channels=tuple(cfg["channels"]), head=cfg["head"])
    rows = m.layer_table()
    macs = sum(r["macs"] for r in rows)
    weights = sum(r["weights"] for r in rows)
    biases = sum(r["biases"] for r in rows)
    n_layers = len(rows)
    # int8 weights, int32 bias (+ folded copy for the plain-C kernel), per-layer struct 48 B
    flash_params = weights + 4 * biases * 2 + 48 * n_layers
    # window mode activations: int8 input window + ping-pong buffers (see export_c.scratch_sizes)
    outs = [r["out_elems"] for r in rows[:6]]
    head = rows[6]["out_elems"]
    scratch = max(outs[0], outs[2], outs[4], head) + max(outs[1], outs[3], outs[5])
    ram_int = C.W * M.C_IN + scratch
    ram_float_api = ram_int + C.W * 2 * 4          # + float window kept by the caller
    stream_macs = sum(r["stream_macs"] for r in rows)
    stream_state = sum(r["stream_state_elems"] for r in rows[:6])
    naive = sum(C.W * 2 * r["c_in"] * r["c_out"] for r in rows[:6]) + sum(r["macs"] for r in rows[6:])
    out = {"name": name, "channels": cfg["channels"], "head": cfg["head"], "layers": rows,
           "macs_window_tree": int(macs), "params": int(weights + biases), "weights_int8_B": int(weights),
           "biases_int32_B": int(4 * biases), "flash_params_B": int(flash_params),
           "ram_activation_int_B": int(ram_int), "ram_activation_float_api_B": int(ram_float_api),
           "streaming": {"macs_per_step": int(stream_macs),
                         "state_int8_B": int(stream_state),
                         "note": "one new position per level per 4 ms step from cached level outputs; exact "
                                 "only if the f_est channel is stored per step or moved to the head"},
           "naive_dilated_all_positions_macs": int(naive),
           "val_rr_all_at_fc25": cfg.get("val_rr_all_at_fc25")}
    cm = {}
    for k, eff in CMSIS_MAC_PER_CYCLE.items():
        cyc = macs / eff + CMSIS_CALL_OVERHEAD * 8
        cm[k] = {"mac_per_cycle": eff, "cycles": cyc, "time_ms_128MHz": cyc / 128e6 * 1e3,
                 "time_ms_64MHz": cyc / 64e6 * 1e3, "energy_uJ_128MHz": cyc * PJ_PER_CYCLE[128e6] * 1e6,
                 "power_mW_at_250Hz_128MHz": cyc * PJ_PER_CYCLE[128e6] * 250 * 1e3,
                 "cpu_load_128MHz": cyc / 128e6 / C.TS}
        s_cyc = stream_macs / eff + CMSIS_CALL_OVERHEAD * 8
        cm[k]["streaming_time_ms_128MHz"] = s_cyc / 128e6 * 1e3
    out["cmsis_nn_estimate"] = cm
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="tcn_s")
    ap.add_argument("--alt", default="tcn_m")
    args = ap.parse_args()
    res = {"budget_icd": {"macs": C.MAC_BUDGET, "flash_B": C.FLASH_BUDGET_B, "ram_B": C.RAM_BUDGET_B,
                          "time_ms": C.TIME_BUDGET_S * 1e3, "f_clk_MHz": C.F_CLK_HZ / 1e6},
           "assumptions": {"cpi_plain_c": CPI, "cmsis_mac_per_cycle": CMSIS_MAC_PER_CYCLE,
                           "cmsis_call_overhead_cycles": CMSIS_CALL_OVERHEAD,
                           "energy_pJ_per_cycle": {"128MHz": 183, "64MHz": 155, "source": "EML-02 CoreMark, whole SoC"}},
           "models": {}}
    for nm in (args.model, args.alt):
        if nm and os.path.exists(os.path.join(C.RESULTS, "model", f"{nm}.json")):
            res["models"][nm] = arch_budget(nm)
    # measured artefacts of the exported model
    ex_path = os.path.join(C.RESULTS, "export_c.json")
    if os.path.exists(ex_path):
        ex = json.load(open(ex_path))
        d = res["models"][ex["model"]]
        arm = ex.get("arm_m33", {}).get("sections", {}).get("-O2", {})
        d["arm_O2_object"] = {k: v for k, v in arm.items() if k != "detail"}
        d["arm_Os_object"] = {k: v for k, v in ex.get("arm_m33", {}).get("sections", {}).get("-Os", {}).items()
                              if k != "detail"}
        ins = ex.get("qemu_m33", {}).get("instructions_per_inference")
        if ins:
            pc = {}
            for cpi in CPI:
                cyc = ins * cpi
                pc[f"cpi_{cpi}"] = {"cycles": cyc, "time_ms_128MHz": cyc / 128e6 * 1e3, "time_ms_64MHz": cyc / 64e6 * 1e3,
                                    "energy_uJ_128MHz": cyc * PJ_PER_CYCLE[128e6] * 1e6,
                                    "power_mW_at_250Hz_128MHz": cyc * PJ_PER_CYCLE[128e6] * 250 * 1e3,
                                    "cpu_load_128MHz": cyc / 128e6 / C.TS}
            d["plain_c"] = {"qemu_instructions_per_inference": ins,
                            "instructions_per_mac": ins / d["macs_window_tree"], "by_cpi": pc,
                            "note": "QEMU -icount instruction count (not cycle accurate)"}
            # scale the instruction count to the other architecture by MACs (same kernel)
            for nm, dd in res["models"].items():
                if nm != ex["model"]:
                    ins2 = ins / d["macs_window_tree"] * dd["macs_window_tree"]
                    dd["plain_c_scaled"] = {"instructions_est": ins2,
                                            "time_ms_128MHz_cpi_1.3": ins2 * 1.3 / 128e6 * 1e3,
                                            "note": "scaled from the exported model by MAC count"}
    for nm, d in res["models"].items():
        chk = {"macs": d["macs_window_tree"] <= C.MAC_BUDGET, "flash_params": d["flash_params_B"] <= C.FLASH_BUDGET_B,
               "ram": d["ram_activation_float_api_B"] <= C.RAM_BUDGET_B,
               "time_cmsis_central": d["cmsis_nn_estimate"]["central"]["time_ms_128MHz"] <= 1.0,
               "time_cmsis_pessimistic": d["cmsis_nn_estimate"]["pessimistic"]["time_ms_128MHz"] <= 1.0}
        if "plain_c" in d:
            chk["time_plain_c_cpi_1.3"] = d["plain_c"]["by_cpi"]["cpi_1.3"]["time_ms_128MHz"] <= 1.0
        d["meets_icd"] = chk
    res["meta"] = C.meta(status="ANALYTICAL CALCULATION + emulator instruction count (no hardware measurement); "
                                "model trained on SIMULATION / synthetic data")
    C.write_json(os.path.join(C.RESULTS, "budget.json"), res)
    lines = ["| quantity | " + " | ".join(res["models"]) + " | ICD budget |", "|---|" + "---|" * (len(res["models"]) + 1)]

    def row(label, f, budget=""):
        lines.append(f"| {label} | " + " | ".join(f(d) for d in res["models"].values()) + f" | {budget} |")
    row("MAC per inference (window, tree)", lambda d: f"{d['macs_window_tree']:,}", "<= 35,000")
    row("parameters", lambda d: f"{d['params']:,}")
    row("flash: int8 weights + int32 biases (x2) + structs", lambda d: f"{d['flash_params_B']:,} B", "<= 32 kB")
    row("ARM -O2 object: code / rodata", lambda d: (f"{d['arm_O2_object']['text_code_B']:,} / "
                                                    f"{d['arm_O2_object']['rodata_B']:,} B") if "arm_O2_object" in d else "n/a")
    row("activation RAM (int8 window + ping-pong; + float window)",
        lambda d: f"{d['ram_activation_int_B']:,} B ({d['ram_activation_float_api_B']:,} B)", "<= 8 kB")
    row("plain C: QEMU instructions per inference", lambda d: f"{d['plain_c']['qemu_instructions_per_inference']:,.0f}"
        if "plain_c" in d else (f"~{d['plain_c_scaled']['instructions_est']:,.0f} (scaled)" if "plain_c_scaled" in d else "n/a"))
    row("plain C time @128 MHz (CPI 1.0 / 1.3 / 1.6)", lambda d: " / ".join(
        f"{d['plain_c']['by_cpi'][f'cpi_{c}']['time_ms_128MHz']:.2f}" for c in CPI) + " ms" if "plain_c" in d else
        (f"~{d['plain_c_scaled']['time_ms_128MHz_cpi_1.3']:.2f} ms (CPI 1.3)" if "plain_c_scaled" in d else "n/a"), "<= 1 ms")
    row("CMSIS-NN time @128 MHz (0.5 / 0.15 MAC/cycle)", lambda d: f"{d['cmsis_nn_estimate']['central']['time_ms_128MHz']:.2f}"
        f" / {d['cmsis_nn_estimate']['pessimistic']['time_ms_128MHz']:.2f} ms", "<= 1 ms")
    row("energy per inference @128 MHz (CMSIS central)", lambda d: f"{d['cmsis_nn_estimate']['central']['energy_uJ_128MHz']:.1f} uJ")
    row("power at 250 Hz @128 MHz (CMSIS central)", lambda d: f"{d['cmsis_nn_estimate']['central']['power_mW_at_250Hz_128MHz']:.2f} mW")
    row("streaming alternative: MAC per step / state RAM", lambda d: f"{d['streaming']['macs_per_step']:,} / "
        f"{d['streaming']['state_int8_B']:,} B")
    row("naive dilated conv at all 64 positions", lambda d: f"{d['naive_dilated_all_positions_macs']:,} MAC")
    with open(os.path.join(C.RESULTS, "budget_table.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
