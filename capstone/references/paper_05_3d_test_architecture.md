# Reference Paper 5 Summary

**Title**: Test Architecture Design and Optimization for Three-Dimensional SoCs  
**Authors**: Li Jiang, Lin Huang, and Qiang Xu  

---

## 1. Key Objectives & Contributions
- Seminal paper on test architecture design for 3D multi-die stacked SoCs.
- Introduces TAM distribution architectures for stacked dies interconnected by Through-Silicon Vias (TSVs).
- Formulates vertical test access strategies:
  1. Base die TAM controller routing data to upper die layers.
  2. TSV channel allocation & vertical pin multiplexing.
- Analyzes wrapper design options under IEEE 1500 for 3D integrated circuits.

## 2. Structural Models & Insights
- Vertical TSVs incur routing overhead and area penalties; thus, $TSV_{\text{max}}$ must be strictly budgeted.
- Higher die layers (Die 1, Die 2) depend on vertical TSV channels to communicate with the base test interface on Die 0.

## 3. Capstone Integration
- Provided the architectural basis for `TSVBus` and vertical layer indexing ($z \in \{0, 1, 2\}$) in `src/models/soc_3d.py`.
