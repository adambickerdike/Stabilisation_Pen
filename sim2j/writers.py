r"""Writer model v2: the aiguide glyph writers re-timed by the two-thirds power law and refitted to measured kinematics.

NOTHING HERE IS HUMAN DATA.  The letter shapes, allographs, instance variability, slant, size and spacing are the
aiguide writers' (aiguide/writer.py via handwriting/writers.py, read-only); v2 changes only *when* each point is drawn:

  * each pen-down stroke is split at sharp corners (> corner_deg, the writer stops there, as v1);
  * each piece is resampled by arc length and lightly smoothed (the glyph font draws arcs as 12-degree polylines);
  * speed along the piece follows the two-thirds power law of drawing (angular speed = K curvature^(2/3), i.e.
    tangential speed v = K (kappa + kappa0)^(-1/3); LIT CON-27, CON-37, AMF-147), capped at v_cap, with an
    acceleration limit a_max from both ends of the piece (v = 0 at cusps and at stroke ends);
  * the arc-length-versus-time profile is smoothed with a Gaussian of width sigma_t (zero-phase; a writer plans the
    stroke ahead), which sets the high-frequency content of the velocity;
  * K is calibrated per writer so that the mean pen-down speed of the text equals the writer's target speed, drawn
    per writer from the adult phrase speed on paper, 30.46 +/- 7.90 mm/s (LIT CON-20, between-writer SD).
The kinematic parameters (kappa0, a_max factor, sigma_t, v_cap) are fitted on fitting writers (ids 1000+, never the
test writers 0-5 or the tuning writers 100-105) to the measured targets: mean speed (LIT CON-20), share of velocity
energy at 8-12 Hz 1.3-1.7 % and cumulative spectrum 3.1/4.9/5.9/9.3 Hz at 50/90/95/99 % (LIT CON-25, one writer,
isolated characters), stroke durations 90-150 ms (LIT CON-24) and the power-law exponent 2/3 (LIT CON-27).  The fit is
a CALCULATION on synthetic writing; the measured targets are LIT.

The v1 writers (aiguide minimum-jerk pieces at a constant piece speed) stay available (``handwriting.writers.writer``)
for the comparison of tremor separation (writer_compare stage).  Kinematics are measured exactly as sim2 measures them
(sim2/validate.py: 1 kHz, 20 Hz low-pass, Welch velocity spectrum, speed minima, power-law regression).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.signal import welch

from . import ROOT  # noqa: F401  (paths)
from handwriting import writers as HW  # noqa: E402
from aiguide.glyphs import GLYPH_SET, arclength, width as glyph_width  # noqa: E402
from aiguide.writer import Letter, Path, Written, apply_warp, sample_style, warp_params  # noqa: E402
from penapp.synth import _split_at_corners  # noqa: E402

ET_SENTENCE = HW.ET_SENTENCE              # "return library books by friday"
PD_SENTENCE = HW.PD_SENTENCE
PRACTICE_SENTENCE = HW.PRACTICE_SENTENCE
SIM_DT = HW.SIM_DT

# measured targets (LIT) the fit aims at
TARGETS = {
    "speed_mm_s": {"mean": 30.46, "sd_between": 7.90, "label": "LIT CON-20 (adults, phrase on paper, mean pen-down speed)"},
    "share_8_12Hz": {"lo": 0.013, "hi": 0.017, "label": "LIT CON-25 (median share of velocity energy at 8-12 Hz)"},
    "cum_Hz": {"f50": 3.1, "f90": 4.9, "f95": 5.9, "f99": 9.3, "label": "LIT CON-25 (cumulative velocity energy)"},
    "stroke_ms": {"lo": 90.0, "hi": 150.0, "median_con25": 135.0, "label": "LIT CON-24 (typical stroke 90-150 ms); CON-25 median 135 ms"},
    "beta": {"value": 2.0 / 3.0, "label": "LIT CON-27 (angular speed ~ curvature^(2/3); exponent varies with shape)"},
}


@dataclass
class KinParams:
    """Kinematic parameters of writer v2 (the fitted values replace the defaults: FITTED below)."""
    beta: float = 2.0 / 3.0         # power-law exponent (LIT CON-27), fixed
    kappa0: float = 60.0            # 1/m regulariser of the curvature (straight segments)
    c_acc: float = 6.0              # a_max = c_acc * v_target^2 / h  (h = letter size)
    sigma_t: float = 0.012          # s, Gaussian smoothing of s(t)
    v_cap: float = 2.5              # speed cap as a multiple of the writer's target mean speed
    smooth_geom: float = 0.02       # x-height units, Gaussian smoothing of the piece geometry along its arc
    corner_deg: float = 45.0        # the writer stops at sharper turns (glyph corners; v1: 60 deg on the coarse font)
    trim: float = 0.002             # the smoothed ramps start/end where s(t) passes this share of the piece
    dwell_start: float = 0.005      # s after touchdown (ASSUMPTION; aiguide v1 0.015)
    dwell_end: float = 0.0          # s before lift (ASSUMPTION; aiguide v1 0.010)
    pen_T: float = 0.02             # s touchdown / lift transition (ASSUMPTION; aiguide v1 0.04)
    size_scale: float = 1.0         # letter size relative to the aiguide style (fitted; prior from LIT PDT-06)
    speed_sd: float = 7.90          # mm/s between-writer SD of the target speed (LIT CON-20)
    speed_mean: float = 30.46       # mm/s (LIT CON-20)
    speed_lo: float = 18.0
    speed_hi: float = 45.0


FITTED: Optional[KinParams] = None   # set by fit results (writer_fit stage) when available


def _fitted_path():
    import os
    from . import RESULTS
    return os.path.join(RESULTS, "writer_fit.json")


def kin_params() -> KinParams:
    """The fitted parameters (results/sim2j/writer_fit.json) if the fit has been run, else the defaults."""
    global FITTED
    if FITTED is not None:
        return FITTED
    import json
    import os
    p = _fitted_path()
    if os.path.exists(p):
        d = json.load(open(p))["chosen"]["params"]
        FITTED = KinParams(**{k: v for k, v in d.items() if k in KinParams.__dataclass_fields__})
        return FITTED
    return KinParams()


def target_speed(w: int, kp: KinParams) -> float:
    """Writer's own mean pen-down speed (m/s): N(30.46, 7.90) mm/s clipped to [18, 45] (LIT CON-20), seeded by writer."""
    rng = np.random.default_rng(77_000 + int(w))
    v = rng.normal(kp.speed_mean, kp.speed_sd)
    return float(np.clip(v, kp.speed_lo, kp.speed_hi)) * 1e-3


