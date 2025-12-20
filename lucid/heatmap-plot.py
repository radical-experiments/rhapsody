import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Exact data from the figure
# -----------------------------
throughput = np.array([
    [1261.4, 1515.7, 1716.8, 1829.3],
    [1250.9, 1499.8, 1690.5, 1815.9],
    [1262.7, 1517.3, 1710.6, 1839.9],
])

x_labels = [4, 6, 8, 10]
y_labels = [65536, 98304, 131072]

# -----------------------------
# Plot
# -----------------------------
fig, ax = plt.subplots(figsize=(6, 4))

im = ax.imshow(
    throughput,
    cmap="cividis",
    aspect="auto"
)

# Colorbar
cbar = fig.colorbar(im, ax=ax)
cbar.set_label("tokens/s", fontsize=14, fontweight="bold",)
cbar.ax.tick_params(labelsize=14)

# Axis labels
ax.set_xlabel("max_num_seqs", fontsize=14, fontweight="bold",)
ax.set_ylabel("max_num_batched_tokens", fontsize=14, fontweight="bold",)

# Ticks
ax.set_xticks(np.arange(len(x_labels)))
ax.set_yticks(np.arange(len(y_labels)))
ax.set_xticklabels(x_labels, fontsize=13)
ax.set_yticklabels(y_labels, fontsize=13)

# Title
ax.set_title(
    "Throughput (total tokens / s)",
    fontsize=14,
    fontweight="bold"
)

# -----------------------------
# Annotate cells
# -----------------------------
for i in range(throughput.shape[0]):
    for j in range(throughput.shape[1]):
        ax.text(
            j,
            i,
            f"{throughput[i, j]:.1f}",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color="white" if j < 2 else "black"
        )

plt.tight_layout()
plt.savefig('throughput_heatmap_cividis_improved.png', dpi=600)

