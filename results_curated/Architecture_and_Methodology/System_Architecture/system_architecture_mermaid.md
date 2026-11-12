# System Architecture Mermaid Diagram (Verbatim from Root README.md)

## 3. System Architecture & Workflow

The architecture connects core parsing, wrapper optimization, constraint validation, metaheuristic scheduling, thermal lookahead, and reporting:

```mermaid
flowchart TD
    A["ITC'02 SoC Benchmark (d695 / p22810)"] --> B["IEEE 1500 Wrapper Design Engine"]
    B --> C["Core Pre-Processing & Test Time Calculation"]
    C --> D{"Execution Mode Selection"}
    
    D -->|"Mode: 2D Planar"| E["2D Planar Concurrency Manager"]
    D -->|"Mode: Fixed 3D"| F["Structured 3D Fixed Stacker (Roy & Giri, 2022)"]
    D -->|"Mode: Random 3D"| G["Dynamic 3D Random Stacker"]

    E --> H["Metaheuristic Optimization Schedulers\n(Greedy, ABC, Bat, Firefly, MACO, H-MACO-FA)\nFair Budget (--max-evals) & Multi-Seed (--seeds)"]
    F --> H
    G --> H

    H --> I["Multi-Constraint Physical Verification\n- TAM Width: Sum(W_c) <= W_max\n- Peak Power: Sum(P_c) <= P_max\n- TSV Bandwidth: Sum(W_c, z>0) <= TSV_max\n- Junction Temp: Tj(z) <= T_max (95°C)"]
    
    I --> J{"Thermal Hotspot Check"}
    J -->|"Tj > 85°C / 92°C"| K["3D RC / ML Ridge Thermal Estimator &\nDynamic Frequency Scaling (0.8x / 0.6x)"]
    K --> L["Final Validated Test Schedule"]
    J -->|"Safe"| L

    L --> M["Hardware-in-the-Loop (HIL) Tester\n(Physical Raspberry Pi 4B Rev 1.4 / Safe Mock Fallback)"]
    L --> N["Dynamic Reporting & Results Package\n- Genuine OpenXML Workbooks (.xlsx)\n- Statistical CSV Tables & Raw Logs\n- 20 Publication Plots & Thermal Heatmaps"]
```

