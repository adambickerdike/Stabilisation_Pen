"""Figures from saved study results; no model is tuned or simulation rerun."""
from pathlib import Path
import argparse
import json

import numpy as np


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("results/improvement/writing/numerical_correction_50us"))
    out=parser.parse_args().out
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9})
    M=np.diag([np.sin(np.deg2rad(50.)),1.])
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout="constrained")
    for policy,color in [("feedback_only","#b56a37"),("feedforward","#007d82")]:
        trace=np.loadtxt(out/f"accepted_{policy}_trace.csv",delimiter=",",skiprows=1)
        for letter in (0,1):
            a=trace[trace[:,1]==letter];contact=a[:,6]>.5;requested=a[:,7]>.5
            label=f"{policy.replace('_',' ')} · {'s' if letter==0 else 'e'}"
            axes[0].plot(np.where(contact,a[:,2]*1e3,np.nan),np.where(contact,a[:,3]*1e3,np.nan),color=color,ls="-" if letter==0 else "--",label=label)
            error=np.linalg.norm((a[:,2:4]-a[:,4:6])@M.T,axis=1)*1e6
            axes[1].plot(a[:,0],np.where(requested,error,np.nan),color=color,ls="-" if letter==0 else "--",label=label)
    axes[0].set(xlabel="Page x (mm)",ylabel="Page y (mm)",title="Simulated contacting suffix only; no fabricated old ink")
    axes[0].set_aspect("equal");axes[0].legend(fontsize=7)
    axes[1].axhline(150,color="#9e3347",ls=":",label="150 µm stage tracking threshold")
    axes[1].set(xlabel="Time including assumed pen-up reposition (s)",ylabel="Stage-frame error to reference (µm)",title="Feedback failure includes its finite-lift contact tail")
    axes[1].legend(fontsize=7)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle("SIMULATION · UJI tst_UJI_W12 · hypothetical 3 mm stage · ideal sensing, 20 ms contact · no human result",fontsize=10)
    fig.savefig(out/"accepted_execution_stageframe.png",dpi=180);fig.savefig(out/"accepted_execution_stageframe.svg");plt.close(fig)
    holdout=out/"robust_observer_holdout.json"
    if not holdout.exists():return
    h=json.loads(holdout.read_text());s=h["summary"][0]
    assessment=json.loads((out/"robust_observer_assessment.json").read_text())
    labels=["All fixed\nscenarios","Preflight\nadmitted","Feedforward\nposition success","Observer\nposition success","Observer position\nAND rate success"]
    values=[s["cases"],s["admitted"],s["gain_matched_path_feedforward"]["completed_with_true_tracking_tube"],
            s["bounded_observer"]["completed_with_true_tracking_tube"],
            assessment["summary"]["bounded_observer"]["completed_position_and_actual_rate_limits"]]
    fig,axes=plt.subplots(1,2,figsize=(11,4.3),layout="constrained")
    bars=axes[0].bar(labels,values,color=["#a5aab1","#527f9b","#b56a37","#007d82","#9e3347"])
    axes[0].tick_params(axis="x",labelsize=7)
    axes[0].bar_label(bars);axes[0].set(ylim=(0,s["cases"]*1.12),ylabel="Accepted two-letter scenarios",title="Corrected same cases; full-plan denominator")
    traces=sorted(out.glob("robust_observer_holdout_*_new_mixed_perturbations_200ms_contact.csv"))
    for index,path in enumerate(traces):
        a=np.loadtxt(path,delimiter=",",skiprows=1);error=np.linalg.norm((a[:,2:4]-a[:,4:6])@M.T,axis=1)*1e6
        ink=(a[:,6]>.5)&(a[:,7]>.5)
        axes[1].plot(a[:,0],np.where(ink,error,np.nan),lw=1,label=f"Predeclared first writer, case {index+1}")
    axes[1].axhline(150,color="#9e3347",ls=":",label="Tracking-tube endpoint")
    axes[1].set(xlabel="Time (s)",ylabel="Actual stage error during requested/contacting ink (µm)",title="First three fixed cases, including aborted tails")
    axes[1].legend(fontsize=7)
    for ax in axes:ax.grid(axis="y",alpha=.2)
    fig.suptitle("SIMULATION ONLY · generic 3 mm stage · corrected numerics, same cases/seeds · 200 ms contact · no retuning",fontsize=10)
    fig.savefig(out/"robust_observer_holdout.png",dpi=180);fig.savefig(out/"robust_observer_holdout.svg");plt.close(fig)


if __name__=="__main__":main()
