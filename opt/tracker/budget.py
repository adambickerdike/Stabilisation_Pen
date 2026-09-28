"""MCU cost of the final trackers on an nRF54L15-class MCU (CALCULATION, fusion/budget.py conventions).

Target (AMF-44 via fusion.budget): Arm Cortex-M33 at 128 MHz with single-precision FPU, 256 KB RAM.  Cycle model
(ASSUMPTION, to be profiled): 2 cycles per float32 MAC in plain C; int8 CMSIS-NN 0.5 MAC per cycle plus 300 cycles
per layer call.  Stage tick 0.5 ms (2 kHz).  The adjoint-tuned AKF has the structure of fusion's AKF (8 states per
axis, shared covariance, rollback of the delayed page sample), so its cost is fusion.budget's AKF cost; the cap,
gates and output low-pass add a few tens of operations per tick.  The learned models run at 1 kHz.
"""
from __future__ import annotations

from typing import Dict

from fusion import budget as FB

from . import learned as LN


def gru_cost(n_in: int, hidden: int, n_out: int, rate_hz: float = 1000.0) -> Dict:
    mac = LN.macs_per_step(n_in, hidden, n_out)
    npar = LN.n_params(n_in, hidden, n_out)
    us = FB.CYC_PER_MAC_F32 / FB.F_CLK * 1e6
    return {"n_in": n_in, "hidden": hidden, "n_out": n_out, "rate_hz": rate_hz, "mac_per_step": mac,
            "mac_per_s": mac * rate_hz, "params": npar, "weights_bytes_int8": npar, "weights_bytes_f32": 4 * npar,
            "state_ram_bytes_f32": 4 * (hidden + n_in + 3 * hidden),
            "cpu_fraction_f32": mac * rate_hz * FB.CYC_PER_MAC_F32 / FB.F_CLK,
            "compute_per_step_us_f32": mac * us,
            "cpu_fraction_int8_cmsis": (mac / 0.5 + 3 * 300) * rate_hz / FB.F_CLK,
            "compute_per_step_us_int8_cmsis": (mac / 0.5 + 3 * 300) / FB.F_CLK * 1e6,
            "within_10k_mac_contract": mac <= 10_000}


def costs(gru_hidden: int = 48, gate_hidden: int = 24) -> Dict:
    base = FB.estimator_costs(page_rate=1000.0, rollback_samples=4.0)
    akf = dict(base["akf"])
    extra_per_tick = 60                                  # prediction, cap, gates, authority, low-pass per tick (both axes)
    akf["output_stage_mac_per_tick"] = extra_per_tick
    akf["mac_per_s_total"] = akf["mac_per_s_structured"] + extra_per_tick * 2000.0
    akf["cpu_fraction_f32_total"] = akf["mac_per_s_total"] * FB.CYC_PER_MAC_F32 / FB.F_CLK
    gru = gru_cost(LN.N_IN_GRU, gru_hidden, 2)
    gate = gru_cost(LN.N_IN_GATE, gate_hidden, 1)
    hybrid = {"akf_mac_per_s": akf["mac_per_s_total"], "gate": gate,
              "mac_per_s_total": akf["mac_per_s_total"] + gate["mac_per_s"],
              "cpu_fraction_f32_total": akf["cpu_fraction_f32_total"] + gate["cpu_fraction_f32"],
              "cpu_fraction_akf_f32_gate_int8": akf["cpu_fraction_f32_total"] + gate["cpu_fraction_int8_cmsis"],
              "ram_bytes": akf["ram_bytes"] + gate["state_ram_bytes_f32"] + gate["weights_bytes_f32"]}
    return {"akf_adjoint_tuned": akf, "gru_band": gru, "hybrid_akf_gate": hybrid,
            "frozen_kalman_reference": base["kfosc"], "old_gru_reference": base["gru"],
            "_assumptions": dict(base["_assumptions"], note="CALCULATION; cycle model ASSUMPTION (fusion/budget.py); "
                                 "output stage of the AKF counted as 60 MAC per tick")}
