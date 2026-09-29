r"""Compliant point contacts with LuGre friction (the 'h1' contact law), applied as wrenches every simulation step.

Why a custom law next to MuJoCo's native contacts: the ink errors of interest are micrometres and the friction
transitions (stick, pre-sliding, Stribeck) drive them (H1 found friction drove estimator performance).  MuJoCo's native
soft contacts are regularised: tangential compliance relaxes Coulomb's law so a sticking contact creeps (LIT CON:
Castro et al. 2022; Le Lidec et al. 2024), and in this model stiff settings chatter when the pen slides (SIM,
verification.contact).  This law reproduces H1/P1 exactly and is the default for the ink studies; the native contacts
remain available (contact.model = 'mujoco') for fast RL runs and geometry-rich plug-ins.

Contact points (world frame, recomputed every step from the current kinematics):
  skid   the lowest point of the C ring (a torus of centreline radius R0 in the plane z_ring behind the ball, tube
         radius rho, 120 deg opening on the top): direction u = projection of -n on the ring plane, clamped to the arc
         when it falls in the opening; point = centre + R0 u - rho n.  At the nominal pose this is H1's skid point.
  ball   the lowest point of the ball on the refill (sphere, radius r_b).
  sphere plug-in rolling elements (heel ball): lowest point of a sphere; the slip velocity is the velocity of the
         body's material point at the contact (rolling handled exactly).
Normal: penalty k * penetration - c * penetration rate (>= 0).  Friction: LuGre normalised by N (sigma_0 = mu_s /
x_pre, sigma_1 = sigma_2 = 0, Stribeck g(v) = mu_k + (mu_s - mu_k) exp(-(v/v_s)^2)), implicit bristle update
(sim/pencil/core.py::_lugre).  Parameters: params.Contact (ASSUMPTION H1/P1 values; EXP-Q01, EXP-B01/B02).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import mujoco
import numpy as np

from . import params as P


class PointContact:
    def __init__(self, name: str, body: int, kind: str, k: float, c: float, mu_k: float, mu_s: float, v_s: float,
                 x_pre: float, **geom):
        self.name, self.body, self.kind = name, body, kind
        self.k, self.c = k, c
        self.mu_k, self.mu_s, self.v_s = max(mu_k, 1e-9), max(mu_s, 1e-9), v_s
        self.sg0 = mu_s / x_pre if mu_k > 0 else 0.0
        self.geom = geom
        self.z = [0.0, 0.0]
        self.N = 0.0
        self.fx = 0.0
        self.fy = 0.0
        self.pv = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class ContactLaw:
    def __init__(self, pm, extra: Optional[List[PointContact]] = None):
        cfg = pm.cfg
        c, g = cfg.contact, cfg.geom
        self.pm = pm
        self.m, self.d = pm.m, pm.d
        self.dt = pm.m.opt.timestep
        th = g.theta_deg * P.D2R
        rho = g.skid_rho
        self.bh = pm.ids["body:handle"]
        self.br = pm.ids["body:refill"]
        self.s_tip = pm.ids["site:tip"]
        self.s_ball = pm.ids["site:ball"]
        self.z_ring = g.p_nom() + rho * math.sin(th)
        self.R0 = g.skid_R - rho * math.cos(th)
        self.rho = rho
        self.half_open = 0.5 * g.skid_open_deg * P.D2R
        self.r_b = g.r_b
        ms = c.ms_ratio
        self.pts = [PointContact("skid", self.bh, "ring", c.k_sk, c.c_sk, c.mu_skid, c.mu_skid * ms, c.v_s, c.presliding),
                    PointContact("ball", self.br, "sphere", c.k_ball, c.c_ball, c.mu_ball, c.mu_ball * ms, c.v_s, c.presliding,
                                 site=self.s_ball, r=g.r_b)]
        for pl in pm.plugins:
            for pc in getattr(pl, "point_contacts", lambda pm_: [])(pm):
                self.pts.append(pc)
        self.extra = extra or []
        self.pts += self.extra
        self.bodies = sorted({pc.body for pc in self.pts} | {self.bh, self.br})
        self.fixed_skid = c.skid_point == "fixed"
        self.s_skid = pm.ids["site:skid_pt"]
        self.vbuf = np.zeros(6)
        # compiled path: parameter table (one row per point) and bristle states
        tab = np.zeros((len(self.pts), NPAR))
        for i, pc in enumerate(self.pts):
            if pc.kind == "ring":
                kind = 0 if self.fixed_skid else 1
                site = self.s_skid
            else:
                kind = 2
                site = pc.geom.get("site", -1)
            tab[i, K_KIND] = kind
            tab[i, K_BODY] = pc.body
            tab[i, K_SITE] = site
            tab[i, K_ROOT] = pm.m.body_rootid[pc.body]
            tab[i, K_K] = pc.k
            tab[i, K_C] = pc.c
            tab[i, K_MUK] = pc.mu_k
            tab[i, K_MUS] = pc.mu_s
            tab[i, K_VS] = pc.v_s
            tab[i, K_SG0] = pc.sg0
            tab[i, K_R] = pc.geom.get("r", 0.0)
            tab[i, K_ZR] = self.z_ring
            tab[i, K_R0] = self.R0
            tab[i, K_RHO] = self.rho
            tab[i, K_HO] = self.half_open
        self.tab = tab
        self.zst = np.zeros((len(self.pts), 2))
        self.kout = np.zeros((len(self.pts), 9))
        self.body_arr = np.array(self.bodies, dtype=np.int64)
        self.out = {"Ns": 0.0, "Nb": 0.0, "fsx": 0.0, "fsy": 0.0, "fbx": 0.0, "fby": 0.0}

    # -------------------------------------------------------------------------------------------- geometry
    def _ring_point(self):
        d = self.d
        R = d.xmat[self.bh].reshape(3, 3)            # columns: t1, t2, a of the handle
        o = d.xpos[self.bh]
        a = R[:, 2]
        ctr = o + self.z_ring * a
        # direction of the lowest centreline point: -n projected on the ring plane
        u = np.array([a[2] * a[0], a[2] * a[1], -1.0 + a[2] * a[2]])     # -n - ((-n) . a) a
        nu = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
        if nu < 1e-9:
            u = R[:, 0]
        else:
            u = u / nu
        # angle in the pen frame (0 = t1, toward the paper side); the opening is centred on pi
        ang = math.atan2(u @ R[:, 1], u @ R[:, 0])
        lim = math.pi - self.half_open
        if abs(ang) > lim:
            ang = math.copysign(lim, ang)
            u = math.cos(ang) * R[:, 0] + math.sin(ang) * R[:, 1]
        p = ctr + self.R0 * u
        p = p.copy()
        p[2] -= self.rho
        return p

    def _point_velocity(self, body, px, py, pz):
        vb = self.vbuf
        mujoco.mj_objectVelocity(self.m, self.d, mujoco.mjtObj.mjOBJ_BODY, body, vb, 0)
        c = self.d.xipos[body]
        rx, ry, rz = px - c[0], py - c[1], pz - c[2]
        wx, wy, wz = vb[0], vb[1], vb[2]
        return vb[3] + wy * rz - wz * ry, vb[4] + wz * rx - wx * rz, vb[5] + wx * ry - wy * rx

    def _lugre(self, pc, vx, vy, N):
        dt = self.dt
        vn = math.hypot(vx, vy)
        gv = pc.mu_k + (pc.mu_s - pc.mu_k) * math.exp(-(vn / pc.v_s) ** 2)
        den = 1.0 + dt * pc.sg0 * vn / gv
        z = pc.z
        z[0] = (z[0] + dt * vx) / den
        z[1] = (z[1] + dt * vy) / den
        return -N * pc.sg0 * z[0], -N * pc.sg0 * z[1]

    # -------------------------------------------------------------------------------------------- forces
    def forces(self, fpush: float = 0.0):
        d = self.d
        _kernel(d.site_xpos, d.xmat, d.xpos, d.xipos, d.cvel, d.subtree_com, d.xfrc_applied, self.tab, self.zst,
                self.kout, self.dt, fpush, self.bh, self.s_tip, self.body_arr)

    def summary(self):
        """Forces of the last step as a dict (skid and ball)."""
        ko = self.kout
        o = self.out
        o["Ns"], o["fsx"], o["fsy"] = float(ko[0, 0]), float(ko[0, 1]), float(ko[0, 2])
        o["Nb"], o["fbx"], o["fby"] = float(ko[1, 0]), float(ko[1, 1]), float(ko[1, 2])
        return o

    def forces_py(self, fpush: float = 0.0):
        """Reference Python implementation of forces() (tests compare the two)."""
        d = self.d
        xf = d.xfrc_applied
        for b in self.bodies:
            xf[b, :] = 0.0
        for pc in self.pts:
            if pc.kind == "ring":
                if self.fixed_skid:
                    sp = d.site_xpos[self.s_skid]
                    px, py, pz = sp[0], sp[1], sp[2]
                else:
                    p = self._ring_point()
                    px, py, pz = p[0], p[1], p[2]
            else:
                ctr = d.site_xpos[pc.geom["site"]] if "site" in pc.geom else d.xpos[pc.body]
                px, py, pz = ctr[0], ctr[1], ctr[2] - pc.geom["r"]
            vx, vy, vz = self._point_velocity(pc.body, px, py, pz)
            N = 0.0
            if pz < 0.0:
                N = -pc.k * pz - pc.c * vz
                if N < 0.0:
                    N = 0.0
            if N > 0.0:
                fx, fy = self._lugre(pc, vx, vy, N)
                ci = d.xipos[pc.body]
                rx, ry, rz = px - ci[0], py - ci[1], pz - ci[2]
                row = xf[pc.body]
                row[0] += fx; row[1] += fy; row[2] += N
                row[3] += ry * N - rz * fy
                row[4] += rz * fx - rx * N
                row[5] += rx * fy - ry * fx
            else:
                pc.z[0] = pc.z[1] = 0.0
                fx = fy = 0.0
            pc.N, pc.fx, pc.fy = N, fx, fy
            pc.pv = (px, py, pz, vx, vy, vz)
        if fpush != 0.0:
            pt = d.site_xpos[self.s_tip]
            ch = d.xipos[self.bh]
            row = xf[self.bh]
            row[2] -= fpush
            row[3] -= (pt[1] - ch[1]) * fpush
            row[4] += (pt[0] - ch[0]) * fpush
        o = self.out
        s, b = self.pts[0], self.pts[1]
        o["Ns"], o["fsx"], o["fsy"] = s.N, s.fx, s.fy
        o["Nb"], o["fbx"], o["fby"] = b.N, b.fx, b.fy
        return o

    def dissipated_power(self) -> float:
        """Friction and normal-damping power (W, >= 0 dissipated) of the point contacts this step (energy audit)."""
        ko = self.kout
        return float(-np.sum(ko[:, 1] * ko[:, 6] + ko[:, 2] * ko[:, 7] + ko[:, 0] * ko[:, 8]))


# ------------------------------------------------------------------------------------------------ compiled kernel
from numba import njit  # noqa: E402

# point parameter columns
K_KIND, K_BODY, K_SITE, K_ROOT, K_K, K_C, K_MUK, K_MUS, K_VS, K_SG0, K_R, K_ZR, K_R0, K_RHO, K_HO = range(15)
NPAR = 15


@njit(cache=True)
def _kernel(site_xpos, xmat, xpos, xipos, cvel, subtree_com, xfrc, pts, z, out, dt, fpush, bh, s_tip, bodies):
    for b in bodies:
        for j in range(6):
            xfrc[b, j] = 0.0
    for i in range(pts.shape[0]):
        kind = int(pts[i, K_KIND]); body = int(pts[i, K_BODY]); site = int(pts[i, K_SITE]); root = int(pts[i, K_ROOT])
        if kind == 0:                                   # body-fixed point (H1 skid point)
            px = site_xpos[site, 0]; py = site_xpos[site, 1]; pz = site_xpos[site, 2]
        elif kind == 1:                                 # lowest point of the C ring on the handle
            a0 = xmat[body, 2]; a1 = xmat[body, 5]; a2 = xmat[body, 8]
            zr = pts[i, K_ZR]
            cx = xpos[body, 0] + zr * a0; cy = xpos[body, 1] + zr * a1; cz = xpos[body, 2] + zr * a2
            ux = a2 * a0; uy = a2 * a1; uz = -1.0 + a2 * a2           # -n projected on the ring plane
            nu = math.sqrt(ux * ux + uy * uy + uz * uz)
            if nu < 1e-12:
                ux = xmat[body, 0]; uy = xmat[body, 3]; uz = xmat[body, 6]
            else:
                ux /= nu; uy /= nu; uz /= nu
            e1x = xmat[body, 0]; e1y = xmat[body, 3]; e1z = xmat[body, 6]
            e2x = xmat[body, 1]; e2y = xmat[body, 4]; e2z = xmat[body, 7]
            ang = math.atan2(ux * e2x + uy * e2y + uz * e2z, ux * e1x + uy * e1y + uz * e1z)
            lim = math.pi - pts[i, K_HO]
            if abs(ang) > lim:
                ang = lim if ang > 0 else -lim
                ca = math.cos(ang); sa = math.sin(ang)
                ux = ca * e1x + sa * e2x; uy = ca * e1y + sa * e2y; uz = ca * e1z + sa * e2z
            R0 = pts[i, K_R0]
            px = cx + R0 * ux; py = cy + R0 * uy; pz = cz + R0 * uz - pts[i, K_RHO]
        else:                                           # lowest point of a sphere (site centre, radius r)
            px = site_xpos[site, 0]; py = site_xpos[site, 1]; pz = site_xpos[site, 2] - pts[i, K_R]
        # velocity of the body's material point at p: v = v_c + w x (p - subtree_com[root])
        wx = cvel[body, 0]; wy = cvel[body, 1]; wz = cvel[body, 2]
        rx = px - subtree_com[root, 0]; ry = py - subtree_com[root, 1]; rz = pz - subtree_com[root, 2]
        vx = cvel[body, 3] + wy * rz - wz * ry
        vy = cvel[body, 4] + wz * rx - wx * rz
        vz = cvel[body, 5] + wx * ry - wy * rx
        N = 0.0
        if pz < 0.0:
            N = -pts[i, K_K] * pz - pts[i, K_C] * vz
            if N < 0.0:
                N = 0.0
        fx = 0.0; fy = 0.0
        if N > 0.0:
            vn = math.sqrt(vx * vx + vy * vy)
            muk = pts[i, K_MUK]; mus = pts[i, K_MUS]; sg0 = pts[i, K_SG0]
            gv = muk + (mus - muk) * math.exp(-(vn / pts[i, K_VS]) ** 2)
            den = 1.0 + dt * sg0 * vn / gv
            z[i, 0] = (z[i, 0] + dt * vx) / den
            z[i, 1] = (z[i, 1] + dt * vy) / den
            fx = -N * sg0 * z[i, 0]
            fy = -N * sg0 * z[i, 1]
            cx_ = xipos[body, 0]; cy_ = xipos[body, 1]; cz_ = xipos[body, 2]
            qx = px - cx_; qy = py - cy_; qz = pz - cz_
            xfrc[body, 0] += fx; xfrc[body, 1] += fy; xfrc[body, 2] += N
            xfrc[body, 3] += qy * N - qz * fy
            xfrc[body, 4] += qz * fx - qx * N
            xfrc[body, 5] += qx * fy - qy * fx
        else:
            z[i, 0] = 0.0; z[i, 1] = 0.0
        out[i, 0] = N; out[i, 1] = fx; out[i, 2] = fy
        out[i, 3] = px; out[i, 4] = py; out[i, 5] = pz
        out[i, 6] = vx; out[i, 7] = vy; out[i, 8] = vz
    if fpush != 0.0:
        tx = site_xpos[s_tip, 0] - xipos[bh, 0]; ty = site_xpos[s_tip, 1] - xipos[bh, 1]
        xfrc[bh, 2] -= fpush
        xfrc[bh, 3] -= ty * fpush
        xfrc[bh, 4] += tx * fpush
