"""AST-based CSS Parser built on tinycss2.

Extracts structured rules, selectors, declarations, at-rules, custom properties,
and metrics while preserving declaration order and exact source references.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import tinycss2
from tinycss2.ast import AtRule, Comment, Declaration as TinyDeclaration, ParseError, QualifiedRule

from src.models import (
    AtRuleBlock,
    Declaration,
    ParsedStylesheet,
    SourceLocation,
    StyleRule,
)


def _extract_source_location(node: Any) -> SourceLocation | None:
    """Safely extract line and column from an AST node if present."""
    line = getattr(node, "source_line", None)
    col = getattr(node, "source_column", None)
    if line is not None and col is not None:
        return SourceLocation(line=line, column=col)
    return None


def _split_selectors(prelude_tokens: list[Any]) -> list[str]:
    """Split selector prelude by top-level commas without regex.

    Using the AST token list guarantees commas inside function blocks
    (like :is(h1, h2) or :not(.a, .b)) or attribute brackets ([data-attr="a,b"])
    are never erroneously treated as selector delimiters.
    """
    selectors: list[str] = []
    current_tokens: list[Any] = []

    for token in prelude_tokens:
        if token.type == "literal" and token.value == ",":
            serialized = tinycss2.serialize(current_tokens).strip()
            if serialized:
                selectors.append(serialized)
            current_tokens = []
        else:
            current_tokens.append(token)

    if current_tokens:
        serialized = tinycss2.serialize(current_tokens).strip()
        if serialized:
            selectors.append(serialized)

    return selectors if selectors else [tinycss2.serialize(prelude_tokens).strip()]


def _parse_declarations(
    content_tokens: list[Any] | None,
    parse_errors: list[dict[str, Any]],
    comments_counter: list[int],
) -> list[Declaration]:
    """Parse declaration list from a block's content tokens.

    Preserves exact declaration order, repeated declarations,
    and captures parse errors and comments.
    """
    if not content_tokens:
        return []

    declarations: list[Declaration] = []
    raw_nodes = tinycss2.parse_declaration_list(
        content_tokens, skip_comments=False, skip_whitespace=True
    )

    for node in raw_nodes:
        if isinstance(node, Comment):
            comments_counter[0] += 1
            continue

        if isinstance(node, ParseError):
            parse_errors.append(
                {
                    "type": "declaration_parse_error",
                    "message": node.message,
                    "line": node.source_line,
                    "column": node.source_column,
                }
            )
            continue

        if isinstance(node, TinyDeclaration):
            prop_name = node.name
            # Standard CSS properties are case-insensitive; custom properties (--*) are case-sensitive
            is_custom = prop_name.startswith("--")
            normalized_name = prop_name if is_custom else prop_name.lower()

            value_str = tinycss2.serialize(node.value).strip()
            location = _extract_source_location(node)

            declarations.append(
                Declaration(
                    name=normalized_name,
                    value=value_str,
                    important=bool(node.important),
                    is_custom_property=is_custom,
                    location=location,
                    raw_value=value_str,
                )
            )

    return declarations


def _walk_rule_tree(
    nodes: list[Any],
    context_stack: list[str],
    all_rules: list[StyleRule],
    all_at_rules: list[AtRuleBlock],
    parse_errors: list[dict[str, Any]],
    comments_counter: list[int],
    rule_counter: list[int],
) -> None:
    """Recursively traverse stylesheet nodes and nested at-rules."""
    for node in nodes:
        if isinstance(node, Comment):
            comments_counter[0] += 1
            continue

        if isinstance(node, ParseError):
            parse_errors.append(
                {
                    "type": "rule_parse_error",
                    "message": node.message,
                    "line": node.source_line,
                    "column": node.source_column,
                }
            )
            continue

        if isinstance(node, QualifiedRule):
            # Selector rule block: selector { declarations }
            raw_prelude = tinycss2.serialize(node.prelude).strip()
            selectors = _split_selectors(node.prelude)
            location = _extract_source_location(node)

            decls = _parse_declarations(node.content, parse_errors, comments_counter)
            rule_counter[0] += 1

            style_rule = StyleRule(
                selectors=selectors,
                selector_text=raw_prelude,
                declarations=decls,
                at_rule_context=list(context_stack),
                location=location,
                rule_index=rule_counter[0],
            )
            all_rules.append(style_rule)

        elif isinstance(node, AtRule):
            keyword = node.at_keyword.lower()
            prelude_str = tinycss2.serialize(node.prelude).strip()
            at_header = f"@{keyword} {prelude_str}".strip()
            at_loc = _extract_source_location(node)

            at_block = AtRuleBlock(
                keyword=keyword,
                prelude=prelude_str,
                child_rules=[],
                location=at_loc,
            )

            # Check if this at-rule contains nested rules (e.g. @media, @supports, @layer, @container, @keyframes)
            if node.content is not None:
                # Some at-rules contain declarations directly (e.g. @font-face, @page)
                if keyword in {"font-face", "page", "property", "viewport"}:
                    decls = _parse_declarations(node.content, parse_errors, comments_counter)
                    rule_counter[0] += 1
                    pseudo_rule = StyleRule(
                        selectors=[f"@{keyword}"],
                        selector_text=at_header,
                        declarations=decls,
                        at_rule_context=list(context_stack),
                        location=at_loc,
                        rule_index=rule_counter[0],
                    )
                    all_rules.append(pseudo_rule)
                    at_block.child_rules.append(pseudo_rule)
                else:
                    # Parse inner rule list
                    nested_nodes = tinycss2.parse_rule_list(
                        node.content, skip_comments=False, skip_whitespace=True
                    )
                    sub_rules: list[StyleRule] = []
                    sub_counter: list[int] = [0]

                    new_context = context_stack + [at_header]
                    _walk_rule_tree(
                        nested_nodes,
                        new_context,
                        all_rules,
                        all_at_rules,
                        parse_errors,
                        comments_counter,
                        rule_counter,
                    )
                    # Also link child rules to this at-block for structural inspection
                    at_block.child_rules = sub_rules

            all_at_rules.append(at_block)


class CSSParser:
    """Robust AST-based CSS parser."""

    def __init__(self, css_content: str, file_path: str | None = None) -> None:
        self.css_content = css_content
        self.file_path = file_path

    @classmethod
    def from_file(cls, file_path: str | Path) -> CSSParser:
        """Construct parser from a file path with UTF-8 decoding."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"CSS file not found: {path.resolve()}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return cls(css_content=content, file_path=str(path.resolve()))

    @classmethod
    def from_string(cls, css_content: str, file_path: str | None = None) -> CSSParser:
        """Construct parser directly from a CSS string."""
        return cls(css_content=css_content, file_path=file_path)

    def parse(self) -> ParsedStylesheet:
        """Execute parsing and return a structured ParsedStylesheet model."""
        if not self.css_content.strip():
            # Handle empty stylesheet edge case gracefully
            return ParsedStylesheet(
                file_path=self.file_path,
                rules=[],
                at_rules=[],
                total_style_rules=0,
                total_declarations=0,
                unique_property_count=0,
                property_frequency={},
                parse_errors=[],
                comments_count=0,
                source_bytes=len(self.css_content.encode("utf-8")),
                source_lines=len(self.css_content.splitlines()),
            )

        top_nodes = tinycss2.parse_stylesheet(
            self.css_content, skip_comments=False, skip_whitespace=True
        )

        all_rules: list[StyleRule] = []
        all_at_rules: list[AtRuleBlock] = []
        parse_errors: list[dict[str, Any]] = []
        comments_counter: list[int] = [0]
        rule_counter: list[int] = [0]

        _walk_rule_tree(
            nodes=top_nodes,
            context_stack=[],
            all_rules=all_rules,
            all_at_rules=all_at_rules,
            parse_errors=parse_errors,
            comments_counter=comments_counter,
            rule_counter=rule_counter,
        )

        # Calculate statistics
        total_declarations = sum(len(r.declarations) for r in all_rules)
        property_counter: Counter[str] = Counter()
        for r in all_rules:
            for d in r.declarations:
                property_counter[d.name] += 1

        source_bytes = len(self.css_content.encode("utf-8"))
        source_lines = len(self.css_content.splitlines())

        return ParsedStylesheet(
            file_path=self.file_path,
            rules=all_rules,
            at_rules=all_at_rules,
            total_style_rules=len(all_rules),
            total_declarations=total_declarations,
            unique_property_count=len(property_counter),
            property_frequency=dict(property_counter.most_common()),
            parse_errors=parse_errors,
            comments_count=comments_counter[0],
            source_bytes=source_bytes,
            source_lines=source_lines,
        )
