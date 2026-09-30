"""Coupled coarse/fine accepted-reference plant simulation.

The reference is known because the user accepted it. This is not prediction of
future freehand intent. The plant has a positive-definite coupled mass matrix,
reaction forces, motor limits, wire spring, magnetic map, finite sensor delay,
causal velocity estimates, contact friction and delayed pen lift. Nothing here
is measured hardware or a patient outcome. Rigid bearings, perfect current
loops and the specified contact law remain substantial modelling assumptions.
"""
from __future__ import annotations

import argparse
import json
import hashlib
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

from .grounded import FiveBar, ROOT
from revk.feasibility import electrical_allocation, page_to_nib_matrix, wire_anchor


class FineStage:
    def __init__(self, study_path=None, radius_mm=1.5):
        path=study_path or ROOT/'results/improvement/mechanics/mechanics_study.json'
        data=json.loads(Path(path).read_text())
        self.row=min(data['candidates'],key=lambda r:abs(r['radius_mm']-radius_mm))
        self.radius=self.row['radius_mm']*.001
        self.wire=self.row['wire']; coil=self.row['coil']
        points=np.asarray(coil['map']['positions_m'])
        self.field_scale=.7
        maps=np.asarray(coil['map']['wrench_per_sqrtW'])[:,:2,:]*self.field_scale
        self.field=LinearNDInterpolator(points,maps)
        self.nearest=NearestNDInterpolator(points,maps)
        self.mass=self.row['duty_by_residual']['0.02']['moving_mass_kg']
        self.Rlead=2*self.wire['wire_resistance_20C_ohm']/self.wire['parallel_wires_per_lead']
        self.qgrid=np.linspace(0,self.radius+.2e-3,151)
        self.springgrid=np.array([wire_anchor(q,length=self.wire['length_mm']*.001,
            diameter=self.wire['diameter_mm']*.001,anchor_stiffness=100.,assembly_tension=.005,
            n_wires=self.wire['n_wires'])['lateral_force_N'] for q in self.qgrid])

    def km(self,q):
        if np.linalg.norm(q)>self.radius+.2e-3+1e-12:
            raise ValueError('fine mechanism exceeded hard radial stop')
        value=np.asarray(self.field(np.asarray(q)[None,:]))[0]
        if not np.isfinite(value).all():
            value=np.asarray(self.nearest(np.asarray(q)[None,:]))[0]
        return value

    def spring(self,q):
        r=np.linalg.norm(q)
        return np.interp(r,self.qgrid,self.springgrid)*np.asarray(q)/max(r,1e-15)

    def allocate(self,q,v,force):
        # Instantaneous0.15W is more restrictive than an RMS thermal budget;
        # inductance/current-loop bandwidth is an unverified implementation gate.
        return electrical_allocation(self.km(q),force,v,lead_resistance=self.Rlead,
                                     current_limit=.7,copper_power_limit=.15)

    def heat(self,currents):
        rms=np.sqrt(np.mean(np.asarray(currents)**2,axis=0))
        A=np.pi/4*(self.wire['diameter_mm']*.001)**2
        rho=1.7241e-8/.22; L=self.wire['length_mm']*.001
        heat0=(rms/self.wire['parallel_wires_per_lead'])**2*rho*L*L/(8*105*A*A)
        heat=heat0/(1-.00393*heat0)
        return dict(current_rms_A=rms.tolist(),wire_rise_above_clamps_K=heat.tolist(),
                    lead_thermal_pass=bool(np.all(heat0<1/.00393) and max(heat)<=45),
                    clamp_temperature='unknown; temperature is rise above assumed equal-temperature ends')


def radial_stop(position,velocity,H,limit):
    """Mass-weighted position projection and perfectly inelastic stop impulse.

    A physical stop is not extra controlled authority. Hits are counted as
    failures. The impulse cannot create kinetic energy, and its reaction is
    carried through the coupled inertia instead of deleting fine velocity.
    """
    x=np.asarray(position,float).copy();v=np.asarray(velocity,float).copy()
    if np.linalg.norm(x[2:])<=limit:return x,v,0.,0.
    for _ in range(8):
        r=np.linalg.norm(x[2:]);n=np.r_[0.,0.,x[2:]/r]
        z=np.linalg.solve(H,n)
        x-=z*max(r-limit,0.)/(n@z)
        if np.linalg.norm(x[2:])<=limit+1e-13:break
    n=np.r_[0.,0.,x[2:]/np.linalg.norm(x[2:])];z=np.linalg.solve(H,n)
    impulse=max(float(n@v),0.)/(n@z)
    before=.5*v@H@v;v-=z*impulse;loss=before-.5*v@H@v
    return x,v,float(impulse),float(loss)


