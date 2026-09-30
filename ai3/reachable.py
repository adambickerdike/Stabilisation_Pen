"""Accepted future ink with continuous actuator bounds (CALC / executable design).

This is a reference generator and contact/reference supervisor, not a validated
servo. The pen body is predicted with constant velocity over ONE admitted letter;
bounded prediction errors are charged against travel and actuator authority.
Every ink stroke, lift dwell, air move and lower dwell is checked. A new letter
requires a fresh measured body state. Missing absolute page anchoring aborts.

Unlike complete_plan.py, all limits concern the actual stage coordinates. Cubic
or polygon corners are not sent to an ideal stage: a C4 quintic spline, with zero
page velocity and acceleration at stroke ends, is retimed and certified using
Bezier convex-hull bounds between samples. Geometry is preserved only within an
explicit, also bounded, tolerance. These conservative bounds can reject a path
that a more sophisticated trajectory optimiser could execute.
"""
from __future__ import annotations

import hashlib
import copy
import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
from scipy.interpolate import make_interp_spline

from .layers import LayerError, PlanLetter, WritingPlan


@dataclass(frozen=True)
class MotionLimits:
    # Radius in the nib/stage plane. Rev K travel is radial, not an independent x/y box.
    radius_m: float = 1.0587e-3
    hard_stop_m: float = 1.2587e-3
    tilt_deg: float = 50.0
    tracking_reserve_m: float = 0.15e-3
    speed_m_s: float = 0.030
    acceleration_m_s2: float = 2.0
    jerk_m_s3: float = 300.0
    brake_acceleration_m_s2: float = 1.0
    reaction_delay_s: float = 0.004
    # Fast-contact research assumption, NOT Rev K's slower counterface lift.
    # The replay study also runs 0.200 s both ways; no latch is assumed here.
    lift_delay_s: float = 0.020
    lower_delay_s: float = 0.020
    position_error_m: float = 0.025e-3
    velocity_error_m_s: float = 0.10e-3
    acceleration_error_m_s2: float = 0.20e-3
    jerk_error_m_s3: float = 0.050
    geometry_error_m: float = 0.075e-3
    max_sensor_age_s: float = 0.006
    min_contact_N: float = 0.020
    max_contact_N: float = 0.40
    max_temperature_C: float = 60.0    # coil-temperature supervisory target, ASSUMPTION

    def __post_init__(self):
        vals = [v for v in vars(self).values()]
        if not all(np.isfinite(vals)) or any(v < 0 for v in vals):
            raise ValueError("limits must be finite and nonnegative")
        if not 0 < self.tilt_deg <= 90 or not 0 < self.radius_m < self.hard_stop_m:
            raise ValueError("invalid tilt or radial stops")
        if min(self.speed_m_s, self.acceleration_m_s2, self.jerk_m_s3,
               self.brake_acceleration_m_s2, self.max_sensor_age_s) <= 0:
            raise ValueError("motion and freshness limits must be positive")

    @property
    def page_to_stage(self):
        # Page x is the tilt direction; this assumes an independently known pen roll.
        return np.diag([math.sin(math.radians(self.tilt_deg)), 1.0])

    def prediction_error(self, t: float) -> float:
        return self.position_error_m + self.velocity_error_m_s * t + 0.5 * self.acceleration_error_m_s2 * t*t