# ------------------------------------------------------------------------------------------------ time law of one piece
from numba import njit  # noqa: E402


@njit(cache=True)
def _accel_limit(v, ds, a_max):
    """Forward (from rest) and backward (to rest) acceleration limits on a speed profile over arc-length steps ds."""
    n = v.shape[0]
    vf = v.copy()
    vf[0] = 0.0
    for i in range(1, n):
        lim = math.sqrt(vf[i - 1] * vf[i - 1] + 2.0 * a_max * ds[i - 1])
        if vf[i] > lim:
            vf[i] = lim
    vf[n - 1] = 0.0
    for i in range(n - 2, -1, -1):
        lim = math.sqrt(vf[i + 1] * vf[i + 1] + 2.0 * a_max * ds[i])
        if vf[i] > lim:
            vf[i] = lim
    return vf

def _resample_uniform(P: np.ndarray, ds: float) -> np.ndarray:
    s = arclength(P)
    if s[-1] <= 0:
        return P[:1].copy()
    n = max(int(math.ceil(s[-1] / ds)) + 1, 4)
    u = np.linspace(0.0, s[-1], n)
    return np.column_stack([np.interp(u, s, P[:, 0]), np.interp(u, s, P[:, 1])])


def _smooth_geom(Q: np.ndarray, sigma_pts: float) -> np.ndarray:
    """Gaussian smoothing along the (uniform) arc with the end points pinned (linear end trend removed first)."""
    if sigma_pts < 0.5 or len(Q) < 5:
        return Q
    n = len(Q)
    u = np.linspace(0.0, 1.0, n)[:, None]
    trend = Q[:1] + u * (Q[-1:] - Q[:1])
    R = Q - trend
    Rs = gaussian_filter1d(R, sigma_pts, axis=0, mode="constant", cval=0.0)
    return trend + Rs


