import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path to import plot_config
sys.path.insert(0, str(Path(__file__).parent.parent))
import plot_config

# Configure matplotlib with consistent settings
plot_config.configure_matplotlib()

# -----------------------------
# Exact data used in the figure
# -----------------------------
services = np.array([1, 2, 3, 4])

baseline = np.array([1800])
randomized = np.array([2826, 4338, 5760])
balanced = np.array([3348, 4878, 6750])

# Error bars (as shown in the original figure)
randomized_err = np.array([250, 350, 450])
balanced_err = np.array([200, 300, 400])

# Speedup annotations
randomized_speedup = ["1.57×", "2.41×", "3.20×"]
balanced_speedup = ["1.86×", "2.71×", "3.75×"]

# -----------------------------
# Plot
# -----------------------------
fig, ax = plot_config.create_figure(1, 1)

width = 0.28

# Baseline (single bar)
ax.bar(
    services[0],
    baseline,
    width=width,
    color="gray",
    label="Baseline"
)
ax.text(
    services[0],
    baseline[0] + 150,
    "1.00×",
    ha="center",
    va="bottom",
    fontsize=plot_config.FONT_SIZE_ANNOTATION,
    fontweight="bold"
)

# Randomized routing
ax.bar(
    services[1:] - width / 2,
    randomized,
    width=width,
    yerr=randomized_err,
    capsize=5,
    label="Randomized Routing"
)

# Balanced routing
ax.bar(
    services[1:] + width / 2,
    balanced,
    width=width,
    #yerr=balanced_err,
    capsize=5,
    label="Balanced Routing"
)

# Speedup annotations
for i, x in enumerate(services[1:]):
    ax.text(
        x - width / 2,
        randomized[i] + randomized_err[i] + 150,
        randomized_speedup[i],
        ha="center",
        va="bottom",
        fontsize=plot_config.FONT_SIZE_ANNOTATION,
        fontweight="bold",
    )
    ax.text(
        x + width / 2,
        balanced[i] + balanced_err[i] + 150,
        balanced_speedup[i],
        ha="center",
        va="bottom",
        fontsize=plot_config.FONT_SIZE_ANNOTATION,
        fontweight="bold",
    )

# -----------------------------
# Styling for publication
# -----------------------------
ax.set_xlabel("number of services")
ax.set_ylabel("Throughput (token/s)")

ax.set_title("Strong Scaling of Hypothesis Generation")

ax.set_xticks(services)

ax.legend(frameon=True, loc='upper left')
ax.grid(axis="y", alpha=0.3)

ax.set_ylim(0, 8000)

plot_config.save_figure(fig, 'strong_scaling_barplot_improved.png')

