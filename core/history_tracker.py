"""
History & Metadata Tracker with Cloud Sync
===========================================
Records detailed metadata for every download into an Excel (.xlsx) spreadsheet
and CSV backup in:
  1. The user's local save directory (e.g. C:\\Users\\sadee\\Videos)
  2. The project's tracker/ directory (synced to the GitHub cloud repository)

Captures:
  - Download Date & Time (YYYY-MM-DD HH:MM:SS)
  - Status (COMPLETED / FAILED)
  - Clean Title
  - Saved Filename on Disk
  - Raw / Original Title
  - Full Description Text (full video post text, paragraphs intact)
  - Video Source URL
  - File Size, Duration, Format
  - File Path on Disk
"""

from __future__ import annotations

import csv
import datetime
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable

_LOCK = threading.Lock()
_GIT_LOCK = threading.Lock()

EXCEL_FILENAME = "download_history.xlsx"
CSV_FILENAME = "download_history.csv"

# Root project repository directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_TRACKER_DIR = os.path.join(PROJECT_ROOT, "tracker")


def get_tracker_path(save_dir: str | None = None) -> str:
    """Return path to download_history.xlsx, preferring save_dir then repo tracker."""
    if save_dir and os.path.isdir(save_dir):
        return os.path.join(save_dir, EXCEL_FILENAME)
    return os.path.join(REPO_TRACKER_DIR, EXCEL_FILENAME)


def _write_single_location(entry: dict[str, Any], target_dir: str, timestamp: str) -> str:
    """Helper to append row to CSV and XLSX inside a given directory."""
    os.makedirs(target_dir, exist_ok=True)
    xlsx_path = os.path.join(target_dir, EXCEL_FILENAME)
    csv_path = os.path.join(target_dir, CSV_FILENAME)

    headers = [
        "Download Date & Time",
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

    desc = str(entry.get("description", "") or "")
    if len(desc) > 32000:
        desc = desc[:32000] + "... [truncated]"

    row_data = [
        timestamp,
        entry.get("status", "COMPLETED"),
        entry.get("clean_title", ""),
        entry.get("filename", ""),
        entry.get("raw_title", ""),
        desc,
        entry.get("url", ""),
        entry.get("size", "—"),
        entry.get("duration", "—"),
        entry.get("format", ""),
        entry.get("file_path", ""),
    ]

    # 1. Append to CSV
    file_exists = os.path.isfile(csv_path)
    try:
        with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row_data)
    except Exception as e:
        print(f"[Tracker] CSV write error in {target_dir}: {e}")

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

            header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 26

        ws.append(row_data)
        row_idx = ws.max_row
        ws.row_dimensions[row_idx].height = 24

        regular_font = Font(name="Segoe UI", size=10)
        for col_idx, cell in enumerate(ws[row_idx], start=1):
            cell.font = regular_font
            if col_idx == 6:  # Full Description
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            else:
                cell.alignment = Alignment(vertical="center")

        widths = {
            "A": 22,  # Date & Time
            "B": 14,  # Status
            "C": 35,  # Clean Title
            "D": 35,  # Filename
            "E": 35,  # Raw Title
            "F": 65,  # Full Description
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
        print(f"[Tracker] Excel write error in {target_dir}: {e}")

    return xlsx_path


def record_download_history(
    entry: dict[str, Any],
    save_dir: str,
    sync_cloud: bool = True,
    log_callback: Callable[[str], None] | None = None,
) -> str:
    """
    Append download record to both the local save directory and the repository
    tracker directory, and optionally push to GitHub cloud in the background.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with _LOCK:
        # Write to local save_dir
        local_xlsx = _write_single_location(entry, save_dir, timestamp)

        # Write to repo tracker_dir if different from save_dir
        if os.path.abspath(save_dir) != os.path.abspath(REPO_TRACKER_DIR):
            _write_single_location(entry, REPO_TRACKER_DIR, timestamp)

    # Sync to GitHub Cloud in a background thread
    if sync_cloud:
        threading.Thread(
            target=sync_tracker_to_cloud,
            args=(log_callback,),
            daemon=True,
        ).start()

    return local_xlsx


def sync_tracker_to_cloud(log_callback: Callable[[str], None] | None = None) -> dict[str, Any]:
    """
    Commit and push the tracker directory (Excel + CSV) to GitHub cloud.
    """
    def _log(msg: str) -> None:
        if log_callback:
            log_callback(f"[CLOUD SYNC] {msg}")
        else:
            print(f"[CLOUD SYNC] {msg}")

    with _GIT_LOCK:
        try:
            os.makedirs(REPO_TRACKER_DIR, exist_ok=True)
            # Check if git is available
            status = subprocess.run(
                ["git", "status", "--porcelain", "tracker/"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            if not status.stdout.strip():
                _log("Tracker spreadsheets are already up to date on GitHub cloud.")
                return {"success": True, "message": "Already up to date"}

            # Stage tracker files
            subprocess.run(["git", "add", "tracker/"], cwd=PROJECT_ROOT, check=True)

            # Commit
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"tracker: sync download history to cloud ({now_str})"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT, check=True)

            # Push to origin main
            push_res = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            if push_res.returncode == 0:
                _log(f"Successfully pushed Excel and CSV trackers to GitHub cloud ({now_str})")
                return {"success": True, "message": "Pushed to GitHub cloud"}
            else:
                _log(f"Git push warning: {push_res.stderr.strip()}")
                return {"success": False, "error": push_res.stderr.strip()}

        except Exception as e:
            _log(f"Failed to sync to GitHub cloud: {e}")
            return {"success": False, "error": str(e)}