def curvature(Q: np.ndarray, s: np.ndarray) -> np.ndarray:
    d1 = np.gradient(Q, s, axis=0)
    d2 = np.gradient(d1, s, axis=0)
    num = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0])
    den = np.maximum(np.hypot(d1[:, 0], d1[:, 1]), 1e-9) ** 3
    return num / den


def piece_profile(piece: np.ndarray, h: float, K: float, v_tgt: float, kp: KinParams, grid: float = 1e-3):
    """(t_grid (s), s_of_t (m), Q (m, uniform geometry), su (m)) for one piece between stops, on a `grid` time grid."""
    ds = max(h / 200.0, 2e-6)
    Q = _resample_uniform(np.asarray(piece, float), ds)
    if len(Q) < 4:
        return None
    Q = _smooth_geom(Q, kp.smooth_geom * h / ds)
    su = arclength(Q)
    L = float(su[-1])
    if L < 1e-7:
        return None
    kap = curvature(Q, su)
    v = K * (kap + kp.kappa0) ** (kp.beta - 1.0)
    v = np.minimum(v, kp.v_cap * v_tgt)
    a_max = kp.c_acc * v_tgt * v_tgt / max(h, 1e-4)
    dsu = np.diff(su)
    vf = _accel_limit(np.ascontiguousarray(v, dtype=np.float64), np.ascontiguousarray(dsu), float(a_max))
    vm = 0.5 * (vf[1:] + vf[:-1])
    tt = np.r_[0.0, np.cumsum(dsu / np.maximum(vm, 1e-6))]
    T = float(tt[-1])
    n = max(int(math.ceil(T / grid)), 2)
    tg = np.linspace(0.0, T, n + 1)
    sg = np.interp(tg, tt, su)
    sig = kp.sigma_t / (T / n)
    if sig >= 0.5 and n >= 4:
        # smooth the speed (not the position): odd-symmetric extension keeps v = 0 at both ends, so the piece keeps
        # its duration and its stops; then the arc length is renormalised to the piece length
        vg = np.diff(sg)
        m = len(vg)
        pad = min(int(math.ceil(3.0 * sig)), m)
        ext = np.r_[-vg[:pad][::-1], vg, -vg[-pad:][::-1]]
        vs = gaussian_filter1d(ext, sig, mode="constant", cval=0.0)[pad:pad + m]
        vs = np.maximum(vs, 0.0)
        if vs.sum() > 0:
            sg = np.r_[0.0, np.cumsum(vs)] * (L / vs.sum())
    return tg, sg, Q, su


def sample_piece(prof, dt: float) -> np.ndarray:
    """Positions (n, 2) at the output step dt (PCHIP of s(t): monotone, continuous speed)."""
    tg, sg, Q, su = prof
    T = float(tg[-1])
    n = max(int(round(T / dt)), 2)
    to = np.linspace(0.0, T, n)
    if len(tg) >= 3:
        s_o = PchipInterpolator(tg, sg)(to)
    else:
        s_o = np.interp(to, tg, sg)
    s_o = np.clip(s_o, 0.0, su[-1])
    return np.column_stack([np.interp(s_o, su, Q[:, 0]), np.interp(s_o, su, Q[:, 1])])


