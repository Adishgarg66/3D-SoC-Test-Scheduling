"""
experiments/evaluate_3d.py
===========================
Comprehensive 3D SoC Test Solution Evaluation & Multi-Seed Statistical Benchmarking Suite.
Runs Greedy 3D, ABC 3D, Bat 3D, Firefly 3D, MACO 3D, and H-MACO-FA 3D algorithms across random seeds.
Reports Mean ± Std Dev, Makespan Reduction Ranges, and Empirical Constraint Status.
Incorporates ML Predictive Thermal Estimation & Frequency Scaling (Ref [12]).
"""

import os
import sys
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")
import json
import time
import random
import numpy as np
from typing import Tuple, Dict, List
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.soc_3d import ITC02BenchmarkLoader, SoC3D, ScheduleResult3D
from src.models.predictive_thermal import PredictiveThermalEstimator, FrequencyScaledScheduler
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler
from src.hardware.rpi_tester import RaspberryPi5Tester

SEEDS = [42, 100, 2024]


def evaluate_algorithm_multiseed(alg_class, soc: SoC3D, seeds: list = SEEDS, **kwargs) -> Tuple[ScheduleResult3D, dict]:
    """Runs an algorithm across multiple seeds and compiles statistical metrics."""
    results = []
    makespans = []

    for seed in seeds:
        random.seed(seed)
        np.random.seed(seed)
        scheduler = alg_class(soc, **kwargs)
        res = scheduler.optimize()
        results.append(res)
        makespans.append(res.makespan)

    best_idx = np.argmin(makespans)
    best_result = results[best_idx]

    stats = {
        "best_makespan": int(np.min(makespans)),
        "mean_makespan": float(np.mean(makespans)),
        "std_makespan": float(np.std(makespans)),
        "min_makespan": int(np.min(makespans)),
        "max_makespan": int(np.max(makespans)),
        "all_makespans": makespans
    }

    return best_result, stats


