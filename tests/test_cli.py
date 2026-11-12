"""
tests/test_cli.py
==================
Integration tests for the unified CLI entry point: run_test_suite.py
"""

import sys
import os
import subprocess
import pytest

CLI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run_test_suite.py"))


def test_cli_help():
    """Verify run_test_suite.py --help succeeds and displays key flags."""
    res = subprocess.run([sys.executable, CLI_PATH, "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "--mode" in res.stdout
    assert "--benchmark" in res.stdout
    assert "--algorithm" in res.stdout
    assert "--output-dir" in res.stdout
    assert "--no-plots" in res.stdout


def test_cli_invalid_mode():
    """Verify invalid mode flag raises error and non-zero exit."""
    res = subprocess.run([sys.executable, CLI_PATH, "--mode", "invalid_mode"], capture_output=True, text=True)
    assert res.returncode != 0


def test_cli_2d_greedy_execution(tmp_path):
    """Verify 2D single algorithm CLI execution."""
    out_dir = str(tmp_path / "cli_2d_out")
    cmd = [
        sys.executable, CLI_PATH,
        "--mode", "2d",
        "--benchmark", "d695",
        "--algorithm", "greedy",
        "--output-dir", out_dir,
        "--no-plots"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed with error:\n{res.stderr}"
    assert "Greedy 2D Baseline" in res.stdout
    assert "Execution Complete" in res.stdout

    # Verify generated spreadsheet report in custom output dir
    files = os.listdir(out_dir)
    assert any(f.endswith(".xlsx") for f in files)
    assert any(f.endswith(".csv") for f in files)


def test_cli_fixed3d_maco_execution(tmp_path):
    """Verify Fixed 3D single algorithm CLI execution."""
    out_dir = str(tmp_path / "cli_fixed3d_out")
    cmd = [
        sys.executable, CLI_PATH,
        "--mode", "fixed3d",
        "--benchmark", "d695",
        "--algorithm", "maco",
        "--output-dir", out_dir,
        "--no-plots",
        "--no-hil"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed with error:\n{res.stderr}"
    assert "Modified ACO" in res.stdout
    assert "Execution Complete" in res.stdout


def test_cli_hmaco_fa_and_max_evals(tmp_path):
    """Verify H-MACO-FA execution and --max-evals flag via unified CLI."""
    out_dir = str(tmp_path / "cli_hmaco_out")
    cmd = [
        sys.executable, CLI_PATH,
        "--mode", "fixed3d",
        "--benchmark", "d695",
        "--algorithm", "hmaco_fa",
        "--max-evals", "80",
        "--output-dir", out_dir,
        "--no-plots",
        "--no-hil",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed with error:\n{res.stderr}"
    assert "H-MACO-FA" in res.stdout
    assert "MaxEvals=80" in res.stdout


def test_cli_multiseed_stats(tmp_path):
    """Verify --seeds multi-seed statistical summary CLI mode."""
    out_dir = str(tmp_path / "cli_seeds_out")
    cmd = [
        sys.executable, CLI_PATH,
        "--mode", "2d",
        "--benchmark", "d695",
        "--algorithm", "all",
        "--seeds", "42", "100",
        "--max-evals", "40",
        "--output-dir", out_dir,
        "--no-plots",
        "--no-hil",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed with error:\n{res.stderr}"
    assert "MULTI-SEED STATISTICAL ANALYSIS" in res.stdout
    assert os.path.exists(os.path.join(out_dir, "multiseed_raw_2d_d695.csv"))
    assert os.path.exists(os.path.join(out_dir, "MultiSeed_Stats_2d_d695.xlsx"))
