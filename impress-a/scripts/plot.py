#!/usr/bin/env python3
"""
Rate plot for HPC-AI coupling analysis.
Visualizes temporal coupling between agent decision rate and HPC task realization rate.
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path to import plot_config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import plot_config

# Configure matplotlib with consistent settings (MEDIUM size for 0.45\textwidth)
plot_config.configure_matplotlib(size='medium')


total_tool_calls = 0
total_inferences = 0
pipeline_submissions = defaultdict(int)

def print_inference_and_pipeline_stats(filepath):
    """Print total number of inferences and pipeline submissions."""
    global total_tool_calls
    global total_inferences
    global pipeline_submissions

    with open(filepath, 'r') as f:
        for line in f:
            # Count prompt/inference events
            if "Queued request with" in line and "prompts" in line:
                prompt_match = re.search(r'(\d+) prompts', line)
                if prompt_match:
                    total_inferences += int(prompt_match.group(1))

            # Count pipeline submissions (tasks/blocks)
            elif "Submitting" in line and "tasks/blocks for execution" in line:
                task_match = re.search(r'Submitting (\d+) tasks', line)
                if task_match:
                    num_tasks = int(task_match.group(1))
                    # Each task is a pipeline submission, they cycle through IDs 0-49
                    for _ in range(num_tasks):
                        # We don't have the actual pipeline ID in the log line,
                        # but we know they're resubmitted, so count all submissions
                        pipeline_submissions['total'] += 1
            elif "RUNNING" in line:
                total_tool_calls += 1

    print("\n" + "="*70)
    print("INFERENCE AND PIPELINE STATISTICS")
    print("="*70)
    print(f"Total inferences (prompts): {total_inferences}")
    print(f"Total tool calls (RUNNING state): {total_tool_calls}")
    print(f"Total pipeline submissions: {pipeline_submissions['total']}")
    print(f"Pipeline resubmission ratio: {pipeline_submissions['total'] / 50:.2f}x (50 unique pipeline IDs)")
    print("="*70 + "\n")

def parse_timestamp(ts_str):
    """Parse timestamp string to datetime object."""
    return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")

def parse_log_file(filepath):
    """Extract prompt events and task submission events with timestamps."""
    prompt_events = []
    task_events = []

    with open(filepath, 'r') as f:
        for line in f:
            # Extract timestamp from start of line
            ts_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
            if not ts_match:
                continue

            timestamp = parse_timestamp(ts_match.group(1))

            # Look for prompt events (agent decisions)
            if "Queued request with" in line and "prompts" in line:
                # Extract number of prompts
                prompt_match = re.search(r'(\d+) prompts', line)
                if prompt_match:
                    num_prompts = int(prompt_match.group(1))
                    prompt_events.append((timestamp, num_prompts))

            # Look for task submission events (HPC task realization)
            elif "Submitting" in line and "tasks/blocks for execution" in line:
                # Extract number of tasks
                task_match = re.search(r'Submitting (\d+) tasks', line)
                if task_match:
                    num_tasks = int(task_match.group(1))
                    task_events.append((timestamp, num_tasks))

    return prompt_events, task_events

def compute_rate(events, window_size, time_range):
    """
    Compute event rate over sliding window.

    Args:
        events: List of (timestamp, count) tuples
        window_size: Window duration in seconds
        time_range: (start_time, end_time, step) in seconds from first event

    Returns:
        times: Array of time points (seconds from start)
        rates: Array of rates (events/second)
    """
    if not events:
        return np.array([]), np.array([])

    # Convert to seconds from first event
    first_time = events[0][0]
    event_times = np.array([(ts - first_time).total_seconds() for ts, _ in events])
    event_counts = np.array([count for _, count in events])

    start, end, step = time_range
    times = np.arange(start, end, step)
    rates = np.zeros(len(times))

    for i, t in enumerate(times):
        # Find events within window [t - window_size, t]
        mask = (event_times >= t - window_size) & (event_times <= t)
        total_count = np.sum(event_counts[mask])
        rates[i] = total_count / window_size if window_size > 0 else 0

    return times, rates

def main(logfile: str, figure_file_name:str):

    print(f"Parsing {logfile}...")
    prompt_events, task_events = parse_log_file(logfile)
    print_inference_and_pipeline_stats(logfile)

    print(f"Found {len(prompt_events)} prompt events (agent decisions)")
    print(f"Found {len(task_events)} task submission events (HPC realizations)")

    if not prompt_events or not task_events:
        print("Error: No events found in log file")
        return

    # Calculate time range
    first_time = min(prompt_events[0][0], task_events[0][0])
    last_time = max(prompt_events[-1][0], task_events[-1][0])
    duration = (last_time - first_time).total_seconds()

    print(f"\nTime range: {duration:.2f} seconds")
    print(f"First event: {first_time}")
    print(f"Last event: {last_time}")

    # Sliding window parameters
    window_size = 2.0  # 2 second window
    step = 0.1  # 100ms resolution
    time_range = (0, duration + window_size, step)

    # Compute rates
    print(f"\nComputing rates with {window_size}s sliding window...")
    prompt_times, prompt_rates = compute_rate(prompt_events, window_size, time_range)
    task_times, task_rates = compute_rate(task_events, window_size, time_range)

    # Create the plot
    print("Creating visualization...")
    fig, ax = plot_config.create_figure(1, 1, figsize=(7, 4.5))

    # Plot both rate curves
    ax.plot(prompt_times, prompt_rates, 'r-',
            linewidth=plot_config.LINE_WIDTH, alpha=0.8,
            label='Agent Decision Rate (prompts/s)')
    ax.plot(task_times, task_rates, 'b-',
            linewidth=plot_config.LINE_WIDTH, alpha=0.8,
            label='HPC Task Realization Rate (tasks/s)')

    # Styling
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Rate (events/second)')
    ax.set_title(f'Agent Decisions vs. Task Realization for {pipeline_submissions["total"]} Pipelines',
                 pad=20)
    ax.legend(loc='best', framealpha=0.95)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Add annotations for key insights
    max_prompt_rate = np.max(prompt_rates)
    max_task_rate = np.max(task_rates)

    # Save figure
    plot_config.save_figure(fig, figure_file_name)
    print(f"\nPlot saved to {figure_file_name}")

    # Additional analysis: compute cross-correlation to detect lag
    print("\n" + "="*70)
    print("TEMPORAL COUPLING ANALYSIS")
    print("="*70)

    # Resample to common time grid for correlation
    common_times = np.arange(0, duration, 0.5)
    prompt_interp = np.interp(common_times, prompt_times, prompt_rates)
    task_interp = np.interp(common_times, task_times, task_rates)

    # Compute cross-correlation
    correlation = np.correlate(prompt_interp - np.mean(prompt_interp),
                               task_interp - np.mean(task_interp), mode='full')
    lags = np.arange(-len(common_times) + 1, len(common_times)) * 0.5

    # Find peak correlation
    peak_idx = np.argmax(correlation)
    peak_lag = lags[peak_idx]

    print(f"Peak cross-correlation lag: {peak_lag:.2f}s")
    if peak_lag > 0:
        print(f"  → Tasks lag behind prompts by ~{peak_lag:.2f}s (expected)")
    elif peak_lag < 0:
        print(f"  → Prompts lag behind tasks by ~{-peak_lag:.2f}s (unusual)")
    else:
        print(f"  → Near-simultaneous coupling")

    # Detect phases
    prompt_active = prompt_rates > 0.1 * max_prompt_rate
    task_active = task_rates > 0.1 * max_task_rate
    overlap = np.sum(prompt_active & task_active) / len(prompt_active)

    print(f"\nTemporal overlap: {overlap*100:.1f}% (sustained overlap vs. phased)")
    if overlap > 0.7:
        print("  → High overlap: sustained concurrent execution")
    elif overlap > 0.3:
        print("  → Moderate overlap: mixed phased/concurrent execution")
    else:
        print("  → Low overlap: mostly phased execution")

    # Check for collapse patterns
    high_prompt_periods = prompt_rates > 0.5 * max_prompt_rate
    if np.any(high_prompt_periods):
        avg_task_rate_during_high_prompts = np.mean(task_rates[high_prompt_periods])
        print(f"\nAverage task rate during high prompt activity: {avg_task_rate_during_high_prompts:.2f} tasks/s")
        if avg_task_rate_during_high_prompts < 0.3 * max_task_rate:
            print("  → WARNING: Potential collapse under load (task rate flattens)")
        else:
            print("  → Task realization scales with prompt load")

    print("="*70 + "\n")

if __name__ == '__main__':
    # Parse log file
    parser = argparse.ArgumentParser(
        description="Process a log file and write results to an output file."
    )

    parser.add_argument(
        "log_file",
        help="Path to the input log file"
    )

    parser.add_argument(
        "output_file",
        help="Path to the output file"
    )

    args = parser.parse_args()

    main(args.log_file, args.output_file)
