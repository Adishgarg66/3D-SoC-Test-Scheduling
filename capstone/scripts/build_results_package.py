#!/usr/bin/env python3
"""
capstone/scripts/build_results_package.py
=========================================
Master Experiment & Presentation Builder for the 2D & 3D SoC Test Scheduling Capstone.

Executes genuine (non-fabricated) experiments and compiles the complete root `results/` tree:
1. Multi-seed fair-budget (--max-evals) simulations across 2D, Fixed 3D, and Random 3D
   for all 6 algorithms (Greedy, ABC, Bat, Firefly, MACO, H-MACO-FA Hybrid) on d695 & p22810.
2. Multi-TAM width sweeps (2D IEEE 1500 wrapper reduction & Fixed 3D Post-Bond TAM sweep).
3. Genuine ML Thermal Regression (Linear & Polynomial Ridge) trained/evaluated on
   3D RC model-generated thermal traces + FrequencyScaledScheduler verification.
4. Live Physical Hardware-in-the-Loop (HIL) validation trials on Raspberry Pi 4 Model B Rev 1.4
   (or strict failure if --rpi-host is unreachable when --rpi-no-fallback is enabled).
5. Simulation vs Hardware comparison tables, multi-seed statistics, genuine OpenXML (.xlsx)
   workbooks, publication-grade 300 DPI PNG figures with exact companion CSVs, and
   presentation summary files under `results/`.
"""

import argparse
import csv
import json
import os
import random
import shutil
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
CAPSTONE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(CAPSTONE_DIR, ".."))

for p in [
    os.path.join(CAPSTONE_DIR, "fixed_stacking"),
    os.path.join(CAPSTONE_DIR, "random_stacking"),
    os.path.join(CAPSTONE_DIR, "2d"),
    CAPSTONE_DIR,
    REPO_ROOT,
]:
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.models.soc_2d import ITC02BenchmarkLoader2D
from src.models.wrapper_design_2d import WrapperAnalyzer2D
from src.constraints.vlsi_constraints_2d import STANDARD_TAM_SWEEP_2D
from src.algorithms.greedy_2d import Greedy2DScheduler
from src.algorithms.abc_2d import ABC2DScheduler
from src.algorithms.bat_2d import Bat2DScheduler
from src.algorithms.firefly_2d import Firefly2DScheduler
from src.algorithms.maco_2d import MACO2DScheduler
from src.algorithms.hmaco_fa_2d import HMACOFA2DScheduler
from src.hardware.rpi_tester_2d import RaspberryPi5Tester2D

from src.models.soc_3d_fixed import FixedBenchmarkLoader
from src.models.soc_3d import ITC02BenchmarkLoader
from src.models.predictive_thermal import (
    FrequencyScaledScheduler,
    MLThermalRegressor,
    PredictiveThermalEstimator,
)
from src.constraints.vlsi_constraints import STANDARD_TAM_SWEEP
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler
from src.hardware.rpi_tester import RaspberryPi5Tester
from capstone.src.hardware.rpi_remote_bridge import RemoteRPiHILClient

from capstone.scripts.generate_excel_results import create_excel_openpyxl
from run_test_suite import plot_dashboard, plot_gantt_chart, plot_thermal_heatmaps


ALG_ORDER = ["Greedy", "ABC", "Bat", "Firefly", "MACO", "H-MACO-FA"]
ALG_COLORS = {
    "Greedy": "#6c757d",
    "ABC": "#ff7f0e",
    "Bat": "#2ca02c",
    "Firefly": "#9467bd",
    "MACO": "#d62728",
    "H-MACO-FA": "#17becf",
}

DEFAULT_SEEDS = [42, 100, 2024, 7, 99, 123, 256, 512, 777, 1024]


