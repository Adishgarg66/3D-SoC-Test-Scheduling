# VLSI System Parameters, Formulations, and Derivations

This document provides an explicit reference for all physical parameters, mathematical formulas, threshold definitions, and operational derivations used in the **3D System-on-Chip (SoC) Test Scheduling & Optimization Framework**.

---

## 1. Test Access Mechanism (TAM) Width ($W_{\text{max}}$)

### Definition & Role
The **Test Access Mechanism (TAM)** is the physical bus network that routes test vectors from external tester pins down through internal scan chains and returns test responses.
- **Global TAM Width ($W_{\text{max}}$)**: The maximum allowable bit-width capacity allocated across the entire chip.
- **Evaluated TAM Range**: $W_{\text{max}} \in \{16, 24, 32, 40, 48, 56, 64\}$ bits/channels (following Roy & Giri, 2023 literature standard).

### Mathematical Constraint Formula
At any execution time step $t$, the cumulative sum of TAM widths assigned to all concurrently active test sessions must fit within $W_{\text{max}}$:
$$\sum_{i \in \text{Active}(t)} W_i \le W_{\text{max}}, \quad \forall t \in [0, \text{TAT}]$$

---

## 2. Peak Power Budget ($P_{\text{max}}$)

### Definition & Derivation
Continuous power consumption during testing can exceed normal functional power limits because scan chains toggle at high rates simultaneously.
- **Peak Power Threshold ($P_{\text{max}}$)**: Structural continuous power budget defined to prevent excessive IR drop, structural gate breakdown, and thermal runaways.
- **Benchmark Derivations**:
  - **`d695` Benchmark**: Total module power = $76.48\text{ W}$; safe continuous budget set to $P_{\text{max}} = 45.89\text{ W}$ (~60% of total module power sum).
  - **`p22810` Benchmark**: Total module power = $156.75\text{ W}$; safe continuous budget set to $P_{\text{max}} = 94.05\text{ W}$ (~60% of total module power sum).

### Mathematical Power Calculation Formula
At any time instance $t$:
$$P(t) = \sum_{i \in \text{Active}(t)} P_i \le P_{\text{max}}, \quad \forall t \in [0, \text{TAT}]$$
where $P_i$ is the peak test power rating of embedded core $c_i$.

---

## 3. Through-Silicon Via (TSV) Interconnect Bandwidth ($TSV_{\text{max}}$)

### Definition & Role
In a 3D stacked SoC, vertical interconnect micro-vias (**TSVs**) connect stacked dies (Die 1, Die 2, Die 3).
- Cores on the **Bottom Die (Layer 1 / $z=0$)** connect directly to primary test pads (0 vertical TSVs required).
- Cores on **Upper Dies (Layer 2 & 3 / $z > 0$)** route test data vertically through TSV channels.
- **TSV Bandwidth Limit ($TSV_{\text{max}}$)**: Maximum allowable active vertical TSV channels ($TSV_{\text{max}} = 16$ for `d695`, $TSV_{\text{max}} = 24$ or $80$ for `p22810`).

### Mathematical TSV Calculation Formula
$$TSV_{\text{active}}(t) = \sum_{c_i \in \text{Active}(t), z_i > 0} W_i \le TSV_{\text{max}}, \quad \forall t \in [0, \text{TAT}]$$

---

## 4. Dynamic Spatial-Temporal Thermal Model ($T_j$)

### Definition & Hotspot Mitigation
3D stacking traps thermal energy in inner layers (Die 2 / Die 3).
- **Ambient Baseline**: $T_{\text{ambient}} = 300.15\text{ K}$ ($27^\circ\text{C}$).
- **Maximum Temperature Threshold ($T_{\text{max}}$)**: $368.15\text{ K}$ ($95^\circ\text{C}$).
- **Layer Thermal Resistance ($R_{\text{th}}$)**:
  - Layer 1 (Bottom, Heatsink): $R_{\text{th}}(0) = 0.35\text{ K/W}$
  - Layer 2 (Middle): $R_{\text{th}}(1) = 0.50\text{ K/W}$
  - Layer 3 (Top): $R_{\text{th}}(2) = 0.65\text{ K/W}$

### Thermal Formula Derivation
$$T_j(z) = T_{\text{ambient}} + R_{\text{th}}(z) \cdot P_{\text{effective}}(z) + \text{Penalty}_{\text{hotspot}}$$
$$P_{\text{effective}}(z) = P_{\text{layer}}(z) + 0.75 \cdot \sum_{k > z} P_{\text{layer}}(k)$$
$$\text{Penalty}_{\text{hotspot}} = \sum_{c_1, c_2 \in \text{Active}(t)} \mathbb{I}(|z_1 - z_2| = 1 \text{ and } d_{xy} < 0.35) \cdot (P_1 \cdot P_2) \cdot 0.12$$
$$\text{Constraint}: \max_{z,x,y} T_j(z,x,y,t) \le T_{\text{max}} = 95.0^\circ\text{C}$$

---

## 5. Summary Table of Parameters

| Parameter Symbol | Physical Description | Units | `d695` Value | `p22810` Value | Formula / Standard |
| :---: | :--- | :---: | :---: | :---: | :--- |
| $W_{\text{max}}$ | Total SoC TAM Width | Bits | 16–64 | 16–64 | IEEE 1500 Bus Allocation |
| $P_{\text{max}}$ | Peak Power Budget | Watts | 45.89 W | 94.05 W | $P(t) = \sum_{Active} P_i \le P_{\text{max}}$ |
| $TSV_{\text{max}}$ | Max Vertical TSV Bandwidth | Lines | 16 | 24 / 80 | $TSV(t) = \sum_{z > 0} W_i \le TSV_{\text{max}}$ |
| $T_{\text{max}}$ | Max Junction Temp Limit | °C / K | 95.0°C (368.15K) | 95.0°C (368.15K) | Dynamic RC Thermal Model |
| $T_{\text{ambient}}$| Ambient Baseline Temp | °C / K | 27.0°C (300.15K) | 27.0°C (300.15K) | Physical Baseline |
| $R_{\text{th}}$ | Layer Thermal Resistance | K/W | [0.35, 0.50, 0.65] | [0.35, 0.50, 0.65] | Heatsink Conduction Stack |