@dataclass(frozen=True)
class StageModel:
    """Linear force/electrical screen, NOT a measured actuator model.

    Some scalar parameters originate in Rev K, but this is a generic planar
    translation model, not its constrained, axially sliding mechanism. Damping,
    inductance, load uncertainty and current derating are declared assumptions.
    Spatial magnetic coupling, inertia mapping, lead heat and nonlinear contact
    must be checked by the separate mechanics model.
    """
    mass_kg: float = 0.00344
    stiffness_N_m: float = 1.56
    damping_N_s_m: float = 0.08
    force_constant_N_A: tuple = (0.334 * math.sqrt(2.5), 0.272 * math.sqrt(2.5))
    resistance_ohm: float = 3.03       # includes moving leads; Km above refers to coil-only R=2.5 ohm
    inductance_H: float = 0.001       # ASSUMPTION, not measured
    current_limit_A: float = 0.70     # derated from 1 A design limit, not demonstrated
    voltage_limit_V: float = 3.0      # headroom below 3.3 V bus
    bias_force_N: tuple = (0.0217, 0.0)
    load_uncertainty_N: float = 0.010
    load_slew_uncertainty_N_s: float = 2.0   # ASSUMPTION, must be measured with contact

    def __post_init__(self):
        scalars = [self.mass_kg, self.stiffness_N_m, self.damping_N_s_m,
                   self.resistance_ohm, self.inductance_H, self.current_limit_A,
                   self.voltage_limit_V, self.load_uncertainty_N,self.load_slew_uncertainty_N_s]
        if not np.isfinite(scalars).all() or min(scalars) < 0:
            raise ValueError("stage model values must be finite and nonnegative")
        if len(self.force_constant_N_A) != 2 or not np.isfinite(self.force_constant_N_A).all() or min(self.force_constant_N_A) <= 0:
            raise ValueError("two positive force constants are required")
        if len(self.bias_force_N) != 2 or not np.isfinite(self.bias_force_N).all():
            raise ValueError("two finite bias forces are required")


def _elevate(b: np.ndarray, degree: int) -> np.ndarray:
    """Degree elevation leaves the represented Bezier curve exactly unchanged."""
    b = np.asarray(b, float)
    while len(b) - 1 < degree:
        n = len(b) - 1
        z = np.empty((n + 2, b.shape[1]))
        z[0], z[-1] = b[0], b[-1]
        for i in range(1, n + 1):
            z[i] = i/(n+1)*b[i-1] + (1-i/(n+1))*b[i]
        b = z
    return b


def _derivative(b: np.ndarray, duration: float, order: int = 1) -> np.ndarray:
    out = b
    for _ in range(order):
        out = (len(out)-1) * np.diff(out, axis=0) / duration
    return out


def _elevate_batch(b,degree):
    while b.shape[1]-1<degree:
        n=b.shape[1]-1
        alpha=np.arange(1,n+1)[None,:,None]/(n+1)
        b=np.concatenate([b[:,:1],alpha*b[:,:-1]+(1-alpha)*b[:,1:],b[:,-1:]],axis=1)
    return b


def _evaluate(b: np.ndarray, u: np.ndarray) -> np.ndarray:
    n = len(b)-1
    weights = np.column_stack([math.comb(n,k)*u**k*(1-u)**(n-k) for k in range(n+1)])
    return weights @ b


@dataclass(frozen=True)
class Piece:
    controls: np.ndarray              # six Bezier control vectors, page coordinates in metres
    duration: float
    phase: str                       # ink | lift | air | lower


