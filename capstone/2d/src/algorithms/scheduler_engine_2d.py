"""
capstone/2d/src/algorithms/scheduler_engine_2d.py
=================================================
Unified 2D Planar SoC Scheduling Engine with exact schedule-evaluation
counting (`eval_count` / `max_evals`) and cooperative Hybrid MACO-FA (H-MACO-FA 2D).
"""

import math
import random
import time
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.models.soc_2d import SoC2D, Core2D, ScheduledTask2D, ScheduleResult2D
from src.constraints.vlsi_constraints_2d import verify_2d_vlsi_constraints


class BudgetExhausted2D(Exception):
    """Internal control-flow signal raised cleanly when max_evals is reached."""


class _Base2DScheduler:
    algorithm_label = "Base2D"

    def __init__(self, soc: SoC2D, max_evals: Optional[int] = None):
        self.soc = soc
        self.num_cores = len(soc.cores)
        self.max_evals = int(max_evals) if max_evals is not None else None
        self.eval_count = 0

    def _pack(self, permutation: List[Core2D]) -> Tuple[int, List[ScheduledTask2D]]:
        scheduled_tasks: List[ScheduledTask2D] = []
        completion_events = {0}

        for core in permutation:
            placed = False
            for st in sorted(completion_events):
                if self.soc.is_placement_valid(scheduled_tasks, core, st):
                    et = st + core.test_cycles
                    scheduled_tasks.append(
                        ScheduledTask2D(
                            core_id=core.core_id,
                            core_name=core.name,
                            start_time=st,
                            end_time=et,
                            duration=core.test_cycles,
                            power=core.power,
                            tam_width=core.tam_width,
                            grid_x=core.grid_x,
                            grid_y=core.grid_y,
                        )
                    )
                    completion_events.add(et)
                    placed = True
                    break
            if not placed:
                st = max(completion_events)
                et = st + core.test_cycles
                scheduled_tasks.append(
                    ScheduledTask2D(
                        core_id=core.core_id,
                        core_name=core.name,
                        start_time=st,
                        end_time=et,
                        duration=core.test_cycles,
                        power=core.power,
                        tam_width=core.tam_width,
                        grid_x=core.grid_x,
                        grid_y=core.grid_y,
                    )
                )
                completion_events.add(et)

        makespan = max(t.end_time for t in scheduled_tasks)
        return makespan, scheduled_tasks

    def _build_schedule(self, permutation: List[Core2D]) -> Tuple[int, List[ScheduledTask2D]]:
        if self.max_evals is not None and self.eval_count >= self.max_evals:
            raise BudgetExhausted2D()
        self.eval_count += 1
        return self._pack(permutation)

    def _generate_result(self, makespan: int, tasks: List[ScheduledTask2D], runtime_sec: float) -> ScheduleResult2D:
        time_steps = max(1, min(makespan, 200))
        sampled_times = np.linspace(0, makespan, time_steps, dtype=int)
        power_profile, tam_profile = [], []
        peak_power, max_tam = 0.0, 0

        for t in sampled_times:
            active_t = [tk for tk in tasks if tk.start_time <= t < tk.end_time]
            inst_p = float(sum(tk.power for tk in active_t))
            inst_tam = int(sum(tk.tam_width for tk in active_t))
            power_profile.append(inst_p)
            tam_profile.append(inst_tam)
            peak_power = max(peak_power, inst_p)
            max_tam = max(max_tam, inst_tam)

        _, status = verify_2d_vlsi_constraints(peak_power, self.soc.max_power, max_tam, self.soc.max_tam_width)
        return ScheduleResult2D(
            algorithm_name=self.algorithm_label,
            makespan=int(makespan),
            tasks=tasks,
            power_profile=power_profile,
            tam_profile=tam_profile,
            peak_power=peak_power,
            max_tam_used=max_tam,
            constraint_status=status,
            eval_count=int(self.eval_count),
            runtime_sec=float(runtime_sec),
        )


