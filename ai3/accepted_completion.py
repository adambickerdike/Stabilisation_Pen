"""Create a reviewable future-ink plan for text explicitly accepted by a writer.

Example (uses the public UJI calibration letter bank; no motor is actuated):
 python -m ai3.accepted_completion --accepted-text because --written-prefix becau \
   --writer tst_UJI_W12 --radius-mm 3 --out results/improvement/writing/completion

Coordinates are relative to the supplied page origin. A real app must obtain
the acceptance and page anchor from the writer, and feed actual fresh body/tip
observations into CompletionExecutor. Proposed body locations are reposition
requests, not predictions that a person or internal reaction mass can follow.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

import numpy as np

from . import data as D
from . import layers as L
from . import online as O
from . import reachable as R


def plan_from_acceptance(acceptance:L.Revision,bank:dict, *,xheight_m:float=.003,
                         origin_m=(0.,0.),limits:R.MotionLimits=R.MotionLimits()):
    """An arbitrary accepted suffix/rewrite, using given normalized glyph strokes.

    No completion model supplies the acceptance. Missing or unreachable glyphs
    remain queued and require a changed plan explicitly accepted by the writer.
    The whole word preflight is atomic: any refused letter makes ready=False.
    """
    if acceptance.accepted_by!="writer" or acceptance.kind not in ("completion","spelling","writer_edit"):
        raise L.LayerError("future ink requires an explicit writer acceptance")
    if acceptance.kind=="completion":
        if not acceptance.after.startswith(acceptance.before):
            raise L.LayerError("completion cannot change previously deposited ink; accept a separate rewrite")
        text=acceptance.after[len(acceptance.before):]
    else:
        text=acceptance.after
    if not text or any(c not in bank for c in text):
        raise L.LayerError("accepted text is empty or a glyph is unavailable")
    if not np.isfinite(xheight_m) or xheight_m<=0:
        raise ValueError("x-height must be finite and positive")
    origin=np.asarray(origin_m,float)
    if origin.shape!=(2,) or not np.isfinite(origin).all():
        raise ValueError("page origin must be a finite two-vector")
    letters=[];x=float(origin[0])
    for char in text:
        strokes=bank[char]
        pts=np.vstack(strokes)
        base=np.array([pts[:,0].min(),np.percentile(pts[:,1],5)])
        placed=[(np.asarray(s)-base)*xheight_m+np.array([x,origin[1]]) for s in strokes]
        letters.append(L.PlanLetter(char,placed))
        x+=(np.ptp(pts[:,0])+.25)*xheight_m
    preflight=[];trajectories=[]
    for k,letter in enumerate(letters):
        pts=np.vstack(letter.strokes)
        body=(pts.min(0)+pts.max(0))/2
        trajectory,diag=R.plan_letter(letter.strokes,body,limits=limits)
        preflight.append({"letter_index":k,"char":letter.char,"proposed_body_position_m":body.tolist(),
                          "admitted_at_proposed_position":trajectory is not None,"reason":diag["reason"],
                          "bounds":trajectory.bounds if trajectory else diag.get("last_bounds"),
                          "geometry_bound_m":trajectory.geometry_bound_m if trajectory else diag.get("geometry_bound_m")})
        trajectories.append(trajectory)
    ready=all(t is not None for t in trajectories)
    plan=L.WritingPlan(acceptance,letters,{"reach":True,"tracking":True}) if ready else None
    if plan is not None:
        for k,trajectory in enumerate(trajectories):
            trajectory.accepted_plan_id=plan.plan_id
            trajectory.letter_index=k
    report={"evidence":"CALCULATION: offline accepted-geometry preflight, proposed body repositioning; no physical execution",
            "plan_id":plan.plan_id if plan else None,"acceptance":dataclasses.asdict(acceptance),"future_text":text,
            "page_origin_m":origin.tolist(),"xheight_m":xheight_m,"limits":dataclasses.asdict(limits),
            "ready_for_fresh_measured_admission":ready,"letters":preflight,
            "required_body_travel_m":float(sum(np.linalg.norm(np.array(b["proposed_body_position_m"])-a["proposed_body_position_m"])
                                               for a,b in zip(preflight[:-1],preflight[1:]))),
            "repositioning":"The person or an external grounded actuator must supply these pen-up body translations; an internal stage cannot supply them indefinitely.",
            "execution":"Every letter requires fresh anchored observations and CompletionExecutor; this file commands no motor.",
            "ink":"Only future suffix strokes or a separately placed rewrite. Existing ink is untouched."}
    return plan,trajectories,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-text",required=True,help="text explicitly accepted by the writer")
    parser.add_argument("--written-prefix",default="",help="already deposited prefix; it must be preserved")
    parser.add_argument("--writer",required=True,help="UJI writer ID supplying calibration glyphs")
    parser.add_argument("--radius-mm",type=float,default=1.0587)
    parser.add_argument("--xheight-mm",type=float,default=3.)
    parser.add_argument("--origin-mm",type=float,nargs=2,default=[0.,0.])
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--simulate",action="store_true",help="run the declared nominal linear plant; never controls hardware")
    parser.add_argument("--servo-hz",type=float,default=40.)
    parser.add_argument("--no-feedforward",action="store_true",help="matched feedback-only reference replay")
    args=parser.parse_args()
    letters,provenance=D.load_uji()
    calibration=[l for l in letters if l.rep==1]
    heights=O.writer_xheights(calibration)
    if args.writer not in heights:
        parser.error(f"unknown writer; available IDs: {', '.join(sorted(heights))}")
    bank={l.char:[s/heights[l.writer] for s in l.strokes] for l in calibration if l.writer==args.writer}
    transcript=L.Transcript();transcript.add_word(args.written_prefix,[1.]*len(args.written_prefix),[])
    acceptance=transcript.accept(L.Suggestion(0,"completion","writer",args.accepted_text,1.,"explicit CLI accepted-text argument"))
    limits=dataclasses.replace(R.MotionLimits(),radius_m=args.radius_mm*1e-3,hard_stop_m=(args.radius_mm+.2)*1e-3)
    plan,trajectories,report=plan_from_acceptance(acceptance,bank,xheight_m=args.xheight_mm*1e-3,
                                              origin_m=np.array(args.origin_mm)*1e-3,limits=limits)
    report["dataset"]=provenance;report["writer"]=args.writer;report["calibration_session"]=1
    args.out.mkdir(parents=True,exist_ok=True)
    # Rejected letters generate no motor-reference file. Partial offline feasibility
    # does not authorise starting a word the prototype cannot finish.
    if report["ready_for_fresh_measured_admission"]:
        for k,tr in enumerate(trajectories):
            np.savez_compressed(args.out/f"letter_{k:02d}_{plan.letters[k].char}.npz",**tr.sample(),
                                body_origin=tr.body_origin,body_velocity=tr.body_velocity)
        if args.simulate:
            from .completion_replay import replay
            sim,trace=replay(plan,trajectories,servo_hz=args.servo_hz,feedforward=not args.no_feedforward)
            report["simulation"]=sim
            np.savetxt(args.out/"simulated_execution.csv",trace,delimiter=",",header=",".join(sim["trace_columns"]),comments="")
            np.savez_compressed(args.out/"simulated_execution.npz",trace=trace,columns=sim["trace_columns"])
            # Only simulated actually-contacting samples enter this explicitly
            # simulation-labelled ink record. The transcript's literal prefix
            # remains unchanged. There is no synthetic picture of that old ink.
            record=L.StrokeRecord();active=trace[:,6]>.5
            edges=np.diff(np.r_[False,active,False].astype(int))
            for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
                record.append(trace[a:b][:,[0,2,3]],"autowritten",plan.plan_id)
            report["simulated_ink_record"]={"verified":record.verify(),"strokes":len(record),
                                             "digests":[e.digest for e in record.entries],"label":"SIMULATED INK ONLY"}
    (args.out/"accepted_plan.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({"future_text":report["future_text"],"ready":report["ready_for_fresh_measured_admission"],
                      "letters":[{"char":r["char"],"admitted":r["admitted_at_proposed_position"]} for r in report["letters"]]},indent=2))


if __name__=="__main__":
    main()
