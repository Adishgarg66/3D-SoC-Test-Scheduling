"""
tests/test_algorithms_2d.py
===========================
Tests for all 6 metaheuristic scheduling algorithms under 2D planar constraints
and fair schedule-evaluation budgets.
"""

import pytest
from src.algorithms.greedy_2d import Greedy2DScheduler
from src.algorithms.abc_2d import ABC2DScheduler
from src.algorithms.bat_2d import Bat2DScheduler
from src.algorithms.firefly_2d import Firefly2DScheduler
from src.algorithms.maco_2d import MACO2DScheduler
from src.algorithms.hmaco_fa_2d import HMACOFA2DScheduler


class Test2DAlgorithms:
    @pytest.mark.parametrize("scheduler_cls,kwargs", [
        (Greedy2DScheduler, {}),
        (ABC2DScheduler, {"colony_size": 8, "max_iterations": 4}),
        (Bat2DScheduler, {"num_bats": 8, "max_iterations": 4}),
        (Firefly2DScheduler, {"num_fireflies": 8, "max_iterations": 4}),
        (MACO2DScheduler, {"num_ants": 8, "max_iterations": 4}),
        (HMACOFA2DScheduler, {"num_ants": 8, "num_fireflies": 6, "max_iterations": 4}),
    ])
    def test_d695_2d_schedulers(self, d695_soc_2d, scheduler_cls, kwargs):
        scheduler = scheduler_cls(d695_soc_2d, **kwargs)
        res = scheduler.optimize()

        assert res.makespan > 0
        assert res.eval_count >= 1
        assert len(res.tasks) == len(d695_soc_2d.cores)
        assert res.peak_power <= d695_soc_2d.max_power + 1e-3
        assert res.max_tam_used <= d695_soc_2d.max_tam_width
        assert res.constraint_status == "Safe"
        assert len(res.power_profile) > 0
        assert len(res.tam_profile) > 0

    @pytest.mark.parametrize("scheduler_cls,kwargs", [
        (Greedy2DScheduler, {}),
        (ABC2DScheduler, {"colony_size": 6, "max_iterations": 3}),
        (Bat2DScheduler, {"num_bats": 6, "max_iterations": 3}),
        (Firefly2DScheduler, {"num_fireflies": 6, "max_iterations": 3}),
        (MACO2DScheduler, {"num_ants": 6, "max_iterations": 3}),
        (HMACOFA2DScheduler, {"num_ants": 6, "num_fireflies": 6, "max_iterations": 3}),
    ])
    def test_p22810_2d_schedulers(self, p22810_soc_2d, scheduler_cls, kwargs):
        scheduler = scheduler_cls(p22810_soc_2d, **kwargs)
        res = scheduler.optimize()

        assert res.makespan > 0
        assert len(res.tasks) == len(p22810_soc_2d.cores)
        assert res.peak_power <= p22810_soc_2d.max_power + 1e-3
        assert res.max_tam_used <= p22810_soc_2d.max_tam_width
        assert res.constraint_status == "Safe"

    @pytest.mark.parametrize("scheduler_cls", [
        ABC2DScheduler,
        Bat2DScheduler,
        Firefly2DScheduler,
        MACO2DScheduler,
        HMACOFA2DScheduler,
    ])
    def test_fair_eval_budget_2d(self, d695_soc_2d, scheduler_cls):
        budget = 40
        res = scheduler_cls(d695_soc_2d, max_evals=budget).optimize()
        assert 1 <= res.eval_count <= budget
        assert res.constraint_status == "Safe"