@dataclass
class LetterTrajectory:
    pieces: list[Piece]
    body_origin: np.ndarray
    body_velocity: np.ndarray
    limits: MotionLimits
    model: StageModel
    geometry_bound_m: float
    bounds: dict = field(default_factory=dict)
    accepted_plan_id: Optional[int] = None
    letter_index: Optional[int] = None
    path_digest: str = ""
    certificate_digest: str = ""

    @property
    def duration(self):
        return float(sum(p.duration for p in self.pieces))

    def fingerprint(self):
        h=hashlib.sha256()
        for p in self.pieces:
            h.update(np.asarray(p.controls,dtype=np.float64).tobytes())
            h.update(repr((p.duration,p.phase)).encode())
        h.update(np.asarray([self.body_origin,self.body_velocity],dtype=np.float64).tobytes())
        h.update(repr((self.limits,self.model,self.geometry_bound_m,self.path_digest)).encode())
        return h.hexdigest()

    def sample(self, dt=0.002):
        if not np.isfinite(dt) or dt <= 0:
            raise ValueError("sample interval must be positive")
        ts, ps, vs, accs, jerks, phases = [], [], [], [], [], []
        start = 0.0
        for k, piece in enumerate(self.pieces):
            n = max(2, int(math.ceil(piece.duration / dt))+1)
            u = np.linspace(0, 1, n)
            # Each boundary has one sample, belonging to the following phase.
            if k != len(self.pieces)-1:
                u = u[:-1]
            ts.extend(start+u*piece.duration)
            ps.extend(_evaluate(piece.controls,u))
            vs.extend(_evaluate(_derivative(piece.controls,piece.duration),u))
            accs.extend(_evaluate(_derivative(piece.controls,piece.duration,2),u))
            jerks.extend(_evaluate(_derivative(piece.controls,piece.duration,3),u))
            phases.extend([piece.phase]*len(u))
            start += piece.duration
        t = np.array(ts)
        xy = np.asarray(ps)
        q = (xy-self.body_origin-t[:,None]*self.body_velocity) @ self.limits.page_to_stage.T
        qdot=(np.asarray(vs)-self.body_velocity)@self.limits.page_to_stage.T
        qddot=np.asarray(accs)@self.limits.page_to_stage.T
        qjerk=np.asarray(jerks)@self.limits.page_to_stage.T
        force=self.model.mass_kg*qddot+self.model.damping_N_s_m*qdot+self.model.stiffness_N_m*q+self.model.bias_force_N
        return {"t":t,"xy":xy,"down":np.array([x == "ink" for x in phases]),"phase":np.array(phases),"q":q,
                "q_velocity_m_s":qdot,"q_acceleration_m_s2":qddot,"q_jerk_m_s3":qjerk,"nominal_force_N":force}

    def point(self, t: float):
        """Exact polynomial command; time is local to this letter."""
        if not np.isfinite(t) or not 0 <= t <= self.duration + 1e-10:
            raise ValueError("time is outside admitted letter")
        start = 0.0
        for p in self.pieces:
            if t < start+p.duration or p is self.pieces[-1]:
                u = np.array([min(1.,max(0.,(t-start)/p.duration))])
                return _evaluate(p.controls,u)[0], p.phase
            start += p.duration
        raise AssertionError("unreachable")

    def derivatives(self,t:float):
        """Analytic page velocity/acceleration of the explicitly accepted path."""
        if not np.isfinite(t) or not 0<=t<=self.duration+1e-10:
            raise ValueError("time is outside admitted letter")
        start=0.
        for p in self.pieces:
            if t<start+p.duration or p is self.pieces[-1]:
                u=np.array([min(1.,max(0.,(t-start)/p.duration))])
                return (_evaluate(_derivative(p.controls,p.duration),u)[0],
                        _evaluate(_derivative(p.controls,p.duration,2),u)[0])
            start+=p.duration
        raise AssertionError("unreachable")


def _path_digest(strokes):
    h = hashlib.sha256()
    for s in strokes:
        a = np.asarray(s,dtype=np.float64)
        h.update(str(a.shape).encode())
        h.update(a.tobytes())
    return h.hexdigest()


def stopping_distance(speed, acceleration, brake_acceleration, jerk, reaction_delay):
    """Conservative collinear, jerk-limited stop ending at zero acceleration.

    During the reaction delay assume the maximum positive acceleration. Then
    ramp to a negative acceleration, hold if needed, and ramp back to zero.
    The initial acceleration is its positive norm bound, so this is a sufficient
    scalar travel allowance for a path-following emergency stop, conditional on
    the servo supplying the stated acceleration and jerk. It is not a proof for
    an arbitrary uncontrolled plant or a rotating body frame.
    """
    v,a=np.broadcast_arrays(np.asarray(speed,float),np.asarray(acceleration,float))
    if np.any(v<0) or np.any(a<0) or brake_acceleration<=0 or jerk<=0 or reaction_delay<0:
        raise ValueError("invalid stop bounds")
    d=v*reaction_delay+.5*a*reaction_delay**2
    v=v+a*reaction_delay
    # The triangular S-curve needs peak deceleration sqrt(J*v + a²/2).
    b=np.minimum(brake_acceleration,np.sqrt(jerk*v+.5*a*a))
    t1=(a+b)/jerk
    d+=v*t1+.5*a*t1*t1-jerk*t1**3/6
    v1=v+a*t1-.5*jerk*t1*t1
    t2=np.maximum(0.,(v1-b*b/(2*jerk))/np.maximum(b,1e-30))
    d+=v1*t2-.5*b*t2*t2
    v2=v1-b*t2
    t3=b/jerk
    d+=v2*t3-.5*b*t3*t3+jerk*t3**3/6
    return d


