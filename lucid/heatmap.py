import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Global style: bigger text + bold key items
# -----------------------------
plt.rcParams.update({
    # overall font control
    "font.size": 14,          # base size (affects many defaults)
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,

    # make the most important stuff bold
    "axes.titleweight": "bold",
    "axes.labelweight": "bold",
})

# ---- data ----
data = [
    (65536, 4, 1261.4301817044552),
    (65536, 6, 1515.7404272441263),
    (65536, 8, 1716.7802505716713),
    (65536,10, 1829.274689749804),

    (98304, 4, 1250.8552219779297),
    (98304, 6, 1499.76811954388),
    (98304, 8, 1690.5282894821173),
    (98304,10, 1815.8623181167143),

    (131072,4, 1262.6942152215943),
    (131072,6, 1517.3071296706512),
    (131072,8, 1710.6447819297132),
    (131072,10,1839.8502835491163),
]

df = pd.DataFrame(data, columns=["bts", "seqs", "throughput_total_tok_per_s"])

# Build heatmap matrix: rows=bts, cols=seqs
pivot = (
    df.pivot(index="bts", columns="seqs", values="throughput_total_tok_per_s")
      .sort_index(axis=0)
      .sort_index(axis=1)
)

fig, ax = plt.subplots(figsize=(8, 4.3))

im = ax.imshow(pivot.values.astype(float), aspect="auto",
               interpolation="nearest", cmap="cividis")

ax.set_xticks(np.arange(pivot.shape[1]))
ax.set_xticklabels([str(c) for c in pivot.columns], fontweight="bold")
ax.set_yticks(np.arange(pivot.shape[0]))
ax.set_yticklabels([str(r) for r in pivot.index], fontweight="bold")

ax.set_xlabel("max_num_seqs")
ax.set_ylabel("max_num_batched_tokens")
ax.set_title("Throughput (total tokens / s)")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("tokens/s", fontweight="bold")

# Make colorbar tick labels bigger + bold
cbar.ax.tick_params(labelsize=14)
for t in cbar.ax.get_yticklabels():
    t.set_fontweight("bold")

# Annotate with values; switch text color based on cell brightness
vals = pivot.values.astype(float)
vmin, vmax = np.nanmin(vals), np.nanmax(vals)
norm = (vals - vmin) / (vmax - vmin + 1e-12)

for i in range(vals.shape[0]):
    for j in range(vals.shape[1]):
        v = vals[i, j]
        txt_color = "white" if norm[i, j] < 0.50 else "black"
        ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                color=txt_color, fontsize=14, fontweight="bold")

# Cell borders
ax.set_xticks(np.arange(-.5, pivot.shape[1], 1), minor=True)
ax.set_yticks(np.arange(-.5, pivot.shape[0], 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.0)
ax.tick_params(which="minor", bottom=False, left=False)

plt.tight_layout()
plt.savefig("throughput_heatmap_cividis.png", dpi=200, bbox_inches="tight")
Plt.show() 
