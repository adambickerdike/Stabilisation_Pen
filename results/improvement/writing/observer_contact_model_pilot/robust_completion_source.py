"""Causal, bounded-disturbance feedback for explicitly accepted future ink.

This is an engineering prototype for the generic planar stage, not the Rev K
mechanism. Position measurements carry their acquisition timestamps. A delayed
update is replayed through already applied, measured coil currents to estimate
the present state. The disturbance state has a force cap; no target-error
integrator can wind up during current saturation. Position-noise and process
covariance assumptions are fixed by ObserverDesign, not read from plant truth.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.linalg import expm

from . import completion_replay as C
from . import layers as L
from . import reachable as R


@dataclass(frozen=True)
class ObserverDesign:
    measured_position_std_m:float=10e-6
    disturbance_random_walk_m_s2_sqrt_s:float=2.
    innovation_trigger_sigma:float=2.5
    disturbance_jump_std_N:float=.020
    innovation_refractory_s:float=.020
    contact_drag_prior_N:float=.010   # declared nominal paper/refill load, not plant truth
    contact_velocity_scale_m_s:float=.0005
    disturbance_force_cap_N:float=.060
    maximum_bandwidth_hz:float=20.
    damping_ratio:float=.90
    delay_phase_budget_rad:float=np.pi/6
    initial_velocity_std_m_s:float=.003
    initial_disturbance_std_N:float=.010


class DelayedDisturbanceObserver:
    """Two independent axes with common 3-state covariance: position, speed, bias.

    The disturbance state is acceleration added to the nominal plant model.
    Positive state means the real plant accelerates more than its current model.
    Only timestamped position and measured applied current enter this estimator.
    """
    def __init__(self,model,position,dt,design=ObserverDesign()):
        self.model=model;self.dt=dt;self.design=design
        m=model.mass_kg
        if m<=0 or dt<=0:raise ValueError("positive mass and time step required")
        A=np.array([[0.,1.,0.],[-model.stiffness_N_m/m,-model.damping_N_s_m/m,1.],[0.,0.,0.]])
        aug=np.zeros((4,4));aug[:3,:3]=A;aug[1,3]=1.
        discrete=expm(aug*dt);self.F=discrete[:3,:3];self.B=discrete[:3,3]
        Qc=np.zeros((3,3));Qc[2,2]=design.disturbance_random_walk_m_s2_sqrt_s**2
        block=np.block([[A,Qc],[np.zeros((3,3)),-A.T]])
        E=expm(block*dt);self.Q=E[:3,3:]@self.F.T
        self.Q=(self.Q+self.Q.T)/2
        x=np.zeros((3,2));x[0]=position
        P=np.diag([design.measured_position_std_m**2,design.initial_velocity_std_m_s**2,
                   (design.initial_disturbance_std_N/m)**2])
        self.states=[x];self.covariances=[P];self.inputs=[];self.capped_updates=0
        self.previous_innovation=np.zeros(2);self.previous_innovation_large=False
        self.last_change_index=-100000;self.change_detections=0

    def predict(self,current,contact_force=np.zeros(2)):
        model=self.model
        u=(np.asarray(model.force_constant_N_A)*current-model.bias_force_N-contact_force)/model.mass_kg
        self.inputs.append(u.copy())
        self.states.append(self.F@self.states[-1]+self.B[:,None]*u)
        P=self.F@self.covariances[-1]@self.F.T+self.Q
        self.covariances.append((P+P.T)/2)

    def correct(self,position,acquisition_index):
        i=acquisition_index
        if i<0 or i>=len(self.states):raise ValueError("measurement timestamp is outside causal history")
        x=self.states[i].copy();P=self.covariances[i]
        innovation=np.asarray(position)-x[0]
        sigma=np.sqrt(P[0,0]+self.design.measured_position_std_m**2)
        large=np.linalg.norm(innovation)>self.design.innovation_trigger_sigma*sigma
        # Two aligned surprising measurements suggest a change in external
        # load. Inflate only the load-state prior once, then return to the low
        # process noise. No true force, mass or noise parameter is consulted.
        if (large and self.previous_innovation_large and innovation@self.previous_innovation>0 and
            (i-self.last_change_index)*self.dt>=self.design.innovation_refractory_s):
            P=P.copy();P[2,2]+=(self.design.disturbance_jump_std_N/self.model.mass_kg)**2
            self.last_change_index=i;self.change_detections+=1
        self.previous_innovation=innovation.copy();self.previous_innovation_large=large
        K=P[:,0]/(P[0,0]+self.design.measured_position_std_m**2)
        x+=K[:,None]*innovation
        cap=self.design.disturbance_force_cap_N/self.model.mass_kg
        clipped=np.clip(x[2],-cap,cap)
        self.capped_updates+=int(np.any(clipped!=x[2]));x[2]=clipped
        # Joseph covariance update remains symmetric/PSD at small sensor noise.
        J=np.eye(3);J[:,0]-=K
        P=J@P@J.T+np.outer(K,K)*self.design.measured_position_std_m**2
        self.states[i]=x;self.covariances[i]=(P+P.T)/2
        for k in range(i+1,len(self.states)):
            self.states[k]=self.F@self.states[k-1]+self.B[:,None]*self.inputs[k-1]
            P=self.F@self.covariances[k-1]@self.F.T+self.Q
            self.covariances[k]=(P+P.T)/2
        return self.states[-1].copy()


def replay(plan:L.WritingPlan,trajectories, *,plant_dt=.0005,control_dt=.002,
           perturbation:C.Perturbation=C.Perturbation(),design:ObserverDesign=ObserverDesign(),
           fault=None):
    ratio=round(control_dt/plant_dt);delay_ticks=round(perturbation.position_delay_s/plant_dt)
    if min(plant_dt,control_dt)<=0 or abs(ratio*plant_dt-control_dt)>1e-12 or ratio<1:
        raise ValueError("controller interval must be an integer multiple of plant interval")
    if abs(delay_ticks*plant_dt-perturbation.position_delay_s)>1e-12:
        raise ValueError("this replay requires acquisition delays aligned to the plant clock")
    # A 30-degree phase budget on delay plus sample/hold, with a fixed 20Hz cap.
    # This heuristic is not a robust-stability proof for an unknown plant.
    hz=min(design.maximum_bandwidth_hz,design.delay_phase_budget_rad/
           (2*np.pi*(perturbation.position_delay_s+control_dt/2)))
    wn=2*np.pi*hz;damping_ratio=design.damping_ratio
    records=[];results=[];time_origin=0.;rng=np.random.default_rng(perturbation.seed)
    for li,tr in enumerate(trajectories):
        if tr is None:raise L.LayerError("a refused trajectory cannot execute")
        model=tr.model;lim=tr.limits;M=lim.page_to_stage;Minv=np.linalg.inv(M)
        body=tr.body_origin.copy();xy0=tr.pieces[0].controls[0];q=M@(xy0-body)
        qd=np.zeros(2);current=np.zeros(2);command_acc=np.zeros(2)
        ref=xy0.copy();refv=np.zeros(2);refa=np.zeros(2)
        contact=False;want_lift=True;switch_at=np.inf;brake=False;terminal=None
        attitude=(lim.tilt_deg,0.,0.)
        first=R.Observation(0.,tuple(body),tuple(xy0),0.,0.,"replay-page",attitude_deg=attitude)
        executor=R.CompletionExecutor(plan,tr,first)
        observer=DelayedDisturbanceObserver(model,q,plant_dt,design)
        estimated=observer.states[-1].copy();q_history=[]
        kf=np.asarray(model.force_constant_N_A);actual_kf=kf*perturbation.force_constant_scale
        mass=model.mass_kg*perturbation.mass_scale;k=model.stiffness_N_m*perturbation.stiffness_scale
        c=model.damping_N_s_m*perturbation.damping_scale
        local=[];actual_accs=[];command_accs=[];saturated=0
        n=int(np.ceil((tr.duration+max(.2,lim.lift_delay_s+.04))/plant_dt))+1
        for tick in range(n):
            t=tick*plant_dt;body=tr.body_origin+t*tr.body_velocity
            if t>=switch_at-1e-12:contact=not want_lift;switch_at=np.inf
            xy=body+Minv@q;q_history.append(q.copy())
            if tick%ratio==0:
                acquisition=max(0,tick-delay_ticks)
                measured=q_history[acquisition]+rng.normal(0.,perturbation.position_noise_std_m,2)
                estimated=(observer.correct(measured,acquisition) if tick>=delay_ticks
                           else observer.states[-1].copy())
                if terminal is None:
                    epoch=None if fault and fault[0]=="reference" and t>=fault[1] else "replay-page"
                    obs=R.Observation(t,tuple(body),tuple(body+Minv@estimated[0]),.1 if contact else 0.,
                        perturbation.position_delay_s,epoch,current_A=float(max(abs(current))),attitude_deg=attitude)
                    cmd=executor.tick(obs)
                    if "page_target_m" in cmd:
                        ref=np.array(cmd["page_target_m"]);refv=np.array(cmd["stage_velocity_m_s"])
                        refa=np.array(cmd["stage_acceleration_m_s2"])
                    if cmd["request_lift"]!=want_lift:
                        want_lift=cmd["request_lift"];switch_at=t+(lim.lift_delay_s if want_lift else lim.lower_delay_s)
                    brake=cmd["request_brake"]
                    if cmd["state"] in ("aborted","done"):terminal=t
            else:
                # Propagate from measured applied current between sensor updates.
                estimated=observer.states[-1].copy()
            eq,ev,disturbance=estimated
            if brake:
                speed=np.linalg.norm(ev)
                desired=-ev*min(lim.brake_acceleration_m_s2/max(speed,1e-20),1/control_dt)
            else:
                qref=M@(ref-body)
                desired=refa+wn**2*(qref-eq)+2*damping_ratio*wn*(refv-ev)
            desired*=min(1.,lim.acceleration_m_s2/max(np.linalg.norm(desired),1e-20))
            difference=desired-command_acc
            command_acc+=difference*min(1.,lim.jerk_m_s3*plant_dt/max(np.linalg.norm(difference),1e-20))
            # Estimated disturbance compensation is separate from desired
            # acceleration: rejecting an external drag is not requesting motion.
            disturbance_force=np.clip(-model.mass_kg*disturbance,-design.disturbance_force_cap_N,design.disturbance_force_cap_N)
            def contact_prior(velocity):
                speed=np.linalg.norm(velocity)
                return (design.contact_drag_prior_N*np.tanh(speed/design.contact_velocity_scale_m_s)*velocity/max(speed,1e-20)
                        if contact else np.zeros(2))
            # The accepted path supplies desired motion direction. A fixed
            # nominal drag prior reduces load reversals presented to the slower
            # disturbance observer. The true drag magnitude remains unknown.
            friction_feedforward=contact_prior(refv)
            force=(model.mass_kg*command_acc+model.damping_N_s_m*ev+model.stiffness_N_m*eq+
                   model.bias_force_N+disturbance_force+friction_feedforward)
            requested=force/kf
            desired_current=np.clip(requested,-model.current_limit_A,model.current_limit_A)
            decay=np.exp(-model.resistance_ohm*plant_dt/model.inductance_H)
            requested_voltage=model.resistance_ohm*(desired_current-decay*current)/(1-decay)+kf*ev
            voltage=np.clip(requested_voltage,-model.voltage_limit_V,model.voltage_limit_V)
            saturated+=int(np.any(desired_current!=requested) or np.any(voltage!=requested_voltage))
            new_current=decay*current+(1-decay)*(voltage-actual_kf*qd)/model.resistance_ohm
            new_current=np.clip(new_current,-model.current_limit_A,model.current_limit_A)
            speed=np.linalg.norm(qd)
            drag=perturbation.lateral_drag_N*np.tanh(speed/.0005)*qd/max(speed,1e-20) if contact else np.zeros(2)
            qa=(actual_kf*new_current-c*qd-k*q-model.bias_force_N-drag)/mass
            target,phase=tr.point(min(t,tr.duration))
            local.append([time_origin+t,li,xy[0],xy[1],target[0],target[1],int(contact),int(phase=="ink"),
                q[0],q[1],qd[0],qd[1],new_current[0],new_current[1],voltage[0],voltage[1],
                eq[0],eq[1],ev[0],ev[1],disturbance_force[0],disturbance_force[1]])
            actual_accs.append(qa.copy());command_accs.append(command_acc.copy())
            observer.predict(new_current,contact_prior(ev))
            qd+=qa*plant_dt;q+=qd*plant_dt;current=new_current
            if terminal is not None and t-terminal>=lim.lift_delay_s+.010 and not contact:break
        a=np.asarray(local);records.extend(local)
        active=(a[:,6]>.5)&(a[:,7]>.5)
        error=np.linalg.norm(a[active,2:4]-a[active,4:6],axis=1)
        qerror=np.linalg.norm((a[:,2:4]-a[:,4:6])@M.T,axis=1)
        radial=np.linalg.norm(a[:,8:10],axis=1)
        motion_mask=a[:,0]-time_origin<=tr.duration
        true_tube=bool(radial[motion_mask].max()<=lim.radius_m and qerror[motion_mask].max()<=lim.tracking_reserve_m)
        results.append(dict(letter_index=li,char=plan.letters[li].char,state=executor.state,reason=executor.reason,
            simulated_ink_rms_reference_error_m=float(np.sqrt(np.mean(error**2))) if len(error) else None,
            simulated_ink_max_reference_error_m=float(error.max()) if len(error) else None,
            actual_full_motion_tracking_tube_pass=true_tube,
            peak_actual_stage_tracking_error_m=float(qerror[motion_mask].max()),peak_actual_radius_m=float(radial.max()),
            peak_current_A=float(abs(a[:,12:14]).max()),peak_voltage_V=float(abs(a[:,14:16]).max()),
            peak_actual_acceleration_m_s2=float(np.linalg.norm(actual_accs,axis=1).max()),
            peak_actual_jerk_m_s3=float(np.linalg.norm(np.diff(actual_accs,axis=0),axis=1).max()/plant_dt),
            peak_command_acceleration_m_s2=float(np.linalg.norm(command_accs,axis=1).max()),
            peak_command_jerk_m_s3=float(np.linalg.norm(np.diff(command_accs,axis=0),axis=1).max()/plant_dt),
            peak_estimated_disturbance_force_N=float(abs(a[:,20:22]).max()),capped_observer_updates=observer.capped_updates,
            detected_disturbance_changes=observer.change_detections,
            saturated_driver_steps=saturated,copper_energy_J=float((a[:,12:14]**2).sum()*model.resistance_ohm*plant_dt),
            post_abort_contact_time_s=float(np.sum((a[:,6]>.5)&(a[:,0]>=time_origin+terminal))*plant_dt)
                if executor.state=="aborted" else 0.,
            simulated_time_s=float(a[-1,0]-time_origin),n_samples=len(a)))
        if executor.state!="done":break
        time_origin=float(a[-1,0])+.5
    data=np.asarray(records).reshape(-1,22)
    required_time=sum(p.duration for tr in trajectories for p in tr.pieces if p.phase=="ink")
    contacted_time=float(np.sum((data[:,6]>.5)&(data[:,7]>.5))*plant_dt)
    extra_contact_time=float(np.sum((data[:,6]>.5)&(data[:,7]<.5))*plant_dt)
    required_length=0.
    for tr in trajectories:
        s=tr.sample(plant_dt);mask=s["down"][:-1]&s["down"][1:]
        required_length+=float(np.linalg.norm(np.diff(s["xy"],axis=0),axis=1)[mask].sum())
    report=dict(evidence=__doc__,plan_id=plan.plan_id,accepted_revision=plan.acceptance.rev_id,
        accepted_text=plan.acceptance.after,future_text=plan.text,state=plan.state,
        completed_with_true_tracking_tube=bool(plan.state=="done" and all(l["actual_full_motion_tracking_tube_pass"] for l in results)),
        servo_hz=hz,design=asdict(design),perturbation=asdict(perturbation),plant_dt_s=plant_dt,controller_dt_s=control_dt,
        manual_reposition_assumed_s=.5,fault=fault,letters=results,
        ink_accounting=dict(full_plan_required_ink_duration_s=required_time,
            full_plan_required_ink_length_m_sampled=required_length,
            actual_contact_during_required_phases_s=contacted_time,
            required_phase_contact_fraction=min(1.,contacted_time/required_time),
            extra_contact_outside_required_phases_s=extra_contact_time,
            post_abort_contact_time_s=sum(l["post_abort_contact_time_s"] for l in results),
            discretization="Contact durations use 0.5ms samples; length sums only adjacent ink samples. Full-plan denominators include unexecuted letters."),
        trace_columns=["time_s","letter_index","simulated_ink_x_m","simulated_ink_y_m","target_x_m","target_y_m",
            "contact","target_down","q_x_m","q_y_m","qdot_x_m_s","qdot_y_m_s","current_x_A","current_y_A",
            "voltage_x_V","voltage_y_V","estimated_q_x_m","estimated_q_y_m","estimated_qdot_x_m_s","estimated_qdot_y_m_s",
            "estimated_compensation_x_N","estimated_compensation_y_N"],
        limitations=["generic planar stage only; not a concrete Rev K or five-bar validation",
            "exact anchored body position and rigid known attitude","ideal timestamp and measured-current access",
            "filter covariance assumptions do not prove estimation error bounds","observer force cap is a design assumption",
            "retrospective true tracking-tube check is evaluation only, never a controller input",
            "reference jerk limits do not guarantee actual jerk under unknown friction or force mismatch"])
    return report,data
