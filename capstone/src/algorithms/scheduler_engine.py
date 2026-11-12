"""
capstone/src/algorithms/scheduler_engine.py
===========================================
Unified 3D SoC Scheduling Engine & Evaluation-Budget-Aware Metaheuristics.

Provides shared constraint-compliant event packing, profile synthesis,
exact objective evaluation counting (`eval_count` / `max_evals`), and
cooperative Hybrid MACO-Firefly (H-MACO-FA) alongside Greedy, ABC, Bat,
Firefly, and MACO for both Fixed 3D and Random 3D stacking architectures.
"""

import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class BudgetExhausted(Exception):
    """Internal control-flow signal raised cleanly when max_evals is reached."""


def _resolve_model_types(soc: Any) -> Tuple[Any, Any, Any]:
    """Resolves (CoreCls, ScheduledTaskCls, ScheduleResultCls) matching soc's module."""
    core_cls = type(soc.cores[0]) if soc.cores else None
    mod_name = type(soc).__module__
    if "soc_3d_fixed" in mod_name:
        from src.models.soc_3d_fixed import Core3DFixed, ScheduledTask3DFixed, ScheduleResult3DFixed
        return Core3DFixed, ScheduledTask3DFixed, ScheduleResult3DFixed
    from src.models.soc_3d import Core3D, ScheduledTask3D, ScheduleResult3D
    return core_cls or Core3D, ScheduledTask3D, ScheduleResult3D


def compute_constraint_status(
    peak_power: float,
    max_power: float,
    peak_temp_c: float,
    max_temp_c: float,
    max_tsv: int,
    max_tsv_bandwidth: int,
) -> str:
    violations: List[str] = []
    if peak_power > max_power + 1e-3:
        violations.append(f"Power ({peak_power:.1f}W > {max_power:.1f}W)")
    if peak_temp_c > max_temp_c + 1e-3:
        violations.append(f"Thermal ({peak_temp_c:.1f}°C > {max_temp_c:.1f}°C)")
    if max_tsv > max_tsv_bandwidth:
        violations.append(f"TSV ({max_tsv} > {max_tsv_bandwidth})")
    return "Safe" if not violations else "VIOLATED (" + ", ".join(violations) + ")"


def pack_3d_order(soc: Any, order: List[int], task_cls: Any) -> Tuple[int, List[Any]]:
    """
    Event-driven earliest-feasible 3D multi-constraint packer.
    Checks TAM, Peak Power, Vertical TSVs, and Dynamic RC Temperature across intervals.
    """
    scheduled_tasks: List[Any] = []
    completion_events = {0}

    for core_idx in order:
        core = soc.cores[core_idx]
        placed = False
        while not placed:
            for st in sorted(completion_events):
                if soc.is_placement_valid(scheduled_tasks, core, st):
                    end_t = st + core.test_cycles
                    scheduled_tasks.append(
                        task_cls(
                            core_id=core.core_id,
                            core_name=core.name,
                            start_time=st,
                            end_time=end_t,
                            duration=core.test_cycles,
                            power=core.power,
                            tam_width=core.tam_width,
                            layer_id=core.layer_id,
                            grid_x=core.grid_x,
                            grid_y=core.grid_y,
                            tsv_required=core.tsv_required,
                        )
                    )
                    completion_events.add(end_t)
                    placed = True
                    break
            if not placed:
                completion_events.add(max(completion_events) + 500)

    makespan = max(t.end_time for t in scheduled_tasks)
    return makespan, scheduled_tasks


