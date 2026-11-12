"""
fixed_stacking/src/models/soc_3d.py
====================================
Fixed 3D Stacking Module Compatibility Wrapper.
Re-exports SoC3DFixed classes for algorithm compatibility under fixed layer partitioning.
"""

from src.models.soc_3d_fixed import (
    Core3DFixed as Core3D,
    ScheduledTask3DFixed as ScheduledTask3D,
    ScheduleResult3DFixed as ScheduleResult3D,
    SoC3DFixed as SoC3D,
    FixedBenchmarkLoader as ITC02BenchmarkLoader,
    verify_all_vlsi_constraints
)

def compute_empirical_constraint_status(peak_power, max_power, peak_temp, max_temp_celsius, max_tsv, max_tsv_bandwidth):
    _, status = verify_all_vlsi_constraints(peak_power, max_power, peak_temp, max_temp_celsius, max_tsv, max_tsv_bandwidth)
    return status
