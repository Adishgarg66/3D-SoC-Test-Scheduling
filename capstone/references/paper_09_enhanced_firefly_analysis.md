# Reference Paper 9 Summary

**Title**: Test Scheduling and Test Time Reduction for SoC by Using Enhanced Firefly Algorithm (Parameter Analysis)  
**Authors**: Gokul Chandrasekaran, Gopinath Singaram, Rajkumar Duraisamy, Akash Sanjay Ghodake, and Parthiban Kunnathur Ganesan  
**Journal**: *Revue d'Intelligence Artificielle*, Vol. 35, No. 3, pp. 235–241, Jun. 2021.  

---

## 1. Parameter Analysis & Tuning
- Investigates the impact of algorithmic parameters on convergence speed:
  - **Initial Attractiveness ($\beta_0 = 1.0$)**: Ensures strong attraction toward brighter solutions.
  - **Light Absorption Coefficient ($\gamma = 0.2$)**: Controls light attenuation across solution space.
  - **Randomization Parameter ($\alpha = 0.25$)**: Prevents stagnation by providing exploratory perturbation.

## 2. Benchmark Validation & Runtime Trade-Offs
- Shows that while metaheuristics require a few seconds of software compile time, they save tens of thousands of physical hardware test cycles in IC production.

## 3. Capstone Integration
- Parameters ($\beta_0=1.0, \gamma=0.2, \alpha=0.25$) configured in `src/algorithms/firefly_3d.py`.
