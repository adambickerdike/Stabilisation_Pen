"""Conditional accepted-writing architecture: externally reacted coarse + fine motion.

CALCULATION ONLY. A 4 mm page-XY coarse stage plus a 1.5 mm radial nib is NOT the
current Rev K mechanism. The coarse path needs a grounded carriage. A collar
around the improved 24 mm nib has not been packaged. Internal mass does not supply this
sustained translation. Forces below are a transparent engineering screen with
assumed mass, drag, spring/grip and friction; not a validated carriage design.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np

from . import data as D
from . import online as O
from . import reachable as R


@dataclasses.dataclass(frozen=True)
class CoarseStage:
    radius_m:float=.004
    payload_mass_kg:float=.150       # ASSUMPTION: externally grounded moving assembly, excluding moving nib
    drag_N_s_m:float=.20
    spring_N_m:float=0.             # replace with measured collar/grip stiffness for that architecture
    friction_bound_N:float=.080
    force_limit_N:float=.400
    speed_m_s:float=.030
    acceleration_m_s2:float=2.
    reserve_m:float=.200e-3
    fine_radius_m:float=.0015
    fine_reserve_m:float=.200e-3
    fine_mass_kg:float=.003670


def assess(trajectory:R.LetterTrajectory,coarse:CoarseStage=CoarseStage(),time_scale:float=1.):
    """Sufficient continuous polynomial bounds, constant beta split.

    Fine force includes ABSOLUTE nib acceleration, not merely relative-stage
    acceleration: moving the pen body cannot make nib inertia disappear.
    """
    if not np.isfinite(time_scale) or time_scale<=0:
        raise ValueError("positive time scale required")
    if np.linalg.norm(trajectory.body_velocity)>1e-14:
        raise ValueError("coarse/fine split requires a stationary reference body origin")
    beta=coarse.radius_m/(coarse.radius_m+coarse.fine_radius_m)
    center=trajectory.body_origin;M=trajectory.limits.page_to_stage
    bounds={k:0. for k in ("coarse_radius_m","fine_radius_m","coarse_speed_m_s","fine_speed_m_s",
                           "coarse_acceleration_m_s2","fine_acceleration_m_s2","coarse_force_N","fine_force_N")}
    for piece in trajectory.pieces:
        t=piece.duration*time_scale
        r=piece.controls
        delta=r-center
        bc=beta*delta                 # coarse page-XY displacement
        qf=(1-beta)*delta@M.T         # fine mechanical coordinates
        bv=R._derivative(bc,t);ba=R._derivative(bc,t,2)
        fv=R._derivative(qf,t);fa=R._derivative(qf,t,2)
        ra=R._derivative(r,t,2)
        Fcoarse=(coarse.payload_mass_kg*R._elevate(ba,5)+coarse.fine_mass_kg*R._elevate(ra,5)+
                 coarse.drag_N_s_m*R._elevate(bv,5)+coarse.spring_N_m*bc)
        # Virtual work: r=A*q, so generalized inertia force is A.T*m*rddot.
        # The row-vector representation therefore multiplies absolute rddot by A.
        Ffine=(coarse.fine_mass_kg*R._elevate(ra@np.linalg.inv(M),5)+trajectory.model.stiffness_N_m*qf+
               trajectory.model.damping_N_s_m*R._elevate(fv,5)+trajectory.model.bias_force_N)
        metrics={"coarse_radius_m":np.linalg.norm(bc,axis=1).max()+coarse.reserve_m,
                 "fine_radius_m":np.linalg.norm(qf,axis=1).max()+coarse.fine_reserve_m,
                 "coarse_speed_m_s":np.linalg.norm(bv,axis=1).max(),"fine_speed_m_s":np.linalg.norm(fv,axis=1).max(),
                 "coarse_acceleration_m_s2":np.linalg.norm(ba,axis=1).max(),"fine_acceleration_m_s2":np.linalg.norm(fa,axis=1).max(),
                 "coarse_force_N":np.linalg.norm(Fcoarse,axis=1).max()+coarse.friction_bound_N,
                 "fine_force_N":np.linalg.norm(Ffine,axis=1).max()+trajectory.model.load_uncertainty_N}
        for key,value in metrics.items():bounds[key]=max(bounds[key],float(value))
    thresholds={"coarse_radius_m":coarse.radius_m,"fine_radius_m":coarse.fine_radius_m,
                "coarse_speed_m_s":coarse.speed_m_s,"fine_speed_m_s":trajectory.limits.speed_m_s,
                "coarse_acceleration_m_s2":coarse.acceleration_m_s2,"fine_acceleration_m_s2":trajectory.limits.acceleration_m_s2,
                "coarse_force_N":coarse.force_limit_N}
    bounds.update({"passed":all(bounds[k]<=v for k,v in thresholds.items()),
                   "failed":[k for k,v in thresholds.items() if bounds[k]>v],"thresholds":thresholds,
                   "beta":beta,"duration_s":trajectory.duration*time_scale,"time_scale":time_scale,
                   "fine_force_scope":"required force only; use the mechanics spatial allocator and wire heat model to judge authority"})
    return bounds


def export(trajectory,coarse,time_scale,path):
    if np.linalg.norm(trajectory.body_velocity)>1e-14:
        raise ValueError("coarse/fine export requires a stationary reference body origin")
    sample=trajectory.sample(.0005)
    beta=coarse.radius_m/(coarse.radius_m+coarse.fine_radius_m)
    M=trajectory.limits.page_to_stage;Minv=np.linalg.inv(M)
    # The source trajectory was generated with nominally stationary body.
    rv=sample["q_velocity_m_s"]@Minv.T
    ra=sample["q_acceleration_m_s2"]@Minv.T
    delta=sample["xy"]-trajectory.body_origin
    coarse_offset=beta*delta
    fine_q=(1-beta)*delta@M.T
    body_velocity=beta*rv/time_scale;body_acceleration=beta*ra/time_scale**2
    fine_velocity=(1-beta)*rv@M.T/time_scale
    fine_acceleration=(1-beta)*ra@M.T/time_scale**2
    fine_force=(coarse.fine_mass_kg*(ra@Minv)/time_scale**2+trajectory.model.stiffness_N_m*fine_q+
                trajectory.model.damping_N_s_m*fine_velocity+trajectory.model.bias_force_N)
    data=dict(t=sample["t"]*time_scale,xy=sample["xy"],down=sample["down"],phase=sample["phase"],
                        q=fine_q,q_velocity_m_s=fine_velocity,q_acceleration_m_s2=fine_acceleration,
                        body_origin=trajectory.body_origin,coarse_offset_page_m=coarse_offset,
                        coarse_velocity_m_s=body_velocity,coarse_acceleration_m_s2=body_acceleration,
                        absolute_nib_acceleration_page_m_s2=ra/time_scale**2,nominal_force_N=fine_force)
    if path is not None:
        np.savez_compressed(path,**data)
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing"))
    parser.add_argument("--writers",type=int,default=20)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    letters,provenance=D.load_uji();xh=O.writer_xheights([l for l in letters if l.rep==1])
    writers=sorted(w for w in xh if w.startswith("tst"))[:args.writers]
    rows=[];exported=False
    for L in [l for l in letters if l.writer in writers and l.rep==2]:
        allp=np.vstack(L.strokes);center=(allp.min(0)+allp.max(0))/2
        strokes=[(p-center)/xh[L.writer]*.003 for p in L.strokes]
        # This broad reference-only envelope does not claim a 100 mm pen stage.
        lim=dataclasses.replace(R.MotionLimits(),radius_m=.100,hard_stop_m=.101,
                                position_error_m=0.,velocity_error_m_s=0.,acceleration_error_m_s2=0.)
        tr,diag=R.plan_letter(strokes,[0.,0.],limits=lim)
        for spring in (0.,50.,200.,500.):
            coarse=dataclasses.replace(CoarseStage(),spring_N_m=spring)
            best=None
            if tr:
                for scale in (1.,1.25,1.5,2.,3.,4.):
                    best=assess(tr,coarse,scale)
                    if best["passed"]:break
            rows.append({"writer":L.writer,"char":L.char,"spring_N_m":spring,
                         "reference_generated":tr is not None,"reason":diag["reason"],"bounds":best})
            if tr and best["passed"] and not exported and spring==0. and L.char=="e":
                export(tr,coarse,best["time_scale"],args.out/"coarse_fine_reference.npz")
                (args.out/"coarse_fine_example.json").write_text(json.dumps({"writer":L.writer,"session":L.rep,
                    "char":L.char,"evidence":__doc__,"parameters":dataclasses.asdict(coarse),"bounds":best},indent=2))
                exported=True
        if L.char=="z":print(f"coarse/fine screen finished {L.writer}",flush=True)
    summary=[]
    for spring in (0.,50.,200.,500.):
        sel=[r for r in rows if r["spring_N_m"]==spring]
        passed=[r for r in sel if r["bounds"] and r["bounds"]["passed"]]
        summary.append({"spring_N_m":spring,"glyphs":len(sel),"passed":len(passed),"share":len(passed)/len(sel),
                        "median_time_s_passed":float(np.median([r["bounds"]["duration_s"] for r in passed])) if passed else None,
                        "p95_fine_force_N_passed":float(np.quantile([r["bounds"]["fine_force_N"] for r in passed],.95)) if passed else None})
    root=Path(__file__).resolve().parents[1]
    files=["ai3/coarse_fine.py","ai3/reachable.py","ai3/data.py"]
    result={"evidence":__doc__,"dataset":provenance,"fine_radius_mm":1.5,"coarse_radius_mm":4.,
            "assumptions":dataclasses.asdict(CoarseStage()),"summary":summary,"rows":rows,
            "code_sha256":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files},
            "limits":["No built coarse carriage or collar is validated","No freehand-body prediction used; the coarse trajectory is explicitly commanded",
                      "Zero spring means unloaded external carriage, not a person's unknown grip","Force-cap and friction assumptions must be measured",
                      "Fine winding-map/lead heat check and full contact dynamics remain separate"]}
    (args.out/"coarse_fine_screen.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
