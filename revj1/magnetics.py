r"""P1 (magnetic half) and P6: the cap's axial pull, what changes it, and the cap's torque on the heel motors' rotors.

All fields CALC with magpylib's analytic magnets (MFR AMF-139 for N52).  Soft iron is IDEALISED wherever it appears:
infinitely permeable planes by the method of images (nose2/magnetics._images, read-only), never saturating, infinite in
extent.  The pull on an ideal-iron plane is the Maxwell stress B_n^2 / (2 mu0) integrated over its face (an upper bound:
real Hiperco is finite, notched and near saturation).  Free space (no iron at all) is used for the fields at the motors:
an upper bound there, because the coil plate's back iron lies between the cap and the motors.

Convention (as revj.magnetics.axial_pull, so the 16.5 N figure is reproduced): cap iron at z = 0, magnets z 0..t_m,
0.5 mm clearance, two coil layers of t_c each, the plate's iron face at D = t_m + 0.5 + 2 t_c (+ a spacer s).  The force
constant is taken proportional to the mean |B_z| over the two coil layers above the central 60 % of each pole (the leg
region of nose2/magnetics.axial_B) times sqrt(copper volume); only RATIOS to the Rev J design are used.

P1 options computed here
  spacer        a non-magnetic spacer s between the coils and the plate iron (a thinner effective gap to iron is not
                possible; a THINNER back iron only saturates, which lowers flux and pull together, see F_per_Km2)
  air core      no plate iron: the cap's own iron only; the pull then comes from the cell's steel can behind the plate
                (treated as an ideal iron plane: an upper bound, the can is a thin nickel-plated steel shell)
  thick coil    air core with the coil grown into the space of the removed iron
  ring          a pair of repelling ring magnets at the gimbal plane sized to cancel the pull: force, tilt stiffness about
                the pivot and the lateral (Earnshaw) negative stiffness (magpylib getFT, SI units)
  centring      the pull's line passes through the coil plate's sphere centre (fixed in the handle): an axial offset e_p of
                that centre from the pivot adds -F e_p to the pivot stiffness; a lateral offset a constant torque F e
P6
  detent        torque amplitude on a diametric rotor magnet = |m| |<B_perp>| with the transverse field vector-averaged over
                the rotor volume (Rev J used |m| x mean |B| including B_z, which turns nothing); soft-iron cup (analytic
                transverse shielding factor of a thin cylindrical shell, 1 + mu_r t / (2 R)); moving the motors back
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

import numpy as np

from . import ensure_paths

ensure_paths()
from revj import magnetics as RMG  # noqa: E402  (read-only reuse: the C1S cap, motor magnets, the Rev J pull)
from revj import params as RPA  # noqa: E402

MU0 = 4e-7 * math.pi
BR_N52 = RMG.BR_N52        # 1.45 T nominal, MFR AMF-139
BR_MOTOR = RMG.BR_MOTOR    # 1.2 T, ASSUMPTION (Rev J)
CLEAR = 0.5                # mm, study N G_CLEAR (ASSUMPTION)


def _magpy():
    import magpylib as magpy
    return magpy


def _checker(nd: Dict):
    w, t_m = nd["w"], nd["t_m"]
    mags = []
    for i in range(2):
        for j in range(2):
            sgn = 1.0 if (i + j) % 2 == 0 else -1.0
            mags.append((((i - 0.5) * w, (j - 0.5) * w, t_m / 2), (w, w, t_m), (0.0, 0.0, sgn * BR_N52)))
    return mags


def _single_plane_images(mags, axis: int = 2):
    """Magnets on ONE ideal-iron plane at coordinate 0: the magnets and their mirror images (CALC)."""
    magpy = _magpy()
    out = []
    for (pos, dim, M) in mags:
        pos = np.asarray(pos, float); M = np.asarray(M, float)
        Mm = -M.copy(); Mm[axis] = M[axis]
        p2 = pos.copy(); p2[axis] = -pos[axis]
        out.append(magpy.magnet.Cuboid(polarization=M, dimension=dim, position=pos))
        out.append(magpy.magnet.Cuboid(polarization=Mm, dimension=dim, position=p2))
    return magpy.Collection(*out)


def _coil_B(col, nd: Dict, z0: float, z1: float, npts: int = 7, leg_frac: float = 0.6) -> float:
    """Mean |B_z| (T) over the coil region z0..z1 above the central leg_frac of each pole (nose2 axial_B's averaging)."""
    w = nd["w"]
    zs = np.linspace(z0, z1, npts)
    vals = []
    for i in range(2):
        for j in range(2):
            cx, cy = (i - 0.5) * w, (j - 0.5) * w
            u = np.linspace(-leg_frac * w / 2, leg_frac * w / 2, npts)
            P = np.array(np.meshgrid(cx + u, cy + u, zs, indexing="ij")).reshape(3, -1).T
            vals.append(np.abs(col.getB(P)[:, 2]))
    return float(np.mean(np.concatenate(vals)))


def _face_pull(col, z_face: float, half: float = 16.0, n: int = 161) -> Dict:
    """Maxwell-stress pull (N) on an ideal-iron face at z_face (B normal to the face), mm units for the field grid."""
    xs = np.linspace(-half, half, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z_face - 1e-3)], axis=1)
    B = col.getB(P)
    dA = (xs[1] - xs[0]) ** 2 * 1e-6
    return {"F_N": float(np.sum(B[:, 2] ** 2) / (2 * MU0) * dA), "B_max_T": float(np.max(np.abs(B[:, 2])))}


