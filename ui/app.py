"""
Main Application Window
=======================
Assembles all UI components into the main CustomTkinter window and
wires up the download engine with thread-safe UI updates.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from core.config import APP_NAME, APP_VERSION, find_ffmpeg
from core.downloader import Downloader, DownloadStatus, ProgressInfo
from ui.components import (
    LogFrame,
    ProgressFrame,
    SettingsFrame,
    URLInputFrame,
)


class VideoDownloaderApp(ctk.CTk):
    """
    Main application window for the Video Downloader.

    Thread safety:
        The Downloader engine runs on background threads and emits
        ProgressInfo callbacks. These callbacks use `self.after(0, ...)`
        to marshal all GUI updates onto the Tkinter main thread.
    """

    WINDOW_WIDTH = 720
    WINDOW_HEIGHT = 540

    def __init__(self) -> None:
        super().__init__()

        # -- Window configuration --
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.minsize(580, 440)

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # -- Downloader engine --
        self._downloader = Downloader(progress_callback=self._on_progress)

        # -- Build UI --
        self._build_ui()

        # -- Force window to front and center --
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - self.WINDOW_WIDTH) // 2
        y = (screen_h - self.WINDOW_HEIGHT) // 2
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")
        self.lift()
        self.attributes("-topmost", True)
        self.after(1000, lambda: self.attributes("-topmost", False))
        self.focus_force()

        # -- FFmpeg check on startup --
        self.after(500, self._check_ffmpeg)

    # ══════════════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        # Main container with padding
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        # -- Header --
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text=f"⬇  {APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).pack(side="left")

        # Theme toggle
        self._theme_btn = ctk.CTkButton(
            header,
            text="🌙",
            width=36,
            height=36,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right")

        # -- URL Input --
        self._url_frame = URLInputFrame(container)
        self._url_frame.pack(fill="x", pady=(0, 12))

        # -- Settings --
        self._settings_frame = SettingsFrame(container)
        self._settings_frame.pack(fill="x", pady=(0, 16))

        # -- Action buttons --
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 12))

        self._download_btn = ctk.CTkButton(
            btn_row,
            text="⬇  Download",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            command=self._on_download_click,
        )
        self._download_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._cancel_btn = ctk.CTkButton(
            btn_row,
            text="✕  Cancel",
            font=ctk.CTkFont(size=14),
            width=120,
            height=44,
            fg_color=("#D32F2F", "#C62828"),
            hover_color=("#B71C1C", "#B71C1C"),
            state="disabled",
            command=self._on_cancel_click,
        )
        self._cancel_btn.pack(side="left")

        # -- Progress --
        self._progress_frame = ProgressFrame(container)
        self._progress_frame.pack(fill="x", pady=(0, 8))

        # -- Log viewer --
        self._log_frame = LogFrame(container)
        self._log_frame.pack(fill="both", expand=True)

        # -- FFmpeg warning banner (hidden by default) --
        self._ffmpeg_banner = ctk.CTkFrame(container, fg_color=("#FFF3E0", "#3E2723"), corner_radius=8)
        self._ffmpeg_label = ctk.CTkLabel(
            self._ffmpeg_banner,
            text="⚠  FFmpeg not found. Videos above 720p may not merge properly. Install FFmpeg for best results.",
            font=ctk.CTkFont(size=11),
            text_color=("#E65100", "#FFB74D"),
            wraplength=640,
            anchor="w",
        )
        self._ffmpeg_label.pack(padx=12, pady=8)
        # Banner starts hidden; shown only if ffmpeg is missing

    # ══════════════════════════════════════════════════════════════════════
    # Event Handlers
    # ══════════════════════════════════════════════════════════════════════

    def _on_download_click(self) -> None:
        urls = self._url_frame.get_urls()
        if not urls:
            messagebox.showwarning("No URLs", "Please enter at least one valid video or playlist URL (starting with http/https).")
            return

        save_dir = self._settings_frame.get_save_dir()
        if not os.path.isdir(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Folder Error", f"Cannot create folder:\n{e}")
                return

        format_str = self._settings_frame.get_format_string()

        # Disable controls during download
        self._set_controls_enabled(False)
        self._progress_frame.reset()
        self._log_frame.clear()

        self._log_frame.append_log(f"Queued {len(urls)} URL(s):")
        for u in urls:
            self._log_frame.append_log(f"  • {u}")
        self._log_frame.append_log(f"Quality: {self._settings_frame.get_quality_label()}")
        self._log_frame.append_log(f"Save to: {save_dir}")
        self._log_frame.append_log("Starting batch download…\n")

        self._downloader.start_download_async(
            urls=urls,
            save_dir=save_dir,
            format_str=format_str,
        )

    def _on_cancel_click(self) -> None:
        self._downloader.cancel()
        self._progress_frame.set_status("Cancelling…")
        self._log_frame.append_log("Cancellation requested.")

    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("light")
            self._theme_btn.configure(text="☀")
        else:
            ctk.set_appearance_mode("dark")
            self._theme_btn.configure(text="🌙")

    # ══════════════════════════════════════════════════════════════════════
    # Progress Callback (called from background thread → marshalled to main)
    # ══════════════════════════════════════════════════════════════════════

    def _on_progress(self, info: ProgressInfo) -> None:
        """
        Called by the Downloader from a background thread.
        Marshals all GUI updates to the Tkinter main thread via self.after().
        """
        self.after(0, self._apply_progress, info)

    def _apply_progress(self, info: ProgressInfo) -> None:
        """Apply progress updates on the main thread. Safe to touch widgets."""

        if info.status == DownloadStatus.DOWNLOADING:
            self._progress_frame.update_progress(
                percent=info.percent,
                title=info.title,
                speed=info.speed,
                eta=info.eta,
                total_bytes=info.total_bytes,
                downloaded_bytes=info.downloaded_bytes,
                playlist_index=info.playlist_index,
                playlist_count=info.playlist_count,
            )
            if info.title:
                self._log_frame.append_log(
                    f"  ↓ {info.percent:.1f}% | {info.speed} | ETA {info.eta}"
                )

        elif info.status == DownloadStatus.FETCHING_INFO:
            self._progress_frame.set_status(info.title or "Fetching info…")

        elif info.status == DownloadStatus.POST_PROCESSING:
            self._progress_frame.set_completed()
            self._progress_frame.set_status(info.title or "Post-processing…")
            self._log_frame.append_log(f"  ⚙ {info.title}")

        elif info.status == DownloadStatus.COMPLETED:
            self._progress_frame.set_completed()
            self._progress_frame.set_status("✅  Download complete!")
            self._log_frame.append_log("\n✅ Download finished successfully!")
            if info.playlist_count > 1:
                self._log_frame.append_log(f"   {info.playlist_count} items downloaded.")
            self._set_controls_enabled(True)

        elif info.status == DownloadStatus.CANCELLED:
            self._progress_frame.set_status("🚫  Download cancelled.")
            self._log_frame.append_log("\n🚫 Download cancelled by user.")
            self._set_controls_enabled(True)

        elif info.status == DownloadStatus.ERROR:
            self._progress_frame.set_status("❌  Error occurred.")
            self._log_frame.append_log(f"\n❌ Error: {info.error_message}")
            messagebox.showerror("Download Error", info.error_message)
            self._set_controls_enabled(True)

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._url_frame.set_enabled(enabled)
        self._settings_frame.set_enabled(enabled)
        self._download_btn.configure(state="normal" if enabled else "disabled")
        self._cancel_btn.configure(state="disabled" if enabled else "normal")

    def _check_ffmpeg(self) -> None:
        if find_ffmpeg() is None:
            self._ffmpeg_banner.pack(fill="x", pady=(8, 0))
            self._log_frame.append_log(
                "⚠ FFmpeg not found in PATH. Install it for best quality merging.\n"
                "  Run: winget install Gyan.FFmpeg"
            )
