"""
scripts/generate_excel_results.py
==================================
Generates beautifully formatted Excel Spreadsheets (.xlsx / .xml) and CSV data tables:
1. 2d/results/2D_SoC_Test_Scheduling_Results.xlsx (and .xml, .csv)
2. fixed_stacking/results/Fixed_3D_SoC_Test_Scheduling_Results.xlsx (and .xml, .csv)
3. random_stacking/results/Random_3D_SoC_Test_Scheduling_Results.xlsx (and .xml, .csv)

Produces genuine OpenXML (.xlsx) files via openpyxl with automatic column widths,
styled headers, cell borders, and conditional formatting for 'Safe' status tags.
Retains XML Spreadsheet 2003 (.xml) and CSV formats for 100% universal compatibility.
"""

import os
import sys
import csv
from typing import Dict, List, Any, Tuple

# Ensure project root is known
CAPSTONE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.abspath(os.path.join(CAPSTONE_DIR, ".."))
RESULTS_ROOT = os.path.join(REPO_ROOT, "results")


def _coerce_csv_value(val: str) -> Any:
    """Converts numeric CSV strings cleanly to int or float for OpenXML Excel formatting."""
    s = val.strip()
    if s == "":
        return s
    try:
        if "." not in s and "e" not in s.lower():
            return int(s)
        return float(s)
    except ValueError:
        return s


