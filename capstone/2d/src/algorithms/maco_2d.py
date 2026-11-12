"""
2d/src/algorithms/maco_2d.py
============================
Modified Ant Colony Optimization (MACO 2D) Test Scheduling Algorithm.
"""

import os
import sys

_2D_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _2D_ROOT not in sys.path:
    sys.path.insert(0, _2D_ROOT)

from src.algorithms.scheduler_engine_2d import MACO2DEngine as MACO2DScheduler

__all__ = ["MACO2DScheduler"]
