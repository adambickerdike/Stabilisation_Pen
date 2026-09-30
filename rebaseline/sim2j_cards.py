"""Task 2: sim2j's headline cards under causal sensing (SIMULATION, sim2 / MuJoCo with the Rev J pen; synthetic v2
writers and synthetic essential tremor; nothing measured).

The historical headline (results/sim2j/cards.json, docs/revJ_simulation.md 6.1): Rev J with the guarded tracker G4 on the
ET test grid, 8-12 Hz x 1-2 mm, test writers 0-5 on their first test seed (24 cases): ink error 0.63 of the ordinary
pen's, words read 77 -> 100 %, letters 79 -> 94 %.  It ran sim2's nib servo with the exact simulator velocity, the
immediate true ball force as the servo's contact gate, a 400 Hz inner loop and an immediate firmware contact flag.

Modes (one per process; the mode is a runtime configuration of the imported, unmodified sim2j):
  causal        the current defaults: causal Hall velocity (timestamped differences, 300 Hz filter, stale-feedback
                cut), the delayed measured refill-slide contact as the servo's gate, the 80 Hz inner loop; the firmware
                sees the delayed contact channel (sim2j/sensing.py as now)
  legacy_flags  the labelled optimistic flags on the current code: velocity_source='legacy_true',
                contact_source='legacy_force', inner_hz=400; everything else as now (including the firmware's delayed
                contact channel, which no flag restores)
  legacy_exact  legacy_flags plus the historical firmware contact channel (the slide read every 2 kHz tick with no
                delay, sim2j/sensing.py at 4ad62b6), restored by a runtime substitution of OnlineSensors.read in this
                process.  It must reproduce the historical rows exactly; it is a reproduction check, not a design.
Same writers, cells and seeds as the historical run (paired): writer w, seed = sim2j.run_study.et_seeds(w)[0].
Controllers: 'none' (the Rev J pen with the nose held centred by its servo: the ordinary-pen column), 'nose' (G4, the
frozen tracker of results/sim2j/rules.json), 'oracle' (perfect knowledge of the handle's tremor: the mechanism limit);
tremor-free writing with G4 against the device-off run of the same seed (the clean-writing change, rule <= 25 um).
The writer's adapted hand path is re-learned on each pen model (the historical protocol: the writer has learned the
pen); the legacy modes reproduce the historical adaptation exactly (checked against sim2j/build/setups, read-only).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import BUILD_DIR, REPO_ROOT
from . import common as CM

MODES: Dict[str, Dict] = {
    "causal": {"nose": {}, "firmware_contact": "delayed (current sim2j/sensing.py)", "setups": "causal",
               "label": "causal Hall velocity, delayed measured contact, 80 Hz inner loop (current defaults)"},
    "legacy_flags": {"nose": {"velocity_source": "legacy_true", "inner_hz": 400.0, "contact_source": "legacy_force"},
                     "firmware_contact": "delayed (current sim2j/sensing.py)", "setups": "legacy",
                     "label": "legacy optimistic flags on current code: true velocity, true-force gate, 400 Hz inner"},
    "legacy_exact": {"nose": {"velocity_source": "legacy_true", "inner_hz": 400.0, "contact_source": "legacy_force"},
                     "firmware_contact": "historical immediate (runtime substitution of OnlineSensors.read)",
                     "setups": "legacy",
                     "label": "legacy flags + the historical firmware contact channel: the exact reproduction"},
}
HEADLINE_CELLS: Tuple[Tuple[float, float], ...] = ((8.0, 1.0e-3), (8.0, 2.0e-3), (12.0, 1.0e-3), (12.0, 2.0e-3))
OTHER_CELLS: Tuple[Tuple[float, float], ...] = ((4.0, 0.3e-3), (4.0, 1.0e-3), (4.0, 2.0e-3), (8.0, 0.3e-3),
                                                (12.0, 0.3e-3))
CTLS = ("none", "nose", "oracle")
WRITERS = (0, 1, 2, 3, 4, 5)
HIST_ROWS = REPO_ROOT / "sim2j" / "build" / "et_rows.json"          # read-only (git-ignored historical rows)
HIST_CARDS = REPO_ROOT / "results" / "sim2j" / "cards.json"          # committed historical cards
HIST_SETUPS = REPO_ROOT / "sim2j" / "build" / "setups"               # read-only
SOURCES = ("sim2/sim.py", "sim2/params.py", "sim2/hall_velocity.py", "sim2/contact_sensor.py", "sim2j/et.py",
           "sim2j/revj.py", "sim2j/stepper.py", "sim2j/sensing.py", "sim2j/firmware.py", "sim2j/akf_online.py",
           "sim2j/tasks.py", "sim2j/writers.py", "results/sim2j/rules.json", "results/revJ/sim_params.json",
           "results/revJ/layout.json", "rebaseline/sim2j_cards.py", "rebaseline/common.py")
_INSTALLED: Dict[str, str] = {}


# ------------------------------------------------------------------ mode installation (runtime, this process only)
def _historical_contact_read(orig):
    """sim2j/sensing.py OnlineSensors.read at 4ad62b6 set the firmware's contact flag from the slide reading of the SAME
    tick (every 2 kHz tick, threshold 0.1 mm above the front stop, no delay).  The current read samples the slide at
    1 kHz and delivers it 1 ms later.  This wrapper calls the current read (so every other state, and the shared noise
    buffer, advance exactly as now) and then restores the historical flag from the same noise draw (nz[8])."""
    def read(self, t):
        out = orig(self, t)
        nz = self._nb[self._ni - 1]                      # the noise row this tick used (the buffer refills before use)
        s = float(self.pm.d.qpos[self.js] + nz[8] * self.slide_noise)
        out["slide"] = s
        out["contact"] = bool(s > self.pm.m.jnt_range[self.j_refill, 0] + 0.1e-3)
        out.pop("contact_t", None)
        return out
    read.__wrapped_historical__ = True
    return read


def install(mode: str) -> Dict:
    """Configure the imported sim2j for one mode.  A process runs one mode only."""
    if mode not in MODES:
        raise KeyError(mode)
    if _INSTALLED and _INSTALLED.get("mode") != mode:
        raise RuntimeError(f"this process already runs mode {_INSTALLED['mode']}; one mode per process")
    import sim2j.et as ET
    import sim2j.sensing as SE
    ET.BUILD = str(BUILD_DIR / "sim2j" / MODES[mode]["setups"])     # adapted hand paths: never sim2j/build
    if mode == "legacy_exact" and not getattr(SE.OnlineSensors.read, "__wrapped_historical__", False):
        SE.OnlineSensors.read = _historical_contact_read(SE.OnlineSensors.read)
    _INSTALLED["mode"] = mode
    return {"mode": mode, "setup_cache": ET.BUILD, **{k: v for k, v in MODES[mode].items() if k != "setups"}}


def pen_models(mode: str, quick: bool = False):
    import sim2j.et as ET
    import sim2j.revj as RJ
    over = MODES[mode]["nose"]

    class Pens(ET.PenModels):
        def get(self, pen: str = "base"):
            if pen not in self.pms:
                cfg = RJ.config(heel=True, endcap=(pen == "endcap"), **self.kw)
                if over:
                    cfg = cfg.replace(nose=replace(cfg.nose, **over))
                self.pms[pen] = RJ.build(cfg)
            return self.pms[pen]
    return Pens()


_SEED_INDEX = {"i": 0}


def first_seed(w: int) -> int:
    """The case's test seed: sim2j.run_study.et_seeds(w)[0] (the historical cards), or et_seeds(w)[1] when a run is
    started with --seed-index 1 (the second seed, never run historically; its rows go to their own file)."""
    from sim2j import TEST_SEEDS
    return int(TEST_SEEDS[w % 4] if _SEED_INDEX["i"] == 0 else TEST_SEEDS[(w + 2) % 4])


def cell_key(f0: float, amp: float, w: int, seed: int, ctl: str) -> str:
    return f"{f0:g}|{amp * 1e3:g}|{w}|{seed}|{ctl}"


def _servo_info(r) -> Dict:
    sf = (r.info or {}).get("servo_feedback") or {}
    return {"servo_version": sf.get("version"), "stale_or_warmup_ticks": sf.get("stale_or_warmup_ticks"),
            "copper_energy_J": sf.get("copper_energy_J"), "online_sensor_version": (r.info or {}).get("online_sensor_version")}


def _setup_check(su, mode: str) -> Dict:
    """Setup record: adaptation history, clean floor, hand-path hash; legacy modes: equality with sim2j's own cache."""
    import hashlib
    hp = np.ascontiguousarray(su.case.hand_path)
    out = {"adapt_hist_um": list(su.adapt_hist), "clean_floor": su.clean_floor,
           "hand_path_sha256_16": hashlib.sha256(hp.tobytes()).hexdigest()[:16]}
    try:
        cache = Path(su._cache_path(3))
        hist = HIST_SETUPS / cache.name
        if hist.exists():
            z = np.load(hist)
            out["historical_setup_file"] = f"sim2j/build/setups/{cache.name}"
            out["max_abs_diff_to_historical_hand_path_um"] = float(np.max(np.abs(z["hand_path"] - hp)) * 1e6)
    except Exception as e:                                   # informative only
        out["historical_setup_check_error"] = repr(e)
    return out


