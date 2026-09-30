"""Postprocess saved grounded traces; no controller or plant replay.

For the recorded semi-implicit step x[n+1]=x[n]+dt*v[n+1], the position
increments recover solver velocity exactly when no stop projection occurred.
Known initial position and zero initial velocity also recover the first step.
Acceleration follows from velocity increments. Reported jerk is a sampled
acceleration difference, not a continuous-time physical jerk certificate.
"""
from pathlib import Path
import hashlib
import json

import numpy as np

from wholepen.grounded import FiveBar, ROOT
from wholepen.grounded_replay import FineStage
from revk.feasibility import page_to_nib_matrix


def metrics(velocity,acceleration,ink,requested,dt):
    speed=np.linalg.norm(velocity,axis=1)
    acc=np.linalg.norm(acceleration,axis=1)
    delta=np.linalg.norm(np.diff(acceleration,axis=0),axis=1)
    jerk=delta/dt
    changes=ink[1:]!=ink[:-1]
    writing=ink&requested
    uninterrupted=writing[1:]&writing[:-1]&~changes
    return dict(peak_speed_m_s=float(speed.max()),peak_acceleration_m_s2=float(acc.max()),
        peak_sampled_jerk_m_s3=float(jerk.max()),
        peak_unchanged_contact_sampled_jerk_m_s3=float(jerk[~changes].max()),
        peak_requested_ink_speed_m_s=float(speed[writing].max()),
        peak_requested_ink_acceleration_m_s2=float(acc[writing].max()),
        peak_requested_ink_sampled_jerk_m_s3=float(jerk[uninterrupted].max()),
        acceleration_samples_over_2_m_s2=int(np.sum(acc>2.)),
        unchanged_contact_jerk_samples_over_300_m_s3=int(np.sum((jerk>300.)&~changes)),
        peak_acceleration_difference_at_contact_flag_change_m_s2=float(delta[changes].max()) if changes.any() else None,
        sampled_acceleration_2_gate_pass=bool(acc.max()<=2.),
        sampled_jerk_300_gate_pass=bool(jerk[~changes].max()<=300.))