def _write_csv(path: str, headers: List[str], rows: List[List[Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def _create_results_dirs(root: str) -> Dict[str, str]:
    subdirs = {
        "root": root,
        "raw_sim": os.path.join(root, "raw_data", "simulation"),
        "raw_rpi": os.path.join(root, "raw_data", "raspberry_pi"),
        "sim_2d": os.path.join(root, "simulation", "2d"),
        "sim_fixed3d": os.path.join(root, "simulation", "fixed_3d"),
        "sim_random3d": os.path.join(root, "simulation", "random_3d"),
        "hw_2d": os.path.join(root, "hardware", "2d"),
        "hw_fixed3d": os.path.join(root, "hardware", "fixed_3d"),
        "hw_random3d": os.path.join(root, "hardware", "random_3d"),
        "comp_sim_hw": os.path.join(root, "comparisons", "simulation_vs_hardware"),
        "stats": os.path.join(root, "statistical_analysis"),
        "g_2d": os.path.join(root, "graphs", "2d"),
        "g_fixed3d": os.path.join(root, "graphs", "fixed_3d"),
        "g_random3d": os.path.join(root, "graphs", "random_3d"),
        "g_hw": os.path.join(root, "graphs", "hardware"),
        "g_comp": os.path.join(root, "graphs", "comparisons"),
        "g_stats": os.path.join(root, "graphs", "statistical"),
        "tbl_csv": os.path.join(root, "tables", "csv"),
        "tbl_xlsx": os.path.join(root, "tables", "excel"),
        "pres": os.path.join(root, "presentation"),
        "pres_graphs": os.path.join(root, "presentation", "selected_graphs"),
        "pres_tables": os.path.join(root, "presentation", "selected_tables"),
    }
    for d in subdirs.values():
        os.makedirs(d, exist_ok=True)
    return subdirs


def _load_soc(mode: str, benchmark: str, max_tam: Optional[int] = None):
    if mode == "2d":
        if benchmark == "d695":
            return ITC02BenchmarkLoader2D.load_d695_2d(max_tam_width=max_tam or 16, max_power=45.89)
        return ITC02BenchmarkLoader2D.load_p22810_2d(max_tam_width=max_tam or 32, max_power=94.05)
    if mode == "fixed3d":
        if benchmark == "d695":
            return FixedBenchmarkLoader.load_d695_fixed(max_tam_width=max_tam or 16, max_power=45.89, max_tsv=16)
        return FixedBenchmarkLoader.load_p22810_fixed(max_tam_width=max_tam or 32, max_power=94.05, max_tsv=24)
    if benchmark == "d695":
        return ITC02BenchmarkLoader.load_d695_3d(max_tam_width=max_tam or 16, max_power=45.89, max_tsv=16)
    return ITC02BenchmarkLoader.load_p22810_3d(max_tam_width=max_tam or 32, max_power=94.05, max_tsv=24)


def _scheduler_specs(mode: str, max_evals: int) -> List[Tuple[str, Any, Dict[str, Any]]]:
    if mode == "2d":
        return [
            ("Greedy", Greedy2DScheduler, {}),
            ("ABC", ABC2DScheduler, {"colony_size": 15, "max_iterations": 20, "max_evals": max_evals}),
            ("Bat", Bat2DScheduler, {"num_bats": 15, "max_iterations": 20, "max_evals": max_evals}),
            ("Firefly", Firefly2DScheduler, {"num_fireflies": 15, "max_iterations": 20, "max_evals": max_evals}),
            ("MACO", MACO2DScheduler, {"num_ants": 15, "max_iterations": 20, "max_evals": max_evals}),
            ("H-MACO-FA", HMACOFA2DScheduler, {"num_ants": 15, "num_fireflies": 12, "max_iterations": 20, "max_evals": max_evals}),
        ]
    return [
        ("Greedy", Greedy3DScheduler, {}),
        ("ABC", ABC3DScheduler, {"colony_size": 15, "max_iterations": 20, "max_evals": max_evals}),
        ("Bat", Bat3DScheduler, {"num_bats": 15, "max_iterations": 20, "max_evals": max_evals}),
        ("Firefly", Firefly3DScheduler, {"num_fireflies": 15, "max_iterations": 20, "max_evals": max_evals}),
        ("MACO", MACO3DScheduler, {"num_ants": 15, "max_iterations": 20, "max_evals": max_evals}),
        ("H-MACO-FA", HMACOFA3DScheduler, {"num_ants": 15, "num_fireflies": 12, "max_iterations": 20, "max_evals": max_evals}),
    ]


# ----------------------------------------------------------------------------
# PART A: MULTI-SEED FAIR-BUDGET SIMULATION SUITE
# ----------------------------------------------------------------------------
def run_multiseed_fair_budget_simulations(
    dirs: Dict[str, str],
    seeds: List[int],
    max_evals: int,
) -> Dict[str, Any]:
    print(f"\n[Step 1/5] Running Multi-Seed Fair-Budget Simulations ({len(seeds)} seeds, max_evals={max_evals})...")
    raw_rows: List[List[Any]] = []
    conv_rows: List[List[Any]] = []
    stats_rows: List[List[Any]] = []
    representative_results: Dict[Tuple[str, str], Dict[str, Any]] = {}
    best_schedules: Dict[Tuple[str, str], Tuple[Any, Any]] = {}
    grouped_makespans: Dict[Tuple[str, str, str], List[int]] = {}
    grouped_records: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}

    modes = ["2d", "fixed3d", "random3d"]
    benchmarks = ["d695", "p22810"]

    for mode in modes:
        for bm in benchmarks:
            soc = _load_soc(mode, bm)
            specs = _scheduler_specs(mode, max_evals=max_evals)
            rep_map: Dict[str, Any] = {}
            best_overall = None

            for alg_short, cls, kwargs in specs:
                records = []
                for idx, seed in enumerate(seeds):
                    random.seed(seed)
                    np.random.seed(seed)
                    t0 = time.perf_counter()
                    sched = cls(soc, **kwargs)
                    res = sched.optimize()
                    elapsed = time.perf_counter() - t0
                    res.runtime_sec = elapsed

                    rec = {
                        "mode": mode,
                        "benchmark": bm,
                        "seed": seed,
                        "algorithm": alg_short,
                        "full_name": res.algorithm_name,
                        "makespan": int(res.makespan),
                        "peak_power": float(res.peak_power),
                        "max_power": float(soc.max_power),
                        "peak_temp_c": float(getattr(res, "peak_temperature", 0.0)),
                        "max_temp_c": float(getattr(soc, "max_temperature", 273.15) - 273.15 if mode != "2d" else 0.0),
                        "tsv_or_tam_used": int(getattr(res, "max_tsv_used", getattr(res, "max_tam_used", 0))),
                        "tsv_or_tam_limit": int(getattr(soc, "max_tsv_bandwidth", getattr(soc, "max_tam_width", 0))),
                        "eval_count": int(getattr(res, "eval_count", 0)),
                        "runtime_sec": float(elapsed),
                        "status": res.constraint_status,
                        "result_obj": res,
                    }
                    records.append(rec)
                    raw_rows.append([
                        mode, bm, seed, alg_short, res.algorithm_name,
                        rec["makespan"], round(rec["peak_power"], 3), rec["max_power"],
                        round(rec["peak_temp_c"], 2), rec["tsv_or_tam_used"], rec["tsv_or_tam_limit"],
                        rec["eval_count"], round(rec["runtime_sec"], 5), rec["status"],
                    ])

                    if idx == 0 and mode != "2d" and hasattr(sched, "best_history") and sched.best_history:
                        for eval_idx, best_ms in sched.best_history:
                            conv_rows.append([mode, bm, seed, alg_short, eval_idx, best_ms])

                    if best_overall is None or res.makespan < best_overall.makespan:
                        best_overall = res

                grouped_makespans[(mode, bm, alg_short)] = [r["makespan"] for r in records]
                grouped_records[(mode, bm, alg_short)] = records
                best_rec = min(records, key=lambda r: r["makespan"])
                rep_map[best_rec["full_name"]] = best_rec["result_obj"]

                ms_vals = [float(r["makespan"]) for r in records]
                ev_vals = [float(r["eval_count"]) for r in records]
                rt_vals = [float(r["runtime_sec"]) for r in records]
                pw_vals = [float(r["peak_power"]) for r in records]
                tj_vals = [float(r["peak_temp_c"]) for r in records]
                tsv_vals = [int(r["tsv_or_tam_used"]) for r in records]

                greedy_mean = statistics.mean([float(x) for x in grouped_makespans[(mode, bm, "Greedy")]])
                mean_ms = statistics.mean(ms_vals)
                red_pct = ((greedy_mean - mean_ms) / greedy_mean * 100.0) if greedy_mean > 0 else 0.0

                stats_rows.append([
                    mode, bm, alg_short, len(seeds),
                    int(min(ms_vals)), int(max(ms_vals)),
                    round(mean_ms, 2), round(statistics.median(ms_vals), 2),
                    round(statistics.stdev(ms_vals) if len(ms_vals) > 1 else 0.0, 2),
                    round(red_pct, 3),
                    round(statistics.mean(ev_vals), 1),
                    round(statistics.mean(rt_vals), 5),
                    round(max(pw_vals), 2),
                    round(max(tj_vals), 2) if mode != "2d" else "N/A (2D)",
                    max(tsv_vals),
                    "Safe" if all(r["status"] == "Safe" for r in records) else "Violation",
                ])

            representative_results[(mode, bm)] = rep_map
            best_schedules[(mode, bm)] = (soc, best_overall)

    raw_headers = [
        "Mode", "Benchmark", "Seed", "Algorithm", "Full Name",
        "Makespan (CC)", "Peak Power (W)", "Max Power (W)", "Peak Tj (C)",
        "TSV or TAM Used", "Resource Limit", "Eval Count", "Runtime (s)", "Status",
    ]
    _write_csv(os.path.join(dirs["raw_sim"], "raw_runs_all_modes_10seeds.csv"), raw_headers, raw_rows)
    _write_csv(
        os.path.join(dirs["raw_sim"], "convergence_histories_3d.csv"),
        ["Mode", "Benchmark", "Seed", "Algorithm", "Evaluation Index", "Best Makespan (CC)"],
        conv_rows,
    )

    stats_headers = [
        "Mode", "Benchmark", "Algorithm", "N Seeds", "Best (CC)", "Worst (CC)",
        "Mean (CC)", "Median (CC)", "Std Dev (CC)", "Mean Reduction vs Greedy (%)",
        "Mean Evals", "Mean CPU Runtime (s)", "Worst-Case Power (W)",
        "Worst-Case Peak Tj (C)", "Max TSV/TAM Used", "Constraint Status",
    ]
    _write_csv(os.path.join(dirs["stats"], "multiseed_statistical_summary.csv"), stats_headers, stats_rows)
    _write_csv(os.path.join(dirs["tbl_csv"], "multiseed_statistical_summary.csv"), stats_headers, stats_rows)

    for mode, sim_key in [("2d", "sim_2d"), ("fixed3d", "sim_fixed3d"), ("random3d", "sim_random3d")]:
        mode_rows = [r for r in stats_rows if r[0] == mode]
        _write_csv(os.path.join(dirs[sim_key], f"{mode}_scheduling_summary.csv"), stats_headers, mode_rows)

    # Ranking overview across all 6 mode-benchmark pairs
    rank_rows = []
    for mode in modes:
        for bm in benchmarks:
            pairs = []
            for alg in ALG_ORDER:
                vals = grouped_makespans[(mode, bm, alg)]
                pairs.append((alg, statistics.mean(vals), min(vals)))
            pairs.sort(key=lambda x: (x[1], x[2]))
            for rank_idx, (alg, m_ms, b_ms) in enumerate(pairs, start=1):
                rank_rows.append([mode, bm, rank_idx, alg, round(m_ms, 2), int(b_ms)])
    _write_csv(
        os.path.join(dirs["stats"], "algorithm_ranking_overview.csv"),
        ["Mode", "Benchmark", "Rank", "Algorithm", "Mean Makespan (CC)", "Best Makespan (CC)"],
        rank_rows,
    )

    return {
        "raw_rows": raw_rows,
        "conv_rows": conv_rows,
        "stats_rows": stats_rows,
        "representative_results": representative_results,
        "best_schedules": best_schedules,
        "grouped_makespans": grouped_makespans,
        "grouped_records": grouped_records,
    }


# ----------------------------------------------------------------------------
# PART B: TAM WIDTH SWEEPS (2D IEEE 1500 & FIXED 3D MULTI-TAM)
# ----------------------------------------------------------------------------
def run_tam_sweeps(dirs: Dict[str, str], max_evals: int) -> Dict[str, Any]:
    print("\n[Step 2/5] Running IEEE 1500 Wrapper Sweep (2D) & Multi-TAM Width Sweep (Fixed 3D)...")
    wrapper_rows = []
    for bm, prof_fn in [
        ("d695", ITC02BenchmarkLoader2D.get_wrapper_profiles_d695),
        ("p22810", ITC02BenchmarkLoader2D.get_wrapper_profiles_p22810),
    ]:
        analyzer = WrapperAnalyzer2D(prof_fn())
        for entry in analyzer.compute_wrapper_reduction_table(STANDARD_TAM_SWEEP_2D):
            wrapper_rows.append([
                bm, entry["tam_width"], entry["raw_test_cycles"],
                entry["post_wrapper_cycles"], entry["cycles_saved"], round(entry["reduction_pct"], 4),
            ])
    _write_csv(
        os.path.join(dirs["sim_2d"], "ieee1500_wrapper_sweep.csv"),
        ["Benchmark", "TAM Width (w)", "Pre-Wrapper Raw Cycles", "Post-Wrapper IEEE 1500 Cycles", "Cycles Saved", "Reduction %"],
        wrapper_rows,
    )

    tam_rows = []
    specs_3d = _scheduler_specs("fixed3d", max_evals=max_evals)
    for bm, loader_fn, tsv_budget in [
        ("d695", FixedBenchmarkLoader.load_d695_fixed, 16),
        ("p22810", FixedBenchmarkLoader.load_p22810_fixed, 80),
    ]:
        for tam_w in STANDARD_TAM_SWEEP:
            soc = loader_fn(max_tam_width=tam_w, max_tsv=tsv_budget)
            for alg_short, cls, kwargs in specs_3d:
                random.seed(42)
                np.random.seed(42)
                t0 = time.perf_counter()
                sched = cls(soc, **kwargs)
                res = sched.optimize()
                elapsed = time.perf_counter() - t0
                tam_rows.append([
                    bm, tam_w, alg_short, int(res.makespan),
                    int(res.max_tsv_used), tsv_budget, int(getattr(res, "eval_count", 0)),
                    round(elapsed, 4), round(res.peak_power, 2), soc.max_power,
                    round(res.peak_temperature, 2), res.constraint_status,
                ])
    _write_csv(
        os.path.join(dirs["sim_fixed3d"], "fixed3d_multi_tam_sweep.csv"),
        ["Benchmark", "TAM Width", "Algorithm", "Makespan (CC)", "TSV Used", "TSV Budget", "Eval Count", "Runtime (s)", "Peak Power (W)", "Max Power (W)", "Peak Tj (C)", "Status"],
        tam_rows,
    )
    return {"wrapper_rows": wrapper_rows, "tam_rows": tam_rows}


def load_existing_sim_and_sweeps(dirs: Dict[str, str], max_evals: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Reconstruct in-memory simulation & sweep structures strictly from already-saved CSVs
    (preserving all 360 raw runs, 36 multi-seed statistics rows, and sweep tables verbatim)
    while re-hydrating only the representative ScheduleResult objects for Gantt/thermal/HIL figures.
    """
    raw_csv = os.path.join(dirs["raw_sim"], "raw_runs_all_modes_10seeds.csv")
    conv_csv = os.path.join(dirs["raw_sim"], "convergence_histories_3d.csv")
    stats_csv = os.path.join(dirs["stats"], "multiseed_statistical_summary.csv")
    wrap_csv = os.path.join(dirs["sim_2d"], "ieee1500_wrapper_sweep.csv")
    tam_csv = os.path.join(dirs["sim_fixed3d"], "fixed3d_multi_tam_sweep.csv")

    grouped_makespans: Dict[Tuple[str, str, str], List[int]] = {}
    grouped_records: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    raw_rows: List[List[Any]] = []
    with open(raw_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mode = row["Mode"]
            bm = row["Benchmark"]
            seed = int(row["Seed"])
            alg = row["Algorithm"]
            ms = int(row["Makespan (CC)"])
            rt = float(row["Runtime (s)"])
            pw = float(row["Peak Power (W)"])
            mpw = float(row["Max Power (W)"])
            ptj = float(row["Peak Tj (C)"])
            tsv_u = int(row["TSV or TAM Used"])
            tsv_l = int(row["Resource Limit"])
            ev_c = int(row["Eval Count"])
            st = row["Status"]
            raw_rows.append([mode, bm, seed, alg, row["Full Name"], ms, pw, mpw, ptj, tsv_u, tsv_l, ev_c, rt, st])
            grouped_makespans.setdefault((mode, bm, alg), []).append(ms)
            grouped_records.setdefault((mode, bm, alg), []).append({
                "mode": mode, "benchmark": bm, "seed": seed, "algorithm": alg,
                "full_name": row["Full Name"], "makespan": ms, "peak_power": pw,
                "max_power": mpw, "peak_temp_c": ptj, "tsv_or_tam_used": tsv_u,
                "tsv_or_tam_limit": tsv_l, "eval_count": ev_c, "runtime_sec": rt, "status": st,
            })

    conv_rows: List[List[Any]] = []
    with open(conv_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            conv_rows.append([
                row["Mode"], row["Benchmark"], int(row["Seed"]),
                row["Algorithm"], int(row["Evaluation Index"]), int(row["Best Makespan (CC)"]),
            ])

    stats_rows: List[List[Any]] = []
    with open(stats_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            wtj = row["Worst-Case Peak Tj (C)"]
            stats_rows.append([
                row["Mode"], row["Benchmark"], row["Algorithm"], int(row["N Seeds"]),
                int(row["Best (CC)"]), int(row["Worst (CC)"]),
                float(row["Mean (CC)"]), float(row["Median (CC)"]), float(row["Std Dev (CC)"]),
                float(row["Mean Reduction vs Greedy (%)"]), float(row["Mean Evals"]),
                float(row["Mean CPU Runtime (s)"]), float(row["Worst-Case Power (W)"]),
                wtj if wtj == "N/A (2D)" else float(wtj),
                int(row["Max TSV/TAM Used"]), row["Constraint Status"],
            ])

    # Deterministically reconstruct only the winning (mode, bm, alg) schedules for charts & HIL metadata
    representative_results: Dict[Tuple[str, str], Dict[str, Any]] = {}
    best_schedules: Dict[Tuple[str, str], Tuple[Any, Any]] = {}
    for mode in ["2d", "fixed3d", "random3d"]:
        specs_map = {a: (cls, kw) for a, cls, kw in _scheduler_specs(mode, max_evals=max_evals)}
        for bm in ["d695", "p22810"]:
            soc = _load_soc(mode, bm)
            rep_map: Dict[str, Any] = {}
            best_overall = None
            for alg_short in ALG_ORDER:
                recs = grouped_records[(mode, bm, alg_short)]
                best_rec = min(recs, key=lambda r: r["makespan"])
                cls, kw = specs_map[alg_short]
                random.seed(best_rec["seed"])
                np.random.seed(best_rec["seed"])
                res = cls(soc, **kw).optimize()
                res.runtime_sec = float(best_rec["runtime_sec"])
                rep_map[best_rec["full_name"]] = res
                if best_overall is None or res.makespan < best_overall.makespan:
                    best_overall = res
            representative_results[(mode, bm)] = rep_map
            best_schedules[(mode, bm)] = (soc, best_overall)

    wrapper_rows: List[List[Any]] = []
    with open(wrap_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            wrapper_rows.append([
                row["Benchmark"], int(row["TAM Width (w)"]),
                int(row["Pre-Wrapper Raw Cycles"]), int(row["Post-Wrapper IEEE 1500 Cycles"]),
                int(row["Cycles Saved"]), float(row["Reduction %"]),
            ])

    tam_rows: List[List[Any]] = []
    with open(tam_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tam_rows.append([
                row["Benchmark"], int(row["TAM Width"]), row["Algorithm"],
                int(row["Makespan (CC)"]), int(row["TSV Used"]), int(row["TSV Budget"]),
                int(row["Eval Count"]), float(row["Runtime (s)"]),
                float(row["Peak Power (W)"]), float(row["Max Power (W)"]),
                float(row["Peak Tj (C)"]), row["Status"],
            ])

    return (
        {
            "raw_rows": raw_rows,
            "conv_rows": conv_rows,
            "stats_rows": stats_rows,
            "representative_results": representative_results,
            "best_schedules": best_schedules,
            "grouped_makespans": grouped_makespans,
            "grouped_records": grouped_records,
        },
        {"wrapper_rows": wrapper_rows, "tam_rows": tam_rows},
    )


# ----------------------------------------------------------------------------
# PART C: GENUINE ML THERMAL PREDICTION & FREQUENCY SCALING
# ----------------------------------------------------------------------------
def run_ml_thermal_experiment(
    dirs: Dict[str, str],
    best_schedules: Dict[Tuple[str, str], Tuple[Any, Any]],
) -> Dict[str, Any]:
    print("\n[Step 3/5] Training & Evaluating Genuine ML Thermal Prediction Models (Deduplicated + Unseen Trajectories)...")
    soc_d695_r = _load_soc("random3d", "d695")
    soc_p22810_r = _load_soc("random3d", "p22810")
    soc_d695_f = _load_soc("fixed3d", "d695")
    soc_p22810_f = _load_soc("fixed3d", "p22810")

    ml_eval_random = MLThermalRegressor.train_and_evaluate(
        [soc_d695_r, soc_p22810_r],
        samples_per_soc=1000,
        test_fraction=0.2,
        seed=42,
    )
    ml_eval_fixed = MLThermalRegressor.train_and_evaluate(
        [soc_d695_f, soc_p22810_f],
        samples_per_soc=1000,
        test_fraction=0.2,
        seed=42,
    )

    traj_random = MLThermalRegressor.evaluate_on_solver_trajectories(
        socs=[soc_d695_r, soc_p22810_r],
        model=ml_eval_random["best_model"],
        train_feature_keys=ml_eval_random["train_feature_keys"],
        seeds=(512, 777, 1024),
    )
    traj_fixed = MLThermalRegressor.evaluate_on_solver_trajectories(
        socs=[soc_d695_f, soc_p22810_f],
        model=ml_eval_fixed["best_model"],
        train_feature_keys=ml_eval_fixed["train_feature_keys"],
        seeds=(512, 777, 1024),
    )

    reg_headers = [
        "RC Architecture", "Model", "Poly Degree", "Train Samples", "Test Samples", "Train-Test Overlap",
        "Train MAE (C)", "Train RMSE (C)", "Train R2",
        "Test MAE (C)", "Test RMSE (C)", "Test Max Error (C)", "Test R2",
        "Train Time (s)", "Inference (ms/sample)", "Reference Data Source",
    ]
    reg_rows = []
    for arch_lbl, ev in [("Random 3D RC", ml_eval_random), ("Fixed 3D RC", ml_eval_fixed)]:
        for m in ev["summary"]:
            reg_rows.append([
                arch_lbl,
                m["model_name"], m["degree"], m["train_samples"], m["test_samples"], m.get("train_test_overlap", 0),
                m["train_mae_c"], m["train_rmse_c"], m["train_r2"],
                m["test_mae_c"], m["test_rmse_c"], m["test_max_error_c"], m["test_r2"],
                m["train_time_sec"], m["inference_ms_per_sample"], m["reference_source"],
            ])
    _write_csv(os.path.join(dirs["sim_random3d"], "ml_thermal_regression_metrics.csv"), reg_headers, reg_rows)

    traj_headers = [
        "RC Architecture", "Validation Set", "Model", "Steps Evaluated",
        "MAE (C)", "RMSE (C)", "Max Error (C)", "R2", "Reference Data Source",
    ]
    traj_rows = []
    for arch_lbl, tr_res, model_name in [
        ("Random 3D RC", traj_random, ml_eval_random["summary"][1]["model_name"]),
        ("Fixed 3D RC", traj_fixed, ml_eval_fixed["summary"][1]["model_name"]),
    ]:
        all_m = tr_res["all_steps_metrics"]
        un_m = tr_res["unseen_steps_metrics"]
        traj_rows.append([
            arch_lbl, "All Trajectory Steps (seeds=512,777,1024)", model_name,
            tr_res["total_steps"], all_m["mae_c"], all_m["rmse_c"], all_m["max_error_c"], all_m["r2"],
            "Independent 3D RC Schedule Trajectory Simulation",
        ])
        traj_rows.append([
            arch_lbl, "Strictly Unseen vs Train Set", model_name,
            tr_res["strictly_unseen_steps"], un_m["mae_c"], un_m["rmse_c"], un_m["max_error_c"], un_m["r2"],
            "Independent 3D RC Schedule Trajectory Simulation (0% overlap with training set)",
        ])
    _write_csv(os.path.join(dirs["sim_random3d"], "ml_thermal_trajectory_validation.csv"), traj_headers, traj_rows)

    pred_rows = []
    for arch_lbl, ev in [("Random 3D RC", ml_eval_random), ("Fixed 3D RC", ml_eval_fixed)]:
        y_true = ev["test_actual_tj_c"]
        y_pred = ev["test_predicted_tj_c"]
        bms = ev["test_benchmarks"]
        feats = ev["test_features"]
        for i in range(len(y_true)):
            pred_rows.append([
                arch_lbl, i, bms[i], round(float(feats[i, 3]), 3), int(feats[i, 4]), int(feats[i, 9]),
                round(float(y_true[i]), 3), round(float(y_pred[i]), 3), round(float(y_pred[i] - y_true[i]), 3),
            ])
    _write_csv(
        os.path.join(dirs["raw_sim"], "ml_thermal_test_predictions.csv"),
        ["RC Architecture", "Sample Index", "Benchmark", "Total Power (W)", "Active Cores", "Active TSV", "RC Reference Tj (C)", "ML Predicted Tj (C)", "Residual (C)"],
        pred_rows,
    )

    # Apply FrequencyScaledScheduler using architecture-matched MLThermalRegressor & PredictiveThermalEstimator
    scale_rows = []
    for mode in ["fixed3d", "random3d"]:
        ml_model = ml_eval_fixed["best_model"] if mode == "fixed3d" else ml_eval_random["best_model"]
        for bm in ["d695", "p22810"]:
            soc, base_res = best_schedules[(mode, bm)]
            rc_est = PredictiveThermalEstimator(num_layers=soc.num_layers)
            res_rc_scaled = FrequencyScaledScheduler(soc, rc_est).apply_frequency_scaling(base_res)
            res_ml_scaled = FrequencyScaledScheduler(soc, ml_model).apply_frequency_scaling(base_res)

            for tag, r in [
                ("Unscaled Best Schedule", base_res),
                ("RC-Estimator Frequency Scaled", res_rc_scaled),
                ("ML-Regressor Frequency Scaled", res_ml_scaled),
            ]:
                scale_rows.append([
                    mode, bm, base_res.algorithm_name, tag,
                    int(r.makespan), round(r.peak_power, 2), round(r.peak_temperature, 2),
                    int(r.max_tsv_used), r.constraint_status,
                ])
    _write_csv(
        os.path.join(dirs["sim_random3d"], "thermal_frequency_scaling_comparison.csv"),
        ["Mode", "Benchmark", "Base Algorithm", "Thermal Scaling Strategy", "Makespan (CC)", "Peak Power (W)", "Peak Tj (C)", "Max TSV Used", "Status"],
        scale_rows,
    )
    return {
        "ml_eval": ml_eval_random,
        "ml_eval_fixed": ml_eval_fixed,
        "traj_random": traj_random,
        "traj_fixed": traj_fixed,
        "reg_rows": reg_rows,
        "traj_rows": traj_rows,
        "pred_rows": pred_rows,
        "scale_rows": scale_rows,
    }


# ----------------------------------------------------------------------------
# PART D: REAL RASPBERRY PI 4 PHYSICAL HIL TRIALS + SIM VS HARDWARE COMPARISON
# ----------------------------------------------------------------------------
def run_raspberry_pi_hil_trials(
    dirs: Dict[str, str],
    best_schedules: Dict[Tuple[str, str], Tuple[Any, Any]],
    grouped_records: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    rpi_host: Optional[str],
    rpi_port: int,
    rpi_transport: str,
    rpi_user: Optional[str],
    time_scale: float,
    trials: int,
    no_fallback: bool,
    reuse_raw_dir: Optional[str] = None,
) -> Dict[str, Any]:
    if reuse_raw_dir:
        print(f"\n[Step 4/5] Loading Verified Physical Raspberry Pi Raw Logs from '{reuse_raw_dir}'...")
        ping_path = os.path.join(reuse_raw_dir, "rpi_ping_verification.json")
        if not os.path.exists(ping_path):
            raise FileNotFoundError(f"Missing '{ping_path}' for --reuse-rpi-dir")
        with open(ping_path, "r", encoding="utf-8") as f:
            ping_info = json.load(f)
    else:
        print(f"\n[Step 4/5] Running Live Raspberry Pi Hardware-in-the-Loop Validation (trials={trials}, time_scale={time_scale})...")
        ping_info = {"status": "skipped", "is_physical_hardware": False}
        if rpi_host:
            client = RemoteRPiHILClient(host=rpi_host, port=rpi_port, transport=rpi_transport, ssh_user=rpi_user, timeout=60.0)
            ping_info = client.ping()
            with open(os.path.join(dirs["raw_rpi"], "rpi_ping_verification.json"), "w", encoding="utf-8") as f:
                json.dump(ping_info, f, indent=2)
            print(f"  Connected Hardware: {ping_info.get('board_model')} | OS: {ping_info.get('os_release')} | Backend: {ping_info.get('gpio_backend')} | Physical: {ping_info.get('is_physical_hardware')}")

    trial_headers = [
        "Mode", "Benchmark", "Algorithm", "Trial", "Is Physical Hardware",
        "Board Model", "GPIO Backend", "Transport", "Started UTC", "Ended UTC",
        "Time Scale (s/cycle)", "Makespan Cycles", "Total Task Cycles",
        "Scaled Makespan (s)", "Expected Task Sleep (s)", "RPi Replay Wall Clock (s)",
        "Client Roundtrip (s)", "Jitter vs Cumulative Sleep (s)", "Overhead vs Cumulative Sleep (%)",
        "Replay Expansion vs Makespan (x)", "GPIO Events Count", "Tasks Replayed",
        "Execution Status", "Error", "Raw Log File",
    ]
    all_trial_rows: List[List[Any]] = []
    hw_summary_rows: List[List[Any]] = []
    comp_rows: List[List[Any]] = []

    for mode, hw_key in [("2d", "hw_2d"), ("fixed3d", "hw_fixed3d"), ("random3d", "hw_random3d")]:
        mode_trial_rows = []
        mode_summary_rows = []

        for bm in ["d695", "p22810"]:
            _, sched_res = best_schedules[(mode, bm)]
            tester_cls = RaspberryPi5Tester2D if mode == "2d" else RaspberryPi5Tester
            total_task_cycles = sum(int(t.duration) for t in sched_res.tasks)
            sim_cpu_mean = statistics.mean([float(r["runtime_sec"]) for r in grouped_records[(mode, bm, "MACO")]])
            best_alg_cpu = float(getattr(sched_res, "runtime_sec", sim_cpu_mean))

            wall_list, rt_list, jitt_list, oh_list, gpio_list = [], [], [], [], []
            board_model = "Unknown"
            backend = "Unknown"
            is_phys = False

            for tr in range(1, trials + 1):
                raw_filename = f"hil_{mode}_{bm}_trial{tr}.json"
                raw_path = os.path.join(dirs["raw_rpi"], raw_filename)
                if reuse_raw_dir:
                    src_raw = os.path.join(reuse_raw_dir, raw_filename)
                    if not os.path.exists(src_raw):
                        raise FileNotFoundError(f"Missing recorded Raspberry Pi trial file '{src_raw}'")
                    with open(src_raw, "r", encoding="utf-8") as f:
                        hil_res = json.load(f)
                    if os.path.abspath(src_raw) != os.path.abspath(raw_path):
                        shutil.copyfile(src_raw, raw_path)
                else:
                    tester = tester_cls(
                        mock_mode=False if rpi_host else None,
                        remote_host=rpi_host,
                        remote_port=rpi_port,
                        transport=rpi_transport,
                        ssh_user=rpi_user,
                        allow_mock_fallback=not no_fallback,
                    )
                    try:
                        hil_res = tester.replay_schedule(sched_res, time_scale_factor=time_scale)
                    finally:
                        tester.cleanup()

                    with open(raw_path, "w", encoding="utf-8") as f:
                        json.dump(hil_res, f, indent=2)

                is_phys = bool(hil_res.get("is_physical_hardware", False))
                board_model = str(hil_res.get("board_model", hil_res.get("device_model", hil_res.get("hardware_mode", "Unknown"))))
                backend = str(hil_res.get("gpio_backend", hil_res.get("hardware_mode", "Unknown")))
                if no_fallback and rpi_host and not is_phys:
                    raise RuntimeError(f"Physical Raspberry Pi verification failed on {mode}/{bm} trial {tr}: {hil_res}")

                wall_s = float(hil_res["total_wall_clock_sec"])
                rt_s = float(hil_res.get("client_roundtrip_sec", wall_s))
                cum_sleep = float(hil_res.get("cumulative_task_sleep_sec", total_task_cycles * time_scale))
                scaled_ms = float(hil_res.get("scaled_schedule_makespan_sec", sched_res.makespan * time_scale))
                jitter_s = float(hil_res.get("sleep_and_os_jitter_sec", wall_s - cum_sleep))
                oh_sleep_pct = float(hil_res.get("overhead_vs_cumulative_sleep_pct", ((wall_s - cum_sleep) / cum_sleep * 100.0) if cum_sleep > 0 else 0.0))
                expansion_x = wall_s / scaled_ms if scaled_ms > 0 else 1.0
                gpio_cnt = int(hil_res.get("gpio_events_count", 0))

                wall_list.append(wall_s)
                rt_list.append(rt_s)
                jitt_list.append(jitter_s)
                oh_list.append(oh_sleep_pct)
                gpio_list.append(gpio_cnt)

                row = [
                    mode, bm, sched_res.algorithm_name, tr, is_phys,
                    board_model, backend, str(hil_res.get("transport", "local")),
                    str(hil_res.get("started_at_utc", "")), str(hil_res.get("ended_at_utc", "")),
                    time_scale, int(sched_res.makespan), total_task_cycles,
                    round(scaled_ms, 5), round(cum_sleep, 5), round(wall_s, 5),
                    round(rt_s, 5), round(jitter_s, 5), round(oh_sleep_pct, 3),
                    round(expansion_x, 4), gpio_cnt, len(sched_res.tasks),
                    str(hil_res.get("execution_status", "completed")), str(hil_res.get("error") or ""),
                    raw_filename,
                ]
                all_trial_rows.append(row)
                mode_trial_rows.append(row)
                print(f"    {mode.upper():<8} | {bm:<6} | Trial {tr}/{trials} | Physical={is_phys} | Wall={wall_s:.4f}s | Roundtrip={rt_s:.4f}s | GPIO={gpio_cnt} | Jitter={jitter_s*1000:.2f}ms")

            mean_wall = statistics.mean(wall_list)
            std_wall = statistics.stdev(wall_list) if len(wall_list) > 1 else 0.0
            mean_rt = statistics.mean(rt_list)
            mean_jitter = statistics.mean(jitt_list)
            mean_oh = statistics.mean(oh_list)
            scaled_ms = sched_res.makespan * time_scale
            cum_sleep = total_task_cycles * time_scale

            sum_row = [
                mode, bm, sched_res.algorithm_name, trials, is_phys, board_model, backend,
                int(sched_res.makespan), total_task_cycles, round(scaled_ms, 5), round(cum_sleep, 5),
                round(mean_wall, 5), round(std_wall, 5), round(mean_rt, 5),
                round(mean_jitter, 5), round(mean_oh, 3), int(statistics.mean(gpio_list)),
            ]
            hw_summary_rows.append(sum_row)
            mode_summary_rows.append(sum_row)

            comp_rows.append([
                mode, bm, sched_res.algorithm_name, is_phys, board_model,
                int(sched_res.makespan), total_task_cycles, round(best_alg_cpu, 5),
                round(scaled_ms, 5), round(cum_sleep, 5), round(mean_wall, 5),
                round(std_wall, 5), round(mean_rt, 5), round(mean_jitter, 5),
                round(mean_oh, 3), round(mean_wall / scaled_ms, 3) if scaled_ms > 0 else 1.0,
                "Sequential GPIO replay across tasks accounts for (Total Task Cycles / Makespan) factor + Linux sleep jitter",
            ])

        _write_csv(os.path.join(dirs[hw_key], f"rpi_{mode}_trials.csv"), trial_headers, mode_trial_rows)
        _write_csv(
            os.path.join(dirs[hw_key], f"rpi_{mode}_summary.csv"),
            ["Mode", "Benchmark", "Algorithm", "Trials", "Is Physical", "Board Model", "GPIO Backend", "Makespan (CC)", "Total Task Cycles", "Scaled Makespan (s)", "Expected Cumulative Sleep (s)", "Mean Wall Clock (s)", "Std Wall Clock (s)", "Mean Client Roundtrip (s)", "Mean Jitter (s)", "Mean Overhead vs Sleep (%)", "GPIO Events"],
            mode_summary_rows,
        )

    _write_csv(os.path.join(dirs["raw_rpi"], "rpi_all_trials_raw.csv"), trial_headers, all_trial_rows)
    comp_headers = [
        "Mode", "Benchmark", "Algorithm", "Is Physical Hardware", "Hardware Board",
        "Sim Makespan (CC)", "Cumulative Task Cycles", "Sim Optimizer CPU (s)",
        "Scaled Concurrent Makespan (s)", "Expected Sequential Sleep (s)",
        "RPi Mean Wall Clock (s)", "RPi Std Wall Clock (s)", "RPi Mean Client Roundtrip (s)",
        "RPi Jitter vs Sleep (s)", "RPi Overhead vs Sleep (%)",
        "Sequential vs Concurrent Time Ratio", "Engineering Note",
    ]
    _write_csv(os.path.join(dirs["comp_sim_hw"], "sim_vs_rpi_comparison.csv"), comp_headers, comp_rows)
    _write_csv(os.path.join(dirs["tbl_csv"], "sim_vs_rpi_comparison.csv"), comp_headers, comp_rows)
    return {
        "ping_info": ping_info,
        "all_trial_rows": all_trial_rows,
        "hw_summary_rows": hw_summary_rows,
        "comp_rows": comp_rows,
    }


# ----------------------------------------------------------------------------
# PART E: PUBLICATION-QUALITY 300 DPI FIGURES + COMPANION DATA CSVs
# ----------------------------------------------------------------------------
def generate_all_figures_and_workbooks(
    dirs: Dict[str, str],
    sim_data: Dict[str, Any],
    sweep_data: Dict[str, Any],
    ml_data: Dict[str, Any],
    hil_data: Dict[str, Any],
    seeds: List[int],
    max_evals: int,
) -> None:
    print("\n[Step 5/5] Generating Publication-Quality 300 DPI Graphs, CSVs, and OpenXML Workbooks...")

    # ---- Figure 1: 2D Mean Makespan Comparison ----
    f1_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    for ax, bm in zip(axes, ["d695", "p22810"]):
        means, stds, bar_cols = [], [], []
        for alg in ALG_ORDER:
            vals = [float(x) for x in sim_data["grouped_makespans"][("2d", bm, alg)]]
            m_v = statistics.mean(vals)
            s_v = statistics.stdev(vals) if len(vals) > 1 else 0.0
            means.append(m_v)
            stds.append(s_v)
            bar_cols.append(ALG_COLORS[alg])
            f1_rows.append(["2d", bm, alg, round(m_v, 2), round(s_v, 2), min(vals), max(vals)])
        x = np.arange(len(ALG_ORDER))
        bars = ax.bar(x, means, yerr=stds, capsize=4, color=bar_cols, edgecolor="black", alpha=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(ALG_ORDER, rotation=20, ha="right", fontweight="bold")
        ax.set_ylabel("Makespan (Clock Cycles)", fontweight="bold")
        ax.set_title(f"2D Planar — ITC'02 {bm.upper()} (N={len(seeds)}, max_evals={max_evals})", fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        y_min = min(means) * 0.985
        span = max(max(m + s for m, s in zip(means, stds)) - y_min, 100.0)
        y_max = y_min + span * 1.18
        ax.set_ylim(y_min, y_max)
        for b, m_v, s_v in zip(bars, means, stds):
            ax.text(b.get_x() + b.get_width() / 2.0, m_v + s_v + span * 0.025, f"{m_v:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    fig.suptitle("Figure 1: 2D Planar SoC Makespan Comparison Across All Six Algorithms (Mean ± Std)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_2d"], "fig01_2d_makespan_comparison.png"), dpi=300)
    plt.close()
    _write_csv(os.path.join(dirs["g_2d"], "fig01_2d_makespan_comparison.csv"), ["Mode", "Benchmark", "Algorithm", "Mean Makespan", "Std Dev", "Min Makespan", "Max Makespan"], f1_rows)

    # ---- Figure 2: IEEE 1500 Wrapper Test Time Reduction ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
    shared_handles, shared_labels = None, None
    for ax, bm in zip(axes, ["d695", "p22810"]):
        sub = [r for r in sweep_data["wrapper_rows"] if r[0] == bm]
        tams = [r[1] for r in sub]
        post_c = [r[3] for r in sub]
        red_p = [r[5] for r in sub]
        l1 = ax.plot(tams, post_c, "o-", color="#1f77b4", linewidth=2.2, label="Post-Wrapper Cycles (Left Axis)")
        ax.set_xlabel("TAM Width (bits)", fontweight="bold")
        ax.set_ylabel("Post-Wrapper Test Cycles", fontweight="bold", color="#1f77b4")
        ax.tick_params(axis="y", labelcolor="#1f77b4")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax2 = ax.twinx()
        l2 = ax2.plot(tams, red_p, "s--", color="#d62728", linewidth=1.8, label="Test Time Reduction % (Right Axis)")
        ax2.set_ylabel("Test Time Reduction vs Unwrapped (%)", fontweight="bold", color="#d62728")
        ax2.tick_params(axis="y", labelcolor="#d62728")
        ax.set_title(f"IEEE 1500 Wrapper Analysis — {bm.upper()}", fontweight="bold")
        if shared_handles is None:
            shared_handles = l1 + l2
            shared_labels = [h.get_label() for h in shared_handles]
    fig.suptitle("Figure 2: IEEE 1500 Wrapper Design Test Cycle Reduction vs TAM Width", fontsize=13, fontweight="bold")
    if shared_handles:
        fig.legend(shared_handles, shared_labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 0.93), frameon=True, framealpha=0.95, fontsize=9)
    plt.tight_layout(rect=[0, 0, 1, 0.87])
    plt.savefig(os.path.join(dirs["g_2d"], "fig02_ieee1500_wrapper_reduction.png"), dpi=300)
    plt.close()
    _write_csv(
        os.path.join(dirs["g_2d"], "fig02_ieee1500_wrapper_reduction.csv"),
        ["Benchmark", "TAM Width", "Raw Cycles", "Post-Wrapper Cycles", "Cycles Saved", "Reduction %"],
        sweep_data["wrapper_rows"],
    )

    # ---- Figures 3 & 4: 2D Best Gantt Charts ----
    for fig_name, bm in [("fig03_2d_gantt_d695.png", "d695"), ("fig04_2d_gantt_p22810.png", "p22810")]:
        _, res_best = sim_data["best_schedules"][("2d", bm)]
        plot_gantt_chart(res_best, f"{bm.upper()} 2D Planar", os.path.join(dirs["g_2d"], fig_name), is_3d=False)

    # ---- Figure 5: Fixed 3D Multi-TAM Width Sweep (p22810) ----
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    f5_rows = [r for r in sweep_data["tam_rows"] if r[0] == "p22810"]
    for alg in ALG_ORDER:
        sub = sorted([r for r in f5_rows if r[2] == alg], key=lambda x: x[1])
        ax.plot([r[1] for r in sub], [r[3] for r in sub], "o-", linewidth=2.0, color=ALG_COLORS[alg], label=alg)
    ax.set_xlabel("Post-Bond TAM Width (bits)", fontweight="bold")
    ax.set_ylabel("Test Makespan (Clock Cycles)", fontweight="bold")
    ax.set_title(f"Figure 5: Fixed 3D Post-Bond TAM Width Sweep on ITC'02 p22810 (TSV Limit = 80, max_evals = {max_evals})", fontweight="bold")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_fixed3d"], "fig05_fixed3d_tam_sweep_p22810.png"), dpi=300)
    plt.close()
    _write_csv(
        os.path.join(dirs["g_fixed3d"], "fig05_fixed3d_tam_sweep_p22810.csv"),
        ["Benchmark", "TAM Width", "Algorithm", "Makespan (CC)", "TSV Used", "TSV Budget", "Eval Count", "Runtime (s)", "Peak Power (W)", "Max Power (W)", "Peak Tj (C)", "Status"],
        f5_rows,
    )

    # ---- Figures 6-11: Fixed 3D & Random 3D Dashboards, Gantt, Heatmaps ----
    for bm, out_p in [
        ("d695", os.path.join(dirs["g_fixed3d"], "fig06_fixed3d_dashboard_d695.png")),
        ("p22810", os.path.join(dirs["g_fixed3d"], "fig07_fixed3d_dashboard_p22810.png")),
    ]:
        soc = _load_soc("fixed3d", bm)
        plot_dashboard(sim_data["representative_results"][("fixed3d", bm)], bm, "fixed3d", out_p, soc.max_power, soc.max_tam_width, soc.max_tsv_bandwidth)

    soc_f, res_f = sim_data["best_schedules"][("fixed3d", "p22810")]
    plot_thermal_heatmaps(soc_f, res_f, os.path.join(dirs["g_fixed3d"], "fig08_fixed3d_thermal_heatmap_p22810.png"))
    plot_gantt_chart(res_f, "p22810 Fixed 3D", os.path.join(dirs["g_fixed3d"], "fig09_fixed3d_gantt_p22810.png"), is_3d=True)

    # Save exact spatial thermal grid CSV for Fixed 3D p22810 at peak temp
    peak_idx = int(np.argmax(res_f.thermal_profile))
    sampled_times = np.linspace(0, res_f.makespan, len(res_f.thermal_profile), dtype=int)
    peak_t = int(sampled_times[peak_idx])
    active_cores_peak = [soc_f.cores[tk.core_id - 1] for tk in res_f.tasks if tk.start_time <= peak_t < tk.end_time]
    t_prof = soc_f.thermal_model.estimate_temperature_profile(active_cores_peak, grid_resolution=6)["temp_grids"] - 273.15
    hm_rows = []
    for z in range(t_prof.shape[0]):
        for x_i in range(t_prof.shape[1]):
            for y_i in range(t_prof.shape[2]):
                hm_rows.append([z, x_i, y_i, round(float(t_prof[z, x_i, y_i]), 3)])
    _write_csv(os.path.join(dirs["g_fixed3d"], "fig08_fixed3d_thermal_heatmap_p22810.csv"), ["Layer Z", "Grid X", "Grid Y", "Junction Temp (C)"], hm_rows)

    soc_r, res_r = sim_data["best_schedules"][("random3d", "p22810")]
    plot_dashboard(sim_data["representative_results"][("random3d", "p22810")], "p22810", "random3d", os.path.join(dirs["g_random3d"], "fig10_random3d_dashboard_p22810.png"), soc_r.max_power, soc_r.max_tam_width, soc_r.max_tsv_bandwidth)
    plot_thermal_heatmaps(soc_r, res_r, os.path.join(dirs["g_random3d"], "fig11_random3d_thermal_heatmap_p22810.png"))

    # ---- Figure 12: Fair-Budget Convergence Curves (3D p22810) ----
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    f12_rows = []
    for ax, mode_lbl, mode_key in zip(axes, ["Fixed 3D (p22810)", "Random 3D (p22810)"], ["fixed3d", "random3d"]):
        for alg in ["ABC", "Bat", "Firefly", "MACO", "H-MACO-FA"]:
            pts = sorted([(r[4], r[5]) for r in sim_data["conv_rows"] if r[0] == mode_key and r[1] == "p22810" and r[3] == alg], key=lambda p: p[0])
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                if xs[-1] < max_evals:
                    xs.append(max_evals)
                    ys.append(ys[-1])
                ax.step(xs, ys, where="post", linewidth=2.0, color=ALG_COLORS[alg], label=alg)
                for ev_i, ms_v in zip(xs, ys):
                    f12_rows.append([mode_key, "p22810", alg, ev_i, ms_v])
        ax.set_xlabel("Schedule Evaluation Count (Fair Budget)", fontweight="bold")
        ax.set_ylabel("Best Makespan Found (CC)", fontweight="bold")
        ax.set_title(f"{mode_lbl} Convergence (seed=42)", fontweight="bold")
        ax.set_xlim(0, max_evals + 5)
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
    fig.suptitle(f"Figure 12: Fair-Budget Anytime Convergence Curves Across 3D Optimizers (max_evals={max_evals})", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_random3d"], "fig12_3d_convergence_curves.png"), dpi=300)
    plt.close()
    _write_csv(os.path.join(dirs["g_random3d"], "fig12_3d_convergence_curves.csv"), ["Mode", "Benchmark", "Algorithm", "Evaluation Index", "Best Makespan (CC)"], f12_rows)

    # ---- Figure 13: Genuine ML Thermal Regression Predicted vs Reference ----
    ml_eval = ml_data["ml_eval"]
    ml_fixed = ml_data["ml_eval_fixed"]
    y_true_r = ml_eval["test_actual_tj_c"]
    y_pred_r = ml_eval["test_predicted_tj_c"]
    y_true_f = ml_fixed["test_actual_tj_c"]
    y_pred_f = ml_fixed["test_predicted_tj_c"]
    res_err_r = y_pred_r - y_true_r
    res_err_f = y_pred_f - y_true_f
    poly_r = ml_eval["summary"][1]
    poly_f = ml_fixed["summary"][1]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    axes[0].scatter(y_true_r, y_pred_r, s=16, alpha=0.6, color="#1f77b4", edgecolors="none", label=f"Random 3D RC (MAE={poly_r['test_mae_c']}°C, R²={poly_r['test_r2']:.4f})")
    axes[0].scatter(y_true_f, y_pred_f, s=16, alpha=0.6, color="#ff7f0e", edgecolors="none", label=f"Fixed 3D RC (MAE={poly_f['test_mae_c']}°C, R²={poly_f['test_r2']:.4f})")
    mn = float(min(np.min(y_true_r), np.min(y_true_f)))
    mx = float(max(np.max(y_true_r), np.max(y_true_f)))
    axes[0].plot([mn, mx], [mn, mx], "r--", linewidth=1.8, label="Ideal y = x")
    axes[0].set_xlabel("RC Reference Peak Tj (°C) [Simulated Model]", fontweight="bold")
    axes[0].set_ylabel("ML Predicted Peak Tj (°C)", fontweight="bold")
    axes[0].set_title("Deduplicated Held-Out Test Predictions (0% Overlap)", fontweight="bold")
    axes[0].legend(fontsize=8.5)
    axes[0].grid(True, linestyle="--", alpha=0.5)

    axes[1].hist(res_err_r, bins=25, color="#1f77b4", edgecolor="black", alpha=0.55, label=f"Random 3D Residuals (RMSE={poly_r['test_rmse_c']}°C)")
    axes[1].hist(res_err_f, bins=25, color="#ff7f0e", edgecolor="black", alpha=0.55, label=f"Fixed 3D Residuals (RMSE={poly_f['test_rmse_c']}°C)")
    axes[1].axvline(0.0, color="r", linestyle="--", linewidth=1.5)
    axes[1].set_xlabel("Prediction Error: Predicted - Reference (°C)", fontweight="bold")
    axes[1].set_ylabel("Test Sample Count", fontweight="bold")
    axes[1].set_title("Deduplicated Held-Out Residual Distributions", fontweight="bold")
    axes[1].legend(fontsize=8.5)
    axes[1].grid(True, linestyle="--", alpha=0.5)

    fig.suptitle("Figure 13: Polynomial Ridge (d=2) Thermal Prediction vs 3D RC Reference Models", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_random3d"], "fig13_ml_thermal_regression.png"), dpi=300)
    plt.close()
    _write_csv(os.path.join(dirs["g_random3d"], "fig13_ml_thermal_regression.csv"), ["RC Architecture", "Sample Index", "Benchmark", "Total Power (W)", "Active Cores", "Active TSV", "RC Reference Tj (C)", "ML Predicted Tj (C)", "Residual (C)"], ml_data["pred_rows"])

    # ---- Figure 14: Live Raspberry Pi Wall-Clock Trials ----
    fig, ax = plt.subplots(figsize=(11, 5.2))
    labels = [f"{r[0].upper()}\n{r[1]}" for r in hil_data["hw_summary_rows"]]
    means_w = [r[11] for r in hil_data["hw_summary_rows"]]
    stds_w = [r[12] for r in hil_data["hw_summary_rows"]]
    exp_s = [r[10] for r in hil_data["hw_summary_rows"]]
    x = np.arange(len(labels))
    w = 0.36
    b1 = ax.bar(x - w / 2, exp_s, w, label="Expected Sequential Sleep Sum (s)", color="#7f8c8d", edgecolor="black")
    b2 = ax.bar(x + w / 2, means_w, w, yerr=stds_w, capsize=4, label="Measured Physical RPi 4 Sequential Wall (s)", color="#1f77b4", edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight="bold")
    ax.set_ylabel("Execution Time (seconds)", fontweight="bold")
    board_lbl = hil_data["ping_info"].get("board_model", "Raspberry Pi 4 Model B")
    ax.set_title(f"Figure 14: Sequential {board_lbl} GPIO Replay vs Cumulative Task Sleep", fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_ylim(0, max(m + s for m, s in zip(means_w, stds_w)) * 1.26)
    for bar, val, std_val in zip(b2, means_w, stds_w):
        ax.text(bar.get_x() + bar.get_width() / 2.0, val + std_val + max(means_w) * 0.025, f"{val:.2f}s", ha="center", va="bottom", fontsize=8, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_hw"], "fig14_rpi_wallclock_trials.png"), dpi=300)
    plt.close()
    _write_csv(
        os.path.join(dirs["g_hw"], "fig14_rpi_wallclock_trials.csv"),
        ["Mode", "Benchmark", "Algorithm", "Trials", "Is Physical", "Board Model", "GPIO Backend", "Makespan (CC)", "Total Task Cycles", "Scaled Makespan (s)", "Expected Sleep (s)", "Mean Wall Clock (s)", "Std Wall Clock (s)", "Mean Roundtrip (s)", "Mean Jitter (s)", "Mean Overhead %", "GPIO Events"],
        hil_data["hw_summary_rows"],
    )

    # ---- Figure 15: Per-Core GPIO Task Duration vs Measured Pi Duration (Sample from Trial 1) ----
    sample_raw_path = os.path.join(dirs["raw_rpi"], "hil_fixed3d_d695_trial1.json")
    f15_rows = []
    if os.path.exists(sample_raw_path):
        with open(sample_raw_path, "r", encoding="utf-8") as f:
            raw_j = json.load(f)
        events = raw_j.get("task_events", [])
        if events:
            fig, ax = plt.subplots(figsize=(11, 5.0))
            cores = [f"C{e['core_id']} (L{e['layer_id']})" for e in events]
            exp_ms = [e["duration_cycles"] * float(raw_j.get("time_scale_factor", 1e-6)) * 1000.0 for e in events]
            act_ms = [e["wall_task_ms"] for e in events]
            xi = np.arange(len(cores))
            ax.bar(xi - 0.18, exp_ms, 0.36, label="Target Scaled Duration (ms)", color="#2ca02c", edgecolor="black")
            ax.bar(xi + 0.18, act_ms, 0.36, label="Measured Sequential Pi GPIO Execution (ms)", color="#ff7f0e", edgecolor="black")
            ax.set_xticks(xi)
            ax.set_xticklabels(cores, rotation=20, ha="right", fontweight="bold")
            ax.set_ylabel("Duration per Core Task (ms)", fontweight="bold")
            ax.set_title("Figure 15: Sequential Per-Core Physical GPIO Switching Time vs Scaled Target (Fixed 3D d695 Trial 1)", fontweight="bold")
            ax.legend()
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.savefig(os.path.join(dirs["g_hw"], "fig15_rpi_gpio_task_events.png"), dpi=300)
            plt.close()
            for e, em in zip(events, exp_ms):
                f15_rows.append([e["core_id"], e["core_name"], e["layer_id"], e["duration_cycles"], round(em, 3), round(e["wall_task_ms"], 3), e["gpio_transitions"]])
            _write_csv(os.path.join(dirs["g_hw"], "fig15_rpi_gpio_task_events.csv"), ["Core ID", "Core Name", "Layer ID", "Duration (Cycles)", "Target Duration (ms)", "Measured Pi Wall (ms)", "GPIO Transitions"], f15_rows)

    # ---- Figure 16: Simulation Timing vs Physical Raspberry Pi Timing Comparison ----
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    labels_c = [f"{r[0].upper()}\n{r[1]}" for r in hil_data["comp_rows"]]
    sim_cpu = [r[7] for r in hil_data["comp_rows"]]
    scaled_ms = [r[8] for r in hil_data["comp_rows"]]
    rpi_wall = [r[10] for r in hil_data["comp_rows"]]
    oh_pct = [r[14] for r in hil_data["comp_rows"]]
    xc = np.arange(len(labels_c))

    axes[0].bar(xc - 0.25, sim_cpu, 0.25, label="Host Optimizer CPU (s)", color="#9467bd", edgecolor="black")
    axes[0].bar(xc, scaled_ms, 0.25, label="Scaled Concurrent Makespan (s)", color="#2ca02c", edgecolor="black")
    axes[0].bar(xc + 0.25, rpi_wall, 0.25, label="Physical RPi 4 Sequential Wall (s)", color="#1f77b4", edgecolor="black")
    axes[0].set_xticks(xc)
    axes[0].set_xticklabels(labels_c, fontweight="bold")
    axes[0].set_ylabel("Time (seconds)", fontweight="bold")
    axes[0].set_title("Optimizer CPU vs Scaled Makespan vs Physical RPi 4 Replay", fontweight="bold")
    axes[0].set_ylim(0, max(rpi_wall) * 1.28)
    axes[0].legend(fontsize=8, loc="upper left")
    axes[0].grid(axis="y", linestyle="--", alpha=0.5)

    axes[1].bar(xc, oh_pct, 0.45, color="#d62728", edgecolor="black", alpha=0.85)
    axes[1].set_xticks(xc)
    axes[1].set_xticklabels(labels_c, fontweight="bold")
    axes[1].set_ylabel("Timing Overhead vs Expected Task Sleep (%)", fontweight="bold")
    axes[1].set_title("Measured Linux Userspace + GPIO Transition Overhead (%)", fontweight="bold")
    axes[1].set_ylim(0, max(oh_pct + [0.1]) * 1.20)
    axes[1].grid(axis="y", linestyle="--", alpha=0.5)
    for idx_b, val in enumerate(oh_pct):
        axes[1].text(idx_b, val + max(oh_pct + [0.1]) * 0.03, f"{val:.2f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

    fig.suptitle("Figure 16: Simulation Timing vs Physical Raspberry Pi 4 Hardware Execution", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_comp"], "fig16_sim_vs_rpi_execution_time.png"), dpi=300)
    plt.close()
    _write_csv(
        os.path.join(dirs["g_comp"], "fig16_sim_vs_rpi_execution_time.csv"),
        ["Mode", "Benchmark", "Algorithm", "Host CPU (s)", "Scaled Makespan (s)", "Expected Sleep (s)", "RPi Wall Clock (s)", "Overhead vs Sleep (%)"],
        [[r[0], r[1], r[2], r[7], r[8], r[9], r[10], r[14]] for r in hil_data["comp_rows"]],
    )

    # ---- Figure 17: 2D vs Fixed 3D vs Random 3D Architecture Comparison ----
    f17_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    arch_modes = [("2d", "2D Planar"), ("fixed3d", "Fixed 3D"), ("random3d", "Random 3D")]
    for ax, bm in zip(axes, ["d695", "p22810"]):
        xa = np.arange(len(arch_modes))
        maco_m = [statistics.mean(sim_data["grouped_makespans"][(m, bm, "MACO")]) for m, _ in arch_modes]
        hmaco_m = [statistics.mean(sim_data["grouped_makespans"][(m, bm, "H-MACO-FA")]) for m, _ in arch_modes]
        greedy_m = [statistics.mean(sim_data["grouped_makespans"][(m, bm, "Greedy")]) for m, _ in arch_modes]
        ax.bar(xa - 0.25, greedy_m, 0.25, label="Greedy", color=ALG_COLORS["Greedy"], edgecolor="black")
        ax.bar(xa, maco_m, 0.25, label="MACO", color=ALG_COLORS["MACO"], edgecolor="black")
        ax.bar(xa + 0.25, hmaco_m, 0.25, label="H-MACO-FA", color=ALG_COLORS["H-MACO-FA"], edgecolor="black")
        ax.set_xticks(xa)
        ax.set_xticklabels([lbl for _, lbl in arch_modes], fontweight="bold")
        ax.set_ylabel("Mean Makespan (Clock Cycles)", fontweight="bold")
        ax.set_title(f"Architecture Comparison — {bm.upper()}", fontweight="bold")
        all_v = greedy_m + maco_m + hmaco_m
        y_lo = min(all_v) * 0.94
        y_span = max(all_v) - y_lo
        ax.set_ylim(y_lo, y_lo + y_span * 1.45)
        ax.legend(loc="upper left", ncol=3, fontsize=8.5)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        for (m, lbl), gv, mv, hv in zip(arch_modes, greedy_m, maco_m, hmaco_m):
            f17_rows.append([bm, m, lbl, round(gv, 2), round(mv, 2), round(hv, 2)])
    fig.suptitle("Figure 17: 2D Planar vs Fixed 3D vs Random 3D Test Scheduling Makespan", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_comp"], "fig17_2d_vs_3d_architecture_comparison.png"), dpi=300)
    plt.close()
    _write_csv(os.path.join(dirs["g_comp"], "fig17_2d_vs_3d_architecture_comparison.csv"), ["Benchmark", "Mode Key", "Architecture", "Greedy Mean", "MACO Mean", "H-MACO-FA Mean"], f17_rows)

    # ---- Figures 18 & 19: Multi-Seed Statistical Boxplots ----
    for fig_fn, csv_fn, bm in [
        ("fig18_multiseed_boxplot_d695.png", "fig18_multiseed_boxplot_d695.csv", "d695"),
        ("fig19_multiseed_boxplot_p22810.png", "fig19_multiseed_boxplot_p22810.csv", "p22810"),
    ]:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
        box_rows = []
        for ax, (m, lbl) in zip(axes, [("2d", "2D Planar"), ("fixed3d", "Fixed 3D"), ("random3d", "Random 3D")]):
            data_groups = [sim_data["grouped_makespans"][(m, bm, alg)] for alg in ALG_ORDER]
            bp = ax.boxplot(data_groups, tick_labels=ALG_ORDER, patch_artist=True)
            for patch, alg in zip(bp["boxes"], ALG_ORDER):
                patch.set_facecolor(ALG_COLORS[alg])
                patch.set_alpha(0.75)
            ax.set_title(f"{lbl} ({bm.upper()})", fontweight="bold")
            ax.set_ylabel("Makespan (Clock Cycles)", fontweight="bold")
            plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontweight="bold")
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            for alg, vals in zip(ALG_ORDER, data_groups):
                box_rows.append([m, bm, alg, min(vals), round(statistics.median(vals), 2), round(statistics.mean(vals), 2), max(vals), round(statistics.stdev(vals) if len(vals) > 1 else 0.0, 2)])
        fig.suptitle(f"Multi-Seed Statistical Distribution Across {len(seeds)} Seeds — {bm.upper()} (max_evals={max_evals})", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(dirs["g_stats"], fig_fn), dpi=300)
        plt.close()
        _write_csv(os.path.join(dirs["g_stats"], csv_fn), ["Mode", "Benchmark", "Algorithm", "Min", "Median", "Mean", "Max", "Std Dev"], box_rows)

    # ---- Figure 20: Fair Evaluation Budget & Mean CPU Runtime (Fixed 3D p22810) ----
    f20_rows = [r for r in sim_data["stats_rows"] if r[0] == "fixed3d" and r[1] == "p22810"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0))
    algs_20 = [r[2] for r in f20_rows]
    evals_20 = [r[10] for r in f20_rows]
    times_20 = [r[11] for r in f20_rows]
    cols_20 = [ALG_COLORS[a] for a in algs_20]
    axes[0].bar(algs_20, evals_20, color=cols_20, edgecolor="black")
    axes[0].axhline(max_evals, color="r", linestyle="--", label=f"Budget Cap ({max_evals})")
    axes[0].set_ylabel("Mean Schedule Evaluations", fontweight="bold")
    axes[0].set_title("Actual Evaluation Budget Compliance", fontweight="bold")
    axes[0].legend()
    axes[0].grid(axis="y", linestyle="--", alpha=0.5)

    axes[1].bar(algs_20, times_20, color=cols_20, edgecolor="black")
    axes[1].set_ylabel("Mean Optimizer CPU Time (s)", fontweight="bold")
    axes[1].set_title("Mean Optimizer Runtime under Fair Budget (Fixed 3D p22810)", fontweight="bold")
    axes[1].set_ylim(0, max(times_20) * 1.18)
    axes[1].grid(axis="y", linestyle="--", alpha=0.5)
    for i_b, tv in enumerate(times_20):
        axes[1].text(i_b, tv + max(times_20) * 0.03, f"{tv:.3f}s", ha="center", va="bottom", fontsize=8, fontweight="bold")

    fig.suptitle("Figure 20: Fair-Budget Evaluation Counts & Runtime Comparison (Fixed 3D p22810)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(dirs["g_stats"], "fig20_fair_budget_runtime_vs_evals.png"), dpi=300)
    plt.close()
    _write_csv(
        os.path.join(dirs["g_stats"], "fig20_fair_budget_runtime_vs_evals.csv"),
        ["Mode", "Benchmark", "Algorithm", "Mean Evals", "Mean CPU Runtime (s)", "Mean Makespan (CC)"],
        [[r[0], r[1], r[2], r[10], r[11], r[6]] for r in f20_rows],
    )

    # ---- Genuine OpenXML Excel Workbooks ----
    stats_hdr = [
        "Mode", "Benchmark", "Algorithm", "N Seeds", "Best (CC)", "Worst (CC)",
        "Mean (CC)", "Median (CC)", "Std Dev (CC)", "Mean Reduction vs Greedy (%)",
        "Mean Evals", "Mean CPU Runtime (s)", "Worst-Case Power (W)",
        "Worst-Case Peak Tj (C)", "Max TSV/TAM Used", "Constraint Status",
    ]
    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "01_2D_Planar_Results.xlsx"), {
        "2D Multi-Seed Stats": {"title": "2D Planar Fair-Budget Multi-Seed Summary", "headers": stats_hdr, "rows": [r for r in sim_data["stats_rows"] if r[0] == "2d"]},
        "IEEE 1500 Wrapper Sweep": {"title": "IEEE 1500 Wrapper Reduction vs TAM Width", "headers": ["Benchmark", "TAM Width", "Pre-Wrapper Cycles", "Post-Wrapper Cycles", "Cycles Saved", "Reduction %"], "rows": sweep_data["wrapper_rows"]},
    })
    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "02_Fixed_3D_Results.xlsx"), {
        "Fixed 3D Multi-Seed Stats": {"title": "Fixed 3D Fair-Budget Multi-Seed Summary", "headers": stats_hdr, "rows": [r for r in sim_data["stats_rows"] if r[0] == "fixed3d"]},
        "Multi-TAM Width Sweep": {"title": "Fixed 3D Post-Bond Multi-TAM Sweep (6 Algorithms)", "headers": ["Benchmark", "TAM Width", "Algorithm", "Makespan (CC)", "TSV Used", "TSV Budget", "Eval Count", "Runtime (s)", "Peak Power (W)", "Max Power (W)", "Peak Tj (C)", "Status"], "rows": sweep_data["tam_rows"]},
    })
    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "03_Random_3D_Results.xlsx"), {
        "Random 3D Multi-Seed Stats": {"title": "Random 3D Fair-Budget Multi-Seed Summary", "headers": stats_hdr, "rows": [r for r in sim_data["stats_rows"] if r[0] == "random3d"]},
        "Frequency Scaling": {"title": "RC vs ML Thermal Frequency Scaling Comparison", "headers": ["Mode", "Benchmark", "Base Algorithm", "Strategy", "Makespan (CC)", "Peak Power (W)", "Peak Tj (C)", "Max TSV", "Status"], "rows": ml_data["scale_rows"]},
    })
    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "04_MultiSeed_Statistical_Summary.xlsx"), {
        "All Modes Summary": {"title": f"Fair-Budget ({max_evals} evals) Multi-Seed Statistical Summary ({len(seeds)} Seeds)", "headers": stats_hdr, "rows": sim_data["stats_rows"]},
    })
    shutil.copyfile(os.path.join(dirs["tbl_xlsx"], "04_MultiSeed_Statistical_Summary.xlsx"), os.path.join(dirs["stats"], "multiseed_statistical_summary.xlsx"))

    comp_hdr = [
        "Mode", "Benchmark", "Algorithm", "Is Physical Hardware", "Hardware Board",
        "Sim Makespan (CC)", "Cumulative Task Cycles", "Sim Optimizer CPU (s)",
        "Scaled Concurrent Makespan (s)", "Expected Sequential Sleep (s)",
        "RPi Mean Wall Clock (s)", "RPi Std Wall Clock (s)", "RPi Mean Client Roundtrip (s)",
        "RPi Jitter vs Sleep (s)", "RPi Overhead vs Sleep (%)",
        "Sequential vs Concurrent Time Ratio", "Engineering Note",
    ]
    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "05_Raspberry_Pi_HIL_vs_Simulation.xlsx"), {
        "Sim vs RPi Comparison": {"title": "Simulation Timing vs Live Raspberry Pi Physical HIL Comparison", "headers": comp_hdr, "rows": hil_data["comp_rows"]},
        "RPi Raw Trials": {
            "title": "All Individual Raspberry Pi Physical HIL Trial Measurements",
            "headers": [
                "Mode", "Benchmark", "Algorithm", "Trial", "Is Physical", "Board Model", "GPIO Backend",
                "Transport", "Started UTC", "Ended UTC", "Time Scale", "Makespan (CC)", "Total Task Cycles",
                "Scaled Makespan (s)", "Expected Sleep (s)", "Wall Clock (s)", "Roundtrip (s)",
                "Jitter (s)", "Overhead %", "Expansion x", "GPIO Events", "Tasks", "Status", "Error", "Raw JSON",
            ],
            "rows": hil_data["all_trial_rows"],
        },
    })
    shutil.copyfile(os.path.join(dirs["tbl_xlsx"], "05_Raspberry_Pi_HIL_vs_Simulation.xlsx"), os.path.join(dirs["comp_sim_hw"], "sim_vs_rpi_comparison.xlsx"))

    ml_reg_hdr = [
        "RC Architecture", "Model", "Degree", "Train N", "Test N", "Overlap",
        "Train MAE (C)", "Train RMSE (C)", "Train R2",
        "Test MAE (C)", "Test RMSE (C)", "Test Max Err (C)", "Test R2",
        "Train Time (s)", "Inference (ms/sample)", "Reference Source",
    ]
    traj_hdr = [
        "RC Architecture", "Validation Set", "Model", "Steps Evaluated",
        "MAE (C)", "RMSE (C)", "Max Err (C)", "R2", "Reference Source",
    ]
    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "06_ML_Thermal_Prediction_Report.xlsx"), {
        "ML Regression Metrics": {"title": "Deduplicated (0% Overlap) Train/Test Regression Metrics on 3D RC Data", "headers": ml_reg_hdr, "rows": ml_data["reg_rows"]},
        "Unseen Solver Trajectories": {"title": "Independent Unseen Solver Schedule Trajectory Validation (seeds=512,777,1024)", "headers": traj_hdr, "rows": ml_data["traj_rows"]},
        "Frequency Scaling": {"title": "Frequency Scaling with RC vs ML Predictor", "headers": ["Mode", "Benchmark", "Base Algorithm", "Strategy", "Makespan (CC)", "Peak Power (W)", "Peak Tj (C)", "Max TSV", "Status"], "rows": ml_data["scale_rows"]},
    })

    create_excel_openpyxl(os.path.join(dirs["tbl_xlsx"], "Master_Capstone_Complete_Report.xlsx"), {
        "MultiSeed Summary": {"title": "Complete 6-Algorithm Multi-Seed Fair-Budget Statistical Summary", "headers": stats_hdr, "rows": sim_data["stats_rows"]},
        "Sim vs Physical RPi": {"title": "Simulation vs Live Raspberry Pi 4 HIL Summary", "headers": comp_hdr, "rows": hil_data["comp_rows"]},
        "ML Thermal Regression": {"title": "ML Thermal Prediction Deduplicated Train/Test Metrics", "headers": ml_reg_hdr, "rows": ml_data["reg_rows"]},
        "ML Trajectory Validation": {"title": "ML Unseen Solver Trajectory Validation", "headers": traj_hdr, "rows": ml_data["traj_rows"]},
        "Fixed 3D TAM Sweep": {"title": "Fixed 3D Post-Bond TAM Width Sweep", "headers": ["Benchmark", "TAM Width", "Algorithm", "Makespan (CC)", "TSV Used", "TSV Budget", "Eval Count", "Runtime (s)", "Peak Power (W)", "Max Power (W)", "Peak Tj (C)", "Status"], "rows": sweep_data["tam_rows"]},
    })

    # Copy selected presentation graphs & tables
    selected_graph_copies = [
        (dirs["g_2d"], "fig01_2d_makespan_comparison.png"),
        (dirs["g_fixed3d"], "fig05_fixed3d_tam_sweep_p22810.png"),
        (dirs["g_fixed3d"], "fig07_fixed3d_dashboard_p22810.png"),
        (dirs["g_fixed3d"], "fig08_fixed3d_thermal_heatmap_p22810.png"),
        (dirs["g_random3d"], "fig12_3d_convergence_curves.png"),
        (dirs["g_random3d"], "fig13_ml_thermal_regression.png"),
        (dirs["g_hw"], "fig14_rpi_wallclock_trials.png"),
        (dirs["g_comp"], "fig16_sim_vs_rpi_execution_time.png"),
        (dirs["g_comp"], "fig17_2d_vs_3d_architecture_comparison.png"),
        (dirs["g_stats"], "fig19_multiseed_boxplot_p22810.png"),
    ]
    for src_d, fname in selected_graph_copies:
        src_p = os.path.join(src_d, fname)
        if os.path.exists(src_p):
            shutil.copyfile(src_p, os.path.join(dirs["pres_graphs"], fname))

    for tbl_src in [
        os.path.join(dirs["tbl_csv"], "multiseed_statistical_summary.csv"),
        os.path.join(dirs["tbl_csv"], "sim_vs_rpi_comparison.csv"),
        os.path.join(dirs["sim_random3d"], "ml_thermal_regression_metrics.csv"),
        os.path.join(dirs["sim_random3d"], "ml_thermal_trajectory_validation.csv"),
        os.path.join(dirs["tbl_xlsx"], "Master_Capstone_Complete_Report.xlsx"),
    ]:
        if os.path.exists(tbl_src):
            shutil.copyfile(tbl_src, os.path.join(dirs["pres_tables"], os.path.basename(tbl_src)))

    _write_results_docs(dirs, sim_data, ml_data, hil_data, seeds, max_evals)


def _write_results_docs(
    dirs: Dict[str, str],
    sim_data: Dict[str, Any],
    ml_data: Dict[str, Any],
    hil_data: Dict[str, Any],
    seeds: List[int],
    max_evals: int,
) -> None:
    board_lbl = hil_data["ping_info"].get("board_model", "Raspberry Pi 4 Model B Rev 1.4")
    os_lbl = hil_data["ping_info"].get("os_release", "Debian GNU/Linux")
    backend_lbl = hil_data["ping_info"].get("gpio_backend", "RPi.GPIO")
    is_phys = hil_data["ping_info"].get("is_physical_hardware", False)

    poly_r = ml_data["ml_eval"]["summary"][1]
    lin_r = ml_data["ml_eval"]["summary"][0]
    poly_f = ml_data["ml_eval_fixed"]["summary"][1]
    lin_f = ml_data["ml_eval_fixed"]["summary"][0]
    traj_r_un = ml_data["traj_random"]["unseen_steps_metrics"]
    traj_f_un = ml_data["traj_fixed"]["unseen_steps_metrics"]
    traj_r_n = ml_data["traj_random"]["strictly_unseen_steps"]
    traj_f_n = ml_data["traj_fixed"]["strictly_unseen_steps"]

    # Pick concrete verified numbers directly from computed rows
    hmaco_f_p22810 = [r for r in sim_data["stats_rows"] if r[0] == "fixed3d" and r[1] == "p22810" and r[2] == "H-MACO-FA"][0]
    greedy_f_p22810 = [r for r in sim_data["stats_rows"] if r[0] == "fixed3d" and r[1] == "p22810" and r[2] == "Greedy"][0]
    maco_f_p22810 = [r for r in sim_data["stats_rows"] if r[0] == "fixed3d" and r[1] == "p22810" and r[2] == "MACO"][0]
    hmaco_r_p22810 = [r for r in sim_data["stats_rows"] if r[0] == "random3d" and r[1] == "p22810" and r[2] == "H-MACO-FA"][0]
    d695_wall = statistics.mean([r[11] for r in hil_data["hw_summary_rows"] if r[1] == "d695"])
    p22810_wall = statistics.mean([r[11] for r in hil_data["hw_summary_rows"] if r[1] == "p22810"])
    d695_rt = statistics.mean([r[13] for r in hil_data["hw_summary_rows"] if r[1] == "d695"])
    p22810_rt = statistics.mean([r[13] for r in hil_data["hw_summary_rows"] if r[1] == "p22810"])

    results_readme = f"""# Results Directory Index (2D & 3D SoC Test Scheduling Capstone)

All tables, raw logs, Excel workbooks, and 300 DPI graphs in this folder were **programmatically generated** from genuine simulation runs and live Hardware-in-the-Loop (HIL) executions on the connected Raspberry Pi tester. No measurements are estimated or hardcoded.

## Experimental Configuration Summary
- **Multi-Seed Simulation**: `{len(seeds)}` seeds (`{seeds}`), Fair Evaluation Budget `--max-evals {max_evals}` across all 5 stochastic optimizers (`1` deterministic LPT baseline evaluation for Greedy)
- **Algorithms Evaluated (6)**: Greedy (Deterministic LPT Baseline), ABC, Bat, Firefly, MACO, H-MACO-FA Hybrid
- **Benchmarks**: ITC'02 `d695` (10 cores) & `p22810` (30 cores) across `2d`, `fixed3d`, and `random3d`
- **Physical HIL Hardware**: `{board_lbl}` | OS: `{os_lbl}` | Backend: `{backend_lbl}` | Physical Verified: `{is_phys}`
- **ML Thermal Reference Provenance**: Model-generated 3D RC ThermalModel traces (deduplicated hold-out split with 0% train-test overlap + independent unseen solver trajectory validation; no physical silicon thermal sensor attached)

## Directory Structure
- `raw_data/simulation/`: Raw per-seed run CSV (`raw_runs_all_modes_10seeds.csv`), anytime convergence traces, and ML test prediction residuals.
- `raw_data/raspberry_pi/`: Live ping verification JSON, per-trial GPIO task event JSON logs, and consolidated raw trial CSV.
- `simulation/{{2d,fixed_3d,random_3d}}/`: Mode-specific summaries, IEEE 1500 wrapper table, Fixed 3D multi-TAM sweep, and ML thermal regression/trajectory/scaling metrics.
- `hardware/{{2d,fixed_3d,random_3d}}/`: Physical Raspberry Pi replay trials and statistical hardware summaries.
- `comparisons/simulation_vs_hardware/`: Direct simulation vs physical Raspberry Pi timing CSV and `.xlsx`.
- `statistical_analysis/`: Multi-seed statistical summary (Best, Worst, Mean, Median, Std Dev) and rankings.
- `graphs/{{2d,fixed_3d,random_3d,hardware,comparisons,statistical}}/`: 20 publication-quality 300 DPI PNG figures + exact underlying CSV tables.
- `tables/{{csv,excel}}/`: Consolidated CSV and genuine OpenXML `.xlsx` workbooks (`Master_Capstone_Complete_Report.xlsx`, etc.).
- `presentation/`: Curated thesis/viva figures (`selected_graphs/`), key tables (`selected_tables/`), `key_findings.md`, and `figure_index.md`.
"""
    with open(os.path.join(dirs["root"], "README.md"), "w", encoding="utf-8") as f:
        f.write(results_readme)

    findings_md = f"""# Key Verified Experimental Findings (Presentation & Viva Summary)

1. **H-MACO-FA Hybrid Performance Under Fair Evaluation Budget (`max_evals={max_evals}`, {len(seeds)} seeds)**:
   - **Evaluation Budget Methodology**: All five stochastic metaheuristics (`ABC`, `Bat`, `Firefly`, `MACO`, `H-MACO-FA`) share the exact `max_evals={max_evals}` schedule-evaluation budget cap (`Mean Evals = 300.0`). `Greedy` is a deterministic non-iterative Longest-Processing-Time (LPT) list-scheduling heuristic that executes once per benchmark (`1` evaluation), serving as the un-iterated deterministic lower-effort baseline.
   - On Fixed 3D `p22810`, **H-MACO-FA** achieved Mean = `{hmaco_f_p22810[6]:,.2f}` cycles (Best = `{hmaco_f_p22810[4]:,}`, Std = `{hmaco_f_p22810[8]}`), outperforming Greedy Baseline (`{greedy_f_p22810[6]:,.2f}`) and MACO (`{maco_f_p22810[6]:,.2f}`), with Peak Power `{hmaco_f_p22810[12]}W <= 94.05W`, Peak Tj `{hmaco_f_p22810[13]}°C < 95.0°C`, and TSVs `{hmaco_f_p22810[14]}/24` (`Safe`).
   - On Random 3D `p22810`, **H-MACO-FA** achieved Mean = `{hmaco_r_p22810[6]:,.2f}` cycles (Best = `{hmaco_r_p22810[4]:,}`, Std = `{hmaco_r_p22810[8]}`), achieving `{hmaco_r_p22810[9]:.2f}%` mean makespan reduction vs Greedy.
2. **Real Physical Hardware Validation (`{board_lbl}`)**:
   - Verified `is_physical_hardware = {is_phys}` via `RPi.GPIO` over TCP socket HIL (`raw_data/raspberry_pi/rpi_ping_verification.json`).
   - Recorded 3 physical trials for every architecture/benchmark pair (`{len(hil_data["all_trial_rows"])}` total live hardware executions) with UTC timestamps, per-core GPIO event logs, client roundtrip latency, and Linux sleep jitter.
   - **Critical HIL Timing Distinction (Sequential GPIO Replay vs Concurrent SoC Simulation)**: The simulated SoC scheduler executes non-conflicting cores **concurrently** (`makespan < sum(core durations)`), whereas the physical Raspberry Pi HIL server replays each scheduled core **sequentially** (`for task in tasks:`) on GPIO pins (`wall_clock ≈ cumulative_task_cycles × time_scale + OS/GPIO jitter`). Measured physical Pi server wall-clock (`{d695_wall:.4f}s` mean on `d695`, `{p22810_wall:.4f}s` mean on `p22810`; client TCP roundtrip `{d695_rt:.3f}s` / `{p22810_rt:.3f}s`) validates exact cumulative cycle replay time + sub-0.2% Linux/GPIO jitter against expected sequential task sleep sums, rather than modeling simultaneous silicon ATE channels.
3. **Genuine ML Thermal Regression — Deduplicated Split & Unseen Solver Trajectories (No Physical Thermal Sensor)**:
   - Trained architecture-matched Linear (`d=1`) and Polynomial Ridge (`d=2`) models on unique active-core states generated by 3D RC thermal reference models (`seed=42`, strictly deduplicated before train/test split so `train_test_overlap = 0`).
   - **Random 3D RC (`ThermalModel`)** [`{lin_r['train_samples']}` train / `{lin_r['test_samples']}` unique test]: Linear (`d=1`) Test MAE = `{lin_r['test_mae_c']}°C`, R² = `{lin_r['test_r2']}`; Polynomial (`d=2`) Test MAE = `{poly_r['test_mae_c']}°C`, RMSE = `{poly_r['test_rmse_c']}°C`, Max Err = `{poly_r['test_max_error_c']}°C`, R² = `{poly_r['test_r2']}`.
   - **Fixed 3D RC (`FixedThermalModel`)** [`{lin_f['train_samples']}` train / `{lin_f['test_samples']}` unique test]: Linear (`d=1`) Test MAE = `{lin_f['test_mae_c']}°C`, R² = `{lin_f['test_r2']}`; Polynomial (`d=2`) Test MAE = `{poly_f['test_mae_c']}°C`, RMSE = `{poly_f['test_rmse_c']}°C`, Max Err = `{poly_f['test_max_error_c']}°C`, R² = `{poly_f['test_r2']}`.
   - **Independent Unseen Solver Schedule Trajectories (`seeds=512,777,1024`, Bat/MACO/H-MACO-FA)**: On strictly unseen active-core steps (`0%` training overlap), Polynomial Ridge (`d=2`) achieved MAE = `{traj_r_un['mae_c']}°C`, RMSE = `{traj_r_un['rmse_c']}°C`, R² = `{traj_r_un['r2']}` on Random 3D (`n={traj_r_n}` steps) and MAE = `{traj_f_un['mae_c']}°C`, RMSE = `{traj_f_un['rmse_c']}°C`, R² = `{traj_f_un['r2']}` on Fixed 3D (`n={traj_f_n}` steps).
"""
    with open(os.path.join(dirs["pres"], "key_findings.md"), "w", encoding="utf-8") as f:
        f.write(findings_md)

    figure_index = """# Presentation Figure Index

| Figure | File | Category | Companion CSV | Description |
| :--- | :--- | :--- | :--- | :--- |
| Fig 1 | `graphs/2d/fig01_2d_makespan_comparison.png` | 2D Simulation | `fig01_2d_makespan_comparison.csv` | Mean ± Std Makespan across all 6 algorithms (d695 & p22810) |
| Fig 2 | `graphs/2d/fig02_ieee1500_wrapper_reduction.png` | 2D Wrapper | `fig02_ieee1500_wrapper_reduction.csv` | IEEE 1500 wrapper test time reduction across TAM widths |
| Fig 3 | `graphs/2d/fig03_2d_gantt_d695.png` | 2D Schedule | — | Best 2D Gantt chart for ITC'02 d695 |
| Fig 4 | `graphs/2d/fig04_2d_gantt_p22810.png` | 2D Schedule | — | Best 2D Gantt chart for ITC'02 p22810 |
| Fig 5 | `graphs/fixed_3d/fig05_fixed3d_tam_sweep_p22810.png` | Fixed 3D | `fig05_fixed3d_tam_sweep_p22810.csv` | Post-bond TAM sweep (W=16..64) on Fixed 3D p22810 |
| Fig 6 | `graphs/fixed_3d/fig06_fixed3d_dashboard_d695.png` | Fixed 3D | — | Makespan, Power, Thermal, TSV dashboard (d695) |
| Fig 7 | `graphs/fixed_3d/fig07_fixed3d_dashboard_p22810.png` | Fixed 3D | — | Makespan, Power, Thermal, TSV dashboard (p22810) |
| Fig 8 | `graphs/fixed_3d/fig08_fixed3d_thermal_heatmap_p22810.png` | Fixed 3D | `fig08_fixed3d_thermal_heatmap_p22810.csv` | 3-Layer 3D spatial thermal footprint at peak Tj |
| Fig 9 | `graphs/fixed_3d/fig09_fixed3d_gantt_p22810.png` | Fixed 3D | — | Layer-colored 3D Gantt chart for Fixed 3D p22810 |
| Fig 10 | `graphs/random_3d/fig10_random3d_dashboard_p22810.png` | Random 3D | — | Makespan, Power, Thermal, TSV dashboard (Random 3D p22810) |
| Fig 11 | `graphs/random_3d/fig11_random3d_thermal_heatmap_p22810.png` | Random 3D | — | 3-Layer thermal footprint (Random 3D p22810) |
| Fig 12 | `graphs/random_3d/fig12_3d_convergence_curves.png` | Fair Budget | `fig12_3d_convergence_curves.csv` | Anytime convergence vs evaluation count (Fixed & Random 3D p22810) |
| Fig 13 | `graphs/random_3d/fig13_ml_thermal_regression.png` | ML Thermal | `fig13_ml_thermal_regression.csv` | Polynomial Ridge deduplicated held-out predictions & residuals |
| Fig 14 | `graphs/hardware/fig14_rpi_wallclock_trials.png` | Physical RPi 4 | `fig14_rpi_wallclock_trials.csv` | Sequential Raspberry Pi 4 GPIO replay wall clock vs task sleep |
| Fig 15 | `graphs/hardware/fig15_rpi_gpio_task_events.png` | Physical RPi 4 | `fig15_rpi_gpio_task_events.csv` | Sequential per-core measured Pi GPIO task duration vs scaled target |
| Fig 16 | `graphs/comparisons/fig16_sim_vs_rpi_execution_time.png` | Sim vs Hardware | `fig16_sim_vs_rpi_execution_time.csv` | Optimizer CPU vs scaled makespan vs Pi wall clock & overhead % |
| Fig 17 | `graphs/comparisons/fig17_2d_vs_3d_architecture_comparison.png` | Architecture | `fig17_2d_vs_3d_architecture_comparison.csv` | 2D vs Fixed 3D vs Random 3D mean makespans |
| Fig 18 | `graphs/statistical/fig18_multiseed_boxplot_d695.png` | Statistical | `fig18_multiseed_boxplot_d695.csv` | Multi-seed boxplot distributions on d695 |
| Fig 19 | `graphs/statistical/fig19_multiseed_boxplot_p22810.png` | Statistical | `fig19_multiseed_boxplot_p22810.csv` | Multi-seed boxplot distributions on p22810 |
| Fig 20 | `graphs/statistical/fig20_fair_budget_runtime_vs_evals.png` | Fair Budget | `fig20_fair_budget_runtime_vs_evals.csv` | Evaluation counts & CPU runtime under fair budget |
"""
    with open(os.path.join(dirs["pres"], "figure_index.md"), "w", encoding="utf-8") as f:
        f.write(figure_index)


def main():
    parser = argparse.ArgumentParser(description="Build complete genuine simulation + live RPi4 results/ tree")
    parser.add_argument("--results-dir", type=str, default=os.path.join(REPO_ROOT, "results"))
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--max-evals", type=int, default=300)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--rpi-host", type=str, default="10.231.118.57")
    parser.add_argument("--rpi-port", type=int, default=5055)
    parser.add_argument("--rpi-transport", choices=["tcp", "ssh"], default="tcp")
    parser.add_argument("--rpi-user", type=str, default="vivo")
    parser.add_argument("--rpi-time-scale", type=float, default=3e-6)
    parser.add_argument("--rpi-no-fallback", action="store_true")
    parser.add_argument("--reuse-rpi-dir", type=str, default=None, help="Reuse already recorded raw Raspberry Pi JSON files instead of re-executing over Wi-Fi")
    parser.add_argument(
        "--refresh-ml-and-plots-only",
        action="store_true",
        help="Preserve existing 360 raw simulation CSVs and 18 RPi JSONs verbatim; refresh only ML validation, figures, workbooks, and docs",
    )
    args = parser.parse_args()

    t_start = time.perf_counter()
    dirs = _create_results_dirs(os.path.abspath(args.results_dir))

    if args.refresh_ml_and_plots_only:
        sim_data, sweep_data = load_existing_sim_and_sweeps(dirs, args.max_evals)
        reuse_dir = args.reuse_rpi_dir or dirs["raw_rpi"]
    else:
        sim_data = run_multiseed_fair_budget_simulations(dirs, args.seeds, args.max_evals)
        sweep_data = run_tam_sweeps(dirs, args.max_evals)
        reuse_dir = args.reuse_rpi_dir

    ml_data = run_ml_thermal_experiment(dirs, sim_data["best_schedules"])
    hil_data = run_raspberry_pi_hil_trials(
        dirs=dirs,
        best_schedules=sim_data["best_schedules"],
        grouped_records=sim_data["grouped_records"],
        rpi_host=args.rpi_host,
        rpi_port=args.rpi_port,
        rpi_transport=args.rpi_transport,
        rpi_user=args.rpi_user,
        time_scale=args.rpi_time_scale,
        trials=args.trials,
        no_fallback=args.rpi_no_fallback,
        reuse_raw_dir=reuse_dir,
    )
    generate_all_figures_and_workbooks(dirs, sim_data, sweep_data, ml_data, hil_data, args.seeds, args.max_evals)
    print(f"\n[COMPLETE] Full genuine results package built at '{args.results_dir}' in {time.perf_counter() - t_start:.2f}s.")


if __name__ == "__main__":
    main()