def run_writer(mode: str, w: int, cells: Sequence[Tuple[float, float]], rows: CM.Rows, pens, ctls=CTLS,
               clean: bool = True, log=CM.log) -> None:
    import sim2j.et as ET
    seed = first_seed(w)
    need = [cell_key(f0, amp, w, seed, c) for f0, amp in cells for c in ctls]
    if clean:
        need.append(f"clean|{w}|{seed}|nose")
    if all(rows.has(k) for k in need) and rows.has(f"setup|{w}"):
        return
    t0 = time.time()
    su = ET.WriterSetup(w, pens, log=log)
    if not rows.has(f"setup|{w}"):
        rows.put(f"setup|{w}", dict(_setup_check(su, mode), kind="setup", w=w, setup_s=time.time() - t0), save=True)
    if clean and not rows.has(f"clean|{w}|{seed}|nose"):
        m = ET.run_case(su, "nose", 0.0, 0.0, seed, keep=True)
        r = m.pop("_r")
        m.update(_servo_info(r), kind="clean", ctl="nose", mode=mode)
        rows.put(f"clean|{w}|{seed}|nose", m, save=True)
        del r
        log(f"[{mode}] w{w} s{seed} clean nose: moved {m['moved_vs_clean_um']:.1f} um, P {m['P_total_W']:.2f} W")
    for f0, amp in cells:
        keys = {c: cell_key(f0, amp, w, seed, c) for c in ctls}
        if all(rows.has(k) for k in keys.values()):
            continue
        rn = ET.run_case(su, "none", f0, amp, seed, keep=True, record=True)
        r_none = rn.pop("_r")
        rn.update(_servo_info(r_none), kind="tremor", ctl="none", mode=mode)
        rows.put(keys["none"], rn)
        for c in ctls:
            if c == "none":
                continue
            m = ET.run_case(su, c, f0, amp, seed, ref_none=r_none, keep=True)
            r = m.pop("_r")
            m.update(_servo_info(r), kind="tremor", ctl=c, mode=mode, none_ink_err_um=rn["ink_err_um"],
                     ratio=m["ink_err_um"] / max(rn["ink_err_um"], 1e-9))
            rows.put(keys[c], m)
            del r
        del r_none
        rows.save()
        log(f"[{mode}] w{w} s{seed} {f0:g} Hz {amp * 1e3:g} mm: " + ", ".join(
            f"{c} {rows.get(k)['ink_err_um']:.0f} um" + (f" ({rows.get(k)['ratio']:.3f})" if c != "none" else "")
            for c, k in keys.items()) + f"  [{time.time() - t0:.0f} s]")
    rows.save()


