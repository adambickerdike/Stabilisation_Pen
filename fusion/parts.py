"""Candidate inertial sensors: datasheet values (MFR) and tremor-band signal-to-noise (CALC).

Every datasheet number carries the ledger id of its row in results/fusion/evidence_rows.csv
(proposed rows OPT-37..OPT-42).  Values that the fetched document did not state are None and
the field "unverified" says what is missing; they are never filled from memory.

What an accelerometer sees (CALC)
---------------------------------
A displacement x(t) = A cos(2 pi f t) has acceleration amplitude A (2 pi f)^2: the
accelerometer weights motion by omega^2.  Its white noise density n_a (m/s^2/sqrt(Hz)) is
therefore a displacement noise density n_a / (2 pi f)^2 that falls with frequency, and the
amplitude SNR of a tremor line measured over an effective bandwidth B is

    SNR = (A (2 pi f)^2 / sqrt(2)) / (n_a sqrt(B)).

The optical page sensor has a flat displacement noise density sigma_p / sqrt(f_s / 2).  Which
sensor is better in the tremor band is a crossover frequency, computed in `crossover_hz`.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, Optional

G0 = 9.80665
UG = 1e-6 * G0                  # m/s^2 per micro-g
MDPS = math.radians(1e-3)       # rad/s per milli-degree-per-second


@dataclass
class Part:
    name: str
    kind: str                                  # "6-axis IMU" | "accelerometer"
    ledger: str                                # proposed evidence row
    source: str                                # document and revision actually read
    acc_nd_ug: float                           # accelerometer noise density, ug/sqrt(Hz), best mode
    acc_nd_note: str
    gyro_nd_mdps: Optional[float]              # gyroscope rate noise density, mdps/sqrt(Hz)
    odr_max_hz: Optional[float]
    bandwidth: str                             # anti-aliasing / digital filter as stated
    group_delay_ms: Optional[str]              # stated filter group delay (None: not stated)
    current_ua: Dict[str, float]               # supply current, uA, mode -> value
    package_mm: str
    offset: str                                # zero-g offset and temperature coefficient as stated
    unverified: str = ""                       # what the fetched source did not state

    def acc_nd(self) -> float:
        """Accelerometer noise density in m/s^2/sqrt(Hz)."""
        return self.acc_nd_ug * UG

    def gyro_nd(self) -> Optional[float]:
        """Gyroscope noise density in rad/s/sqrt(Hz)."""
        return None if self.gyro_nd_mdps is None else self.gyro_nd_mdps * MDPS


PARTS: Dict[str, Part] = {
    "LSM6DSV16X": Part(
        "LSM6DSV16X", "6-axis IMU", "OPT-37",
        "ST DS13510 Rev 3 (March 2023), Table 3 mechanical and Table 4 electrical characteristics; s6.2, Table 69",
        60.0, "high-performance mode, FS +-2..16 g, independent of ODR (100 ug/sqrt(Hz) in normal mode)",
        2.8, 7680.0,
        "analog anti-aliasing filter active in high-performance mode; digital LPF1 cut-off ODR/2; optional LPF2 ODR/4 ... ODR/800",
        None, {"accel + gyro, high-performance": 650.0, "accel only, high-performance": 190.0},
        "LGA-14L 2.5 x 3.0 x 0.83", "zero-g +-12 mg after calibration, +-0.07 mg/degC; zero-rate +-1 dps, +-0.006 dps/degC",
        unverified="filter group delay / latency not stated in DS13510"),
    "ICM-45686": Part(
        "ICM-45686", "6-axis IMU", "OPT-38",
        "TDK InvenSense product page (invensense.tdk.com, retrieved 2026-09-28), citing DS-000577 v1.0",
        70.0, "product-page value (mode not stated there)", 3.8, None,
        "not stated on the product page", None, {"6-axis low-noise mode": 420.0},
        "LGA-14 2.5 x 3.0 x 0.81", "not stated on the product page",
        unverified="DS-000577 not retrievable here (the URL returned a search page): max ODR, filter and offset unverified"),
    "ICM-42688-P": Part(
        "ICM-42688-P", "6-axis IMU", "OPT-39",
        "TDK InvenSense product page (retrieved 2026-09-28), citing DS-000347 v1.9",
        70.0, "product-page value", 2.8, None,
        "programmable 2nd-order anti-alias filter (search snippet of DS-000347 v1.6; not read in full)", None,
        {"6-axis low-noise mode": 880.0}, "LGA-14 2.5 x 3.0 x 0.91", "not stated on the product page",
        unverified="DS-000347 not retrievable here (HTTP 403): max ODR (32 kHz per a search snippet), filter latency and offset unverified"),
    "BMI323": Part(
        "BMI323", "6-axis IMU", "OPT-40",
        "Bosch Sensortec BST-BMI323-DS000-13, revision 1.7 (15 Apr 2026): accelerometer and gyroscope tables, Table 10, Table 11",
        180.0, "high-performance mode, range 8 g", 7.0, 6400.0,
        "3 dB bandwidth 674 / 1181 / 1677 Hz at ODR 1600 / 3200 / 6400 Hz (ODR/2 filter setting)",
        "0.63 / 0.47 / 0.39 ms at ODR 1600 / 3200 / 6400 Hz (Table 11)",
        {"IMU high-performance": 790.0, "accel only, high-performance": 145.0},
        "LGA-14 2.5 x 3.0 x 0.83", "zero-g +-35 mg soldered (+-50 mg over life), TCO +-0.3 mg/K"),
    "BMA530": Part(
        "BMA530", "accelerometer", "OPT-41",
        "Bosch Sensortec product flyer BST-BMA530-FL000-02, version 1.2 (03/2024), technical data",
        120.0, "flyer value", None, 6400.0, "not stated in the flyer", None,
        {"high performance, continuous": 125.0, "low power, 100 Hz": 18.0},
        "WLCSP 1.2 x 0.8 x 0.55", "offset +-75 mg soldered over life, TCO +-0.5 mg/K",
        unverified="full datasheet not read: filter bandwidth and latency unverified"),
    "ADXL367": Part(
        "ADXL367", "accelerometer", "OPT-42",
        "Analog Devices ADXL367 data sheet Rev. 0, specifications table (p. 4)",
        170.0, "low-noise mode at 400 Hz ODR (200 ug/sqrt(Hz) low-noise mode, 370 normal)", None, 400.0,
        "2-pole anti-aliasing filter, -3 dB at ODR/2", None,
        {"measurement, 100 Hz ODR, normal": 0.89, "measurement, 100 Hz ODR, low noise": 1.77},
        "LGA 2.2 x 2.3 x 0.87", "0 g offset +-35 mg (x, y) typ., 0.6 mg/degC"),
}


def displacement_noise_um(nd: float, f_hz: float) -> float:
    """Displacement noise density (um/sqrt(Hz)) of an accelerometer with noise density nd (m/s^2/sqrt(Hz)) at f."""
    return nd / (2 * math.pi * f_hz) ** 2 * 1e6


def tremor_snr(nd: float, amp_m: float, f_hz: float, bw_hz: float = 1.0) -> float:
    """Amplitude SNR of a tremor line of peak amplitude amp_m at f_hz, over an effective bandwidth bw_hz."""
    return amp_m * (2 * math.pi * f_hz) ** 2 / math.sqrt(2) / (nd * math.sqrt(bw_hz))


def page_sensor_nd_um(sigma_m: float, rate_hz: float) -> float:
    """Flat displacement noise density (um/sqrt(Hz)) of a page sensor with sigma_m RMS per sample at rate_hz."""
    return sigma_m / math.sqrt(rate_hz / 2.0) * 1e6


def crossover_hz(nd: float, sigma_m: float, rate_hz: float) -> float:
    """Frequency above which the accelerometer has the lower displacement noise density."""
    return math.sqrt(nd / (sigma_m / math.sqrt(rate_hz / 2.0))) / (2 * math.pi)


def snr_table(amps=(0.1e-3, 0.3e-3, 0.5e-3), freqs=(4.0, 6.0, 8.0, 10.0, 12.0), bw_hz: float = 1.0,
              page=((3e-6, 1000.0), (3e-6, 120.0))) -> Dict:
    """CALC: per part, the tremor-band SNR and displacement noise, and the crossover against page sensors."""
    out = {}
    for name, p in PARTS.items():
        nd = p.acc_nd()
        row = {"acc_nd_ug": p.acc_nd_ug,
               "displacement_noise_um_per_rtHz": {f"{f:g}Hz": displacement_noise_um(nd, f) for f in freqs},
               "snr_amplitude": {f"{f:g}Hz_{a * 1e3:g}mm": tremor_snr(nd, a, f, bw_hz) for f in freqs for a in amps},
               "crossover_vs_page_Hz": {f"{s * 1e6:g}um_{r:g}Hz": crossover_hz(nd, s, r) for s, r in page}}
        if p.gyro_nd() is not None:
            # lever-arm term r * d(omega)/dt that a gyroscope-based compensation adds (r = 0.1 m), at f
            row["gyro_leverarm_noise_ug_per_rtHz_at_r100mm"] = {f"{f:g}Hz": 0.1 * 2 * math.pi * f * p.gyro_nd() / UG
                                                                 for f in freqs}
        out[name] = row
    out["_page_sensor_noise_um_per_rtHz"] = {f"{s * 1e6:g}um_{r:g}Hz": page_sensor_nd_um(s, r) for s, r in page}
    out["_definition"] = ("SNR = (A (2 pi f)^2 / sqrt 2) / (n_a sqrt B), B = %g Hz; displacement noise = n_a / (2 pi f)^2; "
                          "page-sensor noise density = sigma / sqrt(rate / 2)" % bw_hz)
    return out


def writing_vs_tremor_acceleration(letter_amp_m: float = 2e-3, stroke_hz: float = 3.0, tremor=(0.1e-3, 6.0)) -> Dict:
    """CALC: acceleration amplitude of a letter-scale stroke against a tremor line (the omega^2 emphasis)."""
    a_w = letter_amp_m * (2 * math.pi * stroke_hz) ** 2
    a_t = tremor[0] * (2 * math.pi * tremor[1]) ** 2
    return {"writing_m_s2": a_w, "tremor_m_s2": a_t, "tremor_over_writing_displacement": tremor[0] / letter_amp_m,
            "tremor_over_writing_acceleration": a_t / a_w}


def catalog() -> Dict:
    return {k: asdict(v) for k, v in PARTS.items()}
