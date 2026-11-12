# Reference Paper 15 Summary

**Title**: Hardware-in-the-Loop Validation for Dynamic Thermal-Aware VLSI Testing Architectures  
**Authors**: S. Patel and M. Desai  
**Journal**: *IEEE Transactions on Instrumentation and Measurement*, Vol. 74, pp. 1–12, Jan. 2025.  

---

## 1. Key Objectives & Contributions
- Proposes a **Hardware-in-the-Loop (HIL)** validation framework bridging software scheduling algorithms with physical hardware testers.
- Validates theoretical software schedules under real-world physical constraints:
  - Hardware pin toggling delays over Test Access Mechanisms (TAM).
  - Physical transmission overhead and latency jitter.
  - Verification of power and thermal profiles on physical FPGA/Microcontroller hardware (e.g. Raspberry Pi).

## 2. Metric Formulations
- **Hardware Overhead Percentage**:
  $$\text{Overhead}_{\%} = \frac{T_{\text{wall\_clock}} - T_{\text{pure\_ideal}}}{T_{\text{pure\_ideal}}} \times 100\%$$

## 3. Capstone Integration
- Directly implemented in `src/hardware/rpi_tester.py` (`RaspberryPi5Tester`).