SEVERE_CELLS: Tuple[Tuple[float, float], ...] = ((5.0, 3.0e-3), (8.0, 3.0e-3))
AUTOWRITE_CONDITIONS: Tuple[Tuple[float, float], ...] = ((8.0, 0.0), (8.0, 1.0e-3), (5.0, 2.0e-3), (8.0, 2.0e-3),
                                                         (5.0, 3.0e-3), (8.0, 3.0e-3))
HIST_AW_ROWS = REPO_ROOT / "sim2j" / "build" / "autowrite_rows.json"   # read-only


def run_severe(mode: str, w: int, rows: CM.Rows, pens, log=CM.log) -> None:
    """sim2j.run_study.stage_autowrite's severe block (3 mm at 5 and 8 Hz, writing through it): the ordinary pen, G4
    and perfect knowledge, keys 'sev|w|seed|f0|amp|ctl' as the historical rows (the heel wheel is not rerun)."""
    import sim2j.et as ET
    seed = first_seed(w)
    su = None
    for f0, amp in SEVERE_CELLS:
        keys = {c: f"sev|{w}|{seed}|{f0:g}|{amp * 1e3:g}|{c}" for c in CTLS}
        if all(rows.has(k) for k in keys.values()):
            continue
        su = su or ET.WriterSetup(w, pens, log=log)
        t0 = time.time()
        rn = ET.run_case(su, "none", f0, amp, seed, keep=True)
        r_none = rn.pop("_r")
        rows.put(keys["none"], dict(rn, **_servo_info(r_none), task="severe", kind="severe", ctl="none", mode=mode))
        for c in ("nose", "oracle"):
            m = ET.run_case(su, c, f0, amp, seed, ref_none=r_none, keep=True)
            r = m.pop("_r")
            m.update(_servo_info(r), task="severe", kind="severe", ctl=c, mode=mode,
                     ratio=m["ink_err_um"] / max(rn["ink_err_um"], 1e-9))
            rows.put(keys[c], m)
            del r
        del r_none
        rows.save()
        log(f"[{mode}] severe w{w} {f0:g} Hz 3 mm: none {rn['ink_err_um']:.0f} um ({rn['words_app']:.2f}), nose "
            f"{rows.get(keys['nose'])['ink_err_um']:.0f} ({rows.get(keys['nose'])['words_app']:.2f}), oracle "
            f"{rows.get(keys['oracle'])['ink_err_um']:.0f} [{time.time() - t0:.0f} s]")


