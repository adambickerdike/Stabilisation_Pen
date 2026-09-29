"""Loaders: one per dataset, each returning records in SI units (or labelled arbitrary units) at a uniform rate.

Tremor recordings -> ``TremorRec`` (uniformly sampled, (n, k) array, quantity 'displacement' or 'acceleration').
Writing recordings -> ``WritingRec`` (points with time, pen-down flag and per-point character index) or, for UJI,
shapes only.  Personal fields in the files (names, person ID numbers, weights, heights) are never read into the
records; only the dataset's own anonymous subject key, the group, the task, the hand and an age band where given.
"""
from __future__ import annotations

import glob
import hashlib
import io
import json
import math
import os
import pickle
import re
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from . import RAW_DIR
from . import calib as CB
from . import dsp as D

FS_TREMOR = 1000.0            # common rate of tremor records (Hz), except PADS (100 Hz, kept)


@dataclass
class TremorRec:
    rid: str
    source: str
    subject: str
    group: str                 # PD | ET | control | other
    task: str
    condition: str             # rest | postural | kinetic
    fs: float
    quantity: str              # displacement | acceleration
    units: str                 # m | m/s2 | a.u.
    x: np.ndarray              # (n, k)
    calib: str
    meta: Dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return len(self.x) / self.fs


@dataclass
class WritingRec:
    rid: str
    source: str
    writer: str
    text: str
    t: np.ndarray              # (n,) s (pen-down points only for BRUSH; with pen-up points where recorded)
    xy: np.ndarray             # (n, 2) m, page frame (x right, y up)
    down: np.ndarray           # (n,) bool
    char: np.ndarray           # (n,) index into text, -1 if unknown
    stroke: np.ndarray         # (n,) stroke number (pen-down run), -1 while up
    fs: float
    units: str
    meta: Dict = field(default_factory=dict)


# ================================================================== tremor: UCI PD spiral tablet (CC BY 4.0)
UCI_DIR = RAW_DIR / "uci_pd_spiral"
UCI_TESTS = {0: "static_spiral", 1: "dynamic_spiral", 2: "circles_around_point"}


def _uci_files() -> List[Tuple[str, str]]:
    if not UCI_DIR.exists():
        zp = RAW_DIR / "uci_pd_spiral.zip"
        if zp.exists():
            zipfile.ZipFile(zp).extractall(UCI_DIR)
    out = []
    for grp, pat in (("control", "hw_dataset/control/*.txt"), ("PD", "hw_dataset/parkinson/*.txt"),
                     ("PD", "new_dataset/parkinson/*.txt")):
        out += [(grp, p) for p in sorted(glob.glob(str(UCI_DIR / pat)))]
    return out


def uci_spiral_records(min_s: float = 5.0, fs: float = FS_TREMOR) -> List[TremorRec]:
    """One record per (file, test): the longest run without a time gap > 50 ms, resampled (cubic) to fs.  Position =
    screen pixels x 0.204 mm (MFR pitch; DERIVED unit), y flipped to point up the page.  Hover samples inside the
    stream are kept (the tablet tracks the pen up to 5 mm above the glass, MFR)."""
    recs = []
    for grp, p in _uci_files():
        a = np.genfromtxt(p, delimiter=";")
        a = a[np.all(np.isfinite(a[:, :7]), axis=1)]
        subj = os.path.basename(p)[:-4]
        ds = "new" if "new_dataset" in p else "hw"
        for tid in np.unique(a[:, 6]).astype(int):
            b = a[a[:, 6] == tid]
            t = b[:, 5] * 1e-3
            best = max(D.segments(t, 0.05), key=lambda ab: ab[1] - ab[0], default=None)
            if best is None:
                continue
            s = slice(*best)
            tt = t[s]
            if tt[-1] - tt[0] < min_s:
                continue
            xy = np.column_stack([b[s, 0], -b[s, 1]]) * CB.CINTIQ12WX_PITCH_M
            tu, xu = D.uniform(tt, xy, fs)
            dt_med = float(np.median(np.diff(tt)))
            recs.append(TremorRec(
                rid=f"uci_spiral/{ds}/{subj}/t{tid}", source="uci_spiral", subject=f"{ds}/{subj}", group=grp,
                task=UCI_TESTS.get(tid, f"test{tid}"), condition="kinetic", fs=fs, quantity="displacement", units="m",
                x=xu, calib=CB.LABELS["uci_spiral"],
                meta={"native_rate_hz": 1.0 / dt_med, "pressure_zero_frac": float(np.mean(b[s, 3] <= 0)),
                      "hover_frac": float(np.mean(b[s, 2] > 0)), "dataset_part": ds}))
    return recs


