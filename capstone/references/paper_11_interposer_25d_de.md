# Reference Paper 11 Summary

**Title**: Test-Path Scheduling for Interposer-Based 2.5D Integrated Circuits Using an Orthogonal Learning-Based Differential Evolution Algorithm  
**Authors**: Y. Zhang et al.  
**Journal**: *Mathematics*, Vol. 13, No. 16, p. 2679, Aug. 2023.  

---

## 1. Key Objectives & Contributions
- Focuses on test-path scheduling and routing channel allocation for 2.5D interposer-based multi-chip modules (MCMs).
- Uses Orthogonal Learning Differential Evolution (OLDE) to optimize interposer trace allocation and minimize test access latency.

## 2. Key Insights
- Interposer micro-bumps and routing channels present strict bandwidth limits similar to vertical TSVs in 3D stacks.
- Orthogonal design matrices enhance population diversity in metaheuristic search.

## 3. Capstone Integration
- Supported the routing bandwidth constraint formulation used in `TSVBus` (`src/models/soc_3d.py`).
