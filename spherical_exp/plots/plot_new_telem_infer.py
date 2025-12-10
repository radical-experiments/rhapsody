import json
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path


# --------------------------------------------------
# Load metrics from a JSON file
# --------------------------------------------------
def load_metrics(path):
    with open(path, "r") as f:
        data = json.load(f)

    rows = []
    for entry in data["metrics"]:
        ts = entry["timestamp"]
        metrics = entry["metrics"].copy()
        metrics["hostname"] = entry["hostname"]
        metrics["timestamp"] = ts
        rows.append(metrics)

    return pd.DataFrame(rows)

def plot_data(n_hosts, hosts, df, outfile):

    # --------------------------------------------------
    # Create figure with N subplots
    # --------------------------------------------------
    fig, axes = plt.subplots(
        n_hosts,
        1,
        figsize=(10, 4.5 * n_hosts),
        sharex=True,
        constrained_layout=True,
    )
   
    # Always iterable
    if n_hosts == 1:
        axes = [axes]

    # Colors & alpha
    alpha = 0.25
    colors = {
        "cpu": "#1f77b4",
        "gpu0": "#ff7f0e",
        "gpu1": "#2ca02c",
    }


    for ax, host in zip(axes, hosts):
        d = df[df["hostname"] == host]

        # GPU0
        if "gpu_0_utilization" in d:
            ax.fill_between(
                d["timestamp"],
                d["gpu_0_utilization"],
                step="mid",
                alpha=alpha  ,
                color=colors["gpu0"],
                label=f"GPU (%)",
            )

        # # GPU1
        # if "gpu_1_utilization" in d:
        #     ax.fill_between(
        #         d["timestamp"],
        #         d["gpu_1_utilization"],
        #        step="mid",
        #        alpha=alpha,
        #         color=colors["gpu1"],
        #         label="GPU1 (%)",
        #     )

        # CPU
        if "cpu_percent" in d:
            ax.fill_between(
                d["timestamp"],
                d["cpu_percent"],
                step="mid",
                alpha=alpha+0.2,
                color=colors["cpu"],
                label=f"CPU (%)",
            )

        ax.set_title(f"CPU + GPU Utilization — {host}", fontsize=13)
        ax.set_ylabel("Utilization (%)")
        ax.grid(True, alpha=0.2)
        ax.legend(loc="upper right")

    axes[-1].set_xlabel("Time (s)")

    fig.savefig(outfile, dpi=150)
    print("Saved:", outfile)

    
# --------------------------------------------------
# Main
# --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Plot CPU/GPU telemetry from JSON files.")
    parser.add_argument("directory", help="Directory containing telemetry checkpoint .json files")
    parser.add_argument("--out", default="all_nodes.png", help="Output figure filename")
    parser.add_argument("--nodes", default="all", help="Output figure filename")
    args = parser.parse_args()

    directory = Path(args.directory)

    # Find telemetry files
    files = sorted(directory.glob("telemetry_checkpoint_*.json"))

    if not files:
        print("No telemetry files found in:", directory)
        return

    print(f"Found {len(files)} telemetry files.")

    # Load all telemetry files into list
    dfs = []
    for f in files:
        try:
            print("Loading:", f)
            dfs.append(load_metrics(f))
        except Exception as e:
            print("Error loading:", f, e)

    df = pd.concat(dfs, ignore_index=True)
    df["timestamp"] = df["timestamp"] - df["timestamp"].min()

    df = df.sort_values(["hostname", "timestamp"])

    hosts = sorted(df["hostname"].unique())
    if args.nodes != 'all':
        hosts = [hosts[0]]
    n_hosts = len(hosts)

    print(f"Plotting {n_hosts} node subplots...")

    plot_data(n_hosts, hosts, df, args.out)



if __name__ == "__main__":
    main()