# ------------------------------------------------------------------------------------------------ writer v2
def densify(stroke: np.ndarray, step: float = 0.02, corner_deg: float = 45.0) -> np.ndarray:
    """A glyph stroke (x-height units) resampled at `step` along its arc, keeping every corner vertex (turn >
    corner_deg) exactly, so that the smooth warps of the writer bend arcs as arcs (the font draws arcs as 12-degree
    chords; warped chords of a coarse polyline make spurious kinks that v1 turns into stops)."""
    P = np.asarray(stroke, float)
    if len(P) < 2:
        return P.copy()
    pieces = _split_at_corners(P, corner_deg)
    out = [pieces[0][:1]]
    for pc in pieces:
        s = arclength(pc)
        if s[-1] <= 0:
            continue
        n = max(int(math.ceil(s[-1] / step)), 1)
        u = np.linspace(0.0, s[-1], n + 1)[1:]
        out.append(np.column_stack([np.interp(u, s, pc[:, 0]), np.interp(u, s, pc[:, 1])]))
    return np.vstack(out)


class PathV2(Path):
    """aiguide's path builder with the contact flag at the end of the touchdown (and the start of the lift): the ball
    touches when the hand has lowered it (sim2's fpush ramps with the lift height), not half-way (aiguide v1)."""

    def pen(self, down, T=0.08):
        from stabpen.signals import min_jerk_profile
        n = max(int(round(T / self.dt)), 2)
        sv = min_jerk_profile(np.linspace(0, 1, n))
        z = self.lift_height * (1 - sv) if down else self.lift_height * sv
        dflag = (sv > 0.97) if down else (sv < 0.03)
        self._append(np.repeat(self.pos[None, :], n, 0), dflag, z)
        return self


