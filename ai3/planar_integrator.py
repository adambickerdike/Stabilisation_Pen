"""Passive implicit-midpoint integration for the generic planar pen plant.

The controller still runs on its original clock. Only the continuous R-L,
spring/mass/damper and radial smooth-Coulomb friction equations are substepped.
Electrical back-EMF and mechanical force use the same midpoint current and
velocity, so their exchanged power cancels. With zero voltage/bias, no current
clipping and nonnegative damping/drag, midpoint discrete stored energy cannot
increase. This numerical property does not validate the physical friction law.

Binary contact can switch force discontinuously. A finite sampled jerk at that
event is resolution dependent; the return value separately exposes acceleration
jump and smooth-within-contact jerk. The 0.5 ms replay clock must not hide a
smaller internal acceleration peak.
"""
from __future__ import annotations

import math
import numpy as np
from numba import njit


@njit(cache=True)
def _acceleration(q,v,current,kf,mass,spring,damping,bias,drag,velocity_scale):
    speed=math.sqrt(v[0]*v[0]+v[1]*v[1])
    drag_gain=drag*math.tanh(speed/velocity_scale)/speed if speed>1e-20 else drag/velocity_scale
    return (kf*current-spring*q-bias-(damping+drag_gain)*v)/mass


@njit(cache=True)
def _integrate(q0,v0,i0,voltage,kf,mass,spring,damping,bias,resistance,inductance,
               current_limit,voltage_limit,drag,velocity_scale,dt,max_step):
    count=max(1,int(math.ceil(dt/max_step-1e-12)));h=dt/count
    q=q0.copy();v=v0.copy();current=i0.copy();mean_i=np.zeros(2)
    half=h/(2*inductance);denom=1+resistance*half
    base_coefficient=2*mass/h+damping+h*spring/2
    coefficient=base_coefficient+half*kf*kf/denom
    first_acc=_acceleration(q,v,current,kf,mass,spring,damping,bias,drag,velocity_scale)
    prev_acc=first_acc.copy();peak_a=np.sqrt(np.sum(first_acc*first_acc));peak_j=0.
    peak_i=np.max(np.abs(current));clipped=0
    max_residual=0.;copper_energy=0.;source_energy=0.;peak_effective_voltage=0.
    for _ in range(count):
        electrical_base=(current+half*voltage)/denom
        rhs_base=2*mass*v/h-spring*q-bias
        rhs=rhs_base+kf*electrical_base
        vm=rhs/(coefficient+drag/velocity_scale)
        # The positive diagonal inertial term plus monotone radial drag is
        # strongly monotone. Substeps keep this solve far from ill-conditioning.
        for _newton in range(16):
            speed=math.sqrt(vm[0]*vm[0]+vm[1]*vm[1])
            if speed<1e-14:
                gain=drag/velocity_scale;cross=0.
            else:
                tanh=math.tanh(speed/velocity_scale)
                gain=drag*tanh/speed
                cross=drag*((1-tanh*tanh)/velocity_scale-tanh/speed)/(speed*speed)
            unconstrained_i=2*(electrical_base-half*kf*vm/denom)-current
            limited_i=np.minimum(current_limit,np.maximum(-current_limit,unconstrained_i))
            im=(current+limited_i)/2
            residual=(base_coefficient+gain)*vm-rhs_base-kf*im
            active=np.abs(unconstrained_i)>current_limit
            electrical_jacobian=half*kf*kf/denom*(1.-active.astype(np.float64))
            norm=math.sqrt(np.sum(residual*residual))
            if norm<1e-13:break
            j00=base_coefficient+electrical_jacobian[0]+gain+cross*vm[0]*vm[0]
            j11=base_coefficient+electrical_jacobian[1]+gain+cross*vm[1]*vm[1]
            j01=cross*vm[0]*vm[1]
            determinant=j00*j11-j01*j01
            delta=np.array([(j11*residual[0]-j01*residual[1])/determinant,
                            (j00*residual[1]-j01*residual[0])/determinant])
            # Damping is defensive for extreme inputs outside the replay range.
            rate=1.
            for _line in range(20):
                candidate=vm-rate*delta
                size=math.sqrt(np.sum(candidate*candidate))
                g=drag*math.tanh(size/velocity_scale)/size if size>1e-20 else drag/velocity_scale
                proposed_i=2*(electrical_base-half*kf*candidate/denom)-current
                limited=np.minimum(current_limit,np.maximum(-current_limit,proposed_i))
                rr=(base_coefficient+g)*candidate-rhs_base-kf*(current+limited)/2
                if np.sum(rr*rr)<=norm*norm:break
                rate*=.5
            vm=candidate
        size=math.sqrt(np.sum(vm*vm))
        g=drag*math.tanh(size/velocity_scale)/size if size>1e-20 else drag/velocity_scale
        unconstrained_i=2*(electrical_base-half*kf*vm/denom)-current
        new_i=np.minimum(current_limit,np.maximum(-current_limit,unconstrained_i))
        im=(current+new_i)/2
        residual=(base_coefficient+g)*vm-rhs_base-kf*im
        max_residual=max(max_residual,math.sqrt(np.sum(residual*residual)))
        effective_voltage=resistance*im+inductance*(new_i-current)/h+kf*vm
        peak_effective_voltage=max(peak_effective_voltage,np.max(np.abs(effective_voltage)))
        if peak_effective_voltage>voltage_limit*(1+1e-10):
            raise ValueError("ideal current limiter requires voltage outside the supply rails")
        clipped+=np.sum(np.abs(unconstrained_i)>current_limit)
        copper_energy+=resistance*np.sum(im*im)*h
        source_energy+=np.sum(effective_voltage*im)*h
        q=q+h*vm;v=2*vm-v
        # Active axes are re-solved with limited midpoint current. The recovered
        # effective voltage must fit supply rails: no imaginary regenerative rail.
        mean_i+=im/count;current=new_i
        acc=_acceleration(q,v,current,kf,mass,spring,damping,bias,drag,velocity_scale)
        peak_a=max(peak_a,math.sqrt(np.sum(acc*acc)))
        peak_j=max(peak_j,math.sqrt(np.sum((acc-prev_acc)**2))/h)
        peak_i=max(peak_i,np.max(np.abs(current)));prev_acc=acc
    return q,v,current,mean_i,first_acc,prev_acc,peak_a,peak_j,peak_i,clipped,max_residual,count,copper_energy,source_energy,peak_effective_voltage


