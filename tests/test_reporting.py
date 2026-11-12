"""
tests/test_reporting.py
========================
Unit tests for spreadsheet generation and simulation report exporters:
1. create_excel_openpyxl (Binary OpenXML .xlsx generation, worksheets, headers, styles)
2. create_excel_xml (XML Spreadsheet 2003 .xml fallback)
3. create_csv_files (Universal CSV tabular export)
4. export_custom_run (Live simulation export integration)
"""

import os
import sys
import zipfile
import pytest

# Ensure capstone scripts can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "capstone"))
from scripts.generate_excel_results import (
    create_excel_openpyxl,
    create_excel_xml,
    create_csv_files,
    save_reports,
    export_custom_run,
    HAS_OPENPYXL
)
from src.models.soc_3d import ScheduleResult3D, ScheduledTask3D


@pytest.fixture
def sample_sheets_data():
    return {
        "TestSheet1": {
            "title": "Sample Benchmark Performance",
            "headers": ["Algorithm", "Makespan", "Peak Power", "Status"],
            "rows": [
                ["Greedy 3D", 322500, 22.20, "Safe"],
                ["MACO 3D", 320500, 22.20, "Safe"]
            ]
        },
        "TestSheet2": {
            "title": "HIL Metrics",
            "headers": ["Mode", "Overhead %"],
            "rows": [
                ["Mock Bridge", "0.10%"]
            ]
        }
    }


def test_create_excel_openpyxl(tmp_path, sample_sheets_data):
    """Test generating binary OpenXML .xlsx workbook."""
    if not HAS_OPENPYXL:
        pytest.skip("openpyxl not installed")

    out_file = str(tmp_path / "test_report.xlsx")
    success = create_excel_openpyxl(out_file, sample_sheets_data)
    assert success is True
    assert os.path.exists(out_file)

    # Verify it is a valid zip archive (standard for .xlsx)
    assert zipfile.is_zipfile(out_file)

    # Load and verify contents
    import openpyxl
    wb = openpyxl.load_workbook(out_file)
    assert "TestSheet1" in wb.sheetnames
    assert "TestSheet2" in wb.sheetnames

    ws1 = wb["TestSheet1"]
    # Check headers
    headers = [cell.value for cell in ws1[3]]
    assert headers == ["Algorithm", "Makespan", "Peak Power", "Status"]

    # Check first data row
    row1 = [cell.value for cell in ws1[4]]
    assert row1 == ["Greedy 3D", 322500, 22.20, "Safe"]


def test_create_excel_xml(tmp_path, sample_sheets_data):
    """Test generating XML Spreadsheet 2003 (.xml)."""
    out_file = str(tmp_path / "test_report.xml")
    create_excel_xml(out_file, sample_sheets_data)
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<?xml version=\"1.0\"" in content
    assert "<Workbook" in content
    assert "ss:Name=\"TestSheet1\"" in content
    assert "ss:Name=\"TestSheet2\"" in content
    assert "Greedy 3D" in content


def test_create_csv_files(tmp_path, sample_sheets_data):
    """Test generating CSV data tables."""
    create_csv_files(str(tmp_path), sample_sheets_data)

    csv1 = str(tmp_path / "TestSheet1.csv")
    csv2 = str(tmp_path / "TestSheet2.csv")

    assert os.path.exists(csv1)
    assert os.path.exists(csv2)

    with open(csv1, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines()]

    assert "Algorithm,Makespan,Peak Power,Status" in lines
    assert "Greedy 3D,322500,22.2,Safe" in lines


def test_save_reports_generates_all_formats(tmp_path, sample_sheets_data):
    """Test save_reports produces .xlsx, .xml, and .csv files."""
    save_reports(str(tmp_path), "AllFormatsReport", sample_sheets_data)

    assert os.path.exists(tmp_path / "AllFormatsReport.xlsx")
    assert os.path.exists(tmp_path / "AllFormatsReport.xml")
    assert os.path.exists(tmp_path / "TestSheet1.csv")


