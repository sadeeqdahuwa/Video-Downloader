"""
Application Configuration
=========================
Default paths, preferences, and constants for the Video Downloader app.
"""

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Default download directory
# ---------------------------------------------------------------------------
def get_default_download_dir() -> str:
    """Return the user's Videos folder, falling back to Downloads, then home."""
    for folder_name in ("Videos", "Downloads"):
        candidate = Path.home() / folder_name
        if candidate.is_dir():
            return str(candidate)
    return str(Path.home())


# ---------------------------------------------------------------------------
# Quality presets  (label -> yt-dlp format string)
# ---------------------------------------------------------------------------
QUALITY_OPTIONS: dict[str, str] = {
    "Best Quality":  "bestvideo+bestaudio/best",
    "1080p":         "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":          "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":          "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":          "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "Audio Only":    "bestaudio/best",
}

# ---------------------------------------------------------------------------
# Concurrency / performance
# ---------------------------------------------------------------------------
DEFAULT_CONCURRENT_FRAGMENTS: int = 4

# ---------------------------------------------------------------------------
# FFmpeg detection
# ---------------------------------------------------------------------------
def find_ffmpeg() -> str | None:
    """
    Return the path to ffmpeg if it is installed, else None.
    Checks PATH first, then common Windows install locations.
    """
    import shutil

    path = shutil.which("ffmpeg")
    if path:
        return path

    # Check common Windows install locations and existing software
    common_dirs = [
        os.path.join(os.environ.get("ProgramFiles", ""), "Softdeluxe", "Free Download Manager"),
        os.path.join(os.environ.get("ProgramFiles", ""), "iTubeGo"),
        os.path.join(os.environ.get("ProgramFiles", ""), "iDownerGo"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Wondershare", "UniConverter 16"),
        os.path.join(os.environ.get("ProgramFiles", ""), "ffmpeg", "bin"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "ffmpeg", "bin"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "ffmpeg", "bin"),
        os.path.join(os.environ.get("USERPROFILE", ""), "ffmpeg", "bin"),
    ]
    for d in common_dirs:
        candidate = os.path.join(d, "ffmpeg.exe")
        if os.path.isfile(candidate):
            return candidate

    return None


# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_NAME = "Video Downloader"
APP_VERSION = "1.0.0"