def pull_and_B(nd: Optional[Dict] = None, spacer: float = 0.0, air_core: bool = False, t_coil_total: Optional[float] = None,
               can_gap: Optional[float] = None, n_img: int = 3, grid_n: int = 161) -> Dict:
    """Pull on the plate iron (or on the cell can for an air-core plate) and the mean coil field (CALC, ideal iron)."""
    from nose2 import magnetics as NM
    nd = nd or RPA.nose_design()
    t_m, t_c = nd["t_m"], nd["t_c"]
    tcoil = 2 * t_c if t_coil_total is None else t_coil_total
    z0, z1 = t_m + CLEAR, t_m + CLEAR + tcoil
    mags = _checker(nd)
    if not air_core:
        D = z1 + spacer
        col = NM._images(mags, D, axis=2, n=n_img)
        pull = _face_pull(col, D, n=grid_n)
        Bc = _coil_B(col, nd, z0, z1)
        return {"D_mm": D, "pull_N": pull["F_N"], "B_face_max_T": pull["B_max_T"], "B_coil_T": Bc, "t_coil_mm": tcoil,
                "spacer_mm": spacer, "air_core": False}
    col1 = _single_plane_images(mags)
    Bc = _coil_B(col1, nd, z0, z1)
    out = {"B_coil_T": Bc, "t_coil_mm": tcoil, "spacer_mm": 0.0, "air_core": True, "pull_from_plate_N": 0.0}
    if can_gap is not None:
        Dc = z1 + can_gap
        colc = NM._images(mags, Dc, axis=2, n=n_img)
        out.update({"can_face_mm": Dc, "pull_from_cell_can_N_upper": _face_pull(colc, Dc, n=grid_n)["F_N"]})
    return out


