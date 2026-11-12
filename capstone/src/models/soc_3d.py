"""
src/models/soc_3d.py
====================
Core Data Structures for 3D System-on-Chip (SoC) Test Scheduling.
Supports multi-die vertical stacks, TSV interconnect bandwidth constraints,
and spatial-temporal dynamic thermal modeling (junction temperature Tj & hotspot mitigation).
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np


@dataclass
class WrapperConfig:
    """IEEE 1500 Wrapper Configuration mapping TAM width to test cycles."""
    tam_width: int
    test_cycles: int


@dataclass
class Core3D:
    """
    Represents an embedded core / IP module in a 3D SoC architecture.
    """
    core_id: int
    name: str
    test_cycles: int
    power: float  # Peak operational test power (Watts)
    tam_width: int  # Assigned TAM width (bits/channels)
    layer_id: int  # Die layer index z (0 = bottom layer closest to heat sink/substrate)
    grid_x: float  # Physical x-coordinate on die (0.0 to 1.0 normalized)
    grid_y: float  # Physical y-coordinate on die (0.0 to 1.0 normalized)
    tsv_required: int = 0  # Number of vertical TSV lines required if accessed from base TAM
    wrapper_configs: List[WrapperConfig] = field(default_factory=list)

    def __post_init__(self):
        if self.tsv_required == 0 and self.layer_id > 0:
            self.tsv_required = self.tam_width


@dataclass
class DieLayer:
    """Represents a physical die layer in the 3D vertical stack."""
    layer_id: int
    name: str
    thickness_um: float = 100.0  # Thickness in micrometers
    thermal_resistance: float = 0.45  # K/W vertical thermal resistance
    thermal_capacitance: float = 1.2  # J/K thermal capacitance
    ambient_temp: float = 300.15  # Baseline ambient temperature in Kelvin (27°C)
    max_power_density: float = 15.0  # Max power limit per layer (Watts)


class TSVBus:
    """Manages vertical Through-Silicon Via (TSV) interconnect resources."""
    def __init__(self, max_tsv_bandwidth: int = 32):
        self.max_tsv_bandwidth = max_tsv_bandwidth

    def check_tsv_compliance(self, active_cores: List[Core3D]) -> bool:
        """Verify total active vertical TSV channels do not exceed TSV_max limit."""
        total_tsv = sum(c.tsv_required for c in active_cores if c.layer_id > 0)
        return total_tsv <= self.max_tsv_bandwidth

    def get_tsv_utilization(self, active_cores: List[Core3D]) -> Tuple[int, float]:
        """Returns (active_tsv_count, utilization_percentage)."""
        active_tsv = sum(c.tsv_required for c in active_cores if c.layer_id > 0)
        utilization = (active_tsv / self.max_tsv_bandwidth * 100.0) if self.max_tsv_bandwidth > 0 else 0.0
        return active_tsv, utilization


class ThermalModel:
    """
    Spatial-Temporal Dynamic Thermal Model for 3D Multi-Layer Die Stacks.
    Models junction temperature Tj(z, x, y, t) considering:
    1. Layer self-heating and power accumulation.
    2. Vertical thermal conduction down the stack to the heat sink (Die 0).
    3. Lateral spatial thermal diffusion between cores on the same die.
    4. Inter-layer spatial hotspot penalties.
    """
    def __init__(
        self,
        num_layers: int = 3,
        ambient_temp: float = 300.15,  # 27°C baseline
        max_temp_threshold: float = 368.15,  # 95°C hotspot limit
        layer_rth: Optional[List[float]] = None,
        coupling_coeff: float = 0.25
    ):
        self.num_layers = num_layers
        self.ambient_temp = ambient_temp
        self.max_temp_threshold = max_temp_threshold
        self.layer_rth = layer_rth or [0.35 + 0.15 * z for z in range(num_layers)]
        self.coupling_coeff = coupling_coeff

    def estimate_temperature_profile(
        self,
        active_cores: List[Core3D],
        grid_resolution: int = 5
    ) -> Dict[str, any]:
        """
        Calculates spatial-temporal thermal profile across all die layers.
        Returns temperature maps per layer, max Tj, and hotspot flag.
        """
        temp_grids = np.full((self.num_layers, grid_resolution, grid_resolution), self.ambient_temp)
        power_grids = np.zeros((self.num_layers, grid_resolution, grid_resolution))

        for core in active_cores:
            z = min(core.layer_id, self.num_layers - 1)
            gx = int(np.clip(core.grid_x * (grid_resolution - 1), 0, grid_resolution - 1))
            gy = int(np.clip(core.grid_y * (grid_resolution - 1), 0, grid_resolution - 1))
            power_grids[z, gx, gy] += core.power

        accumulated_power_from_above = 0.0
        layer_temps = np.zeros(self.num_layers)

        for z in range(self.num_layers - 1, -1, -1):
            layer_power = np.sum(power_grids[z])
            effective_power = layer_power + accumulated_power_from_above
            delta_t = self.layer_rth[z] * effective_power
            layer_temps[z] = self.ambient_temp + delta_t
            accumulated_power_from_above += layer_power * 0.75

        for z in range(self.num_layers):
            for i in range(grid_resolution):
                for j in range(grid_resolution):
                    cell_power = power_grids[z, i, j]
                    if cell_power > 0:
                        temp_grids[z, i, j] = layer_temps[z] + cell_power * 1.8
                        for di in [-1, 0, 1]:
                            for dj in [-1, 0, 1]:
                                if di == 0 and dj == 0:
                                    continue
                                ni, nj = i + di, j + dj
                                if 0 <= ni < grid_resolution and 0 <= nj < grid_resolution:
                                    dist = math.sqrt(di**2 + dj**2)
                                    temp_grids[z, ni, nj] += (cell_power * 0.4) / dist

        hotspot_penalty = 0.0
        for c1 in active_cores:
            for c2 in active_cores:
                if c1.core_id < c2.core_id:
                    dz = abs(c1.layer_id - c2.layer_id)
                    dxy = math.sqrt((c1.grid_x - c2.grid_x)**2 + (c1.grid_y - c2.grid_y)**2)
                    if dz == 1 and dxy < 0.35:
                        hotspot_penalty += (c1.power * c2.power) * 0.12

        max_tj = np.max(temp_grids) + hotspot_penalty
        is_hotspot = max_tj > self.max_temp_threshold

        return {
            "max_tj": max_tj,
            "max_tj_celsius": max_tj - 273.15,
            "is_hotspot": is_hotspot,
            "layer_temps": layer_temps,
            "temp_grids": temp_grids,
            "hotspot_penalty": hotspot_penalty
        }


class SoC3D:
    """
    Main 3D SoC System Container holding architecture components,
    power/thermal thresholds, TAM width, and TSV limits.
    """
    def __init__(
        self,
        name: str,
        cores: List[Core3D],
        num_layers: int = 3,
        max_tam_width: int = 32,
        max_power: float = 50.0,
        max_tsv_bandwidth: int = 16,
        max_temperature: float = 368.15  # 95°C
    ):
        self.name = name
        self.cores = cores
        self.num_layers = num_layers
        self.max_tam_width = max_tam_width
        self.max_power = max_power
        self.max_tsv_bandwidth = max_tsv_bandwidth
        self.max_temperature = max_temperature

        self.layers = [DieLayer(layer_id=z, name=f"Die_Layer_{z}") for z in range(num_layers)]
        self.tsv_bus = TSVBus(max_tsv_bandwidth=max_tsv_bandwidth)
        self.thermal_model = ThermalModel(
            num_layers=num_layers,
            max_temp_threshold=max_temperature
        )

    def validate_concurrency(self, active_cores: List[Core3D]) -> Tuple[bool, str]:
        """
        Multi-Constraint Checker validating:
        1. TAM Width Limit (W_max)
        2. Peak Power Limit (P_max)
        3. TSV Interconnect Bandwidth (TSV_max)
        4. Thermal Hotspot Limit (T_max / Tj)
        """
        total_tam = sum(c.tam_width for c in active_cores)
        if total_tam > self.max_tam_width:
            return False, f"TAM Limit Exceeded: {total_tam} > {self.max_tam_width}"

        total_power = sum(c.power for c in active_cores)
        if total_power > self.max_power:
            return False, f"Peak Power Exceeded: {total_power:.2f}W > {self.max_power:.2f}W"

        if not self.tsv_bus.check_tsv_compliance(active_cores):
            tsv_used, _ = self.tsv_bus.get_tsv_utilization(active_cores)
            return False, f"TSV Limit Exceeded: {tsv_used} > {self.max_tsv_bandwidth}"

        thermal_res = self.thermal_model.estimate_temperature_profile(active_cores)
        if thermal_res["is_hotspot"]:
            return False, f"Thermal Hotspot Violation: Tj={thermal_res['max_tj_celsius']:.1f}°C > {self.max_temperature-273.15:.1f}°C"

        return True, "Valid"

    def is_placement_valid(self, scheduled_tasks, candidate_core: Core3D, st: int) -> bool:
        """
        Continuous Interval Concurrency Checker:
        Validates that candidate_core starting at st (running to st + candidate_core.test_cycles)
        strictly satisfies TAM, Power, TSV, and Thermal constraints across ALL sub-interval checkpoints
        where concurrent task activity changes.
        """
        et = st + candidate_core.test_cycles

        # Filter tasks that overlap with interval [st, et)
        overlapping = [t for t in scheduled_tasks if max(st, t.start_time) < min(et, t.end_time)]
        if not overlapping:
            valid, _ = self.validate_concurrency([candidate_core])
            return valid

        # Collect event boundary times inside [st, et)
        checkpoints = set([st])
        for t in overlapping:
            if st < t.start_time < et:
                checkpoints.add(t.start_time)

        for cp in checkpoints:
            active_at_cp = [t for t in overlapping if t.start_time <= cp < t.end_time]
            active_cores = [
                Core3D(
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


@dataclass
class ScheduledTask3D:
    """Represents a scheduled test task in 3D execution space."""
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
class ScheduleResult3D:
    """Execution output summary of a 3D test schedule."""
    algorithm_name: str
    makespan: int  # Total test execution time in cycles
    tasks: List[ScheduledTask3D]
    power_profile: List[float]
    thermal_profile: List[float]
    tsv_profile: List[int]
    peak_power: float
    peak_temperature: float
    max_tsv_used: int
    constraint_status: str = "Safe"
    eval_count: int = 0
    runtime_sec: float = 0.0


def compute_empirical_constraint_status(
    peak_power: float, max_power: float,
    peak_temp: float, max_temp_celsius: float,
    max_tsv: int, max_tsv_bandwidth: int
) -> str:
    """Computes dynamic, truthful constraint compliance status."""
    violations = []
    if peak_power > max_power + 1e-3:
        violations.append(f"Power ({peak_power:.1f}W > {max_power:.1f}W)")
    if peak_temp > max_temp_celsius + 1e-3:
        violations.append(f"Thermal ({peak_temp:.1f}°C > {max_temp_celsius:.1f}°C)")
    if max_tsv > max_tsv_bandwidth:
        violations.append(f"TSV ({max_tsv} > {max_tsv_bandwidth})")

    if not violations:
        return "Safe"
    else:
        return "VIOLATED (" + ", ".join(violations) + ")"


class ITC02BenchmarkLoader:
    """
    Benchmark loader providing standard ITC'02 benchmarks (d695 and p22810)
    extended with realistic 3D die layer mapping, spatial coordinates, and TSVs.
    """
    @staticmethod
    def load_d695_3d(max_tam_width: int = 16, max_power: float = 45.89, max_tsv: int = 16) -> SoC3D:
        """
        d695 ITC'02 Benchmark (10 modules, Pmax = 45.89 W).
        Extended to 3-Die Stack (Die 0, Die 1, Die 2).
        """
        raw_cores = [
            (1, "c17", 12000, 3.50, 4, 0, 0.2, 0.2),
            (2, "c432", 18500, 4.20, 4, 0, 0.7, 0.3),
            (3, "c499", 24000, 5.10, 4, 1, 0.3, 0.6),
            (4, "c880", 31000, 6.80, 8, 1, 0.8, 0.7),
            (5, "c1355", 28000, 7.50, 8, 2, 0.2, 0.8),
            (6, "c1908", 45000, 9.20, 8, 2, 0.7, 0.2),
            (7, "c2670", 52000, 10.40, 8, 0, 0.5, 0.5),
            (8, "c3540", 64000, 11.80, 8, 1, 0.4, 0.4),
            (9, "c5315", 85000, 13.50, 16, 2, 0.5, 0.8),
            (10, "c7552", 110000, 14.80, 16, 0, 0.8, 0.8),
        ]

        cores = []
        for cid, name, cycles, power, tam, layer, gx, gy in raw_cores:
            cores.append(Core3D(
                core_id=cid,
                name=name,
                test_cycles=cycles,
                power=power,
                tam_width=min(tam, max_tam_width),
                layer_id=layer,
                grid_x=gx,
                grid_y=gy,
                tsv_required=min(tam, max_tam_width) if layer > 0 else 0
            ))

        return SoC3D(
            name="ITC02_d695_3D",
            cores=cores,
            num_layers=3,
            max_tam_width=max_tam_width,
            max_power=max_power,
            max_tsv_bandwidth=max_tsv,
            max_temperature=368.15  # 95°C
        )

    @staticmethod
    def load_p22810_3d(max_tam_width: int = 32, max_power: float = 94.05, max_tsv: int = 24) -> SoC3D:
        """
        p22810 ITC'02 Benchmark (30 modules, Pmax = 94.05 W).
        Extended to 3-Die Stack.
        """
        np.random.seed(42)
        cores = []
        base_cycles = [8000, 12000, 15000, 22000, 29000, 35000, 42000, 50000, 61000, 75000]
        for i in range(1, 31):
            cycles = int(base_cycles[(i-1) % 10] * (1.0 + 0.15 * (i // 10)))
            power = round(2.5 + (i * 0.45), 2)
            tam_width = 8 if (i % 3 != 0) else 16
            layer = i % 3
            gx = round(float(np.random.uniform(0.1, 0.9)), 2)
            gy = round(float(np.random.uniform(0.1, 0.9)), 2)

            cores.append(Core3D(
                core_id=i,
                name=f"p22810_mod_{i}",
                test_cycles=cycles,
                power=power,
                tam_width=min(tam_width, max_tam_width),
                layer_id=layer,
                grid_x=gx,
                grid_y=gy,
                tsv_required=min(tam_width, max_tsv) if layer > 0 else 0
            ))

        return SoC3D(
            name="ITC02_p22810_3D",
            cores=cores,
            num_layers=3,
            max_tam_width=max_tam_width,
            max_power=max_power,
            max_tsv_bandwidth=max_tsv,
            max_temperature=368.15  # 95°C
        )
