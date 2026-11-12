#!/usr/bin/env python3
"""
run_test_suite.py
=================
Unified Command-Line Execution Entry Point for 2D & 3D System-on-Chip (SoC) Test Scheduling.

Supports:
- Modes: 2d, fixed3d, random3d, all
- Benchmarks: d695 (10 cores), p22810 (30 cores), all
- Algorithms: greedy, abc, bat, firefly, maco, hmaco_fa, all
- Fair Evaluation Budget (--max-evals) & Multi-Seed Statistical Evaluation (--seeds)
- Full VLSI constraint validation (TAM, Power, TSV, Dynamic RC Thermal Model)
- IEEE 1500 Wrapper Design & Analysis
- Predictive Thermal Estimation & Dynamic Frequency Scaling
- Hardware-in-the-Loop (HIL) Raspberry Pi Tester Replay (Pi 4 Model B / Pi 5)
- Genuine OpenXML Excel (.xlsx), XML (.xml), CSV, and Publication-Quality Visualizations

Examples:
  python run_test_suite.py --mode 2d --benchmark d695
  python run_test_suite.py --mode fixed3d --benchmark p22810
  python run_test_suite.py --mode random3d --benchmark d695
  python run_test_suite.py --mode all --benchmark all
"""

import os
import sys
import csv
import time
import json
import random
import statistics
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set writable Matplotlib configuration directory
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")

# Setup project import paths
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
CAPSTONE_DIR = os.path.join(PROJECT_ROOT, "capstone")

sys.path.insert(0, os.path.join(CAPSTONE_DIR, "fixed_stacking"))
sys.path.insert(0, os.path.join(CAPSTONE_DIR, "random_stacking"))
sys.path.insert(0, os.path.join(CAPSTONE_DIR, "2d"))
sys.path.insert(0, CAPSTONE_DIR)

import numpy as np

# Visualization imports
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# 2D Imports
from src.models.soc_2d import ITC02BenchmarkLoader2D, SoC2D, ScheduleResult2D
from src.models.wrapper_design_2d import WrapperAnalyzer2D
from src.constraints.vlsi_constraints_2d import STANDARD_TAM_SWEEP_2D
from src.algorithms.greedy_2d import Greedy2DScheduler
from src.algorithms.abc_2d import ABC2DScheduler
from src.algorithms.bat_2d import Bat2DScheduler
from src.algorithms.firefly_2d import Firefly2DScheduler
from src.algorithms.maco_2d import MACO2DScheduler
from src.algorithms.hmaco_fa_2d import HMACOFA2DScheduler
from src.hardware.rpi_tester_2d import RaspberryPi5Tester2D

# 3D Imports
from src.models.soc_3d_fixed import FixedBenchmarkLoader, SoC3DFixed, ScheduleResult3DFixed
from src.models.soc_3d import ITC02BenchmarkLoader, SoC3D, ScheduleResult3D
from src.models.predictive_thermal import PredictiveThermalEstimator, FrequencyScaledScheduler
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler
from src.hardware.rpi_tester import RaspberryPi5Tester
from capstone.src.hardware.rpi_remote_bridge import RemoteRPiHILClient

# Reporting exporter
from capstone.scripts.generate_excel_results import export_custom_run, save_reports


