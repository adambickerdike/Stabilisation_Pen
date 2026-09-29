r"""P1, the structural half: can the C1S gimbal carry the magnet cap's axial pull?

Question.  The magnet cap pulls toward the coil plate's back iron with F = 16.5 N (revj.magnetics.axial_pull: image
method, ideal iron, an upper bound for its iron face; 12.4-22.2 N across the three face positions in Rev J's code,
revj1.magnetics).  Study N's cross-strip gimbal (301 full-hard steel, t 50 um, b 2.55 mm, L 3.80 mm, strips at +-45 deg,
crossing at mid-length) was credited with 14.5 N per strip (Euler, clamped-clamped, half length); the pull puts
F / (2 cos 45 deg) = 11.7 N on each strip in compression.

What this module computes (CALC; beam theory, no FEM of the real part):
  1. A geometrically non-linear (co-rotational, Crisfield) beam model of one cross-strip pivot: two strips from the fixed
     frame to a rigid moving body, an axial dead load F through the pivot (tension > 0), the body's rotation imposed and
     its translation free.  It gives the pivot's rotational stiffness k(F), the strips' peak strain and the pivot's
     buckling load, for any crossing point lambda (fraction of the strip length from the fixed end).  Checked against
     the closed forms derived here: k0 = 2 (EI/L)(c0^2 + c0 c1 + c1^2/3) (= E b t^3 / (6 L) at lambda 0.5) and the
     small-load term k_F = F L f(lambda) / cos(alpha), f = 1.2 lambda^2 - 1.2 lambda + 2/15 (f = 0 at lambda = 0.1273,
     Wittrick's classic 12.7 % crossing).
  2. Designs: study N's strips; the same in tension; tension with a near-end crossing (narrow and 10 mm wide); the
     Rev J.1 choice, 75 um strips in compression; 100 um x 5 mm as the fallback.  Stresses, strain at the usable and
     stop tilts, Goodman safety factor (full-travel tilt fully reversed; a compressive mean ignored).
  3. Thrust pivots (a ball or jewel carrying F): Hertz pressure, friction torque, its size at the ball, the dead band it
     puts into the servo, rolling resistance, Archard wear.
  4. Shock: the drop loads on the 18.1 g nose, the stop gap that keeps buckled strips elastic.
Result: tension fails (negative stiffness at mid-length crossing; boundary-layer bending strain ~ phi sqrt(3 sigma / E)
at a near-end crossing); 75 um strips in compression buckle at 55 N and keep a safety factor of 2.0.
Frames: y along the pen axis from the fixed frame toward the moving body; x across; the pivot at the origin.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import ensure_paths

ensure_paths()

# --------------------------------------------------------------------------------------------------- inputs (labelled)
E_301FH = 200e9          # Pa, LIT AMF-20 (301 full hard; aggregated database)
UTS_301FH = 1460e6       # Pa, LIT AMF-20
YIELD_301FH = 1080e6     # Pa, LIT AMF-20
FATIGUE_301FH = 540e6    # Pa, LIT AMF-20 (cycle count of the listing not stated)
FAT_SF = 1.5             # ASSUMPTION, study N (nose2/designs.FAT_SF)
F_PULL_IMAGES = 16.5     # N, CALC revj.magnetics.axial_pull (upper bound); recomputed in revj1.magnetics
F_PULL_LUMPED = 36.0     # N, CALC revj (B_gap^2 x pole area / 2 mu0; ignores fringing)
F_REFILL = 0.15          # N, ASSUMPTION (REQ-RVJ-N05): the ink force also reaches the handle through the gimbal
Z_PIVOT_TO_TIP = 76.48   # mm, CALC study N (gimbal to ball)
ALPHA_USABLE = 0.0859    # rad, CALC revj.frontend.close (6.0 mm guaranteed over 35-75 deg)
ALPHA_STOP = 0.0925      # rad, CALC revj (usable + 0.5 mm at the ball)
SERVO_HZ = 80.0          # Hz, ASSUMPTION (Rev H, study N)
M_TIP_G = 2.10           # g, CALC study N (moving mass at the tip)
NOSE_MASS_G = 18.1       # g, CALC revj (the tilting nose)


@dataclass(frozen=True)
class Strip:
    t: float = 50e-6          # m, study N (stock >= 50 um, ASSUMPTION)
    b: float = 2.55e-3        # m, study N
    L: float = 3.80e-3        # m, study N
    alpha_deg: float = 45.0   # strips at +-alpha to the pen axis (study N's cross-strip gimbal)
    lam: float = 0.5          # crossing point as a fraction of the length from the FIXED end
    E: float = E_301FH

    @property
    def I(self):
        return self.b * self.t ** 3 / 12.0

    @property
    def A(self):
        return self.b * self.t


STUDY_N = Strip()


# --------------------------------------------------------------------------------------------------- closed forms
def f_lambda(lam: float) -> float:
    """Load factor of a cross-strip pivot (CALC, derived in the module docstring): k_F = F L f / cos(alpha)."""
    return 1.2 * lam * lam - 1.2 * lam + 2.0 / 15.0


def k_elastic_closed(s: Strip) -> float:
    """Rotational stiffness of the unloaded pivot (two strips), N m/rad: 2 (EI/L) (c0^2 + c0 c1 + c1^2/3) with
    c0 = 2 (2 - 3 lam), c1 = 6 (2 lam - 1) (a strip whose far end rotates about the crossing point; = 2 EI / L at 0.5)."""
    c0, c1 = 2 * (2 - 3 * s.lam), 6 * (2 * s.lam - 1)
    return 2.0 * s.E * s.I / s.L * (c0 * c0 + c0 * c1 + c1 * c1 / 3.0)


def k_load_closed(s: Strip, F: float) -> float:
    """Load-dependent stiffness (N m/rad) for an axial dead load F through the pivot (tension > 0)."""
    return F * s.L * f_lambda(s.lam) / math.cos(math.radians(s.alpha_deg))


def curvature_peak_factor(lam: float) -> float:
    """Largest |curvature| along a strip / (theta / L) (CALC): max(|c0|, |c0 + c1|)."""
    c0, c1 = 2 * (2 - 3 * lam), 6 * (2 * lam - 1)
    return max(abs(c0), abs(c0 + c1))


def wittrick_lambda() -> float:
    return (1.0 - math.sqrt(1.0 - 4 * (2.0 / 15.0) / 1.2)) / 2.0


# --------------------------------------------------------------------------------------------------- co-rotational beam model
class CrossPivot:
    """Two co-rotational Euler-Bernoulli strips (n elements each) from fixed clamps to a rigid body (CALC).

    The body's reference point is the crossing point (the pivot); its rotation phi is imposed, its translation (X, Y) is
    solved with the axial dead load F (tension > 0, along +y) applied at a point e along the axis from the pivot
    (e = 0: through the pivot).  Returns the moment needed to hold phi."""

    def __init__(self, s: Strip, n: int = 24):
        self.s = s
        self.n = n
        a = math.radians(s.alpha_deg)
        self.u = [np.array([math.sin(a), math.cos(a)]), np.array([-math.sin(a), math.cos(a)])]
        self.A0 = [-s.lam * s.L * u for u in self.u]
        self.B0 = [(1 - s.lam) * s.L * u for u in self.u]
        self.l0 = s.L / n
        self.EA, self.EI = s.E * s.A, s.E * s.I
        # unknowns: interior nodes (n-1 per strip, 3 dof) + body X, Y
        self.ni = n - 1
        self.nq = 2 * 3 * self.ni + 2

    def _index(self):
        """Global dof index of every element's six dofs (-1: fixed or imposed), for both strips (vectorised assembly)."""
        if hasattr(self, "_idx"):
            return self._idx
        idx = []
        for k in range(2):
            off = 3 * self.ni * k
            g = np.full((self.n + 1, 3), -1, int)
            for node in range(1, self.n):
                g[node] = [off + 3 * (node - 1) + j for j in range(3)]
            g[self.n] = [self.nq - 2, self.nq - 1, -1]          # end node x, y -> body X, Y; its rotation is imposed
            idx.append(np.hstack([g[:-1], g[1:]]))
        self._idx = np.vstack(idx)
        return self._idx

    def _nodes(self, q: np.ndarray, phi: float):
        """Node positions (x, y), rotations and undeformed positions of both strips, stacked strip by strip."""
        c, sn = math.cos(phi), math.sin(phi)
        R = np.array([[c, -sn], [sn, c]])
        X = q[-2:]
        Ps, ths, bases = [], [], []
        for k in range(2):
            base = np.linspace(0, 1, self.n + 1)[:, None] * (self.B0[k] - self.A0[k])[None, :] + self.A0[k][None, :]
            P = base.copy()
            th = np.zeros(self.n + 1)
            off = 3 * self.ni * k
            qi = q[off:off + 3 * self.ni].reshape(self.ni, 3)
            P[1:-1] += qi[:, :2]
            th[1:-1] = qi[:, 2]
            P[-1] = X + R @ self.B0[k]
            th[-1] = phi
            Ps.append(P); ths.append(th); bases.append(base)
        return Ps, ths, bases

    def _elements(self, Ps, ths, bases):
        """Co-rotational element forces (e, 6) and tangents (e, 6, 6) for both strips (Crisfield's 2-D beam)."""
        d = np.vstack([P[1:] - P[:-1] for P in Ps])
        d0 = np.vstack([b[1:] - b[:-1] for b in bases])
        th1 = np.concatenate([t[:-1] for t in ths])
        th2 = np.concatenate([t[1:] for t in ths])
        l = np.hypot(d[:, 0], d[:, 1])
        c, s = d[:, 0] / l, d[:, 1] / l
        rig = np.angle(np.exp(1j * (np.arctan2(s, c) - np.arctan2(d0[:, 1], d0[:, 0]))))
        t1, t2 = th1 - rig, th2 - rig
        N = self.EA * (l - self.l0) / self.l0
        M1 = self.EI / self.l0 * (4 * t1 + 2 * t2)
        M2 = self.EI / self.l0 * (2 * t1 + 4 * t2)
        z0 = np.zeros_like(c)
        o1 = np.ones_like(c)
        r = np.stack([-c, -s, z0, c, s, z0], axis=1)
        zz = np.stack([s, -c, z0, -s, c, z0], axis=1)
        b2 = np.stack([-s / l, c / l, o1, s / l, -c / l, z0], axis=1)
        b3 = np.stack([-s / l, c / l, z0, s / l, -c / l, o1], axis=1)
        B = np.stack([r, b2, b3], axis=1)                                   # (e, 3, 6)
        fl = np.stack([N, M1, M2], axis=1)
        fe = np.einsum("eij,ei->ej", B, fl)
        D = np.zeros((3, 3))
        D[0, 0] = self.EA / self.l0
        D[1:, 1:] = self.EI / self.l0 * np.array([[4, 2], [2, 4]])
        K = np.einsum("eki,kl,elj->eij", B, D, B)
        K += (N / l)[:, None, None] * np.einsum("ei,ej->eij", zz, zz)
        K += ((M1 + M2) / l ** 2)[:, None, None] * (np.einsum("ei,ej->eij", r, zz) + np.einsum("ei,ej->eij", zz, r))
        return fe, K, (N, M1, M2, t1, t2)

    def residual_and_tangent(self, q: np.ndarray, phi: float, F: float, e_load: float = 0.0):
        Ps, ths, bases = self._nodes(q, phi)
        fe, Ke, loc = self._elements(Ps, ths, bases)
        idx = self._index()
        R = np.zeros(self.nq + 1)
        ii = np.where(idx >= 0, idx, self.nq)
        np.add.at(R, ii.ravel(), fe.ravel())
        R = R[:-1]
        K = np.zeros((self.nq + 1, self.nq + 1))
        np.add.at(K, (np.repeat(ii, 6, axis=1).ravel(), np.tile(ii, (1, 6)).ravel()), Ke.reshape(len(fe), 36).ravel())
        K = K[:-1, :-1]
        R[-1] -= F                      # external dead load along +y on the body (tension > 0)
        # end-node element forces (for the moment) per strip
        info = []
        n = self.n
        for k in range(2):
            fend = fe[(k + 1) * n - 1, 3:]
            loc_k = tuple(v[k * n:(k + 1) * n] for v in loc)
            info.append((Ps[k], ths[k], fend, loc_k))
        return R, K, info

    def solve(self, phi: float, F: float, e_load: float = 0.0, q0: Optional[np.ndarray] = None, steps: int = 4,
              tol: float = 1e-10, it_max: int = 40):
        q = np.zeros(self.nq) if q0 is None else q0.copy()
        for kstep in range(1, steps + 1):
            ph, Fk = phi * kstep / steps, F * kstep / steps
            for _ in range(it_max):
                R, K, _ = self.residual_and_tangent(q, ph, Fk, e_load)
                dq = np.linalg.solve(K, -R)
                q += dq
                if np.max(np.abs(dq)) < tol:
                    break
        R, K, info = self.residual_and_tangent(q, phi, F, e_load)
        # moment about the pivot needed to hold phi: sum over the strips' end forces on the body
        M = 0.0
        cph, sph = math.cos(phi), math.sin(phi)
        Rm = np.array([[cph, -sph], [sph, cph]])
        for k, (P, th, fB, loc) in enumerate(info):
            rB = Rm @ self.B0[k]        # internal force vector of the strip's last element at the body node
            M += rB[0] * fB[1] - rB[1] * fB[0] + fB[2]
        # a dead load (0, F) applied at a BODY point e along the axis from the pivot: the moment needed to hold phi gains
        # + F e sin(phi) (a pendulum for e F > 0).  The magnetic pull is not such a load: its line passes through the
        # plate's sphere centre, fixed in the handle; its centring term is -F e_p (revj1.magnetics.centring).
        M += F * e_load * math.sin(phi)
        eig = np.linalg.eigvalsh(0.5 * (K + K.T))
        return {"q": q, "M": M, "min_eig": float(eig.min()), "info": info, "residual": float(np.max(np.abs(R)))}

    def stiffness(self, F: float, phi: float = 0.0, dphi: float = 1e-3, e_load: float = 0.0) -> float:
        """Tangent rotational stiffness dM/dphi (N m/rad) at the rotation phi."""
        a = self.solve(phi + dphi, F, e_load)
        b = self.solve(phi - dphi, F, e_load)
        return (a["M"] - b["M"]) / (2 * dphi)

    def peak_strain(self, F: float, phi: float) -> Dict:
        """Largest bending strain and axial stress in either strip at the rotation phi under F (CALC)."""
        r = self.solve(phi, F)
        eb, sN = 0.0, 0.0
        for (P, th, fB, loc) in r["info"]:
            N, M1, M2, t1, t2 = loc
            Mmax = np.max(np.abs(np.concatenate([M1, M2])))
            eb = max(eb, Mmax / self.EI * self.s.t / 2)
            sN = max(sN, float(np.max(np.abs(N))) / self.s.A)
        return {"bending_strain": eb, "bending_stress_MPa": eb * self.s.E / 1e6, "axial_stress_MPa": sN / 1e6,
                "M_hold_mNm": r["M"] * 1e3}

    def stable(self, F: float) -> bool:
        """Stable under the axial load F (compression < 0) with the rotation free: the tangent with the rotation held is
        positive definite AND the condensed rotational stiffness is positive (Schur complement) (CALC)."""
        try:
            r = self.solve(0.0, F, steps=8)
            if r["residual"] > 1e-6 or r["min_eig"] <= 0.0:
                return False
            return self.stiffness(F) > 0.0
        except np.linalg.LinAlgError:
            return False


