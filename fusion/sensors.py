r"""Sensor models on top of the recorded housing motion of the pencil model P1.

The simulator records the true housing (nib reference point) position p_H and its
acceleration a_H after a 4th-order Butterworth anti-aliasing low-pass at 400 Hz (group
delay 1.04 ms at low frequency; sim/pencil/core.py).  Everything a real pen would add on
top is modelled here, causally and with its own random draws:

page sensor    optical relative-position sensor in the nose: rate, latency, white noise,
               validity (lift height below 0.8 mm).  P1 default 1 kHz / 2 ms / 3 um
               (config sensing.opt_*; ASSUMPTION); proposed requirement 120 Hz / <= 10 ms.
accelerometer  specific force in the housing frame at a distance r along the barrel from the
               nib: noise density, ODR, remaining latency after the recorded 1.04 ms (FIFO and
               SPI), constant bias after calibration plus Gauss-Markov drift, scale error,
               mounting misalignment, 16-bit quantisation and range.  Gravity is part of the
               specific force, so any unmodelled rotation of the pen leaks g * angle.
gyroscope      body rates with noise density, bias and scale error (same ODR and latency).
pen rotation   P1 has no pen rotation.  A kinematic small rotation Omega(t) of the rigid pen is
               added here (ASSUMPTION, parametric):
                   Omega = (rho_t / r_ref) (d_psi x a) + (rho_w / r_ref) (h_w x a)
               d_psi: the hand tremor displacement (scenario), phase-shifted by psi_t (Hilbert);
               h_w: the intended hand path high-passed at 1 Hz (finger strokes); a: barrel axis.
               rho is the rotation-induced displacement of a point r_ref = 100 mm up the barrel
               relative to the nib, per unit nib displacement: 0 = pure translation, 0.67 = pure
               rotation about a wrist 150 mm from the nib, 1.25 = about the web of the hand at 80 mm.
               The nib motion stays the P1 motion; the IMU at r sees
                   a_I = a_nib + r (Omega'' x a),   f_body = R^T (a_I - g),   R = (I + [Omega]x) R0.
compensation   what the firmware does with the readings, giving a page-frame estimate of the nib
               acceleration:
                 ideal  translation-only IMU at the nib (no rotation effects): a reference
                 none   board accelerometer, nominal attitude, no compensation
                 nose   nose accelerometer only (r = 17 mm), nominal attitude
                 gyro   board 6-axis IMU: attitude from the integrated gyroscope (leaky, 2 s) removes
                        the gravity leak; lever arm removed with r * d(omega)/dt (backward difference,
                        2nd-order 300 Hz low-pass)
                 dual   nose + board accelerometers: rigid-body extrapolation to the nib (removes the
                        lever arm exactly); nominal attitude, so the gravity leak g * Omega remains
contact        axial slide sensor (Hall z): 1 kHz, 1 ms, 2 um noise, contact when the slide exceeds
               the front stop by 0.1 mm (as the P1 core).

Every quantity is SI.  Streams are time-stamped twice: acquisition time (the instant the
sample describes) and availability time (when firmware could use it).  Estimators may use a
sample only once the tick time reaches its availability time.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, Optional

import numpy as np
from scipy.signal import butter, hilbert, lfilter, lfilter_zi, sosfilt, sosfiltfilt

from . import parts as PT

G0 = PT.G0
G_VEC = np.array([0.0, 0.0, -G0])


# ------------------------------------------------------------------ specifications
@dataclass
class PageSensor:
    rate: float = 1000.0
    latency: float = 2e-3
    noise: float = 3e-6
    lift_max: float = 0.8e-3
    label: str = "P1 default: 1 kHz, 2 ms, 3 um (config sensing.opt_*; ASSUMPTION)"


def page_1k() -> PageSensor:
    return PageSensor()


def page_120() -> PageSensor:
    return PageSensor(rate=120.0, latency=10e-3, label="proposed requirement: 120 Hz, 10 ms latency, 3 um (ASSUMPTION)")


@dataclass
class AccelModel:
    part: str = "LSM6DSV16X"
    nd: float = 60.0 * PT.UG               # MFR OPT-37 (DS13510 Rev 3, high-performance mode)
    odr: float = 3840.0                    # config sensing.imu_rate; 7.68 kHz available (OPT-37)
    extra_latency: float = 0.35e-3         # ASSUMPTION: FIFO read every 0.5 ms (0.25 ms mean) + SPI/processing 0.1 ms
    bias_sd: float = 0.02                  # m/s^2 per axis after calibration (config sensing.imu_acc_bias; ASSUMPTION)
    drift_sd: float = 0.005                # m/s^2, Gauss-Markov drift over a session (ASSUMPTION; 0.07 mg/degC OPT-37)
    drift_tau: float = 30.0                # s
    scale_sd: float = 0.005                # ASSUMPTION (after calibration)
    misalign_sd: float = math.radians(0.5)  # ASSUMPTION: axes to housing frame after calibration
    range_g: float = 4.0                   # full scale +-4 g: 0.122 mg/LSB (OPT-37 sensitivity table)


def accel_for(part: str, **kw) -> AccelModel:
    p = PT.PARTS[part]
    odr = min(3840.0, p.odr_max_hz or 3840.0)
    return AccelModel(part=part, nd=p.acc_nd(), odr=kw.pop("odr", odr), **kw)


@dataclass
class GyroModel:
    part: str = "LSM6DSV16X"
    nd: float = 2.8 * PT.MDPS              # MFR OPT-37
    bias_sd: float = math.radians(0.1)     # rad/s after calibration (ASSUMPTION; zero-rate level +-1 dps uncalibrated, OPT-37)
    scale_sd: float = 0.01                 # ASSUMPTION
    fs_dps: float = 125.0                  # full scale +-125 dps: 4.375 mdps/LSB (OPT-37)


@dataclass
class Rotation:
    rho_t: float = 0.5                     # ASSUMPTION (no measurement of pen rotation during writing tremor; EXP-H01)
    rho_w: float = 0.5                     # ASSUMPTION
    psi_t: float = 0.0                     # rad, phase of the rotation relative to the hand translation
    r_ref: float = 0.100
    hp_w_hz: float = 1.0


@dataclass
class ContactSensor:
    rate: float = 1000.0
    latency: float = 1e-3
    noise: float = 2e-6
    thr: float = 0.1e-3


@dataclass
class SensorConfig:
    page: PageSensor = field(default_factory=page_1k)
    acc: AccelModel = field(default_factory=AccelModel)
    gyro: Optional[GyroModel] = field(default_factory=GyroModel)
    nose: Optional[AccelModel] = None
    comp: str = "gyro"                     # ideal | none | nose | gyro | dual
    rot: Rotation = field(default_factory=Rotation)
    r_board: float = 0.100                 # IMU distance from the nib along the barrel (78-120 mm, lead)
    r_nose: float = 0.017                  # nose accelerometer on the flex near the Hall sensor (15-20 mm)
    contact: ContactSensor = field(default_factory=ContactSensor)
    tick_hz: float = 2000.0

    def describe(self) -> Dict:
        return asdict(self)


def config(page: str = "1k", comp: str = "gyro", rho_t: Optional[float] = None, rho_w: Optional[float] = None,
           psi_t: float = 0.0, acc_part: str = "LSM6DSV16X", nose_part: str = "BMA530", nd_ug: Optional[float] = None,
           **acc_kw) -> SensorConfig:
    """Convenience constructor.  page "1k" (P1 default) or "120" (proposed requirement); nd_ug overrides the
    accelerometer noise density (e.g. 70 ug/sqrt(Hz), the value in config/parameters.yaml that the P1 core uses)."""
    rot = Rotation()
    if rho_t is not None:
        rot.rho_t = rho_t
    if rho_w is not None:
        rot.rho_w = rho_w
    rot.psi_t = psi_t
    acc = accel_for(acc_part, **acc_kw)
    if nd_ug is not None:
        acc.nd = nd_ug * PT.UG
    nose = accel_for(nose_part) if comp in ("dual", "nose") else None
    gyro = GyroModel(part=acc_part, nd=PT.PARTS[acc_part].gyro_nd() or GyroModel().nd) if comp == "gyro" else None
    return SensorConfig(page=page_1k() if page == "1k" else page_120(), acc=acc, gyro=gyro, nose=nose, comp=comp, rot=rot)


# ------------------------------------------------------------------ records
@dataclass
class Record:
    """What the sensor models need from one P1 run, at the record rate (4 kHz)."""
    t: np.ndarray
    pH: np.ndarray            # (n, 3) housing reference point (nominal ball centre), page frame
    aH: np.ndarray            # (n, 3) its acceleration after the 400 Hz anti-aliasing filter
    s: np.ndarray             # axial slide
    contact: np.ndarray       # nib force > 0 (truth, for evaluation only)
    hand_tremor: np.ndarray   # (n, 2) hand tremor displacement (scenario), for the rotation model
    intended: np.ndarray      # (n, 2) intended hand path (scenario), for the rotation model
    theta: float
    phi: float
    rho: float
    z0: float
    s_min: float
    n_steps: int
    dt: float
    sdec: int

    @property
    def fs(self) -> float:
        return 1.0 / float(self.t[1] - self.t[0])


def record_from_result(res, scn) -> Record:
    from sim.pencil.layout import IDX
    t = res["t"].copy()
    k = np.clip(np.round(t / (scn.t[1] - scn.t[0])).astype(int), 0, len(scn.t) - 1)
    P = res.P
    return Record(t=t, pH=np.column_stack([res["pHx"], res["pHy"], res["pHz"]]),
                  aH=np.column_stack([res["aHx"], res["aHy"], res["aHz"]]), s=res["s"].copy(),
                  contact=res["contact"].copy(), hand_tremor=np.asarray(scn.dtrue)[k].copy(),
                  intended=np.asarray(scn.intended)[k].copy(), theta=float(P[IDX["theta"]]), phi=float(P[IDX["phi"]]),
                  rho=float(P[IDX["rho"]]), z0=float(P[IDX["z0"]]), s_min=float(P[IDX["s_min"]]),
                  n_steps=int(P[IDX["n_steps"]]), dt=float(P[IDX["dt"]]), sdec=int(P[IDX["stage_decim"]]))


@dataclass
class Streams:
    tick_t: np.ndarray
    acc_t: np.ndarray
    acc_av: np.ndarray
    acc: np.ndarray           # (N, 2) page-frame estimate of the nib acceleration (after compensation)
    pos_t: np.ndarray
    pos_av: np.ndarray
    pos: np.ndarray           # (M, 2) page-sensor position
    pos_ok: np.ndarray        # (M,) 1.0 valid
    con_t: np.ndarray
    con_av: np.ndarray
    con: np.ndarray           # (K,) 1.0 in contact (axial sensor)
    meta: Dict = field(default_factory=dict)

    def n_ticks(self) -> int:
        return len(self.tick_t)


# ------------------------------------------------------------------ helpers
_AA = {}


def aa_sos(fs: float, fc: float = 400.0):
    key = (round(fs, 6), fc)
    if key not in _AA:
        _AA[key] = butter(4, fc, fs=fs, output="sos")
    return _AA[key]


def _interp_cols(tq, t, X):
    X = np.atleast_2d(X.T).T
    return np.column_stack([np.interp(tq, t, X[:, j]) for j in range(X.shape[1])])


def _skew(w):
    return np.array([[0.0, -w[2], w[1]], [w[2], 0.0, -w[0]], [-w[1], w[0], 0.0]])


def _gauss_markov(n, dt, tau, sd, rng):
    a = math.exp(-dt / tau)
    e = rng.standard_normal(n)
    x0 = sd * e[0]
    y, _ = lfilter([sd * math.sqrt(1 - a * a)], [1.0, -a], e[1:], zi=[a * x0])
    return np.concatenate([[x0], y])


def geometry(rec: Record):
    from stabpen.frames import basis
    B = basis(rec.theta, rec.phi, rec.rho)
    R0 = np.column_stack([B["xH"], B["yH"], B["a"]])
    return B["a"], R0


def rotation(rec: Record, rot: Rotation) -> np.ndarray:
    """Omega(t) (n, 3), page frame: the kinematic pen rotation (see module doc)."""
    a, _ = geometry(rec)
    n = len(rec.t)
    Om = np.zeros((n, 3))
    if rot.rho_t != 0.0:
        d = rec.hand_tremor
        if rot.psi_t != 0.0:
            d = math.cos(rot.psi_t) * d + math.sin(rot.psi_t) * np.imag(hilbert(d, axis=0))
        d3 = np.column_stack([d, np.zeros(n)])
        Om += rot.rho_t / rot.r_ref * np.cross(d3, a)
    if rot.rho_w != 0.0:
        hw = sosfiltfilt(butter(2, rot.hp_w_hz, btype="high", fs=rec.fs, output="sos"), rec.intended, axis=0)
        h3 = np.column_stack([hw, np.zeros(n)])
        Om += rot.rho_w / rot.r_ref * np.cross(h3, a)
    return Om


def body_signals(rec: Record, cfg: SensorConfig):
    """True body-frame specific force at the board (and nose) accelerometer and the body rates, at the record rate."""
    a, R0 = geometry(rec)
    fs = rec.fs
    sos = aa_sos(fs)
    use_rot = cfg.comp != "ideal"
    Om = rotation(rec, cfg.rot) if use_rot else np.zeros((len(rec.t), 3))
    dt = 1.0 / fs
    Omd = np.gradient(Om, dt, axis=0)
    Omdd = np.gradient(Omd, dt, axis=0)
    f_nom = rec.aH - G_VEC                                     # page-frame specific force at the nib
    grav = -np.cross(Om, f_nom)                                # rotation of gravity (and of a_H) into the body frame
    out = {}
    for key, r in (("board", cfg.r_board), ("nose", cfg.r_nose)):
        extra = r * np.cross(Omdd, a) + grav
        out[key] = (f_nom + sosfilt(sos, extra, axis=0)) @ R0     # body frame = R0^T f
    out["rate"] = sosfilt(sos, Omd, axis=0) @ R0
    out["Omega"] = Om
    return out


def _accel_readings(f_b, t_rec, t_a, m: AccelModel, rng):
    """Readings of one accelerometer at the sample times t_a (body frame)."""
    f = _interp_cols(t_a, t_rec, f_b)
    n = len(t_a)
    dt = 1.0 / m.odr
    mis = _skew(rng.normal(0.0, m.misalign_sd, 3))
    scale = 1.0 + rng.normal(0.0, m.scale_sd, 3)
    f = (f + f @ mis.T) * scale
    bias = rng.normal(0.0, m.bias_sd, 3)
    drift = np.column_stack([_gauss_markov(n, dt, m.drift_tau, m.drift_sd, rng) for _ in range(3)])
    f = f + bias + drift + rng.standard_normal((n, 3)) * m.nd * math.sqrt(m.odr / 2.0)
    lsb = 2.0 * m.range_g * G0 / 65536.0
    return np.clip(np.round(f / lsb) * lsb, -m.range_g * G0, m.range_g * G0)


def _gyro_readings(w_b, t_rec, t_a, g: GyroModel, odr: float, rng):
    w = _interp_cols(t_a, t_rec, w_b)
    n = len(t_a)
    w = w * (1.0 + rng.normal(0.0, g.scale_sd, 3)) + rng.normal(0.0, g.bias_sd, 3)
    w = w + rng.standard_normal((n, 3)) * g.nd * math.sqrt(odr / 2.0)
    lsb = 2.0 * math.radians(g.fs_dps) / 65536.0
    return np.round(w / lsb) * lsb


def _leaky_integrate(x, dt, tau):
    lam = math.exp(-dt / tau)
    return lfilter([dt], [1.0, -lam], x, axis=0)


def nib_acceleration(rec: Record, cfg: SensorConfig, rng, t_a: np.ndarray, return_truth: bool = False):
    """Page-frame estimate of the nib acceleration (n_a, 3) at the sample times t_a, per cfg.comp."""
    a, R0 = geometry(rec)
    sig = body_signals(rec, cfg)
    dt = 1.0 / cfg.acc.odr
    fb = _accel_readings(sig["board"], rec.t, t_a, cfg.acc, rng)
    if cfg.comp == "ideal":
        est = fb @ R0.T + G_VEC
    elif cfg.comp == "none":
        est = fb @ R0.T + G_VEC
    elif cfg.comp == "nose":
        fn = _accel_readings(sig["nose"], rec.t, t_a, cfg.nose, rng)
        est = fn @ R0.T + G_VEC
    elif cfg.comp == "gyro":
        if cfg.gyro is None:
            raise ValueError("comp 'gyro' needs a gyroscope")
        wb = _gyro_readings(sig["rate"], rec.t, t_a, cfg.gyro, cfg.acc.odr, rng)
        wp = wb @ R0.T
        Omh = _leaky_integrate(wp, dt, 2.0)
        fp = fb @ R0.T
        est = fp + G_VEC + np.cross(Omh, fp)
        alpha = np.vstack([np.zeros((1, 3)), np.diff(wp, axis=0) / dt])
        alpha = sosfilt(butter(2, 300.0, fs=cfg.acc.odr, output="sos"), alpha, axis=0)
        est = est - cfg.r_board * np.cross(alpha, a)
    elif cfg.comp == "dual":
        # rigid-body extrapolation of the two specific forces to the nib (the lever-arm terms are linear
        # in r and cancel exactly).  The attitude is NOT taken from the doubly integrated differential
        # acceleration: its noise (the difference of two accelerometers divided by 83 mm) integrates to a
        # 0.07-0.2 rad low-frequency wander that rotates the tremor acceleration itself into the page axes
        # (tested: 8-12 % band error).  The remaining gravity leak g*Omega is 2.6 % (6 Hz) to 6 % (4 Hz) of
        # the nib acceleration at rho_t = 0.5.
        fn = _accel_readings(sig["nose"], rec.t, t_a, cfg.nose, rng)
        k = cfg.r_nose / (cfg.r_board - cfg.r_nose)
        f_nib = fn - k * (fb - fn)
        est = f_nib @ R0.T + G_VEC
    else:
        raise ValueError(cfg.comp)
    if return_truth:
        return est, _interp_cols(t_a, rec.t, rec.aH)
    return est


def make_streams(rec: Record, cfg: SensorConfig, seed: int) -> Streams:
    """All sensor streams of one run.  seed fixes every random draw (noise, bias, phase of the clocks)."""
    rng = np.random.default_rng(seed)
    t_end = float(rec.t[-1])
    Ts = rec.sdec * rec.dt
    n_ticks = int(math.ceil(rec.n_steps / rec.sdec))
    tick_t = np.arange(n_ticks) * Ts
    # IMU
    t_a = np.arange(rng.uniform(0, 1.0 / cfg.acc.odr), t_end, 1.0 / cfg.acc.odr)
    acc = nib_acceleration(rec, cfg, rng, t_a)
    acc_av = t_a + cfg.acc.extra_latency
    # page sensor
    ps = cfg.page
    t_p = np.arange(rng.uniform(0, 1.0 / ps.rate), t_end, 1.0 / ps.rate)
    pos = _interp_cols(t_p, rec.t, rec.pH[:, :2]) + rng.standard_normal((len(t_p), 2)) * ps.noise
    hz = np.interp(t_p, rec.t, rec.pH[:, 2]) - rec.z0
    pos_ok = (hz < ps.lift_max).astype(np.float64)
    # axial contact sensor
    cs = cfg.contact
    t_c = np.arange(rng.uniform(0, 1.0 / cs.rate), t_end, 1.0 / cs.rate)
    s_meas = np.interp(t_c, rec.t, rec.s) + rng.standard_normal(len(t_c)) * cs.noise
    con = (s_meas > rec.s_min + cs.thr).astype(np.float64)
    return Streams(tick_t=tick_t, acc_t=t_a, acc_av=acc_av, acc=np.ascontiguousarray(acc[:, :2]),
                   pos_t=t_p, pos_av=t_p + ps.latency, pos=np.ascontiguousarray(pos), pos_ok=pos_ok,
                   con_t=t_c, con_av=t_c + cs.latency, con=con,
                   meta={"seed": seed, "comp": cfg.comp, "page_rate": ps.rate, "page_latency": ps.latency,
                         "imu_odr": cfg.acc.odr, "imu_extra_latency": cfg.acc.extra_latency, "acc_part": cfg.acc.part})


def expand_to_steps(dhat_ticks: np.ndarray, n_steps: int, sdec: int) -> np.ndarray:
    """Zero-order hold of a per-tick estimate onto the simulation steps (the core reads it at tick steps)."""
    return np.ascontiguousarray(np.repeat(np.asarray(dhat_ticks, float), sdec, axis=0)[:n_steps])


def truth_at(t_query: np.ndarray, rec_tremor: Record, rec_clean: Record) -> np.ndarray:
    """True disturbance d = p_H(tremor run) - p_H(clean run) (the oracle's definition) at t_query."""
    n = min(len(rec_tremor.t), len(rec_clean.t))
    d = rec_tremor.pH[:n, :2] - rec_clean.pH[:n, :2]
    return _interp_cols(t_query, rec_tremor.t[:n], d)
