# Reference Paper 13 Summary

**Title**: A Metaheuristic Optimization Approach for Through-Silicon Via (TSV) Test Scheduling in 3D Integrated Circuits  
**Authors**: A. Verma and R. Kumar  
**Journal**: *Integration, the VLSI Journal*, Vol. 95, p. 105670, Mar. 2024.  

---

## 1. Key Objectives & Contributions
- Formulates TSV bandwidth allocation as a primary constraint in 3D IC test scheduling.
- Classifies TSV defect profiles:
  1. **Open Faults**: Discontinuities causing loss of test signal integrity.
  2. **Short Faults**: Isolation breakdowns leading to signal bridging between vertical vias.
  3. **Delay Faults**: High resistance causing signal propagation lags across die boundaries.
- Uses metaheuristic optimization to bound total concurrent vertical TSV line allocation ($TSV_{\text{max}}$).

## 2. Capstone Integration
- Directly modeled in `TSVBus` and `Core3D.tsv_required` in `src/models/soc_3d.py`.
