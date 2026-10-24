"""Report generation module for CSS Insight Engine.

Produces:
1. Structured JSON output
2. Human-readable terminal summary
3. Self-contained, responsive, offline-ready HTML report
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from src.models import AnalysisResult, QualityFinding, TokenItem
from src.html_template import render_design_forensics_html


def _format_location(loc: Any) -> str:
    """Format source location as line:column or N/A."""
    if not loc:
        return "N/A"
    return f"L{loc.line}:C{loc.column}"


class ReportGenerator:
    """Generates JSON, CLI, and standalone HTML reports from analysis results."""

    def __init__(self, result: AnalysisResult) -> None:
        self.result = result
        self.parsed = result.parsed

    def generate_json(self, indent: int = 2) -> str:
        """Return serialized JSON string of analysis results."""
        return json.dumps(self.result.to_dict(), indent=indent, ensure_ascii=False)

    def write_json(self, destination: str | Path, indent: int = 2) -> Path:
        """Write JSON output to target file path."""
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.generate_json(indent=indent), encoding="utf-8")
        return path

    def generate_terminal_summary(self) -> str:
        """Build clean human-readable terminal report."""
        stats = self.result.stats
        p = self.parsed
        fn = p.file_path or "inline_css"

        lines: list[str] = [
            "=" * 76,
            " CSS INSIGHT ENGINE - DESIGN INTELLIGENCE & QUALITY REPORT",
            "=" * 76,
            f" File: {fn}",
            f" Source: {p.source_lines} lines | {p.source_bytes} bytes | {p.comments_count} comments",
            "-" * 76,
            " OVERVIEW METRICS",
            f"  * Total Style Rules       : {stats['total_rules']}",
            f"  * Total Declarations      : {stats['total_declarations']}",
            f"  * Unique CSS Properties   : {stats['unique_properties']}",
            f"  * !important Declarations : {stats['important_declarations_count']}",
            f"  * CSS Custom Properties   : {stats['total_custom_properties']}",
            f"  * Colors Extracted        : {stats['total_colors']}",
            f"  * Spacings Extracted      : {stats['total_spacings']}",
            f"  * Quality Findings        : {stats['quality_findings_count']}",
            "-" * 76,
        ]

        # Top properties
        lines.append(" TOP CSS PROPERTIES FREQUENCY:")
        top_props = list(p.property_frequency.items())[:8]
        if top_props:
            max_count = max(c for _, c in top_props)
            for prop, count in top_props:
                bar_len = int((count / max(max_count, 1)) * 24)
                bar = "#" * bar_len
                lines.append(f"  {prop:<24} : {count:>3} occurrences [{bar:<24}]")
        else:
            lines.append("  (No declarations parsed)")

        lines.append("-" * 76)

        # High-confidence design token candidates
        lines.append(" TOKENIZATION CANDIDATES (Frequently Repeated Literal Values):")
        if self.result.token_candidates:
            for c in self.result.token_candidates[:6]:
                sample_rule = c.occurrences[0].selector if c.occurrences else "?"
                lines.append(
                    f"  * [{c.category.upper():<12}] {c.raw_value:<20} x{c.count:<2} (e.g. {sample_rule})"
                )
        else:
            lines.append("  * No repeated literal values exceeded the threshold (clean token usage).")

        lines.append("-" * 76)

        # Quality Insights
        lines.append(" QUALITY & SPECIFICITY FINDINGS:")
        if self.result.quality_findings:
            warnings = [f for f in self.result.quality_findings if f.severity == "warning"]
            advisories = [f for f in self.result.quality_findings if f.severity == "advisory"]
            infos = [f for f in self.result.quality_findings if f.severity == "info"]

            lines.append(f"  Found {len(warnings)} Warnings | {len(advisories)} Advisories | {len(infos)} Info notices\n")

            for f in self.result.quality_findings:
                loc_str = _format_location(f.location)
                tag = f"[{f.severity.upper()}]"
                lines.append(f"  {tag:<11} {f.title} ({loc_str})")
                lines.append(f"              Target  : {f.rule_selector}")
                if f.property_name:
                    lines.append(f"              Property: {f.property_name}")
                lines.append(f"              Why     : {f.explanation}")
                lines.append(f"              Fix     : {f.suggested_improvement}\n")
        else:
            lines.append("  * Excellent! No duplicate declarations, specificity issues, or untokenized repetitions detected.")

        if p.parse_errors:
            lines.append("-" * 76)
            lines.append(f" PARSE ERRORS / RECOVERED TOKENS ({len(p.parse_errors)}):")
            for err in p.parse_errors:
                lines.append(f"  * L{err.get('line', '?')}:C{err.get('column', '?')} - {err.get('message', 'Syntax recovery')}")

        lines.append("=" * 76)
        return "\n".join(lines)

    def write_html(self, destination: str | Path) -> Path:
        """Generate and save self-contained responsive HTML report."""
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        html_content = self.generate_html()
        path.write_text(html_content, encoding="utf-8")
        return path

    def generate_html(self) -> str:
        """Render standalone, offline-ready HTML report with The Design Forensics Studio interface."""
        return render_design_forensics_html(self.result)