def _stroke_curve(points,step_m=0.12e-3):
    """Return normalized-time quintic Bezier pieces and certified deviation.

    The bound compares the spline with the original polyline at the same
    normalized arc length. It is consequently also an upper bound on both
    directed Hausdorff distances. No target letter classifier is used here.
    """
    p = np.asarray(points,float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 1 or not np.isfinite(p).all():
        raise ValueError("finite N by 2 stroke points are required")
    keep = np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-12]
    p=p[keep]
    if len(p)==1:
        return [(np.repeat(p,6,axis=0),1.0)],0.,0.
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    length=float(s[-1]); s/=length
    # Uniform arc-length knots reduce sensitivity to repeated densely spaced digitizer samples.
    n=max(2,int(math.ceil(length/step_m))+1)
    u=np.linspace(0,1,n)
    pts=np.column_stack([np.interp(u,s,p[:,axis]) for axis in range(2)])
    zero=np.zeros(2)
    # Place arc-length samples on a minimum-jerk clock. For a straight line this
    # recovers the exact minimum-jerk polynomial, avoiding a tiny, high-jerk
    # acceleration ramp in only the first digitizer interval.
    clock=np.polynomial.Polynomial([0.,0.,0.,10.,-15.,6.])
    def inverse_clock(s):
        low=np.zeros_like(s);high=np.ones_like(s)
        for _ in range(55):
            mid=(low+high)/2
            left=clock(mid)<s
            low=np.where(left,mid,low);high=np.where(left,high,mid)
        out=(low+high)/2
        return np.where(s==0,0.,np.where(s==1,1.,out))
    clock_knots=inverse_clock(u)
    spline=make_interp_spline(clock_knots,pts,k=5,bc_type=([(1,zero),(2,zero)],[(1,zero),(2,zero)]))
    # Include original polyline knots: each comparison subinterval is linear there.
    knots=np.unique(np.r_[inverse_clock(s),spline.t[(spline.t>=0)&(spline.t<=1)]])
    pieces=[]; error=0.
    for lo,hi in zip(knots[:-1],knots[1:]):
        if hi-lo<1e-12:
            continue
        powers=np.array([spline(lo,nu=k)*(hi-lo)**k/math.factorial(k) for k in range(6)])
        controls=np.array([sum(powers[k]*math.comb(i,k)/math.comb(5,k) for k in range(i+1)) for i in range(6)])
        j=min(len(s)-2,max(0,np.searchsorted(s,clock((lo+hi)/2),side="right")-1))
        delta=(p[j+1]-p[j])/(s[j+1]-s[j])
        refpowers=np.array([delta*clock.deriv(k)(lo)*(hi-lo)**k/math.factorial(k) for k in range(6)])
        refpowers[0]+=p[j]-delta*s[j]
        reference=np.array([sum(refpowers[k]*math.comb(i,k)/math.comb(5,k) for k in range(i+1)) for i in range(6)])
        error=max(error,float(np.max(np.linalg.norm(controls-reference,axis=1))))
        pieces.append((controls,float(hi-lo)))
    return pieces,error,length