def pull_variants(nd: Optional[Dict] = None, quick: bool = False) -> Dict:
    """Spacer, air-core and thick-coil variants against the Rev J design (CALC)."""
    nd = nd or RPA.nose_design()
    gn = 81 if quick else 161
    base = pull_and_B(nd, grid_n=gn)
    rows = {"revJ": dict(base)}
    for s in ((0.25, 0.5) if quick else (0.1, 0.25, 0.5, 0.75, 1.0)):
        rows[f"spacer_{s:g}mm"] = pull_and_B(nd, spacer=s, grid_n=gn)
    tb = nd["t_bi"]
    rows["air_core"] = pull_and_B(nd, air_core=True, can_gap=0.5, grid_n=gn)             # plate iron removed; can 0.5 mm behind
    rows["air_core_thick_coil"] = pull_and_B(nd, air_core=True, t_coil_total=2 * nd["t_c"] + tb, can_gap=0.5, grid_n=gn)
    rows["air_core_can_moved_up"] = pull_and_B(nd, air_core=True, can_gap=0.5 - tb if 0.5 - tb > 0.05 else 0.05, grid_n=gn)
    # conventions for D (the pull is sensitive to where the iron face really is)
    from nose2 import magnetics as NM
    mags = _checker(nd)
    D_n2 = nd["t_m"] + nd["gap"] + nd["t_c"]                                            # nose2's flux convention
    D_lay = nd["t_m"] + nd["gap"] + 2 * nd["t_c"]                                       # revj packaging's plate front + coils
    conv = {"nose2_flux_convention": {"D_mm": D_n2, "pull_N": _face_pull(NM._images(mags, D_n2, 2, 3), D_n2, n=gn)["F_N"]},
            "revj_pull_convention": {"D_mm": base["D_mm"], "pull_N": base["pull_N"]},
            "revj_layout_iron_face": {"D_mm": D_lay, "pull_N": _face_pull(NM._images(mags, D_lay, 2, 3), D_lay, n=gn)["F_N"]}}
    for k, r in rows.items():
        c_ratio = math.sqrt(r["t_coil_mm"] / base["t_coil_mm"])                        # copper volume at the same leg area
        km = r["B_coil_T"] / base["B_coil_T"] * c_ratio
        r["Km_ratio"] = km
        r["coil_power_ratio"] = 1.0 / km ** 2
        pull = r.get("pull_N", r.get("pull_from_cell_can_N_upper", 0.0))
        r["pull_used_N"] = pull
        r["F_per_Km2_ratio"] = (pull / base["pull_N"]) / km ** 2 if km > 0 else None
    return {"rows": rows, "D_conventions": conv, "t_bi_mm": tb,
            "note": ("coil power at the same force scales as 1 / Km^2; a thinner back iron is not modelled (ideal iron "
                     "does not saturate): real saturation lowers flux, pull and Km together, so F / Km^2 stays near 1"),
            "label": "CALC (magpylib + images, ideal iron: upper bounds of the pull; Km ratios from the mean coil field)"}


# --------------------------------------------------------------------------------------------------- repelling ring
def ring_pair(r_in: float, r_out: float, t: float, gap: float, Br: float = 1.33):
    """Two coaxial axially magnetised rings in repulsion across `gap` (SI, metres): the handle ring below z = 0 and the
    nose ring above; returns (source, target)."""
    magpy = _magpy()
    fixed = magpy.magnet.CylinderSegment(polarization=(0, 0, Br), dimension=(r_in, r_out, t, 0, 360),
                                         position=(0, 0, -gap / 2 - t / 2))
    moving = magpy.magnet.CylinderSegment(polarization=(0, 0, -Br), dimension=(r_in, r_out, t, 0, 360),
                                          position=(0, 0, gap / 2 + t / 2), meshing=600)
    return fixed, moving


def ring_forces(r_in=3.0e-3, r_out=9.0e-3, t=1.0e-3, gap=0.5e-3, Br=1.33, d_ang=2e-3, d_lat=20e-6) -> Dict:
    """Force of the repelling pair, the tilt stiffness about the pivot (the gap's mid-plane on the axis) and the lateral
    stiffness (CALC, magpylib getFT; N45 Br 1.33 T low end, MFR AMF-28)."""
    magpy = _magpy()
    src, tgt = ring_pair(r_in, r_out, t, gap, Br)
    F0, T0 = magpy.getFT(src, tgt, pivot=(0, 0, 0))
    out = {"geometry_mm": {"r_in": r_in * 1e3, "r_out": r_out * 1e3, "t": t * 1e3, "gap": gap * 1e3}, "Fz_N": float(F0[2])}
    taus = []
    for a in (-d_ang, d_ang):
        src, tgt = ring_pair(r_in, r_out, t, gap, Br)
        tgt.rotate_from_angax(math.degrees(a), "x", anchor=(0, 0, 0))
        F, T = magpy.getFT(src, tgt, pivot=(0, 0, 0))
        taus.append(float(T[0]))
    out["tilt_stiffness_Nm_per_rad"] = -(taus[1] - taus[0]) / (2 * d_ang)         # restoring torque -> positive
    fl = []
    for dx in (-d_lat, d_lat):
        src, tgt = ring_pair(r_in, r_out, t, gap, Br)
        tgt.move((dx, 0, 0))
        F, T = magpy.getFT(src, tgt, pivot=(0, 0, 0))
        fl.append(float(F[0]))
    out["lateral_stiffness_N_per_m"] = -(fl[1] - fl[0]) / (2 * d_lat)             # negative = pushes further out
    return out


