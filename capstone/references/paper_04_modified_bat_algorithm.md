# Reference Paper 4 Summary

**Title**: Test Scheduling and Test Time Minimization of System-on-Chip Using Modified BAT Algorithm  
**Authors**: A. K. Singh and S. K. Singh  
**Journal**: *IEEE Transactions on Very Large Scale Integration (VLSI) Systems*, Vol. 30, No. 8, pp. 1152–1165, Aug. 2022.  

---

## 1. Key Objectives & Contributions
- Proposes a **Modified Bat Algorithm (MBA)** for SoC test scheduling.
- Leverages microbat echolocation dynamics with variable pulse emission frequencies ($f_i$), velocity update vectors ($v_i$), and adaptive loudness decay ($A_i$).
- Incorporates local random walks near global best candidates to avoid local minima trapdoors in multi-constrained packing space.

## 2. Mathematical Equations
- **Frequency Update**:
  $$f_i = f_{\text{min}} + (f_{\text{max}} - f_{\text{min}}) \cdot \beta$$
- **Velocity & Position Update**:
  $$v_i^{(t)} = v_i^{(t-1)} + (x_i^{(t-1)} - x_*) \cdot f_i$$
  $$x_i^{(t)} = x_i^{(t-1)} + v_i^{(t)}$$
- **Loudness & Pulse Rate Adaptation**:
  $$A_i^{(t+1)} = \alpha A_i^{(t)}, \quad r_i^{(t+1)} = r_i^{(0)} \cdot [1 - e^{-\gamma t}]$$

## 3. Capstone Integration
- Directly implemented in `src/algorithms/bat_3d.py`.
