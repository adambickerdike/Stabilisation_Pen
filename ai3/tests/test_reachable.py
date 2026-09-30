"""Continuous motion contracts and failure paths, independent of a learned recognizer."""
from dataclasses import replace

import numpy as np
import pytest

from ai3 import layers as L
from ai3 import reachable as R


@pytest.fixture(scope="module")
def line():
    pts=np.array([[0.,0.],[2e-3,0.]])
    limits=R.MotionLimits(radius_m=3e-3,hard_stop_m=3.2e-3)
    trajectory,diagnostic=R.plan_letter([pts],[1e-3,0.],limits=limits)
    assert trajectory is not None
    return pts,trajectory,diagnostic


def _accepted(pts):
    tr=L.Transcript()
    tr.add_word("a",[1.],[0])
    rev=tr.accept(L.Suggestion(0,"completion","predictor","ab",.9,"chosen by writer"))
    return L.WritingPlan(rev,[L.PlanLetter("b",[pts])],{"reach":True,"tracking":True})


def _executor(line):
    pts,_,_=line
    plan=_accepted(pts)
    traj,_=R.admit_accepted_letter(plan,0,[1e-3,0.],limits=R.MotionLimits(radius_m=3e-3,hard_stop_m=3.2e-3))
    first=R.Observation(0.,(1e-3,0.),tuple(pts[0]),0.,.001,"page-1",attitude_deg=(traj.limits.tilt_deg,0.,0.))
    return plan,traj,R.CompletionExecutor(plan,traj,first),first


def _obs(traj,t):
    xy,phase=traj.point(min(t,traj.duration))
    body=traj.body_origin+t*traj.body_velocity
    return R.Observation(t,tuple(body),tuple(xy),.1 if phase=="ink" else 0.,.001,"page-1",attitude_deg=(traj.limits.tilt_deg,0.,0.))


def test_straight_line_is_analytic_minimum_jerk(line):
    _,tr,_=line
    ink=[p for p in tr.pieces if p.phase=="ink"]
    duration=sum(p.duration for p in ink)
    elapsed=0.
    # Compare against a separately evaluated closed-form minimum-jerk line.
    for piece in ink:
        u=np.linspace(0,1,19)
        s=(elapsed+u*piece.duration)/duration
        expected=2e-3*(10*s**3-15*s**4+6*s**5)
        xy=R._evaluate(piece.controls,u)
        assert np.max(abs(xy[:,0]-expected))<1e-13
        assert np.max(abs(xy[:,1]))<1e-15
        elapsed+=piece.duration
    assert tr.geometry_bound_m<1e-12


def test_all_continuous_bounds_dominate_dense_derivative_checks(line):
    _,tr,diag=line
    assert any(d["failures"] for d in diag["trials"][:-1])
    start=0.
    for piece in tr.pieces:
        u=np.linspace(0,1,401)
        body=tr.body_origin+(start+np.linspace(0,piece.duration,6))[:,None]*tr.body_velocity
        q=(piece.controls-body)@tr.limits.page_to_stage.T
        assert np.linalg.norm(R._evaluate(q,u),axis=1).max()<=tr.bounds["radial_m"]+1e-12
        for order,key in [(1,"speed_m_s"),(2,"acceleration_m_s2"),(3,"jerk_m_s3")]:
            dense=R._evaluate(R._derivative(q,piece.duration,order),u)
            assert np.linalg.norm(dense,axis=1).max()<=tr.bounds[key]+1e-8
        start+=piece.duration
    for key,limit in tr.bounds["thresholds"].items():
        assert tr.bounds[key]<=limit


def test_geometry_bound_dominates_dense_polyline_distance():
    p=np.array([[0.,0.],[.0008,.0012],[.0018,.0009],[.002,0.]])
    pieces,bound,_=R._stroke_curve(p)
    points=np.vstack([R._evaluate(b,np.linspace(0,1,101)) for b,_ in pieces])
    a=p[:-1];d=np.diff(p,axis=0)
    u=np.clip(((points[:,None,:]-a)*d).sum(-1)/(d*d).sum(-1),0,1)
    distances=np.linalg.norm(points[:,None,:]-(a+u[:,:,None]*d),axis=2).min(1)
    assert distances.max()<=bound+1e-10


def test_radial_workspace_rejects_square_corner():
    pts=np.array([[.00095,.00095],[.000951,.00095]])
    tr,diag=R.plan_letter([pts],[0.,0.],duration_scales=[1.,2.])
    assert tr is None and "radial_with_reserve_m" in diag["last_bounds"]["failures"]


