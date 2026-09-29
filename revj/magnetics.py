r"""Magnetic interactions inside the integrated Rev J pen (CALC with magpylib's analytic magnets; free space unless
stated, so the iron's shielding is NOT counted: upper bounds away from the actuator).

Questions (the lead's conflict 5): the C1S magnets near the heel motors, the Hall sensors and the IMU; what must be
shielded or measured.  Also found here: the axial pull between the C1S magnet cap and its coil plate (not in study N's
model), which the 50 um gimbal strips must carry.

Sources (pen frame: x away from the paper, y lateral, z along the axis from the ball tip; mm; magnet fields are
scale-invariant, so millimetres are used throughout):
  C1S cap       4 x N52 6.32 x 6.32 x 3.34 mm, checkerboard +-z, magnet face at z_a (study N; Br 1.45 T nominal, AMF-139)
  motors        each Faulhaber 0620 B rotor magnet: d 2.5 x 12 mm, diametric, Br 1.2 T (ASSUMPTION: not in the ledger
                extract); its steel housing is ignored (upper bound)
  position mag  2 x 2 x 1 mm N52 on the carrier, magnetised along x (revj.packaging)
  end-cap       4 x N45 tiles 1 x 3 x 12 mm on the slug, magnetised radially (study K; Br 1.33 T, AMF-28)
  pod magnets   steering: d 1 x 1 mm diametric N45 on the fork; wheel load: d 1 x 1 mm axial N45 on the flexure (AMF-72)
Sensors: TMAG5170 (nose, XY noise 140 uT rms at CONV_AVG 000, 24 uT at 101; OPT-53), TMAG5273 (steering, 110-125 uT
rms; OPT-45), DRV5055 (wheel load, 23.6 uT rms with a 3 kHz filter, OPT-46 CALC), LSM6DSV16X IMU (accelerometer and
gyroscope only, no magnetometer: fields do not enter its readings, MFR OPT-37).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from . import ensure_paths
from . import params as PA

ensure_paths()

MU0 = 4e-7 * math.pi
BR_N52 = 1.45            # T, AMF-139 nominal (1.42-1.48)
BR_N45 = 1.33            # T, AMF-28 low end of N45 (1.33-1.37)
BR_MOTOR = 1.2           # T, ASSUMPTION (bonded or sintered NdFeB rotor)


def _magpy():
    import magpylib as magpy
    return magpy


def c1s_cap(dx: float = 0.0, dy: float = 0.0, nd: Optional[Dict] = None) -> "object":
    """The C1S checkerboard (free space), displaced laterally by (dx, dy) mm (the cap's motion at the stop)."""
    magpy = _magpy()
    nd = nd or PA.nose_design()
    w, t = nd["w"], nd["t_m"]
    zc = nd["z_a"] - t / 2
    mags = []
    for i, sx in enumerate((-1, 1)):
        for j, sy in enumerate((-1, 1)):
            sgn = 1.0 if (i + j) % 2 == 0 else -1.0
            mags.append(magpy.magnet.Cuboid(polarization=(0, 0, sgn * BR_N52), dimension=(w, w, t),
                                            position=(sx * w / 2 + dx, sy * w / 2 + dy, zc)))
    return magpy.Collection(*mags)


def motor_magnet(xy, z_mid: float, direction: str = "x") -> "object":
    magpy = _magpy()
    pol = {"x": (BR_MOTOR, 0, 0), "y": (0, BR_MOTOR, 0)}[direction]
    return magpy.magnet.Cylinder(polarization=pol, dimension=(2.5, 12.0), position=(xy[0], xy[1], z_mid))


def dipole_moment_Am2(Br: float, volume_mm3: float) -> float:
    return Br / MU0 * volume_mm3 * 1e-9


# --------------------------------------------------------------------------------------------------- axial pull
def axial_pull(nd: Optional[Dict] = None, n_img: int = 3, half: float = 16.0, n: int = 161) -> Dict:
    """Axial attraction between the magnet cap and the coil plate's iron (CALC, image method as nose2/magnetics: iron
    planes behind the magnets and behind the two coil layers, infinitely permeable).  Maxwell stress B_z^2 / (2 mu0) on
    the plate's iron face.  Upper bound (ideal iron, no saturation)."""
    from nose2 import magnetics as NM                       # read-only reuse of the image construction
    nd = nd or PA.nose_design()
    w, t_m, t_c = nd["w"], nd["t_m"], nd["t_c"]
    clear = 0.5                                             # study N G_CLEAR
    D = t_m + clear + 2 * t_c                               # cap iron (z = 0) to the plate iron (z = D)
    mags = []
    for i in range(2):
        for j in range(2):
            sgn = 1.0 if (i + j) % 2 == 0 else -1.0
            mags.append(((((i - 0.5) * w), ((j - 0.5) * w), t_m / 2), (w, w, t_m), (0.0, 0.0, sgn * BR_N52)))
    col = NM._images(mags, D, axis=2, n=n_img)
    xs = np.linspace(-half, half, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, D - 1e-3)], axis=1)
    B = col.getB(P)
    dA = (xs[1] - xs[0]) ** 2 * 1e-6
    F = float(np.sum(B[:, 2] ** 2) / (2 * MU0) * dA)
    Bmax = float(np.max(np.abs(B[:, 2])))
    F_lumped = nd["B_gap_T"] ** 2 * 4 * (w * 1e-3) ** 2 / (2 * MU0)
    buckling_per_strip = 14.5                                # N, study N (docs/nose_v2.md s4.4, CALC)
    out = {"F_axial_N_images": F, "B_max_at_plate_T": Bmax, "F_axial_N_lumped_Bgap": F_lumped,
           "gimbal_strip_buckling_N": buckling_per_strip,
           "strip_force_if_one_strip_per_axis_carries_it_N": F / math.sqrt(2.0),
           "torque_from_eccentricity_mNm_per_0.1mm": F * 0.1,
           "negative_stiffness_Nm_per_rad_per_0.1mm": F * 0.1e-3,
           "gimbal_bending_stiffness_Nm_per_rad": 0.0028,
           "label": "CALC (magpylib + images, ideal iron: upper bound); eccentricity = offset of the spheres' centre from the "
                    "flexure's pivot (tolerance, ASSUMPTION 0.1 mm)"}
    # an axial offset e of the spheres' centre from the pivot tilts the pull's line with the nose: negative stiffness F e;
    # a lateral offset puts the pull's line e beside the pivot: a constant torque F e that the coils must hold
    arm = (nd["z_a"] - nd["z_p"]) * 1e-3
    km = nd["Km_act"]
    for e_mm in (0.02, 0.05, 0.1):
        tq = F * e_mm * 1e-3
        out[f"lateral_offset_{e_mm}mm"] = {"torque_mNm": tq * 1e3, "coil_force_N": tq / arm,
                                           "hold_power_W": (tq / arm / km) ** 2,
                                           "axial_offset_negative_k_share_of_flexure": F * e_mm * 1e-3 / 0.0028}
    out["offset_note"] = ("hold power = (F e / (arm Km))^2 with arm = actuator - pivot and Km at the magnets (study N, an "
                          "upper bound: a lower Km raises it); the servo holds either offset, at a cost in power")
    return out