def certify(trajectory: LetterTrajectory) -> dict:
    """Sufficient bounds, valid over every polynomial interval (not sample-only).

    Unknown hand acceleration/velocity are included in available actuation. A
    bounded normal force and the simplified linear actuator model do not prove
    successful ink deposition, stable contact, flexible-mode stability or comfort.
    """
    lim=trajectory.limits; model=trajectory.model; M=lim.page_to_stage
    kf=np.array(model.force_constant_N_A)
    gauss_x,gauss_w=np.polynomial.legendre.leggauss(6)
    dt=np.array([p.duration for p in trajectory.pieces])
    if not len(dt) or not np.isfinite(dt).all() or np.any(dt<=0):
        raise ValueError("every phase must have positive duration")
    start=np.r_[0.,np.cumsum(dt[:-1])];end=start+dt
    time=start[:,None]+dt[:,None]*np.linspace(0,1,6)
    body=trajectory.body_origin+time[:,:,None]*trajectory.body_velocity
    q=(np.array([p.controls for p in trajectory.pieces])-body)@M.T
    vel=5*np.diff(q,axis=1)/dt[:,None,None]
    acc=4*np.diff(vel,axis=1)/dt[:,None,None]
    jerk=3*np.diff(acc,axis=1)/dt[:,None,None]
    qmax=np.linalg.norm(q,axis=2).max(1)
    vmax=np.linalg.norm(vel,axis=2).max(1)+lim.velocity_error_m_s+lim.acceleration_error_m_s2*end
    amax=np.linalg.norm(acc,axis=2).max(1)+lim.acceleration_error_m_s2
    jmax=np.linalg.norm(jerk,axis=2).max(1)+lim.jerk_error_m_s3
    # Include positive initial acceleration, reaction delay and both jerk ramps.
    # Lift is independent: a stop does not erase ink made during lift latency.
    brake_reserve=stopping_distance(vmax,amax,lim.brake_acceleration_m_s2,
                                   lim.jerk_m_s3,lim.reaction_delay_s)
    reserve=lim.tracking_reserve_m+lim.prediction_error(end)+brake_reserve
    force=model.mass_kg*_elevate_batch(acc,5)+model.damping_N_s_m*_elevate_batch(vel,5)+model.stiffness_N_m*q+model.bias_force_N
    current=force/kf
    force_error=(model.load_uncertainty_N+model.mass_kg*lim.acceleration_error_m_s2+
                 model.damping_N_s_m*(lim.velocity_error_m_s+lim.acceleration_error_m_s2*end)+
                 model.stiffness_N_m*lim.prediction_error(end))
    current_bound=np.abs(current)+force_error[:,None,None]/kf
    di=5*np.diff(current,axis=1)/dt[:,None,None]
    voltage=model.resistance_ohm*current+model.inductance_H*_elevate_batch(di,5)+kf*_elevate_batch(vel,5)
    force_slew_error=(model.load_slew_uncertainty_N_s+model.mass_kg*lim.jerk_error_m_s3+
                      model.damping_N_s_m*lim.acceleration_error_m_s2+
                      model.stiffness_N_m*(lim.velocity_error_m_s+lim.acceleration_error_m_s2*end))
    voltage_bound=(np.abs(voltage)+
                   (model.resistance_ohm*force_error+model.inductance_H*force_slew_error)[:,None,None]/kf+
                   (lim.velocity_error_m_s+lim.acceleration_error_m_s2*end)[:,None,None]*kf)
    stop_peak_v=vmax+amax*lim.reaction_delay_s+amax**2/(2*lim.jerk_m_s3)
    stop_peak_a=np.maximum(amax,lim.brake_acceleration_m_s2)
    # Sufficient vector-norm force/current bounds for the assumed linear stage.
    stop_force=(model.mass_kg*stop_peak_a+model.damping_N_s_m*stop_peak_v+
                model.stiffness_N_m*lim.hard_stop_m+np.linalg.norm(model.bias_force_N)+model.load_uncertainty_N)
    stop_current=stop_force/kf.min()
    stop_slew=(model.mass_kg*lim.jerk_m_s3+model.damping_N_s_m*stop_peak_a+
               model.stiffness_N_m*stop_peak_v+model.load_slew_uncertainty_N_s)/kf.min()
    stop_voltage=model.resistance_ohm*stop_current+model.inductance_H*stop_slew+kf.max()*stop_peak_v
    gu=(gauss_x+1)/2
    weights=np.column_stack([math.comb(5,k)*gu**k*(1-gu)**(5-k) for k in range(6)])
    it=np.einsum("kp,npa->nka",weights,current)
    energy=dt/2*np.einsum("k,nk->n",gauss_w,model.resistance_ohm*(it*it).sum(2))
    bound={"radial_m":float(qmax.max()),"radial_with_reserve_m":float((qmax+reserve).max()),
           "speed_m_s":float(vmax.max()),"acceleration_m_s2":float(amax.max()),"jerk_m_s3":float(jmax.max()),
           "current_A":float(current_bound.max()),"voltage_V":float(voltage_bound.max()),"coil_energy_J":float(energy.sum())}
    bound.update({"braking_reserve_m":float(brake_reserve.max()),"braking_current_A":float(stop_current.max()),
                  "braking_voltage_V":float(stop_voltage.max())})
    thresholds={"radial_with_reserve_m":lim.radius_m,"speed_m_s":lim.speed_m_s,
                "acceleration_m_s2":lim.acceleration_m_s2,"jerk_m_s3":lim.jerk_m_s3,
                "current_A":model.current_limit_A,"voltage_V":model.voltage_limit_V,
                "braking_current_A":model.current_limit_A,"braking_voltage_V":model.voltage_limit_V}
    failures=[key for key,value in thresholds.items() if bound[key]>value*(1+1e-10)]
    if trajectory.geometry_bound_m>lim.geometry_error_m:
        failures.append("geometry_error_m")
    bound.update({"geometry_error_m":trajectory.geometry_bound_m,"duration_s":float(end[-1]),
                  "passed":not failures,"failures":failures,"thresholds":thresholds,
                  "scope":"CALC: reference within assumed motion/load/slew envelope; no plant or ink validation"})
    return bound


