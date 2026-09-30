"""Publication-style figure of the frozen causal-controller experiment."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "causal_controller_results.json").read_text())
pairs = d["pairs"]
modes = ["old_causal400", "causal80"]
labels = ["Causal Hall, old 400 Hz gains", "Causal Hall, repaired 80 Hz gains"]
colors = ["#748393", "#087F8C"]
groups = ["clean", "mild", "large"]
groups_text = ["No added tremor", "0.30 mm disturbance", "1.72 mm disturbance"]
cluster_rng = np.random.default_rng(998)


def interval(group, mode, metric):
    selected = [p for p in pairs if group == "all" or p["case"]["class"] == group]
    writers = sorted({p["case"]["writer"] for p in selected})
    means = np.array([np.mean([p[mode][metric] for p in selected if p["case"]["writer"] == w]) for w in writers])
    resamples = means[cluster_rng.integers(0, len(means), (5000, len(means)))].mean(axis=1)
    return means.mean(), np.quantile(resamples, [.025, .975])


plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.labelcolor": "#263442",
                     "xtick.color": "#263442", "ytick.color": "#263442", "svg.fonttype": "none"})
fig, axes = plt.subplots(2, 2, figsize=(12.6, 9.4))
fig.subplots_adjust(left=.07, right=.97, top=.81, bottom=.20, wspace=.25, hspace=.46)
fig.suptitle("A causal controller repair reduces instability", x=.055, y=.978, ha="left", fontsize=20, weight="bold")
fig.text(.055, .929, "Rev J simulation  •  45 frozen paired cases  •  same Hall and contact sensors  •  common clean target", fontsize=10.5)

ax = axes[0, 0]
x = np.arange(3)
for mi, mode in enumerate(modes):
    summaries = [interval(g, mode, "rms_um") for g in groups]
    vals = np.array([s[0] for s in summaries])
    err = np.array([[s[0]-s[1][0] for s in summaries], [s[1][1]-s[0] for s in summaries]])
    pos = x + (mi-.5)*.36
    ax.bar(pos, vals, .34, yerr=err, capsize=3, color=colors[mi], label=labels[mi], ecolor="#344250")
    for xx, val, bounds in zip(pos, vals, summaries):
        ax.text(xx, bounds[1][1]+15, f"{val:.0f}", ha="center", va="bottom", fontsize=9, weight="bold")
ax.set(xticks=x, xticklabels=["None", "0.30 mm", "1.72 mm"], ylabel="Mean trajectory RMS error (µm)", xlabel="Synthetic hand-disturbance amplitude")
ax.set_title("A  Error against the same clean target", loc="left", pad=12)
ax.grid(axis="y", alpha=.15)
ax.set_axisbelow(True)

ax = axes[0, 1]
for mi, mode in enumerate(modes):
    mean, ci = interval("all", mode, "coil_power_W")
    ax.bar(mi, mean, .52, color=colors[mi], yerr=np.array([[mean-ci[0]], [ci[1]-mean]]), capsize=4, ecolor="#344250")
    ax.text(mi, ci[1]+.15, f"{mean:.3f} W", ha="center", va="bottom", weight="bold")
ax.set(xticks=[0, 1], xticklabels=["400 Hz", "80 Hz"], ylabel="Mean copper dissipation (W)", ylim=(0, 9.9))
ax.set_title("B  Electrical cost of the instability", loc="left", pad=12)
ax.text(.98, .89, "80.6% lower mean copper power\nWinding temperature still reaches 65.7°C", transform=ax.transAxes,
        ha="right", va="top", fontsize=9.5, bbox=dict(boxstyle="round,pad=.5", facecolor="#EEF6F6", edgecolor="none"))
ax.grid(axis="y", alpha=.15)
ax.set_axisbelow(True)

required = sum(p["causal80"]["reference_ink_s"] for p in pairs)
duration = sum(p["causal80"]["duration_s"] for p in pairs)
lift = duration-required
ink_rates = {}
ax = axes[1, 0]
for mi, mode in enumerate(modes):
    missing = sum(p[mode]["missing_fraction"]*p[mode]["duration_s"] for p in pairs)
    extra = sum(p[mode]["extra_fraction"]*p[mode]["duration_s"] for p in pairs)
    rates = np.array([missing/required, extra/lift])*100
    ink_rates[mode] = {"missing_seconds": missing, "missing_percent_required_ink": rates[0],
                       "extra_seconds": extra, "extra_percent_required_lift": rates[1]}
    pos = np.arange(2)+(mi-.5)*.36
    ax.bar(pos, rates, .34, color=colors[mi])
    for xx, val in zip(pos, rates):
        ax.text(xx, val+.6, f"{val:.2f}%", ha="center", va="bottom", fontsize=9, weight="bold")
ax.set(xticks=[0, 1], xticklabels=["Missing ink /\nrequired ink time", "Extra ink /\nrequired lift time"],
       ylabel="Fraction of the stated time denominator (%)", ylim=(0, 33))
ax.set_title("C  Missing ink improves; extra ink rises", loc="left", pad=12)
ax.grid(axis="y", alpha=.15)
ax.set_axisbelow(True)

ax = axes[1, 1]
jitter = np.random.default_rng(909)
for gi, group in enumerate(groups):
    subset = [p for p in pairs if p["case"]["class"] == group]
    ratios = np.array([p["causal80"]["rms_um"]/p["old_causal400"]["rms_um"] for p in subset])
    ax.scatter(gi+jitter.uniform(-.15, .15, len(ratios)), ratios, s=38, color=["#087F8C", "#AC7020", "#6E55A0"][gi],
               alpha=.8, edgecolor="white", linewidth=.6, zorder=3)
ax.axhline(1, color="#A53434", ls="--", lw=1.1)
ax.set(xticks=[0, 1, 2], xticklabels=["None", "0.30 mm", "1.72 mm"], ylabel="80 Hz / 400 Hz trajectory error",
       xlabel="Synthetic hand-disturbance amplitude", yscale="log", ylim=(.12, 1.5))
ax.set_yticks([.2, .5, 1.], labels=["0.2", "0.5", "1.0"])
ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.text(.97, .14, "5 of 45 cases have worse error\nLargest repaired error: 2.181 mm", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=9, bbox=dict(boxstyle="round,pad=.35", facecolor="white", alpha=.85, edgecolor="none"))
ax.set_title("D  Every case remains visible", loc="left", pad=12)
ax.grid(axis="y", alpha=.15, which="both")

handles, legend_labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, legend_labels, loc="upper left", bbox_to_anchor=(.055, .904), ncol=2, frameon=False, fontsize=10)
fig.text(.055, .09, "Each class: 15 cases = 5 synthetic writers × 3 frequencies. Error and power bars are case means; intervals are descriptive 95% writer-cluster bootstraps.", fontsize=8.4)
fig.text(.055, .065, f"Ink rates pool {duration:.3f} s scored time: {required:.4f} s required ink and {lift:.4f} s required lift. Each note follows 3 s rest, then 2.5 s writing.", fontsize=8.4)
fig.text(.055, .04, "Proposed mechanics and sensor parameters remain unmeasured. This is a stability repair, with no demonstrated word-readability, patient or thermal-safety benefit.", fontsize=8.4)
fig.savefig(HERE / "causal_controller_comparison.png", dpi=190, facecolor="white")
fig.savefig(HERE / "causal_controller_comparison.svg", facecolor="white")
(HERE / "figure_metrics.json").write_text(json.dumps({"scored_seconds": duration, "required_ink_seconds": required,
    "required_lift_seconds": lift, "ink_rates": ink_rates, "source": "causal_controller_results.json"}, indent=2)+"\n")
print("Wrote comparison PNG/SVG and explicit denominator metadata")
