"""Firmware cost of each estimator on an nRF54L15-class MCU (CALCULATION).

Target: Arm Cortex-M33 at 128 MHz with single-precision FPU, 256 KB RAM, 1.5 MB NVM (AMF-44).
Counts are multiply-accumulates (MAC) of the implementation in fusion/ written as plain loops;
"structured" counts exploit the block structure of F (intent 3x3, oscillators 2x2, bias 1x1), which a
firmware port would use.  Cycle model (ASSUMPTION, to be profiled on hardware as ml/ did with QEMU
for the TCN): float32 2 cycles per MAC in plain C loops (range 1.5-3: one load/store unit feeds two loads per MAC), int8 CMSIS-NN 0.5 MAC per
cycle plus 300 cycles per layer call (ml/budget.py convention).  Memory in bytes, float32 unless noted.
Latency: the sensor chain (IMU anti-aliasing and digital filter 1.04 ms (the recorded 400 Hz filter),
FIFO read 0.35 ms mean, page sensor 2 ms or 10 ms) is compensated by prediction inside each estimator;
the compute time per stage tick is what the 0.5 ms tick budget (control.f_stage 2 kHz) must absorb.
"""
from __future__ import annotations

from typing import Dict

F_CLK = 128e6
CYC_PER_MAC_F32 = 2.0
TICK_S = 0.5e-3


def kf_dense(n: int, n_meas_scalar: int) -> int:
    """Covariance predict F P F' (2 n^3) + scalar updates (about 3 n^2 + 2 n each)."""
    return 2 * n ** 3 + n_meas_scalar * (3 * n * n + 2 * n)


