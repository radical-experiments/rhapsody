import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import ScalarFormatter

# Add parent directory to path to import plot_config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import plot_config

# Configure matplotlib with consistent settings
plot_config.configure_matplotlib()

using_old_data = True
EXPERIMENTS = {
    's1': 's1.p10',
    's2': 's2.p20',
    's4': 's4.p40',
    's8': 's8.p80'
    }

def read_telemetry(path):
    print(f'\nReading inference data from directoty: {path}')
    data = {}

    for d in path.iterdir():
        if not d.is_dir():
            continue

        total = 0
        for f in d.iterdir():

            if not f.is_file() or 'infer' not in f.stem:
                continue
            print(f'Reading inference data from file: {f}')
            with open(f, "r") as f:
                tput_data = json.load(f)

            for tput_data1 in tput_data:
                for tput_data2 in tput_data1:
                    tokens_per_sec = tput_data2["total_tokens_per_second"]
                    hostname = tput_data2["hostname"]
                    data.setdefault(hostname, []).append(tokens_per_sec)

        print(f'\nCollected data for hosts: {data.keys()}')
        total += sum(sum(v) / len(v) for v in data.values())
    return total


# # --------------------------------------------------
# # Load metrics from a JSON file
# # --------------------------------------------------
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


def _plot(plot_type, outfile, single_df, mean_gpu, std_gpu, mean_cpu, std_cpu, mean_tput, std_tput):
    # ------------------------------------------------------
    # Data and labels
    # ------------------------------------------------------
    x_labels = [
        "1 | 1 | 10",
        "2 | 2 | 20",
        "4 | 4 | 40",
        "8 | 8 | 80",
    ]
    x = np.arange(len(x_labels))

    # Convert dict_values to NumPy arrays
    mean_gpu_vals = np.array(list(mean_gpu.values()))
    std_gpu_vals  = np.array(list(std_gpu.values()))
    mean_cpu_vals = np.array(list(mean_cpu.values()))
    std_cpu_vals  = np.array(list(std_cpu.values()))
    mean_tput_vals = np.array(list(mean_tput.values()))
    std_tput_vals  = np.array(list(std_tput.values()))

    # ------------------------------------------------------
    # Colors
    # ------------------------------------------------------
    colors = sns.color_palette("Set2", 3)
    gpu_color, cpu_color, tput_color = colors[0], colors[1], colors[2]

    # ------------------------------------------------------
    # Create figure with 2 subplots
    # ------------------------------------------------------
    #fig, (ax2, ax3) = plt.subplots(2, 1, figsize=(5, 7))  # increased width

    if plot_type == 'htp':
        fig, ax2 = plot_config.create_figure(1, 1)



    #fig.subplots_adjust(hspace=0.35)  # increase/decrease as needed

    #plt.subplots_adjust(wspace=0.3)  # add space between subplots

    # # -------------------------------
    # # Plot 1 — Resource Utilization
    # # -------------------------------
    # ax1.errorbar(x, mean_gpu_vals, yerr=std_gpu_vals,
    #              fmt='o-',
    #              capsize=5, label='GPU Util (%)',
    #              color=gpu_color,
    #              markersize=8, linewidth=2
    #              )

    # ax1.errorbar(x, mean_cpu_vals, yerr=std_cpu_vals,
    #              fmt='o-',
    #              capsize=5, label='CPU Util (%)',
    #              color=cpu_color,
    #              markersize=8, linewidth=2
    #              )

    # ax1.set_title("Resource Utilization", fontsize=12, fontweight='bold')
    # ax1.set_ylabel("Utilization (%)", fontsize=12, fontweight='bold')
    # ax1.set_xlabel("Node | Service Instance | Inference Client", fontsize=10, fontweight='bold')
    # ax1.set_xticks(x+0.35)
    # ax1.set_xticklabels(x_labels, rotation=0, ha="right")
    # ax1.grid(axis="y", linestyle="--", alpha=0.4)
    # ax1.minorticks_on()
    # ax1.grid(which='minor', axis='y', linestyle=':', alpha=0.2)
    # ax1.legend()
    # ax1.yaxis.set_major_locator(plt.MultipleLocator(10))

        # -------------------------------
        # Plot 2 — Throughput
        # -------------------------------
        bar_width = 0.6
        bars = ax2.bar(x, mean_tput_vals, width=bar_width,
                    yerr=std_tput_vals, capsize=5,
                    color=tput_color, edgecolor='black', alpha=0.8)

        # Annotate bar values (small adjustment for clarity)
        for i, val in enumerate(mean_tput_vals):
            ax2.text(x[i], val + std_tput_vals[i]*0.5, f'{val:.1e}',
                    ha='center', va='bottom', fontsize=plot_config.FONT_SIZE_ANNOTATION)

        ax2.set_title("Throughput")
        ax2.set_ylabel("Combined Tokens / second")
        ax2.set_xlabel("Node | Service Instance | Inference Client")
        ax2.set_xticks(x+0.4)
        ax2.set_xticklabels(x_labels, rotation=0, ha="right")
        ax2.grid(axis="y", linestyle="--", alpha=0.4)
        ax2.minorticks_on()
        ax2.grid(which='minor', axis='y', linestyle=':', alpha=0.2)

        # Scientific notation for y-axis
        ax2.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        ax2.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    elif plot_type == 'util':
        fig, ax3 = plot_config.create_figure(1, 1)


        # -------------------------------
        # Plot 3 — Urilization from single run
        # -------------------------------

        # GPU0
        if "gpu_0_utilization" in single_df:
            ax3.fill_between(
                single_df["timestamp"],
                single_df["gpu_0_utilization"],
                step="mid",
                alpha=0.4  ,
                color="#ff7f0e",
                label=f"GPU (%)",
            )

        # CPU
        if "cpu_percent" in single_df:
            ax3.fill_between(
                single_df["timestamp"],
                single_df["cpu_percent"],
                step="mid",
                alpha=0.4,
                color="#1f77b4",
                label=f"CPU (%)",
            )



        ax3.set_title(f"CPU + GPU Utilization")
        ax3.set_ylabel("Utilization (%)")
        ax3.grid(True, alpha=0.2)
        ax3.legend(loc="upper right")
        ax3.set_xlabel("Time (s)")

    else:
        print(f"Unknown plot_type: {plot_type}. Expected 'htp' or 'util'.")
        return

    # ------------------------------------------------------
    # Save and show figure
    # ------------------------------------------------------
    plot_config.save_figure(fig, outfile)