def study():
    folder=ROOT/'results/improvement/mechanics'
    batch_path=folder/'grounded_batch.json'
    batch=json.loads(batch_path.read_text())
    selected=[r for r in batch['rows'] if r['feedforward'] and r['grip_stiffness_N_m']==0.]
    assert len(selected)==20
    fine=FineStage();rows=[];trace_hashes={};consistency=[]
    for record in selected:
        assert record['hard_stop_contacts']==0, 'stop projection prevents exact derivative reconstruction'
        path=folder/'grounded_words'/f"{record['writer']}_0N_m_ff.npz"
        with np.load(path) as saved:
            t=saved['t'];x=saved['position'];x0=saved['reference'][0]
            ink=saved['ink'];requested=saved['requested'];actual=saved['actual_xy']
            coarse_force=saved['coarse_force_N'];fine_current=saved['fine_current_A']
        dt=record['dt_s'];assert np.allclose(np.diff(t),dt,atol=1e-12,rtol=0)
        previous=np.vstack([x0,x[:-1]])
        v=(x-previous)/dt
        previous_v=np.vstack([np.zeros(4),v[:-1]])
        a=(v-previous_v)/dt
        A=np.linalg.inv(page_to_nib_matrix(record['model_assumptions']['tilt_deg']))
        assert np.max(abs(actual-(x[:,:2]+x[:,2:]@A.T)))<1e-14
        # Three independent force-balance checks per trace corroborate the
        # reconstruction and the replay's5ms cached coarse mass/Coriolis update.
        stage=FiveBar(**record['model_assumptions']['stage'])
        base=np.array([0.,stage.centre_y]);mass=record['model_assumptions']['fine_mass_kg']
        cache_steps=max(1,round(.005/dt));residual=[]
        for n in [0,len(x)//2,len(x)-1]:
            cached=n-n%cache_steps
            mc=stage.mass_matrix(base+previous[cached,:2])
            cor=stage.coriolis(base+previous[cached,:2],previous_v[cached,:2])
            H=np.block([[mc+mass*np.eye(2),mass*A],[mass*A.T,mass*A.T@A]])
            qp=previous[n,2:];vp=previous_v[n]
            fine_force=fine.km(qp)@fine_current[n]*np.sqrt(2.5)
            coarse_drag=.08*vp[:2]/np.sqrt(vp[:2]@vp[:2]+.001**2)+.2*vp[:2]
            force=np.r_[coarse_force[n]-coarse_drag-cor,
                fine_force-fine.spring(qp)-.008*np.tanh(vp[2:]/.001)-np.array([.012,-.008])]
            residual.append(np.linalg.norm(a[n]-np.linalg.solve(H,force)))
        consistency.extend(residual)
        tip_v=v[:,:2]+v[:,2:]@A.T;tip_a=a[:,:2]+a[:,2:]@A.T
        rows.append(dict(writer=record['writer'],samples=len(t),dt_s=dt,
            contact_flag_transitions=int(np.sum(ink[1:]!=ink[:-1])),
            original_ink_tracking_criterion_pass=record['engineering_complete'],
            tip_page=metrics(tip_v,tip_a,ink,requested,dt),
            body_page=metrics(v[:,:2],a[:,:2],ink,requested,dt),
            fine_mechanical=metrics(v[:,2:],a[:,2:],ink,requested,dt),
            force_balance_acceleration_residual_max_m_s2=float(max(residual))))
        trace_hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    summary={}
    for part in ['tip_page','body_page','fine_mechanical']:
        keys=['peak_speed_m_s','peak_acceleration_m_s2','peak_sampled_jerk_m_s3',
              'peak_unchanged_contact_sampled_jerk_m_s3','peak_requested_ink_speed_m_s',
              'peak_requested_ink_acceleration_m_s2','peak_requested_ink_sampled_jerk_m_s3',
              'peak_acceleration_difference_at_contact_flag_change_m_s2']
        summary[part]={key:dict(maximum=float(max(r[part][key] for r in rows)),
                               median_word_peak=float(np.median([r[part][key] for r in rows]))) for key in keys}
        summary[part].update(words=len(rows),acceleration_2_gate_pass=sum(r[part]['sampled_acceleration_2_gate_pass'] for r in rows),
            sampled_jerk_300_gate_pass=sum(r[part]['sampled_jerk_300_gate_pass'] for r in rows),
            both_gates_pass=sum(r[part]['sampled_acceleration_2_gate_pass'] and r[part]['sampled_jerk_300_gate_pass'] for r in rows))
    result=dict(evidence='Postprocessing frozen simulated states; no plant/controller changes or rerun',
        cohort='All20 unloaded feedforward+feedback accepted se traces;40 letters; final25Hz fine/9Hz coarse gains',
        reconstruction='v[n+1]=(x[n+1]-x[n])/dt; a[n]=(v[n+1]-v[n])/dt; initial x=reference[0],v=0; no stop projections',
        sample_time_note='The source stores post-step positions at pre-step labels t[n]; reconstructed state time is t[n]+dt. Acceleration is the force update for the preceding interval.',
        dt_s=.0005,jerk_definition='Norm of adjacent reconstructed acceleration-vector differences divided by0.5ms, unfiltered; not a continuous-time jerk bound',
        contact_note='Contact flag gates ink only in this plant. Guide drag/balance bias remain continuous; no landing-impact or contact-onset force jump is modelled. Differences coincident with flag changes are not physical impact estimates.',
        original_acceptance='No refusal/stop;>=98% requested-ink contact;<=0.10mm RMS during actual requested ink;<=0.02mm air-phase ink path. Actual acceleration/jerk were not acceptance gates.',
        comparison_note='2m/s² and300m/s³ are reference-planning assumptions reused as diagnostic comparisons here, not measured hardware ratings. Mechanical fine axes, body page axes and combined tip page axes are reported separately.',
        force_balance_checks=len(consistency),maximum_force_balance_acceleration_residual_m_s2=float(max(consistency)),
        summary=summary,rows=rows,
        limitations=['perfect current loops permit force changes at each0.5ms control update',
                     'no inductive current-loop dynamics or finite current-slew validation',
                     'normal impact, friction onset and pen attitude changes absent',
                     'passed friction-step energy check does not imply acceleration or jerk compliance'],
        trace_sha256=trace_hashes,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),ROOT/'wholepen/grounded_replay.py',batch_path]})
    assert max(consistency)<1e-7
    (folder/'grounded_derivative_check.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(summary=summary,force_balance_residual_max=max(consistency)),indent=2))


if __name__=='__main__':study()
