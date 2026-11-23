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
import os
import sys

# Ensure UTF-8 output encoding across Windows subshells and consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
from core.config import APP_NAME, DEFAULT_CONCURRENT_FRAGMENTS, find_ffmpeg, get_default_download_dir, get_app_data_dir
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskProgress:
        return cls(
            id=int(data.get("id", 1)),
            url=str(data.get("url", "")),
            title=str(data.get("title", "Queued...")),
            raw_title=str(data.get("raw_title", "")),
            description=str(data.get("description", "")),
            duration_str=str(data.get("duration_str", "—")),
            status=str(data.get("status", "PAUSED")),
            percent=float(data.get("percent", 0.0)),
            speed=str(data.get("speed", "—")),
            eta=str(data.get("eta", "—")),
            total_bytes=str(data.get("total_bytes", "—")),
            downloaded_bytes=str(data.get("downloaded_bytes", "—")),
            filename=str(data.get("filename", "")),
            error_message=str(data.get("error_message", "")),
            save_dir=str(data.get("save_dir", "")),
            format_str=str(data.get("format_str", "bestvideo+bestaudio/best")),
        )


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
    def __init__(self, log_callback: Callable[[str], None] | None = None, task: TaskProgress | None = None):
        self.log_callback = log_callback
        self.task = task
        self.last_error = ""

    def debug(self, msg: str) -> None:
        if self.log_callback and any(msg.startswith(p) for p in ("[download]", "[Merger]", "[ExtractAudio]", "[ffmpeg]")):
            self.log_callback(msg)

    def warning(self, msg: str) -> None:
        if self.log_callback:
            self.log_callback(f"[WARN] {msg}")

    def error(self, msg: str) -> None:
        self.last_error = msg
        clean_msg = msg.replace("ERROR: ", "").strip()
        if self.task:
            self.task.error_message = clean_msg
        if self.log_callback:
            self.log_callback(f"[ERROR] {clean_msg}")


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
        self._lock = threading.RLock()
        self._log_lock = threading.RLock()
        self._cancel_event = threading.Event()
        self._paused_task_ids: set[int] = set()
        self._manager_thread: threading.Thread | None = None
        self._is_running = False
        self._next_id = 1
        self.load_tasks_from_disk()
        self.log(f"{APP_NAME} engine initialized (4x parallel mode).")

    def save_tasks_to_disk(self) -> None:
        """Persist current task list to tasks.json so tasks and progress survive restarts."""
        try:
            tasks_file = os.path.join(get_app_data_dir(), "tasks.json")
            with self._lock:
                tasks_data = [t.to_dict() for t in self.tasks]
            tmp_file = tasks_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(tasks_data, f, indent=2, ensure_ascii=False)
            if os.path.exists(tmp_file):
                os.replace(tmp_file, tasks_file)
        except Exception as e:
            try:
                self.log(f"[Warning] Failed to persist tasks to disk: {e}")
            except Exception:
                pass

    def load_tasks_from_disk(self) -> None:
        """Load tasks from tasks.json, or reconstruct from download_history.csv + cleaned_facebook_links.txt."""
        tasks_file = os.path.join(get_app_data_dir(), "tasks.json")
        loaded_tasks: list[TaskProgress] = []
        if os.path.isfile(tasks_file):
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        t = TaskProgress.from_dict(item)
                        if t.status in ("DOWNLOADING", "CONNECTING", "POST_PROCESSING", "QUEUED"):
                            t.status = "PAUSED"
                            t.speed = "—"
                            t.eta = "—"
                        loaded_tasks.append(t)
            except Exception as e:
                self.log(f"[Warning] Could not read tasks.json: {e}")

        # If tasks.json was empty or missing, reconstruct from download_history.csv & cleaned_facebook_links.txt
        if not loaded_tasks:
            loaded_tasks = self._reconstruct_tasks_from_history()

        with self._lock:
            self.tasks = loaded_tasks
            if self.tasks:
                self._next_id = max((t.id for t in self.tasks), default=0) + 1
            completed_c = sum(1 for t in self.tasks if t.status == "COMPLETED")
            paused_c = sum(1 for t in self.tasks if t.status == "PAUSED")
            self.log(f"Restored {len(self.tasks)} persistent tasks ({completed_c} completed, {paused_c} ready to resume).")

        # Save back to ensure tasks.json exists immediately
        self.save_tasks_to_disk()

    def _reconstruct_tasks_from_history(self) -> list[TaskProgress]:
        """Automatically reconstruct task list from download_history.csv and cleaned_facebook_links.txt."""
        tasks: list[TaskProgress] = []
        downloaded_urls: dict[str, dict[str, Any]] = {}
        history_csv = os.path.join(get_default_download_dir(), "download_history.csv")
        if not os.path.isfile(history_csv):
            history_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tracker", "download_history.csv")

        if os.path.isfile(history_csv):
            try:
                import csv
                with open(history_csv, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        u = row.get("Video URL", "").strip()
                        st = row.get("Status", "").strip().upper()
                        if u and st == "COMPLETED":
                            downloaded_urls[u] = row
            except Exception:
                pass

        tid = 1
        for u, row in downloaded_urls.items():
            tasks.append(
                TaskProgress(
                    id=tid,
                    url=u,
                    title=row.get("Clean Title") or row.get("Raw Title") or f"Video #{tid}",
                    raw_title=row.get("Raw Title") or "",
                    description=row.get("Full Description (Full Post Text)") or "",
                    duration_str=row.get("Duration") or "—",
                    status="COMPLETED",
                    percent=100.0,
                    speed="—",
                    eta="—",
                    total_bytes=row.get("File Size") or "—",
                    downloaded_bytes=row.get("File Size") or "—",
                    filename=row.get("Saved Filename") or "",
                    save_dir=row.get("File Path") or get_default_download_dir(),
                )
            )
            tid += 1

        search_dirs = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            os.path.dirname(sys.executable),
            os.getcwd(),
        ]
        links_file = None
        for d in search_dirs:
            p = os.path.join(d, "cleaned_facebook_links.txt")
            if os.path.isfile(p):
                links_file = p
                break

        if links_file:
            try:
                with open(links_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line_u = line.strip()
                        if line_u.startswith("http") and line_u not in downloaded_urls:
                            tasks.append(
                                TaskProgress(
                                    id=tid,
                                    url=line_u,
                                    title=f"Video #{tid}",
                                    status="PAUSED",
                                    percent=0.0,
                                    save_dir=get_default_download_dir(),
                                )
                            )
                            tid += 1
            except Exception:
                pass

        return tasks

    def log(self, msg: str) -> None:
        """Record a timestamped log line to memory, stdout, and downloader.log file."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        try:
            print(entry)
        except Exception:
            try:
                enc = getattr(sys.stdout, "encoding", None) or "utf-8"
                print(entry.encode(enc, errors="replace").decode(enc, errors="replace"))
            except Exception:
                pass
        with self._log_lock:
            self.logs.append(entry)
            if len(self.logs) > 600:
                self.logs.pop(0)
            try:
                with open(self._log_file, "a", encoding="utf-8", errors="replace") as f:
                    f.write(entry + "\n")
            except Exception:
                pass

    def get_logs(self) -> list[str]:
        """Return a copy of recent log messages."""
        with self._log_lock:
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
        def _normalize(u: str) -> str:
            u = u.strip().strip("'\"[]() ;,")
            if u and not u.startswith("http://") and not u.startswith("https://"):
                if u.startswith("www.") or any(d in u.lower() for d in ("facebook.com", "fb.watch", "youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com")):
                    u = "https://" + u
            return u

        if isinstance(urls, str):
            raw_lines = [_normalize(line) for line in urls.strip().splitlines()]
            url_list = [l for l in raw_lines if l and (l.startswith("http://") or l.startswith("https://"))]
        else:
            url_list = [_normalize(u) for u in urls if u and (_normalize(u).startswith("http://") or _normalize(u).startswith("https://"))]

        if not url_list:
            raise ValueError("No valid URLs provided to download.")

        new_tasks = []
        with self._lock:
            existing_by_url = {t.url: t for t in self.tasks}
            for i, u in enumerate(url_list):
                if u in existing_by_url:
                    existing = existing_by_url[u]
                    if existing.status == "COMPLETED":
                        target_dir = existing.save_dir or save_dir
                        target_file = os.path.join(target_dir, existing.filename) if existing.filename else ""
                        if target_file and os.path.isfile(target_file):
                            continue
                    existing.status = "QUEUED"
                    existing.error_message = ""
                    existing.save_dir = save_dir
                    existing.format_str = format_str
                    new_tasks.append(existing)
                    continue

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

            self.save_tasks_to_disk()

        self.log(f"Queued {len(new_tasks)} links for download (Parallel: {max_parallel}x, Quality: {format_str})")
        if new_tasks:
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
            self.save_tasks_to_disk()

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
            self.save_tasks_to_disk()

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
                    self.save_tasks_to_disk()
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
            self.save_tasks_to_disk()

    def cancel(self) -> None:
        """Alias for pause_all."""
        self.pause_all()

    def remove_completed(self) -> None:
        """Remove completed tasks from list."""
        with self._lock:
            self.tasks = [t for t in self.tasks if t.status != "COMPLETED"]
            self.save_tasks_to_disk()

    def remove_task(self, task_id: int) -> None:
        """Remove a task by ID."""
        with self._lock:
            self._paused_task_ids.discard(task_id)
            self.tasks = [t for t in self.tasks if t.id != task_id]
            self.save_tasks_to_disk()

    def clear_all(self) -> None:
        """Clear all tasks."""
        self.pause_all()
        _set_sleep_prevention(False)
        with self._lock:
            self._paused_task_ids.clear()
            self.tasks = []
            self._next_id = 1
            self.save_tasks_to_disk()

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
                elif status == "finished":
                    info = d.get("info_dict", {})
                    fn = info.get("_filename") or d.get("filepath")
                    if fn:
                        with self._lock:
                            task.filename = os.path.basename(fn)

            def metadata_cb(info_dict: dict[str, Any]) -> None:
                with self._lock:
                    if not task.raw_title:
                        task.raw_title = info_dict.get("title", "") or ""
                    if not task.description:
                        task.description = info_dict.get("description", "") or ""
                    dur = info_dict.get("duration") or 0
                    if dur and task.duration_str == "—":
                        task.duration_str = _format_eta(dur)
                    if task.raw_title and (not task.title or task.title.startswith("Video #")):
                        task.title = sanitize_title(task.raw_title)
                if task.description:
                    self.log(f"[Task #{task.id}] Captured video description ({len(task.description)} chars)")

            outtmpl = os.path.join(task.save_dir or get_default_download_dir(), "%(title)s.%(ext)s")
            ydl_logger = _YDLLogger(log_callback=lambda msg: self.log(f"[Task #{task.id}] {msg}"), task=task)

            ydl_opts: dict[str, Any] = {
                "format": task.format_str or "bestvideo+bestaudio/best",
                "outtmpl": outtmpl,
                "concurrent_fragment_downloads": DEFAULT_CONCURRENT_FRAGMENTS,
                "continuedl": True,              # Resume from partial .part files
                "nopart": False,                 # Preserve .part files for resuming
                "retries": 15,                   # Auto-retry on network drop
                "fragment_retries": 15,          # Auto-retry broken fragments
                "file_access_retries": 10,
                "socket_timeout": 30,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "logger": ydl_logger,
                "ignoreerrors": False,           # Surface real extraction/download errors
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
                        ret_code = ydl.download([task.url])
                        if ret_code != 0:
                            raise yt_dlp.utils.DownloadError(ydl_logger.last_error or f"Download failed (code {ret_code})")

                    target_dir = task.save_dir or get_default_download_dir()
                    target_file = ""
                    if task.filename and os.path.exists(os.path.join(target_dir, task.filename)):
                        target_file = os.path.join(target_dir, task.filename)
                    else:
                        clean_stem = task.title[:45].strip() if task.title else ""
                        if clean_stem and os.path.exists(target_dir):
                            for f in os.listdir(target_dir):
                                if f.endswith((".mp4", ".mkv", ".mp3", ".m4a", ".webm")) and not f.endswith(".part"):
                                    if clean_stem.lower() in f.lower():
                                        target_file = os.path.join(target_dir, f)
                                        task.filename = f
                                        break

                    is_completed = False
                    with self._lock:
                        if not self._cancel_event.is_set() and task.id not in self._paused_task_ids:
                            task.status = "COMPLETED"
                            task.percent = 100.0
                            is_completed = True
                        else:
                            task.status = "PAUSED"

                    if is_completed:
                        self.log(f"[Task #{task.id}] [SUCCESS] Download finished: {task.title}")
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
                                    "file_path": target_file or (os.path.join(target_dir, task.filename) if task.filename else ""),
                                },
                                save_dir=target_dir,
                                sync_cloud=False,
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
                        self.save_tasks_to_disk()
                    break

                except yt_dlp.utils.DownloadCancelled:
                    with self._lock:
                        task.status = "PAUSED"
                    self.save_tasks_to_disk()
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
                    err_str = str(e)
                    is_fatal = any(term in err_str.lower() for term in ("unsupported url", "private video", "cannot parse data", "login", "requires authentication"))
                    if attempt < max_auto_retries and not is_fatal and not self._cancel_event.is_set() and task.id not in self._paused_task_ids:
                        with self._lock:
                            task.status = f"AUTO-RESUMING ({attempt}/{max_auto_retries})..."
                        self.log(f"[Task #{task.id}] Connection interrupted ({err_str}). Auto-resuming ({attempt}/{max_auto_retries})...")
                        time.sleep(2)
                        continue
                    else:
                        with self._lock:
                            task.status = "ERROR"
                            task.error_message = err_str.replace("ERROR: ", "").strip()
                        self.save_tasks_to_disk()
                        self.log(f"[Task #{task.id}] [ERROR] {task.error_message}")
                        if self.progress_callback:
                            try:
                                self.progress_callback(ProgressInfo(
                                    status=DownloadStatus.ERROR,
                                    error_message=task.error_message,
                                    title=task.title,
                                ))
                            except Exception:
                                pass
                        break

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