def fine_postcheck(path,out=None):
    data=np.load(path); fine=FineStage(); M=page_to_nib_matrix(50); A=np.linalg.inv(M)
    q=data['q']; v=data['q_velocity_m_s']; a=data['q_acceleration_m_s2']
    absolute_a=(data['absolute_nib_acceleration_page_m_s2'] if 'absolute_nib_acceleration_page_m_s2' in data
                else a@A.T)
    currents=[]; powers=[]; requested=[]; voltages=[]; force_norm=[]
    for qi,vi,ai in zip(q,v,absolute_a):
        # True virtual-work projection; acceleration is absolute and parallel
        # to the page because the refill can slide axially at fixed contact.
        f=fine.mass*A.T@ai+fine.spring(qi)+np.array([.012,-.008])
        speed=np.linalg.norm(vi)
        f+=.008*vi/max(speed,1e-12)
        result=fine.allocate(qi,vi,f)
        currents.append(result['requested_current_A']); requested.append(result['authority'])
        powers.append(result['requested_copper_power_W']);voltages.append(result['voltage_V'])
        force_norm.append(np.linalg.norm(f))
    report=dict(status='CALC sampled spatial magnetic-map force screen, not tracking or a worst-case proof',
                source=str(path),mass_kg=fine.mass,field_scale=fine.field_scale,
                force_peak_N=float(max(force_norm)),current_peak_A=float(np.max(np.abs(currents))),
                copper_mean_W=float(np.mean(powers)),copper_peak_W=float(max(powers)),
                minimum_authority=float(min(requested)),radial_peak_mm=float(np.linalg.norm(q,axis=1).max()*1000),
                limitations=['linear interpolation of97 calculated map points','constant50degree pose',
                             '20mN nominal combined guide/balance load, not measured','no inductive voltage'],
                heat=fine.heat(currents))
    report['screen_pass']=bool(min(requested)>=1-1e-9 and report['heat']['lead_thermal_pass'])
    if out:Path(out).write_text(json.dumps(report,indent=2)+'\n')
    return report