def run_autowrite(mode: str, w: int, rows: CM.Rows, pens, log=CM.log) -> None:
    """sim2j.run_study.stage_autowrite's autowrite block: the nose writes the known text (nose2 planner, pen lift) in
    2.5 mm letters while the hand sweeps, 8 Hz tremor of 0/1 mm and 5/8 Hz of 2/3 mm; keys 'aw|w|seed|f0|amp'."""
    import sim2j.stepper as ST
    import sim2j.tasks as TK
    from sim2j.firmware import FWConfig
    pm = pens.get("base")
    seed = first_seed(w)
    ac = None
    for f0, amp in AUTOWRITE_CONDITIONS:
        key = f"aw|{w}|{seed}|{f0:g}|{amp * 1e3:g}"
        if rows.has(key):
            continue
        ac = ac or TK.AutowriteCase(w, h_mm=2.5, version="v2")
        if not ac.ok:
            rows.put(key, {"w": w, "plan_ok": False, "amp_mm": amp * 1e3, "f0": f0, "task": "autowrite", "mode": mode})
            continue
        scn = ac.scenario(f0, amp, seed)
        fw = FWConfig(nose="autowrite", pen_lift="plan", seed=seed, reach=pm.cfg.geom.travel)
        t0 = time.time()
        r = ST.run(pm, scn, fw, ac.task(), seed=seed)
        m = ac.metrics(r)
        m.update(_servo_info(r), w=w, seed=seed, f0=f0, amp_mm=amp * 1e3, plan_ok=True, ctl="autowrite",
                 task="autowrite", kind="autowrite", mode=mode, wall_s=time.time() - t0)
        rows.put(key, m, save=True)
        del r
        log(f"[{mode}] autowrite w{w} {f0:g} Hz {amp * 1e3:g} mm: ink {m['ink_err_um']:.0f} um, letters "
            f"{m['letters_read']:.2f}, words {m['words_app']:.2f}, P {m['P_total_W']:.2f} W [{m['wall_s']:.0f} s]")


