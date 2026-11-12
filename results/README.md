# Results Directory Index (2D & 3D SoC Test Scheduling Capstone)

All tables, raw logs, Excel workbooks, and 300 DPI graphs in this folder were **programmatically generated** from genuine simulation runs and live Hardware-in-the-Loop (HIL) executions on the connected Raspberry Pi tester. No measurements are estimated or hardcoded.

## Experimental Configuration Summary
- **Multi-Seed Simulation**: `10` seeds (`[42, 100, 2024, 7, 99, 123, 256, 512, 777, 1024]`), Fair Evaluation Budget `--max-evals 300` across all 5 stochastic optimizers (`1` deterministic LPT baseline evaluation for Greedy)
- **Algorithms Evaluated (6)**: Greedy (Deterministic LPT Baseline), ABC, Bat, Firefly, MACO, H-MACO-FA Hybrid
- **Benchmarks**: ITC'02 `d695` (10 cores) & `p22810` (30 cores) across `2d`, `fixed3d`, and `random3d`
- **Physical HIL Hardware**: `Raspberry Pi 4 Model B Rev 1.4` | OS: `Debian GNU/Linux 13 (trixie)` | Backend: `RPi.GPIO` | Physical Verified: `True`
- **ML Thermal Reference Provenance**: Model-generated 3D RC ThermalModel traces (deduplicated hold-out split with 0% train-test overlap + independent unseen solver trajectory validation; no physical silicon thermal sensor attached)

## Directory Structure
- `raw_data/simulation/`: Raw per-seed run CSV (`raw_runs_all_modes_10seeds.csv`), anytime convergence traces, and ML test prediction residuals.
- `raw_data/raspberry_pi/`: Live ping verification JSON, per-trial GPIO task event JSON logs, and consolidated raw trial CSV.
- `simulation/{2d,fixed_3d,random_3d}/`: Mode-specific summaries, IEEE 1500 wrapper table, Fixed 3D multi-TAM sweep, and ML thermal regression/trajectory/scaling metrics.
- `hardware/{2d,fixed_3d,random_3d}/`: Physical Raspberry Pi replay trials and statistical hardware summaries.
- `comparisons/simulation_vs_hardware/`: Direct simulation vs physical Raspberry Pi timing CSV and `.xlsx`.
- `statistical_analysis/`: Multi-seed statistical summary (Best, Worst, Mean, Median, Std Dev) and rankings.
- `graphs/{2d,fixed_3d,random_3d,hardware,comparisons,statistical}/`: 20 publication-quality 300 DPI PNG figures + exact underlying CSV tables.
- `tables/{csv,excel}/`: Consolidated CSV and genuine OpenXML `.xlsx` workbooks (`Master_Capstone_Complete_Report.xlsx`, etc.).
- `presentation/`: Curated thesis/viva figures (`selected_graphs/`), key tables (`selected_tables/`), `key_findings.md`, and `figure_index.md`.