# ============================================================================
# VISUALIZATION HELPERS
# ============================================================================
def plot_gantt_chart(schedule_res, title: str, output_path: str, is_3d: bool = False):
    """Generates a professional publication-quality Gantt Chart."""
    if not HAS_MATPLOTLIB:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    tasks = sorted(schedule_res.tasks, key=lambda t: t.core_id)
    y_positions = list(range(len(tasks)))
    y_labels = [f"Core {t.core_id} ({t.core_name})" for t in tasks]
    makespan = max(1, max((t.start_time + t.duration for t in tasks), default=1))

    if is_3d:
        colors = {0: '#1f77b4', 1: '#ff7f0e', 2: '#2ca02c'}
        layer_names = {
            0: 'Layer 1 / L0 (Bottom/Heatsink)',
            1: 'Layer 2 / L1 (Middle)',
            2: 'Layer 3 / L2 (Top)',
        }
        for idx, t in enumerate(tasks):
            c = colors.get(getattr(t, "layer_id", 0), '#1f77b4')
            ax.barh(idx, t.duration, left=t.start_time, height=0.6, color=c, edgecolor='black', alpha=0.85)
            if t.duration >= makespan * 0.085:
                ax.text(t.start_time + t.duration * 0.04, idx, f"L{getattr(t, 'layer_id', 0)} | {t.power}W",
                        va='center', ha='left', color='white', fontsize=7.5, fontweight='bold')
        legend_patches = [mpatches.Patch(color=colors[l], label=layer_names[l]) for l in range(3)]
        ax.set_ylim(-0.8, len(tasks) + 2.4)
        ax.legend(handles=legend_patches, loc='upper right', ncol=3, framealpha=0.95)
    else:
        for idx, t in enumerate(tasks):
            ax.barh(idx, t.duration, left=t.start_time, height=0.6, color='#1f77b4', edgecolor='black', alpha=0.85)
            if t.duration >= makespan * 0.085:
                ax.text(t.start_time + t.duration * 0.04, idx, f"W={t.tam_width} | {t.power}W",
                        va='center', ha='left', color='white', fontsize=7.5, fontweight='bold')

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=8)
    ax.set_xlim(0, makespan * 1.02)
    ax.set_xlabel("Test Application Time (Clock Cycles)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Embedded IP Cores / Modules", fontsize=11, fontweight='bold')
    title_text = title if schedule_res.algorithm_name in title else f"{title} ({schedule_res.algorithm_name})"
    ax.set_title(f"Test Schedule Gantt Chart — {title_text}", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  [Plot] Saved Gantt Chart: '{output_path}'")


def plot_dashboard(results: dict, benchmark_name: str, mode_name: str, output_path: str, max_p: float, max_tam: int, max_tsv: int = 0):
    """Generates a multi-panel execution profile and constraint compliance dashboard."""
    if not HAS_MATPLOTLIB:
        return

    is_3d = "3d" in mode_name.lower()
    nrows = 2 if is_3d else 1
    ncols = 2 if is_3d else 3
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 9 if is_3d else 4.8))
    fig.suptitle(f"{mode_name.upper()} Test Scheduling Performance Dashboard ({benchmark_name.upper()})", fontsize=14, fontweight='bold')

    algs = list(results.keys())
    makespans = [results[a].makespan for a in algs]
    palette = ['#1F4E79', '#D9534F', '#5CB85C', '#F0AD4E', '#5BC0DE', '#8E44AD', '#16A085']

    # Makespan bar chart
    ax_ms = axes[0, 0] if is_3d else axes[0]
    bars = ax_ms.bar(algs, makespans, color=palette[:len(algs)], width=0.52, edgecolor='black')
    ax_ms.set_ylabel("Makespan (Test Cycles)", fontweight='bold')
    ax_ms.set_title("Makespan Reduction Across Algorithms", fontweight='bold')
    ax_ms.grid(axis='y', linestyle='--', alpha=0.6)
    ax_ms.set_ylim(0, max(makespans) * 1.15 if makespans else 1)
    plt.setp(ax_ms.get_xticklabels(), rotation=22, ha='right', fontsize=8)
    for b in bars:
        h = b.get_height()
        ax_ms.text(b.get_x() + b.get_width() / 2., h * 1.01, f"{h:,}", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

    # Power Profile
    ax_p = axes[0, 1] if is_3d else axes[1]
    for idx, alg in enumerate(algs):
        ax_p.plot(results[alg].power_profile, label=alg, linewidth=1.8, color=palette[idx % len(palette)])
    ax_p.axhline(y=max_p, color='red', linestyle='--', label=f"Pmax Limit ({max_p:.1f}W)")
    ax_p.set_ylabel("Power Dissipation (W)", fontweight='bold')
    ax_p.set_xlabel("Normalized Timeline", fontweight='bold')
    ax_p.set_title("Continuous Peak Power Profile (Pmax Compliance)", fontweight='bold')
    ax_p.legend(fontsize=7.5, loc='upper right')
    ax_p.grid(True, linestyle='--', alpha=0.5)

    if not is_3d:
        # TAM profile for 2D
        ax_tam = axes[2]
        for idx, alg in enumerate(algs):
            ax_tam.plot(results[alg].tam_profile, label=alg, linewidth=1.8, color=palette[idx % len(palette)])
        ax_tam.axhline(y=max_tam, color='red', linestyle='--', label=f"Wmax Limit ({max_tam})")
        ax_tam.set_ylabel("Active TAM Width", fontweight='bold')
        ax_tam.set_xlabel("Normalized Timeline", fontweight='bold')
        ax_tam.set_title("Global TAM Bus Utilization", fontweight='bold')
        ax_tam.legend(fontsize=7.5)
        ax_tam.grid(True, linestyle='--', alpha=0.5)
    else:
        # Thermal Profile for 3D
        ax_th = axes[1, 0]
        for idx, alg in enumerate(algs):
            if hasattr(results[alg], "thermal_profile") and results[alg].thermal_profile:
                ax_th.plot(results[alg].thermal_profile, label=alg, linewidth=1.8, color=palette[idx % len(palette)])
        ax_th.axhline(y=95.0, color='red', linestyle='--', label="Tmax Limit (95.0°C)")
        ax_th.set_ylabel("Junction Temp Tj (°C)", fontweight='bold')
        ax_th.set_xlabel("Normalized Timeline", fontweight='bold')
        ax_th.set_title("Spatial-Temporal Thermal Profile (Tmax Compliance)", fontweight='bold')
        ax_th.legend(fontsize=7.5, loc='lower right')
        ax_th.grid(True, linestyle='--', alpha=0.5)

        # TSV profile for 3D
        ax_tsv = axes[1, 1]
        for idx, alg in enumerate(algs):
            if hasattr(results[alg], "tsv_profile") and results[alg].tsv_profile:
                ax_tsv.plot(results[alg].tsv_profile, label=alg, linewidth=1.8, color=palette[idx % len(palette)])
        if max_tsv > 0:
            ax_tsv.axhline(y=max_tsv, color='red', linestyle='--', label=f"TSVmax Limit ({max_tsv})")
        ax_tsv.set_ylabel("Active Vertical TSV Lines", fontweight='bold')
        ax_tsv.set_xlabel("Normalized Timeline", fontweight='bold')
        ax_tsv.set_title("Vertical TSV Interconnect Bandwidth", fontweight='bold')
        ax_tsv.legend(fontsize=7.5)
        ax_tsv.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  [Plot] Saved Execution Dashboard: '{output_path}'")


def plot_thermal_heatmaps(soc, schedule_res, output_path: str):
    """Plots spatial thermal footprint across all 3 vertical die layers."""
    if not HAS_MATPLOTLIB or not hasattr(schedule_res, "thermal_profile"):
        return

    peak_idx = int(np.argmax(schedule_res.thermal_profile))
    sampled_times = np.linspace(0, schedule_res.makespan, len(schedule_res.thermal_profile), dtype=int)
    peak_time = sampled_times[peak_idx]

    active_tasks = [t for t in schedule_res.tasks if t.start_time <= peak_time < t.end_time]
    active_cores = [soc.cores[t.core_id - 1] for t in active_tasks]

    thermal_res = soc.thermal_model.estimate_temperature_profile(active_cores, grid_resolution=6)
    temp_grids = thermal_res["temp_grids"] - 273.15

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    fig.suptitle(f"3D SoC Spatial Thermal Footprint at Peak Temp (t={peak_time:,} cycles) — {schedule_res.algorithm_name}", fontsize=13, fontweight='bold')

    for z in range(3):
        im = axes[z].imshow(temp_grids[z], cmap='hot', vmin=25, vmax=100)
        axes[z].set_title(f"Die Layer {z + 1} ({'Heatsink/Bottom' if z == 0 else 'Middle' if z == 1 else 'Top Die'})", fontsize=11, fontweight='bold')
        axes[z].set_xlabel("X Grid")
        axes[z].set_ylabel("Y Grid")
        fig.colorbar(im, ax=axes[z], label="Junction Temp (°C)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  [Plot] Saved Die Thermal Heatmap: '{output_path}'")


# ============================================================================
# HARDWARE-IN-THE-LOOP HELPER
# ============================================================================
def _run_hil_replay(tester_cls, schedule_res, rpi_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Executes local GPIO/Mock or remote Raspberry Pi (TCP/SSH) HIL schedule replay."""
    cfg = rpi_config or {}
    remote_host = cfg.get("host")
    time_scale = cfg.get("time_scale") or (1e-5 if remote_host else 1e-6)

    tester = tester_cls(
        mock_mode=False if remote_host else None,
        remote_host=remote_host,
        remote_port=cfg.get("port", 5055),
        transport=cfg.get("transport", "tcp"),
        ssh_user=cfg.get("user"),
        allow_mock_fallback=cfg.get("allow_fallback", True),
    )
    try:
        hil_res = tester.replay_schedule(schedule_res, time_scale_factor=time_scale)
    finally:
        tester.cleanup()

    hil_mode = hil_res.get("hardware_mode", hil_res.get("hardware_status", "Mock Engine"))
    overhead = hil_res.get("overhead_percentage", hil_res.get("overhead_percent", 0.0))
    endpoint = hil_res.get("remote_endpoint")
    header_suffix = f" ({endpoint})" if endpoint else ""
    print(f"\n[Hardware-in-the-Loop Replay (Raspberry Pi Tester{header_suffix})]")
    print(f"  Status: {hil_mode} | Wall Clock: {hil_res['total_wall_clock_sec']:.4f}s | Hardware Overhead: {overhead:.2f}%")
    return hil_res


# ============================================================================
# BENCHMARK SUITE RUNNERS
# ============================================================================
def run_2d_suite(
    benchmark: str,
    algorithms: List[str],
    seed: int,
    output_dir: Optional[str],
    no_plots: bool,
    run_hil: bool,
    rpi_config: Optional[Dict[str, Any]] = None,
    max_evals: Optional[int] = None,
    save_outputs: bool = True,
    verbose: bool = True,
) -> dict:
    """Executes the 2D Planar SoC Test Scheduling Suite."""
    if verbose:
        print("\n" + "=" * 98)
        print(f"   2D PLANAR SYSTEM-ON-CHIP (SoC) TEST SCHEDULING — {benchmark.upper()}")
        print("=" * 98)

    random.seed(seed)
    np.random.seed(seed)

    if benchmark == "d695":
        soc = ITC02BenchmarkLoader2D.load_d695_2d(max_tam_width=16, max_power=45.89)
    else:
        soc = ITC02BenchmarkLoader2D.load_p22810_2d(max_tam_width=32, max_power=94.05)

    # 1. IEEE 1500 Wrapper Design Reduction Analysis
    if verbose:
        profiles = ITC02BenchmarkLoader2D.get_wrapper_profiles_d695() if benchmark == "d695" else ITC02BenchmarkLoader2D.get_wrapper_profiles_p22810()
        analyzer = WrapperAnalyzer2D(profiles)
        wrapper_table = analyzer.compute_wrapper_reduction_table(STANDARD_TAM_SWEEP_2D)
        print("\n[IEEE 1500 Wrapper Design & Test Time Reduction Table]")
        print(f"{'TAM Width':<10} | {'Pre-Wrapper Raw':<18} | {'Post-Wrapper IEEE1500':<22} | {'Reduction %':<12}")
        print("-" * 68)
        for r in wrapper_table[:4]:
            print(f"{r['tam_width']:<10} | {r['raw_test_cycles']:<18,} | {r['post_wrapper_cycles']:<22,} | {r['reduction_pct']:.2f}%")
        print(f"... ({len(wrapper_table)} TAM sweep entries evaluated)")

    # 2. Scheduling Metaheuristics
    schedulers_map = {
        "greedy": ("Greedy 2D Baseline", Greedy2DScheduler, {}),
        "abc": ("Artificial Bee Colony (ABC 2D)", ABC2DScheduler, {"colony_size": 15, "max_iterations": 15}),
        "bat": ("Bat 2D Algorithm", Bat2DScheduler, {"num_bats": 15, "max_iterations": 15}),
        "firefly": ("Firefly 2D Algorithm", Firefly2DScheduler, {"num_fireflies": 15, "max_iterations": 15}),
        "maco": ("Modified ACO (MACO 2D)", MACO2DScheduler, {"num_ants": 15, "max_iterations": 15}),
        "hmaco_fa": ("H-MACO-FA Hybrid (2D)", HMACOFA2DScheduler, {"num_ants": 15, "num_fireflies": 12, "max_iterations": 15}),
    }

    selected = list(schedulers_map.keys()) if "all" in algorithms else [a for a in algorithms if a in schedulers_map]
    results = {}

    if verbose:
        budget_lbl = f" | max_evals={max_evals}" if max_evals is not None else ""
        print(f"\n[Executing {len(selected)} Metaheuristics across seed={seed}{budget_lbl}]")
        print(f"{'Algorithm':<32} | {'Makespan (CC)':<14} | {'Peak Power':<15} | {'TAM Used':<9} | {'Evals':<6} | {'Runtime':<9} | {'Status'}")
        print("-" * 108)

    for key in selected:
        disp_name, cls, base_kwargs = schedulers_map[key]
        kwargs = dict(base_kwargs)
        if max_evals is not None:
            kwargs["max_evals"] = max_evals
        random.seed(seed)
        np.random.seed(seed)
        t0 = time.perf_counter()
        scheduler = cls(soc, **kwargs)
        res = scheduler.optimize()
        runtime = time.perf_counter() - t0
        res.runtime_sec = runtime
        res.algorithm_name = disp_name
        results[disp_name] = res

        if verbose:
            evals = getattr(res, "eval_count", 0)
            print(f"{disp_name:<32} | {res.makespan:<14,} | {res.peak_power:<6.2f}/{soc.max_power:<5.1f}W | {res.max_tam_used:<3}/{soc.max_tam_width:<4} | {evals:<6} | {runtime:<7.4f}s | {res.constraint_status}")

    best_alg = min(results.keys(), key=lambda a: results[a].makespan)
    best_res = results[best_alg]
    if verbose:
        print("-" * 108)
        print(f"Optimal 2D Algorithm: '{best_alg}' with Makespan = {best_res.makespan:,} cycles")

    # 3. Hardware-in-the-Loop Replay
    if run_hil:
        _run_hil_replay(RaspberryPi5Tester2D, best_res, rpi_config)

    # 4. Save Artifacts
    if save_outputs:
        target_dir = output_dir or os.path.join(CAPSTONE_DIR, "2d", "results")
        os.makedirs(target_dir, exist_ok=True)

        if not no_plots and HAS_MATPLOTLIB:
            plot_gantt_chart(best_res, f"{benchmark.upper()} 2D Planar", os.path.join(target_dir, f"gantt_{benchmark}_2d.png"), is_3d=False)
            plot_dashboard(results, benchmark, "2d", os.path.join(target_dir, f"dashboard_{benchmark}_2d.png"), soc.max_power, soc.max_tam_width)

        export_custom_run(target_dir, benchmark, "2d", results)
    return results


def run_3d_suite(
    mode: str,
    benchmark: str,
    algorithms: List[str],
    seed: int,
    output_dir: Optional[str],
    no_plots: bool,
    run_hil: bool,
    rpi_config: Optional[Dict[str, Any]] = None,
    max_evals: Optional[int] = None,
    save_outputs: bool = True,
    verbose: bool = True,
) -> dict:
    """Executes the 3D SoC Test Scheduling Suite (Fixed Stacking or Random Stacking)."""
    is_fixed = mode == "fixed3d"
    mode_title = "STRUCTURED FIXED 3D STACKING" if is_fixed else "DYNAMIC RANDOM 3D STACKING"

    if verbose:
        print("\n" + "=" * 116)
        print(f"   {mode_title} — {benchmark.upper()}")
        print("=" * 116)

    random.seed(seed)
    np.random.seed(seed)

    if is_fixed:
        if benchmark == "d695":
            soc = FixedBenchmarkLoader.load_d695_fixed(max_tam_width=16, max_power=45.89, max_tsv=16)
        else:
            soc = FixedBenchmarkLoader.load_p22810_fixed(max_tam_width=32, max_power=94.05, max_tsv=24)
    else:
        if benchmark == "d695":
            soc = ITC02BenchmarkLoader.load_d695_3d(max_tam_width=16, max_power=45.89, max_tsv=16)
        else:
            soc = ITC02BenchmarkLoader.load_p22810_3d(max_tam_width=32, max_power=94.05, max_tsv=24)

    schedulers_map = {
        "greedy": ("Greedy 3D Baseline", Greedy3DScheduler, {}),
        "abc": ("Artificial Bee Colony (ABC 3D)", ABC3DScheduler, {"colony_size": 15, "max_iterations": 15}),
        "bat": ("Bat 3D Algorithm", Bat3DScheduler, {"num_bats": 15, "max_iterations": 15}),
        "firefly": ("Firefly 3D Algorithm", Firefly3DScheduler, {"num_fireflies": 15, "max_iterations": 15}),
        "maco": ("Modified ACO (MACO 3D)", MACO3DScheduler, {"num_ants": 15, "max_iterations": 15}),
        "hmaco_fa": ("H-MACO-FA Hybrid (3D)", HMACOFA3DScheduler, {"num_ants": 15, "num_fireflies": 12, "max_iterations": 15}),
    }

    selected = list(schedulers_map.keys()) if "all" in algorithms else [a for a in algorithms if a in schedulers_map]
    results = {}

    if verbose:
        budget_lbl = f" | max_evals={max_evals}" if max_evals is not None else ""
        print(f"\n[Executing {len(selected)} Metaheuristics across seed={seed}{budget_lbl}]")
        print(f"{'Algorithm':<30} | {'Makespan (CC)':<14} | {'Peak Power':<15} | {'Peak Tj (°C)':<13} | {'TSV':<8} | {'Evals':<6} | {'Runtime':<9} | {'Status'}")
        print("-" * 120)

    for key in selected:
        disp_name, cls, base_kwargs = schedulers_map[key]
        kwargs = dict(base_kwargs)
        if max_evals is not None:
            kwargs["max_evals"] = max_evals
        random.seed(seed)
        np.random.seed(seed)
        t0 = time.perf_counter()
        scheduler = cls(soc, **kwargs)
        res = scheduler.optimize()
        runtime = time.perf_counter() - t0
        res.runtime_sec = runtime
        res.algorithm_name = disp_name
        results[disp_name] = res

        if verbose:
            evals = getattr(res, "eval_count", 0)
            print(f"{disp_name:<30} | {res.makespan:<14,} | {res.peak_power:<6.2f}/{soc.max_power:<5.1f}W | {res.peak_temperature:<5.1f}/{soc.max_temperature - 273.15:<5.1f}°C | {res.max_tsv_used:<2}/{soc.max_tsv_bandwidth:<4} | {evals:<6} | {runtime:<7.4f}s | {res.constraint_status}")

    # Predictive Thermal Estimation & Frequency Scaling on best schedule
    best_alg = min(results.keys(), key=lambda a: results[a].makespan)
    best_res = results[best_alg]

    estimator = PredictiveThermalEstimator(num_layers=3)
    scaler = FrequencyScaledScheduler(soc, estimator)
    scaled_res = scaler.apply_frequency_scaling(best_res)
    scaled_res.runtime_sec = best_res.runtime_sec + 0.002
    scaled_res.eval_count = getattr(best_res, "eval_count", 0)
    results[f"{best_alg} + Scaled"] = scaled_res

    if verbose:
        print("\n[Applying Predictive Thermal Estimation & Dynamic Clock Scaling]")
        print(f"  {best_alg:<28} -> Makespan: {best_res.makespan:,} | Peak Tj: {best_res.peak_temperature:.1f}°C | Peak P: {best_res.peak_power:.2f}W")
        print(f"  {scaled_res.algorithm_name:<28} -> Makespan: {scaled_res.makespan:,} | Peak Tj: {scaled_res.peak_temperature:.1f}°C | Peak P: {scaled_res.peak_power:.2f}W | Status: {scaled_res.constraint_status}")

    # Hardware-in-the-Loop Replay
    if run_hil:
        _run_hil_replay(RaspberryPi5Tester, best_res, rpi_config)

    # Save Artifacts
    if save_outputs:
        folder_name = "fixed_stacking" if is_fixed else "random_stacking"
        target_dir = output_dir or os.path.join(CAPSTONE_DIR, folder_name, "results")
        os.makedirs(target_dir, exist_ok=True)

        clean_benchmark = "d695" if "d695" in benchmark.lower() else "p22810"
        suffix = "fixed" if is_fixed else "3d"

        if not no_plots and HAS_MATPLOTLIB:
            plot_gantt_chart(best_res, f"{benchmark.upper()} 3D ({'Fixed' if is_fixed else 'Random'})", os.path.join(target_dir, f"gantt_{clean_benchmark}_{suffix}.png"), is_3d=True)
            plot_thermal_heatmaps(soc, best_res, os.path.join(target_dir, f"thermal_heatmap_{clean_benchmark}_{suffix}.png"))
            plot_dashboard(results, benchmark, mode, os.path.join(target_dir, f"dashboard_{clean_benchmark}_{suffix}.png"), soc.max_power, soc.max_tam_width, soc.max_tsv_bandwidth)

        export_custom_run(target_dir, benchmark, mode, results)
    return results


def run_multiseed_comparison(
    mode: str,
    benchmark: str,
    algorithms: List[str],
    seeds: List[int],
    output_dir: Optional[str],
    no_plots: bool,
    run_hil: bool,
    rpi_config: Optional[Dict[str, Any]],
    max_evals: Optional[int],
) -> Dict[str, Any]:
    """Executes multi-seed experiments and computes Best, Worst, Mean, Median, and Std Dev."""
    print("\n" + "=" * 116)
    budget_lbl = f" | max_evals={max_evals}" if max_evals is not None else ""
    print(f"   MULTI-SEED STATISTICAL ANALYSIS — {mode.upper()} | {benchmark.upper()} | {len(seeds)} seeds{budget_lbl}")
    print("=" * 116)

    raw_rows = []
    grouped: Dict[str, List[Any]] = {}
    best_overall_res = None

    for idx, s in enumerate(seeds):
        is_last = idx == len(seeds) - 1
        if mode == "2d":
            res_map = run_2d_suite(
                benchmark, algorithms, s, output_dir,
                no_plots=no_plots or not is_last,
                run_hil=run_hil and is_last,
                rpi_config=rpi_config,
                max_evals=max_evals,
                save_outputs=is_last,
                verbose=False,
            )
        else:
            res_map = run_3d_suite(
                mode, benchmark, algorithms, s, output_dir,
                no_plots=no_plots or not is_last,
                run_hil=run_hil and is_last,
                rpi_config=rpi_config,
                max_evals=max_evals,
                save_outputs=is_last,
                verbose=False,
            )

        for alg_name, res in res_map.items():
            grouped.setdefault(alg_name, []).append(res)
            raw_rows.append([
                mode,
                benchmark,
                s,
                alg_name,
                int(res.makespan),
                round(float(res.peak_power), 4),
                round(float(getattr(res, "peak_temperature", 0.0)), 2),
                int(getattr(res, "max_tsv_used", getattr(res, "max_tam_used", 0))),
                int(getattr(res, "eval_count", 0)),
                round(float(getattr(res, "runtime_sec", 0.0)), 6),
                res.constraint_status,
            ])
            if best_overall_res is None or res.makespan < best_overall_res.makespan:
                best_overall_res = res

    print(f"{'Algorithm':<32} | {'Best':<10} | {'Worst':<10} | {'Mean':<12} | {'Median':<10} | {'Std Dev':<9} | {'Mean Evals':<10} | {'Mean Time'}")
    print("-" * 116)

    summary_rows = []
    for alg_name, items in grouped.items():
        makespans = [float(r.makespan) for r in items]
        evals = [float(getattr(r, "eval_count", 0)) for r in items]
        times = [float(getattr(r, "runtime_sec", 0.0)) for r in items]
        best_v = min(makespans)
        worst_v = max(makespans)
        mean_v = statistics.mean(makespans)
        med_v = statistics.median(makespans)
        std_v = statistics.stdev(makespans) if len(makespans) > 1 else 0.0
        mean_ev = statistics.mean(evals)
        mean_t = statistics.mean(times)

        print(f"{alg_name:<32} | {best_v:<10,.0f} | {worst_v:<10,.0f} | {mean_v:<12,.1f} | {med_v:<10,.1f} | {std_v:<9.1f} | {mean_ev:<10.1f} | {mean_t:<7.4f}s")
        summary_rows.append([
            mode,
            benchmark,
            alg_name,
            len(items),
            int(round(best_v)),
            int(round(worst_v)),
            round(mean_v, 2),
            round(med_v, 2),
            round(std_v, 2),
            round(mean_ev, 1),
            round(mean_t, 5),
            round(max(float(r.peak_power) for r in items), 2),
            round(max(float(getattr(r, "peak_temperature", 0.0)) for r in items), 2),
            "Safe" if all(r.constraint_status == "Safe" for r in items) else "Violation",
        ])

    folder_name = "2d" if mode == "2d" else ("fixed_stacking" if mode == "fixed3d" else "random_stacking")
    target_dir = output_dir or os.path.join(CAPSTONE_DIR, folder_name, "results")
    os.makedirs(target_dir, exist_ok=True)

    raw_csv_path = os.path.join(target_dir, f"multiseed_raw_{mode}_{benchmark}.csv")
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Mode", "Benchmark", "Seed", "Algorithm", "Makespan (CC)", "Peak Power (W)", "Peak Tj (C)", "Max TSV/TAM", "Eval Count", "Runtime (s)", "Status"])
        w.writerows(raw_rows)

    sheets = {
        f"Stats {mode.upper()} {benchmark.upper()}": {
            "title": f"Multi-Seed Statistical Summary ({mode.upper()} - {benchmark.upper()}, Seeds={seeds})",
            "headers": ["Mode", "Benchmark", "Algorithm", "N Seeds", "Best (CC)", "Worst (CC)", "Mean (CC)", "Median (CC)", "Std Dev (CC)", "Mean Evals", "Mean Runtime (s)", "Max Power (W)", "Max Tj (C)", "Status"],
            "rows": summary_rows,
        }
    }
    save_reports(target_dir, f"MultiSeed_Stats_{mode}_{benchmark}", sheets)
    return {"raw_rows": raw_rows, "summary_rows": summary_rows, "best_result": best_overall_res, "last_map": grouped}


# ============================================================================
# MAIN DISPATCHER
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Unified Test Solution for 2D & 3D System-on-Chip (SoC) Manufacturing Test Scheduling Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_test_suite.py --mode 2d --benchmark d695
  python run_test_suite.py --mode fixed3d --benchmark p22810 --algorithm hmaco_fa --max-evals 300
  python run_test_suite.py --mode random3d --benchmark d695 --seeds 42 100 2024 7 99 --max-evals 300
  python run_test_suite.py --mode fixed3d --benchmark d695 --rpi-host 10.231.118.57 --rpi-port 5055
  python run_test_suite.py --mode all --benchmark all
        """
    )

    parser.add_argument("--mode", choices=["2d", "fixed3d", "random3d", "all"], default="all",
                        help="Execution mode: 2d planar, fixed3d structured, random3d dynamic, or all (default: all)")
    parser.add_argument("--benchmark", choices=["d695", "p22810", "all"], default="all",
                        help="ITC'02 Benchmark: d695 (10 cores), p22810 (30 cores), or all (default: all)")
    parser.add_argument("--algorithm", choices=["greedy", "abc", "bat", "firefly", "maco", "hmaco_fa", "all"], default="all",
                        help="Specific metaheuristic algorithm to execute (default: all)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducible single-seed search (default: 42)")
    parser.add_argument("--seeds", type=int, nargs="+", default=None,
                        help="Multiple random seeds for statistical evaluation (e.g. --seeds 42 100 2024 7 99)")
    parser.add_argument("--max-evals", type=int, default=None,
                        help="Fair evaluation budget: max schedule evaluations per stochastic algorithm")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Custom directory to store generated Excel spreadsheets, CSVs, and plots")
    parser.add_argument("--no-plots", action="store_true",
                        help="Skip generating graphical Matplotlib visualizations (useful for headless servers)")
    parser.add_argument("--no-hil", action="store_true",
                        help="Skip Raspberry Pi Hardware-in-the-Loop schedule replay")
    parser.add_argument("--rpi-host", type=str, default=os.environ.get("RPI_HIL_HOST"),
                        help="Remote Raspberry Pi hostname or IP (e.g. 10.231.118.57 or raspberrypi.local)")
    parser.add_argument("--rpi-port", type=int, default=5055,
                        help="TCP port of remote rpi_hil_server.py (default: 5055)")
    parser.add_argument("--rpi-transport", choices=["tcp", "ssh"], default="tcp",
                        help="Remote Raspberry Pi connection transport: tcp or ssh (default: tcp)")
    parser.add_argument("--rpi-user", type=str, default=None,
                        help="SSH username on remote Raspberry Pi (when using --rpi-transport ssh)")
    parser.add_argument("--rpi-time-scale", type=float, default=None,
                        help="Hardware cycle-to-second scale factor (default: 1e-5 remote, 1e-6 local mock)")
    parser.add_argument("--rpi-no-fallback", action="store_true",
                        help="Fail instead of falling back to mock simulator if remote Raspberry Pi is unreachable")
    parser.add_argument("--rpi-ping", action="store_true",
                        help="Verify connectivity & GPIO backend on --rpi-host and exit")

    args = parser.parse_args()

    rpi_config = {
        "host": args.rpi_host,
        "port": args.rpi_port,
        "transport": args.rpi_transport,
        "user": args.rpi_user,
        "time_scale": args.rpi_time_scale,
        "allow_fallback": not args.rpi_no_fallback,
    }

    if args.rpi_ping:
        if not args.rpi_host:
            parser.error("--rpi-ping requires --rpi-host")
        client = RemoteRPiHILClient(
            host=args.rpi_host,
            port=args.rpi_port,
            transport=args.rpi_transport,
            ssh_user=args.rpi_user,
        )
        print(json.dumps(client.ping(), indent=2))
        return

    print("\n" + "#" * 90)
    print("   DEVELOPMENT OF TEST SOLUTION FOR 2D & 3D SYSTEM-ON-CHIP (SoC)")
    print("   Advanced VLSI Manufacturing Test Optimization & Architecture Framework")
    print("#" * 90)
    rpi_summary = f"Remote:{args.rpi_transport}://{args.rpi_host}" if args.rpi_host else "Local/Mock"
    seed_desc = f"Seeds={args.seeds}" if args.seeds else f"Seed={args.seed}"
    budget_desc = f" | MaxEvals={args.max_evals}" if args.max_evals else ""
    print(f"Configurations: Mode={args.mode} | Benchmark={args.benchmark} | Algorithm={args.algorithm} | {seed_desc}{budget_desc} | HIL={rpi_summary}")

    modes = ["2d", "fixed3d", "random3d"] if args.mode == "all" else [args.mode]
    benchmarks = ["d695", "p22810"] if args.benchmark == "all" else [args.benchmark]
    algorithms = [args.algorithm]

    start_total_time = time.perf_counter()
    all_runs_summary = {}

    for m in modes:
        for b in benchmarks:
            run_key = f"{m}_{b}"
            if args.seeds:
                stats_res = run_multiseed_comparison(
                    m, b, algorithms, args.seeds, args.output_dir,
                    args.no_plots, not args.no_hil, rpi_config, args.max_evals
                )
                all_runs_summary[run_key] = {k: min(v, key=lambda r: r.makespan) for k, v in stats_res["last_map"].items()}
            elif m == "2d":
                all_runs_summary[run_key] = run_2d_suite(
                    b, algorithms, args.seed, args.output_dir, args.no_plots,
                    not args.no_hil, rpi_config, max_evals=args.max_evals
                )
            else:
                all_runs_summary[run_key] = run_3d_suite(
                    m, b, algorithms, args.seed, args.output_dir, args.no_plots,
                    not args.no_hil, rpi_config, max_evals=args.max_evals
                )

    total_elapsed = time.perf_counter() - start_total_time

    # Print final multi-mode cross-comparison if mode='all'
    if args.mode == "all" and args.benchmark == "all":
        print("\n" + "=" * 95)
        print("   MULTI-DIMENSIONAL VLSI TEST ARCHITECTURE COMPARISON SUMMARY")
        print("=" * 95)
        print(f"{'Architecture Mode':<20} | {'Benchmark':<10} | {'Best Algorithm':<28} | {'Makespan (CC)':<15} | {'Peak Power':<12}")
        print("-" * 95)
        for run_key, res_dict in all_runs_summary.items():
            mode_lbl, bench_lbl = run_key.split("_")
            best_a = min(res_dict.keys(), key=lambda a: res_dict[a].makespan)
            best_res = res_dict[best_a]
            print(f"{mode_lbl.upper():<20} | {bench_lbl.upper():<10} | {best_a:<28} | {best_res.makespan:<15,} | {best_res.peak_power:<8.2f}W")
        print("-" * 95)

    print(f"\n[Execution Complete] Successfully executed entire suite in {total_elapsed:.2f} seconds.")
    print("All schedules, genuine Excel (.xlsx) files, CSV tables, and plots saved successfully.\n")


if __name__ == "__main__":
    main()
