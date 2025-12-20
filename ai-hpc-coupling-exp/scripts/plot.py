#!/usr/bin/env python
"""
Plot: ROSE+Memory Coupling vs ROSE+Filesystem with RHAPSODY overheads
Updated: Single figure with 3 subplots
"""

import glob
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path to import plot_config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import plot_config

# Configure matplotlib with consistent settings (LARGE size for 1.0\textwidth)
plot_config.configure_matplotlib(size='large')

# -----------------------------
# 1-Parse RHAPSODY log
# -----------------------------
def parse_rhapsody_log(log_file):
    """
    Parse a Rhapsody log where a single 'Submitting batch of N tasks' line
    corresponds to N subsequent 'task.xxx is in RUNNING state' lines.
    Return a list of dicts with 'submit' and 'running' datetime pairs per task.
    """
    task_times = []
    with open(log_file, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        parts = line.split("│")
        if len(parts) < 2:
            i += 1
            continue
        timestamp_str = parts[0].strip()
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            i += 1
            continue

        if "Submitting batch of" in line:
            # Extract number of tasks submitted in this batch
            m = re.search(r'Submitting batch of (\d+) tasks', line)
            if not m:
                i += 1
                continue
            batch_size = int(m.group(1))
            submit_time = timestamp

            # Next batch_size lines should be RUNNING states
            running_times = []
            for j in range(batch_size):
                i += 1
                if i >= len(lines):
                    break
                run_line = lines[i]
                if "is in RUNNING state" not in run_line:
                    # Unexpected format, skip
                    continue
                run_parts = run_line.split("│")
                if len(run_parts) < 2:
                    continue
                run_timestamp_str = run_parts[0].strip()
                try:
                    run_timestamp = datetime.strptime(run_timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    continue
                # Save each task's submit and running times
                task_times.append({"submit": submit_time, "running": run_timestamp})
            i += 1
        else:
            i += 1
    return task_times


# -----------------------------
# 2- Load JSON results
# -----------------------------
def load_results(results_dir='../data/1-8nodes-results/results'):
    results_dir = Path(results_dir)

    redis_results = defaultdict(list)
    fs_results = defaultdict(list)

    # Expect filenames like: redis_nodes4_run2.json
    pattern = re.compile(r'(redis|filesystem)_nodes(\d+)_run\d+\.json')

    for json_file in results_dir.glob('*.json'):
        m = pattern.match(json_file.name)
        if not m:
            continue
        mode, nodes = m.groups()
        nodes = int(nodes)

        with open(json_file, 'r') as f:
            data = json.load(f)

        if mode == 'redis':
            redis_results[nodes].append(data)
        else:
            fs_results[nodes].append(data)

    return redis_results, fs_results

# -----------------------------
# 3- Attach RHAPSODY overhead to results
# -----------------------------
def attach_rhapsody_overhead(redis_results, logs_pattern="../data/1-8nodes-results/rose.dragon.*.log"):
    log_files = glob.glob(logs_pattern)
    for log_file in log_files:
        m = re.search(r"n(\d+)\.w(\d+)\.sim(\d+)\.train(\d+)\.r(\d+)", log_file)
        if not m:
            continue
        n, w, sim, train, r = map(int, m.groups())
        task_times = parse_rhapsody_log(log_file)

        # Attach to matching result
        if n in redis_results:
            for d in redis_results[n]:
                d["task_times"] = task_times
                rhapsody_overhead = sum(
                    (ts['running'] - ts['submit']).total_seconds() for ts in task_times
                )
                wall = d['timing']['wall_clock_time']
                compute = d['breakdown']['total_computation_time']
                transfer = d['breakdown']['total_data_transfer_time']
                orchestration = wall - compute - transfer

                # Ensure no negative values
                rose_overhead = max(orchestration - rhapsody_overhead, 0)

                d["rhapsody_overhead"] = rhapsody_overhead
                d["rose_overhead"] = rose_overhead

# -----------------------------
# 4- Plotting function (3 subplots)
# -----------------------------
def plot_all_in_one(redis_results, fs_results, output_file='combined_plots.png'):
    nodes = sorted(set(list(redis_results.keys()) + list(fs_results.keys())))
    fig, (ax1, ax2, ax3) = plot_config.create_figure(1, 3, figsize=(16, 4))
    x = np.arange(len(nodes))
    width = 0.35

    # --------- Subplot 1: Total Runtime ---------
    redis_times, redis_err, fs_times, fs_err = [], [], [], []

    for n in nodes:
        if n in redis_results:
            times = [d['timing']['wall_clock_time'] for d in redis_results[n]]
            redis_times.append(np.mean(times))
            redis_err.append(np.std(times))
        else:
            redis_times.append(0)
            redis_err.append(0)
        if n in fs_results:
            times = [d['timing']['wall_clock_time'] for d in fs_results[n]]
            fs_times.append(np.mean(times))
            fs_err.append(np.std(times))
        else:
            fs_times.append(0)
            fs_err.append(0)

    bars1 = ax1.bar(x - width/2, fs_times, width, yerr=fs_err,
                    label='File System Coupling', color='#FFD93D',
                    edgecolor='black', linewidth=1.5, hatch='/',
                    capsize=plot_config.CAPSIZE)
    bars2 = ax1.bar(x + width/2, redis_times, width, yerr=redis_err,
                    label='Memory Coupling', color='#4ECDC4',
                    edgecolor='black', linewidth=1.5, hatch='\\',
                    capsize=plot_config.CAPSIZE)

    ax1.set_xlabel('Number of Nodes')
    ax1.set_ylabel('Time (s)')
    ax1.set_title('Total Runtime')
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(n) for n in nodes])
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}s',
                     ha='center', va='bottom', fontweight='bold')

    # --------- Subplot 2: Latency vs Runtime ---------
    avg_latencies, latency_stds, total_runtimes, runtime_stds = [], [], [], []

    for n in nodes:
        data_list = redis_results[n]
        put_means = [d['coupling_latencies']['put_ms']['mean'] for d in data_list]
        get_means = [d['coupling_latencies']['get_ms']['mean'] for d in data_list]
        avg_latency_runs = [(p+g)/2 for p,g in zip(put_means,get_means)]
        avg_latencies.append(np.mean(avg_latency_runs))
        latency_stds.append(np.std(avg_latency_runs))
        runtimes = [d['timing']['wall_clock_time'] for d in data_list]
        total_runtimes.append(np.mean(runtimes))
        runtime_stds.append(np.std(runtimes))

    ax2_twin = ax2.twinx()
    bars_runtime = ax2.bar(x, total_runtimes, width=0.4, alpha=0.7,
                           label='Total Runtime', color='#4ECDC4',
                           edgecolor='black', linewidth=1.5,
                           yerr=runtime_stds, capsize=plot_config.CAPSIZE)
    line_latency = ax2_twin.errorbar(x, avg_latencies, yerr=latency_stds,
                                     fmt='o-', linewidth=plot_config.LINE_WIDTH,
                                     markersize=plot_config.MARKER_SIZE,
                                     label='Avg Latency', color='#FF6B6B',
                                     alpha=0.5, capsize=plot_config.CAPSIZE)

    ax2.set_xlabel('Number of Nodes')
    ax2.set_ylabel('Total Runtime (s)', color='#4ECDC4')
    ax2_twin.set_ylabel('Per-Operation Latency (ms)', color='#FF6B6B')
    ax2.set_title('Latency vs Runtime')
    ax2.set_xticks(x)
    ax2.set_xticklabels([str(n) for n in nodes])
    ax2.tick_params(axis='y', labelcolor='#4ECDC4')
    ax2_twin.tick_params(axis='y', labelcolor='#FF6B6B')
    ax2.grid(True, alpha=0.3)

    for i, bar in enumerate(bars_runtime):
        ax2.text(bar.get_x() + bar.get_width()/2., total_runtimes[i], f'{total_runtimes[i]:.1f}s',
                 ha='center', va='bottom', fontsize=8, fontweight='bold')

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    # --------- Subplot 3: Time Breakdown (stacked with RHAPSODY) ---------
    for i, n in enumerate(nodes):
        if n in redis_results:
            data_list = redis_results[n]
            compute = np.mean([d['breakdown']['total_computation_time'] for d in data_list])
            transfer = np.mean([d['breakdown']['total_data_transfer_time'] for d in data_list])
            rhap = np.mean([d.get("rhapsody_overhead", 0) for d in data_list])
            rose = np.mean([d.get("rose_overhead", 0) for d in data_list])

            # Log per-node breakdown
            print(f"Node {n}: compute={compute:.2f}, transfer={transfer:.2f}, "
                  f"rhapsody={rhap:.2f}, rose={rose:.2f}")

            x_pos = i
            ax3.bar(x_pos, compute, width=0.4, label='Computations' if i==0 else '',
                    color='grey', edgecolor='black', linewidth=1.5, hatch='..')
            ax3.bar(x_pos, transfer, width=0.4, bottom=compute, label='Data Transfer' if i==0 else '',
                    color='#4ECDC4', edgecolor='black', linewidth=1.5, hatch='\\')
            ax3.bar(x_pos, rhap, width=0.4, bottom=compute+transfer, label='RHAPSODY Overhead' if i==0 else '',
                    color='#FFA500', edgecolor='black', linewidth=1.5, hatch='//')
            ax3.bar(x_pos, rose, width=0.4, bottom=compute+transfer+rhap, label='ROSE Overhead' if i==0 else '',
                    color='#FF6B6B', edgecolor='black', linewidth=1.5, hatch='**')

    ax3.set_xlabel('Number of Nodes')
    ax3.set_ylabel('Time (s)')
    ax3.set_title('Memory Coupling Time Breakdown')
    ax3.set_xticks(x)
    ax3.set_xticklabels([str(n) for n in nodes])
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    data_volumes = {
        1: "320 MB",
        2: "640 MB",
        4: "1.28 GB",
        8: "2.56 GB"
        }

    volume_labels = [f"{n} nodes: {data_volumes[n]}" for n in nodes]

    dummy_handles = [mpatches.Patch(color='none', label=lbl) for lbl in volume_labels]

    # First legend: computation / transfer / orchestration
    handles, labels = ax3.get_legend_handles_labels()
    first_leg = ax3.legend(handles[::-1], labels[::-1])

    # Second legend: data volumes
    second_leg = ax3.legend(
        handles=dummy_handles,
        labels=volume_labels,
        title="Transfered Data per Node Count",
        loc='center left',
        title_fontsize='medium',
        frameon=False,
        bbox_to_anchor=(-0.025, 0.425),
    )

    # Add the first legend back
    ax3.add_artist(first_leg)


    plot_config.save_figure(fig, output_file)
    print(f"✅ Combined plot saved to {output_file}")


