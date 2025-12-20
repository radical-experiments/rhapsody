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
fig, ax = plot_config.create_figure(1, 1)

im = ax.imshow(
    throughput,
    cmap="cividis",
    aspect="auto"
)

# Colorbar
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("tokens/s")
cbar.ax.tick_params(labelsize=plot_config.FONT_SIZE_TICK)

# Axis labels
ax.set_xlabel("max_num_seqs")
ax.set_ylabel("max_num_batched_tokens")

# Ticks
ax.set_xticks(np.arange(len(x_labels)))
ax.set_yticks(np.arange(len(y_labels)))
ax.set_xticklabels(x_labels)
ax.set_yticklabels(y_labels)

# Title
ax.set_title("Throughput (total tokens / s)")

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
            fontsize=plot_config.FONT_SIZE_ANNOTATION,
            fontweight="bold",
            color="white" if j < 2 else "black"
        )

plot_config.save_figure(fig, 'throughput_heatmap_cividis_improved.png')
