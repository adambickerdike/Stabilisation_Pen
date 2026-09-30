"""A declared lumped plant for accepted-command integration checks.

SIMULATION ONLY. Constant-pose two-axis translation, anchored page/body sensing,
linear mechanics and motor electrical dynamics, delayed binary contact, and a
PD position loop. Optional fixed plant mismatch and causal noisy/delayed position
feedback are sensitivity experiments. No human response, flexible modes,
magnetic spatial map or recognizer. These are integration traces, not predictions
of handwriting benefit or proof of the proposed hardware.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from . import layers as L
from . import reachable as R


@dataclass(frozen=True)
class Perturbation:
    mass_scale:float=1.
    stiffness_scale:float=1.
    damping_scale:float=1.
    force_constant_scale:float=1.
    position_delay_s:float=0.
    position_noise_std_m:float=0.
    causal_position_feedback:bool=False
    velocity_filter_hz:float=80.       # fixed before sensitivity cases, no tuning
    lateral_drag_N:float=0.           # stage-plane friction magnitude while contact
    seed:int=812

    def __post_init__(self):
        positive=[self.mass_scale,self.stiffness_scale,self.damping_scale,
                  self.force_constant_scale,self.velocity_filter_hz]
        nonnegative=[self.position_delay_s,self.position_noise_std_m,self.lateral_drag_N]
        if not np.isfinite(positive+nonnegative).all() or min(positive)<=0 or min(nonnegative)<0:
            raise ValueError("finite positive scales and nonnegative disturbances required")


def replay(plan:L.WritingPlan,trajectories, *,servo_hz:float=40.,damping_ratio:float=.85,
           plant_dt:float=.0005,control_dt:float=.002,fault:tuple|None=None,feedforward:bool=True,
           perturbation:Perturbation=Perturbation()):
    if servo_hz<=0 or damping_ratio<=0 or not 0<plant_dt<=control_dt:
        raise ValueError("invalid simulation rates")
    ratio=round(control_dt/plant_dt)
    if abs(ratio*plant_dt-control_dt)>1e-12:
        raise ValueError("controller interval must be an integer multiple of plant dt")
    records=[];letter_results=[];time_origin=0.;rng=np.random.default_rng(perturbation.seed)
    sensed=(perturbation.causal_position_feedback or perturbation.position_delay_s>0 or
            perturbation.position_noise_std_m>0)
    for li,tr in enumerate(trajectories):
        if tr is None:
            raise L.LayerError("a refused trajectory cannot execute")
        model=tr.model;lim=tr.limits;M=lim.page_to_stage;Minv=np.linalg.inv(M)
        body=tr.body_origin.copy();xy0=tr.pieces[0].controls[0]
        q=M@(xy0-body);qd=np.zeros(2);current=np.zeros(2)
        ref=xy0.copy();ref_velocity=np.zeros(2);ref_acceleration=np.zeros(2)
        contact=False;want_lift=True;switch_at=np.inf
        request_brake=False;terminal_t=None
        attitude=(lim.tilt_deg,0.,0.)
        first=R.Observation(0.,tuple(body),tuple(xy0),0.,0.,"replay-page",attitude_deg=attitude)
        executor=R.CompletionExecutor(plan,tr,first)
        wn=2*np.pi*servo_hz;kf=np.asarray(model.force_constant_N_A)
        actual_kf=kf*perturbation.force_constant_scale
        mass=model.mass_kg*perturbation.mass_scale
        spring=model.stiffness_N_m*perturbation.stiffness_scale
        damping=model.damping_N_s_m*perturbation.damping_scale
        q_history=[];observed_q=q.copy();observed_qd=np.zeros(2);previous_q=q.copy()
        alpha=1-np.exp(-2*np.pi*perturbation.velocity_filter_hz*control_dt)
        local=[];commands=[];last_cmd={"state":"armed"};command_acc=np.zeros(2)
        actual_accelerations=[];command_accelerations=[]
        max_ticks=int(np.ceil((tr.duration+max(.2,lim.lift_delay_s+.04))/plant_dt))+1
        for k in range(max_ticks):
            t=k*plant_dt
            body=tr.body_origin+t*tr.body_velocity
            if t>=switch_at-1e-12:
                contact=not want_lift;switch_at=np.inf
            xy=body+Minv@q
            q_history.append(q.copy())
            if sensed and k%ratio==0:
                # A causal position-only encoder, sampled at the controller
                # rate. The controller never receives true qdot in this mode.
                fractional=max(0.,(t-perturbation.position_delay_s)/plant_dt)
                lower=min(k,int(np.floor(fractional)));upper=min(k,lower+1)
                blend=fractional-lower
                observed_q=(1-blend)*q_history[lower]+blend*q_history[upper]
                observed_q+=rng.normal(0.,perturbation.position_noise_std_m,2)
                raw_velocity=(observed_q-previous_q)/control_dt if k else np.zeros(2)
                observed_qd=(1-alpha)*observed_qd+alpha*raw_velocity
                previous_q=observed_q.copy()
            elif not sensed:
                observed_q=q.copy();observed_qd=qd.copy()
            if k%ratio==0 and terminal_t is None:
                epoch=None if fault and fault[0]=="reference" and t>=fault[1] else "replay-page"
                measured_force=.1 if contact else 0.
                observed_xy=body+Minv@observed_q
                obs=R.Observation(t,tuple(body),tuple(observed_xy),measured_force,
                                  perturbation.position_delay_s,epoch,
                                  current_A=float(np.max(np.abs(current))),attitude_deg=attitude)
                last_cmd=executor.tick(obs);commands.append(last_cmd)
                if "page_target_m" in last_cmd:
                    ref=np.array(last_cmd["page_target_m"])
                    ref_velocity=np.array(last_cmd["stage_velocity_m_s"])
                    ref_acceleration=np.array(last_cmd["stage_acceleration_m_s2"])
                requested=last_cmd["request_lift"]
                if requested!=want_lift:
                    want_lift=requested;switch_at=t+(lim.lift_delay_s if requested else lim.lower_delay_s)
                request_brake=last_cmd["request_brake"]
                if last_cmd["state"] in ("aborted","done"):
                    terminal_t=t
            if request_brake:
                speed=np.linalg.norm(observed_qd)
                desired_acc=-observed_qd*min(lim.brake_acceleration_m_s2/max(speed,1e-20),1/control_dt)
            else:
                qref=M@(ref-body)
                desired_acc=wn**2*(qref-observed_q)-2*damping_ratio*wn*(observed_qd+M@tr.body_velocity)
                if feedforward:
                    desired_acc+=ref_acceleration+2*damping_ratio*wn*(ref_velocity+M@tr.body_velocity)
            desired_acc*=min(1.,lim.acceleration_m_s2/max(np.linalg.norm(desired_acc),1e-20))
            change=desired_acc-command_acc
            command_acc+=change*min(1.,lim.jerk_m_s3*plant_dt/max(np.linalg.norm(change),1e-20))
            desired_acc=command_acc.copy()
            force=(model.mass_kg*desired_acc+model.damping_N_s_m*observed_qd+
                   model.stiffness_N_m*observed_q+model.bias_force_N)
            desired_current=np.clip(force/kf,-model.current_limit_A,model.current_limit_A)
            decay=np.exp(-model.resistance_ohm*plant_dt/model.inductance_H)
            # Exact R-L update with constant voltage/back-EMF within one plant step.
            voltage=model.resistance_ohm*(desired_current-decay*current)/(1-decay)+kf*observed_qd
            voltage=np.clip(voltage,-model.voltage_limit_V,model.voltage_limit_V)
            new_current=decay*current+(1-decay)*(voltage-actual_kf*qd)/model.resistance_ohm
            new_current=np.clip(new_current,-model.current_limit_A,model.current_limit_A)
            speed=np.linalg.norm(qd)
            drag=perturbation.lateral_drag_N*np.tanh(speed/.0005)*qd/max(speed,1e-20) if contact else np.zeros(2)
            qa=(actual_kf*new_current-damping*qd-spring*q-model.bias_force_N-drag)/mass
            actual_accelerations.append(qa.copy());command_accelerations.append(command_acc.copy())
            target,phase=tr.point(min(t,tr.duration))
            local.append([time_origin+t,li,xy[0],xy[1],target[0],target[1],int(contact),int(phase=="ink"),
                          q[0],q[1],qd[0],qd[1],new_current[0],new_current[1],voltage[0],voltage[1],
                          observed_q[0],observed_q[1],observed_qd[0],observed_qd[1]])
            qd+=qa*plant_dt;q+=qd*plant_dt;current=new_current
            if terminal_t is not None and t-terminal_t>=lim.lift_delay_s+.010 and not contact:
                break
        a=np.array(local);records.extend(local)
        in_motion=(a[:,6]>.5)&(a[:,7]>.5)
        errors=np.linalg.norm(a[in_motion,2:4]-a[in_motion,4:6],axis=1)
        letter_results.append({"letter_index":li,"char":plan.letters[li].char,"state":executor.state,
                               "reason":executor.reason,"simulated_ink_rms_reference_error_m":float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
                               "simulated_ink_max_reference_error_m":float(errors.max()) if len(errors) else None,
                               "peak_current_A":float(np.max(abs(a[:,12:14]))),"peak_voltage_V":float(np.max(abs(a[:,14:16]))),
                               "copper_energy_J":float((a[:,12:14]**2).sum()*model.resistance_ohm*plant_dt),
                               "peak_actual_acceleration_m_s2":float(np.linalg.norm(actual_accelerations,axis=1).max()),
                               "peak_actual_jerk_m_s3":float(np.linalg.norm(np.diff(actual_accelerations,axis=0),axis=1).max()/plant_dt),
                               "peak_command_acceleration_m_s2":float(np.linalg.norm(command_accelerations,axis=1).max()),
                               "peak_command_jerk_m_s3":float(np.linalg.norm(np.diff(command_accelerations,axis=0),axis=1).max()/plant_dt),
                               "simulated_time_s":float(a[-1,0]-time_origin),"n_samples":len(a)})
        if executor.state!="done":
            break
        # Explicitly unmodelled manual reposition while the pen is up. Time is
        # accounted as a declared .5 s assumption; no ink is generated by it.
        time_origin=float(a[-1,0])+.5
    data=np.array(records).reshape(-1,20)
    report={"evidence":"SIMULATION: generic planar stage, real glyph shape only; no hardware or human validation",
            "plan_id":plan.plan_id,"accepted_revision":plan.acceptance.rev_id,"accepted_text":plan.acceptance.after,
            "future_text":plan.text,"state":plan.state,"servo_hz":servo_hz,"damping_ratio":damping_ratio,
            "accepted_path_feedforward":feedforward,
            "command_limits":"Acceleration vector <=2m/s² and vector slew <=300m/s³; true acceleration can violate these under unmodelled loads or plant mismatch. Certificate stopping reserve requires demonstrated plant authority, not merely command clipping.",
            "perturbation":asdict(perturbation),
            "sensing":"causal delayed/noisy position; fixed 80Hz filtered finite-difference velocity" if sensed else "ideal true position and velocity",
            "plant_dt_s":plant_dt,"controller_dt_s":control_dt,"manual_reposition_assumed_s":.5,
            "fault":fault,"letters":letter_results,
            "trace_columns":["time_s","letter_index","simulated_ink_x_m","simulated_ink_y_m","target_x_m","target_y_m",
                             "contact","target_down","q_x_m","q_y_m","qdot_x_m_s","qdot_y_m_s","current_x_A","current_y_A","voltage_x_V","voltage_y_V",
                             "observed_q_x_m","observed_q_y_m","observed_qdot_x_m_s","observed_qdot_y_m_s"],
            "omissions":["page/body drift and attitude uncertainty","measured nonlinear paper friction","flexible modes","spatial magnetic map",
                         "real hand response","thermal dynamics","ink deposition characteristics","recognition and intention inference"]}
    return report,data
