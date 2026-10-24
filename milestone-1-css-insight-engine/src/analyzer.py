"""Design token discovery and static quality checks.

Extracts colors, typography, spacing, border-radii, and CSS custom properties.
Performs explainable static checks for repeated declarations, excessive !important,
and repeated literal design values.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from src.models import (
    AnalysisResult,
    Declaration,
    ParsedStylesheet,
    QualityFinding,
    SourceLocation,
    StyleRule,
    TokenItem,
    TokenOccurrence,
)

# Common CSS named colors
NAMED_COLORS = {
    "black", "white", "transparent", "currentcolor", "red", "green", "blue",
    "yellow", "orange", "purple", "cyan", "magenta", "gray", "grey", "silver",
    "navy", "teal", "aqua", "maroon", "olive", "lime", "fuchsia"
}

# Regex patterns for token value extraction
RE_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b")
RE_FUNC_COLOR = re.compile(
    r"\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|color-mix|color)\([^)]*\)",
    re.IGNORECASE,
)
RE_VAR_CALL = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)")
RE_DIMENSION = re.compile(r"^-?\d+(?:\.\d+)?(?:px|rem|em|%|vh|vw|vmin|vmax|ch|ex|pt|pc|in|cm|mm)$")

COLOR_PROPERTIES = {
    "color", "background-color", "background", "border-color", "border",
    "border-top-color", "border-bottom-color", "border-left-color", "border-right-color",
    "outline-color", "outline", "box-shadow", "text-shadow", "fill", "stroke",
    "accent-color", "caret-color", "text-decoration-color"
}

SPACING_PROPERTIES = {
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-inline", "margin-block", "margin-inline-start", "margin-inline-end",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-inline", "padding-block", "padding-inline-start", "padding-inline-end",
    "gap", "row-gap", "column-gap"
}

RADIUS_PROPERTIES = {
    "border-radius", "border-top-left-radius", "border-top-right-radius",
    "border-bottom-left-radius", "border-bottom-right-radius"
}

FONT_SIZE_PROPERTIES = {"font-size"}
FONT_FAMILY_PROPERTIES = {"font-family"}

FALLBACK_KEYWORDS = {"linear-gradient", "radial-gradient", "clamp(", "min(", "max(", "-webkit-", "-moz-", "-ms-", "color-mix"}


def _normalize_color(raw_val: str) -> str:
    """Normalize color strings while preserving syntactical identity."""
    val = raw_val.strip()
    if val.startswith("#"):
        return val.lower()
    # Normalize internal spaces in functional forms like rgb( 10, 20 , 30 )
    val_compact = re.sub(r"\s*([(),])\s*", r"\1", val).lower()
    return val_compact


def _suggest_variable_name(category: str, raw_val: str, index: int) -> str:
    """Generate a clean semantic CSS custom property name recommendation."""
    if category == "color":
        clean = re.sub(r"[^a-zA-Z0-9]", "", raw_val).lower()
        if raw_val.startswith("#"):
            return f"--color-palette-{clean[:6]}"
        return f"--color-token-{index}"
    if category == "spacing":
        clean = re.sub(r"[^a-zA-Z0-9]", "", raw_val)
        return f"--spacing-{clean}"
    if category == "font_size":
        clean = re.sub(r"[^a-zA-Z0-9]", "", raw_val)
        return f"--font-size-{clean}"
    if category == "border_radius":
        clean = re.sub(r"[^a-zA-Z0-9]", "", raw_val)
        return f"--radius-{clean}"
    return f"--token-{category}-{index}"


IGNORE_CANDIDATE_VALUES = {
    "0", "0px", "0rem", "0em", "0%", "none", "auto", "inherit", "initial", "unset",
    "transparent", "currentcolor", "normal"
}


class CSSAnalyzer:
    """Static analysis engine discovering design tokens and quality insights."""

    def __init__(self, parsed: ParsedStylesheet, repetition_threshold: int = 3) -> None:
        self.parsed = parsed
        self.threshold = repetition_threshold

    def analyze(self) -> AnalysisResult:
        """Run token cataloging and explainable static checks."""
        token_catalog = self._discover_tokens()
        token_candidates = self._identify_token_candidates(token_catalog)
        quality_findings = self._run_quality_checks(token_candidates)

        stats = {
            "total_rules": self.parsed.total_style_rules,
            "total_declarations": self.parsed.total_declarations,
            "unique_properties": self.parsed.unique_property_count,
            "total_colors": len(token_catalog.get("colors", [])),
            "total_spacings": len(token_catalog.get("spacings", [])),
            "total_custom_properties": len(token_catalog.get("custom_properties", [])),
            "token_candidate_count": len(token_candidates),
            "quality_findings_count": len(quality_findings),
            "important_declarations_count": sum(
                1 for r in self.parsed.rules for d in r.declarations if d.important
            ),
        }

        return AnalysisResult(
            parsed=self.parsed,
            token_catalog=token_catalog,
            token_candidates=token_candidates,
            quality_findings=quality_findings,
            stats=stats,
        )

    def _discover_tokens(self) -> dict[str, list[TokenItem]]:
        """Extract and categorize design tokens from all declarations."""
        colors_map: dict[str, list[TokenOccurrence]] = defaultdict(list)
        font_families_map: dict[str, list[TokenOccurrence]] = defaultdict(list)
        font_sizes_map: dict[str, list[TokenOccurrence]] = defaultdict(list)
        spacings_map: dict[str, list[TokenOccurrence]] = defaultdict(list)
        radius_map: dict[str, list[TokenOccurrence]] = defaultdict(list)
        custom_props_map: dict[str, list[TokenOccurrence]] = defaultdict(list)

        for rule in self.parsed.rules:
            selector = rule.selector_text

            for decl in rule.declarations:
                prop = decl.name
                val = decl.value
                loc = decl.location

                # 1. Custom Properties (--*)
                if decl.is_custom_property:
                    occ = TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    custom_props_map[f"{prop}: {val}"].append(occ)

                # Skip tokenizing if value is already a variable reference
                has_var = "var(" in val

                # 2. Colors
                # Look for hex codes
                for hex_code in RE_HEX_COLOR.findall(val):
                    colors_map[hex_code].append(
                        TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    )

                # Look for functional colors (rgb, rgba, hsl, etc.)
                for fn_color in RE_FUNC_COLOR.findall(val):
                    colors_map[fn_color].append(
                        TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    )

                # Named colors when in color-specific properties
                if prop in COLOR_PROPERTIES and not has_var:
                    for word in re.split(r"[\s,;]+", val.strip()):
                        lower_word = word.lower()
                        if lower_word in NAMED_COLORS:
                            colors_map[word].append(
                                TokenOccurrence(selector=selector, property_name=prop, location=loc)
                            )

                # 3. Font Family
                if prop in FONT_FAMILY_PROPERTIES and not has_var:
                    font_families_map[val].append(
                        TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    )

                # 4. Font Size
                if prop in FONT_SIZE_PROPERTIES and not has_var:
                    font_sizes_map[val].append(
                        TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    )

                # 5. Spacings
                if prop in SPACING_PROPERTIES and not has_var:
                    spacings_map[val].append(
                        TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    )

                # 6. Border Radius
                if prop in RADIUS_PROPERTIES and not has_var:
                    radius_map[val].append(
                        TokenOccurrence(selector=selector, property_name=prop, location=loc)
                    )

        # Convert maps to TokenItem lists
        catalog: dict[str, list[TokenItem]] = {
            "colors": self._build_token_items("color", colors_map, normalizer=_normalize_color),
            "font_families": self._build_token_items("font_family", font_families_map),
            "font_sizes": self._build_token_items("font_size", font_sizes_map),
            "spacings": self._build_token_items("spacing", spacings_map),
            "border_radii": self._build_token_items("border_radius", radius_map),
            "custom_properties": self._build_token_items(
                "custom_property", custom_props_map, is_custom_property=True
            ),
        }

        return catalog

    def _build_token_items(
        self,
        category: str,
        occurrence_map: dict[str, list[TokenOccurrence]],
        normalizer: Any = None,
        is_custom_property: bool = False,
    ) -> list[TokenItem]:
        """Aggregate occurrences into TokenItem records sorted by frequency."""
        items: list[TokenItem] = []
        for raw_val, occurrences in occurrence_map.items():
            norm_val = normalizer(raw_val) if normalizer else raw_val.strip()
            count = len(occurrences)
            is_candidate = (
                not is_custom_property
                and raw_val.lower() not in IGNORE_CANDIDATE_VALUES
                and count >= self.threshold
                and category in {"color", "spacing", "font_size", "border_radius"}
            )
            items.append(
                TokenItem(
                    category=category,
                    raw_value=raw_val,
                    normalized_value=norm_val,
                    count=count,
                    occurrences=occurrences,
                    is_custom_property=is_custom_property,
                    is_token_candidate=is_candidate,
                )
            )

        items.sort(key=lambda t: t.count, reverse=True)
        return items

    def _identify_token_candidates(
        self, token_catalog: dict[str, list[TokenItem]]
    ) -> list[TokenItem]:
        """Collect high-frequency literal values suitable for tokenization."""
        candidates: list[TokenItem] = []
        for cat, items in token_catalog.items():
            if cat == "custom_properties":
                continue
            for item in items:
                if item.is_token_candidate:
                    candidates.append(item)
        candidates.sort(key=lambda c: c.count, reverse=True)
        return candidates

    def _run_quality_checks(self, candidates: list[TokenItem]) -> list[QualityFinding]:
        """Execute the static quality checks."""
        findings: list[QualityFinding] = []

        # Track defined vs consumed custom properties
        defined_vars: set[str] = set()
        consumed_vars: list[tuple[str, str, SourceLocation | None]] = []

        # Check A: Repeated Declarations within same rule block
        # Check B: Excessive !important usage
        for rule in self.parsed.rules:
            selector = rule.selector_text

            # Group declarations by property name
            prop_decls: dict[str, list[Declaration]] = defaultdict(list)
            for decl in rule.declarations:
                prop_decls[decl.name].append(decl)

                if decl.is_custom_property:
                    defined_vars.add(decl.name)

                # Scan for consumed var(--*)
                for var_name in RE_VAR_CALL.findall(decl.value):
                    consumed_vars.append((var_name, selector, decl.location))

                # Check B: !important detection
                if decl.important:
                    findings.append(
                        QualityFinding(
                            check_id="excessive-important",
                            severity="warning"
                            if sum(1 for r in self.parsed.rules for d in r.declarations if d.important) >= 3
                            else "advisory",
                            title="Cascade Specificity Override (!important)",
                            rule_selector=selector,
                            property_name=decl.name,
                            location=decl.location,
                            explanation=(
                                f"Declaration '{decl.name}: {decl.value} !important' overrides normal "
                                "cascade specificity. Using !important creates technical debt and makes "
                                "future design system component overrides error-prone."
                            ),
                            suggested_improvement=(
                                "Refactor selector specificity (e.g., scoping with a parent class) "
                                "or use CSS Cascade Layers (@layer) instead of !important."
                            ),
                            context={"property": decl.name, "value": decl.value},
                        )
                    )

            # Analyze property repetitions in this rule
            for prop_name, decls in prop_decls.items():
                if len(decls) <= 1:
                    continue

                for i in range(1, len(decls)):
                    prev = decls[i - 1]
                    curr = decls[i]

                    if prev.value == curr.value and prev.important == curr.important:
                        # Exact duplicate
                        findings.append(
                            QualityFinding(
                                check_id="repeated-declaration",
                                severity="warning",
                                title="Exact Duplicate Declaration",
                                rule_selector=selector,
                                property_name=prop_name,
                                location=curr.location,
                                explanation=(
                                    f"Property '{prop_name}' is declared multiple times with identical "
                                    f"value '{curr.value}'. The second declaration is redundant."
                                ),
                                suggested_improvement=(
                                    f"Delete the redundant duplicate declaration at line {curr.location.line if curr.location else 'unknown'}."
                                ),
                                context={"value": curr.value, "first_location": prev.location.to_dict() if prev.location else None},
                            )
                        )
                    else:
                        # Different value override - check if it's progressive enhancement
                        is_fallback = any(
                            kw in curr.value.lower() or kw in prev.value.lower()
                            for kw in FALLBACK_KEYWORDS
                        ) or prop_name.startswith("-") or prev.value.startswith("-")

                        if is_fallback:
                            findings.append(
                                QualityFinding(
                                    check_id="repeated-declaration",
                                    severity="info",
                                    title="Progressive Enhancement Fallback",
                                    rule_selector=selector,
                                    property_name=prop_name,
                                    location=curr.location,
                                    explanation=(
                                        f"Property '{prop_name}' has fallback '{prev.value}' followed by "
                                        f"modern syntax '{curr.value}'. This is an intentional backward-compatibility pattern."
                                    ),
                                    suggested_improvement=(
                                        "Retain if legacy browser support is required; otherwise modernize to standard syntax."
                                    ),
                                    context={"fallback": prev.value, "modern": curr.value},
                                )
                            )
                        else:
                            findings.append(
                                QualityFinding(
                                    check_id="repeated-declaration",
                                    severity="advisory",
                                    title="Overwritten Property Declaration",
                                    rule_selector=selector,
                                    property_name=prop_name,
                                    location=curr.location,
                                    explanation=(
                                        f"Property '{prop_name}' was set to '{prev.value}' (line {prev.location.line if prev.location else '?'}) "
                                        f"but overridden by '{curr.value}' in the same block. The earlier value is never rendered."
                                    ),
                                    suggested_improvement=(
                                        f"Remove the superseded declaration or check if '{prev.value}' belonged to another selector/state."
                                    ),
                                    context={"overwritten": prev.value, "active": curr.value},
                                )
                            )

        # Check C: Repeated Design Values (Tokenization Opportunities)
        for idx, candidate in enumerate(candidates, 1):
            suggested_var = _suggest_variable_name(candidate.category, candidate.raw_value, idx)
            first_occ = candidate.occurrences[0] if candidate.occurrences else None
            loc = first_occ.location if first_occ else None
            selectors = list({o.selector for o in candidate.occurrences})
            sample_selectors = ", ".join(selectors[:3])
            if len(selectors) > 3:
                sample_selectors += f" (+{len(selectors) - 3} more)"

            findings.append(
                QualityFinding(
                    check_id="repeated-design-value",
                    severity="advisory",
                    title="Un-tokenized Repeated Design Value",
                    rule_selector=sample_selectors,
                    property_name=first_occ.property_name if first_occ else None,
                    location=loc,
                    explanation=(
                        f"Literal {candidate.category.replace('_', ' ')} '{candidate.raw_value}' is repeated "
                        f"{candidate.count} times across {len(selectors)} rules without using a design token. "
                        "Hardcoded values make theme updates error-prone."
                    ),
                    suggested_improvement=(
                        f"Extract into `:root {{ {suggested_var}: {candidate.raw_value}; }}` and "
                        f"replace hardcoded instances with `var({suggested_var})`."
                    ),
                    context={
                        "category": candidate.category,
                        "value": candidate.raw_value,
                        "count": candidate.count,
                        "suggested_var": suggested_var,
                    },
                )
            )

        # Check D: Undefined CSS Custom Property Reference
        for var_name, selector, loc in consumed_vars:
            if var_name not in defined_vars:
                findings.append(
                    QualityFinding(
                        check_id="undefined-variable",
                        severity="warning",
                        title="Undefined CSS Custom Property",
                        rule_selector=selector,
                        property_name=None,
                        location=loc,
                        explanation=(
                            f"Custom property '{var_name}' is referenced via var() in rule '{selector}', "
                            "but is never declared in this stylesheet. In browsers, it will resolve to unset."
                        ),
                        suggested_improvement=(
                            f"Declare '{var_name}' in `:root` or supply an in-line fallback: `var({var_name}, fallback_value)`."
                        ),
                        context={"variable": var_name},
                    )
                )

        return findings
