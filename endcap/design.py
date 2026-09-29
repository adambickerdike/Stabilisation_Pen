r"""Parametric end-cap designs inside the envelope (PROPOSED DESIGN models; CALC with labelled inputs).

Classes (key: arrangement)
  LRM2  active reaction mass, 2 lateral axes: tungsten slug on flexures, moving-magnet flat coils (as the Rev H module)
  TMD   the same slug as a passive tuned-mass damper (for the screen only)
  SP2   two scissored pairs of single-gimbal CMGs (4 rotors, spin axis along the pen axis, gimbals transverse): 2-axis torque
  SP1   one scissored pair (2 rotors): 1-axis torque (the tilt plane)
  DG1   one rotor on a 2-axis (double) gimbal: 2-axis torque H delta_dot per axis, net momentum H
  DG2   two counter-spinning rotors, each on a double gimbal, driven in opposite trajectories (Walker et al. 2018, HAP-82):
        2-axis torque 2 H delta_dot per axis, no net momentum
  PL2   two rotors spinning across the pen, both gimballed about the pen axis ('planar' pair, biased +/-60 deg):
        2-axis torque 1.73 H delta_dot (scissor axis) and 1.0 H delta_dot (common axis), net momentum H
  RW2   two reaction wheels (flat BLDC + tungsten ring), 2 axes
  PG    passive gyroscope: one rotor spinning along the pen axis (gyroscopic 'stiffening')
  PROP  ducted micro-propellers (limiting case: the only steady ungrounded force)
Every design returns masses (moving, fixed), the force/torque limit as a function of frequency, powers, spin-up time,
stored energy, rotor stress, imbalance force, fit margins and constraint violations.  Torch tensors pass through, so the
optimiser can differentiate every continuous variable.
Evidence status: PROPOSED DESIGN + CALCULATION.  Dimensions and several part masses are ASSUMPTIONS (params.LABELS).
"""
from __future__ import annotations

import math
from typing import Dict

import torch

from . import params as P

T = torch.as_tensor
SHELL_M = P.RHO_PEEK * math.pi / 4 * (P.ENV["od"] ** 2 - P.D_IN ** 2) * P.ENV["length"]   # 4.6 g end-cap shell (CALC)
ELEC_M = 1.5e-3            # drivers and wiring (ASSUMPTION)
CLEAR = 0.5e-3             # radial clearance (ASSUMPTION)
X_MAX = 4.0e-3             # largest lateral stroke of a 2-axis flexure suspension in a 24 mm bore (ASSUMPTION)
FRAME_RADIAL = 1.5e-3      # radial space taken by each gimbal ring around a rotor (ASSUMPTION)


def _t(x):
    return x if torch.is_tensor(x) else torch.tensor(float(x))


def relu(x):
    return torch.clamp(x, min=0.0)


def windage_t(D, t, gap, n_rpm):
    """Torch version of sim/handpen/devices.windage (laminar Couette rim with a Taylor factor 2 above Ta = 1700, plus
    enclosed-disc faces, Daily-Nece regime I).  CALC."""
    w = n_rpm * P.TWO_PI / 60.0
    r = D / 2
    nu = P.MU_AIR / P.RHO_AIR
    rim = 2 * math.pi * P.MU_AIR * r ** 3 * t * w / gap
    Ta = w ** 2 * r * gap ** 3 / nu ** 2
    rim = rim * (1.0 + torch.sigmoid((Ta - 1700.0) / 100.0))        # smooth step to the factor 2
    Re = w * r * r / nu
    Cm = 2 * math.pi / ((gap / r) * Re)
    face = 0.5 * P.RHO_AIR * w ** 2 * r ** 5 * Cm * 2
    return rim + face


def spin_rotor(D, t, n, motor: P.Motor, gap=0.4e-3):
    """Rotor mass, polar inertia, momentum, drag torque and holding power (per rotor)."""
    m = P.RHO_WHA * math.pi / 4 * (D * D - (2e-3) ** 2) * t
    J = m * (D * D + (2e-3) ** 2) / 8 + motor.J
    w = n * P.TWO_PI / 60.0
    H = J * w
    drag = motor.C0 + motor.Cv * n + windage_t(D, t, gap, n) + P.BEARING_FRICTION
    I = drag / motor.kM
    Pw = drag * w + I * I * motor.R + P.DRIVER_Q_W
    return dict(m=m, J=J, H=H, drag=drag, P=Pw, w=w)


