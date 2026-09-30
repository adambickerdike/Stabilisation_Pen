"""Reproducible audit of the historic completion planner and new reference generator.

All UJI shapes are real recorded isolated characters. Timing, scale, body motion,
actuator properties and responses to reposition prompts are assumed. No human,
recognizer or handwriting-legibility result is produced. The old study-S test
writers are reused: this is an engineering replay, not a newly blind test set.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np

from . import complete_plan as CP
from . import data as D
from . import online as O
from . import reachable as R


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=("CALCULATION: reference-generation replay on real UJI glyph shapes; "
          "assumed scale, timing, body motion and actuator model. Not a built pen, "
          "closed-loop plant result, recognition result or human handwriting improvement.")


def _trace_metrics(trace,limits):
    if len(trace)<3:
        return {"legacy_stage_speed_m_s":0.,"legacy_stage_acceleration_m_s2":0.,
                "legacy_stage_radius_m":0.,"legacy_dynamic_pass":False}
    q=(trace[:,1:3]-trace[:,3:5])@limits.page_to_stage.T
    dt=np.diff(trace[:,0]);vel=np.diff(q,axis=0)/dt[:,None]
    acc=np.diff(vel,axis=0)/((dt[:-1]+dt[1:])/2)[:,None]
    vm=float(np.linalg.norm(vel,axis=1).max());am=float(np.linalg.norm(acc,axis=1).max())
    qm=float(np.linalg.norm(q,axis=1).max())
    return {"legacy_stage_speed_m_s":vm,"legacy_stage_acceleration_m_s2":am,
            "legacy_stage_radius_m":qm,"legacy_dynamic_pass":bool(vm<=limits.speed_m_s and am<=limits.acceleration_m_s2 and qm<=limits.radius_m)}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"results/improvement/writing")
    parser.add_argument("--writers",type=int,default=20)
    parser.add_argument("--letters",default=O.LETTERS)
    parser.add_argument("--radii-mm",type=float,nargs="+",default=[1.0587,1.5,2.,3.,6.])
    parser.add_argument("--skip-figures",action="store_true")
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    t0=time.time()
    letters,provenance=D.load_uji()
    # Scale is estimated from session 1 only; replay uses session 2.
    xh=O.writer_xheights([L for L in letters if L.rep==1])
    writers=sorted({L.writer for L in letters if O.split_of(L.writer)=="test"})[:args.writers]
    selected=[L for L in letters if L.writer in writers and L.rep==2 and L.char in args.letters]
    rows=[];examples=[]
    lim0=R.MotionLimits();model=R.StageModel()
    for li,L in enumerate(selected):
        norm=[np.asarray(s,float)/xh[L.writer] for s in L.strokes]
        allp=np.vstack(norm);base=np.array([allp[:,0].min(),np.percentile(allp[:,1],5)])
        strokes=[(s-base)*.003 for s in norm]
        p=np.vstack(strokes);center=(p.min(0)+p.max(0))/2
        P,pen,lid,s=CP.word_path([norm])
        # Current body is centred on this letter after an ASSUMED pen-up reposition.
        # That reposition is requested from a person or an external actuator, not performed by this code.
        B=np.tile(center,(int((s[-1]/CP.V_MAX*4+6)/CP.DT)+1,1))
        for radius in args.radii_mm:
            lim=dataclasses.replace(lim0,radius_m=radius*1e-3,hard_stop_m=(radius+.2)*1e-3)
            old=CP.simulate(P,pen,lid,s,B,radius,"letter_admission",return_trace=True)
            new,diag=R.plan_letter(strokes,center,limits=lim,model=model)
            row={"writer":L.writer,"session":L.rep,"char":L.char,"radius_mm":radius,
                 "body_assumption":"repositioned_to_letter_then_nominally_stationary",
                 "path_length_mm":float(s[-1]*1e3),"height_mm":float(np.ptp(p[:,1])*1e3),
                 "legacy_done":old["state"]=="done","legacy_state":old["state"],"legacy_time_s":old["time_s"],
                 **_trace_metrics(old["command_trace"],lim),
                 "new_admitted":new is not None,"new_reason":diag["reason"],
                 "new_time_s":new.duration if new else None,
                 "geometry_bound_m":new.geometry_bound_m if new else diag.get("geometry_bound_m"),
                 "new_bounds":new.bounds if new else diag.get("last_bounds"),"retiming_trials":diag.get("trials",[])}
            rows.append(row)
            if new is not None and len(examples)<3 and radius>=2. and L.char in "aems":
                examples.append((L,strokes,new,old["command_trace"],row))
        if (li+1)%26==0:
            print(f"{li+1}/{len(selected)} glyphs evaluated in {time.time()-t0:.1f}s",flush=True)
    summary=[]
    for radius in args.radii_mm:
        sel=[r for r in rows if r["radius_mm"]==radius]
        old=[r for r in sel if r["legacy_done"]];new=[r for r in sel if r["new_admitted"]]
        wrates=[]
        for writer in writers:
            w=[r for r in sel if r["writer"]==writer]
            wrates.append(sum(r["new_admitted"] for r in w)/len(w))
        rng=np.random.default_rng(921)
        boots=rng.choice(wrates,(4000,len(wrates)),replace=True).mean(1)
        matched=[r for r in new if r["legacy_done"]]
        summary.append({"radius_mm":radius,"n_glyphs":len(sel),"writers":len(writers),
                        "legacy_complete":len(old),"legacy_complete_with_sampled_dynamics_pass":sum(r["legacy_dynamic_pass"] for r in old),
                        "new_admitted":len(new),"new_admitted_share":len(new)/len(sel),
                        "writer_cluster_bootstrap_95pct":np.quantile(boots,[.025,.975]).tolist(),
                        "median_new_time_s":float(np.median([r["new_time_s"] for r in new])) if new else None,
                        "matched_new_over_legacy_time_median":float(np.median([r["new_time_s"]/r["legacy_time_s"] for r in matched])) if matched else None,
                        "legacy_peak_acceleration_p95_m_s2":float(np.quantile([r["legacy_stage_acceleration_m_s2"] for r in old],.95)) if old else None})
    try:
        revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    except Exception:
        revision="unknown"
    code_files=[Path(__file__),ROOT/"ai3/reachable.py",ROOT/"ai3/layers.py",ROOT/"ai3/complete_plan.py",ROOT/"ai3/data.py"]
    out={"evidence":EVIDENCE,"revision":revision,"code_sha256":{str(p.relative_to(ROOT)):_sha(p) for p in code_files},
         "python":platform.python_version(),"numpy":np.__version__,"dataset":provenance,
         "protocol":{"shape_source":"UJI tst writer session 2, scale from that writer's session 1",
                     "reuse":"These writers appeared in historical studies and development inspection; not an untouched validation set.",
                     "human_or_tremor_inputs":"None. UJI has no timings, force, pen-body motion or tremor labels.",
                     "body":"centred on each letter, nominally still, with the declared bounded prediction error",
                     "radius":"Rev K 1.0587 mm radial stage; all other travel values are hypothetical research envelopes",
                     "comparison":"same letters, x-height, current body location; historic page-circle admission and sampled path commands versus continuous stage-ellipse constraints",
                     "completion":"one whole letter admitted; this is not a complete-word success rate and does not verify a physical plant",
                     "refusal":"no partial letter is intentionally started if the full remaining letter cannot be admitted",
                     "parameters_chosen_on_test":False,
                     "runtime_parameter_tuning":"No model, classifier or parameter fitting in this runner; reuse caveat above still applies."},
         "limits":dataclasses.asdict(lim0),"stage_model":dataclasses.asdict(model),
         "summary":summary,"rows":rows,"elapsed_s":time.time()-t0}
    (args.out/"reachable_replay.json").write_text(json.dumps(out,indent=2,allow_nan=False))
    keys=[k for k in rows[0] if k not in ("new_bounds","retiming_trials")]
    with (args.out/"reachable_replay.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for r in rows:writer.writerow({k:r[k] for k in keys})
    (args.out/"summary.json").write_text(json.dumps(summary,indent=2))
    if not args.skip_figures:
        figures(args.out,summary,examples)
    print(json.dumps(summary,indent=2),flush=True)


def figures(out,summary,examples):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9})
    fig,axes=plt.subplots(1,2,figsize=(11,4.1),layout="constrained")
    r=np.array([s["radius_mm"] for s in summary]);n=np.array([s["n_glyphs"] for s in summary])
    axes[0].plot(r,[s["legacy_complete"]/nn*100 for s,nn in zip(summary,n)],"o--",label="Historic kinematic completion",color="#9c6b3e")
    axes[0].plot(r,[s["new_admitted_share"]*100 for s in summary],"o-",label="New continuous bounds passed",color="#007d82")
    axes[0].plot(r,[s["legacy_complete_with_sampled_dynamics_pass"]/nn*100 for s,nn in zip(summary,n)],"s:",label="Historic completion + v/a checks",color="#9e3347")
    axes[0].set(xlabel="Stage radius (mm)",ylabel="Recorded glyphs (%)",ylim=(-3,103),title="Admissible reference is stricter than geometric completion")
    axes[0].legend(fontsize=8,loc="lower right");axes[0].grid(alpha=.2)
    if examples:
        L,strokes,tr,old,row=examples[0]
        for j,s in enumerate(strokes):axes[1].plot(s[:,0]*1e3,s[:,1]*1e3,"-",color="#a5aab1",lw=3,label="Recorded desired glyph" if j==0 else None)
        sm=tr.sample(.0005)
        for j,p in enumerate(tr.pieces):
            if p.phase=="ink":
                pp=R._evaluate(p.controls,np.linspace(0,1,31))
                axes[1].plot(pp[:,0]*1e3,pp[:,1]*1e3,color="#007d82",lw=1)
        axes[1].plot([],[],color="#007d82",label="Planned reference (not measured ink)")
        axes[1].set(xlabel="Page x (mm)",ylabel="Page y (mm)",title=f"UJI {L.writer}, session {L.rep}, '{L.char}'\nBounded geometry error {tr.geometry_bound_m*1e6:.1f} µm")
        axes[1].set_aspect("equal");axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
        np.savez_compressed(out/"example_reference.npz",**sm,body_origin=tr.body_origin,body_velocity=tr.body_velocity)
        (out/"example_provenance.json").write_text(json.dumps({"evidence":EVIDENCE,"writer":L.writer,"session":L.rep,
            "char":L.char,"radius_mm":row["radius_mm"],"bound":tr.bounds,"source_path_digest":tr.path_digest,
            "certificate_digest":tr.certificate_digest,"meaning":"desired recorded glyph compared with planned reference; not before/after patient handwriting"},indent=2))
    fig.suptitle("CALCULATION · Real isolated glyph shapes, assumed timing/body/actuator · No hardware validation",fontsize=10)
    fig.savefig(out/"reachable_comparison.svg");fig.savefig(out/"reachable_comparison.png",dpi=180)
    plt.close(fig)


if __name__=="__main__":
    main()