def print_summary(redis_results, fs_results):
    nodes = sorted(set(list(redis_results.keys()) + list(fs_results.keys())))

    print("\n" + "="*150)
    print("SUMMARY OF METRICS: Memory Coupling (Redis) vs Filesystem with Overheads")
    print("="*150)

    header = (
        f"{'Nodes':<6} "
        f"{'#Tasks':<8} "
        f"{'FS Runtime (s)':<18} "
        f"{'MC Runtime (s)':<18} "
        f"{'MC Latency (ms)':<18} "
        f"{'MC Compute (s)':<18} "
        f"{'MC Transfer (s)':<18} "
        f"{'RHAPSODY Overhead (s)':<22} "
        f"{'ROSE Overhead (s)':<18}"
    )
    print(header)
    print("-" * 150)

    for n in nodes:
        total_tasks = n * 200   # total number of tasks

        # ---- Filesystem ----
        if n in fs_results:
            fs_times = [d['timing']['wall_clock_time'] for d in fs_results[n]]
            fs_mean = np.mean(fs_times)
            fs_std = np.std(fs_times)
        else:
            fs_mean = fs_std = 0.0

        # ---- Memory Coupling ----
        if n in redis_results:
            data_list = redis_results[n]
            # Runtime
            mc_times = [d['timing']['wall_clock_time'] for d in data_list]
            mc_mean = np.mean(mc_times)
            mc_std = np.std(mc_times)

            # Latency (PUT+GET avg)
            put_means = [d['coupling_latencies']['put_ms']['mean'] for d in data_list]
            get_means = [d['coupling_latencies']['get_ms']['mean'] for d in data_list]
            lat_runs = [(p + g) / 2 for p, g in zip(put_means, get_means)]
            lat_mean = np.mean(lat_runs)
            lat_std = np.std(lat_runs)

            # Breakdown
            compute_vals = [d['breakdown']['total_computation_time'] for d in data_list]
            compute = np.mean(compute_vals)
            compute_std = np.std(compute_vals)

            transfer_vals = [d['breakdown']['total_data_transfer_time'] for d in data_list]
            transfer = np.mean(transfer_vals)
            transfer_std = np.std(transfer_vals)

            # Overheads
            rhapsody_vals = [d.get("rhapsody_overhead", 0.0) for d in data_list]
            rose_vals = [d.get("rose_overhead", 0.0) for d in data_list]
            rhapsody_mean = np.mean(rhapsody_vals)
            rhapsody_std = np.std(rhapsody_vals)
            rose_mean = np.mean(rose_vals)
            rose_std = np.std(rose_vals)
        else:
            mc_mean = mc_std = 0.0
            lat_mean = lat_std = 0.0
            compute = compute_std = 0.0
            transfer = transfer_std = 0.0
            rhapsody_mean = rhapsody_std = 0.0
            rose_mean = rose_std = 0.0

        # Print row with mean ± std
        print(
            f"{n:<6} "
            f"{total_tasks:<8} "
            f"{fs_mean:5.2f} ± {fs_std:4.2f}    "
            f"{mc_mean:5.2f} ± {mc_std:4.2f}        "
            f"{lat_mean:5.2f} ± {lat_std:4.2f}        "
            f"{compute:5.2f} ± {compute_std:4.2f}          "
            f"{transfer:5.2f} ± {transfer_std:4.2f}          "
            f"{rhapsody_mean:5.2f} ± {rhapsody_std:4.2f}         "
            f"{rose_mean:5.2f} ± {rose_std:4.2f}"
        )

    print("="*150 + "\n")

# -----------------------------
# 5- Main
# -----------------------------
if __name__ == "__main__":
    redis_results, fs_results = load_results()
    attach_rhapsody_overhead(redis_results)
    if redis_results and fs_results:
        plot_all_in_one(redis_results, fs_results)
        print_summary(redis_results, fs_results)
    else:
        print("Missing results!")