def plan_letter(strokes:Sequence[np.ndarray], body_origin, body_velocity=(0.,0.), *,
                limits:MotionLimits=MotionLimits(), model:StageModel=StageModel(),
                duration_scales:Optional[Sequence[float]]=None):
    """Retiming search using only current body position/velocity and bounded errors.

    Returns (trajectory or None, diagnostic). A failed letter is not shortened,
    rescaled or partly drawn. A user may reposition the body while pen-up, then
    re-admit the same accepted geometry. No software command moves that body.
    """
    b=np.asarray(body_origin,float); v=np.asarray(body_velocity,float)
    if b.shape!=(2,) or v.shape!=(2,) or not np.isfinite([b,v]).all() or not strokes:
        raise ValueError("finite two-dimensional body state and strokes are required")
    # Prefer a smooth, compact representation but never assume smoothing kept
    # the accepted shape. Refine knots until the exact convex-hull comparison
    # with the original path proves the requested geometric tolerance.
    curves=[]
    for points in strokes:
        for step in (0.60e-3,0.40e-3,0.24e-3,0.12e-3,0.06e-3,0.03e-3):
            curve=_stroke_curve(points,step)
            if curve[1]<=limits.geometry_error_m:
                break
        curves.append(curve)
    geometry=max(c[1] for c in curves)
    if geometry>limits.geometry_error_m:
        return None,{"reason":"geometry_tolerance","geometry_bound_m":geometry}
    # The geometry error is bounded separately; longer times cannot fix it.
    scales=np.asarray(duration_scales if duration_scales is not None else np.geomspace(.75,12.,55),float)
    if scales.ndim!=1 or not len(scales) or not np.isfinite(scales).all() or np.any(scales<=0):
        raise ValueError("duration scales must be finite and positive")
    diagnostics=[]
    for scale in sorted(scales):
        pieces=[]
        for i,(curve,_,length) in enumerate(curves):
            start=curve[0][0][0]
            if i:
                prev=curves[i-1][0][-1][0][-1]
                dist=np.linalg.norm(start-prev)
                if dist>1e-12:
                    controls=np.vstack([np.tile(prev,(3,1)),np.tile(start,(3,1))])
                    pieces.append(Piece(controls,max(.010,dist/.020)*scale,"air"))
            pieces.append(Piece(np.repeat(start[None,:],6,axis=0),max(limits.lower_delay_s+limits.reaction_delay_s,1e-6),"lower"))
            total=max(.025,length/.030)*scale
            for controls,fraction in curve:
                pieces.append(Piece(controls,total*fraction,"ink"))
            end=curve[-1][0][-1]
            pieces.append(Piece(np.repeat(end[None,:],6,axis=0),max(limits.lift_delay_s+limits.reaction_delay_s,1e-6),"lift"))
        trajectory=LetterTrajectory(pieces,b.copy(),v.copy(),limits,model,geometry,path_digest=_path_digest(strokes))
        trajectory.bounds=certify(trajectory)
        diagnostics.append({"scale":float(scale),"duration_s":trajectory.duration,"failures":trajectory.bounds["failures"]})
        if trajectory.bounds["passed"]:
            trajectory.certificate_digest=trajectory.fingerprint()
            return trajectory,{"reason":"admitted","trials":diagnostics}
    return None,{"reason":"no_feasible_duration","trials":diagnostics,"last_bounds":trajectory.bounds}


