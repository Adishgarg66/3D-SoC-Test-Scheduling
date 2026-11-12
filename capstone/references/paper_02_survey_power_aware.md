# Reference Paper 2 Summary

**Title**: Survey on Power-Aware Test Scheduling and Scan Chain Optimization in SoC Testing  
**Authors**: P. Kumar and R. Singh  
**Journal**: *International Journal of Advanced Research in Computer Science*, Vol. 16, No. 4, pp. 80–87, Aug. 2025.  

---

## 1. Key Objectives & Contributions
- Provides a comprehensive survey of power-aware test scheduling techniques and scan chain balancing for SoC designs.
- Categorizes power constraints into:
  - **Peak Test Power ($P_{\text{max}}$)**: Structural hardware limit to prevent IR drop and permanent gate breakdown.
  - **Average Test Power ($P_{\text{avg}}$)**: Thermal energy dissipation budget over time.
- Emphasizes the trade-off between TAM bandwidth allocation, wrapper chain balancing (IEEE 1500), and test session parallelism.

## 2. Key Insights & Formulations
- **Continuous Power Constraint**:
  $$\sum_{i \in \text{Active}(t)} P_i \le P_{\text{max}}, \quad \forall t \in [0, \text{TAT}]$$
- **Scan Chain Length Balancing**:
  $$S_i = \max(S_{\text{in}}, S_{\text{out}}), \quad T_i(w) = (1 + \lceil N_v / w \rceil) \cdot S_i + N_v$$
  where $N_v$ is test vector count, $w$ is TAM width slice.

## 3. Capstone Integration
- Provided exact peak power budget specs used in our 3D SoC model:
  - $P_{\text{max}} = 45.89\text{ W}$ for `d695`
  - $P_{\text{max}} = 94.05\text{ W}$ for `p22810`
- Integrated into `src/models/soc_3d.py` in `validate_concurrency`.
