"""Export accepted future 'se' for the concrete grounded-mechanism postcheck.

UJI session-1 glyphs and synthetic explicit acceptances only. Each word includes
200 ms lower/lift phases and a commanded, pen-up, 500 ms minimum-jerk move between
letters. The external coarse mechanism supplies that translation. All position,
velocity and acceleration channels share the same analytic piecewise reference.
No claim is made that a freehand person follows this body trajectory.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np

from . import accepted_completion as A
from . import coarse_fine as F
from . import data as D
from . import layers as L
from . import online as O
from . import reachable as R


def join_word(samples,origin,lim,model):
    """Join zero-velocity, zero-acceleration endpoints with analytic air moves."""
    M=lim.page_to_stage;Minv=np.linalg.inv(M);chunks=[];clock=0.
    array_keys=("t","xy","down","phase","q","q_velocity_m_s","q_acceleration_m_s2",
                "coarse_offset_page_m","coarse_velocity_m_s","coarse_acceleration_m_s2",
                "absolute_nib_acceleration_page_m_s2","nominal_force_N")
    for li,data0 in enumerate(samples):
        data={k:np.array(data0[k],copy=True) for k in array_keys}
        data["coarse_offset_page_m"]+=data0["body_origin"]-origin
        data["letter_index"]=np.full(len(data["t"]),li)
        if chunks:
            prev=chunks[-1];duration=.5
            u=np.linspace(0,1,1001)[1:]
            h=10*u**3-15*u**4+6*u**5
            hv=(30*u**2-60*u**3+30*u**4)/duration
            ha=(60*u-180*u**2+120*u**3)/duration**2
            def blend(key):
                start=prev[key][-1];delta=data[key][0]-start
                return start+h[:,None]*delta,hv[:,None]*delta,ha[:,None]*delta
            b,bv,ba=blend("coarse_offset_page_m");q,qv,qa=blend("q")
            xy=origin+b+q@Minv.T;ra=ba+qa@Minv.T
            force=F.CoarseStage().fine_mass_kg*(ra@Minv)+model.stiffness_N_m*q+model.damping_N_s_m*qv+model.bias_force_N
            chunks.append(dict(t=clock+u*duration,xy=xy,down=np.zeros(len(u),bool),phase=np.full(len(u),"air"),
                q=q,q_velocity_m_s=qv,q_acceleration_m_s2=qa,coarse_offset_page_m=b,
                coarse_velocity_m_s=bv,coarse_acceleration_m_s2=ba,
                absolute_nib_acceleration_page_m_s2=ra,nominal_force_N=force,letter_index=np.full(len(u),-1)))
            clock+=duration
            # The preceding air move owns the shared endpoint.
            data={k:v[1:] for k,v in data.items()}
        data["t"]+=clock
        chunks.append(data);clock=float(data["t"][-1])
    out={k:np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
    out["body_origin"]=np.asarray(origin)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writers",type=int,default=20)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing/grounded_accepted"))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    letters,provenance=D.load_uji();calibration=[l for l in letters if l.rep==1]
    heights=O.writer_xheights(calibration)
    writers=sorted(w for w in heights if w.startswith("tst"))[:args.writers]
    limits=dataclasses.replace(R.MotionLimits(),radius_m=.100,hard_stop_m=.101,lift_delay_s=.200,lower_delay_s=.200,
        position_error_m=0.,velocity_error_m_s=0.,acceleration_error_m_s2=0.)
    rows=[]
    for writer in writers:
        bank={l.char:[s/heights[writer] for s in l.strokes] for l in calibration if l.writer==writer}
        acceptance=L.Revision(0,0,"becau","because","completion","writer","writer","ASSUMED explicit acceptance for mechanical replay",0.)
        plan,trajectories,preflight=A.plan_from_acceptance(acceptance,bank,limits=limits)
        row={"writer":writer,"session":1,"acceptance":dataclasses.asdict(acceptance),"future_text":"se",
             "reference_preflight":preflight,"letters":[],"word_reference":None}
        samples=[]
        if plan:
            for i,tr in enumerate(trajectories):
                for scale in (1.,1.25,1.5,2.,3.,4.):
                    bounds=F.assess(tr,F.CoarseStage(),scale)
                    if bounds["passed"]:break
                letter={"letter_index":i,"char":plan.letters[i].char,"bounds":bounds,"reference":None}
                if bounds["passed"]:
                    path=args.out/f"{writer}_{i}_{plan.letters[i].char}.npz"
                    samples.append(F.export(tr,F.CoarseStage(),scale,path));letter["reference"]=str(path)
                row["letters"].append(letter)
            if len(samples)==len(trajectories):
                points=np.vstack([s["xy"] for s in samples]);origin=(points.min(0)+points.max(0))/2
                word=join_word(samples,origin,limits,trajectories[0].model)
                path=args.out/f"{writer}_accepted_se.npz";np.savez_compressed(path,**word)
                row["word_reference"]=str(path)
                row["global_page_origin_m"]=origin.tolist()
                row["duration_s"]=float(word["t"][-1])
                row["coarse_max_xy_m"]=abs(word["coarse_offset_page_m"]).max(0).tolist()
                row["fine_max_radius_m"]=float(np.linalg.norm(word["q"],axis=1).max())
        rows.append(row)
    # Same session-2 e as the original coarse screen, with slower contact phases.
    e=next(l for l in letters if l.writer==writers[0] and l.rep==2 and l.char=="e")
    pts=np.vstack(e.strokes);centre=(pts.min(0)+pts.max(0))/2
    strokes=[(s-centre)/heights[e.writer]*.003 for s in e.strokes]
    tr,_=R.plan_letter(strokes,[0.,0.],limits=limits)
    if tr:
        F.export(tr,F.CoarseStage(),1.,args.out.parent/"coarse_fine_reference_200ms.npz")
    root=Path(__file__).resolve().parents[1]
    files=["ai3/reachable.py","ai3/coarse_fine.py","ai3/accepted_completion.py","ai3/export_grounded_completion.py"]
    report={"evidence":__doc__,"dataset":provenance,"new_blind_validation":False,
        "assumed_lift_and_lower_s":.200,"assumed_interletter_air_move_s":.500,"xheight_mm":3.,
        "reference_only_envelope_m":.100,"note":"The 100mm envelope only generates references; it is not a pen-stage feasibility claim. Each 4+1.5mm split is screened separately, and full words require the actual five-bar and fine-stage postcheck.",
        "writers":len(rows),"whole_suffix_exported":sum(r["word_reference"] is not None for r in rows),"rows":rows,
        "code_sha256":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}}
    (args.out/"manifest.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({"writers":len(rows),"whole_suffix_exported":report["whole_suffix_exported"],"path":str(args.out/"manifest.json")}),flush=True)


if __name__=="__main__":main()
