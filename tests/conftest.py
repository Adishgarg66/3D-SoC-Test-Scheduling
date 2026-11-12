"""
tests/conftest.py
=================
Pytest configuration and fixture definitions for the VLSI SoC Test Scheduling Framework.
"""

import os
import sys
import pytest

# Anchor project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPSTONE_DIR = os.path.join(PROJECT_ROOT, "capstone")

# Add all relevant source directories to sys.path
for p in [
    os.path.join(CAPSTONE_DIR, "fixed_stacking"),
    os.path.join(CAPSTONE_DIR, "random_stacking"),
    os.path.join(CAPSTONE_DIR, "2d"),
    CAPSTONE_DIR,
    PROJECT_ROOT
]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")


@pytest.fixture(scope="session")
def d695_soc_2d():
    from src.models.soc_2d import ITC02BenchmarkLoader2D
    return ITC02BenchmarkLoader2D.load_d695_2d(max_tam_width=16, max_power=45.89)


@pytest.fixture(scope="session")
def p22810_soc_2d():
    from src.models.soc_2d import ITC02BenchmarkLoader2D
    return ITC02BenchmarkLoader2D.load_p22810_2d(max_tam_width=32, max_power=94.05)


@pytest.fixture(scope="session")
def d695_soc_fixed3d():
    from src.models.soc_3d_fixed import FixedBenchmarkLoader
    return FixedBenchmarkLoader.load_d695_fixed(max_tam_width=16, max_power=45.89, max_tsv=16)


@pytest.fixture(scope="session")
def p22810_soc_fixed3d():
    from src.models.soc_3d_fixed import FixedBenchmarkLoader
    return FixedBenchmarkLoader.load_p22810_fixed(max_tam_width=32, max_power=94.05, max_tsv=24)


@pytest.fixture(scope="session")
def d695_soc_random3d():
    from src.models.soc_3d import ITC02BenchmarkLoader
    return ITC02BenchmarkLoader.load_d695_3d(max_tam_width=16, max_power=45.89, max_tsv=16)


@pytest.fixture(scope="session")
def p22810_soc_random3d():
    from src.models.soc_3d import ITC02BenchmarkLoader
    return ITC02BenchmarkLoader.load_p22810_3d(max_tam_width=32, max_power=94.05, max_tsv=24)