def simulate(path,grip_stiffness=0.,feedforward=True,dt=.0005,seed=31,
             lift_delay=.200,noise_factor=1.,fine_stage=None,fine_bandwidth=25.):
    source=np.load(path); fine=fine_stage or FineStage(); stage=FiveBar()
    ts=source['t']; duration=ts[-1]; t=np.arange(0,duration+dt/2,dt)
    def interp(key):
        raw=source[key]
        return np.column_stack([np.interp(t,ts,raw[:,i]) for i in range(raw.shape[1])])
    cr=interp('coarse_offset_page_m'); cv=interp('coarse_velocity_m_s'); ca=interp('coarse_acceleration_m_s2')
    qr=interp('q'); qv=interp('q_velocity_m_s'); qa=interp('q_acceleration_m_s2')
    # Requested down is held piecewise, never linearly ramped to a contact state.
    indices=np.minimum(np.searchsorted(ts,t,side='right')-1,len(ts)-1)
    requested=source['down'][indices]
    phases=source['phase'][indices]
    M=page_to_nib_matrix(50); A=np.linalg.inv(M); mass=fine.mass
    base=np.array([0.,stage.centre_y]); x=np.r_[cr[0],qr[0]]; v=np.zeros(4)
    hand_neutral=cr[0].copy()  # person initially holds the placed starting pose
    rng=np.random.default_rng(seed); delay_steps=max(1,round(.002/dt)); lift_steps=max(1,round(lift_delay/dt))
    sensor_history=[x.copy() for _ in range(delay_steps+1)]; previous=x.copy(); vest=np.zeros(4)
    positions=[]; velocities=[]; fine_current=[]; coarse_current=[]; forces=[]; voltage=[]; authority=[]; ink=[]; errors=[]
    refusal=None; unsafe_since=None; commanded_down=False; contact=False; lift_due=None;hold=None
    k_coarse=stage.mass_matrix(base)*(2*np.pi*9)**2
    c_coarse=stage.mass_matrix(base)*2*.9*2*np.pi*9
    # Frozen from grounded_servo_design's delayed local pole screen, not tuned
    # to these held-out writer trajectories. Higher45Hz gains had a limit cycle.
    k_fine=mass*A.T@A*(2*np.pi*fine_bandwidth)**2
    c_fine=mass*A.T@A*2*.85*2*np.pi*fine_bandwidth
    fine_bias=np.array([.012,-.008]); controller_bias=np.array([.010,-.006])
    drag=.2; peak_reaction=0.;stop_hits=0;stop_impulse=0.;stop_energy=0.
    for n,ti in enumerate(t):
        measured=sensor_history[0]+noise_factor*rng.normal(0,[3e-6,3e-6,1.5e-6,1.5e-6])
        alpha=1-np.exp(-2*np.pi*100*dt)
        vest+=(alpha*((measured-previous)/dt-vest));previous=measured.copy()
        estimated=measured+vest*(delay_steps*dt)  # causal constant-velocity extrapolation
        if n%max(1,round(.005/dt))==0:
            mass_coarse=stage.mass_matrix(base+x[:2])
            coriolis=stage.coriolis(base+x[:2],v[:2])
        # Equal and opposite reactions appear through the off-diagonal mass
        # blocks; treating the fine stage as grounded would omit them.
        H=np.block([[mass_coarse+mass*np.eye(2),mass*A],
                    [mass*A.T,mass*A.T@A]])
        pref=np.r_[cr[n],qr[n]] if hold is None else hold
        vref=np.r_[cv[n],qv[n]] if hold is None else np.zeros(4)
        ref_acc=np.r_[ca[n],qa[n]] if hold is None else np.zeros(4)
        desired=np.r_[k_coarse@(pref[:2]-estimated[:2])+c_coarse@(vref[:2]-vest[:2]),
                      k_fine@(pref[2:]-estimated[2:])+c_fine@(vref[2:]-vest[2:])]
        spring=fine.spring(x[2:]); fine_drag=.008*np.tanh(v[2:]/.001)
        coarse_drag=.08*v[:2]/np.sqrt(v[:2]@v[:2]+.001**2)+drag*v[:2]
        if feedforward:
            desired+=H@ref_acc
            desired[:2]+=.08*vref[:2]/np.sqrt(vref[:2]@vref[:2]+.001**2)+drag*vref[:2]
            desired[2:]+=fine.spring(pref[2:])+controller_bias+.006*np.tanh(vref[2:]/.001)
        coarse=stage.allocate_force(base+x[:2],desired[:2],v[:2])
        if not coarse['feasible']:raise RuntimeError('coarse electrical solution absent')
        fa=fine.allocate(x[2:],v[2:],desired[2:])
        if not fa['feasible']:raise RuntimeError('fine electrical solution absent')
        fu=np.r_[coarse['force_N'],fa['force_N']]
        hand=-grip_stiffness*(x[:2]-hand_neutral)-.6*v[:2] if grip_stiffness else np.zeros(2)
        peak_reaction=max(peak_reaction,np.linalg.norm(hand))
        external=np.r_[hand-coarse_drag-coriolis,-spring-fine_drag-fine_bias]
        acc=np.linalg.solve(H,fu+external)
        # Semi-implicit integration. dt-halving comparison is saved by main.
        v+=acc*dt; x+=v*dt
        if np.linalg.norm(x[2:])>fine.radius+.2e-3:
            x,v,impulse,energy=radial_stop(x,v,H,fine.radius+.2e-3)
            stop_hits+=1;stop_impulse=max(stop_impulse,impulse);stop_energy+=energy
            if refusal is None:refusal=float(ti);hold=x.copy()
        sensor_history.append(x.copy());sensor_history.pop(0)
        actual=x[:2]+A@x[2:]; reference=cr[n]+A@qr[n]
        error=float(np.linalg.norm(actual-reference))
        bad=error>.0002 or np.linalg.norm(x[2:])>fine.radius-.05e-3
        if bad:
            if unsafe_since is None:unsafe_since=ti
            if ti-unsafe_since>=.010 and refusal is None:
                refusal=float(ti);hold=x.copy()
        else:unsafe_since=None
        # The lower phase must start the actuator BEFORE the first ink sample.
        # A modelled contact state, not the requested ink flag, gates actual ink.
        down=str(phases[n]) in ('lower','ink') and refusal is None
        if down!=commanded_down:
            commanded_down=down;lift_due=n+lift_steps
        if lift_due is not None and n>=lift_due:
            contact=commanded_down;lift_due=None
        positions.append(x.copy());velocities.append(v.copy());fine_current.append(fa['current_A'])
        coarse_current.append(coarse['motor_current_A']);forces.append(coarse['force_N'])
        voltage.append(coarse['voltage_V']);authority.append([coarse['authority'],fa['authority']])
        ink.append(contact);errors.append(error)
    pos=np.asarray(positions);ink=np.asarray(ink);errors=np.asarray(errors);fine_current=np.asarray(fine_current)
    actual_xy=pos[:,:2]+pos[:,2:]@A.T
    travelled=np.r_[0.,np.linalg.norm(np.diff(actual_xy,axis=0),axis=1)]
    air=np.isin(phases,['air','transfer'])
    report={
        'status':'COUPLED SIMULATION of proposed grounded stage +1.5mm fine stage; not measured',
        'grip_stiffness_N_m':grip_stiffness,'feedforward':feedforward,'dt_s':dt,'seed':seed,
        'duration_s':float(duration),'requested_ink_samples':int(requested.sum()),'actual_ink_samples':int(ink.sum()),
        'ink_coverage_fraction':float(np.sum(ink&requested)/max(requested.sum(),1)),
        'actual_ink_rms_error_mm':float(np.sqrt(np.mean(errors[ink]**2))*1000) if ink.any() else None,
        'actual_requested_ink_rms_error_mm':float(np.sqrt(np.mean(errors[ink&requested]**2))*1000) if (ink&requested).any() else None,
        'air_phase_ink_path_mm':float(np.sum(travelled[air&ink])*1000),
        'all_trajectory_rms_error_mm':float(np.sqrt(np.mean(errors**2))*1000),
        'all_trajectory_max_error_mm':float(max(errors)*1000),
        'refusal_time_s':refusal,'refusal_reason':None if refusal is None else 'tracking error>0.20mm for10ms or radial reserve exhausted',
        'coarse_force_peak_N':float(np.linalg.norm(forces,axis=1).max()),'hand_reaction_peak_N':float(peak_reaction),
        'coarse_current_peak_A':float(np.max(np.abs(coarse_current))),'coarse_voltage_peak_V':float(np.max(np.abs(voltage))),
        'fine_current_peak_A':float(np.max(abs(fine_current))),'fine_radial_peak_mm':float(np.linalg.norm(pos[:,2:],axis=1).max()*1000),
        'minimum_authority':np.min(authority,axis=0).tolist(),'fine_wire_heat':fine.heat(fine_current),
        'hard_stop_contacts':stop_hits,'maximum_stop_impulse_Ns':stop_impulse,'stop_dissipated_energy_J':stop_energy,
        'model_assumptions':{'stage':asdict(stage),'tilt_deg':50,'fine_mass_kg':mass,'field_scale':.7,
                            'sensor_delay_s':delay_steps*dt,'sensor_noise_std_m':[3e-6,3e-6,1.5e-6,1.5e-6],
                            'velocity_filter_Hz':100,'lift_delay_s':lift_steps*dt,'lift_feedback':'ideal binary model after commanded phase delay',
                            'noise_factor':noise_factor,
                            'fine_bandwidth_Hz':fine_bandwidth,'coarse_bandwidth_Hz':9.,
                            'hand_neutral_position_m':hand_neutral.tolist(),'hand_neutral_rule':'placed start; no artificial initial spring preload',
                            'fine_nominal_bias_N':fine_bias.tolist(),'coarse_refusal_error_m':.0002},
        'limitations':['rigid links and perfect current loops','sampled/interpolated static magnetic map',
                       'no human trial, friction/hand/load assumptions','time-discrete servo validation only',
                       'constant tilt, normal support and delayed contact are idealized','electrical inductance not in current-loop plant'],
    }
    arrays=dict(t=t,position=pos,reference=np.column_stack([cr,qr]),ink=ink,requested=requested,
                actual_xy=actual_xy,reference_xy=cr+qr@A.T,
                coarse_force_N=np.asarray(forces),fine_current_A=fine_current,error_m=errors)
    return report,arrays


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trajectory',type=Path,default=ROOT/'results/improvement/writing/coarse_fine_reference_200ms.npz')
    ap.add_argument('--out',type=Path,default=ROOT/'results/improvement/mechanics')
    ap.add_argument('--batch',type=Path,help='writing-agent accepted-word manifest; every exported word stays in denominator')
    args=ap.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    if args.batch:
        manifest=json.loads(args.batch.read_text());rows=[];fine=FineStage()
        trace_dir=args.out/'grounded_words';trace_dir.mkdir(exist_ok=True)
        cases=[(0.,False),(0.,True),(200.,True),(500.,True)]
        for entry in manifest['rows']:
            for grip,ff in cases:
                path=ROOT/entry['word_reference']
                result,arrays=simulate(path,grip,ff,fine_stage=fine)
                result.update(writer=entry['writer'],session=entry['session'],text='se',source=str(path.relative_to(ROOT)))
                result['engineering_complete']=bool(result['refusal_time_s'] is None and result['hard_stop_contacts']==0 and
                    result['ink_coverage_fraction']>=.98 and result['actual_requested_ink_rms_error_mm'] is not None and
                    result['actual_requested_ink_rms_error_mm']<=.10 and result['air_phase_ink_path_mm']<=.02)
                name=f"{entry['writer']}_{int(grip)}N_m_{'ff' if ff else 'feedback'}"
                np.savez_compressed(trace_dir/(name+'.npz'),**arrays)
                rows.append(result)
                print(name,'complete',result['engineering_complete'],'coverage',round(result['ink_coverage_fraction'],3),
                      'rms_mm',result['actual_requested_ink_rms_error_mm'],'refusal',result['refusal_time_s'],flush=True)
            (args.out/'grounded_batch.json').write_text(json.dumps({'rows':rows,'status':'running'},indent=2)+'\n')
        summary=[]
        for grip,ff in cases:
            selected=[r for r in rows if r['grip_stiffness_N_m']==grip and r['feedforward']==ff]
            errors=[r['actual_requested_ink_rms_error_mm'] for r in selected if r['actual_requested_ink_rms_error_mm'] is not None]
            summary.append(dict(grip_stiffness_N_m=grip,feedforward=ff,words=len(selected),letters=2*len(selected),
                engineering_complete=sum(r['engineering_complete'] for r in selected),
                refused=sum(r['refusal_time_s'] is not None for r in selected),
                words_hitting_hard_stop=sum(r['hard_stop_contacts']>0 for r in selected),
                median_ink_coverage=float(np.median([r['ink_coverage_fraction'] for r in selected])),
                median_actual_ink_error_mm=float(np.median(errors)) if errors else None,
                error_denominator_words_with_ink=len(errors),
                coarse_force_max_N=max(r['coarse_force_peak_N'] for r in selected),
                fine_current_max_A=max(r['fine_current_peak_A'] for r in selected)))
        final=dict(status='SIMULATION ONLY; not clinical or hardware validation',summary=summary,rows=rows,
            reference_manifest=str(args.batch),manifest_sha256=hashlib.sha256(args.batch.read_bytes()).hexdigest(),
            code_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [Path(__file__),ROOT/'wholepen/grounded.py',ROOT/'revk/feasibility.py']},
            declared_engineering_criterion='no refusal;>=98% ink coverage;<=0.10mm RMS while requested ink actually contacts;<=0.02mm air-phase ink path',
            criterion_status='engineering assumptions, not clinical readability thresholds',
            cohort='20 exported UJI test-writer session1 template suffixes;synthetic explicit acceptance;not newly blind validation')
        (args.out/'grounded_batch.json').write_text(json.dumps(final,indent=2)+'\n')
        print(json.dumps(summary,indent=2));return
    fine=fine_postcheck(args.trajectory,args.out/'fine_trajectory.json');print(fine,flush=True)
    results=[]
    for grip,ff in [(0.,False),(0.,True),(50.,True),(200.,True),(500.,True)]:
        result,arrays=simulate(args.trajectory,grip,ff)
        name=f'grounded_{int(grip)}N_m_{"ff" if ff else "feedback"}'
        np.savez_compressed(args.out/(name+'.npz'),**arrays)
        results.append(result);print({k:result[k] for k in ['grip_stiffness_N_m','feedforward','actual_ink_rms_error_mm','refusal_time_s','coarse_force_peak_N']},flush=True)
    quiet,_=simulate(args.trajectory,0.,True,noise_factor=0.)
    half,_=simulate(args.trajectory,0.,True,dt=.00025,noise_factor=0.)
    data=dict(cases=results,noise_free=quiet,noise_free_half_step=half,source=str(args.trajectory),
              evidence='Simulated actual contact/trajectory under explicit assumed dynamics; no patient outcomes')
    (args.out/'grounded_replay.json').write_text(json.dumps(data,indent=2)+'\n')


if __name__=='__main__':main()
