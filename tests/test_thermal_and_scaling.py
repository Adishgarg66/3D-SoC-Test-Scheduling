"""
tests/test_thermal_and_scaling.py
==================================
Unit and regression tests for:
1. PredictiveThermalEstimator (transient junction temperature estimation, vertical accumulation, spatial coupling)
2. FrequencyScaledScheduler (dynamic thermal lookahead, frequency throttling, concurrent execution preservation)
"""

import pytest
import sys
import os

from src.models.soc_3d import Core3D, SoC3D, ScheduledTask3D, ScheduleResult3D
from src.models.predictive_thermal import PredictiveThermalEstimator, FrequencyScaledScheduler, MLThermalRegressor


@pytest.fixture
def thermal_estimator():
    return PredictiveThermalEstimator(num_layers=3, ambient_temp_k=300.15, thermal_threshold_k=365.15)


def test_estimator_ambient_baseline(thermal_estimator):
    """Empty active core list should return ambient temperature (27.0 °C)."""
    tj_c = thermal_estimator.predict_transient_tj([])
    assert abs(tj_c - 27.0) < 1e-3, f"Expected 27.0°C ambient, got {tj_c}°C"


def test_estimator_monotonic_power_response(thermal_estimator):
    """Temperature prediction should rise monotonically with core power."""
    c_low = Core3D(core_id=1, name="c1", test_cycles=1000, power=2.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    c_high = Core3D(core_id=2, name="c2", test_cycles=1000, power=10.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)

    tj_low = thermal_estimator.predict_transient_tj([c_low])
    tj_high = thermal_estimator.predict_transient_tj([c_high])

    assert tj_high > tj_low, f"Higher power ({tj_high}°C) must yield higher temperature than lower power ({tj_low}°C)"
    assert tj_low > 27.0


def test_estimator_layer_resistance_gradient(thermal_estimator):
    """Cores in upper layers experience higher thermal resistance to heat sink."""
    c_bottom = Core3D(core_id=1, name="c1", test_cycles=1000, power=5.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    c_top = Core3D(core_id=2, name="c2", test_cycles=1000, power=5.0, tam_width=4, layer_id=2, grid_x=0, grid_y=0, tsv_required=4)

    tj_bottom = thermal_estimator.predict_transient_tj([c_bottom])
    tj_top = thermal_estimator.predict_transient_tj([c_top])

    assert tj_top > tj_bottom, f"Upper layer core should reach higher Tj ({tj_top:.2f}°C) than bottom layer ({tj_bottom:.2f}°C)"


def test_estimator_spatial_coupling(thermal_estimator):
    """Two concurrent cores on adjacent layers incur inter-die coupling penalty."""
    c0 = Core3D(core_id=1, name="c1", test_cycles=1000, power=8.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    c1 = Core3D(core_id=2, name="c2", test_cycles=1000, power=8.0, tam_width=4, layer_id=1, grid_x=0, grid_y=0, tsv_required=4)

    tj_single_0 = thermal_estimator.predict_transient_tj([c0])
    tj_single_1 = thermal_estimator.predict_transient_tj([c1])
    tj_combined = thermal_estimator.predict_transient_tj([c0, c1])

    # Combined should exceed either single core and include coupling spike
    assert tj_combined > max(tj_single_0, tj_single_1)


def test_frequency_scaled_scheduler_nominal(d695_soc_fixed3d, thermal_estimator):
    """Low-power schedule should not trigger frequency scaling (remains 1.0x)."""
    # Create simple 2-task schedule with low power
    t1 = ScheduledTask3D(core_id=1, core_name="c1", start_time=0, end_time=100, duration=100, power=1.5, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    t2 = ScheduledTask3D(core_id=2, core_name="c2", start_time=0, end_time=150, duration=150, power=1.5, tam_width=4, layer_id=1, grid_x=0, grid_y=0, tsv_required=4)
    schedule = ScheduleResult3D(
        algorithm_name="Test", makespan=150, tasks=[t1, t2],
        power_profile=[3.0], thermal_profile=[30.0], tsv_profile=[4],
        peak_power=3.0, peak_temperature=30.0, max_tsv_used=4
    )

    scheduler = FrequencyScaledScheduler(d695_soc_fixed3d, thermal_estimator)
    scaled = scheduler.apply_frequency_scaling(schedule)

    assert len(scaled.tasks) == 2
    for orig, sc in zip(schedule.tasks, scaled.tasks):
        assert sc.duration == orig.duration
        assert sc.power == orig.power


def test_frequency_scaled_scheduler_throttling(d695_soc_fixed3d, thermal_estimator):
    """High-power schedule triggers frequency throttling, extending test duration and cutting power."""
    # Create high-power tasks on multiple layers that push Tj > 85°C
    t1 = ScheduledTask3D(core_id=1, core_name="c1", start_time=0, end_time=1000, duration=1000, power=40.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    t2 = ScheduledTask3D(core_id=2, core_name="c2", start_time=0, end_time=1000, duration=1000, power=40.0, tam_width=4, layer_id=1, grid_x=0, grid_y=0, tsv_required=4)
    schedule = ScheduleResult3D(
        algorithm_name="TestHighPower", makespan=1000, tasks=[t1, t2],
        power_profile=[80.0], thermal_profile=[90.0], tsv_profile=[4],
        peak_power=80.0, peak_temperature=90.0, max_tsv_used=4
    )

    scheduler = FrequencyScaledScheduler(d695_soc_fixed3d, thermal_estimator)
    scaled = scheduler.apply_frequency_scaling(schedule)

    # At least one task should be throttled (duration extended)
    has_extended_duration = any(sc.duration > orig.duration for sc, orig in zip(scaled.tasks, schedule.tasks))
    has_reduced_power = any(sc.power < orig.power for sc, orig in zip(scaled.tasks, schedule.tasks))

    assert has_extended_duration, "Expected duration extension under severe thermal stress"
    assert has_reduced_power, "Expected power reduction under frequency scaling"


def test_frequency_scaled_concurrency_preservation(d695_soc_fixed3d, thermal_estimator):
    """
    Regression test for the concurrency bug:
    Tasks with low power scheduled concurrently at start_time=0 must remain concurrent (start_time=0),
    not sequentially serialized.
    """
    t1 = ScheduledTask3D(core_id=1, core_name="c1", start_time=0, end_time=500, duration=500, power=2.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    t2 = ScheduledTask3D(core_id=2, core_name="c2", start_time=0, end_time=500, duration=500, power=2.0, tam_width=4, layer_id=1, grid_x=0, grid_y=0, tsv_required=4)
    schedule = ScheduleResult3D(
        algorithm_name="ConcurrentTest", makespan=500, tasks=[t1, t2],
        power_profile=[4.0], thermal_profile=[30.0], tsv_profile=[4],
        peak_power=4.0, peak_temperature=30.0, max_tsv_used=4
    )

    scheduler = FrequencyScaledScheduler(d695_soc_fixed3d, thermal_estimator)
    scaled = scheduler.apply_frequency_scaling(schedule)

    assert scaled.tasks[0].start_time == 0
    assert scaled.tasks[1].start_time == 0, f"Task 2 was serialized to start_time {scaled.tasks[1].start_time} instead of remaining concurrent at 0"
    assert scaled.makespan == 500


def test_ml_thermal_regressor_train_and_evaluate(d695_soc_fixed3d):
    """Verify leak-free deduplicated ML regressor and independent trajectory validation."""
    eval_out = MLThermalRegressor.train_and_evaluate([d695_soc_fixed3d], samples_per_soc=300, test_fraction=0.2, seed=42)
    summary = eval_out["summary"]
    assert len(summary) == 2
    assert eval_out["train_test_overlap"] == 0
    poly_metrics = summary[1]
    assert poly_metrics["train_test_overlap"] == 0
    assert 30 <= poly_metrics["test_samples"] <= 60
    assert poly_metrics["test_r2"] > 0.90
    assert poly_metrics["test_mae_c"] < 5.0

    traj_out = MLThermalRegressor.evaluate_on_solver_trajectories(
        [d695_soc_fixed3d],
        eval_out["best_model"],
        train_feature_keys=eval_out["train_feature_keys"],
        seeds=(512, 777, 1024),
        max_evals=50,
    )
    assert traj_out["total_steps"] > 0
    assert traj_out["all_steps_metrics"]["r2"] > 0.90
    if traj_out["strictly_unseen_steps"] > 0:
        assert traj_out["unseen_steps_metrics"]["mae_c"] < 5.0

    ml_model = eval_out["best_model"]
    scheduler = FrequencyScaledScheduler(d695_soc_fixed3d, ml_model)
    t1 = ScheduledTask3D(core_id=1, core_name="c1", start_time=0, end_time=500, duration=500, power=2.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    base_res = ScheduleResult3D(
        algorithm_name="Base", makespan=500, tasks=[t1],
        power_profile=[2.0], thermal_profile=[30.0], tsv_profile=[4],
        peak_power=2.0, peak_temperature=30.0, max_tsv_used=4
    )
    ml_scaled = scheduler.apply_frequency_scaling(base_res)
    assert ml_scaled.makespan > 0
    assert ml_scaled.constraint_status == "Safe"