class Greedy2DEngine(_Base2DScheduler):
    algorithm_label = "Greedy 2D Baseline"

    def optimize(self) -> ScheduleResult2D:
        t0 = time.perf_counter()
        self.eval_count = 0
        sorted_cores = sorted(self.soc.cores, key=lambda c: c.test_cycles, reverse=True)
        ms, tasks = self._build_schedule(sorted_cores)
        return self._generate_result(ms, tasks, time.perf_counter() - t0)


class ABC2DEngine(_Base2DScheduler):
    algorithm_label = "Artificial Bee Colony (ABC 2D)"

    def __init__(self, soc: SoC2D, colony_size: int = 15, max_iterations: int = 15, max_evals: Optional[int] = None):
        super().__init__(soc, max_evals=max_evals)
        self.colony_size = colony_size
        self.max_iterations = max_iterations

    def optimize(self) -> ScheduleResult2D:
        t0 = time.perf_counter()
        self.eval_count = 0
        num_foods = self.colony_size
        foods = []
        best_food = None

        try:
            for _ in range(num_foods):
                perm = self.soc.cores.copy()
                random.shuffle(perm)
                ms, tasks = self._build_schedule(perm)
                entry = {"perm": perm, "makespan": ms, "tasks": tasks, "trial": 0}
                foods.append(entry)
                if best_food is None or ms < best_food["makespan"]:
                    best_food = entry

            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for _ in range(iters):
                for i in range(num_foods):
                    new_perm = foods[i]["perm"].copy()
                    idx1, idx2 = random.sample(range(len(new_perm)), 2)
                    new_perm[idx1], new_perm[idx2] = new_perm[idx2], new_perm[idx1]
                    new_ms, new_tasks = self._build_schedule(new_perm)
                    if new_ms <= foods[i]["makespan"]:
                        foods[i] = {"perm": new_perm, "makespan": new_ms, "tasks": new_tasks, "trial": 0}
                        if new_ms < best_food["makespan"]:
                            best_food = foods[i]
                    else:
                        foods[i]["trial"] += 1

                fitnesses = [1.0 / (f["makespan"] + 1) for f in foods]
                total_fit = sum(fitnesses)
                probs = [fit / total_fit for fit in fitnesses]
                for _ in range(num_foods):
                    i = int(np.random.choice(num_foods, p=probs))
                    new_perm = foods[i]["perm"].copy()
                    idx1, idx2 = random.sample(range(len(new_perm)), 2)
                    new_perm[idx1], new_perm[idx2] = new_perm[idx2], new_perm[idx1]
                    new_ms, new_tasks = self._build_schedule(new_perm)
                    if new_ms <= foods[i]["makespan"]:
                        foods[i] = {"perm": new_perm, "makespan": new_ms, "tasks": new_tasks, "trial": 0}
                        if new_ms < best_food["makespan"]:
                            best_food = foods[i]
                    else:
                        foods[i]["trial"] += 1

                for i in range(num_foods):
                    if foods[i]["trial"] > 5:
                        perm = self.soc.cores.copy()
                        random.shuffle(perm)
                        ms, tasks = self._build_schedule(perm)
                        foods[i] = {"perm": perm, "makespan": ms, "tasks": tasks, "trial": 0}
                        if ms < best_food["makespan"]:
                            best_food = foods[i]
        except BudgetExhausted2D:
            pass

        return self._generate_result(best_food["makespan"], best_food["tasks"], time.perf_counter() - t0)