# --------------------------------------------------
# Main
# --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Plot CPU/GPU telemetry from JSON files.")
    parser.add_argument("directory", help="Directory containing telemetry checkpoint .json files")
    parser.add_argument("--out", default="average_utilization_throughput.png", help="Output figure filename")
    parser.add_argument("--experiment", default="s4", help="Output figure filename")
    parser.add_argument("--plot_type", default="htp", help="The type of the plot - htp or util")
    args = parser.parse_args()

    mean_cpu = {}
    mean_gpu = {}
    std_cpu = {}
    std_gpu = {}
    mean_tput = {}
    std_tput = {}

    if using_old_data:
        import json
        with open('tpt.json', "r") as f:
            tputs = json.load(f)

    for e, dir in EXPERIMENTS.items():
        dir = Path(args.directory, dir)

        if not using_old_data:
            tput_data = read_telemetry(dir)
        else:
            tput_data = np.array(tputs[e])

        mean_tput[e] = np.mean(tput_data)
        std_tput[e] = np.std(tput_data)

        gpu_util = []
        cpu_util = []

        for d in dir.iterdir():
            #print('d', d)
            directory = Path(d, 'telemetry-results')

            # Find telemetry files
            files = sorted(directory.glob("telemetry_checkpoint_*.json"))

            if not files:
                print("No telemetry files found in:", directory)
                return

            # Load all telemetry files into list
            dfs = []
            for f in files:
                try:
                    dfs.append(load_metrics(f))
                except Exception as e:
                    print("Error loading:", f, e)

            df = pd.concat(dfs, ignore_index=True)

            df["timestamp"] = df["timestamp"] - df["timestamp"].min()
            df = df.sort_values(["hostname", "timestamp"])

            if e == args.experiment:
                single_df = df

            df = df[(df["gpu_0_utilization"] > 5)]
            gpu_util.extend(df["gpu_0_utilization"].to_list())
            cpu_util.extend(df["cpu_percent"].to_list())


        std_cpu[e] = np.std(cpu_util)
        std_gpu[e] = np.std(gpu_util)
        mean_cpu[e] = np.mean(cpu_util)
        mean_gpu[e] = np.mean(gpu_util)


    std_cpu = dict(sorted(std_cpu.items()))
    std_gpu = dict(sorted(std_gpu.items()))
    mean_cpu = dict(sorted(mean_cpu.items()))
    mean_gpu = dict(sorted(mean_gpu.items()))
    std_tput = dict(sorted(std_tput.items()))
    mean_tput = dict(sorted(mean_tput.items()))

    hosts = sorted(single_df["hostname"].unique())
    first_host = hosts[0]
    single_df = single_df[single_df["hostname"] == first_host]



    _plot(args.plot_type, args.out, single_df, mean_gpu, std_gpu, mean_cpu, std_cpu, mean_tput, std_tput)


if __name__ == "__main__":
    main()