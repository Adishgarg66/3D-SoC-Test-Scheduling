"""
2d/src/algorithms/greedy_2d.py
==============================
Greedy 2D Test Scheduling Baseline Algorithm (LPT).
"""

import os
import sys

_2D_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _2D_ROOT not in sys.path:
    sys.path.insert(0, _2D_ROOT)

from src.algorithms.scheduler_engine_2d import Greedy2DEngine as Greedy2DScheduler

__all__ = ["Greedy2DScheduler"]
