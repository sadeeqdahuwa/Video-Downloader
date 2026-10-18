"""
StreamVault Pro - Application Entry Point
==========================================
Launch the StreamVault Pro native desktop application window.

Usage:
    python run_app.py
    python run_app.py --tkinter   (legacy CustomTkinter GUI)
"""

import sys
import os
import subprocess

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    if "--tkinter" in sys.argv:
        from ui.app import VideoDownloaderApp
        app = VideoDownloaderApp()
        app.mainloop()
    else:
        # Launch modern native desktop window
        web_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_app.py")
        subprocess.run([sys.executable, web_app_path] + sys.argv[1:])


if __name__ == "__main__":
    main()
