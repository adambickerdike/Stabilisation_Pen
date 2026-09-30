"""Independent geometry and energy checks for the grounded alternative."""
import numpy as np
import pytest
from wholepen.grounded import FiveBar


def forward(theta, g):
    e=np.array([[-g.base/2,0],[g.base/2,0]])+g.proximal*np.column_stack([np.cos(theta),np.sin(theta)])
    d=e[1]-e[0]; l=np.linalg.norm(d); mid=e.mean(axis=0)
    perp=np.array([-d[1],d[0]])/l
    h=np.sqrt(g.distal**2-l*l/4)
    solutions=np.array([mid+h*perp,mid-h*perp])
    return solutions[np.argmax(solutions[:,1])]


@pytest.mark.parametrize('xy',[[0,.09],[.03,.07],[-.03,.11]])
def test_closure_derivative_virtual_work(xy):
    g=FiveBar(); k=g.kinematics(xy)
    assert np.linalg.norm(k['distal_vectors'],axis=1)==pytest.approx([g.distal]*2)
    assert forward(k['angles'],g)==pytest.approx(xy)
    h=1e-6
    J=np.column_stack([(forward(k['angles']+np.eye(2)[i]*h,g)-forward(k['angles']-np.eye(2)[i]*h,g))/(2*h) for i in range(2)])
    assert J==pytest.approx(k['J'],rel=1e-8,abs=1e-10)
    f=np.array([.2,-.1]); qdot=np.array([.3,-.4])
    assert f@(J@qdot)==pytest.approx((J.T@f)@qdot)


def test_energy_mass_and_coriolis():
    g=FiveBar(); p=np.array([.012,.086]); v=np.array([.023,-.012])
    M=g.mass_matrix(p)
    assert np.linalg.eigvalsh(M).min()>g.payload_mass
    # dT/dt under constant Cartesian velocity equals v.C.
    h=1e-5
    rate=(.5*v@g.mass_matrix(p+h*v)@v-.5*v@g.mass_matrix(p-h*v)@v)/(2*h)
    assert v@g.coriolis(p,v)==pytest.approx(rate,rel=2e-7,abs=1e-12)
    assert np.trace(g.mass_matrix(p))>np.trace(g.mass_matrix(p,False))


def test_force_disk_obeys_all_directions():
    g=FiveBar(); p=np.array([.03,.07]); J=g.kinematics(p)['J']; radius=g.static_force_radius(p)
    cap=g.rated_torque*g.ratio*g.transmission_efficiency
    for angle in np.linspace(0,2*np.pi,361):
        f=radius*np.array([np.cos(angle),np.sin(angle)])
        assert np.max(abs(J.T@f))<=cap+1e-12
    col=np.argmax(np.linalg.norm(J,axis=0))
    f=radius*J[:,col]/np.linalg.norm(J[:,col])
    assert abs((J.T@f)[col])==pytest.approx(cap)


def test_allocator_has_no_direction_distortion_or_stall_boost():
    g=FiveBar(); f=np.array([1.,-2.]); r=g.allocate_force([0,.09],f)
    assert r['force_N']==pytest.approx(f*r['authority'])
    assert np.linalg.norm(r['force_N'])<=g.force_cap+1e-12
    assert max(abs(r['motor_current_A']))<g.rated_current
    assert max(abs(r['output_torque_Nm']))<=g.rated_torque*g.ratio*g.transmission_efficiency


def test_unreachable_rejected_not_clipped():
    with pytest.raises(ValueError): FiveBar().kinematics([0,.3])
    with pytest.raises(ValueError): FiveBar().kinematics([np.nan,.1])
    with pytest.raises(ValueError): FiveBar(ratio=-1).kinematics([0,.1])


def test_locked_payload_requires_more_current():
    low=FiveBar(payload_mass=.03); high=FiveBar(payload_mass=.1)
    a=low.motor_requirements([0,.09],[0,0],[1.,0],[0,0])
    b=high.motor_requirements([0,.09],[0,0],[1.,0],[0,0])
    assert np.linalg.norm(b['current_A'])>np.linalg.norm(a['current_A'])


def test_coupled_radial_stop_dissipates_energy_and_preserves_reaction():
    from wholepen.grounded_replay import radial_stop
    from revk.feasibility import page_to_nib_matrix
    A=np.linalg.inv(page_to_nib_matrix(50));m=.00367;Mc=FiveBar().mass_matrix([0,.09])
    H=np.block([[Mc+m*np.eye(2),m*A],[m*A.T,m*A.T@A]])
    assert np.linalg.eigvalsh(H).min()>0
    x=np.array([0.,0.,.0018,.0002]);v=np.array([.01,-.02,.1,.02])
    xn,vn,impulse,loss=radial_stop(x,v,H,.0017)
    assert np.linalg.norm(xn[2:])<=.0017+1e-12
    assert impulse>0 and loss>0
    assert .5*vn@H@vn==pytest.approx(.5*v@H@v-loss)
    # No external impulse acts on the coarse generalized coordinate.
    assert (H@(vn-v))[:2]==pytest.approx([0.,0.],abs=1e-12)
    assert np.linalg.norm(vn[:2]-v[:2])>0


def test_frozen_gain_passes_delayed_local_pole_corners():
    from wholepen.grounded_servo_design import pole_radius
    for mass_scale in [.8,1.,1.2]:
        for fine_drag in [0.,.2,2.,8.]:
            for coarse_drag in [0.,80.2]:
                assert pole_radius(25,mass_scale=mass_scale,fine_drag=fine_drag,coarse_drag=coarse_drag)<1
    assert pole_radius(45,mass_scale=.8)>1


def test_voltage_boundary_includes_friction_and_flags_no_solution():
    g=FiveBar(supply=.4)
    r=g.allocate_force([0,.09],[.4,.2],[.02,0.])
    assert r['feasible'] and r['authority']<1
    assert max(abs(r['voltage_V']))<=g.supply+1e-12
    assert max(abs(r['motor_current_A']))<=g.rated_current+1e-12
    bad=g.allocate_force([0,.09],[0.,0.],[1.,0.])
    assert not bad['feasible'] and bad['authority']==0
    assert 'solution' in bad['reason']
