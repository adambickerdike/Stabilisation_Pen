r"""Task 2: constrained multi-objective search over the balanced-nib family (NSGA-II written here; CALCULATION).

Genes (continuous; categorical genes are floor(x n) of a gene in [0, 1)):
  reach 1.0-2.0 mm, body OD 20-26 mm, pole side (fraction of what the bore allows), magnet thickness 1.5-5 mm, grade
  {N52, N48SH}, layout {single array + keeper, double array}, second array's thickness fraction, iron {1010, Hiperco
  50A}, copper stack 0.8-2.6 mm, sublayer order {xy, xyyx}, fill {0.45 etched flex, 0.55 bonded round wire, 0.65 bonded
  rectangular wire}, racetrack bundle 0.8-3.2 mm, row centre and leg position (fractions of the pole pitch), coil
  resistance 2-12 ohm, wire set {4 x 0.10, 8 x 0.10, 4 x 0.08, 8 x 0.08 mm}, wire length 26-50 mm, anchor stiffness
  50-10,000 N/m (below about 50 N/m the lead's flex cable alone would exceed the budget: the pass allotted it 23 N/m), race preload 0.3-4 N, ball diameter 0.8-1.5 mm, carrier tube {Ti, CFRP}, flange {Ti, Al with hard
  inserts}, flange thickness 1.0-1.5 mm and radius (0.65-1.0 of what the bore allows), board {14 mm (study K), 10 mm
  repackaged}, rear race {full ring (study K / the pass: the leads pass inside it), pads (one pad per ball, the leads
  pass between them on the ball circle; their envelope then takes the main board's place over the leads, so the board
  moves behind the counter-face head: +22.8 mm of length)}.
Objectives (minimised): -reach; worst-case copper loss (the pass's screen with the matched loads, weakest point x 0.7,
  coil at the temperature it would reach); typical-duty copper loss (duty A, weakest point x 0.7); OD; length.
Constraints (evaluate.constraints): Goodman >= 1.5 at the stop, worst tolerance corner; Hertz <= 3.33 GPa for the
  sustained writing load and 3.67 GPa for a drop (ISO 76's 4.2 GPa at the static rating with s0 2 and 1.5); lowest mode >= 2.5 x 40 Hz ball free and stuck; coil clearance >= 0.2 mm at the stop (99th
  percentile); skin <= 41 degC (severe duty at 35 deg, 30 degC room); coil, magnets, guide, wires, board and
  counter-face head inside the body; length <= 175 mm; 3.3 V headroom at the peak force; lead heating <= 45 K; guide
  preload >= 1.2 x the preload at which a ball first unloads under the 35 deg couple (added after the NSGA-II archives in
  nibopt/build/ were computed: the archives carry every other constraint, the refined candidates carry this one too;
  the guide's drag is under 1 % of the typical loss, so the floor moves the front by well under 1 %).
Constraint handling: Deb's rules (feasible first, then smaller normalised violation).  Every evaluated point is kept;
the front is read off the pooled feasible points.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import BUILD
from . import evaluate as E
from . import magnet as M
from . import params as P
from .design import Design
from .params import val

GENES = [
    ("reach_mm", 1.0, 2.0), ("od_mm", 20.0, 26.0), ("w_frac", 0.55, 1.0), ("t_m_mm", 1.5, 5.0), ("grade", 0, 1),
    ("layout", 0, 1), ("t_m2_frac", 0.3, 1.0), ("iron", 0, 1), ("t_cu_mm", 0.8, 2.6), ("order", 0, 1), ("fill", 0, 1),
    ("b_mm", 0.8, 3.2), ("yc_frac", 0.75, 1.15), ("leg_frac", 0.6, 1.2), ("R_coil_log", math.log(2.0), math.log(12.0)),
    ("wireset", 0, 1), ("L_w_mm", 26.0, 50.0), ("K_a_log", math.log10(50.0), 4.0), ("preload_N", 0.3, 4.0),
    ("ball_d_mm", 0.8, 1.5), ("carrier", 0, 1), ("flange", 0, 1), ("flange_t_mm", 1.0, 1.5), ("board", 0, 1),
    ("flange_frac", 0.65, 1.0), ("race", 0, 1),
]
NAMES = [g[0] for g in GENES]
LO = np.array([g[1] for g in GENES], float)
HI = np.array([g[2] for g in GENES], float)
CAT = {"grade": ["N52", "N48SH"], "layout": ["single", "double"], "iron": ["1010", "Hiperco50A"], "order": ["xy", "xyyx"],
       "fill": [0.45, 0.55, 0.65], "wireset": [(4, 0.10), (8, 0.10), (4, 0.08), (8, 0.08)], "carrier": ["Ti", "CFRP"],
       "flange": ["Ti", "Al"], "board": [False, True], "race": ["ring", "pads"]}
LABELS = {"fill": {0.45: "etched flex coil (ASSUMPTION)", 0.55: "bonded round wire (study B / K)",
                   0.65: "bonded rectangular wire (ASSUMPTION)"}}


def _cat(name: str, x: float):
    opts = CAT[name]
    return opts[min(int(x * len(opts)), len(opts) - 1)]


def decode(x: np.ndarray) -> Dict:
    g = {n: float(v) for n, v in zip(NAMES, x)}
    for n in CAT:
        g[n] = _cat(n, g[n])
    g["R_coil"] = math.exp(g["R_coil_log"])
    g["K_a"] = 10 ** g["K_a_log"]
    return g


def build(x: np.ndarray, name: str = "opt") -> Tuple[Optional[Design], Dict]:
    """Genes -> a Design (None if the winding cannot fit), with the reason (PROPOSED DESIGN)."""
    g = decode(x)
    r = g["reach_mm"]
    stop = r + val(P.MECH["stop_margin_mm"])
    bore = g["od_mm"] / 2 - val(P.THERMAL["wall_mm"])
    e = (val(P.MECH["R_carrier_mm"]) + stop + 0.3) / math.sqrt(2.0)
    w_max = (bore - 0.2) / math.sqrt(2.0) - e
    if w_max < 1.5:
        return None, {"reason": "no room for the poles"}
    w = g["w_frac"] * w_max
    c = w / 2 + e
    Br = val(P.KM["grades"])[g["grade"]]["Br_T"]
    double = g["layout"] == "double"
    mag = M.Magnets(w=w * 1e-3, e=e * 1e-3, t_m=g["t_m_mm"] * 1e-3, t_cu=g["t_cu_mm"] * 1e-3, Br=Br, double=double,
                    t_m2=(g["t_m2_frac"] * g["t_m_mm"] * 1e-3) if double else 0.0)
    rmax = bore - stop - val(P.MECH["c_run_mm"])
    b = g["b_mm"]
    yc = g["yc_frac"] * c
    x_in = g["leg_frac"] * c - b / 2
    y_min = val(P.MECH["R_carrier_mm"]) + 0.1
    if x_in < 0.3 or x_in + b >= rmax:
        return None, {"reason": "legs outside the bore or across the carrier"}
    y_in = min(math.sqrt(max(rmax ** 2 - (x_in + b) ** 2, 0.0)) - yc - b, yc - b - y_min)
    if y_in < 0.15:
        return None, {"reason": "no racetrack fits between the carrier and the bore"}
    coil = M.Coil(x_in * 1e-3, y_in * 1e-3, b * 1e-3, yc * 1e-3, g["order"], g["fill"])
    n_w, d_w = g["wireset"]
    ball_d = round(g["ball_d_mm"] * 10) / 10
    flange_r = g["flange_frac"] * (bore - stop - 0.3)
    ball_c = flange_r - stop / 2 - ball_d / 2 - 0.2
    race_w = stop + ball_d + 0.4
    w_min = val(P.MECH["refill_r_mm"]) + stop + 0.6
    if g["race"] == "ring":
        w_maxc = ball_c - race_w / 2 - stop - d_w / 2 - 0.3
        wc = 0.5 * (w_min + w_maxc)
    else:
        wc = ball_c                    # the leads pass between the rear race's pads, on the ball circle
    n_balls = 6 if g["race"] == "ring" else max(6, n_w)
    d = Design(name, "nibopt NSGA-II", r, g["od_mm"], mag, coil, grade=g["grade"], iron=g["iron"], R_coil=g["R_coil"],
               n_w=n_w, d_w_mm=d_w, L_w_mm=g["L_w_mm"], K_a=g["K_a"], T0=0.005, parallel=max(1, n_w // 4),
               wire_circle_mm=wc, guide_circle_mm=ball_c, preload_N=g["preload_N"], ball_d_mm=ball_d, n_balls=n_balls,
               race_topology=g["race"],
               flange_r_mm=flange_r, flange_t_mm=g["flange_t_mm"], carrier_mat=g["carrier"],
               flange_mat="Ti" if g["flange"] == "Ti" else "Al", board_narrow=g["board"],
               notes={"genes": {k: (v if not isinstance(v, (np.floating,)) else float(v)) for k, v in g.items()}})
    if g["flange"] == "Al":
        d.notes["flange_inserts_g"] = 0.10
    return d, {"reason": None}


SCALES = {"goodman": 0.5, "hertz_run": 0.5, "hertz_static": 1.0, "preload": 0.5, "modes": 10.0, "coil_p99": 0.1, "skin": 2.0,
          "coil_inner": 0.1, "magnets": 0.2, "wires_min": 0.3, "wires_max": 0.3, "head": 0.5, "board": 1.0,
          "length": 5.0, "voltage": 0.5, "lead_heat": 10.0, "magnet_T": 5.0}


def score(x: np.ndarray, fine: bool = False) -> Dict:
    """Objectives, violation and the key numbers of one gene vector (CALC)."""
    d, why = build(x)
    if d is None:
        return {"x": x.tolist(), "ok": False, "reason": why["reason"], "F": [0.0, 10.0, 10.0, 30.0, 300.0], "V": 1e3}
    try:
        ev = E.evaluate(d, fine=fine, full=False)
    except Exception as exc:  # pragma: no cover - a numerical failure is an infeasible point, recorded
        return {"x": x.tolist(), "ok": False, "reason": f"evaluation failed: {exc}", "F": [0.0, 10.0, 10.0, 30.0, 300.0],
                "V": 1e3}
    c = ev["constraints"]
    V = sum((1e3 if not np.isfinite(c[k]) else max(0.0, -c[k]) / SCALES[k]) for k in SCALES if k in c)
    extra = 0.0
    F = [-d.reach_mm, ev["screen"]["worst07"], ev["dutyA"]["worst07"]["mean"], d.od_mm, d.length_mm()]
    if not all(np.isfinite(F)):
        return {"x": x.tolist(), "ok": False, "reason": "non-finite objective", "F": [0.0, 10.0, 10.0, 30.0, 300.0], "V": 1e3}
    return {"x": x.tolist(), "ok": True, "F": F, "V": V, "feasible": V <= 0.0,
            "m_move_g": d.m_move_g() + extra, "sv_min": ev["magnetics"]["sv_min_workspace_N_sqrtW"],
            "severe_P35_W": ev["severe"]["worst07"]["P35_W"], "skin_C": ev["severe"]["worst07"]["skin"]["max_shell_C"],
            "severe_mean_W": ev["severe"]["worst07"]["mean"], "goodman": ev["wires"]["goodman_worst_corner"],
            "constraints": {k: float(v) for k, v in c.items() if k != "feasible"}}


# ------------------------------------------------------------------------------------------------ NSGA-II
def _dominates(a: Dict, b: Dict) -> bool:
    if a["V"] <= 0 and b["V"] > 0:
        return True
    if a["V"] > 0 and b["V"] > 0:
        return a["V"] < b["V"]
    if a["V"] > 0:
        return False
    fa, fb = np.array(a.get("Fo", a["F"])), np.array(b.get("Fo", b["F"]))
    return bool(np.all(fa <= fb) and np.any(fa < fb))


def _fronts(pop: List[Dict]) -> List[List[int]]:
    n = len(pop)
    S = [[] for _ in range(n)]
    cnt = np.zeros(n, int)
    fronts = [[]]
    for i in range(n):
        for j in range(n):
            if i != j:
                if _dominates(pop[i], pop[j]):
                    S[i].append(j)
                elif _dominates(pop[j], pop[i]):
                    cnt[i] += 1
        if cnt[i] == 0:
            fronts[0].append(i)
    k = 0
    while fronts[k]:
        nxt = []
        for i in fronts[k]:
            for j in S[i]:
                cnt[j] -= 1
                if cnt[j] == 0:
                    nxt.append(j)
        k += 1
        fronts.append(nxt)
    return fronts[:-1]


def _crowding(pop: List[Dict], idx: List[int]) -> Dict[int, float]:
    d = {i: 0.0 for i in idx}
    if len(idx) <= 2:
        return {i: float("inf") for i in idx}
    F = np.array([pop[i].get("Fo", pop[i]["F"]) for i in idx])
    for m in range(F.shape[1]):
        order = np.argsort(F[:, m])
        span = F[order[-1], m] - F[order[0], m]
        d[idx[order[0]]] = d[idx[order[-1]]] = float("inf")
        if span <= 0:
            continue
        for k in range(1, len(idx) - 1):
            d[idx[order[k]]] += (F[order[k + 1], m] - F[order[k - 1], m]) / span
    return d


def _sbx(p1, p2, rng, eta=15.0):
    u = rng.random(len(p1))
    beta = np.where(u <= 0.5, (2 * u) ** (1 / (eta + 1)), (1 / (2 * (1 - u))) ** (1 / (eta + 1)))
    c1 = 0.5 * ((1 + beta) * p1 + (1 - beta) * p2)
    c2 = 0.5 * ((1 - beta) * p1 + (1 + beta) * p2)
    swap = rng.random(len(p1)) < 0.5
    return np.where(swap, c1, c2), np.where(swap, c2, c1)


def _mutate(x, rng, eta=20.0, pm=None):
    pm = 1.0 / len(x) if pm is None else pm
    y = x.copy()
    for i in range(len(x)):
        if rng.random() < pm:
            u = rng.random()
            d = (2 * u) ** (1 / (eta + 1)) - 1 if u < 0.5 else 1 - (2 * (1 - u)) ** (1 / (eta + 1))
            y[i] = y[i] + d * (HI[i] - LO[i])
    return np.clip(y, LO, HI - 1e-12)


def seeds() -> List[np.ndarray]:
    """Gene vectors near study K's and the pass's designs (a head start, not a constraint): leg and row positions from
    their coils (x_in + b / 2 and yc over the pole pitch c)."""
    base = {"w_frac": 0.95, "t_m_mm": 3.5, "grade": 0.0, "layout": 0.0, "t_m2_frac": 0.5, "iron": 0.0, "t_cu_mm": 1.6,
            "order": 0.0, "fill": 0.5, "b_mm": 2.2, "yc_frac": 1.0, "leg_frac": 0.7, "R_coil_log": math.log(2.5),
            "wireset": 0.3, "L_w_mm": 30.0, "K_a_log": 2.0, "preload_N": 1.5, "ball_d_mm": 1.0, "carrier": 0.0,
            "flange": 0.0, "flange_t_mm": 1.5, "board": 0.0, "flange_frac": 1.0, "race": 0.0}
    specs = [dict(reach_mm=1.0587, od_mm=24.0, L_w_mm=30.0, b_mm=2.6, leg_frac=0.81, yc_frac=0.99, order=0.75),
             dict(reach_mm=1.5, od_mm=24.0, L_w_mm=34.0, b_mm=2.2, leg_frac=0.67, yc_frac=0.96),
             dict(reach_mm=1.0587, od_mm=20.0, L_w_mm=30.0, b_mm=1.7, leg_frac=0.65, yc_frac=1.04, order=0.75, board=0.75),
             dict(reach_mm=1.25, od_mm=24.0, L_w_mm=32.0, b_mm=2.2, leg_frac=0.7, yc_frac=1.0),
             dict(reach_mm=2.0, od_mm=26.0, L_w_mm=40.0, b_mm=1.8, leg_frac=0.65, yc_frac=0.96),
             dict(reach_mm=1.5, od_mm=22.0, L_w_mm=34.0, b_mm=1.8, leg_frac=0.65, yc_frac=1.0, board=0.75)]
    out = []
    for sp in specs:
        g = dict(base, **sp)
        out.append(np.clip(np.array([g[n] for n in NAMES], float), LO, HI - 1e-9))
    return out


def nsga2(pop_size: int = 64, gens: int = 60, seed: int = 7, pool=None, archive_path=None, log=print,
          bounds: Optional[Dict[str, Tuple[float, float]]] = None, objectives: Tuple[int, ...] = (0, 1, 2, 3, 4)) -> Dict:
    """NSGA-II with Deb's constraint rules; bounds narrow genes (e.g. a fixed reach), objectives pick F columns."""
    global LO, HI
    LO0, HI0 = LO.copy(), HI.copy()
    if bounds:
        LO, HI = LO.copy(), HI.copy()
        for k, (a, b) in bounds.items():
            i = NAMES.index(k)
            LO[i], HI[i] = a, max(b, a + 1e-9)
    try:
        return _nsga2(pop_size, gens, seed, pool, archive_path, log, objectives)
    finally:
        LO, HI = LO0, HI0


