"""
tests/test_vlsi_constraints.py
==============================
Unit tests for VLSI Electronic & Computer Architecture Constraint Engines (2D & 3D).
"""

import math
import pytest
from src.constraints.vlsi_constraints import (
    calculate_wrapper_test_time,
    calculate_instantaneous_power,
    calculate_active_tsv_count,
    calculate_junction_temperature,
    verify_all_vlsi_constraints,
    PEAK_POWER_LIMITS,
    TSV_BANDWIDTH_LIMITS,
    AMBIENT_TEMP_KELVIN,
    MAX_TEMP_LIMIT_KELVIN,
    MAX_TEMP_LIMIT_CELSIUS
)
from src.constraints.vlsi_constraints_2d import (
    calculate_unwrapped_test_time,
    calculate_ieee1500_wrapper_test_time,
    calculate_instantaneous_power_2d,
    verify_2d_vlsi_constraints
)


class TestVLSIConstraints2D:
    def test_unwrapped_test_time(self):
        # T_raw = N_v * total_scan_elements
        assert calculate_unwrapped_test_time(100, 20) == 2000
        assert calculate_unwrapped_test_time(500, 0) == 500  # max(0, 1)

    def test_ieee1500_wrapper_test_time(self):
        # N_v = 300, S_in = 10, S_out = 10, w = 4
        # s_in = ceil(10/4) = 3, s_out = ceil(10/4) = 3, max_s = 3
        # T = (1 + ceil(300/4)) * 3 + 300 = (1 + 75) * 3 + 300 = 76 * 3 + 300 = 528
        expected = (1 + math.ceil(300 / 4)) * 3 + 300
        assert calculate_ieee1500_wrapper_test_time(300, 10, 10, 4) == expected

    def test_instantaneous_power_2d(self):
        powers = [3.5, 4.2, 5.1]
        assert pytest.approx(calculate_instantaneous_power_2d(powers), 0.01) == 12.8

    def test_verify_2d_vlsi_constraints_safe(self):
        is_safe, status = verify_2d_vlsi_constraints(
            peak_power=40.0, max_power=45.89, max_tam_used=16, max_tam_width=16
        )
        assert is_safe is True
        assert status == "Safe"

    def test_verify_2d_vlsi_constraints_violated(self):
        is_safe, status = verify_2d_vlsi_constraints(
            peak_power=50.0, max_power=45.89, max_tam_used=24, max_tam_width=16
        )
        assert is_safe is False
        assert "VIOLATED" in status
        assert "Peak Power" in status
        assert "TAM Width" in status


class TestVLSIConstraints3D:
    def test_calculate_wrapper_test_time(self):
        # test_vectors=1000, scan_chains=20, tam_width=8
        # T = (1 + ceil(1000/8)) * 20 + 1000 = (1 + 125) * 20 + 1000 = 126 * 20 + 1000 = 3520
        assert calculate_wrapper_test_time(1000, 20, 8) == 3520

    def test_instantaneous_power_3d(self):
        powers = [10.5, 12.0, 8.4]
        assert pytest.approx(calculate_instantaneous_power(powers), 0.01) == 30.9

    def test_tsv_utilization_calculation(self):
        # Base die (layer 0) requires 0 vertical TSVs; upper dies (layer > 0) require tam_width TSVs
        active_layer_tams = [
            (0, 8),  # Layer 0 (Base) -> 0 TSVs
            (1, 8),  # Layer 1 -> 8 TSVs
            (2, 16)  # Layer 2 -> 16 TSVs
        ]
        assert calculate_active_tsv_count(active_layer_tams) == 24

    def test_calculate_junction_temperature_normal(self):
        layer_powers = [10.0, 8.0, 6.0]
        max_k, max_c, is_hotspot = calculate_junction_temperature(layer_powers, coupling_penalty=0.0)
        assert max_k > AMBIENT_TEMP_KELVIN
        assert pytest.approx(max_c, 0.1) == (max_k - 273.15)
        assert is_hotspot is False

    def test_calculate_junction_temperature_hotspot_violation(self):
        # High power inducing thermal spike > 95°C (368.15K)
        layer_powers = [120.0, 100.0, 90.0]
        max_k, max_c, is_hotspot = calculate_junction_temperature(layer_powers, coupling_penalty=20.0)
        assert max_c > MAX_TEMP_LIMIT_CELSIUS
        assert is_hotspot is True

    def test_verify_all_vlsi_constraints_safe(self):
        is_safe, status = verify_all_vlsi_constraints(
            peak_power=40.0, max_power=45.89,
            peak_temp_celsius=65.0, max_temp_celsius=95.0,
            max_tsv_used=16, max_tsv_bandwidth=16
        )
        assert is_safe is True
        assert status == "Safe"

    def test_verify_all_vlsi_constraints_violations(self):
        is_safe, status = verify_all_vlsi_constraints(
            peak_power=50.0, max_power=45.89,
            peak_temp_celsius=98.5, max_temp_celsius=95.0,
            max_tsv_used=20, max_tsv_bandwidth=16
        )
        assert is_safe is False
        assert "VIOLATED" in status
        assert "Power" in status
        assert "Junction Temp" in status
        assert "TSV" in status
