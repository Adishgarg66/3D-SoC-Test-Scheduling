"""
src/constraints/vlsi_constraints.py
===================================
Standalone VLSI Electronic & Computer Architecture Constraints Module.

Centralizes all operational budgets, physical constants, mathematical formulas,
and threshold limits for 3D System-on-Chip (SoC) Test Scheduling:
1. TAM Width Constraints (W_max)
2. Peak Power Budget Constraints (P_max)
3. Vertical TSV Interconnect Bandwidth Limits (TSV_max)
4. Spatial-Temporal Thermal Limits (T_max / Junction Temp Tj)
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple


# ============================================================================
# 1. TAM (TEST ACCESS MECHANISM) PARAMETERS & FORMULAS (IEEE 1500 Standard)
# ============================================================================
# Global TAM width sweep configurations matching literature standard (Roy & Giri, 2023)
STANDARD_TAM_SWEEP: List[int] = [16, 24, 32, 40, 48, 56, 64]

def calculate_wrapper_test_time(test_vectors: int, scan_chains: int, tam_width: int) -> int:
    """
    IEEE 1500 Wrapper Test Time Formula for an embedded core:
    T(w) = (1 + ceil(N_v / w)) * max(S_in, S_out) + N_v
    
    where:
    - N_v: Number of test vectors
    - w: Allocated TAM width slice
    - S_in, S_out: Internal scan chain lengths
    """
    scan_length = max(scan_chains, 1)
    return int((1 + math.ceil(test_vectors / max(tam_width, 1))) * scan_length + test_vectors)


# ============================================================================
# 2. POWER BUDGET PARAMETERS & FORMULAS
# ============================================================================
# Benchmark Peak Power Limits (P_max in Watts)
PEAK_POWER_LIMITS: Dict[str, float] = {
    "d695": 45.89,    # ITC'02 d695 continuous power ceiling (Watts)
    "p22810": 94.05,  # ITC'02 p22810 continuous power ceiling (Watts)
    "default": 50.0   # General 3D SoC continuous power ceiling (Watts)
}

def calculate_instantaneous_power(active_powers: List[float]) -> float:
    """
    Instantaneous Power Dissipation Formula at time step t:
    P(t) = Sum_{i in Active(t)} P_i
    
    Constraint: P(t) <= P_max  forall t in [0, TAT]
    """
    return float(sum(active_powers))


# ============================================================================
# 3. TSV (THROUGH-SILICON VIA) INTERCONNECT PARAMETERS & FORMULAS
# ============================================================================
# Maximum allowable active vertical TSV channels between dies
TSV_BANDWIDTH_LIMITS: Dict[str, int] = {
    "d695": 16,       # d695 vertical TSV channel budget
    "p22810": 24,     # p22810 post-bond TSV channel budget
    "p22810_full": 80 # High-density 3D TSV bus limit (Roy & Giri, 2023)
}

def calculate_active_tsv_count(active_layer_tams: List[Tuple[int, int]]) -> int:
    """
    Vertical TSV Utilization Formula at time step t:
    TSV_active(t) = Sum_{c in Active(t), z_c > 0} W_c
    
    Constraint: TSV_active(t) <= TSV_max  forall t in [0, TAT]
    Note: Base die (Layer 1 / z=0) cores connect directly to test pads;
    upper die cores (Layer 2 & 3 / z > 0) require vertical TSV routing.
    """
    return sum(tam_width for layer_id, tam_width in active_layer_tams if layer_id > 0)


# ============================================================================
# 4. THERMAL & JUNCTION TEMPERATURE (Tj) PARAMETERS & RC FORMULAS
# ============================================================================
AMBIENT_TEMP_KELVIN: float = 300.15   # 27°C baseline ambient temperature
MAX_TEMP_LIMIT_KELVIN: float = 368.15 # 95°C maximum allowable junction temperature (T_max)
MAX_TEMP_LIMIT_CELSIUS: float = 95.0   # 95°C threshold in Celsius

# Thermal resistance per layer (K/W) - Die 0 (bottom) closest to heatsink has lowest Rth
LAYER_THERMAL_RESISTANCE: List[float] = [0.35, 0.50, 0.65] # Layer 1, Layer 2, Layer 3

def calculate_junction_temperature(
    layer_powers: List[float],
    coupling_penalty: float = 0.0
) -> Tuple[float, float, bool]:
    """
    Spatial-Temporal Dynamic Thermal RC Model Formula:
    T_j(z) = T_ambient + R_th(z) * P_effective(z) + Penalty_coupling
    
    Returns:
    - max_tj_kelvin: Peak junction temperature in Kelvin
    - max_tj_celsius: Peak junction temperature in Celsius
    - is_hotspot: True if peak Tj exceeds T_max threshold
    """
    accumulated_heat = 0.0
    max_tj_k = AMBIENT_TEMP_KELVIN

    num_layers = len(layer_powers)
    for z in range(num_layers - 1, -1, -1):
        r_th = LAYER_THERMAL_RESISTANCE[z] if z < len(LAYER_THERMAL_RESISTANCE) else 0.5
        eff_power = layer_powers[z] + accumulated_heat
        t_layer = AMBIENT_TEMP_KELVIN + r_th * eff_power
        if t_layer > max_tj_k:
            max_tj_k = t_layer
        accumulated_heat += layer_powers[z] * 0.75

    max_tj_k += coupling_penalty
    max_tj_c = max_tj_k - 273.15
    is_hotspot = max_tj_k > MAX_TEMP_LIMIT_KELVIN

    return max_tj_k, max_tj_c, is_hotspot


# ============================================================================
# 5. EMPIRICAL CONSTRAINT VERIFICATION FUNCTION
# ============================================================================
def verify_all_vlsi_constraints(
    peak_power: float, max_power: float,
    peak_temp_celsius: float, max_temp_celsius: float,
    max_tsv_used: int, max_tsv_bandwidth: int
) -> Tuple[bool, str]:
    """
    Truthful Empirical Constraint Verification Engine:
    Validates power, thermal, and TSV limits against empirical execution traces.
    """
    violations = []
    if peak_power > max_power + 1e-3:
        violations.append(f"Peak Power ({peak_power:.2f}W > {max_power:.2f}W)")
    if peak_temp_celsius > max_temp_celsius + 1e-3:
        violations.append(f"Junction Temp ({peak_temp_celsius:.1f}°C > {max_temp_celsius:.1f}°C)")
    if max_tsv_used > max_tsv_bandwidth:
        violations.append(f"TSV Bandwidth ({max_tsv_used} > {max_tsv_bandwidth})")

    if not violations:
        return True, "Safe"
    else:
        return False, "VIOLATED (" + ", ".join(violations) + ")"
