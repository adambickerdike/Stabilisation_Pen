"""Compare two completed numerical corrections without changing either policy.

The same already-spent protocol, noise stream and controller clock are retained.
This reports step-size sensitivity; agreement is not physical model validation.
"""
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    base=Path("results/improvement/writing")
    paths=[base/f"numerical_correction_{dt}us"/"robust_observer_holdout.json" for dt in (50,25)]
    reports=[json.loads(p.read_text()) for p in paths]
    a,b=reports
    for key in ("specifications","design","policy_tick_s","sensor_control_tick_s","original_protocol_sha256"):
        assert a["protocol"][key]==b["protocol"][key],key
    assert a["protocol"]["code_sha256"]==b["protocol"]["code_sha256"]
    rows=[]
    for ra,rb in zip(a["rows"],b["rows"]):
        assert (ra["writer"],ra["perturbation"])==(rb["writer"],rb["perturbation"])
        for name,ca in ra["controllers"].items():
            cb=rb["controllers"][name]
            row={"writer":ra["writer"],"seed":ra["perturbation"]["seed"],"controller":name,
                 "supervisor_agrees":ca["state"]==cb["state"],
                 "actual_position_endpoint_agrees":ca["completed_with_true_tracking_tube"]==cb["completed_with_true_tracking_tube"],
                 "same_executed_letter_count":len(ca["letters"])==len(cb["letters"])}
            for metric in ("peak_actual_acceleration_m_s2","peak_actual_jerk_m_s3","peak_current_A","copper_energy_J"):
                left=max(l[metric] for l in ca["letters"]);right=max(l[metric] for l in cb["letters"])
                row[metric+"_relative_change"]=abs(left-right)/max(abs(right),1e-20)
            row["maximum_letter_duration_change_s"]=max(abs(la["simulated_time_s"]-lb["simulated_time_s"]) for la,lb in zip(ca["letters"],cb["letters"]))
            row["maximum_letter_ink_rms_change_um"]=max((abs(la["simulated_ink_rms_reference_error_m"]-lb["simulated_ink_rms_reference_error_m"])*1e6
                for la,lb in zip(ca["letters"],cb["letters"]) if la["simulated_ink_rms_reference_error_m"] is not None and lb["simulated_ink_rms_reference_error_m"] is not None),default=0.)
            rows.append(row)
    result={"scope":__doc__,"sources":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            "integrator":"coupled implicit midpoint; internal50vs25microseconds",
            "policy_sensor_clocks_fixed":True,"cases":len(a["rows"]),"admitted_policy_pairs":len(rows),
            "all_supervisor_decisions_agree":all(r["supervisor_agrees"] for r in rows),
            "all_position_endpoint_decisions_agree":all(r["actual_position_endpoint_agrees"] for r in rows),
            "all_executed_letter_counts_agree":all(r["same_executed_letter_count"] for r in rows),
            "maximum_letter_ink_rms_change_um":max(r["maximum_letter_ink_rms_change_um"] for r in rows),
            "maximum_letter_duration_change_s":max(r["maximum_letter_duration_change_s"] for r in rows),
            "rows":rows}
    for metric in ("peak_actual_acceleration_m_s2","peak_actual_jerk_m_s3","peak_current_A","copper_energy_J"):
        result["maximum_"+metric+"_relative_change"]=max(r[metric+"_relative_change"] for r in rows)
    (base/"numerical_convergence.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))


if __name__=="__main__":main()
