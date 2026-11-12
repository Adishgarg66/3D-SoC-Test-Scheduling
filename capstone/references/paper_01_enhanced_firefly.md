# Reference Paper 1 Summary

**Title**: Test Scheduling and Test Time Reduction for SoC by Using Enhanced Firefly Algorithm  
**Authors**: Gokul Chandrasekaran, Gopinath Singaram, Rajkumar Duraisamy, Akash Sanjay Ghodake, and Parthiban Kunnathur Ganesan  
**Journal**: *Revue d'Intelligence Artificielle*, Vol. 35, No. 3, pp. 235–241, Jun. 2021.  

---

## 1. Key Objectives & Contributions
- Proposes an **Enhanced Firefly Algorithm (EFA)** specifically tailored for System-on-Chip (SoC) test scheduling.
- Aims to minimize Total Test Application Time (TAT / Makespan) under peak power constraints ($P_{\text{max}}$) and Test Access Mechanism (TAM) width constraints ($W_{\text{max}}$).
- Introduces an adaptive absorption coefficient ($\gamma$) and dynamic random walk step size ($\alpha$) to prevent premature convergence to local optima.

## 2. Mathematical Formulation
- **Light Attractiveness Equation**:
  $$\beta(r) = \beta_0 \cdot e^{-\gamma r^2}$$
- **Firefly Movement Vector**:
  $$x_i^{(t+1)} = x_i^{(t)} + \beta_0 e^{-\gamma r_{ij}^2} (x_j^{(t)} - x_i^{(t)}) + \alpha_t \cdot \epsilon_i$$
- **Fitness Evaluation**:
  $$\text{Fitness}(x_i) = \frac{1}{\text{Makespan}(x_i) + \lambda \cdot \max(0, P_{\text{peak}} - P_{\text{max}})}$$

## 3. Data Extracted & Relevance to Capstone
- **Benchmark Data**: Uses ITC'02 benchmarks (`d695` and `p22810`).
- **Results Baseline**: Achieved up to 36% TAT reduction on `d695` and ~15% on `p22810` compared to traditional LPT Greedy scheduling.
- **Capstone Integration**: Directly forms the foundation of `src/algorithms/firefly_3d.py`.
