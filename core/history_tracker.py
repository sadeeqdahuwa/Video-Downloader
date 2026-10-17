"""
History & Metadata Tracker
==========================
Records detailed metadata for every download into an Excel (.xlsx) spreadsheet
and CSV backup in the user's download directory.

Captures:
  - Timestamp
  - Saved Filename & Clean Title
  - Original / Raw Title
  - Full Description Text (even if pages long, preserving full post text)
  - Source URL
  - File Size, Duration, Format
  - File Path on Disk
"""

from __future__ import annotations

import csv
import datetime
import os
import threading
from typing import Any

_LOCK = threading.Lock()

EXCEL_FILENAME = "download_history.xlsx"
CSV_FILENAME = "download_history.csv"


def get_tracker_path(save_dir: str) -> str:
    """Return the absolute path to download_history.xlsx in save_dir."""
    return os.path.join(save_dir, EXCEL_FILENAME)


def record_download_history(entry: dict[str, Any], save_dir: str) -> str:
    """
    Append a completed or failed download record to download_history.xlsx
    and download_history.csv in save_dir.
    
    Returns path to the Excel file.
    """
    os.makedirs(save_dir, exist_ok=True)
    xlsx_path = os.path.join(save_dir, EXCEL_FILENAME)
    csv_path = os.path.join(save_dir, CSV_FILENAME)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_data = [
        timestamp,
        entry.get("status", "COMPLETED"),
        entry.get("clean_title", ""),
        entry.get("filename", ""),
        entry.get("raw_title", ""),
        entry.get("description", ""),  # Full description text
        entry.get("url", ""),
        entry.get("size", "—"),
        entry.get("duration", "—"),
        entry.get("format", ""),
        entry.get("file_path", ""),
    ]

    headers = [
        "Date & Time",
        "Status",
        "Clean Title",
        "Saved Filename",
        "Raw Title",
        "Full Description (Full Post Text)",
        "Video URL",
        "File Size",
        "Duration",
        "Quality / Format",
        "File Path",
    ]

    with _LOCK:
        # 1. Append to CSV
        file_exists = os.path.isfile(csv_path)
        try:
            with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers)
                writer.writerow(row_data)
        except Exception as e:
            print(f"[Tracker] CSV write error: {e}")

        # 2. Append to Excel (.xlsx) using openpyxl
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Font, PatternFill

            wb = None
            if os.path.isfile(xlsx_path):
                try:
                    wb = openpyxl.load_workbook(xlsx_path)
                    ws = wb.active
                except Exception:
                    wb = None

            if wb is None:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Download History"
                ws.append(headers)

                # Style header row
                header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
                header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                ws.row_dimensions[1].height = 26

            # Append the row
            ws.append(row_data)
            row_idx = ws.max_row
            ws.row_dimensions[row_idx].height = 22

            # Alignment styling for cells
            regular_font = Font(name="Segoe UI", size=10)
            for col_idx, cell in enumerate(ws[row_idx], start=1):
                cell.font = regular_font
                if col_idx == 6:  # Full Description column
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                else:
                    cell.alignment = Alignment(vertical="center")

            # Column widths
            widths = {
                "A": 20,  # Date
                "B": 14,  # Status
                "C": 35,  # Clean Title
                "D": 35,  # Filename
                "E": 35,  # Raw Title
                "F": 60,  # Full Description
                "G": 40,  # Video URL
                "H": 14,  # Size
                "I": 12,  # Duration
                "J": 18,  # Format
                "K": 50,  # File Path
            }
            for col_letter, width in widths.items():
                ws.column_dimensions[col_letter].width = width

            wb.save(xlsx_path)
        except Exception as e:
            print(f"[Tracker] Excel write error: {e}")

    return xlsx_path