def build_3d_schedule_result(
    soc: Any,
    algorithm_name: str,
    tasks: List[Any],
    makespan: int,
    eval_count: int = 0,
    runtime_sec: float = 0.0,
) -> Any:
    """Builds sampled time-series power/thermal/TSV profiles and verified ScheduleResult3D."""
    core_cls, _, result_cls = _resolve_model_types(soc)
    time_steps = max(1, min(makespan, 200))
    sampled_times = np.linspace(0, makespan, time_steps, dtype=int)

    power_profile: List[float] = []
    thermal_profile: List[float] = []
    tsv_profile: List[int] = []
    peak_power, peak_temp, max_tsv = 0.0, 0.0, 0

    for t in sampled_times:
        active_t = [task for task in tasks if task.start_time <= t < task.end_time]
        active_cores = [
            core_cls(
                core_id=tk.core_id,
                name=tk.core_name,
                test_cycles=tk.duration,
                power=tk.power,
                tam_width=tk.tam_width,
                layer_id=tk.layer_id,
                grid_x=tk.grid_x,
                grid_y=tk.grid_y,
                tsv_required=tk.tsv_required,
            )
            for tk in active_t
        ]
        inst_power = float(sum(c.power for c in active_cores))
        tsv_used, _ = soc.tsv_bus.get_tsv_utilization(active_cores)
        thermal_res = soc.thermal_model.estimate_temperature_profile(active_cores)
        inst_temp_c = float(thermal_res["max_tj_celsius"])

        power_profile.append(inst_power)
        thermal_profile.append(inst_temp_c)
        tsv_profile.append(int(tsv_used))

        peak_power = max(peak_power, inst_power)
        peak_temp = max(peak_temp, inst_temp_c)
        max_tsv = max(max_tsv, int(tsv_used))

    status = compute_constraint_status(
        peak_power=peak_power,
        max_power=soc.max_power,
        peak_temp_c=peak_temp,
        max_temp_c=soc.max_temperature - 273.15,
        max_tsv=max_tsv,
        max_tsv_bandwidth=soc.max_tsv_bandwidth,
    )

    return result_cls(
        algorithm_name=algorithm_name,
        makespan=int(makespan),
        tasks=tasks,
        power_profile=power_profile,
        thermal_profile=thermal_profile,
        tsv_profile=tsv_profile,
        peak_power=peak_power,
        peak_temperature=peak_temp,
        max_tsv_used=max_tsv,
        constraint_status=status,
        eval_count=int(eval_count),
        runtime_sec=float(runtime_sec),
    )


class _Base3DScheduler:
    """Shared base providing exact schedule evaluation counting and budget enforcement."""

    algorithm_label: str = "Base3D"

    def __init__(self, soc: Any, max_evals: Optional[int] = None):
        self.soc = soc
        self.num_cores = len(soc.cores)
        self.max_evals = int(max_evals) if max_evals is not None else None
        self.eval_count = 0
        self.best_history: List[Tuple[int, int]] = []
        _, self._task_cls, _ = _resolve_model_types(soc)

    def _decode_permutation(self, position_vector: np.ndarray) -> List[int]:
        return [int(idx) for idx in np.argsort(position_vector)]

    def _encode_permutation(self, order: List[int]) -> np.ndarray:
        vec = np.zeros(self.num_cores, dtype=float)
        denom = max(self.num_cores, 1)
        for rank, core_idx in enumerate(order):
            vec[core_idx] = (rank + 0.5) / denom
        return vec

    def _evaluate_schedule(self, order: List[int]) -> Tuple[int, List[Any]]:
        if self.max_evals is not None and self.eval_count >= self.max_evals:
            raise BudgetExhausted()
        self.eval_count += 1
        return pack_3d_order(self.soc, order, self._task_cls)

    def _record_best(self, best_makespan: float) -> None:
        if best_makespan < float("inf"):
            self.best_history.append((self.eval_count, int(best_makespan)))

    def _generate_schedule_result(self, tasks: List[Any], makespan: int, runtime_sec: float = 0.0) -> Any:
        return build_3d_schedule_result(
            soc=self.soc,
            algorithm_name=self.algorithm_label,
            tasks=tasks,
            makespan=makespan,
            eval_count=self.eval_count,
            runtime_sec=runtime_sec,
        )


class Greedy3DEngine(_Base3DScheduler):
    algorithm_label = "Greedy (Baseline 3D)"

    def __init__(self, soc: Any, max_evals: Optional[int] = None):
        super().__init__(soc, max_evals=max_evals)

    def optimize(self):
        t0 = time.perf_counter()
        self.eval_count = 0
        self.best_history = []
        order = sorted(range(self.num_cores), key=lambda i: self.soc.cores[i].test_cycles, reverse=True)
        makespan, tasks = self._evaluate_schedule(order)
        self._record_best(makespan)
        return self._generate_schedule_result(tasks, makespan, time.perf_counter() - t0)