# --------------------------------------------------------------------------------------------------- stray fields
def field_at(col, pts) -> np.ndarray:
    """B (T) at points (N, 3) mm, always returned as (N, 3)."""
    P = np.atleast_2d(np.asarray(pts, float))
    return np.asarray(col.getB(P)).reshape(-1, 3)


def c1s_at_motors(geo: Dict, n: int = 21) -> Dict:
    """C1S cap field along the motor axes (free space: an upper bound; the 2.4 mm Hiperco plate between them is not
    counted), and the torque it can put on each motor's rotor magnet: |m| |B| (CALC)."""
    nd = PA.nose_design()
    mot = next(c for c in geo["components"] if c["id"] == "drive_motor")
    ox, oy = mot["offset"]
    zs = np.linspace(mot["z0"], mot["z1"], n)
    res = {}
    m_rot = dipole_moment_Am2(BR_MOTOR, math.pi / 4 * 2.5 ** 2 * 12.0)
    for name, (dx, dy) in {"rest": (0.0, 0.0), "stop_toward": (-nd["stroke_act"], 0.0), "stop_side": (0.0, nd["stroke_act"])}.items():
        col = c1s_cap(dx, dy, nd)
        B = field_at(col, np.stack([np.full(n, ox), np.full(n, oy), zs], axis=1))
        Bm = np.linalg.norm(B, axis=1)
        # the rotor spans the middle 12 mm of the motor: mean field over it
        mid = (zs >= mot["z0"] + 4) & (zs <= mot["z1"] - 4)
        Bmean = float(np.mean(Bm[mid]))
        res[name] = {"B_front_mT": float(Bm[0] * 1e3), "B_rotor_mean_mT": Bmean * 1e3, "B_max_mT": float(Bm.max() * 1e3),
                     "torque_bound_mNm": m_rot * Bmean * 1e3}
    fr = PA.MOTOR["friction_mNm"].value
    rated = PA.MOTOR["rated_mNm"].value
    worst = max(v["torque_bound_mNm"] for v in res.values())
    return {"positions": res, "rotor_moment_Am2": m_rot, "motor_friction_mNm": fr, "motor_rated_mNm": rated,
            "worst_torque_to_friction": worst / fr, "worst_torque_to_rated": worst / rated,
            "shield_factor_needed_for_friction_level": max(worst / fr, 1.0),
            "label": "CALC (free space upper bound; rotor magnet ASSUMPTION; housing and plate shielding not counted)"}


