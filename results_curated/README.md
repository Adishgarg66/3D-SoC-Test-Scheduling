# Curated & Complete Capstone Results Archive (`results_curated/`)

> **Non-Destructive Organization Guarantee:** This folder (`results_curated/`) was created alongside the original `results/` and `capstone/*/results/` directories without deleting, moving, or altering any original project files, scripts, notebooks, or test suite targets.

This archive collects **every unique genuine visual, architecture/workflow diagram, hardware GPIO log, statistical table, and workbook** generated across the entire **2D & 3D SoC Test Scheduling Capstone Project** (`d695` & `p22810` ITC'02 benchmarks; IEEE 1500 wrapper; 6 algorithms including `H-MACO-FA`; fair `--max-evals 300` evaluation budget; 10 random seeds; ML thermal prediction & dynamic frequency scaling; and live physical Hardware-in-the-Loop replay on **Raspberry Pi 4 Model B Rev 1.4**).

See [`figure_index.md`](./figure_index.md) for the item-by-item table of all **62 unique PNG figures & diagrams** with exact resolutions, companion CSV files, descriptions, and original source locations.

---

## Directory Tree & Contents Summary

```text
results_curated/
├── 2D_Simulation/
│   ├── Graphs/                    # Fig 02 IEEE 1500 wrapper plot, notebook session power, 2D CSVs & XLSX
│   ├── Gantt_Charts/              # Figs 03–04, standalone 2D Gantts, & notebook per-session Gantt grids
│   └── Algorithm_Comparisons/     # Fig 01 (10-seed Mean±Std), standalone 2D dashboards, notebook dashboard, XLSX
├── Fixed_3D_Simulation/
│   ├── Graphs/                    # Figs 06–07, standalone fixed 3D dashboards, partitioning CSVs, XLSX & MD
│   ├── Gantt_Charts/              # Fig 09 & standalone fixed 3D layer-coded Gantt charts (d695 & p22810)
│   ├── Thermal_Heatmaps/          # Fig 08 & standalone fixed 3D 3-layer spatial thermal heatmaps
│   └── Power_TSV_TAM_Profiles/    # Fig 05 post-bond TAM sweep (W=16..64) & Roy-Giri format CSV tables
├── Random_3D_Simulation/
│   ├── Graphs/                    # Fig 10, standalone H-MACO-FA & legacy dashboards, notebook 3D cuboids & bars
│   ├── Gantt_Charts/              # Standalone random 3D Gantt charts (d695 & p22810)
│   ├── Thermal_Heatmaps/          # Fig 11 & standalone 3-layer random 3D thermal heatmaps + scaling CSV
│   └── Power_TSV_TAM_Profiles/    # Notebook Power vs TAM utilization plots (d695 & p22810)
├── Raspberry_Pi_Hardware/
│   ├── GPIO_Execution/            # All 18 live physical RPi 4 trial JSON event logs + HIL summary CSVs
│   ├── Hardware_Logs/             # RPi ping verification JSON + mode-wise/consolidated hardware timing CSVs
│   └── Hardware_Graphs/           # Figs 14–15 (sequential RPi 4 GPIO wall-clock & per-core event timings)
├── Simulation_vs_Hardware/
│   ├── Comparison_Graphs/         # Figs 16–17 (Sim vs physical RPi 4 overhead; 2D vs Fixed 3D vs Random 3D)
│   └── Comparison_Tables/         # sim_vs_rpi_comparison.csv & 05_Raspberry_Pi_HIL_vs_Simulation.xlsx
├── Statistical_Analysis/
│   ├── Multi_Seed_Graphs/         # Figs 18–20, 10-seed raw runs CSV (360 records), summary CSV & XLSX
│   └── Algorithm_Comparisons/     # Fig 12 anytime convergence curves, convergence CSV, & ranking overview CSV
├── ML_Thermal_Prediction/
│   ├── Prediction_Graphs/         # Fig 13 (Polynomial Ridge d=2 held-out scatter & residuals) + CSV
│   └── Error_Analysis/            # Deduplicated split metrics, unseen trajectory validation CSVs, & XLSX
├── Architecture_and_Methodology/
│   ├── System_Architecture/       # Fig 3.2/3.4 blocks, Mermaid arch spec, formulation docs, MidTerm + 5 ref PDFs
│   ├── Workflow_Diagrams/         # Fig 1.1, Fig 3.1, Figs 3.6–3.8 algorithm flowcharts, & system breakdown MD
│   └── Block_Diagrams/            # Fig 3.3 TAM bus distribution & Fig 3.5 3D stack hotspot cross-section
├── Presentation_Ready/
│   ├── Best_Graphs/               # 13 highest-impact 300 DPI thesis/viva PNG figures
│   ├── Best_Diagrams/             # 6 high-res architecture/workflow block PNGs + Mermaid & breakdown MDs
│   └── Important_Tables/          # Master_Capstone_Complete_Report.xlsx + key CSVs, XLSXs & key_findings.md
├── README.md
└── figure_index.md
```

---

## Important Methodological & Provenance Distinctions

1. **Fair-Budget Suite (`fig01`–`fig20`) vs. Standalone Runners (`capstone/*/results/`) vs. Early Notebook Plots**:
   - **`fig01`–`fig20`** were generated programmatically from uniform `10`-seed experiments under the shared `--max-evals 300` evaluation cap (`Greedy` runs once as deterministic LPT baseline = `1` evaluation; all `5` stochastic metaheuristics run `300` schedule evaluations).
   - **`capstone/{2d,fixed_stacking,random_stacking,results}/`** preserve distinct single-run CLI and standalone runner dashboards, frequency-scaled comparisons, and per-benchmark `d695` Fixed 3D Gantt/Thermal outputs.
   - **Notebook (`nb_*`) outputs** capture Phase-1 2D session power charts, stacked session Gantts, and 3D cuboid visualizations directly extracted from `soc_scheduling_improved_.(1).ipynb`.

2. **Physical Hardware Platform (`Raspberry Pi 4 Model B Rev 1.4`)**:
   - All `18` `hil_*.json` files in `Raspberry_Pi_Hardware/GPIO_Execution/` and `rpi_ping_verification.json` record genuine `RPi.GPIO` executions (`Debian GNU/Linux 13 (trixie)`, `is_physical_hardware = True`) on the connected **Raspberry Pi 4 Model B Rev 1.4**.
   - As documented in `Presentation_Ready/Important_Tables/key_findings.md` and `fig14`–`fig16`, simulated SoC schedules pack non-conflicting cores **concurrently** (`makespan < sum of core durations`), whereas the physical Raspberry Pi HIL tester replays scheduled tasks **sequentially** on GPIO pins (`wall_clock ≈ cumulative_task_cycles × time_scale + OS/GPIO jitter`, <0.7% userspace overhead).
   - Historical diagrams (`diagram_01`, `diagram_02`) extracted verbatim from the earlier MidTerm PDF text read "Raspberry Pi 5"; final physical validation was executed on the **Raspberry Pi 4 Model B Rev 1.4**.

3. **Zero Byte-Duplicate Guarantee**:
   - Exact SHA-256 byte duplicates across folders (`capstone/results/{gantt_*,thermal_heatmap_*}`, duplicate CSV/XLSX exports, and lower-res plain-styled notebook subsets) were deduplicated inside the primary folders and logged in [`figure_index.md`](./figure_index.md).
   - Same-name files with different pixel resolutions or experimental runs (e.g., `capstone/results/dashboard_*.png` vs `capstone/random_stacking/results/dashboard_*.png`) were both retained using descriptive filenames.
