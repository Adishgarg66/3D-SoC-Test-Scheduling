"""
fixed_stacking/experiments/evaluate_paper_format.py
=====================================================
Paper-Aligned Multi-TAM Benchmark Evaluation Suite.
Generates experimental output tables matching the publication format of:
"Test Architecture Optimization for Post-bond Test and Pre-bond Tests of 3D SoCs Using TAM Reuse"
(Roy & Giri, 2023 - Tables 3 & 4).

Sweeps TAM Widths (16, 24, 32, 40, 48, 56, 64) across:
1. Fixed Layer Stacking (Mentor-Requested Partitioning - Table 2)
2. All 5 Swarm Metaheuristics (Greedy, ABC, Bat, Firefly, MACO)
3. Full VLSI Electronic & Computer Constraints (TAM, Power, TSV, Thermal)

Saves output tables directly to fixed_stacking/results/paper_format_results.md and paper_format_results.txt.
"""

import os
import sys
import time
import random
import numpy as np

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.constraints.vlsi_constraints import STANDARD_TAM_SWEEP, verify_all_vlsi_constraints
from src.models.soc_3d_fixed import FixedBenchmarkLoader, SoC3DFixed
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler


def evaluate_fixed_tam_sweep(benchmark_name: str, loader_func, tsv_budget: int):
    print("\n" + "=" * 105)
    print(f"   EXPERIMENTAL RESULTS FOR {benchmark_name.upper()} POST-BOND TEST (TSV LIMIT = {tsv_budget})")
    print(f"   Format Aligned with Roy & Giri (2023) Table 3 & 4 | Structured Fixed Stacking")
    print("=" * 105)

    header = f"{'TAM Width':<10} | {'Algorithm':<15} | {'Test Time (CC)':<16} | {'TSV Used':<10} | {'Run Time (s)':<12} | {'Peak Power (W)':<14} | {'Peak Tj (°C)':<12} | {'Status'}"
    print(header)
    print("-" * len(header))

    algorithms = [
        ("Greedy 3D", Greedy3DScheduler),
        ("ABC 3D", ABC3DScheduler),
        ("Bat 3D", Bat3DScheduler),
        ("Firefly 3D", Firefly3DScheduler),
        ("MACO 3D", MACO3DScheduler),
        ("H-MACO-FA 3D", HMACOFA3DScheduler),
    ]

    summary_rows = []

    for tam_w in STANDARD_TAM_SWEEP:
        soc = loader_func(max_tam_width=tam_w, max_tsv=tsv_budget)

        for alg_name, alg_class in algorithms:
            random.seed(42)
            np.random.seed(42)

            t0 = time.perf_counter()

            if alg_class == Greedy3DScheduler:
                scheduler = alg_class(soc)
            elif alg_class == ABC3DScheduler:
                scheduler = alg_class(soc, colony_size=15, max_iterations=12)
            elif alg_class == Bat3DScheduler:
                scheduler = alg_class(soc, num_bats=15, max_iterations=12)
            elif alg_class == Firefly3DScheduler:
                scheduler = alg_class(soc, num_fireflies=15, max_iterations=12)
            elif alg_class == MACO3DScheduler:
                scheduler = alg_class(soc, num_ants=15, max_iterations=12)
            elif alg_class == HMACOFA3DScheduler:
                scheduler = alg_class(soc, num_ants=15, num_fireflies=12, max_iterations=12)

            res = scheduler.optimize()
            t1 = time.perf_counter()
            exec_time_sec = t1 - t0

            is_valid, status = verify_all_vlsi_constraints(
                peak_power=res.peak_power, max_power=soc.max_power,
                peak_temp_celsius=res.peak_temperature, max_temp_celsius=soc.max_temperature - 273.15,
                max_tsv_used=res.max_tsv_used, max_tsv_bandwidth=soc.max_tsv_bandwidth
            )

            row_str = f"{tam_w:<10} | {alg_name:<15} | {res.makespan:<16,} | {res.max_tsv_used:<4}/{soc.max_tsv_bandwidth:<5} | {exec_time_sec:<12.4f} | {res.peak_power:<6.2f}/{soc.max_power:<6.1f} | {res.peak_temperature:<12.1f} | {status}"
            print(row_str)

            summary_rows.append({
                "tam_width": tam_w,
                "algorithm": alg_name,
                "makespan_cc": res.makespan,
                "tsv_used": res.max_tsv_used,
                "tsv_budget": soc.max_tsv_bandwidth,
                "runtime_sec": round(exec_time_sec, 4),
                "peak_power": res.peak_power,
                "max_power": soc.max_power,
                "peak_tj": res.peak_temperature,
                "status": status
            })

    print("-" * len(header))
    return summary_rows


def main():
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    # 1. Evaluate p22810 Fixed Stacking across TAM widths 16 to 64
    p22810_results = evaluate_fixed_tam_sweep(
        benchmark_name="ITC'02 p22810",
        loader_func=FixedBenchmarkLoader.load_p22810_fixed,
        tsv_budget=80
    )

    # 2. Evaluate d695 Fixed Stacking across TAM widths 16 to 64
    d695_results = evaluate_fixed_tam_sweep(
        benchmark_name="ITC'02 d695",
        loader_func=FixedBenchmarkLoader.load_d695_fixed,
        tsv_budget=16
    )

    # Save to fixed_stacking/results/paper_format_results.md
    md_path = os.path.join(results_dir, "paper_format_results.md")
    with open(md_path, "w") as f:
        f.write("# Paper-Aligned Multi-TAM Benchmark Evaluation Results (Roy & Giri, 2023)\n\n")
        
        f.write("## ITC'02 p22810 Benchmark Results (Fixed Stacking, TSV Limit = 80, Pmax = 94.05W)\n\n")
        f.write("| TAM Width | Algorithm | Test Time (CC) | TSV Used | Run Time (s) | Peak Power (W) | Peak Tj (°C) | Status |\n")
        f.write("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for r in p22810_results:
            f.write(f"| {r['tam_width']} | **{r['algorithm']}** | {r['makespan_cc']:,} | {r['tsv_used']} / {r['tsv_budget']} | {r['runtime_sec']:.4f} | {r['peak_power']:.2f}W / {r['max_power']:.1f}W | {r['peak_tj']:.1f}°C | **{r['status']}** |\n")

        f.write("\n\n## ITC'02 d695 Benchmark Results (Fixed Stacking, TSV Limit = 16, Pmax = 45.89W)\n\n")
        f.write("| TAM Width | Algorithm | Test Time (CC) | TSV Used | Run Time (s) | Peak Power (W) | Peak Tj (°C) | Status |\n")
        f.write("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for r in d695_results:
            f.write(f"| {r['tam_width']} | **{r['algorithm']}** | {r['makespan_cc']:,} | {r['tsv_used']} / {r['tsv_budget']} | {r['runtime_sec']:.4f} | {r['peak_power']:.2f}W / {r['max_power']:.1f}W | {r['peak_tj']:.1f}°C | **{r['status']}** |\n")

    print(f"\nSaved markdown paper-format results table to '{md_path}'")
    print("\n==========================================================================")
    print("   ALL PAPER-ALIGNED MULTI-TAM EVALUATIONS COMPLETED SUCCESSFULLY!")
    print("==========================================================================")


if __name__ == "__main__":
    main()
