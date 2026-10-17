"""
All Video Downloader Pro - Professional Desktop UI
==================================================
Authentic Windows desktop application design:
  - Pixel-perfect native Windows 10/11 desktop styling (zero "AI template" look)
  - Clean vector SVG icons (no cartoon emojis)
  - Authentic Windows Explorer-style toolstrip and data grid
  - Multi-line batch download with Facebook title sanitizer and 4x parallel engine
  - Auto-resume and failure recovery
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import QUALITY_OPTIONS, find_ffmpeg, get_default_download_dir
from core.downloader import Downloader
from core.title_sanitizer import sanitize_title

app = Flask(__name__)
downloader = Downloader()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Video Downloader Pro</title>
    <style>
        :root {
            --win-bg: #f3f3f3;
            --win-chrome: #e6e6e6;
            --win-border: #d0d0d0;
            --win-text: #1a1a1a;
            --win-text-muted: #555555;
            --win-select: #e5f3ff;
            --win-select-border: #99d1ff;
            --win-green: #0e8a16;
            --win-blue: #0066cc;
            --win-red: #cc0000;
            --win-amber: #b25900;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Tahoma, sans-serif; }
        body { background: #dcdcdc; color: var(--win-text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; user-select: none; }

        /* Window Container */
        .app-window {
            background: #ffffff; width: 100%; height: 100%; display: flex; flex-direction: column;
            border: 1px solid #999999;
        }

        /* Top Menu & Tab Strip */
        .app-header {
            background: #f0f0f0; border-bottom: 1px solid var(--win-border); display: flex; flex-direction: column;
        }
        .app-menubar {
            height: 28px; display: flex; align-items: center; justify-content: space-between;
            padding: 0 8px; border-bottom: 1px solid #e0e0e0; font-size: 12px; color: #333333;
        }
        .app-title-tag { display: flex; align-items: center; gap: 6px; font-weight: 600; }
        .app-logo-badge {
            width: 16px; height: 16px; background: #c5221f; border-radius: 2px; display: flex;
            align-items: center; justify-content: center; color: white;
        }
        .app-logo-badge svg { width: 10px; height: 10px; fill: currentColor; }

        .app-tabs {
            height: 34px; display: flex; align-items: flex-end; padding: 0 6px; gap: 2px;
        }
        .tab-btn {
            height: 30px; padding: 0 20px; font-size: 12px; font-weight: 400; color: #444444;
            background: transparent; border: 1px solid transparent; border-bottom: none;
            border-top-left-radius: 3px; border-top-right-radius: 3px; cursor: pointer;
            display: flex; align-items: center;
        }
        .tab-btn:hover { background: #e5e5e5; }
        .tab-btn.active {
            background: #ffffff; color: #000000; font-weight: 600;
            border-color: var(--win-border); position: relative; bottom: -1px;
        }

        /* Windows Toolstrip Toolbar */
        .app-toolbar {
            background: #f7f7f7; padding: 4px 8px; display: flex; align-items: center;
            gap: 4px; border-bottom: 1px solid var(--win-border);
        }
        .tb-button {
            display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
            height: 28px; background: #ffffff; border: 1px solid #cccccc; border-radius: 2px;
            font-size: 12px; font-weight: 400; color: #222222; cursor: pointer;
        }
        .tb-button:hover { background: #e5f1fb; border-color: #0078d7; }
        .tb-button:active { background: #cce4f7; }
        .tb-button:disabled { opacity: 0.45; cursor: not-allowed; background: #f0f0f0; border-color: #d9d9d9; }
        
        .tb-button svg { width: 14px; height: 14px; flex-shrink: 0; }
        .tb-button.highlight { font-weight: 600; color: #0e8a16; border-color: #a3d9a5; background: #f4fbf5; }
        .tb-button.highlight:hover { background: #e6f6e8; border-color: #0e8a16; }
        .tb-separator { width: 1px; height: 20px; background: #d0d0d0; margin: 0 4px; }

        /* Content Area */
        .app-body { flex: 1; display: flex; overflow: hidden; background: #ffffff; }

        /* Sidebar Pane */
        .app-sidebar {
            width: 160px; background: #fafafa; border-right: 1px solid var(--win-border);
            padding: 8px 6px; display: flex; flex-direction: column; gap: 2px;
        }
        .sb-category {
            display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 2px;
            font-size: 12px; color: #333333; cursor: pointer; border: 1px solid transparent;
        }
        .sb-category:hover { background: #f0f0f0; }
        .sb-category.active {
            background: #4a4a4a; color: #ffffff; font-weight: 600;
        }
        .sb-category svg { width: 13px; height: 13px; flex-shrink: 0; fill: currentColor; }
        .sb-count {
            margin-left: auto; font-size: 11px; padding: 0 5px; border-radius: 2px;
            background: #e4e4e4; color: #444444; font-weight: 600;
        }
        .sb-category.active .sb-count { background: #666666; color: #ffffff; }

        /* Data Grid Table */
        .app-grid-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #ffffff; }
        .grid-header-row {
            display: grid; grid-template-columns: 120px 2fr 1.6fr 70px 100px 220px;
            background: #f0f0f0; border-bottom: 1px solid var(--win-border);
            font-size: 11px; font-weight: 600; color: #444444; height: 26px; align-items: center;
        }
        .grid-col-th {
            padding: 0 8px; border-right: 1px solid #e0e0e0; height: 100%; display: flex;
            align-items: center; overflow: hidden; white-space: nowrap;
        }
        .grid-col-th:last-child { border-right: none; }

        .grid-items-scroll { flex: 1; overflow-y: auto; }
        .grid-item-row {
            display: grid; grid-template-columns: 120px 2fr 1.6fr 70px 100px 220px;
            padding: 8px; border-bottom: 1px solid #ebebeb; align-items: center;
            font-size: 12px; position: relative; background: #ffffff;
        }
        .grid-item-row:hover { background: #f5f8fc; }
        .grid-item-row.selected { background: var(--win-select); }

        /* Row Progress Underline */
        .row-progress-track {
            position: absolute; bottom: 0; left: 0; height: 3px; background: #06b025;
            transition: width 0.3s;
        }

        /* Thumb Box */
        .cell-thumb-wrap { display: flex; align-items: center; gap: 6px; }
        .cell-play-icon svg { width: 12px; height: 12px; fill: #0078d7; }
        .cell-thumb-box {
            width: 84px; height: 48px; background: #374151; border-radius: 2px; position: relative;
            display: flex; align-items: center; justify-content: center; color: #9ca3af;
        }
        .cell-thumb-box svg { width: 22px; height: 22px; fill: #cbd5e1; }
        .cell-badge {
            position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.75);
            color: #ffffff; font-size: 9px; font-weight: 700; padding: 1px 3px; border-radius: 1px;
        }

        .cell-source { display: flex; flex-direction: column; gap: 3px; padding-right: 8px; }
        .source-text { color: #1a1a1a; font-size: 12px; word-break: break-all; max-height: 32px; overflow: hidden; line-height: 1.3; }
        .cell-sub-btn {
            align-self: flex-start; padding: 1px 8px; font-size: 11px; background: #ffffff;
            border: 1px solid #cccccc; border-radius: 2px; cursor: pointer; color: #333333;
        }
        .cell-sub-btn:hover { background: #e5f1fb; border-color: #0078d7; }

        .cell-dest { display: flex; flex-direction: column; gap: 3px; padding-right: 8px; }
        .dest-title { font-weight: 600; color: #000000; word-break: break-all; max-height: 32px; overflow: hidden; line-height: 1.3; }

        .cell-size { display: flex; flex-direction: column; font-size: 11px; color: #555555; gap: 1px; }

        .cell-status-wrap { display: flex; flex-direction: column; gap: 2px; position: relative; padding-right: 18px; }
        .status-speed-label { font-size: 11px; color: #1a1a1a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .big-percent-label { font-size: 22px; font-weight: 300; color: #444444; line-height: 1; }
        .cell-close-btn {
            position: absolute; top: -2px; right: 0; cursor: pointer; color: #777777; font-size: 14px;
        }
        .cell-close-btn:hover { color: #cc0000; font-weight: 700; }

        /* Empty placeholder */
        .grid-empty-state {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            height: 100%; color: #888888; font-size: 12px; gap: 8px;
        }
        .grid-empty-state svg { width: 36px; height: 36px; fill: #bbbbbb; }

        /* Bottom Status Bar (Windows standard) */
        .app-statusbar {
            height: 22px; background: #f0f0f0; border-top: 1px solid var(--win-border);
            display: flex; align-items: center; font-size: 11px; color: #333333;
        }
        .sb-pane {
            padding: 0 10px; border-right: 1px solid #d9d9d9; height: 100%; display: flex;
            align-items: center;
        }
        .sb-pane.flex { flex: 1; }
        .sb-pane.right { margin-left: auto; border-right: none; font-weight: 600; color: #0e8a16; }

        /* Modal Popup: Clean Windows Dialog */
        .win-modal-backdrop {
            position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: none;
            align-items: center; justify-content: center; z-index: 1000;
        }
        .win-modal-box {
            background: #ffffff; border: 1px solid #707070; width: 620px; max-width: 95vw;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25); display: flex; flex-direction: column;
        }
        .win-modal-header {
            background: #f0f0f0; height: 30px; display: flex; align-items: center; justify-content: space-between;
            padding: 0 10px; border-bottom: 1px solid #d0d0d0; font-size: 12px; font-weight: 600;
        }
        .win-modal-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
        .win-modal-footer {
            background: #f0f0f0; padding: 10px 16px; border-top: 1px solid #d0d0d0;
            display: flex; justify-content: flex-end; gap: 8px;
        }

        .win-form-row { display: flex; flex-direction: column; gap: 4px; }
        .win-label { font-size: 12px; font-weight: 600; color: #333333; }
        textarea.win-textarea {
            width: 100%; height: 120px; padding: 8px; font-family: Consolas, monospace;
            font-size: 12px; border: 1px solid #868686; outline: none; resize: vertical; line-height: 1.4;
        }
        textarea.win-textarea:focus, select.win-select:focus, input.win-input:focus { border-color: #0078d7; }
        
        .win-grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        select.win-select, input.win-input {
            width: 100%; padding: 5px 8px; font-size: 12px; border: 1px solid #868686;
            outline: none; background: #ffffff;
        }
        .win-btn {
            padding: 5px 16px; font-size: 12px; border: 1px solid #adadad; background: #e1e1e1;
            cursor: pointer; min-width: 80px;
        }
        .win-btn:hover { background: #e5f1fb; border-color: #0078d7; }
        .win-btn.primary { font-weight: 600; border-color: #0078d7; background: #0078d7; color: white; }
        .win-btn.primary:hover { background: #106ebe; }
    </style>
</head>
<body>

<div class="app-window">
    <!-- Header / Tab Strip -->
    <div class="app-header">
        <div class="app-menubar">
            <div class="app-title-tag">
                <span class="app-logo-badge">
                    <svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                </span>
                <span>All Video Downloader Pro</span>
            </div>
            <div style="font-size: 11px; color: #777777;">4x Parallel Download Engine</div>
        </div>

        <div class="app-tabs">
            <button class="tab-btn active" id="tab-tasks-btn" onclick="showTab('tasks')">Tasks</button>
            <button class="tab-btn" id="tab-download-btn" onclick="openAddDialog()">Download</button>
            <button class="tab-btn" onclick="alert('Audio conversion format presets (MP3/M4A) are built into the Quality settings.')">Convert</button>
            <button class="tab-btn" onclick="setFilter('Completed')">History</button>
        </div>
    </div>

    <!-- Toolbar -->
    <div class="app-toolbar">
        <button class="tb-button highlight" onclick="openAddDialog()">
            <svg viewBox="0 0 24 24" fill="#0e8a16"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            <span>Paste URL</span>
        </button>
        <button class="tb-button" onclick="openAddDialog()">
            <svg viewBox="0 0 24 24" fill="#0066cc"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            <span>Add Files</span>
        </button>
        <div class="tb-separator"></div>
        <button class="tb-button" id="btn-start-all" onclick="startAllQueued()">
            <svg viewBox="0 0 24 24" fill="#0e8a16"><path d="M8 5v14l11-7z"/></svg>
            <span>Start All</span>
        </button>
        <button class="tb-button" id="btn-pause-all" onclick="pauseAll()" disabled>
            <svg viewBox="0 0 24 24" fill="#b25900"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            <span>Pause All</span>
        </button>
        <div class="tb-separator"></div>
        <button class="tb-button" onclick="removeCompleted()">
            <svg viewBox="0 0 24 24" fill="#666666"><path d="M19 13H5v-2h14v2z"/></svg>
            <span>Remove Completed</span>
        </button>
        <button class="tb-button" onclick="clearAll()">
            <svg viewBox="0 0 24 24" fill="#cc0000"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            <span>Clear All</span>
        </button>
        <div class="tb-separator"></div>
        <button class="tb-button" onclick="openExcelTracker()" title="Open Excel spreadsheet tracking all URLs, filenames, and full description texts">
            <svg viewBox="0 0 24 24" fill="#0e8a16"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
            <span>Excel Tracker (.xlsx)</span>
        </button>
        <button class="tb-button" onclick="syncTrackerCloud()" title="Push the latest Excel & CSV download history directly to GitHub cloud">
            <svg viewBox="0 0 24 24" fill="#0066cc"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
            <span>Sync to Cloud</span>
        </button>
        <button class="tb-button" onclick="openLogsDialog()" title="View live engine and download execution logs">
            <svg viewBox="0 0 24 24" fill="#555555"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/></svg>
            <span>Live Logs</span>
        </button>
    </div>

    <!-- Workspace Body -->
    <div class="app-body">
        <!-- Sidebar Navigation -->
        <div class="app-sidebar">
            <div class="sb-category active" id="filter-all" onclick="setFilter('All')">
                <svg viewBox="0 0 24 24"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>
                <span>All</span>
                <span class="sb-count" id="count-all">0</span>
            </div>
            <div class="sb-category" id="filter-processing" onclick="setFilter('Processing')">
                <svg viewBox="0 0 24 24" fill="#0066cc"><path d="M8 5v14l11-7z"/></svg>
                <span>Processing</span>
                <span class="sb-count" id="count-processing">0</span>
            </div>
            <div class="sb-category" id="filter-paused" onclick="setFilter('Paused')">
                <svg viewBox="0 0 24 24" fill="#b25900"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                <span>Paused</span>
                <span class="sb-count" id="count-paused">0</span>
            </div>
            <div class="sb-category" id="filter-completed" onclick="setFilter('Completed')">
                <svg viewBox="0 0 24 24" fill="#0e8a16"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                <span>Completed</span>
                <span class="sb-count" id="count-completed">0</span>
            </div>
            <div class="sb-category" id="filter-failed" onclick="setFilter('Failed')">
                <svg viewBox="0 0 24 24" fill="#cc0000"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                <span>Failed</span>
                <span class="sb-count" id="count-failed">0</span>
            </div>
        </div>

        <!-- Data Grid -->
        <div class="app-grid-container">
            <div class="grid-header-row">
                <div class="grid-col-th">Thumbnail</div>
                <div class="grid-col-th">Source</div>
                <div class="grid-col-th">Destination</div>
                <div class="grid-col-th">Quality</div>
                <div class="grid-col-th">Size</div>
                <div class="grid-col-th">Status</div>
            </div>

            <div class="grid-items-scroll" id="grid-items">
                <div class="grid-empty-state" id="empty-state">
                    <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                    <span>Click <strong>Paste URL</strong> to add video or audio links</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Status Bar -->
    <div class="app-statusbar">
        <div class="sb-pane" id="sb-status-text">Ready</div>
        <div class="sb-pane" id="sb-counts-text">0 downloads: 0 processing</div>
        <div class="sb-pane" id="sb-power-text" style="color: #0e8a16;" title="Laptop sleep is automatically prevented while downloads are actively running">⚡ Laptop Sleep: Normal</div>
        <div class="sb-pane flex">Save location: {{ default_dir }}</div>
        <div class="sb-pane right" id="sb-speed-text">Speed: 0.00 KB/s</div>
    </div>
</div>

<!-- Add Download Modal Dialog -->
<div class="win-modal-backdrop" id="add-modal">
    <div class="win-modal-box">
        <div class="win-modal-header">
            <span>Add Download Link(s)</span>
            <span style="cursor: pointer; font-size: 14px;" onclick="closeAddDialog()">✕</span>
        </div>
        <div class="win-modal-body">
            <div class="win-form-row">
                <label class="win-label">Video or Audio Links (One link per line):</label>
                <textarea class="win-textarea" id="modal-urls-input" placeholder="Paste one or multiple video/reel links here:&#10;https://web.facebook.com/.../videos/...&#10;https://web.facebook.com/reel/...&#10;https://www.youtube.com/watch?v=..."></textarea>
            </div>

            <div class="win-grid-2col">
                <div class="win-form-row">
                    <label class="win-label">Download Quality:</label>
                    <select class="win-select" id="modal-quality-select">
                        <option value="Best Quality" selected>Best Quality (Original)</option>
                        <option value="1080p">HD 1080 (1080p)</option>
                        <option value="720p">HD 720 (720p)</option>
                        <option value="480p">SD 480 (480p)</option>
                        <option value="Audio Only">Audio Only (MP3 192k)</option>
                    </select>
                </div>
                <div class="win-form-row">
                    <label class="win-label">Simultaneous Downloads:</label>
                    <select class="win-select" id="modal-concurrency-select">
                        <option value="4" selected>4 Videos at once (Fast)</option>
                        <option value="2">2 Videos</option>
                        <option value="6">6 Videos</option>
                        <option value="1">1 by 1</option>
                    </select>
                </div>
            </div>

            <div class="win-form-row">
                <label class="win-label">Save To Folder:</label>
                <input class="win-input" type="text" id="modal-save-folder" value="{{ default_dir }}">
            </div>
        </div>
        <div class="win-modal-footer">
            <button class="win-btn" onclick="closeAddDialog()">Cancel</button>
            <button class="win-btn primary" onclick="submitDownloads()">Start Download</button>
        </div>
    </div>
</div>

<!-- Live Logs Modal Dialog -->
<div class="win-modal-backdrop" id="logs-modal">
    <div class="win-modal-box" style="width: 780px; max-width: 95vw;">
        <div class="win-modal-header">
            <span>Live Execution Logs (Real-time Engine Logs)</span>
            <span style="cursor: pointer; font-size: 14px;" onclick="closeLogsDialog()">✕</span>
        </div>
        <div class="win-modal-body">
            <div style="font-size: 11px; color: #555555;">Real-time logs for multi-threading, fragment fetching, FFmpeg merging, and Excel tracker updates:</div>
            <textarea class="win-textarea" id="logs-textarea" readonly style="height: 320px; background: #1e1e1e; color: #00ff66; font-family: Consolas, monospace; font-size: 11px; line-height: 1.4;"></textarea>
        </div>
        <div class="win-modal-footer">
            <button class="win-btn" onclick="fetchLogs()">Refresh</button>
            <button class="win-btn" onclick="navigator.clipboard.writeText(document.getElementById('logs-textarea').value); alert('Logs copied to clipboard!');">Copy Logs</button>
            <button class="win-btn primary" onclick="closeLogsDialog()">Close</button>
        </div>
    </div>
</div>

<script>
    let activeFilter = 'All';
    let pollInterval = null;
    let taskList = [];

    function openAddDialog() {
        document.getElementById('add-modal').style.display = 'flex';
        // Auto-paste clipboard if available
        if (navigator.clipboard && navigator.clipboard.readText) {
            navigator.clipboard.readText().then(text => {
                if (text && text.includes('http') && !document.getElementById('modal-urls-input').value) {
                    document.getElementById('modal-urls-input').value = text;
                }
            }).catch(() => {});
        }
    }

    function closeAddDialog() {
        document.getElementById('add-modal').style.display = 'none';
    }

    function setFilter(filter) {
        activeFilter = filter;
        document.querySelectorAll('.sb-category').forEach(el => el.classList.remove('active'));
        const el = document.getElementById('filter-' + filter.toLowerCase());
        if (el) el.classList.add('active');
        renderGrid(taskList);
    }

    async function submitDownloads() {
        const text = document.getElementById('modal-urls-input').value;
        const urls = text.split('\n').map(s => s.trim()).filter(s => s.length > 0 && s.startsWith('http'));

        if (urls.length === 0) {
            alert('Please paste at least one valid video URL starting with http/https.');
            return;
        }

        const quality = document.getElementById('modal-quality-select').value;
        const parallel = parseInt(document.getElementById('modal-concurrency-select').value) || 4;
        const saveDir = document.getElementById('modal-save-folder').value.trim();

        closeAddDialog();
        document.getElementById('btn-pause-all').disabled = false;
        document.getElementById('sb-status-text').innerText = 'Starting ' + urls.length + ' download(s)...';

        try {
            const resp = await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    urls: urls,
                    quality: quality,
                    parallel: parallel,
                    save_dir: saveDir
                })
            });
            const res = await resp.json();
            if (res.error) {
                alert('Error: ' + res.error);
                return;
            }
            pollStatusOnce();
        } catch (e) {
            alert('Download failed to start: ' + e);
        }
    }

    async function pollStatusOnce() {
        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();
            taskList = data.tasks || [];

            // Update count badges
            document.getElementById('count-all').innerText = data.total || 0;
            document.getElementById('count-processing').innerText = data.active || 0;
            document.getElementById('count-completed').innerText = data.completed || 0;
            document.getElementById('count-failed').innerText = data.errors || 0;
            document.getElementById('count-paused').innerText = (data.paused || data.cancelled || 0);

            // Status bar update
            document.getElementById('sb-counts-text').innerText = `${data.total} downloads: ${data.active} processing, ${data.completed} completed`;
            
            let totalSpeedKB = 0;
            taskList.forEach(t => {
                if (t.speed && t.speed.includes('MiB/s')) {
                    totalSpeedKB += parseFloat(t.speed) * 1024;
                } else if (t.speed && t.speed.includes('KiB/s')) {
                    totalSpeedKB += parseFloat(t.speed);
                }
            });
            document.getElementById('sb-speed-text').innerText = `Speed: ${totalSpeedKB.toFixed(2)} KB/s`;

            const powerEl = document.getElementById('sb-power-text');
            if (powerEl) {
                powerEl.innerText = data.is_busy ? '⚡ Laptop Sleep: Prevented (Awake)' : 'Laptop Sleep: Normal';
                powerEl.style.color = data.is_busy ? '#b25900' : '#0e8a16';
            }

            const hasUnfinished = taskList.some(t => ['PAUSED', 'CANCELLED', 'ERROR', 'QUEUED'].includes(t.status));
            document.getElementById('btn-start-all').disabled = !hasUnfinished;

            if (data.is_busy) {
                document.getElementById('sb-status-text').innerText = `Downloading ${data.active} file(s) in parallel...`;
                document.getElementById('btn-pause-all').disabled = false;
            } else {
                document.getElementById('sb-status-text').innerText = data.total > 0 ? (hasUnfinished ? 'Paused / Waiting' : 'Finished') : 'Ready';
                document.getElementById('btn-pause-all').disabled = true;
            }

            renderGrid(taskList);
        } catch (err) {}
    }

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollStatusOnce();
        pollInterval = setInterval(pollStatusOnce, 800);
    }

    function renderGrid(tasks) {
        const container = document.getElementById('grid-items');
        let filtered = tasks;

        if (activeFilter === 'Processing') {
            filtered = tasks.filter(t => ['CONNECTING', 'DOWNLOADING', 'POST_PROCESSING', 'QUEUED'].includes(t.status) || t.status.startsWith('AUTO-RESUMING'));
        } else if (activeFilter === 'Completed') {
            filtered = tasks.filter(t => t.status === 'COMPLETED');
        } else if (activeFilter === 'Failed') {
            filtered = tasks.filter(t => t.status === 'ERROR');
        } else if (activeFilter === 'Paused') {
            filtered = tasks.filter(t => ['PAUSED', 'CANCELLED'].includes(t.status));
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="grid-empty-state">
                    <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                    <span>${tasks.length === 0 ? 'Click <strong>Paste URL</strong> to add video or audio links' : 'No tasks in this category'}</span>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        filtered.forEach(task => {
            const isAudio = task.title.toLowerCase().endsWith('.mp3');
            const badgeText = isAudio ? 'MP3' : 'HD 1080';
            const rowClass = task.status === 'DOWNLOADING' ? 'grid-item-row selected' : 'grid-item-row';
            const sizeDisplay = (task.downloaded_bytes !== '—' && task.total_bytes !== '—') 
                ? `${task.downloaded_bytes} / ${task.total_bytes}` 
                : (task.total_bytes !== '—' ? task.total_bytes : '—');

            let actionBtnHtml = '';
            if (['DOWNLOADING', 'CONNECTING', 'POST_PROCESSING'].includes(task.status) || task.status.startsWith('AUTO-RESUMING')) {
                actionBtnHtml = `<button class="cell-sub-btn" style="color: #b25900; font-weight: 600;" onclick="pauseTask(${task.id})">Pause</button>`;
            } else if (['PAUSED', 'CANCELLED', 'ERROR', 'QUEUED'].includes(task.status)) {
                actionBtnHtml = `<button class="cell-sub-btn" style="color: #0066cc; font-weight: 600;" onclick="resumeTask(${task.id})">Resume</button>`;
            } else if (task.status === 'COMPLETED') {
                actionBtnHtml = `<button class="cell-sub-btn" style="color: #0e8a16; font-weight: 600;" onclick="openFolder('${(task.save_dir || '').replace(/\\/g, '\\\\')}')">Open Folder</button>`;
            }

            const statusText = task.status === 'DOWNLOADING' 
                ? `Downloading: ${task.speed}` 
                : (task.status === 'POST_PROCESSING' ? 'Processing...' : (task.error_message ? `Error: ${task.error_message}` : task.status));

            const row = document.createElement('div');
            row.className = rowClass;
            row.innerHTML = `
                <!-- Thumbnail -->
                <div class="cell-thumb-wrap">
                    <span class="cell-play-icon">
                        <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    </span>
                    <div class="cell-thumb-box">
                        <svg viewBox="0 0 24 24"><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/></svg>
                        <span class="cell-badge">${badgeText}</span>
                    </div>
                </div>

                <!-- Source -->
                <div class="cell-source">
                    <span class="source-text" title="${task.url}">${task.url}</span>
                    <button class="cell-sub-btn" onclick="window.open('${task.url}', '_blank')">Browse</button>
                </div>

                <!-- Destination -->
                <div class="cell-dest">
                    <span class="dest-title" title="${task.title}">${task.title}</span>
                    <button class="cell-sub-btn" onclick="openFolder('${(task.save_dir || '').replace(/\\/g, '\\\\')}')">Folder</button>
                </div>

                <!-- Quality -->
                <div style="font-size: 11px; color: #444444;">${document.getElementById('modal-quality-select').value}</div>

                <!-- Size -->
                <div class="cell-size">
                    <span>${sizeDisplay}</span>
                </div>

                <!-- Status -->
                <div class="cell-status-wrap">
                    <span class="cell-close-btn" title="Remove Task" onclick="removeTask(${task.id})">✕</span>
                    <span class="status-speed-label" title="${statusText}">${statusText}</span>
                    <div class="big-percent-label">${task.percent}%</div>
                    <div style="margin-top: 2px;">
                        ${actionBtnHtml}
                    </div>
                </div>

                <!-- Bottom Progress Line -->
                <div class="row-progress-track" style="width: ${task.percent}%;"></div>
            `;
            container.appendChild(row);
        });
    }

    async function resumeTask(id) {
        await fetch('/api/resume_task', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({task_id: id})
        });
        pollStatusOnce();
    }

    async function pauseTask(id) {
        await fetch('/api/pause_task', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({task_id: id})
        });
        pollStatusOnce();
    }

    async function startAllQueued() {
        document.getElementById('sb-status-text').innerText = 'Resuming unfinished tasks...';
        await fetch('/api/start_all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({parallel: 4})
        });
        pollStatusOnce();
    }

    async function pauseAll() {
        await fetch('/api/pause_all', {method: 'POST'});
        document.getElementById('sb-status-text').innerText = 'Paused All';
        pollStatusOnce();
    }

    async function removeCompleted() {
        await fetch('/api/remove_completed', {method: 'POST'});
        pollStatusOnce();
    }

    async function removeTask(id) {
        await fetch('/api/remove_task', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({task_id: id})
        });
        pollStatusOnce();
    }

    async function clearAll() {
        if (confirm('Clear all tasks from the list?')) {
            await fetch('/api/clear_all', {method: 'POST'});
            pollStatusOnce();
        }
    }

    async function openFolder(folder) {
        await fetch('/api/open_folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({folder: folder || ''})
        });
    async function openExcelTracker() {
        const saveDir = document.getElementById('modal-save-folder') ? document.getElementById('modal-save-folder').value.trim() : '';
        const resp = await fetch('/api/open_tracker', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({folder: saveDir})
        });
        const res = await resp.json();
        if (res.error) alert(res.error);
    }

    let logsInterval = null;
    async function openLogsDialog() {
        document.getElementById('logs-modal').style.display = 'flex';
        await fetchLogs();
        if (logsInterval) clearInterval(logsInterval);
        logsInterval = setInterval(fetchLogs, 1500);
    }

    function closeLogsDialog() {
        document.getElementById('logs-modal').style.display = 'none';
        if (logsInterval) clearInterval(logsInterval);
    }

    async function fetchLogs() {
        try {
            const resp = await fetch('/api/logs');
            const data = await resp.json();
            const box = document.getElementById('logs-textarea');
            if (box && data.logs) {
                const atBottom = box.scrollHeight - box.scrollTop <= box.clientHeight + 50;
                box.value = data.logs.join('\n');
                if (atBottom) {
                    box.scrollTop = box.scrollHeight;
                }
            }
    async function syncTrackerCloud() {
        document.getElementById('sb-status-text').innerText = 'Syncing Excel & CSV trackers to GitHub cloud...';
        try {
            const resp = await fetch('/api/sync_cloud', {method: 'POST'});
            const res = await resp.json();
            if (res.success) {
                alert('Spreadsheet tracker successfully synced and pushed to GitHub cloud!');
            } else {
                alert('Cloud sync status: ' + (res.message || res.error || 'Done'));
            }
        } catch (e) {
            alert('Cloud sync error: ' + e);
        }
        pollStatusOnce();
    }

    // Start auto polling as soon as DOM loads
    window.addEventListener('DOMContentLoaded', startPolling);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        default_dir=get_default_download_dir(),
    )


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    urls = data.get("urls", [])
    quality = data.get("quality", "Best Quality")
    parallel = int(data.get("parallel", 4))
    save_dir = data.get("save_dir", "").strip() or get_default_download_dir()

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    format_str = QUALITY_OPTIONS.get(quality, "bestvideo+bestaudio/best")
    os.makedirs(save_dir, exist_ok=True)

    downloader.start_download_async(
        urls=urls,
        save_dir=save_dir,
        format_str=format_str,
        max_parallel=parallel,
    )
    return jsonify({"success": True})


@app.route("/api/status")
def status():
    return jsonify(downloader.get_status_payload())


@app.route("/api/start_all", methods=["POST"])
def start_all():
    data = request.get_json() or {}
    parallel = int(data.get("parallel", 4))
    resumed = downloader.start_all_unfinished(max_parallel=parallel)
    return jsonify({"success": True, "resumed_count": resumed})


@app.route("/api/pause_all", methods=["POST"])
def pause_all_endpoint():
    downloader.pause_all()
    return jsonify({"success": True})


@app.route("/api/cancel", methods=["POST"])
def cancel_endpoint():
    downloader.pause_all()
    return jsonify({"success": True})


@app.route("/api/resume_task", methods=["POST"])
def resume_task_endpoint():
    data = request.get_json() or {}
    task_id = int(data.get("task_id", 0))
    resumed = downloader.resume_task(task_id)
    return jsonify({"success": resumed})


@app.route("/api/pause_task", methods=["POST"])
def pause_task_endpoint():
    data = request.get_json() or {}
    task_id = int(data.get("task_id", 0))
    paused = downloader.pause_task(task_id)
    return jsonify({"success": paused})


@app.route("/api/remove_task", methods=["POST"])
def remove_task_endpoint():
    data = request.get_json() or {}
    task_id = int(data.get("task_id", 0))
    downloader.remove_task(task_id)
    return jsonify({"success": True})


@app.route("/api/remove_completed", methods=["POST"])
def remove_completed_endpoint():
    downloader.remove_completed()
    return jsonify({"success": True})


@app.route("/api/clear_all", methods=["POST"])
def clear_all_endpoint():
    downloader.clear_all()
    return jsonify({"success": True})


@app.route("/api/open_folder", methods=["POST"])
def open_folder_endpoint():
    data = request.get_json() or {}
    folder = data.get("folder", "").strip() or get_default_download_dir()
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    return jsonify({"success": True})


@app.route("/api/logs")
def get_logs_endpoint():
    return jsonify({"logs": downloader.get_logs()})


@app.route("/api/open_tracker", methods=["POST"])
def open_tracker_endpoint():
    data = request.get_json() or {}
    folder = data.get("folder", "").strip() or get_default_download_dir()
    os.makedirs(folder, exist_ok=True)
    from core.history_tracker import get_tracker_path, record_download_history
    xlsx_path = get_tracker_path(folder)
    if not os.path.isfile(xlsx_path):
        # Create initial empty template if file does not exist yet
        record_download_history({
            "status": "INITIALIZED",
            "clean_title": "All Video Downloader Pro Tracker",
            "filename": "",
            "raw_title": "",
            "description": "This Excel spreadsheet automatically tracks all downloaded video URLs, clean filenames, and full description captions.",
            "url": "https://github.com/sadeeqdahuwa/Video-Downloader",
            "size": "—",
            "duration": "—",
            "format": "System",
            "file_path": folder,
        }, folder)
    if sys.platform == "win32":
        try:
            os.startfile(xlsx_path)
        except Exception as e:
            return jsonify({"error": f"Could not launch Excel: {e}"}), 500
    return jsonify({"success": True, "path": xlsx_path})


@app.route("/api/sync_cloud", methods=["POST"])
def sync_cloud_endpoint():
    from core.history_tracker import sync_tracker_to_cloud
    res = sync_tracker_to_cloud(log_callback=downloader.log)
    return jsonify(res)


if __name__ == "__main__":
    import threading
    import time
    import webbrowser

    port = 5000
    print(f"Starting All Video Downloader Pro UI on http://127.0.0.1:{port}")

    def _open_browser():
        time.sleep(1.0)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=port, debug=False)

