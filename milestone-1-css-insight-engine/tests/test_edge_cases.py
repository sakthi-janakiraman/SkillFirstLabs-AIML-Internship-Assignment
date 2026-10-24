"""Robust edge-case tests for CSS Insight Engine."""

from pathlib import Path
import pytest
from src.cli import main
from src.parser import CSSParser


def test_empty_and_whitespace_only():
    """Verify empty and whitespace-only stylesheets parse safely."""
    for empty_input in ["", "   \n\t  \n  "]:
        parser = CSSParser.from_string(empty_input)
        result = parser.parse()
        assert result.total_style_rules == 0
        assert result.total_declarations == 0
        assert result.parse_errors == []


def test_comments_handling():
    """Verify multiline and inline comments do not disrupt AST parsing and are counted."""
    css = """
    /* Top-level header comment */
    .card /* inline comment */ {
        /* inner property comment */
        color: #1e3a8a; /* trailing comment */
        /* another comment */
        padding: 10px;
    }
    /* Footer comment */
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    assert result.comments_count >= 4
    assert len(result.rules[0].declarations) == 2


def test_quoted_string_containing_semicolon():
    """Critical edge case: quoted strings containing semicolons must not split declarations."""
    css = """
    .tooltip::after {
        content: "Warning; do not proceed; check logs";
        color: #ef4444;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    decls = result.rules[0].declarations
    assert len(decls) == 2
    assert decls[0].name == "content"
    assert "Warning; do not proceed; check logs" in decls[0].value
    assert decls[1].name == "color"
    assert decls[1].value == "#ef4444"


def test_data_url_with_commas_and_semicolons():
    """Edge case: Data URLs containing semicolons, commas, and SVG tags."""
    css = """
    .icon {
        background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='%2310b981' d='M8 0a8 8 0 100 16A8 8 0 008 0z'/%3E%3C/svg%3E");
        width: 16px;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    decls = result.rules[0].declarations
    assert len(decls) == 2
    assert decls[0].name == "background-image"
    assert "data:image/svg+xml" in decls[0].value
    assert decls[1].name == "width"


def test_commas_inside_functions():
    """Edge case: commas inside rgba(), linear-gradient(), clamp() must not break property values."""
    css = """
    .gradient-box {
        background: linear-gradient(90deg, rgba(15, 23, 42, 0.8) 0%, rgba(16, 185, 129, 0.9) 100%);
        font-size: clamp(1rem, 2.5vw, 2rem);
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    decls = result.rules[0].declarations
    assert len(decls) == 2
    assert decls[0].name == "background"
    assert "linear-gradient" in decls[0].value
    assert decls[1].name == "font-size"
    assert "clamp(1rem, 2.5vw, 2rem)" in decls[1].value


def test_nested_media_queries():
    """Edge case: Arbitrarily nested media queries."""
    css = """
    @media screen {
        @media (min-width: 768px) {
            .responsive-hero {
                display: grid;
            }
        }
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    rule = result.rules[0]
    assert rule.selector_text == ".responsive-hero"
    assert rule.at_rule_context == ["@media screen", "@media (min-width: 768px)"]


def test_unicode_in_selectors_and_content():
    """Edge case: Unicode emojis and non-ASCII characters in selectors and content."""
    css = """
    .btn-🚀, .status-✓ {
        content: "🎓 Scholar ✨";
        color: #10b981;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    rule = result.rules[0]
    assert ".btn-🚀" in rule.selectors
    assert ".status-✓" in rule.selectors
    assert "🎓 Scholar ✨" in rule.declarations[0].value


def test_malformed_css_recovery():
    """Edge case: Parser recovers from missing semicolons or malformed declarations without crashing."""
    css = """
    .valid-before { color: green; }
    .broken-rule {
        color red;
        : invalid-prop;
        display: flex;
    }
    .valid-after { color: blue; }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    # Engine must not crash and should parse valid rules
    assert result.total_style_rules >= 2
    selectors = [r.selector_text for r in result.rules]
    assert ".valid-before" in selectors
    assert ".valid-after" in selectors
    assert len(result.parse_errors) > 0


def test_complex_selectors():
    """Edge case: Attribute selectors, pseudo-classes, and pseudo-elements with complex delimiters."""
    css = """
    table.talent-matrix > tbody > tr:nth-child(even):not(.disabled)::before {
        content: "";
        display: inline-block;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    assert "tr:nth-child(even):not(.disabled)::before" in result.rules[0].selector_text


def test_missing_file_cli_error(capsys):
    """Edge case: CLI gracefully reports missing file with non-zero exit code and no unhandled stack trace."""
    exit_code = main(["non_existent_file_xyz.css"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error: File not found" in captured.err
