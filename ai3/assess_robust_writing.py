"""Post-evaluation accounting of a frozen holdout; never changes its controller.

The registered primary endpoint is completion within the true position tube.
This secondary audit additionally asks whether actual acceleration and jerk
stay inside the provisional reference limits. These distinct endpoints must not
be merged into a claim of physical feasibility.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing/numerical_correction_50us"))
    out=parser.parse_args().out
    path=out/"robust_observer_holdout.json";report=json.loads(path.read_text())
    rows=report["rows"];admitted=[r for r in rows if r["controllers"]]
    summaries={}
    for policy in ("gain_matched_path_feedforward","bounded_observer"):
        sims=[r["controllers"][policy] for r in admitted]
        complete=[s for s in sims if s["completed_with_true_tracking_tube"]]
        smooth=[s for s in complete if all(l["peak_actual_acceleration_m_s2"]<=2. and
                  l["peak_actual_jerk_m_s3"]<=300. for l in s["letters"])]
        summaries[policy]={"all_fixed_cases":len(rows),"preflight_admitted":len(sims),
            "completed_position_tube":len(complete),"completed_position_and_actual_rate_limits":len(smooth),
            "median_required_ink_contact_fraction_all_admitted":float(np.median([s["ink_accounting"]["required_phase_contact_fraction"] for s in sims])),
            "median_post_abort_contact_seconds_aborted":float(np.median([s["ink_accounting"]["post_abort_contact_time_s"] for s in sims if s["state"]!="done"])) if policy=="bounded_observer" else None,
            "median_extra_contact_seconds_all_admitted":float(np.median([s["ink_accounting"]["extra_contact_outside_required_phases_s"] for s in sims])),
            "peak_actual_acceleration_m_s2_all_attempts":max(l["peak_actual_acceleration_m_s2"] for s in sims for l in s["letters"]),
            "peak_actual_jerk_m_s3_all_attempts":max(l["peak_actual_jerk_m_s3"] for s in sims for l in s["letters"]),
            "peak_voltage_V_all_attempts":max(l["peak_voltage_V"] for s in sims for l in s["letters"]),
            "peak_current_A_all_attempts":max(l["peak_current_A"] for s in sims for l in s["letters"])}
        if complete:
            summaries[policy]["successful_peak_actual_acceleration_range_m_s2"]=[min(max(l["peak_actual_acceleration_m_s2"] for l in s["letters"]) for s in complete),max(max(l["peak_actual_acceleration_m_s2"] for l in s["letters"]) for s in complete)]
            summaries[policy]["successful_peak_actual_jerk_range_m_s3"]=[min(max(l["peak_actual_jerk_m_s3"] for l in s["letters"]) for s in complete),max(max(l["peak_actual_jerk_m_s3"] for l in s["letters"]) for s in complete)]
    rates=[]
    for writer in sorted({r["writer"] for r in rows}):
        group=[r for r in rows if r["writer"]==writer]
        rates.append(sum(bool(r["controllers"]) and r["controllers"]["bounded_observer"]["completed_with_true_tracking_tube"] for r in group)/len(group))
    boots=np.random.default_rng(51029).choice(rates,(5000,len(rates)),replace=True).mean(1)
    result={"scope":__doc__,"source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "reference_acceleration_limit_m_s2":2.,"reference_jerk_limit_m_s3":300.,
        "summary":summaries,"position_endpoint_writer_cluster_bootstrap_95pct":np.quantile(boots,[.025,.975]).tolist(),
        "bootstrap_scope":"20 already-seen UJI writers with3 fixed simulated cases each. Same spent protocol after numerical correction; not fresh validation or a clinical confidence interval.",
        "jerk_scope":"Peak internal finite differences hold contact fixed; binary contact acceleration jumps are separately reported and do not have a finite physical jerk bound. No completed case even passes the constant-contact rate screen.",
        "conclusion":"Bounded observer/recovery improves position tracking in some cases, but no holdout completion meets both actual rate limits. Unready for physical deployment; no claimed human handwriting benefit."}
    (out/"robust_observer_assessment.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
