"""
src/algorithms/abc_3d.py
========================
3D-Aware Artificial Bee Colony (ABC) Algorithm for 3D SoC Test Scheduling.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.algorithms.scheduler_engine import ABC3DEngine as ABC3DScheduler

__all__ = ["ABC3DScheduler"]
