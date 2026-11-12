# 3D SoC Test Scheduling Framework - System Breakdown & Execution Workflow

This document provides a comprehensive, step-by-step breakdown of how the **3D System-on-Chip (SoC) Test Scheduling Framework** works internally across software optimization, constraint enforcement, and hardware-in-the-loop validation.

---

## 1. High-Level Architectural Flow

```
[ ITC'02 Benchmarks (d695, p22810) ]
                 │
                 ▼
[ IEEE 1500 Wrapper Design & TAM Allocation ]
                 │
                 ▼
[ 3D Structural Partitioning (Fixed Layer Mapping vs Random Stacking) ]
                 │
                 ▼
[ Multi-Constraint Verification (TAM, Power, TSV, Thermal Checkpoints) ]
                 │
                 ▼
[ 3D Metaheuristic Search Suite (Greedy, ABC, Bat, Firefly, MACO, H-MACO-FA) ]
                 │
                 ▼
[ ML Predictive Thermal Estimation & Frequency Scaling (Roy & Giri, 2022) ]
                 │
                 ▼
[ Physical Schedule Replay & Hardware-in-the-Loop (Raspberry Pi 4 / HIL Tester Bridge) ]
                 │
                 ▼
[ Performance Visualizations & Paper-Aligned Output Tables (Roy & Giri, 2023) ]
```

---

## 2. Step-by-Step System Breakdown

### Step 1: Input Data Preparation & Wrapper Design
1. The framework reads standard **ITC'02 benchmark profiles** (`d695` and `p22810`). Each embedded IP core has specified test vector counts ($N_v$), internal scan chain counts ($S_{\text{in}}, S_{\text{out}}$), and power dissipation ratings ($P_i$).
2. Adhering to the **IEEE 1500 Wrapper Standard**, scan chains are balanced to compute test duration $T_i(w)$ as a function of allocated TAM width $w$:
   $$T_i(w) = (1 + \lceil N_v / w \rceil) \cdot \max(S_{\text{in}}, S_{\text{out}}) + N_v$$

### Step 2: 3D Multi-Layer Die Stacking Partitioning
1. **Random Stacking Baseline (`base_random_stacking/`)**: Cores are dynamically or randomly mapped across 3 die layers ($z=0, 1, 2$).
2. **Structured Fixed Stacking (`structured_fixed_stacking/`)**: Cores are assigned to immutable die layers according to literature structural partitioning (Table 2 from Roy & Giri, 2023):
   - **Layer 1 (Bottom, $z=0$)**: Cores `1, 2, 3, 5, 6, 8, 9, 15, 21, 26, 27` (for `p22810`).
   - **Layer 2 (Middle, $z=1$)**: Cores `4, 7, 10, 11, 17, 18, 22, 23, 25, 28`.
   - **Layer 3 (Top, $z=2$)**: Cores `12, 13, 14, 16, 19, 20, 24, 29, 30`.

### Step 3: Strict Continuous Interval Concurrency Enforcement
1. During schedule construction, when an algorithm evaluates placing a core at candidate start time $st$ (running to $st + T_i$), `SoC3D.is_placement_valid` collects all event checkpoints $cp \in [st, st + T_i)$ where active task sets can change.
2. At every checkpoint $cp$, it validates:
   - **TAM Constraint**: $\sum_{c \in \text{Active}(cp)} W_c \le W_{\text{max}}$
   - **Peak Power Constraint**: $\sum_{c \in \text{Active}(cp)} P_c \le P_{\text{max}}$
   - **TSV Constraint**: $\sum_{c \in \text{Active}(cp), z_c > 0} W_c \le TSV_{\text{max}}$
   - **Thermal Constraint**: $T_j(cp) \le 95.0^\circ\text{C}$
3. Placements are accepted ONLY if 100% of interval checkpoints satisfy all 4 VLSI constraints.

### Step 4: Swarm Intelligence Metaheuristics Search
- **Greedy 3D**: LPT (Longest Processing Time) baseline.
- **ABC 3D (Artificial Bee Colony)**: Employed, Onlooker, and Scout bee search phases exploring core sequence permutations.
- **Bat 3D (Bat Algorithm)**: Microbat echolocation with frequency tuning ($f_i$), velocity vectors ($v_i$), loudness decay ($A_i$), and pulse rates ($r_i$).
- **Firefly 3D (Firefly Algorithm)**: Flashing attraction vectors based on inverse makespan brightness.
- **MACO 3D (Modified Ant Colony Optimization)**: Pheromone matrix ($\tau_{ij}$), heuristic visibility ($\eta_{ij}$), and **Dynamic Ant Population Scaling** to prevent premature convergence.
- **H-MACO-FA 3D (Hybrid MACO-Firefly)**: Combines global MACO pheromone construction with Firefly attractiveness local refinement.

### Step 5: Machine Learning Predictive Thermal Estimation & Frequency Scaling
1. `PredictiveThermalEstimator` forecasts transient junction temperature spikes $\hat{T}_j(t + \Delta t)$ over a lookahead window.
2. If predicted $T_j$ threatens safe thermal budgets ($>85.0^\circ\text{C}$), `FrequencyScaledScheduler` dynamically scales test clock frequencies (0.8x / 0.5x throttling) or inserts cooling pauses to maintain thermal integrity.

### Step 6: Hardware-in-the-Loop (HIL) Validation on Raspberry Pi 4 (and Legacy Mock Mode)
1. `RaspberryPi5Tester` (legacy class name; wraps the shared TCP/SSH HIL bridge used with **Raspberry Pi 4 Model B Rev 1.4**) receives the optimized 3D test schedule and translates task execution into sequential GPIO pin toggles and clock pulse signals.
2. Measures pin setup overhead, physical transmission lag, and calculates empirical **Hardware Overhead Percentage**:
   $$\text{Overhead}_{\%} = \frac{T_{\text{wall\_clock}} - T_{\text{pure\_ideal}}}{T_{\text{pure\_ideal}}} \times 100\%$$

### Step 7: Output Table & Visual Dashboard Generation
- Exports multi-TAM benchmark results ($W_{\text{max}} = 16, 24, 32, 40, 48, 56, 64$) matching Roy & Giri (2023) sample paper format.
- Generates 3D Gantt Charts, Die Thermal Heatmaps, and Peak Power/TSV dashboards in `results/`.
