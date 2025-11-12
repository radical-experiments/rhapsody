#!/usr/bin/env python3
from datetime import datetime
import argparse
import glob
import os
import matplotlib.pyplot as plt
import numpy as np
import re

def process_log(log_path):
    earliest_running = None
    latest_done = None
    all_done = 0

    try:
        with open(log_path, "r") as log_file:
            for line in log_file:
                if "Submitted" in line:
                    try:
                        timestamp = line.split("│")[0].strip()
                        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                        if earliest_running is None or dt < earliest_running:
                            earliest_running = dt
                    except Exception:
                        continue

                elif "DONE" in line:
                    try:
                        timestamp = line.split("│")[0].strip()
                        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                        if latest_done is None or dt > latest_done:
                            latest_done = dt
                        all_done += 1
                    except Exception:
                        continue
    except FileNotFoundError:
        print(f"File not found: {log_path}")
        return None

    if earliest_running and latest_done:
        wall_time = (latest_done - earliest_running).total_seconds()
        throughput = all_done / wall_time if wall_time > 0 else 0
        print(f"📄 {os.path.basename(log_path)} → "
              f"Tasks: {all_done}, Overhead: {wall_time:.2f}s, Throughput: {throughput:.2f} tasks/s")
        return {
            "file": os.path.basename(log_path),
            "tasks": all_done,
            "wall_time": wall_time,
            "throughput": throughput,
            "mode": "weak" if "weak" in os.path.basename(log_path).lower() else "strong"
        }
    else:
        print(f"{os.path.basename(log_path)} → Missing 'Submitted' or 'DONE' entries.")
        return None


def parse_nodes_from_name(name):
    m = re.search(r"[._-]n(\d+)[._-]", name)
    return int(m.group(1)) if m else None

def plot_results(results):
    if not results:
        print("No valid data to plot.")
        return


    weak_results = [r for r in results if r["mode"] == "weak"]
    strong_results = [r for r in results if r["mode"] == "strong"]

    plt.style.use("seaborn-v0_8-whitegrid")
    # Smaller figsize for smaller plot area on paper, increased dpi for better clarity.
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.5), dpi=300) 
    # Larger font size for suptitle
    #fig.suptitle("Dragon.Batch + Rhapsody Integration Scaling (1-16 nodes)", fontsize=14, fontweight="bold", y=0.98)

    def aggregate(data, x_key):
        """Aggregate multiple runs with same x value."""
        agg = {}
        for r in data:
            xval = r[x_key]
            if xval not in agg:
                agg[xval] = {"throughput": [], "wall_time": []}
            agg[xval]["throughput"].append(r["throughput"])
            agg[xval]["wall_time"].append(r["wall_time"])

        xs = sorted(agg.keys())
        means_th = [np.mean(agg[x]["throughput"]) for x in xs]
        stds_th  = [np.std(agg[x]["throughput"]) for x in xs]
        means_wl = [np.mean(agg[x]["wall_time"]) for x in xs]
        stds_wl  = [np.std(agg[x]["wall_time"]) for x in xs]
        return xs, (means_th, stds_th), (means_wl, stds_wl)

    def plot_metric(ax, x, ymean, ystd, xlabel, ylabel, title, color):
        # Larger markersize and linewidth
        ax.plot(
            x, ymean, "-o", markersize=8, linewidth=3.5,
            color=color, markerfacecolor="white", markeredgewidth=2, label="mean"
        )

        ax.fill_between(
            x,
            np.array(ymean) - np.array(ystd),
            np.array(ymean) + np.array(ystd),
            color=color, alpha=0.15, label="±1σ"
        )
        if xlabel == "#Nodes":
            ax.set_xlim(0,18)

        # MODIFICATION 1: Smaller font size for data labels
        #for i, val in enumerate(ymean):
        #    ax.text(x[i], val + 0.3, f"{val:.1f}", fontsize=5, ha="center", va="bottom") # Reduced fontsize to 8
        # MODIFICATION 2: Added labelpad to x-axis labels
        ax.set_xlabel(xlabel, fontweight="bold", fontsize=10, labelpad=8) 
        ax.set_ylabel(ylabel, fontweight="bold", fontsize=10)
        ax.grid(alpha=0.4, linestyle="--")
        # Larger font size for legend
        ax.legend(fontsize=9, loc="best")
        # Ensure tick labels are also readable
        ax.tick_params(axis='both', which='major', labelsize=9)

    # --- Weak Scaling (top row) ---
    if weak_results:
        wx, (wth_m, wth_s), (wwl_m, wwl_s) = aggregate(weak_results, "tasks")
        
        # MODIFICATION 3: Adjusted y-coordinate for row titles
        weak_title = "Weak Scaling (2K-32K no-op funcs)"
        fig.text(0.5, 0.9, weak_title, ha='center', va='center', fontweight="bold", fontsize=11)
        
        plot_metric(axes[0, 0], wx, wth_m, wth_s, "#Tasks", "Throughput (tasks/s)", None, "#F57C00")
        plot_metric(axes[0, 1], wx, wwl_m, wwl_s, "#Tasks", "Overhead (s)", None, "#1565C0")
    else:
        # Larger font size for "No Logs" text
        for j in (0, 1):
            axes[0, j].text(0.5, 0.5, "No Weak Logs", ha="center", va="center", fontsize=14)

    # --- Strong Scaling (bottom row) ---
    if strong_results:
        for r in strong_results:
            r["nodes"] = parse_nodes_from_name(r["file"]) or 1
        sx, (sth_m, sth_s), (swl_m, swl_s) = aggregate(strong_results, "nodes")

        # MODIFICATION 3: Adjusted y-coordinate for row titles
        strong_title = "Strong Scaling (50K no-op funcs)"
        fig.text(0.5, 0.44, strong_title, ha='center', va='center', fontweight="bold", fontsize=11) # Adjusted y
        
        # MODIFICATION 4: Corrected xlabel for strong scaling plots to "#Nodes"
        plot_metric(axes[1, 0], sx, sth_m, sth_s, "#Nodes", "Throughput (tasks/s)", None, "#F57C00")
        plot_metric(axes[1, 1], sx, swl_m, swl_s, "#Nodes", "Overhead (s)", None, "#1565C0")
    else:
        # Larger font size for "No Logs" text
        for j in (0, 1):
            axes[1, j].text(0.5, 0.5, "No Strong Logs", ha="center", va="center", fontsize=14)


    # Force a large vertical space between subplot rows (e.g., hspace=1.0 or 2.0)
    plt.subplots_adjust(hspace=0.5, wspace=0.3)

    # REMOVED plt.tight_layout() because it overrides plt.subplots_adjust()
    # If the image is still cropped, you might need to adjust the `y` coordinates for the fig.text row titles.
    plt.savefig("n_sessions.png")
    print("Plot with error bars saved to n_sessions.png")

def main():
    parser = argparse.ArgumentParser(description="Process multiple log files and plot performance vs #tasks.")
    parser.add_argument("logs", nargs="+", help="Paths or glob patterns to log files (e.g., *.log)")
    args = parser.parse_args()

    log_files = []
    for pattern in args.logs:
        log_files.extend(glob.glob(pattern))

    if not log_files:
        print("No log files found.")
        return

    results = []
    for log_file in sorted(log_files):
        print(f"\nScanning: {log_file}")
        result = process_log(log_file)
        if result:
            results.append(result)

    plot_results(results)


if __name__ == "__main__":
    main()