def admit_accepted_letter(plan:WritingPlan, letter_index:int, body_origin, body_velocity=(0.,0.), **kwargs):
    """Only future strokes of the accepted text can enter the execution interface."""
    if plan.state not in ("planned","writing") or not 0<=letter_index<len(plan.letters):
        raise LayerError("plan is unavailable")
    letter=plan.letters[letter_index]
    if letter.state!="queued" or any(L.state!="done" for L in plan.letters[:letter_index]):
        raise LayerError("letters must be admitted in accepted order")
    trajectory,diag=plan_letter(letter.strokes,body_origin,body_velocity,**kwargs)
    if trajectory is not None:
        trajectory.accepted_plan_id=plan.plan_id
        trajectory.letter_index=letter_index
    return trajectory,diag


@dataclass(frozen=True)
class Observation:
    t:float
    body_xy:tuple
    tip_xy:tuple
    force_N:float
    sensor_age_s:float
    page_epoch:Optional[str]           # None means there is no valid absolute page reference
    reference_valid:bool=True
    current_A:float=0.                # max(abs(I_x), abs(I_y)), not the signed mean
    temperature_C:float=25.
    attitude_deg:Optional[tuple]=None # measured (tilt above page, roll, tilt-plane azimuth)


class CompletionExecutor:
    """Reference/contact supervisor. A motor interface must implement lift/brake.

    Outputs a page reference while observations remain inside the admitted tube.
    It never teleports to a future waypoint or retroactively changes deposited ink.
    On abort it requests independent lift and controlled braking, not zero stage
    position. Firmware must honour that request within the configured delay.
    """
    def __init__(self,plan:WritingPlan,trajectory:LetterTrajectory,first:Observation):
        if trajectory.accepted_plan_id!=plan.plan_id or trajectory.letter_index is None:
            raise LayerError("trajectory is not bound to this accepted plan")
        if trajectory.path_digest!=_path_digest(plan.letters[trajectory.letter_index].strokes):
            raise LayerError("accepted geometry changed")
        if not trajectory.bounds.get("passed"):
            raise LayerError("an infeasible trajectory cannot execute")
        if trajectory.certificate_digest!=trajectory.fingerprint():
            raise LayerError("certified trajectory changed; re-admit it")
        self.plan=plan; self.trajectory=copy.deepcopy(trajectory); self.start=first.t; self.last=first.t
        self.epoch=first.page_epoch; self.state="armed"; self.reason=""
        self._last_phase="lower"
        # An admitted start is still conditional on fresh sensing and current position.
        fault=self._fault(first,0.,check_tracking=False)
        start_point=trajectory.pieces[0].controls[0]
        if fault or np.linalg.norm(np.asarray(first.tip_xy)-start_point)>trajectory.limits.tracking_reserve_m:
            raise LayerError(f"cannot arm: {fault or 'move to accepted stroke start while pen-up'}")
        plan.start_letter(trajectory.letter_index)

    def _fault(self,obs,elapsed,check_tracking=True):
        fields=[obs.t,obs.force_N,obs.sensor_age_s,obs.current_A,obs.temperature_C,*obs.body_xy,*obs.tip_xy]
        if len(obs.body_xy)!=2 or len(obs.tip_xy)!=2 or not np.isfinite(fields).all():
            return "invalid_observation"
        lim=self.trajectory.limits
        # This certificate is for a constant, known frame. Numerical equality
        # is not an IMU accuracy claim: a hardware implementation must certify
        # orientation uncertainty or constrain the pose mechanically.
        if obs.attitude_deg is None or len(obs.attitude_deg)!=3 or not np.isfinite(obs.attitude_deg).all():
            return "attitude_unavailable"
        if np.max(abs(np.asarray(obs.attitude_deg)-[lim.tilt_deg,0.,0.]))>1e-6:
            return "attitude_changed"
        if not obs.reference_valid or obs.page_epoch is None or obs.page_epoch!=self.epoch:
            return "page_reference_lost"
        if obs.sensor_age_s<0 or obs.sensor_age_s>lim.max_sensor_age_s:
            return "stale_sensor"
        if obs.t<self.last:
            return "clock_reversed"
        if elapsed>0 and obs.t-self.last>lim.reaction_delay_s+1e-9:
            return "control_deadline_missed"
        if abs(obs.current_A)>self.trajectory.model.current_limit_A or obs.temperature_C>lim.max_temperature_C:
            return "actuator_limit"
        if not 0<=obs.force_N<=lim.max_contact_N:
            return "contact_force_limit"
        predicted=self.trajectory.body_origin+elapsed*self.trajectory.body_velocity
        if np.linalg.norm(np.asarray(obs.body_xy)-predicted)>lim.prediction_error(elapsed)+1e-10:
            return "body_prediction_exceeded"
        actual_q=lim.page_to_stage@(np.asarray(obs.tip_xy)-np.asarray(obs.body_xy))
        if np.linalg.norm(actual_q)>lim.radius_m:
            return "workspace_exceeded"
        if check_tracking:
            target,phase=self.trajectory.point(min(elapsed,self.trajectory.duration))
            if np.linalg.norm(lim.page_to_stage@(np.asarray(obs.tip_xy)-target))>lim.tracking_reserve_m:
                return "tracking_error"
            if phase=="ink" and obs.force_N<lim.min_contact_N:
                return "contact_lost"
            if phase=="air" and obs.force_N>=lim.min_contact_N:
                return "lift_not_confirmed"
        return None

    def tick(self,obs:Observation):
        if self.state in ("aborted","done"):
            return {"state":self.state,"request_lift":True,"request_brake":True,"reason":self.reason}
        elapsed=obs.t-self.start
        if self.plan.state in ("cancelled","handed_back"):
            fault="writer_cancelled"
        else:
            fault=self._fault(obs,elapsed)
        if fault:
            self.state="aborted";self.reason=fault
            if self.plan.state not in ("cancelled","handed_back"):
                self.plan.hand_back(fault)
            return {"state":"aborted","request_lift":True,"request_brake":True,"reason":fault}
        self.last=obs.t
        if elapsed>=self.trajectory.duration:
            if obs.force_N>=self.trajectory.limits.min_contact_N:
                self.state="aborted";self.reason="lift_not_confirmed"
                self.plan.hand_back(self.reason)
                return {"state":"aborted","request_lift":True,"request_brake":True,"reason":self.reason}
            self.plan.finish_letter(self.trajectory.letter_index)
            self.state="done"
            return {"state":"done","request_lift":True,"request_brake":False,"reason":"letter_finished"}
        target,phase=self.trajectory.point(elapsed)
        velocity,acceleration=self.trajectory.derivatives(elapsed)
        self.state="executing";self._last_phase=phase
        return {"state":"executing","page_target_m":target.tolist(),
                "stage_velocity_m_s":(self.trajectory.limits.page_to_stage@(velocity-self.trajectory.body_velocity)).tolist(),
                "stage_acceleration_m_s2":(self.trajectory.limits.page_to_stage@acceleration).tolist(),
                "plan_id":self.plan.plan_id,"letter_index":self.trajectory.letter_index,
                "request_lift":phase in ("lift","air"),"request_brake":False,
                "phase":phase,"may_deposit_ink":phase=="ink"}
