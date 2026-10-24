"""Tests for CSS Analyzer (Design Token Discovery and Quality Checks)."""

import pytest
from src.analyzer import CSSAnalyzer
from src.parser import CSSParser


def test_token_discovery_colors():
    """Verify extraction and categorization of hex and functional colors."""
    css = """
    .btn {
        background-color: #1e3a8a;
        color: rgba(255, 255, 255, 0.9);
        border: 1px solid #1e3a8a;
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed, repetition_threshold=2)
    result = analyzer.analyze()

    colors = result.token_catalog["colors"]
    color_vals = {c.raw_value: c.count for c in colors}
    assert color_vals["#1e3a8a"] == 2
    assert "rgba(255, 255, 255, 0.9)" in color_vals


def test_token_discovery_spacing_and_radius():
    """Verify extraction of spacing and border-radius tokens."""
    css = """
    .card {
        padding: 16px;
        margin-bottom: 24px;
        border-radius: 8px;
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    result = analyzer.analyze()

    spacings = {s.raw_value: s.count for s in result.token_catalog["spacings"]}
    radii = {r.raw_value: r.count for r in result.token_catalog["border_radii"]}

    assert spacings["16px"] == 1
    assert spacings["24px"] == 1
    assert radii["8px"] == 1


def test_exact_duplicate_declaration_check():
    """Verify detection of exact duplicate property declarations within same block."""
    css = """
    .sidebar {
        display: block;
        padding: 10px;
        display: block;
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    result = analyzer.analyze()

    findings = [f for f in result.quality_findings if f.check_id == "repeated-declaration"]
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert "Exact Duplicate" in findings[0].title
    assert findings[0].property_name == "display"


def test_overwritten_declaration_check():
    """Verify detection of accidental overwritten properties within same block."""
    css = """
    .card-title {
        color: #1e3a8a;
        font-size: 16px;
        color: #374151;
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    result = analyzer.analyze()

    findings = [f for f in result.quality_findings if f.check_id == "repeated-declaration"]
    assert len(findings) == 1
    assert findings[0].severity == "advisory"
    assert "Overwritten" in findings[0].title
    assert findings[0].property_name == "color"


def test_progressive_enhancement_fallback_check():
    """Verify intentional fallback declarations are classified as info, not warnings."""
    css = """
    .hero {
        background: #1e3a8a;
        background: linear-gradient(135deg, #1e3a8a, #3b82f6);
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    result = analyzer.analyze()

    findings = [f for f in result.quality_findings if f.check_id == "repeated-declaration"]
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert "Progressive Enhancement" in findings[0].title


def test_excessive_important_check():
    """Verify !important declarations trigger specific location and debt warnings."""
    css = """
    .override-1 { margin: 10px !important; }
    .override-2 { padding: 5px !important; }
    .override-3 { color: red !important; }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    result = analyzer.analyze()

    important_findings = [f for f in result.quality_findings if f.check_id == "excessive-important"]
    assert len(important_findings) == 3
    # 3 or more should elevate severity to warning
    assert all(f.severity == "warning" for f in important_findings)


def test_token_candidate_discovery():
    """Verify repeated literal values exceeding repetition threshold are flagged."""
    css = """
    .one { color: #1e3a8a; padding: 13px; }
    .two { color: #1e3a8a; padding: 13px; }
    .three { color: #1e3a8a; padding: 13px; }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed, repetition_threshold=3)
    result = analyzer.analyze()

    assert len(result.token_candidates) == 2
    cand_vals = {c.raw_value: c.count for c in result.token_candidates}
    assert cand_vals["#1e3a8a"] == 3
    assert cand_vals["13px"] == 3


def test_undefined_custom_property_check():
    """Verify reference to undeclared CSS variable triggers warning."""
    css = """
    .alert {
        box-shadow: 0 0 10px var(--missing-shadow);
    }
    """
    parser = CSSParser.from_string(css)
    parsed = parser.parse()
    analyzer = CSSAnalyzer(parsed)
    result = analyzer.analyze()

    var_findings = [f for f in result.quality_findings if f.check_id == "undefined-variable"]
    assert len(var_findings) == 1
    assert var_findings[0].severity == "warning"
    assert var_findings[0].context["variable"] == "--missing-shadow"
