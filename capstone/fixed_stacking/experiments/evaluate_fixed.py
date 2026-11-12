"""
fixed_stacking/experiments/evaluate_fixed.py
=========================================================
Runner script for Structured Fixed 3D Stacking Benchmark Evaluation.
Enforces fixed layer structural partitioning (Table 2 from literature) across all 5 algorithms:
Greedy 3D, ABC 3D, Bat 3D, Firefly 3D, MACO 3D.

Generates and saves visual dashboards, Gantt charts, heatmaps, and text results inside fixed_stacking/results/.
"""

import os
import sys
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.models.soc_3d_fixed import FixedBenchmarkLoader, SoC3DFixed, ScheduleResult3DFixed
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler


def plot_3d_gantt_chart(results: dict, benchmark_name: str, output_path: str):
    best_alg = min(results.keys(), key=lambda a: results[a].makespan)
    best_schedule = results[best_alg]

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {0: '#1f77b4', 1: '#ff7f0e', 2: '#2ca02c'}
    layer_names = {0: 'Layer 1 (Bottom/Heatsink)', 1: 'Layer 2 (Middle)', 2: 'Layer 3 (Top)'}

    tasks_by_core = sorted(best_schedule.tasks, key=lambda t: t.core_id)
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
    ax.set_title(f"Fixed 3D Test Schedule Gantt Chart - {benchmark_name} ({best_alg})", fontsize=13, fontweight='bold')

    legend_patches = [mpatches.Patch(color=colors[l], label=layer_names[l]) for l in range(3)]
    ax.legend(handles=legend_patches, loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved Gantt chart to '{output_path}'")


def plot_thermal_heatmaps(soc: SoC3DFixed, best_result: ScheduleResult3DFixed, output_path: str):
    peak_idx = np.argmax(best_result.thermal_profile)
    sampled_times = np.linspace(0, best_result.makespan, len(best_result.thermal_profile), dtype=int)
    peak_time = sampled_times[peak_idx]

    active_tasks = [t for t in best_result.tasks if t.start_time <= peak_time < t.end_time]
    active_cores = [soc.cores[t.core_id - 1] for t in active_tasks]

    thermal_res = soc.thermal_model.estimate_temperature_profile(active_cores, grid_resolution=6)
    temp_grids = thermal_res["temp_grids"] - 273.15

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    fig.suptitle(f"Fixed 3D SoC Spatial Thermal Profile at Peak Temp (t={peak_time:,} cycles)", fontsize=13, fontweight='bold')

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


def plot_execution_dashboard(results: dict, benchmark_name: str, output_path: str, max_p: float, max_tsv: int):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Fixed 3D SoC Optimization & Empirical Constraint Dashboard ({benchmark_name})", fontsize=14, fontweight='bold')

    algs = list(results.keys())
    makespans = [results[a].makespan for a in algs]
    colors = ['#708090', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728', '#17becf']
    bars = axes[0, 0].bar(algs, makespans, color=colors[:len(algs)], width=0.5, edgecolor='black')
    axes[0, 0].set_ylabel("Makespan (Test Cycles)", fontweight='bold')
    axes[0, 0].set_title("Makespan (TAT) Reduction Across Algorithms", fontweight='bold')
    axes[0, 0].grid(axis='y', linestyle='--', alpha=0.6)
    for bar in bars:
        height = bar.get_height()
        axes[0, 0].text(bar.get_x() + bar.get_width()/2., height * 1.01, f"{height:,}", ha='center', va='bottom', fontsize=8, fontweight='bold')

    for alg in algs:
        axes[0, 1].plot(results[alg].power_profile, label=alg, linewidth=1.8)
    axes[0, 1].axhline(y=max_p, color='r', linestyle='--', label=f"Pmax ({max_p}W)")
    axes[0, 1].set_ylabel("Power Consumption (W)", fontweight='bold')
    axes[0, 1].set_xlabel("Normalized Timeline", fontweight='bold')
    axes[0, 1].set_title("Continuous Peak Power Profile (Pmax Compliance)", fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)

    for alg in algs:
        axes[1, 0].plot(results[alg].thermal_profile, label=alg, linewidth=1.8)
    axes[1, 0].axhline(y=95.0, color='r', linestyle='--', label="Tmax Limit (95°C)")
    axes[1, 0].set_ylabel("Junction Temp Tj (°C)", fontweight='bold')
    axes[1, 0].set_xlabel("Normalized Timeline", fontweight='bold')
    axes[1, 0].set_title("Spatial-Temporal Junction Temperature Profile", fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)

    for alg in algs:
        axes[1, 1].plot(results[alg].tsv_profile, label=alg, linewidth=1.8)
    axes[1, 1].axhline(y=max_tsv, color='r', linestyle='--', label=f"TSVmax ({max_tsv})")
    axes[1, 1].set_ylabel("Active TSV Channels", fontweight='bold')
    axes[1, 1].set_xlabel("Normalized Timeline", fontweight='bold')
    axes[1, 1].set_title("Vertical TSV Interconnect Utilization", fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved Execution Dashboard to '{output_path}'")


def run_fixed_benchmark(soc_name: str, soc, results_dir: str):
    print(f"\n==========================================================================")
    print(f"   RUNNING STRUCTURED FIXED 3D STACKING EVALUATION: {soc_name}")
    print(f"   Cores: {len(soc.cores)} | Layers: {soc.num_layers} | Pmax: {soc.max_power}W | Wmax: {soc.max_tam_width} | TSVmax: {soc.max_tsv_bandwidth}")
    print(f"==========================================================================")

    algos = [
        ("Greedy 3D Baseline", Greedy3DScheduler(soc)),
        ("Artificial Bee Colony (ABC 3D)", ABC3DScheduler(soc, colony_size=15, max_iterations=15)),
        ("Bat 3D Algorithm", Bat3DScheduler(soc, num_bats=15, max_iterations=15)),
        ("Firefly 3D Algorithm", Firefly3DScheduler(soc, num_fireflies=15, max_iterations=15)),
        ("Modified ACO (MACO 3D)", MACO3DScheduler(soc, num_ants=15, max_iterations=15)),
        ("H-MACO-FA Hybrid (3D)", HMACOFA3DScheduler(soc, num_ants=15, num_fireflies=12, max_iterations=15)),
    ]

    results = {}
    for name, scheduler in algos:
        t0 = time.time()
        res = scheduler.optimize()
        t1 = time.time()
        results[name] = res
        print(f"[{name:<30}] Makespan: {res.makespan:>8,} cycles | Peak P: {res.peak_power:5.2f}W | Peak Tj: {res.peak_temperature:5.1f}°C | TSV: {res.max_tsv_used:<2}/{soc.max_tsv_bandwidth:<2} | Status: {res.constraint_status} | Time: {(t1-t0):.3f}s")

    clean_name = "d695" if "d695" in soc_name.lower() else "p22810"
    plot_3d_gantt_chart(results, f"{soc_name} Fixed", os.path.join(results_dir, f"gantt_{clean_name}_fixed.png"))
    plot_thermal_heatmaps(soc, results[min(results.keys(), key=lambda a: results[a].makespan)], os.path.join(results_dir, f"thermal_heatmap_{clean_name}_fixed.png"))
    plot_execution_dashboard(results, f"{soc_name} Fixed", os.path.join(results_dir, f"dashboard_{clean_name}_fixed.png"), soc.max_power, soc.max_tsv_bandwidth)

    return results


def main():
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    soc_d695 = FixedBenchmarkLoader.load_d695_fixed(max_tam_width=16, max_power=45.89, max_tsv=16)
    res_d695 = run_fixed_benchmark("ITC'02 d695 (Fixed Stacking)", soc_d695, results_dir)

    soc_p22810 = FixedBenchmarkLoader.load_p22810_fixed(max_tam_width=32, max_power=94.05, max_tsv=24)
    res_p22810 = run_fixed_benchmark("ITC'02 p22810 (Fixed Stacking)", soc_p22810, results_dir)

    # Write summary text file inside fixed_stacking/results/
    summary_txt_path = os.path.join(results_dir, "fixed_stacking_summary.txt")
    with open(summary_txt_path, "w") as f:
        f.write("========================================================================\n")
        f.write("       STRUCTURED FIXED 3D STACKING BENCHMARK EVALUATION RESULTS        \n")
        f.write("========================================================================\n\n")

        f.write("ITC'02 d695 Benchmark (10 Cores, 3 Layers, Pmax=45.89W, Wmax=16, TSVmax=16):\n")
        for alg, r in res_d695.items():
            f.write(f"  - {alg:<30}: Makespan={r.makespan:,} cycles | Peak P={r.peak_power:.2f}W | Peak Tj={r.peak_temperature:.1f}°C | TSV={r.max_tsv_used}/16 | Status={r.constraint_status}\n")

        f.write("\nITC'02 p22810 Benchmark (30 Cores, 3 Layers, Pmax=94.05W, Wmax=32, TSVmax=24):\n")
        for alg, r in res_p22810.items():
            f.write(f"  - {alg:<30}: Makespan={r.makespan:,} cycles | Peak P={r.peak_power:.2f}W | Peak Tj={r.peak_temperature:.1f}°C | TSV={r.max_tsv_used}/24 | Status={r.constraint_status}\n")

    print(f"\nSaved summary text report to '{summary_txt_path}'")


if __name__ == "__main__":
    main()