class ABC3DEngine(_Base3DScheduler):
    algorithm_label = "Artificial Bee Colony (ABC 3D)"

    def __init__(self, soc: Any, colony_size: int = 20, max_iterations: int = 30, limit: int = 8, max_evals: Optional[int] = None):
        super().__init__(soc, max_evals=max_evals)
        self.colony_size = colony_size
        self.num_employed = max(2, colony_size // 2)
        self.num_onlookers = max(2, colony_size // 2)
        self.max_iterations = max_iterations
        self.limit = limit

    def optimize(self):
        t0 = time.perf_counter()
        self.eval_count = 0
        self.best_history = []

        food_sources = np.random.uniform(0, 1, (self.num_employed, self.num_cores))
        fitness = np.zeros(self.num_employed)
        trial_counts = np.zeros(self.num_employed)
        best_makespan = float("inf")
        best_tasks: List[Any] = []

        try:
            for i in range(self.num_employed):
                mk, tasks = self._evaluate_schedule(self._decode_permutation(food_sources[i]))
                fitness[i] = 1.0 / float(mk)
                if mk < best_makespan:
                    best_makespan = mk
                    best_tasks = tasks
                    self._record_best(best_makespan)

            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for _ in range(iters):
                for i in range(self.num_employed):
                    k = random.choice([idx for idx in range(self.num_employed) if idx != i])
                    phi = np.random.uniform(-1, 1, self.num_cores)
                    v = np.clip(food_sources[i] + phi * (food_sources[i] - food_sources[k]), 0, 1)
                    v_mk, v_tasks = self._evaluate_schedule(self._decode_permutation(v))
                    v_fit = 1.0 / float(v_mk)
                    if v_fit > fitness[i]:
                        food_sources[i] = v
                        fitness[i] = v_fit
                        trial_counts[i] = 0
                        if v_mk < best_makespan:
                            best_makespan = v_mk
                            best_tasks = v_tasks
                            self._record_best(best_makespan)
                    else:
                        trial_counts[i] += 1

                total_fit = np.sum(fitness)
                probs = fitness / total_fit if total_fit > 0 else np.full(self.num_employed, 1.0 / self.num_employed)
                for _ in range(self.num_onlookers):
                    i = int(np.random.choice(range(self.num_employed), p=probs))
                    k = random.choice([idx for idx in range(self.num_employed) if idx != i])
                    phi = np.random.uniform(-1, 1, self.num_cores)
                    v = np.clip(food_sources[i] + phi * (food_sources[i] - food_sources[k]), 0, 1)
                    v_mk, v_tasks = self._evaluate_schedule(self._decode_permutation(v))
                    v_fit = 1.0 / float(v_mk)
                    if v_fit > fitness[i]:
                        food_sources[i] = v
                        fitness[i] = v_fit
                        trial_counts[i] = 0
                        if v_mk < best_makespan:
                            best_makespan = v_mk
                            best_tasks = v_tasks
                            self._record_best(best_makespan)
                    else:
                        trial_counts[i] += 1

                for i in range(self.num_employed):
                    if trial_counts[i] >= self.limit:
                        food_sources[i] = np.random.uniform(0, 1, self.num_cores)
                        mk, tasks = self._evaluate_schedule(self._decode_permutation(food_sources[i]))
                        fitness[i] = 1.0 / float(mk)
                        trial_counts[i] = 0
                        if mk < best_makespan:
                            best_makespan = mk
                            best_tasks = tasks
                            self._record_best(best_makespan)
        except BudgetExhausted:
            pass

        return self._generate_schedule_result(best_tasks, int(best_makespan), time.perf_counter() - t0)


class Bat3DEngine(_Base3DScheduler):
    algorithm_label = "Bat Algorithm (Bat 3D)"

    def __init__(
        self,
        soc: Any,
        num_bats: int = 20,
        max_iterations: int = 30,
        f_min: float = 0.0,
        f_max: float = 2.0,
        alpha_loudness: float = 0.9,
        gamma_pulse: float = 0.9,
        max_evals: Optional[int] = None,
    ):
        super().__init__(soc, max_evals=max_evals)
        self.num_bats = num_bats
        self.max_iterations = max_iterations
        self.f_min = f_min
        self.f_max = f_max
        self.alpha_loudness = alpha_loudness
        self.gamma_pulse = gamma_pulse

    def optimize(self):
        t0 = time.perf_counter()
        self.eval_count = 0
        self.best_history = []

        positions = np.random.uniform(0, 1, (self.num_bats, self.num_cores))
        velocities = np.zeros((self.num_bats, self.num_cores))
        loudness = np.ones(self.num_bats)
        pulse_rate = np.random.uniform(0.1, 0.5, self.num_bats)
        best_makespan = float("inf")
        best_pos = positions[0].copy()
        best_tasks: List[Any] = []

        try:
            for i in range(self.num_bats):
                mk, tasks = self._evaluate_schedule(self._decode_permutation(positions[i]))
                if mk < best_makespan:
                    best_makespan = mk
                    best_pos = positions[i].copy()
                    best_tasks = tasks
                    self._record_best(best_makespan)

            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for t in range(iters):
                for i in range(self.num_bats):
                    freq = self.f_min + (self.f_max - self.f_min) * random.random()
                    velocities[i] = velocities[i] + (best_pos - positions[i]) * freq
                    new_pos = np.clip(positions[i] + velocities[i], 0, 1)

                    if random.random() > pulse_rate[i]:
                        new_pos = np.clip(best_pos + 0.05 * np.random.randn(self.num_cores), 0, 1)

                    new_mk, new_tasks = self._evaluate_schedule(self._decode_permutation(new_pos))
                    if new_mk <= best_makespan and random.random() < loudness[i]:
                        positions[i] = new_pos
                        loudness[i] *= self.alpha_loudness
                        pulse_rate[i] = pulse_rate[i] * (1.0 - math.exp(-self.gamma_pulse * t))

                    if new_mk < best_makespan:
                        best_makespan = new_mk
                        best_pos = new_pos.copy()
                        best_tasks = new_tasks
                        self._record_best(best_makespan)
        except BudgetExhausted:
            pass

        return self._generate_schedule_result(best_tasks, int(best_makespan), time.perf_counter() - t0)


class Firefly3DEngine(_Base3DScheduler):
    algorithm_label = "Firefly Algorithm (Firefly 3D)"

    def __init__(
        self,
        soc: Any,
        num_fireflies: int = 20,
        max_iterations: int = 30,
        beta0: float = 1.0,
        gamma: float = 0.2,
        alpha: float = 0.25,
        max_evals: Optional[int] = None,
    ):
        super().__init__(soc, max_evals=max_evals)
        self.num_fireflies = num_fireflies
        self.max_iterations = max_iterations
        self.beta0 = beta0
        self.gamma = gamma
        self.alpha = alpha

    def optimize(self):
        t0 = time.perf_counter()
        self.eval_count = 0
        self.best_history = []

        positions = np.random.uniform(0, 1, (self.num_fireflies, self.num_cores))
        intensity = np.zeros(self.num_fireflies)
        best_makespan = float("inf")
        best_tasks: List[Any] = []

        try:
            for i in range(self.num_fireflies):
                mk, tasks = self._evaluate_schedule(self._decode_permutation(positions[i]))
                intensity[i] = 1.0 / float(mk)
                if mk < best_makespan:
                    best_makespan = mk
                    best_tasks = tasks
                    self._record_best(best_makespan)

            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for _ in range(iters):
                for i in range(self.num_fireflies):
                    moved = False
                    for j in range(self.num_fireflies):
                        if intensity[j] > intensity[i]:
                            moved = True
                            r = float(np.linalg.norm(positions[i] - positions[j]))
                            beta = self.beta0 * math.exp(-self.gamma * r * r)
                            rand_vec = self.alpha * (np.random.rand(self.num_cores) - 0.5)
                            positions[i] = np.clip(positions[i] + beta * (positions[j] - positions[i]) + rand_vec, 0, 1)
                            new_mk, new_tasks = self._evaluate_schedule(self._decode_permutation(positions[i]))
                            intensity[i] = 1.0 / float(new_mk)
                            if new_mk < best_makespan:
                                best_makespan = new_mk
                                best_tasks = new_tasks
                                self._record_best(best_makespan)
                    if not moved and self.max_evals is not None:
                        # Brightest firefly performs a small local exploration step
                        cand = np.clip(positions[i] + self.alpha * (np.random.rand(self.num_cores) - 0.5), 0, 1)
                        new_mk, new_tasks = self._evaluate_schedule(self._decode_permutation(cand))
                        if new_mk < best_makespan:
                            positions[i] = cand
                            intensity[i] = 1.0 / float(new_mk)
                            best_makespan = new_mk
                            best_tasks = new_tasks
                            self._record_best(best_makespan)
        except BudgetExhausted:
            pass

        return self._generate_schedule_result(best_tasks, int(best_makespan), time.perf_counter() - t0)


class MACO3DEngine(_Base3DScheduler):
    algorithm_label = "Modified ACO (MACO 3D)"

    def __init__(
        self,
        soc: Any,
        num_ants: int = 25,
        max_iterations: int = 35,
        alpha: float = 1.0,
        beta: float = 2.0,
        evaporation_rate: float = 0.15,
        q_value: float = 100.0,
        dynamic_scaling: bool = True,
        max_evals: Optional[int] = None,
    ):
        super().__init__(soc, max_evals=max_evals)
        self.num_ants = num_ants
        self.max_iterations = max_iterations
        self.alpha = alpha
        self.beta = beta
        self.evaporation_rate = evaporation_rate
        self.q_value = q_value
        self.dynamic_scaling = dynamic_scaling
        self.pheromone = np.full((self.num_cores, self.num_cores), 1.0)

    def _compute_heuristics(self) -> np.ndarray:
        eta = np.zeros((self.num_cores, self.num_cores))
        for i in range(self.num_cores):
            for j, c2 in enumerate(self.soc.cores):
                if i != j:
                    cycle_weight = c2.test_cycles / 10000.0
                    power_weight = 1.0 / (c2.power + 0.1)
                    layer_factor = 1.2 if c2.layer_id == 0 else 1.0
                    eta[i][j] = (cycle_weight * 0.6 + power_weight * 0.4) * layer_factor
        return eta

    def _construct_ant_order(self, eta: np.ndarray) -> List[int]:
        unscheduled = list(range(self.num_cores))
        first_idx = random.choice(unscheduled)
        ordered = [first_idx]
        unscheduled.remove(first_idx)

        while unscheduled:
            last_idx = ordered[-1]
            probs = [
                (self.pheromone[last_idx][cand] ** self.alpha) * (eta[last_idx][cand] ** self.beta)
                for cand in unscheduled
            ]
            total_prob = sum(probs)
            if total_prob == 0 or np.isnan(total_prob):
                next_idx = random.choice(unscheduled)
            else:
                norm_probs = [p / total_prob for p in probs]
                next_idx = int(np.random.choice(unscheduled, p=norm_probs))
            ordered.append(next_idx)
            unscheduled.remove(next_idx)
        return ordered

    def _construct_ant_schedule(self, eta: np.ndarray) -> Tuple[int, List[Any], List[int]]:
        ordered = self._construct_ant_order(eta)
        mk, tasks = self._evaluate_schedule(ordered)
        return mk, tasks, ordered

    def optimize(self):
        t0 = time.perf_counter()
        self.eval_count = 0
        self.best_history = []
        self.pheromone = np.full((self.num_cores, self.num_cores), 1.0)

        eta = self._compute_heuristics()
        best_makespan = float("inf")
        best_tasks: List[Any] = []
        best_order: List[int] = list(range(self.num_cores))

        try:
            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for iteration in range(iters):
                if self.dynamic_scaling and self.max_iterations > 0:
                    phase = (iteration % max(self.max_iterations, 1)) / max(self.max_iterations, 1)
                    current_ants = max(1, int(self.num_ants * (1.0 + 0.3 * math.sin(math.pi * phase))))
                else:
                    current_ants = self.num_ants

                ant_schedules = []
                for _ in range(current_ants):
                    mk, tasks, ordered = self._construct_ant_schedule(eta)
                    ant_schedules.append((mk, ordered))
                    if mk < best_makespan:
                        best_makespan = mk
                        best_tasks = tasks
                        best_order = ordered
                        self._record_best(best_makespan)

                self.pheromone *= (1.0 - self.evaporation_rate)
                for mk, ordered in ant_schedules:
                    delta_tau = self.q_value / float(mk)
                    for k in range(len(ordered) - 1):
                        self.pheromone[ordered[k]][ordered[k + 1]] += delta_tau

                delta_best = (2.5 * self.q_value) / float(best_makespan)
                for k in range(len(best_order) - 1):
                    self.pheromone[best_order[k]][best_order[k + 1]] += delta_best
        except BudgetExhausted:
            pass

        return self._generate_schedule_result(best_tasks, int(best_makespan), time.perf_counter() - t0)


class HMACOFA3DEngine(MACO3DEngine):
    """
    Hybrid Modified Ant Colony Optimization + Firefly Algorithm (H-MACO-FA) for 3D SoCs.

    Two-stage cooperative optimization:
    1. Stage 1 (MACO Global Pheromone Search): Explores permutation space via 3D thermal/power
       desirability + pheromone trails and builds a diverse elite schedule archive.
    2. Stage 2 (Firefly Attractiveness & Discrete Swap Intensification): Converts top MACO paths
       into continuous firefly priority vectors, applies exponential attractiveness movement
       toward brighter peers + decaying perturbation and targeted discrete 2-opt swaps, and
       feeds discovered improvements back into global pheromone reinforcement.
    """

    algorithm_label = "Hybrid MACO-FA (H-MACO-FA 3D)"

    def __init__(
        self,
        soc: Any,
        num_ants: int = 15,
        num_fireflies: int = 12,
        max_iterations: int = 15,
        stage1_ratio: float = 0.5,
        beta0: float = 1.0,
        gamma: float = 0.25,
        fa_alpha: float = 0.22,
        max_evals: Optional[int] = None,
    ):
        super().__init__(soc, num_ants=num_ants, max_iterations=max_iterations, max_evals=max_evals)
        self.num_fireflies = num_fireflies
        self.stage1_ratio = stage1_ratio
        self.beta0 = beta0
        self.gamma = gamma
        self.fa_alpha = fa_alpha

    def optimize(self):
        t0 = time.perf_counter()
        self.eval_count = 0
        self.best_history = []
        self.pheromone = np.full((self.num_cores, self.num_cores), 1.0)

        eta = self._compute_heuristics()
        best_makespan = float("inf")
        best_tasks: List[Any] = []
        best_order: List[int] = sorted(
            range(self.num_cores), key=lambda i: self.soc.cores[i].test_cycles, reverse=True
        )

        # Elite archive mapping tuple(order) -> (makespan, order)
        elite_archive: Dict[Tuple[int, ...], Tuple[int, List[int]]] = {}

        if self.max_evals is not None:
            stage1_budget = max(self.num_fireflies, int(self.max_evals * self.stage1_ratio))
            stage1_iters = max(1, self.max_evals)
        else:
            stage1_budget = None
            stage1_iters = max(1, int(round(self.max_iterations * self.stage1_ratio)))

        try:
            # ------------------------------------------------------------------
            # STAGE 1: MACO Global Pheromone Construction
            # ------------------------------------------------------------------
            for it in range(stage1_iters):
                if stage1_budget is not None and self.eval_count >= stage1_budget:
                    break
                phase = it / max(stage1_iters, 1)
                current_ants = max(2, int(self.num_ants * (1.0 + 0.25 * math.sin(math.pi * phase))))
                ant_batch = []
                for _ in range(current_ants):
                    if stage1_budget is not None and self.eval_count >= stage1_budget:
                        break
                    mk, tasks, ordered = self._construct_ant_schedule(eta)
                    ant_batch.append((mk, ordered))
                    key = tuple(ordered)
                    if key not in elite_archive or mk < elite_archive[key][0]:
                        elite_archive[key] = (mk, ordered)
                    if mk < best_makespan:
                        best_makespan = mk
                        best_tasks = tasks
                        best_order = ordered
                        self._record_best(best_makespan)

                if not ant_batch:
                    break
                self.pheromone *= (1.0 - self.evaporation_rate)
                for mk, ordered in ant_batch:
                    delta = self.q_value / float(mk)
                    for k in range(len(ordered) - 1):
                        self.pheromone[ordered[k]][ordered[k + 1]] += delta
                delta_best = (2.5 * self.q_value) / float(best_makespan)
                for k in range(len(best_order) - 1):
                    self.pheromone[best_order[k]][best_order[k + 1]] += delta_best

            # ------------------------------------------------------------------
            # STAGE 2: Seed Firefly Swarm from Top MACO Solutions & Intensify
            # ------------------------------------------------------------------
            sorted_elites = sorted(elite_archive.values(), key=lambda x: x[0])
            pop_vectors: List[np.ndarray] = []
            pop_orders: List[List[int]] = []
            pop_makespans: List[int] = []

            for mk, ord_seq in sorted_elites[: self.num_fireflies]:
                pop_vectors.append(self._encode_permutation(ord_seq))
                pop_orders.append(ord_seq)
                pop_makespans.append(mk)

            while len(pop_vectors) < self.num_fireflies:
                base_vec = self._encode_permutation(best_order)
                perturbed = np.clip(base_vec + 0.12 * np.random.randn(self.num_cores), 0, 1)
                ord_seq = self._decode_permutation(perturbed)
                mk, tasks = self._evaluate_schedule(ord_seq)
                pop_vectors.append(perturbed)
                pop_orders.append(ord_seq)
                pop_makespans.append(mk)
                if mk < best_makespan:
                    best_makespan = mk
                    best_tasks = tasks
                    best_order = ord_seq
                    self._record_best(best_makespan)

            n_ff = len(pop_vectors)
            intensity = [1.0 / float(mk) for mk in pop_makespans]
            stage2_iters = (
                max(1, self.max_iterations - stage1_iters)
                if self.max_evals is None
                else max(self.max_iterations, self.max_evals)
            )

            for s2_it in range(stage2_iters):
                alpha_now = self.fa_alpha * (0.94 ** s2_it)
                for i in range(n_ff):
                    moved = False
                    for j in range(n_ff):
                        if intensity[j] > intensity[i]:
                            moved = True
                            r = float(np.linalg.norm(pop_vectors[i] - pop_vectors[j]))
                            beta = self.beta0 * math.exp(-self.gamma * r * r)
                            rand_vec = alpha_now * (np.random.rand(self.num_cores) - 0.5)
                            cand_vec = np.clip(
                                pop_vectors[i] + beta * (pop_vectors[j] - pop_vectors[i]) + rand_vec,
                                0,
                                1,
                            )
                            cand_order = self._decode_permutation(cand_vec)
                            if cand_order == pop_orders[i] and self.num_cores >= 2:
                                # Discrete 2-opt swap when continuous step stays in same rank basin
                                idx1, idx2 = random.sample(range(self.num_cores), 2)
                                cand_order[idx1], cand_order[idx2] = cand_order[idx2], cand_order[idx1]
                                cand_vec = self._encode_permutation(cand_order)

                            new_mk, new_tasks = self._evaluate_schedule(cand_order)
                            pop_vectors[i] = cand_vec
                            pop_orders[i] = cand_order
                            pop_makespans[i] = new_mk
                            intensity[i] = 1.0 / float(new_mk)

                            if new_mk < best_makespan:
                                best_makespan = new_mk
                                best_tasks = new_tasks
                                best_order = cand_order
                                self._record_best(best_makespan)

                    if not moved and self.num_cores >= 2:
                        # Elite discrete local swap around brightest firefly
                        cand_order = list(best_order)
                        idx1, idx2 = random.sample(range(self.num_cores), 2)
                        cand_order[idx1], cand_order[idx2] = cand_order[idx2], cand_order[idx1]
                        new_mk, new_tasks = self._evaluate_schedule(cand_order)
                        if new_mk < best_makespan:
                            best_makespan = new_mk
                            best_tasks = new_tasks
                            best_order = cand_order
                            pop_vectors[i] = self._encode_permutation(cand_order)
                            pop_orders[i] = cand_order
                            pop_makespans[i] = new_mk
                            intensity[i] = 1.0 / float(new_mk)
                            self._record_best(best_makespan)
        except BudgetExhausted:
            pass

        return self._generate_schedule_result(best_tasks, int(best_makespan), time.perf_counter() - t0)
