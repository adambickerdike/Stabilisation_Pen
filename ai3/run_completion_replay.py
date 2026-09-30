"""Matched feedback/accepted-path-feedforward execution on UJI calibration shapes.

The two text decisions are fixed integration scenarios, not recognition results:
accepted suffix 'becau' -> 'because', and a separately placed 'libary' -> 'library'
rewrite. Their acceptances and manual pen-up body repositioning are ASSUMED.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from . import accepted_completion as A
from . import completion_replay as C
from . import data as D
from . import layers as L
from . import online as O
from . import reachable as R


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing"))
    parser.add_argument("--writers",type=int,default=20)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    all_letters,provenance=D.load_uji()
    letters=[l for l in all_letters if l.rep==1]
    xh=O.writer_xheights(letters)
    writers=sorted(w for w in xh if w.startswith("tst"))[:args.writers]
    cases=[];examples=[]
    for writer in writers:
        bank={l.char:[s/xh[writer] for s in l.strokes] for l in letters if l.writer==writer}
        for before,after,kind in [("becau","because","completion"),("libary","library","spelling")]:
            # A synthetic explicit-acceptance event exercises the physical API.
            acceptance=L.Revision(0,0,before,after,kind,"writer","writer","ASSUMED acceptance for replay",0.)
            for radius in (1.0587,1.5,2.,3.,6.):
                limits=dataclasses.replace(R.MotionLimits(),radius_m=radius*1e-3,hard_stop_m=(radius+.2)*1e-3)
                plan,trajectories,preflight=A.plan_from_acceptance(acceptance,bank,limits=limits)
                result={"writer":writer,"calibration_session":1,"before":before,"accepted":after,"kind":kind,
                        "radius_mm":radius,"preflight":preflight,"controllers":{}}
                if plan:
                    for feedforward in (False,True):
                        sim,trace=C.replay(copy.deepcopy(plan),copy.deepcopy(trajectories),feedforward=feedforward)
                        result["controllers"]["feedforward" if feedforward else "feedback_only"]=sim
                        if writer==writers[0] and kind=="completion" and radius==3.:
                            tag="feedforward" if feedforward else "feedback_only"
                            np.savetxt(args.out/f"accepted_{tag}_trace.csv",trace,delimiter=",",
                                       header=",".join(sim["trace_columns"]),comments="")
                            examples.append((tag,trace))
                    if writer==writers[0] and kind=="completion" and radius==3.:
                        fault,trace=C.replay(copy.deepcopy(plan),copy.deepcopy(trajectories),fault=("reference",.15))
                        result["reference_loss_replay"]=fault
                        np.savetxt(args.out/"accepted_reference_loss_trace.csv",trace,delimiter=",",
                                   header=",".join(fault["trace_columns"]),comments="")
                cases.append(result)
        print(f"executed {writer}; {len(cases)} text/workspace scenarios",flush=True)
    summary=[]
    for kind in ("completion","spelling"):
        for radius in (1.0587,1.5,2.,3.,6.):
            selected=[r for r in cases if r["kind"]==kind and r["radius_mm"]==radius]
            admitted=[r for r in selected if r["controllers"]]
            row={"kind":kind,"radius_mm":radius,"n_writers":len(selected),"whole_text_preflight_pass":len(admitted)}
            for policy in ("feedback_only","feedforward"):
                sims=[r["controllers"][policy] for r in admitted]
                done=[s for s in sims if s["state"]=="done"]
                errors=[l["simulated_ink_rms_reference_error_m"] for s in done for l in s["letters"]]
                row[policy+"_completed"]=len(done)
                row[policy+"_median_letter_rms_um_completed"]=float(np.median(errors)*1e6) if errors else None
            summary.append(row)
    root=Path(__file__).resolve().parents[1]
    code_files=["ai3/reachable.py","ai3/layers.py","ai3/accepted_completion.py","ai3/completion_replay.py","ai3/planar_integrator.py","ai3/run_completion_replay.py"]
    report={"evidence":C.__doc__,"dataset":provenance,"protocol":__doc__,
            "revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
            "code_sha256":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in code_files},
            "new_blind_validation":False,"summary":summary,"cases":cases}
    (args.out/"accepted_execution_replay.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(summary,indent=2),flush=True)
    if examples:
        plot(args.out,examples)


def plot(out,examples):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout="constrained")
    for tag,trace in examples:
        for letter in np.unique(trace[:,1]).astype(int):
            a=trace[trace[:,1]==letter]
            ink=a[a[:,6]>.5]
            if len(ink):
                axes[0].plot(ink[:,2]*1e3,ink[:,3]*1e3,label=f"{tag.replace('_',' ')} · letter {letter+1}")
            active=a[:,7]>.5
            err=np.linalg.norm((a[:,2:4]-a[:,4:6])@np.diag([np.sin(np.deg2rad(50.)),1.]),axis=1)*1e6
            axes[1].plot(a[active,0],err[active],label=f"{tag.replace('_',' ')} · {letter+1}")
    axes[0].set(xlabel="Page x (mm)",ylabel="Page y (mm)",title="Only the accepted future suffix 'se'")
    axes[0].set_aspect("equal");axes[0].legend(fontsize=7)
    axes[1].set(xlabel="Time including assumed pen-up reposition (s)",ylabel="Stage-frame error from planned reference (µm)",title="Same nominal 40 Hz plant and sensor assumptions")
    axes[1].axhline(150,color="red",ls="--",lw=.8,label="tracking abort threshold")
    axes[1].legend(fontsize=7)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle("SIMULATION · UJI tst_UJI_W12 glyphs · 3 mm hypothetical stage · perfect sensing · no human result",fontsize=10)
    fig.savefig(out/"accepted_execution.svg");fig.savefig(out/"accepted_execution.png",dpi=180)
    plt.close(fig)


if __name__=="__main__":
    main()