class WriterV2(HW.ScheduledWriter):
    """aiguide writer (style, allographs, instance variability, optional PD/practice schedules) with v2 timing."""

    def glyph_shape(self, ch: str, rng: Optional[np.random.Generator] = None) -> List[np.ndarray]:
        """aiguide's glyph_shape on a densified glyph: the same allograph and instance warps (the same random draws, in
        the same order), applied to a glyph resampled at 0.02 x-height with its corners kept."""
        out = []
        inst = warp_params(rng, self.style.instance_amp) if rng is not None else None
        off = rng.normal(0.0, self.style.offset_jitter, 2) if rng is not None else np.zeros(2)
        for s in GLYPH_SET[ch]:
            p = apply_warp(densify(s), self.allographs[ch])
            if inst is not None:
                p = apply_warp(p, inst)
            out.append(p + off)
        return out

    def __init__(self, style, seed: int = 0, kp: Optional[KinParams] = None, v_target: Optional[float] = None):
        super().__init__(style, seed=seed)
        self.kp = kp or kin_params()
        self.v_target = v_target if v_target is not None else target_speed(seed, self.kp)
        self.K = None

    # the text is drawn once per K; the calibration finds K so that the mean pen-down speed hits the target
    def write(self, text: str, *, dt: float = 1e-3, seed: int = 0, start=(0.0, 0.0), size_scale: float = 1.0,
              size_factors: Optional[Sequence[float]] = None, tempo_factors: Optional[Sequence[float]] = None,
              glyph_override: Optional[Dict[int, str]] = None, extra_warp: Optional[Sequence[float]] = None,
              baseline_offsets: Optional[Sequence[float]] = None, err_seed: int = 0, K: Optional[float] = None,
              calibrate: bool = True) -> Written:
        kw = dict(seed=seed, start=start, size_scale=size_scale, size_factors=size_factors, tempo_factors=tempo_factors,
                  glyph_override=glyph_override, extra_warp=extra_warp, baseline_offsets=baseline_offsets,
                  err_seed=err_seed)
        if K is None and calibrate:
            K = self.calibrate_K(text, **kw)
        elif K is None:
            K = self._K_guess()
        self.K = K
        return self._write(text, dt=dt, K=K, **kw)

    def _K_guess(self) -> float:
        # v = K kappa^(-1/3): at a typical curvature 1/(0.4 h) the speed is about 1.6 x the target mean
        h = self.style.x_height_mm * 1e-3 * self.kp.size_scale
        return 1.6 * self.v_target * (1.0 / (0.4 * h) + self.kp.kappa0) ** (1.0 / 3.0)

    def calibrate_K(self, text: str, tol: float = 0.01, **kw) -> float:
        """Secant iteration on K so that the mean pen-down speed of `text` (1 kHz draft) equals the target."""
        K0 = self._K_guess()
        v0 = mean_down_speed(self._write(text, dt=1e-3, K=K0, **kw))
        K1 = K0 * self.v_target / max(v0, 1e-6)
        v1 = mean_down_speed(self._write(text, dt=1e-3, K=K1, **kw))
        for _ in range(8):
            if abs(v1 / self.v_target - 1.0) < tol:
                break
            if abs(v1 - v0) < 1e-9:
                break
            K2 = K1 + (self.v_target - v1) * (K1 - K0) / (v1 - v0)
            K2 = float(np.clip(K2, 0.3 * K1, 3.0 * K1))
            K0, v0 = K1, v1
            K1 = K2
            v1 = mean_down_speed(self._write(text, dt=1e-3, K=K1, **kw))
        return float(K1)

    def _write(self, text: str, *, dt: float, K: float, seed: int = 0, start=(0.0, 0.0), size_scale: float = 1.0,
               size_factors=None, tempo_factors=None, glyph_override=None, extra_warp=None, baseline_offsets=None,
               err_seed: int = 0) -> Written:
        st = self.style
        kp = self.kp
        rng = np.random.default_rng(seed)
        rng_err = np.random.default_rng(err_seed)
        rng_t = np.random.default_rng(55_000 + seed)
        h0 = st.x_height_mm * 1e-3 * size_scale * kp.size_scale
        shear = math.tan(math.radians(st.slant_deg))
        slope = math.tan(math.radians(st.baseline_slope_deg))
        wph = rng.uniform(0, 2 * np.pi)
        pb = PathV2(dt, start=(start[0] - 1.0e-3, start[1] + 1.0e-3), lift_height=1.5e-3)
        pb.dwell(0.2)
        n_glyphs = sum(1 for c in text if c != " ")
        letters: List[Letter] = []
        x = start[0]
        gi = 0
        wi = 0
        for ti, ch in enumerate(text):
            sf = 1.0 if size_factors is None else float(size_factors[min(gi, len(size_factors) - 1)])
            if ch == " ":
                size = h0 * (1.0 - st.micrographia * gi / max(n_glyphs - 1, 1)) * sf
                x += (st.word_gap - st.letter_gap) * size
                wi += 1
                continue
            wch = ch if glyph_override is None else glyph_override.get(gi, ch)
            if wch not in GLYPH_SET:
                raise ValueError(f"no glyph for {wch!r}")
            size = h0 * (1.0 - st.micrographia * gi / max(n_glyphs - 1, 1)) * (1.0 + rng.normal(0.0, st.scale_jitter)) * sf
            y_base = start[1] + slope * (x - start[0]) + st.baseline_wander * h0 * math.sin(
                2 * np.pi * (x - start[0]) / (st.wander_period * h0) + wph)
            if baseline_offsets is not None:
                y_base += float(baseline_offsets[gi]) * h0
            shape = self.glyph_shape(wch, rng)
            if extra_warp is not None and extra_warp[gi] > 0:
                w_extra = warp_params(rng_err, float(extra_warp[gi]))
                shape = [apply_warp(s, w_extra) for s in shape]
            tf = 1.0 if tempo_factors is None else float(tempo_factors[gi])
            polys, strokes = [], []
            a_letter = None
            for s in shape:
                P = np.column_stack([x + size * (st.width * s[:, 0] + s[:, 1] * shear), y_base + size * s[:, 1]])
                travel = float(np.hypot(*(P[0] - pb.pos)))
                pb.move(P[0], (0.06 + travel / (st.air_speed_mm_s * 1e-3)) * tf)
                a = pb.n
                if a_letter is None:
                    a_letter = a
                pb.pen(True, kp.pen_T)
                pb.dwell(kp.dwell_start)
                drawn = [P[:1]]
                for piece in _split_at_corners(P, kp.corner_deg):
                    jit = max(0.5, 1.0 + rng_t.normal(0.0, st.tempo_jitter))
                    prof = piece_profile(piece, size, K * jit / tf, self.v_target * jit / tf, kp)
                    if prof is None:
                        # a dot or a degenerate piece: a short minimum-jerk move (as v1)
                        L = float(arclength(piece)[-1])
                        pb.polyline(piece, max(0.05, L / max(self.v_target, 1e-3)) * tf)
                        drawn.append(np.asarray(piece, float))
                        continue
                    xy = sample_piece(prof, dt)
                    xy[0] = pb.pos
                    n = len(xy)
                    pb._append(xy, np.full(n, True), np.zeros(n))
                    drawn.append(prof[2])
                pb.dwell(kp.dwell_end)
                pb.pen(False, kp.pen_T)
                strokes.append((a, pb.n))
                polys.append(np.vstack(drawn))
            letters.append(Letter(wch, ti, gi, wi, (a_letter, pb.n), strokes, polys, size, x, y_base))
            x += (glyph_width(wch) * st.width + st.letter_gap) * size
            gi += 1
        pb.dwell(0.3)
        it = pb.build()
        for L in letters:
            L.t0 = float(it.t[L.span[0]])
            L.t1 = float(it.t[min(L.span[1], len(it.t) - 1)])
            it.features.append(("letter", L.t0, L.t1, {"char": L.char, "glyph_index": L.glyph_index}))
        return Written(text, st, it, letters, dt, meta={"writer_seed": self.seed, "instance_seed": seed,
                                                         "style": dict(vars(st)), "synthetic": True, "writer_model": "v2",
                                                         "K": K, "v_target_mm_s": self.v_target * 1e3,
                                                         "kin_params": asdict(kp)})


