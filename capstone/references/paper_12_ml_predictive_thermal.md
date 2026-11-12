# Reference Paper 12 Summary

**Title**: Machine Learning-Based Predictive Thermal Estimation and Frequency-Scaled Test Scheduling for 3D ICs  
**Authors**: S. Roy and P. Giri  
**Journal**: *Computers & Electrical Engineering*, Vol. 101, p. 108065, Jul. 2022.  

---

## 1. Key Objectives & Contributions
- Proposes a machine learning-based framework for dynamic predictive thermal estimation ($T_j$) during 3D IC testing.
- Uses ML regression models to predict transient junction temperature spikes before they occur based on active core sequences.
- Implements **Frequency-Scaled Test Scheduling**: dynamically scales test clock frequencies ($f_{\text{test}}$) or inserts thermal cooling pauses when predicted $T_j$ breaches safe thresholds.

## 2. Mathematical & Machine Learning Formulation
- **Predictive Model**:
  $$\hat{T}_j(t + \Delta t) = f_{\text{ML}}\left( \mathbf{P}_{\text{active}}(t), \mathbf{Z}_{\text{layers}}(t), T_j(t) \right)$$
- **Frequency Scaling**:
  $$f_{\text{test}}(t) = f_{\text{base}} \cdot \min\left(1.0, \frac{T_{\text{threshold}} - T_{\text{amb}}}{\hat{T}_j(t + \Delta t) - T_{\text{amb}}}\right)$$

## 3. Capstone Integration
- Directly implemented in `src/models/predictive_thermal.py` as the dynamic predictive thermal estimator and frequency scaling engine.
