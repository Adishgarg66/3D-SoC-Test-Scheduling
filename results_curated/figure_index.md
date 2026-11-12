# Complete Curated Figure & Diagram Index

This index documents **all 62 unique existing figures and diagrams** (and 6 source PDFs + 2 architecture markdown diagram sources) organized in `results_curated/` across the Capstone repository—covering the 20 publication 300 DPI PNGs (`results/graphs/`), 22 distinct standalone simulation PNGs (`capstone/{2d,fixed_stacking,random_stacking,results}/`), 11 unique plots extracted verbatim from `soc_scheduling_improved_.(1).ipynb`, and 9 authentic architecture/workflow/block diagrams extracted at 288 DPI from `capstone/FinalCapstoneMidTerm-1.pdf`.

> **Preservation Notice:** Zero original files were deleted or altered. Duplicate files with identical SHA-256 content were deduplicated in primary category folders; filename collisions with distinct content were preserved under descriptive names. Note that older MidTerm PDF figures (`Fig 1.1`, `Fig 3.1`) originally stated "Raspberry Pi 5"; actual physical HIL execution throughout this project was verified on **Raspberry Pi 4 Model B Rev 1.4**.

---

## 1. 2D Planar Simulation (`2D_Simulation/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F01** | `2D_Simulation/Algorithm_Comparisons/fig01_2d_makespan_comparison.png` | `4050×1560` | 2D Fairness (10 Seeds) | `fig01_2d_makespan_comparison.csv` | Mean ± Std Makespan across all 6 algorithms (`Greedy`, `ABC`, `Bat`, `Firefly`, `MACO`, `H-MACO-FA`) under `--max-evals 300` on `d695` & `p22810` | `results/graphs/2d/fig01_2d_makespan_comparison.png` |
| **F02** | `2D_Simulation/Graphs/fig02_ieee1500_wrapper_reduction.png` | `3900×1620` | 2D IEEE 1500 Wrapper | `fig02_ieee1500_wrapper_reduction.csv`, `ieee1500_wrapper_sweep.csv` | Post-wrapper test cycles and % reduction vs unwrapped across TAM widths (`W = 16..64`) on `d695` & `p22810` | `results/graphs/2d/fig02_ieee1500_wrapper_reduction.png` |
| **F03** | `2D_Simulation/Gantt_Charts/fig03_2d_gantt_d695.png` | `3600×1800` | 2D Schedule Gantt | `2d_scheduling_summary.csv` | Best 2D planar concurrent core schedule Gantt chart for ITC'02 `d695` (`seed=42`, `--max-evals 300`) | `results/graphs/2d/fig03_2d_gantt_d695.png` |
| **F04** | `2D_Simulation/Gantt_Charts/fig04_2d_gantt_p22810.png` | `3600×1800` | 2D Schedule Gantt | `2d_scheduling_summary.csv` | Best 2D planar concurrent core schedule Gantt chart for ITC'02 `p22810` (`seed=42`, `--max-evals 300`) | `results/graphs/2d/fig04_2d_gantt_p22810.png` |
| **C01** | `2D_Simulation/Algorithm_Comparisons/capstone_2d_dashboard_d695.png` | `4800×1500` | Standalone 2D Dashboard | `2D_D695.csv`, `2D_SoC_Test_Scheduling_Results.xlsx` | Standalone 2D runner multi-algorithm makespan, power profile & TAM dashboard for `d695` | `capstone/2d/results/dashboard_d695_2d.png` |
| **C02** | `2D_Simulation/Algorithm_Comparisons/capstone_2d_dashboard_p22810.png` | `4800×1500` | Standalone 2D Dashboard | `2D_P22810.csv`, `2D_SoC_Test_Scheduling_Results.xlsx` | Standalone 2D runner multi-algorithm makespan, power profile & TAM dashboard for `p22810` | `capstone/2d/results/dashboard_p22810_2d.png` |
| **C03** | `2D_Simulation/Gantt_Charts/capstone_2d_gantt_d695.png` | `3600×1800` | Standalone 2D Gantt | `2D_D695.csv` | Standalone 2D runner best schedule Gantt chart for `d695` | `capstone/2d/results/gantt_d695_2d.png` |
| **C04** | `2D_Simulation/Gantt_Charts/capstone_2d_gantt_p22810.png` | `3600×1800` | Standalone 2D Gantt | `2D_P22810.csv` | Standalone 2D runner best schedule Gantt chart (Bat 2D, TAM/Power annotations) for `p22810` | `capstone/2d/results/gantt_p22810_2d.png` |
| **NB01** | `2D_Simulation/Algorithm_Comparisons/nb_2d_algorithm_comparison_dashboard.png` | `1589×1115` | Notebook 2D Dashboard | `soc_scheduling_improved_.(1).ipynb` | Early Phase-1 annotated 4-panel dashboard (Runtime, Makespan, Total Power, Max Simultaneous Power; 6 algorithms) *(supersedes unannotated `cell21` & subsets `cell27`)* | `soc_scheduling_improved_.(1).ipynb` (Cell 11, Img 0) |
| **NB02** | `2D_Simulation/Graphs/nb_2d_power_per_session.png` | `1589×495` | Notebook Power Profile | `soc_scheduling_improved_.(1).ipynb` | Stacked Power Distribution Across Parallel Sessions per Algorithm with $P_{\max}$ threshold (`d695` & `p22810`) | `soc_scheduling_improved_.(1).ipynb` (Cell 17, Img 0) |
| **NB03** | `2D_Simulation/Gantt_Charts/nb_2d_gantt_compact_grid.png` | `2211×911` | Notebook Gantt Grid | `soc_scheduling_improved_.(1).ipynb` | Compact 2×6 Gantt grid comparing all 6 Phase-1 algorithms across `d695` & `p22810` | `soc_scheduling_improved_.(1).ipynb` (Cell 13, Img 0) |
| **NB04** | `2D_Simulation/Gantt_Charts/nb_2d_gantt_all_algs_d695.png` | `1811×1811` | Notebook Session Gantt | `soc_scheduling_improved_.(1).ipynb` | Per-session stacked Gantt chart grid on `d695` (Greedy, Bat, ABC, MACO, Firefly, Hybrid) | `soc_scheduling_improved_.(1).ipynb` (Cell 23, Img 0) |
| **NB05** | `2D_Simulation/Gantt_Charts/nb_2d_gantt_all_algs_p22810.png` | `1811×1811` | Notebook Session Gantt | `soc_scheduling_improved_.(1).ipynb` | Per-session stacked Gantt chart grid on `p22810` (Greedy, Bat, ABC, MACO, Firefly, Hybrid) | `soc_scheduling_improved_.(1).ipynb` (Cell 23, Img 1) |

