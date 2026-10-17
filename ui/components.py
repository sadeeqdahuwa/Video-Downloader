"""
UI Components
=============
Reusable CustomTkinter widgets for the Video Downloader app:
  - URLInputFrame:     URL entry with paste support
  - SettingsFrame:     Quality selector + save folder picker
  - ProgressFrame:     Progress bar, speed, ETA, and status
  - LogFrame:          Scrollable log viewer
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from core.config import QUALITY_OPTIONS, get_default_download_dir


# ═══════════════════════════════════════════════════════════════════════════
# URL Input Frame
# ═══════════════════════════════════════════════════════════════════════════

class URLInputFrame(ctk.CTkFrame):
    """
    Top panel: URL entry box with a Paste button.
    Supports pasting single links, playlist URLs, or multiple lines.
    """

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")

        # Label
        self._label = ctk.CTkLabel(
            self,
            text="🔗  Paste video or playlist URLs (one per line)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._label.pack(fill="x", padx=5, pady=(0, 6))

        # Textbox row
        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(fill="x")
        entry_row.columnconfigure(0, weight=1)

        self._textbox = ctk.CTkTextbox(
            entry_row,
            height=85,
            font=ctk.CTkFont(size=12),
        )
        self._textbox.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._paste_btn = ctk.CTkButton(
            entry_row,
            text="📋 Paste",
            width=80,
            height=85,
            command=self._paste_from_clipboard,
        )
        self._paste_btn.grid(row=0, column=1)

    # -- Public API --------------------------------------------------------

    def get_url(self) -> str:
        return self._textbox.get("1.0", "end").strip()

    def get_urls(self) -> list[str]:
        text = self._textbox.get("1.0", "end")
        return [line.strip() for line in text.strip().splitlines() if line.strip() and line.strip().startswith("http")]

    def set_url(self, url: str) -> None:
        self._textbox.delete("1.0", "end")
        self._textbox.insert("1.0", url)

    def clear(self) -> None:
        self._textbox.delete("1.0", "end")

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._textbox.configure(state=state)
        self._paste_btn.configure(state=state)

    # -- Internal ----------------------------------------------------------

    def _paste_from_clipboard(self) -> None:
        try:
            text = self.clipboard_get().strip()
            if text:
                self._entry.delete(0, "end")
                self._entry.insert(0, text)
        except tk.TclError:
            pass  # clipboard empty or inaccessible


# ═══════════════════════════════════════════════════════════════════════════
# Settings Frame
# ═══════════════════════════════════════════════════════════════════════════

class SettingsFrame(ctk.CTkFrame):
    """
    Settings row: quality dropdown + download folder picker.
    """

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")

        # -- Quality dropdown --
        qual_col = ctk.CTkFrame(self, fg_color="transparent")
        qual_col.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(qual_col, text="Quality", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._quality_var = ctk.StringVar(value="Best Quality")
        self._quality_menu = ctk.CTkOptionMenu(
            qual_col,
            values=list(QUALITY_OPTIONS.keys()),
            variable=self._quality_var,
            width=160,
            height=36,
        )
        self._quality_menu.pack()

        # -- Save folder --
        folder_col = ctk.CTkFrame(self, fg_color="transparent")
        folder_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(folder_col, text="Save to", font=ctk.CTkFont(size=12)).pack(anchor="w")

        folder_row = ctk.CTkFrame(folder_col, fg_color="transparent")
        folder_row.pack(fill="x")
        folder_row.columnconfigure(0, weight=1)

        self._folder_var = ctk.StringVar(value=get_default_download_dir())
        self._folder_entry = ctk.CTkEntry(
            folder_row,
            textvariable=self._folder_var,
            height=36,
            font=ctk.CTkFont(size=12),
        )
        self._folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._browse_btn = ctk.CTkButton(
            folder_row,
            text="📁 Browse",
            width=90,
            height=36,
            command=self._browse_folder,
        )
        self._browse_btn.grid(row=0, column=1)

    # -- Public API --------------------------------------------------------

    def get_quality_label(self) -> str:
        return self._quality_var.get()

    def get_format_string(self) -> str:
        return QUALITY_OPTIONS.get(self._quality_var.get(), "bestvideo+bestaudio/best")

    def get_save_dir(self) -> str:
        return self._folder_var.get()

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._quality_menu.configure(state=state)
        self._folder_entry.configure(state=state)
        self._browse_btn.configure(state=state)

    # -- Internal ----------------------------------------------------------

    def _browse_folder(self) -> None:
        from tkinter import filedialog
        d = filedialog.askdirectory(
            title="Choose Download Folder",
            initialdir=self._folder_var.get(),
        )
        if d:
            self._folder_var.set(d)


# ═══════════════════════════════════════════════════════════════════════════
# Progress Frame
# ═══════════════════════════════════════════════════════════════════════════

class ProgressFrame(ctk.CTkFrame):
    """
    Download progress display: progress bar, percentage, speed, ETA, and status text.
    """

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(master, **kwargs)

        # -- Title / status label --
        self._title_label = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            wraplength=600,
        )
        self._title_label.pack(fill="x", padx=12, pady=(10, 4))

        # -- Progress bar --
        self._progress_bar = ctk.CTkProgressBar(self, height=18)
        self._progress_bar.pack(fill="x", padx=12, pady=(0, 4))
        self._progress_bar.set(0)

        # -- Metrics row --
        metrics_row = ctk.CTkFrame(self, fg_color="transparent")
        metrics_row.pack(fill="x", padx=12, pady=(0, 10))

        self._percent_label = ctk.CTkLabel(metrics_row, text="0%", font=ctk.CTkFont(size=12))
        self._percent_label.pack(side="left")

        self._eta_label = ctk.CTkLabel(metrics_row, text="", font=ctk.CTkFont(size=12))
        self._eta_label.pack(side="right")

        self._speed_label = ctk.CTkLabel(metrics_row, text="", font=ctk.CTkFont(size=12))
        self._speed_label.pack(side="right", padx=(0, 16))

        self._size_label = ctk.CTkLabel(metrics_row, text="", font=ctk.CTkFont(size=12))
        self._size_label.pack(side="right", padx=(0, 16))

    # -- Public API --------------------------------------------------------

    def update_progress(
        self,
        percent: float = 0.0,
        title: str = "",
        speed: str = "",
        eta: str = "",
        total_bytes: str = "",
        downloaded_bytes: str = "",
        playlist_index: int = 0,
        playlist_count: int = 0,
    ) -> None:
        """Update all progress display elements. Call from main thread only."""
        self._progress_bar.set(percent / 100.0)
        self._percent_label.configure(text=f"{percent:.1f}%")

        # Build title with playlist info
        display_title = title
        if playlist_count > 1 and playlist_index > 0:
            display_title = f"[{playlist_index}/{playlist_count}] {title}"

        self._title_label.configure(text=display_title or "Ready")
        self._speed_label.configure(text=f"⚡ {speed}" if speed and speed != "—" else "")
        self._eta_label.configure(text=f"⏱ {eta}" if eta and eta != "—" else "")

        if downloaded_bytes and total_bytes and total_bytes != "—":
            self._size_label.configure(text=f"📦 {downloaded_bytes} / {total_bytes}")
        else:
            self._size_label.configure(text="")

    def reset(self) -> None:
        self._progress_bar.set(0)
        self._percent_label.configure(text="0%")
        self._title_label.configure(text="Ready")
        self._speed_label.configure(text="")
        self._eta_label.configure(text="")
        self._size_label.configure(text="")

    def set_status(self, text: str) -> None:
        self._title_label.configure(text=text)

    def set_completed(self) -> None:
        self._progress_bar.set(1.0)
        self._percent_label.configure(text="100%")
        self._speed_label.configure(text="")
        self._eta_label.configure(text="")


# ═══════════════════════════════════════════════════════════════════════════
# Log Frame
# ═══════════════════════════════════════════════════════════════════════════

class LogFrame(ctk.CTkFrame):
    """
    Collapsible scrollable log viewer for detailed download output.
    """

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(master, **kwargs)

        # Toggle button
        self._expanded = False
        self._toggle_btn = ctk.CTkButton(
            self,
            text="▶ Show Logs",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray40", "gray60"),
            height=28,
            anchor="w",
            command=self._toggle,
        )
        self._toggle_btn.pack(fill="x", padx=4)

        # Textbox (hidden by default)
        self._textbox = ctk.CTkTextbox(
            self,
            height=120,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
            wrap="word",
        )

    # -- Public API --------------------------------------------------------

    def append_log(self, message: str) -> None:
        self._textbox.configure(state="normal")
        self._textbox.insert("end", message + "\n")
        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def clear(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")

    # -- Internal ----------------------------------------------------------

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._textbox.pack(fill="both", expand=True, padx=4, pady=(0, 4))
            self._toggle_btn.configure(text="▼ Hide Logs")
        else:
            self._textbox.pack_forget()
            self._toggle_btn.configure(text="▶ Show Logs")
