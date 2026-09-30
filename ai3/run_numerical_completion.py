"""Numerical correction of already-spent frozen observer replay cases.

All case specifications and controller designs are loaded from their original
recorded protocols. This corrects unstable explicit friction without retuning.
The old holdout is already spent; this rerun is not new blind validation. It is simulator
generalization only; the glyph writers and synthetic acceptance are not new
human validation data. Results count supervisor completion and retrospectively
checked true tracking separately, so observer optimism cannot hide a failure.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np

from . import accepted_completion as A
from . import completion_replay as C
from . import data as D
from . import layers as L
from . import online as O
from . import reachable as R
from . import robust_completion as B
from .run_completion_robustness import SCENARIOS


def summarize(rows):
    groups=sorted({r["scenario"] for r in rows});summary=[]
    for scenario in groups:
        selected=[r for r in rows if r["scenario"]==scenario]
        row=dict(scenario=scenario,cases=len(selected),admitted=sum(bool(r["controllers"]) for r in selected))
        for policy in ("gain_matched_path_feedforward","bounded_observer"):
            sims=[r["controllers"][policy] for r in selected if r["controllers"]]
            done=[s for s in sims if s["state"]=="done"]
            strict=[s for s in done if s["completed_with_true_tracking_tube"]]
            err=[l["simulated_ink_rms_reference_error_m"] for s in strict for l in s["letters"]]
            reasons={}
            for s in sims:
                if s["state"]!="done":
                    reason=s["letters"][-1]["reason"];reasons[reason]=reasons.get(reason,0)+1
            row[policy]=dict(supervisor_completed=len(done),completed_with_true_tracking_tube=len(strict),
                aborts=len(sims)-len(done),abort_reasons=reasons,
                median_letter_rms_um_strict_completed=float(np.median(err)*1e6) if err else None,
                peak_current_A=max((l["peak_current_A"] for s in sims for l in s["letters"]),default=None))
        summary.append(row)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase",choices=("development","holdout"),required=True)
    parser.add_argument("--internal-dt",type=float,default=.00005)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing/numerical_correction_50us"))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    code_files=["ai3/reachable.py","ai3/layers.py","ai3/accepted_completion.py","ai3/completion_replay.py",
                "ai3/robust_completion.py","ai3/planar_integrator.py","ai3/run_numerical_completion.py"]
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in code_files}
    letters,provenance=D.load_uji();calibration=[l for l in letters if l.rep==1]
    heights=O.writer_xheights(calibration)
    original_path=root/"results/improvement/writing"/f"robust_observer_{args.phase}_protocol.json"
    original=json.loads(original_path.read_text())
    specs=original["specifications"]
    writers=sorted({s["writer"] for s in specs})
    design=B.ObserverDesign(**original["design"])
    protocol=dict(scope=__doc__,phase=args.phase,design=dataclasses.asdict(design),code_sha256=hashes,
                  radius_mm=3.,xheight_mm=3.,calibration_session=1,specifications=specs,
                  primary_endpoint="whole accepted suffix completed AND actual stage tracking error <=150um and radius <=3mm at every simulated sample",
                  no_human_efficacy=True,no_fresh_writer_validation=True,
                  numerical_correction_of_spent_cases=True,
                  original_protocol_sha256=hashlib.sha256(original_path.read_bytes()).hexdigest(),
                  internal_max_dt_s=args.internal_dt,policy_tick_s=.0005,sensor_control_tick_s=.002,
                  integrator="coupled implicit midpoint, active current-limit solve, substep copper integration",
                  numerical_scope="same controller gains, source case specifications, seeds and acquisition schedule; mean applied-current observation corrects legacy endpoint-as-held approximation")
    # Written before any case executes. Holdout protocol/results are immutable:
    # a changed source, seed list or completed output requires a new named study.
    protocol_path=args.out/f"robust_observer_{args.phase}_protocol.json"
    result_path=args.out/f"robust_observer_{args.phase}.json"
    serialized=json.dumps(protocol,indent=2,allow_nan=False)
    if args.phase=="holdout":
        if result_path.exists():raise FileExistsError("this numerical correction already exists; do not overwrite its evidence")
        if protocol_path.exists():
            if protocol_path.read_text()!=serialized:raise ValueError("holdout protocol differs from its immutable frozen record")
        else:
            with protocol_path.open("x") as stream:stream.write(serialized)
    else:protocol_path.write_text(serialized)
    rows=[];cached={}
    for i,spec in enumerate(specs):
        writer=spec["writer"];contact=spec["contact_delay_s"];key=(writer,contact)
        if key not in cached:
            bank={l.char:[s/heights[writer] for s in l.strokes] for l in calibration if l.writer==writer}
            accept=L.Revision(0,0,"becau","because","completion","writer","writer","ASSUMED acceptance for model replay",0.)
            lim=dataclasses.replace(R.MotionLimits(),radius_m=.003,hard_stop_m=.0032,lift_delay_s=contact,lower_delay_s=contact)
            cached[key]=A.plan_from_acceptance(accept,bank,limits=lim)
        plan,trs,preflight=cached[key];row=dict(**spec,preflight=preflight,controllers={})
        if plan:
            perturb=C.Perturbation(**spec["perturbation"])
            robust,trace=B.replay(copy.deepcopy(plan),copy.deepcopy(trs),perturbation=perturb,design=design,internal_dt=args.internal_dt)
            baseline,base_trace=C.replay(copy.deepcopy(plan),copy.deepcopy(trs),perturbation=perturb,
                                       servo_hz=robust["servo_hz"],damping_ratio=design.damping_ratio,internal_dt=args.internal_dt)
            strict=True
            for li,tr in enumerate(trs):
                a=base_trace[base_trace[:,1]==li]
                if not len(a):strict=False;continue
                active=a[:,0]-a[0,0]<=tr.duration
                error=np.linalg.norm((a[:,2:4]-a[:,4:6])@tr.limits.page_to_stage.T,axis=1)
                radius=np.linalg.norm(a[:,8:10],axis=1)
                strict=bool(strict and error[active].max()<=tr.limits.tracking_reserve_m and radius[active].max()<=tr.limits.radius_m)
            baseline["completed_with_true_tracking_tube"]=bool(baseline["state"]=="done" and strict)
            required=sum(p.duration for tr in trs for p in tr.pieces if p.phase=="ink")
            covered=float(np.sum((base_trace[:,6]>.5)&(base_trace[:,7]>.5))*.0005)
            baseline["ink_accounting"]={"full_plan_required_ink_duration_s":required,
                "actual_contact_during_required_phases_s":covered,
                "required_phase_contact_fraction":min(1.,covered/required),
                "extra_contact_outside_required_phases_s":float(np.sum((base_trace[:,6]>.5)&(base_trace[:,7]<.5))*.0005),
                "discretization":"0.5ms samples; denominator includes unexecuted letters"}
            row["controllers"]={"gain_matched_path_feedforward":baseline,"bounded_observer":robust}
            if writer==writers[0]:
                tag=f"robust_observer_{args.phase}_{i:03d}_{spec['scenario']}"
                np.savetxt(args.out/(tag+".csv"),trace,delimiter=",",header=",".join(robust["trace_columns"]),comments="")
        rows.append(row)
        if i==len(specs)-1 or specs[i+1]["writer"]!=writer:
            print(f"{args.phase} finished {writer}; {len(rows)} cases",flush=True)
    report=dict(protocol=protocol,dataset=provenance,rows=rows,summary=summarize(rows))
    if hashes!={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in code_files}:
        raise RuntimeError("source changed during replay; evidence not published")
    if args.phase=="holdout":
        with result_path.open("x") as stream:stream.write(json.dumps(report,indent=2,allow_nan=False))
    else:result_path.write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report["summary"],indent=2),flush=True)


if __name__=="__main__":main()
