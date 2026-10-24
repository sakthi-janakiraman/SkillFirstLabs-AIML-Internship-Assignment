"""Tests for CSS AST Parser."""

import pytest
from src.parser import CSSParser


def test_empty_stylesheet():
    """Verify parser gracefully handles empty stylesheet without errors."""
    parser = CSSParser.from_string("")
    result = parser.parse()

    assert result.total_style_rules == 0
    assert result.total_declarations == 0
    assert result.unique_property_count == 0
    assert result.property_frequency == {}
    assert result.parse_errors == []


def test_basic_qualified_rule():
    """Verify parsing of standard qualified rule with multiple declarations."""
    css = """
    .dashboard-card {
        background-color: #ffffff;
        color: #0f172a;
        padding: 1rem;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    rule = result.rules[0]
    assert rule.selector_text == ".dashboard-card"
    assert rule.selectors == [".dashboard-card"]
    assert len(rule.declarations) == 3

    decl_names = [d.name for d in rule.declarations]
    assert decl_names == ["background-color", "color", "padding"]
    assert rule.location is not None
    assert rule.location.line == 2


def test_declaration_order_preserved():
    """Ensure declaration order is strictly preserved."""
    css = """
    .ordered {
        z-index: 10;
        top: 0;
        position: fixed;
        left: 0;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()
    decl_names = [d.name for d in result.rules[0].declarations]
    assert decl_names == ["z-index", "top", "position", "left"]


def test_repeated_declarations_preserved():
    """Ensure duplicate declarations are preserved rather than overwritten in AST."""
    css = """
    .duplicate-test {
        display: block;
        color: red;
        display: block;
        color: blue;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()
    decls = result.rules[0].declarations
    assert len(decls) == 4
    assert [d.name for d in decls] == ["display", "color", "display", "color"]
    assert [d.value for d in decls] == ["block", "red", "block", "blue"]


def test_important_flag():
    """Verify !important flag extraction on declarations."""
    css = """
    .important-test {
        margin-top: 10px !important;
        padding: 5px;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()
    decls = result.rules[0].declarations
    assert decls[0].name == "margin-top"
    assert decls[0].important is True
    assert decls[1].name == "padding"
    assert decls[1].important is False


def test_custom_properties():
    """Verify extraction and case-preservation of CSS custom properties (--*)."""
    css = """
    :root {
        --brandPrimary: #1e3a8a;
        --color-accent: #10b981;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()
    decls = result.rules[0].declarations

    assert decls[0].name == "--brandPrimary"  # case preserved for custom props
    assert decls[0].is_custom_property is True
    assert decls[1].name == "--color-accent"
    assert decls[1].is_custom_property is True


def test_at_rule_media_and_nesting():
    """Verify nested rules inside @media preserve at-rule context stack."""
    css = """
    @media (min-width: 768px) {
        .card {
            display: flex;
        }
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 1
    rule = result.rules[0]
    assert rule.selector_text == ".card"
    assert rule.at_rule_context == ["@media (min-width: 768px)"]
    assert len(result.at_rules) == 1
    assert result.at_rules[0].keyword == "media"


def test_multiple_comma_selectors_without_regex():
    """Verify splitting of comma-separated selectors preserving inner pseudo commas."""
    css = """
    h1, h2.title, a:is(.active, .highlight) {
        font-family: sans-serif;
    }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()
    rule = result.rules[0]

    assert len(rule.selectors) == 3
    assert rule.selectors[0] == "h1"
    assert rule.selectors[1] == "h2.title"
    assert rule.selectors[2] == "a:is(.active, .highlight)"


def test_property_metrics():
    """Verify total style-rule count, unique property count, and frequency map."""
    css = """
    .one { color: red; margin: 10px; }
    .two { color: blue; padding: 5px; }
    .three { color: green; margin: 20px; }
    """
    parser = CSSParser.from_string(css)
    result = parser.parse()

    assert result.total_style_rules == 3
    assert result.total_declarations == 6
    assert result.unique_property_count == 3
    assert result.property_frequency == {
        "color": 3,
        "margin": 2,
        "padding": 1,
    }