def nose_hall(geo: Dict, y_pair: float = 1.2, die_x: float = 6.8) -> Dict:
    """The nose position sensor (PROPOSED): two single-axis linear Halls (DRV5055-A4, +-169 mT, MFR OPT-46) on the main
    board's underside, y = +-1.2 mm, their dies 2.8 mm above a 2 x 2 x 1 mm N52 magnet on the carrier (magnetised along
    x).  x from the sum of their Bx readings, y from the difference (a gradiometer: uniform fields cancel in y).  Signal
    slopes, the largest field over the stroke (a circle), noise at the tip, and the disturbances from the C1S cap, the
    motors, the end-cap tiles and the Earth's field (CALC, free space).  The single 3-D Hall (TMAG5170) is kept as the
    comparison."""
    magpy = _magpy()
    nd = PA.nose_design()
    pm = next(c for c in geo["components"] if c["id"] == "position_magnet")
    hs = next(c for c in geo["components"] if c["id"] == "nose_hall")
    zc = 0.5 * (pm["z0"] + pm["z1"])
    zs = 0.5 * (hs["z0"] + hs["z1"])
    S = np.array([[die_x, y_pair, zs], [die_x, -y_pair, zs]])
    k_lever = (nd["z_p"] - zc) / nd["z_p"]                                            # magnet motion per tip motion

    def mag(dx=0.0, dy=0.0):
        return magpy.magnet.Cuboid(polarization=(BR_N52, 0, 0), dimension=tuple(pm["size"]),
                                   position=(pm["offset"][0] + dx, pm["offset"][1] + dy, zc))

    def chans(m):
        B = field_at(m, S)
        return 0.5 * (B[0, 0] + B[1, 0]), 0.5 * (B[0, 0] - B[1, 0])
    d = 0.01
    sx = abs(chans(mag(dx=d))[0] - chans(mag(dx=-d))[0]) / (2 * d)                     # T per mm of magnet motion
    sy = abs(chans(mag(dy=d))[1] - chans(mag(dy=-d))[1]) / (2 * d)
    st_u = nd["X_nom"] * k_lever
    st_s = (nd["X_nom"] + 0.5) * k_lever

    def bmax(st):
        vals = []
        for a in np.linspace(0, 2 * math.pi, 24, endpoint=False):
            for rr in (0.5 * st, st):
                vals.append(float(np.max(np.abs(field_at(mag(dx=rr * math.cos(a), dy=rr * math.sin(a)), S)[:, 0]))))
        return max(vals) * 1e3
    n_pair = 23.6e-6 / math.sqrt(2.0)                                                   # OPT-46 CALC per sensor, averaged pair
    tip_noise = {"DRV5055_A4_pair": {"x": n_pair / sx / k_lever * 1e3, "y": n_pair / sy / k_lever * 1e3}}
    # comparison: one 3-D Hall on the axis at the same height (TMAG5170, MFR OPT-53)
    S1 = np.array([[die_x, 0.0, zs]])
    g1x = abs(field_at(mag(dx=d), S1)[0][0] - field_at(mag(dx=-d), S1)[0][0]) / (2 * d)
    g1y = abs(field_at(mag(dy=d), S1)[0][1] - field_at(mag(dy=-d), S1)[0][1]) / (2 * d)
    for k, v in {"TMAG5170_CONV_AVG_000_20kSPS": 140e-6, "TMAG5170_CONV_AVG_101": 24e-6}.items():
        tip_noise[k] = {"x": v / g1x / k_lever * 1e3, "y": v / g1y / k_lever * 1e3}
    # disturbances at the pair (x channel = mean; y channel = half difference)
    cap, cap_stop = c1s_cap(0.0, 0.0, nd), c1s_cap(-nd["stroke_act"], 0.0, nd)

    def ch_ext(col):
        B = field_at(col, S)
        return np.array([0.5 * (B[0, 0] + B[1, 0]), 0.5 * (B[0, 0] - B[1, 0])])
    dcap = ch_ext(cap_stop) - ch_ext(cap)
    mot = next(c for c in geo["components"] if c["id"] == "drive_motor")
    zm = 0.5 * (mot["z0"] + mot["z1"])
    dm_x, dm_y = 0.0, 0.0
    for sgn in (1, -1):
        for dr in ("x", "y"):
            e = ch_ext(motor_magnet((mot["offset"][0], sgn * mot["offset"][1]), zm, dr))
            dm_x, dm_y = max(dm_x, abs(e[0])), max(dm_y, abs(e[1]))
    ec = [c for c in geo["components"] if c["id"].startswith("ec_magnet")]
    de_x = de_y = 0.0
    for dx in (-4.0, 0.0, 4.0):
        cols = []
        for c in ec:
            ox, oy = c["offset"]
            r = math.hypot(ox, oy)
            cols.append(magpy.magnet.Cuboid(polarization=(BR_N45 * ox / r, BR_N45 * oy / r, 0.0), dimension=tuple(c["size"]),
                                            position=(ox + dx, oy, 0.5 * (c["z0"] + c["z1"]))))
        e = sum(ch_ext(cc) for cc in cols)
        de_x, de_y = max(de_x, abs(e[0])), max(de_y, abs(e[1]))
    um = lambda B, sl: B / sl / k_lever * 1e3                                          # noqa: E731  field -> tip error (um)
    clear_stop = hs["offset"][0] - hs["size"][0] / 2 - (pm["offset"][0] + pm["size"][0] / 2 + nd["z_p"] * 0 + (nd["X_nom"] + 0.5) / nd["z_p"] * (nd["z_p"] - zc))
    return {"sensors_xyz_mm": S.tolist(), "magnet_motion_per_tip_motion": k_lever,
            "slope_mT_per_mm_magnet": {"x": sx * 1e3, "y": sy * 1e3},
            "max_field_mT": {"usable": bmax(st_u), "stop": bmax(st_s)}, "range_mT": {"DRV5055_A4": 169.0, "DRV5055_A3": 85.0},
            "package_to_magnet_at_stop_mm": clear_stop,
            "tip_noise_um_rms": tip_noise,
            "disturbance_equiv_tip_error_um": {
                "c1s_cap_over_stroke_x_y": [um(abs(dcap[0]), sx), um(abs(dcap[1]), sy)],
                "motors_unshielded_x_y": [um(dm_x, sx), um(dm_y, sy)],
                "endcap_tiles_x_y": [um(de_x, sx), um(de_y, sy)],
                "earth_50uT_x_y": [um(50e-6, sx), 0.0]},
            "notes": ["the C1S cap's field at the sensors is a fixed function of the nose position: calibrate it (a map)",
                      "the y channel is a gradiometer: uniform fields (Earth, distant motors) cancel; the x channel sees them",
                      "the Earth's field changes only as the pen turns (slow): a slow offset in x, removed by the page sensor's "
                      "absolute position in autowrite"],
            "label": "CALC (magpylib, free space; DRV5055 noise from the OPT-46 CALC; TMAG5170 noise MFR OPT-53; Earth field "
                     "25-65 uT, 50 uT used, ASSUMPTION)"}


