"""Physical reach and force tools for the independent mechanics improvement.

All results are CALCULATIONS, not measured device performance. SI units except
explicit *_mm fields. The magnetic image model is an upper bound; use field_scale
to examine a stated derating. No values here override the recorded Rev K design.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
from scipy.optimize import brentq, root


def page_to_nib_matrix(tilt_deg: float, roll_deg: float = 0.0) -> np.ndarray:
    """Page axes are along the tilt plane and lateral to it; nib axes rotate with roll.

    A circular mechanical workspace maps to an ellipse on the paper because the
    axially sliding refill maintains contact. This is a local, constant-pose
    Jacobian; large pose changes need a new matrix.
    """
    if not 0.0 < tilt_deg <= 90.0:
        raise ValueError("tilt must be in (0, 90] degrees")
    p = math.radians(roll_deg)
    rot = np.array([[math.cos(p), math.sin(p)], [-math.sin(p), math.cos(p)]])
    return rot @ np.diag([math.sin(math.radians(tilt_deg)), 1.0])


def radial_project(q: Sequence[float], radius: float) -> np.ndarray:
    q = np.asarray(q, float)
    if q.shape != (2,) or not np.all(np.isfinite(q)) or radius <= 0:
        raise ValueError("finite 2D displacement and positive radius required")
    return q * min(1.0, radius / max(float(np.linalg.norm(q)), 1e-30))


def harmonic_force_rms(mass: float, stiffness: float, damping: float,
                       frequency: float, displacement_rms: float) -> float:
    if min(mass, damping, frequency, displacement_rms) < 0:
        raise ValueError("mass, damping, frequency and displacement must be nonnegative")
    w = 2 * math.pi * frequency
    return displacement_rms * math.hypot(stiffness - mass * w * w, damping * w)


def wire_anchor(q: float, length: float = 26.801041139863813e-3,
                diameter: float = 0.10e-3, young: float = 127.6e9,
                n_wires: int = 4, anchor_stiffness: float = 10000.0,
                assembly_tension: float = 0.0, kt: float = 1.8,
                fatigue_strength: float = 310e6 * 0.85,
                ultimate_strength: float = 1280e6) -> dict:
    """Fixed-guided beam-column wires coupled to an axial floating anchor.

    At imposed lateral q, solve P = P_assembly + K_series * integral(y'^2)/2.
    y is the exact linear beam-column displacement shape at this tension P/n.
    The geometric compatibility is second order in slope, valid here q/L <0.1.
    P_assembly is TOTAL tension across n_wires. Anchor stiffness includes the
    diaphragm, flex cable and wiring in parallel; a cable can spoil the design.
    """
    if min(length, diameter, young, n_wires, anchor_stiffness) <= 0 or assembly_tension < 0:
        raise ValueError("positive dimensions/stiffness and nonnegative assembly tension required")
    from bnib.flexure import k_wire_lateral
    area = math.pi * diameter ** 2 / 4
    inertia = math.pi * diameter ** 4 / 64
    kw_ax = n_wires * young * area / length
    kseries = kw_ax * anchor_stiffness / (kw_ax + anchor_stiffness)
    nodes, weights = np.polynomial.legendre.leggauss(64)
    s, wg = (nodes + 1) / 2, weights / 2

    def shape(total_tension):
        x = math.sqrt(total_tension / n_wires / (young * inertia)) * length
        if x < 1e-3:
            slope = q / length * 6 * s * (1 - s)
            curv = q / length ** 2 * 6 * (1 - 2 * s)
            root_curvature = 6 * q / length ** 2
        else:
            a = x * (s - 0.5)
            # Scaled hyperbolic functions stay finite even with a rigid anchor.
            cr = (np.exp(a - x / 2) + np.exp(-a - x / 2)) / (1 + math.exp(-x))
            sr = (np.exp(a - x / 2) - np.exp(-a - x / 2)) / (1 + math.exp(-x))
            mean = 1 - 2 * math.tanh(x / 2) / x
            slope = q / length * (1 - cr) / mean
            curv = -q / length ** 2 * x * sr / mean
            root_curvature = q / length ** 2 * x * math.tanh(x / 2) / mean
        elongation = 0.5 * length * float(wg @ slope ** 2)
        bend_energy = 0.5 * n_wires * young * inertia * length * float(wg @ curv ** 2)
        return elongation, bend_energy, root_curvature

    upper = assembly_tension + kseries * 0.61 * q ** 2 / length + 1e-12
    if abs(q) < 1e-16:
        tension = assembly_tension
    else:
        tension = brentq(lambda p: p - assembly_tension - kseries * shape(p)[0],
                         assembly_tension, upper, xtol=1e-13)
    elongation, bend_energy, curvature = shape(tension)
    extra = tension - assembly_tension
    force = n_wires * k_wire_lateral(young, inertia, length, tension / n_wires) * q
    anchor_motion = extra / anchor_stiffness
    stress_bend = abs(curvature) * young * diameter / 2 * kt
    # Reversal q -> -q reverses bending; geometric axial stress runs 0..peak
    # twice per cycle. Conservatively add its alternating half to bending.
    stress_axial_amp = extra / (n_wires * area) / 2
    stress_mean = assembly_tension / (n_wires * area) + stress_axial_amp
    sf = 1.0 / max((stress_bend + stress_axial_amp) / fatigue_strength + stress_mean / ultimate_strength, 1e-30)
    return {"displacement_m": q, "tension_total_N": tension, "extra_tension_N": extra,
            "elongation_m": elongation, "anchor_motion_m": anchor_motion,
            "wire_stretch_m": extra / kw_ax, "lateral_force_N": force,
            "linear_lateral_force_N": n_wires * 12 * young * inertia / length ** 3 * q,
            "bend_stress_MPa": stress_bend / 1e6, "goodman_sf_conservative": sf,
            "elastic_energy_J": bend_energy + 0.5 * extra ** 2 / kseries + assembly_tension * elongation,
            "wire_axial_stiffness_N_m": kw_ax, "anchor_stiffness_N_m": anchor_stiffness,
            "small_slope_ratio": abs(q) / length,
            "model": "self-consistent beam-column + second-order arc length; material fatigue unmeasured"}


def thrust_guide(moment_xy: Sequence[float], axial_force: float = 0.0,
                 preload_per_race: float = 4.0, balls_per_race: int = 6,
                 ball_radius: float = 0.4e-3, circle_radius: float = 8.3e-3,
                 effective_modulus: float | None = None, rolling_coefficient: float = 0.001) -> dict:
    """Opposed preloaded sphere-on-flat races with unilateral Hertz contacts.

    Preload is INTERNAL ball load on EACH race, not wave-spring force on a
    retaining seat. These differ: a seat spring does not prove ball preload or
    clamp an impact force. Both flat contacts of each ball deform in series.
    Races/mounts are rigid in this calculation; reported rigidity is an upper
    bound until race, seat and shell compliance are measured.
    """
    if min(preload_per_race, ball_radius, circle_radius, balls_per_race) <= 0:
        raise ValueError("positive guide geometry and internal preload required")
    E = effective_modulus or 1 / ((1 - .27 ** 2) / 310e9 + (1 - .3 ** 2) / 200e9)
    hertz = 4 / 3 * E * math.sqrt(ball_radius) / 2 ** 1.5
    indent0 = (preload_per_race / balls_per_race / hertz) ** (2 / 3)
    a = np.arange(balls_per_race) * 2 * math.pi / balls_per_race
    # Coordinates scaled so root's three unknowns all have displacement units.
    A = np.column_stack([np.ones_like(a), np.sin(a), -np.cos(a)])
    target = np.r_[axial_force, np.asarray(moment_xy, float) / circle_radius]

    def contacts(u):
        gap = A @ u
        dp, dm = np.maximum(indent0 + gap, 0), np.maximum(indent0 - gap, 0)
        return hertz * dp ** 1.5, hertz * dm ** 1.5, 1.5 * hertz * (np.sqrt(dp) + np.sqrt(dm))

    def fun(u):
        plus, minus, _ = contacts(u)
        return A.T @ (plus - minus) - target

    def jac(u):
        return A.T @ (contacts(u)[2][:, None] * A)

    sol = root(fun, np.zeros(3), jac=jac, tol=1e-11)
    residual = float(np.linalg.norm(fun(sol.x)))
    if residual > 1e-7:
        raise RuntimeError(f"Hertz equilibrium failed: {sol.message}; residual {residual}")
    plus, minus, _ = contacts(sol.x)
    loads = np.r_[plus, minus]
    radii = (3 * loads * ball_radius / (4 * E)) ** (1 / 3)
    stress = np.divide(3 * loads, 2 * math.pi * radii ** 2, out=np.zeros_like(loads), where=loads > 0)
    trans = np.diag([1, circle_radius, circle_radius])
    K = trans @ jac(sol.x) @ trans
    return {"loads_per_ball_N": loads.tolist(), "total_normal_load_N": float(loads.sum()),
            "max_ball_load_N": float(loads.max()), "min_ball_load_N": float(loads.min()),
            "unloaded_contacts": int(np.sum(loads <= 1e-12)), "max_hertz_GPa": float(stress.max() / 1e9),
            "rolling_force_N": rolling_coefficient * float(loads.sum()),
            "axial_displacement_m": float(sol.x[0]), "tilt_rad": (sol.x[1:] / circle_radius).tolist(),
            "stiffness_matrix": K.tolist(), "min_tilt_stiffness_Nm_rad": float(np.linalg.eigvalsh(K[1:, 1:]).min()),
            "equilibrium_residual_N": residual, "preload_per_race_N": preload_per_race,
            "race_compliance_included": False, "drop_rating": "UNKNOWN: requires spring rate, stop path and impact model"}


@dataclass(frozen=True)
class CoilShape:
    x_in: float
    y_in: float
    bundle: float
    row_centre: float

    @property
    def outer_radius(self):
        return math.hypot(self.x_in + self.bundle, self.row_centre + self.y_in + self.bundle)

    @property
    def inner_edge(self):
        return self.row_centre - self.y_in - self.bundle


def winding_map(g, shape: CoilShape, positions: np.ndarray, order: str = "xy",
                insulation: float = .05e-3, field_scale: float = 1.0,
                quadrature: tuple[int, int, int] = (3, 2, 12)) -> dict:
    """Signed 6D wrench per sqrt(coil copper W), including actual end turns.

    x/y winding packs share a fixed axial stack. Additional interlayer insulation
    consumes available copper thickness; it is not free. Equal turns are assumed
    in same-axis sublayers connected in series. Rounded winding corners, iron
    saturation, joint resistance and manufacturing scatter remain unmeasured.
    """
    from bnib.magnetics import sources
    from .nib import _racetrack_filaments, RHO_CU, CU_DENS
    positions = np.asarray(positions, float)
    if positions.ndim != 2 or positions.shape[1] != 2:
        raise ValueError("positions must be an N x 2 array")
    if set(order) != {"x", "y"} or order.count("x") != order.count("y"):
        raise ValueError("equal nonzero counts of x and y slabs required")
    n = len(order)
    height = g.t_x + g.t_y
    active = (height - (n - 1) * insulation) / n
    if active <= 0 or field_scale <= 0:
        raise ValueError("positive active copper thickness and field scale required")
    from dataclasses import replace
    local = replace(g, t_x=active, t_y=active)
    src = sources(g)
    nb, nt, nl = quadrature
    result = np.zeros((len(positions), 6, 2))
    mass = []
    lengths = []
    for j, axis in enumerate(("x", "y")):
        sublayers = [i for i, char in enumerate(order) if char == axis]
        force = np.zeros((len(positions), 6))
        for layer_index in sublayers:
            p, dl, weights = _racetrack_filaments(local, shape.x_in, shape.y_in, shape.bundle,
                                                 shape.row_centre, axis, nb, nt, nl)
            old_z = local.t_m + local.c0 + (local.t_x if axis == "y" else 0)
            new_z = g.t_m + g.c0 + layer_index * (active + insulation)
            p[:, 2] += new_z - old_z
            points = np.broadcast_to(p, (len(positions), *p.shape)).copy()
            points[:, :, :2] += positions[:, None, :]
            B = src.getB(points.reshape(-1, 3)).reshape(points.shape) * field_scale
            df = np.cross(dl[None, :, :], B) * weights[None, :, None]
            # Mechanical centre at moving winding centre, not fixed world axis.
            arm = p.copy()
            arm[:, 2] -= g.t_m + g.c0 + height / 2
            force[:, :3] += df.sum(axis=1) / len(sublayers)
            force[:, 3:] += np.cross(arm[None, :, :], df).sum(axis=1) / len(sublayers)
        mean_turn_length = 4 * (shape.x_in + shape.y_in + shape.bundle)
        area = shape.bundle * active * len(sublayers)
        normalization = math.sqrt(g.k_fill * area / (2 * RHO_CU * mean_turn_length))
        # The reflected y racetrack has reversed orientation. Normalize polarity
        # to a positive requested axis using the centre, keeping all offdiagonals.
        sign = 1.0 if axis == "x" else -1.0
        result[:, :, j] = sign * force * normalization
        mass.append(2 * CU_DENS * g.k_fill * area * mean_turn_length)
        lengths.append(mean_turn_length)
    singular = np.linalg.svd(result[:, :2, :], compute_uv=False)
    return {"positions_m": positions, "wrench_per_sqrtW": result,
            "min_singular_N_sqrtW": singular[:, -1], "max_singular_N_sqrtW": singular[:, 0],
            "copper_mass_kg": np.array(mass), "order": order, "insulation_m": insulation,
            "active_thickness_per_axis_m": active * len(order) / 2,
            "field_scale": field_scale, "mean_turn_length_m": lengths,
            "label": "CALCULATION: analytical cuboid magnets with infinite-permeability iron images; upper bound"}


def electrical_allocation(km_matrix: np.ndarray, desired_force: Sequence[float], velocity: Sequence[float],
                          coil_resistance: float = 2.5, lead_resistance: float = .536,
                          temperature_rise: float = 90.0, voltage: float = 3.3,
                          current_limit: float = 1.0, copper_power_limit: float = .15,
                          driver_resistance: float = .24) -> dict:
    """Preserve desired force direction while meeting 2D current/voltage/heat bounds.

    Back-EMF follows reciprocity e = Kf.T v. Inductive transient voltage is NOT
    included: the caller must reserve L di/dt headroom before using this in a
    servo. Thermal cap is an input, not a validated temperature prediction.
    """
    K = np.asarray(km_matrix, float) * math.sqrt(coil_resistance)
    F, v = np.asarray(desired_force, float), np.asarray(velocity, float)
    if K.shape != (2, 2) or not np.all(np.isfinite(K)) or np.linalg.cond(K) > 1e8:
        raise ValueError("finite, nonsingular 2 x 2 force matrix required")
    if min(coil_resistance, voltage, current_limit, copper_power_limit) <= 0 or min(lead_resistance, driver_resistance) < 0:
        raise ValueError("invalid electrical limits")
    Rcu = (coil_resistance + lead_resistance) * (1 + .00393 * temperature_rise)
    if Rcu <= 0:
        raise ValueError("temperature gives nonpositive copper resistance")
    i = np.linalg.solve(K, F)
    emf = K.T @ v
    upper = min(1.0, current_limit / max(float(np.max(np.abs(i))), 1e-30),
                math.sqrt(copper_power_limit / max(float(i @ i) * Rcu, 1e-30)))
    lower = 0.0
    for slope, offset in zip((Rcu + driver_resistance) * i, emf):
        if abs(slope) < 1e-15:
            if abs(offset) > voltage:
                return {"feasible": False, "reason": "back_emf_exceeds_bus", "authority": 0.0}
        else:
            a, b = sorted(((-voltage - offset) / slope, (voltage - offset) / slope))
            lower, upper = max(lower, a), min(upper, b)
    if upper < lower or upper < 0:
        return {"feasible": False, "reason": "no_electrical_solution", "authority": 0.0}
    current = i * upper
    return {"feasible": True, "authority": upper, "force_N": (K @ current).tolist(),
            "current_A": current.tolist(), "voltage_V": ((Rcu + driver_resistance) * current + emf).tolist(),
            "copper_power_W": float(current @ current) * Rcu,
            "requested_current_A": i.tolist(), "back_emf_V": emf.tolist(),
            "requested_copper_power_W": float(i @ i) * Rcu,
            "inductive_voltage_included": False}
