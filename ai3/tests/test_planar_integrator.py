"""Independent dissipativity, analytic friction and coupled linear checks."""
import numpy as np
import pytest
from scipy.linalg import expm

from ai3.planar_integrator import step


def evolve(*,dt=.0005,internal=.00005,duration=.002,v0=(1e-6,0),q0=(0,0),i0=(0,0),
           force=.020,mass=.00344,kf=(0,0),spring=0.,damping=0.,voltage=(0,0)):
    q=np.array(q0,dtype=float);v=np.array(v0,dtype=float);i=np.array(i0,dtype=float)
    history=[np.r_[q,v,i]]
    for _ in range(round(duration/dt)):
        result=step(q,v,i,np.array(voltage),force_constant_N_A=kf,mass_kg=mass,
            stiffness_N_m=spring,damping_N_s_m=damping,bias_force_N=(0,0),
            resistance_ohm=3.03,inductance_H=.001,current_limit_A=10.,
            drag_N=force,dt_s=dt,max_step_s=internal)
        q,v,i=result[:3];history.append(np.r_[q,v,i])
    return np.asarray(history)


@pytest.mark.parametrize("v0",[(1e-6,0.),(.001,-.002),(.02,.01)])
def test_analytic_radial_decay_is_dissipative_and_preserves_direction(v0):
    v=np.asarray(v0);speed=np.linalg.norm(v);m=.00344;force=.020;vs=.0005
    a=evolve(v0=v0,duration=.01,internal=5e-6)
    t=np.arange(len(a))*.0005
    exact=vs*np.arcsinh(np.sinh(speed/vs)*np.exp(-force*t/(m*vs)))
    observed=np.linalg.norm(a[:,2:4],axis=1)
    assert np.all(np.diff(observed**2)<=1e-22)
    np.testing.assert_allclose(observed,exact,atol=3e-8,rtol=.003)
    assert np.max(abs(a[:,2]*v[1]-a[:,3]*v[0]))<1e-17


def test_friction_refinement_converges_to_independent_exact_solution():
    m=.00344;force=.020;vs=.0005;v0=.001;t=.002
    exact=vs*np.arcsinh(np.sinh(v0/vs)*np.exp(-force*t/(m*vs)))
    errors=[]
    for internal in (50e-6,25e-6,12.5e-6):
        a=evolve(v0=(v0,0),duration=t,internal=internal)
        errors.append(abs(a[-1,2]-exact))
    assert errors[1]<errors[0]/3 and errors[2]<errors[1]/3


def test_coupled_electrical_mechanical_energy_cannot_be_created():
    m=.002408;k=2.;L=.001
    a=evolve(v0=(.001,.002),q0=(.0004,-.0002),i0=(.06,-.04),
        kf=(.45,.30),force=.025,mass=m,spring=k,damping=.08,duration=.03)
    energy=.5*(k*np.sum(a[:,:2]**2,axis=1)+m*np.sum(a[:,2:4]**2,axis=1)+L*np.sum(a[:,4:]**2,axis=1))
    assert np.all(np.diff(energy)<=1e-17)


def test_no_drag_forced_coupled_plant_matches_matrix_exponential():
    m=.00344;k=1.56;c=.08;L=.001;R=3.03;kf=.45;V=.2;duration=.01
    a=evolve(v0=(.001,0),q0=(.0001,0),i0=(.03,0),kf=(kf,kf),force=0,
        mass=m,spring=k,damping=c,duration=duration,voltage=(V,0),internal=25e-6)
    A=np.array([[0,1,0,0],[-k/m,-c/m,kf/m,0],[0,-kf/L,-R/L,V/L],[0,0,0,0]])
    exact=(expm(A*duration)@np.array([.0001,.001,.03,1.]))[:3]
    np.testing.assert_allclose(a[-1,[0,2,4]],exact,rtol=5e-5,atol=1e-9)


def test_nonphysical_parameters_rejected():
    with pytest.raises(ValueError):
        evolve(internal=0.)


def test_active_current_limit_uses_same_midpoint_force_and_measured_current():
    q=np.zeros(2);v=np.zeros(2);current=np.array([.099,-.099]);m=.00344;L=.001
    result=step(q,v,current,[3.,-3.],force_constant_N_A=[.5,.4],mass_kg=m,
        stiffness_N_m=0.,damping_N_s_m=0.,bias_force_N=[0.,0.],resistance_ohm=3.,
        inductance_H=L,current_limit_A=.1,dt_s=50e-6,max_step_s=50e-6)
    q1,v1,i1,mean_i=result[:4]
    assert result[9]>0 and max(abs(i1))<=.1
    np.testing.assert_allclose(m*(v1-v),np.array([.5,.4])*mean_i*50e-6,rtol=1e-11,atol=1e-15)
    energy0=.5*L*np.sum(current**2)
    energy1=.5*m*np.sum(v1*v1)+.5*L*np.sum(i1*i1)
    assert energy1-energy0==pytest.approx(result[13]-result[12],abs=1e-17)
    assert result[14]<=3.


def test_current_clamp_cannot_invent_regenerative_voltage():
    with pytest.raises(ValueError,match="supply rails"):
        step([0,0],[100.,0],[.1,0],[0,0],force_constant_N_A=[.5,.4],mass_kg=.00344,
            stiffness_N_m=0.,damping_N_s_m=0.,bias_force_N=[0,0],resistance_ohm=3.,
            inductance_H=.001,current_limit_A=.1,dt_s=.0005,max_step_s=.00005)
