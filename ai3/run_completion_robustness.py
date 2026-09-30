"""Fixed sensitivity matrix for accepted 'se' on a hypothetical 3 mm stage.

No recognizer is tested and no hardware result is implied. The scenarios and
gains are fixed in this source; this is an engineering stress test, not training
or blind validation. A separate mechanics study checks a grounded five-bar.
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


SCENARIOS=[
    ("nominal_ideal_sensing",C.Perturbation(),40.,.020),
    ("mass_stiffness_damping_plus30pct",C.Perturbation(mass_scale=1.3,stiffness_scale=1.3,damping_scale=1.3),40.,.020),
    ("mass_stiffness_damping_minus30pct",C.Perturbation(mass_scale=.7,stiffness_scale=.7,damping_scale=.7),40.,.020),
    ("force_constant_minus30pct",C.Perturbation(force_constant_scale=.7),40.,.020),
    ("position_delay2ms_noise5um",C.Perturbation(position_delay_s=.002,position_noise_std_m=5e-6),40.,.020),
    ("position_delay2ms_noise5um_gain20Hz",C.Perturbation(position_delay_s=.002,position_noise_std_m=5e-6),20.,.020),
    ("position_delay4ms_noise10um_gain20Hz",C.Perturbation(position_delay_s=.004,position_noise_std_m=10e-6),20.,.020),
    ("contact_drag20mN",C.Perturbation(lateral_drag_N=.020),40.,.020),
    ("combined_gain20Hz",C.Perturbation(mass_scale=1.3,stiffness_scale=1.3,damping_scale=1.3,
        force_constant_scale=.7,position_delay_s=.002,position_noise_std_m=5e-6,lateral_drag_N=.010),20.,.020),
    ("slow_contact200ms",C.Perturbation(),40.,.200),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writers",type=int,default=20)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing"))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    letters,provenance=D.load_uji();calibration=[l for l in letters if l.rep==1]
    heights=O.writer_xheights(calibration)
    writers=sorted(w for w in heights if w.startswith("tst"))[:args.writers]
    rows=[]
    for wi,writer in enumerate(writers):
        bank={l.char:[s/heights[writer] for s in l.strokes] for l in calibration if l.writer==writer}
        acceptance=L.Revision(0,0,"becau","because","completion","writer","writer","ASSUMED explicit acceptance for replay",0.)
        cache={}
        for name,perturb,hz,contact in SCENARIOS:
            if contact not in cache:
                lim=dataclasses.replace(R.MotionLimits(),radius_m=.003,hard_stop_m=.0032,
                                        lift_delay_s=contact,lower_delay_s=contact)
                cache[contact]=A.plan_from_acceptance(acceptance,bank,limits=lim)
            plan,trajectories,preflight=cache[contact]
            row={"writer":writer,"calibration_session":1,"scenario":name,"servo_hz":hz,
                 "contact_delay_s":contact,"preflight":preflight,"controllers":{}}
            if plan:
                for ff in (False,True):
                    sim,trace=C.replay(copy.deepcopy(plan),copy.deepcopy(trajectories),feedforward=ff,
                        servo_hz=hz,perturbation=dataclasses.replace(perturb,seed=812+wi))
                    row["controllers"]["feedforward" if ff else "feedback_only"]=sim
                    if wi==0 and ff:
                        np.savetxt(args.out/f"robustness_{name}_trace.csv",trace,delimiter=",",
                            header=",".join(sim["trace_columns"]),comments="")
            rows.append(row)
        print(f"robustness completed {writer}",flush=True)
    summary=[]
    for name,perturb,hz,contact in SCENARIOS:
        group=[r for r in rows if r["scenario"]==name]
        row={"scenario":name,"n_writers":len(group),"preflight_admitted":sum(bool(r["controllers"]) for r in group),
             "servo_hz":hz,"contact_delay_s":contact,"perturbation":dataclasses.asdict(perturb)}
        for policy in ("feedback_only","feedforward"):
            sims=[r["controllers"][policy] for r in group if r["controllers"]]
            done=[s for s in sims if s["state"]=="done"]
            errors=[l["simulated_ink_rms_reference_error_m"] for s in done for l in s["letters"]]
            reasons={}
            for s in sims:
                if s["state"]!="done":
                    reason=s["letters"][-1]["reason"];reasons[reason]=reasons.get(reason,0)+1
            row[policy]={"completed":len(done),"aborted":len(sims)-len(done),"abort_reasons":reasons,
                         "median_letter_rms_um_completed":float(np.median(errors)*1e6) if errors else None,
                         "max_current_A_all_attempts":max((l["peak_current_A"] for s in sims for l in s["letters"]),default=None)}
        summary.append(row)
    root=Path(__file__).resolve().parents[1]
    files=["ai3/reachable.py","ai3/layers.py","ai3/accepted_completion.py","ai3/completion_replay.py","ai3/planar_integrator.py","ai3/run_completion_robustness.py"]
    report={"protocol":__doc__,"dataset":provenance,"radius_mm":3.,"xheight_mm":3.,"new_blind_validation":False,
        "seed":"812 + writer index; same noise realization for paired controllers",
        "sensor_scope":"Noise is on stage position. Body/page registration and pose remain exact. Velocity is derived causally from the delayed noisy position at 500Hz, fixed80Hz low-pass, held between samples. Baseline ideal mode is explicitly labelled.",
        "contact_scope":"20ms is a fast research assumption; 200ms is a conservative sensitivity motivated by Rev K counterface calculations. Neither is a measured bidirectional contact response. No imaginary latch or force servo is assumed.",
        "summary":summary,"rows":rows,"code_sha256":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}}
    (args.out/"accepted_robustness.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=="__main__":main()
