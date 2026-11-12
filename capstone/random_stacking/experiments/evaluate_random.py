"""
base_random_stacking/experiments/evaluate_random.py
==================================================
Runner script for Baseline Random 3D Stacking Benchmark Evaluation.
Preserves the baseline dynamic / random 3D layer assignment setup.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.models.soc_3d import ITC02BenchmarkLoader
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler


def run_random_benchmark(soc_name: str, soc):
    print(f"\n==========================================================================")
    print(f"   RUNNING BASELINE RANDOM 3D STACKING EVALUATION: {soc_name}")
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

    for name, scheduler in algos:
        t0 = time.time()
        res = scheduler.optimize()
        t1 = time.time()
        print(f"[{name:<30}] Makespan: {res.makespan:>8,} cycles | Peak P: {res.peak_power:5.2f}W | Peak Tj: {res.peak_temperature:5.1f}°C | TSV: {res.max_tsv_used:<2}/{soc.max_tsv_bandwidth:<2} | Status: {res.constraint_status} | Time: {(t1-t0):.3f}s")


def main():
    soc_d695 = ITC02BenchmarkLoader.load_d695_3d(max_tam_width=16, max_power=45.89, max_tsv=16)
    run_random_benchmark("ITC'02 d695 (Random Stacking)", soc_d695)

    soc_p22810 = ITC02BenchmarkLoader.load_p22810_3d(max_tam_width=32, max_power=94.05, max_tsv=24)
    run_random_benchmark("ITC'02 p22810 (Random Stacking)", soc_p22810)


if __name__ == "__main__":
    main()
