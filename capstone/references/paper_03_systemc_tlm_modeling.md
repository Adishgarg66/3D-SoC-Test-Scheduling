# Reference Paper 3 Summary

**Title**: Using SystemC TLM Modeling To Solve AI Data Movement Challenges  
**Authors**: K. Sharma and V. Gupta  
**Publisher/Source**: *SemiEngineering*, Mar. 2026.  

---

## 1. Key Objectives & Contributions
- Explores Transaction-Level Modeling (TLM) using SystemC for high-speed inter-die communication in AI hardware accelerators and multi-die SoCs.
- Addresses data movement bottlenecks, channel latency, and bus contention in 3D stacked memories and processing arrays.

## 2. Technical Findings
- High-level abstract modeling enables fast performance estimation of interconnect throughput and latency prior to RTL synthesis.
- Transaction-level abstraction reduces simulation time by up to $100\times$ compared to cycle-accurate pin-level simulations.

## 3. Capstone Integration
- Concepts of high-level transaction modeling inspired our cycle-accurate event-driven test schedule replay and pin transmission simulator in `src/hardware/rpi_tester.py`.
