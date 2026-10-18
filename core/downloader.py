"""
Download Engine with Multi-Threaded Parallel Downloads & Task Control
=====================================================================
Threaded wrapper around yt_dlp.YoutubeDL that:
  - Supports true "Pause All" and "Start All" (for paused or failed tasks)
  - Resumes downloads from partial .part files without starting over
  - Maintains persistent task lists (does not wipe completed tasks)
  - 4x parallel simultaneous downloads
  - Automatic title cleaning and resilient error recovery
"""

from __future__ import annotations

import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any, Callable

import yt_dlp

import datetime
from core.config import DEFAULT_CONCURRENT_FRAGMENTS, find_ffmpeg, get_default_download_dir
from core.history_tracker import get_tracker_path, record_download_history
from core.title_sanitizer import sanitize_title

import sys
if sys.platform == "win32":
    import ctypes

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_AWAYMODE_REQUIRED = 0x00000040

    def _set_sleep_prevention(enable: bool) -> None:
        """Prevent Windows from sleeping while downloads are running."""
        try:
            if enable:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
                )
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass
else:
    def _set_sleep_prevention(enable: bool) -> None:
        pass


from enum import Enum, auto


class DownloadStatus(Enum):
    IDLE = auto()
    FETCHING_INFO = auto()
    DOWNLOADING = auto()
    POST_PROCESSING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    ERROR = auto()


@dataclass
class ProgressInfo:
    status: DownloadStatus = DownloadStatus.IDLE
    percent: float = 0.0
    speed: str = "—"
    eta: str = "—"
    total_bytes: str = "—"
    downloaded_bytes: str = "—"
    title: str = ""
    error_message: str = ""
    playlist_index: int = 0
    playlist_count: int = 0


# ---------------------------------------------------------------------------
# Individual Task Progress Structure
# ---------------------------------------------------------------------------

@dataclass
class TaskProgress:
    id: int
    url: str
    title: str = "Queued..."
    raw_title: str = ""
    description: str = ""
    duration_str: str = "—"
    status: str = "QUEUED"  # QUEUED, CONNECTING, DOWNLOADING, POST_PROCESSING, COMPLETED, PAUSED, ERROR
    percent: float = 0.0
    speed: str = "—"
    eta: str = "—"
    total_bytes: str = "—"
    downloaded_bytes: str = "—"
    filename: str = ""
    error_message: str = ""
    save_dir: str = ""
    format_str: str = "bestvideo+bestaudio/best"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Custom YoutubeDL Subclass with Built-in Title Sanitization & Metadata Capture
# ---------------------------------------------------------------------------

