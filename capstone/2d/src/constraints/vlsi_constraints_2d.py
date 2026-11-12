"""
2d/src/constraints/vlsi_constraints_2d.py
=========================================
2D Planar VLSI Electronic & Computer Architecture Constraints Module.
Base Reference Paper: Iyengar, Chakrabarty, & Marinissen (IEEE TCAD 2002) [Paper 16].

Centralizes 2D operational budgets, physical parameters, and mathematical formulas:
1. TAM Width Constraints (W_max)
2. Continuous Peak Power Budget Constraints (P_max)
3. IEEE 1500 Wrapper Scan Chain Balancing & Test Time Formulas
"""

import math
from typing import List, Dict, Tuple


# Standard TAM Width Sweep matching 2D literature baseline
STANDARD_TAM_SWEEP_2D: List[int] = [16, 24, 32, 40, 48, 56, 64]

# Peak Power Budgets for 2D Planar Benchmarks (P_max in Watts)
PEAK_POWER_LIMITS_2D: Dict[str, float] = {
    "d695": 45.89,    # ITC'02 d695 continuous power ceiling (Watts)
    "p22810": 94.05,  # ITC'02 p22810 continuous power ceiling (Watts)
    "default": 50.0   # General 2D SoC continuous power ceiling (Watts)
}


def calculate_unwrapped_test_time(test_vectors: int, total_scan_elements: int) -> int:
    """
    Un-wrapped / Raw Test Time Formula (Pre-Wrapper Baseline):
    T_raw = N_v * Total_Scan_Elements
    """
    return test_vectors * max(total_scan_elements, 1)


def calculate_ieee1500_wrapper_test_time(test_vectors: int, scan_inputs: int, scan_outputs: int, tam_width: int) -> int:
    """
    IEEE 1500 Pareto-Optimal Post-Wrapper Test Time Formula (Iyengar et al., IEEE TCAD 2002):
    s(w) = max( ceil(Sum S_in / w), ceil(Sum S_out / w) )
    T_wrapper(w) = (1 + ceil(N_v / w)) * s(w) + N_v
    
    where:
    - N_v: Number of test vectors
    - w: Allocated TAM width slice
    - s(w): Max wrapper scan chain length
    """
    w = max(tam_width, 1)
    s_in = math.ceil(max(scan_inputs, 1) / w)
    s_out = math.ceil(max(scan_outputs, 1) / w)
    max_scan_length = max(s_in, s_out, 1)
    
    return int((1 + math.ceil(test_vectors / w)) * max_scan_length + test_vectors)


def calculate_instantaneous_power_2d(active_powers: List[float]) -> float:
    """
    Instantaneous 2D Planar Power Dissipation:
    P_2d(t) = Sum_{i in Active(t)} P_i
    
    Constraint: P_2d(t) <= P_max  forall t in [0, TAT]
    """
    return float(sum(active_powers))


def verify_2d_vlsi_constraints(
    peak_power: float, max_power: float,
    max_tam_used: int, max_tam_width: int
) -> Tuple[bool, str]:
    """
    Empirical 2D Constraint Verification Engine:
    Validates power and TAM width budgets against 2D planar execution traces.
    """
    violations = []
    if peak_power > max_power + 1e-3:
        violations.append(f"Peak Power ({peak_power:.2f}W > {max_power:.2f}W)")
    if max_tam_used > max_tam_width:
        violations.append(f"TAM Width ({max_tam_used} > {max_tam_width})")

    if not violations:
        return True, "Safe"
    else:
        return False, "VIOLATED (" + ", ".join(violations) + ")"
