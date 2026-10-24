"""Tests for ReportGenerator and CLI output."""

import json
from pathlib import Path
import pytest
from src.analyzer import CSSAnalyzer
from src.cli import main
from src.parser import CSSParser
from src.report import ReportGenerator


@pytest.fixture
def sample_analysis():
    css = """
    :root { --main-color: #1e3a8a; }
    .card {
        color: #1e3a8a;
        margin: 10px;
        margin: 10px;
        padding: 16px !important;
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    return analyzer.analyze()


def test_json_generation_structure(sample_analysis):
    """Verify JSON generation produces valid schema with all required keys."""
    report_gen = ReportGenerator(sample_analysis)
    json_str = report_gen.generate_json()
    data = json.loads(json_str)

    assert "metadata" in data
    assert "stylesheet" in data
    assert "design_tokens" in data
    assert "quality_insights" in data
    assert data["metadata"]["engine"] == "CSS Insight Engine"
    assert data["stylesheet"]["total_style_rules"] == 2


def test_terminal_summary_generation(sample_analysis):
    """Verify terminal summary contains overview, findings, and formatting."""
    report_gen = ReportGenerator(sample_analysis)
    summary = report_gen.generate_terminal_summary()

    assert "CSS INSIGHT ENGINE" in summary
    assert "OVERVIEW METRICS" in summary
    assert "QUALITY & SPECIFICITY FINDINGS" in summary
    assert "Exact Duplicate Declaration" in summary


def test_html_report_self_contained(sample_analysis, tmp_path):
    """Verify standalone HTML report is completely self-contained and offline-ready."""
    report_gen = ReportGenerator(sample_analysis)
    html_path = tmp_path / "test_report.html"
    report_gen.write_html(html_path)

    assert html_path.is_file()
    content = html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "CSS INSIGHT ENGINE" in content
    assert "<style>" in content
    assert "http://" not in content  # Zero external dependencies
    assert "https://" not in content  # Completely offline


def test_cli_execution_with_flags(tmp_path):
    """Verify end-to-end CLI with --json and --html flags."""
    css_file = tmp_path / "sample.css"
    css_file.write_text(".test { color: #1e3a8a; }", encoding="utf-8")

    json_out = tmp_path / "out.json"
    html_out = tmp_path / "out.html"

    exit_code = main([
        str(css_file),
        "-j", str(json_out),
        "-H", str(html_out),
        "--quiet",
    ])

    assert exit_code == 0
    assert json_out.is_file()
    assert html_out.is_file()

    json_data = json.loads(json_out.read_text(encoding="utf-8"))
    assert json_data["stylesheet"]["total_style_rules"] == 1