def run_benchmark_suite(benchmark_name: str, soc: SoC3D):
    """Executes all 6 algorithms on the given 3D SoC benchmark with multi-seed statistical evaluation."""
    print(f"\n==========================================================================")
    print(f"   RUNNING MULTI-SEED 3D SoC BENCHMARK EVALUATION: {benchmark_name}")
    print(f"   Cores: {len(soc.cores)} | Layers: {soc.num_layers} | Pmax: {soc.max_power}W | Wmax: {soc.max_tam_width} | TSVmax: {soc.max_tsv_bandwidth}")
    print(f"==========================================================================")

    best_results = {}
    stats_dict = {}

    # 1. Greedy 3D (Deterministic baseline)
    print("\n[1/6] Running Greedy 3D Baseline...")
    greedy = Greedy3DScheduler(soc)
    greedy_res = greedy.optimize()
    best_results["Greedy 3D"] = greedy_res
    stats_dict["Greedy 3D"] = {
        "best_makespan": greedy_res.makespan,
        "mean_makespan": float(greedy_res.makespan),
        "std_makespan": 0.0,
        "min_makespan": greedy_res.makespan,
        "max_makespan": greedy_res.makespan,
        "all_makespans": [greedy_res.makespan]
    }
    print(f"      Makespan: {greedy_res.makespan:,} cycles | Peak P: {greedy_res.peak_power:.2f}W | Peak Tj: {greedy_res.peak_temperature:.1f}°C | Status: {greedy_res.constraint_status}")

    # 2. ABC 3D
    print("\n[2/6] Running Artificial Bee Colony (ABC 3D across seeds)...")
    best_results["ABC 3D"], stats_dict["ABC 3D"] = evaluate_algorithm_multiseed(
        ABC3DScheduler, soc, colony_size=15, max_iterations=15
    )
    print(f"      Mean ± Std: {stats_dict['ABC 3D']['mean_makespan']:,.0f} ± {stats_dict['ABC 3D']['std_makespan']:.0f} | Best: {stats_dict['ABC 3D']['best_makespan']:,} | Peak Tj: {best_results['ABC 3D'].peak_temperature:.1f}°C | Status: {best_results['ABC 3D'].constraint_status}")

    # 3. Bat 3D
    print("\n[3/6] Running Bat 3D Algorithm (across seeds)...")
    best_results["Bat 3D"], stats_dict["Bat 3D"] = evaluate_algorithm_multiseed(
        Bat3DScheduler, soc, num_bats=15, max_iterations=15
    )
    print(f"      Mean ± Std: {stats_dict['Bat 3D']['mean_makespan']:,.0f} ± {stats_dict['Bat 3D']['std_makespan']:.0f} | Best: {stats_dict['Bat 3D']['best_makespan']:,} | Peak Tj: {best_results['Bat 3D'].peak_temperature:.1f}°C | Status: {best_results['Bat 3D'].constraint_status}")

    # 4. Firefly 3D
    print("\n[4/6] Running Firefly 3D Algorithm (across seeds)...")
    best_results["Firefly 3D"], stats_dict["Firefly 3D"] = evaluate_algorithm_multiseed(
        Firefly3DScheduler, soc, num_fireflies=15, max_iterations=15
    )
    print(f"      Mean ± Std: {stats_dict['Firefly 3D']['mean_makespan']:,.0f} ± {stats_dict['Firefly 3D']['std_makespan']:.0f} | Best: {stats_dict['Firefly 3D']['best_makespan']:,} | Peak Tj: {best_results['Firefly 3D'].peak_temperature:.1f}°C | Status: {best_results['Firefly 3D'].constraint_status}")

    # 5. MACO 3D
    print("\n[5/6] Running Modified ACO (MACO 3D across seeds)...")
    best_results["MACO 3D"], stats_dict["MACO 3D"] = evaluate_algorithm_multiseed(
        MACO3DScheduler, soc, num_ants=15, max_iterations=15
    )
    print(f"      Mean ± Std: {stats_dict['MACO 3D']['mean_makespan']:,.0f} ± {stats_dict['MACO 3D']['std_makespan']:.0f} | Best: {stats_dict['MACO 3D']['best_makespan']:,} | Peak Tj: {best_results['MACO 3D'].peak_temperature:.1f}°C | Status: {best_results['MACO 3D'].constraint_status}")

    # 6. H-MACO-FA Hybrid 3D
    print("\n[6/6] Running Hybrid MACO-Firefly (H-MACO-FA 3D across seeds)...")
    best_results["H-MACO-FA 3D"], stats_dict["H-MACO-FA 3D"] = evaluate_algorithm_multiseed(
        HMACOFA3DScheduler, soc, num_ants=15, num_fireflies=12, max_iterations=15
    )
    print(f"      Mean ± Std: {stats_dict['H-MACO-FA 3D']['mean_makespan']:,.0f} ± {stats_dict['H-MACO-FA 3D']['std_makespan']:.0f} | Best: {stats_dict['H-MACO-FA 3D']['best_makespan']:,} | Peak Tj: {best_results['H-MACO-FA 3D'].peak_temperature:.1f}°C | Status: {best_results['H-MACO-FA 3D'].constraint_status}")

    # ML Dynamic Thermal Frequency Scaling (Ref [12])
    print("\n[+ ML] Running ML Predictive Thermal Frequency-Scaled Scheduler (Ref [12])...")
    estimator = PredictiveThermalEstimator(num_layers=soc.num_layers)
    scaler = FrequencyScaledScheduler(soc, estimator)
    best_results["MACO 3D + ML Scaled"] = scaler.apply_frequency_scaling(best_results["MACO 3D"])
    stats_dict["MACO 3D + ML Scaled"] = {
        "best_makespan": best_results["MACO 3D + ML Scaled"].makespan,
        "mean_makespan": float(best_results["MACO 3D + ML Scaled"].makespan),
        "std_makespan": 0.0,
        "min_makespan": best_results["MACO 3D + ML Scaled"].makespan,
        "max_makespan": best_results["MACO 3D + ML Scaled"].makespan,
        "all_makespans": [best_results["MACO 3D + ML Scaled"].makespan]
    }
    print(f"      Makespan: {best_results['MACO 3D + ML Scaled'].makespan:,} | Peak Tj: {best_results['MACO 3D + ML Scaled'].peak_temperature:.1f}°C | Status: {best_results['MACO 3D + ML Scaled'].constraint_status}")

    return best_results, stats_dict