def kf_structured(blocks, n_meas_scalar: int, nnz_h: int = 4) -> int:
    """Block-diagonal F: F P F' costs sum over block rows of 2 n b_i per column-block pair."""
    n = sum(blocks)
    fp = sum(2 * b * b * n for b in blocks)          # (F P): each block row b x b times b x n
    return fp + n_meas_scalar * (2 * n * nnz_h + 2 * n * n // 2 + 2 * n)


def estimator_costs(acc_rate: float = 1920.0, page_rate: float = 1000.0, rollback_samples: float = 4.0,
                    gru_hidden: int = 48, bmflc_basis: int = 23, tpl_rate: float = 500.0) -> Dict[str, Dict]:
    out = {}
    tick_rate = 1.0 / TICK_S
    # frozen Kalman oscillator (core mode 3): 5 states per axis, one update per tick per axis
    k5 = kf_dense(5, 1)
    out["kfosc"] = {"mac_per_tick": 2 * k5, "mac_per_s": 2 * k5 * tick_rate, "ram_bytes": 4 * (2 * 5 + 2 * 25) + 4 * 2 * 8,
                    "note": "two 5-state filters at 2 kHz plus the IMU increment buffer"}
    # AKF: 8 states, covariance shared by the two axes; accelerometer updates at acc_rate, page updates with rollback
    per_acc = 2 * 8 ** 3 + 2 * (3 * 64 + 16)          # dense predict + one scalar update per axis on the shared P
    per_acc_s = kf_structured((3, 2, 2, 1), 2)
    per_page = (2 * (3 * 64 + 16)) + rollback_samples * per_acc
    per_page_s = (2 * (3 * 64 + 16)) + rollback_samples * per_acc_s
    mac_s = per_acc * acc_rate + per_page * page_rate
    mac_s_s = per_acc_s * acc_rate + per_page_s * page_rate
    hist = int(max(4, rollback_samples + 2))
    out["akf"] = {"mac_per_s_dense": mac_s, "mac_per_s_structured": mac_s_s,
                  "mac_per_tick_structured": mac_s_s / tick_rate,
                  "ram_bytes": 4 * (16 + 64) * (1 + hist) + 4 * 2 * hist,
                  "history_snapshots": hist, "note": "8 states x 2 axes, shared covariance, rollback history for the delayed page sensor"}
    # context KF: 18 states jointly (template couples the axes); template update at 250 Hz
    per_acc_c = 2 * 18 ** 3 + 2 * (3 * 324 + 36)
    per_acc_cs = kf_structured((3, 3, 2, 2, 2, 2, 1, 1, 1, 1), 2)
    per_page_c = 2 * (3 * 324 + 36) + rollback_samples * per_acc_c
    per_page_cs = 2 * (3 * 324 + 36) + rollback_samples * per_acc_cs
    tpl = tpl_rate * (3 * 324 + 36 + 2 * 90)        # template update + nearest-point search over ~90 points
    out["context"] = {"mac_per_s_dense": per_acc_c * acc_rate + per_page_c * page_rate + tpl,
                      "mac_per_s_structured": per_acc_cs * acc_rate + per_page_cs * page_rate + tpl,
                      "ram_bytes": 4 * (18 + 324) * (1 + hist) + 2 * 4 * 2 * 2000,
                      "template_rate_hz": tpl_rate,
                      "note": "18 joint states; plus a template buffer of about 2000 points (2 letters at 20 um) in int16 pairs would be 8 kB, counted as float here"}
    # BMFLC and WFLC on acceleration (2 axes, pre-filter biquads, recursive sin/cos: 4 MAC per basis frequency)
    nb = bmflc_basis
    per_bm = 2 * 2 * 5 + 4 * nb + 2 * (2 * 2 * nb) + 2 * (2 * 2 * nb)
    out["bmflc"] = {"mac_per_s": per_bm * acc_rate + tick_rate * 2 * 2 * nb * 3, "ram_bytes": 4 * (2 * 2 * nb + 2 * nb + 8),
                    "note": f"{nb} basis frequencies x (sin, cos) x 2 axes"}
    out["wflc"] = {"mac_per_s": (2 * 2 * 5 + 40) * acc_rate + tick_rate * 40, "ram_bytes": 4 * 24,
                   "note": "fundamental + harmonic, adaptive frequency"}
    # learned GRU at 1 kHz
    from .learned import macs_per_step, n_params, N_IN
    H = gru_hidden
    out["gru"] = {"mac_per_step": macs_per_step(H), "mac_per_s": macs_per_step(H) * 1000.0,
                  "params": n_params(H), "weights_bytes_int8": n_params(H), "weights_bytes_f32": 4 * n_params(H),
                  "ram_bytes": 4 * (H + N_IN + 3 * H), "note": f"GRU({N_IN} -> {H}) + linear head at 1 kHz"}
    for k, v in out.items():
        m = v.get("mac_per_s_structured", v.get("mac_per_s", v.get("mac_per_s_dense")))
        v["cpu_fraction_f32"] = m * CYC_PER_MAC_F32 / F_CLK
        v["compute_per_tick_us_f32"] = m / tick_rate * CYC_PER_MAC_F32 / F_CLK * 1e6
    # worst tick: a page sample arrives and the filter re-applies the accelerometer samples since its acquisition
    us = CYC_PER_MAC_F32 / F_CLK * 1e6
    acc_per_tick = acc_rate / tick_rate
    out["akf"]["worst_tick_us_f32"] = (acc_per_tick * per_acc_s + per_page_s) * us
    out["context"]["worst_tick_us_f32"] = (acc_per_tick * per_acc_cs + per_page_cs) * us
    out["context"]["worst_tick_note"] = ("above the 500 us tick when rollback_samples is large (120 Hz page sensor): re-apply the stored "
                                         "gains to the state only (about 60 MAC per sample) and update the covariance once per page "
                                         "sample, or run the rollback in a lower-priority thread (proposal, not simulated)")
    out["gru"]["compute_per_step_us_f32"] = macs_per_step(H) * us
    out["gru"]["compute_per_step_us_int8_cmsis"] = (macs_per_step(H) / 0.5 + 3 * 300) / F_CLK * 1e6
    out["gru"]["cpu_fraction_int8_cmsis"] = (out["gru"]["mac_per_s"] / 0.5 + 1000.0 * 3 * 300) / F_CLK
    out["_assumptions"] = {"f_clk_hz": F_CLK, "float32_cycles_per_mac": CYC_PER_MAC_F32,
                           "int8_cmsis_nn": "0.5 MAC/cycle + 300 cycles per layer call (ml/budget.py convention)",
                           "acc_rate_hz": acc_rate, "page_rate_hz": page_rate, "rollback_samples": rollback_samples,
                           "label": "CALCULATION; ASSUMPTION for the cycle model; to be profiled on the target"}
    return out
