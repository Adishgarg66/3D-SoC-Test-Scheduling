# Reference Paper 7 Summary

**Title**: Minimization of Test Time in System on Chip Using Artificial Intelligence-Based Test Scheduling Techniques  
**Authors**: Gokul Chandrasekaran, Sakthivel Periyasamy, and Karthikeyan Panjappagounder Rajamanickam  

---

## 1. Key Objectives & Contributions
- Explores Artificial Intelligence (AI) and Metaheuristic Search algorithms for minimizing SoC test application time.
- Compares traditional rule-based greedy algorithms against swarm intelligence heuristics (ACO, ABC, Firefly).
- Highlights that AI-guided schedule construction bypasses local minima trapdoors and finds near-optimal makespans.

## 2. Benchmark Findings
- Evaluated on ITC'02 benchmarks (`d695` and `p22810`).
- Demonstrated that metaheuristics achieve 15% to 36% TAT savings over static LPT greedy algorithms.

## 3. Capstone Integration
- Guided our comparative evaluation setup in `experiments/evaluate_3d.py`.
