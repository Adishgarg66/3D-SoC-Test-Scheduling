"""
src/hardware/rpi_tester.py
==========================
Phase 3: Hardware-in-the-Loop (HIL) Validation for Raspberry Pi (Pi 4 / 3 / Zero / 5).
Delegates execution to the unified BaseRaspberryPiTester bridge supporting:
- Remote Raspberry Pi TCP Socket or SSH execution
- Local physical RPi.GPIO / gpiozero execution
- Calibrated Mock Simulator fallback
"""

import json
import logging
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from capstone.src.hardware.rpi_remote_bridge import BaseRaspberryPiTester, RemoteRPiHILClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [RPi-Tester] - %(levelname)s - %(message)s")


class RaspberryPi5Tester(BaseRaspberryPiTester):
    """3D SoC Hardware-in-the-Loop (HIL) Interface & Execution Engine."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("is_3d", True)
        super().__init__(*args, **kwargs)


if __name__ == "__main__":
    from src.models.soc_3d import ITC02BenchmarkLoader
    from src.algorithms.maco_3d import MACO3DScheduler

    soc = ITC02BenchmarkLoader.load_d695_3d()
    maco = MACO3DScheduler(soc, num_ants=15, max_iterations=15)
    res = maco.optimize()

    tester = RaspberryPi5Tester(mock_mode=True)
    report = tester.replay_schedule(res)
    print("\n--- HIL Validation Performance Report ---")
    print(json.dumps(report, indent=2))
