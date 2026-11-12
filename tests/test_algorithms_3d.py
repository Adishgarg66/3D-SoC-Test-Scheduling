"""
tests/test_algorithms_3d.py
===========================
Tests for 3D SoC Test Scheduling Metaheuristics (Structured Fixed & Dynamic Random Stacking).
"""

import pytest
from src.algorithms.greedy_3d import Greedy3DScheduler
from src.algorithms.abc_3d import ABC3DScheduler
from src.algorithms.bat_3d import Bat3DScheduler
from src.algorithms.firefly_3d import Firefly3DScheduler
from src.algorithms.maco_3d import MACO3DScheduler
from src.algorithms.hmaco_fa_3d import HMACOFA3DScheduler


class Test3DAlgorithms:
    @pytest.mark.parametrize("scheduler_cls,kwargs", [
        (Greedy3DScheduler, {}),
        (ABC3DScheduler, {"colony_size": 8, "max_iterations": 4}),
        (Bat3DScheduler, {"num_bats": 8, "max_iterations": 4}),
        (Firefly3DScheduler, {"num_fireflies": 8, "max_iterations": 4}),
        (MACO3DScheduler, {"num_ants": 8, "max_iterations": 4}),
        (HMACOFA3DScheduler, {"num_ants": 8, "num_fireflies": 6, "max_iterations": 4}),
    ])
    def test_d695_fixed3d_schedulers(self, d695_soc_fixed3d, scheduler_cls, kwargs):
        scheduler = scheduler_cls(d695_soc_fixed3d, **kwargs)
        res = scheduler.optimize()

        assert res.makespan > 0
        assert res.eval_count >= 1
        assert len(res.tasks) == len(d695_soc_fixed3d.cores)
        assert res.peak_power <= d695_soc_fixed3d.max_power + 1e-3
        assert res.peak_temperature <= (d695_soc_fixed3d.max_temperature - 273.15) + 1e-3
        assert res.max_tsv_used <= d695_soc_fixed3d.max_tsv_bandwidth
        assert res.constraint_status == "Safe"

        # Verify fixed layer mappings
        for t in res.tasks:
            expected_layer = d695_soc_fixed3d.cores[t.core_id - 1].layer_id
            assert t.layer_id == expected_layer

    @pytest.mark.parametrize("scheduler_cls,kwargs", [
        (Greedy3DScheduler, {}),
        (ABC3DScheduler, {"colony_size": 6, "max_iterations": 3}),
        (Bat3DScheduler, {"num_bats": 6, "max_iterations": 3}),
        (Firefly3DScheduler, {"num_fireflies": 6, "max_iterations": 3}),
        (MACO3DScheduler, {"num_ants": 6, "max_iterations": 3}),
        (HMACOFA3DScheduler, {"num_ants": 6, "num_fireflies": 6, "max_iterations": 3}),
    ])
    def test_p22810_fixed3d_schedulers(self, p22810_soc_fixed3d, scheduler_cls, kwargs):
        scheduler = scheduler_cls(p22810_soc_fixed3d, **kwargs)
        res = scheduler.optimize()

        assert res.makespan > 0
        assert len(res.tasks) == len(p22810_soc_fixed3d.cores)
        assert res.peak_power <= p22810_soc_fixed3d.max_power + 1e-3
        assert res.peak_temperature <= (p22810_soc_fixed3d.max_temperature - 273.15) + 1e-3
        assert res.max_tsv_used <= p22810_soc_fixed3d.max_tsv_bandwidth
        assert res.constraint_status == "Safe"

    @pytest.mark.parametrize("scheduler_cls,kwargs", [
        (Greedy3DScheduler, {}),
        (ABC3DScheduler, {"colony_size": 6, "max_iterations": 3}),
        (Bat3DScheduler, {"num_bats": 6, "max_iterations": 3}),
        (Firefly3DScheduler, {"num_fireflies": 6, "max_iterations": 3}),
        (MACO3DScheduler, {"num_ants": 6, "max_iterations": 3}),
        (HMACOFA3DScheduler, {"num_ants": 6, "num_fireflies": 6, "max_iterations": 3}),
    ])
    def test_p22810_random3d_schedulers(self, p22810_soc_random3d, scheduler_cls, kwargs):
        scheduler = scheduler_cls(p22810_soc_random3d, **kwargs)
        res = scheduler.optimize()

        assert res.makespan > 0
        assert len(res.tasks) == len(p22810_soc_random3d.cores)
        assert res.peak_power <= p22810_soc_random3d.max_power + 1e-3
        assert res.peak_temperature <= (p22810_soc_random3d.max_temperature - 273.15) + 1e-3
        assert res.max_tsv_used <= p22810_soc_random3d.max_tsv_bandwidth
        assert res.constraint_status == "Safe"

    @pytest.mark.parametrize("scheduler_cls", [
        ABC3DScheduler,
        Bat3DScheduler,
        Firefly3DScheduler,
        MACO3DScheduler,
        HMACOFA3DScheduler,
    ])
    def test_fair_eval_budget_3d(self, d695_soc_fixed3d, scheduler_cls):
        budget = 40
        res = scheduler_cls(d695_soc_fixed3d, max_evals=budget).optimize()
        assert 1 <= res.eval_count <= budget
        assert res.constraint_status == "Safe"
