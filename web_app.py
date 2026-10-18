"""
StreamVault Pro - Kotato-Style High-Performance Video Downloader & Archiver
==========================================================================
Faithful, modern desktop replica of the classic All Video Downloader Pro (Kotato):
  - Top Tabs: Download, Tasks, Convert, History
  - Action Toolbar: Paste Link, Start All, Pause All, Remove Completed, Clear All, Open Folder, Excel Tracker, Cloud Sync, Logs, Updates
  - Left Filter Sidebar: All, Processing, Paused, Completed, Failed with live counts
  - Kotato Data Grid: Thumbnail, Source URL, Clean Title, Quality, Duration, Size, Status & Speed
  - Bulletproof multi-link paste: automatically splits 1 or 200+ links onto their own lines with \n
  - High-performance in-place DOM updates: silky smooth even with 500+ tasks
  - Embedded application icon & Windows PE metadata
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request, send_file

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import APP_NAME, APP_TAGLINE, APP_VERSION, QUALITY_OPTIONS, find_ffmpeg, get_default_download_dir
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
    <title>{{ app_name }} - {{ app_tagline }}</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <style>
        :root {
            --win-bg: #f0f2f5;
            --win-header: #e4e6eb;
            --win-border: #cbd5e1;
            --win-text: #0f172a;
            --win-text-sub: #64748b;
            --win-card: #ffffff;
            --win-hover: #f1f5f9;
            --win-active: #e2e8f0;
            --accent-blue: #2563eb;
            --accent-green: #16a34a;
            --accent-amber: #d97706;
            --accent-red: #dc2626;
            --grid-line: #e2e8f0;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Tahoma, sans-serif; }
        body { background: #dcdfe4; color: var(--win-text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; user-select: none; font-size: 12px; }

        /* Window Container */
        .app-window {
            background: #ffffff; width: 100%; height: 100%; display: flex; flex-direction: column;
            border: 1px solid #94a3b8;
        }

        /* Top Menu & Tab Strip */
        .app-header {
            background: #eef1f5; border-bottom: 1px solid var(--win-border); display: flex; flex-direction: column;
        }
        .app-menubar {
            height: 30px; display: flex; align-items: center; justify-content: space-between;
            padding: 0 10px; border-bottom: 1px solid #dfe3ea; font-size: 12px; color: #1e293b;
        }
        .app-title-tag { display: flex; align-items: center; gap: 8px; font-weight: 700; }
        .app-logo-badge {
            width: 18px; height: 18px; background: linear-gradient(135deg, #2563eb, #7c3aed);
            border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white;
        }
        .app-logo-badge svg { width: 11px; height: 11px; fill: currentColor; }

        .app-tabs {
            height: 36px; display: flex; align-items: flex-end; padding: 0 8px; gap: 4px;
        }
        .tab-btn {
            height: 32px; padding: 0 22px; font-size: 12px; font-weight: 500; color: #475569;
            background: transparent; border: 1px solid transparent; border-bottom: none;
            border-top-left-radius: 4px; border-top-right-radius: 4px; cursor: pointer;
            display: flex; align-items: center; gap: 6px; transition: all 0.15s ease;
        }
        .tab-btn:hover { background: #e2e8f0; color: #0f172a; }
        .tab-btn.active {
            background: #ffffff; color: var(--accent-blue); font-weight: 700;
            border-color: var(--win-border); border-bottom: 1px solid #ffffff; position: relative; bottom: -1px;
        }

        /* Windows Action Toolstrip */
        .app-toolbar {
            background: #f8fafc; padding: 5px 10px; display: flex; align-items: center;
            gap: 5px; border-bottom: 1px solid var(--win-border); flex-wrap: wrap;
        }
        .tb-button {
            display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
            height: 30px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px;
            font-size: 12px; font-weight: 500; color: #1e293b; cursor: pointer; transition: all 0.15s ease;
        }
        .tb-button:hover { background: #f1f5f9; border-color: #94a3b8; }
        .tb-button:active { background: #e2e8f0; }
        .tb-button:disabled { opacity: 0.45; cursor: not-allowed; background: #f8fafc; border-color: #e2e8f0; }
        
        .tb-button svg { width: 15px; height: 15px; flex-shrink: 0; }
        .tb-button.highlight {
            font-weight: 700; color: #15803d; border-color: #86efac; background: #f0fdf4;
        }
        .tb-button.highlight:hover { background: #dcfce7; border-color: #4ade80; }
        .tb-separator { width: 1px; height: 20px; background: #cbd5e1; margin: 0 4px; }

        /* Main Workspace Container */
        .app-body { flex: 1; display: flex; overflow: hidden; background: #ffffff; position: relative; }

        /* View Panels */
        .view-panel { width: 100%; height: 100%; display: none; overflow: hidden; }
        .view-panel.active { display: flex; }

        /* --- DOWNLOAD COMPOSER VIEW --- */
        .composer-view {
            width: 100%; height: 100%; display: flex; flex-direction: column; padding: 20px 28px;
            background: #f8fafc; overflow-y: auto;
        }
        .composer-card {
            background: #ffffff; border: 1px solid var(--win-border); border-radius: 6px;
            padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); max-width: 900px;
            display: flex; flex-direction: column; gap: 16px;
        }
        .composer-header-row { display: flex; justify-content: space-between; align-items: baseline; }
        .composer-title { font-size: 14px; font-weight: 700; color: #0f172a; }
        .badge-count {
            font-size: 12px; font-weight: 700; background: #dbeafe; color: #1d4ed8;
            padding: 3px 10px; border-radius: 12px;
        }

        .composer-textarea {
            width: 100%; height: 220px; padding: 12px 14px; border: 1px solid #cbd5e1;
            border-radius: 4px; font-family: "Consolas", "JetBrains Mono", monospace;
            font-size: 12px; line-height: 1.6; resize: vertical; outline: none;
            background: #ffffff; color: #0f172a;
        }
        .composer-textarea:focus { border-color: var(--accent-blue); box-shadow: 0 0 0 2px rgba(37,99,235,0.15); }

        .composer-btn-bar { display: flex; justify-content: space-between; align-items: center; }
        .action-group-left { display: flex; gap: 8px; }
        .composer-btn {
            height: 32px; padding: 0 14px; border: 1px solid #cbd5e1; border-radius: 4px;
            background: #ffffff; font-size: 12px; font-weight: 600; color: #334155; cursor: pointer;
            display: inline-flex; align-items: center; gap: 6px;
        }
        .composer-btn:hover { background: #f1f5f9; border-color: #94a3b8; }
        .composer-btn.danger:hover { background: #fee2e2; border-color: #f87171; color: #b91c1c; }

        .composer-grid-settings {
            display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 4px;
        }
        .setting-field { display: flex; flex-direction: column; gap: 6px; }
        .setting-label { font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; }
        .setting-select, .setting-input {
            height: 34px; padding: 0 10px; border: 1px solid #cbd5e1; border-radius: 4px;
            font-size: 12px; background: #ffffff; color: #0f172a; outline: none;
        }
        .setting-select:focus, .setting-input:focus { border-color: var(--accent-blue); }

        .folder-row { display: flex; gap: 8px; }
        .folder-row input { flex: 1; }

        .btn-download-hero {
            height: 44px; background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border: none; border-radius: 6px; color: #ffffff; font-size: 14px; font-weight: 700;
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            cursor: pointer; box-shadow: 0 2px 4px rgba(37,99,235,0.25); transition: all 0.15s ease;
            margin-top: 8px;
        }
        .btn-download-hero:hover { background: linear-gradient(135deg, #1d4ed8, #1e40af); transform: translateY(-1px); }
        .btn-download-hero:active { transform: translateY(0); }
        .btn-download-hero svg { width: 18px; height: 18px; fill: currentColor; }

        /* --- TASKS GRID VIEW (Kotato Style) --- */
        .tasks-view { width: 100%; height: 100%; display: flex; }

        /* Left Filter Sidebar */
        .app-sidebar {
            width: 175px; background: #f8fafc; border-right: 1px solid var(--win-border);
            padding: 10px 8px; display: flex; flex-direction: column; gap: 3px; flex-shrink: 0;
        }
        .sb-category {
            display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 4px;
            font-size: 12px; color: #334155; cursor: pointer; border: 1px solid transparent;
            transition: all 0.1s ease;
        }
        .sb-category:hover { background: #f1f5f9; color: #0f172a; }
        .sb-category.active {
            background: #2563eb; color: #ffffff; font-weight: 600;
        }
        .sb-category svg { width: 14px; height: 14px; flex-shrink: 0; fill: currentColor; }
        .sb-count {
            margin-left: auto; font-size: 11px; padding: 1px 6px; border-radius: 10px;
            background: #e2e8f0; color: #475569; font-weight: 700;
        }
        .sb-category.active .sb-count { background: rgba(255,255,255,0.25); color: #ffffff; }

        /* Main Data Grid */
        .grid-container {
            flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #ffffff;
        }
        .grid-header {
            display: grid;
            grid-template-columns: 46px 1fr 1.6fr 105px 75px 125px 230px 100px;
            background: #f1f5f9; border-bottom: 1px solid var(--win-border);
            font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase;
            letter-spacing: 0.5px; line-height: 32px; padding: 0 10px;
        }
        .grid-header > div { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        .grid-body {
            flex: 1; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column;
        }

        .task-row {
            display: grid;
            grid-template-columns: 46px 1fr 1.6fr 105px 75px 125px 230px 100px;
            padding: 8px 10px; border-bottom: 1px solid var(--grid-line);
            align-items: center; font-size: 12px; transition: background 0.1s;
        }
        .task-row:hover { background: #f8fafc; }

        .cell-thumb {
            width: 32px; height: 28px; background: #e2e8f0; border-radius: 3px;
            display: flex; align-items: center; justify-content: center; color: #64748b;
        }
        .cell-thumb svg { width: 16px; height: 16px; fill: currentColor; }

        .cell-source {
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 12px;
            font-family: monospace; font-size: 11px; color: #64748b;
        }
        .cell-title {
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 12px;
            font-weight: 600; color: #0f172a;
        }

        .quality-pill {
            display: inline-block; padding: 2px 7px; border-radius: 3px;
            font-size: 10px; font-weight: 700; background: #f1f5f9; color: #475569;
            border: 1px solid #cbd5e1; text-align: center;
        }

        .cell-duration { color: #64748b; font-size: 11px; }
        .cell-size { font-size: 11px; color: #334155; }

        /* Progress Cell */
        .cell-progress { display: flex; flex-direction: column; gap: 4px; padding-right: 12px; }
        .progress-bar-bg {
            width: 100%; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;
        }
        .progress-bar-fill {
            height: 100%; background: var(--accent-green); width: 0%; transition: width 0.2s ease;
        }
        .progress-meta {
            display: flex; justify-content: space-between; font-size: 10.5px; color: #475569;
        }
        .status-badge {
            font-weight: 700;
        }
        .status-badge.DOWNLOADING { color: var(--accent-blue); }
        .status-badge.COMPLETED { color: var(--accent-green); }
        .status-badge.ERROR { color: var(--accent-red); }
        .status-badge.PAUSED { color: var(--accent-amber); }
        .status-badge.QUEUED { color: #64748b; }

        .cell-actions { display: flex; gap: 4px; }
        .row-action-btn {
            width: 26px; height: 26px; border: 1px solid #cbd5e1; border-radius: 3px;
            background: #ffffff; color: #475569; display: flex; align-items: center; justify-content: center;
            cursor: pointer; transition: all 0.1s;
        }
        .row-action-btn:hover { background: #f1f5f9; color: #0f172a; border-color: #94a3b8; }
        .row-action-btn svg { width: 13px; height: 13px; fill: currentColor; }

        .grid-empty-state {
            margin: auto; display: flex; flex-direction: column; align-items: center;
            justify-content: center; gap: 12px; color: #94a3b8; padding: 60px 0;
        }
        .grid-empty-state svg { width: 44px; height: 44px; fill: #cbd5e1; }
        .grid-empty-state span { font-size: 13px; }

        /* Bottom Status Bar */
        .app-statusbar {
            height: 26px; background: #f1f5f9; border-top: 1px solid var(--win-border);
            display: flex; align-items: center; padding: 0 12px; font-size: 11px; color: #475569;
            gap: 16px;
        }
        .sb-status-item { display: flex; align-items: center; gap: 6px; }
        .sb-status-item.right { margin-left: auto; font-weight: 600; color: #16a34a; }

        /* Modals */
        .modal-backdrop {
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); display: none;
            align-items: center; justify-content: center; z-index: 1000;
        }
        .modal-card {
            background: #ffffff; border: 1px solid #94a3b8; border-radius: 6px;
            width: 640px; max-width: 95vw; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            display: flex; flex-direction: column; overflow: hidden;
        }
        .modal-header {
            background: #f1f5f9; padding: 10px 16px; border-bottom: 1px solid #cbd5e1;
            display: flex; align-items: center; justify-content: space-between;
            font-size: 13px; font-weight: 700; color: #0f172a;
        }
        .modal-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; max-height: 75vh; overflow-y: auto; }
        .modal-footer {
            background: #f8fafc; padding: 10px 16px; border-top: 1px solid #cbd5e1;
            display: flex; justify-content: flex-end; gap: 8px;
        }
    </style>
</head>
<body>

<div class="app-window">
    <!-- Header -->
    <div class="app-header">
        <div class="app-menubar">
            <div class="app-title-tag">
                <div class="app-logo-badge">
                    <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                </div>
                <span>{{ app_name }}</span>
                <span style="font-weight: 400; color: #64748b;">— {{ app_tagline }} (v{{ app_version }})</span>
            </div>
            <div style="font-size: 11px; color: #64748b;">
                Bundled Portable Engine • Clean Title Filter Active
            </div>
        </div>

        <!-- Top Navigation Tabs (Kotato Style) -->
        <div class="app-tabs">
            <button class="tab-btn active" id="tab-download-btn" onclick="switchTab('download')">
                <svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                <span>Download</span>
            </button>
            <button class="tab-btn" id="tab-tasks-btn" onclick="switchTab('tasks')">
                <svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
                <span>Tasks (<span id="tab-task-count">0</span>)</span>
            </button>
            <button class="tab-btn" id="tab-convert-btn" onclick="switchTab('convert')">
                <svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                <span>Convert</span>
            </button>
            <button class="tab-btn" id="tab-history-btn" onclick="switchTab('history')">
                <svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;"><path d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg>
                <span>History</span>
            </button>
        </div>

        <!-- Action Toolbar -->
        <div class="app-toolbar">
            <button class="tb-button highlight" onclick="pasteClipboardDirect()" title="Read clipboard, auto-extract all links line-by-line, and open Download composer">
                <svg viewBox="0 0 24 24" fill="#15803d"><path d="M19 2h-4.18C14.4.84 13.3 0 12 0c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm7 18H5V4h2v3h10V4h2v16z"/></svg>
                <span>Paste Link</span>
            </button>

            <button class="tb-button" id="btn-start-all" onclick="startAllTasks()" title="Start or resume all queued / paused downloads">
                <svg viewBox="0 0 24 24" fill="#15803d"><path d="M8 5v14l11-7z"/></svg>
                <span>Start All</span>
            </button>

            <button class="tb-button" id="btn-pause-all" onclick="pauseAllTasks()" title="Pause all active downloads">
                <svg viewBox="0 0 24 24" fill="#d97706"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                <span>Pause All</span>
            </button>

            <div class="tb-separator"></div>

            <button class="tb-button" onclick="removeCompletedTasks()" title="Remove all completed tasks from the grid">
                <svg viewBox="0 0 24 24" fill="#64748b"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>
                <span>Remove Completed</span>
            </button>

            <button class="tb-button" onclick="clearAllTasks()" title="Clear all tasks from the grid">
                <svg viewBox="0 0 24 24" fill="#dc2626"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                <span>Clear All</span>
            </button>

            <div class="tb-separator"></div>

            <button class="tb-button" onclick="openDownloadFolder()" title="Open the current save folder in Windows Explorer">
                <svg viewBox="0 0 24 24" fill="#2563eb"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                <span>Open Folder</span>
            </button>

            <button class="tb-button" onclick="openExcelTracker()" title="Open Excel history spreadsheet tracking all titles and full descriptions">
                <svg viewBox="0 0 24 24" fill="#15803d"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
                <span>Excel Tracker</span>
            </button>

            <button class="tb-button" onclick="syncTrackerCloud()" title="Sync download history to GitHub cloud">
                <svg viewBox="0 0 24 24" fill="#0284c7"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
                <span>Cloud Sync</span>
            </button>

            <button class="tb-button" onclick="openLogsModal()" title="View live engine and execution logs">
                <svg viewBox="0 0 24 24" fill="#475569"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                <span>Logs</span>
            </button>

            <button class="tb-button" onclick="openUpdateModal()" title="Check for app updates or dynamic extractor updates">
                <svg viewBox="0 0 24 24" fill="#7c3aed"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
                <span>Updates</span>
            </button>
        </div>
    </div>

    <!-- Main Workspace -->
    <div class="app-body">

        <!-- 1. DOWNLOAD COMPOSER VIEW -->
        <div class="view-panel active" id="view-download">
            <div class="composer-view">
                <div class="composer-card">
                    <div class="composer-header-row">
                        <span class="composer-title">Video or audio links (One link per line):</span>
                        <span class="badge-count" id="composer-count-badge">0 links detected</span>
                    </div>

                    <!-- Large Multi-Line Textarea with Auto-Break Formatter -->
                    <textarea id="composer-urls-input" class="composer-textarea" placeholder="Paste video or audio links here (one link per line)...&#10;Paste individual links, comma-separated lists, or large blocks: links will automatically be extracted and formatted onto individual lines with line breaks!&#10;&#10;Supports: Facebook (Videos & Reels), YouTube, Instagram, TikTok, Twitter/X, and 1,000+ sources."></textarea>

                    <div class="composer-btn-bar">
                        <div class="action-group-left">
                            <button class="composer-btn" onclick="pasteClipboardToComposer()">
                                <svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: #2563eb;"><path d="M19 2h-4.18C14.4.84 13.3 0 12 0c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm7 18H5V4h2v3h10V4h2v16z"/></svg>
                                <span>Paste from Clipboard</span>
                            </button>
                            <button class="composer-btn danger" onclick="clearComposer()">
                                <span>Clear</span>
                            </button>
                        </div>
                        <div style="font-size: 11px; color: #64748b;">
                            Smart Breaker active: Multiple URLs are automatically split line-by-line.
                        </div>
                    </div>

                    <div class="composer-grid-settings">
                        <div class="setting-field">
                            <label class="setting-label">Quality Preset</label>
                            <select id="composer-quality-select" class="setting-select">
                                <option value="Best Quality" selected>⭐ Best (Original Uploaded Quality - No Upscaling)</option>
                                <option value="1080p">1080p Full HD (Max 1080p)</option>
                                <option value="720p">720p HD (Max 720p)</option>
                                <option value="480p">480p SD (Standard)</option>
                                <option value="360p">360p Low (Mobile / Data Saver)</option>
                                <option value="Audio Only">🎵 Audio Only (MP3 192k / Best Audio)</option>
                            </select>
                        </div>

                        <div class="setting-field">
                            <label class="setting-label">Simultaneous Parallel Downloads</label>
                            <select id="composer-parallel-select" class="setting-select">
                                <option value="4" selected>4 Simultaneous (Fast & Stable)</option>
                                <option value="2">2 Simultaneous</option>
                                <option value="6">6 Simultaneous</option>
                                <option value="1">1 by 1</option>
                            </select>
                        </div>
                    </div>

                    <div class="setting-field">
                        <label class="setting-label">Save To Folder</label>
                        <div class="folder-row">
                            <input type="text" id="composer-save-dir" class="setting-input" value="{{ default_dir }}">
                            <button class="composer-btn" onclick="openDownloadFolder()">Browse...</button>
                        </div>
                    </div>

                    <button class="btn-download-hero" onclick="submitComposerDownload()">
                        <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                        <span>Download Now</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- 2. TASKS GRID VIEW -->
        <div class="view-panel" id="view-tasks">
            <div class="tasks-view">
                <!-- Left Sidebar Filters -->
                <div class="app-sidebar">
                    <div class="sb-category active" id="filter-all" onclick="setFilter('All')">
                        <svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
                        <span>All</span>
                        <span class="sb-count" id="count-all">0</span>
                    </div>

                    <div class="sb-category" id="filter-processing" onclick="setFilter('Processing')">
                        <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
                        <span>Processing</span>
                        <span class="sb-count" id="count-processing">0</span>
                    </div>

                    <div class="sb-category" id="filter-paused" onclick="setFilter('Paused')">
                        <svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                        <span>Paused</span>
                        <span class="sb-count" id="count-paused">0</span>
                    </div>

                    <div class="sb-category" id="filter-completed" onclick="setFilter('Completed')">
                        <svg viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>
                        <span>Completed</span>
                        <span class="sb-count" id="count-completed">0</span>
                    </div>

                    <div class="sb-category" id="filter-failed" onclick="setFilter('Failed')">
                        <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                        <span>Failed</span>
                        <span class="sb-count" id="count-failed">0</span>
                    </div>
                </div>

                <!-- Kotato Table Grid -->
                <div class="grid-container">
                    <div class="grid-header">
                        <div>Icon</div>
                        <div>Source URL</div>
                        <div>Destination (Clean Title)</div>
                        <div>Quality</div>
                        <div>Duration</div>
                        <div>Size</div>
                        <div>Status & Progress</div>
                        <div>Actions</div>
                    </div>

                    <div class="grid-body" id="grid-items">
                        <div class="grid-empty-state" id="empty-state">
                            <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                            <span>No download tasks. Click <strong>Paste Link</strong> or use the <strong>Download</strong> tab to add videos.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 3. CONVERT VIEW -->
        <div class="view-panel" id="view-convert">
            <div class="composer-view">
                <div class="composer-card">
                    <span class="composer-title">Audio / Video Converter</span>
                    <p style="color: #64748b; font-size: 12px; line-height: 1.5;">
                        StreamVault Pro automatically extracts and converts audio directly to MP3 or M4A using bundled FFmpeg.
                        To download audio directly from any video, select <strong>Audio Only (MP3 192k)</strong> in the Quality selector.
                    </p>
                    <button class="composer-btn" style="width: fit-content;" onclick="selectQualityAndSwitch('Audio Only')">
                        🎵 Switch to Audio Only (MP3) Mode
                    </button>
                </div>
            </div>
        </div>

        <!-- 4. HISTORY VIEW -->
        <div class="view-panel" id="view-history">
            <div class="composer-view">
                <div class="composer-card">
                    <div class="composer-header-row">
                        <span class="composer-title">Download History & Metadata Archive</span>
                        <button class="composer-btn" onclick="openExcelTracker()">📊 Open Excel Spreadsheet (.xlsx)</button>
                    </div>
                    <p style="color: #64748b; font-size: 12px; line-height: 1.5;">
                        All downloaded videos, original URLs, clean titles, and complete Facebook descriptions are recorded in the Excel history tracker.
                    </p>
                    <div style="display: flex; gap: 8px;">
                        <button class="composer-btn" onclick="openDownloadFolder()">📁 Open Downloads Folder</button>
                        <button class="composer-btn" onclick="syncTrackerCloud()">☁️ Sync Tracker to GitHub</button>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Status Bar -->
    <div class="app-statusbar">
        <div class="sb-status-item">
            <span id="sb-status-text">Ready</span>
        </div>
        <div class="sb-status-item">
            <span>Folder:</span>
            <span id="sb-folder-text" style="font-family: monospace; color: #2563eb; cursor: pointer;" onclick="openDownloadFolder()">{{ default_dir }}</span>
        </div>
        <div class="sb-status-item right">
            <span id="sb-speed-text">Speed: 0.00 KB/s</span>
        </div>
    </div>
</div>

<!-- Modal: Execution Logs -->
<div class="modal-backdrop" id="logs-modal">
    <div class="modal-card" style="width: 780px;">
        <div class="modal-header">
            <span>Engine & Multi-Threading Execution Logs</span>
            <span style="cursor: pointer;" onclick="closeLogsModal()">✕</span>
        </div>
        <div class="modal-body">
            <textarea id="logs-textarea" readonly style="height: 340px; background: #0f172a; color: #4ade80; font-family: monospace; font-size: 11px; padding: 12px; border-radius: 4px; resize: none;"></textarea>
        </div>
        <div class="modal-footer">
            <button class="composer-btn" onclick="fetchLogs()">Refresh</button>
            <button class="composer-btn" onclick="copyLogs()">Copy Logs</button>
            <button class="composer-btn" onclick="closeLogsModal()">Close</button>
        </div>
    </div>
</div>

<!-- Modal: Updates -->
<div class="modal-backdrop" id="update-modal">
    <div class="modal-card">
        <div class="modal-header">
            <span>Software & Video Extractor Updates</span>
            <span style="cursor: pointer;" onclick="closeUpdateModal()">✕</span>
        </div>
        <div class="modal-body">
            <div id="update-status-box" style="padding: 12px; background: #f1f5f9; border-radius: 4px; font-size: 12px;">
                Checking for updates...
            </div>
            <div style="border-top: 1px solid #cbd5e1; padding-top: 10px; margin-top: 6px;">
                <strong>Dynamic Extractor Engine:</strong>
                <p style="color: #64748b; font-size: 11px; margin-top: 4px;">
                    When video platforms update their video player algorithms, you can update extraction algorithms on-the-fly without reinstalling.
                </p>
                <button class="composer-btn" style="margin-top: 8px;" onclick="updateEngine()">Update Extraction Algorithms</button>
            </div>
        </div>
        <div class="modal-footer">
            <button class="composer-btn" onclick="closeUpdateModal()">Close</button>
        </div>
    </div>
</div>

<script>
    // State
    let currentTab = 'download';
    let currentFilter = 'All';
    let isPolling = false;
    let allTasks = [];

    // --- TAB SWITCHING ---
    function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

        const btn = document.getElementById('tab-' + tab + '-btn');
        const view = document.getElementById('view-' + tab);
        if (btn) btn.classList.add('active');
        if (view) view.classList.add('active');

        if (tab === 'history') {
            setFilter('Completed');
        }
    }

    function selectQualityAndSwitch(q) {
        document.getElementById('composer-quality-select').value = q;
        switchTab('download');
    }

    // --- URL EXTRACTION & FORMATTING ---
    // Bulletproof: handles spaces, tabs, commas, newlines, quotes, brackets.
    // Every single URL is extracted and formatted onto its own line with \n!
    function extractUrls(text) {
        if (!text) return [];
        const regex = /https?:\\/\\/[^\\s"',<>\\u3000]+/gi;
        const matches = text.match(regex) || [];
        return Array.from(new Set(matches.map(u => u.trim())));
    }

    function updateComposerCount() {
        const input = document.getElementById('composer-urls-input');
        const urls = extractUrls(input.value);
        const badge = document.getElementById('composer-count-badge');
        badge.textContent = `${urls.length} link(s) detected`;
    }

    function formatTextareaWithLineBreakers() {
        const input = document.getElementById('composer-urls-input');
        const urls = extractUrls(input.value);
        if (urls.length > 0) {
            input.value = urls.join('\\n');
        }
        updateComposerCount();
    }

    async function pasteClipboardToComposer() {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                const urls = extractUrls(text);
                const input = document.getElementById('composer-urls-input');
                const existing = extractUrls(input.value);
                const merged = Array.from(new Set([...existing, ...urls]));
                input.value = merged.join('\\n');
                updateComposerCount();
            }
        } catch (err) {
            alert('Clipboard access denied. Please press Ctrl+V directly in the box.');
        }
    }

    async function pasteClipboardDirect() {
        switchTab('download');
        await pasteClipboardToComposer();
    }

    function clearComposer() {
        const input = document.getElementById('composer-urls-input');
        input.value = '';
        updateComposerCount();
    }

    // --- SUBMIT DOWNLOADS ---
    async function submitComposerDownload() {
        const input = document.getElementById('composer-urls-input');
        const urls = extractUrls(input.value);

        if (urls.length === 0) {
            alert('Please paste at least one valid video URL starting with http:// or https://');
            return;
        }

        const quality = document.getElementById('composer-quality-select').value;
        const parallel = parseInt(document.getElementById('composer-parallel-select').value) || 4;
        const saveDir = document.getElementById('composer-save-dir').value;

        try {
            const resp = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    urls: urls,
                    quality: quality,
                    parallel: parallel,
                    save_dir: saveDir,
                })
            });
            const data = await resp.json();
            if (data.success) {
                // Clear composer
                input.value = '';
                updateComposerCount();
                // Switch immediately to Tasks tab to view progress!
                switchTab('tasks');
                fetchStatus();
            } else {
                alert('Download error: ' + (data.error || 'Unknown error'));
            }
        } catch (e) {
            alert('Network connection error: ' + e);
        }
    }

    // --- SIDEBAR FILTERS ---
    function setFilter(filter) {
        currentFilter = filter;
        document.querySelectorAll('.sb-category').forEach(c => c.classList.remove('active'));
        const el = document.getElementById('filter-' + filter.toLowerCase());
        if (el) el.classList.add('active');
        renderTasksGrid();
    }

    // --- IN-PLACE ULTRA-RESPONSIVE TASK RENDERING ---
    function renderTasksGrid() {
        const container = document.getElementById('grid-items');
        const emptyState = document.getElementById('empty-state');

        // Filter tasks
        const filtered = allTasks.filter(t => {
            if (currentFilter === 'All') return true;
            if (currentFilter === 'Processing') return ['CONNECTING', 'DOWNLOADING', 'POST_PROCESSING'].includes(t.status);
            if (currentFilter === 'Paused') return ['PAUSED', 'CANCELLED'].includes(t.status);
            if (currentFilter === 'Completed') return t.status === 'COMPLETED';
            if (currentFilter === 'Failed') return t.status === 'ERROR';
            return true;
        });

        if (filtered.length === 0) {
            if (emptyState) emptyState.style.display = 'flex';
            // Remove existing task rows
            document.querySelectorAll('.task-row').forEach(r => r.remove());
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        const existingRowIds = new Set();
        document.querySelectorAll('.task-row').forEach(row => {
            const id = parseInt(row.id.replace('task-row-', ''));
            if (!filtered.some(t => t.id === id)) {
                row.remove();
            } else {
                existingRowIds.add(id);
            }
        });

        filtered.forEach(task => {
            let row = document.getElementById('task-row-' + task.id);
            if (!row) {
                row = document.createElement('div');
                row.className = 'task-row';
                row.id = 'task-row-' + task.id;
                row.innerHTML = `
                    <div class="cell-thumb">
                        <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    </div>
                    <div class="cell-source" title="${task.url}">${task.url}</div>
                    <div class="cell-title" id="title-${task.id}" title="${task.title || task.url}">${task.title || 'Connecting...'}</div>
                    <div><span class="quality-pill" id="qual-${task.id}">Best</span></div>
                    <div class="cell-duration" id="dur-${task.id}">—</div>
                    <div class="cell-size" id="size-${task.id}">—</div>
                    <div class="cell-progress">
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" id="pbar-${task.id}" style="width: 0%;"></div>
                        </div>
                        <div class="progress-meta">
                            <span class="status-badge" id="badge-${task.id}">QUEUED</span>
                            <span id="speed-${task.id}">—</span>
                        </div>
                    </div>
                    <div class="cell-actions" id="actions-${task.id}">
                        <button class="row-action-btn" onclick="toggleTask(${task.id}, '${task.status}')" title="Pause / Resume">
                            <svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                        </button>
                        <button class="row-action-btn" onclick="openDownloadFolder()" title="Open Folder">
                            <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                        </button>
                        <button class="row-action-btn" onclick="deleteTask(${task.id})" title="Delete">
                            <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                        </button>
                    </div>
                `;
                container.appendChild(row);
            }

            // In-place text/attribute updates (lightweight, zero DOM rebuild)
            const titleEl = document.getElementById('title-' + task.id);
            if (titleEl && task.title && titleEl.textContent !== task.title) {
                titleEl.textContent = task.title;
                titleEl.title = task.title;
            }

            const pbar = document.getElementById('pbar-' + task.id);
            if (pbar) {
                pbar.style.width = task.percent + '%';
                if (task.status === 'ERROR') pbar.style.background = '#dc2626';
                else if (task.status === 'COMPLETED') pbar.style.background = '#16a34a';
                else pbar.style.background = '#2563eb';
            }

            const badge = document.getElementById('badge-' + task.id);
            if (badge) {
                badge.className = 'status-badge ' + task.status;
                badge.textContent = `${task.status} (${task.percent}%)`;
            }

            const speed = document.getElementById('speed-' + task.id);
            if (speed) {
                speed.textContent = task.speed !== '—' ? `${task.speed} • ETA ${task.eta}` : task.status;
            }

            const dur = document.getElementById('dur-' + task.id);
            if (dur && task.duration_str) dur.textContent = task.duration_str;

            const size = document.getElementById('size-' + task.id);
            if (size && task.total_bytes) size.textContent = `${task.downloaded_bytes} / ${task.total_bytes}`;
        });
    }

    // --- STATUS POLLING ---
    async function fetchStatus() {
        if (isPolling) return;
        isPolling = true;

        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();

            allTasks = data.tasks || [];

            // Update tab badge
            document.getElementById('tab-task-count').textContent = allTasks.length;

            // Update sidebar counts
            document.getElementById('count-all').textContent = data.total || 0;
            document.getElementById('count-processing').textContent = data.active || 0;
            document.getElementById('count-paused').textContent = data.paused || 0;
            document.getElementById('count-completed').textContent = data.completed || 0;
            document.getElementById('count-failed').textContent = data.errors || 0;

            // Update status bar
            const sbStatus = document.getElementById('sb-status-text');
            if (data.is_busy) {
                sbStatus.textContent = `Downloading ${data.active} of ${data.total} tasks (${data.overall_percent}%) • Sleep Prevention Active`;
                document.getElementById('btn-pause-all').disabled = false;
            } else {
                sbStatus.textContent = data.total > 0 ? `Ready (${data.completed}/${data.total} completed)` : 'Ready';
                document.getElementById('btn-pause-all').disabled = true;
            }

            // Calculate aggregate speed
            let totalSpeedBytes = 0;
            allTasks.forEach(t => {
                if (['DOWNLOADING', 'CONNECTING'].includes(t.status) && t.speed && t.speed.includes('/s')) {
                    const parts = t.speed.split(' ');
                    const val = parseFloat(parts[0]);
                    const unit = parts[1];
                    if (!isNaN(val)) {
                        if (unit.startsWith('KiB')) totalSpeedBytes += val * 1024;
                        else if (unit.startsWith('MiB')) totalSpeedBytes += val * 1024 * 1024;
                        else if (unit.startsWith('GiB')) totalSpeedBytes += val * 1024 * 1024 * 1024;
                        else totalSpeedBytes += val;
                    }
                }
            });

            const speedText = totalSpeedBytes > 1024 * 1024
                ? (totalSpeedBytes / (1024 * 1024)).toFixed(2) + ' MB/s'
                : (totalSpeedBytes / 1024).toFixed(1) + ' KB/s';
            document.getElementById('sb-speed-text').textContent = 'Total Speed: ' + speedText;

            // In-place update grid
            renderTasksGrid();

        } catch (e) {
            // Ignore temporary network interruptions
        } finally {
            isPolling = false;
        }
    }

    // --- ACTIONS ---
    async function startAllTasks() {
        await fetch('/api/start_all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parallel: 4 }) });
        fetchStatus();
    }

    async function pauseAllTasks() {
        await fetch('/api/pause_all', { method: 'POST' });
        fetchStatus();
    }

    async function removeCompletedTasks() {
        await fetch('/api/remove_completed', { method: 'POST' });
        fetchStatus();
    }

    async function clearAllTasks() {
        if (confirm('Clear all tasks from the download list?')) {
            await fetch('/api/clear_all', { method: 'POST' });
            fetchStatus();
        }
    }

    async function toggleTask(taskId, currentStatus) {
        if (['DOWNLOADING', 'CONNECTING', 'QUEUED'].includes(currentStatus)) {
            await fetch('/api/pause_task', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId }) });
        } else {
            await fetch('/api/resume_task', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId }) });
        }
        fetchStatus();
    }

    async function deleteTask(taskId) {
        await fetch('/api/remove_task', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId }) });
        fetchStatus();
    }

    async function openDownloadFolder() {
        const folder = document.getElementById('composer-save-dir').value;
        await fetch('/api/open_folder', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder: folder }) });
    }

    async function openExcelTracker() {
        const folder = document.getElementById('composer-save-dir').value;
        await fetch('/api/open_tracker', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder: folder }) });
    }

    async function syncTrackerCloud() {
        alert('Syncing Excel download history to GitHub cloud...');
        const resp = await fetch('/api/sync_cloud', { method: 'POST' });
        const data = await resp.json();
        alert(data.message || (data.success ? 'Successfully synced to cloud!' : 'Sync notice: ' + (data.error || 'Done')));
    }

    // --- MODALS ---
    function openLogsModal() {
        document.getElementById('logs-modal').style.display = 'flex';
        fetchLogs();
    }
    function closeLogsModal() { document.getElementById('logs-modal').style.display = 'none'; }

    async function fetchLogs() {
        const resp = await fetch('/api/logs');
        const data = await resp.json();
        const ta = document.getElementById('logs-textarea');
        ta.value = (data.logs || []).join('\\n');
        ta.scrollTop = ta.scrollHeight;
    }

    function copyLogs() {
        const text = document.getElementById('logs-textarea').value;
        navigator.clipboard.writeText(text);
        alert('Logs copied to clipboard!');
    }

    function openUpdateModal() {
        document.getElementById('update-modal').style.display = 'flex';
        checkUpdates();
    }
    function closeUpdateModal() { document.getElementById('update-modal').style.display = 'none'; }

    async function checkUpdates() {
        const box = document.getElementById('update-status-box');
        box.innerHTML = 'Checking GitHub releases for updates...';
        try {
            const resp = await fetch('/api/check_update');
            const data = await resp.json();
            if (data.has_update) {
                box.innerHTML = `
                    <strong style="color: #16a34a;">New Version Available: v${data.latest_version}</strong><br>
                    <span style="color: #64748b;">Current version: ${data.current_version}</span><br>
                    <button class="composer-btn" style="margin-top: 8px; background: #2563eb; color: white;" onclick="applyUpdate('${data.download_url}')">
                        Download & Apply Update Automatically
                    </button>
                `;
            } else {
                box.innerHTML = `
                    <strong style="color: #16a34a;">✓ Up to Date!</strong><br>
                    You are running the latest version (${data.current_version || '1.0.0'}).
                `;
            }
        } catch (e) {
            box.innerHTML = 'Unable to check for updates: ' + e;
        }
    }

    async function applyUpdate(url) {
        if (!confirm('Download and apply update now? The app will close, update, and relaunch.')) return;
        await fetch('/api/apply_update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ download_url: url }) });
        alert('Update started in background. The app will relaunch in a moment.');
    }

    async function updateEngine() {
        const box = document.getElementById('update-status-box');
        box.innerHTML = 'Updating extraction algorithms from PyPI in background...';
        const resp = await fetch('/api/update_engine', { method: 'POST' });
        const data = await resp.json();
        alert(data.message || (data.success ? 'Extraction engine updated successfully!' : 'Engine update status: ' + data.error));
        box.innerHTML = data.message || 'Extractor updated.';
    }

    // --- SETUP LISTENERS ---
    window.addEventListener('DOMContentLoaded', () => {
        const textarea = document.getElementById('composer-urls-input');
        if (textarea) {
            textarea.addEventListener('paste', () => {
                setTimeout(formatTextareaWithLineBreakers, 20);
            });
            textarea.addEventListener('input', updateComposerCount);
        }

        // Poll status every 1000ms
        setInterval(fetchStatus, 1000);
        fetchStatus();
    });
</script>
</body>
</html>
"""


