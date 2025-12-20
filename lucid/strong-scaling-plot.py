import matplotlib.pyplot as plt
import numpy as np

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
fig, ax = plt.subplots(figsize=(6, 4))

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
    fontsize=10,
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
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        x + width / 2,
        balanced[i] + balanced_err[i] + 150,
        balanced_speedup[i],
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )

# -----------------------------
# Styling for publication
# -----------------------------
ax.set_xlabel("number of services", fontsize=14, fontweight="bold")
ax.set_ylabel("Throughput (token/s)", fontsize=14, fontweight="bold")

ax.set_title(
    "Strong Scaling of Hypothesis Generation",
    fontsize=14,
    fontweight="bold",
)

ax.set_xticks(services)
ax.tick_params(axis="both", labelsize=13)

ax.legend(fontsize=13, frameon=True)
ax.grid(axis="y", alpha=0.3)

ax.set_ylim(0, 8000)

plt.tight_layout()
plt.savefig('strong_scaling_barplot_improved.png', dpi=600)