---

## 2. Fixed 3D Stacking Simulation (`Fixed_3D_Simulation/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F05** | `Fixed_3D_Simulation/Power_TSV_TAM_Profiles/fig05_fixed3d_tam_sweep_p22810.png` | `3150×1650` | Fixed 3D TAM Sweep | `fig05_fixed3d_tam_sweep_p22810.csv`, `fixed3d_multi_tam_sweep.csv` | Post-bond TAM sweep ($W_{\max} = 16\text{ to }64$ bits, $\text{TSV}_{\max}=80$, `max_evals=300`) across all 6 algorithms on `p22810` | `results/graphs/fixed_3d/fig05_fixed3d_tam_sweep_p22810.png` |
| **F06** | `Fixed_3D_Simulation/Graphs/fig06_fixed3d_dashboard_d695.png` | `4500×2700` | Fixed 3D Dashboard | `fixed3d_scheduling_summary.csv`, `02_Fixed_3D_Results.xlsx` | 4-panel dashboard (Makespan, Power, Thermal $T_j$, Vertical TSV utilization) for Fixed 3D `d695` (`seed=42`, `--max-evals 300`) | `results/graphs/fixed_3d/fig06_fixed3d_dashboard_d695.png` |
| **F07** | `Fixed_3D_Simulation/Graphs/fig07_fixed3d_dashboard_p22810.png` | `4500×2700` | Fixed 3D Dashboard | `fixed3d_scheduling_summary.csv`, `02_Fixed_3D_Results.xlsx` | 4-panel dashboard (Makespan, Power, Thermal $T_j$, Vertical TSV utilization) for Fixed 3D `p22810` (`seed=42`, `--max-evals 300`) | `results/graphs/fixed_3d/fig07_fixed3d_dashboard_p22810.png` |
| **F08** | `Fixed_3D_Simulation/Thermal_Heatmaps/fig08_fixed3d_thermal_heatmap_p22810.png` | `4500×1350` | Fixed 3D Thermal Heatmap | `fig08_fixed3d_thermal_heatmap_p22810.csv` | 3-Layer spatial thermal grid heatmap ($6\times 6$ grids for Bottom/Middle/Top dies) at peak $T_j$ for Fixed 3D `p22810` | `results/graphs/fixed_3d/fig08_fixed3d_thermal_heatmap_p22810.png` |
| **F09** | `Fixed_3D_Simulation/Gantt_Charts/fig09_fixed3d_gantt_p22810.png` | `3600×1800` | Fixed 3D Schedule Gantt | `fixed3d_scheduling_summary.csv` | Layer-color-coded 3D Gantt chart for Fixed 3D `p22810` showing fixed die partitioning across 30 cores | `results/graphs/fixed_3d/fig09_fixed3d_gantt_p22810.png` |
| **C05** | `Fixed_3D_Simulation/Graphs/capstone_fixed3d_dashboard_d695.png` | `4200×3000` | Standalone Fixed 3D | `FIXED3D_D695.csv`, `Fixed_3D_SoC_Test_Scheduling_Results.xlsx` | Standalone `fixed_stacking` runner 4-panel constraint & makespan dashboard for `d695` | `capstone/fixed_stacking/results/dashboard_d695_fixed.png` |
| **C06** | `Fixed_3D_Simulation/Graphs/capstone_fixed3d_dashboard_p22810.png` | `4200×3000` | Standalone Fixed 3D | `FIXED3D_P22810.csv`, `Fixed_3D_SoC_Test_Scheduling_Results.xlsx` | Standalone `fixed_stacking` runner 4-panel constraint & makespan dashboard for `p22810` | `capstone/fixed_stacking/results/dashboard_p22810_fixed.png` |
| **C07** | `Fixed_3D_Simulation/Gantt_Charts/capstone_fixed3d_gantt_d695.png` | `3600×1800` | Standalone Fixed Gantt | `FIXED3D_D695.csv` | Standalone `fixed_stacking` layer-coded 3D Gantt chart for `d695` | `capstone/fixed_stacking/results/gantt_d695_fixed.png` |
| **C08** | `Fixed_3D_Simulation/Gantt_Charts/capstone_fixed3d_gantt_p22810.png` | `3600×1800` | Standalone Fixed Gantt | `FIXED3D_P22810.csv` | Standalone `fixed_stacking` layer-coded 3D Gantt chart for `p22810` (Firefly 3D best single run) | `capstone/fixed_stacking/results/gantt_p22810_fixed.png` |
| **C09** | `Fixed_3D_Simulation/Thermal_Heatmaps/capstone_fixed3d_thermal_heatmap_d695.png` | `4500×1350` | Standalone Fixed Thermal | `FIXED3D_D695.csv` | Standalone `fixed_stacking` 3-layer spatial thermal footprint at peak $T_j$ for `d695` | `capstone/fixed_stacking/results/thermal_heatmap_d695_fixed.png` |
| **C10** | `Fixed_3D_Simulation/Thermal_Heatmaps/capstone_fixed3d_thermal_heatmap_p22810.png` | `4500×1350` | Standalone Fixed Thermal | `FIXED3D_P22810.csv` | Standalone `fixed_stacking` 3-layer spatial thermal footprint at peak $T_j$ ($t=250,976$) for `p22810` | `capstone/fixed_stacking/results/thermal_heatmap_p22810_fixed.png` |