def ring_options(target_N: float, quick: bool = False) -> Dict:
    """Ring pairs that fit the gimbal (r 2.75-10 mm) and roughly cancel the pull: size, force, stiffness (CALC)."""
    rows = []
    geos = [(3.0e-3, 9.0e-3, 1.0e-3, 0.5e-3), (3.0e-3, 9.0e-3, 1.5e-3, 1.0e-3), (6.0e-3, 9.5e-3, 1.0e-3, 0.4e-3)]
    if quick:
        geos = geos[:1]
    for (ri, ro, t, g) in geos:
        r = ring_forces(ri, ro, t, g)
        r["share_of_pull"] = r["Fz_N"] / target_N
        rows.append(r)
    return {"rows": rows, "target_N": target_N,
            "label": "CALC (magpylib getFT on meshed ring magnets, SI; N45 rings, ASSUMPTION sizes)"}


# --------------------------------------------------------------------------------------------------- centring
def centring(F: float, k_pivot_Nm_rad: float, arm_mm: float, Km_act: float) -> Dict:
    """Offsets of the plate's sphere centre from the pivot (CALC).  Axial offset e_p: stiffness change -F e_p (its sign
    follows the offset; the pull's line passes through the fixed centre).  Lateral offset e: a constant torque F e, held
    by the coils: coil force F e / arm, power (F e / (arm Km))^2."""
    rows = []
    for e in (0.02, 0.05, 0.1):
        dk = F * e * 1e-3
        tq = F * e * 1e-3
        fcoil = tq / (arm_mm * 1e-3)
        rows.append({"offset_mm": e, "axial_dk_Nm_per_rad": dk, "axial_dk_share_of_pivot": dk / k_pivot_Nm_rad,
                     "lateral_torque_mNm": tq * 1e3, "lateral_coil_force_N": fcoil, "lateral_hold_power_W": (fcoil / Km_act) ** 2})
    return {"F_N": F, "k_pivot_Nm_rad": k_pivot_Nm_rad, "rows": rows,
            "proposal": "sphere centre on the pivot within 0.05 mm both ways; the coil plate seats on a shim set after a "
                        "measurement of the unpowered nose's stiffness (EXP-J01 set-up)",
            "label": "CALC (Km at the magnets from study N: an upper bound, so the hold power is a lower bound)"}


# --------------------------------------------------------------------------------------------------- P6: detent
def rotor_moment_Am2(d_mm: float = 2.5, l_mm: float = 12.0, Br: float = BR_MOTOR) -> float:
    return Br / MU0 * math.pi / 4 * d_mm ** 2 * l_mm * 1e-9


def rotor_field(geo: Dict, dz: float = 0.0, cap_offset=(0.0, 0.0), n_z: int = 13, n_r: int = 3, nd: Optional[Dict] = None,
                which: str = "drive_motor") -> Dict:
    """Cap field over the rotor volume of one motor (free space, mm units): vector mean of the transverse field, mean |B|."""
    nd = nd or RPA.nose_design()
    mot = next(c for c in geo["components"] if c["id"] == which)
    ox, oy = mot["offset"]
    zc = 0.5 * (mot["z0"] + mot["z1"]) + dz
    col = RMG.c1s_cap(cap_offset[0], cap_offset[1], nd)
    zs = np.linspace(zc - 6.0, zc + 6.0, n_z)                     # the rotor magnet spans the middle 12 mm (ASSUMPTION)
    rr = np.linspace(0.0, 1.25, n_r)
    pts = []
    for z in zs:
        for r in rr:
            for a in (np.linspace(0, 2 * np.pi, 6, endpoint=False) if r > 0 else (0.0,)):
                pts.append([ox + r * math.cos(a), oy + r * math.sin(a), z])
    B = RMG.field_at(col, np.array(pts))
    Bp = B[:, :2].mean(axis=0)
    return {"B_perp_vector_mean_mT": float(np.linalg.norm(Bp) * 1e3), "B_abs_mean_mT": float(np.mean(np.linalg.norm(B, axis=1)) * 1e3),
            "B_front_mT": float(np.linalg.norm(RMG.field_at(col, np.array([[ox, oy, mot['z0'] + dz]]))[0]) * 1e3),
            "z_mid_mm": zc}