def pod_crosstalk(geo: Dict) -> Dict:
    """Steering magnet (rotating) seen by the wheel-load Hall, and the load magnet seen by the steering Hall (CALC)."""
    magpy = _magpy()
    fork = next(c for c in geo["components"] if c["id"] == "drive_fork")
    ls = next(c for c in geo["components"] if c["id"] == "drive_load_sensor")
    ss = next(c for c in geo["components"] if c["id"] == "drive_steer_sensor")
    p_steer = np.array([fork["offset"][0], 0.0, 0.5 * (fork["z0"] + fork["z1"])])
    p_ls = np.array([ls["offset"][0], ls["offset"][1], 0.5 * (ls["z0"] + ls["z1"])])
    p_ss = np.array([ss["offset"][0], ss["offset"][1], 0.5 * (ss["z0"] + ss["z1"])])
    p_lmag = p_ls + np.array([-1.5, 0.0, 0.0])                    # load magnet 1.5 mm from its sensor (AMF-72 calc distance)
    th = math.radians(50.0)
    n = np.array([math.cos(th), 0.0, math.sin(th)])
    e1 = np.array([math.sin(th), 0.0, -math.cos(th)])
    e2 = np.array([0.0, 1.0, 0.0])
    Bx_load = []
    for a in np.linspace(0, 2 * math.pi, 36, endpoint=False):
        u = math.cos(a) * e1 + math.sin(a) * e2
        m = magpy.magnet.Cylinder(polarization=tuple(BR_N45 * u), dimension=(1.0, 1.0), position=tuple(p_steer))
        Bx_load.append(field_at(m, p_ls)[0][0])                   # the DRV5055 reads one axis (x here)
    Bx_load = np.array(Bx_load)
    lm = magpy.magnet.Cylinder(polarization=(-BR_N45, 0, 0), dimension=(1.0, 1.0), position=tuple(p_lmag))
    d = 0.01
    sig = (field_at(magpy.magnet.Cylinder(polarization=(-BR_N45, 0, 0), dimension=(1.0, 1.0), position=tuple(p_lmag + [d, 0, 0])), p_ls)[0][0]
           - field_at(magpy.magnet.Cylinder(polarization=(-BR_N45, 0, 0), dimension=(1.0, 1.0), position=tuple(p_lmag - [d, 0, 0])), p_ls)[0][0]) / (2 * d)
    k_spring = PA.HEEL["preload_N"].value / 0.54                  # N/mm (0.55 N over the 0.54 mm travel)
    x_err = (Bx_load.max() - Bx_load.min()) / 2 / abs(sig)
    B_lm_at_ss = float(np.linalg.norm(field_at(lm, p_ss)[0]))
    return {"steer_magnet_at_load_sensor_pp_mT": float((Bx_load.max() - Bx_load.min()) * 1e3),
            "load_signal_slope_mT_per_mm": float(abs(sig) * 1e3),
            "false_deflection_um_amplitude": float(x_err * 1e3), "false_load_mN_amplitude": float(x_err * k_spring * 1e3),
            "load_magnet_at_steer_sensor_mT": B_lm_at_ss * 1e3,
            "note": "the crosstalk is a fixed function of the heading: calibrate it out (a heading-indexed table) or place the "
                    "load magnet and sensor 90 deg around the fork",
            "label": "CALC (magpylib; magnet sizes and positions ASSUMPTION, AMF-72 class magnets)"}


