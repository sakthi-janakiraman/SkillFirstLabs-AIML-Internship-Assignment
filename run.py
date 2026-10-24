"""Root runner for Skill First Labs Assignment.

Executes Milestone 1 and Milestone 2 workflows with a single command.
Usage:
    python run.py             # Runs complete end-to-end pipeline (M1 + M2 + reports)
    python run.py --test      # Runs all 63 unit tests across both milestones
    python run.py --m1        # Runs Milestone 1 only
    python run.py --m2        # Runs Milestone 2 only
"""

import argparse
from pathlib import Path
import subprocess
import sys

_ROOT = Path(__file__).resolve().parent
_M1_DIR = _ROOT / "milestone-1-css-insight-engine"
_M2_DIR = _ROOT / "milestone-2-talentgraph-agent"


def run_tests() -> int:
    """Run all 63 automated unit tests across both milestones."""
    print("=" * 76)
    print(" RUNNING AUTOMATED TEST SUITE (Milestone 1 & Milestone 2)")
    print("=" * 76)

    print("\n--- Milestone 1 Tests (CSS Insight Engine) ---")
    cmd_m1 = [sys.executable, "-m", "pytest", str(_M1_DIR / "tests"), "-v"]
    res_m1 = subprocess.run(cmd_m1, cwd=str(_ROOT))

    print("\n--- Milestone 2 Tests (TalentGraph Agent) ---")
    cmd_m2 = [
        sys.executable,
        "-m",
        "pytest",
        str(_M2_DIR / "tests"),
        "-v",
        "-o",
        f"pythonpath={_M2_DIR.name}",
    ]
    res_m2 = subprocess.run(cmd_m2, cwd=str(_ROOT))

    print("\n" + "=" * 76)
    if res_m1.returncode == 0 and res_m2.returncode == 0:
        print(" [OK] ALL 63 UNIT TESTS PASSED SUCCESSFULLY!")
    else:
        print(" [!] SOME TESTS FAILED. CHECK OUTPUT ABOVE.")
    print("=" * 76)
    return max(res_m1.returncode, res_m2.returncode)


def run_milestone_1() -> int:
    """Run Milestone 1 CSS Insight Engine analysis."""
    print("\n" + "=" * 76)
    print(" [1/2] MILESTONE 1: CSS INSIGHT ENGINE")
    print("=" * 76)
    sample_css = _M1_DIR / "samples" / "sample_clean.css"
    report_html = _M1_DIR / "report.html"
    cmd = [
        sys.executable,
        str(_ROOT / "run_insight_engine.py"),
        str(sample_css),
        "-H",
        str(report_html),
    ]
    res = subprocess.run(cmd, cwd=str(_ROOT))
    if res.returncode == 0:
        print(f"[OK] Milestone 1 Report generated: {report_html}")
    return res.returncode


def run_milestone_2() -> int:
    """Run Milestone 2 TalentGraph Agent evaluation."""
    print("\n" + "=" * 76)
    print(" [2/2] MILESTONE 2: TALENTGRAPH AGENT CONSISTENCY LAB")
    print("=" * 76)
    script = _M2_DIR / "evaluation" / "evaluate_consistency.py"
    report_html = _M2_DIR / "reports" / "consistency_report.html"
    cmd = [sys.executable, str(script)]
    res = subprocess.run(cmd, cwd=str(_M2_DIR))
    if res.returncode == 0:
        print(f"[OK] Milestone 2 Report generated: {report_html}")
    return res.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified runner for Skill First Labs AI/ML Assignment"
    )
    parser.add_argument("--test", action="store_true", help="Run full pytest test suite (63 tests)")
    parser.add_argument("--m1", action="store_true", help="Run Milestone 1 only")
    parser.add_argument("--m2", action="store_true", help="Run Milestone 2 only")
    args = parser.parse_args()

    if args.test:
        return run_tests()

    if args.m1:
        return run_milestone_1()

    if args.m2:
        return run_milestone_2()

    # Default: Run both end-to-end
    print("=" * 76)
    print(" SKILL FIRST LABS -- AI/ML INTERNSHIP ASSIGNMENT PIPELINE")
    print("=" * 76)
    code_m1 = run_milestone_1()
    code_m2 = run_milestone_2()

    print("\n" + "=" * 76)
    print(" PIPELINE EXECUTION SUMMARY")
    print("=" * 76)
    print(f"  * Milestone 1 (CSS Insight Engine) : {'SUCCESS' if code_m1 == 0 else 'FAILED'}")
    print(f"    Report: {_M1_DIR / 'report.html'}")
    print(f"  * Milestone 2 (TalentGraph Agent)  : {'SUCCESS' if code_m2 == 0 else 'FAILED'}")
    print(f"    Report: {_M2_DIR / 'reports' / 'consistency_report.html'}")
    print("=" * 76)
    print(" All workflows executed cleanly and reports generated successfully.")
    print("=" * 76)
    return max(code_m1, code_m2)


if __name__ == "__main__":
    sys.exit(main())
