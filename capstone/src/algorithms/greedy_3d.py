"""
src/algorithms/greedy_3d.py
===========================
Greedy First-Fit Baseline Algorithm (LPT) for 3D SoC Test Scheduling.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.algorithms.scheduler_engine import Greedy3DEngine as Greedy3DScheduler

__all__ = ["Greedy3DScheduler"]
