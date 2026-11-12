# Reference Paper 6 Summary

**Title**: Thermal-Aware Task Scheduling for 3D-Network-on-Chip: A Bottom-to-Top Scheme  
**Authors**: Y. Cui, W. Zhang, V. Chaturvedi, W. Liu, and B. He  

---

## 1. Key Objectives & Contributions
- Proposes a **Bottom-to-Top (B2T)** thermal-aware scheduling scheme for 3D Network-on-Chip (3D NoC) architectures.
- Recognizes that 3D stacking drastically reduces the surface-to-volume ratio, trapping heat in middle and upper die layers.
- Shows that heat generated in upper layers accumulates down through lower layers toward the bottom substrate/heatsink.

## 2. Thermal Formulation & Rules
- **Layer Thermal Resistance ($R_{\text{th}}$)** increases with distance from the bottom heatsink:
  $$T_j(z) = T_{\text{ambient}} + R_{\text{th}}(z) \cdot P_{\text{effective}}(z)$$
- Bottom-to-Top Rule: High-power cores are preferentially assigned to bottom layers (Die 0) closer to the heatsink to lower peak junction temperature ($T_j$).

## 3. Capstone Integration
- Directly modeled in `ThermalModel` inside `src/models/soc_3d.py` and incorporated into MACO 3D heuristic visibility ($\eta$).
