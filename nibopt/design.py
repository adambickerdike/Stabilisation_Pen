r"""One record per nib design, the four designs of the reconciliation, and the builder the optimiser uses (PROPOSED
DESIGN; derived quantities CALCULATION).

A design is the moving-coil checkerboard actuator (nibopt/magnet.py), straight C17200 wire leads on a preloaded ball
thrust guide (nibopt/suspension.py; the flexure alternatives are screened there), and the pen around it.  Masses and
lengths follow study K's layout conventions (revk/layout.py, results/revK/layout.json):

  moving mass  refill 0.84 g + holder 0.05 g + carrier tube (3.2 / 2.5 mm, from z 9 mm to the flange) + two rolling
               guide stations 0.06 g + coils (copper + 0.1 g of formers) + flange (a disc from 2.6 mm to the flange
               diameter, 1.5 mm thick, 70 % solid, study K's rule) + position magnet 7.5 mg; reproduces study K's 3.44 g
  stator       back plate and keeper (discs to the bore - 0.3 mm, thickness from a flux rule) + magnets
  length       study K's 145.13 mm + the actuator stack's change + the guide stack's change + any wire length beyond
               study K's 26.8 mm (the pass's convention: the refill holder and the head move back with the anchor)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace, asdict
from typing import Dict, Optional

from . import magnet as M
from . import params as P
from .params import val


@dataclass
class Design:
    name: str
    source: str
    reach_mm: float                 # usable radius (the workspace disk)
    od_mm: float                    # body outside diameter where the actuator sits
    mag: M.Magnets
    coil: M.Coil
    grade: str = "N52"
    iron: str = "1010"
    R_coil: float = 2.5             # ohm per axis at 20 degC
    n_w: int = 4
    d_w_mm: float = 0.10
    L_w_mm: float = 26.801
    K_a: float = 10000.0            # axial anchor stiffness incl. cable (N/m)
    T0: float = 0.005               # assembly tension (N, total)
    parallel: int = 1               # wires per coil lead
    wire_circle_mm: float = 5.5
    guide_circle_mm: float = 8.3
    preload_N: float = 4.0          # internal preload per race
    ball_d_mm: float = 0.8
    n_balls: int = 6
    flange_r_mm: Optional[float] = None
    race_topology: str = "ring"     # 'ring': full rear race, wires inside it; 'pads': one pad per ball, wires between
    flange_t_mm: float = 1.5
    flange_solid: float = 0.7       # study K's lightening factor
    carrier_mat: str = "Ti"
    flange_mat: str = "Ti"
    t_plate_mm: Optional[float] = None   # back plate and keeper thickness (None: flux rule)
    board_narrow: bool = False
    weight_trim: bool = False
    m_move_override_g: Optional[float] = None
    length_override_mm: Optional[float] = None
    notes: Dict = field(default_factory=dict)

    # ------------------------------------------------------------------------------------------ geometry
    @property
    def stop_mm(self) -> float:
        return self.reach_mm + val(P.MECH["stop_margin_mm"])

    @property
    def bore_mm(self) -> float:
        return self.od_mm / 2 - val(P.THERMAL["wall_mm"])

    @property
    def flange_radius_mm(self) -> float:
        if self.flange_r_mm is not None:
            return self.flange_r_mm
        return self.bore_mm - self.stop_mm - 0.3

    def plate_t_mm(self) -> float:
        """Back plate and keeper thickness from the flux rule: one pole's flux (the face field ~ Br t_m / (t_m + G)
        over w^2) shared by its two neighbours through a section w x t at the working density of the iron (CALC)."""
        if self.t_plate_mm is not None:
            return self.t_plate_mm
        g = self.mag
        G = g.c0 + g.t_cu + g.c1
        B_face = g.Br * (g.t_m + (g.t_m2 if g.double else 0)) / (g.t_m + (g.t_m2 if g.double else 0) + G)
        phi = B_face * g.w ** 2
        B_work = val(P.MECH["B_plate_T"])[self.iron]
        return max(0.6, phi / (2 * g.w * B_work) * 1e3)

    def stack_mm(self) -> float:
        g = self.mag
        return 2 * self.plate_t_mm() + g.D * 1e3

    def guide_stack_mm(self) -> float:
        return 0.3 + self.ball_d_mm + self.flange_t_mm + self.ball_d_mm + 0.3

    def flange_z(self):
        z0 = val(P.PEN["actuator_z0_mm"]) + self.stack_mm() + 0.3 + self.ball_d_mm
        return z0, z0 + self.flange_t_mm

    def rear_shift_mm(self) -> float:
        """How far the flange and everything behind it move relative to study K's layout (may be negative)."""
        return (self.stack_mm() - val(P.PEN["actuator_stack_K_mm"])) + (self.guide_stack_mm() - val(P.PEN["guide_stack_K_mm"]))

    def length_mm(self) -> float:
        if self.length_override_mm is not None:
            return self.length_override_mm
        L = val(P.PEN["length_K_mm"]) + self.holder_extension_mm()
        if self.race_topology == "pads":
            L += 22.8                    # the main board moves behind the head (the leads' envelope takes its place)
        elif self.board_narrow:
            L += 22.8 * (14.0 / 10.0 - 1.0)
        if self.bore_mm < 10.0:
            L += 4.0          # the cue LRA moves behind the cell (the cell can no longer sit 3 mm off axis)
        return L

    # ------------------------------------------------------------------------------------------ masses
    def moving_parts_g(self) -> Dict[str, float]:
        rho = {"Ti": val(P.MECH["Ti_rho"]), "CFRP": val(P.MECH["CFRP_rho"]), "Al": val(P.MECH["Al_rho"])}
        z1 = self.flange_z()[1]
        tube_len = z1 + 0.5 - 9.0
        tube = math.pi / 4 * (3.2 ** 2 - 2.5 ** 2) * tube_len * rho[self.carrier_mat] * 1e-6
        Rf = self.flange_radius_mm
        flange = math.pi / 4 * ((2 * Rf) ** 2 - 2.6 ** 2) * self.flange_t_mm * rho[self.flange_mat] * 1e-6 * self.flange_solid
        active, _ = M.sublayer_z(self.mag, self.coil)
        A = self.coil.b * active * (len(self.coil.order) // 2)
        m_cu = 2 * 2 * M.CU_DENS * self.coil.k_fill * A * self.coil.l_mean * 1e3
        wires = self.n_w * val(P.MECH["C17200"])["rho"] * math.pi / 4 * (self.d_w_mm * 1e-3) ** 2 * self.L_w_mm * 1e-3 * 1e3 / 3
        ext = self.holder_extension_mm() * val(P.MECH["holder_ext_g_per_mm"])
        return {"refill": 0.84, "refill_holder": 0.05, "holder_extension": ext, "carrier_tube": tube,
                "guide_stations": 0.06, "coils": m_cu + 0.10, "flange": flange,
                "flange_inserts": self.notes.get("flange_inserts_g", 0.0), "position_magnet": 0.0075, "wires_third": wires}

    def holder_extension_mm(self) -> float:
        """The counter-face head and the refill holder move back when the wire anchor does (a longer actuator stack,
        guide or wire; the pass's convention for the wire); the refill's own rear end fixes how far forward the head
        can sit, so a shorter stack saves nothing (PROPOSED DESIGN)."""
        return max(0.0, self.rear_shift_mm() + self.L_w_mm - val(P.PEN["wire_K_mm"]))

    def couple_lever_mm(self) -> float:
        return val(P.LOADS["couple_lever_mm"]) + self.holder_extension_mm()

    def m_move_g(self) -> float:
        if self.m_move_override_g is not None:
            return self.m_move_override_g
        return sum(self.moving_parts_g().values())

    def stator_parts_g(self) -> Dict[str, float]:
        g = self.mag
        t = self.plate_t_mm()
        rho = val(P.MECH["Fe_rho"]) if self.iron == "1010" else val(P.MECH["Hiperco_rho"])
        d0 = 2 * (self.bore_mm - 0.3)
        d_in = 2 * (val(P.MECH["R_carrier_mm"]) + self.stop_mm + 0.3)
        plate = math.pi / 4 * (d0 ** 2 - d_in ** 2) * t * rho * 1e-6
        return {"back_plate": plate, "keeper": plate, "magnets": g.mass_kg * 1e3}

    def summary(self) -> Dict:
        mp = self.moving_parts_g()
        return {"name": self.name, "source": self.source, "reach_mm": self.reach_mm, "stop_mm": self.stop_mm,
                "od_mm": self.od_mm, "bore_mm": self.bore_mm, "length_mm": self.length_mm(),
                "m_move_g": self.m_move_g(), "moving_parts_g": mp, "stator_parts_g": self.stator_parts_g(),
                "stack_mm": self.stack_mm(), "plate_t_mm": self.plate_t_mm(),
                "magnets_mm": {"w": self.mag.w * 1e3, "e": self.mag.e * 1e3, "t_m": self.mag.t_m * 1e3,
                               "t_cu": self.mag.t_cu * 1e3, "c0": self.mag.c0 * 1e3, "c1": self.mag.c1 * 1e3,
                               "Br_T": self.mag.Br, "double": self.mag.double, "t_m2": self.mag.t_m2 * 1e3},
                "coil_mm": {"x_in": self.coil.x_in * 1e3, "y_in": self.coil.y_in * 1e3, "b": self.coil.b * 1e3,
                            "yc": self.coil.yc * 1e3, "order": self.coil.order, "k_fill": self.coil.k_fill,
                            "outer_corner_r": self.coil.outer_radius * 1e3, "inner_edge": self.coil.inner_edge * 1e3},
                "grade": self.grade, "iron": self.iron, "R_coil_ohm": self.R_coil,
                "wires": {"n": self.n_w, "d_mm": self.d_w_mm, "L_mm": self.L_w_mm, "anchor_N_m": self.K_a,
                          "assembly_N": self.T0, "parallel_per_lead": self.parallel, "circle_mm": self.wire_circle_mm},
                "guide": {"circle_r_mm": self.guide_circle_mm, "preload_per_race_N": self.preload_N,
                          "ball_d_mm": self.ball_d_mm, "n_balls": self.n_balls, "flange_r_mm": self.flange_radius_mm,
                          "rear_race": self.race_topology},
                "flange_t_mm": self.flange_t_mm,
                "carrier_mat": self.carrier_mat, "flange_mat": self.flange_mat, "board_narrow": self.board_narrow,
                "weight_trim": self.weight_trim, "notes": self.notes}


# ------------------------------------------------------------------------------------------------ the four designs
def _e_for(stop_mm: float) -> float:
    return (val(P.MECH["R_carrier_mm"]) + stop_mm + 0.3) / math.sqrt(2.0) * 1e-3


def rev_k() -> Design:
    """Rev K's B1 as study K laid it out (results/revK/revK.json, layout.json): study B's poles, K's buildable coil in
    'xy' order, four 0.10 mm C17200 wires 26.8 mm on a 5.5 mm circle, anchor 'about 0.01 N/um', 2 x 6 balls on a
    16.6 mm circle at 4 N per race, flange 18.86 mm."""
    k = P.load_json("results/revK/revK.json")["nib"]
    gm = k["buildable_coil"]["geometry_mm"]
    reach = 1.058695965882101
    mag = M.Magnets(w=5.120275187158268e-3, e=_e_for(reach + 0.2), t_m=3.5e-3, t_cu=1.6e-3)
    coil = M.Coil(gm["X_in"] * 1e-3, gm["Y_in"] * 1e-3, gm["bundle_b"] * 1e-3, gm["row_centre_yc"] * 1e-3, "xy", 0.55)
    return Design("K_B1", "study K (results/revK/revK.json nib, layout.json)", reach, 24.0, mag, coil, R_coil=2.5,
                  n_w=4, d_w_mm=0.10, L_w_mm=26.801041139863813, K_a=10000.0, T0=0.005, parallel=1, wire_circle_mm=5.5,
                  guide_circle_mm=8.3, preload_N=4.0, ball_d_mm=0.8, flange_r_mm=18.86 / 2, t_plate_mm=1.4653,
                  m_move_override_g=k_moving_mass_g(),
                  notes={"anchor": "revk/layout.py: 'axially soft (about 0.01 N/um)' = 10,000 N/m",
                         "moving_mass": "study K's layout parts that move with the nib (results/revK/layout.json)"})


def k_moving_mass_g() -> float:
    lay = P.load_json("results/revK/layout.json")
    return float(sum(c.get("mass_g") or 0.0 for c in lay["components"] if c.get("moves_with") == "nib"))


def _pass_candidate(c: Dict, body: float, name: str, src: str, pass_mass_g: float) -> Design:
    sh, mg, w = c["coil"]["shape_m"], c["coil"]["magnet_geometry_m"], c["wire"]
    geom = c["geometry"]
    mag = M.Magnets(w=mg["w"], e=mg["e"], t_m=mg["t_m"], c0=mg["c0"], t_cu=mg["t_x"] + mg["t_y"], c1=mg["c1"], Br=mg["Br"])
    coil = M.Coil(sh["x_in"], sh["y_in"], sh["bundle"], sh["row_centre"], c["coil"]["order"], mg["k_fill"])
    return Design(name, src, geom["radius_mm"], body, mag, coil, R_coil=2.5, n_w=w["n_wires"], d_w_mm=w["diameter_mm"],
                  L_w_mm=float(w["length_mm"]), K_a=w["anchor_stiffness_N_m"], T0=w["assembly_tension_max_N"],
                  parallel=w["parallel_wires_per_lead"], wire_circle_mm=geom["wire_circle_mm"],
                  guide_circle_mm=geom["ball_circle_radius_mm"], preload_N=4.0, ball_d_mm=0.8,
                  flange_r_mm=geom["flange_radius_mm"], t_plate_mm=1.4653,
                  notes={"pass_moving_mass_g": pass_mass_g, "pass_length_mm": 145.1 + w["holder_and_body_extension_mm"]})


def pass_designs() -> Dict[str, Design]:
    st = P.load_json("results/improvement/mechanics/mechanics_study.json")
    cands = {round(c["radius_mm"], 4): c for c in st["candidates"]}
    c1 = cands[round(1.058695965882101, 4)]
    c15 = cands[1.5]
    cp = P.load_json("results/improvement/mechanics/compact_20mm.json")
    cp_c = {"coil": cp["coil"], "wire": cp["wire"], "geometry": cp["geometry"]}
    out = {
        "P_1059_24": _pass_candidate(c1, 24.0, "P_1059_24", "the pass, re-optimised 1.059 mm (mechanics_study.json)",
                                     c1["duty_by_residual"]["0.02"]["moving_mass_kg"] * 1e3),
        "P_150_24": _pass_candidate(c15, 24.0, "P_150_24", "the pass, 1.5 mm (mechanics_study.json)",
                                    c15["duty_by_residual"]["0.02"]["moving_mass_kg"] * 1e3),
        "P_1059_20": _pass_candidate(cp_c, 20.0, "P_1059_20", "the pass, 20 mm body / 1.059 mm (compact_20mm.json)",
                                     cp["duty_by_residual"]["0.02"]["moving_mass_kg"] * 1e3),
    }
    return out


def reconciliation_designs() -> Dict[str, Design]:
    d = {"K_B1": rev_k()}
    d.update(pass_designs())
    return d
