"""Root convenience runner for CSS Insight Engine."""

import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_DIR = Path(__file__).resolve().parent / "milestone-1-css-insight-engine"
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from src.cli import main

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        # Default to analyzing sample_clean.css and generating HTML report
        sample_file = _PROJECT_DIR / "samples" / "sample_clean.css"
        report_file = _PROJECT_DIR / "report.html"
        print("[Info] No arguments provided. Running default analysis on sample_clean.css...")
        sys.exit(main([str(sample_file), "-H", str(report_file)]))
    sys.exit(main(args))