def power_limited_torque(motor: P.Motor, w, P_share):
    """Motor torque (N m) at speed w (rad/s) when the electrical input is capped at P_share: the current solves
    I^2 R + I kM w = P_share, also capped by the stall torque (CALC)."""
    kM, R = motor.kM, motor.R
    I = (-kM * w + torch.sqrt((kM * w) ** 2 + 4 * R * P_share)) / (2 * R)
    return torch.minimum(kM * I, _t(motor.stall))


def spin_extras(rot, motor: P.Motor, n, D, n_rot):
    """Spin-up (s) with the 1 W peak budget shared by the rotors (torque evaluated at half speed minus half the drag;
    endcap/design.spin_up_numeric integrates it exactly), stored energy (J, total), centre stress (Pa), imbalance force at
    G2.5 and G0.4 (N, per rotor), tone (Hz)."""
    tq = power_limited_torque(motor, 0.5 * rot["w"], P.ENV["p_peak"] / n_rot)
    su = rot["J"] * rot["w"] / relu(tq - 0.5 * rot["drag"]).clamp(min=1e-9)
    E = 0.5 * rot["J"] * rot["w"] ** 2 * n_rot
    sig = (3 + P.NU_WHA) / 8 * P.RHO_WHA * rot["w"] ** 2 * (D / 2) ** 2
    imb = rot["m"] * P.BALANCE_G["nominal"] * rot["w"]
    imb_best = rot["m"] * P.BALANCE_G["best"] * rot["w"]
    return dict(spin_up_s=su, E_J=E, stress_Pa=sig, imb_N=imb, imb_best_N=imb_best, tone_Hz=n / 60.0)


# ================================================================================================== designs
def lrm2(x: Dict, P_axis=0.5, f_c=5.0):
    """Active 2-axis reaction mass.  x: d_s (slug diameter), L_s (slug length), t_c (coil thickness per side).
    Radial budget per side: magnet 1.0 mm + coil t_c + clearance 0.5 mm; stroke X = (D_in - d_s)/2 - that budget."""
    d_s, L_s, t_c = _t(x["d_s"]), _t(x["L_s"]), _t(x["t_c"])
    t_m = 1.0e-3
    X = (P.D_IN - d_s) / 2 - t_m - t_c - CLEAR
    m_slug = P.RHO_WHA * math.pi / 4 * d_s ** 2 * L_s
    L_mag = torch.clamp(L_s, max=12e-3)
    m_mag = P.RHO_NDFEB * 0.5 * math.pi * d_s * L_mag * t_m
    L_coil = L_mag + 2 * relu(X)
    m_cu = P.RHO_CU * 0.6 * 0.5 * math.pi * (P.D_IN - t_c) * L_coil * t_c
    # Km (N/sqrt(W)) per axis: sqrt(copper) law calibrated to the Rev H module (0.9 at 4 g), times the share of each turn that
    # sits under the magnet (L_mag / L_coil, reference 12 / 17.5 mm) and the gap-flux factor t_m / (t_m + t_c + clearance)
    # (reference coil 1.0 mm).  A crude lumped magnetic model (ASSUMPTION; bench EXP-K03 measures Km).
    alpha = L_mag / L_coil
    Bf = (t_m / (t_m + t_c + CLEAR)) / (1.0e-3 / 2.5e-3)
    Km = P.KM_LRM_PER_SQRT_G_CU * torch.sqrt(m_cu * 1e3) * (alpha / (12.0 / 17.5)) * Bf
    F_act = Km * math.sqrt(P_axis)
    m_r = m_slug + m_mag
    m_frame = 3.0e-3 + 0.1 * m_slug
    m_fix = m_cu + m_frame + SHELL_M + ELEC_M
    k_c = m_r * (P.TWO_PI * f_c) ** 2
    c_c = 2 * 0.7 * torch.sqrt(k_c * m_r)
    L_ax = L_s + 9e-3                                   # flexure plates 2 x 3 mm + driver board 3 mm (ASSUMPTION)
    viol = dict(stroke=relu(0.5e-3 - X) / 1e-3, flexure=relu(X - X_MAX) / 1e-3, length=relu(L_ax - P.ENV["length"]) / 1e-3)
    return dict(cls="LRM2", m_r=m_r, m_fix=m_fix, m_total=m_r + m_fix, X=X, Km=Km, F_act=F_act, k_c=k_c, c_c=c_c,
                z_r=P.Z_CAP, z_fix=P.Z_CAP, P_spin=_t(0.0), axes=2, viol=viol,
                parts=dict(slug_g=m_slug * 1e3, magnets_g=m_mag * 1e3, copper_g=m_cu * 1e3, frame_g=m_frame * 1e3,
                           shell_g=SHELL_M * 1e3, electronics_g=ELEC_M * 1e3))