def buckling_load(s: Strip, n: int = 16, F_hi: float = 80.0) -> float:
    """Compressive axial load (N, positive number) at which the pivot becomes unstable (CALC, bisection on CrossPivot.stable)."""
    cp = CrossPivot(s, n)
    lo, hi = 0.0, F_hi
    if cp.stable(-hi):
        return float("inf")
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        if cp.stable(-mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def euler_strip(s: Strip) -> float:
    """Study N's buckling check: one strip, clamped-clamped, effective length L/2 (N)."""
    return math.pi ** 2 * s.E * s.I / (0.5 * s.L) ** 2


# --------------------------------------------------------------------------------------------------- designs in tension
def goodman_sf(sig_a: float, sig_m: float) -> float:
    """Goodman safety factor with the listed fatigue strength (AMF-20) and UTS (CALC)."""
    return 1.0 / (sig_a / FATIGUE_301FH + sig_m / UTS_301FH)


def design_row(s: Strip, F: float, n: int = 20, with_fe: bool = True) -> Dict:
    """One strip design under an axial load F (tension > 0): stiffness (closed form and beam model), stresses, fatigue."""
    k0 = k_elastic_closed(s)
    kF = k_load_closed(s, F)
    row = {"t_um": s.t * 1e6, "b_mm": s.b * 1e3, "L_mm": s.L * 1e3, "alpha_deg": s.alpha_deg, "lambda": s.lam, "F_N": F,
           "k0_closed_mNm_rad": k0 * 1e3, "kF_closed_mNm_rad": kF * 1e3, "k_closed_mNm_rad": (k0 + kF) * 1e3,
           "axial_span_mm": s.L * math.cos(math.radians(s.alpha_deg)) * 1e3,
           "span_ahead_of_pivot_mm": s.lam * s.L * math.cos(math.radians(s.alpha_deg)) * 1e3 if F >= 0 else None}
    sig_ax = F / (2 * math.cos(math.radians(s.alpha_deg))) / s.A
    cpf = curvature_peak_factor(s.lam)
    eps_u = cpf * ALPHA_USABLE / s.L * s.t / 2
    eps_s = cpf * ALPHA_STOP / s.L * s.t / 2
    row.update({"strip_force_N": F / (2 * math.cos(math.radians(s.alpha_deg))), "axial_stress_MPa": sig_ax / 1e6,
                "bending_strain_usable_closed": eps_u, "bending_strain_stop_closed": eps_s,
                "bending_stress_usable_MPa_closed": eps_u * s.E / 1e6})
    if with_fe:
        cp = CrossPivot(s, n)
        k_fe = cp.stiffness(F)
        ps = cp.peak_strain(F, ALPHA_USABLE)
        pss = cp.peak_strain(F, ALPHA_STOP)
        row.update({"k_beam_model_mNm_rad": k_fe * 1e3,
                    "k_beam_model_at_usable_mNm_rad": cp.stiffness(F, phi=ALPHA_USABLE) * 1e3,
                    "bending_strain_usable_beam": ps["bending_strain"], "bending_strain_stop_beam": pss["bending_strain"],
                    "axial_stress_MPa_beam": ps["axial_stress_MPa"], "M_hold_usable_mNm": ps["M_hold_mNm"]})
        eps_a = ps["bending_strain"]
    else:
        eps_a = eps_u
    sig_a = eps_a * s.E                              # fully reversed bending as the nose sweeps +-usable
    sig_m = max(sig_ax, 0.0)
    row["goodman_SF_1e8"] = goodman_sf(sig_a, sig_m)
    row["static_SF_stop"] = YIELD_301FH / ((row.get("bending_strain_stop_beam", eps_s)) * s.E + abs(sig_ax))
    row["tip_stiffness_N_m"] = row.get("k_beam_model_mNm_rad", (k0 + kF) * 1e3) * 1e-3 / (Z_PIVOT_TO_TIP * 1e-3) ** 2
    return row


def stiffness_vs_load(s: Strip, loads: Sequence[float], n: int = 16) -> List[Dict]:
    cp = CrossPivot(s, n)
    out = []
    for F in loads:
        out.append({"F_N": F, "k_beam_mNm_rad": cp.stiffness(F) * 1e3,
                    "k_closed_mNm_rad": (k_elastic_closed(s) + k_load_closed(s, F)) * 1e3})
    return out


def lambda_scan(s: Strip, F: float, lams: Sequence[float], n: int = 16) -> List[Dict]:
    out = []
    for lam in lams:
        s2 = replace(s, lam=lam)
        cp = CrossPivot(s2, n)
        out.append({"lambda": lam, "f_lambda": f_lambda(lam), "k0_closed_mNm_rad": k_elastic_closed(s2) * 1e3,
                    "k_closed_mNm_rad": (k_elastic_closed(s2) + k_load_closed(s2, F)) * 1e3,
                    "k_beam_mNm_rad": cp.stiffness(F) * 1e3, "k_beam_F0_mNm_rad": cp.stiffness(0.0) * 1e3,
                    "curvature_peak_factor": curvature_peak_factor(lam)})
    return out


# --------------------------------------------------------------------------------------------------- thrust pivots
E_STEEL, NU_STEEL = 210e9, 0.30          # ASSUMPTION handbook (hardened bearing steel)
E_SAPPHIRE, NU_SAPPHIRE = 400e9, 0.25    # ASSUMPTION handbook (single-crystal alumina)


def hertz_sphere_flat(F: float, R: float, E1=E_STEEL, nu1=NU_STEEL, E2=E_SAPPHIRE, nu2=NU_SAPPHIRE) -> Dict:
    """Hertz contact of a sphere (radius R) on a flat (CALC): contact radius a, peak pressure p0."""
    Es = 1.0 / ((1 - nu1 ** 2) / E1 + (1 - nu2 ** 2) / E2)
    a = (3 * F * R / (4 * Es)) ** (1 / 3)
    p0 = 3 * F / (2 * math.pi * a * a)
    return {"R_mm": R * 1e3, "a_um": a * 1e6, "p0_GPa": p0 / 1e9, "E_star_GPa": Es / 1e9}


def thrust_pivot_options(F: float = F_PULL_IMAGES) -> Dict:
    """Friction and hysteresis of pivots that carry F at the gimbal (CALC; friction and wear inputs ASSUMPTION ranges).

    Tilting a sphere that bears on a cup or a flat about the pivot needs either sliding (friction torque mu F r, r = the
    radius at which the surfaces slide: the ball radius for a ball-and-socket, the pin's tip radius for a pin on a
    jewel) or rolling (rolling-resistance torque F x delta_r).  The servo sees the friction torque at the ball as
    F_f = T / z_p, and a stiff position loop with an integrator must build that force from a position error before the nose
    moves: dead band ~ F_f / k_servo, k_servo = m_tip (2 pi f_servo)^2."""
    k_servo = M_TIP_G * 1e-3 * (2 * math.pi * SERVO_HZ) ** 2
    rows = []
    p_allow = 2.5e9                         # Pa, ASSUMPTION: static contact-pressure limit for hardened steel on sapphire
    for R in (0.25e-3, 0.5e-3, 1.0e-3, 2.0e-3, 3.0e-3):
        hz = hertz_sphere_flat(F, R)
        for mu, kind in ((0.10, "sliding, lubricated steel on sapphire (mu 0.10, ASSUMPTION)"),
                         (0.15, "sliding, dry (mu 0.15, ASSUMPTION)")):
            T = mu * F * R
            Ff = T / (Z_PIVOT_TO_TIP * 1e-3)
            rows.append({"R_mm": R * 1e3, "kind": kind, "hertz": hz, "pressure_ok": hz["p0_GPa"] * 1e9 <= p_allow,
                         "friction_torque_mNm": T * 1e3, "friction_at_tip_mN": Ff * 1e3,
                         "dead_band_um": Ff / k_servo * 1e6})
    roll = []
    for dr in (1e-6, 5e-6, 20e-6):
        T = F * dr
        Ff = T / (Z_PIVOT_TO_TIP * 1e-3)
        roll.append({"delta_r_um": dr * 1e6, "friction_torque_mNm": T * 1e3, "friction_at_tip_mN": Ff * 1e3,
                     "dead_band_um": Ff / k_servo * 1e6})
    # wear (Archard): V = k_w F s / H; sliding distance per small cycle ~ 2 x R x 2 alpha_tremor (ASSUMPTION)
    H_steel = 7.0e9                          # Pa, ASSUMPTION (HV ~700)
    alpha_trem = 1.3e-3 / (Z_PIVOT_TO_TIP * 1e-3)     # rad amplitude for 1.3 mm at the ball (1 mm rms tremor)
    wear = []
    for kw in (1e-7, 1e-6):
        for R in (1.0e-3,):
            s_per_cycle = 4 * R * alpha_trem
            V = kw * F * s_per_cycle * 1e8 / H_steel
            a = hertz_sphere_flat(F, R)["a_um"] * 1e-6
            wear.append({"k_wear": kw, "R_mm": R * 1e3, "cycles": 1e8, "volume_mm3": V * 1e9,
                         "depth_um_over_contact": V / (math.pi * a * a) * 1e6})
    return {"F_N": F, "k_servo_tip_N_m": k_servo, "sliding": rows, "rolling": roll, "wear": wear,
            "duty_force_at_tip_mN": {"tremor_1mm_inertia": M_TIP_G * 1e-3 * 10.6 * 1e3,
                                     "ball_drag_rms": math.sqrt(0.3) * 0.15 * 0.15 / math.sin(math.radians(50)) * 1e3},
            "geometry_note": ("the refill holder passes the gimbal's centre (its rear end reaches z 80.4 mm at full retraction, "
                              "revj/refill.py), so no pivot can sit ON the axis at z 76.5: a thrust pivot must be split into two "
                              "or four off-axis pivots (at the gimbal's axis ends), each at a radius r from the axis"),
            "label": "CALC (Hertz; friction, rolling resistance, wear coefficient and pressure limit ASSUMPTION ranges)"}


# --------------------------------------------------------------------------------------------------- the choice
def chosen_strip() -> Strip:
    """Rev J.1 gimbal strips (PROPOSED DESIGN): study N's cross-strip geometry and load path (the pull compresses the
    strips), one stock step thicker: 75 um instead of 50 um."""
    return Strip(t=75e-6, b=2.55e-3, L=3.80e-3, alpha_deg=45.0, lam=0.5)


TENSION_NEAR_END = Strip(t=50e-6, b=2.55e-3, L=5.0e-3, alpha_deg=45.0, lam=0.06)


def curves(quick: bool = False) -> Dict:
    """Stiffness and peak strain at the usable tilt against the axial load, for the three designs of the figure (CALC)."""
    n = 12 if quick else 16
    loads = [-16.0, -12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0, 16.5, 25.0, 36.0] if not quick else [-8.0, 0.0, 16.5]
    out = {}
    for key, st, lo in (("studyN_50um", STUDY_N, -16.0), ("tension_near_end", TENSION_NEAR_END, 0.0),
                        ("chosen_75um", chosen_strip(), -36.0)):
        cp = CrossPivot(st, n)
        rows = []
        Fs = sorted(set([F for F in loads if F >= lo] + ([-25.0, -36.0] if key == "chosen_75um" and not quick else [])))
        for F in Fs:
            try:
                k = cp.stiffness(F)
                e = cp.peak_strain(F, ALPHA_USABLE)["bending_strain"]
            except np.linalg.LinAlgError:
                continue
            rows.append({"F_N": F, "k_mNm_rad": k * 1e3, "strain_usable": e})
        out[key] = rows
    return out


def summary(quick: bool = False) -> Dict:
    n = 12 if quick else 20
    sN = STUDY_N
    s1 = chosen_strip()
    lam_w = wittrick_lambda()
    loads = [-10.0, -5.0, 0.0, 5.0, 10.0, 16.5, 25.0, 36.0] if not quick else [-5.0, 0.0, 16.5]
    Fp = F_PULL_IMAGES
    out = {
        "inputs": {"E_Pa": E_301FH, "UTS_Pa": UTS_301FH, "yield_Pa": YIELD_301FH, "fatigue_Pa": FATIGUE_301FH,
                   "labels": "LIT AMF-20 (301 full hard, aggregated database); FAT_SF 1.5 ASSUMPTION (study N)",
                   "F_pull_N": {"images_upper_bound": Fp, "lumped": F_PULL_LUMPED},
                   "alpha_usable_rad": ALPHA_USABLE, "alpha_stop_rad": ALPHA_STOP},
        "wittrick_lambda_closed_form": lam_w,
        "check_closed_vs_beam": {
            "k0_studyN_closed_mNm_rad": k_elastic_closed(sN) * 1e3,
            "k0_studyN_nose2_formula_mNm_rad": sN.E * sN.b * sN.t ** 3 / (6 * sN.L) * 1e3,
            "k0_studyN_beam_mNm_rad": CrossPivot(sN, n).stiffness(0.0) * 1e3,
            "k0_lambda_wittrick_closed_mNm_rad": k_elastic_closed(replace(sN, lam=lam_w)) * 1e3,
            "k0_lambda_wittrick_beam_mNm_rad": CrossPivot(replace(sN, lam=lam_w), n).stiffness(0.0) * 1e3},
        "buckling_N": {"studyN_50um_beam": buckling_load(sN, n=12 if quick else 24),
                       "studyN_euler_per_strip_x2cos45": 2 * math.cos(math.radians(45)) * euler_strip(sN),
                       "chosen_75um_beam": buckling_load(s1, n=12 if quick else 24),
                       "alt_100um_L5_beam": buckling_load(replace(sN, t=100e-6, L=5e-3), n=12, F_hi=150.0)},
        "stiffness_vs_load_studyN": stiffness_vs_load(sN, loads, n=12 if quick else 16),
        "lambda_scan_F16.5_tension": lambda_scan(sN, Fp, [0.0, 0.04, 0.06, 0.08, 0.1, lam_w, 0.2, 0.5] if not quick else [0.06, 0.5],
                                                 n=12 if quick else 16),
        "options": {
            "A_studyN_50um_compression": design_row(sN, -min(Fp, 16.0), n),
            "B_tension_mid_length": design_row(sN, Fp, n),
            "B2_tension_near_end_b2.55": design_row(TENSION_NEAR_END, Fp, n),
            "B3_tension_near_end_b10": design_row(replace(TENSION_NEAR_END, b=10e-3), Fp, n),
            "C_chosen_75um_compression": design_row(s1, -Fp, n),
            "C_chosen_75um_compression_22N": design_row(s1, -22.2, n),
            "C_chosen_75um_compression_36N": design_row(s1, -F_PULL_LUMPED, n),
            "C2_100um_L5_compression": design_row(replace(sN, t=100e-6, L=5e-3), -Fp, n),
        },
        "curves": curves(quick),
        "thrust_pivot": thrust_pivot_options(Fp),
        "shock": shock_check(s1),
        "chosen": {"t_um": s1.t * 1e6, "b_mm": s1.b * 1e3, "L_mm": s1.L * 1e3, "alpha_deg": s1.alpha_deg, "lambda": s1.lam,
                   "load_path": "compression (study N's arrangement)", "label": "PROPOSED DESIGN"},
        "label": "CALC (co-rotational beam model and closed forms derived here; material LIT AMF-20; loads CALC revj1.magnetics)"}
    return out


def shock_check(s: Strip, g_levels=(50.0, 100.0, 200.0, 500.0, 1000.0)) -> Dict:
    """Axial shock on the 18.1 g nose (a drop): net load on the pivot = pull +- m a (CALC).  The pull compresses the strips
    (study N's arrangement); a tail-first drop adds compression, a tip-first drop takes it away.  Past the buckling load
    a stop must carry the rest; a buckled clamped-clamped strip with end shortening delta has an amplitude
    w0 = (2 / pi) sqrt(L delta) and a peak strain (t / 2)(2 pi / L)^2 w0 / 2 (CALC)."""
    m = NOSE_MASS_G * 1e-3
    P_b = buckling_load(s, n=12)
    rows = []
    for g in g_levels:
        Fi = m * 9.81 * g
        for sign, what in ((1, "tail-first (more compression)"), (-1, "tip-first (toward tension)")):
            Fcomp = F_PULL_IMAGES + sign * Fi                     # compression positive here
            fs = Fcomp / (2 * math.cos(math.radians(s.alpha_deg)))
            rows.append({"g": g, "case": what, "net_compression_N": Fcomp, "strip_force_N": fs,
                         "strip_stress_MPa": fs / s.A / 1e6, "buckles": Fcomp > P_b, "yields_in_tension": -fs / s.A > YIELD_301FH})
    stops = []
    for delta in (2e-6, 5e-6, 10e-6, 20e-6):
        w0 = 2 / math.pi * math.sqrt(s.L * delta)
        eps = s.t / 2 * (2 * math.pi / s.L) ** 2 * w0 / 2
        stops.append({"stop_gap_um": delta * 1e6, "buckled_amplitude_um": w0 * 1e6, "peak_strain": eps,
                      "elastic": eps * s.E < YIELD_301FH})
    k_ax = 2 * s.E * s.A / s.L * math.cos(math.radians(s.alpha_deg)) ** 2
    g_buckle = (P_b - F_PULL_IMAGES) / (m * 9.81)
    return {"rows": rows, "pivot_buckling_N": P_b, "g_at_buckling_tail_first": g_buckle,
            "axial_stiffness_N_per_um": k_ax * 1e-6,
            "compression_travel_to_buckling_um": (P_b - F_PULL_IMAGES) / k_ax * 1e6,
            "stops": stops,
            "proposal": "axial stops on the nose at the gimbal: a rear stop that engages after the strips shorten by <= 5 um "
                        "beyond their loaded position (buckled strips then stay elastic) and a front stop at <= 20 um; the "
                        "cap-to-plate clearance (0.5 mm) is not a stop (PROPOSED DESIGN; EXP-J10 drop test)"}