def outside_field(geo: Dict, dists=(5.0, 10.0, 20.0, 30.0, 50.0, 100.0, 150.0), n_z: int = 60, n_phi: int = 24) -> Dict:
    """Largest |B| on cylinders around the pen at a distance d from its surface (radius 12 + d), over the whole length,
    with every magnet in the pen (motors unshielded, the C1S without its irons): an upper bound (CALC)."""
    magpy = _magpy()
    cols = [c1s_cap()]
    for sgn in (1, -1):
        mot = next(c for c in geo["components"] if c["id"] == "drive_motor")
        cols.append(motor_magnet((mot["offset"][0], sgn * mot["offset"][1]), 0.5 * (mot["z0"] + mot["z1"]), "x"))
    pm = next(c for c in geo["components"] if c["id"] == "position_magnet")
    cols.append(magpy.magnet.Cuboid(polarization=(BR_N52, 0, 0), dimension=tuple(pm["size"]),
                                    position=(pm["offset"][0], 0.0, 0.5 * (pm["z0"] + pm["z1"]))))
    for c in geo["components"]:
        if c["id"].startswith("ec_magnet"):
            ox, oy = c["offset"]
            r = math.hypot(ox, oy)
            cols.append(magpy.magnet.Cuboid(polarization=(BR_N45 * ox / r, BR_N45 * oy / r, 0.0), dimension=tuple(c["size"]),
                                            position=(ox, oy, 0.5 * (c["z0"] + c["z1"]))))
    groups = {"all": cols, "c1s_cap": cols[:1], "motors": cols[1:3], "endcap_tiles": cols[4:] if len(cols) > 4 else None}
    L = geo["length_with_endcap"]
    zs = np.linspace(-20.0, L + 20.0, n_z)
    phis = np.linspace(0, 2 * math.pi, n_phi, endpoint=False)
    out = {}
    for d in dists:
        r = 12.0 + d
        P = np.array([[r * math.cos(p), r * math.sin(p), z] for z in zs for p in phis])
        row = {}
        for g, col in groups.items():
            if col is None:
                continue
            B = np.linalg.norm(sum(field_at(src, P) for src in col), axis=1)
            k = int(np.argmax(B))
            row[g] = {"B_max_mT": float(B[k] * 1e3), "at_z_mm": float(P[k, 2])}
        out[f"{d:g}"] = row
    return {"by_distance_from_surface_mm": out,
            "threshold_note": "ASSUMPTION 1 mT (10 G) static field: the level commonly used for implanted cardiac devices' "
                              "magnet mode; the applicable limit (ISO 14117 and the implant makers' guidance) was not opened "
                              "here and must be checked",
            "label": "CALC (magpylib, free space: every iron and housing ignored, an upper bound)"}


def summary(geo: Dict) -> Dict:
    ap = axial_pull()
    return {"axial_pull": ap, "c1s_at_motors": c1s_at_motors(geo), "nose_hall": nose_hall(geo),
            "pod_crosstalk": pod_crosstalk(geo), "outside": outside_field(geo),
            "imu": {"note": "LSM6DSV16X has an accelerometer and a gyroscope only (MFR OPT-37): no magnetometer, so the fields "
                            "do not enter its readings; its lever to the tip is 56 mm (was 92 mm in Rev H)"}}