def cup_shielding(mu_r: float, t_mm: float, R_mm: float = 3.2) -> float:
    """Transverse shielding factor of a long thin soft-iron cylindrical shell (CALC, magnetostatics of a shell in a
    uniform transverse field: S = 1 + (mu_r - 1)^2 / (4 mu_r) (1 - R_i^2 / R_o^2) ~ 1 + mu_r t / (2 R))."""
    Ro, Ri = R_mm + t_mm, R_mm
    return 1.0 + (mu_r - 1) ** 2 / (4 * mu_r) * (1 - Ri ** 2 / Ro ** 2)


def detent(geo: Dict, quick: bool = False) -> Dict:
    """P6: the cap's torque on the heel motors' rotors, and what a cup or moving the motors does (CALC)."""
    nd = RPA.nose_design()
    m = rotor_moment_Am2()
    fr = RPA.MOTOR["friction_mNm"].value
    rated = RPA.MOTOR["rated_mNm"].value
    cases = {"rest": (0.0, 0.0), "stop_toward_paper": (-nd["stroke_act"], 0.0), "stop_side": (0.0, nd["stroke_act"]),
             "stop_diag": (-nd["stroke_act"] / math.sqrt(2), nd["stroke_act"] / math.sqrt(2))}
    pos = {}
    for k, off in cases.items():
        rf = rotor_field(geo, 0.0, off, nd=nd)
        rf["torque_amp_mNm"] = m * rf["B_perp_vector_mean_mT"] * 1e-3 * 1e3
        rf["revJ_style_bound_mNm"] = m * rf["B_abs_mean_mT"] * 1e-3 * 1e3
        pos[k] = rf
    worst = max(v["torque_amp_mNm"] for v in pos.values())
    ripple = {k: v["torque_amp_mNm"] for k, v in pos.items()}
    move = []
    for dz in ((0.0, 10.0) if quick else (0.0, 5.0, 10.0, 15.0, 20.0)):
        vals = [m * rotor_field(geo, dz, off, nd=nd)["B_perp_vector_mean_mT"] for off in cases.values()]
        move.append({"moved_back_mm": dz, "torque_amp_mNm": max(vals), "to_friction": max(vals) / fr})
    cups = []
    for mu_r in (500.0, 2000.0, 20000.0):
        for t in (0.1, 0.2):
            S = cup_shielding(mu_r, t)
            B_wall = pos["stop_toward_paper"]["B_front_mT"] * 1e-3 * 3.2 / t          # flux collected over the radius into the wall
            cups.append({"mu_r": mu_r, "t_mm": t, "shielding_factor_transverse": S, "torque_amp_mNm": worst / S,
                         "to_friction": worst / S / fr, "wall_flux_density_T_est": B_wall,
                         "mass_g_two_cups_8mm": 2 * (math.pi * 6.4 * t * 8.0 + math.pi * 3.2 ** 2 * t) * 7.87e-3})
    return {"rotor_moment_Am2": m, "rotor_magnet": RPA.MOTOR["rotor_magnet"].value, "positions": pos,
            "worst_torque_amp_mNm": worst, "to_friction": worst / fr, "to_rated": worst / rated,
            "at_tyre_N": worst * 1e-3 * 2.0 / 1e-3,
            "revJ_bound_mNm": 0.080, "moving_back": move, "cups": cups,
            "housing": "aluminium, black anodized (MFR, Faulhaber 0620 B datasheet, edition 2026-07-28): the housing does not "
                       "shield; whether the stator has an iron return ring is not stated",
            "plate_between": "the coil plate's 2.37 mm back iron lies between the cap and the motor fronts (motors at 24 deg "
                             "from the bottom, outside the +-10 deg notch): free space is an upper bound; an infinite ideal "
                             "plane would be a lower bound of zero",
            "label": "CALC (magpylib free space; rotor magnet d 2.5 x 12 mm Br 1.2 T ASSUMPTION; mu_r ASSUMPTION range)"}


def summary(geo: Dict, F_pull: float, k_pivot_Nm_rad: float, quick: bool = False) -> Dict:
    nd = RPA.nose_design()
    pv = pull_variants(nd, quick)
    return {"pull_variants": pv, "revJ_pull": RMG.axial_pull(n=81 if quick else 161),
            "ring": ring_options(F_pull, quick),
            "centring": centring(F_pull, k_pivot_Nm_rad, nd["z_a"] - nd["z_p"], nd["Km_act"]),
            "detent": detent(geo, quick)}
