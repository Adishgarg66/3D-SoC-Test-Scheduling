"""
2d/experiments/evaluate_2d.py
=============================
Main 2D Planar SoC Test Scheduling Evaluation Runner.
Base Reference Paper: Iyengar, Chakrabarty, & Marinissen (IEEE TCAD 2002) [Paper 16].
2D Metaheuristics Reference Paper: Chandrasekaran et al. (Revue d'Intelligence Artificielle 2021) [Paper 1].

Runs Greedy 2D, ABC 2D, Bat 2D, Firefly 2D, and MACO 2D algorithms.
Generates Gantt charts, power profiles, and dashboards in 2d/results/.
"""

import os
import sys
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.models.soc_2d import ITC02BenchmarkLoader2D, SoC2D, ScheduleResult2D
from src.algorithms.greedy_2d import Greedy2DScheduler
from src.algorithms.abc_2d import ABC2DScheduler
from src.algorithms.bat_2d import Bat2DScheduler
from src.algorithms.firefly_2d import Firefly2DScheduler
from src.algorithms.maco_2d import MACO2DScheduler
from src.algorithms.hmaco_fa_2d import HMACOFA2DScheduler
from src.hardware.rpi_tester_2d import RaspberryPi5Tester2D


def plot_2d_gantt_chart(results: dict, benchmark_name: str, output_path: str):
    best_alg = min(results.keys(), key=lambda a: results[a].makespan)
    best_schedule = results[best_alg]

    fig, ax = plt.subplots(figsize=(12, 6))
    tasks_by_core = sorted(best_schedule.tasks, key=lambda t: t.core_id)
    y_positions = list(range(len(tasks_by_core)))
    y_labels = [f"Core {t.core_id} ({t.core_name})" for t in tasks_by_core]

    for idx, t in enumerate(tasks_by_core):
        ax.barh(idx, t.duration, left=t.start_time, height=0.6, color='#1f77b4', edgecolor='black', alpha=0.85)
        ax.text(t.start_time + t.duration * 0.05, idx, f"W={t.tam_width} | {t.power}W",
                va='center', ha='left', color='white', fontsize=8, fontweight='bold')

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Test Application Time (Clock Cycles)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Embedded Cores / IP Modules", fontsize=11, fontweight='bold')
    ax.set_title(f"2D Test Schedule Gantt Chart - {benchmark_name} ({best_alg})", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved 2D Gantt chart to '{output_path}'")


def plot_2d_execution_dashboard(results: dict, benchmark_name: str, output_path: str, max_p: float, max_tam: int):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(f"2D SoC Optimization & Empirical Constraint Dashboard ({benchmark_name})", fontsize=14, fontweight='bold')

    algs = list(results.keys())
    makespans = [results[a].makespan for a in algs]
    colors = ['#708090', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728', '#17becf']

    bars = axes[0].bar(algs, makespans, color=colors[:len(algs)], width=0.5, edgecolor='black')
    axes[0].set_ylabel("Makespan (Test Cycles)", fontweight='bold')
    axes[0].set_title("Makespan (TAT) Reduction Across Algorithms", fontweight='bold')
    axes[0].grid(axis='y', linestyle='--', alpha=0.6)
    plt.setp(axes[0].get_xticklabels(), rotation=15, ha='right')
    for bar in bars:
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2., height * 1.01, f"{height:,}", ha='center', va='bottom', fontsize=8, fontweight='bold')

    for alg in algs:
        axes[1].plot(results[alg].power_profile, label=alg, linewidth=1.8)
    axes[1].axhline(y=max_p, color='r', linestyle='--', label=f"Pmax ({max_p}W)")
    axes[1].set_ylabel("Power Consumption (W)", fontweight='bold')
    axes[1].set_xlabel("Normalized Timeline", fontweight='bold')
    axes[1].set_title("Continuous Peak Power Profile (Pmax Compliance)", fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, linestyle='--', alpha=0.5)

    for alg in algs:
        axes[2].plot(results[alg].tam_profile, label=alg, linewidth=1.8)
    axes[2].axhline(y=max_tam, color='r', linestyle='--', label=f"Wmax ({max_tam})")
    axes[2].set_ylabel("Active TAM Width", fontweight='bold')
    axes[2].set_xlabel("Normalized Timeline", fontweight='bold')
    axes[2].set_title("Global TAM Bus Width Utilization", fontweight='bold')
    axes[2].legend()
    axes[2].grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved 2D Execution Dashboard to '{output_path}'")


def run_2d_benchmark_suite(soc_name: str, soc: SoC2D, results_dir: str):
    print(f"\n==========================================================================")
    print(f"   RUNNING 2D PLANAR SOC TEST SCHEDULING EVALUATION: {soc_name}")
    print(f"   Cores: {len(soc.cores)} | Pmax: {soc.max_power}W | Wmax: {soc.max_tam_width}")
    print(f"==========================================================================")

    algos = [
        ("Greedy 2D Baseline", Greedy2DScheduler(soc)),
        ("Artificial Bee Colony (ABC 2D)", ABC2DScheduler(soc, colony_size=15, max_iterations=15)),
        ("Bat 2D Algorithm", Bat2DScheduler(soc, num_bats=15, max_iterations=15)),
        ("Firefly 2D Algorithm", Firefly2DScheduler(soc, num_fireflies=15, max_iterations=15)),
        ("Modified ACO (MACO 2D)", MACO2DScheduler(soc, num_ants=15, max_iterations=15)),
        ("H-MACO-FA Hybrid (2D)", HMACOFA2DScheduler(soc, num_ants=15, num_fireflies=12, max_iterations=15)),
    ]

    results = {}
    for name, scheduler in algos:
        t0 = time.time()
        res = scheduler.optimize()
        t1 = time.time()
        results[name] = res
        print(f"[{name:<30}] Makespan: {res.makespan:>8,} cycles | Peak P: {res.peak_power:5.2f}W | TAM: {res.max_tam_used:<2}/{soc.max_tam_width:<2} | Status: {res.constraint_status} | Time: {(t1-t0):.3f}s")

    clean_name = "d695" if "d695" in soc_name.lower() else "p22810"
    plot_2d_gantt_chart(results, f"{soc_name}", os.path.join(results_dir, f"gantt_{clean_name}_2d.png"))
    plot_2d_execution_dashboard(results, f"{soc_name}", os.path.join(results_dir, f"dashboard_{clean_name}_2d.png"), soc.max_power, soc.max_tam_width)

    return results


def main():
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    # 1. d695 2D Evaluation
    soc_d695 = ITC02BenchmarkLoader2D.load_d695_2d(max_tam_width=16, max_power=45.89)
    res_d695 = run_2d_benchmark_suite("ITC'02 d695 (2D Planar)", soc_d695, results_dir)

    # 2. p22810 2D Evaluation
    soc_p22810 = ITC02BenchmarkLoader2D.load_p22810_2d(max_tam_width=32, max_power=94.05)
    res_p22810 = run_2d_benchmark_suite("ITC'02 p22810 (2D Planar)", soc_p22810, results_dir)

    # 3. Hardware-in-the-Loop Replay
    print("\n==========================================================================")
    print("      RUNNING 2D HARDWARE-IN-THE-LOOP (HIL) VALIDATION (RPi HIL Bridge)")
    print("==========================================================================")
    tester = RaspberryPi5Tester2D(mock_mode=True)
    hil_report = tester.replay_schedule(res_d695["Modified ACO (MACO 2D)"])
    print("\n--- 2D HIL Physical Schedule Replay Summary ---")
    print(json.dumps(hil_report, indent=2))

    # Save summary report text
    summary_txt_path = os.path.join(results_dir, "2d_scheduling_summary.txt")
    with open(summary_txt_path, "w") as f:
        f.write("========================================================================\n")
        f.write("        2D PLANAR SOC TEST SCHEDULING BENCHMARK RESULTS SUMMARY        \n")
        f.write("========================================================================\n\n")

        f.write("ITC'02 d695 2D Benchmark (10 Cores, Pmax=45.89W, Wmax=16):\n")
        for alg, r in res_d695.items():
            f.write(f"  - {alg:<30}: Makespan={r.makespan:,} cycles | Peak P={r.peak_power:.2f}W | TAM={r.max_tam_used}/16 | Status={r.constraint_status}\n")

        f.write("\nITC'02 p22810 2D Benchmark (30 Cores, Pmax=94.05W, Wmax=32):\n")
        for alg, r in res_p22810.items():
            f.write(f"  - {alg:<30}: Makespan={r.makespan:,} cycles | Peak P={r.peak_power:.2f}W | TAM={r.max_tam_used}/32 | Status={r.constraint_status}\n")

    print(f"\nSaved 2D scheduling summary to '{summary_txt_path}'")


if __name__ == "__main__":
    main()