def lrm_limit(d, f, eta=0.7):
    """Largest COIL force amplitude per axis (the linear model's input acts between the slug and the pen): the coil limit
    F_act, or the force that drives the slug on its flexure (k_c, c_c) through eta x the stroke,
    eta X |k_c - m w^2 + j c_c w|.  Below the flexure resonance most of this force is taken by the spring, so the NET force
    on the pen stays at most eta m w^2 X (the stroke-limited inertial force)."""
    w = P.TWO_PI * f
    dyn = torch.sqrt((d["k_c"] - d["m_r"] * w * w) ** 2 + (d["c_c"] * w) ** 2)
    lim = torch.minimum(d["F_act"], eta * relu(d["X"]) * dyn)
    return torch.stack([lim, lim])


def cmg(x: Dict, arr="SP2", motor="0620B"):
    """CMG clusters.  x: D (rotor diameter), t (thickness), n (rpm), delta (gimbal half-range, rad).
    Fit (ASSUMPTION geometry): spin-along-axis arrangements (SP1, SP2, DG1, DG2) need per rotor an axial length
    D sin(delta) + (t + L_motor) cos(delta) + 1 mm and D <= D_in - 1 mm; PL2 stands each disc in an axial plane:
    axial D + 2 mm per rotor, and (t + L_motor)/2 and D/2 must fit in the bore circle."""
    mot = P.MOTORS[motor]
    D, t, n, dl = _t(x["D"]), _t(x["t"]), _t(x["n"]), _t(x["delta"])
    rot = spin_rotor(D, t, n, mot)
    n_rot = {"SP2": 4, "SP1": 2, "DG1": 1, "DG2": 2, "PL2": 2}[arr]
    n_gd = {"SP2": 2, "SP1": 1, "DG1": 2, "DG2": 2, "PL2": 2}[arr]
    rate = P.GIMBAL_DRIVE["rate_max"]
    m_rot_assy = n_rot * (rot["m"] + mot.m + 2 * P.BEARINGS["618/4"]["m"] + P.FRAME_PER_ROTOR)
    m_fix = m_rot_assy + n_gd * P.GIMBAL_DRIVE["m"] + SHELL_M + ELEC_M + 0.3e-3 * n_rot
    h = t + mot.L
    if arr == "PL2":
        L_ax = n_rot * (D + 2e-3)
        rad = torch.sqrt((h / 2) ** 2 + (D / 2) ** 2) - (P.D_IN / 2 - CLEAR - FRAME_RADIAL)
        dl_eff = torch.clamp(dl, max=0.5)
        k_axes = (1.73, 1.0)
        H_net = rot["H"]
    else:
        L_ax = n_rot * (D * torch.sin(dl) + h * torch.cos(dl) + 1e-3)
        rings = 2 if arr in ("DG1", "DG2") else 1
        # swept radius of the tilting stack about a pivot at the rotor centre: the disc (at most sqrt((D/2)^2 + (t/2)^2))
        # and the spin motor on one side (d_m/2 cos(delta) + (t/2 + L_m) sin(delta), for delta below its maximum)
        r_disc = torch.sqrt((D / 2) ** 2 + (t / 2) ** 2)
        r_mot = mot.d / 2 * torch.cos(dl) + (t / 2 + mot.L) * torch.sin(dl)
        rad = torch.maximum(r_disc, r_mot) - (P.D_IN / 2 - CLEAR - rings * FRAME_RADIAL)
        dl_eff = dl
        k_axes = {"SP2": (2.0, 2.0), "SP1": (2.0, 0.0), "DG1": (1.0, 1.0), "DG2": (2.0, 2.0)}[arr]
        H_net = rot["H"] if arr == "DG1" else _t(0.0)
    ex = spin_extras(rot, mot, n, D, n_rot)
    P_spin = n_rot * rot["P"]
    viol = dict(length=relu(L_ax - P.ENV["length"]) / 1e-3, radial=relu(rad) / 1e-3,
                speed=relu(n - min(P.N_SPIN_MAX, mot.n_max)) / 1e3, spin_up=relu(ex["spin_up_s"] - 10.0),
                energy=relu(ex["E_J"] - 3.0), thin=relu(1.0e-3 - t) / 1e-3)
    return dict(cls=arr, motor=motor, H=rot["H"], m_rotor=rot["m"], J_rotor=rot["J"], n_rot=n_rot, m_r=_t(0.0), m_fix=m_fix,
                m_total=m_fix, rate=rate, delta=dl_eff, k_axes=k_axes, P_spin=P_spin, H_net=H_net, L_ax=L_ax,
                z_fix=P.Z_CAP, axes=sum(1 for k in k_axes if k > 0), viol=viol, extras=ex,
                parts=dict(rotors_g=n_rot * rot["m"] * 1e3, spin_motors_g=n_rot * mot.m * 1e3,
                           bearings_g=n_rot * 2 * P.BEARINGS["618/4"]["m"] * 1e3, frames_g=n_rot * P.FRAME_PER_ROTOR * 1e3,
                           gimbal_drives_g=n_gd * P.GIMBAL_DRIVE["m"] * 1e3, shell_g=SHELL_M * 1e3,
                           electronics_g=(ELEC_M + 0.3e-3 * n_rot) * 1e3))


