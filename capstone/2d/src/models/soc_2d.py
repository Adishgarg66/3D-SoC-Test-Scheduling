"""
2d/src/models/soc_2d.py
======================
2D Planar System-on-Chip (SoC) Model & Benchmark Data Loaders.
Base Reference Paper: Iyengar, Chakrabarty, & Marinissen (IEEE TCAD 2002) [Paper 16].
2D Metaheuristics Reference Paper: Chandrasekaran et al. (Revue d'Intelligence Artificielle 2021) [Paper 1].
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np

from src.constraints.vlsi_constraints_2d import (
    PEAK_POWER_LIMITS_2D,
    calculate_instantaneous_power_2d,
    verify_2d_vlsi_constraints
)
from src.models.wrapper_design_2d import CoreWrapperProfile2D


@dataclass
class Core2D:
    """Represents an embedded IP core on a 2D planar die."""
    core_id: int
    name: str
    test_cycles: int
    power: float
    tam_width: int
    grid_x: float = 0.5
    grid_y: float = 0.5


@dataclass
class ScheduledTask2D:
    """Scheduled task representation in 2D execution space."""
    core_id: int
    core_name: str
    start_time: int
    end_time: int
    duration: int
    power: float
    tam_width: int
    grid_x: float
    grid_y: float


@dataclass
class ScheduleResult2D:
    """Output summary of a 2D test schedule."""
    algorithm_name: str
    makespan: int
    tasks: List[ScheduledTask2D]
    power_profile: List[float]
    tam_profile: List[int]
    peak_power: float
    max_tam_used: int
    constraint_status: str = "Safe"
    eval_count: int = 0
    runtime_sec: float = 0.0


class SoC2D:
    """Main 2D Planar SoC System Container."""
    def __init__(
        self,
        name: str,
        cores: List[Core2D],
        max_tam_width: int = 32,
        max_power: float = 50.0
    ):
        self.name = name
        self.cores = cores
        self.max_tam_width = max_tam_width
        self.max_power = max_power

    def validate_concurrency(self, active_cores: List[Core2D]) -> Tuple[bool, str]:
        total_tam = sum(c.tam_width for c in active_cores)
        if total_tam > self.max_tam_width:
            return False, f"TAM Exceeded: {total_tam} > {self.max_tam_width}"

        total_power = calculate_instantaneous_power_2d([c.power for c in active_cores])
        if total_power > self.max_power:
            return False, f"Power Exceeded: {total_power:.2f}W > {self.max_power:.2f}W"

        return True, "Valid"

    def is_placement_valid(self, scheduled_tasks, candidate_core: Core2D, st: int) -> bool:
        et = st + candidate_core.test_cycles

        overlapping = [t for t in scheduled_tasks if max(st, t.start_time) < min(et, t.end_time)]
        if not overlapping:
            valid, _ = self.validate_concurrency([candidate_core])
            return valid

        checkpoints = set([st])
        for t in overlapping:
            if st < t.start_time < et:
                checkpoints.add(t.start_time)

        for cp in checkpoints:
            active_at_cp = [t for t in overlapping if t.start_time <= cp < t.end_time]
            active_cores = [
                Core2D(
                    core_id=t.core_id, name=t.core_name, test_cycles=t.duration,
                    power=t.power, tam_width=t.tam_width, grid_x=t.grid_x, grid_y=t.grid_y
                ) for t in active_at_cp
            ]
            active_cores.append(candidate_core)

            valid, _ = self.validate_concurrency(active_cores)
            if not valid:
                return False

        return True


class ITC02BenchmarkLoader2D:
    """Benchmark loader for 2D Planar ITC'02 circuits."""
    @staticmethod
    def load_d695_2d(max_tam_width: int = 16, max_power: float = 45.89) -> SoC2D:
        raw_cores = [
            (1, "c17", 12000, 3.50, 4, 0.2, 0.2),
            (2, "c432", 18500, 4.20, 4, 0.7, 0.3),
            (3, "c499", 24000, 5.10, 4, 0.3, 0.6),
            (4, "c880", 31000, 6.80, 8, 0.8, 0.7),
            (5, "c1355", 28000, 7.50, 8, 0.2, 0.8),
            (6, "c1908", 45000, 9.20, 8, 0.7, 0.2),
            (7, "c2670", 52000, 10.40, 8, 0.5, 0.5),
            (8, "c3540", 64000, 11.80, 8, 0.4, 0.4),
            (9, "c5315", 85000, 13.50, 16, 0.5, 0.8),
            (10, "c7552", 110000, 14.80, 16, 0.8, 0.8),
        ]

        cores = []
        for cid, name, cycles, power, tam, gx, gy in raw_cores:
            tam_width = min(tam, max_tam_width)
            cores.append(Core2D(
                core_id=cid, name=name, test_cycles=cycles,
                power=power, tam_width=tam_width, grid_x=gx, grid_y=gy
            ))

        return SoC2D(name="ITC02_d695_2D", cores=cores, max_tam_width=max_tam_width, max_power=max_power)

    @staticmethod
    def load_p22810_2d(max_tam_width: int = 32, max_power: float = 94.05) -> SoC2D:
        np.random.seed(42)
        cores = []
        base_cycles = [8000, 12000, 15000, 22000, 29000, 35000, 42000, 50000, 61000, 75000]

        for i in range(1, 31):
            cycles = int(base_cycles[(i-1) % 10] * (1.0 + 0.15 * (i // 10)))
            power = round(2.5 + (i * 0.45), 2)
            tam_width = min(8 if (i % 3 != 0) else 16, max_tam_width)
            gx = round(float(np.random.uniform(0.1, 0.9)), 2)
            gy = round(float(np.random.uniform(0.1, 0.9)), 2)

            cores.append(Core2D(
                core_id=i, name=f"p22810_mod_{i}", test_cycles=cycles,
                power=power, tam_width=tam_width, grid_x=gx, grid_y=gy
            ))

        return SoC2D(name="ITC02_p22810_2D", cores=cores, max_tam_width=max_tam_width, max_power=max_power)

    @staticmethod
    def get_wrapper_profiles_d695() -> List[CoreWrapperProfile2D]:
        """Returns CoreWrapperProfile2D list for d695 wrapper analysis."""
        return [
            CoreWrapperProfile2D(1, "c17", test_vectors=300, scan_inputs=10, scan_outputs=10, power=3.50),
            CoreWrapperProfile2D(2, "c432", test_vectors=400, scan_inputs=15, scan_outputs=15, power=4.20),
            CoreWrapperProfile2D(3, "c499", test_vectors=500, scan_inputs=18, scan_outputs=18, power=5.10),
            CoreWrapperProfile2D(4, "c880", test_vectors=600, scan_inputs=25, scan_outputs=25, power=6.80),
            CoreWrapperProfile2D(5, "c1355", test_vectors=550, scan_inputs=22, scan_outputs=22, power=7.50),
            CoreWrapperProfile2D(6, "c1908", test_vectors=750, scan_inputs=30, scan_outputs=30, power=9.20),
            CoreWrapperProfile2D(7, "c2670", test_vectors=800, scan_inputs=35, scan_outputs=35, power=10.40),
            CoreWrapperProfile2D(8, "c3540", test_vectors=900, scan_inputs=40, scan_outputs=40, power=11.80),
            CoreWrapperProfile2D(9, "c5315", test_vectors=1100, scan_inputs=50, scan_outputs=50, power=13.50),
            CoreWrapperProfile2D(10, "c7552", test_vectors=1300, scan_inputs=60, scan_outputs=60, power=14.80),
        ]

    @staticmethod
    def get_wrapper_profiles_p22810() -> List[CoreWrapperProfile2D]:
        """Returns CoreWrapperProfile2D list for p22810 wrapper analysis."""
        np.random.seed(42)
        profiles = []
        for i in range(1, 31):
            vectors = 400 + i * 40
            scan_in = 15 + i * 3
            scan_out = 15 + i * 3
            power = round(2.5 + (i * 0.45), 2)
            profiles.append(CoreWrapperProfile2D(i, f"p22810_mod_{i}", test_vectors=vectors, scan_inputs=scan_in, scan_outputs=scan_out, power=power))
        return profiles
