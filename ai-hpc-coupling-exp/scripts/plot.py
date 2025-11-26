#!/usr/bin/env python
"""
Plot: ROSE+Memory Coupling vs ROSE+Filesystem
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re
from collections import defaultdict

def load_results(results_dir='../data/results'):
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

def plot_all_in_one(redis_results, fs_results, output_file='combined_plots.png'):
    nodes = sorted(set(list(redis_results.keys()) + list(fs_results.keys())))
    
    # ==== NEW: Only 3 subplots, all on one row ====
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4))

    x = np.arange(len(nodes))
    width = 0.35

    # --------- Subplot 1: Total Runtime Comparison ---------
    redis_times = []
    redis_err = []
    fs_times = []
    fs_err = []

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
                    label='File System Coupling', color='#FFD93D', edgecolor='black', linewidth=1.5, hatch='/', capsize=5)
    bars2 = ax1.bar(x + width/2, redis_times, width, yerr=redis_err,
                    label='Memory Coupling', color='#4ECDC4', edgecolor='black', linewidth=1.5, hatch='\\', capsize=5)

    ax1.set_xlabel('# Nodes | # Tasks', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Time (s)', fontsize=12, fontweight='bold')
    ax1.set_title('Total Runtime', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['1|200', '2|400', '4|800', '8|1600'], fontsize=12)
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3, axis='y')

    # Value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1f}s',
                     ha='center', va='bottom', fontsize=8, fontweight='bold')

    # --------- Subplot 2: Latency vs Runtime Correlation ---------
    avg_latencies = []
    latency_stds = []
    total_runtimes = []
    runtime_stds = []

    for n in nodes:
        data_list = redis_results[n]
        put_means = [d['coupling_latencies']['put_ms']['mean'] for d in data_list]
        get_means = [d['coupling_latencies']['get_ms']['mean'] for d in data_list]
        avg_latency_runs = [(p+g)/2 for p, g in zip(put_means, get_means)]
        avg_latencies.append(np.mean(avg_latency_runs))
        latency_stds.append(np.std(avg_latency_runs))

        runtimes = [d['timing']['wall_clock_time'] for d in data_list]
        total_runtimes.append(np.mean(runtimes))
        runtime_stds.append(np.std(runtimes))

    ax2_twin = ax2.twinx()
    bars_runtime = ax2.bar(x, total_runtimes, width=0.4, alpha=0.7,
                           label='Total Runtime', color='#4ECDC4', edgecolor='black', linewidth=1.5,
                           yerr=runtime_stds, capsize=5)
    line_latency = ax2_twin.errorbar(x, avg_latencies, yerr=latency_stds, fmt='o-', linewidth=3, markersize=10,
                                     label='Avg Latency', color='#FF6B6B', alpha=0.7, capsize=5)

    ax2.set_xlabel('# Nodes | # Tasks', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Total Runtime (s)', fontsize=12, fontweight='bold', color='#4ECDC4')
    ax2_twin.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold', color='#FF6B6B')
    ax2.set_title('Latency vs Runtime', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['1|200', '2|400', '4|800', '8|1600'], fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#4ECDC4')
    ax2_twin.tick_params(axis='y', labelcolor='#FF6B6B')
    ax2.grid(True, alpha=0.3)

    for i, bar in enumerate(bars_runtime):
        ax2.text(bar.get_x() + bar.get_width()/2., total_runtimes[i], f'{total_runtimes[i]:.1f}s',
                 ha='center', va='bottom', fontsize=8, fontweight='bold')

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=12)

    # --------- Subplot 3: Time Breakdown (stacked) ---------
    for i, n in enumerate(nodes):
        if n in redis_results:
            data_list = redis_results[n]
            transfer = np.mean([d['breakdown']['total_data_transfer_time'] for d in data_list])
            compute = np.mean([d['breakdown']['total_computation_time'] for d in data_list])
            wall = np.mean([d['timing']['wall_clock_time'] for d in data_list])
            overhead = wall - transfer - compute
            x_pos = i

            ax3.bar(x_pos, compute, width=0.4, label='Computations' if i == 0 else '',
                    color='grey', edgecolor='black', linewidth=1.5, hatch='..')
            ax3.bar(x_pos, transfer, width=0.4, bottom=compute, label='Data Transfer' if i == 0 else '',
                    color='#4ECDC4', edgecolor='black', linewidth=1.5, hatch='\\')
            ax3.bar(x_pos, overhead, width=0.4, bottom=compute + transfer, label='Orchestration' if i == 0 else '',
                    color='#FF6B6B', edgecolor='black', linewidth=1.5, hatch='**')

    ax3.set_xlabel('# Nodes | # Tasks', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Time (s)', fontsize=12, fontweight='bold')
    ax3.set_title('Time Breakdown', fontsize=12, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(['1|200', '2|400', '4|800', '8|1600'], fontsize=12)
    ax3.grid(True, alpha=0.3, axis='y')

    data_volumes = {
        1: "320 MB",
        2: "640 MB",
        4: "1.28 GB",
        8: "2.56 GB"
        }

    volume_labels = [f"{n} nodes: {data_volumes[n]}" for n in nodes]

    import matplotlib.patches as mpatches
    dummy_handles = [mpatches.Patch(color='none', label=lbl) for lbl in volume_labels]

    # 1️⃣ First legend: computation / transfer / orchestration
    first_leg = ax3.legend(
        fontsize=12,
        loc='upper left',
        frameon=True
    )

    # 2️⃣ Second legend: data volumes
    second_leg = ax3.legend(
        handles=dummy_handles,
        labels=volume_labels,
        title="Transfered Data per Node Count",
        loc='center left',
        fontsize=12,
        title_fontsize=12,
        frameon=False,
        bbox_to_anchor=(-0.025, 0.45),    # (x, y) you can edit
    )

    # 3️⃣ Add the first legend back
    ax3.add_artist(first_leg)


    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Combined plot saved to {output_file}")
    plt.show()

def print_summary(redis_results, fs_results):
    nodes = sorted(set(list(redis_results.keys()) + list(fs_results.keys())))
    print("\n" + "="*90)
    print("COUPLING COMPARISON: Memory Coupling vs Filesystem")
    print("="*90)
    print(f"{'Nodes':<10} {'Filesystem (s)':<20} {'Memory Coupling (s)':<20} {'Speedup':<15}")
    print("-"*90)
    for n in nodes:
        if n in redis_results and n in fs_results:
            fs_time = np.mean([d['timing']['wall_clock_time'] for d in fs_results[n]])
            redis_time = np.mean([d['timing']['wall_clock_time'] for d in redis_results[n]])
            speedup = fs_time / redis_time
            print(f"{n:<10} {fs_time:<20.3f} {redis_time:<20.3f} {speedup:<15.2f}×")
    print("="*90 + "\n")

if __name__ == "__main__":
    redis_results, fs_results = load_results()
    if redis_results and fs_results:
        print_summary(redis_results, fs_results)
        plot_all_in_one(redis_results, fs_results)
    else:
        print("❌ Missing results!")

