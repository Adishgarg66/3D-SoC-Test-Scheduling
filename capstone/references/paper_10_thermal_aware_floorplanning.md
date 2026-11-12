# Reference Paper 10 Summary

**Title**: Thermal-Aware Test Scheduling and Floor Planning for Three-Dimensional Stacked Integrated Circuits  
**Authors**: N. S. M. Shah et al.  
**Journal**: *Journal of Engineering and Technology*, Vol. 15, No. 2, pp. 203–218, Dec. 2024.  

---

## 1. Key Objectives & Contributions
- Combines test scheduling with spatial floorplanning to mitigate thermal hotspots in 3D stacked ICs.
- Introduces spatial-temporal thermal decoupling:
  - Systematically distributes high-power test vectors across non-adjacent vertical layers ($z$) and distinct time frames ($t$).
  - Evaluates spatial distance ($d_{xy}$) between concurrent high-power cores on stacked dies.

## 2. Mathematical Hotspot Penalty
- Hotspot penalty formulation for vertically stacked cores:
  $$\text{Penalty}_{\text{hotspot}} = \sum_{c_1, c_2} \mathbb{I}(|z_1 - z_2| = 1 \text{ and } d_{xy} < d_{\text{threshold}}) \cdot (P_1 \cdot P_2) \cdot \alpha_{\text{thermal}}$$

## 3. Capstone Integration
- Directly integrated into `ThermalModel.estimate_temperature_profile` in `src/models/soc_3d.py`.