def test_air_moves_are_bound_and_cannot_bypass_reach():
    strokes=[np.array([[0.,0.],[.1e-3,0.]]),np.array([[5e-3,0.],[5.1e-3,0.]])]
    tr,diag=R.plan_letter(strokes,[0.,0.],duration_scales=[1.,2.])
    assert tr is None and "radial_with_reserve_m" in diag["last_bounds"]["failures"]


def test_predicted_body_uncertainty_is_charged_against_reach(line):
    pts,tr,_=line
    lim=replace(tr.limits,velocity_error_m_s=.05)
    candidate,diag=R.plan_letter([pts],[1e-3,0.],limits=lim,duration_scales=[2.,4.])
    assert candidate is None and "radial_with_reserve_m" in diag["last_bounds"]["failures"]


def test_force_and_voltage_limits_reject_before_any_ink(line):
    pts,tr,_=line
    candidate,diag=R.plan_letter([pts],[1e-3,0.],limits=tr.limits,
                                model=replace(tr.model,current_limit_A=.001,voltage_limit_V=.01),duration_scales=[3.])
    assert candidate is None and {"current_A","voltage_V"}<=set(diag["last_bounds"]["failures"])


def test_voltage_includes_uncertain_back_emf():
    # With zero nominal motion and no mechanical load terms, R*I and L*di
    # vanish. The remaining uncertainty must still reserve Kf*delta_velocity.
    model=R.StageModel(mass_kg=0.,stiffness_N_m=0.,damping_N_s_m=0.,bias_force_N=(0.,0.),
                       load_uncertainty_N=0.,load_slew_uncertainty_N_s=0.,force_constant_N_A=(1.,2.))
    lim=R.MotionLimits(velocity_error_m_s=.002,acceleration_error_m_s2=.001,jerk_error_m_s3=0.)
    tr=R.LetterTrajectory([R.Piece(np.zeros((6,2)),.1,"lower")],np.zeros(2),np.zeros(2),lim,model,0.)
    assert R.certify(tr)["voltage_V"]==pytest.approx(2*(.002+.001*.1))


def test_exported_derivatives_match_analytic_commands(line):
    _,tr,_=line
    data=tr.sample(.001)
    for i in range(0,len(data["t"]),17):
        v,a=tr.derivatives(float(data["t"][i]))
        np.testing.assert_allclose(data["q_velocity_m_s"][i],tr.limits.page_to_stage@(v-tr.body_velocity),atol=1e-11)
        np.testing.assert_allclose(data["q_acceleration_m_s2"][i],tr.limits.page_to_stage@a,atol=1e-9)


@pytest.mark.parametrize("v,a",[(.03,2.),(.001,0.),(.005,.8)])
def test_stop_reserve_matches_independent_jerk_limited_integration(v,a):
    J=300.;B=1.;delay=.004
    bound=float(R.stopping_distance(v,a,B,J,delay))
    after=v+a*delay;peak=min(B,np.sqrt(J*after+a*a/2))
    t1=(a+peak)/J
    v1=after+a*t1-.5*J*t1*t1
    hold=max(0.,(v1-peak*peak/(2*J))/max(peak,1e-20))
    # Independent trapezoidal quadrature of acceleration then velocity.
    duration=delay+t1+hold+peak/J
    t=np.linspace(0,duration,200001)
    ac=np.where(t<=delay,a,np.where(t<=delay+t1,a-J*(t-delay),
        np.where(t<=delay+t1+hold,-peak,-peak+J*(t-delay-t1-hold))))
    h=t[1]-t[0]
    vel=np.r_[v,v+np.cumsum((ac[:-1]+ac[1:])*.5*h)]
    distance=np.trapezoid(vel,t)
    assert abs(vel[-1])<1e-8
    assert bound==pytest.approx(distance,abs=1e-9)
    assert bound>v*delay+v*v/(2*B)


def test_executor_completes_only_accepted_future_ink(line):
    plan,tr,ex,_=_executor(line)
    commands=[ex.tick(_obs(tr,float(t))) for t in np.linspace(0,tr.duration,int(np.ceil(tr.duration/.002))+1)]
    assert ex.state=="done" and plan.state=="done"
    assert any(c.get("may_deposit_ink") for c in commands)
    assert all(not c.get("may_deposit_ink",False) for c in commands if c.get("phase") in ("air","lift","lower"))


