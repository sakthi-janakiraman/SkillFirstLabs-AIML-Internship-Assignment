import argparse
from pathlib import Path
import sys

# Ensure milestone-1-css-insight-engine directory is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.analyzer import CSSAnalyzer
from src.parser import CSSParser
from src.report import ReportGenerator


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="css-insight",
        description="CSS Insight Engine: From Raw Stylesheets to Explainable Design Intelligence",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input CSS file",
    )
    parser.add_argument(
        "-i", "--input-file",
        dest="flag_input",
        help="Path to input CSS file (alternative to positional argument)",
    )
    parser.add_argument(
        "-j", "--json",
        dest="output_json",
        help="Path to write structured JSON analysis report",
    )
    parser.add_argument(
        "-H", "--html",
        dest="output_html",
        help="Path to write self-contained offline HTML report",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=int,
        default=3,
        help="Repetition threshold for design token candidates (default: 3)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress terminal summary output",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not print terminal summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    css_path = args.input or args.flag_input
    if not css_path:
        parser.print_help()
        print("\nError: Please specify an input CSS file.", file=sys.stderr)
        return 1

    path = Path(css_path)
    if not path.is_file():
        print(f"Error: File not found: {path.resolve()}", file=sys.stderr)
        return 1

    try:
        css_parser = CSSParser.from_file(path)
        parsed = css_parser.parse()

        analyzer = CSSAnalyzer(parsed, repetition_threshold=args.threshold)
        result = analyzer.analyze()

        report_gen = ReportGenerator(result)

        # Output JSON if requested
        if args.output_json:
            json_path = report_gen.write_json(args.output_json)
            if not args.quiet:
                print(f"[+] Wrote JSON report to: {json_path}")

        # Output HTML if requested
        if args.output_html:
            html_path = report_gen.write_html(args.output_html)
            if not args.quiet:
                print(f"[+] Wrote HTML report to: {html_path}")

        # Print terminal summary unless suppressed
        if not args.quiet and not args.no_summary:
            print(report_gen.generate_terminal_summary())

        return 0

    except Exception as e:
        print(f"Engine Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
