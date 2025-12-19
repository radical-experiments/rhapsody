import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# -----------------------------
# Global style: bigger text + bold key items
# -----------------------------
plt.rcParams.update({
"font.size": 14,          # base size
"axes.titlesize": 18,
"axes.labelsize": 16,
"xtick.labelsize": 14,
"ytick.labelsize": 14,
"legend.fontsize": 14,
"axes.titleweight": "bold",
"axes.labelweight": "bold",
})

# Data
x_vals = np.array([1, 2, 3, 4])

# Left-series (Randomized Routing)
left_y   = np.array([1839.85, 2897.21, 4440.84, 5887.62])
left_err = np.array([0.0,     337.87,  489.49,  610.33])

# Right-series (Balanced Routing)
right_y = np.array([np.nan, 3426.35, 4992.62, 6902.01])

# Bottleneck (x=1)
bottleneck = left_y[0]

fig, ax = plt.subplots(figsize=(8, 4.8))

bar_w = 0.35
idx = np.arange(len(x_vals))  # categorical positions: 0,1,2,3

# x=1: baseline bar (different color, separate legend entry)
baseline_color = "tab:gray"
bars_left_x1 = ax.bar(
    idx[0],
    left_y[0],
    width=bar_w,
    yerr=left_err[0],
    capsize=6,
    color=baseline_color,
    label="_nolegend_"  # handle baseline legend manually
)

# x=2..4: grouped bars (Randomized Routing always present)
bars_left = ax.bar(
    idx[1:] - bar_w/2,
    left_y[1:],
    width=bar_w,
    yerr=left_err[1:],
    capsize=6,
    label="Randomized Routing"
)

# x=2..4: grouped bars (Balanced Routing)
mask = ~np.isnan(right_y[1:])
bars_right = ax.bar(
    idx[1:][mask] + bar_w/2,
    right_y[1:][mask],
    width=bar_w,
    label="Balanced Routing"
)

# ---- Annotate factor vs bottleneck on top of each bar (above error bars) ----
def annotate_factors(bar_container, errs=None, pad_points=8):
    for k, rect in enumerate(bar_container):
        h = rect.get_height()
        if np.isnan(h):
            continue

        e = 0.0
        if errs is not None:
            e = float(errs[k])

        factor = h / bottleneck

        # place label above the error bar top
        y_top = h + e

        ax.annotate(
            f"{factor:.2f}×",
            xy=(rect.get_x() + rect.get_width() / 2, y_top),
            xytext=(0, pad_points),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold"
        )

# baseline has one bar + one error
annotate_factors(bars_left_x1, errs=left_err[0:1], pad_points=8)

# randomized routing bars (x=2..4) have 3 errors
annotate_factors(bars_left, errs=left_err[1:], pad_points=8)

# balanced routing bars have no error bars provided
annotate_factors(bars_right, errs=None, pad_points=8)

# Axes / labels
ax.set_xticks(idx)
ax.set_xticklabels([str(v) for v in x_vals], fontweight="bold")
ax.set_xlabel("number of services")
ax.set_ylabel("overall throughput (token/s)")
ax.set_title("strong scaling behavior of data parallelism in hypothesis generation pipeline")

ax.grid(axis="y", alpha=0.3)

# --- Y axis limit ---
ax.set_ylim(0, 8000)

# Legend: Baseline + the two routing methods
handles, labels = ax.get_legend_handles_labels()
handles = [Patch(facecolor=baseline_color, label="Baseline")] + handles
labels = ["Baseline"] + labels

# Deduplicate (in case anything repeats)
uniq = dict(zip(labels, handles))
leg = ax.legend(uniq.values(), uniq.keys())

# Bold legend text
for t in leg.get_texts():
    t.set_fontweight("bold")

plt.tight_layout()

# Save file
out_png = "strong_scaling_barplot.png"
plt.savefig(out_png, dpi=300, bbox_inches="tight")

plt.show()
