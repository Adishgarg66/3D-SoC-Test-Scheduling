# Fixed 3D SoC Layer Stacking Structural Partitioning Table

This document defines the **Fixed Multi-Layer Die Stacking Structure** for 3D System-on-Chip (SoC) architectures as requested by the mentor and aligned with literature standard (Table 2 from *Test Architecture Optimization for Post-bond Test and Pre-bond Tests of 3D SoCs Using TAM Reuse*, Roy & Giri, 2023).

---

## 1. Distribution of Cores Among Die Layers

In the structured fixed stacking model (`structured_fixed_stacking/`), embedded cores are assigned to immutable physical die layers in a 3-die vertical stack:
- **Layer 1 (Bottom Layer / $z=0$)**: Attached directly to substrate and heat sink. Receives external test stimuli directly from test pads (0 vertical TSVs needed).
- **Layer 2 (Middle Layer / $z=1$)**: Positioned between Layer 1 and Layer 3. Routes test data vertically via TSVs.
- **Layer 3 (Top Layer / $z=2$)**: Uppermost active die layer farthest from heat sink. Highest thermal resistance ($R_{\text{th}} = 0.65\text{ K/W}$) and requires vertical TSVs.

---

## 2. Core Distribution Mapping Table

| Layer No. (Bottom 1, Top 3) | ITC'02 `p22810` Core Assignments (30 Cores) | ITC'02 `d695` Core Assignments (10 Cores) |
| :--- | :--- | :--- |
| **Layer 1 (Bottom, Heatsink)** | Cores `1, 2, 3, 5, 6, 8, 9, 15, 21, 26, 27` (11 cores) | Cores `1, 2, 7, 10` (4 cores) |
| **Layer 2 (Middle Layer)** | Cores `4, 7, 10, 11, 17, 18, 22, 23, 25, 28` (10 cores) | Cores `3, 4, 8` (3 cores) |
| **Layer 3 (Top Die Layer)** | Cores `12, 13, 14, 16, 19, 20, 24, 29, 30` (9 cores) | Cores `5, 6, 9` (3 cores) |

---

## 3. Structural Parameters Comparison

| Parameter | `p22810` Fixed Structure | `d695` Fixed Structure |
| :--- | :--- | :--- |
| **Total Embedded Cores** | 30 Modules | 10 Modules |
| **Active Die Tiers** | 3 Vertical Layers | 3 Vertical Layers |
| **Layer 1 Cores / Power Ratio** | 11 Cores (~36.7% Core Ratio) | 4 Cores (~40.0% Core Ratio) |
| **Layer 2 Cores / Power Ratio** | 10 Cores (~33.3% Core Ratio) | 3 Cores (~30.0% Core Ratio) |
| **Layer 3 Cores / Power Ratio** | 9 Cores (~30.0% Core Ratio) | 3 Cores (~30.0% Core Ratio) |
| **TSV Interconnect Channel Budget** | $TSV_{\text{max}} = 24$ (or $80$) | $TSV_{\text{max}} = 16$ |
| **Peak Power Budget** | $P_{\text{max}} = 94.05\text{ W}$ | $P_{\text{max}} = 45.89\text{ W}$ |
| **Thermal Threshold** | $T_{\text{max}} = 95.0^\circ\text{C}$ ($368.15\text{ K}$) | $T_{\text{max}} = 95.0^\circ\text{C}$ ($368.15\text{ K}$) |