def writer(w: int, version: str = "v2", kp: Optional[KinParams] = None, **style_over):
    """Writer w: 'v2' (this module) or 'v1' (aiguide/handwriting, unchanged)."""
    if version == "v1":
        return HW.writer(w, **style_over)
    st = sample_style(np.random.default_rng(w))
    for k, v in style_over.items():
        setattr(st, k, v)
    return WriterV2(st, seed=w, kp=kp)


# ------------------------------------------------------------------------------------------------ kinematics
def mean_down_speed(wr: Written) -> float:
    it = wr.intended
    dt = float(it.t[1] - it.t[0])
    v = np.hypot(*np.gradient(it.xy, dt, axis=0).T)
    return float(np.mean(v[it.pen_down]))


def kinematics(items: Sequence[Tuple[np.ndarray, np.ndarray, np.ndarray]], fs_out: float = 1000.0) -> Dict:
    """sim2/validate.writer_kinematics on (t, xy, pen_down) paths: mean pen-down speed, Welch velocity spectrum
    (share by band, cumulative percentiles), stroke durations between speed minima, power-law exponent."""
    from sim2 import validate as SV
    speeds, strokes, P_all, betas = [], [], [], []
    F_all = None
    for t, xy, down in items:
        k = SV._kin(np.asarray(t), np.asarray(xy), np.asarray(down, bool), fs_out)
        m = k["down"] & (k["t"] > 0.3)
        if m.sum() < 64:
            continue
        speeds.append(k["speed"][m])
        strokes.append(SV._strokes(k["speed"], k["down"], fs_out))
        f, Pxx = welch(k["v"][m], fs=fs_out, nperseg=min(2048, int(np.sum(m))), axis=0)
        if F_all is None or len(f) == len(F_all):
            F_all = f
            P_all.append(Pxx.sum(axis=1))
        sel = m & (k["speed"] > 5e-3) & (k["kappa"] > 1.0 / 0.05) & (k["kappa"] < 1.0 / 0.3e-3)
        if np.sum(sel) > 50:
            x = np.log(k["kappa"][sel])
            y = np.log(k["speed"][sel] * k["kappa"][sel])
            betas.append(float(np.polyfit(x, y, 1)[0]))
    sp = np.concatenate(speeds)
    st = np.concatenate(strokes) if strokes else np.zeros(0)
    Pm = np.mean(np.array(P_all), axis=0)
    cum = np.cumsum(Pm) / np.sum(Pm)
    fq = lambda q: float(F_all[min(np.searchsorted(cum, q), len(F_all) - 1)])
    band = lambda lo, hi: float(np.sum(Pm[(F_all >= lo) & (F_all < hi)]) / np.sum(Pm))
    return {"n_paths": len(speeds),
            "speed_mm_s": {"mean": float(sp.mean() * 1e3), "median": float(np.median(sp) * 1e3),
                           "p95": float(np.percentile(sp, 95) * 1e3)},
            "stroke_ms": {"median": float(np.median(st) * 1e3) if len(st) else None,
                          "iqr": [float(np.percentile(st, 25) * 1e3), float(np.percentile(st, 75) * 1e3)] if len(st) else None,
                          "n": int(len(st))},
            "spectrum": {"peak_Hz": float(F_all[np.argmax(Pm[1:]) + 1]), "f50": fq(0.5), "f90": fq(0.9), "f95": fq(0.95),
                         "f99": fq(0.99), "share_0_3": band(0, 3), "share_3_12": band(3, 12), "share_4_7": band(4, 7),
                         "share_8_12": band(8, 12), "share_above_12": band(12, 500)},
            "beta": {"mean": float(np.mean(betas)) if betas else None, "sd": float(np.std(betas)) if betas else None,
                     "n": len(betas)},
            "spectrum_Hz": F_all[F_all <= 30].tolist(), "spectrum_rel": (Pm[F_all <= 30] / Pm.max()).tolist()}


