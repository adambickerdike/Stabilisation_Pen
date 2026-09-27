"""Synthetic sessions for tests and the demo.  NOTHING HERE IS HUMAN DATA.

``synth_text_session``
    Known text written with a single-line glyph font (polylines in x-height
    units), slanted and jittered, timed with minimum-jerk segments from
    ``stabpen.signals.PathBuilder`` (pen lifts between strokes, stops at sharp
    corners), plus a small synthetic residual tremor
    (``stabpen.signals.tremor``).  Generated at 1 kHz, logged as ICD 0x02
    stroke samples at 200 Hz with pen-down/up events.  The generator knows
    which stroke ids form each word: that transcript is the ground truth.
``synth_sim_session``
    Wraps a coupled-simulator trace (``results/sim/nominal/traces_*.npz``,
    1 kHz): deposited ink ``tip`` -> 0x02 stroke samples at 200 Hz, housing
    ``housing`` / stage ``q`` / coil ``i`` -> 0x01 research frames (at the
    trace's 1 kHz, not the ICD's 2 kHz; fields the trace lacks are zero).

Synthetic parameters (writing speed, force, residual tremor, angles) are
illustrative settings of the generator, not claims about people.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import __version__
from ._util import ensure_stabpen_importable, file_sha256, ranges_from_ids, rel_to_repo, write_json
from .capture import contact_intervals
from .logfmt import (Event, EventCode, Header, RawRecord, RecordType, ResearchFrame, StrokeSample,
                     encode_log)

GENERATOR_ID = f"penapp.synth@{__version__}"
SYNTHETIC_DEVICE_ID = 0x5EED_0000_0000_00A1
MODE_ASSIST_KF = 3      # position of ASSIST_KF in the ICD section 6 list (numbering not defined by the ICD)


# ================================================================= glyphs
def _arc(cx, cy, rx, ry, a0, a1, step=12.0):
    n = max(3, int(abs(a1 - a0) / step) + 1)
    a = np.deg2rad(np.linspace(a0, a1, n))
    return [(cx + rx * math.cos(t), cy + ry * math.sin(t)) for t in a]


def _dot(x, y):
    return [(x, y), (x + 0.04, y + 0.03)]


# single-line glyphs in x-height units: baseline y = 0, x-height 1, ascender 1.6, descender -0.6
GLYPHS: Dict[str, List[List[Tuple[float, float]]]] = {
    "a": [_arc(.32, .5, .32, .5, 40, 400) + [(.64, 1.0), (.64, 0.0)]],
    "b": [[(0, 1.6), (0, 0)], _arc(.32, .5, .32, .5, 180, 540)],
    "c": [_arc(.32, .5, .32, .5, 45, 315)],
    "d": [_arc(.32, .5, .32, .5, 0, 360), [(.64, 1.6), (.64, 0)]],
    "e": [[(.02, .5), (.62, .5)] + _arc(.32, .5, .32, .5, 0, 320)],
    "f": [[(.6, 1.5)] + _arc(.4, 1.3, .18, .25, 60, 180) + [(.22, 0)], [(0, 1.0), (.5, 1.0)]],
    "g": [_arc(.32, .5, .32, .5, 0, 360), [(.64, 1.0), (.64, -.35)] + _arc(.34, -.35, .3, .28, 0, -160)],
    "h": [[(0, 1.6), (0, 0)], _arc(.32, .6, .32, .4, 180, 0) + [(.64, 0)]],
    "i": [[(.1, 1), (.1, 0)], _dot(.1, 1.4)],
    "j": [[(.3, 1), (.3, -.4)] + _arc(.08, -.4, .22, .22, 0, -150), _dot(.3, 1.4)],
    "k": [[(0, 1.6), (0, 0)], [(.55, 1.0), (.03, .42), (.58, 0)]],
    "l": [[(.1, 1.6), (.1, 0)]],
    "m": [[(0, 1), (0, 0)], _arc(.26, .6, .26, .4, 180, 0) + [(.52, 0)],
          _arc(.78, .6, .26, .4, 180, 0) + [(1.04, 0)]],
    "n": [[(0, 1), (0, 0)], _arc(.32, .6, .32, .4, 180, 0) + [(.64, 0)]],
    "o": [_arc(.32, .5, .32, .5, 90, 450)],
    "p": [[(0, 1), (0, -.6)], _arc(.32, .5, .32, .5, 180, 540)],
    "q": [_arc(.32, .5, .32, .5, 0, 360), [(.64, 1), (.64, -.6)]],
    "r": [[(0, 1), (0, 0)], _arc(.32, .6, .32, .4, 180, 50)],
    "s": [[(.58, .86), (.44, .98), (.22, 1.0), (.06, .9), (.04, .72), (.18, .58), (.46, .46), (.6, .3),
           (.56, .1), (.38, 0), (.16, 0), (0, .12)]],
    "t": [[(.2, 1.45), (.2, .18)] + _arc(.4, .18, .2, .18, 180, 300), [(0, 1), (.46, 1)]],
    "u": [[(0, 1), (0, .4)] + _arc(.32, .4, .32, .4, 180, 360) + [(.64, 1.0), (.64, 0)]],
    "v": [[(0, 1), (.32, 0), (.64, 1)]],
    "w": [[(0, 1), (.22, 0), (.44, .8), (.66, 0), (.88, 1)]],
    "x": [[(0, 1), (.62, 0)], [(.62, 1), (0, 0)]],
    "y": [[(0, 1), (.32, .05)], [(.64, 1), (.12, -.6)]],
    "z": [[(0, 1), (.6, 1), (0, 0), (.62, 0)]],
    "0": [_arc(.36, .75, .36, .75, 90, 450)],
    "1": [[(.05, 1.2), (.3, 1.5), (.3, 0)]],
    "2": [_arc(.32, 1.1, .32, .4, 160, -20) + [(0, 0), (.66, 0)]],
    "3": [_arc(.3, 1.12, .3, .38, 150, -90) + _arc(.3, .4, .34, .4, 90, -150)],
    "4": [[(.48, 0), (.48, 1.5), (0, .45), (.68, .45)]],
    "5": [[(.58, 1.5), (.1, 1.5), (.06, .85)] + _arc(.32, .45, .34, .45, 135, -150)],
    "6": [[(.52, 1.45)] + _arc(.34, .42, .34, .42, 160, 520)],
    "7": [[(0, 1.5), (.62, 1.5), (.2, 0)]],
    "8": [_arc(.32, 1.12, .26, .36, 270, 630) + _arc(.32, .4, .32, .4, 90, -270)],
    "9": [_arc(.32, 1.08, .32, .42, 0, 360), [(.64, 1.1), (.5, 0)]],
    ".": [_dot(.05, .02)],
    ",": [[(.1, .08), (.02, -.25)]],
    ":": [_dot(.05, .02), _dot(.05, .8)],
    "-": [[(0, .5), (.42, .5)]],
    "/": [[(0, -.2), (.5, 1.5)]],
    "'": [[(.05, 1.5), (.03, 1.15)]],
}


def glyph_width(ch: str) -> float:
    return max(x for stroke in GLYPHS[ch] for x, _ in stroke)


@dataclass
class SynthConfig:
    x_height_mm: float = 2.6
    slant_deg: float = 12.0
    letter_gap: float = 0.3        # x-height units
    word_gap: float = 1.3
    line_pitch: float = 3.4
    speed_mm_s: float = 28.0       # mean pen speed along a stroke piece
    air_speed_mm_s: float = 60.0   # pen-up travel
    corner_deg: float = 60.0       # split into separate min-jerk pieces (stop) at sharper turns
    jitter: float = 0.04           # per-glyph offset, x-height units (SD)
    scale_jitter: float = 0.05     # per-glyph scale (SD)
    tremor_residual_um: float = 25.0   # synthetic residual ink tremor, peak (6 Hz)
    force_mN: float = 950.0
    theta_deg: float = 52.0
    phi_deg: float = 35.0
    dt: float = 1e-3               # generator rate (1 kHz)


@dataclass
class SynthSession:
    header: Header
    records: list
    truth: Optional[dict]
    meta: dict
    ink_1khz: Optional[np.ndarray] = None       # (n, 2) um, page frame (for fidelity cross-checks)
    contact_1khz: Optional[np.ndarray] = None

    def encode(self) -> bytes:
        return encode_log(self.header, self.records)

    def write(self, log_path, *, truth_path=None, meta_path=None) -> dict:
        data = self.encode()
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes(data)
        out = {"log": rel_to_repo(log_path), "log_sha256": file_sha256(log_path), "log_bytes": len(data)}
        if truth_path is not None and self.truth is not None:
            write_json(truth_path, self.truth)
            out["truth"] = rel_to_repo(truth_path)
            out["truth_sha256"] = file_sha256(truth_path)
        if meta_path is not None:
            write_json(meta_path, {**self.meta, "files": out})
            out["meta"] = rel_to_repo(meta_path)
        return out


def _split_at_corners(P: np.ndarray, corner_deg: float) -> List[np.ndarray]:
    if len(P) < 3:
        return [P]
    d = np.diff(P, axis=0)
    ang = np.degrees(np.abs(np.arctan2(d[1:, 0] * d[:-1, 1] - d[1:, 1] * d[:-1, 0],
                                       np.sum(d[1:] * d[:-1], axis=1))))
    cuts = [0] + [k + 1 for k in np.flatnonzero(ang > corner_deg)] + [len(P) - 1]
    return [P[a:b + 1] for a, b in zip(cuts[:-1], cuts[1:]) if b > a]


def _polyline_fn(P: np.ndarray):
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    total = s[-1] if s[-1] > 0 else 1.0

    def fn(u):
        su = u * total
        return np.array([np.interp(su, s, P[:, 0]), np.interp(su, s, P[:, 1])])
    return fn, s[-1]


def _angles(cfg: SynthConfig, t: np.ndarray, rng) -> Tuple[np.ndarray, np.ndarray]:
    th = cfg.theta_deg + 2.0 * np.sin(2 * np.pi * 0.2 * t + rng.uniform(0, 6.28))
    ph = cfg.phi_deg + 3.0 * np.sin(2 * np.pi * 0.15 * t + rng.uniform(0, 6.28))
    return th, ph


def _events_and_samples(t_ms, xy_um, contact, force_mN, theta_deg, phi_deg, *, period_ms=5):
    """Stroke samples on the 5 ms grid inside contact runs + pen events."""
    items = []   # (time_us, order, record)
    for sid, (a, b) in enumerate(contact_intervals(contact)):
        items.append((int(t_ms[a]) * 1000, 0, Event(int(t_ms[a]) * 1000, EventCode.PEN_DOWN, sid)))
        for k in range(a, b):
            if t_ms[k] % period_ms:
                continue
            th, ph = StrokeSample.angles_to_raw(float(theta_deg[k]), float(phi_deg[k]))
            items.append((int(t_ms[k]) * 1000, 1, StrokeSample(int(t_ms[k]), sid, int(xy_um[k, 0]), int(xy_um[k, 1]),
                                                              int(np.clip(round(force_mN[k]), 0, 65535)), th, ph)))
        t_up = int(t_ms[b]) if b < len(t_ms) else int(t_ms[b - 1]) + 1
        items.append((t_up * 1000, 2, Event(t_up * 1000, EventCode.PEN_UP, sid)))
    items.sort(key=lambda it: (it[0], it[1]))
    return [it[2] for it in items], len(contact_intervals(contact))


def synth_text_session(lines: Sequence[str], *, seed: int = 0, session_id: int = 1,
                       start_unix_ms: int = 1788253200000, cfg: Optional[SynthConfig] = None,
                       device_id: int = SYNTHETIC_DEVICE_ID) -> SynthSession:
    """Write ``lines`` of known text as a synthetic pen session (see module docstring)."""
    ensure_stabpen_importable()
    from stabpen import signals as sg

    cfg = cfg or SynthConfig()
    rng = np.random.default_rng(seed)
    h = cfg.x_height_mm * 1e-3
    shear = math.tan(math.radians(cfg.slant_deg))
    pb = sg.PathBuilder(cfg.dt, start=(0.0, 0.0), lift_height=1.5e-3)
    pb.dwell(0.2)
    truth_lines = []
    n_strokes = 0
    for li, line in enumerate(lines):
        words = line.lower().split()
        x_cursor = rng.normal(0.0, 0.05) * h
        baseline = -li * cfg.line_pitch * h
        truth_words = []
        for word in words:
            ids = []
            for ch in word:
                if ch not in GLYPHS:
                    raise ValueError(f"no glyph for {ch!r}")
                sc = 1.0 + rng.normal(0.0, cfg.scale_jitter)
                dx, dy = rng.normal(0.0, cfg.jitter, 2)
                for stroke in GLYPHS[ch]:
                    pts = np.asarray(stroke, float) * sc + [dx, dy]
                    P = np.column_stack([x_cursor + (pts[:, 0] + pts[:, 1] * shear) * h, baseline + pts[:, 1] * h])
                    travel = float(np.hypot(*(P[0] - pb.pos)))
                    pb.move(P[0], 0.06 + travel / (cfg.air_speed_mm_s * 1e-3))
                    pb.pen(True, 0.04)
                    pb.dwell(0.015)
                    for piece in _split_at_corners(P, cfg.corner_deg):
                        fn, length = _polyline_fn(piece)
                        pb.curve(fn, max(0.05, length / (cfg.speed_mm_s * 1e-3)))
                    pb.dwell(0.01)
                    pb.pen(False, 0.04)
                    ids.append(n_strokes)
                    n_strokes += 1
                x_cursor += (glyph_width(ch) * sc + cfg.letter_gap) * h
            x_cursor += (cfg.word_gap - cfg.letter_gap) * h
            truth_words.append({"text": word, "stroke_ranges": ranges_from_ids(ids)})
        truth_lines.append({"text": " ".join(words), "words": truth_words})
    pb.dwell(0.3)
    it = pb.build()
    t = it.t
    n = len(t)
    trem = sg.tremor(t, sg.TremorSpec(f0=6.0, amp_pk=cfg.tremor_residual_um * 1e-6, onset=0.0),
                     np.random.default_rng(seed + 7000))
    ink = it.xy + trem
    contact = it.pen_down.astype(bool)
    runs = contact_intervals(contact)
    if len(runs) != n_strokes:
        raise RuntimeError(f"generator produced {len(runs)} contact runs for {n_strokes} planned strokes")
    first = runs[0][0]
    xy_um = np.rint((ink - ink[first]) * 1e6).astype(np.int64)
    t_ms = np.rint(t * 1000).astype(np.int64)
    force = np.zeros(n)
    for a, b in runs:
        k = np.arange(a, b)
        ramp = np.minimum(1.0, np.minimum((k - a + 1) / 15.0, (b - k) / 15.0))
        force[a:b] = cfg.force_mN * ramp * (1 + 0.08 * np.sin(2 * np.pi * 1.3 * t[a:b] + rng.uniform(0, 6.28)))
    force[contact] += rng.normal(0.0, 15.0, int(contact.sum()))
    force = np.clip(force, 0.0, None)
    th, ph = _angles(cfg, t, rng)
    recs, _ = _events_and_samples(t_ms, xy_um, contact, force, th, ph)
    note = (f"SYNTHETIC session: {GENERATOR_ID} glyph handwriting of a known transcript, seed {seed}; "
            f"not human data")
    header = Header(device_id=device_id, session_id=session_id, start_unix_ms=start_unix_ms)
    records = [RawRecord(int(RecordType.ANNOTATION), note.encode("utf-8")),
               Event(0, EventCode.MODE_CHANGE, MODE_ASSIST_KF)] + recs
    truth = {"object": "synthetic_truth", "generator": GENERATOR_ID, "seed": seed, "language": "en",
             "evidence_status": "SYNTHETIC ground truth (generator-known transcript and stroke ids)",
             "text": "\n".join(l["text"] for l in truth_lines), "lines": truth_lines, "n_strokes": n_strokes}
    meta = {"object": "synthetic_session_meta", "generator": GENERATOR_ID, "kind": "glyph_text", "seed": seed,
            "evidence_status": "SYNTHETIC - not a recording of a person, not a measurement",
            "session_id": session_id, "device_id": str(device_id), "start_unix_ms": start_unix_ms,
            "config": vars(cfg), "duration_s": round(n * cfg.dt, 3), "n_strokes": n_strokes,
            "stroke_samples": sum(isinstance(r, StrokeSample) for r in records),
            "notes": ["pen-down/up events carry arg = stroke_id (proposed; ICD does not define the arg)",
                      "mode-change arg 3 = ASSIST_KF by position in ICD section 6 (numbering not defined by ICD)",
                      "force: synthetic profile with 15 ms ramps; theta/phi slow synthetic variation"]}
    return SynthSession(header, records, truth, meta, ink_1khz=(ink - ink[first]) * 1e6, contact_1khz=contact)


def synth_sim_session(trace_path, *, session_id: int = 3, start_unix_ms: int = 1788256800000,
                      theta_deg: float = 50.0, phi_deg: float = 0.0,
                      device_id: int = SYNTHETIC_DEVICE_ID) -> SynthSession:
    """ICD log (0x02 + 0x01 + events) from a coupled-simulator trace (1 kHz)."""
    ensure_stabpen_importable()
    from stabpen.contact import reaction_components

    d = np.load(trace_path)
    t_ms = np.rint(d["t"].astype(np.float64) * 1000).astype(np.int64)
    tip = d["tip"].astype(np.float64)
    housing = d["housing"].astype(np.float64)
    q = d["q"].astype(np.float64)
    cur = d["i"].astype(np.float64)
    N = d["N"].astype(np.float64)
    contact = d["contact"].astype(bool)
    runs = contact_intervals(contact)
    origin = tip[runs[0][0]]
    xy_um = np.rint((tip - origin) * 1e6).astype(np.int64)
    f_ax = reaction_components(N, 0.0, 0.0, math.radians(theta_deg))["R_a"] * 1e3   # axial proxy, mu = 0
    th = np.full(len(t_ms), theta_deg)
    ph = np.full(len(t_ms), phi_deg)
    recs, n_strokes = _events_and_samples(t_ms, xy_um, contact, f_ax, th, ph)
    frames = []
    pH = np.rint((housing - origin) * 1e7).astype(np.int64)
    q01 = np.clip(np.rint(q * 1e7), -32768, 32767).astype(np.int64)
    i01 = np.clip(np.rint(cur * 1e4), -32768, 32767).astype(np.int64)
    fax = np.clip(np.rint(f_ax), -32768, 32767).astype(np.int64)
    for k in range(len(t_ms)):
        frames.append((int(t_ms[k]) * 1000, 0, ResearchFrame(
            t_us=int(t_ms[k]) * 1000, q1=int(q01[k, 0]), q2=int(q01[k, 1]), i1=int(i01[k, 0]), i2=int(i01[k, 1]),
            f_ax=int(fax[k]), p_Hx=int(pH[k, 0]), p_Hy=int(pH[k, 1]), mode=MODE_ASSIST_KF,
            flags=int(contact[k]), theta=int(round(theta_deg * 100)), phi=int(round(phi_deg * 100)))))
    def order(r):   # pen-down event, research frame, stroke sample, pen-up event at equal times
        if isinstance(r, StrokeSample):
            return r.t_ms * 1000, 2
        return r.t_us, 0 if r.code == EventCode.PEN_DOWN else 3
    ordered = [(*order(r), r) for r in recs]
    ordered += [(t, 1, fr) for t, _, fr in frames]
    ordered.sort(key=lambda it: (it[0], it[1]))
    name = Path(trace_path).name
    sha = file_sha256(trace_path)
    note = (f"SYNTHETIC session: {GENERATOR_ID} from simulator trace {name} sha256 {sha[:16]}; "
            f"not human data")
    header = Header(device_id=device_id, session_id=session_id, start_unix_ms=start_unix_ms)
    records = [RawRecord(int(RecordType.ANNOTATION), note.encode("utf-8")),
               Event(0, EventCode.MODE_CHANGE, MODE_ASSIST_KF)] + [it[2] for it in ordered]
    meta = {"object": "synthetic_session_meta", "generator": GENERATOR_ID, "kind": "simulator_trace",
            "evidence_status": "SYNTHETIC - coupled-simulator output on synthetic handwriting; not a measurement",
            "trace": rel_to_repo(trace_path), "trace_sha256": sha, "session_id": session_id,
            "device_id": str(device_id), "start_unix_ms": start_unix_ms, "n_strokes": n_strokes,
            "theta_deg": theta_deg, "phi_deg": phi_deg,
            "notes": ["stroke samples: 'tip' (deposited ink) on the 5 ms grid inside contact runs, rounded to 1 um",
                      "research frames at the trace's 1 kHz (ICD: 2 kHz); p_H = 'housing', q = stage, i = coil current",
                      "force / f_ax = simulator normal force N * sin(theta) (axial component with mu = 0; the trace "
                      "has no F_ax)",
                      "research-frame fields absent from the trace (qr, iref, dhat, g, f_est, vbat, t_coil, imu) are 0",
                      "p_H and stroke x, y share the page origin (first-contact ink position)"]}
    return SynthSession(header, records, None, meta, ink_1khz=(tip - origin) * 1e6, contact_1khz=contact)