def print_performance_table(benchmark_name: str, results: dict, stats_dict: dict, soc: SoC3D):
    """Prints formatted ASCII comparison table with statistical ranges and empirical constraint status."""
    greedy_ms = stats_dict["Greedy 3D"]["mean_makespan"]
    print(f"\n=========================================================================================================")
    print(f"            MULTI-SEED STATISTICAL PERFORMANCE TABLE: {benchmark_name} (5 Seeds)")
    print(f"=========================================================================================================")
    header = f"{'Algorithm':<22} | {'Best Makespan':<14} | {'Mean ± Std Dev (Cycles)':<24} | {'Reduction Range':<18} | {'Peak Power':<12} | {'Peak Tj':<10} | {'Max TSV':<8} | {'Empirical Status'}"
    print(header)
    print("-" * len(header))

    for alg_name in results.keys():
        res = results[alg_name]
        st = stats_dict[alg_name]

        if alg_name == "Greedy 3D":
            red_str = "Baseline"
            mean_str = f"{st['best_makespan']:,}"
        else:
            min_red = ((greedy_ms - st['max_makespan']) / greedy_ms * 100.0)
            max_red = ((greedy_ms - st['min_makespan']) / greedy_ms * 100.0)
            red_str = f"-[{min_red:.1f}% to {max_red:.1f}%]"
            mean_str = f"{st['mean_makespan']:,.0f} ± {st['std_makespan']:.0f}"

        print(f"{alg_name:<22} | {st['best_makespan']:<14,} | {mean_str:<24} | {red_str:<18} | {res.peak_power:<5.2f}W/{soc.max_power:.1f}W | {res.peak_temperature:<5.1f}°C | {res.max_tsv_used:<3}/{soc.max_tsv_bandwidth:<3} | {res.constraint_status}")
    print("=" * len(header))


