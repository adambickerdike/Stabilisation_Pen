r"""The Rev J firmware in the loop: every controller runs causally at the 2 kHz tick on the pen's own sensors
(sensing.py) and commands the devices inside sim2 (PROPOSED DESIGN control laws; SIMULATION results).

Nose (tip reference in the page plane, converted to the gimbal's tip deflection q1 = sin(theta) (x . h), q2 = x . t2,
clipped to the usable travel; authority on while the pen is within 0.8 mm of the page (page-sensor valid; the
handwriting study's hover gating T7, here with the page sensor's own limit), ramp 50 ms):
  off        held centred
  tremor     -d_hat from the guarded AKF (akf_online.GuardedTracker: the Rev H tracker re-tuned in round 1,
             results/opt/inertial_tracker_revh.json, horizon + the servo's group delay; frequency-runaway guard)
  oracle     -d(t + group delay), d = handle(tremor) - handle(clean) of the same plant: the mechanism's limit
  guide      HW1's template guidance (capture gate 2 mm, drop rule 2.5 mm / 60 ms, stroke matching; gain g_guide)
  detail     template point - handle, no gate (drive study's '+nose' for lead-through: the nose adds the detail)
  autowrite  nose2's autowrite (planner.py plan, complementary handle observer 100 Hz, progress filter 0.4 Hz,
             command = planned ink point - predicted handle; results/nose2 tuning) with the pen lift along the plan
Heel wheel (drive/plant.py laws and results/drive/rules.json gains, ported to the tick):
  off        retracted (no contact)
  free       steered free (LIT HAP-60 eq. 2: heading turns toward the writer's lateral push, apparent mass m_eff),
             drive train back-driven with 70 % of its friction compensated
  path       steer-only guidance: Stanley law on the template (tangent L_t ahead + atan(k_st e / v)), free mode when
             the writer leaves it (yield), lateral release above the force cap (optional), pre-steer while lifted
  tremor     free mode on the low-passed lateral push (m_eff 0.05, 9.3 Hz) + along-path brake of the high-passed
             speed (b 1.95 N s/m, dissipative only): the drive study's 'wheel steer + brake' (tuned there)
  lead       Stanley steering + drive push along the template: F = max(0, F_lead + Kv (v_lead - v)) (0.167 N,
             6.27 N s/m, 20 mm/s), stop at the stroke end: lead-through / gross-scale autowrite
  Supervisor (every mode): command cap min(0.5 N, 0.8 mu_hat N_meas), 20 N/s slew, zero below 0.02 N wheel load,
             yield after 0.3 s beyond 4 mm, slip detection (page sensor against wheel odometry) lowering mu_hat.
End-cap (reaction mass): 'ff' = the Rev H phasor feed-forward of study K (u = Re(H) e(t) - Im(H) e(t - T/4),
H = -G(f)^-1 at the tracked frequency, G the tip response per unit slug force of this model's linearisation at
r_rot 0.5, gain 0.75, capped at the coil force that uses 70 % of the stroke on the flexure) on the tracker's estimate
of the tremor that the end-cap has not yet removed (internal model: e = d_hat - G u applied), so the online loop keeps
the open-loop cascade of study K.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import ROOT  # noqa: F401
from .akf_online import DetParams, GatedListening, GuardParams, GuardedTracker
from .sensing import OnlineSensors
from handwriting.plant import _nearest  # noqa: E402

TWO_PI = 2.0 * math.pi


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _near_mod_pi(target, current):
    d = _wrap(target - current)
    if d > 0.5 * math.pi:
        d -= math.pi
    elif d < -0.5 * math.pi:
        d += math.pi
    return current + d


@dataclass
class WheelGains:
    """results/drive/rules.json (frozen by study D on its tuning writers before its test) and drive/scenarios
    Hardware; the lateral release is the post-test proposal of study D (off unless set)."""
    k_st: float = 15.419668260712363
    L_t: float = 0.00040255014753969986
    F_lead: float = 0.16712713318501016
    Kv: float = 6.269901150870037
    v_lead: float = 0.02
    m_eff_free: float = 0.3
    m_eff_tremor: float = 0.05
    f_lp_tremor: float = 9.33639490057998
    b_brake: float = 1.9540397807675998
    b_max: float = 50.0
    u_min: float = 5e-3
    F_cap: float = 0.5
    k_safe: float = 0.8
    mu_hat0: float = 0.8
    slew: float = 20.0
    over_d: float = 4e-3
    over_t: float = 0.3
    fade: float = 0.3
    restore: float = 0.5
    k_fc: float = 0.7
    rel_on: bool = False
    m_rel: float = 0.02
    slip_v: float = 8e-3
    slip_t: float = 0.05
    N_noise: float = 0.01
    Flat_noise: float = 0.005
    v_noise: float = 0.002
    label: str = "results/drive/rules.json (sha256_16 6b64568210e3c0b5) + drive Hardware; ASSUMPTION where not tuned"


@dataclass
class FWConfig:
    nose: str = "off"
    wheel: str = "off"
    endcap: str = "off"
    pen_lift: str = "none"
    akf: Optional[Dict] = None
    guard: GuardParams = field(default_factory=GuardParams)
    det: DetParams = field(default_factory=DetParams)
    wheel_gains: WheelGains = field(default_factory=WheelGains)
    g_guide: float = 1.0
    capture: float = 2.0e-3
    drop_d: float = 2.5e-3
    drop_t: float = 0.06
    tau_auth: float = 0.05
    endcap_gain: float = 0.75
    endcap_stroke_frac: float = 0.7
    aw_obs_hz: float = 100.0
    aw_prog_hz: float = 0.4
    aw_lift_delay: float = 8e-3
    lift_stroke: float = 0.5e-3
    reach: Optional[float] = None       # page-plane clip of the nose command (default: the usable travel)
    policy: Optional[object] = None     # an RL policy object with .act(obs) -> action (rl.py)
    min_lift_s: float = 0.04            # a touchdown starts a new template stroke only after the ball was off the
                                        # paper this long (sim2's touchdown bounces: ASSUMPTION 40 ms)
    tracker: str = "guarded"            # 'guarded' (Rev H AKF + guard + detector gate) | 'gl' (ai2's gated listening,
                                        # fallback the Rev H tracker as built, DEC-042) | 'glg' (gated listening with
                                        # the guarded tracker as the fallback)
    seed: int = 0
    imu_noise: float = 1.0              # IMU noise scale (DR: 0.5-2 x the datasheet densities)
    record_streams: bool = False        # keep the sensor samples (for learned estimators run on the record: replay)
    label: str = ""


class Firmware:
    """Called by the stepper once per 2 kHz tick (after mj_step1): returns the nose's tip-deflection reference (t1, t2)
    and sets the wheel, end-cap and pen-lift commands on the stepper."""

    def __init__(self, pm, fw: FWConfig, task: Optional[Dict] = None, wheel=None, mu_true: float = 0.9):
        self.pm = pm
        self.fw = fw
        self.task = task or {}
        cfg = pm.cfg
        self.Ts = 0.5e-3
        th = math.radians(cfg.geom.theta_deg)
        self.sth = math.sin(th)
        a, t1, t2, n, h = cfg.geom.vectors()
        self.h = h[:2].copy()
        self.t2 = t2[:2].copy()
        self.reach = fw.reach if fw.reach is not None else cfg.geom.travel
        self.sens = OnlineSensors(pm, self.Ts, seed=fw.seed + 11, noise_scale=fw.imu_noise)
        self.streams = {"acc": [], "pos": [], "con": []}
        nz = cfg.nose
        self.gd = 2.0 * nz.servo_zeta / (TWO_PI * nz.servo_hz) + 0.5 * self.Ts      # servo group delay + tick hold
        self.tracker = None
        if fw.nose == "tremor" or fw.endcap == "ff" or (fw.policy is not None):
            p = dict(fw.akf or {})
            p["acc_gd"] = 0.5 * self.Ts                    # the online IMU's block average (sensing.py)
            if fw.tracker == "guarded":
                self.tracker = GuardedTracker(p, Ts=self.Ts, horizon_extra=self.gd, guard=fw.guard, det=fw.det)
            elif fw.tracker in ("gl", "glg"):
                self.tracker = GatedListening(p, Ts=self.Ts, horizon_extra=self.gd,
                                              fallback_guard=fw.guard if fw.tracker == "glg" else None,
                                              fallback_det=fw.det)
            else:
                raise KeyError(fw.tracker)
        self.wheel = wheel
        self.g_auth = 0.0
        self.a_auth = 1.0 - math.exp(-self.Ts / fw.tau_auth)
        self.k = 0
        # latest available page sample (handle tip) and its velocity estimate
        self.ps = None
        self.ps_prev = None
        self.ps_valid = False
        self.vs = np.zeros(2)
        self.vlp = np.zeros(2)
        self.vl2 = np.zeros(2)
        self.page_q = []
        self.contact = False
        self.was_con = False
        self.up_s = 1.0                  # time the ball has been off the paper (slide sensor)
        self.up_s_prev = 1.0
        self.up_w = 1.0
        self.d_hat = np.zeros(2)
        self.q_page = np.zeros(2)
        self.log = {"q": [], "dhat": [], "f": [], "g": [], "det": [], "wheel_cmd": [], "ec": [], "lift": []}
        self._init_guide()
        self._init_wheel(mu_true)
        self._init_endcap()
        self._init_autowrite()
        self.lift_cmd = 0.0          # 1 = ball lifted (pen lift), applied by the stepper after the switching delay
        self.policy = fw.policy
        if self.policy is not None and hasattr(self.policy, "reset"):
            self.policy.reset(self)

    # ------------------------------------------------------------------------------------------------ helpers
    def to_q(self, x: np.ndarray):
        """Page-plane ink offset -> tip deflection (t1, t2), clipped to the reach."""
        r = math.hypot(x[0], x[1])
        if r > self.reach:
            x = x * (self.reach / r)
        return (self.sth * float(x @ self.h), float(x @ self.t2)), x

    # ------------------------------------------------------------------------------------------------ template
    def _init_guide(self):
        tm = self.task.get("template")
        if tm is None:
            self.tmpl = None
            return
        from handwriting.plant import stroke_ranges
        self.tmpl = np.ascontiguousarray(tm["xy"], dtype=np.float64)
        self.tdown = np.ascontiguousarray(tm["down"], dtype=np.float64)
        self.tss, self.tse = stroke_ranges(self.tdown)
        d = np.hypot(*np.diff(self.tmpl, axis=0).T) if len(self.tmpl) > 1 else np.zeros(0)
        self.dcum = np.r_[0.0, np.cumsum(d)]
        self.prog = 0
        self.cur_s = -1
        self.dist = 1e3
        self.over_tn = 0.0
        self.dropped = False
        self.gate_g = 0.0

    def _pick_stroke(self, px, py, cur):
        """The template stroke a touchdown starts: among the current one and the next three, the one whose start is
        nearest to the touchdown point (sim2 starts with the ball on the paper and bounces at touchdown, so counting
        touchdowns - HW1's rule - can skip a stroke)."""
        n = len(self.tss)
        best = min(cur + 1, n - 1)
        bd = 1e9
        for s in range(max(cur, 0), min(cur + 4, n)):
            a = int(self.tss[s])
            d = math.hypot(self.tmpl[a, 0] - px, self.tmpl[a, 1] - py)
            if d < bd:
                best, bd = s, d
        return best

    def _template_progress(self, px, py, new_stroke):
        """Stroke-matched nearest template sample (HW1 _nearest with stroke matching)."""
        if new_stroke:
            self.cur_s = self._pick_stroke(px, py, self.cur_s)
            self.dropped = False
            self.over_tn = 0.0
            if self.cur_s < len(self.tss):
                self.prog = int(self.tss[self.cur_s])
        if self.cur_s < len(self.tss) and self.cur_s >= 0:
            bj, dist = _nearest(self.tmpl, self.tdown, px, py, self.prog, 20, 400, int(self.tss[self.cur_s]),
                                int(self.tse[self.cur_s]))
        else:
            bj, dist = self.prog, 1e3
        self.prog = int(bj)
        self.dist = float(dist)
        return self.prog, self.dist

    def _tangent(self, j, lo, hi, span=0.3e-3):
        jf = j
        while jf + 1 < hi and self.dcum[jf] - self.dcum[j] < span:
            jf += 1
        jr = j
        while jr - 1 >= lo and self.dcum[j] - self.dcum[jr] < span:
            jr -= 1
        sx = self.tmpl[jf, 0] - self.tmpl[jr, 0]
        sy = self.tmpl[jf, 1] - self.tmpl[jr, 1]
        sn = math.hypot(sx, sy)
        return (sx / sn, sy / sn) if sn > 0 else (1.0, 0.0)

    # ------------------------------------------------------------------------------------------------ wheel
    def _init_wheel(self, mu_true):
        g = self.fw.wheel_gains
        self.psic = 0.0
        self.gy = 1.0
        self.t_ov = 0.0
        self.muh = g.mu_hat0
        self.capd = 0.0
        self.fp = 0.0
        self.flp = 0.0
        self.dl = np.zeros(2)
        self.slipf = False
        self.alpha_lp_tr = 1.0 - math.exp(-TWO_PI * g.f_lp_tremor * self.Ts)
        self.alpha_lp3 = 1.0 - math.exp(-TWO_PI * 3.0 * self.Ts)
        self.alpha_v = 1.0 - math.exp(-TWO_PI * 100.0 * self.Ts)
        self.alpha_bd = 1.0 - math.exp(-TWO_PI * 30.0 * self.Ts)
        self.er_prev = 0.0
        self.erd = 0.0
        self.progd = 0
        self.cur_sd = -1
        self.w_log = {"N": 0.0, "F": 0.0}
        self.was_con_w = False
        self.rng_w = np.random.default_rng(self.fw.seed + 29)

    def _wheel_tick(self, t):
        fw, g, wh = self.fw, self.fw.wheel_gains, self.wheel
        if wh is None or fw.wheel == "off":
            return
        o = wh.out
        N_true = float(o[0])
        N_meas = N_true + g.N_noise * self.rng_w.standard_normal() if N_true > 0 else 0.0
        Flat = float(o[12]) + g.Flat_noise * self.rng_w.standard_normal()
        u = float(wh.st[2])
        psi = float(wh.st[3])
        con = self.contact and N_meas > 0.02
        vs = self.vs
        want = self.psic
        F_along = 0.0
        has_long = False
        Fmc = 0.0
        mode = fw.wheel
        if con and self.ps is None:
            con = False                      # no page position yet: the wheel waits (free)
        if con:
            if mode in ("path", "lead") and self.tmpl is not None:
                new = (not self.was_con_w) and self.up_w >= fw.min_lift_s
                if new:
                    self.cur_sd = self._pick_stroke(self.ps[0], self.ps[1], self.cur_sd)
                    if self.cur_sd < len(self.tss):
                        self.progd = int(self.tss[self.cur_sd])
                if 0 <= self.cur_sd < len(self.tss):
                    lo, hi = int(self.tss[self.cur_sd]), int(self.tse[self.cur_sd])
                    bj, bd = _nearest(self.tmpl, self.tdown, self.ps[0], self.ps[1], self.progd, 20, 400, lo, hi)
                    self.progd = int(bj)
                else:
                    lo, hi = 0, 1
                    bd = 1e3
                j = self.progd
                e = self.tmpl[j] - self.ps
                er = math.hypot(e[0], e[1])
                sx, sy = self._tangent(j, lo, hi)
                end_zone = self.dcum[hi - 1] - self.dcum[j] < 0.3e-3
                if new:
                    self.er_prev = er
                    self.erd = 0.0
                self.erd += self.alpha_bd * ((er - self.er_prev) / self.Ts - self.erd)
                self.er_prev = er
                # supervisor: yield when the writer keeps away from the template
                if er > g.over_d:
                    self.t_ov += self.Ts
                else:
                    self.t_ov = max(0.0, self.t_ov - self.Ts)
                if self.t_ov > g.over_t:
                    self.gy = max(0.0, self.gy - self.Ts / g.fade)
                elif er < 1e-3:
                    self.gy = min(1.0, self.gy + self.Ts / g.restore)
                if self.gy < 0.5:
                    um = max(abs(u), g.u_min)
                    want = self.psic + Flat / (g.m_eff_free * um) * self.Ts
                else:
                    # Stanley: template tangent L_t ahead + atan(k_st e_cross / v)
                    jt = j
                    while jt + 1 < hi and self.dcum[jt] - self.dcum[j] < g.L_t:
                        jt += 1
                    qx, qy = self._tangent(jt, lo, hi)
                    if vs[0] * qx + vs[1] * qy < 0.0 and (vs[0] ** 2 + vs[1] ** 2) > 1e-6:
                        qx, qy = -qx, -qy
                    ecr = e[0] * (-qy) + e[1] * qx
                    vm = math.hypot(vs[0], vs[1])
                    want = _near_mod_pi(math.atan2(qy, qx) + math.atan(g.k_st * ecr / (vm + 0.005)), self.psic)
                if g.rel_on and abs(Flat) > self.capd > 0.0:
                    um = max(abs(u), g.u_min)
                    want += math.copysign(abs(Flat) - self.capd, Flat) / (g.m_rel * um) * self.Ts
                if mode == "lead":
                    has_long = True
                    sgn = 1.0 if (math.cos(psi) * sx + math.sin(psi) * sy) >= 0.0 else -1.0
                    v_al = vs[0] * sx + vs[1] * sy
                    F_along = sgn * max(0.0, g.F_lead + g.Kv * (g.v_lead - v_al)) * self.gy
                    if end_zone:
                        F_along = -sgn * g.Kv * v_al
            elif mode in ("free", "tremor"):
                self.flp += self.alpha_lp_tr * (Flat - self.flp)
                um = max(abs(u), g.u_min)
                if mode == "tremor":
                    want = self.psic + self.flp / (g.m_eff_tremor * um) * self.Ts
                else:
                    want = self.psic + Flat / (g.m_eff_free * um) * self.Ts
            self.psic = want
        else:
            # lifted: zero force; pre-steer toward the next template stroke's first direction (the app knows it)
            if mode in ("path", "lead") and self.tmpl is not None:
                ns = self.cur_sd + 1
                if ns < len(self.tss):
                    a_ = int(self.tss[ns])
                    sx, sy = self._tangent(a_, a_, int(self.tse[ns]), span=0.5e-3)
                    self.psic = _near_mod_pi(math.atan2(sy, sx), self.psic)
            self.gy = 1.0
            self.t_ov = 0.0
        self.was_con_w = con
        self.up_w = 0.0 if con else self.up_w + self.Ts
        # force cap from the traction estimate, slew
        self.capd = min(g.F_cap, self.wheel.wp.F_peak, g.k_safe * self.muh * max(N_meas, 0.0))
        if has_long:
            f = max(-self.capd, min(self.capd, F_along))
        else:
            f = 0.0
        if not con:
            f = 0.0
        df = f - self.fp
        if abs(df) > g.slew * self.Ts:
            f = self.fp + math.copysign(g.slew * self.Ts, df)
        self.fp = f
        # slip detection: page-sensor velocity against the wheel's surface velocity
        if con:
            wx_, wy_ = u * math.cos(psi), u * math.sin(psi)
            rv = np.array([vs[0] - wx_, vs[1] - wy_])
            if mode in ("path", "tremor", "free") and not has_long:
                c_, s_ = math.cos(psi), math.sin(psi)
                lat = -rv[0] * s_ + rv[1] * c_
                rv = np.array([-lat * s_, lat * c_])
            self.dl += rv * self.Ts - self.dl * self.Ts / g.slip_t
            d_th = 1.5 * 1.2 * N_meas / wh.wp.k_lat + g.slip_v * 0.004
            if math.hypot(self.dl[0], self.dl[1]) > d_th:
                if not self.slipf:
                    self.muh = max(0.3, 0.9 * self.muh)
                self.slipf = True
            else:
                self.slipf = False
                self.muh += (g.mu_hat0 - self.muh) * self.Ts / 2.0
        else:
            self.slipf = False
            self.dl[:] = 0.0
        # motor command
        fric = g.k_fc * (wh.wp.c_bd * u + wh.wp.F_bdc * math.tanh(u / 1e-3))
        if mode == "tremor":
            hx, hy = math.cos(psi), math.sin(psi)
            vh_ = (vs[0] - self.vl2[0]) * hx + (vs[1] - self.vl2[1]) * hy
            Fd = -g.b_brake * vh_
            Fmc = Fd if Fd * u < 0.0 else 0.0
            if abs(Fmc) > g.b_max * abs(u):
                Fmc = -g.b_max * u
        elif mode in ("lead",):
            Fmc = f + fric
        elif mode in ("free", "path"):
            Fmc = fric                                   # the drive train's own friction compensated (steer only)
        if not con:
            Fmc = fric if mode in ("lead", "free", "path") else 0.0
        wh.set_command(self.psic, Fmc)
        self.w_log = {"N": N_true, "F": f, "Fmc": Fmc, "muh": self.muh, "capd": self.capd, "slip": self.slipf, "gy": self.gy}

    # ------------------------------------------------------------------------------------------------ end-cap
    def _init_endcap(self):
        self.ec = None
        if self.fw.endcap != "ff":
            return
        from .plant_frf import endcap_plant
        f, G = endcap_plant(self.pm)
        H = np.array([-np.linalg.pinv(g) for g in G])
        self.ec = {"f": f, "G": G, "H": H, "u_hist": [], "e_hist": []}
        rm = [pl for pl in self.pm.plugins if pl.name == "rm"][0]
        self.rm = rm
        self.ec_u = np.zeros(2)

    def _endcap_tick(self, t, dh, f_est):
        if self.ec is None:
            return None
        ec = self.ec
        fq = float(np.clip(f_est, ec["f"][0], ec["f"][-1]))
        kq = max(1, int(round(1.0 / (4.0 * fq * self.Ts))))
        Gr = np.array([[np.interp(fq, ec["f"], ec["G"][:, i, j].real) for j in range(2)] for i in range(2)])
        Gi = np.array([[np.interp(fq, ec["f"], ec["G"][:, i, j].imag) for j in range(2)] for i in range(2)])
        Hr = np.array([[np.interp(fq, ec["f"], ec["H"][:, i, j].real) for j in range(2)] for i in range(2)])
        Hi = np.array([[np.interp(fq, ec["f"], ec["H"][:, i, j].imag) for j in range(2)] for i in range(2)])
        uh = ec["u_hist"]
        eh = ec["e_hist"]
        u_now = self.ec_u
        u_q = uh[-kq] if len(uh) >= kq else np.zeros(2)
        # internal model: the handle motion the end-cap itself caused (phasor at the tracked frequency)
        y_u = Gr @ u_now - Gi @ u_q
        e = dh - y_u
        eh.append(e.copy())
        e_q = eh[-kq] if len(eh) > kq else np.zeros(2)
        u = self.fw.endcap_gain * (Hr @ e - Hi @ e_q)
        # cap: the coil force that uses stroke_frac of the stroke on the flexure (endcap/sim.rm_coil_cap)
        w = TWO_PI * fq
        rm = self.rm
        dyn = math.sqrt((rm.k_c - rm.m * w * w) ** 2 + (rm.c_c * w) ** 2)
        cap = min(rm.K_f * rm.I_max, self.fw.endcap_stroke_frac * rm.stroke[0] * dyn)
        mag = float(np.max(np.abs(u)))
        if mag > cap:
            u = u * (cap / mag)
        if not self.contact and not self.ps_valid:
            u = u * 0.0
        uh.append(u.copy())
        if len(uh) > 400:
            del uh[:200]
        if len(eh) > 400:
            del eh[:200]
        self.ec_u = u
        return u

    # ------------------------------------------------------------------------------------------------ autowrite
    def _init_autowrite(self):
        self.aw = None
        plan = self.task.get("plan")
        if plan is None or self.fw.nose != "autowrite":
            return
        w = TWO_PI * self.fw.aw_obs_hz
        Tp = 1e-3
        kp_, kv_ = 2 * 0.9 * w * Tp, w * w * Tp
        self.aw = {"plan": plan, "t": plan.t, "x": plan.xy[:, 0].copy(), "y": plan.xy[:, 1].copy(),
                   "down": plan.down.astype(float), "x0": float(plan.hand[0, 0]), "v_h": float(self.task["v_h"]),
                   "kp": kp_, "kv": kv_, "wp": TWO_PI * self.fw.aw_prog_hz, "p": None, "v": np.zeros(2), "a": np.zeros(2),
                   "hist": [], "xf": None, "vf": float(self.task["v_h"]), "tau": 0.0, "tau_log": []}

    def _autowrite_tick(self, t, acc_samples, page_new):
        aw = self.aw
        Ts = self.Ts
        # complementary handle observer (nose2/autowrite._loop): IMU double integration corrected by the page sensor
        if aw["p"] is None:
            if not page_new:
                return np.zeros(2), False
            aw["p"] = np.array(page_new[-1][2], float)
        a = acc_samples if acc_samples is not None else aw["a"]
        aw["a"] = np.asarray(a, float)
        aw["v"] = aw["v"] + aw["a"] * Ts
        aw["p"] = aw["p"] + aw["v"] * Ts
        aw["hist"].append((t, aw["p"].copy()))
        if len(aw["hist"]) > 200:
            del aw["hist"][:100]
        for (t_acq, t_av, y, ok) in page_new:
            if not ok:
                continue
            ph = None
            for (th_, pp) in reversed(aw["hist"]):
                if th_ <= t_acq + 1e-12:
                    ph = pp
                    break
            if ph is None:
                continue
            e = np.asarray(y) - ph
            dt_a = t - t_acq
            aw["p"] = aw["p"] + aw["kp"] * e + aw["kv"] * e * dt_a
            aw["v"] = aw["v"] + aw["kv"] * e
            for i in range(len(aw["hist"])):
                th_, pp = aw["hist"][i]
                if th_ >= t_acq:
                    aw["hist"][i] = (th_, pp + aw["kp"] * e + aw["kv"] * e * (th_ - t_acq))
        L = self.gd
        pred = aw["p"] + aw["v"] * L + 0.5 * aw["a"] * L * L
        # progress: critically damped tracking filter on the along-line position
        if aw["xf"] is None:
            aw["xf"] = float(aw["p"][0])
        e = float(aw["p"][0]) - aw["xf"]
        aw["vf"] += aw["wp"] ** 2 * e * Ts
        aw["xf"] += (aw["vf"] + 2.0 * aw["wp"] * e) * Ts
        tn = (aw["xf"] - aw["x0"]) / aw["v_h"] + L
        if tn > aw["tau"]:
            aw["tau"] = tn
        tau = aw["tau"]
        tx = np.interp(tau, aw["t"], aw["x"])
        ty = np.interp(tau, aw["t"], aw["y"])
        down = np.interp(tau + self.fw.aw_lift_delay, aw["t"], aw["down"]) > 0.5
        aw["tau_log"].append(tau)
        return np.array([tx, ty]) - pred, bool(down)

    # ------------------------------------------------------------------------------------------------ main tick
    def tick(self, t: float):
        fw = self.fw
        r = self.sens.read(t)
        if self.fw.record_streams:
            S_ = self.streams
            S_["acc"].append((r["acc_t"], r["acc_av"], r["acc"][0], r["acc"][1]))
            if "page" in r:
                p_ = r["page"]
                S_["pos"].append((p_[0], p_[1], p_[2][0], p_[2][1], 1.0 if p_[3] else 0.0))
            S_["con"].append((t, t + self.pm.cfg.sensors.slide_latency, 1.0 if r["contact"] else 0.0))
        # page samples: queue with their availability; the controllers use the latest available one
        page_new = []
        if "page" in r:
            self.page_q.append(r["page"])
        while self.page_q and self.page_q[0][1] <= t + 1e-12:
            s = self.page_q.pop(0)
            page_new.append(s)
            if self.tracker is not None:
                self.tracker.feed_pos(s[0], s[1], s[2], s[3], ok_det=bool(s[3]) and self.contact)
            self.ps_valid = s[3]
            if s[3]:
                p_new = np.array(s[2])
                if self.ps is not None:
                    v_new = (p_new - self.ps) / 1e-3
                    self.vs = self.vs + self.alpha_v * 2.0 * (v_new - self.vs)
                self.ps = p_new
        self.vlp += self.alpha_lp3 * (self.vs - self.vlp)
        self.vl2 += self.alpha_lp3 * (self.vlp - self.vl2)
        if self.tracker is not None:
            self.tracker.feed_acc(r["acc_t"], r["acc_av"], r["acc"])
            self.d_hat = self.tracker.step(t).copy()
        self.was_con = self.contact
        self.contact = r["contact"]
        self.up_s_prev = self.up_s
        self.up_s = 0.0 if self.contact else self.up_s + self.Ts
        # nose authority: hover gating by the page sensor's validity
        target = 1.0 if self.ps_valid else 0.0
        self.g_auth += self.a_auth * (target - self.g_auth)
        x = np.zeros(2)
        mode = fw.nose
        if mode == "tremor":
            x = -self.g_auth * self.d_hat
        elif mode == "oracle":
            dtab = self.task["oracle_d"]
            k = min(int(round((t + self.gd) / self.Ts)), len(dtab) - 1)
            x = -self.g_auth * dtab[k]
        elif mode in ("guide", "detail") and self.tmpl is not None and self.ps is not None:
            new = self.contact and not self.was_con and self.up_s_prev >= fw.min_lift_s
            if self.contact:
                j, dist = self._template_progress(self.ps[0], self.ps[1], new)
                if mode == "guide":
                    if dist > fw.drop_d:
                        self.over_tn += self.Ts
                    else:
                        self.over_tn = 0.0
                    if self.over_tn > fw.drop_t:
                        self.dropped = True
                    if dist <= fw.capture:
                        gate = 1.0
                    elif dist < 1.5 * fw.capture:
                        gate = (1.5 * fw.capture - dist) / (0.5 * fw.capture)
                    else:
                        gate = 0.0
                    if self.dropped:
                        gate = 0.0
                else:
                    gate = 1.0 if dist < 10e-3 else 0.0
                x = fw.g_guide * gate * (self.tmpl[j] - self.ps) * self.g_auth
        elif mode == "autowrite" and self.aw is not None:
            acc = r["acc"]
            x, down = self._autowrite_tick(t, acc, page_new)
            self.lift_cmd = 0.0 if down else 1.0
            x = x * self.g_auth if self.aw["p"] is not None else x * 0.0
        if self.policy is not None:
            x = self.policy.act(self, t, x)
        q, x_used = self.to_q(x)
        self.q_page = x_used
        # wheel and end-cap
        self._wheel_tick(t)
        ec_u = None
        if fw.endcap == "ff" and self.tracker is not None:
            ec_u = self._endcap_tick(t, self.d_hat, self.tracker.last[2])
        self.ec_cmd = ec_u
        self.k += 1
        return q
