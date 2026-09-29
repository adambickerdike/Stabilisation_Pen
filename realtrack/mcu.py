"""MCU cost of each estimator family per 1 kHz step (1 ms of real time) on the pen's microcontroller (CALCULATION).

Target: Arm Cortex-M33 at 128 MHz with single-precision FPU: the nRF54L15 of the Rev H / Rev J pens (256 KB RAM, 1.5 MB
NVM; LIT AMF-44 via fusion/budget.py) and the nRF5340 application core of the research board (512 KB RAM, 1 MB flash;
electronics/README.md, firmware/README.md).  Cycle model (ASSUMPTION of fusion/budget.py, to be profiled on the target):
2 cycles per float32 multiply-accumulate in plain C loops (range 1.5-3), int8 CMSIS-NN 0.5 MAC per cycle plus 300 cycles
per layer call; sin/cos by a rotation recursion (4 MAC per step) or a 256-entry table; one scalar division = 14 cycles
(VDIV, firmware/README.md), counted as 7 MAC.  Counts are for both page axes.  The firmware's own measured load (QEMU
instruction counts, firmware/README.md: the stage tick with the frozen Kalman estimator 11 535 instructions per 0.5 ms,
31 % of the core at CPI 1) is the context: the budget left for a tracker is about half the core.
"""
from __future__ import annotations

import math
from typing import Dict

F_CLK = 128e6
CYC_MAC = 2.0
ACC_RATE = 1920.0            # accelerometer pairs per second (3.84 kHz ODR, pairs averaged)
TICK_RATE = 2000.0
PAGE_RATE = 1000.0


def _pack(mac_per_s: float, ram_bytes: int, flash_bytes: int, note: str, int8_cycles_per_s: float = None) -> Dict:
    cyc = int8_cycles_per_s if int8_cycles_per_s is not None else mac_per_s * CYC_MAC
    return {"mac_per_1ms_step": mac_per_s / 1000.0, "mac_per_s": mac_per_s, "cycles_per_1ms_step": cyc / 1000.0,
            "cpu_share_128MHz": cyc / F_CLK, "us_per_1ms_step": cyc / F_CLK * 1e6 / 1000.0,
            "ram_bytes": int(ram_bytes), "flash_bytes": int(flash_bytes),
            "ram_share_nrf54l15": ram_bytes / (256 * 1024), "ram_share_nrf5340": ram_bytes / (512 * 1024),
            "note": note}


def authority_cost() -> Dict:
    per_tick = 2 * 2 + 3 + 6 + 2 * 2          # |d|^2, low-pass, sqrt (~6), clip/ramp, two multiplies
    return _pack(per_tick * TICK_RATE, 32, 400, "soft amplitude authority: one low-pass of |d|^2, sqrt, clip, ramp")


def epll_cost(harm: bool = True) -> Dict:
    nh = 2 if harm else 1
    per_acc = 2 * 2 * 5 + 2 * (4 * nh * 2 + 4) + 4 * nh + 7 + 10    # pre-filters, amplitude loops, PD, recursion, div
    per_tick = 2 * (4 * nh) + nh * (2 * 10 + 7) + 8                  # prediction, pre-filter inversion at w, 2w
    return _pack(per_acc * ACC_RATE + per_tick * TICK_RATE, 4 * (2 * 4 * nh + 16 + 8), 1500,
                 f"EPLL: shared phase/frequency, per-axis amplitudes of {nh} harmonic(s); pre-filter inverted at w, 2w")


def bmflc_kf_cost(nb: int, decim: int = 2) -> Dict:
    ns = 2 * nb
    per_upd = ns * ns + ns * ns + 2 * 2 * ns + 4 * nb + ns + 7        # P h, P update, 2 axes innovations, recursion
    per_tick = 2 * 2 * nb + 4 * nb                                     # prediction of every component, both axes
    return _pack(per_upd * ACC_RATE / decim + per_tick * TICK_RATE + 2 * 2 * 5 * ACC_RATE,
                 4 * (ns * ns + 2 * ns + 2 * nb + 16), 2000,
                 f"BMFLC-KF: {nb} frequencies, {ns} weights per axis, one {ns}x{ns} covariance shared by the axes")


def bmflc_cost(nb: int) -> Dict:
    per_acc = 2 * 2 * 5 + 2 * (2 * 2 * nb) + 4 * nb
    per_tick = 2 * 2 * nb + 4 * nb
    return _pack(per_acc * ACC_RATE + per_tick * TICK_RATE, 4 * (2 * 2 * nb + 2 * nb + 16), 1500,
                 f"BMFLC (LMS): {nb} frequencies")


