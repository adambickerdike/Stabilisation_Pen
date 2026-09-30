"""Independent energy bound for the grounded replay's explicit friction step.

This isolates friction at a frozen coupled mass matrix. It does not certify the
feedback loop, changing inertia, stiffness, impacts, or contact-model accuracy.
The replay itself is not changed by this diagnostic.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from scipy.linalg import eigh
from scipy.integrate import solve_ivp

from wholepen.grounded import FiveBar, ROOT
from revk.feasibility import page_to_nib_matrix


def friction(v):
    """Same physical drag laws; includes the larger resisting-grip damping."""
    velocity=np.atleast_2d(v)
    coarse=velocity[:,:2]
    coarse_force=.08*coarse/np.sqrt(np.sum(coarse*coarse,axis=1)[:,None]+.001**2)+.8*coarse
    fine_force=.008*np.tanh(velocity[:,2:]/.001)
    result=np.column_stack([coarse_force,fine_force])
    return result[0] if np.asarray(v).ndim==1 else result


def study():
    stage=FiveBar()
    data=json.loads((ROOT/'results/improvement/mechanics/mechanics_study.json').read_text())
    fine=next(r for r in data['candidates'] if r['radius_mm']==1.5)
    mass=fine['duty_by_residual']['0.02']['moving_mass_kg']
    A=np.linalg.inv(page_to_nib_matrix(50.))
    # The radial coarse drag's largest differential slope is80N.s/m;
    # add0.2 viscous and0.6 hand damping. Fine tanh slopes are <=8N.s/m.
    upper=np.diag([80.8,80.8,8.,8.])
    rows=[];worst=None
    for x in np.linspace(-.03,.03,25):
        for y in np.linspace(.07,.11,17):
            mc=stage.mass_matrix([x,y])
            H=np.block([[mc+mass*np.eye(2),mass*A],[mass*A.T,mass*A.T@A]])
            eigenvalues,eigenvectors=eigh(upper,H)
            row=dict(x_m=float(x),y_m=float(y),lambda_max_per_s=float(eigenvalues[-1]),
                     energy_nonincrease_dt_max_s=float(2/eigenvalues[-1]))
            rows.append(row)
            if worst is None or eigenvalues[-1]>worst[0]:
                worst=(float(eigenvalues[-1]),H,eigenvectors[:,-1],row)
    lam,H,direction,row=worst
    direction=direction/np.linalg.norm(direction)
    rng=np.random.default_rng(34018)
    vectors=rng.normal(size=(20000,4));vectors/=np.linalg.norm(vectors,axis=1)[:,None]
    velocities=vectors*10**rng.uniform(-9,-.5,size=(len(vectors),1))
    velocities=np.vstack([velocities,direction[None,:]*np.geomspace(1e-10,.3,200)[:,None]])
    energies=.5*np.einsum('ni,ij,nj->n',velocities,H,velocities)
    dt=.0005
    nextv=velocities-dt*np.linalg.solve(H,friction(velocities).T).T
    nextenergies=.5*np.einsum('ni,ij,nj->n',nextv,H,nextv)
    ratios=nextenergies/energies
    decays=[]
    for amplitude in [1e-6,.003,.03]:
        v0=direction*amplitude
        t=np.arange(101)*dt
        precise=solve_ivp(lambda _,v:-np.linalg.solve(H,friction(v)),[0,t[-1]],v0,
                          t_eval=t,rtol=1e-10,atol=1e-13,method='Radau').y.T
        explicit=np.empty_like(precise);explicit[0]=v0
        for n in range(len(t)-1):explicit[n+1]=explicit[n]-dt*np.linalg.solve(H,friction(explicit[n]))
        energy=.5*np.einsum('ni,ij,nj->n',explicit,H,explicit)
        decays.append(dict(initial_speed_m_s=amplitude,energy_nonincreasing=bool(np.all(np.diff(energy)<=1e-25)),
            peak_energy_over_initial=float(max(energy)/energy[0]),
            max_velocity_difference_from_Radau_m_s=float(np.linalg.norm(explicit-precise,axis=1).max()),
            largest_zero_speed_euler_multiplier=float(1-dt*lam)))
    trace_dir=ROOT/'results/improvement/mechanics/grounded_words'
    paths=list(trace_dir.glob('*.npz'))
    coarse_positions=[]
    for path in paths:
        with np.load(path) as trace:coarse_positions.append(trace['position'][:,:2])
    offsets=np.vstack(coarse_positions)
    patch_pass=bool(np.all(np.abs(offsets)<=np.array([.03,.02])+1e-12))
    result=dict(evidence='Independent mathematical friction-step diagnostic; not a full closed-loop or hardware certificate',
        parameters=dict(fine_mass_kg=mass,tilt_deg=50.,dt_s=dt,
                        max_damping_diagonal_N_s_m=np.diag(upper).tolist(),sampled_patch_points=len(rows)),
        derivation='For fixed H and friction f=gradient(phi) with0<=Jacobian(f)<=Dmax, explicit velocity-step energy decreases if dt*lambda_max(Dmax,H)<=2. DeltaE=-dt*v.T*f+dt^2/2*f.T*H^-1*f.',
        worst_patch_point=row,maximum_dt_lambda=dt*lam,
        nonlinear_velocity_samples=len(velocities),maximum_sampled_energy_ratio=float(ratios.max()),
        sampled_kinetic_energy_nonincrease=bool(np.all(nextenergies<=energies*(1+1e-12))),
        free_decay_checks=decays,
        observed_trace_count=len(paths),observed_max_abs_coarse_offset_m=np.max(abs(offsets),axis=0).tolist(),
        observed_coarse_positions_inside_checked_patch=patch_pass,
        limitations=['fixed-mass isolated friction step only','sign reversal near zero is possible at0.5ms',
                     'not an accuracy certificate for forced feedback dynamics','mass variation sampled on425points, not a continuous interval proof',
                     'friction and hand damping remain unmeasured assumptions'],
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                       [Path(__file__),ROOT/'wholepen/grounded.py',ROOT/'wholepen/grounded_replay.py']})
    out=ROOT/'results/improvement/mechanics/grounded_friction_check.json'
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':study()