def cmg_limit(d, f):
    w = P.TWO_PI * f
    base = d["H"] * torch.minimum(_t(d["rate"]), w * d["delta"])
    return torch.stack([base * d["k_axes"][0], base * d["k_axes"][1]])


def cmg_gimbal_power(d, f, tau_amp):
    """Gimbal-drive power (W) to produce torque amplitudes tau_amp (2,) at f: gimbal angle amplitude delta = tau/(k H w),
    torque on the drive J_g w^2 delta (gimbal inertia = half the rotor polar inertia + motor, ASSUMPTION), mechanical power
    0.5 tau_g w delta per gimbal, divided by the drive efficiency (ASSUMPTION)."""
    w = P.TWO_PI * f
    out = _t(0.0)
    for i, k in enumerate(d["k_axes"]):
        if k <= 0:
            continue
        dl = tau_amp[i] / (k * d["H"] * w)
        J_g = P.GIMBAL_DRIVE["J_rotor_frac"] * d["J_rotor"] * (d["n_rot"] / max(1, len([kk for kk in d["k_axes"] if kk > 0])))
        tq = J_g * w * w * dl
        out = out + 0.5 * tq * w * dl / P.GIMBAL_DRIVE["eta"]
    return out


def rw2(x: Dict, motor="0824B"):
    """Two reaction wheels (tungsten ring on a flat or slotless BLDC).  x: D (ring OD), t (ring thickness), nb (bias rpm).
    Torque <= motor rated torque (continuous) or kM sqrt(P_cu/R) with P_cu = (P_peak - P_spin)/2 per wheel (peak); speed
    swing <= min(nb, n_max/2 - nb)."""
    mot = P.MOTORS[motor]
    D, t, nb = _t(x["D"]), _t(x["t"]), _t(x["nb"])
    m_w = P.RHO_WHA * math.pi / 4 * (D ** 2 - (D - 4e-3) ** 2) * t     # 2 mm wide ring
    J = m_w * (D ** 2 + (D - 4e-3) ** 2) / 8 + mot.J
    w_b = nb * P.TWO_PI / 60
    dW = torch.minimum(w_b, (mot.n_max * 0.5) * P.TWO_PI / 60 - w_b).clamp(min=0.0)
    drag = mot.C0 + mot.Cv * nb + windage_t(D, t, 0.4e-3, nb)
    P_spin = 2 * (drag * w_b + (drag / mot.kM) ** 2 * mot.R + P.DRIVER_Q_W)
    # peak torque from the copper power left in the peak budget after the bias spin (per wheel)
    P_cu = ((P.ENV["p_peak"] - P_spin) / 2).clamp(min=1e-6)
    tau_pk = torch.minimum(_t(mot.stall), mot.kM * torch.sqrt(P_cu / mot.R))
    m_fix = 2 * (m_w + mot.m + 0.5e-3) + SHELL_M + ELEC_M
    L_ax = 2 * (torch.maximum(D, _t(mot.d)) + 2e-3)
    rad = torch.sqrt(((t + mot.L) / 2) ** 2 + (torch.maximum(D, _t(mot.d)) / 2) ** 2) - (P.D_IN / 2 - CLEAR)
    viol = dict(length=relu(L_ax - P.ENV["length"]) / 1e-3, radial=relu(rad) / 1e-3)
    return dict(cls="RW2", motor=motor, J=J, dW=dW, tau_pk=tau_pk, tau_rated=_t(mot.rated), m_r=_t(0.0), m_fix=m_fix,
                m_total=m_fix, P_spin=P_spin, z_fix=P.Z_CAP, axes=2, viol=viol, mot=mot,
                parts=dict(rings_g=2 * m_w * 1e3, motors_g=2 * mot.m * 1e3, shell_g=SHELL_M * 1e3, electronics_g=ELEC_M * 1e3))


