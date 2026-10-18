"""
Application Configuration
=========================
Default paths, preferences, and constants for the Video Downloader app.
"""

import os
from pathlib import Path


def _load_env_file() -> None:
    """Load key-value pairs from .env into os.environ if present."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass


_load_env_file()


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

    # Check current working directory, executable dir, and app root
    current_dir = os.getcwd()
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_candidates = [
        os.path.join(current_dir, "ffmpeg.exe"),
        os.path.join(app_dir, "ffmpeg.exe"),
        os.path.join(current_dir, "_internal", "ffmpeg.exe"),
        os.path.join(app_dir, "_internal", "ffmpeg.exe"),
    ]
    for c in local_candidates:
        if os.path.isfile(c):
            return c

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
APP_NAME = "StreamVault Pro"
APP_TAGLINE = "High-Performance Multi-Source Video Downloader & Archiver"
APP_VERSION = "1.0.0"