---

## 3. Random 3D Stacking Simulation (`Random_3D_Simulation/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F10** | `Random_3D_Simulation/Graphs/fig10_random3d_dashboard_p22810.png` | `4500×2700` | Random 3D Dashboard | `random3d_scheduling_summary.csv`, `03_Random_3D_Results.xlsx` | 4-panel dashboard (Makespan, Power, Thermal $T_j$, TSV utilization) for Random 3D `p22810` (`seed=42`, `--max-evals 300`, H-MACO-FA included) | `results/graphs/random_3d/fig10_random3d_dashboard_p22810.png` |
| **F11** | `Random_3D_Simulation/Thermal_Heatmaps/fig11_random3d_thermal_heatmap_p22810.png` | `4500×1350` | Random 3D Thermal | `thermal_frequency_scaling_comparison.csv` | 3-Layer spatial thermal grid footprint at peak $T_j$ for Random 3D `p22810` (`seed=42`, `--max-evals 300`) | `results/graphs/random_3d/fig11_random3d_thermal_heatmap_p22810.png` |
| **C11** | `Random_3D_Simulation/Graphs/capstone_random3d_dashboard_d695_hmacofa.png` | `4500×2700` | Standalone Random 3D | `RANDOM3D_D695.csv`, `Random_3D_SoC_Test_Scheduling_Results.xlsx` | Standalone Random 3D 6-algorithm dashboard (`d695`, including `H-MACO-FA 3D`) | `capstone/random_stacking/results/dashboard_d695_3d.png` |
| **C12** | `Random_3D_Simulation/Graphs/capstone_random3d_dashboard_p22810_hmacofa.png` | `4500×2700` | Standalone Random 3D | `RANDOM3D_P22810.csv`, `Random_3D_SoC_Test_Scheduling_Results.xlsx` | Standalone Random 3D 6-algorithm dashboard (`p22810`, `H-MACO-FA 3D` = `415,700` cycles) | `capstone/random_stacking/results/dashboard_p22810_3d.png` |
| **C13** | `Random_3D_Simulation/Graphs/capstone_random3d_dashboard_d695_scaled.png` | `4200×3000` | Legacy Frequency-Scaled | `thermal_frequency_scaling_comparison.csv` | Earlier 5-alg + Frequency-Scaled runner dashboard for Random 3D `d695` (`ABC 3D + Scaled`) | `capstone/random_stacking/results/dashboard_d695.png` |
| **C14** | `Random_3D_Simulation/Graphs/capstone_random3d_dashboard_p22810_scaled.png` | `4200×3000` | Legacy Frequency-Scaled | `thermal_frequency_scaling_comparison.csv` | Earlier 5-alg + Frequency-Scaled runner dashboard for Random 3D `p22810` (`Firefly 3D + Scaled`) | `capstone/random_stacking/results/dashboard_p22810.png` |
| **C15** | `Random_3D_Simulation/Graphs/capstone_cli_random3d_dashboard_d695_4200x3000.png` | `4200×3000` | Legacy CLI Dashboard | `RANDOM3D_D695.csv` | Unified CLI (`capstone/results/`) 6-alg Random 3D dashboard (`d695`, 4200×3000 layout) | `capstone/results/dashboard_d695.png` |
| **C16** | `Random_3D_Simulation/Graphs/capstone_cli_random3d_dashboard_p22810_4200x3000.png` | `4200×3000` | Legacy CLI Dashboard | `RANDOM3D_P22810.csv` | Unified CLI (`capstone/results/`) 6-alg Random 3D dashboard (`p22810`, 4200×3000 layout) | `capstone/results/dashboard_p22810.png` |
| **C17** | `Random_3D_Simulation/Gantt_Charts/capstone_random3d_gantt_d695.png` | `3600×1800` | Random 3D Gantt | `RANDOM3D_D695.csv` | Standalone Random 3D layer-colored Gantt chart (`d695`) *(deduplicated identical copy in `capstone/results/`)* | `capstone/random_stacking/results/gantt_d695_3d.png` |
| **C18** | `Random_3D_Simulation/Gantt_Charts/capstone_random3d_gantt_p22810.png` | `3600×1800` | Random 3D Gantt | `RANDOM3D_P22810.csv` | Standalone Random 3D layer-colored Gantt chart (`p22810`, MACO 3D) *(deduplicated identical copy in `capstone/results/`)* | `capstone/random_stacking/results/gantt_p22810_3d.png` |
| **C19** | `Random_3D_Simulation/Thermal_Heatmaps/capstone_random3d_thermal_heatmap_d695_3d.png` | `4500×1350` | Random 3D Thermal | — | Standalone 3-layer spatial thermal heatmap (`d695`, H-MACO-FA run) | `capstone/random_stacking/results/thermal_heatmap_d695_3d.png` |
| **C20** | `Random_3D_Simulation/Thermal_Heatmaps/capstone_random3d_thermal_heatmap_p22810_3d.png` | `4500×1350` | Random 3D Thermal | — | Standalone 3-layer spatial thermal heatmap (`p22810`, Firefly 3D, $t=212,149$) | `capstone/random_stacking/results/thermal_heatmap_p22810_3d.png` |
| **C21** | `Random_3D_Simulation/Thermal_Heatmaps/capstone_random3d_thermal_heatmap_d695_legacy.png` | `4500×1350` | Random 3D Thermal | — | Standalone 3-layer thermal heatmap (`d695`, earlier CLI run) *(deduplicated identical copy in `capstone/results/`)* | `capstone/random_stacking/results/thermal_heatmap_d695.png` |
| **C22** | `Random_3D_Simulation/Thermal_Heatmaps/capstone_random3d_thermal_heatmap_p22810_legacy.png` | `4500×1350` | Random 3D Thermal | — | Standalone 3-layer thermal heatmap (`p22810`, earlier CLI run) *(deduplicated identical copy in `capstone/results/`)* | `capstone/random_stacking/results/thermal_heatmap_p22810.png` |
| **NB06** | `Random_3D_Simulation/Graphs/nb_3d_cuboid_schedule_d695_bat.png` | `867×890` | Notebook 3D Cuboid | `soc_scheduling_improved_.(1).ipynb` | Interactive-style 3D Cuboid SoC Test Schedule (`d695` — Bat: Time × TAM Width × Power) | `soc_scheduling_improved_.(1).ipynb` (Cell 44, Img 0) |
| **NB07** | `Random_3D_Simulation/Graphs/nb_3d_cuboid_schedule_p22810_bat.png` | `867×890` | Notebook 3D Cuboid | `soc_scheduling_improved_.(1).ipynb` | Interactive-style 3D Cuboid SoC Test Schedule (`p22810` — Bat: Time × TAM Width × Power) | `soc_scheduling_improved_.(1).ipynb` (Cell 44, Img 1) |
| **NB08** | `Random_3D_Simulation/Graphs/nb_3d_makespan_comparison_d695.png` | `1089×590` | Notebook 3D Bars | `soc_scheduling_improved_.(1).ipynb` | Early notebook 3D makespan bar comparison across 6 algorithms (`d695`) | `soc_scheduling_improved_.(1).ipynb` (Cell 45, Img 0) |
| **NB09** | `Random_3D_Simulation/Graphs/nb_3d_makespan_comparison_p22810.png` | `1089×590` | Notebook 3D Bars | `soc_scheduling_improved_.(1).ipynb` | Early notebook 3D makespan bar comparison across 6 algorithms (`p22810`) | `soc_scheduling_improved_.(1).ipynb` (Cell 45, Img 1) |
| **NB10** | `Random_3D_Simulation/Power_TSV_TAM_Profiles/nb_3d_power_vs_tam_utilization_d695.png` | `1189×590` | Notebook TAM vs Power | `soc_scheduling_improved_.(1).ipynb` | Scatter comparison of Total Power vs TAM Utilization across 6 algorithms (`d695`) | `soc_scheduling_improved_.(1).ipynb` (Cell 46, Img 0) |
| **NB11** | `Random_3D_Simulation/Power_TSV_TAM_Profiles/nb_3d_power_vs_tam_utilization_p22810.png` | `1189×590` | Notebook TAM vs Power | `soc_scheduling_improved_.(1).ipynb` | Scatter comparison of Total Power vs TAM Utilization across 6 algorithms (`p22810`) | `soc_scheduling_improved_.(1).ipynb` (Cell 46, Img 1) |