class SanitizedYoutubeDL(yt_dlp.YoutubeDL):
    """
    Subclass that automatically intercepts all video metadata and passes
    the title through our TitleSanitizer before filenames are generated on disk.
    Also calls metadata_callback to record raw titles and full descriptions.
    """

    def __init__(self, *args, metadata_callback: Callable[[dict[str, Any]], None] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta_cb = metadata_callback

    def process_video_result(self, info_dict: dict[str, Any], download: bool = True) -> dict[str, Any]:
        if info_dict:
            if self._meta_cb:
                try:
                    self._meta_cb(info_dict)
                except Exception:
                    pass
            if info_dict.get("title"):
                info_dict["title"] = sanitize_title(info_dict["title"])
        return super().process_video_result(info_dict, download=download)

    def process_ie_result(self, ie_result: dict[str, Any], download: bool = True, extra_info: dict[str, Any] | None = None) -> dict[str, Any]:
        if ie_result:
            if self._meta_cb:
                try:
                    self._meta_cb(ie_result)
                except Exception:
                    pass
            if ie_result.get("title"):
                ie_result["title"] = sanitize_title(ie_result["title"])
        return super().process_ie_result(ie_result, download=download, extra_info=extra_info)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_bytes(b: float | None) -> str:
    if b is None or b < 0:
        return "—"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TiB"


def _format_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"0:{s:02d}"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _format_speed(bps: float | None) -> str:
    if bps is None or bps <= 0:
        return "—"
    return f"{_format_bytes(bps)}/s"


class _YDLLogger:
    def __init__(self, log_callback: Callable[[str], None] | None = None):
        self.log_callback = log_callback

    def debug(self, msg: str) -> None:
        if self.log_callback and any(msg.startswith(p) for p in ("[download]", "[Merger]", "[ExtractAudio]", "[ffmpeg]")):
            self.log_callback(msg)

    def warning(self, msg: str) -> None:
        if self.log_callback:
            self.log_callback(f"[WARN] {msg}")

    def error(self, msg: str) -> None:
        if self.log_callback:
            self.log_callback(f"[ERROR] {msg}")


# ---------------------------------------------------------------------------
# Main Downloader with Start All / Pause All / Task Retention
# ---------------------------------------------------------------------------

class Downloader:
    """
    Downloader engine capable of downloading multiple videos simultaneously
    with robust Start All, Pause All, Resume, and Task List persistence.
    """

    def __init__(self, max_parallel: int = 4, progress_callback: Callable[[ProgressInfo], None] | None = None):
        self.default_parallel = max_parallel
        self.progress_callback = progress_callback
        self.tasks: list[TaskProgress] = []
        self.logs: list[str] = []
        self._log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloader.log")
        self._lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._paused_task_ids: set[int] = set()
        self._manager_thread: threading.Thread | None = None
        self._is_running = False
        self._next_id = 1
        self.log("All Video Downloader Pro engine initialized (4x parallel mode).")

    def log(self, msg: str) -> None:
        """Record a timestamped log line to memory, stdout, and downloader.log file."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > 600:
                self.logs.pop(0)
        with self._log_lock:
            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(entry + "\n")
            except Exception:
                pass

    def get_logs(self) -> list[str]:
        """Return a copy of recent log messages."""
        with self._lock:
            return list(self.logs)

    def fetch_info(self, url: str) -> dict[str, Any]:
        """Fetch metadata for a single URL and return sanitized title."""
        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": True,
            "extract_flat": "in_playlist",
        }
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg)

        with SanitizedYoutubeDL(ydl_opts) as ydl:
            raw_info = ydl.extract_info(url, download=False)

        if not raw_info:
            raise ValueError("Could not extract video metadata from URL.")

        raw_title = raw_info.get("title", "") or ""
        clean = sanitize_title(raw_title)
        is_playlist = raw_info.get("_type") == "playlist"
        entries = raw_info.get("entries", [])
        playlist_count = len(entries) if is_playlist else 0

        return {
            "raw_title": raw_title,
            "clean_title": clean,
            "duration": raw_info.get("duration", 0),
            "thumbnail": raw_info.get("thumbnail", ""),
            "uploader": raw_info.get("uploader", ""),
            "is_playlist": is_playlist,
            "playlist_count": playlist_count,
        }

    def start_download_async(
        self,
        urls: list[str] | str,
        save_dir: str,
        format_str: str = "bestvideo+bestaudio/best",
        custom_title: str = "",
        max_parallel: int = 4,
    ) -> None:
        """Add new URLs to the queue and begin processing."""
        if isinstance(urls, str):
            url_list = [line.strip() for line in urls.strip().splitlines() if line.strip() and line.strip().startswith("http")]
        else:
            url_list = [u.strip() for u in urls if u and u.strip() and u.strip().startswith("http")]

        if not url_list:
            raise ValueError("No valid URLs provided to download.")

        new_tasks = []
        with self._lock:
            for i, u in enumerate(url_list):
                task = TaskProgress(
                    id=self._next_id,
                    url=u,
                    title=custom_title if (custom_title and len(url_list) == 1) else f"Video #{self._next_id}",
                    status="QUEUED",
                    save_dir=save_dir,
                    format_str=format_str,
                )
                self._next_id += 1
                self.tasks.append(task)
                new_tasks.append(task)

        self._start_pool_on_tasks(new_tasks, max_parallel)

    def start_all_unfinished(self, max_parallel: int = 4) -> int:
        """
        Resumes / starts all tasks that are currently PAUSED, ERROR, CANCELLED, or QUEUED.
        Returns the number of resumed tasks.
        """
        unfinished = []
        with self._lock:
            self._paused_task_ids.clear()
            for t in self.tasks:
                if t.status in ("PAUSED", "CANCELLED", "ERROR", "QUEUED"):
                    t.status = "QUEUED"
                    t.error_message = ""
                    unfinished.append(t)

        if unfinished:
            self._start_pool_on_tasks(unfinished, max_parallel)
        return len(unfinished)

    def resume_task(self, task_id: int, max_parallel: int = 4) -> bool:
        """Resume a single specific task by ID."""
        target = None
        with self._lock:
            self._paused_task_ids.discard(task_id)
            for t in self.tasks:
                if t.id == task_id and t.status in ("PAUSED", "CANCELLED", "ERROR", "QUEUED"):
                    t.status = "QUEUED"
                    t.error_message = ""
                    target = t
                    break

        if target:
            self._start_pool_on_tasks([target], max_parallel)
            return True
        return False

    def pause_task(self, task_id: int) -> bool:
        """Pause a specific running task by ID."""
        with self._lock:
            self._paused_task_ids.add(task_id)
            for t in self.tasks:
                if t.id == task_id:
                    if t.status in ("QUEUED", "CONNECTING", "DOWNLOADING", "POST_PROCESSING"):
                        t.status = "PAUSED"
                    return True
        return False

    def pause_all(self) -> None:
        """Pause all currently running/queued downloads."""
        self._cancel_event.set()
        _set_sleep_prevention(False)
        self.log("[POWER] Downloads paused. Normal laptop sleep mode restored.")
        with self._lock:
            for task in self.tasks:
                self._paused_task_ids.add(task.id)
                if task.status in ("QUEUED", "CONNECTING", "DOWNLOADING", "POST_PROCESSING"):
                    task.status = "PAUSED"
            self._is_running = False

    def cancel(self) -> None:
        """Alias for pause_all."""
        self.pause_all()

    def remove_completed(self) -> None:
        """Remove completed tasks from list."""
        with self._lock:
            self.tasks = [t for t in self.tasks if t.status != "COMPLETED"]

    def remove_task(self, task_id: int) -> None:
        """Remove a task by ID."""
        with self._lock:
            self._paused_task_ids.discard(task_id)
            self.tasks = [t for t in self.tasks if t.id != task_id]

    def clear_all(self) -> None:
        """Clear all tasks."""
        self.pause_all()
        _set_sleep_prevention(False)
        with self._lock:
            self._paused_task_ids.clear()
            self.tasks = []
            self._next_id = 1

    @property
    def is_busy(self) -> bool:
        return self._is_running

    def get_status_payload(self) -> dict[str, Any]:
        """Return full snapshot of all active, paused, and completed tasks."""
        with self._lock:
            tasks_copy = [t.to_dict() for t in self.tasks]
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks if t.status == "COMPLETED")
            errors = sum(1 for t in self.tasks if t.status == "ERROR")
            active = sum(1 for t in self.tasks if t.status in ("CONNECTING", "DOWNLOADING", "POST_PROCESSING"))
            paused = sum(1 for t in self.tasks if t.status in ("PAUSED", "CANCELLED"))

            overall_pct = (completed / total * 100) if total > 0 else 0.0

            return {
                "is_busy": self._is_running,
                "sleep_prevented": self._is_running,
                "total": total,
                "completed": completed,
                "errors": errors,
                "active": active,
                "paused": paused,
                "cancelled": paused,
                "overall_percent": round(overall_pct, 1),
                "tasks": tasks_copy,
            }

    def _start_pool_on_tasks(self, tasks_to_run: list[TaskProgress], max_parallel: int) -> None:
        self._cancel_event.clear()
        _set_sleep_prevention(True)
        self.log("[POWER] Active download started. Laptop sleep prevention enabled.")
        with self._lock:
            for t in tasks_to_run:
                self._paused_task_ids.discard(t.id)
        self._is_running = True
        self._manager_thread = threading.Thread(
            target=self._run_parallel_pool,
            args=(tasks_to_run, max_parallel),
            daemon=True
        )
        self._manager_thread.start()

    def _run_parallel_pool(
        self,
        tasks_to_run: list[TaskProgress],
        max_parallel: int,
    ) -> None:
        """Worker manager executing tasks via ThreadPoolExecutor."""
        ffmpeg_path = find_ffmpeg()

        def download_single(task: TaskProgress) -> None:
            if self._cancel_event.is_set() or task.id in self._paused_task_ids:
                with self._lock:
                    task.status = "PAUSED"
                return

            with self._lock:
                task.status = "CONNECTING"

            def progress_hook(d: dict[str, Any]) -> None:
                if self._cancel_event.is_set() or task.id in self._paused_task_ids:
                    raise yt_dlp.utils.DownloadCancelled("User paused")

                raw_status = d.get("status", "")
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0) or 0
                pct = (downloaded / total * 100) if total > 0 else 0.0

                info_dict = d.get("info_dict", {})
                current_title = info_dict.get("title", "") or d.get("filename", "")
                if current_title:
                    current_title = sanitize_title(current_title)

                with self._lock:
                    task.status = "DOWNLOADING" if raw_status == "downloading" else "POST_PROCESSING"
                    task.percent = min(round(pct, 1), 100.0)
                    task.speed = _format_speed(d.get("speed"))
                    task.eta = _format_eta(d.get("eta"))
                    task.downloaded_bytes = _format_bytes(downloaded)
                    task.total_bytes = _format_bytes(total)
                    task.filename = os.path.basename(d.get("filename", ""))
                    if current_title:
                        task.title = current_title

                if self.progress_callback:
                    try:
                        self.progress_callback(ProgressInfo(
                            status=DownloadStatus.DOWNLOADING if raw_status == "downloading" else DownloadStatus.POST_PROCESSING,
                            percent=task.percent,
                            speed=task.speed,
                            eta=task.eta,
                            total_bytes=task.total_bytes,
                            downloaded_bytes=task.downloaded_bytes,
                            title=task.title,
                        ))
                    except Exception:
                        pass

            def postprocessor_hook(d: dict[str, Any]) -> None:
                if self._cancel_event.is_set() or task.id in self._paused_task_ids:
                    raise yt_dlp.utils.DownloadCancelled("User paused")
                status = d.get("status", "")
                if status == "started":
                    with self._lock:
                        task.status = "POST_PROCESSING"
                        task.percent = 100.0

            def metadata_cb(info_dict: dict[str, Any]) -> None:
                with self._lock:
                    if not task.raw_title:
                        task.raw_title = info_dict.get("title", "") or ""
                    if not task.description:
                        task.description = info_dict.get("description", "") or ""
                    dur = info_dict.get("duration") or 0
                    if dur and task.duration_str == "—":
                        task.duration_str = _format_eta(dur)
                if task.description:
                    self.log(f"[Task #{task.id}] Captured video description ({len(task.description)} chars)")

            outtmpl = os.path.join(task.save_dir or get_default_download_dir(), "%(title)s.%(ext)s")

            ydl_opts: dict[str, Any] = {
                "format": task.format_str or "bestvideo+bestaudio/best",
                "outtmpl": outtmpl,
                "concurrent_fragment_downloads": DEFAULT_CONCURRENT_FRAGMENTS,
                "continuedl": True,              # Resume from partial .part files
                "nopart": False,                 # Preserve .part files for resuming
                "retries": 25,                   # Auto-retry on network drop up to 25 times
                "fragment_retries": 25,          # Auto-retry broken fragments up to 25 times
                "file_access_retries": 10,
                "socket_timeout": 30,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "logger": _YDLLogger(log_callback=lambda msg: self.log(f"[Task #{task.id}] {msg}")),
                "ignoreerrors": True,
                "noprogress": True,
                "quiet": True,
                "no_warnings": False,
                "windowsfilenames": True,
            }

            if task.format_str == "bestaudio/best":
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

            if ffmpeg_path:
                ydl_opts["ffmpeg_location"] = os.path.dirname(ffmpeg_path)

            max_auto_retries = 3
            for attempt in range(1, max_auto_retries + 1):
                if self._cancel_event.is_set() or task.id in self._paused_task_ids:
                    with self._lock:
                        task.status = "PAUSED"
                    break

                try:
                    with SanitizedYoutubeDL(ydl_opts, metadata_callback=metadata_cb) as ydl:
                        self.log(f"[Task #{task.id}] Starting extraction & download for {task.url}")
                        ydl.download([task.url])

                    with self._lock:
                        if not self._cancel_event.is_set() and task.id not in self._paused_task_ids:
                            task.status = "COMPLETED"
                            task.percent = 100.0
                            self.log(f"[Task #{task.id}] [SUCCESS] Download finished: {task.title}")
                            target_dir = task.save_dir or get_default_download_dir()
                            try:
                                tracker_file = record_download_history(
                                    {
                                        "status": "COMPLETED",
                                        "clean_title": task.title,
                                        "filename": task.filename,
                                        "raw_title": task.raw_title or task.title,
                                        "description": task.description,
                                        "url": task.url,
                                        "size": task.total_bytes,
                                        "duration": task.duration_str,
                                        "format": task.format_str,
                                        "file_path": os.path.join(target_dir, task.filename) if task.filename else "",
                                    },
                                    save_dir=target_dir,
                                    sync_cloud=True,
                                    log_callback=self.log,
                                )
                                self.log(f"[Task #{task.id}] [TRACKER] Logged metadata to Excel tracker: {tracker_file}")
                            except Exception as te:
                                self.log(f"[Task #{task.id}] [TRACKER ERROR] Failed to write Excel tracker: {te}")
                            if self.progress_callback:
                                try:
                                    self.progress_callback(ProgressInfo(
                                        status=DownloadStatus.COMPLETED,
                                        title=task.title,
                                        percent=100.0,
                                    ))
                                except Exception:
                                    pass
                        else:
                            task.status = "PAUSED"
                    break

                except yt_dlp.utils.DownloadCancelled:
                    with self._lock:
                        task.status = "PAUSED"
                        self.log(f"[Task #{task.id}] Download paused.")
                    if self.progress_callback:
                        try:
                            self.progress_callback(ProgressInfo(
                                status=DownloadStatus.CANCELLED,
                                title=task.title,
                            ))
                        except Exception:
                            pass
                    break
                except Exception as e:
                    if attempt < max_auto_retries and not self._cancel_event.is_set() and task.id not in self._paused_task_ids:
                        with self._lock:
                            task.status = f"AUTO-RESUMING ({attempt}/{max_auto_retries})..."
                        self.log(f"[Task #{task.id}] Connection interrupted. Auto-resuming ({attempt}/{max_auto_retries})...")
                        time.sleep(2)
                        continue
                    else:
                        with self._lock:
                            task.status = "ERROR"
                            task.error_message = str(e)
                        self.log(f"[Task #{task.id}] [ERROR] {e}")
                        if self.progress_callback:
                            try:
                                self.progress_callback(ProgressInfo(
                                    status=DownloadStatus.ERROR,
                                    error_message=str(e),
                                    title=task.title,
                                ))
                            except Exception:
                                pass

        workers_count = max(1, min(max_parallel, len(tasks_to_run)))
        with ThreadPoolExecutor(max_workers=workers_count) as executor:
            futures = [executor.submit(download_single, t) for t in tasks_to_run]
            for f in as_completed(futures):
                pass

        with self._lock:
            # Check if any tasks are still running
            any_active = any(t.status in ("CONNECTING", "DOWNLOADING", "POST_PROCESSING") for t in self.tasks)
            self._is_running = any_active
            if not any_active:
                _set_sleep_prevention(False)
                self.log("[POWER] All downloads completed. Normal laptop sleep mode restored.")
