# Reference Paper 14 Summary

**Title**: Constraint-Driven Test Scheduling in 3D Stacked ICs via Swarm Optimization Techniques  
**Authors**: L. Zheng and Q. Xu  
**Journal**: *ACM Transactions on Design Automation of Electronic Systems*, Vol. 29, No. 4, pp. 1–22, Jul. 2024.  

---

## 1. Key Objectives & Contributions
- Presents a swarm intelligence framework for multi-constrained test scheduling in 3D stacked ICs.
- Introduces **Dynamic Worker Scaling** in Ant Colony Optimization (MACO):
  - Solves the stagnation problem of standard ACO by adjusting ant population dynamically based on unscheduled core count.

## 2. Mathematical Formulation
- **Dynamic Ant Scaling**:
  $$N_{\text{ants}}(t) = N_{\text{base}} \cdot \left(1.0 + \gamma \cdot \sin\left(\pi \frac{t}{T_{\text{max}}}\right)\right)$$
- **Pheromone Reinforcement**:
  $$\tau_{ij}^{(t+1)} = (1 - \rho)\tau_{ij}^{(t)} + \frac{Q}{\text{Makespan}_{\text{best}}}$$

## 3. Capstone Integration
- Directly implemented in `MACO3DScheduler` (`src/algorithms/maco_3d.py`).
