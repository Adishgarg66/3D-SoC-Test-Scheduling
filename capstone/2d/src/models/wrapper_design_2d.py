"""
2d/src/models/wrapper_design_2d.py
===================================
IEEE 1500 Wrapper Design & Scan Chain Balancer Engine.
Base Reference Paper: Iyengar, Chakrabarty, & Marinissen (IEEE TCAD 2002) [Paper 16].

Calculates pareto-optimal wrapper configurations and provides pre-wrapper vs post-wrapper
test time comparison across varying TAM width allocations (16 to 64).
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple
from src.constraints.vlsi_constraints_2d import (
    calculate_unwrapped_test_time,
    calculate_ieee1500_wrapper_test_time
)


@dataclass
class CoreWrapperProfile2D:
    """Core Profile with Pre-Wrapper and IEEE 1500 Post-Wrapper Attributes."""
    core_id: int
    name: str
    test_vectors: int
    scan_inputs: int
    scan_outputs: int
    power: float

    def get_pre_wrapper_test_time(self) -> int:
        """Pre-wrapper raw test time without scan chain balancing."""
        return calculate_unwrapped_test_time(self.test_vectors, self.scan_inputs + self.scan_outputs)

    def get_post_wrapper_test_time(self, tam_width: int) -> int:
        """Post-wrapper IEEE 1500 pareto-optimal balanced test time for allocated TAM width w."""
        return calculate_ieee1500_wrapper_test_time(self.test_vectors, self.scan_inputs, self.scan_outputs, tam_width)


class WrapperAnalyzer2D:
    """Evaluates and compares pre-wrapper vs post-wrapper test cycle metrics."""
    def __init__(self, cores: List[CoreWrapperProfile2D]):
        self.cores = cores

    def compute_wrapper_reduction_table(self, tam_widths: List[int] = [16, 24, 32, 40, 48, 56, 64]) -> List[Dict]:
        """
        Computes pre-wrapper vs post-wrapper test cycle comparisons across TAM widths.
        """
        table_data = []
        raw_total = sum(c.get_pre_wrapper_test_time() for c in self.cores)

        for w in tam_widths:
            # Post-wrapper total test cycles assuming parallel TAM partitioning
            wrapper_total = sum(c.get_post_wrapper_test_time(w) for c in self.cores)
            reduction_pct = ((raw_total - wrapper_total) / raw_total * 100.0) if raw_total > 0 else 0.0

            table_data.append({
                "tam_width": w,
                "raw_test_cycles": raw_total,
                "post_wrapper_cycles": wrapper_total,
                "cycles_saved": raw_total - wrapper_total,
                "reduction_pct": round(reduction_pct, 2)
            })

        return table_data