def written_items(ws: Sequence[Written]):
    return [(w.intended.t, w.intended.xy, w.intended.pen_down) for w in ws]


def fit_loss(kin: Dict) -> float:
    """Distance of a writer population's kinematics to the LIT targets (dimensionless; CALC)."""
    s = kin["spectrum"]
    l = ((kin["speed_mm_s"]["mean"] - TARGETS["speed_mm_s"]["mean"]) / 3.0) ** 2
    l += (math.log(max(s["share_8_12"], 1e-5) / 0.015) / math.log(1.25)) ** 2
    for q in ("f50", "f90", "f95", "f99"):
        l += 0.5 * (math.log(s[q] / TARGETS["cum_Hz"][q]) / math.log(1.15)) ** 2
    med = kin["stroke_ms"]["median"] or 0.0
    l += (max(0.0, 90.0 - med) / 10.0) ** 2 + (max(0.0, med - 150.0) / 10.0) ** 2
    b = kin["beta"]["mean"] or 1.0
    l += ((b - 2.0 / 3.0) / 0.05) ** 2
    return float(l)


# ------------------------------------------------------------------------------------------------ the fit (CALC)
# x-height prior: LIT PDT-06 median letter height 5.0 mm (IQR 1.4 mm) in healthy adults' free writing on paper, the
# mean of the heights of 'T', 'p' and 'a'; with the glyph font's proportions ('a' 1.0, 'p' 1.6 x-heights) and a capital
# 'T' of 1.5 x-heights (ASSUMPTION) that is an x-height of 5.0 / 1.37 = 3.65 mm (CALC), 1.40 x the aiguide mean (2.6 mm)
SIZE_PRIOR = {"x_height_mm": 5.0 / ((1.0 + 1.6 + 1.5) / 3.0), "scale_mean": (5.0 / ((1.0 + 1.6 + 1.5) / 3.0)) / 2.6,
              "scale_sd": (1.4 / ((1.0 + 1.6 + 1.5) / 3.0)) / 2.6 / 1.35,
              "label": "LIT PDT-06 (median letter height 5.0 mm, IQR 1.4 mm; mean of T, p, a) -> x-height 3.65 mm (CALC, "
                       "capital T = 1.5 x-heights ASSUMPTION)"}