---

## 4. Raspberry Pi Hardware Validation (`Raspberry_Pi_Hardware/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F14** | `Raspberry_Pi_Hardware/Hardware_Graphs/fig14_rpi_wallclock_trials.png` | `3300×1560` | Physical RPi 4 Wall-Clock | `fig14_rpi_wallclock_trials.csv`, `rpi_all_trials_raw.csv`, `18 hil_*.json` | Sequential Raspberry Pi 4 Model B Rev 1.4 GPIO replay wall-clock vs expected sequential task sleep sums across all 6 modes×benchmarks | `results/graphs/hardware/fig14_rpi_wallclock_trials.png` |
| **F15** | `Raspberry_Pi_Hardware/Hardware_Graphs/fig15_rpi_gpio_task_events.png` | `3300×1500` | Physical RPi 4 GPIO | `fig15_rpi_gpio_task_events.csv`, `hil_fixed3d_d695_trial1.json` | Sequential per-core measured Raspberry Pi 4 GPIO pulse duration vs scaled target (ms) for Fixed 3D `d695` Trial 1 | `results/graphs/hardware/fig15_rpi_gpio_task_events.png` |

---

## 5. Simulation vs Hardware Comparison (`Simulation_vs_Hardware/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F16** | `Simulation_vs_Hardware/Comparison_Graphs/fig16_sim_vs_rpi_execution_time.png` | `4050×1560` | Sim vs Hardware | `fig16_sim_vs_rpi_execution_time.csv`, `sim_vs_rpi_comparison.csv` | Host Optimizer CPU vs Scaled Concurrent Makespan vs Physical RPi 4 Sequential Wall-Clock & Measured Linux/GPIO overhead (%) | `results/graphs/comparisons/fig16_sim_vs_rpi_execution_time.png` |
| **F17** | `Simulation_vs_Hardware/Comparison_Graphs/fig17_2d_vs_3d_architecture_comparison.png` | `3900×1560` | 2D vs 3D Architecture | `fig17_2d_vs_3d_architecture_comparison.csv` | Mean makespan comparison across 2D Planar, Fixed 3D, and Random 3D for Greedy, MACO, and H-MACO-FA (`d695` & `p22810`) | `results/graphs/comparisons/fig17_2d_vs_3d_architecture_comparison.png` |