def step(q,velocity,current,voltage, *,force_constant_N_A,mass_kg,stiffness_N_m,
         damping_N_s_m,bias_force_N,resistance_ohm,inductance_H,current_limit_A,
         drag_N=0.,velocity_scale_m_s=.0005,dt_s=.0005,max_step_s=.00005,voltage_limit_V=3.):
    """Advance one policy tick; return endpoints and internal physical metrics.

    `voltage` and contact are held over this tick. No target, controller state,
    noise, seed, or true external parameter is exposed to the controller here.
    The force constants are *plant* parameters, including test perturbations.
    """
    vectors=[np.asarray(x,dtype=float) for x in (q,velocity,current,voltage,force_constant_N_A,bias_force_N)]
    if any(v.shape!=(2,) or not np.isfinite(v).all() for v in vectors):
        raise ValueError("finite two-axis states and plant parameters required")
    scalars=[mass_kg,resistance_ohm,inductance_H,current_limit_A,velocity_scale_m_s,dt_s,max_step_s,voltage_limit_V]
    if not np.isfinite(scalars).all() or min(scalars)<=0 or not np.isfinite([stiffness_N_m,damping_N_s_m,drag_N]).all() or min(stiffness_N_m,damping_N_s_m,drag_N)<0:
        raise ValueError("positive electrical/inertial/clock parameters and nonnegative dissipation required")
    result=_integrate(*vectors[:4],vectors[4],mass_kg,stiffness_N_m,damping_N_s_m,vectors[5],
        resistance_ohm,inductance_H,current_limit_A,voltage_limit_V,drag_N,velocity_scale_m_s,dt_s,max_step_s)
    if result[10]>1e-10:raise RuntimeError("implicit mechanics solve did not converge")
    return result