def run(mode: str, writers: Sequence[int] = WRITERS, phase: str = "headline", quick: bool = False, log=CM.log,
        seed_index: int = 0) -> Dict:
    info = install(mode)
    _SEED_INDEX["i"] = int(seed_index)
    rows = CM.Rows(f"sim2j_{mode}" + ("" if seed_index == 0 else "_seed2"), quick=quick)
    pens = pen_models(mode, quick)
    t0 = time.time()
    if phase in ("severe", "autowrite"):
        for w in (tuple(writers)[:1] if quick else writers):
            (run_severe if phase == "severe" else run_autowrite)(mode, int(w), rows, pens, log=log)
    else:
        cells = {"headline": HEADLINE_CELLS, "other": OTHER_CELLS, "all": HEADLINE_CELLS + OTHER_CELLS}[phase]
        ctls = CTLS
        if quick:
            writers, cells, ctls = tuple(writers)[:1], ((8.0, 1.0e-3),), ("none", "nose")
        for w in writers:
            run_writer(mode, int(w), cells, rows, pens, ctls=ctls, log=log)
    rows.save()
    info.update({"writers": list(writers), "phase": phase, "wall_s": time.time() - t0, "n_rows": len(rows.rows)})
    log(f"[{mode}] done: {info}")
    return info


# ------------------------------------------------------------------ summaries (pure functions on rows)
def _sel(rows: List[Dict], ctl: str, fn) -> List[Dict]:
    return [r for r in rows if r.get("kind") == "tremor" and r.get("ctl") == ctl and fn(r)]


CARD_SEL = {
    "et_mild": ("Essential tremor, mild (0.3 mm, 4-12 Hz)", lambda r: abs(r["amp_mm"] - 0.3) < 1e-6),
    "et_moderate": ("Essential tremor, moderate (1 mm, 8-12 Hz)", lambda r: abs(r["amp_mm"] - 1.0) < 1e-6 and r["f0"] >= 8),
    "et_strong": ("Essential tremor, strong (2 mm, 8-12 Hz)", lambda r: abs(r["amp_mm"] - 2.0) < 1e-6 and r["f0"] >= 8),
    "slow_4hz": ("Slow tremor (4 Hz, 1-2 mm)", lambda r: r["amp_mm"] > 0.5 and r["f0"] < 5),
    "headline_8_12Hz_1_2mm": ("Headline pool: 8-12 Hz x 1-2 mm", lambda r: r["amp_mm"] > 0.5 and r["f0"] >= 8),
}


def card(rows: List[Dict], sel) -> Optional[Dict]:
    """One results card as sim2j/report.py cards_data defines it (means over the cases run), plus the ratio's case and
    writer-cluster bootstrap intervals, the perfect-knowledge limit and power."""
    n = _sel(rows, "none", sel)
    d = _sel(rows, "nose", sel)
    o = _sel(rows, "oracle", sel)
    if not n or not d:
        return None
    mean = lambda L, k, sc=1.0: CM.mean_or_none(r.get(k) * sc for r in L if r.get(k) is not None)   # noqa: E731
    ratios = [r["ratio"] for r in d]
    out = {"n_cases": len(d), "n_writers": len({r["w"] for r in d}),
           "words_of_10": [mean(n, "words_app", 10), mean(d, "words_app", 10)],
           "letters_of_10": [mean(n, "letters_read", 10), mean(d, "letters_read", 10)],
           "err_mm": [mean(n, "ink_err_um", 1e-3), mean(d, "ink_err_um", 1e-3)],
           "ratio_mean": CM.mean_or_none(ratios),
           "ratio_case_boot": CM.boot_mean(ratios),
           "ratio_writer_boot": CM.cluster_boot_mean(ratios, [r["w"] for r in d]),
           "ratio_worse_share": float(np.mean(np.array(ratios) > 1.0)),
           "P_total_W": [mean(n, "P_total_W"), mean(d, "P_total_W")],
           "P_nose_W": [mean(n, "P_nose_W"), mean(d, "P_nose_W")]}
    if o:
        out["oracle_ratio_mean"] = CM.mean_or_none(r["ratio"] for r in o)
        out["oracle_words_of_10"] = mean(o, "words_app", 10)
        out["oracle_P_total_W"] = mean(o, "P_total_W")
    return out