---

## 6. Statistical Analysis & Convergence (`Statistical_Analysis/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F12** | `Statistical_Analysis/Algorithm_Comparisons/fig12_3d_convergence_curves.png` | `4050×1560` | Fair-Budget Convergence | `fig12_3d_convergence_curves.csv`, `convergence_histories_3d.csv` | Anytime convergence curves vs exact schedule evaluation count (`max_evals=300`) across 5 stochastic algorithms on Fixed & Random 3D `p22810` | `results/graphs/random_3d/fig12_3d_convergence_curves.png` |
| **F18** | `Statistical_Analysis/Multi_Seed_Graphs/fig18_multiseed_boxplot_d695.png` | `4800×1560` | Multi-Seed Statistics | `fig18_multiseed_boxplot_d695.csv`, `multiseed_statistical_summary.csv`, `raw_runs_all_modes_10seeds.csv` | 10-seed makespan boxplot distributions on `d695` across 2D, Fixed 3D, and Random 3D (`max_evals=300`) | `results/graphs/statistical/fig18_multiseed_boxplot_d695.png` |
| **F19** | `Statistical_Analysis/Multi_Seed_Graphs/fig19_multiseed_boxplot_p22810.png` | `4800×1560` | Multi-Seed Statistics | `fig19_multiseed_boxplot_p22810.csv`, `multiseed_statistical_summary.csv`, `raw_runs_all_modes_10seeds.csv` | 10-seed makespan boxplot distributions on `p22810` across 2D, Fixed 3D, and Random 3D (`max_evals=300`) | `results/graphs/statistical/fig19_multiseed_boxplot_p22810.png` |
| **F20** | `Statistical_Analysis/Multi_Seed_Graphs/fig20_fair_budget_runtime_vs_evals.png` | `3900×1500` | Fair-Budget Verification | `fig20_fair_budget_runtime_vs_evals.csv`, `algorithm_ranking_overview.csv` | Mean schedule evaluation count verification (Greedy=`1` deterministic LPT vs Stochastic=`300`) & mean CPU runtime (`Fixed 3D p22810`) | `results/graphs/statistical/fig20_fair_budget_runtime_vs_evals.png` |

