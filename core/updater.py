"""
Application & Extractor Auto-Updater
====================================
Allows the application to receive updates without needing a manual reinstallation:
  1. Extractor Engine Updates (yt-dlp):
     Platforms (Facebook, YouTube, Instagram) change their video player formats frequently.
     The app can update the extraction algorithms on-the-fly without rebuilding the .exe!
  2. GitHub Release Updates & In-Place Self-Updating:
     Checks your GitHub repository for new releases, compares version tags,
     and allows 1-click in-app updating where the app automatically downloads,
     replaces its own files, and restarts—without requiring any manual installation wizard.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from typing import Any, Callable

from core.config import APP_VERSION

REPO_OWNER = "sadeeqdahuwa"
REPO_NAME = "Video-Downloader"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


def _get_auth_headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": "AllVideoDownloaderPro-Updater",
        "Accept": "application/vnd.github.v3+json",
    }
    gh_token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"
    return headers


def check_for_app_updates(token: str | None = None) -> dict[str, Any]:
    """
    Check GitHub Releases for a newer version of the application.
    Returns update status, latest version tag, release notes, and download link.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers=_get_auth_headers(token),
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                latest_tag = data.get("tag_name", "").lstrip("v")
                current_clean = APP_VERSION.lstrip("v")

                def _parse_v(v: str) -> tuple[int, ...]:
                    parts = []
                    for x in v.split("."):
                        digits = "".join(ch for ch in x if ch.isdigit())
                        parts.append(int(digits) if digits else 0)
                    return tuple(parts)

                latest_tuple = _parse_v(latest_tag)
                current_tuple = _parse_v(current_clean)
                has_update = latest_tuple > current_tuple

                # Locate download asset
                download_url = data.get("html_url", "")
                assets = data.get("assets", [])
                for asset in assets:
                    if asset.get("name", "").endswith(".zip"):
                        download_url = asset.get("browser_download_url", download_url)
                        break

                return {
                    "has_update": has_update,
                    "current_version": APP_VERSION,
                    "latest_version": latest_tag,
                    "release_notes": data.get("body", "Bug fixes and performance enhancements."),
                    "download_url": download_url,
                    "release_page": data.get("html_url", ""),
                }
    except Exception as e:
        return {
            "has_update": False,
            "current_version": APP_VERSION,
            "error": str(e),
        }

    return {"has_update": False, "current_version": APP_VERSION}


def download_and_apply_update(
    download_url: str,
    token: str | None = None,
    log_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Downloads the new release zip file, unpacks it to a staging folder,
    and launches a detached Windows batch script that waits for this process
    to exit, replaces the files in-place, and relaunches the app.
    Zero manual re-installation needed!
    """
    def _log(msg: str) -> None:
        if log_callback:
            log_callback(f"[AUTO-UPDATER] {msg}")
        else:
            print(f"[AUTO-UPDATER] {msg}")

    try:
        _log(f"Downloading update package from {download_url}...")
        temp_dir = os.path.join(tempfile.gettempdir(), "AllVideoDownloaderPro_Update")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        os.makedirs(temp_dir, exist_ok=True)

        zip_dest = os.path.join(temp_dir, "update.zip")
        extracted_dir = os.path.join(temp_dir, "extracted")

        req = urllib.request.Request(
            download_url,
            headers=_get_auth_headers(token),
        )

        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_dest, "wb") as f_out:
            shutil.copyfileobj(resp, f_out)

        _log("Download complete. Extracting update archive...")
        with zipfile.ZipFile(zip_dest, "r") as zf:
            zf.extractall(extracted_dir)

        # Determine target application directory
        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            target_app_dir = os.path.dirname(os.path.abspath(sys.executable))
            target_exe = sys.executable
        else:
            target_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            target_exe = sys.executable  # python executable

        # Check if the extracted directory has a nested root folder
        source_dir = extracted_dir
        nested_candidates = [
            os.path.join(extracted_dir, "AllVideoDownloaderPro"),
            os.path.join(extracted_dir, "Video-Downloader"),
        ]
        for c in nested_candidates:
            if os.path.isdir(c):
                source_dir = c
                break

        _log(f"Target directory: {target_app_dir}")
        _log(f"Staging directory: {source_dir}")

        # Create Windows self-update script
        updater_bat = os.path.join(temp_dir, "apply_update.bat")
        pid = os.getpid()

        if is_frozen:
            relaunch_cmd = f'start "" "{target_exe}"'
        else:
            main_script = os.path.join(target_app_dir, "web_app.py")
            relaunch_cmd = f'start "" "{target_exe}" "{main_script}"'

        bat_content = f"""@echo off
chcp 65001 >nul
echo =======================================================
echo All Video Downloader Pro - Applying Automatic Update
echo =======================================================
echo Waiting for application (PID {pid}) to shut down...
timeout /t 2 /nobreak >nul

:: Overwrite files in target directory
echo Copying new application files...
xcopy /s /e /y /q "{source_dir}\\*" "{target_app_dir}\\"

echo Relaunching All Video Downloader Pro...
{relaunch_cmd}

:: Clean up updater folder after short delay
timeout /t 3 /nobreak >nul
(goto) 2>nul & rd /s /q "{temp_dir}"
exit
"""
        with open(updater_bat, "w", encoding="utf-8") as bf:
            bf.write(bat_content)

        _log("Update ready. Spawning background updater and restarting application...")

        # Spawn detached process
        if sys.platform == "win32":
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                ["cmd.exe", "/c", updater_bat],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )

        # Trigger clean exit of current application after 1 second
        def _delayed_exit():
            time.sleep(1.2)
            os._exit(0)

        threading.Thread(target=_delayed_exit, daemon=True).start()

        return {"success": True, "message": "Update downloaded. Restarting application..."}

    except Exception as e:
        _log(f"In-place update failed: {e}")
        return {"success": False, "error": str(e)}


def update_extractor_engine(log_callback: Callable[[str], None] | None = None) -> dict[str, Any]:
    """
    Update yt-dlp extractor definitions directly so video downloading never breaks
    when Facebook or YouTube update their website designs.
    """
    def _log(msg: str) -> None:
        if log_callback:
            log_callback(f"[EXTRACTOR] {msg}")
        else:
            print(f"[EXTRACTOR] {msg}")

    _log("Checking for upstream yt-dlp extractor definitions update...")

    try:
        # Check if running from python / venv
        python_exe = sys.executable
        res = subprocess.run(
            [python_exe, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=45,
        )

        if res.returncode == 0:
            _log("yt-dlp engine updated to the latest available version successfully!")
            return {"success": True, "output": res.stdout.strip()}
        else:
            _log(f"Extractor update notice: {res.stderr.strip() or res.stdout.strip()}")
            return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}

    except Exception as e:
        _log(f"Extractor update failed: {e}")
        return {"success": False, "error": str(e)}
