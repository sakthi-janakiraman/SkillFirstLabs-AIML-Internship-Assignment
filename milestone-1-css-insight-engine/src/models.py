"""Data models representing CSS AST elements, tokens, and quality insights."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceLocation:
    """Source code line and column position."""

    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"

    def to_dict(self) -> dict[str, int]:
        return {"line": self.line, "column": self.column}


@dataclass
class Declaration:
    """A single CSS property-value declaration."""

    name: str
    value: str
    important: bool = False
    is_custom_property: bool = False
    location: SourceLocation | None = None
    raw_value: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "important": self.important,
            "is_custom_property": self.is_custom_property,
            "location": self.location.to_dict() if self.location else None,
            "raw_value": self.raw_value or self.value,
        }


@dataclass
class StyleRule:
    """A standard qualified CSS rule block (e.g., selector { declarations })."""

    selectors: list[str]
    selector_text: str
    declarations: list[Declaration] = field(default_factory=list)
    at_rule_context: list[str] = field(default_factory=list)
    location: SourceLocation | None = None
    rule_index: int = 0

    @property
    def full_context_name(self) -> str:
        if self.at_rule_context:
            return f"{' -> '.join(self.at_rule_context)} {self.selector_text}"
        return self.selector_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_index": self.rule_index,
            "selector_text": self.selector_text,
            "selectors": self.selectors,
            "at_rule_context": self.at_rule_context,
            "location": self.location.to_dict() if self.location else None,
            "declarations": [d.to_dict() for d in self.declarations],
        }


@dataclass
class AtRuleBlock:
    """An at-rule containing rules or nested declarations (e.g., @media)."""

    keyword: str
    prelude: str
    child_rules: list[StyleRule] = field(default_factory=list)
    location: SourceLocation | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "prelude": self.prelude,
            "location": self.location.to_dict() if self.location else None,
            "child_rules": [r.to_dict() for r in self.child_rules],
        }


@dataclass
class ParsedStylesheet:
    """Complete structured representation of parsed CSS."""

    file_path: str | None
    rules: list[StyleRule]
    at_rules: list[AtRuleBlock]
    total_style_rules: int
    total_declarations: int
    unique_property_count: int
    property_frequency: dict[str, int]
    parse_errors: list[dict[str, Any]] = field(default_factory=list)
    comments_count: int = 0
    source_bytes: int = 0
    source_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "total_style_rules": self.total_style_rules,
            "total_declarations": self.total_declarations,
            "unique_property_count": self.unique_property_count,
            "comments_count": self.comments_count,
            "source_bytes": self.source_bytes,
            "source_lines": self.source_lines,
            "property_frequency": self.property_frequency,
            "parse_errors": self.parse_errors,
            "at_rules": [a.to_dict() for a in self.at_rules],
            "rules": [r.to_dict() for r in self.rules],
        }


@dataclass
class TokenOccurrence:
    """Location and context where a design token was encountered."""

    selector: str
    property_name: str
    location: SourceLocation | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector": self.selector,
            "property_name": self.property_name,
            "location": self.location.to_dict() if self.location else None,
        }


@dataclass
class TokenItem:
    """A categorized design token entry (color, spacing, font, etc.)."""

    category: str
    raw_value: str
    normalized_value: str
    count: int
    occurrences: list[TokenOccurrence] = field(default_factory=list)
    is_custom_property: bool = False
    is_token_candidate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "count": self.count,
            "is_custom_property": self.is_custom_property,
            "is_token_candidate": self.is_token_candidate,
            "occurrences": [o.to_dict() for o in self.occurrences],
        }


@dataclass
class QualityFinding:
    """An explainable static check advisory finding."""

    check_id: str
    severity: str  # 'warning', 'advisory', 'info'
    title: str
    rule_selector: str
    property_name: str | None
    location: SourceLocation | None
    explanation: str
    suggested_improvement: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "severity": self.severity,
            "title": self.title,
            "rule_selector": self.rule_selector,
            "property_name": self.property_name,
            "location": self.location.to_dict() if self.location else None,
            "explanation": self.explanation,
            "suggested_improvement": self.suggested_improvement,
            "context": self.context,
        }


@dataclass
class AnalysisResult:
    """Consolidated outcome of parsing and design intelligence analysis."""

    parsed: ParsedStylesheet
    token_catalog: dict[str, list[TokenItem]]
    token_candidates: list[TokenItem]
    quality_findings: list[QualityFinding]
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "engine": "CSS Insight Engine",
                "version": "1.0.0",
                "file_path": self.parsed.file_path,
                "stats": self.stats,
            },
            "stylesheet": self.parsed.to_dict(),
            "design_tokens": {
                category: [t.to_dict() for t in tokens]
                for category, tokens in self.token_catalog.items()
            },
            "token_candidates": [t.to_dict() for t in self.token_candidates],
            "quality_insights": [f.to_dict() for f in self.quality_findings],
        }
