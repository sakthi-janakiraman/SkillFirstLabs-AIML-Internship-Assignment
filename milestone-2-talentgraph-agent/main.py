"""TalentGraph Agent - Command Line Interface (CLI).

Interactive career intelligence assistant with real-time tool execution traces,
automated demo runners, and direct consistency lab integration.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.agent import TalentGraphAgent, format_trace
from src.config import (
    OPENAI_MODEL_NAME,
    TEMPERATURE,
    is_live_api_configured,
    mask_secret,
    OPENAI_API_KEY,
    REPORTS_DIR,
)
from src.data_loader import default_data_loader
from evaluation.evaluate_consistency import run_consistency_evaluation

DEMO_QUESTIONS = [
    "1. What skills does student S001 have?",
    "2. Find internships requiring Python.",
    "3. How suitable is student S001 for internship I002?",
    "4. Which required skills are missing for student S001 when applying for internship I001?",
    "5. Which internship has the highest skill-overlap score for student S001?",
    "6. What is the GPA of student S001 if GPA is not stored?",
    "7. What do you know about student S999?",
    "8. Can you recommend learning topics for the missing skills of student S001 for internship I001?",
]


def print_banner() -> None:
    """Print application banner and active configuration status."""
    is_live = is_live_api_configured()
    mode_text = f"Live OpenAI API ({OPENAI_MODEL_NAME})" if is_live else "Deterministic Mock Engine (Offline Mode)"
    api_key_status = mask_secret(OPENAI_API_KEY) if is_live else "Not configured / Running mock tools"

    print("=" * 76)
    print("  TALENTGRAPH AGENT  |  Explainable AI Career Intelligence Assistant")
    print("=" * 76)
    print(f"  Execution Engine:  {mode_text}")
    print(f"  API Key Status:    {api_key_status}")
    print(f"  Generation Temp:   {TEMPERATURE}")
    print(f"  Verified Records:  {len(default_data_loader.get_all_students())} students, "
          f"{len(default_data_loader.get_all_internships())} internships, "
          f"{len(default_data_loader.get_all_learning_topics())} skill roadmaps")
    print("=" * 76)
    print("  Commands:")
    print("    'demo'       - Run all 8 canonical demonstration queries with traces")
    print("    'eval'       - Execute Consistency Lab evaluation (JSON & HTML reports)")
    print("    'console'    - Generate & locate TalentGraph Operations Console HTML")
    print("    'trace on'   - Show detailed tool execution traces (Default: ON)")
    print("    'trace off'  - Show only final grounded answers")
    print("    'exit'       - Quit the application")
    print("=" * 76)


def run_interactive_session(show_trace: bool = True) -> None:
    """Run interactive REPL loop."""
    agent = TalentGraphAgent()
    print_banner()

    while True:
        try:
            user_input = input("\n[TalentGraph] Question > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting TalentGraph Agent. Goodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("exit", "quit", "q"):
            print("Exiting TalentGraph Agent. Goodbye!")
            break
        elif cmd == "demo":
            run_demo_suite(agent, show_trace=show_trace)
            continue
        elif cmd in ("eval", "console", "ui"):
            run_consistency_evaluation()
            console_url = (REPORTS_DIR / "consistency_report.html").resolve()
            print(f"\n[+] Operations Console ready: file:///{console_url}")
            continue
        elif cmd == "trace on":
            show_trace = True
            print("Detailed tool execution traces: ENABLED")
            continue
        elif cmd == "trace off":
            show_trace = False
            print("Detailed tool execution traces: DISABLED")
            continue
        elif cmd in ("help", "?"):
            print("\nCanonical Demo Questions:")
            for q in DEMO_QUESTIONS:
                print(f"  • {q}")
            continue

        # Execute agent query
        print("\nThinking and invoking tools...")
        result = agent.query(user_input)

        if show_trace:
            print("\n--- TOOL EXECUTION TRACE ---")
            print(format_trace(result["trace"]))
            print("----------------------------")

        print("\n--- GROUNDED ANSWER ---")
        print(result["final_answer"])
        print("-" * 24)
        print(f"(Latency: {result['execution_time_seconds']}s | Tool steps: {result['tool_iterations']} | Grounded: {result['grounding_audit']['is_grounded']})")


def run_demo_suite(agent: TalentGraphAgent, show_trace: bool = True) -> None:
    """Run all 8 canonical demo questions with visible traces."""
    print("\n" + "#" * 76)
    print("  RUNNING CANONICAL TALENTGRAPH DEMO SUITE (8 Questions)")
    print("#" * 76)

    for idx, q_str in enumerate(DEMO_QUESTIONS, 1):
        clean_q = q_str.split(". ", 1)[-1]
        print(f"\n[{idx}/8] QUESTION: \"{clean_q}\"")

        res = agent.query(clean_q)

        if show_trace:
            print("\n[Tool Execution Trace]")
            print(format_trace(res["trace"]))

        print("\n[Grounded Final Answer]")
        print(res["final_answer"])
        print(f"[Audit: Grounded={res['grounding_audit']['is_grounded']}, Execution Time={res['execution_time_seconds']}s]")
        print("-" * 76)
        time.sleep(0.3)

    print("\nDemo suite execution completed successfully.")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="TalentGraph Agent - Explainable AI Career Intelligence Assistant",
    )
    parser.add_argument(
        "query",
        nargs="?",
        type=str,
        help="Optional single query to execute directly from CLI",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run through the 8 canonical demonstration questions",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run the Consistency Lab evaluation suite",
    )
    parser.add_argument(
        "--console",
        "--ui",
        dest="console",
        action="store_true",
        help="Generate and locate the TalentGraph Operations Console HTML dashboard",
    )
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Suppress tool execution traces in output",
    )
    parser.add_argument(
        "--force-mock",
        action="store_true",
        help="Force deterministic mock mode even if OpenAI credentials are set",
    )

    args = parser.parse_args()
    show_trace = not args.no_trace

    if args.eval or args.console:
        run_consistency_evaluation(force_mock=args.force_mock)
        if args.console:
            console_path = (REPORTS_DIR / "consistency_report.html").resolve()
            print(f"\n[+] TalentGraph Operations Console available at:\n    file:///{console_path}")
    elif args.demo:
        agent = TalentGraphAgent(force_mock=args.force_mock)
        run_demo_suite(agent, show_trace=show_trace)
    elif args.query:
        agent = TalentGraphAgent(force_mock=args.force_mock)
        res = agent.query(args.query)
        if show_trace:
            print("--- TOOL EXECUTION TRACE ---")
            print(format_trace(res["trace"]))
            print("----------------------------\n")
        print("--- GROUNDED ANSWER ---")
        print(res["final_answer"])
    else:
        run_interactive_session(show_trace=show_trace)


if __name__ == "__main__":
    main()