class Bat2DEngine(_Base2DScheduler):
    algorithm_label = "Bat 2D Algorithm"

    def __init__(self, soc: SoC2D, num_bats: int = 15, max_iterations: int = 15, max_evals: Optional[int] = None):
        super().__init__(soc, max_evals=max_evals)
        self.num_bats = num_bats
        self.max_iterations = max_iterations

    def optimize(self) -> ScheduleResult2D:
        t0 = time.perf_counter()
        self.eval_count = 0
        population = []
        best_bat = None

        try:
            for _ in range(self.num_bats):
                perm = self.soc.cores.copy()
                random.shuffle(perm)
                ms, tasks = self._build_schedule(perm)
                entry = {
                    "perm": perm, "makespan": ms, "tasks": tasks,
                    "frequency": 0.0, "loudness": 1.0, "pulse_rate": 0.5,
                }
                population.append(entry)
                if best_bat is None or ms < best_bat["makespan"]:
                    best_bat = entry

            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for t_iter in range(iters):
                for i in range(self.num_bats):
                    population[i]["frequency"] = random.uniform(0, 1)
                    if random.random() > population[i]["pulse_rate"]:
                        new_perm = best_bat["perm"].copy()
                    else:
                        new_perm = population[i]["perm"].copy()
                    idx1, idx2 = random.sample(range(len(new_perm)), 2)
                    new_perm[idx1], new_perm[idx2] = new_perm[idx2], new_perm[idx1]

                    new_ms, new_tasks = self._build_schedule(new_perm)
                    if new_ms <= population[i]["makespan"] and random.random() < population[i]["loudness"]:
                        population[i]["perm"] = new_perm
                        population[i]["makespan"] = new_ms
                        population[i]["tasks"] = new_tasks
                        population[i]["loudness"] *= 0.95
                        population[i]["pulse_rate"] = 0.5 * (1 - math.exp(-0.05 * t_iter))
                    if new_ms < best_bat["makespan"]:
                        best_bat = {"perm": new_perm, "makespan": new_ms, "tasks": new_tasks}
        except BudgetExhausted2D:
            pass

        return self._generate_result(best_bat["makespan"], best_bat["tasks"], time.perf_counter() - t0)


class Firefly2DEngine(_Base2DScheduler):
    algorithm_label = "Firefly 2D Algorithm"

    def __init__(self, soc: SoC2D, num_fireflies: int = 15, max_iterations: int = 15, max_evals: Optional[int] = None):
        super().__init__(soc, max_evals=max_evals)
        self.num_fireflies = num_fireflies
        self.max_iterations = max_iterations

    def optimize(self) -> ScheduleResult2D:
        t0 = time.perf_counter()
        self.eval_count = 0
        fireflies = []
        best_firefly = None

        try:
            for _ in range(self.num_fireflies):
                perm = self.soc.cores.copy()
                random.shuffle(perm)
                ms, tasks = self._build_schedule(perm)
                entry = {"perm": perm, "makespan": ms, "tasks": tasks}
                fireflies.append(entry)
                if best_firefly is None or ms < best_firefly["makespan"]:
                    best_firefly = entry

            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for _ in range(iters):
                for i in range(self.num_fireflies):
                    moved = False
                    for j in range(self.num_fireflies):
                        if fireflies[j]["makespan"] < fireflies[i]["makespan"]:
                            moved = True
                            new_perm = fireflies[j]["perm"].copy()
                            if random.random() < 0.3:
                                idx1, idx2 = random.sample(range(len(new_perm)), 2)
                                new_perm[idx1], new_perm[idx2] = new_perm[idx2], new_perm[idx1]
                            new_ms, new_tasks = self._build_schedule(new_perm)
                            if new_ms < fireflies[i]["makespan"]:
                                fireflies[i] = {"perm": new_perm, "makespan": new_ms, "tasks": new_tasks}
                                if new_ms < best_firefly["makespan"]:
                                    best_firefly = fireflies[i]
                    if not moved and self.max_evals is not None:
                        cand = fireflies[i]["perm"].copy()
                        idx1, idx2 = random.sample(range(len(cand)), 2)
                        cand[idx1], cand[idx2] = cand[idx2], cand[idx1]
                        new_ms, new_tasks = self._build_schedule(cand)
                        if new_ms < fireflies[i]["makespan"]:
                            fireflies[i] = {"perm": cand, "makespan": new_ms, "tasks": new_tasks}
                            if new_ms < best_firefly["makespan"]:
                                best_firefly = fireflies[i]
        except BudgetExhausted2D:
            pass

        return self._generate_result(best_firefly["makespan"], best_firefly["tasks"], time.perf_counter() - t0)


