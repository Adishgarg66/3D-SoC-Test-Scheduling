"""
tests/test_wrapper_design.py
============================
Unit tests for IEEE 1500 Test Wrapper Design & Scan Chain Balancer (Iyengar et al., 2002).
"""

import pytest
from src.models.soc_2d import ITC02BenchmarkLoader2D
from src.models.wrapper_design_2d import CoreWrapperProfile2D, WrapperAnalyzer2D


class TestIEEE1500WrapperDesign:
    def test_core_wrapper_profile_pre_vs_post(self):
        core = CoreWrapperProfile2D(
            core_id=1, name="c17", test_vectors=300, scan_inputs=10, scan_outputs=10, power=3.50
        )
        pre_time = core.get_pre_wrapper_test_time()
        # Raw = 300 * (10 + 10) = 6000 cycles
        assert pre_time == 6000

        # Post-wrapper with TAM w=4
        post_time_w4 = core.get_post_wrapper_test_time(tam_width=4)
        assert post_time_w4 < pre_time
        assert post_time_w4 == 528

        # Post-wrapper with TAM w=8
        post_time_w8 = core.get_post_wrapper_test_time(tam_width=8)
        assert post_time_w8 <= post_time_w4

    def test_d695_wrapper_reduction_monotonicity(self):
        profiles = ITC02BenchmarkLoader2D.get_wrapper_profiles_d695()
        analyzer = WrapperAnalyzer2D(profiles)
        tam_widths = [16, 24, 32, 40, 48, 56, 64]
        table = analyzer.compute_wrapper_reduction_table(tam_widths)

        assert len(table) == len(tam_widths)
        for i in range(len(table) - 1):
            curr_row = table[i]
            next_row = table[i + 1]
            # Higher TAM width must yield equal or lower post-wrapper cycles
            assert next_row["post_wrapper_cycles"] <= curr_row["post_wrapper_cycles"]
            # Cycles saved should be strictly positive
            assert curr_row["cycles_saved"] > 0
            # Reduction percentage should exceed 95%
            assert curr_row["reduction_pct"] > 95.0

    def test_p22810_wrapper_reduction_table(self):
        profiles = ITC02BenchmarkLoader2D.get_wrapper_profiles_p22810()
        assert len(profiles) == 30
        analyzer = WrapperAnalyzer2D(profiles)
        table = analyzer.compute_wrapper_reduction_table([16, 32, 64])

        assert len(table) == 3
        assert table[0]["tam_width"] == 16
        assert table[1]["tam_width"] == 32
        assert table[2]["tam_width"] == 64
        assert table[2]["post_wrapper_cycles"] < table[0]["post_wrapper_cycles"]