def _load_verified_csv(rel_path: str) -> Tuple[List[str], List[List[Any]]]:
    """Loads verified experimental rows from root results/; returns ([], []) if absent."""
    full_path = os.path.join(RESULTS_ROOT, rel_path)
    if not os.path.exists(full_path):
        return [], []
    with open(full_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    if not reader:
        return [], []
    return reader[0], [[_coerce_csv_value(c) for c in row] for row in reader[1:]]

# Attempt openpyxl import
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def create_excel_openpyxl(filename: str, sheets_data: Dict[str, Dict[str, Any]]) -> bool:
    """
    Creates a genuine binary OpenXML (.xlsx) workbook with multi-tab support,
    professional typography, colored header fills, and safe-status highlight badges.
    """
    if not HAS_OPENPYXL:
        return False

    wb = openpyxl.Workbook()
    default_sheet = wb.active

    # Style definitions
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    title_font = Font(name="Calibri", size=13, bold=True, color="1F4E79")
    data_font = Font(name="Calibri", size=10)
    safe_font = Font(name="Calibri", size=10, bold=True, color="006100")
    safe_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    sheet_index = 0
    for sheet_name, sheet in sheets_data.items():
        if sheet_index == 0:
            ws = default_sheet
            ws.title = sheet_name[:31]
        else:
            ws = wb.create_sheet(title=sheet_name[:31])
        sheet_index += 1

        ws.views.sheetView[0].showGridLines = True
        curr_row = 1

        # Title row if present
        if "title" in sheet:
            ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=len(sheet["headers"]))
            title_cell = ws.cell(row=curr_row, column=1, value=sheet["title"])
            title_cell.font = title_font
            title_cell.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[curr_row].height = 28
            curr_row += 2

        # Header row
        ws.row_dimensions[curr_row].height = 26
        for col_idx, header in enumerate(sheet["headers"], start=1):
            cell = ws.cell(row=curr_row, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border
        curr_row += 1

        # Data rows
        for row in sheet["rows"]:
            ws.row_dimensions[curr_row].height = 20
            for col_idx, val in enumerate(row, start=1):
                cell = ws.cell(row=curr_row, column=col_idx, value=val)
                cell.font = data_font
                cell.alignment = center_align
                cell.border = thin_border

                val_str = str(val).strip()
                if val_str in ("Safe", "Passed", "Optimal"):
                    cell.font = safe_font
                    cell.fill = safe_fill

            curr_row += 1

        # Auto-adjust column width
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    lines = str(cell.value).split("\n")
                    for l in lines:
                        if len(l) > max_len:
                            max_len = len(l)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(filename)
    print(f"Generated genuine OpenXML (.xlsx): '{filename}'")
    return True


def create_excel_xml(filename: str, sheets_data: dict):
    """
    Creates an Excel XML Spreadsheet (.xml) file compatible with
    all spreadsheet software without third-party dependencies.
    """
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<?mso-application progid="Excel.Sheet"?>',
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
        ' xmlns:o="urn:schemas-microsoft-com:office:office"',
        ' xmlns:x="urn:schemas-microsoft-com:office:excel"',
        ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"',
        ' xmlns:html="http://www.w3.org/TR/REC-html40">',
        ' <Styles>',
        '  <Style ss:ID="Default" ss:Name="Normal">',
        '   <Alignment ss:Vertical="Bottom"/>',
        '   <Font ss:FontName="Calibri" ss:Size="11" ss:Color="#000000"/>',
        '  </Style>',
        '  <Style ss:ID="Header">',
        '   <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>',
        '   <Font ss:FontName="Calibri" ss:Size="11" ss:Color="#FFFFFF" ss:Bold="1"/>',
        '   <Interior ss:Color="#1F4E79" ss:Pattern="Solid"/>',
        '  </Style>',
        '  <Style ss:ID="Title">',
        '   <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>',
        '   <Font ss:FontName="Calibri" ss:Size="13" ss:Color="#1F4E79" ss:Bold="1"/>',
        '  </Style>',
        '  <Style ss:ID="DataCell">',
        '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
        '   <Font ss:FontName="Calibri" ss:Size="10"/>',
        '  </Style>',
        '  <Style ss:ID="SafeStatus">',
        '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
        '   <Font ss:FontName="Calibri" ss:Size="10" ss:Color="#006100" ss:Bold="1"/>',
        '   <Interior ss:Color="#C6EFCE" ss:Pattern="Solid"/>',
        '  </Style>',
        ' </Styles>'
    ]

    for sheet_name, sheet in sheets_data.items():
        xml_lines.append(f' <Worksheet ss:Name="{sheet_name}">')
        xml_lines.append('  <Table>')

        if "title" in sheet:
            xml_lines.append('   <Row ss:Height="25">')
            xml_lines.append(f'    <Cell ss:StyleID="Title"><Data ss:Type="String">{sheet["title"]}</Data></Cell>')
            xml_lines.append('   </Row>')
            xml_lines.append('   <Row ss:Height="10"/>')

        xml_lines.append('   <Row ss:Height="24">')
        for h in sheet["headers"]:
            xml_lines.append(f'    <Cell ss:StyleID="Header"><Data ss:Type="String">{h}</Data></Cell>')
        xml_lines.append('   </Row>')

        for row in sheet["rows"]:
            xml_lines.append('   <Row ss:Height="20">')
            for cell in row:
                cell_str = str(cell)
                if cell_str in ("Safe", "Passed", "Optimal"):
                    style = ' ss:StyleID="SafeStatus"'
                    dtype = 'String'
                elif isinstance(cell, (int, float)):
                    style = ' ss:StyleID="DataCell"'
                    dtype = 'Number'
                else:
                    style = ' ss:StyleID="DataCell"'
                    dtype = 'String'
                xml_lines.append(f'    <Cell{style}><Data ss:Type="{dtype}">{cell_str}</Data></Cell>')
            xml_lines.append('   </Row>')

        xml_lines.append('  </Table>')
        xml_lines.append(' </Worksheet>')

    xml_lines.append('</Workbook>')

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_lines))
    print(f"Generated XML Spreadsheet: '{filename}'")