class MACO2DEngine(_Base2DScheduler):
    algorithm_label = "Modified ACO (MACO 2D)"

    def __init__(self, soc: SoC2D, num_ants: int = 15, max_iterations: int = 15, max_evals: Optional[int] = None):
        super().__init__(soc, max_evals=max_evals)
        self.num_ants = num_ants
        self.max_iterations = max_iterations

    def _construct_perm(self, pheromones: np.ndarray, alpha: float = 1.0, beta: float = 2.0) -> List[Core2D]:
        unassigned = self.soc.cores.copy()
        current_core = random.choice(unassigned)
        perm = [current_core]
        unassigned.remove(current_core)
        while unassigned:
            last_idx = current_core.core_id - 1
            probs = [
                (pheromones[last_idx, cand.core_id - 1] ** alpha) * ((1.0 / (cand.test_cycles + 1)) ** beta)
                for cand in unassigned
            ]
            prob_sum = sum(probs)
            if prob_sum > 0:
                norm_probs = [p / prob_sum for p in probs]
                next_core = unassigned[int(np.random.choice(len(unassigned), p=norm_probs))]
            else:
                next_core = random.choice(unassigned)
            perm.append(next_core)
            unassigned.remove(next_core)
            current_core = next_core
        return perm

    def optimize(self) -> ScheduleResult2D:
        t0 = time.perf_counter()
        self.eval_count = 0
        pheromones = np.ones((self.num_cores, self.num_cores))
        best_perm: Optional[List[Core2D]] = None
        best_makespan = float("inf")
        best_tasks: List[ScheduledTask2D] = []

        try:
            iters = self.max_iterations if self.max_evals is None else max(self.max_iterations, self.max_evals)
            for iter_idx in range(iters):
                phase = (iter_idx % max(self.max_iterations, 1)) / max(self.max_iterations, 1)
                active_ants = max(5, int(self.num_ants * (1.0 - 0.3 * phase)))
                for _ in range(active_ants):
                    perm = self._construct_perm(pheromones)
                    ms, tasks = self._build_schedule(perm)
                    if ms < best_makespan:
                        best_makespan = ms
                        best_perm = perm
                        best_tasks = tasks
                pheromones *= 0.9
                if best_perm:
                    delta_tau = 1.0 / (best_makespan + 1)
                    for i in range(len(best_perm) - 1):
                        pheromones[best_perm[i].core_id - 1, best_perm[i + 1].core_id - 1] += delta_tau
        except BudgetExhausted2D:
            pass

        return self._generate_result(int(best_makespan), best_tasks, time.perf_counter() - t0)


