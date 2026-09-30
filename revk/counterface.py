r"""The counter-face head of Rev K (CALCULATION on a PROPOSED DESIGN; study B's principle, docs/balanced_nib.md s1).

Study B's principle: the ink spring pushes the refill's rear end through a face kept parallel to the paper, so the
paper's push on the ball and the face's push are parallel and opposite; a follower stop lets the face go when the ball
lifts.  Study B drew the face as a 6 mm disc with its spring and three positioners in 12 mm of the pen (z 71-83).  Rev K
has to make it follow the pen: the face must turn with the paper (its normal 15-55 deg from the pen axis, at any roll),
its position must follow the refill's rear end as the tilt makes the refill slide (6.7 mm over 35-75 deg with Rev K's
6.0 mm ring), and it must float over the tilt wobble of real writing (+-2.5 deg, LIT CON-02) without losing the balance.

The head (PROPOSED DESIGN):
  - a ROLL CAGE turning about the pen axis (+-30 deg: a SQL-RV-1.8 SQUIGGLE on a 5.5 mm crank; the page sensor already
    fixes the pen's down side within +-20 deg, REQ-RVJ-N06);
  - a TILT HINGE on the ring, its axis across the pen through the head centre O on the pen axis (15-55 deg: a second
    SQL-RV-1.8 on a crank);
  - the FACE (a 0.3 mm sapphire tray on a titanium bracket) at a distance L_O in front of O along the paper normal, so
    that turning the face with the tilt also carries it along the pen: the face's own geometry follows most of the
    refill's tilt-driven slide, and one SQL-RV-1.8 (6 mm of travel) is enough for the AXIAL FOLLOWER that moves the head;
  - a FLOAT: the face rides on a short parallel-strip flexure along its normal with a constant-force strip spring (the
    ink force F_n), between a front and a rear stop that sit a gap g either side of its writing position; the front stop
    is study B's follower stop;
  - a captive SHOE on the face: a 4 mm disc riding on three 0.5 mm Si3N4 balls on the sapphire, parallel to the face and
    under the tray's rim (0.1 mm clearance: no force while writing), with an asymmetric slotted socket for a 1.2 mm ball
    on a short stem from a vented PEEK cup that grips the plain rear end of any metal D1 refill.  The joint lets the
    refill lean 15-55 deg from the face normal; the face's push reaches the refill along the paper normal (the shoe is a
    free body on rolling balls).  The shoe pulls the refill back when the face retreats (the pen lift); the ball
    unsnaps and the shoe stays in the pen when the refill is pulled out (the refill change).  (A flange on the refill's
    own axis cannot run under a rim parallel to a face tilted 15-55 deg to it.)

Kinematics (pen frame: x away from the paper, y lateral, z from the ball tip at 50 deg toward the back).  Paper normal
n = (cos th cos psi, cos th sin psi, sin th) at tilt th and roll psi.  The puck ball centre C sits on the axis at the
refill's rear end, moved by the nib: C = (q_x, q_y, z_c) with z_c = z_c50 - (p(th) - p(50)) - (n . q) / sin th (the ball
stays on the paper); the face plane is n . (X - O) = -L_O + f (f: the float, + away from the paper); contact needs
n . (C - O) = -L_O - r_pb + f, i.e. f does not depend on the nib's correction (the refill end moves parallel to the face).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths
from . import params as PR
from .frontend import protrusion
from .params import val

ensure_paths()

D2R = math.pi / 180.0


def normal(th_deg: float, psi_deg: float = 0.0) -> np.ndarray:
    th, ps = th_deg * D2R, psi_deg * D2R
    return np.array([math.cos(th) * math.cos(ps), math.cos(th) * math.sin(ps), math.sin(th)])


class Head:
    """Head geometry for a ring R_s, a refill rear end at z_r50 (50 deg), a puck ball radius r_pb, a face offset L_O
    and a tilt-hinge offset x_h (the hinge line runs across the pen at x = x_h in the roll ring's frame, negative toward
    the paper: x_h = -R_s puts it on the paper-side generator, where the handle's ring touches the paper)."""

    def __init__(self, R_s: float, L_O: float, x_h: float = 0.0, z_r50: float = 67.0, r_pb: float = None,
                 puck_h: float = None):
        pk = val(PR.HEAD["puck"])
        self.R_s = R_s
        self.L_O = L_O
        self.x_h = x_h
        self.r_pb = pk["r_pb_mm"] if r_pb is None else r_pb
        self.puck_h = pk["h_mm"] if puck_h is None else puck_h
        self.z_r50 = z_r50
        self.z_c50 = z_r50 + self.puck_h - self.r_pb          # the puck ball's centre at 50 deg, nib centred
        self.p50 = protrusion(50.0, R_s)

    def z_c(self, th: float, q=(0.0, 0.0), psi: float = 0.0) -> float:
        n = normal(th, psi)
        return self.z_c50 - (protrusion(th, self.R_s) - self.p50) - (n[0] * q[0] + n[1] * q[1]) / math.sin(th * D2R)

    def z_O(self, th: float) -> float:
        """The follower's set point: float centred with the nib centred (CALC): n . (C - O) = -(L_O + r_pb)."""
        return self.z_c(th) + (self.L_O + self.r_pb - self.x_h * math.cos(th * D2R)) / math.sin(th * D2R)

    def O(self, z_O: float, psi: float = 0.0) -> np.ndarray:
        return np.array([self.x_h * math.cos(psi * D2R), self.x_h * math.sin(psi * D2R), z_O])

    def u_nominal(self, th: float) -> float:
        """Contact point along the face from the hinge's foot, nib centred (closed form, CALC)."""
        t = th * D2R
        return ((self.L_O + self.r_pb) * math.cos(t) - self.x_h) / math.sin(t)

    def contact(self, th: float, psi: float, q, z_O: float, th_face: Optional[float] = None) -> Dict:
        """Contact point in the face's own coordinates (u along the tilt direction from the foot of the hinge line, v
        lateral), the float f and the face-normal error, for the true tilt th and a face set for th_face (the wobble)."""
        thf = th if th_face is None else th_face
        n_true = normal(th, psi)
        n_f = normal(thf, psi)
        C = np.array([q[0], q[1], self.z_c(th, q, psi)])
        O = self.O(z_O, psi)
        P = C + self.r_pb * n_f
        f = float(n_f @ (C - O)) + self.L_O + self.r_pb
        F = O - self.L_O * n_f
        d = P - F
        d = d - (d @ n_f) * n_f
        e_v = np.array([-math.sin(psi * D2R), math.cos(psi * D2R), 0.0])
        e_u = np.cross(e_v, n_f)
        return {"u": float(d @ e_u), "v": float(d @ e_v), "f": f, "err_deg": math.degrees(math.acos(min(1.0, float(n_true @ n_f))))}

    def plate_points(self, th: float, u0: float, u1: float, w: float, back: float = 1.2, z_O: float = None) -> List:
        """Corners of the face plate (and its bracket, 'back' behind the face) at tilt th, roll 0 (the envelope is
        roll-invariant: the head turns with the roll ring) (CALC)."""
        n = normal(th)
        zO = self.z_O(th) if z_O is None else z_O
        F = self.O(zO) - self.L_O * n
        e_v = np.array([0.0, 1.0, 0.0])
        e_u = np.cross(e_v, n)
        pts = []
        for uu in (u0, u1):
            for vv in (-w / 2, w / 2):
                for b in (0.0, back):
                    pts.append(F + uu * e_u + vv * e_v + b * n)
        return pts


def _row(R_s: float, L_O: float, x_h: float, ths, angs) -> Dict:
    stop = val(PR.B1["stop_mm"])
    wob = val(PR.FRONT["tilt_wobble_deg"])
    lift = val(PR.HEAD["lift_mm"])
    F_n = val(PR.B1["F_n_N"])
    pk = val(PR.HEAD["puck"])
    h = Head(R_s, L_O, x_h)
    zO = np.array([h.z_O(t) for t in ths])
    us, vs, fs = [], [], []
    for t, z in zip(ths, zO):
        for a in angs:
            q = (stop * math.cos(a), stop * math.sin(a))
            c = h.contact(t, 0.0, q, z)
            us.append(c["u"])
            vs.append(c["v"])
        for dw in (-wob, wob):
            c = h.contact(min(max(t + dw, 20.0), 89.0), 0.0, (0.0, 0.0), z, th_face=t)
            fs.append(c["f"])
    f_amp = float(np.max(np.abs(fs)))
    g = f_amp + val(PR.HEAD["float_margin_mm"])
    lift_axial = max((g + lift) / math.sin(t * D2R) for t in ths)
    iso = val(PR.HEAD["refill_length_spread_mm"])
    need = float(zO.max() - zO.min()) + lift_axial + iso + 0.5
    u_lo, u_hi = float(min(us)), float(max(us))
    v_lo, v_hi = float(min(vs)), float(max(vs))
    fl = pk["shoe_d_mm"]
    u0, u1 = u_lo - fl / 2 - 0.7, u_hi + fl / 2 + 0.7               # tray clearance 0.2 + wall 0.5 each side
    w = (v_hi - v_lo) + fl + 0.4 + 1.0
    ub0 = min(u0, -1.0)                                               # the bracket reaches back to the hinge line
    rr, zz = [], []
    for t, z in zip(ths, zO):
        for P in h.plate_points(t, ub0, u1, w, z_O=z):
            rr.append(math.hypot(P[0], P[1]))
            zz.append(P[2])
    u_nom = [h.u_nominal(t) for t in ths]
    M = [F_n * abs(u) for u in us]
    M_res = F_n * (max(us) - min(us)) / 2.0
    return {"L_O_mm": float(L_O), "x_h_mm": float(x_h), "follower_range_mm": float(zO.max() - zO.min()),
            "zO_min_mm": float(zO.min()), "zO_max_mm": float(zO.max()),
            "u_range_mm": [u_lo, u_hi], "v_range_mm": [v_lo, v_hi], "u_nominal_mm": [min(u_nom), max(u_nom)],
            "face_length_needed_mm": u_hi - u_lo, "face_width_needed_mm": v_hi - v_lo,
            "plate_mm": {"u0": u0, "u1": u1, "length": u1 - u0, "width": w},
            "float_wobble_mm": f_amp, "gap_mm": g, "lift_axial_max_mm": lift_axial,
            "positioner_travel_needed_mm": need, "fits_one_SQL_RV_1p8": need <= val(PR.HEAD["pos_travel_mm"]),
            "swept_r_max_mm": max(rr), "swept_z_mm": [min(zz), max(zz)],
            "fits_bore": max(rr) <= val(PR.HEAD["head_bore_r_mm"]) - val(PR.FRONT["c_run_mm"]),
            "tilt_moment_max_Nmm": float(max(M)), "tilt_moment_residual_with_balance_spring_Nmm": M_res}


def sweep(R_s: float, quick: bool = False) -> Dict:
    """Head layouts over the face offset L_O and the hinge offset x_h: the follower's travel over 35-75 deg, the contact
    region on the face (nib at the stop, any direction), the float excursion from the tilt wobble, the plate's swept
    envelope against the bore, the tilt-hinge moment; the chosen head is the smallest face whose follower travel + lift
    + refill-length spread + 0.5 mm fits one SQL-RV-1.8 (6 mm) and whose plate stays 0.3 mm inside the bore (CALC)."""
    ths = np.linspace(35.0, 75.0, 9 if quick else 17)
    angs = np.linspace(0, 2 * math.pi, 8 if quick else 16, endpoint=False)
    rows = []
    xhs = (0.0, -2.0, -4.0, -5.0, -R_s, -7.0, -8.0, -9.0) if not quick else (0.0, -R_s, -8.0)
    spare = val(PR.HEAD["follower_spare_mm"])
    for x_h in xhs:
        for L_O in np.arange(-7.0, 8.01, 0.5 if not quick else 1.0):
            r = _row(R_s, float(L_O), float(x_h), ths, angs)
            r["keeps_spare_travel"] = r["positioner_travel_needed_mm"] <= val(PR.HEAD["pos_travel_mm"]) - spare
            rows.append(r)
    fit = [r for r in rows if r["keeps_spare_travel"] and r["fits_bore"]]
    best = None
    if fit:
        L_min = min(r["plate_mm"]["length"] for r in fit)
        near = [r for r in fit if r["plate_mm"]["length"] <= L_min + 0.5]
        best = min(near, key=lambda r: (r["follower_range_mm"], r["plate_mm"]["length"]))
    on_axis = [r for r in rows if r["x_h_mm"] == 0.0 and r["fits_one_SQL_RV_1p8"]]
    ref_axis = min(on_axis, key=lambda r: r["plate_mm"]["length"]) if on_axis else None
    return {"rows": rows, "chosen": best, "on_axis_hinge_best": ref_axis,
            "rule": "among heads whose follower travel + lift + refill-length spread + 0.5 mm leaves "
                    f"{spare:g} mm of one SQL-RV-1.8's 6 mm spare (MFR AMF-15) and whose swept plate stays 0.3 mm inside "
                    "the 11.0 mm bore: a plate within 0.5 mm of the shortest, then the smallest follower range (the "
                    "fewest follower moves when the tilt changes)",
            "closed_forms": {"u_nominal": "((L_O + r_pb) cos th - x_h) / sin th",
                             "z_O": "z_c(th) + (L_O + r_pb - x_h cos th) / sin th; constant when x_h = -R_s and "
                                    "L_O = -(r_b + r_pb): the hinge on the ring's paper-side generator turns the face about "
                                    "a line parallel to the one the pen tilts about, so the tilt needs no follower"},
            "label": "CALCULATION (kinematics; wobble LITERATURE CON-02; positioner MANUFACTURER AMF-15/106)"}


def design(R_s: float, quick: bool = False) -> Dict:
    """The chosen head: L_O, x_h, face size, float gap, the head's envelope and parts (PROPOSED DESIGN; CALC checks)."""
    sw = sweep(R_s, quick=quick)
    ch = sw["chosen"]
    pk = val(PR.HEAD["puck"])
    h = Head(R_s, ch["L_O_mm"], ch["x_h_mm"])
    pl = ch["plate_mm"]
    out = {"L_O_mm": ch["L_O_mm"], "x_h_mm": ch["x_h_mm"], "sweep": sw,
           "face": {"length_mm": pl["length"], "width_mm": pl["width"], "u0_mm": pl["u0"], "u1_mm": pl["u1"],
                    "contact_u_mm": ch["u_range_mm"], "contact_v_mm": ch["v_range_mm"],
                    "tray_len_mm": pl["length"] - 1.0, "tray_w_mm": pl["width"] - 1.0,
                    "facing": val(PR.HEAD["face_facing"])},
           "gap_mm": ch["gap_mm"], "float_wobble_mm": ch["float_wobble_mm"],
           "follower_range_mm": ch["follower_range_mm"], "follower_z_mm": [ch["zO_min_mm"], ch["zO_max_mm"]],
           "positioner_travel_needed_mm": ch["positioner_travel_needed_mm"],
           "tilt_moment_max_Nmm": ch["tilt_moment_max_Nmm"],
           "tilt_moment_residual_with_balance_spring_Nmm": ch["tilt_moment_residual_with_balance_spring_Nmm"],
           "swept_r_max_mm": ch["swept_r_max_mm"], "swept_z_mm": ch["swept_z_mm"],
           "hinge_angle_deg": [15.0, 55.0], "roll_range_deg": [-val(PR.HEAD["roll_range_deg"]), val(PR.HEAD["roll_range_deg"])],
           "z_c50_mm": h.z_c50, "z_r50_mm": h.z_r50,
           "refill_end_z_range_mm": [h.z_c(75.0) - (h.puck_h - h.r_pb), h.z_c(35.0) - (h.puck_h - h.r_pb)],
           "puck": pk}
    # the head's axial envelope: the swept plate and bracket, the roll ring (1.5 mm) in front, the positioners' rack
    # and the follower (SQL-RV-1.8 housing 6 mm + its screw's travel) behind, plus the lift stroke
    z0 = ch["swept_z_mm"][0] - 1.5
    z1 = ch["swept_z_mm"][1] + ch["lift_axial_max_mm"] + 1.0
    out["envelope_z_mm"] = [z0, z1]
    out["follower_motor_z_mm"] = [z1, z1 + 6.0 + 1.0]
    out["loads"] = actuator_loads(out)
    out["lift"] = pen_lift(out)
    out["positioner_power"] = positioner_power(out)
    out["ink_tail"] = ink_tail(out)
    return out


def actuator_loads(hd: Dict) -> Dict:
    """What each positioner must push (CALC): the tilt crank against F_n x u (the contact's distance from the hinge line
    along the face) less a torsion balance spring set to the mean moment, the roll pinion against F_n x v x cos th, the
    follower against the face spring's axial share F_n sin th during a lift; against the SQL-RV-1.8's 0.30 N stall
    (MANUFACTURER AMF-15)."""
    F_n = val(PR.B1["F_n_N"])
    stall = val(PR.HEAD["pos_stall_N"])
    r_crank = val(PR.HEAD["tilt_crank_mm"])
    r_pin = val(PR.HEAD["roll_crank_mm"])
    fr = val(PR.HEAD["hinge_friction_Nmm"])
    M_raw = hd["tilt_moment_max_Nmm"] + fr
    M_t = hd["tilt_moment_residual_with_balance_spring_Nmm"] + fr
    v_max = val(PR.B1["stop_mm"])
    M_r = F_n * v_max * math.cos(35 * D2R) + val(PR.HEAD["roll_bearing_friction_Nmm"])
    F_f = F_n * math.sin(75 * D2R) + 0.01
    return {"tilt": {"moment_Nmm": M_t, "crank_mm": r_crank, "force_N": M_t / r_crank, "margin_x": stall / (M_t / r_crank),
                     "without_balance_spring": {"moment_Nmm": M_raw, "force_N": M_raw / r_crank,
                                                "margin_x": stall / (M_raw / r_crank)},
                     "balance_spring_Nmm": hd["tilt_moment_max_Nmm"] - hd["tilt_moment_residual_with_balance_spring_Nmm"]},
            "roll": {"moment_Nmm": M_r, "crank_mm": r_pin, "force_N": M_r / r_pin, "margin_x": stall / (M_r / r_pin),
                     "travel_for_range_mm": 2 * math.radians(val(PR.HEAD["roll_range_deg"])) * r_pin,
                     "range_deg": [-val(PR.HEAD["roll_range_deg"]), val(PR.HEAD["roll_range_deg"])]},
            "follower": {"force_N": F_f, "margin_x": stall / F_f},
            "note": "the SQUIGGLE holds with zero power (AMF-15); its holding force against back-driving is not in the "
                    "datasheets seen: EXP-B22 measures it on the head",
            "label": "CALCULATION (statics; crank, pinion and balance spring PROPOSED DESIGN; stall MANUFACTURER AMF-15)"}


def _speed(F: float) -> float:
    """SQL-RV-1.8 speed under an axial load (mm/s): the straight line through > 7 mm/s at 15 gf (AMF-106) and the
    0.30 N stall (AMF-15); ASSUMPTION shape (EXP-B22 measures)."""
    stall = val(PR.HEAD["pos_stall_N"])
    v15 = val(PR.HEAD["pos_speed_15gf_mm_s"])
    return max(v15 * (stall - F) / (stall - 0.147), 0.0)


def pen_lift(hd: Dict) -> Dict:
    """The pen lift by the follower screw (DEC-050's first candidate) (CALC): the follower retracts the head along the
    pen; the float's front stop meets the face after g/sin th; the face, the puck and the refill then retreat together
    until the ball is 0.5 mm off the paper (the ring stays on the paper).  Stroke, force, time, energy per lift, holding
    energy (zero: the screw holds), and what it cannot do (a fast gated mode)."""
    F_n = val(PR.B1["F_n_N"])
    lift = val(PR.HEAD["lift_mm"])
    g = hd["gap_mm"]
    P_lo, P_hi = val(PR.HEAD["pos_power_W"])
    rows = []
    for t in (35.0, 50.0, 75.0):
        s = math.sin(t * D2R)
        free = g / s
        loaded = lift / s
        F = F_n * s + 0.01
        v0 = _speed(0.0)
        v1 = _speed(F)
        t_up = free / v0 + loaded / v1
        t_down = loaded / _speed(0.0) + free / v0                  # the spring helps on the way down
        rows.append({"tilt_deg": t, "stroke_axial_mm": free + loaded, "load_N": F, "time_up_s": t_up, "time_down_s": t_down,
                     "ink_stops_after_s": free / v0,
                     "energy_per_lift_J": [P_lo * (t_up + t_down), P_hi * (t_up + t_down)]})
    worst = max(rows, key=lambda r: r["time_up_s"])
    return {"rows": rows, "stroke_at_ball_mm": lift, "holding_energy_J": 0.0, "worst_time_up_s": worst["time_up_s"],
            "energy_per_lift_J": worst["energy_per_lift_J"],
            "serves": {"spelling_cue_lift (EXP-S12/S18)": True,
                       "withhold_the_rest_of_a_letter": "partly: the ink stops after about "
                       f"{worst['ink_stops_after_s'] * 1e3:.0f} ms; at 30 mm/s about {30 * worst['ink_stops_after_s']:.1f} mm more ink",
                       "gated_write_only_in_reach (EXP-W16)": False},
            "fast_lift_option": {"what": "a latching lift coil on the float (a small moving-magnet solenoid pulls the face back "
                                         "0.6 mm and a detent holds it; the brake of Rev J's drum)", "time_s": 0.008,
                                 "energy_J": 0.01, "mass_g": 0.6, "label": "ASSUMPTION (Rev J pen-lift values, study N)"},
            "label": "CALCULATION (kinematics; speed-force line and power MANUFACTURER AMF-15/106, line shape ASSUMPTION)"}


def positioner_power(hd: Dict) -> Dict:
    """Average power of the three positioners while writing (CALC on ASSUMPTION rates): re-sets when the mean tilt or
    roll drifts beyond the deadband, plus the drivers asleep; the follower's share of a re-set from dz_O/dth."""
    P_lo, P_hi = val(PR.HEAD["pos_power_W"])
    rpm = val(PR.HEAD["resets_per_min"])
    db = val(PR.HEAD["deadband_deg"]) * D2R
    rng = hd["follower_range_mm"]
    dz = rng / (40.0 * D2R) * db                    # mean follower motion per re-set
    t_tilt = 6.0 * db / _speed(0.2)                 # crank 6 mm
    t_roll = val(PR.HEAD["roll_crank_mm"]) * db / _speed(0.05)
    t_f = dz / _speed(0.1)
    E = (t_tilt + t_roll + t_f)
    sleep = val(PR.HEAD["driver_sleep_W"])
    lo = E * P_lo * rpm[0] / 60.0 + sleep
    hi = E * P_hi * rpm[1] / 60.0 + sleep
    return {"per_reset_s": E, "W": [lo, hi], "studyB_P_aux_W": 0.002,
            "label": "CALCULATION (motion times from the speed line; re-set rate ASSUMPTION 2-6 per minute; EXP-B28)"}


def ink_tail(hd: Dict) -> Dict:
    """Ink left after a natural pen lift (CALC): the face follows the refill for the gap g along the normal before its
    front stop; the ball stays on the paper while the pen rises by g, so the tail is g x v_lateral / v_lift.  Also the
    refill travel at touchdown (g / sin th) against REQ-BNIB-002's 0.25 mm."""
    g = hd["gap_mm"]
    rows = []
    for vr in (0.5, 1.0, 2.0):
        rows.append({"v_lateral_over_v_lift": vr, "tail_mm": g * vr})
    td = {f"{t:g}": g / math.sin(t * D2R) for t in (35.0, 50.0, 75.0)}
    g_rule = 0.25 * math.sin(35 * D2R)
    wob_ok = g_rule - val(PR.HEAD["float_margin_mm"])
    return {"gap_mm": g, "rows": rows, "refill_travel_at_touchdown_mm": td,
            "REQ_BNIB_002_touchdown_0p25mm_passes": max(td.values()) <= 0.25,
            "wobble_amplitude_that_REQ_BNIB_002_allows_mm": wob_ok,
            "brake_option": {"what": "an electro-permanent brake locks the float when the face-position sensor sees a lift "
                                     "(Rev J's front-stop rule): tail about 0.3 mm (CALC Rev J)", "energy_W": [0.012, 0.06],
                             "label": "ASSUMPTION (Rev J: 3 mJ per switch, 2 switches per lift, 2 lifts/s; 15 mJ per switch "
                                      "high)"},
            "label": "CALCULATION (kinematics; lift and lateral speeds ASSUMPTION; EXP-T11 measures the tail, AC-T11-03)"}


# ------------------------------------------------------------------------------------------------ balance tolerance stack
def face_stack(n: int = 20000, seed: int = 5, Km_tip: float = 0.333) -> Dict:
    """Monte Carlo of the face-parallelism error (CALC; every contributor ASSUMPTION, params.FACE_STACK): tilt 35-75 deg
    and roll uniform; IMU tilt and roll errors (1 / 2 deg, 1 sigma), the calibrated IMU-to-axis residual, the roll ring,
    the hinge, the face, the linkage backlash and the schedule's deadband (uniform); the angle between the face normal and
    the paper normal gives the residual static side load F_n sin(delta) (the orientation part; study B's friction share
    comes on top), against REQ-BNIB-001 (<= 10 % of F_s cot th mean, <= 25 % at the 95th percentile) and its holding
    power; the tilt wobble (+-2.5 deg, not followed) as a dynamic load."""
    rng = np.random.default_rng(seed)
    S = PR.FACE_STACK
    F_n = val(PR.B1["F_n_N"])
    F_s = val(PR.B1["F_s_N"])
    th = rng.uniform(35.0, 75.0, n) * D2R
    t_err = (rng.normal(0, val(S["imu_tilt_deg"]), n) + rng.normal(0, val(S["imu_to_axis_residual_deg"]), n)
             + rng.normal(0, val(S["hinge_axis_deg"]), n) + rng.normal(0, val(S["face_perp_deg"]), n)
             + rng.uniform(-1, 1, n) * val(S["linkage_backlash_deg"]) + rng.uniform(-1, 1, n) * val(S["deadband_deg"]))
    r_err = (rng.normal(0, val(S["imu_roll_deg"]), n) + rng.normal(0, val(S["roll_ring_axis_deg"]), n)
             + rng.uniform(-1, 1, n) * val(S["linkage_backlash_deg"]) + rng.uniform(-1, 1, n) * val(S["deadband_deg"]))
    lat = r_err * np.cos(th) + rng.normal(0, val(S["imu_to_axis_residual_deg"]), n) + rng.normal(0, val(S["face_perp_deg"]), n)
    delta = np.hypot(t_err, lat) * D2R
    Q = F_n * np.sin(delta)
    ref = F_s / np.tan(th)
    ratio = Q / ref
    P = Q ** 2 / Km_tip ** 2
    wob = val(S["wobble_deg"]) * D2R
    Q_dyn = F_n * math.sin(wob)
    slope = {f"{s:g}": F_n * math.sin(s * D2R) for s in (5.0, 10.0, 20.0)}
    return {"delta_deg": {"mean": float(np.degrees(delta).mean()), "p95": float(np.percentile(np.degrees(delta), 95))},
            "Q_mN": {"mean": float(Q.mean() * 1e3), "p95": float(np.percentile(Q, 95) * 1e3)},
            "ratio_to_Fs_cot": {"mean": float(ratio.mean()), "p95": float(np.percentile(ratio, 95))},
            "REQ_BNIB_001": {"mean_le_0.10": bool(ratio.mean() <= 0.10), "p95_le_0.25": bool(np.percentile(ratio, 95) <= 0.25)},
            "holding_mW": {"mean": float(P.mean() * 1e3), "p95": float(np.percentile(P, 95) * 1e3), "Km_tip": Km_tip},
            "wobble_dynamic_mN": Q_dyn * 1e3, "wobble_dynamic_mW": 0.5 * Q_dyn ** 2 / Km_tip ** 2 * 1e3,
            "desk_slope_mN": {k: v * 1e3 for k, v in slope.items()},
            "studyB_residual_mean_mN": 5.3, "n": n,
            "label": "CALCULATION (Monte Carlo; contributors ASSUMPTION, params.FACE_STACK; EXP-B22 / EXP-B28 measure)"}


# ------------------------------------------------------------------------------------------------ refill change
def refill_change(hd: Dict) -> Dict:
    """How a user swaps the refill without touching the counter-face (PROPOSED DESIGN; forces CALC or ASSUMPTION)."""
    pk = val(PR.HEAD["puck"])
    g_lo, g_hi = pk["grip_N"]
    w_ref = (0.84e-3) * 9.81
    steps = [
        {"step": 1, "who": "user", "what": "Choose 'change refill' in the app or hold the button 3 s.",
         "pen": "centres the nib (servo), sets the face to its steepest position (hinge 15 deg, roll 0) and moves the head "
                "to its rear position; the refill is free to come out."},
        {"step": 2, "who": "user", "what": "Pull the old refill out through the ring by its tip (fingernails, or the "
                                           "supplied rubber sleeve).",
         "pen": f"the refill slides out of the carrier's two rolling guides; its cup's ball unsnaps from the shoe at "
                f"{g_lo:.2f}-{g_hi:.2f} N (the cup comes out on the refill and moves to the new one, or a new cup is fitted); "
                "the shoe stays captive under the face tray's rim."},
        {"step": 3, "who": "user", "what": "Press the cup onto the new metal-bodied ISO 12757-1 D1 refill's rear end, push the "
                                           "refill in through the ring until it clicks (about 0.2 N).",
         "pen": "the carrier's guides centre the refill; the head moves forward and the shoe's funnelled slot takes the cup's "
                "ball; the cup is vented so the refill's ink is not sealed."},
        {"step": 4, "who": "pen", "what": "Check the seat.",
         "pen": "the face-position sensor reads the refill's rear end with the head at its front position: a refill within "
                "ISO's +0.3/0 mm length sits in the float window; an unseated or short refill reads outside it and the app asks "
                "to push again."},
        {"step": 5, "who": "user + pen", "what": "Write a line on any paper for 5 s.",
         "pen": "the nib's holding current at the known tilt shows the new refill's balance; the face needs no calibration "
                "(the balance follows the refill's own spring force); the ink force is set by the float spring."},
    ]
    return {"steps": steps, "parts_moved": ["the refill (with its cup)"], "parts_untouched": ["counter-face head", "shoe",
                                                                                                "float spring", "positioners",
                                                                                                "nib", "ring"],
            "forces_N": {"pull_out": [g_lo, g_hi], "insert": g_hi, "refill_weight": w_ref,
                         "grip_holds_refill_at_g": g_lo / w_ref},
            "tools": "none (a rubber sleeve helps)", "time_s": 30,
            "label": "PROPOSED DESIGN; grip forces ASSUMPTION (EXP-B22 checks with three refill brands)"}