@pytest.mark.parametrize("change,reason",[
    ({"page_epoch":None},"page_reference_lost"),
    ({"page_epoch":"new-page"},"page_reference_lost"),
    ({"reference_valid":False},"page_reference_lost"),
    ({"attitude_deg":None},"attitude_unavailable"),
    ({"attitude_deg":(51.,0.,0.)},"attitude_changed"),
    ({"attitude_deg":(50.,1.,0.)},"attitude_changed"),
    ({"attitude_deg":(50.,0.,1.)},"attitude_changed"),
    ({"sensor_age_s":.007},"stale_sensor"),
    ({"current_A":.8},"actuator_limit"),
    ({"force_N":.5},"contact_force_limit"),
    ({"body_xy":(.0012,0.)},"body_prediction_exceeded"),
    ({"tip_xy":(.0004,0.)},"tracking_error"),
    ({"tip_xy":(float("nan"),0.)},"invalid_observation"),
])
def test_executor_fail_closed_including_page_relocalization(line,change,reason):
    plan,tr,ex,_=_executor(line)
    cmd=ex.tick(replace(_obs(tr,.002),**change))
    assert cmd["state"]=="aborted" and cmd["reason"]==reason
    assert cmd["request_lift"] and cmd["request_brake"]
    assert plan.state=="handed_back"
    assert ex.tick(_obs(tr,.004))["state"]=="aborted"  # no resume from ambiguous relative counts


def test_contact_loss_and_late_tick_abort(line):
    plan,tr,ex,_=_executor(line)
    for t in np.arange(0,.024,.002):
        obs=_obs(tr,float(t))
        if tr.point(float(t))[1]=="ink":
            cmd=ex.tick(replace(obs,force_N=0.))
            assert cmd["reason"]=="contact_lost"
            break
        ex.tick(obs)
    _,tr,ex,_=_executor(line)
    assert ex.tick(_obs(tr,.01))["reason"]=="control_deadline_missed"


def test_cancelled_plan_cannot_finish_and_modified_trajectory_cannot_arm(line):
    plan,tr,ex,_=_executor(line)
    plan.cancel("writer stopped")
    assert ex.tick(_obs(tr,.002))["reason"]=="writer_cancelled"
    with pytest.raises(L.LayerError):
        plan.finish_letter(0)
    pts,_,_=line
    plan=_accepted(pts)
    trajectory,_=R.admit_accepted_letter(plan,0,[1e-3,0.],limits=tr.limits)
    trajectory.pieces[0].controls[0,0]+=.001
    with pytest.raises(L.LayerError,match="changed"):
        R.CompletionExecutor(plan,trajectory,R.Observation(0.,(.001,0.),(0.,0.),0.,.001,"page-1"))


def test_writing_plan_does_not_accept_wrong_text_or_empty_gates(line):
    pts,_,_=line
    tr=L.Transcript();tr.add_word("a",[1.],[0])
    rev=tr.accept(L.Suggestion(0,"completion","predictor","ab",1.,"accepted"))
    with pytest.raises(L.LayerError):
        L.WritingPlan(rev,[L.PlanLetter("b",[pts])],{})
    with pytest.raises(L.LayerError):
        L.WritingPlan(rev,[L.PlanLetter("x",[pts])],{"reach":True,"tracking":True})
    plan=L.WritingPlan(rev,[L.PlanLetter("b",[pts])],{"reach":True,"tracking":True})
    pts2=plan.letters[0].strokes[0]
    pts2.setflags(write=True);pts2[0,0]=9.
    assert plan.letters[0].strokes[0][0,0]==0.
    with pytest.raises(L.LayerError):
        plan.finish_letter(0)


def test_ink_audit_covers_metadata_and_rejects_nonphysical_timestamps():
    rec=L.StrokeRecord();rec.append([(0.,0.,0.),(.1,0.,.001)])
    rec._entries[0]=replace(rec._entries[0],t0=2.)
    assert not rec.verify()
    for pts in [[],[(.1,0.,0.),(0.,0.,0.)],[(0.,float("nan"),0.)]]:
        with pytest.raises(L.LayerError):
            L.StrokeRecord().append(pts)


def test_protected_words_also_block_recognition_autocorrection():
    tr=L.Transcript(auto_correct=True)
    tr.add_word("Linn",[.8]*4,[0],protected=True)
    assert not tr.propose(L.Suggestion(0,"recognition","recogniser","Line",.99,"model"))
    assert tr.text()=="Linn"