def test_export_custom_run(tmp_path):
    """Test exporting custom live simulation results."""
    t1 = ScheduledTask3D(core_id=1, core_name="c1", start_time=0, end_time=100, duration=100, power=2.0, tam_width=4, layer_id=0, grid_x=0, grid_y=0, tsv_required=4)
    res = ScheduleResult3D(
        algorithm_name="MockMACO",
        makespan=100,
        tasks=[t1],
        power_profile=[2.0],
        thermal_profile=[45.0],
        tsv_profile=[4],
        peak_power=2.0,
        peak_temperature=45.0,
        max_tsv_used=4,
        constraint_status="Safe"
    )

    results_dict = {"MockMACO": res}
    export_custom_run(str(tmp_path), "d695", "fixed3d", results_dict)

    expected_xlsx = tmp_path / "Live_Results_fixed3d_d695.xlsx"
    expected_xml = tmp_path / "Live_Results_fixed3d_d695.xml"
    assert os.path.exists(expected_xlsx)
    assert os.path.exists(expected_xml)

    import openpyxl
    wb = openpyxl.load_workbook(expected_xlsx, read_only=True)
    assert len(wb.sheetnames) >= 1
    ws = wb.active
    headers = [cell for cell in next(ws.iter_rows(min_row=3, max_row=3, values_only=True))]
    assert "Evaluations" in headers
    wb.close()


def test_results_workbooks_valid_openpyxl():
    """Verify every generated .xlsx workbook in results/ and capstone/*/results/ opens cleanly."""
    import glob
    import openpyxl

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    patterns = [
        os.path.join(repo_root, "results", "tables", "excel", "*.xlsx"),
        os.path.join(repo_root, "results", "comparisons", "**", "*.xlsx"),
        os.path.join(repo_root, "capstone", "2d", "results", "*.xlsx"),
        os.path.join(repo_root, "capstone", "fixed_stacking", "results", "*.xlsx"),
        os.path.join(repo_root, "capstone", "random_stacking", "results", "*.xlsx"),
    ]
    xlsx_files = []
    for pat in patterns:
        xlsx_files.extend(glob.glob(pat, recursive=True))

    assert len(xlsx_files) >= 3
    for path in sorted(set(xlsx_files)):
        assert os.path.getsize(path) > 0, f"Empty workbook: {path}"
        wb = openpyxl.load_workbook(path, read_only=True)
        try:
            assert len(wb.sheetnames) >= 1, f"No worksheets in: {path}"
            first_ws = wb[wb.sheetnames[0]]
            assert first_ws.max_row is None or first_ws.max_row >= 1
        finally:
            wb.close()


def test_results_graphs_valid_images():
    """Verify all generated PNG figures under results/graphs/ are valid non-empty images."""
    import glob
    from PIL import Image

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    graphs_dir = os.path.join(repo_root, "results", "graphs")
    if not os.path.isdir(graphs_dir):
        return
    png_files = sorted(glob.glob(os.path.join(graphs_dir, "**", "*.png"), recursive=True))
    assert len(png_files) == 20
    for path in png_files:
        assert os.path.getsize(path) > 5000, f"Suspiciously small PNG: {path}"
        with Image.open(path) as img:
            width, height = img.size
            assert width >= 600 and height >= 300, f"Invalid dimensions in {path}: {(width, height)}"
            img.verify()


def test_results_raspberry_pi_physical_logs():
    """Verify captured Raspberry Pi HIL JSON logs document genuine Pi 4 hardware."""
    import glob
    import json

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rpi_dir = os.path.join(repo_root, "results", "raw_data", "raspberry_pi")
    if not os.path.isdir(rpi_dir):
        return
    trial_jsons = sorted(glob.glob(os.path.join(rpi_dir, "hil_*.json")))
    assert len(trial_jsons) == 18
    for path in trial_jsons:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        assert payload.get("is_physical_hardware") is True, f"Mock/non-physical payload in {path}"
        assert payload.get("board_model") == "Raspberry Pi 4 Model B Rev 1.4"
        assert payload.get("gpio_backend") == "RPi.GPIO"
        assert payload.get("execution_status") == "Success"
        assert payload.get("error") is None
        assert payload.get("started_at_utc") and payload.get("ended_at_utc")
        assert len(payload.get("task_events", [])) > 0