def summarise_mode(rows: List[Dict]) -> Dict:
    cards = {cid: dict(card(rows, sel) or {}, who=who) for cid, (who, sel) in CARD_SEL.items() if card(rows, sel)}
    cl = [r for r in rows if r.get("kind") == "clean" and r.get("ctl") == "nose"]
    clean = {"n": len(cl), "moved_um_mean": CM.mean_or_none(r["moved_vs_clean_um"] for r in cl),
             "moved_um_max": max((r["moved_vs_clean_um"] for r in cl), default=None),
             "P_total_W_mean": CM.mean_or_none(r["P_total_W"] for r in cl),
             "words_of_10": CM.mean_or_none(r["words_app"] * 10 for r in cl)}
    by_cell = {}
    for r in rows:
        if r.get("kind") != "tremor":
            continue
        k = f"{r['f0']:g} Hz x {r['amp_mm']:g} mm"
        by_cell.setdefault(k, {}).setdefault(r["ctl"], []).append(r)
    cells = {}
    for k, v in sorted(by_cell.items()):
        cells[k] = {c: {"n": len(L), "ink_err_um": CM.mean_or_none(x["ink_err_um"] for x in L),
                        "ratio": CM.mean_or_none(x.get("ratio") for x in L) if c != "none" else None,
                        "words_of_10": CM.mean_or_none(x["words_app"] * 10 for x in L),
                        "letters_of_10": CM.mean_or_none(x["letters_read"] * 10 for x in L),
                        "P_total_W": CM.mean_or_none(x["P_total_W"] for x in L)} for c, L in v.items()}
    stale = [r.get("stale_or_warmup_ticks") for r in rows if r.get("stale_or_warmup_ticks") is not None]
    cards.update(severe_autowrite_cards(rows))
    return {"cards": cards, "clean_writing": clean, "by_cell": cells,
            "stale_or_warmup_ticks_max": max(stale) if stale else None,
            "writers": sorted({r["w"] for r in rows if "w" in r and r.get("kind") in ("tremor", "clean")})}


def severe_autowrite_cards(rows: List[Dict]) -> Dict:
    """sim2j/report.py's severe_through, severe_autowrite and autowrite_no_tremor cards (means over the cases run)."""
    out = {}
    mean = lambda L, k, sc=1.0: CM.mean_or_none(r.get(k) * sc for r in L if r.get(k) is not None)   # noqa: E731
    sev = [r for r in rows if r.get("task") == "severe"]
    sn = [r for r in sev if r["ctl"] == "none"]
    sd = [r for r in sev if r["ctl"] == "nose"]
    so = [r for r in sev if r["ctl"] == "oracle"]
    aw = [r for r in rows if r.get("task") == "autowrite" and r.get("plan_ok")]
    a3 = [r for r in aw if abs(r["amp_mm"] - 3.0) < 1e-6]
    a0 = [r for r in aw if r["amp_mm"] == 0.0]
    if sn and sd:
        ratios = [r["ratio"] for r in sd]
        out["severe_through"] = {"who": "Severe tremor (3 mm, 5 and 8 Hz), writing through it", "n_cases": len(sd),
                                 "words_of_10": [mean(sn, "words_app", 10), mean(sd, "words_app", 10)],
                                 "letters_of_10": [mean(sn, "letters_read", 10), mean(sd, "letters_read", 10)],
                                 "err_mm": [mean(sn, "ink_err_um", 1e-3), mean(sd, "ink_err_um", 1e-3)],
                                 "ratio_mean": CM.mean_or_none(ratios), "ratio_case_boot": CM.boot_mean(ratios),
                                 "ratio_writer_boot": CM.cluster_boot_mean(ratios, [r["w"] for r in sd]),
                                 "oracle_ratio_mean": CM.mean_or_none(r["ratio"] for r in so) if so else None,
                                 "oracle_words_of_10": mean(so, "words_app", 10) if so else None,
                                 "P_total_W": [mean(sn, "P_total_W"), mean(sd, "P_total_W")]}
    if sn and a3:
        out["severe_autowrite"] = {"who": "Severe tremor (3 mm, 5 and 8 Hz), known text: the pen writes it", "n_cases": len(a3),
                                   "words_of_10": [mean(sn, "words_app", 10), mean(a3, "words_app", 10)],
                                   "letters_of_10": [mean(sn, "letters_read", 10), mean(a3, "letters_read", 10)],
                                   "err_mm": [mean(sn, "ink_err_um", 1e-3), mean(a3, "ink_err_um", 1e-3)],
                                   "err_kind": "ordinary pen: to the clean ink; autowrite: to the planned letters",
                                   "q_max_mm": mean(a3, "q_max_mm"), "P_total_W": mean(a3, "P_total_W")}
    if a0:
        out["autowrite_no_tremor"] = {"who": "A known text, no tremor: the pen writes it", "n_cases": len(a0),
                                      "words_of_10": [None, mean(a0, "words_app", 10)],
                                      "letters_of_10": [None, mean(a0, "letters_read", 10)],
                                      "err_mm": [None, mean(a0, "ink_err_um", 1e-3)], "P_total_W": mean(a0, "P_total_W")}
    if aw:
        by = {}
        for r in aw:
            by.setdefault(f"{r['f0']:g} Hz x {r['amp_mm']:g} mm", []).append(r)
        out["autowrite_by_condition"] = {k: {"n": len(v), "words_of_10": mean(v, "words_app", 10),
                                             "letters_of_10": mean(v, "letters_read", 10),
                                             "ink_err_um": mean(v, "ink_err_um"), "q_max_mm": mean(v, "q_max_mm"),
                                             "at_reach": mean(v, "at_reach"), "P_total_W": mean(v, "P_total_W")}
                                         for k, v in sorted(by.items())}
    return out


