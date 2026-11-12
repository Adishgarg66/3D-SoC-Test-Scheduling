"""
2d/src/algorithms/hmaco_fa_2d.py
================================
Hybrid Modified ACO + Firefly Algorithm (H-MACO-FA 2D) Test Scheduling Algorithm.
"""

import os
import sys

_2D_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _2D_ROOT not in sys.path:
    sys.path.insert(0, _2D_ROOT)

from src.algorithms.scheduler_engine_2d import HMACOFA2DEngine as HMACOFA2DScheduler

__all__ = ["HMACOFA2DScheduler"]