def rw_limit(d, f, peak=True):
    w = P.TWO_PI * f
    lim = torch.minimum(d["tau_pk"] if peak else d["tau_rated"], d["J"] * w * d["dW"])
    return torch.stack([lim, lim])


def pg(x: Dict, motor="0620B"):
    """Passive gyroscope: one rotor along the pen axis.  x: D, t, n."""
    mot = P.MOTORS[motor]
    D, t, n = _t(x["D"]), _t(x["t"]), _t(x["n"])
    rot = spin_rotor(D, t, n, mot)
    ex = spin_extras(rot, mot, n, D, 1)
    m_fix = rot["m"] + mot.m + 2 * P.BEARINGS["618/4"]["m"] + 1.0e-3 + SHELL_M + ELEC_M
    viol = dict(radial=relu(D / 2 - (P.D_IN / 2 - CLEAR)) / 1e-3, speed=relu(n - min(P.N_SPIN_MAX, mot.n_max)) / 1e3,
                spin_up=relu(ex["spin_up_s"] - 10.0), energy=relu(ex["E_J"] - 3.0))
    return dict(cls="PG", motor=motor, H=rot["H"], H_gyro=rot["H"], m_r=_t(0.0), m_fix=m_fix, m_total=m_fix, P_spin=rot["P"],
                z_fix=P.Z_CAP, axes=0, viol=viol, extras=ex, m_rotor=rot["m"])


def prop(D=22e-3, n_fans=4, P_elec=1.0):
    """Ducted micro-fans (limiting case): thrust per fan at P_elec shared (CALC, momentum theory, ASSUMPTION FM/eta);
    mass per fan: motor 1.8 g (AMF-127) + propeller and duct 1.3 g (ASSUMPTION)."""
    from . import scaling as SC
    T_fan = SC.prop_thrust(D, P_elec / 2)                   # two fans push along one axis at a time
    return dict(cls="PROP", thrust_N=T_fan, m_total=n_fans * 3.1e-3 + SHELL_M + ELEC_M, P=P_elec,
                note="continuous force only while blowing air out of the end-cap; audible; power at the 1 W peak budget")


def violation(d):
    return sum(v for v in d["viol"].values())


def spin_up_numeric(J, n_target, motor: P.Motor, D, t, n_rot, P_total=None, dt=1e-3, t_max=600.0):
    """Time (s) to reach n_target rpm by explicit integration of J dw/dt = tau_P(w) - drag(w) with the electrical input
    capped at P_total / n_rot (CALC, numpy)."""
    import numpy as np
    P_share = (P.ENV["p_peak"] if P_total is None else P_total) / n_rot
    w_t = n_target * P.TWO_PI / 60.0
    w, tt = 0.0, 0.0
    kM, R = motor.kM, motor.R
    while w < w_t and tt < t_max:
        I = (-kM * w + np.sqrt((kM * w) ** 2 + 4 * R * P_share)) / (2 * R)
        tq = min(kM * I, motor.stall)
        n = w * 60.0 / P.TWO_PI
        drag = motor.C0 + motor.Cv * n + float(windage_t(_t(D), _t(t), 0.4e-3, _t(n))) + P.BEARING_FRICTION
        a = (tq - drag) / J
        if a <= 0:
            return float("inf")
        w += a * dt
        tt += dt
    return tt
