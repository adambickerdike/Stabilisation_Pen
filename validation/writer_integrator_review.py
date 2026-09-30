"""Independent mechanics review of the writing agent's planar plant integrator.

Checks energy/work reciprocity, current limiting, supply refusal, contact
switches and convergence to analytic smooth-Coulomb free decay. This diagnostic
does not assess recognizer accuracy or validate any assumed physical parameter.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from scipy.integrate import quad

from ai3.planar_integrator import step

ROOT=Path(__file__).resolve().parents[1]


def parameters():
    return dict(force_constant_N_A=np.array([.5,.43]),mass_kg=.00344,stiffness_N_m=1.56,
        damping_N_s_m=.002,bias_force_N=np.zeros(2),resistance_ohm=3.03,
        inductance_H=.001,current_limit_A=.7,drag_N=.02,velocity_scale_m_s=.0005,
        dt_s=.00005,max_step_s=.00005,voltage_limit_V=3.)


def study():
    rng=np.random.default_rng(29901);energy_rows=[]
    for label,limit in [('unclipped',100.),('current_limited',.04)]:
        balance=[];momentum=[];heat=[];rail=[];passive=[];clips=0
        for n in range(500):
            p=parameters();p.update(mass_kg=rng.uniform(.0025,.005),stiffness_N_m=rng.uniform(0,5),
                damping_N_s_m=rng.uniform(0,.02),drag_N=rng.uniform(0,.06),
                force_constant_N_A=rng.uniform(.3,.6,2),bias_force_N=rng.uniform(-.01,.01,2),
                current_limit_A=limit)
            q=rng.uniform(-.002,.002,2);v=rng.uniform(-.03,.03,2)
            current=rng.uniform(-min(limit,.1),min(limit,.1),2);voltage=rng.uniform(-3,3,2)
            if n%2==0 and label=='unclipped':voltage[:]=0;p['bias_force_N'][:]=0
            result=step(q,v,current,voltage,**p)
            q1,v1,i1=result[:3];qm=(q+q1)/2;vm=(v+v1)/2;im=(current+i1)/2
            m=p['mass_kg'];k=p['stiffness_N_m'];c=p['damping_N_s_m'];L=p['inductance_H'];h=p['dt_s']
            speed=np.linalg.norm(vm)
            drag=p['drag_N']*np.tanh(speed/p['velocity_scale_m_s'])*vm/max(speed,1e-30)
            energy0=.5*m*(v@v)+.5*k*(q@q)+.5*L*(current@current)
            energy1=.5*m*(v1@v1)+.5*k*(q1@q1)+.5*L*(i1@i1)
            losses=result[12]+h*(p['bias_force_N']@vm+c*(vm@vm)+drag@vm)
            balance.append(abs(energy1-energy0-result[13]+losses))
            impulse=m*(v1-v)+h*(k*qm+c*vm+p['bias_force_N']+drag-p['force_constant_N_A']*im)
            momentum.append(np.linalg.norm(impulse));heat.append(abs(result[12]-h*p['resistance_ohm']*(im@im)))
            rail.append(result[14]);clips+=int(result[9])
            assert np.max(abs(i1))<=limit+1e-12
            if n%2==0 and label=='unclipped':passive.append(energy1-energy0)
        energy_rows.append(dict(case=label,states=500,active_limit_axis_substeps=clips,
            max_energy_work_balance_residual_J=float(max(balance)),max_mechanical_impulse_residual_N_s=float(max(momentum)),
            max_copper_energy_integral_error_J=float(max(heat)),max_effective_voltage_V=float(max(rail)),
            max_unpowered_energy_change_J=float(max(passive)) if passive else None))
    decay=[]
    for h in [.0001,.00005,.000025]:
        p=parameters();p.update(force_constant_N_A=np.zeros(2),stiffness_N_m=0.,damping_N_s_m=0.,
                               dt_s=.0005,max_step_s=h)
        direction=np.array([.6,.8]);initial_speed=.003
        q=np.zeros(2);v=direction*initial_speed;current=np.zeros(2);max_error=0.;energies=[v@v]
        def exact(t):return .0005*np.arcsinh(np.sinh(initial_speed/.0005)*np.exp(-.02*t/(.00344*.0005)))
        for n in range(40):
            q,v,current,*_=step(q,v,current,np.zeros(2),**p)
            max_error=max(max_error,np.linalg.norm(v-direction*exact((n+1)*.0005)));energies.append(v@v)
        distance=quad(exact,0,.02,epsabs=1e-15)[0]
        decay.append(dict(internal_dt_s=h,max_velocity_error_m_s=float(max_error),
            displacement_error_m=float(np.linalg.norm(q-direction*distance)),
            kinetic_energy_nonincreasing=bool(np.all(np.diff(energies)<=1e-20))))
    p=parameters();p['drag_N']=0.
    before=step(np.array([.0001,0.]),np.array([.003,.002]),np.array([.01,0.]),np.zeros(2),**p)
    p['drag_N']=.02
    after=step(*before[:3],np.zeros(2),**p)
    velocity=before[1];speed=np.linalg.norm(velocity)
    expected_jump=-p['drag_N']*np.tanh(speed/p['velocity_scale_m_s'])*velocity/speed/p['mass_kg']
    contact_error=np.linalg.norm(after[4]-before[5]-expected_jump)
    p=parameters();p['current_limit_A']=.04
    rail_refused=False
    try:step(np.zeros(2),np.array([30.,0.]),np.zeros(2),np.zeros(2),**p)
    except ValueError as exc:rail_refused='supply rails' in str(exc)
    result=dict(evidence='Independent numerical-integrity checks; physical parameters and clinical efficacy are unvalidated',
        midpoint_energy_and_force=energy_rows,analytic_radial_friction=decay,
        binary_contact_acceleration_jump_residual_m_s2=float(contact_error),
        infeasible_regenerative_current_limit_refused=rail_refused,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),ROOT/'ai3/planar_integrator.py']})
    assert max(r['max_energy_work_balance_residual_J'] for r in energy_rows)<1e-14
    assert max(r['max_mechanical_impulse_residual_N_s'] for r in energy_rows)<1e-14
    assert rail_refused and contact_error<1e-10
    out=ROOT/'results/improvement/verification/writer_integrator_independent.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':study()
