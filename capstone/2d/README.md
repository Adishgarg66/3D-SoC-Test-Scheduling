# 2D System-on-Chip (SoC) Test Scheduling Framework

The **2D System-on-Chip (SoC) Test Scheduling Framework** serves as the initial 2D baseline in our capstone project **"Development of Test Solution for 3D SoC"**. It establishes the core wrapper design, TAM width allocation, continuous peak power budgeting, and metaheuristic search algorithms on a single planar die before extending constraints to 3D stacked ICs.

---

## 1. Base Reference Papers

1. **Primary Base Paper for 2D IEEE 1500 Wrapper Design & Test Time Equations**:
   > V. Iyengar, K. Chakrabarty, and E. J. Marinissen, *"Test Wrapper Design and TAM Optimization for System-on-Chip (SoC) Test Scheduling"*, **IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD)**, Vol. 21, No. 5, pp. 537–549, May 2002.
   - *Reference Summary*: [references/paper_16_iyengar_2002_wrapper.md](../references/paper_16_iyengar_2002_wrapper.md)

2. **Primary Reference Paper for 2D Swarm Optimization Algorithms**:
   > G. Chandrasekaran, G. Singaram, R. Duraisamy, A. S. Ghodake, and P. K. Ganesan, *"Test Scheduling and Test Time Reduction for SoC by Using Enhanced Firefly Algorithm"*, **Revue d'Intelligence Artificielle**, Vol. 35, No. 3, pp. 235–241, Jun. 2021.
   - *Reference Summary*: [references/paper_01_enhanced_firefly.md](../references/paper_01_enhanced_firefly.md)

---

## 2. Pre-Wrapper vs IEEE 1500 Post-Wrapper Test Time Equations

### Pre-Wrapper Raw Test Time
Without wrapper scan chain optimization, test vectors $N_v$ are shifted sequentially through un-balanced scan chains of total length $L_{\text{scan}}$:
$$T_{\text{pre\_wrapper}} = N_v \cdot L_{\text{scan}}$$

### Post-Wrapper Pareto-Optimal Test Time (Iyengar et al., IEEE TCAD 2002)
Using the **IEEE 1500 Standard**, internal scan chains $S_{\text{in}}$ and $S_{\text{out}}$ are partitioned into $w$ balanced wrapper chains:
$$s(w) = \max\left( \left\lceil \frac{\sum S_{\text{in}}}{w} \right\rceil, \left\lceil \frac{\sum S_{\text{out}}}{w} \right\rceil \right)$$
$$T_{\text{post\_wrapper}}(w) = \left(1 + \left\lceil \frac{N_v}{w} \right\rceil\right) \cdot s(w) + N_v$$

---

## 3. Directory Layout

```
2d/
├── src/
│   ├── constraints/
│   │   └── vlsi_constraints_2d.py  # 2D VLSI constraints (TAM, Power, IEEE 1500)
│   ├── models/
│   │   ├── soc_2d.py               # 2D SoC Core Data Model & Benchmark Loaders
│   │   └── wrapper_design_2d.py    # IEEE 1500 Wrapper Design & Scan Chain Balancer
│   ├── algorithms/
│   │   ├── greedy_2d.py            # 2D LPT Greedy Baseline Scheduler
│   │   ├── abc_2d.py               # 2D Artificial Bee Colony (ABC 2D)
│   │   ├── bat_2d.py               # 2D Bat Algorithm (Bat 2D)
│   │   ├── firefly_2d.py           # 2D Firefly Algorithm (Firefly 2D)
│   │   ├── maco_2d.py              # 2D Modified Ant Colony Optimization (MACO 2D)
│   │   └── hmaco_fa_2d.py          # 2D Hybrid MACO-Firefly (H-MACO-FA 2D)
│   └── hardware/
│       └── rpi_tester_2d.py        # 2D Hardware-in-the-Loop RPi 4 / HIL Tester Bridge
├── experiments/
│   ├── evaluate_2d.py              # Main 2D multi-algorithm evaluation runner
│   └── wrapper_comparison_2d.py    # Post-wrapper vs Pre-wrapper test time analysis
├── results/                        # Output Gantt charts, power profiles & wrapper tables
└── README.md                       # Documentation & Reference Citations
```

---

## 4. Execution Commands

```bash
# 1. Run IEEE 1500 Post-Wrapper vs Pre-Wrapper Test Time Comparison
python 2d/experiments/wrapper_comparison_2d.py

# 2. Run 2D Test Scheduling Benchmark Suite across all 6 algorithms
python 2d/experiments/evaluate_2d.py
```