# ================================================================== tremor: NewHandPD BiSP pen (no licence stated)
NHPD_TASKS = {"sigSp": ("spiral", "kinetic"), "sigMea": ("meander", "kinetic"), "circA": ("circle_on_paper", "kinetic"),
              "circB": ("circle_in_air", "kinetic"), "sigDiaA": ("diadochokinesis_right", "kinetic"),
              "sigDiaB": ("diadochokinesis_left", "kinetic")}


def _nhpd_parse(raw: bytes) -> Tuple[Dict, np.ndarray]:
    s = raw.decode("latin-1")
    head = {}
    for k in ("Age", "Writing_Hand", "Samplerate", "Pen", "Date"):
        m = re.search(rf"<{k}>(.*?)</{k}>", s)
        head[k] = m.group(1) if m else ""
    body = "\n".join(l for l in s.splitlines() if l and not l.startswith("#"))
    a = np.loadtxt(io.StringIO(body)) if body else np.zeros((0, 6))
    return head, np.atleast_2d(a)


def newhandpd_files() -> List[Tuple[str, str, str]]:
    """(zip name, member, group) of every signal file."""
    out = []
    for zn, grp in (("newhandpd_PatientSignal.zip", "PD"), ("newhandpd_HealthySignal.zip", "control")):
        zp = RAW_DIR / zn
        if not zp.exists():
            continue
        with zipfile.ZipFile(zp) as z:
            for n in z.namelist():
                if n.startswith("Signal/") and n.endswith(".txt") and not os.path.basename(n).startswith("._"):
                    out.append((zn, n, grp))
    return out


def _nhpd_task(name: str) -> Tuple[str, str, str]:
    b = os.path.basename(name)[:-4]
    m = re.match(r"(sigSp|sigMea|circA|circB|sigDiaA|sigDiaB)(\d?)-?([HP]?\d+)$", b)
    if not m:
        return "", "", ""
    kind, num, subj = m.groups()
    task, cond = NHPD_TASKS[kind]
    return task + (num or ""), cond, subj


def newhandpd_iter(tasks: Optional[Sequence[str]] = None) -> Iterator[Tuple[Dict, np.ndarray]]:
    """Yield (info, raw 6-channel array) per file, skipping byte-identical duplicates (the patient archive holds
    identical files under two patient numbers, e.g. circB-P2 and circB-P25: a data-quality finding, reported)."""
    seen = {}
    for zn, n, grp in newhandpd_files():
        task, cond, subj = _nhpd_task(n)
        if not task or (tasks and not any(task.startswith(t) for t in tasks)):
            continue
        with zipfile.ZipFile(RAW_DIR / zn) as z:
            raw = z.read(n)
        h = hashlib.sha1(raw).hexdigest()
        subj_key = (subj if subj[:1] in "HP" else ("H" + subj if grp == "control" else "P" + subj))
        info = {"zip": zn, "member": n, "group": grp, "task": task, "condition": cond, "subject": subj_key, "sha1": h}
        if h in seen:
            info["duplicate_of"] = seen[h]
            yield info, None
            continue
        seen[h] = n
        head, a = _nhpd_parse(raw)
        age = head.get("Age", "")
        info.update({"fs": float(head.get("Samplerate") or 1000.0), "pen": head.get("Pen", ""),
                     "age_band": (f"{int(float(age)) // 10 * 10}s" if re.match(r"^\d+(\.\d+)?$", age or "") else ""),
                     "hand": {"1": "right", "2": "left"}.get(head.get("Writing_Hand", ""), "")})
        yield info, a


