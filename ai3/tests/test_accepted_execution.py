"""Acceptance-to-command integration and causal sensing failure boundaries."""
from dataclasses import replace
import copy

import numpy as np
import pytest

from ai3 import accepted_completion as A
from ai3 import coarse_fine as F
from ai3 import completion_replay as C
from ai3 import export_grounded_completion as G
from ai3 import layers as L
from ai3 import reachable as R


def example(lift=.020):
    # Analytic small line strokes, explicitly synthetic rather than a corpus.
    bank={c:[np.array([[0.,0.],[.3,.1]])] for c in "abc"}
    rev=L.Revision(0,0,"a","abc","completion","writer","writer","accepted in unit test",0.)
    lim=replace(R.MotionLimits(),radius_m=.003,hard_stop_m=.0032,lift_delay_s=lift,lower_delay_s=lift)
    return A.plan_from_acceptance(rev,bank,limits=lim)


def test_arbitrary_accepted_suffix_has_exact_binding_and_completes():
    plan,trs,report=example()
    assert plan.text=="bc" and report["future_text"]=="bc"
    assert all(tr.accepted_plan_id==plan.plan_id and tr.letter_index==i for i,tr in enumerate(trs))
    result,trace=C.replay(plan,trs)
    assert result["state"]=="done" and len(result["letters"])==2
    assert trace.shape[1]==len(result["trace_columns"])
    assert max(l["peak_command_jerk_m_s3"] for l in result["letters"])<=300*(1+1e-10)


def test_preflight_refuses_whole_text_atomically():
    bank={"b":[np.array([[0.,0.],[100.,100.]])]}
    rev=L.Revision(0,0,"a","ab","completion","writer","writer","accepted",0.)
    plan,trs,report=A.plan_from_acceptance(rev,bank)
    assert plan is None and trs==[None] and not report["ready_for_fresh_measured_admission"]


def test_reference_loss_stops_future_letters_and_retains_contact_tail():
    plan,trs,_=example(lift=.200)
    result,trace=C.replay(plan,trs,fault=("reference",.230))
    assert result["state"]=="handed_back" and len(result["letters"])==1
    assert result["letters"][0]["reason"]=="page_reference_lost"
    assert np.any((trace[:,0]>.230)&(trace[:,6]>.5))  # lifting is not instantaneous
    assert trace[-1,6]==0


def test_delayed_position_is_causal_and_not_true_velocity():
    plan,trs,_=example()
    perturb=C.Perturbation(position_delay_s=.002,causal_position_feedback=True)
    result,trace=C.replay(plan,trs,servo_hz=20.,perturbation=perturb)
    # Position reported at each 2ms control tick equals the true position 2ms
    # earlier. The held velocity channel is an observer, not hidden plant truth.
    first=trace[trace[:,1]==0]
    for k in range(4,len(first),4):
        np.testing.assert_allclose(first[k,16:18],first[k-4,8:10],atol=1e-12)
    assert np.max(abs(first[:,18:20]-first[:,10:12]))>1e-6
    assert "causal" in result["sensing"]


def test_coarse_fine_export_and_word_join_preserve_physical_decomposition():
    _,trs,_=example(lift=.200)
    samples=[F.export(t,F.CoarseStage(),1.25,None) for t in trs]
    word=G.join_word(samples,np.zeros(2),trs[0].limits,trs[0].model)
    Ainv=np.linalg.inv(trs[0].limits.page_to_stage)
    np.testing.assert_allclose(word["xy"],word["coarse_offset_page_m"]+word["q"]@Ainv.T,atol=1e-14)
    np.testing.assert_allclose(word["absolute_nib_acceleration_page_m_s2"],
        word["coarse_acceleration_m_s2"]+word["q_acceleration_m_s2"]@Ainv.T,atol=1e-12)
    assert np.all(np.diff(word["t"])>0)
    assert np.all(~word["down"][word["letter_index"]==-1])
    moving=copy.deepcopy(trs[0]);moving.body_velocity=np.array([.001,0.])
    with pytest.raises(ValueError,match="stationary"):
        F.assess(moving)