---

## 7. ML Thermal Prediction (`ML_Thermal_Prediction/`)

| ID | Curated Path | Resolution | Category | Companion Data | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **F13** | `ML_Thermal_Prediction/Prediction_Graphs/fig13_ml_thermal_regression.png` | `4050×1560` | ML Thermal Regression | `fig13_ml_thermal_regression.csv`, `ml_thermal_regression_metrics.csv`, `ml_thermal_trajectory_validation.csv`, `06_ML_Thermal_Prediction_Report.xlsx` | Polynomial Ridge ($d=2$) predicted vs 3D RC reference peak $T_j$ scatter & held-out error distribution (`0%` train-test overlap, deduplicated split) | `results/graphs/random_3d/fig13_ml_thermal_regression.png` |

---

## 8. Architecture, Workflow & Block Diagrams (`Architecture_and_Methodology/`)

> All 9 raster diagram PNGs below are genuine pre-existing team figures rendered verbatim at 288 DPI from `capstone/FinalCapstoneMidTerm-1.pdf` (`Figures 1.1` & `3.1–3.8`), accompanied by the original PDF report, 5 reference papers, and Markdown architecture specs.

| ID | Curated Path | Resolution | Category | Source / Companion | Description | Original Source Location |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **D01** | `Architecture_and_Methodology/Workflow_Diagrams/diagram_01_overall_3d_soc_framework_flow.png` | `1809×2810` | Workflow Diagram | `FinalCapstoneMidTerm-1.pdf` (p. 11) | 10-stage Overall Flow of Proposed 3D SoC Test Scheduling Framework (`Figure 1.1`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D02** | `Architecture_and_Methodology/Workflow_Diagrams/diagram_02_integrated_testing_validation_workflow.png` | `1788×1033` | Workflow Diagram | `FinalCapstoneMidTerm-1.pdf` (p. 24) | Horizontal Integrated 2D-to-3D & Hardware Validation Loop Flowchart (`Figure 3.1`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D03** | `Architecture_and_Methodology/System_Architecture/diagram_03_ieee1500_embedded_core_wrapper_block.png` | `1635×356` | Block / System Arch | `FinalCapstoneMidTerm-1.pdf` (p. 25) | IEEE 1500 Embedded Core Wrapper Block Diagram (`SoC Pins -> TAM Bus -> Wrapper -> Core`, `Figure 3.2`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D04** | `Architecture_and_Methodology/Block_Diagrams/diagram_04_global_tam_bandwidth_distribution_block.png` | `1764×601` | Block Diagram | `FinalCapstoneMidTerm-1.pdf` (p. 26) | Global TAM Bus ($\text{TAM}_{\max}$) structural partitioning across concurrent parallel cores (`Figure 3.3`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D05** | `Architecture_and_Methodology/System_Architecture/diagram_05_3d_soc_tsv_interconnect_structure_block.png` | `1456×694` | System Architecture | `FinalCapstoneMidTerm-1.pdf` (p. 28) | Multi-layer 3D SoC vertical Through-Silicon Via (TSV) communication stack across Die 1–3 (`Figure 3.4`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D06** | `Architecture_and_Methodology/Block_Diagrams/diagram_06_3d_soc_thermal_hotspot_cross_section_block.png` | `1949×647` | Block Diagram | `FinalCapstoneMidTerm-1.pdf` (p. 29) | Cross-sectional 3D SoC stack illustrating trapped thermal hotspot zone in inner Die 2 (`Figure 3.5`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D07** | `Architecture_and_Methodology/Workflow_Diagrams/diagram_07_maco_execution_loop_flowchart.png` | `1605×551` | Algorithm Flowchart | `FinalCapstoneMidTerm-1.pdf` (p. 30) | MACO scheduling execution loop & dynamic ant fleet scaling flowchart (`Figure 3.6`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D08** | `Architecture_and_Methodology/Workflow_Diagrams/diagram_08_firefly_exploration_pipeline_flowchart.png` | `1490×574` | Algorithm Flowchart | `FinalCapstoneMidTerm-1.pdf` (p. 31) | Firefly Algorithm brightness evaluation & exploration pipeline flowchart (`Figure 3.7`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **D09** | `Architecture_and_Methodology/Workflow_Diagrams/diagram_09_bat_echolocation_search_loop_flowchart.png` | `1490×610` | Algorithm Flowchart | `FinalCapstoneMidTerm-1.pdf` (p. 32) | Bat Algorithm echolocation frequency/velocity/loudness search loop flowchart (`Figure 3.8`) | `capstone/FinalCapstoneMidTerm-1.pdf` |
| **M01** | `Architecture_and_Methodology/System_Architecture/system_architecture_mermaid.md` | Mermaid Spec | Architecture Spec | Extracted verbatim | Complete updated end-to-end architecture flowchart including `H-MACO-FA`, fair budgets, & Raspberry Pi 4 HIL | `README.md` (Lines 80–108) |
| **M02** | `Architecture_and_Methodology/Workflow_Diagrams/system_breakdown.md` | Markdown/ASCII | Methodology Spec | Original doc | 7-step execution breakdown & ASCII pipeline flow diagram | `capstone/docs/system_breakdown.md` |

---

## Deduplicated & Superseded Items Audit (Zero Loss Guarantee)
The following **7 files** were intentionally omitted from the primary taxonomy folders strictly to eliminate redundancy under curation rules, while all underlying unique plots remain represented cleanly:
1. `capstone/results/gantt_d695_3d.png` — Byte-identical SHA-256 (`bc6f7c983c53`) to `capstone/random_stacking/results/gantt_d695_3d.png` (**kept as C17**).
2. `capstone/results/gantt_p22810_3d.png` — Byte-identical SHA-256 (`3b3c7e8a649a`) to `capstone/random_stacking/results/gantt_p22810_3d.png` (**kept as C18**).
3. `capstone/results/thermal_heatmap_d695.png` — Byte-identical SHA-256 (`c9f30b8a3da5`) to `capstone/random_stacking/results/thermal_heatmap_d695.png` (**kept as C21**).
4. `capstone/results/thermal_heatmap_p22810.png` — Byte-identical SHA-256 (`b7dfbb953f4b`) to `capstone/random_stacking/results/thermal_heatmap_p22810.png` (**kept as C22**).
5. `soc_scheduling_improved_.(1).ipynb` (Cell 21, Img 0) — Earlier plain/unannotated draft (`1589×1082`) of Cell 11 (`1589×1115`, **kept as NB01**).
6. `soc_scheduling_improved_.(1).ipynb` (Cell 27, Img 0 & Img 1) — Lower-resolution single-panel makespan bar subsets (`868×451`, `876×451`) already shown in `NB01` (`1589×1115`).
7. Exact CSV/XLSX duplicates: `results/tables/csv/{multiseed_statistical_summary,sim_vs_rpi_comparison}.csv`, `results/statistical_analysis/multiseed_statistical_summary.xlsx` (identical to `04_MultiSeed_Statistical_Summary.xlsx`), `results/comparisons/simulation_vs_hardware/sim_vs_rpi_comparison.xlsx` (identical to `05_Raspberry_Pi_HIL_vs_Simulation.xlsx`), and `results/raw_data/simulation/ml_thermal_test_predictions.csv` (identical to `fig13_ml_thermal_regression.csv`).