def wflc_cost() -> Dict:
    return _pack((2 * 2 * 5 + 40) * ACC_RATE + 40 * TICK_RATE, 4 * 24, 1200, "WFLC: fundamental + harmonic")


def akf_cost(use_pos: bool = True) -> Dict:
    from fusion import budget as FB
    c = FB.estimator_costs()["akf"]
    mac = c["mac_per_s_structured"]
    if not use_pos:
        mac = mac - (2 * (3 * 64 + 16) + 4.0 * FB.kf_structured((3, 2, 2, 1), 2)) * PAGE_RATE
    return _pack(mac, c["ram_bytes"] if use_pos else 4 * (16 + 64) * 2, 3000,
                 "AKF (fusion/budget.py structured count)" + ("" if use_pos else " without the page sensor's roll-back"))


def detector_cost() -> Dict:
    n_win, nseg = 1000, 500                     # 4 s at 250 Hz, 2 s segments, 50 % overlap -> 3 segments
    fft = 3 * 2 * (2.5 * nseg * math.log2(nseg))
    med = 251 * 25 * math.log2(25)              # running median of the log spectrum (+-3 Hz)
    hp = n_win * 2 * 2 * 5 * 2                  # zero-phase high-pass over the window
    per_update = fft + med + hp
    return _pack(per_update * 20.0, 4 * (n_win * 2 + nseg + 256 * 3), 6000,
                 "ai2's tremor-line detector: Welch over the last 4 s every 50 ms (the G4 / gated trackers' gate)")


def fir_cost(L: int, fs_in: float = 250.0, n_ph: int = 8) -> Dict:
    per_tick = 2 * L
    per_in = 2 * 2
    return _pack(per_tick * TICK_RATE + per_in * fs_in, 4 * (n_ph * L + 2 * L), 4 * n_ph * L,
                 f"polyphase FIR: {L} taps at {fs_in:g} Hz, {n_ph} phases (one per 0.5 ms tick), both axes")


def tcn_cost(cfg: Dict, n_params: int, fs: float = 250.0) -> Dict:
    ch, k, dil = cfg["ch"], cfg["k"], cfg["dil"]
    macs = cfg["n_in"] * ch + len(dil) * (k * ch * ch + ch * ch) + ch * cfg["n_out"]
    layers = 2 + 2 * len(dil)
    int8_cyc = fs * (macs / 0.5 + layers * 300)
    hist = sum((k - 1) * d for d in dil) * ch            # int8 activation history of the dilated convolutions
    return _pack(macs * fs, hist + 4 * 64, n_params, f"TCN int8 (CMSIS-NN): {macs} MAC per 4 ms step, "
                 f"{layers} layer calls, {n_params} weights, {hist} B of activation history", int8_cycles_per_s=int8_cyc)


def g4_cost() -> Dict:
    a = akf_cost(True)
    d = detector_cost()
    return {"akf": a, "detector": d, "cpu_share_128MHz": a["cpu_share_128MHz"] + d["cpu_share_128MHz"],
            "ram_bytes": a["ram_bytes"] + d["ram_bytes"], "note": "G4 = Rev H AKF + guard + ai2's detector"}


def table() -> Dict:
    return {"assumptions": {"f_clk_hz": F_CLK, "float32_cycles_per_mac": CYC_MAC,
                            "int8": "CMSIS-NN 0.5 MAC/cycle + 300 cycles per layer call",
                            "targets": {"nRF54L15": "Cortex-M33 128 MHz, FPU, 256 KB RAM, 1.5 MB NVM (AMF-44)",
                                        "nRF5340": "application core Cortex-M33 128 MHz, FPU, 512 KB RAM, 1 MB flash"},
                            "label": "CALCULATION; the cycle model is an ASSUMPTION to be profiled (DWT CYCCNT)"},
            "epll": epll_cost(True), "epll_fundamental_only": epll_cost(False), "wflc": wflc_cost(),
            "bmflc_19": bmflc_cost(19), "bmflc_kf_19": bmflc_kf_cost(19), "bmflc_kf_37": bmflc_kf_cost(37),
            "akf": akf_cost(True), "akf_imu_only": akf_cost(False), "g4": g4_cost(), "detector": detector_cost(),
            "fir_128": fir_cost(128), "authority": authority_cost()}
