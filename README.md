# All Video Downloader Pro

A high-performance multi-threaded video and audio downloader for Windows with automatic title cleaning, auto-resume, and Kotato-style desktop interface.

---

## ✨ Features

- **Facebook Title Cleaner**:
  - Automatically strips view/reaction metric prefixes (e.g. `1.5K views · 326 reactions _ `) and branding wrappers.
  - Automatically decodes HTML entities (e.g. `&#039;` -> `'`, `&amp;` -> `&`).
  - Preserves maximum safe title length for Windows (up to 200 characters).
- **Multi-Line Batch URL Pasting**:
  - Paste dozens of Facebook, YouTube, or reel URLs directly; automatically parsed and queued.
- **4x Parallel Multi-Threaded Engine**:
  - Downloads up to 4 videos simultaneously with high-speed fragment downloading.
- **True Pause All & Start All**:
  - **`Pause All`**: Pauses all active downloads while preserving partial `.part` files on disk.
  - **`Start All`**: Wakes up and auto-resumes all paused, queued, or failed downloads without restarting from 0%.
  - Individual per-row **Pause** / **Resume** buttons and **Open Folder** shortcuts.
- **Authentic Windows Desktop UI**:
  - Styled after Kotato All Video Downloader Pro (native toolstrip, Segoe UI, vector icons, no AI templates or gradients).
  - Status bar with live aggregate speed (`KB/s` / `MB/s`), file size counters, and progress tracking.

---

## 🚀 Quick Start

### 1. Launch Web Dashboard
Double-click:
```bat
Launch_Web_Browser.bat
```
Or run directly from terminal:
```bash
python web_app.py
```
Then open your browser at:
`http://127.0.0.1:5000`

### 2. Build Standalone `.exe`
Double-click:
```bat
build_exe.bat
```
The compiled executable will be located in:
`dist\AllVideoDownloaderPro\AllVideoDownloaderPro.exe`

---

## 🛠 Prerequisites

- Python 3.10+
- FFmpeg (automatically detected if installed via `winget install Gyan.FFmpeg`, Free Download Manager, or in PATH)
