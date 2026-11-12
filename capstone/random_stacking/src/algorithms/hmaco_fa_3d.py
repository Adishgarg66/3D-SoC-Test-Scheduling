"""
random_stacking/src/algorithms/hmaco_fa_3d.py
=============================================
Hybrid Modified ACO + Firefly Algorithm (H-MACO-FA) for Random 3D SoC Test Scheduling.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.algorithms.scheduler_engine import HMACOFA3DEngine as HMACOFA3DScheduler

__all__ = ["HMACOFA3DScheduler"]
