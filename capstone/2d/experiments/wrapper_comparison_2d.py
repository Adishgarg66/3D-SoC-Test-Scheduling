"""
2d/experiments/wrapper_comparison_2d.py
========================================
Post-Wrapper Test Time Comparison Suite for 2D SoC Architecture.
Base Reference Paper: Iyengar, Chakrabarty, & Marinissen (IEEE TCAD 2002) [Paper 16].

Calculates and compares Pre-Wrapper (Raw) Test Cycles vs Post-Wrapper IEEE 1500 Balanced
Test Cycles across TAM Widths (16, 24, 32, 40, 48, 56, 64) for ITC'02 d695 and p22810.

Saves reports to 2d/results/wrapper_comparison_results.md and wrapper_comparison_results.txt.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.constraints.vlsi_constraints_2d import STANDARD_TAM_SWEEP_2D
from src.models.soc_2d import ITC02BenchmarkLoader2D
from src.models.wrapper_design_2d import WrapperAnalyzer2D


def analyze_benchmark_wrapper(benchmark_name: str, profiles):
    analyzer = WrapperAnalyzer2D(profiles)
    results_table = analyzer.compute_wrapper_reduction_table(STANDARD_TAM_SWEEP_2D)

    print("\n" + "=" * 90)
    print(f"   IEEE 1500 WRAPPER DESIGN & POST-WRAPPER TEST TIME ANALYSIS: {benchmark_name}")
    print(f"   Base Reference Paper: Iyengar et al. (IEEE TCAD 2002)")
    print("=" * 90)

    header = f"{'TAM Width':<10} | {'Pre-Wrapper Cycles':<20} | {'Post-Wrapper Cycles':<20} | {'Cycles Saved':<16} | {'Reduction %':<12}"
    print(header)
    print("-" * len(header))

    for row in results_table:
        print(f"{row['tam_width']:<10} | {row['raw_test_cycles']:<20,} | {row['post_wrapper_cycles']:<20,} | {row['cycles_saved']:<16,} | {row['reduction_pct']:<12.2f}%")

    print("-" * len(header))
    return results_table


def main():
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    # Analyze d695
    d695_profiles = ITC02BenchmarkLoader2D.get_wrapper_profiles_d695()
    d695_wrapper_results = analyze_benchmark_wrapper("ITC'02 d695 (2D Planar)", d695_profiles)

    # Analyze p22810
    p22810_profiles = ITC02BenchmarkLoader2D.get_wrapper_profiles_p22810()
    p22810_wrapper_results = analyze_benchmark_wrapper("ITC'02 p22810 (2D Planar)", p22810_profiles)

    # Save to 2d/results/wrapper_comparison_results.md
    md_path = os.path.join(results_dir, "wrapper_comparison_results.md")
    with open(md_path, "w") as f:
        f.write("# 2D SoC Test Time Comparison Post IEEE 1500 Wrapper Design\n\n")
        f.write("**Base Reference Paper**: V. Iyengar, K. Chakrabarty, and E. J. Marinissen, *\"Test Wrapper Design and TAM Optimization for System-on-Chip (SoC) Test Scheduling\"*, IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD), 2002.\n\n")
        
        f.write("## ITC'02 d695 Benchmark (10 Modules)\n\n")
        f.write("| TAM Width | Pre-Wrapper Cycles | Post-Wrapper Cycles (IEEE 1500) | Cycles Saved | Test Time Reduction % |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: |\n")
        for r in d695_wrapper_results:
            f.write(f"| {r['tam_width']} | {r['raw_test_cycles']:,} | **{r['post_wrapper_cycles']:,}** | {r['cycles_saved']:,} | **{r['reduction_pct']:.2f}%** |\n")

        f.write("\n\n## ITC'02 p22810 Benchmark (30 Modules)\n\n")
        f.write("| TAM Width | Pre-Wrapper Cycles | Post-Wrapper Cycles (IEEE 1500) | Cycles Saved | Test Time Reduction % |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: |\n")
        for r in p22810_wrapper_results:
            f.write(f"| {r['tam_width']} | {r['raw_test_cycles']:,} | **{r['post_wrapper_cycles']:,}** | {r['cycles_saved']:,} | **{r['reduction_pct']:.2f}%** |\n")

    print(f"\nSaved wrapper comparison results table to '{md_path}'")


if __name__ == "__main__":
    main()
