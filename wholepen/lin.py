r"""Reduced linear model of the hand, the grip, an optional pivot collar, the pen, tail devices and the paper (CALC).

Small motions about the writing pose, frequency domain, torch float64/complex128 so that every response is
differentiable in the design parameters (exact gradients through the complex solve; optimise.py uses them).

Frames (sim2 / H1): page frame x, y in the page, z out of it; pen axis a (ball -> cap) at altitude theta (azimuth 0):
a = (cos th, 0, sin th), t1 = (sin th, 0, -cos th) (tilt plane, toward the paper side), t2 = (0, 1, 0).  A point of the
pen at distance z behind the ball is P(z) = z a.

Bodies (6 generalised coordinates each about a reference point O: translation u of O and a small rotation vector phi;
a point P moves u + phi x (P - O)):
  hand    the H1 hand: the HAP-26 hand mass M on the arm spring (k_arm, b_arm) to the imposed tremor path, rotations
          locked (H1's hand frame translates only; LIT HAP-26 via sim2 params.HandH1)
  pen     the Rev J pen with the nose held centred (mass, centre of mass and transverse inertia from the lead's parts,
          CALC: 87.3 g, 86.0 mm, 9.84e-5 kg m^2), plus any rigidly added tail mass
  collar  (pivot designs only) the ring or saddle the fingers and web hold; the pen hangs in a 2-axis gimbal at z_p
          inside it: translational constraint (penalty 1e6 N/m) and rotational stiffness K_c / damping c_c about t1, t2
          (roll locked)
  tmd     (tuned or reaction mass) a point mass at z_m on transverse springs k (t1, t2) and dampers c; axial locked
  gimbal  (CMG scissored pair per axis) one coordinate per pair: inertia J_g, centring stiffness k_g, damping c_g, the
          gyroscopic coupling 2h between the gimbal rate and the pen's rotation about the output axis o = g x a
          (conservative, skew-symmetric; derivation in the docstring of add_cmg_pair)
Grip: H1's two-zone grip (sim/handpen/grip.calibrate, read-only): finger zone at z_f (transverse k_f, axial k_a, pad
tilt stiffness kappa_f), web zone at z_w (transverse k_w), roll k_roll; damping stiffness-proportional (beta).  It
reproduces the HAP-26 tip impedance (575 N/m, 1.3 N s/m) exactly for any split r_rot (CALC, checked in the tests).
Paper: the pen's tip point on a stiff normal spring (1e5 N/m, 10 N s/m) and an in-plane viscous drag c_p (0: the
frictionless bound of study K; the describing function of Coulomb friction 4 mu N / (pi w X) otherwise).
Inputs (unit generalised forces): tremor path (ground motion of the arm spring), torque on the pen, force pair
pen-tmd, torque pair collar-pen, force on the pen tip from the paper (heel), force on the hand from the paper (sled).
Output: the pen tip (ink with the nose centred) in the page plane, x and y.
Evidence status: CALCULATION on a PROPOSED DESIGN with LIT/ASSUMPTION hand parameters.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from . import ROOT  # noqa: F401

torch.set_default_dtype(torch.float64)
CT = torch.complex128

# ------------------------------------------------------------------------------------------------ parameters
# Rev J pen, nose centred (CALC from the lead's parts, results/revJ/layout.json via sim2j.revj.lead_parts; +10 % wiring)
PEN = {"m": 87.265e-3, "z_g": 86.044e-3, "J_t": 9.838e-5, "J_a": 5.54e-6, "length": 0.14472,
       "label": "CALC (sim2j.revj.lead_parts, heel drive included, nose centred; the lead's budget 87.0 g, 86.1 mm)"}


@dataclass
class HandP:
    k_nib: float = 575.0      # LIT HAP-26 (tip-referred grip stiffness)
    b_nib: float = 1.3        # LIT HAP-26
    M: float = 0.21           # LIT HAP-26 hand mass
    k_arm: float = 170.0      # LIT HAP-26
    b_arm: float = 11.0       # LIT HAP-26
    r_rot: float = 0.5        # ASSUMPTION (EXP-I01), swept 0.3-0.7
    rho_w: float = 0.3        # ASSUMPTION
    k_roll: float = 0.2       # ASSUMPTION (sim2 params.HandH1)
    z_f: float = 0.032        # finger pads (results/revJ/layout.json hand.finger_pads_z 26/32/38 mm)
    z_w: float = 0.092        # thumb-index web (layout hand.web_z)
    grip_scale: float = 1.0   # sensitivity: stiffer / softer grip (x scale on every grip zone)
    web_scale: float = 1.0    # design: a softer (or no) web contact on the pen (saddle, rolling rest)


@dataclass
class Collar:
    """The fingers and web hold the collar; the pen pivots in it at z_p (PROPOSED DESIGN, swept)."""
    z_p: float = 0.032        # pivot position along the pen (m)
    K_c: float = 0.2          # rotational stiffness about t1, t2 (N m/rad)
    c_c: float = 1e-3         # rotational damping (N m s/rad)
    m: float = 12e-3          # collar mass (kg), centred at z_cm
    z_cm: float = 0.032
    J: float = 2.0e-6         # collar transverse inertia about its centre (kg m^2)
    web_on_collar: bool = True  # the web rests on the collar's saddle (True) or still on the pen's tail (False)
    skid_on_collar: bool = False  # V2: the skid ring on the collar carries the writing force; the pen's ball rides on
                                  # its (constant-force) refill spring, so the pen tip has no stiff normal support


@dataclass
class Tail:
    """Mass rigidly added behind the pen (the tail module's fixed parts and, for a CMG, the rotors) (PROPOSED DESIGN)."""
    m: float = 0.0
    z: float = 0.165
    J_t: float = 0.0          # about its own centre


@dataclass
class TMD:
    m: float = 0.030
    z: float = 0.160
    k: float = 0.030 * (2 * math.pi * 5.0) ** 2
    c: float = 0.0


@dataclass
class CMGPair:
    """One scissored CMG pair: output torque about o = g x a, o in {'t1', 't2'} (PROPOSED DESIGN)."""
    h: float = 5e-3           # angular momentum of ONE rotor (N m s)
    J_g: float = 2e-6         # gimbal-axis inertia of the pair (both gimbals, rotors' transverse inertia) (kg m^2)
    k_g: float = 0.0          # centring stiffness on the pair coordinate (N m/rad)
    c_g: float = 0.0          # gimbal damping (N m s/rad)
    out: str = "t1"           # output axis


@dataclass
class Model:
    theta_deg: float = 50.0
    hand: HandP = field(default_factory=HandP)
    pen: Dict = field(default_factory=lambda: dict(PEN))
    tail: Tail = field(default_factory=Tail)
    collar: Optional[Collar] = None
    tmd: Optional[TMD] = None
    cmg: List[CMGPair] = field(default_factory=list)
    c_paper: float = 0.0      # in-plane viscous drag at the tip (N s/m)
    k_n: float = 1.0e5        # paper normal (N/m)
    c_n: float = 10.0
    c_sled: float = 0.0       # viscous hand-to-paper damper (sled), N s/m
    c_heel: float = 0.0       # viscous tip-to-paper damper (heel brake), N s/m
    k_refill: float = 5.0     # V2 only: the ball's normal support through the constant-force refill spring (N/m)
    c_skid: float = 2.0       # V2 only: in-plane drag of the collar's skid ring (N s/m; describing function of
                              # mu_skid 0.12 x 0.85 N at 1 mm, 6 Hz: ASSUMPTION)
    z_skid: float = 0.0098    # skid ring plane and contact radius (results/revJ/layout.json skid ring, sim2 builder)
    r_skid: float = 0.0112


def vectors(theta_deg: float):
    th = math.radians(theta_deg)
    a = np.array([math.cos(th), 0.0, math.sin(th)])
    t1 = np.array([math.sin(th), 0.0, -math.cos(th)])
    t2 = np.array([0.0, 1.0, 0.0])
    return a, t1, t2


def skew(r):
    r = np.asarray(r, float)
    return np.array([[0.0, -r[2], r[1]], [r[2], 0.0, -r[0]], [-r[1], r[0], 0.0]])


def grip_zones(h: HandP):
    """H1's two-zone grip calibrated to the tip impedance (sim/handpen/grip.calibrate, read-only)."""
    from sim.handpen import grip as G
    return G.calibrate(h.k_nib, h.b_nib, h.r_rot, h.rho_w, h.z_f, h.z_w, h.grip_scale, 0.0)


# ------------------------------------------------------------------------------------------------ assembly
class Assembly:
    """M, D, K (torch) of a Model.  Parameters that optimise.py differentiates are passed as torch scalars through
    `par` (names: tail_m, tmd_m, tmd_k, tmd_c, K_c, c_c, z_p, cmg_h, cmg_Jg, cmg_kg, cmg_cg, c_sled, c_heel)."""

    def __init__(self, mdl: Model, par: Optional[Dict[str, torch.Tensor]] = None):
        self.mdl = mdl
        par = par or {}
        self.par = par
        a, t1, t2 = vectors(mdl.theta_deg)
        self.a, self.t1, self.t2 = a, t1, t2
        self.T = torch.tensor(np.column_stack([t1, t2]))            # 3x2 transverse basis
        self.blocks = []
        names = ["hand", "pen"]
        if mdl.collar is not None:
            names.append("collar")
        self.bodies = {nm: 6 * i for i, nm in enumerate(names)}
        n = 6 * len(names)
        self.i_tmd = None
        if mdl.tmd is not None:
            self.i_tmd = n
            n += 2                                                   # transverse t1, t2 of the mass relative to the pen
        self.i_cmg = []
        for _ in mdl.cmg:
            self.i_cmg.append(n)
            n += 1
        self.n = n
        z = lambda: torch.zeros(n, n)
        self.M, self.D, self.K = z(), z(), z()
        self._pen()
        self._hand()
        if mdl.collar is not None:
            self._collar()
        self._grip()
        self._paper()
        if mdl.tmd is not None:
            self._tmd()
        for k, cp in enumerate(mdl.cmg):
            self._cmg(k, cp)

    # ---- helpers
    def g(self, name, default):
        v = self.par.get(name, default)
        return v if torch.is_tensor(v) else torch.tensor(float(v))

    def J(self, body: str, P, torch_ok=False):
        """3 x n point Jacobian of the material point P (page frame, at rest) of a body (origin at the ball).  P may be
        a torch vector (then the Jacobian is differentiable with respect to it, e.g. the collar's pivot position)."""
        Jm = torch.zeros(3, self.n)
        i = self.bodies[body]
        Jm[:, i:i + 3] = torch.eye(3)
        if torch.is_tensor(P):
            z0 = torch.zeros((), dtype=P.dtype)
            Sk = torch.stack([torch.stack([z0, -P[2], P[1]]), torch.stack([P[2], z0, -P[0]]),
                              torch.stack([-P[1], P[0], z0])])
            Jm = Jm.to(P.dtype) if Jm.dtype != P.dtype else Jm
            Jm[:, i + 3:i + 6] = -Sk
        else:
            Jm[:, i + 3:i + 6] = torch.tensor(-skew(P))
        return Jm

    def Jrot(self, body: str):
        Jm = torch.zeros(3, self.n)
        i = self.bodies[body]
        Jm[:, i + 3:i + 6] = torch.eye(3)
        return Jm

    def add_spring(self, J: torch.Tensor, K3: torch.Tensor, C3: Optional[torch.Tensor] = None):
        self.K = self.K + J.T @ K3 @ J
        if C3 is not None:
            self.D = self.D + J.T @ C3 @ J

    def add_rigid(self, body: str, m, zc, Jt, Ja, origin_note=""):
        """Rigid body mass about the ball origin: centre of mass at zc on the axis, inertia Jt (transverse) and Ja
        (axial) about the centre of mass."""
        a = torch.tensor(self.a)
        c = zc * a if torch.is_tensor(zc) else torch.tensor(float(zc) * self.a)
        S = torch.stack([torch.stack([torch.zeros(()), -c[2], c[1]]), torch.stack([c[2], torch.zeros(()), -c[0]]),
                         torch.stack([-c[1], c[0], torch.zeros(())])])
        aa = torch.outer(a, a)
        Jc = Jt * (torch.eye(3) - aa) + Ja * aa
        Mb = torch.zeros(6, 6)
        Mb = Mb.clone()
        top = torch.cat([m * torch.eye(3), -m * S], dim=1)
        bot = torch.cat([m * S, Jc - m * (S @ S)], dim=1)
        Mb = torch.cat([top, bot], dim=0)
        i = self.bodies[body]
        E = torch.zeros(6, self.n)
        E[:, i:i + 6] = torch.eye(6)
        self.M = self.M + E.T @ Mb @ E

    # ---- bodies
    def _pen(self):
        mdl = self.mdl
        p = mdl.pen
        self.add_rigid("pen", torch.tensor(p["m"]), p["z_g"], torch.tensor(p["J_t"]), torch.tensor(p["J_a"]))
        tm = self.g("tail_m", mdl.tail.m)
        if float(tm) > 0 or torch.is_tensor(self.par.get("tail_m")):
            self.add_rigid("pen", tm, mdl.tail.z, self.g("tail_J", mdl.tail.J_t), torch.tensor(1e-9))

    def _hand(self):
        h = self.mdl.hand
        # the hand mass at the grip's elastic centre (a point mass: its position does not matter for a translating body)
        self.add_rigid("hand", torch.tensor(h.M), 0.06, torch.tensor(1e-9), torch.tensor(1e-9))
        i = self.bodies["hand"]
        # arm spring to the (moving) ground; rotations locked (H1)
        Ja = torch.zeros(3, self.n)
        Ja[:, i:i + 3] = torch.eye(3)
        self.J_arm = Ja
        self.add_spring(Ja, h.k_arm * torch.eye(3), h.b_arm * torch.eye(3))
        Jr = self.Jrot("hand")
        self.add_spring(Jr, 1e4 * torch.eye(3), 1.0 * torch.eye(3))

    def _collar(self):
        c = self.mdl.collar
        a = self.a
        self.add_rigid("collar", torch.tensor(c.m), c.z_cm, torch.tensor(c.J), torch.tensor(c.J))
        zp = self.par.get("z_p")
        Pp = zp * torch.tensor(a, dtype=zp.dtype) if torch.is_tensor(zp) else c.z_p * a
        # translational constraint at the pivot (penalty), both bodies' material point at the pivot
        Jd = self.J("pen", Pp) - self.J("collar", Pp)
        self.add_spring(Jd, 1e6 * torch.eye(3), 5.0 * torch.eye(3))
        # rotational spring about t1, t2 (K_c, c_c); roll locked
        Jr = self.Jrot("pen") - self.Jrot("collar")
        T = self.T
        Kc = self.g("K_c", c.K_c)
        cc = self.g("c_c", c.c_c)
        aa = torch.outer(torch.tensor(a), torch.tensor(a))
        self.add_spring(Jr, Kc * (T @ T.T) + 1e3 * aa, cc * (T @ T.T) + 0.01 * aa)
        self.J_piv_rel = Jr                                           # relative rotation pen - collar

    def _grip(self):
        h = self.mdl.hand
        gz = grip_zones(h)
        self.gz = gz
        a, T = torch.tensor(self.a), self.T
        target = "collar" if self.mdl.collar is not None else "pen"
        Pf = h.z_f * self.a
        Pw = h.z_w * self.a
        Kf = gz.k_f * (T @ T.T) + gz.k_a * torch.outer(a, a)
        beta = gz.beta
        Jf = self.J(target, Pf) - self.J("hand", Pf)
        self.add_spring(Jf, Kf, beta * Kf)
        web_body = target if (self.mdl.collar is None or self.mdl.collar.web_on_collar) else "pen"
        kw = gz.k_w * h.web_scale
        Kw = kw * (T @ T.T)
        Jw = self.J(web_body, Pw) - self.J("hand", Pw)
        self.add_spring(Jw, Kw, beta * Kw)
        # pad tilt stiffness kappa_f and roll, between the held body and the (non-rotating) hand frame
        Jr = self.Jrot(target) - self.Jrot("hand")
        Kr = gz.kappa_f * (T @ T.T) + h.k_roll * torch.outer(a, a)
        self.add_spring(Jr, Kr, beta * Kr)
        self.J_grip_f = Jf

    def _paper(self):
        mdl = self.mdl
        Jt = self.J("pen", np.zeros(3))
        self.J_tip = Jt
        n = torch.tensor([0.0, 0.0, 1.0])
        Kn = mdl.k_n * torch.outer(n, n)
        Cn = mdl.c_n * torch.outer(n, n)
        P2 = torch.eye(3) - torch.outer(n, n)
        cp = self.g("c_heel", mdl.c_heel) + mdl.c_paper
        if mdl.collar is not None and mdl.collar.skid_on_collar:
            # V2: the ball on its refill spring (soft normal) with its in-plane drag; the skid ring on the collar
            self.add_spring(Jt, mdl.k_refill * torch.outer(n, n), 0.05 * torch.outer(n, n) + cp * P2)
            Ps = mdl.z_skid * self.a + mdl.r_skid * self.t1
            Js = self.J("collar", Ps)
            self.add_spring(Js, Kn, Cn + mdl.c_skid * P2)
        else:
            self.add_spring(Jt, Kn, Cn + cp * P2)
        cs = self.g("c_sled", mdl.c_sled)
        Jh = torch.zeros(3, self.n)
        i = self.bodies["hand"]
        Jh[:, i:i + 3] = torch.eye(3)
        self.D = self.D + Jh.T @ (cs * P2) @ Jh

    def _tmd(self):
        t = self.mdl.tmd
        m = self.g("tmd_m", t.m)
        k = self.g("tmd_k", t.k)
        c = self.g("tmd_c", t.c)
        i = self.i_tmd
        Pm = t.z * self.a
        # absolute displacement of the mass (transverse) = pen point transverse + relative coordinate
        Jp = self.J("pen", Pm)
        Jabs = torch.zeros(3, self.n)
        Jabs = Jabs + Jp
        Jabs[:, i] += torch.tensor(self.t1)
        Jabs[:, i + 1] += torch.tensor(self.t2)
        self.M = self.M + m * (Jabs.T @ Jabs)
        E = torch.zeros(2, self.n)
        E[0, i] = 1.0
        E[1, i + 1] = 1.0
        self.K = self.K + k * (E.T @ E)
        self.D = self.D + c * (E.T @ E)
        self.E_tmd = E
        self.J_tmd_pen = Jp

    def _cmg(self, k, cp: CMGPair):
        """Scissored pair: pair angular momentum 2 h delta o (o = g x a) for small delta.  Torque on the pen
        -2 h delta' o; gimbal generalised force +2 h (omega_pen . o).  D[phi, delta] = 2h o, D[delta, phi] = -2h o^T
        (skew-symmetric: no work), plus J_g, k_g, c_g on delta."""
        i = self.i_cmg[k]
        o = self.t1 if cp.out == "t1" else self.t2
        h = self.g(f"cmg_h{k}", cp.h)
        Jg = self.g(f"cmg_Jg{k}", cp.J_g)
        kg = self.g(f"cmg_kg{k}", cp.k_g)
        cg = self.g(f"cmg_cg{k}", cp.c_g)
        e = torch.zeros(self.n)
        e[i] = 1.0
        ip = self.bodies["pen"]
        ov = torch.zeros(self.n)
        ov[ip + 3:ip + 6] = torch.tensor(o)
        self.M = self.M + Jg * torch.outer(e, e)
        self.K = self.K + kg * torch.outer(e, e)
        self.D = self.D + cg * torch.outer(e, e) + 2 * h * (torch.outer(ov, e) - torch.outer(e, ov))

    # ------------------------------------------------------------------------------------------------ solves
    def A(self, w: float):
        return (self.K.to(CT) - (w * w) * self.M.to(CT) + (1j * w) * self.D.to(CT))

    def exc_tremor(self, w: float, d: np.ndarray) -> torch.Tensor:
        """Generalised force of an imposed tremor path d (page frame, complex 3-vector) through the arm spring."""
        h = self.mdl.hand
        dv = torch.tensor(np.asarray(d, complex), dtype=CT)
        return self.J_arm.T.to(CT) @ ((h.k_arm + 1j * w * h.b_arm) * dv)

    def u_torque_pen(self, axis: np.ndarray) -> torch.Tensor:
        return self.Jrot("pen").T.to(CT) @ torch.tensor(np.asarray(axis, complex), dtype=CT)

    def u_force_pen(self, z: float, d: np.ndarray) -> torch.Tensor:
        return self.J("pen", z * self.a).T.to(CT) @ torch.tensor(np.asarray(d, complex), dtype=CT)

    def u_force_hand(self, d: np.ndarray) -> torch.Tensor:
        i = self.bodies["hand"]
        u = torch.zeros(self.n, dtype=CT)
        u[i:i + 3] = torch.tensor(np.asarray(d, complex), dtype=CT)
        return u

    def u_tmd(self, j: int) -> torch.Tensor:
        """Unit actuator force pushing the tmd mass along t_j and the pen the other way (reaction mass)."""
        u = torch.zeros(self.n, dtype=CT)
        u[self.i_tmd + j] = 1.0
        return u

    def u_collar(self, axis: np.ndarray) -> torch.Tensor:
        """Unit torque of a motor in the collar on the pen about axis (reaction on the collar)."""
        return self.J_piv_rel.T.to(CT) @ torch.tensor(np.asarray(axis, complex), dtype=CT)

    def u_gimbal(self, k: int) -> torch.Tensor:
        u = torch.zeros(self.n, dtype=CT)
        u[self.i_cmg[k]] = 1.0
        return u

    def tip(self, X: torch.Tensor) -> torch.Tensor:
        """Page-plane tip displacement (x, y) from the solution."""
        return (self.J_tip.to(CT) @ X)[0:2]

    def ink(self, X: torch.Tensor) -> torch.Tensor:
        """Page-plane displacement of the ink point.  With the V2 collar the ball rides on its refill spring and stays on
        the paper by sliding along the pen axis a, so the ink moves tip_xy - tip_z a_xy / a_z (the tilt-plane motion
        is 1 / sin(theta) of the tip's transverse motion); otherwise the tip itself."""
        p = self.J_tip.to(CT) @ X
        if self.mdl.collar is not None and self.mdl.collar.skid_on_collar:
            a = self.a
            return p[0:2] - p[2] * torch.tensor([a[0] / a[2], a[1] / a[2]], dtype=CT)
        return p[0:2]

    def solve(self, w: float, F: torch.Tensor) -> torch.Tensor:
        return torch.linalg.solve(self.A(w), F)


# ------------------------------------------------------------------------------------------------ convenience
def tremor_dirs(orientation: float = 0.6, ell: float = 0.4):
    """The project's elliptical hand-path tremor (P1 convention): major axis at `orientation` rad from page x,
    minor/major = ell, quadrature (stabpen.signals.TremorSpec); returns the complex page vector per unit peak."""
    umaj = np.array([math.cos(orientation), math.sin(orientation), 0.0])
    umin = np.array([-math.sin(orientation), math.cos(orientation), 0.0])
    return umaj + (-1j * ell) * umin


def frf_tremor(mdl: Model, f: float, A: float = 1e-3, d: Optional[np.ndarray] = None, par=None) -> torch.Tensor:
    """Tip response (page x, y; complex) to the elliptical hand-path tremor of peak A at f."""
    asm = Assembly(mdl, par)
    w = 2 * math.pi * f
    dv = (tremor_dirs() if d is None else d) * A
    X = asm.solve(w, asm.exc_tremor(w, dv))
    return asm.tip(X)


def tip_compliance_H1(h: HandP, f: float, theta_deg: float = 50.0) -> complex:
    """Driving-point compliance at the pen tip along t2 of the massless-pen grip + hand (for the HAP-26 check)."""
    mdl = Model(theta_deg=theta_deg, hand=h, pen={"m": 1e-7, "z_g": 0.08, "J_t": 1e-12, "J_a": 1e-12, "length": 0.14},
                k_n=0.0, c_n=0.0)
    asm = Assembly(mdl)
    w = 2 * math.pi * f
    X = asm.solve(w, asm.u_force_pen(0.0, asm.t2))
    return complex((asm.J_tip.to(CT) @ X)[1])


def amp(v: torch.Tensor) -> float:
    """Peak amplitude of a complex page vector (the semi-major axis of the ellipse it traces)."""
    vr, vi = v.real.detach().numpy(), v.imag.detach().numpy()
    C = np.outer(vr, vr) + np.outer(vi, vi)
    return float(math.sqrt(max(np.linalg.eigvalsh(C)[-1], 0.0)))