def _nsga2(pop_size, gens, seed, pool, archive_path, log, objectives) -> Dict:
    rng = np.random.default_rng(seed)
    X = [LO + rng.random(len(LO)) * (HI - LO) for _ in range(pop_size - 6)] + [np.clip(s, LO, HI - 1e-12) for s in seeds()]
    archive: List[Dict] = []

    def evaluate_all(xs):
        if pool is not None:
            res = pool.map(score, xs, chunksize=max(1, len(xs) // 8))
        else:
            res = [score(x) for x in xs]
        archive.extend(res)
        for r in res:
            r["Fo"] = [r["F"][k] for k in objectives]
        return res
    t0 = time.time()
    pop = evaluate_all(X)
    for gen in range(gens):
        fr = _fronts(pop)
        rank = {}
        crowd = {}
        for k, f in enumerate(fr):
            for i in f:
                rank[i] = k
            crowd.update(_crowding(pop, f))

        def tour():
            i, j = rng.integers(len(pop), size=2)
            if rank[i] != rank[j]:
                return pop[i] if rank[i] < rank[j] else pop[j]
            return pop[i] if crowd[i] >= crowd[j] else pop[j]
        kids = []
        while len(kids) < pop_size:
            a, b = np.array(tour()["x"]), np.array(tour()["x"])
            if rng.random() < 0.9:
                a, b = _sbx(a, b, rng)
            kids.append(_mutate(np.clip(a, LO, HI - 1e-12), rng))
            kids.append(_mutate(np.clip(b, LO, HI - 1e-12), rng))
        kid_res = evaluate_all(kids[:pop_size])
        union = pop + kid_res
        fr = _fronts(union)
        new = []
        for f in fr:
            if len(new) + len(f) <= pop_size:
                new.extend(f)
            else:
                cd = _crowding(union, f)
                new.extend(sorted(f, key=lambda i: -cd[i])[:pop_size - len(new)])
                break
        pop = [union[i] for i in new]
        nf = sum(1 for p in pop if p["V"] <= 0)
        if log and (gen % 5 == 0 or gen == gens - 1):
            best = [p for p in pop if p["V"] <= 0]
            msg = f"gen {gen:3d}  feasible in pop {nf:3d}/{pop_size}  archive {len(archive)}  {time.time() - t0:.0f} s"
            if best:
                msg += f"  max reach {max(-p['F'][0] for p in best):.2f} mm"
            log(msg)
        if archive_path is not None and gen % 10 == 9:
            archive_path.write_text(json.dumps({"archive": archive}, default=float))
    return {"pop": pop, "archive": archive, "seconds": time.time() - t0, "pop_size": pop_size, "gens": gens, "seed": seed}


def pareto(points: List[Dict], obj=(0, 1, 2, 3, 4)) -> List[Dict]:
    feas = [p for p in points if p.get("ok") and p["V"] <= 0]
    out = []
    F = np.array([[p["F"][k] for k in obj] for p in feas]) if feas else np.zeros((0, len(obj)))
    for i, p in enumerate(feas):
        dom = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        if not dom.any():
            out.append(p)
    return out