@app.route("/favicon.ico")
def favicon():
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
    if os.path.isfile(icon_path):
        return send_file(icon_path, mimetype="image/vnd.microsoft.icon")
    return "", 204


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        default_dir=get_default_download_dir(),
        app_name=APP_NAME,
        app_tagline=APP_TAGLINE,
        app_version=APP_VERSION,
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
def pause_all():
    downloader.pause_all()
    return jsonify({"success": True})


@app.route("/api/cancel", methods=["POST"])
def cancel_all():
    downloader.pause_all()
    return jsonify({"success": True})


@app.route("/api/resume_task", methods=["POST"])
def resume_task_endpoint():
    data = request.get_json() or {}
    task_id = int(data.get("task_id", 0))
    res = downloader.resume_task(task_id)
    return jsonify({"success": res})


@app.route("/api/pause_task", methods=["POST"])
def pause_task_endpoint():
    data = request.get_json() or {}
    task_id = int(data.get("task_id", 0))
    res = downloader.pause_task(task_id)
    return jsonify({"success": res})


@app.route("/api/remove_task", methods=["POST"])
def remove_task_endpoint():
    data = request.get_json() or {}
    task_id = int(data.get("task_id", 0))
    downloader.delete_task(task_id)
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
    if sys.platform == "win32":
        try:
            os.startfile(folder)
        except Exception as e:
            return jsonify({"error": f"Could not open folder: {e}"}), 500
    elif sys.platform == "darwin":
        subprocess.run(["open", folder])
    else:
        subprocess.run(["xdg-open", folder])
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
        record_download_history({
            "status": "INITIALIZED",
            "clean_title": f"{APP_NAME} Tracker",
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


@app.route("/api/check_update")
def check_update_endpoint():
    from core.updater import check_for_app_updates
    res = check_for_app_updates()
    return jsonify(res)


@app.route("/api/apply_update", methods=["POST"])
def apply_update_endpoint():
    data = request.get_json() or {}
    download_url = data.get("download_url", "")
    from core.updater import download_and_apply_update
    res = download_and_apply_update(download_url, log_callback=downloader.log)
    return jsonify(res)


@app.route("/api/update_engine", methods=["POST"])
def update_engine_endpoint():
    from core.updater import update_extractor_engine
    res = update_extractor_engine(log_callback=downloader.log)
    return jsonify(res)


if __name__ == "__main__":
    import sys
    import threading
    import time
    import socket
    import webbrowser

    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    port = 5000
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
    except OSError:
        port = _find_free_port()

    # Suppress werkzeug logging for desktop cleanliness
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True),
        daemon=True,
    )
    server_thread.start()

    # Ensure Flask server is fully initialized and responding before creating window
    import urllib.request
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=0.3) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.05)

    # Prefer Native Desktop Window
    use_browser = "--browser" in sys.argv
    opened_native = False

    if not use_browser:
        try:
            import webview

            window = webview.create_window(
                title=f"{APP_NAME}",
                url=f"http://127.0.0.1:{port}",
                width=1240,
                height=840,
                min_size=(960, 600),
                background_color="#FFFFFF",
            )
            opened_native = True
            webview.start()
            sys.exit(0)
        except Exception as e:
            print(f"[StreamVault Pro] Native window unavailable ({e}), falling back to browser.")

    if not opened_native:
        time.sleep(0.5)
        webbrowser.open(f"http://127.0.0.1:{port}")
        server_thread.join()
