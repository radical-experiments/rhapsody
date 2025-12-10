import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy as np
import seaborn as sns
import argparse
from pathlib import Path


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
   

def _plot(outfile, mean_gpu, std_gpu, mean_cpu, std_cpu, mean_tput, std_tput):
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
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))  # increased width
    plt.subplots_adjust(wspace=0.3)  # add space between subplots

    # -------------------------------
    # Plot 1 — Resource Utilization
    # -------------------------------
    ax1.errorbar(x, mean_gpu_vals, yerr=std_gpu_vals,
                 fmt='o-', 
                 capsize=5, label='GPU Util (%)',
                 color=gpu_color, 
                 markersize=8, linewidth=2
                 )
    
    ax1.errorbar(x, mean_cpu_vals, yerr=std_cpu_vals,
                 fmt='o-', 
                 capsize=5, label='CPU Util (%)',
                 color=cpu_color, 
                 markersize=8, linewidth=2
                 )
    
    ax1.set_title("Resource Utilization", fontsize=16, fontweight='bold')
    ax1.set_ylabel("Utilization (%)", fontsize=13)
    ax1.set_xlabel("Node / Service / Pipeline", fontsize=13)
    ax1.set_xticks(x)
    ax1.set_xticklabels(x_labels, rotation=45, ha="right")
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.minorticks_on()
    ax1.grid(which='minor', axis='y', linestyle=':', alpha=0.2)
    ax1.legend()
    ax1.yaxis.set_major_locator(plt.MultipleLocator(10))

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
                 ha='center', va='bottom', fontsize=10)

    ax2.set_title("Throughput", fontsize=16, fontweight='bold')
    ax2.set_ylabel("Combined Tokens / second", fontsize=13)
    ax2.set_xlabel("Node / Service / Pipeline", fontsize=13)
    ax2.set_xticks(x)
    ax2.set_xticklabels(x_labels, rotation=45, ha="right")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.minorticks_on()
    ax2.grid(which='minor', axis='y', linestyle=':', alpha=0.2)

    # Scientific notation for y-axis
    ax2.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax2.ticklabel_format(style='sci', axis='y', scilimits=(0,0))

    # ------------------------------------------------------
    # Save and show figure
    # ------------------------------------------------------
    plt.savefig(outfile, dpi=200, bbox_inches='tight')

# --------------------------------------------------
# Main
# --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Plot CPU/GPU telemetry from JSON files.")
    parser.add_argument("directory", help="Directory containing telemetry checkpoint .json files")
    parser.add_argument("--out", default="average_utilization_throughput.png", help="Output figure filename")
    #parser.add_argument("--tpt", default="tpt.json", help="Output figure filename")
    args = parser.parse_args()

    mean_cpu = {}
    mean_gpu = {}
    std_cpu = {}
    std_gpu = {}
    mean_tput = {}
    std_tput = {}

    import json

    # with open(args.tpt, "r") as f:
    #     tput_data = json.load(f)

    for e, dir in EXPERIMENTS.items():
        dir = Path(args.directory, dir)

        tput_data = read_telemetry(dir)

        #tput = np.array(tput_data)
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

    _plot(args.out, mean_gpu, std_gpu, mean_cpu, std_cpu, mean_tput, std_tput)


if __name__ == "__main__":
    main()