def paired(rows_a: Dict[str, Dict], rows_b: Dict[str, Dict], sel=None, kinds=("tremor",)) -> Dict:
    """Case-by-case differences (a - b) over the keys both have (rows of the given kinds; 'none', 'nose', 'oracle',
    'autowrite')."""
    out = {}
    for ctl in ("none", "nose", "oracle", "autowrite"):
        diffs_r, diffs_w, diffs_e, ws = [], [], [], []
        for k, ra in rows_a.items():
            if ra.get("kind") not in kinds or ra.get("ctl") != ctl or k not in rows_b:
                continue
            if ra.get("ink_err_um") is None or rows_b[k].get("ink_err_um") is None:
                continue
            if sel is not None and not sel(ra):
                continue
            rb = rows_b[k]
            if ctl != "none" and ra.get("ratio") is not None and rb.get("ratio") is not None:
                diffs_r.append(ra["ratio"] - rb["ratio"])
            diffs_w.append(10 * (ra["words_app"] - rb["words_app"]))
            diffs_e.append(ra["ink_err_um"] - rb["ink_err_um"])
            ws.append(ra["w"])
        if diffs_e:
            out[ctl] = {"n": len(diffs_e),
                        "ratio_diff": CM.cluster_boot_mean(diffs_r, ws) if diffs_r else None,
                        "words_of_10_diff": CM.cluster_boot_mean(diffs_w, ws),
                        "ink_err_um_diff": CM.cluster_boot_mean(diffs_e, ws),
                        "exactly_equal_ink_share": float(np.mean(np.abs(np.array(diffs_e)) < 1e-9))}
    return out


def historical_rows() -> Dict[str, Dict]:
    """sim2j/build/et_rows.json and autowrite_rows.json (git-ignored; read-only).  Empty in a clean clone: the
    committed cards then stand in."""
    out = {}
    if HIST_ROWS.exists():
        d = json.loads(HIST_ROWS.read_text())
        out.update({k: v for k, v in d.items() if v.get("ctl") in ("none", "nose", "oracle")})
    if HIST_AW_ROWS.exists():
        d = json.loads(HIST_AW_ROWS.read_text())
        out.update({k: dict(v, kind=v.get("task")) for k, v in d.items()
                    if v.get("task") == "autowrite" or (v.get("task") == "severe" and v.get("ctl") in CTLS)})
    return out