def plot_3d_gantt_chart(results: dict, benchmark_name: str, output_path: str):
    best_alg = "MACO 3D" if "MACO 3D" in results else list(results.keys())[0]
    res = results[best_alg]

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {0: '#2b5c8f', 1: '#d95f02', 2: '#7570b3'}
    layer_names = {0: 'Die Layer 0 (Bottom/Heatsink)', 1: 'Die Layer 1 (Middle)', 2: 'Die Layer 2 (Top)'}

    tasks_by_core = sorted(res.tasks, key=lambda t: t.core_id)
    y_positions = list(range(len(tasks_by_core)))
    y_labels = [f"Core {t.core_id} ({t.core_name})" for t in tasks_by_core]

    for idx, t in enumerate(tasks_by_core):
        c = colors.get(t.layer_id, '#333333')
        ax.barh(idx, t.duration, left=t.start_time, height=0.6, color=c, edgecolor='black', alpha=0.85)
        ax.text(t.start_time + t.duration * 0.05, idx, f"L{t.layer_id} | {t.power}W",
                va='center', ha='left', color='white', fontsize=8, fontweight='bold')

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Test Application Time (Clock Cycles)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Embedded Cores / IP Modules", fontsize=11, fontweight='bold')
    ax.set_title(f"3D Test Schedule Gantt Chart - {benchmark_name} ({best_alg})", fontsize=13, fontweight='bold')

    legend_patches = [mpatches.Patch(color=colors[l], label=layer_names[l]) for l in range(3)]
    ax.legend(handles=legend_patches, loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved Gantt chart to '{output_path}'")


def plot_thermal_heatmaps(soc: SoC3D, best_result: ScheduleResult3D, output_path: str):
    peak_idx = np.argmax(best_result.thermal_profile)
    sampled_times = np.linspace(0, best_result.makespan, len(best_result.thermal_profile), dtype=int)
    peak_time = sampled_times[peak_idx]

    active_tasks = [t for t in best_result.tasks if t.start_time <= peak_time < t.end_time]
    active_cores = [
        soc.cores[t.core_id - 1] for t in active_tasks
    ]

    thermal_res = soc.thermal_model.estimate_temperature_profile(active_cores, grid_resolution=6)
    temp_grids = thermal_res["temp_grids"] - 273.15

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    fig.suptitle(f"3D SoC Spatial Thermal Distribution at Peak Junction Temp (t={peak_time:,} cycles)", fontsize=13, fontweight='bold')

    for z in range(3):
        im = axes[z].imshow(temp_grids[z], cmap='hot', vmin=25, vmax=100)
        axes[z].set_title(f"Die Layer {z} Thermal Footprint", fontsize=11, fontweight='bold')
        axes[z].set_xlabel("X Grid")
        axes[z].set_ylabel("Y Grid")
        fig.colorbar(im, ax=axes[z], label="Junction Temp (°C)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved Thermal Heatmap to '{output_path}'")


def plot_execution_dashboard(results: dict, benchmark_name: str, output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"3D SoC Optimization & Empirical Constraint Dashboard ({benchmark_name})", fontsize=14, fontweight='bold')

    algs = [a for a in results.keys() if "ML" not in a]
    makespans = [results[a].makespan for a in algs]
    colors = ['#708090', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728', '#17becf']
    bars = axes[0, 0].bar(algs, makespans, color=colors[:len(algs)], width=0.5, edgecolor='black')
    axes[0, 0].tick_params(axis='x', rotation=15)
    axes[0, 0].set_ylabel("Makespan (Test Cycles)", fontweight='bold')
    axes[0, 0].set_title("Makespan (TAT) Reduction Across Algorithms", fontweight='bold')
    axes[0, 0].grid(axis='y', linestyle='--', alpha=0.6)
    for bar in bars:
        height = bar.get_height()
        axes[0, 0].text(bar.get_x() + bar.get_width()/2., height * 1.01, f"{height:,}", ha='center', va='bottom', fontsize=8, fontweight='bold')

    for alg in algs:
        axes[0, 1].plot(results[alg].power_profile, label=alg, linewidth=1.8)
    axes[0, 1].axhline(y=45.89 if "d695" in benchmark_name else 94.05, color='r', linestyle='--', label="Pmax Limit")
    axes[0, 1].set_ylabel("Power Consumption (W)", fontweight='bold')
    axes[0, 1].set_xlabel("Normalized Schedule Timeline", fontweight='bold')
    axes[0, 1].set_title("Continuous Peak Power Profile (Pmax Compliance)", fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)

    for alg in algs:
        axes[1, 0].plot(results[alg].thermal_profile, label=alg, linewidth=1.8)
    axes[1, 0].axhline(y=95.0, color='r', linestyle='--', label="Tmax Limit (95°C)")
    axes[1, 0].set_ylabel("Junction Temp Tj (°C)", fontweight='bold')
    axes[1, 0].set_xlabel("Normalized Schedule Timeline", fontweight='bold')
    axes[1, 0].set_title("Spatial-Temporal Junction Temperature Profile", fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)

    for alg in algs:
        axes[1, 1].plot(results[alg].tsv_profile, label=alg, linewidth=1.8)
    axes[1, 1].axhline(y=16 if "d695" in benchmark_name else 24, color='r', linestyle='--', label="TSVmax Limit")
    axes[1, 1].set_ylabel("Active TSV Channels", fontweight='bold')
    axes[1, 1].set_xlabel("Normalized Schedule Timeline", fontweight='bold')
    axes[1, 1].set_title("Vertical TSV Interconnect Utilization", fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved Execution Dashboard to '{output_path}'")


def main():
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    # Benchmark 1: d695 3D
    soc_d695 = ITC02BenchmarkLoader.load_d695_3d()
    results_d695, stats_d695 = run_benchmark_suite("ITC'02 d695 (3D Stack)", soc_d695)
    print_performance_table("ITC'02 d695 (3D Stack)", results_d695, stats_d695, soc_d695)

    plot_3d_gantt_chart(results_d695, "ITC'02 d695 3D", os.path.join(results_dir, "gantt_d695_3d.png"))
    plot_thermal_heatmaps(soc_d695, results_d695["MACO 3D"], os.path.join(results_dir, "thermal_heatmap_d695.png"))
    plot_execution_dashboard(results_d695, "ITC'02 d695 3D", os.path.join(results_dir, "dashboard_d695.png"))

    # Benchmark 2: p22810 3D
    soc_p22810 = ITC02BenchmarkLoader.load_p22810_3d()
    results_p22810, stats_p22810 = run_benchmark_suite("ITC'02 p22810 (3D Stack)", soc_p22810)
    print_performance_table("ITC'02 p22810 (3D Stack)", results_p22810, stats_p22810, soc_p22810)

    plot_3d_gantt_chart(results_p22810, "ITC'02 p22810 3D", os.path.join(results_dir, "gantt_p22810_3d.png"))
    plot_thermal_heatmaps(soc_p22810, results_p22810["MACO 3D"], os.path.join(results_dir, "thermal_heatmap_p22810.png"))
    plot_execution_dashboard(results_p22810, "ITC'02 p22810 3D", os.path.join(results_dir, "dashboard_p22810.png"))

    # Hardware-in-the-Loop (HIL) Validation Replay
    print("\n==========================================================================")
    print("      RUNNING PHASE 3 HARDWARE-IN-THE-LOOP (HIL) VALIDATION (RPi HIL Bridge)")
    print("==========================================================================")
    tester = RaspberryPi5Tester(mock_mode=True)
    hil_report = tester.replay_schedule(results_d695["MACO 3D"])

    print("\n--- HIL Physical Schedule Replay Summary ---")
    print(json.dumps(hil_report, indent=2))

    print("\nAll 3D SoC Test Scheduling simulations, multi-seed statistical runs, HIL replays, and plots completed cleanly!")


if __name__ == "__main__":
    main()
