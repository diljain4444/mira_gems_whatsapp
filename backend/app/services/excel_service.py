"""
services/excel_service.py

Professional Excel report generation using pandas + openpyxl.
Generates reports entirely in memory (BytesIO) — no temp files are
permanently saved to disk.

This service is completely independent of the Chrome extension so the
same function can be reused by a future Tauri desktop or web application.
"""
import io
from datetime import datetime
from typing import Optional

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ── Report column definitions ─────────────────────────────────────────────────
# (field_key, display_header, column_width)
REPORT_COLUMNS: list[tuple[str, str, int]] = [
    ("StockId",            "Stock ID",          14),
    ("Availability",       "Availability",       13),
    ("Shape",              "Shape",              12),
    ("Weight",             "Carat",              10),
    ("Color",              "Color",               8),
    ("Clarity",            "Clarity",            10),
    ("Cut",                "Cut",                 8),
    ("Polish",             "Polish",             10),
    ("Symm",               "Symmetry",           11),
    ("business_category",  "Category",           11),
    ("Lab",                "Lab",                10),
    ("Fls",                "Fluorescence",       14),
    ("FinalPrice",         "Final Price (USD)",  18),
    ("Location",           "Location",           14),
    ("Measurements",       "Measurements",       24),
]


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def generate_excel_report(
    matched_diamonds: list[dict],
    customer_message: str,
    extracted_requirement: dict,
    total_inventory: int,
    total_available: int,
    total_matched: int,
    total_available_not_matched: int,
) -> bytes:
    """
    Generate a professional branded Excel workbook and return raw bytes.

    Sheet 1: Matched Diamonds — full stone data with formatting.
    Sheet 2: Summary — extracted requirements + inventory statistics.
    """
    now = datetime.now()
    report_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # ── Build DataFrame for Sheet 1 ──────────────────────────────────────────
    rows = []
    for diamond in matched_diamonds:
        row = {field: _safe_str(diamond.get(field, "")) for field, _, _ in REPORT_COLUMNS}
        rows.append(row)

    df = pd.DataFrame(rows, columns=[f for f, _, _ in REPORT_COLUMNS])

    # ── Build DataFrame for Sheet 2 (Summary) ────────────────────────────────
    req = extracted_requirement or {}
    color_val = req.get("color", "") or ""
    if isinstance(color_val, list):
        color_val = ", ".join(color_val)
    clarity_val = req.get("clarity", "") or ""
    if isinstance(clarity_val, list):
        clarity_val = ", ".join(clarity_val)

    carat_min = req.get("carat_min")
    carat_max = req.get("carat_max")
    if carat_min is not None and carat_max is not None:
        carat_display = f"{carat_min} – {carat_max} ct"
    elif carat_min is not None:
        carat_display = f"≥ {carat_min} ct"
    elif carat_max is not None:
        carat_display = f"≤ {carat_max} ct"
    else:
        carat_display = "—"

    summary_data = [
        ("Report Generated",          report_time),
        ("Customer Requirement",       customer_message or "—"),
        ("",                          ""),
        ("── Extracted Requirements",  ""),
        ("Shape",                      _safe_str(req.get("shape")) or "—"),
        ("Color",                      color_val or "—"),
        ("Clarity",                    clarity_val or "—"),
        ("Carat",                      carat_display),
        ("Business Category",          _safe_str(req.get("business_category")) or "—"),
        ("Certification",              _safe_str(req.get("certification")) or "—"),
        ("Fluorescence",               _safe_str(req.get("fluorescence")) or "—"),
        ("",                          ""),
        ("── Inventory Statistics",    ""),
        ("Total Inventory Fetched",    total_inventory),
        ("Total Available Stones",     total_available),
        ("Matched Stones",             total_matched),
        ("Available (Not Matched)",    total_available_not_matched),
    ]
    df_summary = pd.DataFrame(summary_data, columns=["Metric", "Value"])

    # ── Write to BytesIO via ExcelWriter ─────────────────────────────────────
    TITLE_ROWS = 4   # rows reserved for branding above the data header

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer, sheet_name="Matched Diamonds",
            index=False, startrow=TITLE_ROWS
        )
        df_summary.to_excel(
            writer, sheet_name="Summary",
            index=False
        )
    output.seek(0)

    wb = load_workbook(output)

    # ── Style: Sheet 1 — Matched Diamonds ────────────────────────────────────
    ws1 = wb["Matched Diamonds"]
    num_cols = len(REPORT_COLUMNS)
    last_col_letter = get_column_letter(num_cols)

    # Title block
    _merge_title_row(ws1, 1, num_cols, "MIRA GEMS  ·  Diamond Matching Report",
                     font_size=15, bold=True, fg="1A1A2E", text_color="C4A35A")
    ws1.row_dimensions[1].height = 28

    _merge_title_row(ws1, 2, num_cols, f"Generated: {report_time}",
                     font_size=9, bold=False, fg="1A1A2E", text_color="888899")
    ws1.row_dimensions[2].height = 16

    _merge_title_row(ws1, 3, num_cols,
                     f"Customer Requirement:  {customer_message}",
                     font_size=10, bold=True, fg="12121A", text_color="E8D5A3")
    ws1.row_dimensions[3].height = 20

    _merge_title_row(ws1, 4, num_cols,
                     f"Matched: {total_matched}   ·   Available: {total_available}   ·   Total Inventory: {total_inventory}",
                     font_size=9, bold=False, fg="12121A", text_color="8888A8")
    ws1.row_dimensions[4].height = 16

    # Header row (row 5, pandas startrow=4 → Excel row 5)
    HEADER_ROW = TITLE_ROWS + 1
    header_fill = PatternFill("solid", fgColor="0F3460")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws1.row_dimensions[HEADER_ROW].height = 22

    for col_idx, (_, label, width) in enumerate(REPORT_COLUMNS, start=1):
        cell = ws1.cell(row=HEADER_ROW, column=col_idx)
        cell.value = label
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        ws1.column_dimensions[get_column_letter(col_idx)].width = width

    # Data rows
    thin = Side(style="thin", color="E0E0E0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    avail_colors = {
        "AVAILABLE": "E8F5E9",
        "A":         "E8F5E9",
        "MEMO":      "FFF8E1",
        "M":         "FFF8E1",
        "HOLD":      "FFEBEE",
        "H":         "FFEBEE",
    }
    data_start = HEADER_ROW + 1

    for row_idx in range(data_start, data_start + len(matched_diamonds)):
        # Read availability from the Availability column (col 2)
        avail_val = _safe_str(ws1.cell(row=row_idx, column=2).value).upper()
        row_color = avail_colors.get(avail_val, "FFFFFF")

        for col_idx in range(1, num_cols + 1):
            cell = ws1.cell(row=row_idx, column=col_idx)
            # Availability column gets colour; others white
            fill_color = row_color if col_idx == 2 else "FFFFFF"
            cell.fill = PatternFill("solid", fgColor=fill_color)
            cell.border = border
            cell.font = Font(name="Calibri", size=9)
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Freeze pane below header
    ws1.freeze_panes = ws1.cell(row=data_start, column=1)

    # Auto-filter on header row
    if matched_diamonds:
        ws1.auto_filter.ref = (
            f"A{HEADER_ROW}:{last_col_letter}{data_start - 1 + len(matched_diamonds)}"
        )

    # ── Style: Sheet 2 — Summary ─────────────────────────────────────────────
    ws2 = wb["Summary"]
    ws2.column_dimensions["A"].width = 32
    ws2.column_dimensions["B"].width = 48

    header_row_2 = ws2[1]
    for cell in header_row_2:
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="0F3460")
        cell.alignment = Alignment(horizontal="left")

    section_font = Font(name="Calibri", bold=True, color="0F3460", size=10)
    alt_fill = PatternFill("solid", fgColor="F0F4FF")

    for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row):
        label = _safe_str(row[0].value)
        if label.startswith("──"):
            for cell in row:
                cell.font = section_font
                cell.fill = alt_fill
        else:
            for cell in row:
                cell.font = Font(name="Calibri", size=9)

    # ── Return as bytes ───────────────────────────────────────────────────────
    final_buf = io.BytesIO()
    wb.save(final_buf)
    final_buf.seek(0)
    return final_buf.read()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _merge_title_row(
    ws, row: int, num_cols: int, text: str,
    font_size: int, bold: bool, fg: str, text_color: str
) -> None:
    """Merge a full-width title row and apply styling."""
    last_letter = get_column_letter(num_cols)
    ws.merge_cells(f"A{row}:{last_letter}{row}")
    cell = ws.cell(row=row, column=1)
    cell.value = text
    cell.font = Font(name="Calibri", size=font_size, bold=bold, color=text_color)
    cell.fill = PatternFill("solid", fgColor=fg)
    cell.alignment = Alignment(horizontal="center", vertical="center")
