"""
fixed_stacking/src/algorithms/maco_3d.py
========================================
3D-Aware Modified ACO (MACO) for Fixed 3D SoC Test Scheduling.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.algorithms.scheduler_engine import MACO3DEngine as MACO3DScheduler

__all__ = ["MACO3DScheduler"]
