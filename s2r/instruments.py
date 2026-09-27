"""Measurement models of the bench instruments named in validation/bench_protocols.md.

Each channel turns a true signal (continuous, sampled finely by the virtual
plant) into what the instrument would record:

  true x(t) -> sensor/anti-alias low-pass (causal) -> latency -> sampling at fs
  with sample-clock jitter -> session systematics (gain, offset, nonlinearity)
  -> white noise -> quantisation

Every number carries its origin in ``src``: PROTOCOL (copied from
bench_protocols.md §0.9 or the experiment's equipment list), CONFIG
(config/parameters.yaml), DESIGN (docs/icd.md, firmware) or ASSUMPTION (chosen
here, inside the instrument class the protocol names, never better than it).
Session systematics (gain error, angle error, sync offset) are drawn once per
bench session and are NOT reduced by repeating records; that is the point of
modelling them.

Evidence status of everything produced with these models: SIMULATION.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, Optional

import numpy as np
from scipy import signal as sps


@dataclass(frozen=True)
class Channel:
    name: str
    unit: str
    fs: float                    # recorded sample rate (Hz)
    noise_rms: float = 0.0       # white noise per recorded sample (unit)
    lsb: float = 0.0             # quantisation step (unit); 0 = none
    gain_bound: float = 0.0      # session gain error drawn U(-b, +b) (relative)
    offset_bound: float = 0.0    # session offset drawn U(-b, +b) (unit)
    nonlin_bound: float = 0.0    # session smooth nonlinearity, max |error| over full_scale (unit)
    full_scale: float = 1.0      # span over which nonlin_bound applies (unit)
    bw_hz: float = 0.0           # -3 dB of the causal sensor + anti-alias chain; 0 = ideal
    bw_order: int = 2
    resonance_hz: float = 0.0    # mounted resonance (second-order, amplifies below its peak); 0 = none
    resonance_zeta: float = 0.1
    latency: float = 0.0         # fixed delay (s)
    jitter_rms: float = 0.0      # sample-clock jitter (s)
    src: Dict[str, str] = field(default_factory=dict)

    def scaled(self, noise_scale: float) -> "Channel":
        """Same instrument with its random noise scaled (systematics unchanged)."""
        return replace(self, noise_rms=self.noise_rms * noise_scale)


# --------------------------------------------------------------------------- registry
# Protocol numbers: bench_protocols.md §0.9 (rigs R1-R7) and the equipment lists of
# EXP-B01/B02/B03/B05. Values marked ASSUMPTION are inside the protocol's class.
FT_SENSOR = Channel(
    "ft_force", "N", fs=5000.0, noise_rms=2.0e-3, lsb=5.0e-3, gain_bound=0.02,
    bw_hz=2250.0, bw_order=4, resonance_hz=500.0, resonance_zeta=0.1, jitter_rms=1e-7,
    src={"fs": "PROTOCOL EXP-B01 data format (F/T at 5 kHz); R1 24-bit DAQ >= 5 kS/s",
         "lsb": "PROTOCOL R1 resolution <= 5 mN (worst case used as the step)",
         "noise_rms": "ASSUMPTION 2 mN RMS, inside the <= 5 mN resolution class",
         "gain_bound": "PROTOCOL R1 in-situ dead-weight calibration error <= 2 % of reading",
         "bw_hz": "ASSUMPTION sigma-delta DAQ anti-alias at 0.45 fs",
         "resonance_hz": "PROTOCOL R1 mounted resonance >= 500 Hz (lowest value used; zeta 0.1 ASSUMPTION)",
         "offset": "PROTOCOL R1 control: zeroed with the pen lifted before every condition"})
ANGLE = Channel(
    "goniometer_theta", "rad", fs=0.0, offset_bound=np.radians(0.1),
    src={"offset_bound": "PROTOCOL R1 goniometer <= 0.1 deg resolution (session angle error U(+-0.1 deg), distribution ASSUMPTION)"})
ENCODER = Channel(
    "stage_encoder", "m", fs=5000.0, lsb=0.1e-6, noise_rms=0.02e-6,
    src={"lsb": "PROTOCOL R1 encoders <= 0.1 um", "noise_rms": "ASSUMPTION 20 nm interpolation noise"})
CAPACITIVE = Channel(
    "capacitive_disp", "m", fs=10000.0, lsb=1e-9, noise_rms=5e-9, gain_bound=0.005, bw_hz=4500.0,
    src={"fs": "PROTOCOL EXP-B02 data format (displacement at 10 kHz)",
         "noise_rms": "ASSUMPTION 5 nm RMS inside the <= 10 nm resolution class (PROTOCOL EXP-B02)",
         "gain_bound": "ASSUMPTION 0.5 % sensitivity error"})
LASER_TRIANG = Channel(
    "laser_triangulation", "m", fs=5000.0, lsb=0.1e-6, noise_rms=0.05e-6, nonlin_bound=1e-6, full_scale=1e-3,
    bw_hz=10000.0,
    src={"lsb": "PROTOCOL R1 <= 0.1 um resolution", "nonlin_bound": "PROTOCOL R1 +-1 um linearity over 1 mm",
         "noise_rms": "ASSUMPTION 50 nm RMS", "bw_hz": "ASSUMPTION"})
CURRENT_SOURCE = Channel(
    "current_source", "A", fs=0.0, noise_rms=10e-6, gain_bound=0.001,
    src={"gain_bound": "PROTOCOL R4 precision bipolar current source <= 0.1 % accuracy",
         "noise_rms": "ASSUMPTION 10 uA RMS output noise"})
MICRO_OHM = Channel(
    "micro_ohmmeter", "ohm", fs=1.0, noise_rms=0.0, gain_bound=2e-4,
    src={"gain_bound": "ASSUMPTION +-0.02 % of reading (4-wire micro-ohmmeter class, PROTOCOL R4)",
         "temperature": "PROTOCOL R4 measured at 20.0 +- 0.5 C (bath/chamber band, U distribution ASSUMPTION)"})
SCOPE_CURRENT = Channel(
    "scope_current_probe", "A", fs=10e6, noise_rms=1.0e-3, lsb=0.4 / 4096, gain_bound=0.01, bw_hz=10e6,
    bw_order=1, jitter_rms=0.0,
    src={"gain_bound": "PROTOCOL R7 current probe >= 10 MHz, +-1 %",
         "bw_hz": "PROTOCOL R7 probe bandwidth >= 10 MHz",
         "fs": "ASSUMPTION scope set to 10 MS/s", "lsb": "ASSUMPTION 12-bit vertical over a 0.4 A span",
         "noise_rms": "ASSUMPTION 1 mA RMS probe noise"})
SCOPE_VOLT = Channel(
    "scope_voltage", "V", fs=10e6, noise_rms=2e-3, lsb=4.0 / 4096, gain_bound=0.01, bw_hz=20e6, bw_order=1,
    src={"all": "ASSUMPTION 10:1 probe, 12-bit over a 4 V span, +-1 % gain; an 8-bit scope cannot see the "
                "8 mV source sag and biases L by about R_src/R (found in this work)"})
THERMOCOUPLE = Channel(
    "thermocouple_T", "C", fs=1.0, noise_rms=0.05, offset_bound=0.5, bw_hz=0.5, bw_order=1,
    src={"offset_bound": "PROTOCOL R4 type-T 0.08 mm, +-0.5 C after dry-block calibration",
         "noise_rms": "ASSUMPTION", "fs": "PROTOCOL EXP-B07 data format (CSV at 1 Hz)",
         "bw_hz": "ASSUMPTION fine-wire time constant ~0.3 s"})
DMM_RESISTANCE = Channel(
    "dmm_4wire_R", "ohm", fs=10.0, noise_rms=1e-5, gain_bound=1e-3,
    src={"gain_bound": "PROTOCOL R4 0.1 %-class shunt read by a 6.5-digit DMM",
         "noise_rms": "ASSUMPTION 10 uohm at 10 readings/s"})
LDV = Channel(
    "ldv_velocity", "m/s", fs=10000.0, noise_rms=0.1e-6, gain_bound=0.01, bw_hz=20000.0, bw_order=2,
    src={"noise_rms": "PROTOCOL EXP-B05 LDV <= 0.1 um/s resolution (used as RMS noise)",
         "bw_hz": "PROTOCOL EXP-B05 LDV >= 20 kHz bandwidth",
         "gain_bound": "ASSUMPTION +-1 % (cosine and calibration error of the spot on the refill)",
         "fs": "ASSUMPTION rig DAQ at 10 kS/s"})
DAQ_SHUNT_CURRENT = Channel(
    "daq_shunt_current", "A", fs=10000.0, noise_rms=20e-6, gain_bound=0.001, bw_hz=4500.0, bw_order=4,
    src={"gain_bound": "PROTOCOL R4 0.1 %-class shunt", "noise_rms": "ASSUMPTION 20 uA RMS (24-bit DAQ)",
         "bw_hz": "ASSUMPTION DAQ anti-alias 0.45 fs", "fs": "ASSUMPTION 10 kS/s, same DAQ as the LDV"})
FORCE_PROBE = Channel(
    "force_probe", "N", fs=1000.0, noise_rms=1e-3, lsb=0.5e-3, gain_bound=0.005,
    src={"noise_rms": "ASSUMPTION 1 mN RMS inside the <= 2 mN class (PROTOCOL EXP-B05)",
         "gain_bound": "ASSUMPTION 0.5 %"})
TIP_METROLOGY = Channel(
    "tip_metrology", "m", fs=1000.0, noise_rms=0.5e-6, lsb=0.05e-6,
    src={"noise_rms": "PROTOCOL R5 tip position uncertainty <= 1 um (k = 2)", "lsb": "ASSUMPTION"})
AXIAL_LOAD_CELL = Channel(
    "axial_load_cell", "N", fs=1000.0, noise_rms=1e-3, offset_bound=5e-3, gain_bound=0.001,
    src={"offset_bound": "PROTOCOL EXP-B05 axial load cell 0-5 N, +-0.1 % FS",
         "noise_rms": "ASSUMPTION 1 mN RMS"})
LASER_DISP = Channel(
    "laser_displacement", "m", fs=1000.0, noise_rms=0.25e-6, lsb=0.5e-6, nonlin_bound=2e-6, full_scale=4e-3,
    src={"lsb": "PROTOCOL R2 housing lasers <= 0.5 um resolution (same class assumed for EXP-B05 axial)",
         "nonlin_bound": "PROTOCOL R2 +-2 um linearity over +-2 mm", "noise_rms": "ASSUMPTION"})
HALL_FRAME = Channel(
    "hall_q_research_frame", "m", fs=2000.0, noise_rms=1.0e-6, lsb=0.1e-6,
    src={"noise_rms": "CONFIG sensing.hall_noise_tip 1 um RMS (the pen's own sensor)",
         "lsb": "DESIGN docs/icd.md §4.2 q in 0.1 um", "fs": "DESIGN research frame 2 kHz",
         "latency": "CONFIG sensing.hall_delay range; the hidden truth value is identified in EXP-B05"})
PEN_ISNS = Channel(
    "pen_current_sense", "A", fs=2000.0, noise_rms=0.55e-3 / np.sqrt(20.0), lsb=0.1e-3,
    src={"noise_rms": "DESIGN results/electronics/drive_sense.json 0.55 mA RMS per SAADC sample, 20 samples averaged per 2 kHz frame",
         "lsb": "DESIGN docs/icd.md §4.2 i in 0.1 mA"})
SYNC_BOUND = 50e-6   # PROTOCOL §0.4: pen log vs rig DAQ alignment <= 50 us

REGISTRY = {c.name: c for c in (FT_SENSOR, ANGLE, ENCODER, CAPACITIVE, LASER_TRIANG, CURRENT_SOURCE, MICRO_OHM,
                                SCOPE_CURRENT, SCOPE_VOLT, THERMOCOUPLE, DMM_RESISTANCE, LDV, DAQ_SHUNT_CURRENT,
                                FORCE_PROBE, TIP_METROLOGY, AXIAL_LOAD_CELL, LASER_DISP, HALL_FRAME, PEN_ISNS)}


# --------------------------------------------------------------------------- session
@dataclass
class Session:
    """Systematic errors of one bench session (drawn once; unknown to the analyst)."""
    gains: Dict[str, float]
    offsets: Dict[str, float]
    nonlin: Dict[str, np.ndarray]     # polynomial coefficients on normalised span
    sync_offset: float

    def gain(self, ch: Channel) -> float:
        return self.gains.get(ch.name, 1.0)

    def offset(self, ch: Channel) -> float:
        return self.offsets.get(ch.name, 0.0)


def draw_session(rng: np.random.Generator, channels=None, systematic_scale: float = 1.0) -> Session:
    channels = channels or list(REGISTRY.values())
    gains, offsets, nonlin = {}, {}, {}
    for ch in channels:
        gains[ch.name] = 1.0 + systematic_scale * ch.gain_bound * rng.uniform(-1, 1)
        offsets[ch.name] = systematic_scale * ch.offset_bound * rng.uniform(-1, 1)
        if ch.nonlin_bound > 0:
            # smooth odd+even error on u in [-1, 1], scaled so max |e| = bound
            c = rng.normal(size=3)
            u = np.linspace(-1, 1, 201)
            e = c[0] * u ** 2 + c[1] * u ** 3 + c[2] * (u ** 2 - u ** 4)
            nonlin[ch.name] = c * systematic_scale * ch.nonlin_bound / max(np.max(np.abs(e)), 1e-12)
    return Session(gains, offsets, nonlin, sync_offset=systematic_scale * SYNC_BOUND * rng.uniform(-1, 1))


def ideal_session() -> Session:
    return Session({}, {}, {}, 0.0)


# --------------------------------------------------------------------------- measure
def _lowpass(ch: Channel, t: np.ndarray, x: np.ndarray) -> np.ndarray:
    if len(t) < 3:
        return x
    fs_in = 1.0 / (t[1] - t[0])
    y = np.asarray(x, float)
    if ch.resonance_hz > 0 and ch.resonance_hz < 0.45 * fs_in:
        w = 2 * np.pi * ch.resonance_hz
        z = ch.resonance_zeta
        b, a = sps.bilinear([w * w], [1.0, 2 * z * w, w * w], fs=fs_in)
        zi = sps.lfilter_zi(b, a) * y[0]
        y, _ = sps.lfilter(b, a, y, zi=zi)
    if ch.bw_hz > 0 and ch.bw_hz < 0.45 * fs_in:
        sos = sps.butter(ch.bw_order, ch.bw_hz, fs=fs_in, output="sos")
        zi = sps.sosfilt_zi(sos) * y[0]
        y, _ = sps.sosfilt(sos, y, zi=zi)
    return y


def measure(ch: Channel, t: np.ndarray, x: np.ndarray, rng: np.random.Generator,
            session: Optional[Session] = None, noise_scale: float = 1.0, fs: Optional[float] = None,
            latency: Optional[float] = None, t_start: Optional[float] = None, t_stop: Optional[float] = None):
    """Record the true signal x(t) with channel ch. Returns (t_rec, y) where t_rec are the
    nominal time stamps the instrument reports (jitter and latency are not visible in them)."""
    session = session or ideal_session()
    fs = fs or ch.fs
    lat = ch.latency if latency is None else latency
    xf = _lowpass(ch, t, x)
    t0 = t[0] if t_start is None else t_start
    t1 = t[-1] - lat if t_stop is None else t_stop
    n = int(np.floor((t1 - t0) * fs)) + 1
    t_rec = t0 + np.arange(n) / fs
    t_act = t_rec - lat
    if ch.jitter_rms > 0:
        t_act = t_act + ch.jitter_rms * rng.standard_normal(n)
    y = np.interp(t_act, t, xf)
    y = session.gain(ch) * y + session.offset(ch)
    if ch.name in session.nonlin:
        u = np.clip(y / (0.5 * ch.full_scale), -1, 1)
        c = session.nonlin[ch.name]
        y = y + c[0] * u ** 2 + c[1] * u ** 3 + c[2] * (u ** 2 - u ** 4)
    if ch.noise_rms > 0 and noise_scale > 0:
        y = y + noise_scale * ch.noise_rms * rng.standard_normal(n)
    if ch.lsb > 0:
        y = ch.lsb * np.round(y / ch.lsb)
    return t_rec, y


def measure_static(ch: Channel, value: float, rng: np.random.Generator, session: Optional[Session] = None,
                   noise_scale: float = 1.0, n_avg: int = 1) -> float:
    """One averaged reading of a constant quantity (n_avg samples)."""
    session = session or ideal_session()
    y = session.gain(ch) * value + session.offset(ch)
    if ch.noise_rms > 0 and noise_scale > 0:
        y += noise_scale * ch.noise_rms * rng.standard_normal(n_avg).mean()
    if ch.lsb > 0 and n_avg == 1:
        y = ch.lsb * np.round(y / ch.lsb)
    return float(y)


def provenance_table():
    """Rows (channel, field, value, origin) for the report."""
    rows = []
    for ch in REGISTRY.values():
        for k, v in ch.src.items():
            rows.append({"channel": ch.name, "field": k, "value": getattr(ch, k, None), "origin": v})
    rows.append({"channel": "sync", "field": "sync_offset", "value": SYNC_BOUND,
                 "origin": "PROTOCOL §0.4 pen log vs rig DAQ alignment <= 50 us"})
    return rows