def newhandpd_gravity(max_files: int = 400) -> Dict:
    """The DERIVED gravity calibration of CH4-6: quasi-static windows pooled over every task of every file (the
    diadochokinesis and in-air circles turn the pen through many orientations)."""
    S = []
    k = 0
    for info, a in newhandpd_iter():
        if a is None or len(a) < 2000:
            continue
        v = D.lowpass(a[:, 3:6], info["fs"], 5.0)
        qs = CB.quasi_static(v, info["fs"])
        if len(qs):
            S.append(qs[:: max(1, len(qs) // 40)])
        k += 1
        if k >= max_files:
            break
    V = np.vstack(S)
    cal = CB.gravity_fit(V)
    cal["n_files"] = k
    return cal


def newhandpd_records(cal: Dict, tasks: Sequence[str] = ("spiral", "meander", "circle"), fs: float = FS_TREMOR) -> List[TremorRec]:
    recs = []
    for info, a in newhandpd_iter(tasks):
        if a is None or len(a) < 3000:
            continue
        acc = CB.apply_gravity(a[:, 3:6], cal)
        # the first and last 0.5 s (beep, pen landing and lifting) are cut
        c = int(0.5 * info["fs"])
        acc = acc[c:len(acc) - c]
        recs.append(TremorRec(
            rid=f"newhandpd/{info['subject']}/{info['task']}", source="newhandpd", subject=info["subject"],
            group=info["group"], task=info["task"], condition=info["condition"], fs=info["fs"], quantity="acceleration",
            units="m/s2", x=acc, calib=CB.LABELS["newhandpd"],
            meta={"age_band": info.get("age_band", ""), "hand": info.get("hand", ""), "sensor": "pen rear end (BiSP)"}))
    return recs


# ================================================================== tremor: Zenodo ET hand accelerometry (CC BY 4.0)
def zenodo_et_records(fs_out: float = FS_TREMOR) -> List[TremorRec]:
    from scipy.io import loadmat
    from scipy.signal import decimate
    d = RAW_DIR / "zenodo_et_acc"
    a = loadmat(d / "acc_signal_database.mat", squeeze_me=True, struct_as_record=False)["acc_signal_database"]
    c = loadmat(d / "clinical_data.mat", squeeze_me=True, struct_as_record=False)["clinical_data"]
    clin = {}
    for e in c:
        ft = e.FTM_total
        clin[int(e.subject)] = {"FTM_total": float(ft) if np.size(ft) == 1 else None,
                                "age_band": (f"{int(float(e.age)) // 10 * 10}s" if np.size(e.age) == 1 else "")}
    recs = []
    for e in a:
        fs = float(e.Fs)
        q = int(round(fs / fs_out))
        for cond in ("posture", "rest"):
            x = np.asarray(getattr(e, cond), float)
            if x.size < fs * 10:
                continue
            y = decimate(decimate(x, 5, zero_phase=True), q // 5, zero_phase=True) if q == 5 * (q // 5) else decimate(x, q, zero_phase=True)
            recs.append(TremorRec(
                rid=f"zenodo_et/S{int(e.subject):02d}/{e.hand}/{cond}", source="zenodo_et", subject=f"S{int(e.subject):02d}",
                group="ET", task=cond, condition="postural" if cond == "posture" else "rest", fs=fs_out,
                quantity="acceleration", units="a.u.", x=y[:, None], calib=CB.LABELS["zenodo_et"],
                meta={"hand": str(e.hand), "FTM_total": clin.get(int(e.subject), {}).get("FTM_total"),
                      "age_band": clin.get(int(e.subject), {}).get("age_band", ""),
                      "clipped_frac": float(np.mean(np.abs(x) >= 4.999)), "native_fs": fs}))
    return recs


# ================================================================== tremor: PADS smartwatch (CC BY-NC-SA 4.0)
PADS_TASKS = ["Relaxed1", "Relaxed2", "RelaxedTask1", "RelaxedTask2", "StretchHold", "HoldWeight", "DrinkGlas",
              "CrossArms", "TouchNose", "Entrainment1", "Entrainment2"]
PADS_COND = {"Relaxed1": "rest", "Relaxed2": "rest", "RelaxedTask1": "rest", "RelaxedTask2": "rest",
             "StretchHold": "postural", "HoldWeight": "postural", "Entrainment1": "postural", "Entrainment2": "postural",
             "DrinkGlas": "kinetic", "CrossArms": "kinetic", "TouchNose": "kinetic"}
PADS_N = 976                   # samples per task after the authors' preprocessing (1024 - 48)


def pads_subjects() -> List[Dict]:
    import csv
    p = RAW_DIR / "pads" / "file_list.csv"
    rows = list(csv.DictReader(open(p)))
    have = set(os.path.basename(f)[:3] for f in glob.glob(str(RAW_DIR / "pads" / "preprocessed" / "movement" / "*_ml.bin")))
    grp = {"Essential Tremor": "ET", "Parkinson's": "PD", "Healthy": "control"}
    out = []
    for r in rows:
        if r["id"] in have and r["condition"] in grp:
            out.append({"id": r["id"], "group": grp[r["condition"]], "handedness": r["handedness"],
                        "age_band": f"{int(float(r['age'])) // 10 * 10}s" if r["age"] else "",
                        "dbs": "THS" in (r["disease_comment"] or "")})
    return out


def pads_records(tasks: Sequence[str] = tuple(PADS_TASKS), wrists: Sequence[str] = ("Left", "Right")) -> List[TremorRec]:
    """Acceleration (m/s^2, 3 axes) and rotation (rad/s, meta) per subject, task and wrist, 100 samples/s."""
    recs = []
    for s in pads_subjects():
        p = RAW_DIR / "pads" / "preprocessed" / "movement" / f"{s['id']}_ml.bin"
        a = np.fromfile(p, dtype=np.float32)
        nch = len(PADS_TASKS) * 2 * 6
        if a.size != nch * PADS_N:
            continue
        a = a.reshape(nch, PADS_N)
        for ti, task in enumerate(PADS_TASKS):
            if task not in tasks:
                continue
            for wi, wr in enumerate(("Left", "Right")):
                if wr not in wrists:
                    continue
                base = (ti * 2 + wi) * 6
                acc = a[base:base + 3].T.astype(float) * CB.G0
                gyr = a[base + 3:base + 6].T.astype(float)
                writing = (s["handedness"] or "right").lower().startswith(wr.lower()[0])
                recs.append(TremorRec(
                    rid=f"pads/{s['id']}/{task}/{wr}", source="pads", subject=s["id"], group=s["group"], task=task,
                    condition=PADS_COND[task], fs=100.0, quantity="acceleration", units="m/s2", x=acc,
                    calib=CB.LABELS["pads"],
                    meta={"wrist": wr, "writing_hand": bool(writing), "gyro": gyr, "age_band": s["age_band"], "dbs": s["dbs"]}))
    return recs


# ================================================================== writing: UCI Character Trajectories (CC BY 4.0)
@lru_cache(maxsize=1)
def chartraj() -> List[Dict]:
    """Every character: its letter, time (200 Hz) and pen position (m) integrated from the velocities with the file's
    own constants (consts.datanorm, consts.units = 0.005 per tablet unit, consistent with a 5080 lpi WACOM grid;
    the scale of LIT CON-25), and the pen force (normalised).  Leading and trailing zero-velocity padding removed."""
    from scipy.io import loadmat
    d = RAW_DIR / "chartraj"
    if not (d / "mixoutALL_shifted.mat").exists():
        zipfile.ZipFile(RAW_DIR / "chartraj.zip").extractall(d)
    m = loadmat(d / "mixoutALL_shifted.mat", squeeze_me=True, struct_as_record=False)
    c = m["consts"]
    key = [str(k) for k in c.key]
    lab = np.asarray(c.charlabels).astype(int)
    norm = np.asarray(c.datanorm, float)
    unit = float(np.asarray(c.units, float)[0]) * 1e-3            # 0.005 mm -> m
    dt = float(c.dt)
    out = []
    for i, v in enumerate(m["mixout"]):
        v = np.asarray(v, float)
        vx, vy, fz = v[0] * norm[0], v[1] * norm[1], v[2] * norm[2]
        sp = np.hypot(vx, vy)
        nz = np.flatnonzero(sp > 1e-9)
        if len(nz) < 10:
            continue
        a, b = nz[0], nz[-1] + 1
        xy = np.column_stack([np.cumsum(vx[a:b]), np.cumsum(vy[a:b])]) * unit
        out.append({"i": i, "char": key[lab[i] - 1], "t": np.arange(b - a) * dt, "xy": xy - xy[0], "force": fz[a:b],
                    "fs": 1.0 / dt})
    return out


# ================================================================== writing: UJI Pen Characters v2 (CC BY 4.0)
@lru_cache(maxsize=1)
def uji() -> Dict[Tuple[str, str], List[List[np.ndarray]]]:
    """(writer, char) -> instances, each a list of strokes (m, y up).  Shapes only: no timing in the data."""
    p = RAW_DIR / "uji2" / "ujipenchars2.txt"
    if not p.exists():
        zipfile.ZipFile(RAW_DIR / "uji2.zip").extractall(RAW_DIR / "uji2")
    lines = p.read_text(encoding="latin-1").splitlines()
    data: Dict[Tuple[str, str], List[List[np.ndarray]]] = {}
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("WORD"):
            parts = ln.split()
            ch, wid = parts[1], parts[2]
            writer = wid.rsplit("-", 1)[0]
            ns = int(lines[i + 1].split()[1])
            strokes = []
            for s in range(ns):
                toks = lines[i + 2 + s].split("#")[1].split()
                strokes.append(np.array(toks, float).reshape(-1, 2) * np.array([1.0, -1.0]) * CB.UJI_M_PER_UNIT)
            data.setdefault((writer, ch), []).append(strokes)
            i += 2 + ns
        else:
            i += 1
    return data


# ================================================================== writing: BRUSH (non-commercial research use)
BRUSH_ZIP = RAW_DIR / "brush_refined_BRUSH.zip"
BRUSH_DT = 0.01               # s: the authors resampled every drawing at 10 ms


@lru_cache(maxsize=1)
def brush_index() -> Dict[str, List[str]]:
    """writer -> member names of the original (10 ms) drawings."""
    out: Dict[str, List[str]] = {}
    with zipfile.ZipFile(BRUSH_ZIP) as z:
        for n in z.namelist():
            parts = n.split("/")
            if len(parts) == 3 and parts[0] == "BRUSH" and parts[2] and "resample" not in parts[2] \
                    and not parts[2].startswith(".") and not parts[2].startswith("._"):
                out.setdefault(parts[1], []).append(n)
    for k in out:
        out[k].sort(key=lambda s: int(re.sub(r"\D", "", s.split("/")[2]) or 0))
    return out


def brush_load(member: str, z: Optional[zipfile.ZipFile] = None) -> Tuple[str, np.ndarray, np.ndarray]:
    """(sentence, drawing (N, 3): x px, y px (down), end-of-stroke flag, char index per point or -1)."""
    close = z is None
    z = z or zipfile.ZipFile(BRUSH_ZIP)
    try:
        sent, draw, lab = pickle.loads(z.read(member))
    finally:
        if close:
            z.close()
    draw = np.asarray(draw, float)
    lab = np.asarray(lab, float)
    ci = np.where(lab.max(axis=1) > 0.5, lab.argmax(axis=1), -1) if lab.size else -np.ones(len(draw), int)
    return str(sent), draw, ci.astype(int)


def brush_record(member: str, scale_m_per_px: float, z: Optional[zipfile.ZipFile] = None) -> WritingRec:
    """Pen-down points only (as released), 10 ms apart within each stroke; y flipped to point up the page."""
    sent, draw, ci = brush_load(member, z)
    eos = draw[:, 2] > 0.5
    stroke = np.r_[0, np.cumsum(eos[:-1])].astype(int)
    xy = np.column_stack([draw[:, 0], -draw[:, 1]]) * scale_m_per_px
    t = np.arange(len(draw)) * BRUSH_DT                   # pen-down time only (pen-up time is not in the release)
    w, name = member.split("/")[1], member.split("/")[2]
    return WritingRec(rid=f"brush/{w}/{name}", source="brush", writer=w, text=sent, t=t, xy=xy,
                      down=np.ones(len(draw), bool), char=ci, stroke=stroke, fs=1.0 / BRUSH_DT,
                      units=f"m (DERIVED scale {scale_m_per_px * 1e3:.4f} mm/px)", meta={"pen_up_recorded": False})


# ================================================================== writing: UNIPEN train_r01_v07 (research only)
UNIPEN_ROOT = RAW_DIR / "unipen" / "unipen" / "CDROM" / "train_r01_v07"


def _unipen_text(path: str) -> str:
    return open(path, encoding="latin-1", errors="replace").read()


def _unipen_resolve(rel: str) -> str:
    return str(UNIPEN_ROOT / "include" / rel)


def unipen_file(path: str) -> Optional[Dict]:
    """Parse one UNIPEN .dat file with its .INCLUDE files: the header keys (rate, resolution, device) and the pen
    components (PEN_DOWN / PEN_UP blocks) with the .SEGMENT labels.  Writers' names are never kept."""
    txt = _unipen_text(path)
    inc = re.findall(r"^\.INCLUDE\s+(\S+)", txt, flags=re.M)
    head = ""
    body = txt
    for rel in inc:
        p = _unipen_resolve(rel)
        if os.path.exists(p):
            s = _unipen_text(p)
            if ".PEN_DOWN" in s or ".PEN_UP" in s:
                body = s + "\n" + body
            else:
                head += s + "\n"
    allt = head + "\n" + body

    def key(k, cast=float):
        m = re.search(rf"^\.{k}\s+([-\d.eE+]+)", allt, flags=re.M)
        return cast(m.group(1)) if m else None
    pps = key("POINTS_PER_SECOND")
    xmm = key("X_POINTS_PER_MM")
    xin = key("X_POINTS_PER_INCH")
    res = xmm if xmm else (xin / 25.4 if xin else None)
    if not pps or not res:
        return None
    ymm = key("Y_POINTS_PER_MM")
    yin = key("Y_POINTS_PER_INCH")
    yres = ymm if ymm else (yin / 25.4 if yin else res)
    comps = []                                  # (down: bool, points (n, >=2))
    for m in re.finditer(r"^\.(PEN_DOWN|PEN_UP)\s*\n(.*?)(?=^\.[A-Z_]+|\Z)", body, flags=re.M | re.S):
        pts = []
        for ln in m.group(2).splitlines():
            tok = ln.split()
            if len(tok) >= 2:
                try:
                    pts.append([float(tok[0]), float(tok[1])])
                except ValueError:
                    pass
        comps.append((m.group(1) == "PEN_DOWN", np.array(pts).reshape(-1, 2)))
    segs = []
    for m in re.finditer(r'^\.SEGMENT\s+(\S+)\s+([\d,\-\s]+?)\s+(\S+)?\s*"(.*)"', body, flags=re.M):
        segs.append({"level": m.group(1), "range": m.group(2).strip(), "quality": m.group(3), "label": m.group(4)})
    dev = re.search(r"Machine name:\s*(.*)", head)
    pen = re.search(r"Pen:\s*(.*)", head)
    return {"pps": pps, "res_x_per_mm": res, "res_y_per_mm": yres, "components": comps, "segments": segs,
            "device": dev.group(1).strip() if dev else "", "pen": pen.group(1).strip() if pen else "",
            "coord": _first(r"^\.COORD\s+(.*)", allt)}


def _first(pat: str, s: str) -> str:
    m = re.search(pat, s, flags=re.M)
    return m.group(1).strip() if m else ""


def _range_ids(r: str) -> List[int]:
    out = []
    for part in r.replace(" ", "").split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def unipen_segments(categories: Sequence[str] = ("8",), level: str = "TEXT", max_files: Optional[int] = None,
                    min_down_s: float = 1.0) -> Iterator[WritingRec]:
    """Labelled segments (text lines or words) with their pen-down components, in metres and seconds.  UNIPEN counts
    components from 0 over PEN_DOWN and PEN_UP blocks alike; pen-up blocks carry the in-air trajectory where the
    device recorded it.  Coordinates keep the device's y direction (flipped when the header says y grows down is
    not documented here: kinematics are sign-free)."""
    k = 0
    for cat in categories:
        for path in sorted(glob.glob(str(UNIPEN_ROOT / "data" / cat / "**" / "*.dat"), recursive=True)):
            f = unipen_file(path)
            if f is None:
                continue
            comps = f["components"]
            for si, sg in enumerate(f["segments"]):
                if sg["level"] != level:
                    continue
                ids = [i for i in _range_ids(sg["range"]) if i < len(comps)]
                if not ids:
                    continue
                xs, ts, dn, st = [], [], [], []
                t0 = 0.0
                ns = 0
                for i in ids:
                    down, P = comps[i]
                    if len(P) < 2:
                        continue
                    tt = t0 + np.arange(len(P)) / f["pps"]
                    t0 = tt[-1] + 1.0 / f["pps"]
                    xs.append(P / np.array([f["res_x_per_mm"], f["res_y_per_mm"]]) * 1e-3)
                    ts.append(tt)
                    dn.append(np.full(len(P), down))
                    st.append(np.full(len(P), ns if down else -1))
                    ns += int(down)
                if not xs:
                    continue
                down = np.concatenate(dn)
                if down.sum() / f["pps"] < min_down_s:
                    continue
                rel = os.path.relpath(path, UNIPEN_ROOT / "data")
                yield WritingRec(rid=f"unipen/{rel}#{si}", source="unipen", writer=os.path.dirname(rel) + "/" + os.path.basename(rel)[:-4],
                                 text=sg["label"], t=np.concatenate(ts), xy=np.vstack(xs), down=down,
                                 char=-np.ones(len(down), int), stroke=np.concatenate(st), fs=f["pps"],
                                 units="m (documented resolution)",
                                 meta={"device": f["device"], "pen": f["pen"], "category": cat,
                                       "res_x_per_mm": f["res_x_per_mm"], "pps": f["pps"],
                                       "contributor": rel.split("/")[1] if "/" in rel else rel, "timing": "sample index / points per second "
                                       "(pen-up time between blocks is not recorded where no PEN_UP points exist)"})
                k += 1
                if max_files and k >= max_files:
                    return
