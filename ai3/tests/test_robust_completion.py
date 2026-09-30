"""Observer causality, model uncertainty, force limits and full-ink denominators."""
from dataclasses import replace

import numpy as np
import pytest

from ai3 import accepted_completion as A
from ai3 import completion_replay as C
from ai3 import layers as L
from ai3 import reachable as R
from ai3 import robust_completion as B


def observer_stream(positions,currents):
    obs=B.DelayedDisturbanceObserver(R.StageModel(),[0.,0.],.0005)
    outputs=[]
    for i in range(len(positions)):
        if i>=4 and i%4==0:
            estimate=obs.correct(positions[i-4],i-4)
        else:estimate=obs.states[-1].copy()
        outputs.append(estimate)
        obs.predict(currents[i])
    return np.array(outputs),obs


def test_future_measurements_and_currents_cannot_change_output_prefix():
    rng=np.random.default_rng(4323)
    positions=rng.normal(0.,5e-6,(400,2));currents=rng.normal(0.,.005,(400,2))
    a,_=observer_stream(positions,currents)
    positions[201:]+=rng.normal(0.,.01,(199,2));currents[201:]+=.4
    b,obs=observer_stream(positions,currents)
    np.testing.assert_array_equal(a[:202],b[:202])
    assert np.max(abs(a[230:]-b[230:]))>1e-4
    with pytest.raises(ValueError,match="causal history"):
        obs.correct([0.,0.],1000)


@pytest.mark.parametrize("mass_scale,force_scale",[(.7,1.),(1.3,.7)])
def test_observer_tracks_independent_forced_plant_with_wrong_mass_and_force(mass_scale,force_scale):
    # No glyph and no target-dependent tuning: a forced 2-axis spring/mass with
    # known current samples and delayed noisy positions only.
    model=R.StageModel();dt=.0005;q=np.zeros(2);v=np.zeros(2);history=[];estimates=[]
    observer=B.DelayedDisturbanceObserver(model,q,dt);rng=np.random.default_rng(592)
    kf=np.array(model.force_constant_N_A)
    for i in range(3000):
        t=i*dt;history.append(q.copy())
        if i>=4 and i%4==0:
            estimate=observer.correct(history[i-4]+rng.normal(0.,5e-6,2),i-4)
        else:estimate=observer.states[-1].copy()
        estimates.append(estimate[0])
        current=np.array(model.bias_force_N)/kf+np.array([.004*np.sin(2*np.pi*2*t),.003*np.cos(2*np.pi*3*t)])
        acceleration=(force_scale*kf*current-model.bias_force_N-model.damping_N_s_m*v-model.stiffness_N_m*q)/(mass_scale*model.mass_kg)
        v+=dt*acceleration;q+=dt*v;observer.predict(current)
    error=np.linalg.norm(np.asarray(estimates)[100:]-np.asarray(history)[100:],axis=1)
    assert np.quantile(error,.99)<40e-6
    assert all(np.linalg.eigvalsh(p).min()>-1e-14 for p in observer.covariances)
    assert max(abs(s[2]).max()*model.mass_kg for s in observer.states)<=B.ObserverDesign().disturbance_force_cap_N


def accepted_line_pair():
    bank={c:[np.array([[0.,0.],[.3,.1]])] for c in "bc"}
    acceptance=L.Revision(0,0,"a","abc","completion","writer","writer","unit-test accepted geometry",0.)
    limits=replace(R.MotionLimits(),radius_m=.003,hard_stop_m=.0032,lift_delay_s=.2,lower_delay_s=.2)
    return A.plan_from_acceptance(acceptance,bank,limits=limits)[:2]


def test_recovery_force_limits_and_delayed_sensing_on_accepted_plan():
    plan,trs=accepted_line_pair()
    report,trace=B.replay(plan,trs,perturbation=C.Perturbation(position_delay_s=.002,position_noise_std_m=5e-6))
    design=B.ObserverDesign()
    assert trace.shape[1]==len(report["trace_columns"])
    assert max(l["peak_recovery_force_N"] for l in report["letters"])<=design.recovery_force_cap_N*(1+1e-10)
    assert max(l["peak_recovery_force_slew_N_s"] for l in report["letters"])<=design.recovery_force_slew_N_s*(1+1e-10)
    assert report["ink_accounting"]["full_plan_required_ink_duration_s"]==pytest.approx(sum(p.duration for t in trs for p in t.pieces if p.phase=="ink"))
    if report["state"]=="done":
        assert report["completed_with_true_tracking_tube"]


def test_fault_ink_accounting_keeps_unexecuted_letters_in_denominator():
    plan,trs=accepted_line_pair()
    report,trace=B.replay(plan,trs,fault=("reference",.230))
    account=report["ink_accounting"]
    assert len(report["letters"])==1 and not report["completed_with_true_tracking_tube"]
    assert account["full_plan_required_ink_duration_s"]>sum(p.duration for p in trs[0].pieces if p.phase=="ink")
    assert 0<account["required_phase_contact_fraction"]<1
    assert account["post_abort_contact_time_s"]>=.19