FIT_SPACE = {  # name: (lo, hi, log)
    "size_scale": (1.0, 2.0, False), "smooth_geom": (0.02, 0.15, True), "sigma_t": (0.008, 0.05, True),
    "corner_deg": (30.0, 90.0, False), "c_acc": (3.0, 30.0, True), "v_cap": (2.0, 5.0, False),
    "kappa0": (20.0, 500.0, True)}


def population(kp: KinParams, writers: Sequence[int], text: str = ET_SENTENCE, dt: float = 1e-3) -> List[Written]:
    return [writer(w, "v2", kp=kp).write(text, dt=dt, seed=2000 + w) for w in writers]


def fit_objective(kin: Dict, kp: KinParams) -> float:
    l = fit_loss(kin)
    l += ((kp.size_scale - SIZE_PRIOR["scale_mean"]) / SIZE_PRIOR["scale_sd"]) ** 2
    return float(l)


def fit(writers: Sequence[int] = tuple(range(1000, 1006)), n_iter: int = 80, seed: int = 0, log=print) -> Dict:
    """Nelder-Mead over FIT_SPACE (unit-cube coordinates), from the defaults, on fitting writers (CALC)."""
    from scipy.optimize import minimize
    names = list(FIT_SPACE)
    base = KinParams(size_scale=SIZE_PRIOR["scale_mean"], smooth_geom=0.06, sigma_t=0.02, corner_deg=45.0, c_acc=12.0,
                     v_cap=3.5, kappa0=60.0)

    def to_u(kp):
        u = []
        for n in names:
            lo, hi, lg = FIT_SPACE[n]
            v = getattr(kp, n)
            u.append((math.log(v / lo) / math.log(hi / lo)) if lg else (v - lo) / (hi - lo))
        return np.array(u)

    def from_u(u):
        kw = {}
        for n, x in zip(names, np.clip(u, 0.0, 1.0)):
            lo, hi, lg = FIT_SPACE[n]
            kw[n] = float(lo * (hi / lo) ** x) if lg else float(lo + x * (hi - lo))
        return replace(base, **kw)

    hist = []

    def J(u):
        kp = from_u(u)
        try:
            kin = kinematics(written_items(population(kp, writers)))
            val = fit_objective(kin, kp)
        except Exception as e:                 # a degenerate setting: large loss
            kin, val = None, 1e6
        pen = float(np.sum(np.clip(u - 1.0, 0, None) ** 2 + np.clip(-u, 0, None) ** 2)) * 1e3
        hist.append({"params": asdict(kp), "loss": val + pen,
                     "summary": None if kin is None else summary_row(kin)})
        if log and len(hist) % 10 == 0:
            best = min(hist, key=lambda h: h["loss"])
            log(f"[writer fit] {len(hist)} evaluations, best loss {best['loss']:.2f}")
        return val + pen

    u0 = to_u(base)
    res = minimize(J, u0, method="Nelder-Mead", options={"maxfev": n_iter, "xatol": 1e-3, "fatol": 1e-3,
                                                          "initial_simplex": np.vstack([u0] + [np.clip(u0 + 0.25 * e, 0, 1)
                                                                                                for e in np.eye(len(u0))])})
    best = min(hist, key=lambda h: h["loss"])
    return {"method": "Nelder-Mead on the unit cube of FIT_SPACE (scipy), start at the defaults", "writers": list(writers),
            "n_evaluations": len(hist), "best": best, "history": hist, "space": FIT_SPACE, "size_prior": SIZE_PRIOR}


def summary_row(kin: Dict) -> Dict:
    s = kin["spectrum"]
    return {"speed_mean_mm_s": kin["speed_mm_s"]["mean"], "share_8_12": s["share_8_12"], "f50": s["f50"], "f90": s["f90"],
            "f95": s["f95"], "f99": s["f99"], "peak_Hz": s["peak_Hz"], "stroke_median_ms": kin["stroke_ms"]["median"],
            "beta": kin["beta"]["mean"]}
