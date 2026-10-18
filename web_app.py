"""
StreamVault Pro - High-Performance Multi-Source Video Downloader
================================================================
Modern, high-performance video and audio downloader desktop interface:
  - Clean, modern dark glass / slate aesthetic
  - Direct quick-paste hero bar with multi-line batch expansion
  - Automatic title cleaning & Facebook view/reaction metrics stripping
  - 4x parallel multi-threaded download engine with auto-resume
  - Automatic Excel (.xlsx) and CSV download history logging
  - Live laptop sleep prevention during downloads
  - In-app 1-click updates and dynamic video extractor updates
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request

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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0a0e17;
            --bg-surface: #111827;
            --bg-card: #182234;
            --bg-card-hover: #1f2d44;
            --bg-input: #0d131f;
            --border-subtle: #243247;
            --border-highlight: #3b82f6;
            
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            
            --success: #10b981;
            --success-surface: rgba(16, 185, 129, 0.12);
            --amber: #f59e0b;
            --amber-surface: rgba(245, 158, 11, 0.12);
            --danger: #ef4444;
            --danger-surface: rgba(239, 68, 68, 0.12);
            --info: #06b6d4;
            
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-sub: #64748b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-base); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: #2d3d54; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #3b506e; }

        /* Top Header Navbar */
        .header-bar {
            height: 56px; background: var(--bg-surface); border-bottom: 1px solid var(--border-subtle);
            display: flex; align-items: center; justify-content: space-between; padding: 0 18px; flex-shrink: 0;
        }
        .brand-cluster { display: flex; align-items: center; gap: 12px; }
        .brand-icon-box {
            width: 34px; height: 34px; border-radius: 9px; background: var(--primary-gradient);
            display: flex; align-items: center; justify-content: center; color: white;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35); flex-shrink: 0;
        }
        .brand-icon-box svg { width: 18px; height: 18px; fill: currentColor; }
        .brand-name { font-size: 15px; font-weight: 800; letter-spacing: -0.3px; color: #ffffff; }
        .version-badge {
            font-size: 10px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.12);
            padding: 2px 7px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.25);
        }

        .header-tools { display: flex; align-items: center; gap: 8px; }
        .status-pill {
            display: inline-flex; align-items: center; gap: 7px; padding: 5px 12px;
            background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 20px;
            font-size: 11px; font-weight: 600; color: var(--text-muted);
        }
        .pulse-dot {
            width: 7px; height: 7px; border-radius: 50%; background: #64748b;
        }
        .pulse-dot.active {
            background: var(--success); box-shadow: 0 0 10px var(--success);
            animation: pulse-glow 1.6s infinite ease-in-out;
        }
        @keyframes pulse-glow {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.6; }
        }

        .tool-btn {
            display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
            background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 7px;
            color: var(--text-muted); font-size: 12px; font-weight: 600; cursor: pointer;
            transition: all 0.18s ease;
        }
        .tool-btn svg { width: 14px; height: 14px; fill: currentColor; }
        .tool-btn:hover { background: var(--bg-card-hover); color: var(--text-main); border-color: #3e5270; }
        .tool-btn.success { color: #34d399; border-color: rgba(52, 211, 153, 0.3); background: rgba(52, 211, 153, 0.08); }
        .tool-btn.success:hover { background: rgba(52, 211, 153, 0.16); color: #6ee7b7; border-color: #34d399; }

        /* Main Workspace */
        .workspace { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 16px 20px 0 20px; gap: 14px; }

        /* Hero Quick-Paste Download Card */
        .quick-download-card {
            background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px;
            padding: 14px 16px; display: flex; flex-direction: column; gap: 10px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25); flex-shrink: 0;
        }
        .input-row { display: flex; gap: 8px; align-items: center; }
        .url-input-wrap {
            flex: 1; position: relative; display: flex; align-items: center;
        }
        .url-input-wrap svg {
            position: absolute; left: 12px; width: 16px; height: 16px; fill: var(--text-sub);
        }
        .url-input {
            width: 100%; height: 42px; background: var(--bg-input); border: 1px solid var(--border-subtle);
            border-radius: 8px; padding: 0 90px 0 38px; color: #ffffff; font-size: 13px; outline: none;
            transition: border-color 0.18s ease, box-shadow 0.18s ease;
        }
        .url-input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.25); }
        .paste-btn-inside {
            position: absolute; right: 8px; height: 26px; padding: 0 10px;
            background: #1e293b; border: 1px solid #334155; border-radius: 5px; color: #38bdf8;
            font-size: 11px; font-weight: 700; cursor: pointer; transition: all 0.15s ease;
        }
        .paste-btn-inside:hover { background: #334155; color: #7dd3fc; }

        .select-pill {
            height: 42px; background: var(--bg-input); border: 1px solid var(--border-subtle);
            border-radius: 8px; padding: 0 12px; color: var(--text-main); font-size: 12px;
            font-weight: 600; outline: none; cursor: pointer;
        }
        .select-pill:focus { border-color: var(--primary); }

        .btn-download-primary {
            height: 42px; padding: 0 20px; background: var(--primary-gradient); border: none;
            border-radius: 8px; color: white; font-size: 13px; font-weight: 700; cursor: pointer;
            display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
            transition: all 0.18s ease; flex-shrink: 0;
        }
        .btn-download-primary:hover { opacity: 0.95; transform: translateY(-1px); box-shadow: 0 6px 18px rgba(79, 70, 229, 0.5); }
        .btn-download-primary:active { transform: translateY(0); }
        .btn-download-primary svg { width: 16px; height: 16px; fill: currentColor; }

        .btn-batch-toggle {
            height: 42px; padding: 0 14px; background: var(--bg-card); border: 1px solid var(--border-subtle);
            border-radius: 8px; color: var(--text-muted); font-size: 12px; font-weight: 600; cursor: pointer;
            display: inline-flex; align-items: center; gap: 6px; transition: all 0.15s ease;
        }
        .btn-batch-toggle:hover { background: var(--bg-card-hover); color: var(--text-main); }

        /* Batch Dropdown Drawer */
        .batch-drawer {
            display: none; flex-direction: column; gap: 8px; padding-top: 6px;
            border-top: 1px dashed var(--border-subtle); margin-top: 2px;
        }
        .batch-textarea {
            width: 100%; height: 95px; background: var(--bg-input); border: 1px solid var(--border-subtle);
            border-radius: 8px; padding: 10px; color: #ffffff; font-family: "JetBrains Mono", monospace;
            font-size: 12px; outline: none; resize: vertical; line-height: 1.45;
        }
        .batch-textarea:focus { border-color: var(--primary); }

        .sub-bar-options {
            display: flex; align-items: center; justify-content: space-between; font-size: 11px;
            color: var(--text-sub); padding: 0 2px;
        }
        .path-indicator { display: flex; align-items: center; gap: 6px; max-width: 70%; }
        .path-text { color: var(--text-muted); font-family: "JetBrains Mono", monospace; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .text-action-link { color: #38bdf8; cursor: pointer; text-decoration: underline; margin-left: 4px; }

        /* Filter & Controls Row */
        .queue-header-row {
            display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
            padding-bottom: 2px;
        }
        .filter-tabs { display: flex; gap: 4px; }
        .filter-tab-pill {
            padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;
            color: var(--text-muted); cursor: pointer; border: 1px solid transparent; background: transparent;
            display: inline-flex; align-items: center; gap: 6px; transition: all 0.15s ease;
        }
        .filter-tab-pill:hover { background: var(--bg-card); color: var(--text-main); }
        .filter-tab-pill.active {
            background: var(--bg-card); color: #ffffff; border-color: var(--border-subtle);
        }
        .filter-count-badge {
            background: rgba(255, 255, 255, 0.08); font-size: 10px; padding: 1px 6px;
            border-radius: 10px; font-weight: 700;
        }
        .filter-tab-pill.active .filter-count-badge { background: var(--primary); color: white; }

        .queue-actions { display: flex; align-items: center; gap: 6px; }
        .btn-ctrl {
            display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
            border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: none;
            transition: all 0.15s ease;
        }
        .btn-ctrl svg { width: 13px; height: 13px; fill: currentColor; }
        .btn-ctrl.start { background: var(--success-surface); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }
        .btn-ctrl.start:hover { background: rgba(16, 185, 129, 0.2); }
        .btn-ctrl.pause { background: var(--amber-surface); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }
        .btn-ctrl.pause:hover { background: rgba(245, 158, 11, 0.2); }
        .btn-ctrl.ghost { background: transparent; color: var(--text-sub); border: 1px solid transparent; }
        .btn-ctrl.ghost:hover { background: var(--bg-card); color: var(--text-main); border-color: var(--border-subtle); }
        .btn-ctrl:disabled { opacity: 0.4; cursor: not-allowed; }

        /* Task List Container */
        .task-list-scroll {
            flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;
            padding-bottom: 16px;
        }

        /* Modern Video Download Card */
        .task-card {
            background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px;
            padding: 12px 14px; display: flex; align-items: center; gap: 14px; position: relative;
            transition: all 0.18s ease; overflow: hidden;
        }
        .task-card:hover { border-color: #334460; background: var(--bg-card); }
        .task-card.active-download { border-color: rgba(79, 70, 229, 0.4); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2); }

        /* Bottom Progress Underline */
        .card-progress-bar {
            position: absolute; bottom: 0; left: 0; height: 3px; background: var(--primary-gradient);
            transition: width 0.3s ease; border-radius: 0 2px 2px 0;
        }
        .card-progress-bar.completed { background: var(--success); }

        /* Video Thumbnail Box */
        .thumb-box {
            width: 90px; height: 54px; border-radius: 6px; background: #0f172a; position: relative;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;
            overflow: hidden; border: 1px solid #1e293b;
        }
        .thumb-box svg.bg-play-icon { width: 22px; height: 22px; fill: #475569; }
        .badge-format {
            position: absolute; top: 3px; right: 3px; font-size: 9px; font-weight: 800;
            padding: 1px 4px; border-radius: 3px; background: rgba(0, 0, 0, 0.75); color: #ffffff;
        }
        .badge-platform {
            position: absolute; bottom: 3px; left: 3px; font-size: 8px; font-weight: 800;
            padding: 1px 4px; border-radius: 2px; text-transform: uppercase;
        }
        .badge-platform.facebook { background: #1877f2; color: white; }
        .badge-platform.youtube { background: #ff0000; color: white; }
        .badge-platform.tiktok { background: #00f2fe; color: black; }
        .badge-platform.instagram { background: #e1306c; color: white; }
        .badge-platform.generic { background: #475569; color: white; }

        /* Content Center */
        .task-center { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
        .title-row { display: flex; align-items: baseline; gap: 8px; }
        .video-title {
            font-size: 13px; font-weight: 700; color: #f1f5f9; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis; max-width: 90%;
        }
        .video-source-url {
            font-size: 11px; color: var(--text-sub); white-space: nowrap; overflow: hidden;
            text-overflow: ellipsis; cursor: pointer; max-width: 75%;
        }
        .video-source-url:hover { color: #38bdf8; text-decoration: underline; }

        .meta-stat-row {
            display: flex; align-items: center; gap: 12px; font-size: 11px; color: var(--text-muted);
            margin-top: 2px;
        }
        .stat-item { display: inline-flex; align-items: center; gap: 4px; }
        .stat-item.active-speed { color: #38bdf8; font-weight: 600; font-family: "JetBrains Mono", monospace; }
        .stat-badge-status {
            padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.3px;
        }
        .stat-badge-status.downloading { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
        .stat-badge-status.completed { background: var(--success-surface); color: var(--success); }
        .stat-badge-status.paused { background: var(--amber-surface); color: var(--amber); }
        .stat-badge-status.error { background: var(--danger-surface); color: var(--danger); }
        .stat-badge-status.queued { background: rgba(148, 163, 184, 0.12); color: #cbd5e1; }

        /* Task Actions Right */
        .task-actions-col { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
        .task-action-btn {
            height: 30px; padding: 0 10px; border-radius: 6px; font-size: 11px; font-weight: 600;
            cursor: pointer; display: inline-flex; align-items: center; gap: 5px; border: 1px solid var(--border-subtle);
            background: var(--bg-card); color: var(--text-muted); transition: all 0.15s ease;
        }
        .task-action-btn:hover { background: var(--bg-card-hover); color: var(--text-main); }
        .task-action-btn.btn-folder { color: #10b981; border-color: rgba(16, 185, 129, 0.3); }
        .task-action-btn.btn-folder:hover { background: rgba(16, 185, 129, 0.15); }
        .task-action-btn.btn-remove { color: #ef4444; border: none; background: transparent; font-size: 14px; padding: 0 6px; }
        .task-action-btn.btn-remove:hover { color: #f87171; background: rgba(239, 68, 68, 0.1); }

        /* Empty State */
        .empty-holder {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            height: 240px; color: var(--text-sub); gap: 10px; text-align: center;
            border: 2px dashed #1e293b; border-radius: 12px; margin-top: 10px;
        }
        .empty-holder svg { width: 44px; height: 44px; fill: #334155; }
        .empty-holder h4 { font-size: 14px; font-weight: 700; color: var(--text-muted); }
        .empty-holder p { font-size: 12px; max-width: 380px; line-height: 1.45; }

        /* Bottom Status Bar */
        .footer-bar {
            height: 28px; background: #0b0f19; border-top: 1px solid var(--border-subtle);
            display: flex; align-items: center; justify-content: space-between; padding: 0 18px;
            font-size: 11px; color: var(--text-sub); flex-shrink: 0;
        }
        .footer-status-text { color: var(--text-muted); }

        /* Modern Glass Modal Dialogs */
        .modal-overlay {
            position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(4px);
            display: none; align-items: center; justify-content: center; z-index: 1000;
        }
        .modal-window {
            background: var(--bg-surface); border: 1px solid #334155; border-radius: 12px;
            width: 580px; max-width: 92vw; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            display: flex; flex-direction: column; overflow: hidden; animation: popIn 0.18s ease-out;
        }
        @keyframes popIn {
            from { transform: scale(0.96); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .modal-top {
            padding: 14px 18px; border-bottom: 1px solid var(--border-subtle);
            display: flex; align-items: center; justify-content: space-between; font-size: 14px; font-weight: 700;
        }
        .modal-body { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
        .modal-bottom {
            padding: 12px 18px; background: #0c121d; border-top: 1px solid var(--border-subtle);
            display: flex; justify-content: flex-end; gap: 8px;
        }
        .close-icon-btn { cursor: pointer; color: var(--text-sub); font-size: 16px; font-weight: bold; }
        .close-icon-btn:hover { color: white; }
    </style>
</head>
<body>

    <!-- Header Navbar -->
    <header class="header-bar">
        <div class="brand-cluster">
            <div class="brand-icon-box">
                <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
            </div>
            <div>
                <span class="brand-name">{{ app_name }}</span>
                <span class="version-badge">v{{ app_version }}</span>
            </div>
        </div>

        <div class="header-tools">
            <div class="status-pill" id="power-status-pill">
                <span class="pulse-dot" id="power-dot"></span>
                <span id="power-status-text">Sleep: Normal</span>
            </div>

            <div class="status-pill" style="font-family: 'JetBrains Mono', monospace; color: #38bdf8;">
                <span id="sb-total-speed">↓ 0.00 KB/s</span>
            </div>

            <button class="tool-btn success" onclick="openExcelTracker()" title="Open Excel history tracking all URLs and full description captions">
                <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
                <span>Excel Tracker (.xlsx)</span>
            </button>

            <button class="tool-btn" onclick="syncTrackerCloud()" title="Sync download history directly to GitHub cloud repository">
                <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
                <span>Cloud Sync</span>
            </button>

            <button class="tool-btn" onclick="openUpdateDialog()" title="Check for app updates or dynamic extraction algorithm updates">
                <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0020 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 004 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
                <span>Updates</span>
            </button>

            <button class="tool-btn" onclick="openLogsDialog()" title="View real-time engine execution logs">
                <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/></svg>
                <span>Logs</span>
            </button>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="workspace">

        <!-- Hero Quick-Paste Download Card -->
        <section class="quick-download-card">
            <div class="input-row">
                <div class="url-input-wrap">
                    <svg viewBox="0 0 24 24"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg>
                    <input type="text" id="single-url-input" class="url-input" placeholder="Paste video link here (Facebook, YouTube, TikTok, Reels, Instagram, Twitter)..." autocomplete="off">
                    <button class="paste-btn-inside" onclick="pasteClipboardSingle()">Paste</button>
                </div>

                <select id="quick-quality-select" class="select-pill" title="Video Quality Preset">
                    <option value="Best Quality" selected>⭐ Best (Original Upload Quality)</option>
                    <option value="1080p">1080p (Full HD Cap)</option>
                    <option value="720p">720p (HD Cap)</option>
                    <option value="480p">480p (Standard)</option>
                    <option value="360p">360p (Data Saver / Mobile)</option>
                    <option value="Audio Only">🎵 Audio Only (MP3 / M4A)</option>
                </select>

                <select id="quick-concurrency-select" class="select-pill" title="Parallel simultaneous downloads">
                    <option value="4" selected>4 Parallel (Fast)</option>
                    <option value="2">2 Parallel</option>
                    <option value="6">6 Parallel</option>
                    <option value="1">1 by 1</option>
                </select>

                <button class="btn-download-primary" onclick="submitQuickDownload()">
                    <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                    <span>Download</span>
                </button>

                <button class="btn-batch-toggle" id="btn-batch-toggle" onclick="toggleBatchDrawer()" title="Expand multi-link batch paste drawer">
                    <span>Batch Queue (+)</span>
                </button>
            </div>

            <!-- Batch Drawer -->
            <div class="batch-drawer" id="batch-drawer">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Multi-Link Batch Queue (One link per line)</span>
                    <span id="batch-link-count" style="font-size: 11px; color: #64748b; font-weight: 600;">0 links detected</span>
                </div>
                <textarea id="batch-urls-input" class="batch-textarea" placeholder="Paste multiple video URLs here (one URL per line)...&#10;Paste from clipboard or text: links will automatically be split line-by-line with breakers!"></textarea>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-ctrl" style="height: 32px; font-size: 11px; padding: 0 12px; background: #1e293b; color: #38bdf8;" onclick="pasteClipboardToBatch()">📋 Paste Clipboard</button>
                        <button class="btn-ctrl ghost" style="height: 32px; font-size: 11px; padding: 0 10px;" onclick="clearBatchTextarea()">Clear</button>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-ctrl ghost" style="height: 32px; font-size: 11px;" onclick="toggleBatchDrawer()">Collapse</button>
                        <button class="btn-download-primary" style="height: 34px; padding: 0 16px; font-size: 12px;" onclick="submitBatchDownload()">Start Batch Download</button>
                    </div>
                </div>
            </div>

            <!-- Path & Features Bar -->
            <div class="sub-bar-options">
                <div class="path-indicator">
                    <span>Save to:</span>
                    <span class="path-text" id="display-save-path">{{ default_dir }}</span>
                    <span class="text-action-link" onclick="promptChangeFolder()">Change</span>
                    <span class="text-action-link" onclick="openFolder(currentSaveDir)">Open</span>
                </div>
                <div style="display: flex; gap: 14px; font-size: 11px; color: #94a3b8; flex-wrap: wrap;">
                    <span>🎯 <strong>Quality:</strong> Native uploaded resolution (360p, 720p, etc.) preserved without upscaling</span>
                    <span>✨ <strong>Cleaner:</strong> Metric & reaction stripper active</span>
                </div>
            </div>
        </section>

        <!-- Queue Filter & Action Bar -->
        <section class="queue-header-row">
            <div class="filter-tabs">
                <button class="filter-tab-pill active" id="filter-all" onclick="setFilter('All')">
                    <span>All</span>
                    <span class="filter-count-badge" id="count-all">0</span>
                </button>
                <button class="filter-tab-pill" id="filter-processing" onclick="setFilter('Processing')">
                    <span>Downloading</span>
                    <span class="filter-count-badge" id="count-processing">0</span>
                </button>
                <button class="filter-tab-pill" id="filter-paused" onclick="setFilter('Paused')">
                    <span>Paused</span>
                    <span class="filter-count-badge" id="count-paused">0</span>
                </button>
                <button class="filter-tab-pill" id="filter-completed" onclick="setFilter('Completed')">
                    <span>Completed</span>
                    <span class="filter-count-badge" id="count-completed">0</span>
                </button>
                <button class="filter-tab-pill" id="filter-failed" onclick="setFilter('Failed')">
                    <span>Failed</span>
                    <span class="filter-count-badge" id="count-failed">0</span>
                </button>
            </div>

            <div class="queue-actions">
                <button class="btn-ctrl start" id="btn-start-all" onclick="startAllQueued()">
                    <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    <span>Start All</span>
                </button>
                <button class="btn-ctrl pause" id="btn-pause-all" onclick="pauseAll()" disabled>
                    <svg viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                    <span>Pause All</span>
                </button>
                <button class="btn-ctrl ghost" onclick="removeCompleted()">
                    <span>Clear Completed</span>
                </button>
                <button class="btn-ctrl ghost" style="color: #ef4444;" onclick="clearAll()">
                    <span>Clear All</span>
                </button>
            </div>
        </section>

        <!-- Task List Scroll Container -->
        <section class="task-list-scroll" id="task-list-container">
            <div class="empty-holder" id="empty-state">
                <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                <h4>No active downloads</h4>
                <p>Paste any video or audio link from Facebook, YouTube, TikTok, Instagram, or Reels above to begin high-speed downloading.</p>
            </div>
        </section>

    </main>

    <!-- Footer Bar -->
    <footer class="footer-bar">
        <span class="footer-status-text" id="footer-status-label">Ready</span>
        <span id="footer-summary-counts">0 downloads queued</span>
    </footer>

    <!-- Software & Extractor Updates Modal Dialog -->
    <div class="modal-overlay" id="update-modal">
        <div class="modal-window">
            <div class="modal-top">
                <span>Software & Extractor Updates</span>
                <span class="close-icon-btn" onclick="closeUpdateDialog()">✕</span>
            </div>
            <div class="modal-body">
                <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff;">{{ app_name }} Application</div>
                            <div style="font-size: 11px; color: var(--text-sub);">Installed: <strong>v{{ app_version }}</strong> &bull; Channel: GitHub Releases</div>
                        </div>
                        <button class="tool-btn" id="btn-check-app-update" onclick="checkAppUpdates()">Check Now</button>
                    </div>
                    <div id="update-check-result" style="font-size: 11px; color: var(--text-muted); padding: 8px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px; display: none;"></div>
                </div>

                <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff;">Video Scraper Algorithms (yt-dlp)</div>
                            <div style="font-size: 11px; color: var(--text-sub);">Dynamically refresh Facebook, YouTube, TikTok extraction rules without reinstalling</div>
                        </div>
                        <button class="btn-download-primary" style="height: 32px; font-size: 11px; padding: 0 12px;" id="btn-update-engine" onclick="updateExtractorEngine()">Update Extractors</button>
                    </div>
                    <div id="engine-update-result" style="font-size: 11px; color: var(--success); display: none;"></div>
                </div>
            </div>
            <div class="modal-bottom">
                <button class="tool-btn" onclick="closeUpdateDialog()">Close</button>
            </div>
        </div>
    </div>

    <!-- Live Execution Logs Modal Dialog -->
    <div class="modal-overlay" id="logs-modal">
        <div class="modal-window" style="width: 760px;">
            <div class="modal-top">
                <span>Real-Time Execution Logs</span>
                <span class="close-icon-btn" onclick="closeLogsDialog()">✕</span>
            </div>
            <div class="modal-body">
                <textarea id="logs-textarea" readonly style="width: 100%; height: 320px; background: #080d17; border: 1px solid #1e293b; border-radius: 8px; color: #10b981; font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 10px; line-height: 1.45; outline: none;"></textarea>
            </div>
            <div class="modal-bottom">
                <button class="tool-btn" onclick="fetchLogs()">Refresh</button>
                <button class="tool-btn" onclick="navigator.clipboard.writeText(document.getElementById('logs-textarea').value); alert('Logs copied to clipboard!');">Copy Logs</button>
                <button class="btn-download-primary" style="height: 32px; font-size: 12px; padding: 0 14px;" onclick="closeLogsDialog()">Done</button>
            </div>
        </div>
    </div>

    <script>
        let currentSaveDir = "{{ default_dir }}";
        let activeFilter = 'All';
        let pollInterval = null;
        let taskList = [];

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function detectPlatform(url) {
            const u = (url || '').toLowerCase();
            if (u.includes('facebook.com') || u.includes('fb.watch') || u.includes('fb.com')) return { name: 'Facebook', cls: 'facebook' };
            if (u.includes('youtube.com') || u.includes('youtu.be')) return { name: 'YouTube', cls: 'youtube' };
            if (u.includes('tiktok.com')) return { name: 'TikTok', cls: 'tiktok' };
            if (u.includes('instagram.com')) return { name: 'Instagram', cls: 'instagram' };
            return { name: 'Web', cls: 'generic' };
        }

        function toggleBatchDrawer() {
            const el = document.getElementById('batch-drawer');
            const btn = document.getElementById('btn-batch-toggle');
            if (el.style.display === 'flex') {
                el.style.display = 'none';
                btn.style.color = 'var(--text-muted)';
            } else {
                el.style.display = 'flex';
                btn.style.color = '#38bdf8';
                document.getElementById('batch-urls-input').focus();
            }
        }

        function extractUrls(text) {
            if (!text) return [];
            // Match any http:// or https:// URL, stopping at whitespace, quotes, or angle brackets
            const regex = /https?:\/\/[^\s"',<>\u3000]+/gi;
            const matches = text.match(regex);
            if (matches && matches.length > 0) {
                // Strip trailing punctuation like . , ; : ) ] }
                const cleaned = matches.map(u => u.replace(/[.,;:\)\]\}]+$/, '')).filter(u => u.length > 8);
                return Array.from(new Set(cleaned));
            }
            // Fallback: split by newlines, carriage returns, or spaces
            const parts = text.split(/[\r\n\s,;]+/);
            return Array.from(new Set(parts.map(s => s.trim()).filter(s => s.length > 8 && s.toLowerCase().startsWith('http'))));
        }

        function updateBatchCounter() {
            const text = document.getElementById('batch-urls-input').value;
            const urls = extractUrls(text);
            const countEl = document.getElementById('batch-link-count');
            if (countEl) {
                countEl.innerText = urls.length === 1 ? '1 link detected' : `${urls.length} links detected`;
                countEl.style.color = urls.length > 0 ? '#10b981' : '#64748b';
            }
        }

        function openBatchWithUrls(urls) {
            const drawer = document.getElementById('batch-drawer');
            const btn = document.getElementById('btn-batch-toggle');
            drawer.style.display = 'flex';
            btn.style.color = '#38bdf8';

            const area = document.getElementById('batch-urls-input');
            const existing = extractUrls(area.value);
            const merged = Array.from(new Set([...existing, ...urls]));
            area.value = merged.join('\n');
            updateBatchCounter();
            area.focus();

            // Clear the single input so there's no confusion
            document.getElementById('single-url-input').value = '';
        }

        async function pasteClipboardSingle() {
            try {
                let text = '';
                if (navigator.clipboard && navigator.clipboard.readText) {
                    text = await navigator.clipboard.readText();
                } else {
                    text = prompt("Paste your video link(s) here:");
                }
                if (!text) return;

                const urls = extractUrls(text);
                if (urls.length > 1) {
                    openBatchWithUrls(urls);
                } else if (urls.length === 1) {
                    document.getElementById('single-url-input').value = urls[0];
                } else {
                    document.getElementById('single-url-input').value = text.trim();
                }
            } catch(e) {
                const text = prompt("Paste your video link(s) here:");
                if (text) {
                    const urls = extractUrls(text);
                    if (urls.length > 1) openBatchWithUrls(urls);
                    else if (urls.length === 1) document.getElementById('single-url-input').value = urls[0];
                    else document.getElementById('single-url-input').value = text.trim();
                }
            }
        }

        async function pasteClipboardToBatch() {
            try {
                let text = '';
                if (navigator.clipboard && navigator.clipboard.readText) {
                    text = await navigator.clipboard.readText();
                } else {
                    text = prompt("Paste your multiple video links here:");
                }
                if (!text) return;
                const urls = extractUrls(text);
                if (urls.length > 0) {
                    openBatchWithUrls(urls);
                } else {
                    const area = document.getElementById('batch-urls-input');
                    area.value = area.value ? (area.value + '\n' + text.trim()) : text.trim();
                    updateBatchCounter();
                }
            } catch(e) {
                const text = prompt("Paste your multiple video links here:");
                if (text) {
                    const urls = extractUrls(text);
                    if (urls.length > 0) openBatchWithUrls(urls);
                }
            }
        }

        function clearBatchTextarea() {
            document.getElementById('batch-urls-input').value = '';
            updateBatchCounter();
        }

        function promptChangeFolder() {
            const current = currentSaveDir;
            const updated = prompt("Enter download folder path:", current);
            if (updated && updated.trim()) {
                currentSaveDir = updated.trim();
                document.getElementById('display-save-path').innerText = currentSaveDir;
            }
        }

        function setFilter(filter) {
            activeFilter = filter;
            document.querySelectorAll('.filter-tab-pill').forEach(el => el.classList.remove('active'));
            const el = document.getElementById('filter-' + filter.toLowerCase());
            if (el) el.classList.add('active');
            renderTasks(taskList);
        }

        async function submitQuickDownload() {
            const urlInput = document.getElementById('single-url-input');
            const rawVal = urlInput.value.trim();
            const urls = extractUrls(rawVal);
            if (urls.length === 0) {
                alert('Please enter or paste a valid video URL starting with http:// or https://');
                urlInput.focus();
                return;
            }

            const quality = document.getElementById('quick-quality-select').value;
            const parallel = parseInt(document.getElementById('quick-concurrency-select').value) || 4;

            urlInput.value = '';
            // If multiple links were present, queue all of them!
            await sendDownloadRequest(urls, quality, parallel);
        }

        async function submitBatchDownload() {
            const text = document.getElementById('batch-urls-input').value;
            const urls = extractUrls(text);

            if (urls.length === 0) {
                alert('Please paste at least one valid video URL starting with http:// or https://');
                return;
            }

            const quality = document.getElementById('quick-quality-select').value;
            const parallel = parseInt(document.getElementById('quick-concurrency-select').value) || 4;

            document.getElementById('batch-urls-input').value = '';
            updateBatchCounter();
            toggleBatchDrawer();
            await sendDownloadRequest(urls, quality, parallel);
        }

        async function sendDownloadRequest(urls, quality, parallel) {
            document.getElementById('footer-status-label').innerText = `Starting ${urls.length} download(s)...`;
            try {
                const resp = await fetch('/api/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        urls: urls,
                        quality: quality,
                        parallel: parallel,
                        save_dir: currentSaveDir
                    })
                });
                const res = await resp.json();
                if (res.error) {
                    alert('Error: ' + res.error);
                    return;
                }
                pollStatusOnce();
            } catch (e) {
                alert('Failed to start download: ' + e);
            }
        }

        async function pollStatusOnce() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                taskList = data.tasks || [];

                // Badges
                document.getElementById('count-all').innerText = data.total || 0;
                document.getElementById('count-processing').innerText = data.active || 0;
                document.getElementById('count-completed').innerText = data.completed || 0;
                document.getElementById('count-failed').innerText = data.errors || 0;
                document.getElementById('count-paused').innerText = (data.paused || data.cancelled || 0);

                // Speed calculation
                let totalSpeedKB = 0;
                taskList.forEach(t => {
                    if (t.speed && t.speed.includes('MiB/s')) {
                        totalSpeedKB += parseFloat(t.speed) * 1024;
                    } else if (t.speed && t.speed.includes('KiB/s')) {
                        totalSpeedKB += parseFloat(t.speed);
                    }
                });
                document.getElementById('sb-total-speed').innerText = `↓ ${totalSpeedKB.toFixed(2)} KB/s`;

                // Sleep status
                const powerDot = document.getElementById('power-dot');
                const powerText = document.getElementById('power-status-text');
                if (data.is_busy) {
                    powerDot.classList.add('active');
                    powerText.innerText = 'Laptop Awake (Sleep Blocked)';
                    powerText.style.color = '#10b981';
                } else {
                    powerDot.classList.remove('active');
                    powerText.innerText = 'Sleep: Normal';
                    powerText.style.color = '#94a3b8';
                }

                // Controls
                const hasUnfinished = taskList.some(t => ['PAUSED', 'CANCELLED', 'ERROR', 'QUEUED'].includes(t.status));
                document.getElementById('btn-start-all').disabled = !hasUnfinished;
                document.getElementById('btn-pause-all').disabled = !data.is_busy;

                // Footer
                if (data.is_busy) {
                    document.getElementById('footer-status-label').innerText = `Downloading ${data.active} video(s) in parallel...`;
                } else {
                    document.getElementById('footer-status-label').innerText = data.total > 0 ? (hasUnfinished ? 'Paused / Waiting' : 'Completed') : 'Ready';
                }
                document.getElementById('footer-summary-counts').innerText = `${data.total} downloads: ${data.completed} finished, ${data.active} running`;

                renderTasks(taskList);
            } catch (err) {}
        }

        function startPolling() {
            if (pollInterval) clearInterval(pollInterval);
            pollStatusOnce();
            pollInterval = setInterval(pollStatusOnce, 800);
        }

        function renderTasks(tasks) {
            const container = document.getElementById('task-list-container');
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
                    <div class="empty-holder">
                        <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
                        <h4>${tasks.length === 0 ? 'No downloads queued' : 'No items match this filter'}</h4>
                        <p>${tasks.length === 0 ? 'Paste any link into the top bar to begin.' : 'Select "All" to view all downloads.'}</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = '';
            filtered.forEach(task => {
                const isAudio = task.title.toLowerCase().endsWith('.mp3') || (task.format_str && task.format_str.includes('audio') && !task.format_str.includes('video'));
                const badgeFormat = isAudio ? 'MP3' : 'HD';
                const platform = detectPlatform(task.url);

                const safeUrl = escapeHtml(task.url);
                const safeTitle = escapeHtml(task.title);
                const safeDir = (task.save_dir || currentSaveDir || '').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
                const cardClass = task.status === 'DOWNLOADING' ? 'task-card active-download' : 'task-card';

                const sizeDisplay = (task.downloaded_bytes !== '—' && task.total_bytes !== '—') 
                    ? `${task.downloaded_bytes} / ${task.total_bytes}` 
                    : (task.total_bytes !== '—' ? task.total_bytes : '—');

                let statusClass = 'queued';
                let statusLabel = task.status;
                if (task.status === 'DOWNLOADING') {
                    statusClass = 'downloading';
                    statusLabel = `Downloading ${task.percent}%`;
                } else if (task.status === 'COMPLETED') {
                    statusClass = 'completed';
                    statusLabel = 'Completed';
                } else if (task.status === 'PAUSED' || task.status === 'CANCELLED') {
                    statusClass = 'paused';
                    statusLabel = 'Paused';
                } else if (task.status === 'ERROR') {
                    statusClass = 'error';
                    statusLabel = 'Failed';
                } else if (task.status === 'POST_PROCESSING') {
                    statusClass = 'downloading';
                    statusLabel = 'Finalizing';
                }

                let actionHtml = '';
                if (['DOWNLOADING', 'CONNECTING', 'POST_PROCESSING'].includes(task.status) || task.status.startsWith('AUTO-RESUMING')) {
                    actionHtml = `<button class="task-action-btn" onclick="pauseTask(${task.id})">⏸ Pause</button>`;
                } else if (['PAUSED', 'CANCELLED', 'ERROR', 'QUEUED'].includes(task.status)) {
                    actionHtml = `<button class="task-action-btn" style="color: #38bdf8;" onclick="resumeTask(${task.id})">▶ Resume</button>`;
                } else if (task.status === 'COMPLETED') {
                    actionHtml = `<button class="task-action-btn btn-folder" onclick="openFolder('${safeDir}')">📂 Open Folder</button>`;
                }

                const card = document.createElement('div');
                card.className = cardClass;
                card.innerHTML = `
                    <!-- Thumbnail Box -->
                    <div class="thumb-box">
                        <svg class="bg-play-icon" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                        <span class="badge-format">${badgeFormat}</span>
                        <span class="badge-platform ${platform.cls}">${platform.name}</span>
                    </div>

                    <!-- Task Center Info -->
                    <div class="task-center">
                        <div class="title-row">
                            <span class="video-title" title="${safeTitle}">${safeTitle}</span>
                        </div>
                        <div class="video-source-url" onclick="window.open('${safeUrl}', '_blank')" title="${safeUrl}">
                            ${safeUrl}
                        </div>
                        <div class="meta-stat-row">
                            <span class="stat-badge-status ${statusClass}">${statusLabel}</span>
                            ${task.speed && task.speed !== '—' ? `<span class="stat-item active-speed">↓ ${task.speed}</span>` : ''}
                            ${task.eta && task.eta !== '—' ? `<span class="stat-item">ETA: ${task.eta}</span>` : ''}
                            <span class="stat-item">${escapeHtml(sizeDisplay)}</span>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="task-actions-col">
                        ${actionHtml}
                        <button class="task-action-btn btn-remove" title="Remove" onclick="removeTask(${task.id})">✕</button>
                    </div>

                    <!-- Progress Underline -->
                    <div class="card-progress-bar ${task.status === 'COMPLETED' ? 'completed' : ''}" style="width: ${task.percent}%;"></div>
                `;
                container.appendChild(card);
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

        async function removeTask(id) {
            await fetch('/api/remove_task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task_id: id})
            });
            pollStatusOnce();
        }

        async function startAllQueued() {
            const parallel = parseInt(document.getElementById('quick-concurrency-select').value) || 4;
            await fetch('/api/start_all', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({parallel: parallel})
            });
            pollStatusOnce();
        }

        async function pauseAll() {
            await fetch('/api/pause_all', {method: 'POST'});
            pollStatusOnce();
        }

        async function removeCompleted() {
            await fetch('/api/remove_completed', {method: 'POST'});
            pollStatusOnce();
        }

        async function clearAll() {
            if (taskList.length === 0) return;
            if (confirm('Are you sure you want to clear all tasks from the list?')) {
                await fetch('/api/clear_all', {method: 'POST'});
                pollStatusOnce();
            }
        }

        async function openFolder(folder) {
            await fetch('/api/open_folder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({folder: folder || currentSaveDir})
            });
        }

        async function openExcelTracker() {
            try {
                const resp = await fetch('/api/open_tracker', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({folder: currentSaveDir})
                });
                const res = await resp.json();
                if (res.error) alert(res.error);
            } catch(e) {
                alert('Could not open Excel tracker: ' + e);
            }
        }

        async function syncTrackerCloud() {
            document.getElementById('footer-status-label').innerText = 'Syncing Excel & CSV trackers to GitHub cloud...';
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

        /* Auto-Updater JS Functions */
        function openUpdateDialog() {
            document.getElementById('update-modal').style.display = 'flex';
            checkAppUpdates();
        }

        function closeUpdateDialog() {
            document.getElementById('update-modal').style.display = 'none';
        }

        async function checkAppUpdates() {
            const btn = document.getElementById('btn-check-app-update');
            const resBox = document.getElementById('update-check-result');
            btn.disabled = true;
            resBox.style.display = 'block';
            resBox.innerHTML = '<span style="color: #64748b;">Checking GitHub for updates...</span>';
            try {
                const resp = await fetch('/api/check_update');
                const data = await resp.json();
                btn.disabled = false;
                if (data.has_update) {
                    resBox.innerHTML = `
                        <div style="display:flex; flex-direction:column; gap:6px;">
                            <div style="font-weight:700; color:#10b981;">🚀 New Version Available: v${data.latest_version}</div>
                            <div style="color:#94a3b8; font-size:11px;"><strong>Release Notes:</strong> ${data.release_notes || 'Bug fixes and performance improvements.'}</div>
                            <button class="btn-download-primary" style="align-self:flex-start; margin-top:4px; height:32px; font-size:11px;" onclick="applyUpdate('${data.download_url}')">Update Now (Auto-Restart)</button>
                        </div>
                    `;
                } else if (data.error) {
                    resBox.innerHTML = `<span style="color: #f59e0b;">Notice: ${data.error}</span>`;
                } else {
                    resBox.innerHTML = `<span style="color: #10b981;">✓ You are running the latest version (v${data.current_version}). No update needed.</span>`;
                }
            } catch (e) {
                btn.disabled = false;
                resBox.innerHTML = `<span style="color: #ef4444;">Failed to check updates: ${e}</span>`;
            }
        }

        async function applyUpdate(url) {
            if (!confirm('This will download the latest update package, replace the app files in-place, and restart the app. Continue?')) return;
            const resBox = document.getElementById('update-check-result');
            resBox.innerHTML = '<span style="color: #38bdf8;">Downloading update package and applying in-place... App will restart in a few seconds.</span>';
            try {
                const resp = await fetch('/api/apply_update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({download_url: url})
                });
                const data = await resp.json();
                if (data.success) {
                    resBox.innerHTML = `<span style="color: #10b981;">${data.message}</span>`;
                } else {
                    alert('Update failed: ' + (data.error || 'Unknown error'));
                }
            } catch (e) {
                resBox.innerHTML = '<span style="color: #10b981;">App is restarting with the new version...</span>';
            }
        }

        async function updateExtractorEngine() {
            const btn = document.getElementById('btn-update-engine');
            const resBox = document.getElementById('engine-update-result');
            btn.disabled = true;
            resBox.style.display = 'block';
            resBox.style.color = '#38bdf8';
            resBox.innerText = 'Checking video extraction algorithms...';
            try {
                const resp = await fetch('/api/update_engine', {method: 'POST'});
                const data = await resp.json();
                btn.disabled = false;
                if (data.success) {
                    resBox.style.color = '#10b981';
                    resBox.innerText = data.output || '✓ Extraction algorithms are up to date! Ready to download.';
                } else {
                    resBox.style.color = '#f59e0b';
                    resBox.innerText = 'Notice: ' + (data.error || 'Already latest version.');
                }
            } catch (e) {
                btn.disabled = false;
                resBox.style.color = '#ef4444';
                resBox.innerText = 'Error: ' + e;
            }
        }

        /* Logs Functions */
        function openLogsDialog() {
            document.getElementById('logs-modal').style.display = 'flex';
            fetchLogs();
        }

        function closeLogsDialog() {
            document.getElementById('logs-modal').style.display = 'none';
        }

        async function fetchLogs() {
            try {
                const resp = await fetch('/api/logs');
                const data = await resp.json();
                const box = document.getElementById('logs-textarea');
                box.value = (data.logs || []).join('\\n');
                box.scrollTop = box.scrollHeight;
            } catch(e) {}
        }

        // Start auto polling and attach paste handlers
        window.addEventListener('DOMContentLoaded', () => {
            startPolling();

            const singleInput = document.getElementById('single-url-input');
            if (singleInput) {
                singleInput.addEventListener('paste', function(e) {
                    const pasted = (e.clipboardData || window.clipboardData).getData('text');
                    const urls = extractUrls(pasted);
                    if (urls.length > 1) {
                        e.preventDefault();
                        openBatchWithUrls(urls);
                    }
                });
            }

            const batchInput = document.getElementById('batch-urls-input');
            if (batchInput) {
                batchInput.addEventListener('paste', function(e) {
                    const pasted = (e.clipboardData || window.clipboardData).getData('text');
                    const urls = extractUrls(pasted);
                    if (urls.length > 0) {
                        e.preventDefault();
                        const existing = extractUrls(batchInput.value);
                        const merged = Array.from(new Set([...existing, ...urls]));
                        batchInput.value = merged.join('\n');
                        updateBatchCounter();
                    }
                });
                batchInput.addEventListener('input', updateBatchCounter);
            }
        });
    </script>
</body>
</html>
"""


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
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

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
                background_color="#0A0E17",
            )
            opened_native = True
            webview.start()
            sys.exit(0)
        except Exception as e:
            print(f"[StreamVault Pro] Native window unavailable ({e}), falling back to browser.")

    if not opened_native:
        time.sleep(0.8)
        webbrowser.open(f"http://127.0.0.1:{port}")
        server_thread.join()
