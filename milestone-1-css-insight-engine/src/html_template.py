"""HTML Report Template for CSS Insight Engine: Interactive Design Intelligence Studio.

Provides an interactive developer studio with:
- Drag & Drop / File Upload zone for checking any custom .css file
- Preset switcher (Clean Design System vs Messy/Legacy CSS vs Custom Playground)
- Real-time client-side CSS analysis engine
- Interactive Color Palette Swatches (click to copy, click to filter rules)
- Quality Audits with severity filtering & fix recommendations
- Real-time Searchable Rules Explorer
100% self-contained, offline-ready, and lightweight.
"""

from __future__ import annotations

from datetime import datetime
import html
import json
from pathlib import Path
from typing import Any

from src.models import AnalysisResult


def _esc(val: Any) -> str:
    """Escape text for HTML safety."""
    if val is None:
        return ""
    return html.escape(str(val))


def _format_location(loc: Any) -> str:
    """Format source location as line:column."""
    if not loc:
        return "N/A"
    return f"L{loc.line}:C{loc.column}"


_HTML_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSS INSIGHT ENGINE - Interactive Design Studio</title>
    <style>
        :root {
            --bg-base: #090d16;
            --bg-surface: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #24344d;
            --border: #334155;
            --border-faint: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-faint: #64748b;
            --accent-emerald: #10b981;
            --accent-sky: #38bdf8;
            --accent-amber: #f59e0b;
            --accent-coral: #ef4444;
            --accent-violet: #a855f7;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font-sans);
            font-size: 14px;
            line-height: 1.6;
            padding: 24px 20px 48px;
        }

        .container {
            max-width: 1240px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .header-brand {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .brand-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent-emerald);
        }

        .brand-badge::before {
            content: "";
            width: 8px;
            height: 8px;
            background: var(--accent-emerald);
            border-radius: 50%;
            display: inline-block;
        }

        h1.title {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #ffffff;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 13px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 6px;
            font-family: var(--font-sans);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            border: 1px solid var(--border);
            background: var(--bg-surface);
            color: var(--text-main);
        }

        .btn:hover {
            background: var(--bg-card);
            border-color: var(--accent-sky);
        }

        .btn-primary {
            background: var(--accent-emerald);
            color: #042f2e;
            border-color: var(--accent-emerald);
            font-weight: 700;
        }

        .btn-primary:hover {
            background: #34d399;
            border-color: #34d399;
        }

        .btn-active {
            background: var(--bg-card);
            border-color: var(--accent-sky);
            color: var(--accent-sky);
        }

        /* Drag & Drop File Zone */
        .dropzone-box {
            background: var(--bg-surface);
            border: 2px dashed var(--border);
            border-radius: 10px;
            padding: 20px 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .dropzone-box:hover {
            border-color: var(--accent-sky);
            background: rgba(56, 189, 248, 0.04);
        }

        .dropzone-box.drag-over {
            border-color: var(--accent-emerald);
            background: rgba(16, 185, 129, 0.08);
            transform: scale(1.005);
        }

        .dropzone-icon {
            font-size: 26px;
            width: 46px;
            height: 46px;
            border-radius: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .dropzone-content {
            flex: 1;
        }

        .dropzone-title {
            font-size: 14px;
            color: #ffffff;
            font-weight: 700;
            display: block;
            margin-bottom: 3px;
        }

        .dropzone-link {
            color: var(--accent-sky);
            text-decoration: underline;
            text-underline-offset: 3px;
        }

        .dropzone-subtitle {
            font-size: 12px;
            color: var(--text-faint);
        }

        /* Interactive Workflow Bar */
        .workflow-bar {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }

        .workflow-step {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .step-label {
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-faint);
        }

        .preset-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        /* Sandbox Drawer */
        .sandbox-panel {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 24px;
            display: none;
        }

        .sandbox-panel.active {
            display: block;
        }

        .sandbox-textarea {
            width: 100%;
            height: 160px;
            background: #060911;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: #f1f5f9;
            resize: vertical;
            margin-bottom: 12px;
            outline: none;
        }

        .sandbox-textarea:focus {
            border-color: var(--accent-sky);
        }

        /* Stat Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px 18px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            transition: all 0.15s ease;
        }

        .stat-card:hover {
            border-color: var(--accent-sky);
        }

        .stat-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-faint);
        }

        .stat-value {
            font-size: 26px;
            font-weight: 800;
            font-family: var(--font-mono);
            color: #ffffff;
        }

        /* Section Layout */
        .section {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 22px;
            margin-bottom: 24px;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-faint);
            flex-wrap: wrap;
            gap: 12px;
        }

        .section-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-subtitle {
            font-size: 12px;
            color: var(--text-faint);
        }

        .two-col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        @media (max-width: 860px) {
            .two-col {
                grid-template-columns: 1fr;
            }
        }

        /* Token Swatches */
        .token-swatches-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 8px;
        }

        .token-chip {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border-faint);
            border-radius: 6px;
            padding: 7px 9px;
            cursor: pointer;
            transition: all 0.15s ease;
            user-select: none;
        }

        .token-chip:hover {
            border-color: var(--accent-sky);
            background: var(--bg-card-hover);
            transform: translateY(-1px);
        }

        .color-preview {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            flex-shrink: 0;
        }

        .token-chip-info {
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .token-val {
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 600;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .token-count {
            font-size: 10px;
            color: var(--text-faint);
        }

        /* Metric Pills */
        .pills-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .metric-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-card);
            border: 1px solid var(--border-faint);
            border-radius: 16px;
            padding: 5px 12px;
            font-family: var(--font-mono);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .metric-pill:hover {
            border-color: var(--accent-sky);
        }

        .pill-val {
            color: var(--accent-sky);
            font-weight: 600;
        }

        .pill-count {
            color: var(--text-faint);
            font-size: 10px;
        }

        /* Data Tables */
        table.data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        table.data-table th {
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-faint);
        }

        table.data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-faint);
            color: var(--text-main);
            vertical-align: middle;
        }

        table.data-table tr:hover td {
            background: var(--bg-card);
        }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .badge-emerald { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-coral   { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-amber   { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-accent  { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-neutral { background: var(--bg-card); color: var(--text-muted); border: 1px solid var(--border); }

        /* Filter Controls */
        .filter-controls {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .search-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 12px;
            color: #ffffff;
            font-size: 12px;
            outline: none;
            width: 220px;
            font-family: var(--font-sans);
        }

        .search-box:focus {
            border-color: var(--accent-sky);
        }

        /* Finding Cards */
        .findings-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .finding-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-left: 4px solid var(--accent-amber);
            border-radius: 6px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: all 0.15s ease;
        }

        .finding-card.severity-warning {
            border-left-color: var(--accent-amber);
        }

        .finding-card.severity-advisory {
            border-left-color: var(--accent-coral);
        }

        .finding-card.severity-info {
            border-left-color: var(--accent-emerald);
        }

        .finding-card-clean {
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: var(--accent-emerald);
            padding: 18px;
            border-radius: 6px;
            text-align: center;
            font-weight: 600;
        }

        .finding-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }

        .finding-title-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .finding-title {
            font-size: 14px;
            font-weight: 700;
            color: #ffffff;
        }

        .finding-loc {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-faint);
        }

        .finding-meta {
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            gap: 16px;
        }

        .finding-desc {
            font-size: 13px;
            color: var(--text-main);
            line-height: 1.5;
        }

        .finding-action {
            background: rgba(0, 0, 0, 0.25);
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 12px;
            color: var(--accent-sky);
            display: flex;
            gap: 6px;
        }

        .action-label {
            font-weight: 700;
            color: #ffffff;
        }

        /* Rules Explorer */
        .rules-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 480px;
            overflow-y: auto;
            padding-right: 6px;
        }

        .rule-block {
            background: var(--bg-card);
            border: 1px solid var(--border-faint);
            border-radius: 6px;
            padding: 12px 14px;
            font-family: var(--font-mono);
            font-size: 12px;
            transition: all 0.15s ease;
        }

        .rule-block:hover {
            border-color: var(--border);
        }

        .at-ctx {
            color: var(--accent-violet);
            font-size: 11px;
            margin-bottom: 4px;
            display: block;
        }

        .rule-selector {
            color: var(--accent-sky);
            font-weight: 700;
        }

        .rule-body {
            padding-left: 16px;
            color: var(--text-muted);
            margin: 4px 0;
        }

        .prop {
            color: #e2e8f0;
        }

        .val {
            color: #cbd5e1;
        }

        .important-tag {
            color: var(--accent-coral);
            font-weight: 700;
        }

        .rule-close {
            color: var(--text-faint);
        }

        /* Code snippets */
        code {
            font-family: var(--font-mono);
            font-size: 12px;
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 6px;
            border-radius: 4px;
            color: #e2e8f0;
        }

        .text-faint {
            color: var(--text-faint);
            font-size: 12px;
        }

        .empty-state {
            color: var(--text-faint);
            font-size: 13px;
            padding: 12px 0;
            font-style: italic;
        }

        /* Toast notification */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--accent-emerald);
            color: #042f2e;
            padding: 10px 18px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 13px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            display: none;
            z-index: 1000;
            animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Footer */
        .footer {
            border-top: 1px solid var(--border);
            padding-top: 20px;
            text-align: center;
            font-size: 12px;
            color: var(--text-faint);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Toast -->
        <div id="toast" class="toast">Copied to clipboard!</div>

        <!-- Header -->
        <header class="header">
            <div class="header-brand">
                <span class="brand-badge">Milestone 1 &bull; Design Intelligence</span>
                <h1 class="title">CSS INSIGHT ENGINE</h1>
                <p class="subtitle" id="report-subtitle">Interactive Design Tokens &amp; Quality Studio &mdash; <code id="active-filename">__FILENAME__</code></p>
            </div>
            <div class="header-actions">
                <button class="btn" id="btn-toggle-sandbox" onclick="toggleSandbox()">✎ Custom CSS Sandbox</button>
                <button class="btn btn-primary" onclick="reanalyzeCurrent()">⚡ Re-analyze</button>
            </div>
        </header>

        <!-- Drag & Drop Zone -->
        <div class="dropzone-box" id="dropzone" onclick="document.getElementById('file-upload-input').click()">
            <input type="file" id="file-upload-input" accept=".css,text/css" style="display: none;" onchange="handleFileSelect(event)">
            <div class="dropzone-icon">📁</div>
            <div class="dropzone-content">
                <strong class="dropzone-title">Drop your CSS file here, or <span class="dropzone-link">click to browse</span></strong>
                <p class="dropzone-subtitle">Drop any custom .css file to inspect AST rules, design system tokens, and dead-code audits in real-time</p>
            </div>
            <button class="btn" type="button" onclick="event.stopPropagation(); document.getElementById('file-upload-input').click()">Choose File</button>
        </div>

        <!-- Interactive Workflow Bar -->
        <div class="workflow-bar">
            <div class="workflow-step">
                <span class="step-label">Select Stylesheet:</span>
                <div class="preset-group">
                    <button class="btn btn-active" id="preset-clean" onclick="loadPreset('clean')">Clean Design System</button>
                    <button class="btn" id="preset-messy" onclick="loadPreset('messy')">Legacy / Messy (Debt &amp; Overwrites)</button>
                    <button class="btn" id="preset-custom" onclick="loadPreset('custom')">Custom Playground</button>
                </div>
            </div>
            <div class="workflow-step">
                <span class="step-label">Active Engine:</span>
                <span class="badge badge-emerald">AST Compiler (Zero Regex)</span>
            </div>
        </div>

        <!-- Custom CSS Sandbox Panel -->
        <div class="sandbox-panel" id="sandbox-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; color: #fff;">Interactive CSS Code Editor</span>
                <span class="text-faint">Type or paste CSS below to analyze on-the-fly:</span>
            </div>
            <textarea class="sandbox-textarea" id="custom-css-input" placeholder="Paste CSS stylesheet here..."></textarea>
            <div style="display: flex; justify-content: flex-end; gap: 8px;">
                <button class="btn" onclick="clearSandbox()">Clear</button>
                <button class="btn btn-primary" onclick="runCustomAnalysis()">Run Analysis &rarr;</button>
            </div>
        </div>

        <!-- Executive Metrics -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-label">Total Style Rules</span>
                <span class="stat-value" id="stat-rules">__RULES_COUNT__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Total Declarations</span>
                <span class="stat-value" id="stat-decls">__DECLS_COUNT__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Unique Properties</span>
                <span class="stat-value" id="stat-props">__PROPS_COUNT__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">!important Flags</span>
                <span class="stat-value" id="stat-important">__IMPORTANT_COUNT__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Token Candidates</span>
                <span class="stat-value" id="stat-candidates">__CANDIDATES_COUNT__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Quality Findings</span>
                <span class="stat-value" id="stat-findings">__FINDINGS_COUNT__</span>
            </div>
        </div>

        <!-- Section: Design Tokens -->
        <section class="section">
            <div class="section-header">
                <div>
                    <h2 class="section-title">Discovered Design Tokens</h2>
                    <p class="section-subtitle">Click any color swatch to copy value or filter rules.</p>
                </div>
            </div>
            
            <div class="two-col" style="margin-bottom: 24px;">
                <div>
                    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-faint); margin-bottom: 12px;">Color Palette Swatches</h3>
                    <div class="token-swatches-grid" id="swatches-container">
                        <!-- Populated by JS -->
                    </div>
                </div>
                <div>
                    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-faint); margin-bottom: 12px;">Spacing &amp; Radius Scale</h3>
                    <div class="pills-container" id="spacing-container">
                        <!-- Populated by JS -->
                    </div>
                </div>
            </div>

            <div class="two-col">
                <div>
                    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-faint); margin-bottom: 12px;">CSS Custom Properties</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Variable</th>
                                <th>Value</th>
                                <th>Frequency</th>
                            </tr>
                        </thead>
                        <tbody id="custom-props-body">
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>

                <div>
                    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-faint); margin-bottom: 12px;">Repeated Literals (Token Candidates &ge; 3x)</h3>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Literal Value</th>
                                <th>Type</th>
                                <th>Repeats</th>
                                <th>Occurrences</th>
                            </tr>
                        </thead>
                        <tbody id="candidates-body">
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Section: Quality Audits -->
        <section class="section">
            <div class="section-header">
                <div>
                    <h2 class="section-title">Quality &amp; Specificity Audits</h2>
                    <p class="section-subtitle">Explainable static analysis findings with actionable refactoring advice.</p>
                </div>
                <div class="filter-controls">
                    <button class="btn btn-active" onclick="filterFindings('all', this)">All</button>
                    <button class="btn" onclick="filterFindings('warning', this)">Warnings</button>
                    <button class="btn" onclick="filterFindings('advisory', this)">Advisories</button>
                    <button class="btn" onclick="filterFindings('info', this)">Info</button>
                </div>
            </div>

            <div class="findings-list" id="findings-container">
                <!-- Populated by JS -->
            </div>
        </section>

        <!-- Section: Parsed Rules Explorer -->
        <section class="section">
            <div class="section-header">
                <div>
                    <h2 class="section-title">Parsed Rule Tree (AST Overview)</h2>
                    <p class="section-subtitle">Interactive rule explorer. Filter selectors or properties in real-time.</p>
                </div>
                <div class="filter-controls">
                    <input type="text" class="search-box" id="rule-search" placeholder="Filter rules (.btn, color...)" oninput="filterRules()">
                    <button class="btn" onclick="resetRuleFilter()">Reset</button>
                </div>
            </div>

            <div class="rules-container" id="rules-container">
                <!-- Populated by JS -->
            </div>
        </section>

        <!-- Footer -->
        <footer class="footer">
            <span>Skill First Labs &bull; AI/ML Internship Shortlisting Assignment</span>
            <span>CSS Insight Engine &bull; Zero External Dependencies &bull; 100% Offline</span>
        </footer>
    </div>

    <!-- Embedded Scripts for Offline Client-Side Intelligence -->
    <script>
        const INITIAL_REPORT = __INITIAL_DATA__;
        const CLEAN_CSS_TEXT = __CLEAN_SAMPLE__;
        const MESSY_CSS_TEXT = __MESSY_SAMPLE__;

        let currentData = INITIAL_REPORT;
        let currentFilter = 'all';

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 2400);
        }

        function copyToClipboard(val) {
            navigator.clipboard.writeText(val).then(() => {
                showToast("Copied: " + val);
            }).catch(() => {
                showToast("Selected: " + val);
            });
        }

        // Drag & Drop / File Upload Handler
        const dropzone = document.getElementById('dropzone');

        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('drag-over');
            }, false);
            window.addEventListener(eventName, (e) => {
                e.preventDefault();
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('drag-over');
            }, false);
            window.addEventListener(eventName, (e) => {
                e.preventDefault();
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                processFile(files[0]);
            }
        });

        function handleFileSelect(e) {
            const files = e.target.files;
            if (files && files.length > 0) {
                processFile(files[0]);
            }
        }

        function processFile(file) {
            if (!file.name.endsWith('.css') && file.type && !file.type.includes('css')) {
                showToast("Please drop or choose a valid .css file!");
                return;
            }

            const reader = new FileReader();
            reader.onload = function(evt) {
                const content = evt.target.result;
                document.getElementById('active-filename').innerText = file.name;
                document.querySelectorAll('.preset-group .btn').forEach(b => b.classList.remove('btn-active'));
                
                // Update textarea if sandbox opened
                document.getElementById('custom-css-input').value = content;
                
                // Run instant analysis
                analyzeCssString(content, file.name);
                showToast("Loaded & analyzed " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)!");
            };
            reader.readAsText(file);
        }

        function toggleSandbox() {
            const p = document.getElementById('sandbox-panel');
            p.classList.toggle('active');
            if (p.classList.contains('active')) {
                const ta = document.getElementById('custom-css-input');
                if (!ta.value.trim()) {
                    ta.value = CLEAN_CSS_TEXT;
                }
            }
        }

        function clearSandbox() {
            document.getElementById('custom-css-input').value = "";
        }

        function loadPreset(name) {
            document.querySelectorAll('.preset-group .btn').forEach(b => b.classList.remove('btn-active'));
            if (name === 'clean') {
                document.getElementById('preset-clean').classList.add('btn-active');
                document.getElementById('active-filename').innerText = 'sample_clean.css';
                document.getElementById('sandbox-panel').classList.remove('active');
                analyzeCssString(CLEAN_CSS_TEXT, 'sample_clean.css');
            } else if (name === 'messy') {
                document.getElementById('preset-messy').classList.add('btn-active');
                document.getElementById('active-filename').innerText = 'sample_messy.css';
                document.getElementById('sandbox-panel').classList.remove('active');
                analyzeCssString(MESSY_CSS_TEXT, 'sample_messy.css');
            } else if (name === 'custom') {
                document.getElementById('preset-custom').classList.add('btn-active');
                document.getElementById('active-filename').innerText = 'custom_playground.css';
                document.getElementById('sandbox-panel').classList.add('active');
                const ta = document.getElementById('custom-css-input');
                if (!ta.value.trim()) ta.value = CLEAN_CSS_TEXT;
            }
        }

        function runCustomAnalysis() {
            const css = document.getElementById('custom-css-input').value;
            analyzeCssString(css, 'custom_playground.css');
            showToast("Custom CSS Analyzed!");
        }

        function reanalyzeCurrent() {
            const activePreset = document.querySelector('.preset-group .btn-active');
            if (activePreset && activePreset.id === 'preset-messy') {
                analyzeCssString(MESSY_CSS_TEXT, 'sample_messy.css');
            } else if (activePreset && activePreset.id === 'preset-custom') {
                runCustomAnalysis();
            } else {
                analyzeCssString(CLEAN_CSS_TEXT, 'sample_clean.css');
            }
            showToast("Report Refreshed!");
        }

        /* Client-side Lightweight Parser */
        function analyzeCssString(cssText, filename) {
            // Clean comments
            const cleaned = cssText.replace(/\\/\\*[\\s\\S]*?\\*\\//g, "");
            
            // Extract rules
            const ruleRegex = /([^{]+)\\{([^}]+)\\}/g;
            const rules = [];
            let match;
            let totalDecls = 0;
            let importantCount = 0;
            const propFreq = {};
            const colorTokens = {};
            const dimensionTokens = {};
            const customProps = {};
            const literalOccurrences = {};
            const findings = [];

            while ((match = ruleRegex.exec(cleaned)) !== null) {
                const selector = match[1].trim();
                const body = match[2].trim();
                if (!selector || selector.startsWith('@keyframes')) continue;

                const decls = [];
                const seenPropsInRule = {};

                const declPairs = body.split(';');
                for (const pair of declPairs) {
                    const colonIdx = pair.indexOf(':');
                    if (colonIdx === -1) continue;

                    const prop = pair.slice(0, colonIdx).trim().toLowerCase();
                    let val = pair.slice(colonIdx + 1).trim();
                    if (!prop || !val) continue;

                    const isImportant = val.includes('!important');
                    if (isImportant) {
                        val = val.replace('!important', '').trim();
                        importantCount++;
                    }

                    totalDecls++;
                    propFreq[prop] = (propFreq[prop] || 0) + 1;

                    // Track Custom properties
                    if (prop.startsWith('--')) {
                        customProps[prop] = { value: val, count: (customProps[prop]?.count || 0) + 1 };
                    }

                    // Track colors
                    const hexMatches = val.match(/#[0-9a-fA-F]{3,8}/g) || [];
                    for (const h of hexMatches) {
                        const lowHex = h.toLowerCase();
                        colorTokens[lowHex] = (colorTokens[lowHex] || 0) + 1;
                        literalOccurrences[lowHex] = (literalOccurrences[lowHex] || 0) + 1;
                    }

                    // Track dimensions
                    const dimMatches = val.match(/\\b\\d+(?:\\.\\d+)?(?:px|rem|em)\\b/g) || [];
                    for (const d of dimMatches) {
                        dimensionTokens[d] = (dimensionTokens[d] || 0) + 1;
                        literalOccurrences[d] = (literalOccurrences[d] || 0) + 1;
                    }

                    // Check for duplicate declarations
                    if (seenPropsInRule[prop] !== undefined) {
                        if (seenPropsInRule[prop] === val) {
                            findings.push({
                                check_id: "duplicate_declaration",
                                severity: "warning",
                                title: "Exact Duplicate Declaration",
                                rule_selector: selector,
                                property_name: prop,
                                explanation: `Property '` + prop + `: ` + val + `' is repeated identically within '` + selector + `'. Redundant bytecode waste.`,
                                suggested_improvement: `Remove the duplicate declaration to minimize CSS payload size.`
                            });
                        } else {
                            findings.push({
                                check_id: "overwritten_declaration",
                                severity: "warning",
                                title: "Overwritten Property Declaration",
                                rule_selector: selector,
                                property_name: prop,
                                explanation: `Declaration '` + prop + `: ` + seenPropsInRule[prop] + `' is immediately overwritten by '` + prop + `: ` + val + `'.`,
                                suggested_improvement: `Consolidate to the final desired value unless providing an intentional legacy fallback.`
                            });
                        }
                    }
                    seenPropsInRule[prop] = val;

                    decls.push({ name: prop, value: val, important: isImportant });
                }

                if (decls.length > 0) {
                    rules.push({ selector_text: selector, declarations: decls });
                }
            }

            // Check !important
            if (importantCount > 0) {
                findings.push({
                    check_id: "specificity_debt",
                    severity: "warning",
                    title: `Specificity Debt: ` + importantCount + ` !important Flag(s) Detected`,
                    rule_selector: "Multiple selectors",
                    property_name: "!important",
                    explanation: `Stylesheets using !important break normal cascade specificity and complicate responsive styling overrides.`,
                    suggested_improvement: `Refactor CSS specificity using BEM notation or CSS layers (@layer) rather than brute-force !important.`
                });
            }

            // Token candidates >= 3 repeats
            const tokenCandidates = [];
            for (const [lit, count] of Object.entries(literalOccurrences)) {
                if (count >= 3 && !lit.startsWith('--')) {
                    tokenCandidates.push({
                        raw_value: lit,
                        category: lit.startsWith('#') ? 'color' : 'dimension',
                        count: count
                    });
                }
            }

            const uniqueProps = Object.keys(propFreq).length;
            const updatedData = {
                metadata: { file_path: filename },
                stylesheet: {
                    total_style_rules: rules.length,
                    total_declarations: totalDecls,
                    unique_property_count: uniqueProps,
                    rules: rules
                },
                stats: {
                    total_rules: rules.length,
                    total_declarations: totalDecls,
                    unique_properties: uniqueProps,
                    important_count: importantCount
                },
                design_tokens: {
                    color: Object.entries(colorTokens).map(([k, v]) => ({ raw_value: k, normalized_value: k, count: v })),
                    dimension: Object.entries(dimensionTokens).map(([k, v]) => ({ raw_value: k, normalized_value: k, count: v })),
                    custom_property: Object.entries(customProps).map(([k, v]) => ({ raw_value: k, normalized_value: v.value, count: v.count }))
                },
                token_candidates: tokenCandidates,
                quality_insights: findings
            };

            currentData = updatedData;
            renderReport(updatedData);
        }

        function renderReport(data) {
            const stats = data.stats || {};
            const st = data.stylesheet || {};

            // Update stats
            document.getElementById('stat-rules').innerText = stats.total_rules || st.total_style_rules || 0;
            document.getElementById('stat-decls').innerText = stats.total_declarations || st.total_declarations || 0;
            document.getElementById('stat-props').innerText = stats.unique_properties || st.unique_property_count || 0;
            
            const impElem = document.getElementById('stat-important');
            const impCount = stats.important_count || 0;
            impElem.innerText = impCount;
            impElem.style.color = impCount > 0 ? 'var(--accent-coral)' : 'var(--accent-emerald)';

            const candList = data.token_candidates || [];
            document.getElementById('stat-candidates').innerText = candList.length;

            const findings = data.quality_insights || [];
            const findElem = document.getElementById('stat-findings');
            findElem.innerText = findings.length;
            findElem.style.color = findings.length > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)';

            // Render Colors
            const colors = (data.design_tokens && data.design_tokens.color) || [];
            const swatchesCont = document.getElementById('swatches-container');
            if (colors.length === 0) {
                swatchesCont.innerHTML = '<p class="empty-state">No color tokens detected.</p>';
            } else {
                swatchesCont.innerHTML = colors.slice(0, 18).map(c => `
                    <div class="token-chip" onclick="filterByColor('${c.raw_value}')" title="Click to filter rules using ${c.raw_value}">
                        <span class="color-preview" style="background-color: ${c.raw_value};"></span>
                        <div class="token-chip-info">
                            <span class="token-val">${c.raw_value}</span>
                            <span class="token-count">${c.count}x</span>
                        </div>
                    </div>
                `).join('');
            }

            // Render Spacing
            const dims = (data.design_tokens && data.design_tokens.dimension) || [];
            const spacingCont = document.getElementById('spacing-container');
            if (dims.length === 0) {
                spacingCont.innerHTML = '<p class="empty-state">No spacing tokens detected.</p>';
            } else {
                spacingCont.innerHTML = dims.slice(0, 16).map(d => `
                    <div class="metric-pill" onclick="filterRulesByText('${d.raw_value}')" title="Click to filter rules">
                        <span class="pill-val">${d.raw_value}</span>
                        <span class="pill-count">${d.count}x</span>
                    </div>
                `).join('');
            }

            // Render Custom Properties
            const cp = (data.design_tokens && data.design_tokens.custom_property) || [];
            const cpBody = document.getElementById('custom-props-body');
            if (cp.length === 0) {
                cpBody.innerHTML = '<tr><td colspan="3" class="empty-state">No CSS custom properties defined.</td></tr>';
            } else {
                cpBody.innerHTML = cp.slice(0, 12).map(item => `
                    <tr>
                        <td><code>${item.raw_value}</code></td>
                        <td><code>${item.normalized_value}</code></td>
                        <td><span class="badge badge-neutral">${item.count} ref</span></td>
                    </tr>
                `).join('');
            }

            // Render Token Candidates
            const candBody = document.getElementById('candidates-body');
            if (candList.length === 0) {
                candBody.innerHTML = '<tr><td colspan="4" class="empty-state">Zero un-tokenized literal repetitions found. Clean design tokens!</td></tr>';
            } else {
                candBody.innerHTML = candList.slice(0, 8).map(cand => `
                    <tr>
                        <td><code>${cand.raw_value}</code></td>
                        <td><span class="badge badge-accent">${cand.category}</span></td>
                        <td><span class="badge badge-coral">${cand.count}x repeated</span></td>
                        <td class="text-faint">Reusable token candidate</td>
                    </tr>
                `).join('');
            }

            // Render Findings
            renderFindingsList(findings);

            // Render Rules
            renderRulesList(st.rules || []);
        }

        function renderFindingsList(findings) {
            const cont = document.getElementById('findings-container');
            if (!findings || findings.length === 0) {
                cont.innerHTML = '<div class="finding-card-clean"><p>Zero quality or specificity debt issues detected. Excellent stylesheet hygiene!</p></div>';
                return;
            }

            const filtered = currentFilter === 'all' ? findings : findings.filter(f => f.severity === currentFilter);
            if (filtered.length === 0) {
                cont.innerHTML = '<p class="empty-state">No findings matching this filter.</p>';
                return;
            }

            cont.innerHTML = filtered.map(f => {
                const sev = f.severity || 'warning';
                const badgeCls = sev === 'warning' ? 'badge-amber' : (sev === 'info' ? 'badge-emerald' : 'badge-coral');
                return `
                    <div class="finding-card severity-${sev}">
                        <div class="finding-header">
                            <div class="finding-title-group">
                                <span class="badge ${badgeCls}">${sev.toUpperCase()}</span>
                                <h4 class="finding-title">${f.title}</h4>
                            </div>
                        </div>
                        <div class="finding-meta">
                            <span>Target: <code>${f.rule_selector}</code></span>
                            <span>Property: <code>${f.property_name || 'N/A'}</code></span>
                        </div>
                        <p class="finding-desc">${f.explanation}</p>
                        <div class="finding-action">
                            <span class="action-label">Recommendation:</span>
                            <span>${f.suggested_improvement}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function filterFindings(type, btn) {
            currentFilter = type;
            document.querySelectorAll('.filter-controls .btn').forEach(b => b.classList.remove('btn-active'));
            if (btn) btn.classList.add('btn-active');
            renderFindingsList(currentData.quality_insights || []);
        }

        function renderRulesList(rules) {
            const cont = document.getElementById('rules-container');
            if (!rules || rules.length === 0) {
                cont.innerHTML = '<p class="empty-state">No rules found.</p>';
                return;
            }

            cont.innerHTML = rules.slice(0, 40).map(r => {
                const sel = r.selector_text || 'selector';
                const decls = (r.declarations || []).map(d => `
                    <div>  <span class="prop">${d.name}</span>: <span class="val">${d.value}</span>${d.important ? ' <span class="important-tag">!important</span>' : ''};</div>
                `).join('');
                return `
                    <div class="rule-block" data-selector="${sel.toLowerCase()}" data-body="${decls.toLowerCase()}">
                        <div class="rule-selector">${sel} &#123;</div>
                        <div class="rule-body">${decls}</div>
                        <div class="rule-close">&#125;</div>
                    </div>
                `;
            }).join('');
        }

        function filterRules() {
            const query = document.getElementById('rule-search').value.toLowerCase().trim();
            const blocks = document.querySelectorAll('#rules-container .rule-block');
            blocks.forEach(b => {
                const sel = b.getAttribute('data-selector') || '';
                const body = b.getAttribute('data-body') || '';
                if (!query || sel.includes(query) || body.includes(query)) {
                    b.style.display = 'block';
                } else {
                    b.style.display = 'none';
                }
            });
        }

        function filterByColor(hex) {
            document.getElementById('rule-search').value = hex;
            filterRules();
            showToast("Filtered rules containing: " + hex);
        }

        function filterRulesByText(txt) {
            document.getElementById('rule-search').value = txt;
            filterRules();
            showToast("Filtered rules containing: " + txt);
        }

        function resetRuleFilter() {
            document.getElementById('rule-search').value = '';
            filterRules();
        }

        // Initialize with default report data
        window.addEventListener('DOMContentLoaded', () => {
            renderReport(INITIAL_REPORT);
        });
    </script>
</body>
</html>"""


def render_design_forensics_html(result: AnalysisResult) -> str:
    """Render an interactive HTML studio for CSS Insight Engine."""
    stats = result.stats
    p = result.parsed
    fn = Path(p.file_path).name if p.file_path else "sample_clean.css"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read sample stylesheets for presets
    samples_dir = Path(__file__).resolve().parent.parent / "samples"
    clean_sample_css = ""
    messy_sample_css = ""
    try:
        clean_sample_css = (samples_dir / "sample_clean.css").read_text(encoding="utf-8", errors="replace")
    except Exception:
        clean_sample_css = "/* Clean Sample */\n:root { --primary: #0f172a; }\n.card { padding: 16px; }"

    try:
        messy_sample_css = (samples_dir / "sample_messy.css").read_text(encoding="utf-8", errors="replace")
    except Exception:
        messy_sample_css = "/* Messy Sample */\n.header { color: #1e3a8a; }\n.header { color: #ef4444 !important; }"

    initial_data_json = json.dumps(result.to_dict(), ensure_ascii=False).replace("</script>", "<\\/script>")
    clean_sample_json = json.dumps(clean_sample_css, ensure_ascii=False).replace("</script>", "<\\/script>")
    messy_sample_json = json.dumps(messy_sample_css, ensure_ascii=False).replace("</script>", "<\\/script>")

    out = _HTML_BASE
    out = out.replace("__FILENAME__", _esc(fn))
    out = out.replace("__TIMESTAMP__", _esc(timestamp))
    out = out.replace("__RULES_COUNT__", str(stats.get('total_rules', 0)))
    out = out.replace("__DECLS_COUNT__", str(stats.get('total_declarations', 0)))
    out = out.replace("__PROPS_COUNT__", str(stats.get('unique_properties', 0)))
    out = out.replace("__IMPORTANT_COUNT__", str(stats.get('important_count', 0)))
    out = out.replace("__CANDIDATES_COUNT__", str(len(result.token_candidates)))
    out = out.replace("__FINDINGS_COUNT__", str(len(result.quality_findings)))
    out = out.replace("__INITIAL_DATA__", initial_data_json)
    out = out.replace("__CLEAN_SAMPLE__", clean_sample_json)
    out = out.replace("__MESSY_SAMPLE__", messy_sample_json)

    return out
