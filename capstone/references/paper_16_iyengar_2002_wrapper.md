# Base Reference Paper Summary - 2D SoC Wrapper Design & TAM Optimization

**Title**: Test Wrapper Design and TAM Optimization for System-on-Chip (SoC) Test Scheduling  
**Authors**: Vikram Iyengar, Krishnendu Chakrabarty, and Erik Jan Marinissen  
**Journal**: *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD)*, Vol. 21, No. 5, pp. 537–549, May 2002.  

---

## 1. Key Objectives & Contributions
- Seminal paper establishing the formal mathematical formulation of **IEEE 1500 Wrapper Design** for embedded IP cores in 2D System-on-Chip (SoC) testing.
- Formulates wrapper scan chain balancing as a variant of the **Bin Packing Problem** to optimize wrapper scan lengths ($s_{\text{max}}$) for a given TAM width allocation $w$.
- Combines wrapper design with TAM bandwidth allocation and multi-constraint test scheduling under continuous peak power constraints ($P_{\text{max}}$).

## 2. Core Mathematical Formulation

### Pre-Wrapper / Unbalanced Raw Test Time
Without wrapper scan chain optimization, test vectors $N_v$ are shifted through un-balanced internal scan chains of total length $L_{\text{scan}}$:
$$T_{\text{pre\_wrapper}} = N_v \cdot L_{\text{scan}}$$

### Post-Wrapper Pareto-Optimal Test Time (IEEE 1500 Standard)
Given an allocated TAM width $w$, internal scan inputs ($S_{\text{in}}$) and scan outputs ($S_{\text{out}}$) are partitioned into $w$ balanced wrapper chains:
$$s(w) = \max\left( \left\lceil \frac{\sum S_{\text{in}}}{w} \right\rceil, \left\lceil \frac{\sum S_{\text{out}}}{w} \right\rceil \right)$$
$$T_{\text{post\_wrapper}}(w) = \left(1 + \left\lceil \frac{N_v}{w} \right\rceil\right) \cdot s(w) + N_v$$

## 3. Capstone Project Integration
- Serves as the **Primary Base Reference Paper** for the 2D SoC Test Scheduling Framework (`2d/`).
- Directly implemented in `2d/src/models/wrapper_design_2d.py` to compare pre-wrapper vs post-wrapper test times across TAM widths ($W_{\text{max}} = 16, 24, 32, 40, 48, 56, 64$).