def create_csv_files(base_dir: str, sheets_data: dict):
    """Generates standalone CSV data tables for a results folder."""
    os.makedirs(base_dir, exist_ok=True)
    for sheet_name, sheet in sheets_data.items():
        clean_name = sheet_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
        csv_path = os.path.join(base_dir, f"{clean_name}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if "title" in sheet:
                writer.writerow([sheet["title"]])
                writer.writerow([])
            writer.writerow(sheet["headers"])
            writer.writerows(sheet["rows"])
        print(f"Generated CSV Table: '{csv_path}'")


def save_reports(target_dir: str, base_filename: str, sheets_data: dict):
    """Saves both .xlsx, .xml, and individual .csv files to target_dir."""
    os.makedirs(target_dir, exist_ok=True)
    xlsx_path = os.path.join(target_dir, f"{base_filename}.xlsx")
    xml_path = os.path.join(target_dir, f"{base_filename}.xml")

    # Generate genuine openpyxl .xlsx if available
    created_xlsx = create_excel_openpyxl(xlsx_path, sheets_data)
    if not created_xlsx:
        create_excel_xml(xlsx_path, sheets_data)

    create_excel_xml(xml_path, sheets_data)
    create_csv_files(target_dir, sheets_data)


# ============================================================================
# 1. 2D PLANAR RESULTS (LOADED FROM VERIFIED MEASUREMENTS IN results/)
# ============================================================================
def generate_2d_results(custom_dir: str = None, live_data: dict = None):
    dir_2d = custom_dir or os.path.join(CAPSTONE_DIR, "2d", "results")

    hdr_wrap, rows_wrap = _load_verified_csv(os.path.join("simulation", "2d", "ieee1500_wrapper_sweep.csv"))
    hdr_sched, rows_sched = _load_verified_csv(os.path.join("simulation", "2d", "2d_scheduling_summary.csv"))
    hdr_hil, rows_hil = _load_verified_csv(os.path.join("hardware", "2d", "rpi_2d_summary.csv"))

    sheets = {
        "IEEE 1500 Wrapper Analysis": {
            "title": "IEEE 1500 Wrapper Design & Test Time Reduction (Iyengar et al., IEEE TCAD 2002)",
            "headers": hdr_wrap or ["Benchmark", "TAM Width (w)", "Pre-Wrapper Raw Cycles", "Post-Wrapper IEEE 1500 Cycles", "Cycles Saved", "Reduction %"],
            "rows": live_data.get("ieee1500_wrapper", rows_wrap) if live_data else rows_wrap,
        },
        "2D Scheduling Summary": {
            "title": "2D Planar Multi-Seed Fair-Budget Statistical Summary (6 Algorithms, N=10 Seeds)",
            "headers": hdr_sched or ["Mode", "Benchmark", "Algorithm", "N Seeds", "Best (CC)", "Worst (CC)", "Mean (CC)", "Median (CC)", "Std Dev (CC)", "Reduction %", "Mean Evals", "Mean Runtime (s)", "Worst Power (W)", "Worst Peak Tj", "Max TAM Used", "Status"],
            "rows": live_data.get("2d_scheduling", rows_sched) if live_data else rows_sched,
        },
        "2D HIL Replay": {
            "title": "2D Hardware-in-the-Loop (HIL) Physical Raspberry Pi 4 Model B Rev 1.4 Measurements",
            "headers": hdr_hil or ["Mode", "Benchmark", "Algorithm", "Trials", "Is Physical", "Board Model", "GPIO Backend", "Makespan (CC)", "Total Task Cycles", "Scaled Makespan (s)", "Expected Sleep (s)", "Mean Wall Clock (s)", "Std Wall Clock (s)", "Mean Roundtrip (s)", "Mean Jitter (s)", "Mean Overhead %", "GPIO Events"],
            "rows": live_data.get("2d_hil", rows_hil) if live_data else rows_hil,
        },
    }

    save_reports(dir_2d, "2D_SoC_Test_Scheduling_Results", sheets)


# ============================================================================
# 2. FIXED 3D STACKING RESULTS (LOADED FROM VERIFIED MEASUREMENTS IN results/)
# ============================================================================
def generate_fixed_results(custom_dir: str = None, live_data: dict = None):
    dir_fixed = custom_dir or os.path.join(CAPSTONE_DIR, "fixed_stacking", "results")

    hdr_sweep, rows_sweep = _load_verified_csv(os.path.join("simulation", "fixed_3d", "fixed3d_multi_tam_sweep.csv"))
    hdr_sched, rows_sched = _load_verified_csv(os.path.join("simulation", "fixed_3d", "fixed3d_scheduling_summary.csv"))
    hdr_hil, rows_hil = _load_verified_csv(os.path.join("hardware", "fixed_3d", "rpi_fixed3d_summary.csv"))

    sheets = {
        "Multi-TAM Sweep (Paper Format)": {
            "title": "Fixed 3D Multi-TAM Width Sweep Evaluation (All 6 Algorithms, max_evals=300)",
            "headers": hdr_sweep or ["Benchmark", "TAM Width", "Algorithm", "Makespan (CC)", "TSV Used", "TSV Budget", "Eval Count", "Runtime (s)", "Peak Power (W)", "Max Power (W)", "Peak Tj (C)", "Status"],
            "rows": live_data.get("multi_tam_sweep", rows_sweep) if live_data else rows_sweep,
        },
        "Fixed Stacking Summary": {
            "title": "Structured Fixed 3D Multi-Seed Fair-Budget Statistical Summary (6 Algorithms, N=10 Seeds)",
            "headers": hdr_sched or ["Mode", "Benchmark", "Algorithm", "N Seeds", "Best (CC)", "Worst (CC)", "Mean (CC)", "Median (CC)", "Std Dev (CC)", "Reduction %", "Mean Evals", "Mean Runtime (s)", "Worst Power (W)", "Worst Peak Tj (C)", "Max TSV Used", "Status"],
            "rows": live_data.get("fixed_scheduling", rows_sched) if live_data else rows_sched,
        },
        "Fixed Core Partitioning Table": {
            "title": "Fixed 3D Layer Core Distribution Table (Roy & Giri, 2023 Table 2 Mapping)",
            "headers": ["Layer ID", "Layer Description", "p22810 Core Module Assignments", "d695 Core Module Assignments"],
            "rows": [
                ["Layer 1 (z=0)", "Bottom Die (Substrate/Heatsink)", "Cores 1, 2, 3, 5, 6, 8, 9, 15, 21, 26, 27 (11 cores)", "Cores 1, 2, 7, 10 (4 cores)"],
                ["Layer 2 (z=1)", "Middle Die Layer", "Cores 4, 7, 10, 11, 17, 18, 22, 23, 25, 28 (10 cores)", "Cores 3, 4, 8 (3 cores)"],
                ["Layer 3 (z=2)", "Top Die Layer", "Cores 12, 13, 14, 16, 19, 20, 24, 29, 30 (9 cores)", "Cores 5, 6, 9 (3 cores)"],
            ],
        },
        "Fixed 3D HIL Replay": {
            "title": "Fixed 3D Physical Raspberry Pi 4 Model B Rev 1.4 HIL Summary",
            "headers": hdr_hil or ["Mode", "Benchmark", "Algorithm", "Trials", "Is Physical", "Board Model", "GPIO Backend", "Makespan (CC)", "Total Task Cycles", "Scaled Makespan (s)", "Expected Sleep (s)", "Mean Wall Clock (s)", "Std Wall Clock (s)", "Mean Roundtrip (s)", "Mean Jitter (s)", "Mean Overhead %", "GPIO Events"],
            "rows": live_data.get("fixed_hil", rows_hil) if live_data else rows_hil,
        },
    }

    save_reports(dir_fixed, "Fixed_3D_SoC_Test_Scheduling_Results", sheets)


# ============================================================================
# 3. RANDOM 3D STACKING RESULTS (LOADED FROM VERIFIED MEASUREMENTS IN results/)
# ============================================================================
def generate_random_results(custom_dir: str = None, live_data: dict = None):
    dir_random = custom_dir or os.path.join(CAPSTONE_DIR, "random_stacking", "results")

    hdr_stats, rows_stats = _load_verified_csv(os.path.join("simulation", "random_3d", "random3d_scheduling_summary.csv"))
    hdr_hil, rows_hil = _load_verified_csv(os.path.join("hardware", "random_3d", "rpi_random3d_summary.csv"))
    hdr_ml, rows_ml = _load_verified_csv(os.path.join("simulation", "random_3d", "ml_thermal_regression_metrics.csv"))
    hdr_traj, rows_traj = _load_verified_csv(os.path.join("simulation", "random_3d", "ml_thermal_trajectory_validation.csv"))

    sheets = {
        "Multi-Seed Statistical Results": {
            "title": "Dynamic Random 3D Multi-Seed Statistical Performance (6 Algorithms, N=10 Seeds, Fair Budget)",
            "headers": hdr_stats or ["Mode", "Benchmark", "Algorithm", "N Seeds", "Best (CC)", "Worst (CC)", "Mean (CC)", "Median (CC)", "Std Dev (CC)", "Reduction %", "Mean Evals", "Mean Runtime (s)", "Worst Power (W)", "Worst Peak Tj (C)", "Max TSV Used", "Status"],
            "rows": live_data.get("random_scheduling", rows_stats) if live_data else rows_stats,
        },
        "3D HIL Replay Summary": {
            "title": "Random 3D Physical Raspberry Pi 4 Model B Rev 1.4 HIL Replay Summary",
            "headers": hdr_hil or ["Mode", "Benchmark", "Algorithm", "Trials", "Is Physical", "Board Model", "GPIO Backend", "Makespan (CC)", "Total Task Cycles", "Scaled Makespan (s)", "Expected Sleep (s)", "Mean Wall Clock (s)", "Std Wall Clock (s)", "Mean Roundtrip (s)", "Mean Jitter (s)", "Mean Overhead %", "GPIO Events"],
            "rows": live_data.get("random_hil", rows_hil) if live_data else rows_hil,
        },
        "ML Thermal Regression": {
            "title": "Deduplicated (0% Overlap) ML Thermal Regression Metrics (Model-Generated RC Reference)",
            "headers": hdr_ml or ["RC Architecture", "Model", "Degree", "Train N", "Test N", "Overlap", "Train MAE (C)", "Train RMSE (C)", "Train R2", "Test MAE (C)", "Test RMSE (C)", "Test Max Err (C)", "Test R2", "Train Time (s)", "Inference (ms/sample)", "Reference Source"],
            "rows": live_data.get("ml_thermal", rows_ml) if live_data else rows_ml,
        },
    }
    if rows_traj:
        sheets["Unseen Solver Trajectories"] = {
            "title": "Independent Unseen Solver Schedule Trajectory ML Validation (seeds=512,777,1024)",
            "headers": hdr_traj,
            "rows": rows_traj,
        }

    save_reports(dir_random, "Random_3D_SoC_Test_Scheduling_Results", sheets)


def export_custom_run(output_dir: str, benchmark_name: str, mode_name: str, results_dict: dict):
    """
    Exports a live simulation run into genuine .xlsx, .xml, and .csv files.
    """
    os.makedirs(output_dir, exist_ok=True)
    rows = []
    for alg_name, res in results_dict.items():
        peak_tj = getattr(res, "peak_temperature", 0.0)
        max_tsv = getattr(res, "max_tsv_used", getattr(res, "max_tam_used", 0))
        evals = getattr(res, "eval_count", 0)
        runtime = getattr(res, "runtime_sec", 0.0)
        rows.append([
            benchmark_name,
            alg_name,
            res.makespan,
            round(res.peak_power, 2),
            round(peak_tj, 1),
            max_tsv,
            evals,
            round(runtime, 4),
            res.constraint_status
        ])

    sheets = {
        f"{mode_name.upper()} {benchmark_name.upper()}": {
            "title": f"Live Simulation Run: {mode_name.upper()} - {benchmark_name.upper()}",
            "headers": ["Benchmark", "Algorithm", "Makespan (Cycles)", "Peak Power (W)", "Peak Tj (°C)", "Max TSV/TAM", "Evaluations", "Runtime (s)", "Constraint Status"],
            "rows": rows
        }
    }

    base_name = f"Live_Results_{mode_name}_{benchmark_name}"
    save_reports(output_dir, base_name, sheets)


def main():
    print("\n==========================================================================")
    print("   GENERATING GENUINE OPENXML (.xlsx), XML & CSV DATA TABLES FOR ALL RESULTS")
    print("==========================================================================")

    generate_2d_results()
    generate_fixed_results()
    generate_random_results()

    print("\n==========================================================================")
    print("   ALL EXCEL SPREADSHEETS AND CSV TABLES GENERATED SUCCESSFULLY!")
    print("==========================================================================")


if __name__ == "__main__":
    main()
