"""
structured_fixed_stacking/models/soc_3d_fixed.py
=================================================
Structured Fixed 3D Stacking Model for 3D System-on-Chip (SoC) Test Scheduling.
Enforces fixed structural partitioning of cores among die layers based on literature standard
(Table 2 from 'Test Architecture Optimization for Post-bond Test and Pre-bond Tests of 3D SoCs Using TAM Reuse', Roy & Giri, 2023).

Uses centralized VLSI electronic and computer constraints from src.constraints.vlsi_constraints.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np

from src.constraints.vlsi_constraints import (
    PEAK_POWER_LIMITS, TSV_BANDWIDTH_LIMITS, AMBIENT_TEMP_KELVIN,
    MAX_TEMP_LIMIT_KELVIN, MAX_TEMP_LIMIT_CELSIUS, LAYER_THERMAL_RESISTANCE,
    calculate_wrapper_test_time, calculate_instantaneous_power,
    calculate_active_tsv_count, calculate_junction_temperature,
    verify_all_vlsi_constraints
)


@dataclass
class Core3DFixed:
    """Represents an embedded core with fixed physical die layer assignment."""
    core_id: int
    name: str
    test_cycles: int
    power: float
    tam_width: int
    layer_id: int  # Fixed die layer index z (0 = Layer 1 bottom, 1 = Layer 2 middle, 2 = Layer 3 top)
    grid_x: float
    grid_y: float
    tsv_required: int = 0

    def __post_init__(self):
        if self.tsv_required == 0 and self.layer_id > 0:
            self.tsv_required = self.tam_width


@dataclass
class ScheduledTask3DFixed:
    """Scheduled task representation in fixed 3D execution space."""
    core_id: int
    core_name: str
    start_time: int
    end_time: int
    duration: int
    power: float
    tam_width: int
    layer_id: int
    grid_x: float
    grid_y: float
    tsv_required: int


@dataclass
class ScheduleResult3DFixed:
    """Output summary of a fixed 3D test schedule."""
    algorithm_name: str
    makespan: int
    tasks: List[ScheduledTask3DFixed]
    power_profile: List[float]
    thermal_profile: List[float]
    tsv_profile: List[int]
    peak_power: float
    peak_temperature: float
    max_tsv_used: int
    constraint_status: str = "Safe"
    eval_count: int = 0
    runtime_sec: float = 0.0


class FixedTSVBus:
    """Vertical TSV interconnect resource manager."""
    def __init__(self, max_tsv_bandwidth: int = 24):
        self.max_tsv_bandwidth = max_tsv_bandwidth

    def get_tsv_utilization(self, active_cores: List[Core3DFixed]) -> Tuple[int, float]:
        layer_tams = [(c.layer_id, c.tsv_required) for c in active_cores]
        active_tsv = calculate_active_tsv_count(layer_tams)
        utilization = (active_tsv / self.max_tsv_bandwidth * 100.0) if self.max_tsv_bandwidth > 0 else 0.0
        return active_tsv, utilization


class FixedThermalModel:
    """Spatial-temporal thermal model for fixed multi-layer die stacks."""
    def __init__(self, num_layers: int = 3, max_temp_threshold: float = MAX_TEMP_LIMIT_KELVIN):
        self.num_layers = num_layers
        self.max_temp_threshold = max_temp_threshold

    def estimate_temperature_profile(self, active_cores: List[Core3DFixed], grid_resolution: int = 5) -> Dict[str, any]:
        temp_grids = np.full((self.num_layers, grid_resolution, grid_resolution), AMBIENT_TEMP_KELVIN)
        power_grids = np.zeros((self.num_layers, grid_resolution, grid_resolution))

        for core in active_cores:
            z = min(core.layer_id, self.num_layers - 1)
            gx = int(np.clip(core.grid_x * (grid_resolution - 1), 0, grid_resolution - 1))
            gy = int(np.clip(core.grid_y * (grid_resolution - 1), 0, grid_resolution - 1))
            power_grids[z, gx, gy] += core.power

        layer_powers = [float(np.sum(power_grids[z])) for z in range(self.num_layers)]

        accumulated_heat = 0.0
        layer_temps = np.zeros(self.num_layers)
        for z in range(self.num_layers - 1, -1, -1):
            r_th = LAYER_THERMAL_RESISTANCE[z] if z < len(LAYER_THERMAL_RESISTANCE) else 0.5
            layer_temps[z] = AMBIENT_TEMP_KELVIN + r_th * (layer_powers[z] + accumulated_heat)
            accumulated_heat += layer_powers[z] * 0.75

        for z in range(self.num_layers):
            temp_grids[z, :, :] = layer_temps[z]
            for i in range(grid_resolution):
                for j in range(grid_resolution):
                    cell_power = power_grids[z, i, j]
                    if cell_power > 0:
                        temp_grids[z, i, j] += cell_power * 1.8
                        for di in (-1, 0, 1):
                            for dj in (-1, 0, 1):
                                if di == 0 and dj == 0:
                                    continue
                                ni, nj = i + di, j + dj
                                if 0 <= ni < grid_resolution and 0 <= nj < grid_resolution:
                                    dist = math.sqrt(di**2 + dj**2)
                                    temp_grids[z, ni, nj] += (cell_power * 0.4) / dist

        coupling_penalty = 0.0
        for c1 in active_cores:
            for c2 in active_cores:
                if c1.core_id < c2.core_id:
                    dz = abs(c1.layer_id - c2.layer_id)
                    dxy = math.sqrt((c1.grid_x - c2.grid_x)**2 + (c1.grid_y - c2.grid_y)**2)
                    if dz == 1 and dxy < 0.35:
                        coupling_penalty += (c1.power * c2.power) * 0.12

        max_tj_k, max_tj_c, is_hotspot = calculate_junction_temperature(layer_powers, coupling_penalty)

        return {
            "max_tj": max_tj_k,
            "max_tj_celsius": max_tj_c,
            "is_hotspot": is_hotspot,
            "layer_powers": layer_powers,
            "temp_grids": temp_grids,
            "hotspot_penalty": coupling_penalty
        }


class SoC3DFixed:
    """Main fixed 3D SoC System Container."""
    def __init__(
        self,
        name: str,
        cores: List[Core3DFixed],
        num_layers: int = 3,
        max_tam_width: int = 32,
        max_power: float = 50.0,
        max_tsv_bandwidth: int = 24,
        max_temperature: float = MAX_TEMP_LIMIT_KELVIN
    ):
        self.name = name
        self.cores = cores
        self.num_layers = num_layers
        self.max_tam_width = max_tam_width
        self.max_power = max_power
        self.max_tsv_bandwidth = max_tsv_bandwidth
        self.max_temperature = max_temperature

        self.tsv_bus = FixedTSVBus(max_tsv_bandwidth=max_tsv_bandwidth)
        self.thermal_model = FixedThermalModel(num_layers=num_layers, max_temp_threshold=max_temperature)

    def validate_concurrency(self, active_cores: List[Core3DFixed]) -> Tuple[bool, str]:
        total_tam = sum(c.tam_width for c in active_cores)
        if total_tam > self.max_tam_width:
            return False, f"TAM Exceeded: {total_tam} > {self.max_tam_width}"

        total_power = calculate_instantaneous_power([c.power for c in active_cores])
        if total_power > self.max_power:
            return False, f"Power Exceeded: {total_power:.2f}W > {self.max_power:.2f}W"

        tsv_used, _ = self.tsv_bus.get_tsv_utilization(active_cores)
        if tsv_used > self.max_tsv_bandwidth:
            return False, f"TSV Exceeded: {tsv_used} > {self.max_tsv_bandwidth}"

        thermal_res = self.thermal_model.estimate_temperature_profile(active_cores)
        if thermal_res["is_hotspot"]:
            return False, f"Thermal Hotspot: Tj={thermal_res['max_tj_celsius']:.1f}°C > {MAX_TEMP_LIMIT_CELSIUS:.1f}°C"

        return True, "Valid"

    def is_placement_valid(self, scheduled_tasks, candidate_core: Core3DFixed, st: int) -> bool:
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
                Core3DFixed(
                    core_id=t.core_id, name=t.core_name, test_cycles=t.duration,
                    power=t.power, tam_width=t.tam_width, layer_id=t.layer_id,
                    grid_x=t.grid_x, grid_y=t.grid_y, tsv_required=t.tsv_required
                ) for t in active_at_cp
            ]
            active_cores.append(candidate_core)

            valid, _ = self.validate_concurrency(active_cores)
            if not valid:
                return False

        return True


class FixedBenchmarkLoader:
    """
    Benchmark loader with Fixed 3D Layer Stacking Partitioning (Roy & Giri Table 2).
    """
    @staticmethod
    def load_p22810_fixed(max_tam_width: int = 32, max_power: float = 94.05, max_tsv: int = 24) -> SoC3DFixed:
        """
        p22810 ITC'02 Benchmark (30 modules) with Fixed Layer Partitioning:
        - Layer 1 (z=0, Bottom): 1, 2, 3, 5, 6, 8, 9, 15, 21, 26, 27 (11 cores)
        - Layer 2 (z=1, Middle): 4, 7, 10, 11, 17, 18, 22, 23, 25, 28 (10 cores)
        - Layer 3 (z=2, Top):    12, 13, 14, 16, 19, 20, 24, 29, 30 (9 cores)
        """
        layer_mapping = {
            1: 0, 2: 0, 3: 0, 5: 0, 6: 0, 8: 0, 9: 0, 15: 0, 21: 0, 26: 0, 27: 0,
            4: 1, 7: 1, 10: 1, 11: 1, 17: 1, 18: 1, 22: 1, 23: 1, 25: 1, 28: 1,
            12: 2, 13: 2, 14: 2, 16: 2, 19: 2, 20: 2, 24: 2, 29: 2, 30: 2
        }

        np.random.seed(42)
        cores = []
        base_cycles = [8000, 12000, 15000, 22000, 29000, 35000, 42000, 50000, 61000, 75000]

        for i in range(1, 31):
            cycles = int(base_cycles[(i-1) % 10] * (1.0 + 0.15 * (i // 10)))
            power = round(2.5 + (i * 0.45), 2)
            tam_width = min(8 if (i % 3 != 0) else 16, max_tam_width)
            layer = layer_mapping.get(i, 0)
            gx = round(float(np.random.uniform(0.1, 0.9)), 2)
            gy = round(float(np.random.uniform(0.1, 0.9)), 2)

            cores.append(Core3DFixed(
                core_id=i, name=f"p22810_mod_{i}", test_cycles=cycles,
                power=power, tam_width=tam_width, layer_id=layer,
                grid_x=gx, grid_y=gy, tsv_required=tam_width if layer > 0 else 0
            ))

        return SoC3DFixed(
            name="ITC02_p22810_Fixed3D", cores=cores, num_layers=3,
            max_tam_width=max_tam_width, max_power=max_power,
            max_tsv_bandwidth=max_tsv, max_temperature=MAX_TEMP_LIMIT_KELVIN
        )

    @staticmethod
    def load_d695_fixed(max_tam_width: int = 16, max_power: float = 45.89, max_tsv: int = 16) -> SoC3DFixed:
        """
        d695 ITC'02 Benchmark (10 modules) with Fixed Layer Partitioning:
        - Layer 1 (z=0, Bottom): 1, 2, 7, 10 (4 cores)
        - Layer 2 (z=1, Middle): 3, 4, 8 (3 cores)
        - Layer 3 (z=2, Top):    5, 6, 9 (3 cores)
        """
        layer_mapping = {
            1: 0, 2: 0, 7: 0, 10: 0,
            3: 1, 4: 1, 8: 1,
            5: 2, 6: 2, 9: 2
        }
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
            layer = layer_mapping[cid]
            tam_width = min(tam, max_tam_width)
            cores.append(Core3DFixed(
                core_id=cid, name=name, test_cycles=cycles,
                power=power, tam_width=tam_width, layer_id=layer,
                grid_x=gx, grid_y=gy, tsv_required=tam_width if layer > 0 else 0
            ))

        return SoC3DFixed(
            name="ITC02_d695_Fixed3D", cores=cores, num_layers=3,
            max_tam_width=max_tam_width, max_power=max_power,
            max_tsv_bandwidth=max_tsv, max_temperature=MAX_TEMP_LIMIT_KELVIN
        )