class HMACOFA2DEngine(MACO2DEngine):
    """Hybrid Modified ACO + Firefly Algorithm (H-MACO-FA 2D) for 2D Planar SoCs."""

    algorithm_label = "Hybrid MACO-FA (H-MACO-FA 2D)"

    def __init__(
        self,
        soc: SoC2D,
        num_ants: int = 15,
        num_fireflies: int = 12,
        max_iterations: int = 15,
        stage1_ratio: float = 0.5,
        max_evals: Optional[int] = None,
    ):
        super().__init__(soc, num_ants=num_ants, max_iterations=max_iterations, max_evals=max_evals)
        self.num_fireflies = num_fireflies
        self.stage1_ratio = stage1_ratio

    def optimize(self) -> ScheduleResult2D:
        t0 = time.perf_counter()
        self.eval_count = 0
        pheromones = np.ones((self.num_cores, self.num_cores))
        best_perm = sorted(self.soc.cores, key=lambda c: c.test_cycles, reverse=True)
        best_makespan = float("inf")
        best_tasks: List[ScheduledTask2D] = []
        archive: Dict[Tuple[int, ...], Tuple[int, List[Core2D], List[ScheduledTask2D]]] = {}

        if self.max_evals is not None:
            s1_budget = max(self.num_fireflies, int(self.max_evals * self.stage1_ratio))
            s1_iters = max(1, self.max_evals)
        else:
            s1_budget = None
            s1_iters = max(1, int(round(self.max_iterations * self.stage1_ratio)))

        try:
            for iter_idx in range(s1_iters):
                if s1_budget is not None and self.eval_count >= s1_budget:
                    break
                phase = iter_idx / max(s1_iters, 1)
                active_ants = max(4, int(self.num_ants * (1.0 - 0.25 * phase)))
                for _ in range(active_ants):
                    if s1_budget is not None and self.eval_count >= s1_budget:
                        break
                    perm = self._construct_perm(pheromones)
                    ms, tasks = self._build_schedule(perm)
                    key = tuple(c.core_id for c in perm)
                    if key not in archive or ms < archive[key][0]:
                        archive[key] = (ms, perm, tasks)
                    if ms < best_makespan:
                        best_makespan = ms
                        best_perm = perm
                        best_tasks = tasks
                pheromones *= 0.9
                delta_tau = 1.0 / (best_makespan + 1)
                for i in range(len(best_perm) - 1):
                    pheromones[best_perm[i].core_id - 1, best_perm[i + 1].core_id - 1] += delta_tau

            sorted_arch = sorted(archive.values(), key=lambda x: x[0])
            fireflies = [
                {"perm": p.copy(), "makespan": ms, "tasks": tks}
                for ms, p, tks in sorted_arch[: self.num_fireflies]
            ]
            while len(fireflies) < self.num_fireflies:
                cand = best_perm.copy()
                if len(cand) >= 2:
                    i1, i2 = random.sample(range(len(cand)), 2)
                    cand[i1], cand[i2] = cand[i2], cand[i1]
                ms, tasks = self._build_schedule(cand)
                fireflies.append({"perm": cand, "makespan": ms, "tasks": tasks})
                if ms < best_makespan:
                    best_makespan = ms
                    best_perm = cand
                    best_tasks = tasks

            s2_iters = (
                max(1, self.max_iterations - s1_iters)
                if self.max_evals is None
                else max(self.max_iterations, self.max_evals)
            )
            for _ in range(s2_iters):
                for i in range(len(fireflies)):
                    moved = False
                    for j in range(len(fireflies)):
                        if fireflies[j]["makespan"] < fireflies[i]["makespan"]:
                            moved = True
                            cand = fireflies[j]["perm"].copy()
                            if len(cand) >= 2:
                                i1, i2 = random.sample(range(len(cand)), 2)
                                cand[i1], cand[i2] = cand[i2], cand[i1]
                            ms, tasks = self._build_schedule(cand)
                            if ms < fireflies[i]["makespan"]:
                                fireflies[i] = {"perm": cand, "makespan": ms, "tasks": tasks}
                                if ms < best_makespan:
                                    best_makespan = ms
                                    best_perm = cand
                                    best_tasks = tasks
                    if not moved and len(best_perm) >= 2:
                        cand = best_perm.copy()
                        i1, i2 = random.sample(range(len(cand)), 2)
                        cand[i1], cand[i2] = cand[i2], cand[i1]
                        ms, tasks = self._build_schedule(cand)
                        if ms < best_makespan:
                            best_makespan = ms
                            best_perm = cand
                            best_tasks = tasks
                            fireflies[i] = {"perm": cand, "makespan": ms, "tasks": tasks}
        except BudgetExhausted2D:
            pass

        return self._generate_result(int(best_makespan), best_tasks, time.perf_counter() - t0)
