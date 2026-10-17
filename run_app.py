"""
Video Downloader - Application Entry Point
===========================================
Launch the CustomTkinter GUI application.

Usage:
    python run_app.py
"""

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import VideoDownloaderApp


def main() -> None:
    app = VideoDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
