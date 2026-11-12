"""
random_stacking/src/algorithms/firefly_3d.py
============================================
3D-Aware Firefly Algorithm (FA) for Random 3D SoC Test Scheduling.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.algorithms.scheduler_engine import Firefly3DEngine as Firefly3DScheduler

__all__ = ["Firefly3DScheduler"]
