"""
2d/src/hardware/rpi_tester_2d.py
================================
Hardware-in-the-Loop (HIL) Tester Bridge for 2D Planar SoC Test Schedules.
Base Reference Paper: Patel & Desai (IEEE TIM 2025) [Paper 15].

Supports:
- Remote Raspberry Pi execution over TCP Socket or SSH
- Local physical RPi.GPIO / gpiozero execution
- Calibrated Mock Simulator fallback
"""

import logging
import os
import sys
from typing import Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.hardware.rpi_remote_bridge import BaseRaspberryPiTester, RemoteRPiHILClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [RPi-2D-Tester] - %(levelname)s - %(message)s")


class RaspberryPi5Tester2D(BaseRaspberryPiTester):
    """2D Planar SoC Hardware-in-the-Loop (HIL) Interface & Execution Engine."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("is_3d", False)
        super().__init__(*args, **kwargs)

    def replay_schedule(self, schedule_result, time_scale_factor: Optional[float] = None):
        if time_scale_factor is None:
            time_scale_factor = 1e-6 if self.mock_mode else 1e-5
        return super().replay_schedule(schedule_result, time_scale_factor=time_scale_factor)
