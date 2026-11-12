# Reference Paper 8 Summary

**Title**: An Empirical Investigation of Metaheuristic and Heuristic Algorithms for a 2D Packing Problem  
**Authors**: E. Hopper and B. C. H. Turton  
**Journal**: *European Journal of Operational Research*, Vol. 128, No. 1, pp. 34–57, 2001.  

---

## 1. Key Objectives & Contributions
- Classic foundational paper modeling resource allocation as a **2D Rectangle Bin-Packing Problem**.
- Maps core test scheduling into 2D rectangle packing:
  - **Rectangle Width**: TAM width allocation ($w_i$).
  - **Rectangle Height**: Test execution cycles ($T_i$).
  - **Bin Width**: Total SoC TAM pin budget ($W_{\text{max}}$).
  - **Bin Height**: Total Test Application Time (TAT / Makespan).

## 2. Mathematical Model
- Objective:
  $$\min \text{TAT} = \min \left( \max_{i} (S_i + T_i) \right)$$
- Subject to non-overlapping TAM width constraints:
  $$\sum_{i \in \text{Active}(t)} w_i \le W_{\text{max}}, \quad \forall t$$

## 3. Capstone Integration
- Provides the fundamental 2D bin-packing formulation extended to 3D multi-layer stack packing in `src/models/soc_3d.py`.