def summarise(quick: bool = False, write: bool = True) -> Dict:
    hist = historical_rows()
    mode_rows = {m: CM.Rows(f"sim2j_{m}", quick=quick).rows for m in MODES}
    body = {"what": ("sim2j's headline results cards rerun: Rev J (C1S nose) + the frozen guarded tracker G4, H1 hand, "
                     "v2 test writers 0-5 on their first test seed, essential tremor (stabpen model) on the historical "
                     "grid; paired with the historical rows (same writers, cells and seeds)"),
            "evidence": ("SIMULATION (sim2 / MuJoCo 3.6 with the Rev J PROPOSED DESIGN parameters; synthetic writers and "
                         "synthetic tremor); sensing mode per block; ranks concepts only (COU-1), not evidence of "
                         "benefit to people"),
            "modes": {m: {k: v for k, v in MODES[m].items() if k != "setups"} for m in MODES},
            "historical": {"source_rows": "sim2j/build/et_rows.json (read-only)" if hist else None,
                           "source_cards": "results/sim2j/cards.json",
                           "summary": summarise_mode(list(hist.values())) if hist else None,
                           "committed_cards": {c["id"]: c for c in (CM.jload(HIST_CARDS) or {}).get("cards", [])}},
            "by_mode": {}, "paired": {}}
    for m, R in mode_rows.items():
        if not R:
            continue
        body["by_mode"][m] = summarise_mode(list(R.values()))
        body["by_mode"][m]["setups"] = {k: v for k, v in R.items() if k.startswith("setup|")}
        body["by_mode"][m]["wall_s_total"] = float(sum(r.get("wall_s") or 0.0 for r in R.values()))
    s2 = CM.Rows("sim2j_causal_seed2", quick=quick).rows
    if s2:
        both = list(mode_rows.get("causal", {}).values()) + list(s2.values())
        body["causal_second_seed"] = {"summary": summarise_mode(list(s2.values())),
                                      "both_seeds_headline": card(both, CARD_SEL["headline_8_12Hz_1_2mm"][1]),
                                      "note": "the second test seed of each writer (never run historically): new cases, "
                                              "not paired with history"}
    hsel = CARD_SEL["headline_8_12Hz_1_2mm"][1]
    pairs = {"causal_vs_legacy_flags": ("causal", "legacy_flags"), "legacy_flags_vs_historical": ("legacy_flags", None),
             "legacy_exact_vs_historical": ("legacy_exact", None), "causal_vs_historical": ("causal", None)}
    for name, (a, b) in pairs.items():
        ra = mode_rows.get(a) or {}
        rb = (mode_rows.get(b) or {}) if b else hist
        if ra and rb:
            body["paired"][name] = {"all_cells": paired(ra, rb), "headline_cells": paired(ra, rb, hsel),
                                    "severe_and_autowrite": paired(ra, rb, kinds=("severe", "autowrite"))}
    if write and not quick:
        seeds = sorted({first_seed(w) for w in WRITERS})
        CM.write_result("sim2j_cards", body, body["evidence"], inputs=SOURCES, seeds=seeds,
                        parameters={"writers": list(WRITERS), "seed_rule": "sim2j.run_study.et_seeds(w)[0]",
                                    "headline_cells": [list(c) for c in HEADLINE_CELLS],
                                    "other_cells": [list(c) for c in OTHER_CELLS], "controllers": list(CTLS),
                                    "dt_s": 50e-6, "text": "return library", "pre_rest_s": 4.0})
    return body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=list(MODES))
    ap.add_argument("--phase", choices=("headline", "other", "all", "severe", "autowrite"), default="headline")
    ap.add_argument("--writers", default=",".join(map(str, WRITERS)))
    ap.add_argument("--seed-index", type=int, default=0, choices=(0, 1))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args(argv)
    if a.mode:
        run(a.mode, [int(x) for x in a.writers.split(",") if x.strip()], a.phase, a.quick, seed_index=a.seed_index)
    if a.summarise:
        s = summarise(quick=a.quick)
        print(json.dumps({m: v["cards"].get("headline_8_12Hz_1_2mm") for m, v in s["by_mode"].items()}, indent=1,
                         default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
