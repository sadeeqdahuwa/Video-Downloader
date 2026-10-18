# StreamVault Pro

A high-performance multi-source video and audio downloader desktop application with Facebook title cleaning, automatic Excel history tracking, sleep prevention, and in-app auto-updating.

---

## ✨ Key Features

- **Modern Dark Slate Interface**:
  - Sleek, modern card-based UI with direct quick-paste input and multi-line batch expansion drawer.
  - Live aggregate download speed meter (`KB/s` / `MB/s`) and active progress tracking.
- **Facebook & Social Title Cleaner**:
  - Automatically strips view/reaction metric prefixes (e.g. `1.5K views · 326 reactions _ `) and branding wrappers.
  - Automatically decodes HTML entities (e.g. `&#039;` -> `'`, `&amp;` -> `&`).
  - Preserves maximum safe title length for Windows (up to 200 characters).
- **Excel & CSV History Tracker**:
  - Automatically logs every download timestamp, URL, clean title, raw title, and **full untruncated post captions / descriptions** to `download_history.xlsx` and `download_history.csv`.
  - One-click **Cloud Sync** directly pushes spreadsheet history to your GitHub repository.
- **Laptop Sleep Prevention**:
  - Automatically keeps Windows awake and Wi-Fi active while downloads are running (`kernel32.SetThreadExecutionState`). Restores normal sleep mode as soon as downloads complete.
- **4x Parallel Multi-Threaded Engine**:
  - Downloads up to 4 videos simultaneously with high-speed fragment downloading.
  - **`Start All`** & **`Pause All`** with partial `.part` file auto-resume.
- **In-App Auto-Updater**:
  - Checks GitHub Releases with 1-click in-place updating.
  - Dynamically updates video extraction scraper algorithms (`yt-dlp`) without needing a new app installation.

---

## 🚀 Quick Start

### 1. Launch Desktop Application
Double-click:
```bat
Launch_Desktop_App.bat
```
Or run directly from terminal:
```bash
python run_app.py
```
This launches **StreamVault Pro** directly in a **native standalone desktop window** (no browser needed).

*Tip: If you prefer using your regular web browser, run `Launch_Web_Browser.bat` or `python web_app.py --browser`.*

### 2. Build Standalone Portable `.exe`
Double-click:
```bat
build_exe.bat
```
The compiled executable will be located in:
`dist\StreamVaultPro\StreamVaultPro.exe`

---

## 🛠 Prerequisites

- Python 3.10+
- FFmpeg (automatically bundled in portable release or detected in PATH)
